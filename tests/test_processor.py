from pathlib import Path
import pytest
from PIL import Image
from simplegals.core.config import ProjectConfig
from simplegals.core.processor import (
    SGUI_THUMB_MAX,
    HTML_THUMB_MAX,
    generate_output,
    generate_sgui_thumb,
    og_name,
)


def test_sgui_thumb_jpg_is_created(tmp_path, test_jpg):
    meta_dir = tmp_path / ".meta"
    meta_dir.mkdir()
    result = generate_sgui_thumb(test_jpg, meta_dir)
    assert result.exists()
    assert result.name == "TEST_thumb.jpg"


def test_sgui_thumb_jpg_fits_in_max_bounds(tmp_path, test_jpg):
    meta_dir = tmp_path / ".meta"
    meta_dir.mkdir()
    result = generate_sgui_thumb(test_jpg, meta_dir)
    with Image.open(result) as img:
        assert img.size[0] <= SGUI_THUMB_MAX[0]
        assert img.size[1] <= SGUI_THUMB_MAX[1]


def test_sgui_thumb_png_produces_png(tmp_path, test_png):
    meta_dir = tmp_path / ".meta"
    meta_dir.mkdir()
    result = generate_sgui_thumb(test_png, meta_dir)
    assert result.suffix == ".png"
    assert result.exists()


def test_generate_output_jpg_creates_both_files(tmp_path, test_jpg):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    config = ProjectConfig(quality=85, copyright="© 2026 timlnx")
    output_path, thumb_path, _ = generate_output(test_jpg, out_dir, config)
    assert output_path.exists()
    assert thumb_path.exists()
    assert thumb_path.name == "TEST_thumb.jpg"


def test_generate_output_thumb_fits_html_bounds(tmp_path, test_jpg):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    config = ProjectConfig(quality=85)
    _, thumb_path, _ = generate_output(test_jpg, out_dir, config)
    with Image.open(thumb_path) as img:
        assert img.size[0] <= HTML_THUMB_MAX[0]
        assert img.size[1] <= HTML_THUMB_MAX[1]


def test_generate_output_png(tmp_path, test_png):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    config = ProjectConfig(quality=85)
    output_path, thumb_path, _ = generate_output(test_png, out_dir, config)
    assert output_path.suffix == ".png"
    assert thumb_path.suffix == ".png"


def test_generate_output_with_copyright_does_not_raise(tmp_path, test_jpg):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    config = ProjectConfig(quality=90, copyright="© 2026 timlnx")
    output_path, _, _ = generate_output(test_jpg, out_dir, config)
    assert output_path.exists()


def _big(path):
    Image.new("RGB", (4000, 2000), "white").save(path, quality=95)


def test_og_generated_longest_edge_1200(tmp_path):
    src = tmp_path / "p.jpg"
    _big(src)
    out = tmp_path / "out"
    out.mkdir()
    generate_output(src, out, ProjectConfig(social_previews=True))
    og = out / og_name(src)
    assert og.exists()
    with Image.open(og) as im:
        assert max(im.size) == 1200


def test_og_skipped_when_disabled(tmp_path):
    src = tmp_path / "q.jpg"
    _big(src)
    out = tmp_path / "out"
    out.mkdir()
    generate_output(src, out, ProjectConfig(social_previews=False))
    assert not (out / og_name(src)).exists()


def test_og_matches_source_container(tmp_path):
    """The _og preview keeps the source's container: jpg -> jpg, png -> png."""
    out = tmp_path / "out"
    out.mkdir()

    jpg = tmp_path / "p.jpg"
    _big(jpg)
    generate_output(jpg, out, ProjectConfig(social_previews=True))
    assert og_name(jpg) == "p_og.jpg"
    assert (out / "p_og.jpg").exists()

    png = tmp_path / "q.png"
    Image.new("RGBA", (4000, 2000), (10, 20, 30, 255)).save(png)
    generate_output(png, out, ProjectConfig(social_previews=True))
    assert og_name(png) == "q_og.png"
    assert (out / "q_og.png").exists()


def test_og_png_preserves_transparency(tmp_path):
    """A PNG source keeps its container, so a transparent region stays
    transparent in the _og.png (no flatten to black or white).
    """
    src = tmp_path / "r.png"
    img = Image.new("RGBA", (2000, 1000), (0, 0, 0, 255))
    # Punch a fully-transparent hole in the top-left corner.
    alpha = Image.new("L", (2000, 1000), 255)
    alpha.paste(Image.new("L", (200, 200), 0), (0, 0))
    img.putalpha(alpha)
    img.save(src)

    out = tmp_path / "out"
    out.mkdir()
    generate_output(src, out, ProjectConfig(social_previews=True))
    og = out / og_name(src)
    assert og.exists()
    assert og.suffix == ".png"

    with Image.open(og) as im:
        # Source is 2000x1000 scaled to fit 1200x1200 -> 1200x600 (0.6x).
        # The 200x200 transparent corner maps to ~120x120; sample well
        # inside it, away from any resize-edge blending.
        rgba = im.convert("RGBA")
        assert rgba.getpixel((10, 10))[3] == 0, "transparent corner should stay transparent"
