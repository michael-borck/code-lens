# CodeLens Docker Image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
RUN pip install uv

# Create app user with home directory and docker group access
RUN groupadd -r appuser && useradd -r -g appuser -m appuser \
    && groupadd -f docker \
    && usermod -aG docker appuser

# Set working directory
WORKDIR /app

# Copy dependency files and README (needed for package build)
COPY pyproject.toml uv.lock README.md ./

# Copy source code (needed for editable install)
COPY codelens/ ./codelens/

# Install dependencies with uv
RUN uv sync --frozen

# Copy remaining application files
COPY . .

# Create necessary directories and fix permissions
RUN mkdir -p logs uploads temp && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /home/appuser

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (port can be overridden via environment)
CMD ["uv", "run", "uvicorn", "codelens.main:app", "--host", "0.0.0.0", "--port", "8000"]