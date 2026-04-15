import os
import asyncio
import yt_dlp
from config import DOWNLOADS_DIR


async def download_tiktok(url: str) -> dict:
    """Download TikTok video without watermark. Returns dict with path or error."""
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    output_template = os.path.join(DOWNLOADS_DIR, "%(id)s.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        "format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "postprocessors": [],
        # Remove watermark by using the no-watermark source
        "extractor_args": {
            "tiktok": {
                "webpage_download": True,
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
            # Try finding any file with video_id
            for f in os.listdir(DOWNLOADS_DIR):
                if f.startswith(video_id):
                    file_path = os.path.join(DOWNLOADS_DIR, f)
                    break

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
