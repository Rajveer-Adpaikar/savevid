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
import uuid
import shutil
import atexit
import tempfile
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

# ─── Download token cache ────────────────────────────────────────
# Stores downloaded file paths keyed by a unique token so the user's
# browser can pull the file as a download.  Tokens expire after 5 min.
_download_cache = {}       # token -> (file_path, expiry_epoch)
_DOWNLOAD_CACHE_TTL = 300  # seconds


def _cleanup_temp_dirs():
    """Remove any leftover temp download dirs on shutdown."""
    for token, (fpath, _) in list(_download_cache.items()):
        d = os.path.dirname(fpath)
        if d and os.path.isdir(d):
            try:
                shutil.rmtree(d, ignore_errors=True)
            except Exception:
                pass


atexit.register(_cleanup_temp_dirs)


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
    """
    Download a specific format and return a JSON with a one-time
    download URL so the browser can retrieve the actual file.
    """
    data = request.get_json()
    url = data.get("url", "").strip()
    format_id = data.get("format_id", "").strip()
    format_type = data.get("format_type", "").strip()

    if not url or not format_id:
        return jsonify({"error": "Missing URL or format selection."}), 400

    # Download to a temporary directory unique per request
    tmp_dir = tempfile.mkdtemp(prefix="savevid_")
    result = download_video(url, format_id, tmp_dir, format_type=format_type)

    if "error" in result:
        # Clean up the temp dir on failure
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return jsonify({"error": result["error"]}), 400

    file_path = result.get("file_path")
    if file_path and os.path.exists(file_path):
        # Create a one-time download token
        token = str(uuid.uuid4())
        _download_cache[token] = (file_path, time.time() + _DOWNLOAD_CACHE_TTL)
        result["download_url"] = f"/api/dl/{token}"
        result["file_path"] = file_path  # keep for local mode display
    else:
        # No file found — clean up
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return jsonify(result)


@app.route("/api/dl/<token>")
def serve_download(token):
    """
    Serve a previously-downloaded file to the browser and clean up
    the temporary directory afterward.
    """
    entry = _download_cache.pop(token, None)
    if not entry:
        return jsonify({"error": "Download link expired or invalid."}), 404

    file_path, expiry = entry
    if time.time() > expiry or not os.path.exists(file_path):
        _cleanup_one(file_path)
        return jsonify({"error": "Download link expired."}), 410

    filename = os.path.basename(file_path)
    tmp_dir = os.path.dirname(file_path)

    # Stream the file to the browser, then clean up
    response = send_file(
        file_path,
        as_attachment=True,
        download_name=filename,
    )

    # Schedule cleanup after sending
    @response.call_on_close
    def _do_cleanup():
        try:
            if os.path.isdir(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

    return response


def _cleanup_one(file_path):
    """Remove the parent temp dir of *file_path* if it still exists."""
    d = os.path.dirname(file_path)
    if d and os.path.isdir(d):
        try:
            shutil.rmtree(d, ignore_errors=True)
        except Exception:
            pass


@app.route("/api/health")
def health():
    """Health check endpoint (useful for monitoring)."""
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    print(f"\n== SaveVid ==")
    print(f"{'=' * 40}")
    print(f"Downloads folder: {DOWNLOAD_DIR}")
    print(f"Open: http://127.0.0.1:5000")
    print(f"{'=' * 40}\n")
    app.run(host="127.0.0.1", port=5000, debug=True, threaded=True)
