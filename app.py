#!/usr/bin/env python3
"""
SaveVid — Flask Web App
Main entry point for the local downloader interface.
Supports YouTube and Instagram video downloads via yt-dlp.
"""

import json
import os
import sys
import time
import shutil
import threading
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file, session
from flask_cors import CORS

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tools"))
from list_formats import list_formats
from download_video import download_video, get_downloads_folder

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()
CORS(app)

DOWNLOAD_DIR = os.path.join(get_downloads_folder(), "SaveVid")

# ─── Format cache ────────────────────────────────────────────────
# yt-dlp can return different results on repeated calls to the same
# URL (YouTube varies what it serves per request).  Cache results
# per URL for a short TTL so the UI stays consistent.
_format_cache = {}       # url -> (expiry_epoch, result_dict)
_FORMAT_CACHE_TTL = 600  # seconds (10 minutes)

def _get_cached_formats(url):
    """Return cached result for *url* if still fresh, else None."""
    entry = _format_cache.get(url)
    if entry and time.time() < entry[0]:
        return entry[1]
    return None

def _set_cached_formats(url, result):
    """Store *result* for *url* with the configured TTL."""
    _format_cache[url] = (time.time() + _FORMAT_CACHE_TTL, result)


@app.route("/")
def index():
    """Render the main page."""
    return render_template("index.html")


@app.route("/api/formats", methods=["POST"])
def get_formats():
    """Fetch available formats for a given URL."""
    data = request.get_json()
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "Please enter a video URL."}), 400

    if not url.startswith(("http://", "https://")):
        return jsonify({"error": "Please enter a valid URL starting with http:// or https://"}), 400

    # Check if it's a supported platform
    if not any(domain in url.lower() for domain in ["youtube.com", "youtu.be", "instagram.com", "instagr.am", "facebook.com", "fb.watch", "fb.com"]):
        return jsonify({"error": "Only YouTube, Instagram, and Facebook URLs are supported."}), 400

    # Return cached result if fresh
    cached = _get_cached_formats(url)
    if cached:
        return jsonify(cached)

    result = list_formats(url)

    if "error" in result:
        return jsonify({"error": result["error"]}), 400

    # Cache successful result so repeated requests for the same URL
    # show consistent format listings.
    _set_cached_formats(url, result)

    return jsonify(result)


@app.route("/api/download", methods=["POST"])
def download():
    """Download a specific format and stream it to the user."""
    data = request.get_json()
    url = data.get("url", "").strip()
    format_id = data.get("format_id", "").strip()

    if not url or not format_id:
        return jsonify({"error": "Missing URL or format selection."}), 400

    # Run download in a thread so we can track progress
    result = download_video(url, format_id, DOWNLOAD_DIR)

    if "error" in result:
        return jsonify({"error": result["error"]}), 400

    return jsonify(result)


if __name__ == "__main__":
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    print(f"\n== SaveVid ==")
    print(f"{'=' * 40}")
    print(f"Downloads folder: {DOWNLOAD_DIR}")
    print(f"Open: http://127.0.0.1:5000")
    print(f"{'=' * 40}\n")
    app.run(host="127.0.0.1", port=5000, debug=True, threaded=True)
