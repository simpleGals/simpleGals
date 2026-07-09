# tests/test_tui_state.py
import json
from pathlib import Path
import pytest
from simplegals.core.config import Layout, ProjectConfig
from simplegals.tui.state import StagedChangesModel, StagedValue


def test_staged_value_dirty_when_changed():
    v = StagedValue(original="foo", new="bar")
    assert v.dirty


def test_staged_value_not_dirty_when_same():
    v = StagedValue(original="foo", new="foo")
    assert not v.dirty


def test_stage_makes_key_dirty():
    m = StagedChangesModel()
    m.stage("img.jpg", "caption", "original", "new caption")
    assert m.is_dirty("img.jpg")


def test_stage_same_value_not_dirty():
    m = StagedChangesModel()
    m.stage("img.jpg", "caption", "same", "same")
    assert not m.is_dirty("img.jpg")


def test_revert_clears_key():
    m = StagedChangesModel()
    m.stage("img.jpg", "caption", "a", "b")
    m.revert("img.jpg")
    assert not m.is_dirty("img.jpg")


def test_revert_unknown_key_is_safe():
    m = StagedChangesModel()
    m.revert("ghost.jpg")  # should not raise


def test_has_any_dirty_false_when_empty():
    m = StagedChangesModel()
    assert not m.has_any_dirty()


def test_has_any_dirty_true_when_staged():
    m = StagedChangesModel()
    m.stage("img.jpg", "caption", "a", "b")
    assert m.has_any_dirty()


def test_get_current_returns_staged_value():
    m = StagedChangesModel()
    m.stage("img.jpg", "caption", "old", "new")
    assert m.get_current("img.jpg", "caption") == "new"


def test_get_current_returns_default_when_not_staged():
    m = StagedChangesModel()
    assert m.get_current("img.jpg", "caption", "fallback") == "fallback"


def test_dirty_keys_returns_only_changed_keys():
    m = StagedChangesModel()
    m.stage("a.jpg", "caption", "x", "y")   # dirty
    m.stage("b.jpg", "caption", "z", "z")   # same value, not dirty
    assert m.dirty_keys() == ["a.jpg"]


def test_commit_key_applies_image_field(tmp_path):
    config_path = tmp_path / "simpleGal.json"
    config = ProjectConfig(images={"img.jpg": {"caption": "old", "include": True}})
    m = StagedChangesModel()
    m.stage("img.jpg", "caption", "old", "new caption")
    config = m.commit_key("img.jpg", config, config_path)
    assert config.images["img.jpg"]["caption"] == "new caption"
    assert config_path.exists()
    assert not m.is_dirty("img.jpg")


def test_commit_key_applies_gallery_title(tmp_path):
    config_path = tmp_path / "simpleGal.json"
    config = ProjectConfig(title="Old")
    m = StagedChangesModel()
    m.stage("gallery", "title", "Old", "New")
    config = m.commit_key("gallery", config, config_path)
    assert config.title == "New"
    assert not m.is_dirty("gallery")


def test_commit_key_applies_layout_columns(tmp_path):
    config_path = tmp_path / "simpleGal.json"
    config = ProjectConfig(layout=Layout(columns=4, rows=5))
    m = StagedChangesModel()
    m.stage("gallery", "layout_columns", 4, 6)
    config = m.commit_key("gallery", config, config_path)
    assert config.layout.columns == 6
    assert config.layout.rows == 5  # unchanged


def test_commit_all_clears_all_staged(tmp_path):
    config_path = tmp_path / "simpleGal.json"
    config = ProjectConfig(title="t", images={"a.jpg": {"caption": "c"}})
    m = StagedChangesModel()
    m.stage("gallery", "title", "t", "new title")
    m.stage("a.jpg", "caption", "c", "new caption")
    config = m.commit_all(config, config_path)
    assert not m.has_any_dirty()
    assert config.title == "new title"
    assert config.images["a.jpg"]["caption"] == "new caption"
