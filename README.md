# Everytime Crawler API

에브리타임 시간표 공유 링크를 받아 시간표를 JSON으로 반환하는 FastAPI 서비스입니다.

## 특징

- Selenium 기반 시간표 크롤링
- Redis 캐시 지원
- 전체 시간표 응답과 경량 `time-only` 응답 분리
- `sleep` 기반 대기 제거, 실제 DOM 로딩 시점까지만 대기

## 실행 방법

### Docker로 실행

```bash
docker-compose up -d --build
```

기본 노출 주소:

- `http://localhost`
- EC2 배포 시 `http://<EC2_IP>`

## 엔드포인트

### `GET /`

서버 상태 확인

응답 예시:

```json
{
  "message": "Everytime Crawler API",
  "status": "running"
}
```

### `GET /health`

헬스체크

응답 예시:

```json
{
  "status": "healthy"
}
```

### `POST /crawl`

과목명, 교수명, 강의실, 요일, 시작 시간, 종료 시간, 수업 시간을 포함한 전체 시간표를 반환합니다.

요청 본문:

```json
{
  "url": "https://everytime.kr/@0HpGBZKue79CEavond7E",
  "cache": true
}
```

응답 예시:

```json
{
  "success": true,
  "data": [
    {
      "name": "컴퓨터구조론",
      "professor": "이헌준",
      "location": "IT.BT관508강의실",
      "day": "화",
      "startTime": "13:00",
      "endTime": "14:30",
      "duration": "1시간 30분"
    }
  ],
  "error": null,
  "cached": false,
  "timestamp": "2026-03-05T12:37:34.459220",
  "total": 1
}
```

호출 예시:

```bash
curl -X POST "http://localhost/crawl" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://everytime.kr/@0HpGBZKue79CEavond7E", "cache": true}'
```

### `POST /crawl/time-only`

가장 빠르게 사용할 수 있는 경량 엔드포인트입니다.  
과목명과 강의실 없이 `요일`, `시작 시간`, `종료 시간`만 반환합니다.

요청 본문:

```json
{
  "url": "https://everytime.kr/@0HpGBZKue79CEavond7E",
  "cache": true
}
```

응답 예시:

```json
{
  "success": true,
  "data": [
    {
      "day": "화",
      "startTime": "13:00",
      "endTime": "14:30"
    },
    {
      "day": "화",
      "startTime": "19:00",
      "endTime": "22:00"
    }
  ],
  "error": null,
  "cached": false,
  "timestamp": "2026-03-05T12:37:34.459220",
  "total": 2
}
```

호출 예시:

```bash
curl -X POST "http://localhost/crawl/time-only" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://everytime.kr/@0HpGBZKue79CEavond7E", "cache": true}'
```

## 캐시

- `cache: true` 이면 Redis 캐시를 사용합니다.
- 동일한 URL이라도 전체 응답과 `time-only` 응답은 서로 다른 캐시 키를 사용합니다.
- 기본 TTL은 1시간입니다.

## 성능 최적화 포인트

- 기존 고정 `sleep` 제거
- `document.readyState` 와 시간표 DOM 존재 여부를 기준으로 대기
- `time-only` 엔드포인트로 불필요한 문자열 파싱 최소화
- Redis 캐시로 동일 요청 재사용

## Swagger 문서

서버 실행 후 아래 주소에서 확인할 수 있습니다.

- `http://localhost/docs`
- EC2 배포 시 `http://<EC2_IP>/docs`
