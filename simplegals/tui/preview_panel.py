# simplegals/tui/preview_panel.py
from __future__ import annotations

from pathlib import Path
from typing import Callable

import bitmath
import urwid

from ..core.config import ProjectConfig
from .state import StagedChangesModel

try:
    from term_image.image import from_file as _from_file
    from term_image.widget import UrwidImage as _UrwidImage
    _HAS_TERM_IMAGE = True
except Exception:
    _HAS_TERM_IMAGE = False


def _tab_cycle(pile: urwid.Pile, size, forward: bool) -> None:
    """Move focus to the next/previous selectable widget in pile, wrapping around."""
    direction = "down" if forward else "up"
    if pile.keypress(size, direction) is not None:
        contents = pile.contents
        if forward:
            pos = next((i for i, (w, _) in enumerate(contents) if w.selectable()), None)
        else:
            pos = next(
                (len(contents) - 1 - i for i, (w, _) in enumerate(reversed(contents)) if w.selectable()),
                None,
            )
        if pos is not None:
            pile.focus_position = pos


class PreviewWidget(urwid.WidgetWrap):
    """Displays a terminal image preview. Falls back gracefully when term-image is unavailable."""

    def __init__(self) -> None:
        self._placeholder = urwid.Text("(No image selected)", align="center")
        super().__init__(self._placeholder)

    def load(self, thumb_path: Path) -> None:
        if not _HAS_TERM_IMAGE:
            self._w = urwid.Text(f"(Preview: {thumb_path.name})", align="center")
            return
        try:
            img = _from_file(str(thumb_path))
            self._w = _UrwidImage(img)
        except Exception as exc:
            self._w = urwid.Text(f"(Preview error: {exc})", align="center")

    def clear(self) -> None:
        self._w = self._placeholder


class ImageSettingsPanel(urwid.WidgetWrap):
    """Per-image settings: caption, alt text, include flag, Save and Revert buttons."""

    def __init__(
        self,
        filename: str,
        config: ProjectConfig,
        staged: StagedChangesModel,
        on_save: Callable,
        on_revert: Callable,
        on_change: Callable | None = None,
        source_path: Path | None = None,
        thumb_path: Path | None = None,
    ) -> None:
        self.filename = filename
        img = config.images.get(filename, {})

        caption_val = staged.get_current(filename, "caption", img.get("caption", ""))
        alt_val = staged.get_current(filename, "alt", img.get("alt", ""))
        include_val = staged.get_current(filename, "include", img.get("include", True))

        self.caption_field = urwid.Edit("Caption: ", edit_text=str(caption_val))
        self.alt_field = urwid.Edit("Alt:     ", edit_text=str(alt_val))
        self.include_check = urwid.CheckBox("Include in gallery", state=bool(include_val))
        save_btn = urwid.AttrMap(urwid.Button("Save", on_press=lambda _: on_save()), "button", "button_focus")
        revert_btn = urwid.AttrMap(urwid.Button("Revert", on_press=lambda _: on_revert()), "button", "button_focus")

        def _notify() -> None:
            if on_change is not None:
                on_change()

        def _on_caption_change(widget, _old):
            orig = img.get("caption", "")
            staged.stage(filename, "caption", orig, widget.edit_text)
            _notify()

        def _on_alt_change(widget, _old):
            orig = img.get("alt", "")
            staged.stage(filename, "alt", orig, widget.edit_text)
            _notify()

        def _on_include_change(widget, _old_state):
            orig = bool(img.get("include", True))
            staged.stage(filename, "include", orig, widget.state)
            _notify()

        urwid.connect_signal(self.caption_field, "postchange", _on_caption_change)
        urwid.connect_signal(self.alt_field, "postchange", _on_alt_change)
        urwid.connect_signal(self.include_check, "postchange", _on_include_change)

        orig_size = bitmath.getsize(source_path, bestprefix=True).format("{value:.2f} {unit}") if source_path and source_path.exists() else "?"
        thumb_size = bitmath.getsize(thumb_path, bestprefix=True).format("{value:.2f} {unit}") if thumb_path and thumb_path.exists() else "(pending)"
        size_line = urwid.Text(f"original: {orig_size}  thumb: {thumb_size}")

        pile = urwid.Pile([
            urwid.Text(f"Image: {filename}"),
            size_line,
            urwid.Divider(),
            self.caption_field,
            self.alt_field,
            self.include_check,
            urwid.Divider(),
            urwid.Columns([save_btn, revert_btn]),
        ])
        super().__init__(pile)

    def keypress(self, size, key: str) -> str | None:
        if key == "tab":
            _tab_cycle(self._w, size, forward=True)
            return None
        if key == "shift tab":
            _tab_cycle(self._w, size, forward=False)
            return None
        return self._w.keypress(size, key)


class GallerySettingsPanel(urwid.WidgetWrap):
    """Gallery-level settings: title, description, quality, copyright, columns, rows, template."""

    def __init__(
        self,
        config: ProjectConfig,
        staged: StagedChangesModel,
        on_save: Callable,
        on_revert: Callable,
        on_change: Callable | None = None,
    ) -> None:
        def _v(field: str, default) -> str:
            return str(staged.get_current("gallery", field, default))

        self.title_field = urwid.Edit("Title:       ", edit_text=_v("title", config.title))
        self.desc_field = urwid.Edit("Description: ", edit_text=_v("description", config.description))
        self.quality_field = urwid.Edit("Quality:     ", edit_text=_v("quality", config.quality))
        self.copyright_field = urwid.Edit("Copyright:   ", edit_text=_v("copyright", config.copyright))
        self.author_field = urwid.Edit("Author:      ", edit_text=_v("author", config.author))
        self.site_url_field = urwid.Edit("Site URL:    ", edit_text=_v("site_url", config.site_url))
        self.columns_field = urwid.Edit(
            "Columns:     ",
            edit_text=str(staged.get_current("gallery", "layout_columns", config.layout.columns)),
        )
        self.rows_field = urwid.Edit(
            "Rows:        ",
            edit_text=str(staged.get_current("gallery", "layout_rows", config.layout.rows)),
        )
        self.template_field = urwid.Edit("Template:    ", edit_text=_v("template", config.template or ""))
        self.social_previews_check = urwid.CheckBox(
            "Social media previews",
            state=bool(staged.get_current("gallery", "social_previews", config.social_previews)),
        )
        self.exif_display_check = urwid.CheckBox(
            "Show camera EXIF",
            state=bool(staged.get_current("gallery", "exif_display", config.exif_display)),
        )
        self.gallery_zip_check = urwid.CheckBox(
            "Generate gallery zip",
            state=bool(staged.get_current("gallery", "gallery_zip", config.gallery_zip)),
        )
        self.simple_gals_promo_check = urwid.CheckBox(
            "Show 'generated with simpleGals' footer",
            state=bool(staged.get_current("gallery", "simple_gals_promo", config.simple_gals_promo)),
        )
        save_btn = urwid.AttrMap(urwid.Button("Save", on_press=lambda _: on_save()), "button", "button_focus")
        revert_btn = urwid.AttrMap(urwid.Button("Revert", on_press=lambda _: on_revert()), "button", "button_focus")

        def _notify() -> None:
            if on_change is not None:
                on_change()

        def _on_title_change(widget, _old):
            staged.stage("gallery", "title", config.title, widget.edit_text)
            _notify()

        def _on_desc_change(widget, _old):
            staged.stage("gallery", "description", config.description, widget.edit_text)
            _notify()

        def _on_quality_change(widget, _old):
            try:
                val = int(widget.edit_text)
            except ValueError:
                return
            staged.stage("gallery", "quality", config.quality, val)
            _notify()

        def _on_copyright_change(widget, _old):
            staged.stage("gallery", "copyright", config.copyright, widget.edit_text)
            _notify()

        def _on_columns_change(widget, _old):
            try:
                val = int(widget.edit_text)
            except ValueError:
                return
            staged.stage("gallery", "layout_columns", config.layout.columns, val)
            _notify()

        def _on_rows_change(widget, _old):
            try:
                val = int(widget.edit_text)
            except ValueError:
                return
            staged.stage("gallery", "layout_rows", config.layout.rows, val)
            _notify()

        def _on_author_change(widget, _old):
            staged.stage("gallery", "author", config.author, widget.edit_text)
            _notify()

        def _on_site_url_change(widget, _old):
            staged.stage("gallery", "site_url", config.site_url, widget.edit_text)
            _notify()

        def _on_template_change(widget, _old):
            staged.stage("gallery", "template", config.template or "", widget.edit_text)
            _notify()

        def _on_social_previews_change(widget, _old_state):
            staged.stage("gallery", "social_previews", config.social_previews, widget.state)
            _notify()

        def _on_exif_display_change(widget, _old_state):
            staged.stage("gallery", "exif_display", config.exif_display, widget.state)
            _notify()

        def _on_gallery_zip_change(widget, _old_state):
            staged.stage("gallery", "gallery_zip", config.gallery_zip, widget.state)
            _notify()

        def _on_simple_gals_promo_change(widget, _old_state):
            staged.stage("gallery", "simple_gals_promo", config.simple_gals_promo, widget.state)
            _notify()

        urwid.connect_signal(self.title_field, "postchange", _on_title_change)
        urwid.connect_signal(self.desc_field, "postchange", _on_desc_change)
        urwid.connect_signal(self.quality_field, "postchange", _on_quality_change)
        urwid.connect_signal(self.copyright_field, "postchange", _on_copyright_change)
        urwid.connect_signal(self.author_field, "postchange", _on_author_change)
        urwid.connect_signal(self.site_url_field, "postchange", _on_site_url_change)
        urwid.connect_signal(self.columns_field, "postchange", _on_columns_change)
        urwid.connect_signal(self.rows_field, "postchange", _on_rows_change)
        urwid.connect_signal(self.template_field, "postchange", _on_template_change)
        urwid.connect_signal(self.social_previews_check, "postchange", _on_social_previews_change)
        urwid.connect_signal(self.exif_display_check, "postchange", _on_exif_display_change)
        urwid.connect_signal(self.gallery_zip_check, "postchange", _on_gallery_zip_change)
        urwid.connect_signal(self.simple_gals_promo_check, "postchange", _on_simple_gals_promo_change)

        pile = urwid.Pile([
            urwid.Text("Gallery Settings"),
            urwid.Divider(),
            self.title_field,
            self.desc_field,
            self.copyright_field,
            self.author_field,
            self.site_url_field,
            urwid.Text("  e.g. https://photos.example.com/gallery  (used for OG/social preview links)"),
            self.quality_field,
            self.columns_field,
            self.rows_field,
            self.template_field,
            self.social_previews_check,
            self.exif_display_check,
            self.gallery_zip_check,
            self.simple_gals_promo_check,
            urwid.Divider(),
            urwid.Columns([save_btn, revert_btn]),
        ])
        super().__init__(pile)

    def keypress(self, size, key: str) -> str | None:
        if key == "tab":
            _tab_cycle(self._w, size, forward=True)
            return None
        if key == "shift tab":
            _tab_cycle(self._w, size, forward=False)
            return None
        return self._w.keypress(size, key)


class RightPanel(urwid.WidgetWrap):
    """Right panel: preview widget (top 55%, capped at half panel width) and settings panel (bottom 45%)."""

    def __init__(self, preview: PreviewWidget, settings: urwid.Widget) -> None:
        self.preview = preview
        self._settings = settings
        super().__init__(self._build_pile())

    def _build_pile(self) -> urwid.Pile:
        preview_box = urwid.Padding(
            urwid.Filler(self.preview, "top"), "center", ("relative", 50)
        )
        return urwid.Pile([
            ("weight", 55, preview_box),
            ("weight", 45, urwid.Filler(self._settings, "top")),
        ])

    def update_settings(self, new_settings: urwid.Widget) -> None:
        self._settings = new_settings
        self._w = self._build_pile()
