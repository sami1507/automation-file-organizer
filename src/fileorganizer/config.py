"""Configuration loading and validation. Rules are read from a TOML file."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import Any


class ConfigError(ValueError):
    """Raised when a configuration file is missing a required value or contains a bad one."""


@dataclass(frozen=True, slots=True)
class Rule:
    """A file matches when every criterion it defines is satisfied (logical AND)."""

    name: str
    destination: PurePosixPath
    extensions: frozenset[str] = frozenset()
    pattern: str | None = None
    older_than_days: int | None = None

    def matches(self, filename: str, modified: datetime, now: datetime) -> bool:
        if self.extensions and PurePosixPath(filename).suffix.lower() not in self.extensions:
            return False
        if self.pattern is not None and not fnmatchcase(filename.lower(), self.pattern.lower()):
            return False
        if self.older_than_days is not None and now - modified < timedelta(
            days=self.older_than_days
        ):
            return False
        return True


@dataclass(frozen=True, slots=True)
class Config:
    rules: tuple[Rule, ...]
    fallback: PurePosixPath | None = None
    ignore_suffixes: frozenset[str] = field(default_factory=frozenset)


def load_config(path: Path) -> Config:
    with path.open("rb") as handle:
        try:
            data = tomllib.load(handle)
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"{path}: invalid TOML: {exc}") from exc
    return parse_config(data)


def parse_config(data: Mapping[str, Any]) -> Config:
    """Validate a parsed TOML document and build a Config. Errors name the offending rule."""
    raw_rules = data.get("rule", [])
    if not isinstance(raw_rules, list) or not raw_rules:
        raise ConfigError("the configuration needs at least one [[rule]] table")

    rules = tuple(_parse_rule(index, raw) for index, raw in enumerate(raw_rules, start=1))
    fallback = _parse_destination(data["fallback"], "fallback") if "fallback" in data else None
    ignore = frozenset(_normalise_extension(suffix) for suffix in data.get("ignore_suffixes", []))
    return Config(rules=rules, fallback=fallback, ignore_suffixes=ignore)


def _parse_rule(index: int, raw: Any) -> Rule:
    if not isinstance(raw, Mapping):
        raise ConfigError(f"rule #{index} must be a table")

    name = raw.get("name") or f"rule #{index}"
    if "destination" not in raw:
        raise ConfigError(f"{name}: missing 'destination'")
    destination = _parse_destination(raw["destination"], name)

    extensions = frozenset(_normalise_extension(ext) for ext in raw.get("extensions", []))
    pattern = raw.get("pattern")
    older_than_days = raw.get("older_than_days")

    if not (extensions or pattern is not None or older_than_days is not None):
        raise ConfigError(
            f"{name}: add at least one of 'extensions', 'pattern' or 'older_than_days'"
        )
    if pattern is not None and not isinstance(pattern, str):
        raise ConfigError(f"{name}: 'pattern' must be a string")
    if older_than_days is not None and (
        not isinstance(older_than_days, int) or older_than_days < 0
    ):
        raise ConfigError(f"{name}: 'older_than_days' must be a whole number of days, zero or more")

    return Rule(
        name=name,
        destination=destination,
        extensions=extensions,
        pattern=pattern,
        older_than_days=older_than_days,
    )


def _parse_destination(value: Any, owner: str) -> PurePosixPath:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{owner}: destination must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ConfigError(
            f"{owner}: destination '{value}' must stay inside the folder being organised"
        )
    return path


def _normalise_extension(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ConfigError(f"extensions must be non-empty strings, got {value!r}")
    return value.lower() if value.startswith(".") else f".{value.lower()}"
