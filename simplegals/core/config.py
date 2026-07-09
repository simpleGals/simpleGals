from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class GlobalConfig:
    file_panel_width: int | str = 30
    scroll_rate: float = 2.0
    preview_delay: int = 125


@dataclass
class Layout:
    columns: int = 4
    rows: int = 5


@dataclass
class ProjectConfig:
    title: str = "Gallery"
    description: str = ""
    layout: Layout = field(default_factory=Layout)
    quality: int = 90
    copyright: str = ""
    site_url: str = ""
    author: str = ""
    social_previews: bool = True
    exif_display: bool = True
    gallery_zip: bool = False
    simple_gals_promo: bool = False
    template: str | None = None
    images: dict = field(default_factory=dict)


def global_config_path() -> Path:
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "simplegals" / "config.json"
    if system == "Windows":
        import os
        appdata = os.environ.get("APPDATA", str(Path.home()))
        return Path(appdata) / "simplegals" / "config.json"
    import os
    xdg = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(xdg) / "simplegals" / "config.json"


def load_global_config(path: Path | None = None) -> GlobalConfig:
    p = path or global_config_path()
    if not p.exists():
        return GlobalConfig()
    data = json.loads(p.read_text(encoding="utf-8"))
    return GlobalConfig(**{k: v for k, v in data.items() if k in GlobalConfig.__dataclass_fields__})


def save_global_config(config: GlobalConfig, path: Path | None = None) -> None:
    p = path or global_config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")


def load_project_config(path: Path) -> ProjectConfig:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    layout_data = data.pop("layout", {})
    layout = Layout(**{k: v for k, v in layout_data.items() if k in Layout.__dataclass_fields__})
    fields = {k: v for k, v in data.items() if k in ProjectConfig.__dataclass_fields__}
    fields["layout"] = layout
    return ProjectConfig(**fields)


def save_project_config(config: ProjectConfig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")


def init_project(project_dir: Path, config_path: Path | None = None) -> Path:
    target = config_path or (project_dir / "simpleGal.json")
    if not target.exists():
        save_project_config(ProjectConfig(), target)
    for sub in ("in", "out"):
        (project_dir / sub).mkdir(parents=True, exist_ok=True)
    return target


def settings_hash(config: ProjectConfig) -> str:
    data = json.dumps(
        {
            "copyright": config.copyright,
            "quality": config.quality,
            "template": config.template,
            "social_previews": config.social_previews,
        },
        sort_keys=True,
    )
    return hashlib.sha256(data.encode()).hexdigest()[:16]
