import json

from fileorganizer.executor import apply_moves
from fileorganizer.planner import Move
from fileorganizer.undo import undo_from_log


def test_apply_moves_moves_files_and_writes_an_audit_entry(tmp_path, make_file):
    source = make_file(tmp_path / "a.txt")
    destination = tmp_path / "Docs" / "a.txt"
    log = tmp_path / "audit.jsonl"

    applied = apply_moves([Move(source, destination, "Docs")], log_path=log)

    assert not source.exists()
    assert destination.read_bytes() == b"x"
    assert applied == [Move(source, destination, "Docs")]
    entry = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert entry["source"] == str(source)
    assert entry["destination"] == str(destination)
    assert entry["rule"] == "Docs"


def test_dry_run_changes_nothing_on_disk(tmp_path, make_file):
    source = make_file(tmp_path / "a.txt")
    destination = tmp_path / "Docs" / "a.txt"
    log = tmp_path / "audit.jsonl"

    applied = apply_moves([Move(source, destination, "Docs")], log_path=log, dry_run=True)

    assert source.exists()
    assert not destination.exists()
    assert not log.exists()
    assert applied == [Move(source, destination, "Docs")]


def test_destination_is_rechecked_at_move_time(tmp_path, make_file):
    source = make_file(tmp_path / "a.txt")
    planned = tmp_path / "Docs" / "a.txt"
    existing = make_file(planned)  # created after planning, before the move
    existing.write_bytes(b"someone else's file")

    applied = apply_moves([Move(source, planned, "Docs")])

    assert planned.read_bytes() == b"someone else's file"
    assert applied[0].destination == tmp_path / "Docs" / "a (1).txt"


def test_undo_restores_files_and_retires_the_log(tmp_path, make_file):
    source = make_file(tmp_path / "a.txt")
    destination = tmp_path / "Docs" / "a.txt"
    log = tmp_path / "audit.jsonl"
    apply_moves([Move(source, destination, "Docs")], log_path=log)

    result = undo_from_log(log)

    assert source.read_bytes() == b"x"
    assert not destination.exists()
    assert [move.destination for move in result.restored] == [source]
    assert result.skipped == []
    assert not log.exists()
    assert (tmp_path / "audit.jsonl.undone").exists()


def test_undo_skips_a_move_when_the_original_spot_is_taken(tmp_path, make_file):
    source = make_file(tmp_path / "a.txt")
    destination = tmp_path / "Docs" / "a.txt"
    log = tmp_path / "audit.jsonl"
    apply_moves([Move(source, destination, "Docs")], log_path=log)
    make_file(source).write_bytes(b"new file")

    result = undo_from_log(log)

    assert destination.exists()
    assert source.read_bytes() == b"new file"
    assert result.restored == []
    assert result.skipped[0][1] == "original location is occupied"
    assert log.exists(), "a partially undone log must stay so it can be retried"


def test_undo_skips_files_that_have_since_been_removed(tmp_path, make_file):
    source = make_file(tmp_path / "a.txt")
    destination = tmp_path / "Docs" / "a.txt"
    log = tmp_path / "audit.jsonl"
    apply_moves([Move(source, destination, "Docs")], log_path=log)
    destination.unlink()

    result = undo_from_log(log)

    assert result.restored == []
    assert result.skipped[0][1] == "file is no longer at the logged destination"


def test_undo_dry_run_leaves_everything_in_place(tmp_path, make_file):
    source = make_file(tmp_path / "a.txt")
    destination = tmp_path / "Docs" / "a.txt"
    log = tmp_path / "audit.jsonl"
    apply_moves([Move(source, destination, "Docs")], log_path=log)

    result = undo_from_log(log, dry_run=True)

    assert destination.exists()
    assert log.exists()
    assert len(result.restored) == 1
