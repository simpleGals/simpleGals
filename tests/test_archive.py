import zipfile
from pathlib import Path
from simplegals.core.archive import (
    gallery_zip_name, build_zip, compute_manifest, load_zip_state, save_zip_state,
)

def _seed(out: Path, names):
    out.mkdir(parents=True, exist_ok=True)
    for n in names:
        (out / n).write_bytes(b"\xff\xd8" + n.encode() * 50)

def test_zip_name_slugified():
    assert gallery_zip_name("My Gallery") == "My_Gallery.zip"
    assert gallery_zip_name("  ") == "gallery.zip"

def test_build_zip_stored_images_only(tmp_path):
    out = tmp_path / "out"; _seed(out, ["a.jpg", "b.jpg"])
    zp = tmp_path / "g.zip"
    count, size = build_zip(out, ["a.jpg", "b.jpg"], zp)
    assert count == 2 and size > 0
    with zipfile.ZipFile(zp) as z:
        assert sorted(z.namelist()) == ["a.jpg", "b.jpg"]
        assert all(i.compress_type == zipfile.ZIP_STORED for i in z.infolist())

def test_manifest_changes_with_content(tmp_path):
    out = tmp_path / "out"; _seed(out, ["a.jpg"])
    m1 = compute_manifest(out, ["a.jpg"])
    (out / "a.jpg").write_bytes(b"different")
    m2 = compute_manifest(out, ["a.jpg"])
    assert m1 != m2

def test_zip_state_roundtrip(tmp_path):
    meta = tmp_path / ".meta"; meta.mkdir()
    save_zip_state(meta, {"manifest": "x", "zip": "g.zip", "size": 10, "count": 1})
    assert load_zip_state(meta)["manifest"] == "x"

def test_progress_cb_called_per_file(tmp_path):
    out = tmp_path / "out"; _seed(out, ["a.jpg", "b.jpg", "c.jpg"])
    seen = []
    build_zip(out, ["a.jpg", "b.jpg", "c.jpg"], tmp_path / "g.zip", lambda d, t: seen.append((d, t)))
    assert seen == [(1, 3), (2, 3), (3, 3)]

def test_build_zip_skips_missing_files(tmp_path):
    out = tmp_path / "out"; _seed(out, ["a.jpg"])
    zp = tmp_path / "g.zip"
    count, size = build_zip(out, ["a.jpg", "missing.jpg"], zp)
    assert count == 1
    with zipfile.ZipFile(zp) as z:
        assert z.namelist() == ["a.jpg"]

def test_manifest_order_independent_and_missing(tmp_path):
    out = tmp_path / "out"; _seed(out, ["a.jpg", "b.jpg"])
    assert compute_manifest(out, ["a.jpg", "b.jpg"]) == compute_manifest(out, ["b.jpg", "a.jpg"])
    m_present = compute_manifest(out, ["a.jpg"])
    m_with_missing = compute_manifest(out, ["a.jpg", "gone.jpg"])
    assert m_present != m_with_missing
