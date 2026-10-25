# automation-file-organizer

[![CI](https://github.com/sami1507/automation-file-organizer/actions/workflows/ci.yml/badge.svg)](https://github.com/sami1507/automation-file-organizer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Dependencies](https://img.shields.io/badge/runtime%20dependencies-0-brightgreen)

A rule-based file organizer for busy folders such as Downloads, shared drives or export folders. Rules are written in TOML. Every run can be previewed with `--dry-run`, every move is recorded in an audit log, and a single command undoes the last run.

It is built for unattended use. It never overwrites a file, it skips in-progress downloads, and it stops a bad rule from doing damage by checking every destination before it moves anything.

## Quick start

```bash
python -m pip install -e ".[dev]"

file-organizer run ~/Downloads --config examples/organizer.toml --dry-run   # preview
file-organizer run ~/Downloads --config examples/organizer.toml             # apply
file-organizer undo ~/Downloads/.file-organizer.log.jsonl                  # reverse the last run
```

## Writing rules

Rules are checked from top to bottom, and the first match wins. A rule matches when **all** of its criteria hold.

```toml
fallback = "Unsorted"                         # where unmatched files go (optional)
ignore_suffixes = [".crdownload", ".part"]    # partial downloads are never touched

[[rule]]
name = "Invoices"
pattern = "*invoice*"                         # shell-style wildcard, case-insensitive
destination = "Finance/Invoices"

[[rule]]
name = "Old installers"
extensions = [".exe", ".msi"]
older_than_days = 30                          # file must be at least this old
destination = "Archive/Installers"
```

| Criterion        | Meaning                                                    |
| ---------------- | ---------------------------------------------------------- |
| `extensions`     | Any of the listed suffixes, case-insensitive               |
| `pattern`        | A shell-style filename pattern such as `*invoice*`         |
| `older_than_days`| Only files whose modification time is at least N days old  |
| `destination`    | Relative folder inside the organised folder. `..` and absolute paths are rejected |

The full example for a Downloads folder is in [`examples/organizer.toml`](examples/organizer.toml).

## What a run looks like

Dry run against a sample folder:

```text
  would move  acme-invoice-oct.pdf  ->  Finance\Invoices\acme-invoice-oct.pdf  [Invoices]
  would move  archive.zip  ->  Archive\Compressed\archive.zip  [Archives]
  would move  Q3 report.docx  ->  Documents\Q3 report.docx  [Documents]
  would move  random.bin  ->  Unsorted\random.bin  [fallback]
  would move  setup-tool.exe  ->  Archive\Installers\setup-tool.exe  [Old installers]
  would move  vacation.jpg  ->  Media\Images\vacation.jpg  [Images]

6 file(s) would be moved.
```

`video.crdownload` is not in the list because `.crdownload` is an ignored suffix, so a browser that is still downloading it is left alone.

Running `undo` on the same folder prints each file being restored to its original location, and the log is retired so it cannot be applied twice.

## Safety rules

- **No overwrites.** If a name is taken, the file is saved as `report (1).pdf`, `report (2).pdf`, and so on. The destination is checked again just before each move, so a file created after planning is never replaced.
- **Top level only.** Subfolders, hidden files (names starting with `.`) and ignored suffixes are not touched.
- **Dry runs change nothing.** Nothing is moved and no log is written.
- **Every move is logged.** Each run appends one JSON line per move to `.file-organizer.log.jsonl` in the folder: timestamp, source, destination and the rule that matched.
- **Undo is conservative.** A move is skipped and reported when the file has been moved again or when something now sits at the original location. A partially undone log is kept so you can retry.
- **Configuration is validated up front.** Missing destinations, absolute paths, traversal (`..`), rules with no criteria and bad values are reported before any file is touched.

## Scheduling

Run it on a schedule with the platform's own tools, for example Windows Task Scheduler:

```powershell
schtasks /Create /SC HOURLY /TN "Organise Downloads" `
  /TR "file-organizer run C:\Users\me\Downloads --config C:\Users\me\organizer.toml"
```

or cron on Linux and macOS:

```cron
0 * * * * file-organizer run "$HOME/Downloads" --config "$HOME/organizer.toml"
```

## Development

```bash
python -m pip install -e ".[dev]"
pytest          # 34 tests: config validation, rule logic, planning, moves, undo, CLI
ruff check .
```

Project layout:

```text
src/fileorganizer/
  config.py     TOML loading and validation, the Rule model
  planner.py    Matches files to rules and plans collision-free destinations
  executor.py   Performs moves and writes the audit log
  undo.py       Reverses a logged run
  cli.py        `run` and `undo` commands
examples/organizer.toml   A realistic starting configuration
tests/                    Pure-logic tests use fixed clocks and temporary folders
```

## Roadmap

- Recursive mode with a depth limit
- Rules that match on file size or image dimensions
- A `status` command that reports the last run and any skipped undo items

## License

MIT. See [LICENSE](LICENSE).
