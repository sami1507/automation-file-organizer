"""Rule-based file organizer with dry runs, an audit log and undo."""

from fileorganizer.config import Config, ConfigError, Rule, load_config, parse_config
from fileorganizer.executor import apply_moves
from fileorganizer.planner import Move, plan_moves, unique_path
from fileorganizer.undo import UndoResult, undo_from_log

__version__ = "1.0.0"

__all__ = [
    "Config",
    "ConfigError",
    "Move",
    "Rule",
    "UndoResult",
    "__version__",
    "apply_moves",
    "load_config",
    "parse_config",
    "plan_moves",
    "undo_from_log",
    "unique_path",
]
