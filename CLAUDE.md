# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`simpleGals` is a command-line static HTML image gallery generator. It takes directories of images and produces simple HTML files with thumbnails. There are two entry points:

- `simpleGals`: batch-mode CLI
- `sgui`: interactive TUI setup utility

Both commands operate in the current working directory, auto-creating `in/` (input images), `out/` (generated HTML), and `.meta/` (image metadata/cache).

## Tech Stack

- Python >= 3.10
- [`term-image`](https://github.com/AnonymouX47/term-image) for terminal image rendering (requires Kitty graphics protocol, iTerm2 inline image protocol, or Unicode truecolor support)
- [`bitmath`](https://pypi.org/project/bitmath/) >= 2.0.0 for file size display and comparisons (use NIST prefixes: MiB not MB)

## Code Style and Linting

Code must pass `make lint` (pycodestyle + pylint) and `make security` (bandit +
pip-audit) before commit. The `lint` job in CI is currently advisory; treat it as
a gate anyway. simpleGals ships with **zero inline suppressions** — write code that
passes cleanly rather than silencing checks.

Conventions (enforced by pylint/pycodestyle, so follow them up front):
- **Max line length is 120 characters** (pylint `max-line-length`, pycodestyle `--max-line-length=120`).
- **Do not shadow Python builtins** with parameter or variable names (e.g. `copyright`, `id`, `type`, `format`). Bind the value to a descriptive name like `copyright_text`.
- **No mutable default arguments** (`def f(x=set())` / `[]` / `{}`). Default to `None` and normalize inside: `x = x or set()`.
- **Imports go at module top** — no imports inside functions.
- **Prefer non-deprecated APIs** — e.g. `Image.Resampling.LANCZOS`, not `Image.LANCZOS`.
- **Every module and class has a docstring.** Function docstrings are not required (the check is disabled), but public functions should still carry one; the important ones do.
- **Catch specific exceptions where practical.** Broad `except Exception` is allowed only in the worker/TUI code that must degrade gracefully (it is a documented pylint disable); do not add new broad catches elsewhere.
- Tests use `assert` and `subprocess` freely — bandit is scoped to `simplegals/` only, so those are not flagged.

Prefer fixing a lint finding over suppressing it. Do not add `# pylint: disable`,
`# noqa`, or `# nosec` comments, and do not extend the pylint `disable` list in
`pyproject.toml`, without explicit sign-off. The existing `[tool.pylint.messages_control]`
disables are the audited set of exceptions, each with a one-line reason.

## Architecture

- **`sgui`**: TUI with a split layout: scrollable file tree (left, ~20% width) and settings/preview panel (right). Navigation via arrow keys and Tab to switch focus. Ctrl+G opens gallery settings; Escape returns to file selection mode.
- **Template system**: A default HTML template ships with the tool; users can fork it and point to a custom template via `--template/-t <TEMPLATE_DIR>` or the `sgui` settings panel.
- **Thumbnail caching**: `.meta/` stores image metadata and cached thumbnails. On repeat runs, thumbnails are regenerated only when the input file's last-modified time has changed.
- **Preview behavior**: A configurable delay (`preview_delay`, default 125ms) prevents rapid thumbnail generation while paging through files. First-load generates and caches; subsequent views are instant if unchanged.
- **Image pipeline**: For each source image, up to four output files are generated:
  - `out/foo.jpg`: full original (may have EXIF copyright injected)
  - `out/foo_display.jpg`: web display image, capped at 2048×2048 px, quality 85; only generated when the original exceeds 2 MiB (`bitmath.MiB(2)`)
  - `out/foo_thumb.jpg`: grid thumbnail, capped at 600×450 px
  - `out/foo_og.jpg` (or `foo_og.png` for a PNG source): social preview image, longest edge 1200px, quality 80, mirrors the source container; only generated when `social_previews` is true
- **OG/social tags**: When `social_previews` is true, all generated pages emit `og:*` and `twitter:*` meta tags, with `og:image`/`twitter:image` pointing at the per-image `_og` preview. The absolute image URL additionally requires `site_url` to be set; `site_url` is normalized (trailing slash stripped) before being passed to Jinja2 templates.

## Key Configuration Settings

### Global settings (`GlobalConfig`), stored in XDG/platform config dir

| Setting | Type | Default | Description |
|---|---|---|---|
| `file_panel_width` | `int` or `int%` | `30` | Width of the file tree panel |
| `scroll_rate` | `float` | `2.0` | Marquee scroll rate (chars/sec) for truncated filenames |
| `preview_delay` | `int` (ms) | `125` | Delay before generating a thumbnail for the first time |

### Gallery settings (`ProjectConfig`), stored in `simpleGal.json`

| Setting | Type | Default | Description |
|---|---|---|---|
| `title` | `str` | `"Gallery"` | Gallery title shown in header and OG tags |
| `description` | `str` | `""` | Gallery description |
| `cover` | `str` | `""` | Filename in `in/` used as the gallery cover (portfolio thumbnail and gallery-index `og:image`); blank uses the first image |
| `copyright` | `str` | `""` | Copyright string embedded in JPEG EXIF and page footer |
| `author` | `str` | `""` | Author name for `<meta name="author">` |
| `social_previews` | `bool` | `True` | Emit OG/Twitter tags and generate 1200px `_og` previews (in the source container: `_og.jpg` or `_og.png`) |
| `exif_display` | `bool` | `True` | Show a camera-metadata block on item pages |
| `gallery_zip` | `bool` | `False` | Generate a downloadable zip of full-size originals |
| `simple_gals_promo` | `bool` | `False` | Render a "generated with simpleGals" footer link on every page (opt-in) |
| `site_url` | `str` | `""` | Absolute base URL; enables OG image/url tags when set |
| `quality` | `int` | `90` | JPEG output quality (0-100) |
| `columns` | `int` | `4` | Thumbnail grid columns per page |
| `rows` | `int` | `5` | Thumbnail grid rows per page |
| `template` | `str\|None` | `None` | Path to custom template directory |

## Versioning

The version is stored once, in the top-level `VERSION` file (bare PEP 440 string,
no trailing newline). `pyproject.toml` reads it via hatchling (`dynamic = ["version"]`).
Bumping a release is a one-line edit to `VERSION`. Use the bare version with no `v`
prefix everywhere: `VERSION`, the git tag, and the GitHub Release name (e.g. `0.3.0`).
`publish.yml` fails the release if the tag does not equal `VERSION`.
