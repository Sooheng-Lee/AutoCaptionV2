# YouTube Subtitle Translator

Python + PyQt6 desktop application that downloads YouTube audio/video, creates source subtitles with an open-source speech recognition backend, and translates subtitles with a local Gemma-compatible runtime.

## Quick Start

```powershell
.\setup.bat
.\run_app.bat
```

For real speech recognition, install `faster-whisper` separately:

```powershell
.\setup.bat --with-whisper
```

For Gemma translation, configure an Ollama model name in the app settings. The default model name is `gemma4`, and the app can run `ollama pull <model>` when auto-download is enabled.

To ask setup to pull the default Gemma model through Ollama:

```powershell
.\setup.bat --pull-gemma
```

For GPU transcription on Windows, install CUDA DLL wheels into the virtual environment:

```powershell
.\setup.bat --with-cuda
```

To run the provided test video from the command line:

```powershell
.\test_video.bat
```

## Video Preview

The app can download a video file and preview it with the translated SRT synchronized below the video.

- Use `Download Video Only` to download a playable video without running transcription.
- Enable `Download video file` before `Create Subtitles` when you want preview output from the same job.
- Use `Preview Subtitles` after both a video file and translated `.srt` exist in the result folder.

## Notes

- YouTube downloading uses `yt-dlp`.
- Speech model files are checked under the configured model directory.
- If `faster-whisper` is not installed, the app creates a small placeholder source subtitle so the rest of the workflow can still be tested.
- If Ollama or the configured Gemma model is unavailable, translation falls back to preserving subtitle timing and prefixing text with the target language label.
- GPU transcription is optional. If CUDA libraries such as `cublas64_12.dll` are missing, disable `Use GPU when available` in Settings or keep the default CPU mode.
