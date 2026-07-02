#!/usr/bin/env python3
"""
Tool: list_formats.py
Purpose: Fetches all available formats from a YouTube/Instagram URL via yt-dlp
         and returns them as structured JSON with sizes and resolution info.
Output: JSON object with video info + sorted formats array

Usage:
    python list_formats.py <video_url>
"""

import json
import sys
import subprocess
import re
import os

# Resolution hierarchy for sorting and limiting
RESOLUTION_MAP = {
    "4320": "8K",
    "2160": "4K",
    "1440": "2K",
    "1080": "1080p",
    "720": "720p",
    "480": "480p",
    "360": "360p",
    "240": "240p",
    "144": "144p",
}

def human_readable_size(bytes_val):
    """Convert bytes to human-readable string."""
    if bytes_val is None or bytes_val <= 0:
        return "Unknown"
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(bytes_val) < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} TB"


def parse_filesize(filesize_str):
    """Convert yt-dlp filesize strings to bytes."""
    if not filesize_str or filesize_str == "Unknown":
        return None
    filesize_str = str(filesize_str)
    match = re.match(r"([\d.]+)\s*(B|KB|MB|GB|TB)", filesize_str)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2)
    units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    return int(value * units[unit])


def get_resolution_label(height):
    """Get human-readable resolution label from height."""
    if height is None:
        return "Unknown"
    for threshold, label in sorted(RESOLUTION_MAP.items(), key=lambda x: int(x[0]), reverse=True):
        if height >= int(threshold):
            return label
    return f"{height}p"


def extract_height_from_resolution(resolution_str):
    """Extract height from resolution string like '1920x1080'."""
    if not resolution_str:
        return None
    match = re.search(r"x(\d+)", resolution_str)
    if match:
        return int(match.group(1))
    return None


def get_format_type(fmt):
    """Classify format as 'video+audio', 'video only', or 'audio only'."""
    vcodec = fmt.get("vcodec", "none")
    acodec = fmt.get("acodec", "none")
    has_video = vcodec and vcodec != "none"
    has_audio = acodec and acodec != "none"
    if has_video and has_audio:
        return "combined"
    elif has_video:
        return "video_only"
    elif has_audio:
        return "audio_only"
    return "unknown"


def _find_yt_dlp():
    """Locate the yt-dlp binary. Checks project root, cwd, tools dir, then PATH."""
    import shutil
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(script_dir)
    candidates = [
        os.path.join(parent, "yt-dlp.exe"),       # Windows (project root)
        os.path.join(parent, "yt-dlp"),            # Linux/macOS (project root)
        os.path.join(os.getcwd(), "yt-dlp"),       # current working directory
        os.path.join(os.getcwd(), "yt-dlp.exe"),   # cwd with .exe
        os.path.join(script_dir, "yt-dlp.exe"),    # Windows (tools dir)
        os.path.join(script_dir, "yt-dlp"),        # Linux/macOS (tools dir)
        os.path.join(script_dir, "yt-dlp_linux"),  # old naming
    ]
    for path in candidates:
        if os.path.isfile(path):
            resolved = os.path.abspath(path)
            print("[find_yt_dlp] Found:", resolved, file=sys.stderr)
            return resolved
    # Fallback: proper PATH search via shutil
    which = shutil.which("yt-dlp")
    if which:
        print("[find_yt_dlp] Found via PATH:", which, file=sys.stderr)
        return which
    which = shutil.which("yt-dlp_linux")
    if which:
        print("[find_yt_dlp] Found via PATH:", which, file=sys.stderr)
        return which
    print("[find_yt_dlp] Fallback to bare 'yt-dlp'", file=sys.stderr)
    return "yt-dlp"


def _get_browser_cookies_args():
    """Returns (args_list, warning_or_None).

    Firefox is preferred because its cookie DB is readable while the
    browser is running.  Chrome locks its DB with App-Bound Encryption
    and requires the browser to be closed first.

    Checks both standard and MSIX (Microsoft Store) Firefox profile paths.
    """
    # Helper: find Firefox profile dir in a given parent.
    # Prefer .default-release (active profile) over .default (stale).
    def _find_ff_profile(profiles_dir):
        if not os.path.isdir(profiles_dir):
            return None
        best = None
        for p in os.listdir(profiles_dir):
            if p.endswith(".default-release"):
                return os.path.join(profiles_dir, p)
            if p.endswith(".default"):
                best = os.path.join(profiles_dir, p)
        return best

    # Firefox ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â standard install
    ff_std = os.path.expanduser("~/AppData/Roaming/Mozilla/Firefox/Profiles")
    if _find_ff_profile(ff_std):
        return (["--cookies-from-browser", "firefox"], None)

    # Firefox ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â MSIX / Microsoft Store install
    ff_msix = os.path.expanduser(
        "~/AppData/Local/Packages/Mozilla.Firefox_n80bbvh6b1yt2"
        "/LocalCache/Roaming/Mozilla/Firefox/Profiles")
    found = _find_ff_profile(ff_msix)
    if found:
        return (["--cookies-from-browser", f"firefox:{os.path.normpath(found)}"], None)

    # Chrome family ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â DB locked while browser runs
    chrome_cookies = os.path.expanduser(
        "~/AppData/Local/Google/Chrome/User Data/Default/Network/Cookies")
    if os.path.isfile(chrome_cookies):
        return (["--cookies-from-browser", "chrome"],
                "Close Chrome and try again, or use Firefox.")

    edge_cookies = os.path.expanduser(
        "~/AppData/Local/Microsoft/Edge/User Data/Default/Network/Cookies")
    if os.path.isfile(edge_cookies):
        return (["--cookies-from-browser", "edge"],
                "Close Edge and try again, or use Firefox.")

    return ([], None)


INSTAGRAM_COOKIE_MSG = (
    'Instagram now requires login to view content. '
    'Make sure you\'re logged into Instagram in your browser, '
    'then try again.'
)


def list_formats(url, use_cookies=None):
    """
    Fetch all formats for the given URL using yt-dlp.
    Returns a dict with video metadata + formats array.
    """
    try:
        # Build base command
        YT_DLP_EXE = _find_yt_dlp()
        COOKIES_FILE = "/tmp/cookies.txt"
        cmd = [
            YT_DLP_EXE,
            "--no-playlist",
            "--no-warnings",
            "-J",  # dump JSON
        ]

        is_youtube = "youtube" in url.lower() or "youtu.be" in url.lower()
        is_instagram = "instagram" in url.lower()
        is_facebook = "facebook.com" in url.lower() or "fb.watch" in url.lower() or "fb.com" in url.lower()

        # ── YouTube: low-fingerprint clients + skip heavy requests ──
        if is_youtube:
            cmd.extend([
                "--extractor-args",
                "youtube:player_client=android_vr,web_safari,web_embedded;player_skip=webpage,configs",
            ])
            cmd.extend(["--extractor-retries", "5"])

        # ── Instagram: use iOS App ID (only valid extractor arg) ──
        if is_instagram:
            cmd.extend(["--extractor-args", "instagram:app_id=ios"])
            cmd.extend(["--extractor-retries", "5"])

        # ── Cookies: prefer server cookies file, then try local browser ──
        cookie_warning = None
        if os.path.isfile(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0:
            # Render / cloud server: cookies decoded from $COOKIES env var
            cmd.extend(["--cookies", COOKIES_FILE])
        elif use_cookies is True or (use_cookies is None and is_instagram):
            # Local machine: try extracting from browser
            cookie_args, cookie_warning = _get_browser_cookies_args()
            if cookie_warning:
                pass  # Browser found but DB locked
            elif cookie_args:
                cmd.extend(cookie_args)

        cmd.append(url)

        # Run yt-dlp to get JSON info
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            if "This video is unavailable" in stderr or "Private video" in stderr:
                return {"error": "This video is private or unavailable."}
            if "not a valid URL" in stderr.lower() or "Unsupported URL" in stderr:
                return {"error": "Not a valid YouTube or Instagram URL."}
            if "HTTP Error 403" in stderr or "HTTP Error 404" in stderr:
                return {"error": "Video not found (HTTP error). It may have been removed."}

            # Check for impersonation/cURL support (required by Instagram since mid-2026)
            if "Impersonate target" in stderr and "is not available" in stderr:
                return {"error": (
                    "Instagram now requires browser impersonation support, which requires "
                    "a yt-dlp build with curl_cffi. Update with:\n\n"
                    "ÃƒÂ°Ã…Â¸Ã¢â‚¬ËœÃ¢â‚¬Â° Run:  yt-dlp --update-to master\n\n"
                    "Then restart the downloader."
                )}

            # Instagram-specific: retry with cookies if we didn't already
            if is_instagram:
                if "empty media response" in stderr.lower():
                    # On Render: cookies file existed but didn't help → expired cookies
                    if os.path.isfile(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0:
                        return {"error": (
                            "Instagram cookies in the COOKIES env var appear to be expired. "
                            "Please re-export cookies.txt from your browser and update the "
                            "COOKIES environment variable in the Render dashboard."
                        )}

                    # Local mode: retry by extracting browser cookies
                    if use_cookies is None:
                        retry = list_formats(url, use_cookies=True)
                        if "error" not in retry:
                            return retry

                    if cookie_warning:
                        return {"error": (
                            "Instagram requires login, but Chrome's cookie database is locked "
                            "while Chrome is running.\n\n"
                            f"ÃƒÂ°Ã…Â¸Ã¢â‚¬ËœÃ¢â‚¬Â° {cookie_warning}\n\n"
                            "After trying that, paste the link again.")}
                    return {"error": INSTAGRAM_COOKIE_MSG}

                # "Media not found" ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ deleted/private post, not a yt-dlp bug
                if "Media not found or unavailable" in stderr:
                    return {"error": (
                        "This Instagram post could not be found. It may have been removed, "
                        "the URL may be incorrect, or your account may not have access to it."
                    )}

                # Other Instagram API issues (rate limiting, etc.)
                if "HTTP Error 400" in stderr or "not granting access" in stderr:
                    return {"error": (
                        "Instagram returned an error for this post. This usually means the "
                        "post is not accessible ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â try logging into Instagram in your browser "
                        "and paste the link again with Firefox open."
                    )}

            # Facebook-specific: extractor may be broken upstream
            if is_facebook:
                if "Cannot parse data" in stderr:
                    return {"error": (
                        "Facebook videos currently can't be downloaded because the "
                        "yt-dlp Facebook extractor is broken due to a Facebook update.\n\n"
                        "This is a known issue (yt-dlp #15161). Check for updates:\n\n"
                        "   yt-dlp --update-to master\n\n"
                        "Then restart the downloader."
                    )}

            return {"error": f"yt-dlp error: {stderr[:500]}"}

        info = json.loads(result.stdout)

        # Extract video metadata
        video_title = info.get("title", "Unknown Title")
        duration = info.get("duration", 0)
        webpage_url = info.get("webpage_url", url)
        extractor = info.get("extractor", "unknown")

        # Determine source
        if "instagram" in extractor.lower():
            source = "instagram"
        elif "facebook" in extractor.lower():
            source = "facebook"
        else:
            source = "youtube"

        # Process formats
        raw_formats = info.get("formats", [])

        # Find the highest native resolution
        max_height = 0
        for fmt in raw_formats:
            height = fmt.get("height") or extract_height_from_resolution(fmt.get("resolution", ""))
            if height and height > max_height:
                max_height = height

        max_res_label = get_resolution_label(max_height) if max_height else "Unknown"

        # Build clean formats list
        formats_list = []
        seen_formats = set()

        for fmt in raw_formats:
            format_id = str(fmt.get("format_id", ""))
            if not format_id or format_id in seen_formats:
                continue
            seen_formats.add(format_id)

            ext = fmt.get("ext", "unknown")
            resolution = fmt.get("resolution", "")
            height = fmt.get("height") or extract_height_from_resolution(resolution)
            width = fmt.get("width")
            vcodec = fmt.get("vcodec", "none")
            acodec = fmt.get("acodec", "none")
            filesize = fmt.get("filesize") or fmt.get("filesize_approx")
            tbr = fmt.get("tbr") or fmt.get("abr") or fmt.get("vbr")

            fmt_type = get_format_type(fmt)

            # Skip unknown-type formats (no codec info ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â not downloadable)
            if fmt_type == "unknown":
                continue

            # For Instagram and YouTube, video-only DASH formats will be
            # merged with the best available audio during download, so
            # treat them as combined so they show in the "Video (MP4)" UI.
            if source in ("instagram", "youtube", "facebook") and fmt_type == "video_only":
                fmt_type = "combined"

            # Calculate the max resolution this video can be downloaded at
            # If it's 4K native, offer up to 4K. No upscaling.
            native_height = height if height else 0

            # Build display name
            if fmt_type == "audio_only":
                abr = fmt.get("abr", 0)
                display_name = f"Audio {abr:.0f}kbps ({ext})"
            elif fmt_type == "video_only":
                res_label = get_resolution_label(height) if height else "Unknown"
                display_name = f"HQ {res_label} [{ext}]"
            else:  # combined
                res_label = get_resolution_label(height) if height else "Unknown"
                display_name = f"{res_label} [{ext}]"

            # Get note about max resolution
            note = ""
            if height and max_height > height:
                note = f" (downscaled from {max_res_label})"

            formats_list.append({
                "format_id": format_id,
                "ext": ext,
                "type": fmt_type,
                "resolution": resolution or f"{width or '?'}x{height or '?'}",
                "width": width,
                "height": height,
                "vcodec": vcodec,
                "acodec": acodec,
                "filesize_bytes": filesize,
                "filesize": human_readable_size(filesize),
                "bitrate": round(tbr) if tbr else None,
                "display_name": display_name,
                "note": note,
                "native_resolution": height == max_height or height is None,
            })

        # â”€â”€ Deduplicate: keep only the largest file-size option per resolution tier â”€â”€
        deduped = []
        seen_tiers = {}

        for f in formats_list:
            if f["type"] == "audio_only":
                deduped.append(f)
                continue

            tier = get_resolution_label(f["height"]) if f["height"] else "Unknown"
            type_cat = f["type"]
            key = (type_cat, tier)

            existing = seen_tiers.get(key)
            if existing is None:
                seen_tiers[key] = f
            else:
                existing_size = existing.get("filesize_bytes") or 0
                this_size = f.get("filesize_bytes") or 0
                if this_size > existing_size:
                    seen_tiers[key] = f

        for f in seen_tiers.values():
            f["note"] = ""
            f["native_resolution"] = True
            deduped.append(f)

        # Sort: combined first (by resolution desc), then video_only, then audio_only
        def sort_key(f):
            type_order = {"combined": 0, "video_only": 1, "audio_only": 2}
            height = f["height"] or 0
            return (type_order.get(f['type'], 3), -height)

        deduped.sort(key=sort_key)

        return {
            "title": video_title,
            "duration_seconds": duration,
            "duration_formatted": f"{int(duration) // 60}:{int(duration) % 60:02d}",
            "source": source,
            "url": webpage_url,
            "max_resolution": max_res_label,
            "max_height": max_height,
            "formats": deduped,
            "format_count": len(deduped),
        }
    except subprocess.TimeoutExpired:
        return {"error": "Request timed out. Check your internet connection and try again."}
    except FileNotFoundError:
        return {"error": "yt-dlp is not installed. Install it with: winget install yt-dlp.yt-dlp"}
    except json.JSONDecodeError:
        return {"error": "Failed to parse video information."}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)[:500]}"}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python list_formats.py <video_url>"}))
        sys.exit(1)

    url = sys.argv[1].strip()

    # Basic URL validation
    if not url.startswith(("http://", "https://")):
        print(json.dumps({"error": "Please enter a valid URL starting with http:// or https://"}))
        sys.exit(1)

    result = list_formats(url)
    print(json.dumps(result, indent=2))

    if "error" in result:
        sys.exit(1)