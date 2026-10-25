"""Command-line interface.

file-organizer run ~/Downloads --config organizer.toml --dry-run
file-organizer run ~/Downloads --config organizer.toml
file-organizer undo ~/Downloads/.file-organizer.log.jsonl
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from fileorganizer.config import ConfigError, load_config
from fileorganizer.executor import apply_moves
from fileorganizer.planner import Move, plan_moves
from fileorganizer.undo import undo_from_log

LOG_NAME = ".file-organizer.log.jsonl"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="file-organizer",
        description="Sort files in a folder by rules, with dry runs, an audit log and undo.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="sort the files in a folder")
    run.add_argument("folder", type=Path, help="folder to organise (top level only)")
    run.add_argument("--config", type=Path, required=True, help="TOML file with the rules")
    run.add_argument("--dry-run", action="store_true", help="show what would move, change nothing")
    run.add_argument("--log", type=Path, help=f"audit log (default: <folder>/{LOG_NAME})")

    undo = commands.add_parser("undo", help="reverse the moves recorded in a log")
    undo.add_argument("log", type=Path, help="audit log written by a previous run")
    undo.add_argument("--dry-run", action="store_true", help="show what would be restored")
    return parser


def _describe(move: Move, root: Path) -> str:
    source = move.source.relative_to(root)
    destination = move.destination.relative_to(root)
    return f"{source}  ->  {destination}  [{move.rule}]"


def _run(args: argparse.Namespace) -> int:
    folder: Path = args.folder
    if not folder.is_dir():
        print(f"file-organizer: not a folder: {folder}", file=sys.stderr)
        return 2

    config = load_config(args.config)
    moves = plan_moves(folder, config, now=datetime.now(UTC))
    log_path = None if args.dry_run else (args.log or folder / LOG_NAME)
    applied = apply_moves(moves, log_path=log_path, dry_run=args.dry_run)

    verb = "would move" if args.dry_run else "moved"
    for move in applied:
        print(f"{verb:>12}  {_describe(move, folder)}")
    summary_verb = "would be moved" if args.dry_run else "moved"
    print(f"\n{len(applied)} file(s) {summary_verb}.")
    if log_path is not None and applied:
        print(f"Audit log: {log_path}")
    return 0


def _undo(args: argparse.Namespace) -> int:
    result = undo_from_log(args.log, dry_run=args.dry_run)

    verb = "would restore" if args.dry_run else "restored"
    for move in result.restored:
        print(f"{verb:>14}  {move.source}  ->  {move.destination}")
    for move, reason in result.skipped:
        print(f"{'skipped':>14}  {move.source}: {reason}")
    print(f"\n{len(result.restored)} file(s) {verb}, {len(result.skipped)} skipped.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "run":
            return _run(args)
        return _undo(args)
    except ConfigError as exc:
        print(f"file-organizer: configuration error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"file-organizer: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
