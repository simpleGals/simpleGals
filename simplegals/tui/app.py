# simplegals/tui/app.py
from __future__ import annotations

import os
import signal
import threading
from dataclasses import replace
from pathlib import Path
from typing import Literal

import urwid

from ..core.config import GlobalConfig, ProjectConfig, save_project_config
from ..core.gallery import build, ensure_project_dirs, scan_sources
from ..core.processor import generate_sgui_thumb
from ..workers.progress import ProgressState
from .file_panel import FilePanel
from .preview_panel import (
    GallerySettingsPanel,
    ImageSettingsPanel,
    PreviewWidget,
    RightPanel,
)
from .progress_bar import BuildProgressPanel
from .state import StagedChangesModel

PALETTE = [
    ("header", "white,bold", "dark blue"),
    ("footer", "white", "dark blue"),
    ("selected", "black", "light gray"),
    ("dirty", "yellow", "default"),
    ("excluded", "dark gray", "default"),
    ("button", "black", "light cyan"),
    ("button_focus", "white,bold", "dark cyan"),
]

FOOTER_HINT = (
    "↑↓/^P^N navigate · Enter open · t toggle include · Tab cycle fields · "
    "Esc back · ^G settings · ^W write · ^R reload · ^C quit · ^B build"
)

Mode = Literal["file", "image", "gallery", "build"]


class SGUIApp:
    """Main sgui application: owns the urwid main loop and all UI state."""

    def __init__(
        self,
        project_dir: Path,
        config: ProjectConfig,
        global_config: GlobalConfig,
        config_path: Path,
    ) -> None:
        self._project_dir = project_dir
        self._config = config
        self._global_config = global_config
        self._config_path = config_path
        self._staged = StagedChangesModel()
        self._mode: Mode = "file"
        self._preview_alarm = None
        self._build_progress_state = ProgressState()
        self._build_log_path: Path | None = None
        self._build_had_errors: bool = False
        self._pipe: int | None = None
        self._loop: urwid.MainLoop | None = None
        self._quit_prompted: bool = False

        in_dir, _out_dir, meta_dir = ensure_project_dirs(project_dir)
        self._in_dir = in_dir
        self._meta_dir = meta_dir
        self._sources = scan_sources(in_dir)

        self._preview = PreviewWidget()
        self._build_progress_panel = BuildProgressPanel()

        self._file_panel = FilePanel(
            self._sources,
            dirty_filenames=set(),
            excluded_filenames=self._excluded_filenames(),
            on_selection_change=self._on_selection_change,
            on_enter=self._on_file_enter,
            on_toggle_include=self._toggle_include,
            scroll_rate=global_config.scroll_rate,
        )

        placeholder = urwid.Text("Select an image and press Enter.", align="center")
        self._right_panel = RightPanel(self._preview, placeholder)

        header = urwid.AttrMap(
            urwid.Text(f" sgui: {project_dir}", align="left"), "header"
        )
        footer = urwid.AttrMap(urwid.Text(FOOTER_HINT, align="left"), "footer")

        raw = global_config.file_panel_width
        try:
            if isinstance(raw, str) and raw.endswith("%"):
                file_col: tuple = ("weight", int(raw[:-1]), self._file_panel)
            else:
                file_col = (int(raw), self._file_panel)
        except (ValueError, TypeError):
            file_col = (30, self._file_panel)

        self._columns = urwid.Columns([file_col, self._right_panel])
        self._frame = urwid.Frame(self._columns, header=header, footer=footer)

    # ── public ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        self._loop = urwid.MainLoop(
            self._frame,
            palette=PALETTE,
            unhandled_input=self._unhandled_input,
        )
        self._pipe = self._loop.watch_pipe(self._on_pipe_data)
        self._file_panel._loop = self._loop

        def _sigint(signum, frame):
            if self._pipe is not None:
                try:
                    os.write(self._pipe, b"\x03")
                except OSError:
                    pass

        signal.signal(signal.SIGINT, _sigint)
        if not self._sources:
            self._loop.set_alarm_in(0, lambda loop, _: self._show_empty_dir_modal())
        else:
            self._loop.set_alarm_in(0, lambda loop, _: self._fire_first_preview())
        self._loop.run()

    # ── keyboard dispatch ──────────────────────────────────────────────────

    def _unhandled_input(self, key: str) -> None:
        if key == "ctrl b":
            self._trigger_build()
        elif key == "ctrl g":
            self._toggle_gallery_mode()
        elif key == "ctrl w":
            self._save_all()
        elif key == "ctrl r":
            self._reload_sources()
        elif key == "q":
            self._quit()
        elif key == "esc":
            if self._quit_prompted:
                self._close_overlay()
            elif self._mode in ("image", "gallery"):
                self._set_mode("file")

    def _toggle_gallery_mode(self) -> None:
        if self._mode == "gallery":
            self._set_mode("file")
        else:
            self._set_mode("gallery")

    # ── mode management ────────────────────────────────────────────────────

    def _set_mode(self, mode: Mode) -> None:
        self._mode = mode
        if mode == "file":
            self._right_panel.update_settings(
                urwid.Text("Select an image and press Enter.", align="center")
            )
            self._columns.focus_position = 0
        elif mode == "image":
            sel = self._file_panel.selected_filename
            if sel:
                source = self._in_dir / sel
                thumb = self._meta_dir / f"{source.stem}_thumb{source.suffix}"
                self._right_panel.update_settings(ImageSettingsPanel(
                    sel,
                    self._config,
                    self._staged,
                    on_save=lambda: self._save_key(sel),
                    on_revert=lambda: self._revert_key(sel),
                    on_change=self._on_field_change,
                    source_path=source,
                    thumb_path=thumb,
                ))
            self._columns.focus_position = 1
        elif mode == "gallery":
            self._right_panel.update_settings(GallerySettingsPanel(
                self._config,
                self._staged,
                on_save=lambda: self._save_key("gallery"),
                on_revert=lambda: self._revert_key("gallery"),
                on_change=self._on_field_change,
            ))
            self._columns.focus_position = 1
        elif mode == "build":
            self._right_panel.update_settings(self._build_progress_panel)
            self._columns.focus_position = 0
        if self._loop:
            self._loop.draw_screen()

    # ── settings field callbacks ───────────────────────────────────────────

    def _excluded_filenames(self) -> set[str]:
        excluded = set()
        for s in self._sources:
            img = self._config.images.get(s.name, {})
            if not self._staged.get_current(s.name, "include", img.get("include", True)):
                excluded.add(s.name)
        return excluded

    def _sync_file_panel_marks(self) -> None:
        self._file_panel.update_marks(set(self._staged.dirty_keys()), self._excluded_filenames())

    def _prune_stale_config_entries(self) -> None:
        current_names = {s.name for s in self._sources}
        stale = [k for k in self._config.images if k not in current_names]
        if stale:
            images = dict(self._config.images)
            for k in stale:
                del images[k]
                self._staged.revert(k)
            self._config.images = images
            save_project_config(self._config, self._config_path)

    def _on_field_change(self) -> None:
        """Called by settings panels when a widget value changes; refresh dirty marks."""
        self._sync_file_panel_marks()
        if self._loop:
            self._loop.draw_screen()

    # ── file panel callbacks ───────────────────────────────────────────────

    def _on_file_enter(self, filename: str | None) -> None:
        if filename:
            self._set_mode("image")

    def _toggle_include(self, filename: str | None) -> None:
        if not filename:
            return
        img = self._config.images.get(filename, {})
        current = self._staged.get_current(filename, "include", img.get("include", True))
        self._staged.stage(filename, "include", img.get("include", True), not current)
        self._sync_file_panel_marks()
        if self._loop:
            self._loop.draw_screen()

    def _on_selection_change(self, filename: str) -> None:
        if self._loop and self._preview_alarm:
            self._loop.remove_alarm(self._preview_alarm)
            self._preview_alarm = None
        if self._loop:
            delay = self._global_config.preview_delay / 1000.0
            self._preview_alarm = self._loop.set_alarm_in(
                delay, self._fire_preview, filename
            )

    def _fire_preview(self, loop, filename: str) -> None:
        self._preview_alarm = None
        source = self._in_dir / filename
        thumb_path = self._meta_dir / f"{source.stem}_thumb{source.suffix}"
        if not thumb_path.exists():
            try:
                generate_sgui_thumb(source, self._meta_dir)
            except Exception:
                self._preview.clear()
                loop.draw_screen()
                return
        self._preview.load(thumb_path)
        loop.draw_screen()

    def _fire_first_preview(self) -> None:
        filename = self._file_panel.selected_filename
        if filename and self._loop:
            self._fire_preview(self._loop, filename)

    def _show_empty_dir_modal(self) -> None:
        close_btn = urwid.Button("OK", on_press=self._close_overlay)
        body = urwid.Pile([
            urwid.Text("No images found in in/", align="center"),
            urwid.Divider(),
            urwid.Text(
                f"Add images to {self._in_dir}\nthen press Ctrl+R to reload.",
                align="center",
            ),
            urwid.Divider(),
            urwid.Padding(close_btn, "center", 6),
        ])
        self._push_overlay(body, width=60, height=10)

    def _reload_sources(self) -> None:
        if self._loop and self._preview_alarm:
            self._loop.remove_alarm(self._preview_alarm)
            self._preview_alarm = None
        self._sources = scan_sources(self._in_dir)
        self._prune_stale_config_entries()
        self._file_panel.reload(
            self._sources,
            set(self._staged.dirty_keys()),
            self._excluded_filenames(),
        )
        self._preview.clear()
        self._set_mode("file")
        if self._sources and self._loop:
            self._loop.set_alarm_in(0, lambda loop, _: self._fire_first_preview())

    # ── save / revert ──────────────────────────────────────────────────────

    def _save_current(self) -> None:
        if self._mode == "image":
            sel = self._file_panel.selected_filename
            if sel:
                self._save_key(sel)
        elif self._mode == "gallery":
            self._save_key("gallery")

    def _save_key(self, key: str) -> None:
        self._config = self._staged.commit_key(key, self._config, self._config_path)
        self._sync_file_panel_marks()
        self._set_mode(self._mode)

    def _revert_key(self, key: str) -> None:
        self._staged.revert(key)
        self._sync_file_panel_marks()
        self._set_mode(self._mode)

    def _save_all(self) -> None:
        self._config = self._staged.commit_all(self._config, self._config_path)
        self._sync_file_panel_marks()
        self._set_mode("file")

    # ── quit ───────────────────────────────────────────────────────────────

    def _quit(self) -> None:
        if self._staged.has_any_dirty() and not self._quit_prompted:
            self._quit_prompted = True
            self._show_quit_prompt()
        else:
            raise urwid.ExitMainLoop()

    def _show_quit_prompt(self) -> None:
        save_btn = urwid.Button("Save & quit", on_press=self._save_all_and_quit)
        discard_btn = urwid.Button("Quit without saving", on_press=self._discard_and_quit)
        body = urwid.Pile([
            urwid.Text("Save before quitting?", align="center"),
            urwid.Divider(),
            urwid.Columns([save_btn, discard_btn]),
        ])
        self._push_overlay(body, width=60, height=7)

    def _save_all_and_quit(self, _) -> None:
        self._save_all()
        raise urwid.ExitMainLoop()

    def _discard_and_quit(self, _) -> None:
        raise urwid.ExitMainLoop()

    def _close_overlay(self, _=None) -> None:
        self._quit_prompted = False
        if self._loop:
            self._loop.widget = self._frame

    def _push_overlay(self, body: urwid.Widget, width: int, height: int) -> None:
        overlay = urwid.Overlay(
            urwid.LineBox(urwid.Filler(body, "top")),
            self._frame,
            "center", width, "middle", height,
        )
        if self._loop:
            self._loop.widget = overlay

    # ── build ──────────────────────────────────────────────────────────────

    def _trigger_build(self) -> None:
        self._build_progress_state = ProgressState()
        self._build_progress_panel.update(self._build_progress_state)
        self._set_mode("build")
        threading.Thread(target=self._run_build, daemon=True).start()

    def _run_build(self) -> None:
        def progress_callback(state: ProgressState) -> None:
            self._build_progress_state = replace(state)
            if self._pipe is not None:
                try:
                    os.write(self._pipe, b"\x00")
                except OSError:
                    pass

        log_path, had_errors = build(
            self._project_dir, self._config, progress_callback=progress_callback
        )
        self._build_log_path = log_path
        self._build_had_errors = had_errors
        if self._pipe is not None:
            try:
                os.write(self._pipe, b"\x01" if had_errors else b"\x02")
            except OSError:
                pass

    def _on_pipe_data(self, data: bytes) -> None:
        if b"\x00" in data:
            self._build_progress_panel.update(self._build_progress_state)
        if b"\x01" in data:
            self._show_build_error_modal()
        elif b"\x02" in data:
            self._prune_stale_config_entries()
            self._sync_file_panel_marks()
            self._set_mode("file")
        if b"\x03" in data:
            self._quit()
        if self._loop:
            self._loop.draw_screen()

    def _show_build_error_modal(self) -> None:
        log_content = ""
        if self._build_log_path and self._build_log_path.exists():
            log_content = self._build_log_path.read_text(encoding="utf-8")
        log_widget = urwid.Text(log_content or "(empty log)")
        log_box = urwid.BoxAdapter(
            urwid.ListBox(urwid.SimpleListWalker([log_widget])), 20
        )
        close_btn = urwid.Button("Close", on_press=self._close_overlay)
        body = urwid.Pile([
            urwid.Text(f"Build error: {self._build_log_path}", align="center"),
            urwid.Divider(),
            log_box,
            urwid.Divider(),
            close_btn,
        ])
        self._push_overlay(body, ("relative", 80), ("relative", 70))
