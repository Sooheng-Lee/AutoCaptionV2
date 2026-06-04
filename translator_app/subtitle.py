from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class SubtitleBlock:
    index: int
    start: float
    end: float
    text: str


def format_timestamp(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, rem = divmod(millis, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def parse_timestamp(value: str) -> float:
    value = value.strip().replace(".", ",")
    clock, ms = value.split(",")
    hours, minutes, seconds = [int(part) for part in clock.split(":")]
    return hours * 3600 + minutes * 60 + seconds + int(ms) / 1000


def blocks_to_srt(blocks: list[SubtitleBlock]) -> str:
    parts: list[str] = []
    for idx, block in enumerate(blocks, start=1):
        parts.append(str(idx))
        parts.append(f"{format_timestamp(block.start)} --> {format_timestamp(block.end)}")
        parts.append(block.text.strip() or " ")
        parts.append("")
    return "\n".join(parts)


def write_srt(path: Path, blocks: list[SubtitleBlock]) -> None:
    path.write_text(blocks_to_srt(blocks), encoding="utf-8")


def parse_srt(text: str) -> list[SubtitleBlock]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    blocks: list[SubtitleBlock] = []
    for raw in normalized.split("\n\n"):
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        index = int(lines[0]) if lines[0].isdigit() else len(blocks) + 1
        start_raw, end_raw = [part.strip() for part in lines[1].split("-->", 1)]
        blocks.append(
            SubtitleBlock(
                index=index,
                start=parse_timestamp(start_raw),
                end=parse_timestamp(end_raw),
                text="\n".join(lines[2:]),
            )
        )
    return blocks


def chunk_blocks(
    blocks: list[SubtitleBlock],
    chunk_minutes: int,
    max_chars: int,
) -> list[list[SubtitleBlock]]:
    if not blocks:
        return []
    chunks: list[list[SubtitleBlock]] = []
    current: list[SubtitleBlock] = []
    start_at = blocks[0].start
    char_count = 0
    max_seconds = max(1, chunk_minutes) * 60

    for block in blocks:
        next_chars = char_count + len(block.text)
        too_long = block.end - start_at >= max_seconds
        too_many_chars = next_chars >= max_chars
        if current and (too_long or too_many_chars):
            chunks.append(current)
            current = []
            start_at = block.start
            char_count = 0
        current.append(block)
        char_count += len(block.text)

    if current:
        chunks.append(current)
    return chunks

