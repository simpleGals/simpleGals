import shutil
from pathlib import Path
import pytest
from simplegals.core.config import Layout, ProjectConfig
from simplegals.core.template import build_image_records, render_gallery


def _make_output_images(out_dir: Path, names: list[str]) -> list[Path]:
    """Create stub output image files for template tests."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name in names:
        p = out_dir / name
        p.write_bytes(b"FAKE")
        thumb = out_dir / f"{Path(name).stem}_thumb{Path(name).suffix}"
        thumb.write_bytes(b"FAKE")
        paths.append(p)
    return paths


def _make_records(out_dir: Path, names: list[str]) -> list[dict]:
    return [
        {
            "filename": n,
            "output_path": str(out_dir / n),
            "thumb_path": str(out_dir / f"{Path(n).stem}_thumb{Path(n).suffix}"),
            "caption": "",
            "alt": "",
            "include": True,
            "date": "2026-04-25",
            "size": "723.00 KiB",
            "item_page": f"{Path(n).stem}_item.html",
        }
        for n in names
    ]


def test_render_gallery_creates_index(tmp_path):
    out_dir = tmp_path / "out"
    names = ["a.jpg", "b.jpg", "c.jpg"]
    _make_output_images(out_dir, names)
    config = ProjectConfig(title="Test Gallery", layout=Layout(columns=2, rows=10))
    records = _make_records(out_dir, names)
    render_gallery(out_dir, config, records)
    assert (out_dir / "index.html").exists()


def test_render_gallery_creates_all_html(tmp_path):
    out_dir = tmp_path / "out"
    names = ["a.jpg", "b.jpg"]
    _make_output_images(out_dir, names)
    config = ProjectConfig(title="Gallery", layout=Layout(columns=2, rows=10))
    records = _make_records(out_dir, names)
    render_gallery(out_dir, config, records)
    assert (out_dir / "all.html").exists()


def test_render_gallery_creates_item_pages(tmp_path):
    out_dir = tmp_path / "out"
    names = ["a.jpg", "b.jpg"]
    _make_output_images(out_dir, names)
    config = ProjectConfig(layout=Layout(columns=2, rows=10))
    records = _make_records(out_dir, names)
    render_gallery(out_dir, config, records)
    assert (out_dir / "a_item.html").exists()
    assert (out_dir / "b_item.html").exists()


def test_render_gallery_paginates_correctly(tmp_path):
    out_dir = tmp_path / "out"
    # 6 images, 2 cols x 2 rows = 4 per page → 2 pages
    names = [f"img{i}.jpg" for i in range(6)]
    _make_output_images(out_dir, names)
    config = ProjectConfig(layout=Layout(columns=2, rows=2))
    records = _make_records(out_dir, names)
    render_gallery(out_dir, config, records)
    assert (out_dir / "index.html").exists()
    assert (out_dir / "page-2.html").exists()
    assert not (out_dir / "page-3.html").exists()


def test_render_gallery_excludes_flagged_images(tmp_path):
    out_dir = tmp_path / "out"
    names = ["a.jpg", "b.jpg"]
    _make_output_images(out_dir, names)
    config = ProjectConfig(layout=Layout(columns=2, rows=10))
    records = _make_records(out_dir, names)
    records[1]["include"] = False
    render_gallery(out_dir, config, records)
    index_html = (out_dir / "index.html").read_text(encoding="utf-8")
    assert "a_item.html" in index_html
    assert "b_item.html" not in index_html


def test_page2_prev_link_points_to_index(tmp_path):
    out_dir = tmp_path / "out"
    names = [f"img{i}.jpg" for i in range(6)]
    _make_output_images(out_dir, names)
    config = ProjectConfig(layout=Layout(columns=2, rows=2))
    records = _make_records(out_dir, names)
    render_gallery(out_dir, config, records)
    page2_html = (out_dir / "page-2.html").read_text(encoding="utf-8")
    assert 'href="index.html"' in page2_html
    assert 'href="page-1.html"' not in page2_html


def test_item_page_image_is_hyperlink(tmp_path):
    out_dir = tmp_path / "out"
    names = ["a.jpg"]
    _make_output_images(out_dir, names)
    config = ProjectConfig(layout=Layout(columns=2, rows=10))
    records = _make_records(out_dir, names)
    render_gallery(out_dir, config, records)
    item_html = (out_dir / "a_item.html").read_text(encoding="utf-8")
    assert '<a href=' in item_html
    assert 'a.jpg' in item_html


def test_item_page_has_download_link(tmp_path):
    out_dir = tmp_path / "out"
    names = ["a.jpg"]
    _make_output_images(out_dir, names)
    config = ProjectConfig(layout=Layout(columns=2, rows=10))
    records = _make_records(out_dir, names)
    render_gallery(out_dir, config, records)
    item_html = (out_dir / "a_item.html").read_text(encoding="utf-8")
    assert 'download' in item_html
    assert '💾' in item_html


def test_render_gallery_copies_css(tmp_path):
    out_dir = tmp_path / "out"
    names = ["a.jpg"]
    _make_output_images(out_dir, names)
    config = ProjectConfig()
    records = _make_records(out_dir, names)
    render_gallery(out_dir, config, records)
    assert (out_dir / "style.css").exists()


def _render(tmp_path, records, **cfg):
    out = tmp_path / "out"
    out.mkdir()
    render_gallery(out, ProjectConfig(site_url="https://x.example", **cfg), records)
    return out


def _rec(**kw):
    base = dict(filename="a.jpg", output_path="a.jpg", thumb_path="a_thumb.jpg",
                display_path="a.jpg", caption="", alt="", include=True,
                date="2026-01-01", size="1 MiB", og_path="a_og.jpg", exif=None)
    base.update(kw)
    return base


def test_og_image_points_at_og_jpg(tmp_path):
    out = _render(tmp_path, [_rec()], social_previews=True)
    html = (out / "a_item.html").read_text(encoding="utf-8")
    assert "a_og.jpg" in html and 'property="og:image"' in html


def test_social_tags_suppressed_when_disabled(tmp_path):
    out = _render(tmp_path, [_rec()], social_previews=False)
    html = (out / "a_item.html").read_text(encoding="utf-8")
    assert 'property="og:image"' not in html


def test_exif_block_renders_present_fields_only(tmp_path):
    out = _render(tmp_path, [_rec(exif={"camera": "CANON EOS R5", "exposure": "ƒ/2.8 · ISO 100 · 1/250s"})], exif_display=True)
    html = (out / "a_item.html").read_text(encoding="utf-8")
    assert "CANON EOS R5" in html and "class=\"exif\"" in html
    assert "White balance" not in html   # absent field must not appear


def test_exif_block_hidden_without_exif(tmp_path):
    out = _render(tmp_path, [_rec(exif=None)], exif_display=True)
    assert "class=\"exif\"" not in (out / "a_item.html").read_text(encoding="utf-8")


def test_download_button_on_index_and_all(tmp_path):
    out = tmp_path / "out"; out.mkdir()
    render_gallery(out, ProjectConfig(gallery_zip=True), [_rec()],
                   gallery_zip="My_Gallery.zip", gallery_zip_size="3 MiB")
    for page in ("index.html", "all.html"):
        html = (out / page).read_text(encoding="utf-8")
        assert "My_Gallery.zip" in html
        assert "Download all (3 MiB)" in html


def test_no_download_button_without_zip(tmp_path):
    out = tmp_path / "out"; out.mkdir()
    render_gallery(out, ProjectConfig(), [_rec()])
    assert "download-btn" not in (out / "index.html").read_text(encoding="utf-8")


def test_page_og_image_uses_og_path_and_gated(tmp_path):
    on_dir = tmp_path / "on"
    on_dir.mkdir()
    out = _render(on_dir, [_rec()], social_previews=True)
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "a_og.jpg" in html and 'property="og:image"' in html
    assert "a_thumb.jpg" not in html.split("og:image")[1][:200]  # og:image is not the thumb

    off_dir = tmp_path / "off"
    off_dir.mkdir()
    out2 = _render(off_dir, [_rec()], social_previews=False)
    assert 'property="og:image"' not in (out2 / "index.html").read_text(encoding="utf-8")


def test_promo_footer_hidden_by_default(tmp_path):
    out = _render(tmp_path, [_rec()])  # simple_gals_promo defaults to False
    for page in ("index.html", "a_item.html"):
        assert "generated with simpleGals" not in (out / page).read_text(encoding="utf-8")


def test_promo_footer_shown_when_enabled(tmp_path):
    out = _render(tmp_path, [_rec()], simple_gals_promo=True)
    for page in ("index.html", "a_item.html"):
        assert "generated with simpleGals" in (out / page).read_text(encoding="utf-8")
