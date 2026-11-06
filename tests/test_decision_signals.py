"""Q29: a change that looks like an undocumented decision, from diff shape alone."""

from adrcheck.domain.change import Change, FileChange, Line
from adrcheck.domain.decision_signals import decision_signals


def change(path, *added, old_path="same"):
    f = FileChange(path, path if old_path == "same" else old_path, added=tuple(Line(path, "+", i + 1, t) for i, t in enumerate(added)))
    return Change(ref="c1", parent="c0", message="m", files=(f,))


def test_a_new_top_level_directory_is_a_signal():
    [s] = decision_signals(change("newsvc/main.py", "x = 1", old_path=None), present_at_parent=lambda needle: False)
    assert s.kind == "new-top-level-module" and s.detail == "newsvc/"


def test_an_import_not_seen_anywhere_at_the_parent_is_a_signal():
    [s] = decision_signals(change("enrich/x.py", "import requests"), present_at_parent=lambda needle: needle != "requests")
    assert (s.kind, s.detail) == ("new-dependency", "requests")


def test_an_import_already_used_elsewhere_is_not():
    assert decision_signals(change("enrich/x.py", "import json"), present_at_parent=lambda needle: True) == ()


def test_a_new_external_host_is_a_signal():
    [s] = decision_signals(change("enrich/x.py", 'URL = "https://api.example.com/v1"'), present_at_parent=lambda needle: needle != "api.example.com")
    assert (s.kind, s.detail) == ("new-external-host", "api.example.com")


def test_a_host_in_a_markdown_or_text_file_is_not_a_signal():
    assert decision_signals(change("notes/APPLY-NOW.md", "- https://careers.example.com/job/1"), present_at_parent=lambda needle: False) == ()
