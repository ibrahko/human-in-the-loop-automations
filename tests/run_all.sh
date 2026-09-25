#!/usr/bin/env bash
# Starts a throw-away n8n and the mock services, then runs the end-to-end tests.
# Requirements: Node.js 24 and n8n installed (npm install n8n@2.40.7), Python 3.10+.
set -euo pipefail
cd "$(dirname "$0")/.."
DATA=$(mktemp -d)
export N8N_USER_FOLDER="$DATA" N8N_LISTEN_ADDRESS=127.0.0.1 N8N_PORT=5678 \
       N8N_DIAGNOSTICS_ENABLED=false N8N_SECURE_COOKIE=false N8N_RUNNERS_ENABLED=false
N8N_BIN=${N8N_BIN:-n8n}

python3 tests/mock_server.py 8765 & MOCK_PID=$!
$N8N_BIN start > "$DATA/n8n.log" 2>&1 & N8N_PID=$!
trap 'kill $MOCK_PID $N8N_PID 2>/dev/null || true; rm -rf "$DATA"' EXIT

for _ in $(seq 1 90); do
  curl -sf http://127.0.0.1:5678/healthz > /dev/null && break
  sleep 2
done
# healthz answers before the REST API is ready: wait for the settings endpoint too.
for _ in $(seq 1 90); do
  curl -sf http://127.0.0.1:5678/rest/settings > /dev/null && break
  sleep 2
done
curl -sf http://127.0.0.1:5678/rest/settings > /dev/null || { tail -50 "$DATA/n8n.log"; exit 1; }

# Test-only owner account on the throw-away instance (retried until n8n has finished starting).
for _ in $(seq 1 60); do
  curl -s -X POST http://127.0.0.1:5678/rest/owner/setup -H 'content-type: application/json' \
    -d '{"email":"test@example.com","firstName":"Test","lastName":"Runner","password":"Test12345678"}' \
    | grep -q '"data"' && break
  sleep 2
done

python3 build/build.py > /dev/null
if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  git diff --exit-code --quiet -- '*/workflows/*.json' \
    || { echo "Workflows are out of date: run python build/build.py and commit."; exit 1; }
fi
node tests/guardrail_words.test.js
python3 tests/test_workflows.py
