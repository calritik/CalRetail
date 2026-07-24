#!/usr/bin/env bash
# CalRetail — container entrypoint.
#
# The backend starts first but Dash is what the container waits on: api_get()
# in services/api.py catches every request exception and returns None, so a
# page hitting the API before uvicorn finishes its cache warm-up just shows an
# offline banner for a few seconds rather than crashing — no readiness gate
# needed between the two.
set -e

uvicorn backend.main:app --host 127.0.0.1 --port 8000 &

# exec replaces this shell with the Dash process (so it becomes the
# container's PID 1 and receives SIGTERM directly from HF); the backgrounded
# uvicorn above keeps running as its child, unaffected by the exec.
exec python frontend_dash/app.py
