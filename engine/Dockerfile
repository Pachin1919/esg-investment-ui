# Image for the shardable ingest jobs (Cloud Run Jobs). Build context: repo root.
FROM python:3.12-slim

# poppler-utils provides pdftotext, which hkexnews.pdf_pages uses for page text
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY pipeline ./pipeline
COPY scripts ./scripts
RUN pip install --no-cache-dir .

# data and outputs live on the mounted bucket, not in the container
ENV ESGX_DATA_DIR=/data ESGX_OUTPUT_DIR=/data/outputs PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "scripts/ingest_hk_stream.py"]
CMD ["--steps", "documents", "--index", "hsci"]
