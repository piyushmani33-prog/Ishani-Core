# TechBuzz Empire — Deployment Runbook

## Prerequisites

Before deploying, generate and configure required secrets:

```bash
# 1. Generate a session secret
python -c "import os; print(os.urandom(32).hex())"

# 2. Generate master password salt + hash
python -c "
import hashlib, os
salt = os.urandom(16).hex()
password = input('Enter your master password: ')
hash_ = hashlib.sha256((salt + password).encode()).hexdigest()
print(f'MASTER_PASSWORD_SALT={salt}')
print(f'MASTER_PASSWORD_HASH={hash_}')
"
```

Copy `deploy/.env.production.example` to `deploy/.env.production` and fill in all values.

---

## Option 1: Local Development

```bash
cd techbuzz-full/techbuzz-full/backend_python
cp .env.example .env        # Edit .env with your values
pip install -r requirements.txt
python app.py
```

Server starts at **http://localhost:8000**

### Local Demo Mode (safe for sharing)

```bash
DEMO_MODE=true python app.py
```

---

## Option 2: Docker (Recommended for Production)

```bash
# Navigate to the deploy directory
cd techbuzz-full/techbuzz-full

# Copy and fill in the production env template
cp deploy/.env.production.example deploy/.env.production
# Edit deploy/.env.production — fill in all required values

# Build the image
docker build -f deploy/Dockerfile -t techbuzz-empire .

# Run with env file
docker run -d -p 8000:8000 \
  --env-file deploy/.env.production \
  -v $(pwd)/backend_python/data:/app/backend_python/data \
  --name techbuzz-empire \
  techbuzz-empire

# Or with docker-compose (reads deploy/.env.production automatically)
docker-compose -f deploy/docker-compose.yml up -d
```

Verify health: `curl http://localhost:8000/health`

---

## Option 3: Railway.app

1. Go to https://railway.app → New Project → Deploy from GitHub
2. Set **Root Directory** to `techbuzz-full/techbuzz-full`
3. Add environment variables from `.env.production.example` in the Railway dashboard
4. Railway auto-detects Python and deploys
5. Your URL: `https://your-app.railway.app`

For persistent storage: add a Volume mount at `/app/backend_python/data`

---

## Option 4: Render.com

1. Go to https://render.com → New Web Service → Connect GitHub repo
2. **Root Directory:** `techbuzz-full/techbuzz-full`
3. **Build Command:** `pip install -r backend_python/requirements.txt`
4. **Start Command:** `cd backend_python && uvicorn app:app --host 0.0.0.0 --port $PORT`
5. Add environment variables from `.env.production.example`
6. Your URL: `https://your-app.onrender.com`

---

## Option 5: Fly.io

```bash
cd techbuzz-full/techbuzz-full

fly launch --name techbuzz-empire
fly secrets set ANTHROPIC_API_KEY=sk-ant-...
fly secrets set SESSION_SECRET=$(python -c "import os; print(os.urandom(32).hex())")
fly secrets set MASTER_ACCOUNT_EMAIL=owner@yourdomain.com
fly secrets set MASTER_PASSWORD_SALT=<generated-salt>
fly secrets set MASTER_PASSWORD_HASH=<generated-hash>
fly secrets set ALLOWED_ORIGINS=https://your-app.fly.dev
fly deploy
```

---

## Environment Variable Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Optional | Claude AI provider |
| `OPENAI_API_KEY` | Optional | OpenAI provider |
| `GEMINI_API_KEY` | Optional | Google Gemini provider |
| `MASTER_ACCOUNT_EMAIL` | Recommended | Master login email |
| `MASTER_PASSWORD_SALT` | Recommended | Master password salt (hex) |
| `MASTER_PASSWORD_HASH` | Recommended | Master password hash (hex) |
| `SESSION_SECRET` | Recommended | Session cookie signing key |
| `ALLOWED_ORIGINS` | Recommended | Comma-separated CORS origins |
| `DEMO_MODE` | Optional | `true` to disable writes (default: `false`) |
| `ADMIN_ROUTES_ENABLED` | Optional | `false` to hide admin routes (default: `true`) |
| `PORT` | Optional | Server port (default: `8000`) |
| `LOG_LEVEL` | Optional | `DEBUG/INFO/WARNING/ERROR` (default: `INFO`) |
| `RATE_LIMIT_PER_MINUTE` | Optional | Max requests per IP per minute (default: `60`) |
| `DATABASE_URL` | Optional | DB connection string (default: SQLite) |

---

## Health Check Verification

After deployment, verify the service is running:

```bash
# Liveness (always returns 200 if server is up)
curl https://your-domain.com/health

# Readiness (checks DB, AI providers)
curl https://your-domain.com/ready
```

Expected response:
```json
{"status": "ok", "service": "ishani-core", "timestamp": "..."}
```

---

## Important Notes

- **SQLite** is the default database — suitable for single-user deployments.
  For multiple concurrent users, use **PostgreSQL** (`DATABASE_URL=postgresql://...`).
- Add a persistent volume at `/app/backend_python/data` for SQLite data survival across restarts.
- All neural mesh SSE connections work on Railway, Render, and Fly.io.
- Brain learning from the web works without any additional API keys (uses DuckDuckGo/RSS).
