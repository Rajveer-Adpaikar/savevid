#!/usr/bin/env bash
# SaveVid — Render.com startup script
# Downloads the yt-dlp static binary (includes curl_cffi for browser
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

echo "================================================="
echo "=  SaveVid — Render Startup Script              ="
echo "================================================="
echo "Current directory: $(pwd)"
echo "Directory listing:"
ls -la
echo ""

# ── 1. Download yt-dlp static binary (has curl_cffi baked in) ──
if [ ! -f "./yt-dlp" ]; then
    echo "Downloading yt-dlp (static Linux binary with curl_cffi)..."
    if command -v curl &> /dev/null; then
        curl -fL -o yt-dlp \
            "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux" \
            || { echo "ERROR: curl download failed."; exit 1; }
    elif command -v wget &> /dev/null; then
        wget -q --show-progress \
            "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux" \
            -O yt-dlp || { echo "ERROR: wget download failed."; exit 1; }
    else
        echo "ERROR: Neither curl nor wget available — cannot download yt-dlp."
        exit 1
    fi
    chmod +x yt-dlp
    # Verify download succeeded
    if [ ! -s yt-dlp ]; then
        echo "ERROR: Downloaded yt-dlp is empty — download failed."
        exit 1
    fi
    echo "yt-dlp downloaded and made executable ($(stat -c%s yt-dlp 2>/dev/null || wc -c < yt-dlp) bytes)."
else
    echo "yt-dlp binary already exists, skipping download."
fi

# Show binary info for debugging
ls -la yt-dlp
file yt-dlp 2>/dev/null || true

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

# ── 3. Start keep-alive background process ──
# Pings the app every 12 minutes so Render's free tier doesn't spin down.
# RENDER_EXTERNAL_URL is auto-set by Render; falls back to hardcoded URL.
echo "Starting keepalive background process..."
python keepalive.py &
echo "Keepalive PID: $!"

echo ""
echo "Starting Gunicorn..."
exec gunicorn app:app
