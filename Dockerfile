FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BRAIN_MEMORY_ROOT=/app \
    CNEXUS_ENV=production

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import httpx; r=httpx.get('http://127.0.0.1:8000/api/health', timeout=3); r.raise_for_status()"

CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
