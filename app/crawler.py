import time
import json
import os
import random
from datetime import datetime
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from pyvirtualdisplay import Display

def create_driver():
    """Docker 환경에 최적화된 Chrome 드라이버 생성"""

    display = Display(visible=0, size=(1920, 1080))
    display.start()

    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-setuid-sandbox')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--lang=ko-KR')

    driver = uc.Chrome(options=options, version_main=145)
    driver.set_page_load_timeout(30)

    return driver, display

def scrape_timetable(url):
    """시간표 스크래핑 함수"""
    driver = None
    display = None
    try:
        driver, display = create_driver()
        
        time.sleep(random.uniform(2, 4))
        
        print(f"페이지 접속: {url}")
        driver.get(url)
        
        print("페이지 로딩 중...")
        time.sleep(random.uniform(8, 12))
        
        driver.execute_script("return document.readyState")
        time.sleep(5)
        
        # JavaScript 코드 - 로컬 코드와 동일한 로직 사용
        js_script = """
        function extractTimetable() {
            var result = {
                subjects: [],
                daysMap: [],
                debug: []
            };
            
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
            result.debug.push('');
            result.debug.push('=== TD별 과목 정보 ===');
            
            // 각 TD 내용 분석
            for (var i = 0; i < bodyTds.length; i++) {
                var td = bodyTds[i];
                var subjectCount = td.querySelectorAll('div.subject').length;
                
                // TD 인덱스가 곧 요일 인덱스
                var dayName = (i < result.daysMap.length) ? result.daysMap[i] : '?';
                
                if (subjectCount > 0) {
                    result.debug.push('TD[' + i + '] (' + dayName + '요일): ' + subjectCount + '개 과목');
                    var subjs = td.querySelectorAll('div.subject');
                    for (var j = 0; j < subjs.length; j++) {
                        var subj = subjs[j];
                        var name = subj.querySelector('h3') ? subj.querySelector('h3').textContent.trim() : '?';
                        var style = subj.getAttribute('style') || '';
                        result.debug.push('  -> ' + name + ': ' + style);
                    }
                }
            }
            
            result.debug.push('');
            result.debug.push('=== 과목 시간 계산 (60px = 1시간) ===');
            
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
                        
                        // *** 중요: 로컬 코드와 동일한 시간 계산 ***
                        // 시간 계산 - 60px = 1시간 기준 (1px = 1분)
                        var pixelsPerMinute = 1;  // 1px = 1분
                        
                        // 1px 보정 (시간표 UI 특성상 경계선 1px 제외)
                        var adjustedHeight = height - 1;
                        if (adjustedHeight < 0) adjustedHeight = 0;
                        
                        // 시작 시간 계산 (top 값이 곧 분 단위)
                        var startTotalMinutes = Math.round(top / pixelsPerMinute);  // top이 곧 분
                        var startHour = Math.floor(startTotalMinutes / 60);
                        var startMin = startTotalMinutes % 60;
                        
                        // 종료 시간 계산 (보정된 height 사용)
                        var endTotalMinutes = Math.round((top + adjustedHeight) / pixelsPerMinute);
                        var endHour = Math.floor(endTotalMinutes / 60);
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
                        
                        result.debug.push(dayName + '요일 ' + name);
                        result.debug.push('  위치: top=' + top + 'px -> ' + startTimeStr);
                        result.debug.push('  원본 height=' + height + 'px, 보정 후=' + adjustedHeight + 'px');
                        result.debug.push('  수업시간: ' + durationStr);
                        result.debug.push('  시간: ' + startTimeStr + ' ~ ' + endTimeStr);
                        result.debug.push('');
                        
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
            
            // margin-top 확인 (디버깅용)
            var tableBody = document.querySelector('table.tablebody');
            if (tableBody) {
                var style = window.getComputedStyle(tableBody);
                var marginTop = style.marginTop;
                result.debug.push('=== margin-top: ' + marginTop + ' ===');
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
        
        print("\n--- 데이터 추출 중 ---\n")
        
        # JavaScript 실행
        result = driver.execute_script(js_script)
        
        # 디버깅 정보 출력
        if result and result.get('debug'):
            print("\n🔍 디버깅 정보:")
            for info in result['debug']:
                print(f"   {info}")
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
            
            print(f"✅ {len(subjects)}개 과목 발견\n")
            
            # 디버깅: 각 과목 출력
            for subj in subjects:
                if subj['startTime'] != '미정':
                    print(f"📚 {subj['name']}")
                    print(f"   {subj['day']}요일 {subj['startTime']} ~ {subj['endTime']}")
            
            return {
                'success': True,
                'data': subjects,
                'timestamp': datetime.now().isoformat(),
                'total': len(subjects)
            }
        else:
            print("❌ 과목 데이터를 찾을 수 없습니다.")
            
            # 디버깅을 위해 스크린샷과 HTML 저장
            try:
                driver.save_screenshot("/app/debug_screenshot.png")
                print("📸 디버깅 스크린샷 저장: /app/debug_screenshot.png")
                
                with open('/app/debug_page.html', 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                print("📄 디버깅 HTML 저장: /app/debug_page.html")
            except Exception as e:
                print(f"디버깅 파일 저장 실패: {e}")
            
            return {
                'success': False,
                'error': '시간표 데이터를 찾을 수 없습니다',
                'timestamp': datetime.now().isoformat()
            }
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        
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
        if display:
            try:
                display.stop()
                print("가상 디스플레이 종료")
            except:
                pass