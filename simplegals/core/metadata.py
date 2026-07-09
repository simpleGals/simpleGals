from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import ProjectConfig, settings_hash as compute_settings_hash


@dataclass
class ThumbMeta:
    path: str
    generated_at: str


@dataclass
class OutputMeta:
    path: str
    thumb_path: str
    generated_at: str


@dataclass
class OgMeta:
    path: str
    generated_at: str


@dataclass
class ImageSidecar:
    source: str
    mtime: str
    sha256: str
    settings_hash: str
    thumb: ThumbMeta | None = None
    output: OutputMeta | None = None
    og: OgMeta | None = None
    exif: dict | None = None


def sidecar_path(meta_dir: Path, source_name: str) -> Path:
    return meta_dir / f"{source_name}.json"


def load_sidecar(meta_dir: Path, source_name: str) -> ImageSidecar | None:
    p = sidecar_path(meta_dir, source_name)
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    thumb = ThumbMeta(**data["thumb"]) if data.get("thumb") else None
    output = OutputMeta(**data["output"]) if data.get("output") else None
    og = OgMeta(**data["og"]) if data.get("og") else None
    return ImageSidecar(
        source=data["source"],
        mtime=data["mtime"],
        sha256=data["sha256"],
        settings_hash=data["settings_hash"],
        thumb=thumb,
        output=output,
        og=og,
        exif=data.get("exif"),
    )


def save_sidecar(meta_dir: Path, sidecar: ImageSidecar) -> None:
    meta_dir.mkdir(parents=True, exist_ok=True)
    p = sidecar_path(meta_dir, sidecar.source)
    p.write_text(json.dumps(asdict(sidecar), indent=2), encoding="utf-8")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def now_rfc3339() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mtime_str(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def check_staleness(
    source: Path,
    meta_dir: Path,
    config: ProjectConfig,
) -> tuple[bool, bool]:
    """Return (thumb_needs_regen, output_needs_regen)."""
    sidecar = load_sidecar(meta_dir, source.name)
    if sidecar is None:
        return True, True

    current_s_hash = compute_settings_hash(config)
    current_mtime = _mtime_str(source)

    def _artifacts_exist() -> tuple[bool, bool]:
        thumb_missing = sidecar.thumb is None or not Path(sidecar.thumb.path).exists()
        output_missing = sidecar.output is None or not Path(sidecar.output.path).exists()
        return thumb_missing, output_missing

    if current_mtime == sidecar.mtime:
        thumb_missing, output_missing = _artifacts_exist()
        return thumb_missing, output_missing or current_s_hash != sidecar.settings_hash

    current_sha = file_sha256(source)
    if current_sha == sidecar.sha256:
        # touched but unchanged, refresh stored mtime
        sidecar.mtime = current_mtime
        save_sidecar(meta_dir, sidecar)
        thumb_missing, output_missing = _artifacts_exist()
        return thumb_missing, output_missing or current_s_hash != sidecar.settings_hash

    return True, True
