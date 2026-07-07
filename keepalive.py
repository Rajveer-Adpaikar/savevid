"""SaveVid keep-alive: pings the app every 12 min so Render doesn't spin down.

Runs as a background process alongside Gunicorn in start.sh.
Uses only stdlib — zero pip dependencies.
"""
import os
import time
import urllib.request
import urllib.error
import sys

INTERVAL = 12 * 60  # 12 minutes
URL = os.environ.get("RENDER_EXTERNAL_URL") or "https://savevid-1eve.onrender.com"
HEALTH_URL = f"{URL.rstrip('/')}/api/health"


def ping():
    try:
        req = urllib.request.Request(HEALTH_URL, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status
    except Exception as e:
        return f"error: {e}"


def main():
    # Wait a moment for Gunicorn to start before first ping
    time.sleep(10)

    sys.stdout.write(f"[keepalive] pinging {HEALTH_URL} every {INTERVAL}s\n")
    sys.stdout.flush()

    while True:
        result = ping()
        ts = time.strftime("%H:%M:%S")
        sys.stdout.write(f"[keepalive] {ts} → {result}\n")
        sys.stdout.flush()
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
