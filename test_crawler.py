from app.crawler import scrape_timetable

def test_crawl():
    url = "https://everytime.kr/@0HpGBZKue79CEavond7E"
    result = scrape_timetable(url)
    print("크롤링 결과:")
    print(result)

if __name__ == "__main__":
    test_crawl()
