FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (curl for health checks)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer caching)
COPY backend_python/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend_python/ ./backend_python/
COPY frontend/ ./frontend/

# Create required data directories
RUN mkdir -p backend_python/data backend_python/data/nirmaan

EXPOSE 8000

ENV PYTHONPATH=/app
ENV PORT=8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "backend_python.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
