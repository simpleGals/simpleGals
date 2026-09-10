"""Structural checks on the stylesheets shipped with the built-in templates.

These are regression guards for issue #12: a bare ``1fr`` grid track is
``minmax(auto, 1fr)``, and that ``auto`` minimum resolves to the min-content
width of whatever is in the cell. A wide thumbnail or a long ``white-space:
nowrap`` caption then floors the track and the whole grid overflows the
viewport on a phone. Every flexible track must therefore be written as
``minmax(0, 1fr)``.
"""

import re
from pathlib import Path
import pytest
from simplegals.core.template import _BUILTIN_TEMPLATE_DIR

STYLESHEETS = sorted(Path(_BUILTIN_TEMPLATE_DIR).glob("*.css"))


def _strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", " ", css, flags=re.DOTALL)


def _strip_minmax(value: str) -> str:
    """Remove every balanced ``minmax(...)`` call from a declaration value."""
    out = []
    depth = 0
    i = 0
    while i < len(value):
        if depth == 0 and value.startswith("minmax(", i):
            depth = 1
            i += len("minmax(")
            continue
        if depth:
            if value[i] == "(":
                depth += 1
            elif value[i] == ")":
                depth -= 1
        else:
            out.append(value[i])
        i += 1
    return "".join(out)


def _declarations(css: str, prop: str) -> list[str]:
    """Return the values of every declaration of ``prop`` in the stylesheet."""
    pattern = re.compile(rf"(?<![-\w]){re.escape(prop)}\s*:\s*([^;{{}}]+)")
    return [m.group(1).strip() for m in pattern.finditer(_strip_comments(css))]


def _media_blocks(css: str) -> list[tuple[str, str]]:
    """Return (query, body) for each top-level ``@media`` block."""
    blocks = []
    css = _strip_comments(css)
    for match in re.finditer(r"@media([^{]+)\{", css):
        start = match.end()
        depth = 1
        i = start
        while i < len(css) and depth:
            if css[i] == "{":
                depth += 1
            elif css[i] == "}":
                depth -= 1
            i += 1
        blocks.append((match.group(1).strip(), css[start:i - 1]))
    return blocks


def test_stylesheets_are_discovered():
    assert STYLESHEETS, "no stylesheet found in the built-in template directory"


@pytest.mark.parametrize("sheet", STYLESHEETS, ids=lambda p: p.name)
def test_no_bare_fr_grid_tracks(sheet):
    """Every flexible grid track must carry an explicit zero minimum."""
    css = sheet.read_text(encoding="utf-8")
    offenders = [
        value
        for value in _declarations(css, "grid-template-columns") + _declarations(css, "grid-template-rows")
        if re.search(r"[\d.]+fr", _strip_minmax(value))
    ]
    assert not offenders, (
        f"{sheet.name}: flexible track(s) written without a minmax() minimum: {offenders}. "
        "Use minmax(0, 1fr) so content cannot floor the track width."
    )


@pytest.mark.parametrize("sheet", STYLESHEETS, ids=lambda p: p.name)
def test_gallery_grid_uses_minmax_zero(sheet):
    """The gallery grid specifically must use minmax(0, 1fr)."""
    css = _strip_comments(sheet.read_text(encoding="utf-8"))
    if ".gallery-grid" not in css:
        pytest.skip(f"{sheet.name} does not style .gallery-grid")
    tracks = [
        value
        for rule, value in _gallery_grid_column_rules(css)
        if rule
    ]
    assert tracks, f"{sheet.name}: .gallery-grid declares no grid-template-columns"
    for value in tracks:
        assert re.search(r"minmax\(\s*0\s*,", value), (
            f"{sheet.name}: .gallery-grid track list {value!r} must use minmax(0, ...)"
        )


def _gallery_grid_column_rules(css: str) -> list[tuple[str, str]]:
    """Return (selector, grid-template-columns value) for .gallery-grid rules."""
    found = []
    for match in re.finditer(r"([^{}]*)\{([^{}]*)\}", css):
        selector, body = match.group(1).strip(), match.group(2)
        if ".gallery-grid" not in selector:
            continue
        for value in _declarations(body + ";", "grid-template-columns"):
            found.append((selector, value))
    return found


@pytest.mark.parametrize("sheet", STYLESHEETS, ids=lambda p: p.name)
def test_gallery_grid_caps_columns_on_narrow_viewports(sheet):
    """The configured column count must be capped by a max-width media query."""
    css = _strip_comments(sheet.read_text(encoding="utf-8"))
    if ".gallery-grid" not in css:
        pytest.skip(f"{sheet.name} does not style .gallery-grid")
    widths = []
    for query, body in _media_blocks(css):
        if not _gallery_grid_column_rules(body):
            continue
        widths += [float(w) for w in re.findall(r"max-width\s*:\s*([\d.]+)px", query)]
    assert widths, (
        f"{sheet.name}: .gallery-grid has no max-width media query. A configured "
        "5-column grid on a 390px phone yields unusable thumbnails."
    )
    assert min(widths) <= 480, (
        f"{sheet.name}: narrowest .gallery-grid breakpoint is {min(widths)}px; "
        "phones need a breakpoint at 480px or below."
    )


@pytest.mark.parametrize("sheet", STYLESHEETS, ids=lambda p: p.name)
def test_nowrap_caption_cannot_widen_its_track(sheet):
    """A nowrap caption is only safe because the track has a zero minimum."""
    css = _strip_comments(sheet.read_text(encoding="utf-8"))
    if not re.search(r"\.gallery-item[^{}]*\.caption[^{}]*\{[^{}]*white-space\s*:\s*nowrap", css):
        pytest.skip(f"{sheet.name} has no nowrap gallery caption")
    for _selector, value in _gallery_grid_column_rules(css):
        assert re.search(r"minmax\(\s*0\s*,", value), (
            f"{sheet.name}: caption uses white-space: nowrap while the grid track "
            f"{value!r} has an auto minimum. The caption will floor the column width."
        )


def _rules(css: str) -> list[tuple[int, str, str]]:
    """Return (start offset, selector, body) for every rule, media blocks included."""
    found = []
    for match in re.finditer(r"([^{}@]+)\{([^{}]*)\}", css):
        found.append((match.start(), match.group(1).strip().strip("}").strip(), match.group(2)))
    return found


@pytest.mark.parametrize("sheet", STYLESHEETS, ids=lambda p: p.name)
def test_media_overrides_come_after_their_base_rules(sheet):
    """A media override loses to an equally specific base rule declared later.

    Media queries add no specificity, so ``@media`` blocks placed above the rule
    they mean to override are silently dead. Require every media override to sit
    later in the file than the base rule with the same selector and property.
    """
    css = _strip_comments(sheet.read_text(encoding="utf-8"))
    media_spans = []
    for query, body in _media_blocks(css):
        start = css.index(body)
        media_spans.append((start, start + len(body), query))

    def in_media(offset: int) -> str | None:
        for start, end, query in media_spans:
            if start <= offset < end:
                return query
        return None

    parsed = _rules(css)
    for offset, selector, body in parsed:
        query = in_media(offset)
        if query is None:
            continue
        for prop in re.findall(r"(?<![-\w])([a-z-]+)\s*:", body):
            for other_offset, other_selector, other_body in parsed:
                if other_offset <= offset or in_media(other_offset) is not None:
                    continue
                if other_selector != selector:
                    continue
                if re.search(rf"(?<![-\w]){re.escape(prop)}\s*:", other_body):
                    pytest.fail(
                        f"{sheet.name}: '@media {query}' overrides {prop} for '{selector}', but the "
                        f"base rule for that selector is declared later and wins. Move the media "
                        f"block below it."
                    )


@pytest.mark.parametrize("sheet", STYLESHEETS, ids=lambda p: p.name)
def test_ellipsis_rules_are_not_inert(sheet):
    """``text-overflow: ellipsis`` does nothing without overflow and nowrap."""
    css = _strip_comments(sheet.read_text(encoding="utf-8"))
    for _offset, selector, body in _rules(css):
        if not re.search(r"text-overflow\s*:\s*ellipsis", body):
            continue
        assert re.search(r"(?<![-\w])overflow\s*:\s*hidden", body), (
            f"{sheet.name}: '{selector}' sets text-overflow: ellipsis without overflow: hidden"
        )
        assert re.search(r"white-space\s*:\s*nowrap", body), (
            f"{sheet.name}: '{selector}' sets text-overflow: ellipsis without white-space: nowrap"
        )


@pytest.mark.parametrize("sheet", STYLESHEETS, ids=lambda p: p.name)
def test_item_nav_filenames_truncate(sheet):
    """Long filenames must ellipse rather than blow the prev/next buttons apart."""
    css = _strip_comments(sheet.read_text(encoding="utf-8"))
    if "item-nav" not in css:
        pytest.skip(f"{sheet.name} does not style the item nav")
    bodies = {selector: body for _offset, selector, body in _rules(css)}

    name_rule = next((b for s, b in bodies.items() if ".nav-name" in s and "item-nav" in s), None)
    assert name_rule is not None, f"{sheet.name}: no truncation rule for the item-nav filename"
    assert re.search(r"text-overflow\s*:\s*ellipsis", name_rule), (
        f"{sheet.name}: the item-nav filename does not truncate with an ellipsis"
    )

    link_rule = next((b for s, b in bodies.items() if re.fullmatch(r"nav\.item-nav a", s.strip())), None)
    assert link_rule is not None, f"{sheet.name}: no 'nav.item-nav a' rule"
    assert re.search(r"min-width\s*:\s*0", link_rule), (
        f"{sheet.name}: 'nav.item-nav a' needs min-width: 0, otherwise it will not shrink below the "
        "filename width and the ellipsis inside it never engages"
    )
    assert re.search(r"display\s*:\s*(inline-)?flex", link_rule), (
        f"{sheet.name}: 'nav.item-nav a' must be a flex container so the arrow can sit outside the "
        "truncating span"
    )
