"""Tests for ShellCWDBoundRule — SPEC §3.4, PLAN T7.1."""

from pathlib import Path

from harness.guard.rules.shell_cwd_bound import ShellCWDBoundRule
from harness.models.action import Action
from harness.models.rule_result import RuleVerdict


def _make_rule(workspace_root: str) -> ShellCWDBoundRule:
    return ShellCWDBoundRule(workspace_root)


def _make_action(command: str, cwd: str | None = None) -> Action:
    params: dict = {"command": command}
    if cwd is not None:
        params["cwd"] = cwd
    return Action(tool_name="execute_shell", parameters=params, raw_response={})


class TestShellCWDBoundRule:
    def test_no_cwd_allows(self, tmp_path: Path) -> None:
        rule = _make_rule(str(tmp_path))
        action = _make_action("echo hello")
        result = rule.evaluate(action)
        assert result.verdict == RuleVerdict.ALLOW

    def test_cwd_inside_workspace_allows(self, tmp_path: Path) -> None:
        rule = _make_rule(str(tmp_path))
        action = _make_action("echo hello", cwd="subdir")
        result = rule.evaluate(action)
        assert result.verdict == RuleVerdict.ALLOW

    def test_cwd_outside_workspace_blocks(self, tmp_path: Path) -> None:
        rule = _make_rule(str(tmp_path))
        outside = str(tmp_path.parent / "other")
        action = _make_action("echo hello", cwd=outside)
        result = rule.evaluate(action)
        assert result.verdict == RuleVerdict.BLOCK

    def test_cwd_absolute_outside_blocks(self, tmp_path: Path) -> None:
        rule = _make_rule(str(tmp_path))
        action = _make_action("echo hello", cwd="/etc")
        result = rule.evaluate(action)
        assert result.verdict == RuleVerdict.BLOCK

    def test_non_shell_action_allows(self, tmp_path: Path) -> None:
        rule = _make_rule(str(tmp_path))
        action = Action(
            tool_name="read_file", parameters={"path": "x"}, raw_response={}
        )
        result = rule.evaluate(action)
        assert result.verdict == RuleVerdict.ALLOW

    def test_priority_is_100(self, tmp_path: Path) -> None:
        rule = _make_rule(str(tmp_path))
        assert rule.priority == 100

    def test_rule_name(self, tmp_path: Path) -> None:
        rule = _make_rule(str(tmp_path))
        assert rule.rule_name == "ShellCWDBoundRule"
