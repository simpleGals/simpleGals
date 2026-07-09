from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core.config import init_project, load_project_config
from .core.gallery import build, clean, validate
from .workers.progress import ProgressState, format_cli_progress


def _resolve_config(args: argparse.Namespace) -> Path:
    return Path(args.config) if args.config else Path.cwd() / "simpleGal.json"


def cmd_init(args: argparse.Namespace) -> int:
    config_path = Path(args.config) if args.config else None
    result = init_project(Path.cwd(), config_path=config_path)
    print(f"Initialized: {result}")
    for sub in ("in", "out"):
        print(f"  created: {Path.cwd() / sub}/")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    config_path = _resolve_config(args)
    try:
        config = load_project_config(config_path)
    except FileNotFoundError:
        print(f"Config not found: {config_path}. Run 'simpleGals init' first.", file=sys.stderr)
        return 1
    errors = validate(Path.cwd(), config)
    if errors:
        for e in errors:
            print(f"  error: {e}", file=sys.stderr)
        return 1
    print("Validation passed.")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    config_path = _resolve_config(args)
    try:
        config = load_project_config(config_path)
    except FileNotFoundError:
        print(f"Config not found: {config_path}. Run 'simpleGals init' first.", file=sys.stderr)
        return 1

    _prev_lines = [0]

    def _on_progress(state: ProgressState) -> None:
        text = format_cli_progress(state)
        n = text.count("\n") + 1
        if _prev_lines[0]:
            sys.stderr.write(f"\x1b[{_prev_lines[0]}A\r\x1b[J")
        sys.stderr.write(text + "\n")
        sys.stderr.flush()
        _prev_lines[0] = n

    log_path, had_errors = build(Path.cwd(), config, progress_callback=_on_progress, force=args.force)

    if had_errors:
        print(f"\nBuild completed with errors. Log: {log_path}", file=sys.stderr)
        lines = log_path.read_text(encoding="utf-8").splitlines()
        tail = lines[-20:] if len(lines) > 20 else lines
        print("\n--- last 20 lines of build log ---", file=sys.stderr)
        print("\n".join(tail), file=sys.stderr)
        return 1

    print(f"Build complete. Log: {log_path}")
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    clean(Path.cwd())
    print("Cleaned .meta/")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="simpleGals",
        description="Static HTML image gallery generator",
    )
    parser.add_argument(
        "-c", "--config",
        metavar="PATH",
        help="Path to simpleGal.json (default: ./simpleGal.json)",
    )

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Create a stub simpleGal.json in the current directory")
    sub.add_parser("validate", help="Validate config and input images")
    build_parser = sub.add_parser("build", help="Build the gallery")
    build_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Rebuild all output files, ignoring the cache",
    )
    sub.add_parser("clean", help="Remove all cached metadata from .meta/")

    args = parser.parse_args()

    handlers = {
        "init": cmd_init,
        "validate": cmd_validate,
        "build": cmd_build,
        "clean": cmd_clean,
    }
    sys.exit(handlers[args.command](args))


if __name__ == "__main__":
    main()
