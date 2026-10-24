FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

FROM base AS deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM deps AS runtime
COPY app/ ./app/
COPY data/README.md ./data/README.md

RUN mkdir -p data/output data/uploads data/sample

ENV CN_API_HOST=0.0.0.0
ENV CN_API_PORT=8000
ENV CN_LOG_LEVEL=INFO
ENV PYTHONPATH=/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
