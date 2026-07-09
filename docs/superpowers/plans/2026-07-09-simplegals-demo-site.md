# simpleGals Demo Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `simplegals.github.io` showcase: one photo set rendered three ways (dark, bright, retro-fruit) under a branded landing page, built fresh in CI and deployable to GitHub Pages.

**Architecture:** A fresh git repo at `/Users/tbielawa/Projects/simplegals.github.io`. One `shared/in/` photo folder, symlinked into three galleries. Each gallery builds with simpleGals 0.4.0 (from PyPI) into its own `out/`. `build_index.py` reads each `out/gallery.json` plus `site.json`, renders the landing, and assembles a `_site/` deploy tree. GitHub Actions rebuilds and deploys on push and on a release dispatch.

**Tech Stack:** Python 3.12, simpleGals >= 0.4.0 (from PyPI), Jinja2 (via simpleGals), Pillow (via simpleGals), pytest. GitHub Actions Pages artifact deploy.

## Global Constraints

- Repo root: `/Users/tbielawa/Projects/simplegals.github.io` (referred to below as `$SITE`). It already exists (holds a `.superpowers/` brainstorm dir); this plan runs `git init` there.
- Build venv: `$SITE/.venv`, created in Task 1; `simpleGals` CLI is `$SITE/.venv/bin/simpleGals`.
- The simpleGals CLI is `simpleGals build --force` (capital `G`, `build` subcommand, `--force` on the subcommand). On the case-sensitive Linux runner only `simpleGals` resolves.
- Only source originals are committed. `out/`, `.meta/`, `_site/`, `.venv/`, `.superpowers/`, `__pycache__/` are gitignored.
- `galleries/<slug>/in` is a RELATIVE symlink to `../../shared/in`.
- `simpleGal.json` nests grid size under `"layout": {"columns": N, "rows": M}`. `template` is a top-level string path resolved relative to the build cwd (the gallery dir).
- Per-gallery `site_url = https://simplegals.github.io/<slug>/`.
- Prose (README, comments) uses plain punctuation, no em-dashes.
- Commits use conventional-commit prefixes. Do NOT add any `Co-Authored-By` trailer or Claude/generated-by credit.
- The retro-fruit template reuses the 18 original PNG slices from `/Users/tbielawa/Projects/Minecraft-GrandLibrary/Resources/` verbatim.

---

### Task 1: Repo scaffold, gitignore, venv

**Files:**
- Create: `$SITE/.gitignore`, `$SITE/README.md`
- Create dirs: `$SITE/shared/in`, `$SITE/galleries`, `$SITE/templates`, `$SITE/scripts`, `$SITE/tests`, `$SITE/.github/workflows`

**Interfaces:**
- Produces: an initialized git repo and a `.venv` with `simplegals>=0.4.0` and `pytest` installed, used by every later task.

- [ ] **Step 1: Init repo and directory skeleton**

```bash
SITE=/Users/tbielawa/Projects/simplegals.github.io
git -C "$SITE" init -q
mkdir -p "$SITE/shared/in" "$SITE/galleries" "$SITE/templates" "$SITE/scripts" "$SITE/tests" "$SITE/.github/workflows"
```

- [ ] **Step 2: Write `.gitignore`**

Create `$SITE/.gitignore`:

```gitignore
# derived build output, never committed
out/
.meta/
_site/
# local tooling
.venv/
.superpowers/
__pycache__/
*.pyc
```

- [ ] **Step 3: Write `README.md`**

Create `$SITE/README.md`:

```markdown
# simpleGals Showcase (simplegals.github.io)

One photo set, rendered three ways by [simpleGals](https://pypi.org/project/simplegals/):
a dark theme (stock), a bright inverse (forked CSS), and "retro-fruit", a 2010
Apple-style web gallery rebuilt as a custom template. A branded landing page ties
them together.

## Layout

- `shared/in/` the one photo set. The only binaries in git. Replace these with your
  own shots; nothing else changes.
- `galleries/<slug>/` one `simpleGal.json` per gallery; `in` symlinks to `shared/in`.
- `templates/` the landing (`index.html.j2`) plus the `bright` and `retro-fruit`
  template dirs.
- `site.json` landing configuration (title, tagline, hero, per-card badge/blurb).
- `build_index.py` renders the landing and assembles `_site/`.

## Build locally

    python -m venv .venv && .venv/bin/pip install "simplegals>=0.4.0"
    scripts/build_local.sh
    open _site/index.html

Derived `out/`, `.meta/`, and `_site/` are never committed; CI rebuilds them.

## Adding your photos

Drop images into `shared/in/`, optionally set each gallery's `cover` in its
`simpleGal.json` (the `dark` cover doubles as the site hero), and rebuild.
```

- [ ] **Step 4: Create the build venv and install deps**

```bash
SITE=/Users/tbielawa/Projects/simplegals.github.io
python3 -m venv "$SITE/.venv"
"$SITE/.venv/bin/pip" install -q --upgrade pip
"$SITE/.venv/bin/pip" install -q "simplegals>=0.4.0" pytest
"$SITE/.venv/bin/simpleGals" --help >/dev/null && echo "simpleGals OK"
"$SITE/.venv/bin/python" -c "import simplegals; print('simplegals', simplegals.__version__)"
```

Expected: `simpleGals OK` and `simplegals 0.4.0` (or newer).

- [ ] **Step 5: Commit**

```bash
cd /Users/tbielawa/Projects/simplegals.github.io
git add .gitignore README.md
git commit -m "chore: scaffold simplegals.github.io repo"
```

---

### Task 2: Placeholder photo generator

**Files:**
- Create: `$SITE/scripts/gen_placeholders.py`
- Create (generated, committed): `$SITE/shared/in/img-01.jpg` .. `img-36.jpg`, `$SITE/shared/in/README.md`

**Interfaces:**
- Produces: 36 committed placeholder JPEGs named `img-01.jpg` .. `img-36.jpg` that later galleries render.

- [ ] **Step 1: Write the generator**

Create `$SITE/scripts/gen_placeholders.py`:

```python
#!/usr/bin/env python3
"""Generate throwaway placeholder photos into shared/in/.

These prove the build pipeline. Replace them with real shots by clearing
shared/in/ and dropping your own images; nothing else changes.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

IN = Path(__file__).resolve().parent.parent / "shared" / "in"
SIZES = [(1600, 1067), (1067, 1600), (1600, 1200), (1400, 1400)]
PALETTE = [(31, 41, 61), (61, 31, 51), (31, 61, 45), (61, 52, 26),
           (20, 40, 70), (70, 30, 40), (40, 60, 30)]


def _font(px: int):
    for path in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(path, px)
        except Exception:
            continue
    return ImageFont.load_default()


def main() -> None:
    IN.mkdir(parents=True, exist_ok=True)
    for i in range(1, 37):
        w, h = SIZES[i % len(SIZES)]
        base = PALETTE[i % len(PALETTE)]
        img = Image.new("RGB", (w, h), base)
        d = ImageDraw.Draw(img)
        for y in range(h):
            t = y / h
            d.line([(0, y), (w, y)], fill=tuple(min(255, int(c * (0.55 + 0.7 * t))) for c in base))
        label = f"{i:02d}"
        font = _font(int(h * 0.30))
        box = d.textbbox((0, 0), label, font=font)
        d.text(((w - (box[2] - box[0])) / 2, (h - (box[3] - box[1])) / 2 - box[1]),
               label, fill=(245, 245, 245), font=font)
        img.save(IN / f"img-{i:02d}.jpg", quality=85)
    print(f"wrote 36 images to {IN}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Generate the images**

```bash
SITE=/Users/tbielawa/Projects/simplegals.github.io
"$SITE/.venv/bin/python" "$SITE/scripts/gen_placeholders.py"
ls "$SITE/shared/in" | wc -l    # expect 36
```

Expected: `wrote 36 images ...` and a count of `36`.

- [ ] **Step 3: Write `shared/in/README.md`**

Create `$SITE/shared/in/README.md`:

```markdown
# Photo set

These `img-NN.jpg` files are throwaway placeholders generated by
`scripts/gen_placeholders.py`. Replace them with your own photos: delete these,
drop your images here, and rebuild. Every gallery renders from this one folder.
```

- [ ] **Step 4: Commit**

```bash
cd /Users/tbielawa/Projects/simplegals.github.io
git add scripts/gen_placeholders.py shared/in
git commit -m "feat: add placeholder photo generator and 36 sample images"
```

---

### Task 3: The three galleries (configs + symlinks)

**Files:**
- Create: `$SITE/galleries/{dark,bright,retro-fruit}/simpleGal.json`
- Create: relative symlinks `$SITE/galleries/{dark,bright,retro-fruit}/in -> ../../shared/in`

**Interfaces:**
- Consumes: `shared/in` from Task 2.
- Produces: three build-ready gallery directories. `bright` and `retro-fruit` reference template dirs created in Tasks 4 and 5.

- [ ] **Step 1: Write `galleries/dark/simpleGal.json`**

```json
{
  "title": "Dark",
  "description": "The default simpleGals look: near-black, quiet, lets the photos glow.",
  "cover": "img-08.jpg",
  "author": "simpleGals Showcase",
  "site_url": "https://simplegals.github.io/dark/",
  "social_previews": true,
  "exif_display": true,
  "layout": { "columns": 4, "rows": 5 }
}
```

- [ ] **Step 2: Write `galleries/bright/simpleGal.json`**

```json
{
  "title": "Bright",
  "description": "The same layout inverted to dark-on-light. Airy, clean, gallery-wall bright.",
  "cover": "img-08.jpg",
  "author": "simpleGals Showcase",
  "site_url": "https://simplegals.github.io/bright/",
  "social_previews": true,
  "exif_display": true,
  "template": "../../templates/bright",
  "layout": { "columns": 4, "rows": 5 }
}
```

- [ ] **Step 3: Write `galleries/retro-fruit/simpleGal.json`**

```json
{
  "title": "Retro-fruit",
  "description": "A 2010 Apple-style web gallery, rebuilt 1:1 from its original sliced-image chrome.",
  "cover": "img-21.jpg",
  "author": "simpleGals Showcase",
  "site_url": "https://simplegals.github.io/retro-fruit/",
  "social_previews": false,
  "exif_display": false,
  "template": "../../templates/retro-fruit",
  "layout": { "columns": 3, "rows": 10 }
}
```

- [ ] **Step 4: Create the relative symlinks**

```bash
SITE=/Users/tbielawa/Projects/simplegals.github.io
for slug in dark bright retro-fruit; do
  ( cd "$SITE/galleries/$slug" && ln -s ../../shared/in in )
done
ls -l "$SITE/galleries/dark/in"          # -> ../../shared/in
ls "$SITE/galleries/dark/in" | wc -l     # expect 36 (resolves through the link)
```

Expected: the symlink shows `in -> ../../shared/in` and lists 36 files.

- [ ] **Step 5: Commit**

```bash
cd /Users/tbielawa/Projects/simplegals.github.io
git add galleries
git commit -m "feat: add three gallery configs sharing one input via symlink"
```

---

### Task 4: The `bright` template (forked stock + light CSS)

**Files:**
- Create: `$SITE/templates/bright/page.html.j2`, `item.html.j2` (copied from the installed stock template)
- Create: `$SITE/templates/bright/style.css` (light inverse theme)

**Interfaces:**
- Consumes: the installed simpleGals stock template.
- Produces: a template dir the `bright` gallery renders with, producing dark-on-light pages.

- [ ] **Step 1: Copy the stock templates verbatim**

```bash
SITE=/Users/tbielawa/Projects/simplegals.github.io
STOCK=$("$SITE/.venv/bin/python" -c "import simplegals,pathlib;print(pathlib.Path(simplegals.__file__).parent/'template')")
mkdir -p "$SITE/templates/bright"
cp "$STOCK/page.html.j2" "$SITE/templates/bright/page.html.j2"
cp "$STOCK/item.html.j2" "$SITE/templates/bright/item.html.j2"
ls "$SITE/templates/bright"
```

Expected: `item.html.j2  page.html.j2` copied. (These are unchanged forks; the light look comes entirely from `style.css`.)

- [ ] **Step 2: Write the light `style.css`**

Create `$SITE/templates/bright/style.css` (same selectors as stock, inverted palette):

```css
/* Bright: a light inverse of the stock simpleGals theme (demo fork). */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body { font-family: system-ui, sans-serif; background: #faf9f7; color: #1a1a1a; padding: 1rem; }

header { margin-bottom: 1.5rem; }
header h1 { font-size: 1.6rem; margin-bottom: 0.25rem; }
header p  { color: #666; font-size: 0.9rem; }

nav.pagination { display: flex; gap: 0.5rem; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; }
nav.pagination a, nav.pagination span { padding: 0.3rem 0.7rem; border: 1px solid #ccc; border-radius: 4px; text-decoration: none; color: #1a1a1a; font-size: 0.85rem; }
nav.pagination a:hover { background: #ececec; }
nav.pagination .current { background: #ddd; border-color: #bbb; }
nav.pagination .all-link { margin-left: auto; }

.gallery-grid { display: grid; grid-template-columns: repeat(var(--columns, 4), 1fr); gap: 0.75rem; }
.gallery-item a { display: block; }
.gallery-item img { width: 100%; height: 200px; object-fit: cover; border-radius: 4px; display: block; box-shadow: 0 0 0 0 transparent; transition: box-shadow 175ms ease; }
.gallery-item a:hover img { box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.35), 0 2px 12px 2px rgba(0, 0, 0, 0.18); }
.gallery-item .caption { font-size: 0.8rem; color: #666; margin-top: 0.3rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.item-page { max-width: 900px; margin: 0 auto; }
.item-page img { width: 100%; height: auto; border-radius: 4px; display: block; margin: 1rem 0; }
.item-meta { font-size: 0.85rem; color: #666; margin-bottom: 1rem; }
.item-meta span { margin-right: 1.5rem; }

.share-wrap { display: inline-flex; align-items: center; gap: 0.4rem; }
.share-btn { background: none; border: none; cursor: pointer; padding: 0; font-size: inherit; color: inherit; }
.share-hint { font-size: 0.8rem; color: transparent; white-space: nowrap; transition: color 150ms ease; }
.share-wrap:hover .share-hint { color: #666; }

nav.item-nav { display: flex; justify-content: space-between; margin-top: 1rem; }
nav.item-nav a { padding: 0.4rem 1rem; border: 1px solid #ccc; border-radius: 4px; text-decoration: none; color: #1a1a1a; }
nav.item-nav a:hover { background: #ececec; }

footer { margin-top: 2rem; color: #999; font-size: 0.75rem; }
.back-link { color: inherit; text-decoration: none; display: inline-flex; align-items: baseline; gap: 0.75rem; }
.back-hint { font-size: 0.7rem; font-weight: normal; color: transparent; white-space: nowrap; transition: color 150ms ease; }
.back-link:hover .back-hint { color: #999; }

.key-legend { position: fixed; top: 0.75rem; right: 1rem; font-size: 0.65rem; color: #c2185b; pointer-events: none; letter-spacing: 0.02em; }
.key-legend kbd { font-family: monospace; font-style: normal; }

.generated-by { text-align: center; margin-top: 0.75rem; }
.generated-by a { color: #999; text-decoration: none; }
.generated-by a:hover { color: #555; }

.download-btn { display: inline-block; padding: 0.3rem 0.7rem; font-size: 0.85rem; border: 1px solid #2a8; border-radius: 4px; background: rgba(34, 136, 136, 0.10); color: inherit; text-decoration: none; }
.download-btn:hover { background: rgba(34, 136, 136, 0.20); }
.download-row { margin: 0.5rem 0 1rem; }

:focus-visible { outline: 2px solid #c2185b; outline-offset: 2px; }

.exif { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0.5rem 1.5rem; margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #ddd; }
.exif .exif-field { margin: 0; }
.exif dt { font-size: 0.7rem; text-transform: uppercase; letter-spacing: .04em; color: #999; }
.exif dd { margin: 0; font-size: 0.85rem; color: #333; }
```

- [ ] **Step 3: Verify the bright gallery builds light**

```bash
SITE=/Users/tbielawa/Projects/simplegals.github.io
( cd "$SITE/galleries/bright" && "$SITE/.venv/bin/simpleGals" build --force )
grep -q "background: #faf9f7" "$SITE/galleries/bright/out/style.css" && echo "LIGHT CSS OK"
test -f "$SITE/galleries/bright/out/index.html" && echo "INDEX OK"
```

Expected: `LIGHT CSS OK` and `INDEX OK`. (`out/` is gitignored.)

- [ ] **Step 4: Commit**

```bash
cd /Users/tbielawa/Projects/simplegals.github.io
git add templates/bright
git commit -m "feat: add bright template (stock fork with light inverse CSS)"
```

---

### Task 5: The `retro-fruit` template (1:1 revival)

**Files:**
- Create: `$SITE/templates/retro-fruit/assets/*.png` (the 18 original slices, copied)
- Create: `$SITE/templates/retro-fruit/page.html.j2`, `item.html.j2`
- Create: `$SITE/tests/test_retro_template.py`

**Interfaces:**
- Consumes: simpleGals 0.4.0 context (`images`, `columns`, `current_page`, `total_pages`, `total_images`, `prev_image`, `next_image`, `image_number`, `percent`, `image.thumb_path`, `image.item_page`, `image.display_path`, `version`, `project_url`) and the 0.4.0 `assets/` copy.
- Produces: a custom template that renders the 2010 look; consumed by the `retro-fruit` gallery.

- [ ] **Step 1: Copy the 18 original slice PNGs**

```bash
SITE=/Users/tbielawa/Projects/simplegals.github.io
mkdir -p "$SITE/templates/retro-fruit/assets"
cp /Users/tbielawa/Projects/Minecraft-GrandLibrary/Resources/*.png "$SITE/templates/retro-fruit/assets/"
ls "$SITE/templates/retro-fruit/assets" | wc -l   # expect 18
```

Expected: `18`.

- [ ] **Step 2: Write `templates/retro-fruit/page.html.j2`**

Create the grid template (reproduces the original top nav + 9-slice rounded thumb boxes; nav states keyed off `current_page`/`total_pages`):

```jinja
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<!-- Generated with simpleGals {{ version }} | {{ project_url }} -->
<html>
	<head>
		<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
		<meta name="generator" content="simpleGals {{ version }}">
		<title>{{ title }}</title>
	</head>
	<body bgcolor="#ffffff" text="#000000">
		<table background="assets/button_gradient.png" cellpadding=0 cellspacing=0 width="100%" height=29>
			<tr height=2><td><img width=0 height=0/></td></tr>
			<tr height=19>
				<td><img width=10 height=0/></td>
				<td>{% if current_page > 1 %}<a href="{% if current_page == 2 %}index.html{% else %}page-{{ current_page - 1 }}.html{% endif %}"><img border="0" src="assets/previous1.png" alt="previous"></a>{% else %}<img border="0" src="assets/previous0.png" alt="previous">{% endif %}</td>
				<td>{% if current_page < total_pages %}<a href="page-{{ current_page + 1 }}.html"><img border="0" src="assets/next1.png" alt="next"></a>{% else %}<img border="0" src="assets/next0.png" alt="next">{% endif %}</td>
				<td><img width=10 height=0/></td>
				<td><a href="index.html"><img border="0" src="assets/home.png"></a></td>
				<td><img width=10 height=0/></td>
				<td width="100%"></td>
				<td valign="center"><font size=2>{{ total_images }}&nbsp;images</font></td>
				<td><img width=10 height=0/></td>
			</tr>
		</table>

		<p><br>

		<h2 align="center">{{ title }}</h2>
		<table cellspacing="2" cellpadding="2" width="100%">
		{% for row in images|batch(columns) %}
			<tr>
			{% for image in row %}
				<td align="center" width="{{ 100 // columns }}%">
					<table cellspacing=0 cellpadding=0>
						<tr>
							<td width=9 height=6 background="assets/top_left.png"></td>
							<td height=6 background="assets/top_middle.png"></td>
							<td width=8 height=6 background="assets/top_right.png"></td>
						</tr>
						<tr>
							<td width=9 background="assets/left.png"></td>
							<td width=240><a href="{{ image.item_page }}"><img border="0" width=240 alt="" src="{{ image.thumb_path }}"></a></td>
							<td width=8 background="assets/right.png"></td>
						</tr>
						<tr>
							<td width=9 height=13 background="assets/bottom_left.png"></td>
							<td><table height=13 width="100%" cellspacing=0 cellpadding=0>
								<tr>
									<td width=50><img src="assets/bottom_left_2.png"></td>
									<td width="100%" background="assets/bottom_middle_2.png"></td>
									<td width=50><img src="assets/bottom_right_2.png"></td>
								</tr>
							</table></td>
							<td width=8 height=13 background="assets/bottom_right.png"></td>
						</tr>
					</table>
					<br>
				</td>
			{% endfor %}
			</tr>
			<tr><td colspan="{{ columns }}" height=10></td></tr>
		{% endfor %}
		</table>
	</body>
</html>
<!-- Generated with simpleGals {{ version }} | {{ project_url }} -->
```

- [ ] **Step 3: Write `templates/retro-fruit/item.html.j2`**

Create the item template (full image + "Page: N of M (P%)"; nav keyed off `prev_image`/`next_image`):

```jinja
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<!-- Generated with simpleGals {{ version }} | {{ project_url }} -->
<html>
	<head>
		<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
		<meta name="generator" content="simpleGals {{ version }}">
		<title>{{ title }}</title>
	</head>
	<body bgcolor="#ffffff" text="#000000">
		<table background="assets/button_gradient.png" cellpadding=0 cellspacing=0 width="100%" height=29>
			<tr height=2><td><img width=0 height=0/></td></tr>
			<tr height=19>
				<td><img width=10 height=0/></td>
				<td>{% if prev_image %}<a href="{{ prev_image.item_page }}"><img border="0" src="assets/previous1.png" alt="previous"></a>{% else %}<img border="0" src="assets/previous0.png" alt="previous">{% endif %}</td>
				<td>{% if next_image %}<a href="{{ next_image.item_page }}"><img border="0" src="assets/next1.png" alt="next"></a>{% else %}<img border="0" src="assets/next0.png" alt="next">{% endif %}</td>
				<td><img width=10 height=0/></td>
				<td><a href="index.html"><img border="0" src="assets/home.png"></a></td>
				<td><img width=10 height=0/></td>
				<td width="100%"></td>
			</tr>
		</table>

		<p><br>
		<img alt="" src="{{ image.display_path }}"><p>
		<p>
		Page: {{ image_number }} of {{ total_images }} ({{ percent }}%)<p>
	</body>
</html>
<!-- Generated with simpleGals {{ version }} | {{ project_url }} -->
```

- [ ] **Step 4: Write the smoke test**

Create `$SITE/tests/test_retro_template.py`:

```python
from pathlib import Path

from simplegals.core.config import Layout, ProjectConfig
from simplegals.core.template import render_gallery

RETRO = Path(__file__).resolve().parent.parent / "templates" / "retro-fruit"


def _records(out, names):
    out.mkdir(parents=True, exist_ok=True)
    recs = []
    for n in names:
        stem = Path(n).stem
        (out / n).write_bytes(b"X")
        (out / f"{stem}_thumb.jpg").write_bytes(b"X")
        recs.append({
            "filename": n, "output_path": n, "thumb_path": f"{stem}_thumb.jpg",
            "display_path": n, "caption": "", "alt": "", "include": True,
            "date": "2026-01-01", "size": "1 MiB", "og_path": None, "exif": None,
            "item_page": f"{stem}_item.html",
        })
    return recs


def test_retro_renders_assets_grid_and_position(tmp_path):
    out = tmp_path / "out"
    cfg = ProjectConfig(title="Retro-fruit", layout=Layout(columns=3, rows=10),
                        template=str(RETRO), social_previews=False, exif_display=False)
    render_gallery(out, cfg, _records(out, [f"{i}.jpg" for i in range(1, 4)]))
    # assets copied by 0.4.0
    assert (out / "assets" / "button_gradient.png").exists()
    assert (out / "assets" / "previous0.png").exists()
    # grid page: image count in the nav bar, thumbnails linked
    grid = (out / "index.html").read_text(encoding="utf-8")
    assert "3&nbsp;images" in grid
    assert 'href="1_item.html"' in grid
    # first item: prev disabled, next enabled, position line
    item = (out / "1_item.html").read_text(encoding="utf-8")
    assert "assets/previous0.png" in item
    assert "assets/next1.png" in item
    assert "Page: 1 of 3 (33%)" in item
    # last item: next disabled
    last = (out / "3_item.html").read_text(encoding="utf-8")
    assert "assets/next0.png" in last
    assert "Page: 3 of 3 (100%)" in last
```

- [ ] **Step 5: Run the smoke test**

```bash
SITE=/Users/tbielawa/Projects/simplegals.github.io
( cd "$SITE" && .venv/bin/python -m pytest tests/test_retro_template.py -q )
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/tbielawa/Projects/simplegals.github.io
git add templates/retro-fruit tests/test_retro_template.py
git commit -m "feat: add retro-fruit template, a 1:1 revival of the 2010 gallery"
```

---

### Task 6: Landing (`site.json`, `index.html.j2`, `build_index.py`)

**Files:**
- Create: `$SITE/site.json`, `$SITE/templates/index.html.j2`, `$SITE/build_index.py`, `$SITE/tests/test_build_index.py`, `$SITE/tests/conftest.py`

**Interfaces:**
- Consumes: each gallery's `out/gallery.json` (keys `title`, `cover`, `cover_og`, `image_count`) and `site.json`.
- Produces: `build_index.render(root: Path, out_dir: Path)` writes `_site/index.html` and copies each `galleries/<slug>/out/` to `_site/<slug>/`.

- [ ] **Step 1: Write `site.json`**

Create `$SITE/site.json`:

```json
{
  "title": "simpleGals Showcase",
  "tagline": "the same photos, three ways",
  "pitch": "A tiny static-HTML gallery generator. One photo set below, rendered by three templates: a dark theme, its bright inverse, and a 2010 revival brought back to life.",
  "chip": "3 templates · same photo set · rebuilt on every release",
  "hero_gallery": "dark",
  "galleries": [
    { "slug": "dark",        "badge": "stock template", "blurb": "The default simpleGals look: near-black, quiet, lets the photos glow." },
    { "slug": "bright",      "badge": "custom CSS",      "blurb": "The same layout inverted to dark-on-light. Airy, clean, gallery-wall bright." },
    { "slug": "retro-fruit", "badge": "custom template", "blurb": "A 2010 Apple-style web gallery, rebuilt 1:1 from its original sliced-image chrome." }
  ],
  "links": [
    { "label": "View source on GitHub", "href": "https://github.com/simplegals/simplegals.github.io" },
    { "label": "simpleGals on PyPI",    "href": "https://pypi.org/project/simplegals/" },
    { "label": "Fork a template",       "href": "https://github.com/simplegals/simplegals.github.io/tree/main/templates/retro-fruit" }
  ]
}
```

- [ ] **Step 2: Write `templates/index.html.j2`**

Create the landing (Direction A). Consumes `site`, `cards`, `hero`, `version`:

```jinja
<!DOCTYPE html>
<!-- simpleGals Showcase -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ site.title }}</title>
<meta name="description" content="{{ site.tagline }}">
{% if hero %}
<meta property="og:type" content="website">
<meta property="og:title" content="{{ site.title }}">
<meta property="og:description" content="{{ site.tagline }}">
<meta property="og:image" content="{{ hero }}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{{ hero }}">
{% endif %}
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='88'>&#127912;</text></svg>">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;background:#0e0e10;color:#e8e8ec}
a{color:inherit}
.hero{position:relative;min-height:58vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:64px 20px;background:linear-gradient(rgba(10,10,12,.52),rgba(10,10,12,.82)){% if hero %},url('{{ hero }}'){% endif %} center/cover}
.hero h1{font-size:clamp(32px,6vw,52px);font-weight:800;color:#fff;letter-spacing:.4px}
.hero .tagline{font-size:clamp(14px,2.5vw,18px);color:#d7d7dd;margin-top:12px}
.hero .pitch{font-size:14px;color:#9a9aa2;margin-top:16px;max-width:520px;line-height:1.6}
.hero .chip{margin-top:20px;font-size:12px;color:#cfcfd6;border:1px solid #3a3a42;border-radius:20px;padding:6px 15px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px;max-width:1040px;margin:0 auto;padding:28px 20px}
.card{background:#161619;border:1px solid #26262c;border-radius:8px;overflow:hidden;text-decoration:none;display:block;transition:border-color .15s ease,transform .15s ease}
.card:hover{border-color:#3a4a6a;transform:translateY(-2px)}
.card img{width:100%;height:150px;object-fit:cover;display:block;background:#222}
.card .body{padding:14px}
.card .top{display:flex;align-items:center;justify-content:space-between;gap:8px}
.card .name{font-size:16px;font-weight:700;color:#f0f0f2}
.card .badge{font-size:9px;color:#8fd0c4;border:1px solid #2f5b54;border-radius:10px;padding:2px 8px;white-space:nowrap}
.card .blurb{font-size:12px;color:#9a9aa2;margin-top:8px;line-height:1.5}
.card .foot{display:flex;align-items:center;justify-content:space-between;margin-top:12px;font-size:11px}
.card .count{color:#666}
.card .view{color:#8ab4ff}
.fold{text-align:center;padding:8px 0}
.fold .rule{height:1px;margin:0 auto;max-width:1000px;background:linear-gradient(90deg,transparent,#33333a,transparent)}
.fold .chev{color:#44444c;font-size:18px;margin-top:10px}
.how{background:#0b0b0d;padding:40px 20px}
.how .kicker{text-align:center;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#6f6f78}
.how h2{text-align:center;font-size:22px;color:#e9e9ee;margin-top:8px;font-weight:700}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:18px;max-width:820px;margin:26px auto 0}
.steps .step{text-align:center}
.steps .n{color:#8ab4ff;font-weight:700}
.steps p{font-size:13px;color:#9a9aa2;margin-top:6px;line-height:1.5}
.steps code{color:#cfcfd6}
.links{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-top:28px}
.links a{font-size:12px;color:#cfcfd6;border:1px solid #33333a;border-radius:6px;padding:7px 13px;text-decoration:none}
.links a:hover{border-color:#4a4a55}
footer{border-top:1px solid #202024;padding:18px;text-align:center;font-size:11px;color:#666}
footer a{color:#888}
</style>
</head>
<body>
  <header class="hero">
    <h1>{{ site.title }}</h1>
    <div class="tagline">{{ site.tagline }}</div>
    <div class="pitch">{{ site.pitch }}</div>
    <div class="chip">{{ site.chip }}</div>
  </header>

  <main class="cards">
    {% for c in cards %}
    <a class="card" href="{{ c.href }}">
      {% if c.cover_url %}<img src="{{ c.cover_url }}" alt="{{ c.title }} cover">{% endif %}
      <div class="body">
        <div class="top"><span class="name">{{ c.title }}</span><span class="badge">{{ c.badge }}</span></div>
        <div class="blurb">{{ c.blurb }}</div>
        <div class="foot"><span class="count">{{ c.image_count }} photos</span><span class="view">View gallery &rarr;</span></div>
      </div>
    </a>
    {% endfor %}
  </main>

  <div class="fold"><div class="rule"></div><div class="chev">&#8964;</div></div>

  <section class="how">
    <div class="kicker">How the showcase is built</div>
    <h2>One folder in, three sites out</h2>
    <div class="steps">
      <div class="step"><div class="n">1</div><p>Drop one photo set into a single <code>in/</code> folder.</p></div>
      <div class="step"><div class="n">2</div><p>Three galleries render it, each with its own template.</p></div>
      <div class="step"><div class="n">3</div><p>GitHub Actions rebuilds the site on every simpleGals release.</p></div>
    </div>
    <div class="links">
      {% for l in site.links %}<a href="{{ l.href }}">{{ l.label }}</a>{% endfor %}
    </div>
  </section>

  <footer>Built with simpleGals {{ version }} &middot; <a href="https://github.com/simplegals/simplegals.github.io">source on GitHub</a></footer>
</body>
</html>
```

- [ ] **Step 3: Write `build_index.py`**

Create `$SITE/build_index.py`:

```python
#!/usr/bin/env python3
"""Assemble the simpleGals Showcase.

Reads site.json and each gallery's out/gallery.json (never simpleGals output
naming directly), renders templates/index.html.j2, and writes a deployable
_site/ tree. Seed of a future meta-gallery tool.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

try:
    from simplegals import __version__ as SG_VERSION
except Exception:  # pragma: no cover - simplegals always present in CI/build
    SG_VERSION = ""

ROOT = Path(__file__).resolve().parent


def _load_gallery(root: Path, slug: str) -> dict:
    manifest = root / "galleries" / slug / "out" / "gallery.json"
    if not manifest.exists():
        raise SystemExit(f"missing manifest: {manifest} (build the gallery first)")
    return json.loads(manifest.read_text(encoding="utf-8"))


def _cards(root: Path, site: dict) -> list[dict]:
    cards = []
    for entry in site["galleries"]:
        slug = entry["slug"]
        g = _load_gallery(root, slug)
        cover = g.get("cover")
        cards.append({
            "slug": slug,
            "title": g.get("title", slug),
            "image_count": g.get("image_count", 0),
            "badge": entry["badge"],
            "blurb": entry["blurb"],
            "href": f"{slug}/index.html",
            "cover_url": f"{slug}/{cover}" if cover else None,
        })
    return cards


def _hero(root: Path, site: dict) -> str | None:
    slug = site.get("hero_gallery")
    if not slug:
        return None
    g = _load_gallery(root, slug)
    return f"{slug}/{g['cover_og']}" if g.get("cover_og") else None


def render(root: Path, out_dir: Path) -> None:
    site = json.loads((root / "site.json").read_text(encoding="utf-8"))
    cards = _cards(root, site)
    env = Environment(loader=FileSystemLoader(str(root / "templates")),
                      autoescape=select_autoescape(["html", "j2"]))
    html = env.get_template("index.html.j2").render(
        site=site, cards=cards, hero=_hero(root, site), version=SG_VERSION)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    for entry in site["galleries"]:
        slug = entry["slug"]
        shutil.copytree(root / "galleries" / slug / "out", out_dir / slug, dirs_exist_ok=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the simpleGals Showcase into _site/")
    ap.add_argument("--out", default=str(ROOT / "_site"))
    args = ap.parse_args()
    render(ROOT, Path(args.out))
    print(f"Built site into {args.out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Write `tests/conftest.py` (put the repo root on sys.path)**

Create `$SITE/tests/conftest.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

- [ ] **Step 5: Write `tests/test_build_index.py`**

Create `$SITE/tests/test_build_index.py`:

```python
import json

import pytest

import build_index


def _setup(root):
    (root / "templates").mkdir(parents=True)
    (root / "templates" / "index.html.j2").write_text(
        "TITLE={{ site.title }} HERO={{ hero }} VER={{ version }} "
        "{% for c in cards %}[{{ c.slug }}|{{ c.title }}|{{ c.badge }}|{{ c.image_count }}|{{ c.href }}|{{ c.cover_url }}]{% endfor %}",
        encoding="utf-8")
    (root / "site.json").write_text(json.dumps({
        "title": "Showcase", "tagline": "t", "pitch": "p", "chip": "c",
        "hero_gallery": "dark",
        "galleries": [{"slug": "dark", "badge": "stock template", "blurb": "b"}],
        "links": [],
    }), encoding="utf-8")
    g = root / "galleries" / "dark" / "out"
    g.mkdir(parents=True)
    (g / "gallery.json").write_text(json.dumps({
        "title": "Dark", "cover": "img-08_thumb.jpg", "cover_og": "img-08_og.jpg",
        "image_count": 36, "slug": "dark",
    }), encoding="utf-8")
    (g / "index.html").write_text("<html>dark</html>", encoding="utf-8")


def test_render_and_assemble(tmp_path):
    _setup(tmp_path)
    out = tmp_path / "_site"
    build_index.render(tmp_path, out)
    idx = (out / "index.html").read_text(encoding="utf-8")
    assert "TITLE=Showcase" in idx
    assert "HERO=dark/img-08_og.jpg" in idx
    assert "[dark|Dark|stock template|36|dark/index.html|dark/img-08_thumb.jpg]" in idx
    assert (out / "dark" / "index.html").exists()  # gallery out/ assembled into _site/<slug>/


def test_missing_manifest_fails_loudly(tmp_path):
    _setup(tmp_path)
    (tmp_path / "galleries" / "dark" / "out" / "gallery.json").unlink()
    with pytest.raises(SystemExit):
        build_index.render(tmp_path, tmp_path / "_site")
```

- [ ] **Step 6: Run the tests**

```bash
SITE=/Users/tbielawa/Projects/simplegals.github.io
( cd "$SITE" && .venv/bin/python -m pytest tests/ -q )
```

Expected: PASS (retro smoke test from Task 5 plus the two build_index tests).

- [ ] **Step 7: Commit**

```bash
cd /Users/tbielawa/Projects/simplegals.github.io
git add site.json templates/index.html.j2 build_index.py tests/conftest.py tests/test_build_index.py
git commit -m "feat: add landing template, site.json, and build_index assembler"
```

---

### Task 7: CI workflow (`pages.yml`)

**Files:**
- Create: `$SITE/.github/workflows/pages.yml`

**Interfaces:**
- Consumes: the committed source (galleries, templates, site.json, build_index.py).
- Produces: a Pages deployment on push/dispatch.

- [ ] **Step 1: Write `pages.yml`**

Create `$SITE/.github/workflows/pages.yml`:

```yaml
name: Build and deploy Pages

on:
  push:
    branches: [main]
  workflow_dispatch:
  repository_dispatch:
    types: [simplegals-release]

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install simpleGals
        run: pip install "simplegals>=0.4.0"
      - name: Build each gallery
        run: |
          set -e
          for dir in galleries/*/; do
            echo "Building $dir"
            ( cd "$dir" && simpleGals build --force )
          done
      - name: Assemble the site
        run: python build_index.py --out _site
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: _site

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Lint the YAML**

```bash
SITE=/Users/tbielawa/Projects/simplegals.github.io
"$SITE/.venv/bin/python" -c "import yaml,sys; yaml.safe_load(open('$SITE/.github/workflows/pages.yml')); print('YAML OK')" 2>/dev/null \
  || python3 -c "import yaml; yaml.safe_load(open('$SITE/.github/workflows/pages.yml')); print('YAML OK')"
```

Expected: `YAML OK`. (If PyYAML is not present, install it into the venv first with `.venv/bin/pip install pyyaml`, or skip; GitHub validates on push.)

- [ ] **Step 3: Commit**

```bash
cd /Users/tbielawa/Projects/simplegals.github.io
git add .github/workflows/pages.yml
git commit -m "ci: add Pages build/deploy workflow with release dispatch trigger"
```

---

### Task 8: Full local end-to-end build and verification

**Files:**
- Create: `$SITE/scripts/build_local.sh`

**Interfaces:**
- Consumes: everything above.
- Produces: a verified `_site/` proving the whole pipeline before any push.

- [ ] **Step 1: Write the local build helper**

Create `$SITE/scripts/build_local.sh`:

```bash
#!/usr/bin/env bash
# Build the whole showcase locally into _site/ (mirrors CI).
set -euo pipefail
cd "$(dirname "$0")/.."
BIN="$PWD/.venv/bin"
for dir in galleries/*/; do
  echo "Building $dir"
  ( cd "$dir" && "$BIN/simpleGals" build --force )
done
"$BIN/python" build_index.py --out _site
echo "Done: _site/index.html"
```

- [ ] **Step 2: Run the full build**

```bash
SITE=/Users/tbielawa/Projects/simplegals.github.io
chmod +x "$SITE/scripts/build_local.sh"
"$SITE/scripts/build_local.sh"
```

Expected: three "Building ..." lines and `Done: _site/index.html`.

- [ ] **Step 3: Verify the assembled site**

```bash
SITE=/Users/tbielawa/Projects/simplegals.github.io
cd "$SITE"
echo "-- landing has all three cards + hero --"
grep -c 'class="card"' _site/index.html                 # expect 3
grep -o 'dark/img-08_og.jpg' _site/index.html | head -1  # hero present
echo "-- three galleries assembled --"
for s in dark bright retro-fruit; do test -f "_site/$s/index.html" && echo "$s OK"; done
echo "-- retro assets + pagination + position --"
test -f _site/retro-fruit/assets/button_gradient.png && echo "retro assets OK"
test -f _site/retro-fruit/page-2.html && echo "retro paginates OK"   # 36 imgs, 30/page -> 2 pages
grep -q "Page: 1 of 36" _site/retro-fruit/1_item.html && echo "retro position OK"
echo "-- bright is light --"
grep -q "background: #faf9f7" _site/bright/style.css && echo "bright light OK"
```

Expected: `3`, the hero path, `dark OK` / `bright OK` / `retro-fruit OK`, `retro assets OK`, `retro paginates OK`, `retro position OK`, `bright light OK`.

- [ ] **Step 4: Run the full test suite**

```bash
SITE=/Users/tbielawa/Projects/simplegals.github.io
( cd "$SITE" && .venv/bin/python -m pytest tests/ -q )
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/tbielawa/Projects/simplegals.github.io
git add scripts/build_local.sh
git commit -m "chore: add local build helper mirroring CI"
```

---

## Deferred (not part of this plan)

- Wiring the site to the `simpleGals` org: create/point the remote to
  `simplegals/simplegals.github.io`, set Pages source to GitHub Actions, and
  connect the release `repository_dispatch` from the tool repo (sub-project 3, the
  runbook). The `pages.yml` listener is already in place.
- The richer per-gallery description override (retro "features can be re-enabled")
  from the spec backlog.

## Self-Review

- **Spec coverage:** repo layout -> Tasks 1,3,6,7; shared input + symlinks -> Tasks 2,3; three galleries -> Task 3; bright fork -> Task 4; retro 1:1 (assets, nav states, Page N of M, 30/page) -> Task 5; site.json + landing + build_index -> Task 6; CI -> Task 7; local verification -> Task 8; hero = dark cover_og -> Task 6 `_hero`; placeholder count 36 -> Task 2; gitignore/README -> Task 1. Backlog items are explicitly deferred. No gaps.
- **Placeholder scan:** every step has concrete code or commands with expected output.
- **Type consistency:** `build_index.render(root, out_dir)` is defined in Task 6 and called with the same signature in `tests/test_build_index.py`. Card keys (`slug`, `title`, `image_count`, `badge`, `blurb`, `href`, `cover_url`) match between `_cards` and both `index.html.j2` and the test assertions. `_hero` returns `<slug>/<cover_og>`, matching the test's `HERO=dark/img-08_og.jpg`. Retro context names (`current_page`, `total_pages`, `total_images`, `prev_image`, `next_image`, `image_number`, `percent`, `image.thumb_path`, `image.item_page`, `image.display_path`) match simpleGals 0.4.0's render context.
```
