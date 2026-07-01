#!/usr/bin/env python3
"""
Netlify Function: API handler for SaveVid.
Handles /api/formats and /api/download endpoints.
Reuses the project tools directly (no Flask dependency).
"""

import sys
import os
import json
import base64
import tempfile
import traceback
from urllib.parse import parse_qs

# Import tools (copied into the same directory for Netlify bundling)
from list_formats import list_formats
from download_video import download_video


def json_response(data, status=200):
    """Build a JSON response dict for Netlify Functions."""
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        },
        "body": json.dumps(data),
    }


def binary_response(file_path, filename):
    """Build a binary file response for Netlify Functions."""
    with open(file_path, "rb") as f:
        content = f.read()

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/octet-stream",
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
            "Access-Control-Allow-Origin": "*",
        },
        "body": base64.b64encode(content).decode("utf-8"),
        "isBase64Encoded": True,
    }


def validate_url(url):
    """Validate the URL is from a supported platform."""
    if not url:
        return "Please enter a video URL."
    if not url.startswith(("http://", "https://")):
        return "Please enter a valid URL starting with http:// or https://"
    if not any(domain in url.lower() for domain in ["youtube.com", "youtu.be", "instagram.com", "instagr.am"]):
        return "Only YouTube and Instagram URLs are supported."
    return None


def parse_body(event):
    """Parse the request body, handling both JSON and form-encoded data."""
    content_type = (event.get("headers") or {}).get("content-type", "")

    if "application/x-www-form-urlencoded" in content_type:
        body = event.get("body", "")
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode("utf-8")
        params = parse_qs(body)
        return {k: v[0] for k, v in params.items()}

    # Default: JSON
    body = event.get("body", "{}")
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    try:
        return json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return {}


def handler(event, context):
    """
    Main Netlify Function handler.

    Args:
        event: dict with path, httpMethod, headers, body, queryStringParameters, etc.
        context: Netlify execution context

    Returns:
        dict with statusCode, headers, body
    """
    path = (event.get("path") or "").rstrip("/")
    method = event.get("httpMethod", "GET")
    query = event.get("queryStringParameters") or {}

    # ─── CORS preflight ───
    if method == "OPTIONS":
        return json_response({"ok": True})

    # ─── GET /api/health ───
    if "/api/health" in path and method == "GET":
        return json_response({"status": "ok", "environment": "netlify"})

    # ─── POST /api/formats ───
    if "/api/formats" in path and method == "POST":
        body = parse_body(event)
        url = (body.get("url") or query.get("url", "")).strip()

        error = validate_url(url)
        if error:
            return json_response({"error": error}, 400)

        try:
            result = list_formats(url)
            if "error" in result:
                return json_response(result, 400)
            return json_response(result)
        except Exception as e:
            return json_response({"error": f"Server error: {str(e)[:300]}"}, 500)

    # ─── POST/GET /api/download ───
    if "/api/download" in path:
        if method == "POST":
            body = parse_body(event)
            url = (body.get("url") or query.get("url", "")).strip()
            format_id = (body.get("format_id") or query.get("format_id", "")).strip()
        elif method == "GET":
            url = (query.get("url") or "").strip()
            format_id = (query.get("format_id") or "").strip()
        else:
            return json_response({"error": "Method not allowed"}, 405)

        if not url:
            return json_response({"error": "Missing video URL."}, 400)
        if not format_id:
            return json_response({"error": "Missing format selection."}, 400)

        try:
            # Download to a temporary directory (Netlify has ephemeral storage)
            tmp_dir = tempfile.mkdtemp()
            result = download_video(url, format_id, tmp_dir)

            if "error" in result:
                return json_response(result, 400)

            file_path = result.get("file_path")
            if file_path and os.path.exists(file_path):
                filename = os.path.basename(file_path)
                return binary_response(file_path, filename)

            return json_response(result)
        except Exception as e:
            return json_response({"error": f"Download error: {str(e)[:300]}"}, 500)

    # ─── 404 ───
    return json_response({"error": f"Not found: {method} {path}"}, 404)
