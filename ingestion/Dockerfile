# Multi-stage build:
#  1) builder: install docling + deps, pre-download layout / TableFormer /
#     EasyOCR models so the runtime image can operate fully offline.
#  2) runtime: copy site-packages + model caches; set HF offline env vars.
#
# The final image is intentionally chunky (~3.5-5 GB) because layout +
# OCR models live inside it. This is the tradeoff for a hermetic ingest
# stage — no per-run model downloads, no phone-home telemetry.

# --------- builder ----------
FROM python:3.11-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf_cache \
    HF_HUB_DISABLE_TELEMETRY=1

WORKDIR /build

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      libgl1 \
      libglib2.0-0 \
      libmagic1 \
      poppler-utils \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --prefer-binary -r requirements.txt

# Pre-download layout + TableFormer + code-formula models (~1.5 GB).
RUN mkdir -p /opt/hf_cache /root/.cache/docling \
 && docling-tools models download

# Pre-download EasyOCR English models so OCR fallback stays offline.
# This is separate from Docling's model cache.
RUN mkdir -p /opt/easyocr \
 && python -c "import easyocr; easyocr.Reader(['en'], model_storage_directory='/opt/easyocr', download_enabled=True)"

# --------- runtime ----------
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    HF_HOME=/opt/hf_cache \
    HF_HUB_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    TRANSFORMERS_OFFLINE=1 \
    EASYOCR_MODULE_PATH=/opt/easyocr

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      libgl1 \
      libglib2.0-0 \
      libmagic1 \
      poppler-utils \
 && rm -rf /var/lib/apt/lists/*

# Copy installed python packages + pre-warmed model caches.
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /root/.cache/docling /root/.cache/docling
COPY --from=builder /opt/hf_cache /opt/hf_cache
COPY --from=builder /opt/easyocr /opt/easyocr

COPY . .

# Persistent storage for downloaded files — mount a volume here in Compose.
RUN mkdir -p data/xbrl_files data/pdfs data/parsed

# Run the full pipeline by default; override CMD to skip stages, e.g.:
#   docker run ingestion python main.py --skip-crawl --skip-metadata --skip-download
CMD ["python", "main.py"]
