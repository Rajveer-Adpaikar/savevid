#!/usr/bin/env bash
# SaveVid — Render.com startup script
# Downloads the yt-dlp Linux static binary (includes curl_cffi for browser
# impersonation), decodes cookies from env var, then starts Gunicorn.
#
# To add cookies:
#   1. Export cookies.txt from your browser (YouTube + Instagram logged in)
#   2. base64 -w0 cookies.txt  (get the encoded string)
#   3. Paste it as Render env var:  COOKIES = <base64 string>
#   4. Redeploy
#
# Cookies expire every ~2-4 weeks; repeat steps 1-4 when needed.

set -e

echo "== SaveVid =="

# ── 1. Download yt-dlp_linux static binary (has curl_cffi baked in) ──
YTDLP="./yt-dlp_linux"
if [ ! -f "$YTDLP" ]; then
    echo "Downloading yt-dlp_linux (static binary with curl_cffi)..."
    wget -q --show-progress \
        "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux"
    chmod +x yt-dlp_linux
fi

# ── 2. Decode cookies from env var ──
if [ -n "$COOKIES" ]; then
    echo "Decoding cookies from \$COOKIES environment variable..."
    echo "$COOKIES" | base64 -d > /tmp/cookies.txt 2>/dev/null
    if [ -s /tmp/cookies.txt ]; then
        echo "Cookies written to /tmp/cookies.txt ($(wc -l < /tmp/cookies.txt) lines)"
    else
        echo "Warning: \$COOKIES set but decoding produced empty file. Skipping cookies."
        rm -f /tmp/cookies.txt
    fi
else
    echo "No \$COOKIES env var set — running without cookies (YouTube/Instagram may fail)."
    echo "See start.sh comments for how to add cookies."
fi

echo ""
echo "Starting Gunicorn..."
exec gunicorn app:app
