FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy Nova requirements
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir uvicorn fastapi pydantic

# Copy Nova source code
COPY ./mcp /app/mcp
COPY ./meta /app/meta

# Create data directories
RUN mkdir -p /app/data /app/logs

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Start Nova MCP Server
EXPOSE 3000
CMD ["python", "-m", "uvicorn", "mcp.server:app", "--host", "0.0.0.0", "--port", "3000"]
