import os
import re
import asyncio
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
    match = TIKTOK_VIDEO_RE.search(text)
    if match:
        return match.group(0)
    short = re.search(
        r"https?://(?:vm\.|vt\.)?tiktok\.com/\S+", text, re.IGNORECASE
    )
    if short:
        return short.group(0).rstrip(".,;)")
    return None


def expand_short_url(url: str) -> str:
    """
    Expand a short TikTok URL to a full video URL by following redirects
    one step at a time, stopping as soon as we see '/video/' in the path.
    """
    current = url
    for _ in range(8):
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
            if location.startswith("/"):
                from urllib.parse import urlparse
                parsed = urlparse(current)
                location = f"{parsed.scheme}://{parsed.netloc}{location}"
            if "/video/" in location:
                return location
            if "/about" in location or "/login" in location:
                break
            current = location
        except Exception:
            break
    return current


def _download_file(dl_url: str, dest_path: str) -> bool:
    """Stream-download a file from dl_url to dest_path. Returns True on success."""
    try:
        with requests.get(dl_url, headers=BROWSER_HEADERS, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)
        return os.path.exists(dest_path) and os.path.getsize(dest_path) > 10_000
    except Exception:
        return False


def _via_tikwm(url: str) -> dict:
    """
    Primary download strategy: tikwm.com public API.
    Returns a result dict compatible with download_tiktok().
    """
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    try:
        r = requests.post(
            "https://www.tikwm.com/api/",
            data={"url": url, "hd": 1},
            headers={"User-Agent": BROWSER_HEADERS["User-Agent"]},
            timeout=20,
        )
        resp = r.json()
        if resp.get("code") != 0:
            return {"success": False, "error": f"tikwm API: {resp.get('msg', 'unknown error')}"}

        data = resp["data"]
        video_id = data.get("id", "tiktok")
        # Prefer HD (no watermark), fall back to normal play (also no watermark)
        dl_url = data.get("hdplay") or data.get("play")
        if not dl_url:
            return {"success": False, "error": "No download URL returned by API"}

        dest_path = os.path.join(DOWNLOADS_DIR, f"{video_id}.mp4")
        if not _download_file(dl_url, dest_path):
            # retry with normal play URL if HD failed
            if data.get("play") and dl_url != data["play"]:
                dl_url = data["play"]
                if not _download_file(dl_url, dest_path):
                    return {"success": False, "error": "Failed to download video file"}
            else:
                return {"success": False, "error": "Failed to download video file"}

        author_info = data.get("author", {})
        return {
            "success": True,
            "path": dest_path,
            "title": data.get("title") or data.get("content_desc") or "TikTok Video",
            "author": author_info.get("nickname") or author_info.get("unique_id") or "Unknown",
            "duration": data.get("duration", 0),
            "views": data.get("play_count", 0),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _via_ytdlp(url: str) -> dict:
    """
    Fallback download strategy: yt-dlp with API extractor args.
    """
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
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
                "app_name": "musical_ly",
                "app_version": "35.1.2",
                "manifest_app_version": "2023501020",
            }
        },
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        video_id = info.get("id", "video")
        ext = info.get("ext", "mp4")
        file_path = os.path.join(DOWNLOADS_DIR, f"{video_id}.{ext}")
        if not os.path.exists(file_path):
            for f in os.listdir(DOWNLOADS_DIR):
                if f.startswith(video_id):
                    file_path = os.path.join(DOWNLOADS_DIR, f)
                    break

        if not os.path.exists(file_path):
            return {"success": False, "error": "File not saved after yt-dlp download."}

        return {
            "success": True,
            "path": file_path,
            "title": info.get("title", "TikTok Video"),
            "author": info.get("uploader", "Unknown"),
            "duration": info.get("duration", 0),
            "views": info.get("view_count", 0),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def download_tiktok(url: str) -> dict:
    """
    Download TikTok video without watermark.
    Strategy: tikwm API → yt-dlp fallback.
    Returns dict with path/metadata or error.
    """
    # Expand short URLs before anything else
    if "vm.tiktok.com" in url or "vt.tiktok.com" in url:
        expanded = expand_short_url(url)
        if "/video/" in expanded:
            url = expanded

    loop = asyncio.get_event_loop()

    # 1. Try tikwm API (fastest, most reliable)
    result = await loop.run_in_executor(None, _via_tikwm, url)
    if result["success"]:
        return result

    # 2. Fall back to yt-dlp
    result2 = await loop.run_in_executor(None, _via_ytdlp, url)
    if result2["success"]:
        return result2

    # Both failed — return the primary error message
    return {"success": False, "error": result.get("error", result2.get("error", "Download failed"))}


def cleanup_file(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
