# TechBuzz Empire — Internet Deployment Guide

## Option 1: Railway.app (Recommended — Free Tier)
1. Go to https://railway.app
2. New Project → Deploy from GitHub
3. Upload your techbuzz-full folder to GitHub
4. Set environment variables in Railway dashboard:
   - ANTHROPIC_API_KEY=sk-ant-...
   - MASTER_KEY_SALT=7da6609f793750fa55889aa5953517a1
   - MASTER_KEY_HASH=13939481a08f3607cf527a8bc790d77388fcccc692f6c68b5492ab8bc5fb2003
   - MASTER_EMAIL=piyushmani33@gmail.com
5. Railway auto-detects Python and deploys
6. Get your URL: https://your-app.railway.app

## Option 2: Render.com (Free Tier)
1. Go to https://render.com
2. New Web Service → Connect GitHub repo
3. Build Command: pip install -r backend_python/requirements.txt
4. Start Command: cd backend_python && uvicorn app:app --host 0.0.0.0 --port $PORT
5. Add environment variables from .env
6. Deploy — get URL: https://your-app.onrender.com

## Option 3: Docker (VPS/Cloud)
```bash
# Build
docker build -f deploy/Dockerfile -t techbuzz-empire .

# Run with your keys
docker run -d -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e MASTER_EMAIL=piyushmani33@gmail.com \
  -e MASTER_KEY_SALT=7da6609f793750fa55889aa5953517a1 \
  -e MASTER_KEY_HASH=13939481a08f3607cf527a8bc790d77388fcccc692f6c68b5492ab8bc5fb2003 \
  -v $(pwd)/data:/app/backend_python/data \
  techbuzz-empire
```

## Option 4: Fly.io
```bash
fly launch --name techbuzz-empire
fly secrets set ANTHROPIC_API_KEY=sk-ant-...
fly secrets set MASTER_KEY_SALT=7da6609f793750fa55889aa5953517a1
fly secrets set MASTER_KEY_HASH=13939481a08f3607cf527a8bc790d77388fcccc692f6c68b5492ab8bc5fb2003
fly deploy
```

## After Deployment
1. Open https://your-domain.com/login
2. Click "Master" tab
3. Enter piyushmani33@gmail.com
4. Enter master key: ICBAQ00538
5. You're in — all 52 brains alive on the internet

## Important Notes
- Data (SQLite DB) is in-memory on free tiers — use volumes for persistence
- For persistent storage on Railway: add a Volume mount at /app/backend_python/data
- Neural Mesh SSE works on all platforms
- Brain learning from web works everywhere (DuckDuckGo, RSS — no API keys needed)
