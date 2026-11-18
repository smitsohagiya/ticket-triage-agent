FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS build
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev

FROM python:3.12-slim-bookworm
WORKDIR /app
RUN useradd --create-home app
COPY --from=build --chown=app:app /app /app
ENV PATH="/app/.venv/bin:$PATH"
USER app
ENTRYPOINT ["triage"]
CMD ["--help"]
