from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path

from .metadata import file_sha256

STATE_FILE = "gallery-zip.json"


def gallery_zip_name(title: str) -> str:
    slug = re.sub(r"[^\w.-]+", "_", (title or "").strip()).strip("_")
    return f"{slug or 'gallery'}.zip"


def compute_manifest(out_dir: Path, names: list[str]) -> str:
    h = hashlib.sha256()
    for name in sorted(names):
        p = out_dir / name
        sha = file_sha256(p) if p.exists() else "missing"
        h.update(f"{name}:{sha}\n".encode())
    return h.hexdigest()[:16]


def build_zip(out_dir: Path, names: list[str], zip_path: Path, progress_cb=None) -> tuple[int, int]:
    ordered = sorted(names)
    total = len(ordered)
    tmp = zip_path.with_suffix(".zip.tmp")
    count = 0
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_STORED) as z:
            for name in ordered:
                src = out_dir / name
                if not src.exists():
                    continue
                z.write(src, arcname=name)
                count += 1
                if progress_cb:
                    progress_cb(count, total)
        tmp.replace(zip_path)
        return count, zip_path.stat().st_size
    finally:
        tmp.unlink(missing_ok=True)


def load_zip_state(meta_dir: Path) -> dict | None:
    p = meta_dir / STATE_FILE
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    return data if isinstance(data, dict) else None


def save_zip_state(meta_dir: Path, state: dict) -> None:
    meta_dir.mkdir(parents=True, exist_ok=True)
    (meta_dir / STATE_FILE).write_text(json.dumps(state, indent=2), encoding="utf-8")
