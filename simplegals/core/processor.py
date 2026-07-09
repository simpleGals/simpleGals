from __future__ import annotations

from pathlib import Path

import bitmath
import piexif
from PIL import Image, ImageOps

from .config import ProjectConfig

SGUI_THUMB_MAX: tuple[int, int] = (800, 800)
HTML_THUMB_MAX: tuple[int, int] = (600, 450)
DISPLAY_MAX_BYTES: bitmath.MiB = bitmath.MiB(2)
DISPLAY_MAX_DIM: tuple[int, int] = (2048, 2048)
OG_MAX_DIM: tuple[int, int] = (1200, 1200)


def _thumb_name(source: Path) -> str:
    return f"{source.stem}_thumb{source.suffix}"


def _display_name(source: Path) -> str:
    return f"{source.stem}_display{source.suffix}"


def og_name(source: Path) -> str:
    return f"{source.stem}_og{source.suffix}"


def generate_sgui_thumb(source: Path, meta_dir: Path) -> Path:
    """Generate .meta/<stem>_thumb<ext> for sgui preview. Not subject to publishing settings."""
    dest = meta_dir / _thumb_name(source)
    with Image.open(source) as img:
        img = ImageOps.exif_transpose(img)
        img.thumbnail(SGUI_THUMB_MAX, Image.LANCZOS)
        img.save(dest)
    return dest


def generate_output(
    source: Path,
    out_dir: Path,
    config: ProjectConfig,
) -> tuple[Path, Path, Path | None]:
    """Generate full output, optional display image (≤2 MB), and thumbnail.

    Returns (output_path, thumb_path, display_path).
    display_path is None when the original is already within the size limit.
    """
    output_path = out_dir / source.name
    thumb_path = out_dir / _thumb_name(source)

    with Image.open(source) as img:
        img = ImageOps.exif_transpose(img)
        icc = img.info.get("icc_profile")

        if config.copyright:
            img = _inject_copyright(img, config.copyright, source)

        save_kwargs: dict = {"quality": config.quality}
        if icc:
            save_kwargs["icc_profile"] = icc
        img.save(output_path, **_format_save_kwargs(source, save_kwargs))

        display_path: Path | None = None
        if bitmath.getsize(output_path) > DISPLAY_MAX_BYTES:
            display_path = out_dir / _display_name(source)
            display_img = img.copy()
            display_img.thumbnail(DISPLAY_MAX_DIM, Image.LANCZOS)
            dk: dict = {"quality": 85}
            if icc:
                dk["icc_profile"] = icc
            display_img.save(display_path, **_format_save_kwargs(source, dk))
            del display_img

        if config.social_previews:
            # The OG preview mirrors the source container: a JPEG source yields
            # a JPEG _og, a PNG source yields a PNG _og (keeping transparency).
            # Same save path as the thumb/display, so only container-applicable
            # options ride along (ICC for both; PNG keeps its alpha).
            og_img = img.copy()
            og_img.thumbnail(OG_MAX_DIM, Image.LANCZOS)
            og_kwargs: dict = {"quality": 80}
            if icc:
                og_kwargs["icc_profile"] = icc
            og_img.save(out_dir / og_name(source), **_format_save_kwargs(source, og_kwargs))
            del og_img

        img.thumbnail(HTML_THUMB_MAX, Image.LANCZOS)
        img.save(thumb_path, **_format_save_kwargs(source, save_kwargs))

    return output_path, thumb_path, display_path


def _format_save_kwargs(source: Path, kwargs: dict) -> dict:
    ext = source.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        return kwargs
    if ext == ".png":
        # Pillow maps quality 0-100 → compress_level 0-9
        compress = max(0, min(9, round((100 - kwargs.get("quality", 90)) / 11)))
        result = {k: v for k, v in kwargs.items() if k != "quality"}
        result["compress_level"] = compress
        return result
    return {}


def _inject_copyright(img: Image.Image, copyright: str, source: Path) -> Image.Image:
    ext = source.suffix.lower()
    if ext not in (".jpg", ".jpeg"):
        return img
    try:
        exif_bytes = img.info.get("exif", b"")
        if exif_bytes:
            exif_dict = piexif.load(exif_bytes)
        else:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}
        exif_dict["0th"][piexif.ImageIFD.Copyright] = copyright.encode("utf-8")
        img.info["exif"] = piexif.dump(exif_dict)
    except Exception:
        pass
    return img
