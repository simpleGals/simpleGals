from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..core.config import GlobalConfig, init_project, load_global_config, load_project_config
from .app import SGUIApp


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sgui",
        description="simpleGals interactive TUI: browse and edit gallery settings",
    )
    parser.add_argument("-c", "--config", metavar="PATH", help="Path to simpleGal.json")
    args = parser.parse_args()

    project_dir = Path.cwd()
    config_path = Path(args.config) if args.config else project_dir / "simpleGal.json"

    global_config = load_global_config()

    if not config_path.exists():
        init_project(project_dir, config_path=config_path if args.config else None)

    try:
        config = load_project_config(config_path)
    except FileNotFoundError:
        print(f"Config not found: {config_path}. Run 'simpleGals init' first.", file=sys.stderr)
        sys.exit(1)

    app = SGUIApp(project_dir, config, global_config, config_path)
    app.run()


if __name__ == "__main__":
    main()
