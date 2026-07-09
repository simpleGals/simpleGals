# simpleGals 0.3.1: Cover Image, Gallery Manifest, Versioned Promo

Date: 2026-07-09
Status: approved (brainstorming), pending spec review
Parent: 2026-07-09-simplegals-demo-initiative-design.md
Sub-project: 1 of 3 (critical path)

## Summary

A small, self-contained release that gives a gallery a chosen representative
image, publishes a machine readable per-gallery manifest, exposes cover
selection in `sgui`, and stamps the running version into the promo footer. The
manifest is the data contract the demo site's `build_index.py` and the future
meta-gallery tool consume.

## Scope

1. `cover` field in `simpleGal.json` (`ProjectConfig`).
2. `out/gallery.json` manifest emitted on every build.
3. `sgui` cover picker in the gallery settings panel.
4. simpleGals version rendered in the opt-in `simple_gals_promo` footer string.
5. Always-on simpleGals branding in every generated HTML file: a
   `<meta name="generator">` tag plus a comment at the top and bottom, unconditional
   and independent of the opt-in promo footer.

## Non-goals

- No meta-gallery / portfolio index feature in the tool itself. That lives in the
  site repo (`build_index.py`).
- No new image processing. Cover reuses the already generated thumb and og
  outputs for the chosen image.
- No template redesign or inverted theme (separate backlog item).

## Feature 1: `cover` field

- Add `cover: str = ""` to `ProjectConfig` (`simplegals/core/config.py`),
  serialized to and from `simpleGal.json` like the other v0.3.0 fields.
- Value is a filename as it appears in `in/` (basename), for example
  `"milkyway.jpg"`.
- Resolution at build time:
  - Set and the file is present in the input set: use it.
  - Unset or empty: use the first image in the gallery's existing sort order.
  - Set but not found in the input set: log a clear warning and fall back to the
    first image. Do not fail the build.
- The resolved cover is the representative image for the gallery: it populates
  the manifest, and it becomes the `og:image` for the gallery index page when
  `social_previews` is true (today the index page has no single obvious choice;
  the cover makes it deterministic). Per-item pages keep their own per-image og.

## Feature 2: `out/gallery.json` manifest

Emitted once per build into `out/`, additive (a new file, nothing else changes).

Schema:

```json
{
  "title": "Nightscapes",
  "description": "Long exposures under dark skies",
  "author": "Tim Case",
  "slug": "nightscapes",
  "cover": "milkyway_thumb.jpg",
  "cover_og": "milkyway_og.jpg",
  "image_count": 24,
  "simplegals_version": "0.3.1",
  "site_url": "https://simplegals.github.io/nightscapes/",
  "built_at": "2026-07-09T18:04:22Z"
}
```

Field notes:

- `slug`: the gallery directory name (basename of the working directory).
- `cover`: built thumbnail filename for the resolved cover (for example
  `milkyway_thumb.jpg`), relative to `out/`.
- `cover_og`: built og filename for the resolved cover, or `null` when
  `social_previews` is false (no og image is generated).
- `image_count`: number of source images processed.
- `simplegals_version`: from `simplegals.__version__`
  (`simplegals/__init__.py`), the same source `pyproject.toml` reads.
- `site_url`: the normalized `site_url` from config, or `null`/empty when unset.
- `built_at`: UTC ISO 8601 timestamp at build time.

Consumers read `gallery.json` and never need to know simpleGals output naming.

## Feature 3: `sgui` cover picker

- Add a "Cover image" control to the gallery settings panel (Ctrl+G), alongside
  the v0.3.0 toggles.
- The value is the cover filename. Selecting from the current `in/` file list is
  preferred over free text so the value is always valid; match whatever input
  pattern the existing settings fields use.
- Persist to `simpleGal.json` on save, same path as the other project settings.

## Feature 4: version in the promo string (opt-in footer)

- The `simple_gals_promo` footer (default false, opt-in) currently renders a
  "generated with simpleGals" link. Include the bare version:
  "Generated with simpleGals 0.3.1" (no `v` prefix, matching the project
  versioning convention).
- Source the version from `simplegals.__version__`.
- Touch the promo render path (`simplegals/core/template.py` and the promo string
  construction referenced in `simplegals/core/config.py`,
  `simplegals/cli.py`, and the TUI preview) so batch build, sgui preview, and the
  final page all agree.
- This is the visible, opt-in footer link. It is separate from the always-on
  generator branding in Feature 5.

## Feature 5: always-on generator branding

Unconditional simpleGals branding on every generated HTML file, independent of
`simple_gals_promo` (which stays opt-in and default false). This is standard
static-site-generator practice.

- `<meta name="generator" content="simpleGals 0.3.1">` in the `<head>` of every
  page (bare version from `simplegals.__version__`).
- An HTML comment near the top and near the bottom of every generated page.
  - Top comment placed immediately after `<!DOCTYPE html>`, not before it, so it
    cannot trigger quirks mode in legacy browsers. Bottom comment is the final
    line after `</html>`.
  - Default content, same branded comment top and bottom:
    `<!-- Generated with simpleGals 0.3.1 | https://github.com/simplegals/simpleGals -->`
- Applies to every generated HTML file: paginated index / grid pages, per-item
  pages, and the all.html download page.
- The homepage URL comes from a single source of truth (packaging metadata in
  `pyproject.toml` `[project.urls]` or a module constant) so it stays correct
  after the org transfer. Default target is the org repo URL; redirects cover the
  old `timlnx` path.

## Backward compatibility

- `cover` is optional and defaults to current behavior (first image).
- `gallery.json` is a new additive file.
- The promo footer change is cosmetic. Any existing test that asserts the exact
  promo text must be updated to expect the bare version.
- Generator meta and top/bottom comments are additive to the template output.
  Tests that assert exact full-page HTML (byte-for-byte) must be updated to
  account for the branding; tests that assert on structure/fragments are
  unaffected.

## Testing strategy

Follow test-driven development. Add or update:

- Cover resolution: set and present, unset (first image), set and missing
  (warning plus first-image fallback).
- Manifest: file is written; all fields present and correct; `cover_og` is null
  when `social_previews` is false; `image_count` matches the input set;
  `simplegals_version` matches `__version__`.
- Gallery index `og:image` uses the resolved cover when `social_previews` is
  true.
- Promo footer contains the bare version ("simpleGals 0.3.1") when
  `simple_gals_promo` is true.
- Generator branding (Feature 5): `<meta name="generator">` with the bare
  version is present on every page type; top and bottom branding comments are
  present on every generated HTML file; branding appears even when
  `simple_gals_promo` is false and `social_previews` is false.
- The existing suite (182 tests) stays green.

## Release steps

1. Implement and land the feature on the `0.3.1` branch with tests green.
2. Bump `VERSION` to `0.3.1`.
3. Tag `0.3.1` and publish the GitHub Release. `publish.yml` verifies the tag
   equals `VERSION` and publishes to PyPI.

## Decisions resolved during review

- Gallery index `og:image` switches to the resolved cover when `social_previews`
  is true. Confirmed.
- Promo footer and generator branding both use the bare version
  ("simpleGals 0.3.1"), no `v` prefix. Confirmed.
- Always-on generator branding (Feature 5) added: `<meta name="generator">` plus
  top and bottom HTML comments on every generated file, independent of the opt-in
  promo footer. Confirmed.

## Micro-defaults chosen (flag if you disagree)

- Top branding comment sits immediately after `<!DOCTYPE html>` (avoids legacy
  quirks mode); bottom comment is the last line after `</html>`.
- Comment text: `<!-- Generated with simpleGals 0.3.1 | https://github.com/simplegals/simpleGals -->`, identical top and bottom.
- Branding URL points at the org repo (`simplegals/simpleGals`); GitHub redirects
  cover the pre-transfer `timlnx` path.
