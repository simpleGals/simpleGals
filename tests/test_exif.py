from pathlib import Path
from PIL import Image
from PIL.ExifTags import Base
from PIL.TiffImagePlugin import IFDRational
from simplegals.core.exif import _shutter, extract_exif

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
    assert out["exposure"] == "ƒ/5.6 · ISO 100 · 1/125s"


def test_shutter_reduces_unreduced_rational():
    # Cameras commonly store 1/125s as the un-reduced rational 10/1250.
    # Fraction() copies an IFDRational verbatim without reducing, so we must
    # reduce it ourselves; regression for the "10/1250s" display bug.
    assert _shutter(IFDRational(10, 1250)) == "1/125s"
    assert _shutter((10, 1250)) == "1/125s"
    assert _shutter(IFDRational(1, 3)) == "1/3s"
    assert _shutter(IFDRational(2, 1)) == "2s"   # >= 1s renders as seconds

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
