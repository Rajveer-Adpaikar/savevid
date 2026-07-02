# SaveVid — Video Downloader Project Guide

## What This Is

A local Flask web app that downloads videos from **YouTube**, **Instagram**, and **Facebook** via yt-dlp. Runs on `http://127.0.0.1:5000`. Also attempted on Netlify and Render.com — **online deployment works for format listing and file streaming, but YouTube/Instagram bot detection remains a challenge on cloud servers**.

The UI is a cinematic landing page with autoplay video background, particle animation, and glass-morphism cards — designed to showcase both the downloader and the developer's brand (Envoyc).

**Brand name origin**: "SaveVid" was generated using an SEO-focused brand-naming process — it targets the high-volume search phrase "save video" while being short, memorable, and keyword-rich.

## Architecture (WAT Framework)

| Layer | What | Location |
|-------|------|----------|
| **Workflow** | Instructions/SOP | `workflows/yt_ig_downloader.md` |
| **Agent** | You — orchestrates tools | This CLAUDE.md |
| **Tools** | Deterministic Python scripts | `tools/list_formats.py`, `tools/download_video.py` |

## Subagents

Alongside tools (deterministic scripts), you have access to subagents (specialized Claude instances with their own context window) for tasks that would otherwise flood your main context with noise. Defined in `.claude/agents/`:

- **`docs-fetcher`** — looks up current official documentation for an API, library, or tool before you integrate it. Use before writing integration code for anything unfamiliar, rather than relying on memory (which may be outdated or wrong).
- **`debugger`** — investigates a failure and reports the root cause in plain language before any fix is attempted. Use whenever a tool errors out, a workflow produces wrong output, or something breaks in a way that isn't immediately obvious.
- **`qa-tester`** — verifies a tool or workflow actually works after it's built or changed, running existing tests or manually exercising the logic. Use after implementing or fixing something, before marking a workflow step done.
- **`code-reviewer`** — read-only check for exposed secrets, unsafe input handling, and other risks in a tool before it touches real credentials, real data, or a scheduled run. Use before any tool goes from "just written" to "trusted to run unattended."

**How to sequence them:**

- **One at a time, not parallel, when one agent's output feeds the next.** `debugger` → fix → `qa-tester` is a chain: you need the debugger's diagnosis before attempting a fix, and you need the fix in place before testing it. Running these together wastes effort since qa-tester would just be re-confirming the same failure the debugger is diagnosing.
- **`docs-fetcher` runs solo, upfront**, before you write or modify a tool — it's a research step, not a review step, so there's nothing to parallelize it against yet.
- **`qa-tester` and `code-reviewer` CAN run in parallel** once a tool is written and stable enough to check. Neither modifies anything, neither depends on the other's output, and they're looking at different concerns (does it work vs. is it safe). This is the one case where firing both at once genuinely saves time instead of adding coordination overhead.
- **Default rule of thumb:** if a subagent needs to read the result of a previous subagent to do its job, run them in sequence. If two subagents are independently inspecting the same finished piece of work, run them in parallel.

A typical flow for building or fixing a tool: `docs-fetcher` (if new integration) → build/fix the tool → `qa-tester` + `code-reviewer` in parallel → if either finds a problem, `debugger` investigates → fix → re-run `qa-tester`.

## Quick Start

### Local (full downloads, no limits)
```bash
# Start the proxy (required for free models via OpenCode Zen)
python %USERPROFILE%\.claude\zen_proxy.py

# Start the downloader
start.bat
# Or: python app.py
```

Then open `http://127.0.0.1:5000`.

**Browser cookies for Instagram (local):** The app auto-detects Firefox, Chrome, or Edge cookies via `--cookies-from-browser`. Firefox works while the browser is running. For Chrome/Edge, close the browser first so yt-dlp can read the cookie DB. If no browser cookies are available, Instagram will return an error about needing login.

### Online (Render.com — YouTube & Instagram work with cookies)
1. Push code to GitHub: `Rajveer-Adpaikar/savevid`
2. In Render Dashboard → **New Web Service** → connect repo
3. Settings:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `bash start.sh` (downloads yt-dlp_linux binary + decodes cookies)
   - **Plan**: Free
4. **Required**: Set environment variable `COOKIES` = base64-encoded cookies.txt (see instructions in `start.sh`)
5. Live URL: `https://savevid-1eve.onrender.com/`

**Current status on Render**:
- ✅ YouTube — works with fresh browser cookies
- ✅ Instagram — works with fresh browser cookies (includes `sessionid`)
- ✅ Facebook — works without cookies (public videos)
- ✅ File streaming to browser works (downloads trigger via `download_url`)
- Cookies expire every 2-4 weeks — re-export and update `COOKIES` env var when downloads stop working

## Landing Page Design

The page (`templates/index.html`) uses a Veldara-inspired dark theme with:

- **Video background**: Autoplay looped MP4 with dark overlay — instant, no scroll-driven frame extraction.
- **Particle animation**: Lightweight canvas-based particles (~100 max, simple dot rendering).
- **Nav bar**: Left = logo, Center = "Work with Envoyc" button (globe icon, links to envoyc.com), Right = social icons (GitHub, YouTube, Instagram).
- **Hero section**: Badge, "SaveVid" title, "Powered by Envoyc" tagline, subtitle "Download any video from YouTube, Instagram & Facebook. SaveVid is free, no sign-up, no tracking.", then the downloader card with URL input.
- **Footer**: "Let's work together" CTA with 4 link cards (envoyc.com, GitHub, YouTube, Instagram).
- **Format results**: Glass-morphism cards with 2 category buttons (Video MP4, Audio MP3). "Video without Audio" is no longer shown — DASH formats get audio merged automatically.
- **Format dedup**: Only one option per resolution tier (largest file size), so you see 4K → 144p cleanly instead of 30+ codec variants.
- **Mobile responsive**: Collapses nav links, stacks input row, adjusts padding.

### Branding Links

| Location | Link | Icon |
|----------|------|------|
| Nav bar (left) | "SaveVid" logo | Text |
| Nav bar (center) | envoyc.com — "Work with Envoyc" button | Globe |
| Nav bar (right) | GitHub, YouTube, Instagram (shorts) | Brand SVGs |
| Below tagline | "Powered by Envoyc" | Text link |
| Footer links | All 4 links as styled cards | Brand SVGs |

The YouTube link targets `https://www.youtube.com/@Rajveer-Adpaikar-8/shorts` (shorts channel, not main feed).

### YouTube Link
- Navbar and footer YouTube SVGs point to `https://www.youtube.com/@Rajveer-Adpaikar-8/shorts`

## SEO & Metadata

### Invisible SEO (added without UI changes)
All SEO optimizations are invisible to users — no visual changes to the page.

| Tag | Content |
|-----|---------|
| `<title>` | "SaveVid — Free Video Downloader for YouTube, Instagram & Facebook" |
| `<meta name="description">` | 160-char summary covering SaveVid, platforms, features, no sign-up |
| `<meta name="keywords">` | "free video downloader, YouTube downloader, Instagram downloader..." |
| `<meta name="robots">` | `index, follow` |
| `<link rel="canonical">` | Points to self |
| `<meta property="og:title">` | Same as `<title>` |
| `<meta property="og:description">` | Same as description |
| `<meta property="og:type">` | `website` |
| `<meta property="og:url">` | Canonical URL |
| `<meta property="og:site_name">` | "SaveVid" |
| `<meta name="twitter:card">` | `summary_large_image` |
| `<meta name="twitter:title">` | Same as `<title>` |
| `<meta name="twitter:description">` | Same as description |

### JSON-LD Structured Data (WebApplication schema)
Rich result enabling the "Free" badge in Google search results:

```json
{
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "SaveVid — Free Video Downloader",
  "applicationCategory": "Multimedia",
  "offers": { "@type": "Offer", "price": "0", "priceCurrency": "USD" },
  "author": { "@type": "Person", "name": "Envoyc", "url": "https://envoyc.com" }
}
```

### Semantic HTML
- `<div id="content">` changed to `<main id="content">` — tells search engines the primary content area
- Video element: `aria-label="Background animation from Envoyc creative portfolio"` — screen reader accessible

### Name Change for SEO
The app was renamed from "YT + IG Downloader" to **SaveVid** after an SEO brand-naming process:
- "SaveVid" targets the high-volume search query "save video"
- Short, 2-syllable brand name — easier to remember and type
- Action-verb format implies utility (like "Dropbox," "ScanSnap")
- Included in all title tags, meta descriptions, and structured data for keyword density

## Deployment

### Primary: Render.com (Full Server — Cookies Required)
- Live URL: `https://savevid-1eve.onrender.com/`
- Deployed from GitHub repo `Rajveer-Adpaikar/savevid`
- Runs the full Flask app with Gunicorn — file streaming works (browser downloads)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `bash start.sh` (downloads `yt-dlp_linux` static binary with curl_cffi baked in, then decodes `$COOKIES` env var to `/tmp/cookies.txt`)
- Free tier: 512MB RAM, spins down after 15min idle (~30s cold start)
- **YouTube**: ✅ Works with fresh browser cookies
- **Instagram**: ✅ Works with fresh browser cookies (needs `sessionid` cookie)
- **Facebook**: ✅ Works without cookies (public videos)
- **Cookies**: Must be exported as Netscape-format `cookies.txt`, base64-encoded, and stored in `COOKIES` env var. Expire every 2-4 weeks.

### Secondary: Envoyc Portfolio Page
- A **Portfolio page** exists in the Envoyc site (`src/components/Portfolio.tsx`) showing SaveVid as a project
- Navigation link to Portfolio sits between Services and How It Works in the navbar
- Preferred deployment: subdirectory of envoyc.com → `https://envoyc.com/savevid`
  - Subdirectory inherits domain authority from envoyc.com (vs standalone subdomain at zero SEO trust)

### Legacy: Netlify (Replaced — Serverless Limits)
- Deployment at `https://savevidfree.netlify.app/`
- Serverless Functions have a 10-second timeout and 10MB response limit — all downloads fail
- Replaced by Render.com which runs a full server, but even Render couldn't solve YouTube/Instagram bot detection

### yt-dlp — Static Linux Binary with curl_cffi
- Render's `start.sh` downloads `yt-dlp_linux` from GitHub releases — the **static binary with curl_cffi baked in** (browser impersonation support).
- pip-installed `yt-dlp` is the "zipimport" binary which deliberately **excludes curl_cffi**.
- The binary is downloaded fresh on every deploy (auto-updates to latest release).
- On Windows local dev: `winget install yt-dlp.yt-dlp` includes curl_cffi.
- Update to latest master: `yt-dlp --update-to master`

### yt-dlp Binary Discovery (`_find_yt_dlp()`)
Both tools use `_find_yt_dlp()` to locate the binary in this order:
1. **Project root** (`./yt-dlp.exe` or `./yt-dlp`) — where `start.sh` places it on Render
2. **Current working directory** — covers cases where cwd differs from project root
3. **Tools directory** (`tools/yt-dlp`, `tools/yt-dlp_linux`)
4. **PATH lookup** via `shutil.which("yt-dlp")` — for local installations
5. **Fallback**: bare `"yt-dlp"` command (works if on PATH)
- Debug output logged to stderr so Render deploy logs show which path was resolved.

### DASH Streaming (YouTube + Instagram + Facebook)
- YouTube, Instagram, and Facebook all use DASH: video and audio are separate adaptation sets.
- High-resolution video formats (4K, 1080p, etc.) have `acodec: "none"` (video_only in yt-dlp).
- **Download fix**: `format_id + bestaudio/best` auto-merges audio via yt-dlp for both platforms.
- **Display fix**: `video_only` formats are reclassified as "combined" for YouTube, Instagram, and Facebook so higher resolutions appear under "Video (MP4)" instead of being hidden in a separate category.
- Instagram reels sometimes genuinely have no audio — downloads fall back to video-only.

### Format Deduplication
- `list_formats.py` filters raw yt-dlp output (30+ formats) down to **one option per resolution tier**.
- For each `(type_category, resolution_label)` pair — e.g. `("combined", "1080p")` — only the **largest file-size** format is kept.
- Audio formats pass through untouched (users pick by bitrate).
- Result: a clean, compact list (typically ~12 entries) instead of overwhelming the user with codec variants.

### Browser Cookies (Instagram)
- Instagram requires login for most content.
- Cookie detection order:
  1. `/tmp/cookies.txt` — Render/cloud server (from `$COOKIES` env var)
  2. `cookies.txt` — local project root (user-placed Netscape-format file)
  3. Browser cookie extraction via `--cookies-from-browser` (Firefox > Chrome > Edge)
- **Firefox**: Preferred — cookie DB readable while browser is running.
- **Chrome/Edge**: Both use App-Bound Encryption (DPAPI) that **blocks yt-dlp from reading the cookie DB** even when the browser is closed. The error `"Could not copy Chrome cookie database"` or `"Failed to decrypt with DPAPI"` triggers a clear message directing users to export a `cookies.txt` file.
- **Local cookies.txt fix**: If Chrome/Edge don't work, export cookies via a browser extension, save as `cookies.txt` in the project root, and refresh.

### Cookie Setup for Render (YouTube + Instagram)
1. Install a "cookies.txt" export extension in your browser
2. Log into YouTube and Instagram in the same browser session
3. Export cookies for `youtube.com` and `instagram.com` into a single `cookies.txt`
4. Base64-encode it: `base64 -w0 cookies.txt` (Linux/Mac) or use an online tool (Windows)
5. Paste the base64 string as the `COOKIES` environment variable in Render Dashboard
6. Deploy — `start.sh` decodes it to `/tmp/cookies.txt` automatically
7. Re-do steps 2-6 every 2-4 weeks when cookies expire

### Flask Format Cache
- `app.py` caches format listings per URL for 10 minutes (TTL: 600s).
- This prevents inconsistent UI when yt-dlp returns different results on repeated calls.
- Cache key is the URL string; cleared on server restart.

### Format Categorization (2 active buttons + dedup)
| Category | Type in yt-dlp | Appears when |
|----------|----------------|--------------|
| **Video (MP4)** | `combined` | Always (YouTube + Instagram DASH reclassified as combined) |
| **Audio (MP3)** | `audio_only` | Always |

"Video without Audio" is not shown — dedup reclassifies video-only formats as combined since they get merged with audio on download.

### Duration Handling
- YouTube returns `int` duration → works with `:02d` format specifier.
- Instagram returns `float` duration (e.g. 4.966) → must cast to `int`.

### UI Text & Encoding
- Emoji characters in JS string literals caused encoding corruption (mojibake) on save.
- **Fix**: All info labels use plain text instead of emoji:
  - `Duration:` (was `⏱`)
  - `Max Resolution:` (was `📺`)
  - `Number of formats:` (was `📦`)
  - `Download another video` (was `⬅`)
- The "Download another video" button uses class `.again-btn` and is cleaned up before each creation to prevent stacking duplicates.

## Tools

### `tools/list_formats.py`
- Runs `yt-dlp -J` to dump JSON metadata.
- Parses formats, filters unknown types, deduplicates by largest file per resolution tier.
- **Dedup logic**: groups by `(type_category, resolution_label)`, keeps the format with the biggest `filesize_bytes`.
- Reclassifies `video_only` → `combined` for YouTube, Instagram, and Facebook (since `+bestaudio/best` merges audio).
- **Source detection**: reads yt-dlp's `extractor` field to determine whether a URL is YouTube, Instagram, or Facebook — affects DASH merge logic.
- **Facebook graceful error**: "Cannot parse data" from the Facebook extractor shows a clear error directing users to update yt-dlp (upstream bug #15161).
- Output: JSON with title, duration, source, deduped formats array.
- Handles: private videos, invalid URLs, HTTP errors, timeout, missing yt-dlp.

### `tools/download_video.py`
- Downloads single format via yt-dlp to `~/Downloads/SaveVid/`.
- **YouTube + Instagram + Facebook**: auto-appends `+bestaudio/best` for DASH audio merge (skipped for audio-only formats).
- Uses `--windows-filenames`, `--restrict-filenames`, and `--trim-filenames 100` to produce safe, ASCII-only filenames without emojis or special characters.
- Accepts optional `progress_callback` — called with `{"percent": 45.2, "speed": "...", "eta": "..."}` on each yt-dlp progress line.
- Handles: HTTP 403/404, unavailable formats, impersonation errors, media not found.

## Project Structure

```
├── app.py                          # Flask web app (main entry)
├── start.bat                       # Launcher for Windows
├── start.sh                        # Render.com startup script (downloads yt-dlp_linux + decodes cookies)
├── requirements.txt                # flask, flask-cors, gunicorn (yt-dlp downloaded as static binary)
├── runtime.txt                     # Python 3.12 (Netlify — legacy)
├── netlify.toml                    # Netlify deployment config (legacy)
├── netlify/functions/api.py        # Netlify Function handler (legacy)
├── templates/index.html            # Cinematic landing page (video bg, particles, glass UI)
├── tools/
│   ├── list_formats.py             # Fetch available formats + sizes
│   └── download_video.py           # Download a format to ~/Downloads/SaveVid/
├── workflows/
│   └── yt_ig_downloader.md         # SOP for the downloader
├── docs/                           # Design specs
└── .gitignore
```

## Footer
```
Files save to ~/Downloads/SaveVid/
```

## Known Gotchas

- **Facebook support (upstream broken)**: The yt-dlp Facebook extractor is currently broken (yt-dlp issue #15161, open since Nov 2025). Facebook changed its page data structure and the extractor can't parse it. The code support is in place (URL validation, DASH reclassification, audio merge), but `yt-dlp -J` fails with "Cannot parse data" for all Facebook URLs. The app shows a graceful error message with update instructions. Track progress at [yt-dlp issue #15161](https://github.com/yt-dlp/yt-dlp/issues/15161).
- **Instagram 400 errors**: Usually means the post/reel was deleted or your account doesn't have access. Rarely an API break.
- **Chrome/Edge cookies blocked on Windows**: Both use App-Bound Encryption (DPAPI). yt-dlp fails with "Could not copy Chrome cookie database" or "Failed to decrypt with DPAPI". Fix: Export `cookies.txt` from a browser extension, place in project root, refresh.
- **"Impersonate target not available"**: yt-dlp needs the curl_cffi build. Install via winget or download the static binary.
- **Netlify download limits**: Large files (>10MB) may time out on the free tier. Local mode is better for big downloads.
- **Very large files (>2GB)**: No warning currently implemented — downloads proceed directly.
- **Footer below fold**: Fixed by setting `min-height: auto`, `justify-content: center`, reducing hero padding, and removing bottom padding on content container.
- **Emoji mojibake**: Emoji in JS string literals and Python error strings caused encoding corruption on save. All labels and error messages use plain ASCII text instead of emoji.
- **`yt-dlp` binary not found on Render**: Fixed by removing unreliable `os.access(path, os.X_OK)` check and adding `os.getcwd()` + `shutil.which()` fallbacks. Check Render deploy logs for `[find_yt_dlp]` lines to see which path was resolved.
- **YouTube works online with cookies**: Uses `yt-dlp_linux` static binary (curl_cffi baked in) + `--cookies /tmp/cookies.txt` from `$COOKIES` env var. Extractor args: `player_client=android_vr,web_safari,web_embedded` — uses low-fingerprint clients to avoid bot detection. `player_skip=webpage,configs` was removed (Jul 2026) because YouTube started returning error 152 - 18 when configs were skipped.
- **Instagram works online with cookies**: Same static binary — uses `instagram:app_id=ios` (only valid extractor arg) + `--cookies` for the `sessionid` cookie. Note: `instagram:webpage=api` **does not exist** in yt-dlp and was silently ignored.
- **Cookies expire every 2-4 weeks**: YouTube and Instagram cookies are short-lived. When downloads stop working, re-export cookies.txt from your browser, base64-encode it, and update the `COOKIES` env var in Render dashboard. Then trigger a new deploy.
- **Facebook works without cookies**: Facebook downloads work on Render even without authentication, as long as the video is public and the Facebook extractor isn't broken upstream (issue #15161).
- **Download progress streaming**: `app.py` streams real-time download progress as NDJSON (newline-delimited JSON) from `/api/download` using a background thread + queue. The frontend reads the stream via `response.body.getReader()` and animates the progress bar with percentage, speed, and ETA.
- **File streaming via download tokens**: `app.py` generates one-time `/api/dl/<token>` URLs that stream the file to the browser and clean up the temp directory afterward. Works for all successfully downloaded files.
