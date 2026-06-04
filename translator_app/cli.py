from __future__ import annotations

import argparse
from pathlib import Path

from translator_app.config import load_config
from translator_app.cuda import configure_cuda_dll_paths
from translator_app.events import JobOptions
from translator_app.job import SubtitleJob


def main() -> int:
    configure_cuda_dll_paths()
    parser = argparse.ArgumentParser(description="Run a subtitle translation job from the command line.")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--language", default=None, help="Target language")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    parser.add_argument("--model-dir", default=None, help="Model directory")
    parser.add_argument("--speech-model", default=None, help="Speech model key")
    parser.add_argument("--gemma-model", default=None, help="Gemma/Ollama model name")
    parser.add_argument("--download-video", action="store_true", help="Download video instead of audio only")
    parser.add_argument("--no-auto-download", action="store_true", help="Disable automatic model preparation")
    parser.add_argument("--cpu", action="store_true", help="Force CPU mode")
    args = parser.parse_args()

    config = load_config()

    def progress(stage: str, value: int, message: str) -> None:
        safe_message = message.encode("ascii", errors="backslashreplace").decode("ascii")
        print(f"[{stage:13}] {value:3d}% {safe_message}", flush=True)

    options = JobOptions(
        url=args.url,
        target_language=args.language or config.target_language,
        subtitle_format=config.subtitle_format,
        speech_model=args.speech_model or config.speech_model,
        gemma_model=args.gemma_model or config.gemma_model,
        output_dir=Path(args.output_dir or config.output_dir),
        model_dir=Path(args.model_dir or config.model_dir),
        download_video=args.download_video,
        video_quality="best",
        auto_download_models=not args.no_auto_download and config.auto_download_models,
        use_gpu=not args.cpu and config.use_gpu,
        chunk_minutes=config.chunk_minutes,
        max_tokens=config.max_tokens,
        ollama_url=config.ollama_url,
    )
    result = SubtitleJob(options, progress).run()
    print("\nCompleted")
    print(f"Output: {result.output_dir}")
    print(f"Source subtitle: {result.source_subtitle}")
    print(f"Translated subtitle: {result.translated_subtitle}")
    print(f"Media file: {result.media_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
