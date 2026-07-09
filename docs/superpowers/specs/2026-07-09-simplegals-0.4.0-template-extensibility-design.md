# simpleGals 0.4.0: Template Extensibility (Assets and Position Context)

Date: 2026-07-09
Status: approved (brainstorming), pending spec review
Parent: 2026-07-09-simplegals-demo-initiative-design.md
Sub-project: 1b of the demo initiative (unblocks sub-project 2, the site)

## Summary

A small, additive release that lets a custom template ship its own static
assets and know where each image sits in the set. Three backward-compatible
changes to `simplegals/core/template.py`. Nothing about the default template,
the image pipeline, or existing output changes.

This release exists to unblock one demo-site gallery ("retro-fruit", a faithful
reproduction of a 2010 Apple iPhoto / .Mac web-gallery export) that cannot be
expressed today: it is styled entirely by sliced PNG images (no CSS) and its
item pages read "Page N of M (P%)". The current processor copies exactly one
file (`style.css`) into `out/` and exposes no per-item position, so a template
like that has no way to get its images into the build or to number its pages.
The capability is general, not retro-specific: any custom template can now carry
fonts, logos, JavaScript, or a favicon.

## Scope

1. Template asset copying via an `assets/` subdirectory convention.
2. Per-item and per-grid position context (`image_number`, `total_images`,
   `percent`).
3. `style.css` copying becomes optional instead of mandatory.

## Non-goals

- No new image processing. The retro reproduction reuses the already generated
  thumbnail and full-size outputs.
- No template redesign, no inverted or "bright" theme in the tool. Those are
  demo-site content (custom `style.css` overrides in the site repo), not tool
  features.
- The retro-fruit template itself does NOT ship in the package. Its `.j2` files
  and its 18 slice PNGs live in the site repo as the custom-override demo
  (sub-project 2). This release ships only the capability plus the default
  template. Its tests use a tiny throwaway fixture template, not the real retro
  template.

## Feature 1: template asset copying (the `assets/` convention)

A template directory may contain an `assets/` subfolder. On render, its entire
contents are copied, recursively and structure-preserving, into `out/assets/`.
Templates reference the files by relative path, for example
`background="assets/top_left.png"`.

Behavior:

- Source: `<template_dir>/assets/`. Destination: `<out_dir>/assets/`.
- Implemented with `shutil.copytree(src, dst, dirs_exist_ok=True)` so a rebuild
  into an existing `out/` does not fail, and nested subdirectories are
  preserved.
- If the template has no `assets/` directory, nothing extra is copied. Existing
  templates (including the built-in default, which has none) are unaffected.
- The copy runs on every build, matching how `style.css` is handled today
  (assets are treated as static template files, not cached per-image outputs).

Rationale for the subfolder convention over "copy every non-`.j2` file in the
template dir": it keeps template sources and binary assets from intermingling in
one flat directory, it is predictable (a template author knows exactly what ships
and what does not), and it generalizes cleanly to fonts, JS, logos, and
favicons. `style.css` keeps its existing special handling (copied to the `out/`
root, referenced as `css_path`) for backward compatibility; it does not move
under `assets/`.

## Feature 2: position context

The processor computes each image's position and exposes it to templates.

Added to the per-item render context (the loop over `records` in
`render_gallery`):

- `image_number`: 1-based index of this image in the included set (`i + 1`).
- `percent`: integer floor of completion, `(image_number * 100) // total_images`.
  This matches the source export exactly: image 1 of 89 renders "1%", image 2
  renders "2%".

Added to `base_ctx` (so both grid pages and item pages have it):

- `total_images`: `len(records)`, the number of included images. The retro grid
  header renders "89 images" from this; today no page-level total is exposed.

Already present, no change needed:

- `prev_image` / `next_image` (None at the first/last item): drives the retro
  nav's enabled/disabled button swap (`previous0.png` vs `previous1.png`,
  `next0.png` vs `next1.png`).
- `image.thumb_path` (for example `foo_thumb.jpg`), `image.output_path` (full
  image), `image.display_path`, `image.item_page`, `current_page`,
  `total_pages`.

## Feature 3: optional `style.css`

Today `render_gallery` copies `<template_dir>/style.css` unconditionally, so a
template without one raises `FileNotFoundError` before it can render. Change:
copy `style.css` only when it exists.

- If present: copied to `out/style.css`, exactly as today. `css_path` stays
  `"style.css"`.
- If absent: skipped, no error. A template that ships no CSS (like retro, which
  styles via table attributes and sliced images) simply does not emit a
  `<link rel="stylesheet">`.

`css_path` remains `"style.css"` unconditionally for backward compatibility; the
built-in default template always ships one, so its behavior is unchanged.

## Backward compatibility

All three changes are additive:

- No `assets/` directory means no new output. The default template ships none.
- The new context variables are additions; no existing variable changes name,
  type, or value.
- `style.css` is still copied whenever it exists, which is every current
  template.

The existing suite (203 tests) must stay green. This release only adds tests.

## Testing strategy (TDD)

Write failing tests first, then implement. New tests live alongside the existing
template tests and use small fixture template directories created under the
test's temp area.

Asset copying:

- A fixture template with `assets/marker.png` and a nested
  `assets/sub/note.txt`: after render, both `out/assets/marker.png` and
  `out/assets/sub/note.txt` exist (proves recursion and structure preservation).
- A fixture template with no `assets/`: after render, `out/assets/` is not
  created.
- Rebuild into a populated `out/` does not raise (dirs_exist_ok).

Optional `style.css`:

- A fixture template with no `style.css`: render does not raise, and no
  `out/style.css` is written.
- A fixture template with `style.css`: it is copied to `out/style.css` (guards
  the unchanged happy path).

Position context:

- A fixture item template that emits `image_number`, `total_images`, and
  `percent`: render a known set and assert the first item shows
  `image_number=1` and the correct `percent`, the last item shows
  `image_number == total_images` and `percent=100`, and an interior item is
  correct. Verify the floor with a set size that is not a divisor of 100 (for
  example 89 images: item 1 is 1%, item 2 is 2%).
- A fixture grid/page template that emits `total_images`: assert it equals the
  included image count.

Existing suite:

- All 203 current tests remain green (the branding, cover, manifest, and promo
  tests must be untouched by these changes).

## Release steps

1. Implement on a `0.4.0` branch, TDD, suite green.
2. Bump `VERSION` to `0.4.0` (bare PEP 440, no `v`, no trailing newline).
3. Tag `0.4.0`, publish the GitHub Release. `publish.yml` verifies the tag
   equals `VERSION` and publishes to PyPI via trusted publishing.
4. The site (sub-project 2) then installs `simplegals>=0.4.0` from PyPI and uses
   the new capability for its retro-fruit gallery.

Note on the org transfer (sub-project 3): if the PyPI trusted-publisher re-point
has not happened by the time 0.4.0 ships, publishing still works from
`timlnx/simpleGals`. If the transfer has happened, the runbook's pre-added
`simplegals/simpleGals` publisher covers it. Either way, 0.4.0 does not depend on
the transfer.

## Decisions resolved during brainstorming

- Asset copying uses an `assets/` subdirectory copied to `out/assets/`, not a
  flat copy of every non-template file. Confirmed.
- The retro-fruit template lives in the site repo, not in the package. 0.4.0
  ships only the capability plus the default template. Confirmed.
- `percent` is an integer floor, matching the source export ("1 of 89 (1%)").
  Confirmed.
- The stock template is already dark, so the demo's "dark" variation needs no
  work and "bright" is a CSS-only override; neither requires tool changes. Only
  retro-fruit does. Confirmed.

## Micro-defaults chosen (flag if you disagree)

- `assets/` is copied on every build (static template files, not cached
  per-image outputs), consistent with `style.css`.
- `percent` uses integer floor division `(image_number * 100) // total_images`.
- `css_path` stays the literal `"style.css"` regardless of whether the file
  exists, for backward compatibility.

## Consumed by

The demo site's retro-fruit gallery (sub-project 2) will ship
`templates/retro-fruit/{page.html.j2, item.html.j2, assets/*.png}`, reusing the
original `Resources/*.png` slices from the source export 1:1. The exact
reproduction (table-markup mapping, nav button state logic, per-page filename
mapping) belongs to the site spec, not this one. This release only guarantees
the two things that reproduction needs from the tool: assets reach `out/`, and
item pages know their position.

## See also

- [Demo initiative design](2026-07-09-simplegals-demo-initiative-design.md) (parent)
- [0.3.1 cover/manifest spec](2026-07-09-simplegals-0.3.1-cover-manifest-design.md) (the release this builds on)
