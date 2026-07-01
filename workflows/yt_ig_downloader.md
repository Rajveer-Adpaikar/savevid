# YouTube + Instagram Downloader — Workflow

## Objective
Provide a clean, ad-free desktop web app that lets users download videos from YouTube and Instagram in any available format/quality with transparent file-size display before downloading.

## Required Inputs
- A valid YouTube or Instagram video URL

## Tools Used
| Tool | Purpose |
|------|---------|
| `list_formats.py` | Fetches available formats + sizes from a video URL |
| `download_video.py` | Downloads a single format to the downloads folder |

## How It Works

### Step 1: User Provides URL
- User pastes a YouTube or Instagram video link
- Clicks **"Download this video"**

### Step 2: Fetch Formats (`list_formats.py`)
- Runs `yt-dlp -F` on the URL to get all available formats
- Parses and intelligently filters formats:
  - Video formats (video + audio combined, or video-only)
  - Audio-only formats (for MP3 extraction)
- **Resolution rule**: The highest native resolution is detected — no upscaling options are offered (can't download a 4K video as 8K)
- Displays each format with:
  - Format code
  - Resolution (e.g. 1920x1080)
  - File size (estimated)
  - Codec info
  - Note if it's video-only (needs separate audio merge)

### Step 3: User Selects Format
- User picks from the list
- The tool downloads to `~/Downloads/YT + IG Downloader/<filename>`

### Step 4: Download (`download_video.py`)
- Downloads the selected format using yt-dlp
- For video-only formats, automatically merges with best audio
- Shows progress during download
- Saves to the configured output folder

## Edge Cases & Handling

| Edge Case | Handling |
|-----------|----------|
| Invalid URL | Return error: "Not a valid YouTube or Instagram URL" |
| Private/deleted video | Return error from yt-dlp |
| No internet | Connection timeout with clear message |
| Format size unknown | Show "Size unknown" for formats where yt-dlp can't estimate |
| Instagram Reel vs Post | Both work — yt-dlp handles Instagram URLs uniformly |
| Very large files (>2GB) | Warn user before starting download |
| Download cancelled mid-way | Partial file remains in .tmp/ — cleaned on next run |

## Output
- Downloaded files go to `~/Downloads/YT + IG Downloader/`
- Files follow yt-dlp's default naming (`<title>_<id>.<ext>`)
