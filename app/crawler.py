import time
import json
import os
from datetime import datetime
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def create_driver():
    """Docker 환경에 최적화된 Chrome 드라이버 생성"""
    options = uc.ChromeOptions()
    
    # Docker 환경 필수 옵션
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-features=VizDisplayCompositor')
    options.add_argument('--disable-setuid-sandbox')
    
    # 메모리 최적화
    options.add_argument('--memory-pressure-off')
    options.add_argument('--max_old_space_size=4096')
    
    # 성능 옵션
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-extensions')
    
    options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = uc.Chrome(options=options, version_main=None)
    driver.set_page_load_timeout(30)
    
    return driver

def scrape_timetable(url):
    """시간표 스크래핑 함수"""
    driver = None
    try:
        driver = create_driver()
        print(f"페이지 접속: {url}")
        driver.get(url)
        
        # 페이지 로딩 대기
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.tablebody, div.tablebody"))
            )
        except:
            pass
        
        time.sleep(5)
        
        # JavaScript 코드 - BASE_HOUR 계산 추가
        js_script = """
        function extractTimetable() {
            var result = {
                subjects: [],
                daysMap: [],
                debug: []
            };
            
            // BASE_HOUR 계산 - 시간표 시작 시간 파악
            var BASE_HOUR = 9;  // 기본값
            var tableBody = document.querySelector('table.tablebody');
            if (tableBody) {
                var style = window.getComputedStyle(tableBody);
                var marginTop = style.marginTop;
                result.debug.push('=== margin-top: ' + marginTop + ' ===');
                
                // margin-top에서 px 값 추출
                if (marginTop && marginTop.indexOf('px') > -1) {
                    var marginValue = parseInt(marginTop.replace('px', '')) || 0;
                    // margin-top이 음수면 그만큼 시간이 앞당겨짐
                    // 60px = 1시간, margin-top: -540px = 9시간 앞당김 = 9시 시작
                    if (marginValue < 0) {
                        BASE_HOUR = Math.abs(marginValue) / 60;
                    }
                }
            }
            
            result.debug.push('=== 계산된 BASE_HOUR: ' + BASE_HOUR + '시 ===');
            
            // 헤더 분석
            var headerRow = document.querySelector('table.tablehead tr');
            if (!headerRow) {
                result.debug.push('헤더 행을 찾을 수 없습니다');
                return result;
            }
            
            result.debug.push('=== 헤더 분석 ===');
            var allHeaderCells = headerRow.querySelectorAll('th, td');
            for (var i = 0; i < allHeaderCells.length; i++) {
                var cell = allHeaderCells[i];
                var tagName = cell.tagName;
                var text = cell.textContent.trim();
                var style = cell.getAttribute('style') || '';
                var isHidden = style.indexOf('display: none') > -1 || style.indexOf('display:none') > -1;
                result.debug.push('헤더[' + i + '] <' + tagName + '>: "' + text + '" ' + (isHidden ? '(숨김)' : ''));
            }
            
            // 요일만 추출 (th 제외하고 td만)
            var headerTds = headerRow.querySelectorAll('td');
            for (var i = 0; i < headerTds.length; i++) {
                var td = headerTds[i];
                var style = td.getAttribute('style') || '';
                if (style.indexOf('display: none') === -1 && style.indexOf('display:none') === -1) {
                    var dayText = td.textContent.trim();
                    if (dayText === '월' || dayText === '화' || dayText === '수' || 
                        dayText === '목' || dayText === '금' || dayText === '토' || dayText === '일') {
                        result.daysMap.push(dayText);
                    }
                }
            }
            
            // 본문 분석
            var bodyRow = document.querySelector('table.tablebody > tbody > tr');
            if (!bodyRow) {
                result.debug.push('본문 행을 찾을 수 없습니다');
                return result;
            }
            
            result.debug.push('');
            result.debug.push('=== 본문 분석 ===');
            
            // th(시간열)와 td(요일열) 분리
            var bodyTh = bodyRow.querySelector('th');
            var bodyTds = bodyRow.querySelectorAll('td');
            
            result.debug.push('본문 TH: ' + (bodyTh ? '시간열 존재' : '없음'));
            result.debug.push('본문 TD 개수: ' + bodyTds.length);
            
            // 과목 추출 - 60px = 1시간 기준
            for (var tdIndex = 0; tdIndex < bodyTds.length; tdIndex++) {
                var td = bodyTds[tdIndex];
                var subjects = td.querySelectorAll('div.subject');
                
                if (subjects.length > 0) {
                    // TD 인덱스로 직접 요일 결정
                    var dayName = (tdIndex < result.daysMap.length) ? result.daysMap[tdIndex] : null;
                    
                    if (!dayName) {
                        continue;
                    }
                    
                    for (var s = 0; s < subjects.length; s++) {
                        var subj = subjects[s];
                        var style = subj.getAttribute('style') || '';
                        
                        // top과 height 값 추출
                        var top = 0;
                        var height = 0;
                        
                        if (style.indexOf('top:') > -1) {
                            var topStart = style.indexOf('top:') + 4;
                            var topEnd = style.indexOf('px', topStart);
                            if (topEnd > topStart) {
                                var topStr = style.substring(topStart, topEnd).trim();
                                top = parseInt(topStr) || 0;
                            }
                        }
                        
                        if (style.indexOf('height:') > -1) {
                            var heightStart = style.indexOf('height:') + 7;
                            var heightEnd = style.indexOf('px', heightStart);
                            if (heightEnd > heightStart) {
                                var heightStr = style.substring(heightStart, heightEnd).trim();
                                height = parseInt(heightStr) || 0;
                            }
                        }
                        
                        // 과목 정보 추출
                        var name = '';
                        var h3 = subj.querySelector('h3');
                        if (h3) name = h3.textContent.trim();
                        
                        var professor = '';
                        var em = subj.querySelector('p em');
                        if (em) professor = em.textContent.trim();
                        
                        var location = '';
                        var span = subj.querySelector('p span');
                        if (span) location = span.textContent.trim();
                        
                        // 시간 계산 - 60px = 1시간 기준 (1px 보정)
                        var pixelsPerHour = 60;
                        var pixelsPerMinute = 1;  // 60px / 60분 = 1px per minute
                        
                        // 1px 보정 (시간표 UI 특성상 경계선 1px 제외)
                        var adjustedHeight = height - 1;
                        if (adjustedHeight < 0) adjustedHeight = 0;
                        
                        // 시작 시간 계산 (BASE_HOUR 적용)
                        var startTotalMinutes = Math.round(top / pixelsPerMinute);
                        var startHour = BASE_HOUR + Math.floor(startTotalMinutes / 60);
                        var startMin = startTotalMinutes % 60;
                        
                        // 종료 시간 계산 (BASE_HOUR 적용, 보정된 height 사용)
                        var endTotalMinutes = Math.round((top + adjustedHeight) / pixelsPerMinute);
                        var endHour = BASE_HOUR + Math.floor(endTotalMinutes / 60);
                        var endMin = endTotalMinutes % 60;
                        
                        var startTimeStr = (startHour < 10 ? '0' : '') + startHour + ':' + (startMin < 10 ? '0' : '') + startMin;
                        var endTimeStr = (endHour < 10 ? '0' : '') + endHour + ':' + (endMin < 10 ? '0' : '') + endMin;
                        
                        // 수업 시간 계산 (보정된 값 사용)
                        var durationMin = Math.round(adjustedHeight / pixelsPerMinute);
                        var durationHour = Math.floor(durationMin / 60);
                        var durationMinRem = durationMin % 60;
                        var durationStr = '';
                        if (durationHour > 0) {
                            durationStr = durationHour + '시간';
                            if (durationMinRem > 0) {
                                durationStr += ' ' + durationMinRem + '분';
                            }
                        } else {
                            durationStr = durationMinRem + '분';
                        }
                        
                        result.subjects.push({
                            name: name,
                            professor: professor,
                            location: location,
                            day: dayName,
                            startTime: startTimeStr,
                            endTime: endTimeStr,
                            duration: durationStr
                        });
                    }
                }
            }
            
            // 시간 미지정 과목들
            var nontimesDiv = document.querySelector('.nontimes');
            if (nontimesDiv) {
                var nontimeSubjects = nontimesDiv.querySelectorAll('.subject');
                for (var n = 0; n < nontimeSubjects.length; n++) {
                    var subj = nontimeSubjects[n];
                    var nameElem = subj.querySelector('.name');
                    var placeElem = subj.querySelector('.place');
                    
                    var name = nameElem ? nameElem.textContent.trim() : '';
                    var location = placeElem ? placeElem.textContent.trim() : '';
                    
                    if (location === '비지정()') location = '미정';
                    
                    result.subjects.push({
                        name: name,
                        professor: '',
                        location: location,
                        day: '미정',
                        startTime: '미정',
                        endTime: '미정',
                        duration: '미정'
                    });
                }
            }
            
            return result;
        }
        
        return extractTimetable();
        """
        
        # JavaScript 실행
        result = driver.execute_script(js_script)
        
        # 디버그 정보 출력 (옵션)
        if result and result.get('debug'):
            print("\n디버깅 정보:")
            for info in result['debug']:
                print(f"  {info}")
            print()
        
        # 데이터 처리
        if result and result.get('subjects'):
            subjects = result['subjects']
            
            # 요일 순서대로 정렬
            day_order = {'월': 1, '화': 2, '수': 3, '목': 4, '금': 5, '토': 6, '일': 7, '미정': 8}
            subjects.sort(key=lambda x: (
                day_order.get(x['day'], 9),
                x['startTime'] if x['startTime'] != '미정' else '99:99'
            ))
            
            return {
                'success': True,
                'data': subjects,
                'timestamp': datetime.now().isoformat(),
                'total': len(subjects)
            }
        else:
            return {
                'success': False,
                'error': '시간표 데이터를 찾을 수 없습니다',
                'timestamp': datetime.now().isoformat()
            }
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
    finally:
        if driver:
            try:
                driver.quit()
                print("브라우저 종료")
            except:
                pass