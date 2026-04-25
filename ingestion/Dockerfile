# Python 3.9 on slim Debian — matches the local dev environment
FROM python:3.9-slim

WORKDIR /app

# System deps for requests/urllib3 (no Chrome/Selenium needed; crawler uses API)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Legacy resolver avoids pip backtracking issues on 3.9 / LibreSSL-free env;
# --prefer-binary skips source builds for speed.
RUN pip install --no-cache-dir \
      --prefer-binary \
      --use-deprecated=legacy-resolver \
      -r requirements.txt

COPY . .

# Persistent storage for downloaded files — mount a volume here in Compose
RUN mkdir -p data/xbrl_files data/pdfs

# Run the full pipeline by default; override CMD to skip stages, e.g.:
#   docker run ingestion python main.py --skip-crawl --skip-metadata --skip-download
CMD ["python", "main.py"]
