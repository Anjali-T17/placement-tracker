# Production-ready Dockerfile for College Placement Tracker Flask Backend
# Compatible with Apple Silicon (ARM64) and x86_64 architectures

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=5001 \
    DATABASE_PATH=/app/data/placement.db \
    DB_TYPE=sqlite \
    CORS_ORIGINS="*"

# Install system dependencies (curl for container healthcheck)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for optimal Docker layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app/

# Ensure entrypoint script is executable and data directory exists
RUN chmod +x /app/entrypoint.sh && mkdir -p /app/data

# Expose backend port
EXPOSE 5001

# Healthcheck to ensure Flask API is running and responding
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5001/api/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "app.py"]
