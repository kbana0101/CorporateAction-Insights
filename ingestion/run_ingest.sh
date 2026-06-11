#!/usr/bin/env bash
set -euo pipefail
cd /home/kbana/code/CorporateAction-Insights-latest/ingestion

# write start timestamp
mkdir -p logs
echo "$(date --iso-8601=seconds) RUNNER START" >> logs/ingest.log

# load environment from .env if present
if [ -f .env ]; then
	set -a
	# shellcheck disable=SC1091
	. .env
	set +a
fi

# activate virtualenv if present
if [ -f .venv/bin/activate ]; then
	# shellcheck disable=SC1091
	. .venv/bin/activate
fi

# simple lockfile to avoid overlapping runs
LOCKFILE=".ingest.lock"
if [ -f "$LOCKFILE" ]; then
	PID=$(cat "$LOCKFILE" 2>/dev/null || echo "")
	if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
		echo "$(date --iso-8601=seconds) Runner already active (pid=$PID)" >> logs/ingest.log
		exit 0
	else
		rm -f "$LOCKFILE" || true
	fi
fi
echo $$ > "$LOCKFILE"
trap 'rm -f "$LOCKFILE"' EXIT

# run ingestion
/usr/bin/python3 main.py --verbose >> logs/ingest.log 2>&1 || {
	echo "$(date --iso-8601=seconds) RUNNER FAILED" >> logs/ingest.log
}

echo "$(date --iso-8601=seconds) RUNNER END" >> logs/ingest.log
