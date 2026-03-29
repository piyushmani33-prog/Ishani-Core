FROM python:3.11-slim

WORKDIR /app
COPY backend_python/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directory
RUN mkdir -p backend_python/data backend_python/data/nirmaan

EXPOSE 8000

ENV PYTHONPATH=/app
ENV PORT=8000

CMD ["python", "-m", "uvicorn", "backend_python.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
