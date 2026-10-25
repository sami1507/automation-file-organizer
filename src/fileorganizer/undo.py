"""Reverses moves recorded by `apply_moves`, newest first."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from fileorganizer.planner import Move


@dataclass(frozen=True, slots=True)
class UndoResult:
    restored: list[Move] = field(default_factory=list)
    skipped: list[tuple[Move, str]] = field(default_factory=list)


def undo_from_log(log_path: Path, *, dry_run: bool = False) -> UndoResult:
    """Move each logged file back to where it came from.

    A move is skipped, and reported, when the file is no longer at its logged
    destination or when something now occupies the original location. A log
    that was fully reversed is renamed with an ``.undone`` suffix so it is not
    applied twice.
    """
    entries = _read_log(log_path)
    result = UndoResult()

    for entry in reversed(entries):
        current = Move(
            source=Path(entry["destination"]),
            destination=Path(entry["source"]),
            rule=entry["rule"],
        )
        if not current.source.exists():
            result.skipped.append((current, "file is no longer at the logged destination"))
            continue
        if current.destination.exists():
            result.skipped.append((current, "original location is occupied"))
            continue

        if not dry_run:
            current.destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(current.source), str(current.destination))
        result.restored.append(current)

    if not dry_run and not result.skipped:
        log_path.rename(log_path.with_name(log_path.name + ".undone"))
    return result


def _read_log(log_path: Path) -> list[dict[str, str]]:
    with log_path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]
