from datetime import datetime
import traceback

import undetected_chromedriver as uc
from pyvirtualdisplay import Display
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


DAY_ORDER = {"월": 1, "화": 2, "수": 3, "목": 4, "금": 5, "토": 6, "일": 7, "미정": 8}


def create_driver():
    """Docker 환경에 최적화된 Chrome 드라이버 생성"""
    display = Display(visible=0, size=(1920, 1080))
    display.start()

    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=ko-KR")
    options.page_load_strategy = "eager"

    driver = uc.Chrome(options=options, version_main=145)
    driver.set_page_load_timeout(15)
    return driver, display


def wait_for_timetable(driver, timeout=8):
    """불필요한 sleep 대신 실제 시간표 DOM이 뜰 때까지만 대기"""
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
    )
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script(
            """
            return Boolean(
                document.querySelector('table.tablehead tr') &&
                (
                    document.querySelector('table.tablebody > tbody > tr') ||
                    document.querySelector('.nontimes .subject')
                )
            );
            """
        )
    )


def sort_by_time(items):
    items.sort(
        key=lambda x: (
            DAY_ORDER.get(x["day"], 9),
            x["startTime"] if x["startTime"] != "미정" else "99:99",
        )
    )
    return items


FULL_TIMETABLE_SCRIPT = """
function extractTimetable() {
    const result = { subjects: [] };
    const headerRow = document.querySelector('table.tablehead tr');
    if (!headerRow) return result;

    const daysMap = [];
    const headerTds = headerRow.querySelectorAll('td');
    for (const td of headerTds) {
        const style = td.getAttribute('style') || '';
        if (style.includes('display: none') || style.includes('display:none')) continue;
        const dayText = td.textContent.trim();
        if (['월', '화', '수', '목', '금', '토', '일'].includes(dayText)) {
            daysMap.push(dayText);
        }
    }

    const bodyRow = document.querySelector('table.tablebody > tbody > tr');
    if (bodyRow) {
        const bodyTds = bodyRow.querySelectorAll('td');
        for (let tdIndex = 0; tdIndex < bodyTds.length; tdIndex++) {
            const td = bodyTds[tdIndex];
            const dayName = tdIndex < daysMap.length ? daysMap[tdIndex] : null;
            if (!dayName) continue;

            const subjects = td.querySelectorAll('div.subject');
            for (const subj of subjects) {
                const style = subj.getAttribute('style') || '';
                const topMatch = style.match(/top:\\s*(\\d+)px/);
                const heightMatch = style.match(/height:\\s*(\\d+)px/);
                const top = topMatch ? parseInt(topMatch[1], 10) : 0;
                const height = heightMatch ? parseInt(heightMatch[1], 10) : 0;
                const adjustedHeight = Math.max(height - 1, 0);
                const startTotalMinutes = Math.round(top);
                const endTotalMinutes = Math.round(top + adjustedHeight);

                const startHour = Math.floor(startTotalMinutes / 60);
                const startMin = startTotalMinutes % 60;
                const endHour = Math.floor(endTotalMinutes / 60);
                const endMin = endTotalMinutes % 60;

                const durationMin = adjustedHeight;
                const durationHour = Math.floor(durationMin / 60);
                const durationMinRem = durationMin % 60;
                let durationStr = '';
                if (durationHour > 0) {
                    durationStr = durationHour + '시간';
                    if (durationMinRem > 0) durationStr += ' ' + durationMinRem + '분';
                } else {
                    durationStr = durationMinRem + '분';
                }

                const name = subj.querySelector('h3')?.textContent.trim() || '';
                const professor = subj.querySelector('p em')?.textContent.trim() || '';
                const location = subj.querySelector('p span')?.textContent.trim() || '';

                result.subjects.push({
                    name,
                    professor,
                    location,
                    day: dayName,
                    startTime: String(startHour).padStart(2, '0') + ':' + String(startMin).padStart(2, '0'),
                    endTime: String(endHour).padStart(2, '0') + ':' + String(endMin).padStart(2, '0'),
                    duration: durationStr
                });
            }
        }
    }

    const nontimesDiv = document.querySelector('.nontimes');
    if (nontimesDiv) {
        const nontimeSubjects = nontimesDiv.querySelectorAll('.subject');
        for (const subj of nontimeSubjects) {
            const name = subj.querySelector('.name')?.textContent.trim() || '';
            let location = subj.querySelector('.place')?.textContent.trim() || '';
            if (location === '비지정()') location = '미정';

            result.subjects.push({
                name,
                professor: '',
                location,
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


TIME_ONLY_SCRIPT = """
function extractTimeSlots() {
    const result = { subjects: [] };
    const headerRow = document.querySelector('table.tablehead tr');
    if (!headerRow) return result;

    const daysMap = [];
    for (const td of headerRow.querySelectorAll('td')) {
        const style = td.getAttribute('style') || '';
        if (style.includes('display: none') || style.includes('display:none')) continue;
        const dayText = td.textContent.trim();
        if (['월', '화', '수', '목', '금', '토', '일'].includes(dayText)) {
            daysMap.push(dayText);
        }
    }

    const bodyRow = document.querySelector('table.tablebody > tbody > tr');
    if (bodyRow) {
        const bodyTds = bodyRow.querySelectorAll('td');
        for (let tdIndex = 0; tdIndex < bodyTds.length; tdIndex++) {
            const dayName = tdIndex < daysMap.length ? daysMap[tdIndex] : null;
            if (!dayName) continue;

            const subjects = bodyTds[tdIndex].querySelectorAll('div.subject');
            for (const subj of subjects) {
                const style = subj.getAttribute('style') || '';
                const topMatch = style.match(/top:\\s*(\\d+)px/);
                const heightMatch = style.match(/height:\\s*(\\d+)px/);
                const top = topMatch ? parseInt(topMatch[1], 10) : 0;
                const height = heightMatch ? parseInt(heightMatch[1], 10) : 0;
                const adjustedHeight = Math.max(height - 1, 0);
                const startTotalMinutes = Math.round(top);
                const endTotalMinutes = Math.round(top + adjustedHeight);

                const startHour = Math.floor(startTotalMinutes / 60);
                const startMin = startTotalMinutes % 60;
                const endHour = Math.floor(endTotalMinutes / 60);
                const endMin = endTotalMinutes % 60;

                result.subjects.push({
                    day: dayName,
                    startTime: String(startHour).padStart(2, '0') + ':' + String(startMin).padStart(2, '0'),
                    endTime: String(endHour).padStart(2, '0') + ':' + String(endMin).padStart(2, '0')
                });
            }
        }
    }

    const nontimesDiv = document.querySelector('.nontimes');
    if (nontimesDiv) {
        const nontimeSubjects = nontimesDiv.querySelectorAll('.subject');
        for (const subj of nontimeSubjects) {
            result.subjects.push({
                day: '미정',
                startTime: '미정',
                endTime: '미정'
            });
        }
    }

    return result;
}

return extractTimeSlots();
"""


def _execute_scrape(url, script):
    driver = None
    display = None
    try:
        driver, display = create_driver()
        print(f"페이지 접속: {url}")
        driver.get(url)
        wait_for_timetable(driver)

        result = driver.execute_script(script)
        subjects = result.get("subjects") if result else None
        if subjects:
            sort_by_time(subjects)
            return {
                "success": True,
                "data": subjects,
                "timestamp": datetime.now().isoformat(),
                "total": len(subjects),
            }

        try:
            driver.save_screenshot("/app/debug_screenshot.png")
            with open("/app/debug_page.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
        except Exception as debug_error:
            print(f"디버깅 파일 저장 실패: {debug_error}")

        return {
            "success": False,
            "error": "시간표 데이터를 찾을 수 없습니다",
            "timestamp": datetime.now().isoformat(),
        }
    except TimeoutException:
        return {
            "success": False,
            "error": "시간표 로딩이 제한 시간 내에 완료되지 않았습니다",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        if display:
            try:
                display.stop()
            except Exception:
                pass


def scrape_timetable(url):
    """상세 시간표 스크래핑"""
    return _execute_scrape(url, FULL_TIMETABLE_SCRIPT)


def scrape_timetable_time_only(url):
    """요일/시작/종료 시간만 빠르게 반환"""
    return _execute_scrape(url, TIME_ONLY_SCRIPT)