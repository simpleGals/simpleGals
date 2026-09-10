import re
import shutil
from pathlib import Path
import pytest
from simplegals import PROJECT_URL, __version__
from simplegals.core.config import Layout, ProjectConfig
from simplegals.core.template import build_image_records, render_gallery, resolve_cover


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
    out = _render(
        tmp_path,
        [_rec(exif={"camera": "CANON EOS R5", "exposure": "ƒ/2.8 · ISO 100 · 1/250s"})],
        exif_display=True,
    )
    html = (out / "a_item.html").read_text(encoding="utf-8")
    assert "CANON EOS R5" in html and "class=\"exif\"" in html
    assert "White balance" not in html   # absent field must not appear


def test_exif_block_hidden_without_exif(tmp_path):
    out = _render(tmp_path, [_rec(exif=None)], exif_display=True)
    assert "class=\"exif\"" not in (out / "a_item.html").read_text(encoding="utf-8")


def test_download_button_on_index_and_all(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    render_gallery(out, ProjectConfig(gallery_zip=True), [_rec()],
                   gallery_zip="My_Gallery.zip", gallery_zip_size="3 MiB")
    for page in ("index.html", "all.html"):
        html = (out / page).read_text(encoding="utf-8")
        assert "My_Gallery.zip" in html
        assert "Download all (3 MiB)" in html


def test_no_download_button_without_zip(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
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
        assert 'class="generated-by"' not in (out / page).read_text(encoding="utf-8")


def test_promo_footer_shown_with_version_and_url(tmp_path):
    out = _render(tmp_path, [_rec()], simple_gals_promo=True)
    for page in ("index.html", "a_item.html"):
        html = (out / page).read_text(encoding="utf-8")
        assert 'class="generated-by"' in html
        assert f"Generated with simpleGals {__version__}" in html
        assert PROJECT_URL in html


def test_generator_meta_present_on_every_page(tmp_path):
    out = _render(tmp_path, [_rec()], social_previews=False, simple_gals_promo=False)
    for page in ("index.html", "a_item.html"):
        html = (out / page).read_text(encoding="utf-8")
        assert f'<meta name="generator" content="simpleGals {__version__}">' in html


def test_branding_comment_top_and_bottom(tmp_path):
    out = _render(tmp_path, [_rec()], social_previews=False, simple_gals_promo=False)
    marker = f"<!-- Generated with simpleGals {__version__} | {PROJECT_URL} -->"
    for page in ("index.html", "a_item.html"):
        html = (out / page).read_text(encoding="utf-8")
        assert html.count(marker) == 2          # top and bottom
        assert html.rstrip().endswith(marker)   # bottom is the last line


def test_project_url_is_org_url():
    assert PROJECT_URL == "https://github.com/simplegals/simpleGals"


def test_resolve_cover_defaults_to_first():
    recs = [{"filename": "a.jpg"}, {"filename": "b.jpg"}]
    assert resolve_cover("", recs)["filename"] == "a.jpg"


def test_resolve_cover_selects_named():
    recs = [{"filename": "a.jpg"}, {"filename": "b.jpg"}]
    assert resolve_cover("b.jpg", recs)["filename"] == "b.jpg"


def test_resolve_cover_missing_falls_back_to_first():
    recs = [{"filename": "a.jpg"}, {"filename": "b.jpg"}]
    assert resolve_cover("ghost.jpg", recs)["filename"] == "a.jpg"


def test_resolve_cover_empty_returns_none():
    assert resolve_cover("x.jpg", []) is None


def test_index_og_image_uses_cover_not_first(tmp_path):
    recs = [
        _rec(filename="a.jpg", og_path="a_og.jpg", thumb_path="a_thumb.jpg"),
        _rec(filename="b.jpg", og_path="b_og.jpg", thumb_path="b_thumb.jpg"),
    ]
    out = _render(tmp_path, recs, social_previews=True, cover="b.jpg")
    html = (out / "index.html").read_text(encoding="utf-8")
    assert 'property="og:image" content="https://x.example/b_og.jpg"' in html
    assert "a_og.jpg" not in html.split("og:image")[1][:200]


# --- 0.4.0 template extensibility ------------------------------------------

_FIXTURE_PAGE = "PAGE total={{ total_images }} {% for image in images %}{{ image.filename }} {% endfor %}"
_FIXTURE_ITEM = "ITEM n={{ image_number }} t={{ total_images }} p={{ percent }} f={{ image.filename }}"


def _make_template(dir_path, *, with_css, with_assets,
                   page=_FIXTURE_PAGE, item=_FIXTURE_ITEM):
    """Write a minimal custom template dir for render_gallery to consume."""
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / "page.html.j2").write_text(page, encoding="utf-8")
    (dir_path / "item.html.j2").write_text(item, encoding="utf-8")
    if with_css:
        (dir_path / "style.css").write_text("body{}", encoding="utf-8")
    if with_assets:
        sub = dir_path / "assets" / "sub"
        sub.mkdir(parents=True, exist_ok=True)
        (dir_path / "assets" / "marker.png").write_bytes(b"PNG")
        (sub / "note.txt").write_text("hi", encoding="utf-8")
    return dir_path


def test_missing_style_css_does_not_crash(tmp_path):
    tpl = _make_template(tmp_path / "tpl", with_css=False, with_assets=False)
    out = tmp_path / "out"
    render_gallery(out, ProjectConfig(template=str(tpl)), _make_records(out, ["a.jpg"]))
    assert (out / "index.html").exists()
    assert not (out / "style.css").exists()


def test_style_css_copied_when_present(tmp_path):
    tpl = _make_template(tmp_path / "tpl", with_css=True, with_assets=False)
    out = tmp_path / "out"
    render_gallery(out, ProjectConfig(template=str(tpl)), _make_records(out, ["a.jpg"]))
    assert (out / "style.css").exists()


def test_template_assets_copied_recursively(tmp_path):
    tpl = _make_template(tmp_path / "tpl", with_css=False, with_assets=True)
    out = tmp_path / "out"
    render_gallery(out, ProjectConfig(template=str(tpl)), _make_records(out, ["a.jpg"]))
    assert (out / "assets" / "marker.png").exists()
    assert (out / "assets" / "sub" / "note.txt").exists()


def test_no_assets_dir_produces_no_output(tmp_path):
    tpl = _make_template(tmp_path / "tpl", with_css=False, with_assets=False)
    out = tmp_path / "out"
    render_gallery(out, ProjectConfig(template=str(tpl)), _make_records(out, ["a.jpg"]))
    assert not (out / "assets").exists()


def test_assets_copy_on_rebuild_does_not_fail(tmp_path):
    tpl = _make_template(tmp_path / "tpl", with_css=False, with_assets=True)
    out = tmp_path / "out"
    recs = _make_records(out, ["a.jpg"])
    render_gallery(out, ProjectConfig(template=str(tpl)), recs)
    render_gallery(out, ProjectConfig(template=str(tpl)), recs)  # rebuild into populated out/
    assert (out / "assets" / "marker.png").exists()


def test_item_position_context(tmp_path):
    tpl = _make_template(tmp_path / "tpl", with_css=False, with_assets=False)
    out = tmp_path / "out"
    render_gallery(out, ProjectConfig(template=str(tpl)), _make_records(out, ["a.jpg", "b.jpg", "c.jpg"]))
    assert "n=1 t=3 p=33" in (out / "a_item.html").read_text(encoding="utf-8")
    assert "n=2 t=3 p=66" in (out / "b_item.html").read_text(encoding="utf-8")  # interior item, 200//3
    assert "n=3 t=3 p=100" in (out / "c_item.html").read_text(encoding="utf-8")


def test_percent_floor_matches_source_export(tmp_path):
    tpl = _make_template(tmp_path / "tpl", with_css=False, with_assets=False)
    out = tmp_path / "out"
    names = [f"{i}.jpg" for i in range(1, 90)]  # 89 images, mirrors the retro source
    render_gallery(out, ProjectConfig(template=str(tpl)), _make_records(out, names))
    assert "n=1 t=89 p=1" in (out / "1_item.html").read_text(encoding="utf-8")
    assert "n=2 t=89 p=2" in (out / "2_item.html").read_text(encoding="utf-8")


def test_total_images_on_grid_page(tmp_path):
    tpl = _make_template(tmp_path / "tpl", with_css=False, with_assets=False)
    out = tmp_path / "out"
    render_gallery(out, ProjectConfig(template=str(tpl)), _make_records(out, ["a.jpg", "b.jpg"]))
    assert "total=2" in (out / "index.html").read_text(encoding="utf-8")


def test_zero_images_renders_without_crash(tmp_path):
    # Guards the percent divisor: an empty set must render a grid page and never
    # evaluate (i+1)*100//len(records).
    tpl = _make_template(tmp_path / "tpl", with_css=False, with_assets=False)
    out = tmp_path / "out"
    render_gallery(out, ProjectConfig(template=str(tpl)), _make_records(out, []))
    assert (out / "index.html").exists()
    assert "total=0" in (out / "index.html").read_text(encoding="utf-8")


def test_item_nav_filename_is_wrapped_for_truncation(tmp_path):
    """The prev/next filename sits in its own span so CSS can ellipse it."""
    out_dir = tmp_path / "out"
    long_name = "2026-09-06_Sept_Weekend_Shooting_Pillars_Focus_Stack_Attempt_Three.jpg"
    names = [long_name, "b.jpg", "c.jpg"]
    _make_output_images(out_dir, names)
    config = ProjectConfig(layout=Layout(columns=2, rows=10))
    render_gallery(out_dir, config, _make_records(out_dir, names))
    item_html = (out_dir / "b_item.html").read_text(encoding="utf-8")

    nav = item_html.split('<nav class="item-nav">')[1].split("</nav>")[0]
    assert f'<span class="nav-name">{long_name}</span>' in nav
    assert '<span class="nav-name">c.jpg</span>' in nav


def test_item_nav_arrows_are_outside_the_truncating_span(tmp_path):
    """An arrow inside the truncating span would be eaten by the ellipsis."""
    out_dir = tmp_path / "out"
    names = ["a.jpg", "b.jpg", "c.jpg"]
    _make_output_images(out_dir, names)
    config = ProjectConfig(layout=Layout(columns=2, rows=10))
    render_gallery(out_dir, config, _make_records(out_dir, names))
    nav = (out_dir / "b_item.html").read_text(encoding="utf-8")
    nav = nav.split('<nav class="item-nav">')[1].split("</nav>")[0]

    for arrow in ("←", "→"):
        assert f'<span class="nav-arrow">{arrow}</span>' in nav
    for name_span in re.findall(r'<span class="nav-name">(.*?)</span>', nav):
        assert "←" not in name_span and "→" not in name_span


def test_pagination_repeated_below_the_grid(tmp_path):
    """Issue #15: the page links must also appear after the grid."""
    out_dir = tmp_path / "out"
    names = [f"img{i}.jpg" for i in range(6)]
    _make_output_images(out_dir, names)
    config = ProjectConfig(layout=Layout(columns=2, rows=2))
    render_gallery(out_dir, config, _make_records(out_dir, names))
    html = (out_dir / "index.html").read_text(encoding="utf-8")
    grid_end = html.index("</div>", html.index('class="gallery-grid"'))
    before, after = html[:grid_end], html[grid_end:]
    assert 'class="pagination"' in before
    assert "pagination-bottom" in after
    assert "Next →" in after
    assert "View all" in after


def test_top_and_bottom_pagination_are_identical(tmp_path):
    """Both rows come from one macro, so 'View all' and the download button match."""
    out_dir = tmp_path / "out"
    names = [f"img{i}.jpg" for i in range(6)]
    _make_output_images(out_dir, names)
    config = ProjectConfig(layout=Layout(columns=2, rows=2))
    render_gallery(out_dir, config, _make_records(out_dir, names))
    html = (out_dir / "index.html").read_text(encoding="utf-8")
    navs = re.findall(r'<nav class="pagination[^"]*">(.*?)</nav>', html, re.S)
    assert len(navs) == 2
    assert navs[0] == navs[1]


def test_all_page_bottom_row_only_when_zip_enabled(tmp_path):
    out_dir = tmp_path / "out"
    names = ["a.jpg", "b.jpg"]
    _make_output_images(out_dir, names)
    config = ProjectConfig(layout=Layout(columns=2, rows=10))
    render_gallery(out_dir, config, _make_records(out_dir, names))
    assert "pagination" not in (out_dir / "all.html").read_text(encoding="utf-8")
