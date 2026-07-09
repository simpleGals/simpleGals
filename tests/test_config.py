import json
from pathlib import Path
import pytest
from simplegals.core.config import (
    GlobalConfig,
    Layout,
    ProjectConfig,
    global_config_path,
    init_project,
    load_project_config,
    save_project_config,
    settings_hash,
)


def test_global_config_path_points_to_simplegals():
    path = global_config_path()
    assert path.name == "config.json"
    assert "simplegals" in str(path)


def test_settings_hash_ignores_captions_and_images():
    c1 = ProjectConfig(quality=90, copyright="© 2026", images={"a.jpg": {"caption": "foo"}})
    c2 = ProjectConfig(quality=90, copyright="© 2026", images={"a.jpg": {"caption": "bar"}})
    assert settings_hash(c1) == settings_hash(c2)


def test_settings_hash_changes_with_quality():
    assert settings_hash(ProjectConfig(quality=90)) != settings_hash(ProjectConfig(quality=85))


def test_settings_hash_changes_with_copyright():
    assert settings_hash(ProjectConfig(copyright="a")) != settings_hash(ProjectConfig(copyright="b"))


def test_settings_hash_changes_with_template():
    assert settings_hash(ProjectConfig(template=None)) != settings_hash(ProjectConfig(template="/x"))


def test_save_and_load_project_config_roundtrip(tmp_path):
    config_path = tmp_path / "simpleGal.json"
    config = ProjectConfig(
        title="My Gallery",
        quality=85,
        copyright="© 2026",
        images={"a.jpg": {"caption": "hello", "alt": "world", "include": True}},
    )
    save_project_config(config, config_path)
    loaded = load_project_config(config_path)
    assert loaded.title == "My Gallery"
    assert loaded.quality == 85
    assert loaded.images["a.jpg"]["caption"] == "hello"


def test_load_project_config_preserves_layout(tmp_path):
    config_path = tmp_path / "simpleGal.json"
    config = ProjectConfig(layout=Layout(columns=3, rows=6))
    save_project_config(config, config_path)
    loaded = load_project_config(config_path)
    assert loaded.layout.columns == 3
    assert loaded.layout.rows == 6


def test_init_project_creates_stub(tmp_path):
    config_path = init_project(tmp_path)
    assert config_path.exists()
    data = json.loads(config_path.read_text())
    assert "title" in data
    assert "quality" in data
    assert "images" in data
    assert data["simple_gals_promo"] is False


def test_init_project_creates_in_and_out_dirs(tmp_path):
    init_project(tmp_path)
    assert (tmp_path / "in").is_dir()
    assert (tmp_path / "out").is_dir()


def test_init_project_respects_custom_path(tmp_path):
    custom = tmp_path / "custom.json"
    result = init_project(tmp_path, config_path=custom)
    assert result == custom
    assert custom.exists()


def test_init_project_does_not_overwrite_existing(tmp_path):
    config_path = tmp_path / "simpleGal.json"
    config_path.write_text('{"title": "keep me"}')
    init_project(tmp_path)
    assert json.loads(config_path.read_text())["title"] == "keep me"


def test_load_project_config_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_project_config(tmp_path / "nope.json")


def test_new_boolean_defaults():
    c = ProjectConfig()
    assert c.social_previews is True
    assert c.exif_display is True
    assert c.gallery_zip is False


def test_new_booleans_roundtrip(tmp_path):
    p = tmp_path / "simpleGal.json"
    save_project_config(ProjectConfig(social_previews=False, exif_display=False, gallery_zip=True), p)
    loaded = load_project_config(p)
    assert loaded.social_previews is False
    assert loaded.exif_display is False
    assert loaded.gallery_zip is True


def test_settings_hash_tracks_social_previews():
    a = settings_hash(ProjectConfig(social_previews=True))
    b = settings_hash(ProjectConfig(social_previews=False))
    assert a != b


def test_settings_hash_ignores_display_only_toggles():
    # exif_display / gallery_zip do not change generated pixels
    base = settings_hash(ProjectConfig())
    assert settings_hash(ProjectConfig(exif_display=False)) == base
    assert settings_hash(ProjectConfig(gallery_zip=True)) == base
