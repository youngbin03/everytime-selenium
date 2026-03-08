from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import asyncio
from crawler import scrape_timetable, scrape_timetable_time_only
import redis
import json
import hashlib

app = FastAPI(title="Everytime Crawler API", version="1.0.0")

# Redis 캐시 (선택사항)
try:
    r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
except:
    r = None

class CrawlRequest(BaseModel):
    url: str
    cache: bool = True

class CrawlResponse(BaseModel):
    success: bool
    data: Optional[list] = None
    error: Optional[str] = None
    cached: bool = False
    timestamp: str


def build_cache_key(url: str, mode: str) -> str:
    return hashlib.md5(f"{mode}:{url}".encode()).hexdigest()


def get_cached_response(cache_key: str):
    if not r:
        return None
    cached_data = r.get(cache_key)
    if not cached_data:
        return None
    data = json.loads(cached_data)
    data["cached"] = True
    return data


def set_cached_response(cache_key: str, payload: dict, ttl_seconds: int = 3600):
    if r and payload.get("success"):
        r.setex(cache_key, ttl_seconds, json.dumps(payload))

@app.get("/")
def read_root():
    return {"message": "Everytime Crawler API", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/crawl", response_model=CrawlResponse)
async def crawl_timetable(request: CrawlRequest):
    """과목명/강의실까지 포함한 전체 시간표를 반환합니다."""
    cache_key = build_cache_key(request.url, "full")

    if request.cache:
        cached_data = get_cached_response(cache_key)
        if cached_data:
            return cached_data

    result = await asyncio.to_thread(scrape_timetable, request.url)

    set_cached_response(cache_key, result)
    return result


@app.post("/crawl/time-only", response_model=CrawlResponse)
async def crawl_timetable_time_only(request: CrawlRequest):
    """요일, 시작 시간, 종료 시간만 빠르게 반환합니다."""
    cache_key = build_cache_key(request.url, "time-only")

    if request.cache:
        cached_data = get_cached_response(cache_key)
        if cached_data:
            return cached_data

    result = await asyncio.to_thread(scrape_timetable_time_only, request.url)
    set_cached_response(cache_key, result)
    return result

@app.post("/crawl/async")
async def crawl_async(request: CrawlRequest, background_tasks: BackgroundTasks):
    """비동기 크롤링 (백그라운드 작업)"""
    task_id = hashlib.md5(f"{request.url}{datetime.now()}".encode()).hexdigest()
    
    background_tasks.add_task(scrape_and_save, request.url, task_id)
    
    return {
        "message": "크롤링 작업이 시작되었습니다",
        "task_id": task_id
    }

async def scrape_and_save(url: str, task_id: str):
    """백그라운드 크롤링 작업"""
    result = scrape_timetable(url)
    if r:
        r.setex(f"task:{task_id}", 300, json.dumps(result))