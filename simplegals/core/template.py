from __future__ import annotations

import shutil
from math import ceil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .config import ProjectConfig

_BUILTIN_TEMPLATE_DIR = Path(__file__).parent.parent / "template"


def _get_env(config: ProjectConfig) -> tuple[Environment, Path]:
    template_dir = Path(config.template) if config.template else _BUILTIN_TEMPLATE_DIR
    env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)
    return env, template_dir


def build_image_records(
    out_dir: Path,
    config: ProjectConfig,
    raw_records: list[dict],
) -> list[dict]:
    """Enrich raw image records with item_page path. Filters excluded images."""
    records = []
    for r in raw_records:
        if not r.get("include", True):
            continue
        stem = Path(r["filename"]).stem
        records.append({**r, "item_page": f"{stem}_item.html"})
    return records


def render_gallery(
    out_dir: Path,
    config: ProjectConfig,
    raw_records: list[dict],
    template_dir: Path | None = None,
    gallery_zip: str | None = None,
    gallery_zip_size: str | None = None,
) -> list[Path]:
    """Render all HTML output. Returns list of generated HTML paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    env, tpl_dir = _get_env(config)

    css_src = tpl_dir / "style.css"
    css_dest = out_dir / "style.css"
    shutil.copy(css_src, css_dest)

    records = build_image_records(out_dir, config, raw_records)
    per_page = config.layout.columns * config.layout.rows
    total_pages = max(1, ceil(len(records) / per_page))

    page_tpl = env.get_template("page.html.j2")
    item_tpl = env.get_template("item.html.j2")

    generated: list[Path] = []
    base_ctx = {
        "title": config.title,
        "description": config.description,
        "copyright": config.copyright,
        "author": config.author,
        "site_url": config.site_url.rstrip("/") if config.site_url else "",
        "columns": config.layout.columns,
        "css_path": "style.css",
        "total_pages": total_pages,
        "gallery_zip": gallery_zip,
        "gallery_zip_size": gallery_zip_size,
        "social_previews": config.social_previews,
        "exif_display": config.exif_display,
        "simple_gals_promo": config.simple_gals_promo,
    }

    for page_num in range(1, total_pages + 1):
        start = (page_num - 1) * per_page
        page_images = records[start : start + per_page]
        ctx = {
            **base_ctx,
            "images": page_images,
            "current_page": page_num,
            "is_all_page": False,
        }
        filename = "index.html" if page_num == 1 else f"page-{page_num}.html"
        dest = out_dir / filename
        dest.write_text(page_tpl.render(**ctx), encoding="utf-8")
        generated.append(dest)

    all_dest = out_dir / "all.html"
    all_dest.write_text(
        page_tpl.render(**{**base_ctx, "images": records, "is_all_page": True, "current_page": 1}),
        encoding="utf-8",
    )
    generated.append(all_dest)

    for i, record in enumerate(records):
        stem = Path(record["filename"]).stem
        ctx = {
            **base_ctx,
            "image": record,
            "prev_image": records[i - 1] if i > 0 else None,
            "next_image": records[i + 1] if i < len(records) - 1 else None,
        }
        dest = out_dir / f"{stem}_item.html"
        dest.write_text(item_tpl.render(**ctx), encoding="utf-8")
        generated.append(dest)

    return generated
