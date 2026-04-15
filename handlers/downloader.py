import os
import asyncio
import re
import requests
import yt_dlp
from config import DOWNLOADS_DIR

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.tiktok.com/",
}

TIKTOK_VIDEO_RE = re.compile(
    r"https?://(?:www\.)?tiktok\.com/@[\w.]+/video/\d+", re.IGNORECASE
)


def extract_tiktok_url(text: str) -> str | None:
    """Extract the first TikTok URL found in a block of text."""
    # Match full video URLs first
    match = TIKTOK_VIDEO_RE.search(text)
    if match:
        return match.group(0)
    # Match any tiktok.com or vm/vt short links
    short = re.search(
        r"https?://(?:vm\.|vt\.)?tiktok\.com/\S+", text, re.IGNORECASE
    )
    if short:
        url = short.group(0).rstrip(".,;)")
        return url
    return None


def expand_short_url(url: str) -> str:
    """
    Expand a short TikTok URL to a full video URL by following redirects
    one step at a time.  We stop as soon as we get a URL that contains
    '/video/' so we never land on a geo-redirect page like /in/about.
    """
    current = url
    for _ in range(8):  # max 8 hops
        try:
            r = requests.head(
                current,
                headers=BROWSER_HEADERS,
                allow_redirects=False,
                timeout=10,
            )
            location = r.headers.get("Location", "")
            if not location:
                break
            # Make sure relative redirects are handled
            if location.startswith("/"):
                from urllib.parse import urlparse
                parsed = urlparse(current)
                location = f"{parsed.scheme}://{parsed.netloc}{location}"
            # If we already have a proper video URL, stop here
            if "/video/" in location:
                return location
            # Stop if TikTok is sending us to a geo/about page
            if "/about" in location or "/login" in location:
                break
            current = location
        except Exception:
            break
    return current


async def download_tiktok(url: str) -> dict:
    """Download TikTok video without watermark. Returns dict with path or error."""
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)

    # Expand short URLs before handing off to yt-dlp
    if "vm.tiktok.com" in url or "vt.tiktok.com" in url:
        expanded = expand_short_url(url)
        if "/video/" in expanded:
            url = expanded

    output_template = os.path.join(DOWNLOADS_DIR, "%(id)s.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "http_headers": BROWSER_HEADERS,
        "extractor_args": {
            "tiktok": {
                "app_name": "trill",
                "app_version": "34.1.2",
            }
        },
    }

    try:
        loop = asyncio.get_event_loop()

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info

        info = await loop.run_in_executor(None, _download)

        video_id = info.get("id", "video")
        ext = info.get("ext", "mp4")
        file_path = os.path.join(DOWNLOADS_DIR, f"{video_id}.{ext}")

        if not os.path.exists(file_path):
            # Try finding any file with video_id prefix
            for f in os.listdir(DOWNLOADS_DIR):
                if f.startswith(video_id):
                    file_path = os.path.join(DOWNLOADS_DIR, f)
                    break

        if not os.path.exists(file_path):
            return {"success": False, "error": "File was not saved after download."}

        title = info.get("title", "TikTok Video")
        author = info.get("uploader", "Unknown")
        duration = info.get("duration", 0)
        views = info.get("view_count", 0)

        return {
            "success": True,
            "path": file_path,
            "title": title,
            "author": author,
            "duration": duration,
            "views": views,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def cleanup_file(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
