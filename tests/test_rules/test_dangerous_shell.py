"""Tests for DangerousShellRule — SPEC §3.4, PLAN T7.1."""

from harness.guard.rules.dangerous_shell import DangerousShellRule
from harness.models.action import Action
from harness.models.rule_result import RuleVerdict


def _make_rule(workspace_root: str = "/tmp/ws") -> DangerousShellRule:
    return DangerousShellRule(workspace_root)


def _make_action(command: str) -> Action:
    return Action(
        tool_name="execute_shell",
        parameters={"command": command},
        raw_response={},
    )


class TestDangerousShellRule:
    def test_rm_rf_root_flags(self) -> None:
        rule = _make_rule()
        result = rule.evaluate(_make_action("rm -rf /"))
        assert result.verdict == RuleVerdict.FLAG

    def test_rm_rf_root_var_flags(self) -> None:
        rule = _make_rule()
        result = rule.evaluate(_make_action("rm -rf / --no-preserve-root"))
        assert result.verdict == RuleVerdict.FLAG

    def test_rm_rf_relative_path_flags(self) -> None:
        """Per SPEC US-5: rm -rf ./build/ should trigger approval."""
        rule = _make_rule()
        result = rule.evaluate(_make_action("rm -rf ./build/"))
        assert result.verdict == RuleVerdict.FLAG

    def test_rm_rf_tmp_path_flags(self) -> None:
        rule = _make_rule()
        result = rule.evaluate(_make_action("rm -rf /tmp/foo"))
        assert result.verdict == RuleVerdict.FLAG

    def test_rm_rf_home_subdir_flags(self) -> None:
        rule = _make_rule()
        result = rule.evaluate(_make_action("rm -rf ~/foo"))
        assert result.verdict == RuleVerdict.FLAG

    def test_fork_bomb_flags(self) -> None:
        rule = _make_rule()
        result = rule.evaluate(_make_action(":(){ :|:& };:"))
        assert result.verdict == RuleVerdict.FLAG

    def test_chmod_777_root_flags(self) -> None:
        rule = _make_rule()
        result = rule.evaluate(_make_action("chmod 777 /etc/shadow"))
        assert result.verdict == RuleVerdict.FLAG

    def test_chmod_777_relative_allows(self) -> None:
        """chmod 777 on a relative path is a workspace operation, not flagged."""
        rule = _make_rule()
        result = rule.evaluate(_make_action("chmod 777 ./script.sh"))
        assert result.verdict == RuleVerdict.ALLOW

    def test_safe_command_allows(self) -> None:
        rule = _make_rule()
        result = rule.evaluate(_make_action("echo hello world"))
        assert result.verdict == RuleVerdict.ALLOW

    def test_normal_rm_without_rf_allows(self) -> None:
        rule = _make_rule()
        result = rule.evaluate(_make_action("rm ./build/output.o"))
        assert result.verdict == RuleVerdict.ALLOW

    def test_non_shell_action_allows(self) -> None:
        rule = _make_rule()
        action = Action(
            tool_name="read_file", parameters={"path": "x"}, raw_response={}
        )
        result = rule.evaluate(action)
        assert result.verdict == RuleVerdict.ALLOW

    def test_priority_is_200(self) -> None:
        rule = _make_rule()
        assert rule.priority == 200

    def test_rule_name(self) -> None:
        rule = _make_rule()
        assert rule.rule_name == "DangerousShellRule"

    def test_evidence_contains_command(self) -> None:
        rule = _make_rule()
        result = rule.evaluate(_make_action("rm -rf /"))
        assert result.evidence["command"] == "rm -rf /"
        assert "pattern" in result.evidence
