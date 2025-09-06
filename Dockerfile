FROM python:3.11-slim

# 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# --- [수정된 부분 시작] ---
# Chrome 설치 (apt-key 대신 GPG 키를 직접 저장하는 새로운 방식)
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google-chrome.gpg
RUN echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list
RUN apt-get update && apt-get install -y google-chrome-stable --no-install-recommends && rm -rf /var/lib/apt/lists/*
# --- [수정된 부분 끝] ---

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 설치
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 복사
COPY app/ .

# 포트 설정
EXPOSE 8000

# 실행 명령
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]