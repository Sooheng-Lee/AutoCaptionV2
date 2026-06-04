from __future__ import annotations

import json
import time
from pathlib import Path

import requests

from translator_app.subtitle import SubtitleBlock, chunk_blocks, parse_srt, write_srt


class Translator:
    max_blocks_per_request = 15

    def __init__(self, model_name: str, target_language: str, ollama_url: str):
        self.model_name = model_name
        self.target_language = target_language
        self.ollama_url = ollama_url

    def translate(
        self,
        blocks: list[SubtitleBlock],
        output_path: Path,
        chunk_minutes: int,
        max_tokens: int,
        progress,
    ) -> list[SubtitleBlock]:
        partial_path = output_path.with_suffix(f".partial{output_path.suffix}")
        translated: list[SubtitleBlock] = []
        if partial_path.exists():
            translated = parse_srt(partial_path.read_text(encoding="utf-8"))
            if translated:
                progress(
                    "Translation",
                    0,
                    f"Resuming from partial translation at block {len(translated) + 1}.",
                )

        remaining_blocks = blocks[len(translated) :]
        chunks = self._make_translation_chunks(remaining_blocks, chunk_minutes, max_tokens)
        if not blocks:
            write_srt(output_path, [])
            return []
        if not chunks:
            for index, block in enumerate(translated, start=1):
                block.index = index
            write_srt(output_path, translated)
            partial_path.unlink(missing_ok=True)
            progress("Translation", 100, f"Translated subtitle saved: {output_path}")
            return translated

        for idx, chunk in enumerate(chunks, start=1):
            percent = int((len(translated) / len(blocks)) * 90)
            progress("Translation", percent, f"Translating chunk {idx}/{len(chunks)}.")
            translated.extend(self._translate_chunk_with_retry(chunk, progress))
            write_srt(partial_path, translated)

        for index, block in enumerate(translated, start=1):
            block.index = index
        write_srt(output_path, translated)
        partial_path.unlink(missing_ok=True)
        progress("Translation", 100, f"Translated subtitle saved: {output_path}")
        return translated

    def _make_translation_chunks(
        self,
        blocks: list[SubtitleBlock],
        chunk_minutes: int,
        max_tokens: int,
    ) -> list[list[SubtitleBlock]]:
        max_chars = max(1000, max_tokens * 3)
        time_chunks = chunk_blocks(blocks, chunk_minutes=chunk_minutes, max_chars=max_chars)
        chunks: list[list[SubtitleBlock]] = []
        for time_chunk in time_chunks:
            for start in range(0, len(time_chunk), self.max_blocks_per_request):
                chunks.append(time_chunk[start : start + self.max_blocks_per_request])
        return chunks

    def _translate_chunk_with_retry(self, blocks: list[SubtitleBlock], progress) -> list[SubtitleBlock]:
        try:
            return self._translate_chunk(blocks)
        except Exception as exc:
            if len(blocks) <= 1:
                raise RuntimeError(f"Translation failed for subtitle block {blocks[0].index}: {exc}") from exc
            midpoint = len(blocks) // 2
            progress(
                "Translation",
                50,
                f"Chunk failed validation. Retrying as {midpoint} + {len(blocks) - midpoint} blocks.",
            )
            return self._translate_chunk_with_retry(blocks[:midpoint], progress) + self._translate_chunk_with_retry(
                blocks[midpoint:], progress
            )

    def _translate_chunk(self, blocks: list[SubtitleBlock]) -> list[SubtitleBlock]:
        translated_text = self._call_ollama(blocks)
        parsed = parse_srt(translated_text)
        if len(parsed) != len(blocks):
            raise RuntimeError(f"Expected {len(blocks)} translated blocks, got {len(parsed)}.")
        return [
            SubtitleBlock(
                index=source.index,
                start=source.start,
                end=source.end,
                text=target.text,
            )
            for source, target in zip(blocks, parsed)
        ]

    def _call_ollama(self, blocks: list[SubtitleBlock]) -> str:
        from translator_app.subtitle import blocks_to_srt

        prompt = (
            "You are a professional subtitle translator.\n"
            f"Translate the subtitle text into {self.target_language}.\n"
            "Preserve subtitle numbering and timestamps exactly.\n"
            "Do not merge, split, remove, or reorder subtitle blocks.\n"
            "Keep the translation concise and natural for subtitles.\n"
            "Return only valid SRT content.\n\n"
            f"{blocks_to_srt(blocks)}"
        )
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                response = requests.post(
                    self.ollama_url,
                    json={"model": self.model_name, "prompt": prompt, "stream": False},
                    timeout=600,
                )
                response.raise_for_status()
                payload = response.json()
                return str(payload.get("response", "")).strip()
            except requests.RequestException as exc:
                last_error = exc
                time.sleep(attempt * 3)
        raise RuntimeError(f"Ollama request failed after 3 attempts: {last_error}")
