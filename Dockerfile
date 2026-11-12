FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install the package first, so code changes don't reinstall dependencies.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install .

COPY alembic.ini ./
COPY migrations ./migrations
COPY data/sample ./data/sample
COPY docker/entrypoint.sh ./docker/entrypoint.sh

RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8000
CMD ["./docker/entrypoint.sh"]
