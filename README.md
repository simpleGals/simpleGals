# README.md

`simpleGals` is trying to be a very simple command-line driven static HTML image
gallery generating tool. simpleGals just like to have fun, it doesn't want you
getting bogged down with all the tedious overhead associated with fancy gals,
running software that has to get patched, or paying another subscription.
simpleGals ain't like that.

simpleGals isn't for album management. You feed simpleGals directories of images
and in return you get some simple HTML files with thumbnails.


# Tech Stack

- [Python](https://www.python.org/) >= 3.10
- [term-image](https://pypi.org/project/term-image/) for terminal image rendering
- A terminal emulator with **any** of the following:

  - support for the [Kitty graphics protocol](https://sw.kovidgoyal.net/kitty/graphics-protocol/)
  - support for the [iTerm2 inline image protocol](https://iterm2.com/documentation-images.html)
  - Unicode and direct-color (truecolor) support
- [bitmath](https://pypi.org/project/bitmath/) for file size printing and math

(I told you, it's simple)


# Experience

The fanciest part of simpleGals is the tui setup utility. Launching `sgui` opens
the application in the current working directory, `sgui` (and the batch-mode
`simpleGals` interface) will create a directory called `out` and expects to find
a directory called `in`, these directories will be created if they do not
already exist. Image metadata and caching files are saved in a `.meta`
directory.

A basic template ships with simpleGals. Your can fork this template and instruct
simpleGals to use your template instead with the `--template,-t <TEMPLATE_DIR>`
option flag, or in the setup panel of `sgui`.


# `sgui`

The sgui launches with a scrollable file tree ('file panel') of discovered
images in the `in` directory listed on the left, just the file names, about 20%
of the screen up to a max width of ~=30 characters

* setting: `file_panel_width`
* desc: width in characters or percent of horizontal area
* types:
    - `int` for absolute character value (e.g., `30` = 30 characters)
    - `int%` for max width percent (e.g., `30%` = 30% of horizontal space)
* default: `30`

Move the selection cursor with with the up/down arrow keys, pausing or stopping
on a file name will marquee scroll the file name if it was truncated. The ctrl+n
and ctrl+p shortcuts also work for next and previous if you are in the file panel.

* setting: `scroll_rate`
* desc: scroll rate in chars/second
* type: `float`
* default: `2.0`

On the right using the remainder of the visible space is the general gallery
settings input panel. This panel is also where previewing and editing properties
of individual images takes place.

Press **Ctrl+G** to open the gallery settings panel where parameters like title,
description, columns, rows, site URL, and more can be configured. Press
**Escape** to return to the file selection mode.

When moving the selection cursor between images in the file panel there is a
brief delay before the thumbnail is loaded the first time so you can page
through several in a row without attempting to generate thumbnails of each image
rapidly. Once a thumbnail is generated the delay is `0` if the last-modified
metadata has not changed for the input/thumbnail files

* setting: `preview_delay`
* description: delay before generating image metadata thumbnail the first time
* type: `int`
* default: `125ms`

Image thumbnails are displayed in the console using the `term-image` library. A
preview will take up no more than 55% of the available horizontal/vertical space
on the panel on the right.

Pressing tab switches cursor focus between the file panel and the main usage window.

## sgui keyboard shortcuts

| Key | Action |
|-----|--------|
| ↑ / ↓ or Ctrl+P / Ctrl+N | Navigate file list |
| Enter | Open image settings for selected file |
| t | Toggle selected image include/exclude |
| Tab | Cycle focus between panels and fields |
| Escape | Return to file selection mode |
| Ctrl+G | Open gallery settings panel |
| Ctrl+W | Save all staged changes |
| Ctrl+R | Reload source images from `in/` |
| Ctrl+B | Build gallery |
| q | Quit (prompts to save if unsaved changes) |


# Settings

Settings are saved in JSON format.

## Global settings (`~/Library/Application Support/simplegals/config.json` on macOS)

| Setting | Type | Default | Description |
|---|---|---|---|
| `file_panel_width` | `int` or `int%` | `30` | Width of the file tree panel |
| `scroll_rate` | `float` | `2.0` | Marquee scroll rate (chars/sec) for truncated filenames |
| `preview_delay` | `int` (ms) | `125` | Delay before generating a thumbnail preview the first time |

## Gallery settings (`simpleGal.json` in the project directory)

| Setting | Type | Default | Description |
|---|---|---|---|
| `title` | `str` | `"Gallery"` | Gallery title shown in the header and OG tags |
| `description` | `str` | `""` | Gallery description shown below the title |
| `copyright` | `str` | `""` | Copyright string embedded in JPEG EXIF and the footer |
| `author` | `str` | `""` | Author name for `<meta name="author">` |
| `site_url` | `str` | `""` | Absolute base URL (e.g. `https://photos.example.com/summit`) — enables OG/social preview tags |
| `quality` | `int` | `90` | JPEG output quality (0–100) |
| `columns` | `int` | `4` | Thumbnail grid columns per page |
| `rows` | `int` | `5` | Thumbnail grid rows per page |
| `template` | `str\|None` | `None` | Path to a custom template directory |

## Gallery metadata (`/.meta/`)

For each source image `foo.jpg`, the `.meta/` directory contains:

- `foo.jpg.json` — sidecar JSON: records mtime, sha256, settings hash, and paths to generated artifacts
- `foo_thumb.jpg` — cached thumbnail for the `sgui` preview panel

Staleness is determined by mtime first (fast), sha256 second (handles
touched-but-unchanged files), then a settings hash to detect config changes.
Artifact existence is also verified — if a sidecar exists but the output files
are gone, they are regenerated. On each build, any `.meta/` entries whose source
image is no longer present in `in/` are pruned, along with their corresponding
`out/` files.

## Output image tiers (`/out/`)

simpleGals generates up to three versions of each image:

| File | Max dimensions | Notes |
|------|---------------|-------|
| `foo.jpg` | Original size | Full original; linked from individual item pages |
| `foo_display.jpg` | 2048×2048 px | Only generated when the original exceeds 2 MiB; shown on item pages in place of the full original |
| `foo_thumb.jpg` | 600×450 px | Used in the thumbnail grid on gallery index pages |


# Generated gallery features

The features below are all optional; a generated gallery works with none of
them configured. Keyboard navigation is always on, and social preview tags
activate only when `site_url` is set.

## Keyboard navigation

The generated HTML pages include keyboard shortcuts:

| Key | Page type | Action |
|-----|-----------|--------|
| ← / → | Item page | Previous / next image (no wrap-around at ends) |
| u | Item page | Return to the gallery page and scroll to the image's thumbnail row |
| ← / → | Paginated index | Previous / next page (no wrap-around) |
| u | All-images page | Return to the paginated index |

## Social / OG preview tags

When `site_url` is set in the gallery config, every generated page emits
`og:*` and `twitter:*` meta tags. This enables rich link previews when sharing
URLs on Slack, iMessage, Discord, LinkedIn, and similar platforms. The preview
image used is the thumbnail for that page.

`site_url` must be a full absolute URL with no trailing slash, e.g.:
```
https://photos.example.com/summit-2026
```

## Share button

Each individual item page has a 🔗 button in the image metadata row. Clicking it
copies a clean shareable URL (query parameters and fragment stripped) to the
clipboard.


# Reference Material

* base library: https://github.com/AnonymouX47/term-image
* example usage: https://github.com/AnonymouX47/termvisage
