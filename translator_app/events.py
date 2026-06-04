from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


ProgressCallback = Callable[[str, int, str], None]


@dataclass
class JobOptions:
    url: str
    target_language: str
    subtitle_format: str
    speech_model: str
    gemma_model: str
    output_dir: Path
    model_dir: Path
    download_video: bool = False
    video_quality: str = "best"
    auto_download_models: bool = True
    use_gpu: bool = True
    chunk_minutes: int = 8
    max_tokens: int = 6000
    ollama_url: str = "http://localhost:11434/api/generate"


@dataclass
class JobResult:
    output_dir: Path
    source_subtitle: Path | None = None
    translated_subtitle: Path | None = None
    media_file: Path | None = None
    metadata: dict = field(default_factory=dict)

