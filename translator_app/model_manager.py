from __future__ import annotations

import hashlib
import importlib.util
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests

from translator_app.storage import ensure_dir


@dataclass
class ModelSpec:
    key: str
    label: str
    kind: str
    size_hint: str
    path_name: str
    url: str | None = None
    sha256: str | None = None
    ollama_model: str | None = None


SPEECH_MODELS = {
    "faster-whisper-tiny": ModelSpec(
        key="faster-whisper-tiny",
        label="Faster Whisper Tiny",
        kind="speech",
        size_hint="~75 MB, downloaded by faster-whisper on first use",
        path_name="speech/faster-whisper-tiny",
    ),
    "faster-whisper-small": ModelSpec(
        key="faster-whisper-small",
        label="Faster Whisper Small",
        kind="speech",
        size_hint="~460 MB, downloaded by faster-whisper on first use",
        path_name="speech/faster-whisper-small",
    ),
}


def gemma_spec(model_name: str) -> ModelSpec:
    return ModelSpec(
        key=model_name,
        label=f"Gemma model ({model_name})",
        kind="translation",
        size_hint="Depends on selected Ollama model",
        path_name=f"gemma4/{model_name}",
        ollama_model=model_name,
    )


class ModelManager:
    def __init__(self, model_root: Path):
        self.model_root = ensure_dir(model_root)

    def speech_spec(self, key: str) -> ModelSpec:
        return SPEECH_MODELS.get(key, SPEECH_MODELS["faster-whisper-small"])

    def is_available(self, spec: ModelSpec) -> bool:
        marker = self.model_root / spec.path_name / ".ready"
        if spec.kind == "speech":
            return marker.exists() and importlib.util.find_spec("faster_whisper") is not None
        if marker.exists():
            return True
        if spec.ollama_model:
            return self._ollama_has_model(spec.ollama_model)
        return False

    def ensure_model(self, spec: ModelSpec, auto_download: bool, progress) -> Path:
        model_dir = ensure_dir(self.model_root / spec.path_name)
        marker = model_dir / ".ready"
        if self.is_available(spec):
            marker.touch(exist_ok=True)
            progress("Model", 100, f"{spec.label} is ready.")
            return model_dir
        if not auto_download:
            raise RuntimeError(f"{spec.label} is missing. Enable auto-download or set a model path.")

        progress("Model", 5, f"Preparing {spec.label} ({spec.size_hint}).")
        if spec.ollama_model:
            if not shutil.which("ollama"):
                progress(
                    "Model",
                    100,
                    "Ollama is not installed. The app will use translation fallback until Gemma runtime is configured.",
                )
                return model_dir
            self._pull_ollama_model(spec.ollama_model, progress)
        elif spec.url:
            self._download_file(spec, model_dir, progress)
        elif spec.kind == "speech":
            self._ensure_speech_runtime(progress)
        else:
            marker.write_text(
                "This marker allows faster-whisper to download/cache the model during transcription.\n",
                encoding="utf-8",
            )
        marker.touch(exist_ok=True)
        progress("Model", 100, f"{spec.label} is ready.")
        return model_dir

    def _download_file(self, spec: ModelSpec, model_dir: Path, progress) -> None:
        assert spec.url
        filename = Path(urlparse(spec.url).path).name or "model.bin"
        target = model_dir / filename
        temp = model_dir / f"{filename}.part"
        response = requests.get(spec.url, stream=True, timeout=30)
        response.raise_for_status()
        total = int(response.headers.get("content-length", "0"))
        read = 0
        with temp.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                handle.write(chunk)
                read += len(chunk)
                if total:
                    progress("Model", int(read / total * 90), f"Downloading {spec.label}")
        temp.replace(target)
        if spec.sha256 and self._sha256(target) != spec.sha256:
            target.unlink(missing_ok=True)
            raise RuntimeError(f"{spec.label} checksum verification failed.")

    def _ollama_has_model(self, model_name: str) -> bool:
        if not shutil.which("ollama"):
            return False
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except Exception:
            return False
        return model_name in result.stdout

    def _pull_ollama_model(self, model_name: str, progress) -> None:
        if not shutil.which("ollama"):
            raise RuntimeError("Ollama is not installed or not in PATH. Install Ollama or set a manual Gemma runtime.")
        progress("Model", 10, f"Running `ollama pull {model_name}`.")
        process = subprocess.Popen(
            ["ollama", "pull", model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        assert process.stdout
        for raw_line in process.stdout:
            line = _decode_process_output(raw_line).strip()
            progress("Model", 50, line or f"Pulling {model_name}")
        code = process.wait()
        if code != 0:
            raise RuntimeError(f"`ollama pull {model_name}` failed with exit code {code}.")

    def _ensure_speech_runtime(self, progress) -> None:
        if importlib.util.find_spec("faster_whisper"):
            progress("Model", 80, "faster-whisper runtime is installed.")
            return

        progress("Model", 20, "Installing faster-whisper runtime for speech recognition.")
        process = subprocess.Popen(
            [sys.executable, "-m", "pip", "install", "faster-whisper"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        assert process.stdout
        for raw_line in process.stdout:
            line = _decode_process_output(raw_line).strip()
            if line:
                progress("Model", 50, line)
        code = process.wait()
        if code != 0:
            raise RuntimeError(
                "`pip install faster-whisper` failed. Run `setup.bat --with-whisper` or check network access."
            )
        progress("Model", 90, "faster-whisper runtime installed.")

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()


def _decode_process_output(value: bytes) -> str:
    for encoding in ("utf-8", "cp949", "mbcs"):
        try:
            return value.decode(encoding)
        except UnicodeDecodeError:
            continue
    return value.decode("utf-8", errors="replace")
