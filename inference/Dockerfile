FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ARG UV_SYNC_ARGS="--no-dev"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app/inference

COPY inference/pyproject.toml inference/uv.lock inference/README.md ./
COPY inference/src ./src

RUN uv sync --locked ${UV_SYNC_ARGS}

ENV PATH="/app/inference/.venv/bin:${PATH}"

CMD ["inference-worker", "--daemon"]
