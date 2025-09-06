from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import asyncio
from app.crawler import scrape_timetable
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

@app.get("/")
def read_root():
    return {"message": "Everytime Crawler API", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/crawl", response_model=CrawlResponse)
async def crawl_timetable(request: CrawlRequest):
    """시간표 크롤링 엔드포인트"""
    
    # URL 해시로 캐시 키 생성
    cache_key = hashlib.md5(request.url.encode()).hexdigest()
    
    # 캐시 확인
    if request.cache and r:
        cached_data = r.get(cache_key)
        if cached_data:
            data = json.loads(cached_data)
            data['cached'] = True
            return data
    
    # 크롤링 실행
    result = await asyncio.to_thread(scrape_timetable, request.url)
    
    # 캐시 저장 (1시간)
    if result['success'] and r:
        r.setex(cache_key, 3600, json.dumps(result))
    
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