# tests/test_tui_widgets.py
import pytest
from pathlib import Path


def test_selectable_image_row_shows_filename():
    from simplegals.tui.file_panel import SelectableImageRow
    row = SelectableImageRow("IMG_1234.jpg", dirty=False)
    assert "IMG_1234.jpg" in row.label


def test_selectable_image_row_shows_dirty_indicator():
    from simplegals.tui.file_panel import SelectableImageRow
    row = SelectableImageRow("IMG_1234.jpg", dirty=True)
    assert "*" in row.label


def test_selectable_image_row_not_dirty_no_star():
    from simplegals.tui.file_panel import SelectableImageRow
    row = SelectableImageRow("IMG_1234.jpg", dirty=False)
    assert "* " not in row.label


def test_selectable_image_row_update_dirty():
    from simplegals.tui.file_panel import SelectableImageRow
    row = SelectableImageRow("IMG_1234.jpg", dirty=False)
    row.update_marks(True, False)
    assert "*" in row.label


def test_file_panel_source_count():
    from simplegals.tui.file_panel import FilePanel
    sources = [Path("a.jpg"), Path("b.jpg"), Path("c.jpg")]
    panel = FilePanel(sources, dirty_filenames=set())
    assert panel.source_count == 3


def test_file_panel_selected_index_starts_at_zero():
    from simplegals.tui.file_panel import FilePanel
    sources = [Path("a.jpg"), Path("b.jpg")]
    panel = FilePanel(sources, dirty_filenames=set())
    assert panel.selected_index == 0


def test_file_panel_selected_filename():
    from simplegals.tui.file_panel import FilePanel
    sources = [Path("a.jpg"), Path("b.jpg")]
    panel = FilePanel(sources, dirty_filenames=set())
    assert panel.selected_filename == "a.jpg"


def test_file_panel_empty_sources():
    from simplegals.tui.file_panel import FilePanel
    panel = FilePanel([], dirty_filenames=set())
    assert panel.source_count == 0
    assert panel.selected_filename is None


def test_truncate_short_text():
    from simplegals.tui.file_panel import _truncate
    assert _truncate("short", 20) == "short"


def test_truncate_long_text():
    from simplegals.tui.file_panel import _truncate
    result = _truncate("IMG_very_long_filename.jpg", 12)
    assert len(result) <= 12
    assert result.endswith("…")


def test_preview_widget_instantiates():
    from simplegals.tui.preview_panel import PreviewWidget
    widget = PreviewWidget()
    assert widget is not None


def test_image_settings_panel_caption_field(tmp_path):
    from simplegals.core.config import ProjectConfig
    from simplegals.tui.preview_panel import ImageSettingsPanel
    from simplegals.tui.state import StagedChangesModel
    config = ProjectConfig(images={"a.jpg": {"caption": "hello", "alt": "", "include": True}})
    staged = StagedChangesModel()
    panel = ImageSettingsPanel(
        "a.jpg", config, staged, on_save=lambda: None, on_revert=lambda: None
    )
    assert panel.caption_field.edit_text == "hello"


def test_image_settings_panel_include_state(tmp_path):
    from simplegals.core.config import ProjectConfig
    from simplegals.tui.preview_panel import ImageSettingsPanel
    from simplegals.tui.state import StagedChangesModel
    config = ProjectConfig(images={"a.jpg": {"caption": "", "alt": "", "include": False}})
    staged = StagedChangesModel()
    panel = ImageSettingsPanel(
        "a.jpg", config, staged, on_save=lambda: None, on_revert=lambda: None
    )
    assert panel.include_check.state is False


def test_gallery_settings_panel_title_field():
    from simplegals.core.config import ProjectConfig
    from simplegals.tui.preview_panel import GallerySettingsPanel
    from simplegals.tui.state import StagedChangesModel
    config = ProjectConfig(title="My Gallery")
    staged = StagedChangesModel()
    panel = GallerySettingsPanel(
        config, staged, on_save=lambda: None, on_revert=lambda: None
    )
    assert panel.title_field.edit_text == "My Gallery"


def test_gallery_settings_panel_columns_field():
    from simplegals.core.config import Layout, ProjectConfig
    from simplegals.tui.preview_panel import GallerySettingsPanel
    from simplegals.tui.state import StagedChangesModel
    config = ProjectConfig(layout=Layout(columns=3, rows=4))
    staged = StagedChangesModel()
    panel = GallerySettingsPanel(
        config, staged, on_save=lambda: None, on_revert=lambda: None
    )
    assert panel.columns_field.edit_text == "3"


def test_right_panel_instantiates():
    from simplegals.tui.preview_panel import PreviewWidget, RightPanel
    import urwid
    preview = PreviewWidget()
    content = urwid.Text("placeholder")
    panel = RightPanel(preview, content)
    assert panel is not None


def test_render_bar_zero_progress():
    from simplegals.tui.progress_bar import _render_bar
    result = _render_bar(0, 0, 4, "Previews")
    assert "0/4" in result
    assert "░" * 20 in result


def test_render_bar_full_progress():
    from simplegals.tui.progress_bar import _render_bar
    result = _render_bar(4, 0, 4, "Output ")
    assert "4/4" in result
    assert "█" * 20 in result


def test_render_bar_with_errors():
    from simplegals.tui.progress_bar import _render_bar
    result = _render_bar(3, 1, 4, "Output ")
    assert "1 err" in result


def test_build_progress_widget_shows_counts():
    from simplegals.tui.progress_bar import BuildProgressWidget
    widget = BuildProgressWidget(2, 0, 4, "Previews")
    assert "2/4" in widget.text


def test_build_progress_panel_instantiates():
    from simplegals.tui.progress_bar import BuildProgressPanel
    from simplegals.workers.progress import ProgressState
    panel = BuildProgressPanel()
    state = ProgressState(thumb_total=2, thumb_done=1, output_total=2, output_done=0)
    panel.update(state)  # should not raise


def test_sgui_app_instantiates(tmp_project):
    from simplegals.core.config import GlobalConfig, ProjectConfig
    from simplegals.tui.app import SGUIApp
    config = ProjectConfig()
    global_config = GlobalConfig()
    config_path = tmp_project / "simpleGal.json"
    app = SGUIApp(tmp_project, config, global_config, config_path)
    assert app is not None


def test_sgui_app_mode_starts_as_file(tmp_project):
    from simplegals.core.config import GlobalConfig, ProjectConfig
    from simplegals.tui.app import SGUIApp
    config = ProjectConfig()
    global_config = GlobalConfig()
    config_path = tmp_project / "simpleGal.json"
    app = SGUIApp(tmp_project, config, global_config, config_path)
    assert app._mode == "file"


def test_sgui_app_no_dirty_on_start(tmp_project):
    from simplegals.core.config import GlobalConfig, ProjectConfig
    from simplegals.tui.app import SGUIApp
    config = ProjectConfig()
    global_config = GlobalConfig()
    config_path = tmp_project / "simpleGal.json"
    app = SGUIApp(tmp_project, config, global_config, config_path)
    assert not app._staged.has_any_dirty()


def test_sgui_help_exits_zero():
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "simplegals.tui", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "sgui" in result.stdout


def test_image_settings_panel_caption_change_stages():
    from simplegals.core.config import ProjectConfig
    from simplegals.tui.preview_panel import ImageSettingsPanel
    from simplegals.tui.state import StagedChangesModel
    config = ProjectConfig(images={"a.jpg": {"caption": "old", "alt": "", "include": True}})
    staged = StagedChangesModel()
    panel = ImageSettingsPanel(
        "a.jpg", config, staged, on_save=lambda: None, on_revert=lambda: None
    )
    panel.caption_field.set_edit_text("new caption")
    assert staged.get_current("a.jpg", "caption", None) == "new caption"
    assert staged.is_dirty("a.jpg")


def test_image_settings_panel_alt_change_stages():
    from simplegals.core.config import ProjectConfig
    from simplegals.tui.preview_panel import ImageSettingsPanel
    from simplegals.tui.state import StagedChangesModel
    config = ProjectConfig(images={"a.jpg": {"caption": "", "alt": "old alt", "include": True}})
    staged = StagedChangesModel()
    panel = ImageSettingsPanel(
        "a.jpg", config, staged, on_save=lambda: None, on_revert=lambda: None
    )
    panel.alt_field.set_edit_text("new alt")
    assert staged.get_current("a.jpg", "alt", None) == "new alt"


def test_image_settings_panel_include_toggle_stages():
    from simplegals.core.config import ProjectConfig
    from simplegals.tui.preview_panel import ImageSettingsPanel
    from simplegals.tui.state import StagedChangesModel
    config = ProjectConfig(images={"a.jpg": {"caption": "", "alt": "", "include": True}})
    staged = StagedChangesModel()
    panel = ImageSettingsPanel(
        "a.jpg", config, staged, on_save=lambda: None, on_revert=lambda: None
    )
    panel.include_check.set_state(False)
    assert staged.get_current("a.jpg", "include", None) is False
    assert staged.is_dirty("a.jpg")


def test_image_settings_panel_on_change_callback_fires():
    from simplegals.core.config import ProjectConfig
    from simplegals.tui.preview_panel import ImageSettingsPanel
    from simplegals.tui.state import StagedChangesModel
    config = ProjectConfig(images={"a.jpg": {"caption": "", "alt": "", "include": True}})
    staged = StagedChangesModel()
    fired = []
    panel = ImageSettingsPanel(
        "a.jpg",
        config,
        staged,
        on_save=lambda: None,
        on_revert=lambda: None,
        on_change=lambda: fired.append(True),
    )
    panel.caption_field.set_edit_text("hi")
    assert fired, "on_change should fire when caption widget changes"


def test_gallery_settings_panel_title_change_stages():
    from simplegals.core.config import ProjectConfig
    from simplegals.tui.preview_panel import GallerySettingsPanel
    from simplegals.tui.state import StagedChangesModel
    config = ProjectConfig(title="Old Title")
    staged = StagedChangesModel()
    panel = GallerySettingsPanel(
        config, staged, on_save=lambda: None, on_revert=lambda: None
    )
    panel.title_field.set_edit_text("New Title")
    assert staged.get_current("gallery", "title", None) == "New Title"
    assert staged.is_dirty("gallery")


def test_gallery_settings_panel_columns_change_stages_int():
    from simplegals.core.config import Layout, ProjectConfig
    from simplegals.tui.preview_panel import GallerySettingsPanel
    from simplegals.tui.state import StagedChangesModel
    config = ProjectConfig(layout=Layout(columns=3, rows=4))
    staged = StagedChangesModel()
    panel = GallerySettingsPanel(
        config, staged, on_save=lambda: None, on_revert=lambda: None
    )
    panel.columns_field.set_edit_text("7")
    assert staged.get_current("gallery", "layout_columns", None) == 7


def test_gallery_settings_panel_new_booleans_commit(tmp_path):
    from simplegals.tui.preview_panel import GallerySettingsPanel
    from simplegals.tui.state import StagedChangesModel
    from simplegals.core.config import ProjectConfig
    config = ProjectConfig()  # social_previews=True, exif_display=True, gallery_zip/promo=False
    staged = StagedChangesModel()
    panel = GallerySettingsPanel(config, staged, on_save=lambda: None, on_revert=lambda: None)
    panel.social_previews_check.set_state(False)
    panel.exif_display_check.set_state(False)
    panel.gallery_zip_check.set_state(True)
    panel.simple_gals_promo_check.set_state(True)
    new_config = staged.commit_key("gallery", config, tmp_path / "simpleGal.json")
    assert new_config.social_previews is False
    assert new_config.exif_display is False
    assert new_config.gallery_zip is True
    assert new_config.simple_gals_promo is True


def test_gallery_settings_panel_quality_invalid_int_ignored():
    from simplegals.core.config import ProjectConfig
    from simplegals.tui.preview_panel import GallerySettingsPanel
    from simplegals.tui.state import StagedChangesModel
    config = ProjectConfig(quality=90)
    staged = StagedChangesModel()
    panel = GallerySettingsPanel(
        config, staged, on_save=lambda: None, on_revert=lambda: None
    )
    panel.quality_field.set_edit_text("abc")
    assert staged.get_current("gallery", "quality", None) is None


def test_sgui_app_handles_percent_panel_width(tmp_project):
    from simplegals.core.config import GlobalConfig, ProjectConfig
    from simplegals.tui.app import SGUIApp
    config = ProjectConfig()
    global_config = GlobalConfig(file_panel_width="30%")
    config_path = tmp_project / "simpleGal.json"
    app = SGUIApp(tmp_project, config, global_config, config_path)
    assert app is not None


def test_sgui_app_handles_invalid_panel_width(tmp_project):
    from simplegals.core.config import GlobalConfig, ProjectConfig
    from simplegals.tui.app import SGUIApp
    config = ProjectConfig()
    global_config = GlobalConfig(file_panel_width="garbage")
    config_path = tmp_project / "simpleGal.json"
    app = SGUIApp(tmp_project, config, global_config, config_path)
    assert app is not None


# ── dirty color indicator ──────────────────────────────────────────────────

def test_selectable_image_row_dirty_applies_color_attr():
    from simplegals.tui.file_panel import SelectableImageRow
    import urwid
    row = SelectableImageRow("a.jpg", dirty=True)
    assert isinstance(row._w, urwid.AttrMap)
    assert row._w.attr_map.get(None) == "dirty"


def test_selectable_image_row_clean_has_no_color_attr():
    from simplegals.tui.file_panel import SelectableImageRow
    row = SelectableImageRow("a.jpg", dirty=False)
    assert row._w.attr_map.get(None) is None


def test_selectable_image_row_update_dirty_changes_attr():
    from simplegals.tui.file_panel import SelectableImageRow
    row = SelectableImageRow("a.jpg", dirty=False)
    row.update_marks(True, False)
    assert row._w.attr_map.get(None) == "dirty"


def test_selectable_image_row_update_clean_removes_attr():
    from simplegals.tui.file_panel import SelectableImageRow
    row = SelectableImageRow("a.jpg", dirty=True)
    row.update_marks(False, False)
    assert row._w.attr_map.get(None) is None


# ── file size display in ImageSettingsPanel ────────────────────────────────

def test_image_settings_panel_shows_source_size(tmp_path):
    from simplegals.core.config import ProjectConfig
    from simplegals.tui.preview_panel import ImageSettingsPanel
    from simplegals.tui.state import StagedChangesModel
    source = tmp_path / "a.jpg"
    source.write_bytes(b"x" * 2048)
    config = ProjectConfig()
    staged = StagedChangesModel()
    panel = ImageSettingsPanel(
        "a.jpg", config, staged,
        on_save=lambda: None, on_revert=lambda: None,
        source_path=source,
    )
    size_widget = panel._w.contents[1][0]
    assert "original" in size_widget.text
    assert "2.00 KiB" in size_widget.text


def test_image_settings_panel_thumb_pending_when_missing(tmp_path):
    from simplegals.core.config import ProjectConfig
    from simplegals.tui.preview_panel import ImageSettingsPanel
    from simplegals.tui.state import StagedChangesModel
    source = tmp_path / "a.jpg"
    source.write_bytes(b"x" * 100)
    thumb = tmp_path / "a_thumb.jpg"  # does not exist
    config = ProjectConfig()
    staged = StagedChangesModel()
    panel = ImageSettingsPanel(
        "a.jpg", config, staged,
        on_save=lambda: None, on_revert=lambda: None,
        source_path=source, thumb_path=thumb,
    )
    size_widget = panel._w.contents[1][0]
    assert "(pending)" in size_widget.text


def test_image_settings_panel_thumb_size_when_present(tmp_path):
    from simplegals.core.config import ProjectConfig
    from simplegals.tui.preview_panel import ImageSettingsPanel
    from simplegals.tui.state import StagedChangesModel
    source = tmp_path / "a.jpg"
    source.write_bytes(b"x" * 1024)
    thumb = tmp_path / "a_thumb.jpg"
    thumb.write_bytes(b"t" * 512)
    config = ProjectConfig()
    staged = StagedChangesModel()
    panel = ImageSettingsPanel(
        "a.jpg", config, staged,
        on_save=lambda: None, on_revert=lambda: None,
        source_path=source, thumb_path=thumb,
    )
    size_widget = panel._w.contents[1][0]
    assert "thumb" in size_widget.text
    assert "(pending)" not in size_widget.text


def test_image_settings_panel_unknown_source_shows_question_mark():
    from simplegals.core.config import ProjectConfig
    from simplegals.tui.preview_panel import ImageSettingsPanel
    from simplegals.tui.state import StagedChangesModel
    config = ProjectConfig()
    staged = StagedChangesModel()
    panel = ImageSettingsPanel(
        "a.jpg", config, staged, on_save=lambda: None, on_revert=lambda: None
    )
    size_widget = panel._w.contents[1][0]
    assert "?" in size_widget.text


# ── Tab cycling in settings panels ────────────────────────────────────────

def test_image_settings_panel_tab_is_consumed():
    from simplegals.core.config import ProjectConfig
    from simplegals.tui.preview_panel import ImageSettingsPanel
    from simplegals.tui.state import StagedChangesModel
    config = ProjectConfig()
    staged = StagedChangesModel()
    panel = ImageSettingsPanel(
        "a.jpg", config, staged, on_save=lambda: None, on_revert=lambda: None
    )
    assert panel.keypress((80,), "tab") is None


def test_image_settings_panel_shift_tab_is_consumed():
    from simplegals.core.config import ProjectConfig
    from simplegals.tui.preview_panel import ImageSettingsPanel
    from simplegals.tui.state import StagedChangesModel
    config = ProjectConfig()
    staged = StagedChangesModel()
    panel = ImageSettingsPanel(
        "a.jpg", config, staged, on_save=lambda: None, on_revert=lambda: None
    )
    assert panel.keypress((80,), "shift tab") is None


def test_image_settings_panel_tab_moves_focus_forward():
    from simplegals.core.config import ProjectConfig
    from simplegals.tui.preview_panel import ImageSettingsPanel
    from simplegals.tui.state import StagedChangesModel
    config = ProjectConfig()
    staged = StagedChangesModel()
    panel = ImageSettingsPanel(
        "a.jpg", config, staged, on_save=lambda: None, on_revert=lambda: None
    )
    initial_pos = panel._w.focus_position
    panel.keypress((80,), "tab")
    assert panel._w.focus_position > initial_pos


def test_image_settings_panel_tab_wraps_to_first():
    from simplegals.core.config import ProjectConfig
    from simplegals.tui.preview_panel import ImageSettingsPanel
    from simplegals.tui.state import StagedChangesModel
    config = ProjectConfig()
    staged = StagedChangesModel()
    panel = ImageSettingsPanel(
        "a.jpg", config, staged, on_save=lambda: None, on_revert=lambda: None
    )
    initial_pos = panel._w.focus_position
    for _ in range(20):  # tab past all fields repeatedly
        panel.keypress((80,), "tab")
    assert panel._w.focus_position == initial_pos


def test_image_settings_panel_shift_tab_moves_focus_backward():
    from simplegals.core.config import ProjectConfig
    from simplegals.tui.preview_panel import ImageSettingsPanel
    from simplegals.tui.state import StagedChangesModel
    config = ProjectConfig()
    staged = StagedChangesModel()
    panel = ImageSettingsPanel(
        "a.jpg", config, staged, on_save=lambda: None, on_revert=lambda: None
    )
    panel.keypress((80,), "tab")  # move forward first
    pos_after_tab = panel._w.focus_position
    panel.keypress((80,), "shift tab")
    assert panel._w.focus_position < pos_after_tab


def test_gallery_settings_panel_tab_is_consumed():
    from simplegals.core.config import ProjectConfig
    from simplegals.tui.preview_panel import GallerySettingsPanel
    from simplegals.tui.state import StagedChangesModel
    config = ProjectConfig()
    staged = StagedChangesModel()
    panel = GallerySettingsPanel(
        config, staged, on_save=lambda: None, on_revert=lambda: None
    )
    assert panel.keypress((80,), "tab") is None


def test_gallery_settings_panel_tab_moves_focus_forward():
    from simplegals.core.config import ProjectConfig
    from simplegals.tui.preview_panel import GallerySettingsPanel
    from simplegals.tui.state import StagedChangesModel
    config = ProjectConfig()
    staged = StagedChangesModel()
    panel = GallerySettingsPanel(
        config, staged, on_save=lambda: None, on_revert=lambda: None
    )
    initial_pos = panel._w.focus_position
    panel.keypress((80,), "tab")
    assert panel._w.focus_position > initial_pos


# ── RightPanel half-width preview ─────────────────────────────────────────

def test_right_panel_preview_wrapped_in_padding():
    from simplegals.tui.preview_panel import PreviewWidget, RightPanel
    import urwid
    preview = PreviewWidget()
    placeholder = urwid.Text("placeholder")
    panel = RightPanel(preview, placeholder)
    first_weight_widget = panel._w.contents[0][0]
    assert isinstance(first_weight_widget, urwid.Padding)


def test_right_panel_preview_padding_is_50_percent_centered():
    from simplegals.tui.preview_panel import PreviewWidget, RightPanel
    import urwid
    preview = PreviewWidget()
    placeholder = urwid.Text("placeholder")
    panel = RightPanel(preview, placeholder)
    padding = panel._w.contents[0][0]
    assert padding._width_type == urwid.RELATIVE
    assert padding._width_amount == 50
    assert padding._align_type == urwid.CENTER


# ── app keybindings ────────────────────────────────────────────────────────

def test_footer_hint_uses_ctrl_w_write_out():
    from simplegals.tui.app import FOOTER_HINT
    assert "^W" in FOOTER_HINT
    assert "write" in FOOTER_HINT


def test_footer_hint_uses_ctrl_c_quit():
    from simplegals.tui.app import FOOTER_HINT
    assert "^C" in FOOTER_HINT
    assert "^|" not in FOOTER_HINT
    assert "^S" not in FOOTER_HINT


def test_sgui_app_ctrl_w_saves_all(tmp_project):
    from simplegals.core.config import GlobalConfig, ProjectConfig
    from simplegals.tui.app import SGUIApp
    config = ProjectConfig()
    global_config = GlobalConfig()
    config_path = tmp_project / "simpleGal.json"
    app = SGUIApp(tmp_project, config, global_config, config_path)
    called = []
    app._save_all = lambda: called.append(True)
    app._unhandled_input("ctrl w")
    assert called, "ctrl+w should trigger save_all"


def test_sgui_app_ctrl_s_not_bound(tmp_project):
    from simplegals.core.config import GlobalConfig, ProjectConfig
    from simplegals.tui.app import SGUIApp
    config = ProjectConfig()
    global_config = GlobalConfig()
    config_path = tmp_project / "simpleGal.json"
    app = SGUIApp(tmp_project, config, global_config, config_path)
    called = []
    app._save_all = lambda: called.append(True)
    app._unhandled_input("ctrl s")
    assert not called, "ctrl+s should no longer be bound"


def test_sgui_app_q_triggers_quit_when_clean(tmp_project):
    import urwid
    from simplegals.core.config import GlobalConfig, ProjectConfig
    from simplegals.tui.app import SGUIApp
    config = ProjectConfig()
    global_config = GlobalConfig()
    config_path = tmp_project / "simpleGal.json"
    app = SGUIApp(tmp_project, config, global_config, config_path)
    with pytest.raises(urwid.ExitMainLoop):
        app._unhandled_input("q")


def test_sgui_app_quit_shows_prompt_when_dirty(tmp_project):
    from simplegals.core.config import GlobalConfig, ProjectConfig
    from simplegals.tui.app import SGUIApp
    config = ProjectConfig()
    global_config = GlobalConfig()
    config_path = tmp_project / "simpleGal.json"
    app = SGUIApp(tmp_project, config, global_config, config_path)
    app._staged.stage("a.jpg", "caption", "old", "new")
    prompts = []
    app._show_quit_prompt = lambda: prompts.append(True)
    app._quit()
    assert prompts, "dirty state should show quit prompt"
    assert app._quit_prompted


def test_sgui_app_second_quit_exits_immediately(tmp_project):
    import urwid
    from simplegals.core.config import GlobalConfig, ProjectConfig
    from simplegals.tui.app import SGUIApp
    config = ProjectConfig()
    global_config = GlobalConfig()
    config_path = tmp_project / "simpleGal.json"
    app = SGUIApp(tmp_project, config, global_config, config_path)
    app._staged.stage("a.jpg", "caption", "old", "new")
    app._quit_prompted = True  # simulate dialog already shown
    with pytest.raises(urwid.ExitMainLoop):
        app._quit()


def test_sgui_app_esc_dismisses_quit_dialog(tmp_project):
    from simplegals.core.config import GlobalConfig, ProjectConfig
    from simplegals.tui.app import SGUIApp
    config = ProjectConfig()
    global_config = GlobalConfig()
    config_path = tmp_project / "simpleGal.json"
    app = SGUIApp(tmp_project, config, global_config, config_path)
    app._quit_prompted = True
    app._close_overlay = lambda _=None: setattr(app, "_quit_prompted", False)
    app._unhandled_input("esc")
    assert not app._quit_prompted


# ── clip wrap + marquee scroll ─────────────────────────────────────────────

def test_selectable_image_row_uses_clip_wrap():
    from simplegals.tui.file_panel import SelectableImageRow
    import urwid
    row = SelectableImageRow("IMG_very_long_filename.jpg", dirty=False)
    assert row._icon.wrap == urwid.WrapMode.CLIP


class MockLoop:
    def __init__(self):
        self.scheduled = []
        self.removed = []
        self.draw_count = 0
        self._counter = 0

    def set_alarm_in(self, delay, cb, *args):
        handle = self._counter
        self._counter += 1
        self.scheduled.append((handle, delay, cb, args))
        return handle

    def remove_alarm(self, handle):
        self.removed.append(handle)
        self.scheduled = [(h, d, c, a) for h, d, c, a in self.scheduled if h != handle]

    def draw_screen(self):
        self.draw_count += 1


def test_file_panel_accepts_loop_and_scroll_rate():
    from simplegals.tui.file_panel import FilePanel
    loop = MockLoop()
    sources = [Path("a.jpg")]
    panel = FilePanel(sources, dirty_filenames=set(), loop=loop, scroll_rate=4.0)
    assert panel._loop is loop
    assert panel._scroll_rate == 4.0


def test_file_panel_starts_scroll_alarm_for_long_name():
    from simplegals.tui.file_panel import FilePanel
    loop = MockLoop()
    sources = [Path("a_very_long_filename_that_exceeds_panel_width.jpg")]
    panel = FilePanel(sources, dirty_filenames=set(), loop=loop, scroll_rate=4.0)
    panel._last_col = 10
    panel._start_scroll()
    assert len(loop.scheduled) == 1


def test_file_panel_no_scroll_alarm_for_short_name():
    from simplegals.tui.file_panel import FilePanel
    loop = MockLoop()
    sources = [Path("a.jpg")]
    panel = FilePanel(sources, dirty_filenames=set(), loop=loop, scroll_rate=4.0)
    panel._last_col = 40
    panel._start_scroll()
    assert len(loop.scheduled) == 0


def test_file_panel_no_scroll_without_loop():
    from simplegals.tui.file_panel import FilePanel
    sources = [Path("a_very_long_filename_that_exceeds_panel_width.jpg")]
    panel = FilePanel(sources, dirty_filenames=set())
    panel._last_col = 10
    panel._start_scroll()
    assert panel._scroll_alarm is None


def test_file_panel_tick_scroll_advances_text():
    from simplegals.tui.file_panel import FilePanel
    loop = MockLoop()
    long_name = "very_long_image_filename.jpg"
    sources = [Path(long_name)]
    panel = FilePanel(sources, dirty_filenames=set(), loop=loop, scroll_rate=4.0)
    panel._last_col = 10
    original_label = panel._rows[0].label
    panel._tick_scroll(loop, None)
    assert panel._rows[0].label != original_label
    assert panel._scroll_offset == 1


def test_file_panel_tick_scroll_wraps_offset():
    from simplegals.tui.file_panel import FilePanel
    loop = MockLoop()
    sources = [Path("ab.jpg")]
    panel = FilePanel(sources, dirty_filenames=set(), loop=loop, scroll_rate=4.0)
    panel._last_col = 5
    full_label = panel._rows[0]._make_label()
    panel._scroll_offset = len(full_label) - 1
    panel._tick_scroll(loop, None)
    assert panel._scroll_offset == 0


def test_file_panel_tick_scroll_reschedules_alarm():
    from simplegals.tui.file_panel import FilePanel
    loop = MockLoop()
    sources = [Path("long_name_file.jpg")]
    panel = FilePanel(sources, dirty_filenames=set(), loop=loop, scroll_rate=4.0)
    panel._last_col = 5
    panel._tick_scroll(loop, None)
    assert len(loop.scheduled) == 1


def test_file_panel_focus_change_cancels_previous_alarm():
    from simplegals.tui.file_panel import FilePanel
    loop = MockLoop()
    sources = [Path("long_name_a.jpg"), Path("long_name_b.jpg")]
    panel = FilePanel(sources, dirty_filenames=set(), loop=loop, scroll_rate=4.0)
    panel._last_col = 5
    panel._start_scroll()
    first_handle = loop.scheduled[0][0]
    panel._cancel_scroll()
    assert first_handle in loop.removed


def test_file_panel_focus_change_resets_scroll_offset():
    from simplegals.tui.file_panel import FilePanel
    loop = MockLoop()
    sources = [Path("long_name.jpg")]
    panel = FilePanel(sources, dirty_filenames=set(), loop=loop, scroll_rate=4.0)
    panel._last_col = 5
    panel._scroll_offset = 5
    panel._cancel_scroll()
    assert panel._scroll_offset == 0


def test_global_config_default_preview_delay_is_125ms():
    from simplegals.core.config import GlobalConfig
    assert GlobalConfig().preview_delay == 125
