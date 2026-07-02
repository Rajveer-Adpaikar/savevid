# SaveVid — Cookie-Based Auth for YouTube & Instagram on Render

## Problem

YouTube blocks all downloads with "Sign in to confirm you're not a bot" and Instagram requires logged-in cookies. Both fail on Render.com because:

1. Pip-installed `yt-dlp` on Linux is the "zipimport" binary — it **excludes curl_cffi** (browser impersonation library)
2. YouTube extractor args are using `android_creator` which is heavily fingerprinted
3. Instagram extractor args use `instagram:webpage=api` — **this flag does not exist in yt-dlp** (silent no-op this whole time)
4. No cookies are passed to yt-dlp on the server

## Solution

Three changes working together:

### A. Static `yt-dlp_linux` Binary (Replaces pip install)

The official GitHub release `yt-dlp_linux` includes curl_cffi baked in. `start.sh` downloads it at startup instead of `pip install --upgrade yt-dlp`.

### B. Cookies Via Environment Variable

User exports browser cookies (YouTube + Instagram) as a Netscape-format `cookies.txt`, base64-encodes it, and stores it as `COOKIES` env var in Render Dashboard. `start.sh` decodes it to `/tmp/cookies.txt` at startup.

### C. Updated Extractor Args

- **YouTube**: `player_client=android_vr,web_safari,web_embedded;player_skip=webpage,configs` — VR/safari/embedded clients trigger less bot detection, skipping webpage/configs requests removes the most heavily monitored requests
- **Instagram**: `instagram:app_id=ios` — the only valid extractor arg for Instagram; iOS App ID sometimes bypasses rate limiting

## Files Changed

| File | Change |
|------|--------|
| `start.sh` | Download `yt-dlp_linux` binary + decode `$COOKIES` env var to `/tmp/cookies.txt` |
| `tools/list_formats.py` | Add `--cookies /tmp/cookies.txt`, update YouTube extractor args, fix Instagram args |
| `tools/download_video.py` | Same extractor args + cookies |
| `requirements.txt` | Remove `yt-dlp>=2024.0` and `curl_cffi>=0.7.0` (baked into binary) |
| `CLAUDE.md` | Document changes |

## User One-Time Setup

1. Install "cookies.txt" browser extension
2. Log into YouTube + Instagram
3. Export cookies.txt
4. Base64-encode the file
5. Paste into Render Dashboard as `COOKIES` env var
6. (Repeat every 2-4 weeks when cookies expire)

## Rollback

If cookies approach fails for any reason, set `COOKIES` env var to empty and the tools gracefully degrade (skip `--cookies` flag if file missing).
