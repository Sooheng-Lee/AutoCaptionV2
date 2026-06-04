from __future__ import annotations

import os
import site
from pathlib import Path


def configure_cuda_dll_paths() -> list[Path]:
    """Expose CUDA DLLs installed from NVIDIA Python wheels on Windows."""
    if os.name != "nt":
        return []

    added: list[Path] = []
    candidates: list[Path] = []
    for package_root in site.getsitepackages():
        root = Path(package_root)
        candidates.extend(
            [
                root / "nvidia" / "cublas" / "bin",
                root / "nvidia" / "cudnn" / "bin",
                root / "nvidia" / "cuda_nvrtc" / "bin",
                root / "ctranslate2",
            ]
        )

    path_parts = os.environ.get("PATH", "").split(os.pathsep)
    for candidate in candidates:
        if not candidate.exists():
            continue
        candidate_text = str(candidate)
        if candidate_text not in path_parts:
            os.environ["PATH"] = candidate_text + os.pathsep + os.environ.get("PATH", "")
            path_parts.insert(0, candidate_text)
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(candidate_text)
        added.append(candidate)
    return added

