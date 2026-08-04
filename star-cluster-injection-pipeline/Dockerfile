FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE MANIFEST.in requirements.txt ./
COPY src ./src
COPY configs ./configs
COPY scripts ./scripts

RUN python -m pip install --upgrade pip && \
    pip install .

ENTRYPOINT ["injection-pipeline"]
CMD ["--help"]
