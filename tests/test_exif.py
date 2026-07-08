from pathlib import Path
from PIL import Image
from PIL.ExifTags import Base
from simplegals.core.exif import extract_exif

def _make_jpeg_with_exif(path: Path, exif_pairs: dict) -> None:
    img = Image.new("RGB", (8, 8), "white")
    exif = Image.Exif()
    for tag, val in exif_pairs.items():
        exif[tag] = val
    img.save(path, exif=exif)

def test_no_exif_returns_none(tmp_path):
    p = tmp_path / "plain.png"
    Image.new("RGB", (8, 8), "white").save(p)
    assert extract_exif(p) is None

def test_camera_make_model(tmp_path):
    p = tmp_path / "a.jpg"
    _make_jpeg_with_exif(p, {Base.Make.value: "NIKON CORPORATION", Base.Model.value: "NIKON Z 7"})
    out = extract_exif(p)
    assert out is not None
    assert "NIKON" in out["camera"] and "Z 7" in out["camera"]

def test_exposure_triangle_string(tmp_path):
    p = tmp_path / "b.jpg"
    _make_jpeg_with_exif(p, {
        Base.FNumber.value: 5.6,
        Base.ISOSpeedRatings.value: 100,
        Base.ExposureTime.value: (1, 125),
    })
    out = extract_exif(p)
    assert out["exposure"] == "f/5.6 · ISO 100 · 1/125s"

def test_exposure_comp_omitted_when_zero(tmp_path):
    p = tmp_path / "c.jpg"
    _make_jpeg_with_exif(p, {Base.ExposureBiasValue.value: 0.0, Base.Make.value: "X"})
    out = extract_exif(p)
    assert "exposure_comp" not in out

def test_flash_fired(tmp_path):
    p = tmp_path / "d.jpg"
    _make_jpeg_with_exif(p, {Base.Flash.value: 1})   # bit0 = fired
    out = extract_exif(p)
    assert out["flash"] == "Fired"
