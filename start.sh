#!/usr/bin/env bash
# SaveVid — Render.com startup script
# Updates yt-dlp to latest master (with curl_cffi for browser impersonation)
# then starts the Gunicorn server.

set -e

echo "== SaveVid =="
echo "Updating yt-dlp to latest version..."
pip install --upgrade yt-dlp 2>&1 | tail -2

echo "Starting Gunicorn..."
exec gunicorn app:app
