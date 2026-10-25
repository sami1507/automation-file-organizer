"""Decides where each file should go. Nothing is moved here; the planner only reads."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fileorganizer.config import Config

FALLBACK_RULE = "fallback"


@dataclass(frozen=True, slots=True)
class Move:
    source: Path
    destination: Path
    rule: str


def unique_path(candidate: Path, taken: Iterable[Path] = ()) -> Path:
    """Return `candidate`, or `name (1).ext`, `name (2).ext`, ... if the name is already used."""
    reserved = set(taken)
    if candidate not in reserved and not candidate.exists():
        return candidate

    counter = 1
    while True:
        alternative = candidate.with_name(f"{candidate.stem} ({counter}){candidate.suffix}")
        if alternative not in reserved and not alternative.exists():
            return alternative
        counter += 1


def plan_moves(root: Path, config: Config, *, now: datetime | None = None) -> list[Move]:
    """Plan moves for the regular files directly inside `root`.

    Hidden files, files with an ignored suffix (such as in-progress downloads),
    subfolders and files already in their target folder are left alone.
    """
    current_time = now or datetime.now(UTC)
    planned_targets: list[Path] = []
    moves: list[Move] = []

    for entry in sorted(root.iterdir()):
        if not entry.is_file() or entry.name.startswith("."):
            continue
        if entry.suffix.lower() in config.ignore_suffixes:
            continue

        modified = datetime.fromtimestamp(entry.stat().st_mtime, tz=UTC)
        rule = next(
            (r for r in config.rules if r.matches(entry.name, modified, current_time)), None
        )
        if rule is not None:
            target_folder, rule_name = root / rule.destination, rule.name
        elif config.fallback is not None:
            target_folder, rule_name = root / config.fallback, FALLBACK_RULE
        else:
            continue

        if target_folder == entry.parent:
            continue

        destination = unique_path(target_folder / entry.name, planned_targets)
        planned_targets.append(destination)
        moves.append(Move(source=entry, destination=destination, rule=rule_name))

    return moves
