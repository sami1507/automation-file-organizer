import re

import pytest

from fileorganizer.config import ConfigError, load_config, parse_config


def test_parses_rules_and_normalises_extensions():
    config = parse_config(
        {
            "fallback": "Unsorted",
            "ignore_suffixes": [".part"],
            "rule": [
                {"name": "Images", "extensions": ["JPG", ".png"], "destination": "Media/Images"},
                {"name": "Invoices", "pattern": "*invoice*", "destination": "Finance"},
            ],
        }
    )

    assert [rule.name for rule in config.rules] == ["Images", "Invoices"]
    assert config.rules[0].extensions == frozenset({".jpg", ".png"})
    assert config.rules[0].destination.as_posix() == "Media/Images"
    assert config.fallback is not None and config.fallback.as_posix() == "Unsorted"
    assert config.ignore_suffixes == frozenset({".part"})


def test_rules_without_a_name_get_a_numbered_name():
    config = parse_config({"rule": [{"extensions": [".txt"], "destination": "Docs"}]})

    assert config.rules[0].name == "rule #1"


@pytest.mark.parametrize(
    ("data", "message"),
    [
        pytest.param({"rule": []}, "at least one [[rule]]", id="no-rules"),
        pytest.param({}, "at least one [[rule]]", id="missing-rule-section"),
        pytest.param(
            {"rule": [{"name": "Docs", "extensions": [".txt"]}]},
            "missing 'destination'",
            id="no-destination",
        ),
        pytest.param(
            {"rule": [{"name": "Docs", "destination": "/etc", "extensions": [".txt"]}]},
            "must stay inside",
            id="absolute-destination",
        ),
        pytest.param(
            {"rule": [{"name": "Docs", "destination": "../elsewhere", "extensions": [".txt"]}]},
            "must stay inside",
            id="parent-traversal",
        ),
        pytest.param(
            {"rule": [{"name": "Docs", "destination": "Docs"}]},
            "add at least one",
            id="rule-without-criteria",
        ),
        pytest.param(
            {"rule": [{"name": "Old", "destination": "Old", "older_than_days": -1}]},
            "whole number of days",
            id="negative-age",
        ),
        pytest.param(
            {"rule": [{"name": "Odd", "destination": "Odd", "pattern": 3}]},
            "must be a string",
            id="pattern-not-a-string",
        ),
        pytest.param(
            {"rule": ["not-a-table"]},
            "must be a table",
            id="rule-not-a-table",
        ),
    ],
)
def test_invalid_configurations_are_rejected_with_a_clear_message(data, message):
    with pytest.raises(ConfigError, match=re.escape(message)):
        parse_config(data)


def test_load_config_reads_a_toml_file(tmp_path):
    path = tmp_path / "organizer.toml"
    path.write_text(
        '[[rule]]\nname = "Docs"\nextensions = [".pdf"]\ndestination = "Documents"\n',
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.rules[0].destination.as_posix() == "Documents"


def test_invalid_toml_is_reported_as_a_config_error(tmp_path):
    path = tmp_path / "broken.toml"
    path.write_text("[[rule\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="invalid TOML"):
        load_config(path)
