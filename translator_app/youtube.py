from __future__ import annotations

import shutil
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

        safe_title = safe_filename(title)
        job_dir = ensure_dir(self.output_root / safe_title)
        if download_video:
            format_selector = self._format_for_quality(quality)
            output_template = str(job_dir / f"{safe_title}.%(ext)s")
            options = {
                "format": format_selector,
                "outtmpl": output_template,
                "noplaylist": True,
                "quiet": True,
                "merge_output_format": "mp4",
                "overwrites": True,
            }
            ffmpeg_location = self._ffmpeg_location()
            if ffmpeg_location:
                options["ffmpeg_location"] = ffmpeg_location
        else:
            output_template = str(job_dir / f"{safe_title}.audio.%(ext)s")
            options = {
                "format": "bestaudio/best",
                "outtmpl": output_template,
                "noplaylist": True,
                "quiet": True,
                "overwrites": True,
            }

        with YoutubeDL(options) as ydl:
            ydl.download([url])

        preferred = job_dir / (f"{safe_title}.mp4" if download_video else f"{safe_title}.audio.wav")
        if preferred.exists():
            return preferred

        candidates = sorted(job_dir.glob(f"{safe_title}.*" if download_video else f"{safe_title}.audio.*"))
        if candidates:
            return candidates[0]
        raise RuntimeError("Downloaded file was not found.")

    @staticmethod
    def _format_for_quality(quality: str) -> str:
        if quality == "2160p":
            return YouTubeClient._merged_format(2160)
        if quality == "1440p":
            return YouTubeClient._merged_format(1440)
        if quality == "1080p":
            return YouTubeClient._merged_format(1080)
        if quality == "720p":
            return YouTubeClient._merged_format(720)
        return (
            "bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/"
            "bestvideo[ext=mp4]+bestaudio/"
            "bestvideo+bestaudio/best"
        )

    @staticmethod
    def _merged_format(max_height: int) -> str:
        return (
            f"bestvideo[height<={max_height}][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={max_height}][ext=mp4]+bestaudio/"
            f"bestvideo[height<={max_height}]+bestaudio/"
            f"best[height<={max_height}]/best"
        )

    @staticmethod
    def _ffmpeg_location() -> str | None:
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            return system_ffmpeg
        try:
            import imageio_ffmpeg

            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return None
