FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Chromium
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    xvfb \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Set environment variable for Chrome in Docker
ENV USE_LOCAL_CHROME=true
ENV CHROME_BIN=/usr/bin/google-chrome-stable
ENV DISPLAY=:99

# Cloud Run automatically sets PORT env var
# App should listen on $PORT
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT"]