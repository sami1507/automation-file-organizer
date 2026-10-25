from datetime import timedelta
from pathlib import PurePosixPath

from fileorganizer.config import Rule, parse_config
from fileorganizer.planner import plan_moves, unique_path


def rule(**criteria) -> Rule:
    return Rule(name="test", destination=PurePosixPath("out"), **criteria)


def test_extension_matching_ignores_case(now):
    images = rule(extensions=frozenset({".jpg"}))

    assert images.matches("HOLIDAY.JPG", now, now)
    assert not images.matches("notes.txt", now, now)


def test_pattern_matching_uses_shell_style_wildcards(now):
    invoices = rule(pattern="*invoice*")

    assert invoices.matches("ACME-Invoice-2026.pdf", now, now)
    assert not invoices.matches("receipt.pdf", now, now)


def test_age_criterion_compares_against_the_clock(now):
    old_installers = rule(older_than_days=30)

    assert old_installers.matches("setup.exe", now - timedelta(days=45), now)
    assert not old_installers.matches("setup.exe", now - timedelta(days=3), now)


def test_every_criterion_must_hold(now):
    pdf_invoices = rule(extensions=frozenset({".pdf"}), pattern="*invoice*")

    assert pdf_invoices.matches("invoice.pdf", now, now)
    assert not pdf_invoices.matches("invoice.txt", now, now)
    assert not pdf_invoices.matches("receipt.pdf", now, now)


def test_plans_each_file_under_its_first_matching_rule(tmp_path, config, make_file, now):
    make_file(tmp_path / "vacation.jpg")
    make_file(tmp_path / "acme-invoice.jpg")
    make_file(tmp_path / "setup.exe", age_days=60)
    make_file(tmp_path / "mystery.bin")

    by_name = {move.source.name: move for move in plan_moves(tmp_path, config, now=now)}

    assert by_name["vacation.jpg"].destination == tmp_path / "Media" / "Images" / "vacation.jpg"
    assert by_name["acme-invoice.jpg"].rule == "Invoices"
    assert by_name["setup.exe"].rule == "Old installers"
    assert by_name["mystery.bin"].rule == "fallback"
    assert by_name["mystery.bin"].destination == tmp_path / "Unsorted" / "mystery.bin"


def test_hidden_ignored_and_nested_files_are_left_alone(tmp_path, config, make_file, now):
    make_file(tmp_path / ".hidden.jpg")
    make_file(tmp_path / "video.crdownload")
    make_file(tmp_path / "Media" / "Images" / "already-filed.jpg")
    (tmp_path / "subfolder").mkdir()

    assert plan_moves(tmp_path, config, now=now) == []


def test_files_already_in_their_target_folder_are_not_moved(tmp_path, make_file, now):
    config = parse_config({"rule": [{"name": "Docs", "extensions": [".txt"], "destination": "."}]})
    make_file(tmp_path / "notes.txt")

    assert plan_moves(tmp_path, config, now=now) == []


def test_without_a_fallback_unmatched_files_stay_put(tmp_path, make_file, now):
    config = parse_config(
        {"rule": [{"name": "Images", "extensions": [".jpg"], "destination": "Pics"}]}
    )
    make_file(tmp_path / "mystery.bin")

    assert plan_moves(tmp_path, config, now=now) == []


def test_existing_files_are_never_overwritten(tmp_path, config, make_file, now):
    make_file(tmp_path / "Finance" / "Invoices" / "acme-invoice.pdf")
    make_file(tmp_path / "acme-invoice.pdf")

    moves = plan_moves(tmp_path, config, now=now)

    assert moves[0].destination == tmp_path / "Finance" / "Invoices" / "acme-invoice (1).pdf"


def test_unique_path_counts_up_past_taken_names(tmp_path):
    taken = tmp_path / "report.pdf"
    taken.write_bytes(b"x")
    (tmp_path / "report (1).pdf").write_bytes(b"x")

    assert unique_path(taken) == tmp_path / "report (2).pdf"
