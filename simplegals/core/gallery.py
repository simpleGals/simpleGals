from __future__ import annotations

import json
import multiprocessing
import threading
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import bitmath

from .config import ProjectConfig, settings_hash
from .exif import extract_exif
from .metadata import (
    ImageSidecar,
    OgMeta,
    OutputMeta,
    ThumbMeta,
    check_staleness,
    file_sha256,
    load_sidecar,
    now_rfc3339,
    save_sidecar,
)
from .processor import og_name
from .template import render_gallery
from ..workers.pool import dispatch
from ..workers.progress import ProgressState, drain_queue, format_cli_progress

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png"})


def ensure_project_dirs(project_dir: Path) -> tuple[Path, Path, Path]:
    in_dir = project_dir / "in"
    out_dir = project_dir / "out"
    meta_dir = project_dir / ".meta"
    for d in (in_dir, out_dir, meta_dir):
        d.mkdir(parents=True, exist_ok=True)
    return in_dir, out_dir, meta_dir


def scan_sources(in_dir: Path) -> list[Path]:
    return sorted(
        p for p in in_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def validate(project_dir: Path, config: ProjectConfig) -> list[str]:
    errors: list[str] = []
    in_dir = project_dir / "in"
    if not in_dir.exists():
        errors.append(f"Missing input directory: {in_dir}")
        return errors
    source_names = {p.name for p in scan_sources(in_dir)}
    for name in config.images:
        if name not in source_names:
            errors.append(f"Image in config not found in in/: {name}")
    return errors


def clean(project_dir: Path) -> None:
    meta_dir = project_dir / ".meta"
    if meta_dir.exists():
        for p in meta_dir.iterdir():
            if p.is_file():
                p.unlink()


def prune_removed_sources(
    out_dir: Path,
    meta_dir: Path,
    source_names: set[str],
) -> int:
    """Delete out/ and .meta/ artifacts for sources no longer present in in/.

    Returns the number of source entries pruned.
    """
    removed = 0
    for sidecar in meta_dir.glob("*.json"):
        name = sidecar.stem  # e.g. "DSC_8297.jpg" (strip trailing .json)
        if name in source_names:
            continue
        stem = Path(name).stem
        ext = Path(name).suffix
        sidecar.unlink(missing_ok=True)
        (meta_dir / f"{stem}_thumb{ext}").unlink(missing_ok=True)
        (out_dir / name).unlink(missing_ok=True)
        (out_dir / f"{stem}_thumb{ext}").unlink(missing_ok=True)
        (out_dir / f"{stem}_display{ext}").unlink(missing_ok=True)
        (out_dir / f"{stem}_og{ext}").unlink(missing_ok=True)
        (out_dir / f"{stem}_item.html").unlink(missing_ok=True)
        removed += 1
    return removed


def build(
    project_dir: Path,
    config: ProjectConfig,
    progress_callback=None,
    force: bool = False,
) -> tuple[Path, bool]:
    """Run a full gallery build. Returns (log_path, had_errors)."""
    in_dir, out_dir, meta_dir = ensure_project_dirs(project_dir)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = meta_dir / f"build-{ts}.log"
    log_lines: list[str] = []

    def log(msg: str) -> None:
        log_lines.append(msg)

    sources = scan_sources(in_dir)
    log(f"Found {len(sources)} source image(s) in {in_dir}")

    source_names = {s.name for s in sources}
    pruned = prune_removed_sources(out_dir, meta_dir, source_names)
    if pruned:
        log(f"Pruned {pruned} removed source(s) from out/ and .meta/")

    if force:
        log("Force rebuild requested — skipping cache.")

    thumb_tasks: list[tuple] = []
    output_tasks: list[tuple] = []
    regenerated: dict[str, bool] = {}

    for source in sources:
        if force:
            thumb_stale, output_stale = True, True
        else:
            thumb_stale, output_stale = check_staleness(source, meta_dir, config)
        regenerated[source.name] = output_stale
        if thumb_stale:
            thumb_tasks.append((str(source), str(meta_dir), None))
        if output_stale:
            output_tasks.append((str(source), str(out_dir), {
                "quality": config.quality,
                "copyright": config.copyright,
                "template": config.template,
                "social_previews": config.social_previews,
            }))

    log(f"Tasks: {len(thumb_tasks)} thumb, {len(output_tasks)} output")

    had_errors = False
    if thumb_tasks or output_tasks:
        q: multiprocessing.Queue = multiprocessing.Queue()
        state = ProgressState(
            thumb_total=len(thumb_tasks),
            output_total=len(output_tasks),
        )
        _done = threading.Event()

        def _run_dispatch() -> None:
            dispatch(thumb_tasks, output_tasks, q)
            _done.set()

        dispatch_thread = threading.Thread(target=_run_dispatch, daemon=True)
        dispatch_thread.start()

        while not _done.wait(timeout=0.05):
            state = drain_queue(q, state, timeout=0.02)
            if progress_callback:
                progress_callback(state)

        # final drain after all workers finish
        state = drain_queue(q, state, timeout=0.1)
        if progress_callback:
            progress_callback(state)

        dispatch_thread.join()
        log(format_cli_progress(state))
        if state.thumb_failed or state.output_failed:
            had_errors = True
            log(f"Errors: {state.thumb_failed} thumb, {state.output_failed} output")

    s_hash = settings_hash(config)
    for source in sources:
        sidecar = load_sidecar(meta_dir, source.name) or ImageSidecar(
            source=source.name,
            mtime=now_rfc3339(),
            sha256=file_sha256(source),
            settings_hash=s_hash,
        )
        thumb_path = meta_dir / f"{source.stem}_thumb{source.suffix}"
        if thumb_path.exists():
            sidecar.thumb = ThumbMeta(path=str(thumb_path), generated_at=now_rfc3339())
        output_path = out_dir / source.name
        if output_path.exists():
            sidecar.output = OutputMeta(
                path=str(output_path),
                thumb_path=str(out_dir / f"{source.stem}_thumb{source.suffix}"),
                generated_at=now_rfc3339(),
            )
            sidecar.settings_hash = s_hash
        og_path = out_dir / og_name(source)   # mirrors source container (jpg->jpg, png->png)
        if og_path.exists():
            sidecar.og = OgMeta(path=str(og_path), generated_at=now_rfc3339())
        else:
            sidecar.og = None
        if sidecar.exif is None or regenerated.get(source.name, False):
            sidecar.exif = extract_exif(source)
        save_sidecar(meta_dir, sidecar)

    raw_records = []
    for source in sources:
        img_config = config.images.get(source.name, {})
        size_str = bitmath.getsize(str(source), bestprefix=True).format("{value:.2f} {unit}")
        mtime_dt = datetime.fromtimestamp(source.stat().st_mtime, tz=timezone.utc)
        display_name = f"{source.stem}_display{source.suffix}"
        sidecar = load_sidecar(meta_dir, source.name)
        og_rel = Path(sidecar.og.path).name if sidecar and sidecar.og else None
        raw_records.append({
            "filename": source.name,
            "output_path": source.name,
            "thumb_path": f"{source.stem}_thumb{source.suffix}",
            "display_path": display_name if (out_dir / display_name).exists() else source.name,
            "caption": img_config.get("caption", ""),
            "alt": img_config.get("alt", ""),
            "include": img_config.get("include", True),
            "date": mtime_dt.strftime("%Y-%m-%d"),
            "size": size_str,
            "item_page": f"{source.stem}_item.html",
            "og_path": og_rel,
            "exif": sidecar.exif if sidecar else None,
        })

    log("Rendering HTML templates...")
    render_gallery(out_dir, config, raw_records)
    log("Build complete.")

    log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    jsonl_path = meta_dir / "build.jsonl"
    entry = {
        "ts": now_rfc3339(),
        "sources": len(sources),
        "thumb_tasks": len(thumb_tasks),
        "output_tasks": len(output_tasks),
        "had_errors": had_errors,
        "log": str(log_path),
    }
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    return log_path, had_errors
