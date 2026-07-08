import shutil
from pathlib import Path
import pytest
from PIL import Image
from simplegals.core.config import ProjectConfig
from simplegals.core.gallery import (
    SUPPORTED_EXTENSIONS,
    build,
    clean,
    ensure_project_dirs,
    scan_sources,
    validate,
)
from simplegals.core.metadata import load_sidecar
from simplegals.workers.progress import ProgressState


def test_ensure_project_dirs_creates_directories(tmp_path):
    ensure_project_dirs(tmp_path)
    assert (tmp_path / "in").is_dir()
    assert (tmp_path / "out").is_dir()
    assert (tmp_path / ".meta").is_dir()


def test_scan_sources_finds_supported_images(tmp_project):
    in_dir = tmp_project / "in"
    sources = scan_sources(in_dir)
    assert len(sources) == 2
    assert all(s.suffix.lower() in SUPPORTED_EXTENSIONS for s in sources)


def test_scan_sources_ignores_unsupported(tmp_project):
    (tmp_project / "in" / "notes.txt").write_text("ignore me")
    sources = scan_sources(tmp_project / "in")
    assert all(s.suffix.lower() in SUPPORTED_EXTENSIONS for s in sources)


def test_validate_passes_on_clean_project(tmp_project):
    config = ProjectConfig()
    errors = validate(tmp_project, config)
    assert errors == []


def test_validate_catches_missing_images_in_config(tmp_project):
    config = ProjectConfig(images={"ghost.jpg": {"include": True}})
    errors = validate(tmp_project, config)
    assert any("ghost.jpg" in e for e in errors)


def test_clean_removes_meta_contents(tmp_project):
    meta_dir = tmp_project / ".meta"
    (meta_dir / "TEST.jpg.json").write_text("{}")
    (meta_dir / "build.jsonl").write_text("{}")
    clean(tmp_project)
    assert not list(meta_dir.glob("*"))


def test_build_produces_html_output(tmp_project):
    config = ProjectConfig(title="Test Build")
    log_path, had_errors = build(tmp_project, config)
    assert (tmp_project / "out" / "index.html").exists()
    assert (tmp_project / "out" / "all.html").exists()
    assert log_path.exists()
    assert not had_errors


def test_build_writes_build_log(tmp_project):
    config = ProjectConfig()
    log_path, _ = build(tmp_project, config)
    assert log_path.suffix == ".log"
    assert log_path.parent == tmp_project / ".meta"
    content = log_path.read_text()
    assert len(content) > 0


def test_build_appends_to_jsonl(tmp_project):
    config = ProjectConfig()
    build(tmp_project, config)
    jsonl = tmp_project / ".meta" / "build.jsonl"
    assert jsonl.exists()
    lines = [l for l in jsonl.read_text().splitlines() if l.strip()]
    assert len(lines) >= 1


def test_build_calls_progress_callback(tmp_project):
    config = ProjectConfig()
    states = []

    def callback(state: ProgressState) -> None:
        states.append(state)

    build(tmp_project, config, progress_callback=callback)
    assert len(states) > 0
    assert all(isinstance(s, ProgressState) for s in states)


def test_build_prunes_removed_sources(tmp_project, test_jpg):
    config = ProjectConfig()
    in_dir = tmp_project / "in"
    out_dir = tmp_project / "out"
    meta_dir = tmp_project / ".meta"

    # Add a third image with a unique stem so its _item.html won't collide with fixtures
    extra = in_dir / "REMOVE_ME.jpg"
    shutil.copy(test_jpg, extra)
    build(tmp_project, config)

    item_html = out_dir / "REMOVE_ME_item.html"
    sidecar = meta_dir / "REMOVE_ME.jpg.json"
    assert item_html.exists()
    assert sidecar.exists()

    # Remove the extra source and rebuild
    extra.unlink()
    build(tmp_project, config)

    assert not item_html.exists(), "_item.html must be pruned"
    assert not sidecar.exists(), "sidecar must be pruned"
    assert not (out_dir / "REMOVE_ME.jpg").exists(), "output image must be pruned"
    assert not (meta_dir / "REMOVE_ME_thumb.jpg").exists(), "meta thumb must be pruned"


def _proj(tmp_path):
    in_dir, out_dir, meta = ensure_project_dirs(tmp_path)
    img = Image.new("RGB", (1200, 800), "white")
    ex = Image.Exif()
    from PIL.ExifTags import Base
    ex[Base.Make.value] = "CANON"; ex[Base.Model.value] = "EOS R5"
    img.save(in_dir / "shot.jpg", exif=ex)
    return tmp_path, out_dir, meta


def test_build_caches_exif_in_sidecar(tmp_path):
    proj, out_dir, meta = _proj(tmp_path)
    build(proj, ProjectConfig(social_previews=True, exif_display=True))
    sc = load_sidecar(meta, "shot.jpg")
    assert sc.exif is not None and "CANON" in sc.exif["camera"]
    assert sc.og is not None and Path(sc.og.path).name == "shot_og.jpg"


def test_build_does_not_reextract_exif_when_unchanged(tmp_path, monkeypatch):
    proj, out_dir, meta = _proj(tmp_path)
    build(proj, ProjectConfig(social_previews=True, exif_display=True))

    import simplegals.core.gallery as gallery_mod
    calls = []
    real = gallery_mod.extract_exif
    monkeypatch.setattr(gallery_mod, "extract_exif",
                        lambda src: calls.append(src) or real(src))
    build(proj, ProjectConfig(social_previews=True, exif_display=True))
    assert calls == [], "EXIF must not be re-extracted when nothing changed"


def test_build_force_rebuilds_all(tmp_project):
    config = ProjectConfig()
    # First build populates the cache
    build(tmp_project, config)
    # Second build with fresh cache — nothing to do
    log_path, _ = build(tmp_project, config)
    log = log_path.read_text()
    assert "Tasks: 0 thumb, 0 output" in log
    # Force build must queue all tasks despite fresh cache
    log_path2, _ = build(tmp_project, config, force=True)
    log2 = log_path2.read_text()
    assert "Force rebuild" in log2
    assert "Tasks: 0 thumb, 0 output" not in log2
