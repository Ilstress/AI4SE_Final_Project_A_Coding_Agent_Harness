"""Tests for PathBoundaryRule — SPEC §3.4, PLAN T7.1."""

from pathlib import Path

from harness.guard.rules.path_boundary import PathBoundaryRule
from harness.models.action import Action
from harness.models.rule_result import RuleVerdict


def _make_rule(workspace_root: str) -> PathBoundaryRule:
    return PathBoundaryRule(workspace_root)


def _make_action(tool_name: str, path: str) -> Action:
    params: dict = {"path": path}
    if tool_name == "write_file":
        params["content"] = "test"
    return Action(tool_name=tool_name, parameters=params, raw_response={})


class TestPathBoundaryRule:
    def test_write_inside_workspace_allows(self, tmp_path: Path) -> None:
        rule = _make_rule(str(tmp_path))
        action = _make_action("write_file", "src/main.py")
        result = rule.evaluate(action)
        assert result.verdict == RuleVerdict.ALLOW
        assert result.rule_name == "PathBoundaryRule"

    def test_write_outside_workspace_blocks(self, tmp_path: Path) -> None:
        rule = _make_rule(str(tmp_path))
        outside = str(tmp_path.parent / "outside.txt")
        action = _make_action("write_file", outside)
        result = rule.evaluate(action)
        assert result.verdict == RuleVerdict.BLOCK
        assert "outside" in result.reason.lower()

    def test_write_absolute_path_outside_blocks(self, tmp_path: Path) -> None:
        rule = _make_rule(str(tmp_path))
        action = _make_action("write_file", "/etc/passwd")
        result = rule.evaluate(action)
        assert result.verdict == RuleVerdict.BLOCK

    def test_non_write_file_action_allows(self, tmp_path: Path) -> None:
        rule = _make_rule(str(tmp_path))
        action = _make_action("read_file", "/etc/passwd")
        result = rule.evaluate(action)
        assert result.verdict == RuleVerdict.ALLOW

    def test_priority_is_100(self, tmp_path: Path) -> None:
        rule = _make_rule(str(tmp_path))
        assert rule.priority == 100

    def test_rule_name(self, tmp_path: Path) -> None:
        rule = _make_rule(str(tmp_path))
        assert rule.rule_name == "PathBoundaryRule"

    def test_evidence_contains_path_info(self, tmp_path: Path) -> None:
        rule = _make_rule(str(tmp_path))
        action = _make_action("write_file", "/etc/passwd")
        result = rule.evaluate(action)
        assert "path" in result.evidence
        assert result.evidence["path"] == "/etc/passwd"
