from pathlib import Path

import pytest

from fileorganizer.cli import main

RULES_TOML = """
fallback = "Unsorted"

[[rule]]
name = "Images"
extensions = [".jpg", ".png"]
destination = "Media/Images"
"""


@pytest.fixture
def workspace(tmp_path: Path, make_file) -> tuple[Path, Path]:
    folder = tmp_path / "Downloads"
    make_file(folder / "scan.jpg")
    make_file(folder / "notes.bin")
    config = tmp_path / "organizer.toml"
    config.write_text(RULES_TOML, encoding="utf-8")
    return folder, config


def test_dry_run_reports_moves_without_making_them(workspace, capsys):
    folder, config = workspace

    exit_code = main(["run", str(folder), "--config", str(config), "--dry-run"])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "would move" in out
    assert str(Path("Media/Images/scan.jpg")) in out
    assert "[Images]" in out
    assert (folder / "scan.jpg").exists()
    assert not (folder / ".file-organizer.log.jsonl").exists()


def test_run_then_undo_round_trip(workspace, capsys):
    folder, config = workspace

    assert main(["run", str(folder), "--config", str(config)]) == 0
    assert (folder / "Media" / "Images" / "scan.jpg").exists()
    assert (folder / "Unsorted" / "notes.bin").exists()

    log = folder / ".file-organizer.log.jsonl"
    assert main(["undo", str(log)]) == 0

    assert (folder / "scan.jpg").exists()
    assert (folder / "notes.bin").exists()
    assert "2 file(s) restored, 0 skipped." in capsys.readouterr().out


def test_a_missing_folder_is_reported(tmp_path, capsys):
    config = tmp_path / "organizer.toml"
    config.write_text(RULES_TOML, encoding="utf-8")

    assert main(["run", str(tmp_path / "nope"), "--config", str(config)]) == 2
    assert "not a folder" in capsys.readouterr().err


def test_an_invalid_configuration_exits_with_status_two(workspace, capsys):
    folder, config = workspace
    config.write_text('[[rule]]\nname = "broken"\nextensions = [".jpg"]\n', encoding="utf-8")

    assert main(["run", str(folder), "--config", str(config)]) == 2
    assert "configuration error" in capsys.readouterr().err
