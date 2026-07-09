import shutil
from datetime import datetime, timezone
from pathlib import Path
import pytest
from simplegals.core.config import ProjectConfig, settings_hash
from simplegals.core.metadata import (
    ImageSidecar,
    OgMeta,
    OutputMeta,
    ThumbMeta,
    check_staleness,
    file_sha256,
    load_sidecar,
    now_rfc3339,
    save_sidecar,
    sidecar_path,
)


def test_sidecar_path(tmp_path):
    assert sidecar_path(tmp_path, "IMG_1234.jpg") == tmp_path / "IMG_1234.jpg.json"


def test_now_rfc3339_is_parseable_with_tz():
    dt = datetime.fromisoformat(now_rfc3339())
    assert dt.tzinfo is not None


def test_file_sha256_is_stable(test_jpg):
    assert file_sha256(test_jpg) == file_sha256(test_jpg)


def test_file_sha256_differs_by_content(test_jpg, test_png):
    assert file_sha256(test_jpg) != file_sha256(test_png)


def test_save_and_load_sidecar_roundtrip(tmp_path, test_jpg):
    sidecar = ImageSidecar(
        source=test_jpg.name,
        mtime=now_rfc3339(),
        sha256=file_sha256(test_jpg),
        settings_hash="abc123",
    )
    save_sidecar(tmp_path, sidecar)
    loaded = load_sidecar(tmp_path, test_jpg.name)
    assert loaded is not None
    assert loaded.source == test_jpg.name
    assert loaded.sha256 == sidecar.sha256
    assert loaded.settings_hash == "abc123"


def test_load_sidecar_with_thumb_and_output(tmp_path, test_jpg):
    sidecar = ImageSidecar(
        source=test_jpg.name,
        mtime=now_rfc3339(),
        sha256=file_sha256(test_jpg),
        settings_hash="x",
        thumb=ThumbMeta(path=".meta/TEST_thumb.jpg", generated_at=now_rfc3339()),
        output=OutputMeta(
            path="out/TEST.jpg",
            thumb_path="out/TEST_thumb.jpg",
            generated_at=now_rfc3339(),
        ),
    )
    save_sidecar(tmp_path, sidecar)
    loaded = load_sidecar(tmp_path, test_jpg.name)
    assert loaded.thumb is not None
    assert loaded.output is not None
    assert loaded.output.thumb_path == "out/TEST_thumb.jpg"


def test_load_sidecar_returns_none_when_missing(tmp_path):
    assert load_sidecar(tmp_path, "ghost.jpg") is None


def test_no_sidecar_means_fully_stale(tmp_path, test_jpg):
    meta_dir = tmp_path / ".meta"
    meta_dir.mkdir()
    thumb_stale, output_stale = check_staleness(test_jpg, meta_dir, ProjectConfig())
    assert thumb_stale and output_stale


def _make_artifacts(tmp_path, meta_dir, test_jpg):
    """Create thumb and output files on disk and return (ThumbMeta, OutputMeta)."""
    thumb_path = meta_dir / f"{test_jpg.stem}_thumb{test_jpg.suffix}"
    out_dir = tmp_path / "out"
    out_dir.mkdir(exist_ok=True)
    output_path = out_dir / test_jpg.name
    output_thumb_path = out_dir / f"{test_jpg.stem}_thumb{test_jpg.suffix}"
    shutil.copy(test_jpg, thumb_path)
    shutil.copy(test_jpg, output_path)
    shutil.copy(test_jpg, output_thumb_path)
    return (
        ThumbMeta(path=str(thumb_path), generated_at=now_rfc3339()),
        OutputMeta(path=str(output_path), thumb_path=str(output_thumb_path), generated_at=now_rfc3339()),
    )


def test_fresh_mtime_means_not_stale(tmp_path, test_jpg):
    meta_dir = tmp_path / ".meta"
    meta_dir.mkdir()
    config = ProjectConfig()
    mtime = datetime.fromtimestamp(test_jpg.stat().st_mtime, tz=timezone.utc).isoformat()
    thumb_meta, output_meta = _make_artifacts(tmp_path, meta_dir, test_jpg)
    sidecar = ImageSidecar(
        source=test_jpg.name,
        mtime=mtime,
        sha256=file_sha256(test_jpg),
        settings_hash=settings_hash(config),
        thumb=thumb_meta,
        output=output_meta,
    )
    save_sidecar(meta_dir, sidecar)
    thumb_stale, output_stale = check_staleness(test_jpg, meta_dir, config)
    assert not thumb_stale and not output_stale


def test_missing_artifacts_means_stale(tmp_path, test_jpg):
    """Sidecar with current mtime/hash but no artifacts on disk → both stale."""
    meta_dir = tmp_path / ".meta"
    meta_dir.mkdir()
    config = ProjectConfig()
    mtime = datetime.fromtimestamp(test_jpg.stat().st_mtime, tz=timezone.utc).isoformat()
    sidecar = ImageSidecar(
        source=test_jpg.name,
        mtime=mtime,
        sha256=file_sha256(test_jpg),
        settings_hash=settings_hash(config),
    )
    save_sidecar(meta_dir, sidecar)
    thumb_stale, output_stale = check_staleness(test_jpg, meta_dir, config)
    assert thumb_stale and output_stale


def test_settings_change_makes_output_stale_not_thumb(tmp_path, test_jpg):
    meta_dir = tmp_path / ".meta"
    meta_dir.mkdir()
    old_config = ProjectConfig(quality=90)
    new_config = ProjectConfig(quality=85)
    mtime = datetime.fromtimestamp(test_jpg.stat().st_mtime, tz=timezone.utc).isoformat()
    thumb_meta, output_meta = _make_artifacts(tmp_path, meta_dir, test_jpg)
    sidecar = ImageSidecar(
        source=test_jpg.name,
        mtime=mtime,
        sha256=file_sha256(test_jpg),
        settings_hash=settings_hash(old_config),
        thumb=thumb_meta,
        output=output_meta,
    )
    save_sidecar(meta_dir, sidecar)
    thumb_stale, output_stale = check_staleness(test_jpg, meta_dir, new_config)
    assert not thumb_stale
    assert output_stale


def test_sidecar_roundtrips_og_and_exif(tmp_path):
    sc = ImageSidecar(
        source="a.jpg", mtime="t", sha256="h", settings_hash="s",
        og=OgMeta(path="out/a_og.jpg", generated_at="t"),
        exif={"camera": "NIKON Z 7", "exposure": "ƒ/5.6 · ISO 100 · 1/125s"},
    )
    save_sidecar(tmp_path, sc)
    loaded = load_sidecar(tmp_path, "a.jpg")
    assert loaded.og is not None and loaded.og.path == "out/a_og.jpg"
    assert loaded.exif["camera"] == "NIKON Z 7"


def test_sidecar_og_exif_default_none(tmp_path):
    sc = ImageSidecar(source="b.jpg", mtime="t", sha256="h", settings_hash="s")
    save_sidecar(tmp_path, sc)
    loaded = load_sidecar(tmp_path, "b.jpg")
    assert loaded.og is None
    assert loaded.exif is None
