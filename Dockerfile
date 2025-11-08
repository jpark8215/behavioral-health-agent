FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies for audio processing and docling
RUN apt-get update -o Acquire::Retries=3 && apt-get install -y --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    curl \
    ffmpeg \
    libsndfile1 \
    portaudio19-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p static/uploads temp/audio

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
