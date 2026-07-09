"""Camera EXIF metadata extraction and normalization.

Reads EXIF tags from an image via Pillow and produces a dict of
display-ready strings for the subset of tags that are actually present.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from PIL import Image
from PIL.ExifTags import Base, IFD


def _shutter(value) -> str:
    # Cameras encode ExposureTime as a rational that is NOT always in lowest
    # terms: a 1/125s exposure commonly arrives as 10/1250. Pillow surfaces it
    # either as an IFDRational (a numbers.Rational, which Fraction() copies
    # verbatim WITHOUT reducing, trusting it to be in lowest terms) or as a
    # plain (numerator, denominator) tuple. In both cases we must reduce it
    # ourselves via Fraction's two-integer constructor, which applies gcd, so
    # the display shows 1/125s rather than 10/1250s.
    num = den = None
    if isinstance(value, (tuple, list)) and len(value) == 2:
        num, den = value
    elif hasattr(value, "numerator") and hasattr(value, "denominator"):
        num, den = value.numerator, value.denominator
    if num is not None:
        try:
            f = Fraction(int(num), int(den))
        except (TypeError, ValueError, ZeroDivisionError):
            return str(value)
    else:
        try:
            f = Fraction(value).limit_denominator(8000)
        except (TypeError, ValueError):
            return str(value)
    if f >= 1:
        return f"{float(f):g}s"
    return f"{f.numerator}/{f.denominator}s"


def _clean(value) -> str:
    return str(value).strip().strip("\x00").strip()


def _lookup(ifd, exif, tag: int):
    """Look up a tag that normally lives in the Exif SubIFD.

    Well-formed files (real cameras, or files built by pointing an
    `Image.Exif()` sub-IFD at tags via `get_ifd(IFD.Exif)`) nest these tags
    under the Exif SubIFD (0x8769). A standalone `Image.Exif()` with tags
    set directly by number has no IFD hierarchy to preserve, so Pillow
    writes them flat into IFD0 instead. Check both locations so either
    layout resolves correctly.
    """
    value = ifd.get(tag)
    if value is None:
        value = exif.get(tag)
    return value


def extract_exif(source: Path) -> dict | None:
    """Return a dict of display-ready camera-metadata strings, or None if absent.

    Only keys with usable values are included, so callers can render just the
    fields that exist. Possible keys: camera, lens, exposure, focal_length,
    flash, exposure_comp, white_balance, metering.
    """
    try:
        with Image.open(source) as img:
            exif = img.getexif()
    except Exception:
        return None
    if not exif:
        return None

    ifd = exif.get_ifd(IFD.Exif)
    out: dict = {}

    make = _clean(exif.get(Base.Make.value, ""))
    model = _clean(exif.get(Base.Model.value, ""))
    camera = " ".join(p for p in (make, model) if p).strip()
    # Avoid duplicating make when model already contains it (e.g. "NIKON Z 7")
    if make and model and model.upper().startswith(make.split()[0].upper()):
        camera = model
    if camera:
        out["camera"] = camera

    lens = _clean(_lookup(ifd, exif, Base.LensModel.value) or "")
    if lens:
        out["lens"] = lens

    fnum = _lookup(ifd, exif, Base.FNumber.value)
    iso = _lookup(ifd, exif, Base.ISOSpeedRatings.value)
    shutter = _lookup(ifd, exif, Base.ExposureTime.value)
    parts = []
    if fnum:
        parts.append(f"ƒ/{float(fnum):g}")  # ƒ (LATIN SMALL LETTER F WITH HOOK)
    if iso:
        parts.append(f"ISO {int(iso)}")
    if shutter:
        parts.append(_shutter(shutter))
    if parts:
        out["exposure"] = " · ".join(parts)

    focal = _lookup(ifd, exif, Base.FocalLength.value)
    if focal:
        out["focal_length"] = f"{float(focal):g}mm"

    flash = _lookup(ifd, exif, Base.Flash.value)
    if flash is not None:
        out["flash"] = "Fired" if int(flash) & 1 else "Did not fire"

    bias = _lookup(ifd, exif, Base.ExposureBiasValue.value)
    if bias is not None and float(bias) != 0.0:
        out["exposure_comp"] = f"{float(bias):+g} EV"

    wb = _lookup(ifd, exif, Base.WhiteBalance.value)
    if wb is not None:
        out["white_balance"] = {0: "Auto", 1: "Manual"}.get(int(wb), str(wb))

    metering = _lookup(ifd, exif, Base.MeteringMode.value)
    if metering is not None:
        out["metering"] = {
            0: "Unknown", 1: "Average", 2: "Center-weighted", 3: "Spot",
            4: "Multi-spot", 5: "Pattern", 6: "Partial",
        }.get(int(metering), str(metering))

    return out or None
