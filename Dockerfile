# ============================================================
# RealJarvis 24/7 Always-On Cloud Daemon Dockerfile
# Lightweight, high-performance container for 24/7 execution
# ============================================================
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8765

WORKDIR /app

# Install lightweight core dependencies needed for cloud daemon
RUN pip install --no-cache-dir \
    google-genai \
    psutil \
    requests

# Copy project files
COPY . /app

# Ensure data directory exists for SQLite persistent memory
RUN mkdir -p /app/data

EXPOSE 8765

# Run the 24/7 Daemon Gateway
CMD ["python", "daemon_api_server.py"]
