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

### Online (Render.com — attempted, partial success)
1. Push code to GitHub: `Rajveer-Adpaikar/savevid`
2. In Render Dashboard → **New Web Service** → connect repo
3. Settings:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `bash start.sh` (upgrades yt-dlp first)
   - **Plan**: Free
4. Live URL: `https://savevid-1eve.onrender.com/`

**Current limitations on Render**:
- ✅ Format listing works for all platforms
- ✅ File streaming to browser works (downloads trigger via `download_url`)
- ❌ YouTube — "Sign in to confirm you're not a bot" even with `android_creator` client
- ❌ Instagram — "requires login" (private content), public content may also fail
- ✅ Facebook downloads work (the one that actually succeeded in testing)
- Only reliable option is **local** via `start.bat` on your own machine

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

### Primary: Render.com (Full Server — Limited Success)
- Live URL: `https://savevid-1eve.onrender.com/`
- Deployed from GitHub repo `Rajveer-Adpaikar/savevid`
- Runs the full Flask app with Gunicorn — file streaming works (browser downloads)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `bash start.sh` (upgrades yt-dlp to latest, then starts Gunicorn)
- Free tier: 512MB RAM, spins down after 15min idle (~30s cold start)
- **YouTube**: ❌ Bot detection blocks downloads even with `android_creator` client and latest yt-dlp
- **Instagram**: ❌ Requires cookies from a real browser (not available on cloud servers)
- **Facebook**: ✅ Downloads work reliably — both format fetching and downloading
- **Verdict**: Online deployment works well for Facebook. YouTube/Instagram require local machine with browser cookies.

### Secondary: Envoyc Portfolio Page
- A **Portfolio page** exists in the Envoyc site (`src/components/Portfolio.tsx`) showing SaveVid as a project
- Navigation link to Portfolio sits between Services and How It Works in the navbar
- Preferred deployment: subdirectory of envoyc.com → `https://envoyc.com/savevid`
  - Subdirectory inherits domain authority from envoyc.com (vs standalone subdomain at zero SEO trust)

### Legacy: Netlify (Replaced — Serverless Limits)
- Deployment at `https://savevidfree.netlify.app/`
- Serverless Functions have a 10-second timeout and 10MB response limit — all downloads fail
- Replaced by Render.com which runs a full server, but even Render couldn't solve YouTube/Instagram bot detection

### yt-dlp Requirement
- Instagram requires yt-dlp **master build with curl_cffi** (browser impersonation).
- The WinGet version (`winget install yt-dlp.yt-dlp`) includes curl_cffi — **pip install does not**.
- If you update yt-dlp via pip, copy the WinGet binary over it:
  ```
  cp /c/Users/thera/AppData/Local/Microsoft/WinGet/Packages/yt-dlp.yt-dlp_Microsoft.Winget.Source_8wekyb3d8bbwe/yt-dlp.exe /c/Python312/Scripts/yt-dlp.exe
  ```
- Update to latest master: `yt-dlp --update-to master`

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
- `_get_browser_cookies_args()` in both tools auto-detects Firefox profiles first.
- **Firefox**: Preferred — cookie DB readable while browser is running.
- **Chrome/Edge**: DB locked while browser runs. Must close browser first.
- Falls back gracefully — shows clear error message if cookies unavailable.

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
- **YouTube + Instagram + Facebook**: auto-appends `+bestaudio/best` for DASH audio merge.
- Progress output via stdout for UI feedback.
- Handles: HTTP 403/404, unavailable formats, impersonation errors, media not found.

## Project Structure

```
├── app.py                          # Flask web app (main entry)
├── start.bat                       # Launcher for Windows
├── start.sh                        # Render.com startup script (upgrades yt-dlp, starts gunicorn)
├── requirements.txt                # flask, flask-cors, yt-dlp, gunicorn
├── runtime.txt                     # Python 3.12 (Netlify)
├── instagram_cookies.txt           # Cookie file for Instagram auth
├── netlify.toml                    # Netlify deployment config
├── netlify/functions/api.py        # Netlify Function handler (reuses tools)
├── templates/index.html            # Cinematic landing page (video bg, particles, glass UI)
├── tools/
│   ├── list_formats.py             # Fetch available formats + sizes
│   └── download_video.py           # Download a format to ~/Downloads/SaveVid/
├── workflows/
│   └── yt_ig_downloader.md         # SOP for the downloader
├── .tmp/                           # Temporary debug files (gitignored)
│   ├── insta_raw.json
│   └── test_instagram.py
└── .gitignore
```

## Footer
```
Files save to ~/Downloads/SaveVid/
```

## Known Gotchas

- **Facebook support (upstream broken)**: The yt-dlp Facebook extractor is currently broken (yt-dlp issue #15161, open since Nov 2025). Facebook changed its page data structure and the extractor can't parse it. The code support is in place (URL validation, DASH reclassification, audio merge), but `yt-dlp -J` fails with "Cannot parse data" for all Facebook URLs. The app shows a graceful error message with update instructions. Track progress at [yt-dlp issue #15161](https://github.com/yt-dlp/yt-dlp/issues/15161).
- **Instagram 400 errors**: Usually means the post/reel was deleted or your account doesn't have access. Rarely an API break.
- **"Impersonate target not available"**: yt-dlp needs the curl_cffi build. Copy WinGet binary (see above).
- **Netlify download limits**: Large files (>10MB) may time out on the free tier. Local mode is better for big downloads.
- **Cookie DB locked**: Chrome locks its cookie DB when running. Use Firefox or close Chrome first.
- **Facebook is not public-only**: Unlike YouTube, most Facebook videos require login. Adding `--cookies-from-browser` support may be needed once the extractor is fixed.
- **Very large files (>2GB)**: No warning currently implemented — downloads proceed directly.
- **Video background frame extraction**: The Veldara scroll-video frame-extraction approach was replaced with simple `<video autoplay loop>` — far more performant, no lag.
- **Particle performance**: Particle count is capped at 100 with lower opacity/drift to avoid CPU churn on the canvas.
- **Footer below fold**: Original CSS used `min-height: 100vh` on `#content` with `flex: 1` on `.hero`, pushing footer off-screen. Fixed by setting `min-height: auto`, `justify-content: center`, reducing hero padding, and removing bottom padding on content container.
- **Emoji mojibake**: Emoji in JS string literals caused encoding corruption on save. All labels use plain text instead (e.g. `Duration:` not `⏱`).
- **YouTube bot detection unsolved online**: Even with `--extractor-args youtube:player_client=android_creator,android` and latest yt-dlp, Render's pip-installed version can't bypass YouTube's "Sign in to confirm" prompt. The WinGet binary (Windows) has this built-in but Linux pip packages don't include `curl_cffi` for browser impersonation. No known fix without using cookies from a real browser.
- **Instagram unsolved online**: Instagram requires browser cookies for most content. The API extraction flag (`instagram:webpage=api`) helps with some public reels but not reliably. No known fix for cloud deployment.
- **Facebook works online**: Facebook downloads surprisingly work on Render. The only platform that fully functions in cloud deployment.
- **File streaming via download tokens**: `app.py` generates one-time `/api/dl/<token>` URLs that stream the file to the browser and clean up the temp directory afterward. Works for all successfully downloaded files.
