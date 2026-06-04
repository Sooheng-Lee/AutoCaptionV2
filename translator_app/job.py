from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from translator_app.events import JobOptions, JobResult
from translator_app.model_manager import ModelManager, gemma_spec
from translator_app.storage import ensure_dir, safe_filename
from translator_app.transcription import Transcriber
from translator_app.translation import Translator
from translator_app.youtube import YouTubeClient, validate_youtube_url


class SubtitleJob:
    def __init__(self, options: JobOptions, progress):
        self.options = options
        self.progress = progress

    def run(self) -> JobResult:
        if not validate_youtube_url(self.options.url):
            raise RuntimeError("Invalid YouTube URL.")

        self.progress("Metadata", 5, "Reading YouTube metadata.")
        youtube = YouTubeClient(self.options.output_dir)
        metadata = youtube.fetch_metadata(self.options.url)
        title = safe_filename(metadata["title"])
        job_dir = ensure_dir(self.options.output_dir / title)

        manager = ModelManager(self.options.model_dir)
        speech_spec = manager.speech_spec(self.options.speech_model)
        speech_model_dir = manager.ensure_model(speech_spec, self.options.auto_download_models, self.progress)
        manager.ensure_model(gemma_spec(self.options.gemma_model), self.options.auto_download_models, self.progress)

        self.progress("Download", 10, "Downloading media.")
        media = youtube.download(
            self.options.url,
            metadata["title"],
            self.options.download_video,
            self.options.video_quality,
        )

        source_path = job_dir / "source.srt"
        translated_path = job_dir / f"{self.options.target_language.lower()}.srt"
        transcriber = Transcriber(self.options.speech_model, self.options.use_gpu, speech_model_dir)
        blocks = transcriber.transcribe(media, source_path, self.progress)

        translator = Translator(
            model_name=self.options.gemma_model,
            target_language=self.options.target_language,
            ollama_url=self.options.ollama_url,
        )
        translator.translate(
            blocks,
            translated_path,
            chunk_minutes=self.options.chunk_minutes,
            max_tokens=self.options.max_tokens,
            progress=self.progress,
        )

        job_state = {
            "url": self.options.url,
            "video_id": metadata.get("id"),
            "title": metadata.get("title"),
            "target_language": self.options.target_language,
            "speech_model": self.options.speech_model,
            "gemma_model": self.options.gemma_model,
            "source_subtitle": str(source_path),
            "translated_subtitle": str(translated_path),
            "media_file": str(media),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        (job_dir / "job.json").write_text(json.dumps(job_state, ensure_ascii=False, indent=2), encoding="utf-8")
        return JobResult(
            output_dir=job_dir,
            source_subtitle=source_path,
            translated_subtitle=translated_path,
            media_file=media,
            metadata=metadata,
        )
