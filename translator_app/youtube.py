from __future__ import annotations

from pathlib import Path

from translator_app.storage import ensure_dir, safe_filename


def validate_youtube_url(url: str) -> bool:
    lowered = url.strip().lower()
    return "youtube.com/watch" in lowered or "youtu.be/" in lowered


class YouTubeClient:
    def __init__(self, output_root: Path):
        self.output_root = ensure_dir(output_root)

    def fetch_metadata(self, url: str) -> dict:
        try:
            from yt_dlp import YoutubeDL
        except ImportError as exc:
            raise RuntimeError("yt-dlp is not installed. Run `pip install -r requirements.txt`.") from exc

        options = {"quiet": True, "skip_download": True, "noplaylist": True}
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            raise RuntimeError("Could not read YouTube metadata.")
        return {
            "id": info.get("id") or "unknown",
            "title": info.get("title") or "youtube-video",
            "channel": info.get("channel") or info.get("uploader") or "",
            "duration": info.get("duration") or 0,
            "webpage_url": info.get("webpage_url") or url,
            "subtitles": bool(info.get("subtitles") or info.get("automatic_captions")),
        }

    def download(self, url: str, title: str, download_video: bool, quality: str) -> Path:
        try:
            from yt_dlp import YoutubeDL
        except ImportError as exc:
            raise RuntimeError("yt-dlp is not installed. Run `pip install -r requirements.txt`.") from exc

        job_dir = ensure_dir(self.output_root / safe_filename(title))
        if download_video:
            format_selector = self._format_for_quality(quality)
            output_template = str(job_dir / "video.%(ext)s")
            options = {
                "format": format_selector,
                "outtmpl": output_template,
                "noplaylist": True,
                "quiet": True,
                "merge_output_format": "mp4",
            }
        else:
            output_template = str(job_dir / "audio.%(ext)s")
            options = {
                "format": "bestaudio/best",
                "outtmpl": output_template,
                "noplaylist": True,
                "quiet": True,
            }

        with YoutubeDL(options) as ydl:
            ydl.download([url])

        preferred = job_dir / ("video.mp4" if download_video else "audio.wav")
        if preferred.exists():
            return preferred

        candidates = sorted(job_dir.glob("video.*" if download_video else "audio.*"))
        if candidates:
            return candidates[0]
        raise RuntimeError("Downloaded file was not found.")

    @staticmethod
    def _format_for_quality(quality: str) -> str:
        if quality == "1080p":
            return "best[ext=mp4][height<=1080]/best[height<=1080]/bestvideo[height<=1080]+bestaudio/best"
        if quality == "720p":
            return "best[ext=mp4][height<=720]/best[height<=720]/bestvideo[height<=720]+bestaudio/best"
        return "best[ext=mp4]/best/bestvideo+bestaudio"
