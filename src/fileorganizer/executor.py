"""Carries out a plan and records every move in a JSON Lines audit log."""

from __future__ import annotations

import json
import shutil
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from fileorganizer.planner import Move, unique_path


def apply_moves(
    moves: Sequence[Move], *, log_path: Path | None = None, dry_run: bool = False
) -> list[Move]:
    """Move files as planned and return the moves that were made.

    With ``dry_run`` nothing on disk changes and nothing is logged. Destination
    names are checked again just before each move, so a file created since
    planning is never overwritten.
    """
    if dry_run:
        return list(moves)

    applied: list[Move] = []
    for move in moves:
        move.destination.parent.mkdir(parents=True, exist_ok=True)
        destination = unique_path(move.destination)
        shutil.move(str(move.source), str(destination))
        record = Move(source=move.source, destination=destination, rule=move.rule)
        applied.append(record)
        if log_path is not None:
            _append_log(log_path, record)
    return applied


def _append_log(log_path: Path, move: Move) -> None:
    entry = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": str(move.source),
        "destination": str(move.destination),
        "rule": move.rule,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")
