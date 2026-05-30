# KK backend image (uv-based).
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install deps first (better layer caching), then app code.
COPY pyproject.toml ./
RUN uv sync --no-dev

COPY app ./app

EXPOSE 8000
# Bind to 0.0.0.0 so the container is reachable behind the load balancer.
CMD ["uv", "run", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
