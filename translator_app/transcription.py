from __future__ import annotations

from pathlib import Path

from translator_app.cuda import configure_cuda_dll_paths
from translator_app.subtitle import SubtitleBlock, write_srt


class Transcriber:
    def __init__(self, model_key: str, use_gpu: bool, model_dir: Path | None = None):
        self.model_key = model_key
        self.use_gpu = use_gpu
        self.model_dir = model_dir

    def transcribe(self, media_path: Path, output_path: Path, progress) -> list[SubtitleBlock]:
        try:
            return self._transcribe_with_faster_whisper(media_path, output_path, progress)
        except ImportError:
            progress(
                "Transcription",
                10,
                "faster-whisper is not installed. Creating a placeholder subtitle for workflow testing.",
            )
            return self._placeholder(media_path, output_path)

    def _transcribe_with_faster_whisper(self, media_path: Path, output_path: Path, progress) -> list[SubtitleBlock]:
        cuda_paths = configure_cuda_dll_paths()
        if self.use_gpu and cuda_paths:
            progress("Transcription", 12, f"Registered CUDA DLL paths: {len(cuda_paths)}.")
        from faster_whisper import WhisperModel

        model_size = self.model_key.replace("faster-whisper-", "")
        if self.use_gpu:
            try:
                return self._run_faster_whisper(media_path, output_path, progress, WhisperModel, model_size, "cuda", "float16")
            except Exception as exc:
                progress(
                    "Transcription",
                    15,
                    f"GPU transcription failed ({exc}). Retrying on CPU.",
                )
        return self._run_faster_whisper(media_path, output_path, progress, WhisperModel, model_size, "cpu", "int8")

    def _run_faster_whisper(
        self,
        media_path: Path,
        output_path: Path,
        progress,
        whisper_model_class,
        model_size: str,
        device: str,
        compute_type: str,
    ) -> list[SubtitleBlock]:
        progress("Transcription", 15, f"Loading {model_size} speech model on {device}.")
        model = whisper_model_class(
            model_size,
            device=device,
            compute_type=compute_type,
            download_root=str(self.model_dir) if self.model_dir else None,
        )
        segments, info = model.transcribe(str(media_path), vad_filter=True)
        progress("Transcription", 25, f"Detected language: {getattr(info, 'language', 'unknown')}.")
        blocks: list[SubtitleBlock] = []
        for index, segment in enumerate(segments, start=1):
            blocks.append(
                SubtitleBlock(
                    index=index,
                    start=float(segment.start),
                    end=float(segment.end),
                    text=segment.text.strip(),
                )
            )
            if index % 5 == 0:
                progress("Transcription", min(90, 25 + index), f"Transcribed {index} subtitle blocks.")
        write_srt(output_path, blocks)
        progress("Transcription", 100, f"Source subtitle saved: {output_path}")
        return blocks

    @staticmethod
    def _placeholder(media_path: Path, output_path: Path) -> list[SubtitleBlock]:
        blocks = [
            SubtitleBlock(
                index=1,
                start=0,
                end=5,
                text=f"Placeholder transcript for {media_path.name}. Install faster-whisper for real transcription.",
            )
        ]
        write_srt(output_path, blocks)
        return blocks
