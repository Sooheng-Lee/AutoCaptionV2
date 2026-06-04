from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir


APP_NAME = "YouTubeSubtitleTranslator"


@dataclass
class AppConfig:
    output_dir: str
    model_dir: str
    target_language: str = "Korean"
    subtitle_format: str = "srt"
    speech_model: str = "faster-whisper-small"
    gemma_model: str = "gemma4"
    auto_download_models: bool = True
    confirm_model_download: bool = True
    use_gpu: bool = False
    chunk_minutes: int = 8
    max_tokens: int = 6000
    keep_temp_files: bool = True
    ollama_url: str = "http://localhost:11434/api/generate"


def default_config() -> AppConfig:
    data_dir = _writable_dir(Path(user_data_dir(APP_NAME)), Path.cwd() / ".appdata")
    return AppConfig(
        output_dir=str(data_dir / "outputs"),
        model_dir=str(data_dir / "models"),
    )


def config_path() -> Path:
    path = _writable_dir(Path(user_config_dir(APP_NAME)), Path.cwd() / ".appdata" / "config")
    return path / "config.json"


def _writable_dir(preferred: Path, fallback: Path) -> Path:
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        probe = preferred / ".write-test"
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return preferred
    except OSError:
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def load_config() -> AppConfig:
    path = config_path()
    if not path.exists():
        cfg = default_config()
        save_config(cfg)
        return cfg

    raw = json.loads(path.read_text(encoding="utf-8"))
    base = asdict(default_config())
    base.update(raw)
    return AppConfig(**base)


def save_config(config: AppConfig) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
