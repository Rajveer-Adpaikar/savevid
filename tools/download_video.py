#!/usr/bin/env python3
"""
Tool: download_video.py
Purpose: Downloads a single format from a YouTube/Instagram URL using yt-dlp
         and saves it to ~/Downloads/SaveVid/
Output: JSON with download status and file path

Usage:
    python download_video.py <video_url> <format_id> [--output-dir <path>]
"""

import json
import sys
import subprocess
import os
import shutil
import re


def get_downloads_folder():
    """Get the path to the user's Downloads folder across platforms."""
    if os.name == "nt":  # Windows
        return os.path.join(os.environ["USERPROFILE"], "Downloads")
    else:  # macOS / Linux
        return os.path.join(os.path.expanduser("~"), "Downloads")


DEFAULT_OUTPUT_DIR = os.path.join(get_downloads_folder(), "SaveVid")


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

    # Firefox Ã¢â‚¬â€ standard install
    ff_std = os.path.expanduser("~/AppData/Roaming/Mozilla/Firefox/Profiles")
    if _find_ff_profile(ff_std):
        return (["--cookies-from-browser", "firefox"], None)

    # Firefox Ã¢â‚¬â€ MSIX / Microsoft Store install
    ff_msix = os.path.expanduser(
        "~/AppData/Local/Packages/Mozilla.Firefox_n80bbvh6b1yt2"
        "/LocalCache/Roaming/Mozilla/Firefox/Profiles")
    found = _find_ff_profile(ff_msix)
    if found:
        return (["--cookies-from-browser", f"firefox:{os.path.normpath(found)}"], None)

    # Chrome family Ã¢â‚¬â€ DB locked while browser runs
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
    "Make sure you're logged into Instagram in your browser, "
    'then try again.'
)


def download_video(url, format_id, output_dir=None, use_cookies=None, format_type=None, progress_callback=None):
    """
    Download the specified format from the given URL.

    Args:
        url: Video URL
        format_id: yt-dlp format code (e.g., '137', 'bestaudio', '18')
        output_dir: Directory to save the file (default: ~/Downloads/SaveVid/)
        use_cookies: Force cookie usage (None=auto for Instagram, True=force, False=skip)

    Returns:
        dict with status and file info
    """
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Build yt-dlp command
        YT_DLP_EXE = _find_yt_dlp()
        COOKIES_FILE = "/tmp/cookies.txt"
        LOCAL_COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cookies.txt")
        cmd = [
            YT_DLP_EXE,
            "--no-playlist",
            "--no-warnings",
            "--newline",  # Progress on new lines for easier parsing
        ]

        is_youtube = "youtube" in url.lower() or "youtu.be" in url.lower()
        is_instagram = "instagram" in url.lower()
        is_facebook = "facebook.com" in url.lower() or "fb.watch" in url.lower() or "fb.com" in url.lower()

        # ── YouTube: low-fingerprint clients ──
        if is_youtube:
            cmd.extend([
                "--extractor-args",
                "youtube:player_client=android_vr,web_safari,web_embedded",
            ])
            cmd.extend(["--extractor-retries", "5"])

        # ── Instagram: use iOS App ID (only valid extractor arg) ──
        if is_instagram:
            cmd.extend(["--extractor-args", "instagram:app_id=ios"])
            cmd.extend(["--extractor-retries", "5"])

        # ── Cookies: check multiple locations ──
        cookie_warning = None
        # 1. Render / cloud server: cookies decoded from $COOKIES env var
        if os.path.isfile(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0:
            cmd.extend(["--cookies", COOKIES_FILE])
        # 2. Local project root: user can place cookies.txt for Instagram/YouTube auth
        elif os.path.isfile(LOCAL_COOKIES_FILE) and os.path.getsize(LOCAL_COOKIES_FILE) > 0:
            cmd.extend(["--cookies", os.path.abspath(LOCAL_COOKIES_FILE)])
        # 3. Try browser cookie extraction (falls back gracefully if encrypted)

        # For all DASH-based platforms, merge with best available audio since
        # they use separate adaptation sets for video & audio.
        # yt-dlp gracefully falls back to just the video if no audio exists.
        # Skip merge for audio-only formats — they don't need DASH audio stitching.
        needs_audio_merge = (is_instagram or is_youtube or is_facebook) and format_type != "audio_only"
        actual_format = f"{format_id}+bestaudio/best" if needs_audio_merge else format_id

        cmd.extend([
            "--windows-filenames",
            "--restrict-filenames",
            "--trim-filenames", "100",
            "-f", actual_format,
            "-o", os.path.join(output_dir, "%(title).100B.%(ext)s"),
            url,
        ])

        # Run the download
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        # Collect output
        stdout_lines = []
        stderr_lines = []

        for line in process.stdout:
            line = line.strip()
            stdout_lines.append(line)
            print(line, file=sys.stderr, flush=True)

            if progress_callback:
                m = re.search(r"\[download\]\s+([\d.]+)%", line)
                if m:
                    info = {"percent": float(m.group(1))}
                    speed_m = re.search(r"at\s+([\d.]+[KMGTP]?i?B/s)", line)
                    eta_m = re.search(r"ETA\s+([\d:]+)", line)
                    if speed_m:
                        info["speed"] = speed_m.group(1)
                    if eta_m:
                        info["eta"] = eta_m.group(1)
                    progress_callback(info)

        for line in process.stderr:
            stderr_lines.append(line)

        process.wait()

        if process.returncode != 0:
            stderr_text = "\n".join(stderr_lines)
            if "HTTP Error 403" in stderr_text or "HTTP Error 404" in stderr_text:
                return {"error": "Download failed - the video or format may no longer be available."}
            if "Requested format is not available" in stderr_text:
                return {"error": "The requested format is not available for this video."}

            # Check for impersonation/cURL support (required by Instagram since mid-2026)
            if "Impersonate target" in stderr_text and "is not available" in stderr_text:
                return {"error": (
                    "Instagram now requires browser impersonation support, which requires "
                    "a yt-dlp build with curl_cffi. Update with:\n\n"
                    "Run:  yt-dlp --update-to master\n\n"
                    "Then restart the downloader."
                )}

            # Instagram: retry with cookies if we didn't already
            if is_instagram:
                if "empty media response" in stderr_text.lower():
                    # Check for Chrome/Edge encrypted cookie DB errors first
                    if "could not copy" in stderr_text.lower() or "failed to decrypt" in stderr_text.lower():
                        return {"error": (
                            "Instagram requires login, but your browser's cookie database is "
                            "encrypted and yt-dlp cannot read it.\n\n"
                            "Fix: Export cookies.txt from your browser and place it in the "
                            "project root folder.\n\n"
                            "How: Install a 'cookies.txt' export extension, log into Instagram, "
                            "export cookies, save the file as 'cookies.txt' in the SaveVid "
                            "project folder, then refresh this page."
                        )}

                    # On Render: cookies file existed but didn't help → expired
                    if os.path.isfile(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0:
                        return {"error": (
                            "Instagram cookies in the COOKIES env var appear to be expired. "
                            "Please re-export cookies.txt from your browser and update the "
                            "COOKIES environment variable in the Render dashboard."
                        )}

                    # Local mode: retry with browser cookies
                    if use_cookies is None:
                        retry = download_video(url, format_id, output_dir, use_cookies=True)
                        if "error" not in retry:
                            return retry

                    if cookie_warning:
                        return {"error": (
                            "Instagram requires login, but the browser's cookie database is "
                            "locked while the browser is running.\n\n"
                            f"{cookie_warning}\n\n"
                            "After trying that, paste the link again.")}
                    return {"error": INSTAGRAM_COOKIE_MSG}

                # "Media not found" = deleted/private post, not a yt-dlp bug
                if "Media not found or unavailable" in stderr_text:
                    return {"error": (
                        "This Instagram post could not be found. It may have been removed, "
                        "the URL may be incorrect, or your account may not have access to it."
                    )}

                # Other Instagram API issues
                if "HTTP Error 400" in stderr_text or "not granting access" in stderr_text:
                    return {"error": (
                        "Instagram returned an error for this post. This usually means the "
                        "post is not accessible. Try logging into Instagram in your browser "
                        "and paste the link again with Firefox open."
                    )}

            return {"error": f"Download failed: {stderr_text[:500]}"}

        # Find the downloaded file
        downloaded_file = None
        for line in stdout_lines:
            if "[info]" in line and "has already been downloaded" in line:
                # File was already downloaded Ã¢â‚¬â€ find it in the output dir
                break
            if "[download]" in line and "Destination:" in line:
                # yt-dlp sometimes prints destination
                match = __import__("re").search(r"Destination:\s*(.+)", line)
                if match:
                    downloaded_file = match.group(1).strip()
                    break
            if "[Merger]" in line:
                # Merged video+audio
                break

        # Fallback: find the most recent file in output dir
        if not downloaded_file or not os.path.exists(downloaded_file):
            files = [
                os.path.join(output_dir, f)
                for f in os.listdir(output_dir)
                if os.path.isfile(os.path.join(output_dir, f))
            ]
            if files:
                downloaded_file = max(files, key=os.path.getmtime)

        if downloaded_file and os.path.exists(downloaded_file):
            size_bytes = os.path.getsize(downloaded_file)
            size_mb = size_bytes / (1024 * 1024)
            return {
                "status": "success",
                "file_path": downloaded_file,
                "file_name": os.path.basename(downloaded_file),
                "file_size_bytes": size_bytes,
                "file_size_mb": round(size_mb, 2),
                "output_dir": output_dir,
            }
        else:
            return {
                "status": "success",
                "message": "Download completed, but couldn't locate the file.",
                "output_dir": output_dir,
            }

    except FileNotFoundError:
        return {"error": "yt-dlp is not installed. Install it with: winget install yt-dlp.yt-dlp"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)[:500]}"}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: python download_video.py <video_url> <format_id> [--output-dir <path>]"}))
        sys.exit(1)

    url = sys.argv[1].strip()
    format_id = sys.argv[2].strip()

    output_dir = DEFAULT_OUTPUT_DIR
    if "--output-dir" in sys.argv:
        idx = sys.argv.index("--output-dir")
        if idx + 1 < len(sys.argv):
            output_dir = sys.argv[idx + 1]

    result = download_video(url, format_id, output_dir)
    print(json.dumps(result, indent=2))

    if "error" in result:
        sys.exit(1)