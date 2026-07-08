"""Tests for FileReadBoundRule — SPEC §3.4, PLAN T7.1."""

from pathlib import Path

from harness.guard.rules.file_read_bound import FileReadBoundRule
from harness.models.action import Action
from harness.models.rule_result import RuleVerdict


def _make_rule(workspace_root: str) -> FileReadBoundRule:
    return FileReadBoundRule(workspace_root)


def _make_action(path: str) -> Action:
    return Action(
        tool_name="read_file", parameters={"path": path}, raw_response={}
    )


class TestFileReadBoundRule:
    def test_read_inside_workspace_allows(self, tmp_path: Path) -> None:
        rule = _make_rule(str(tmp_path))
        action = _make_action("src/main.py")
        result = rule.evaluate(action)
        assert result.verdict == RuleVerdict.ALLOW

    def test_read_outside_workspace_blocks(self, tmp_path: Path) -> None:
        rule = _make_rule(str(tmp_path))
        outside = str(tmp_path.parent / "outside.txt")
        action = _make_action(outside)
        result = rule.evaluate(action)
        assert result.verdict == RuleVerdict.BLOCK

    def test_read_absolute_path_outside_blocks(self, tmp_path: Path) -> None:
        rule = _make_rule(str(tmp_path))
        action = _make_action("/etc/shadow")
        result = rule.evaluate(action)
        assert result.verdict == RuleVerdict.BLOCK

    def test_non_read_file_action_allows(self, tmp_path: Path) -> None:
        rule = _make_rule(str(tmp_path))
        action = Action(
            tool_name="write_file",
            parameters={"path": "/etc/passwd", "content": "x"},
            raw_response={},
        )
        result = rule.evaluate(action)
        assert result.verdict == RuleVerdict.ALLOW

    def test_priority_is_100(self, tmp_path: Path) -> None:
        rule = _make_rule(str(tmp_path))
        assert rule.priority == 100

    def test_rule_name(self, tmp_path: Path) -> None:
        rule = _make_rule(str(tmp_path))
        assert rule.rule_name == "FileReadBoundRule"

    def test_evidence_contains_path_info(self, tmp_path: Path) -> None:
        rule = _make_rule(str(tmp_path))
        action = _make_action("/etc/shadow")
        result = rule.evaluate(action)
        assert "path" in result.evidence
        assert result.evidence["path"] == "/etc/shadow"
