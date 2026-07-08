"""Tests for DBDestructiveRule — SPEC §3.4, PLAN T7.1."""

from harness.guard.rules.db_destructive import DBDestructiveRule
from harness.models.action import Action
from harness.models.rule_result import RuleVerdict


def _make_rule(workspace_root: str = "/tmp/ws") -> DBDestructiveRule:
    return DBDestructiveRule(workspace_root)


def _make_action(command: str) -> Action:
    return Action(
        tool_name="execute_shell",
        parameters={"command": command},
        raw_response={},
    )


class TestDBDestructiveRule:
    def test_drop_table_flags(self) -> None:
        rule = _make_rule()
        result = rule.evaluate(_make_action("DROP TABLE users"))
        assert result.verdict == RuleVerdict.FLAG

    def test_drop_database_flags(self) -> None:
        rule = _make_rule()
        result = rule.evaluate(_make_action("DROP DATABASE production"))
        assert result.verdict == RuleVerdict.FLAG

    def test_delete_from_flags(self) -> None:
        rule = _make_rule()
        result = rule.evaluate(_make_action("DELETE FROM users WHERE id=1"))
        assert result.verdict == RuleVerdict.FLAG

    def test_truncate_flags(self) -> None:
        rule = _make_rule()
        result = rule.evaluate(_make_action("TRUNCATE TABLE logs"))
        assert result.verdict == RuleVerdict.FLAG

    def test_select_allows(self) -> None:
        rule = _make_rule()
        result = rule.evaluate(_make_action("SELECT * FROM users"))
        assert result.verdict == RuleVerdict.ALLOW

    def test_insert_allows(self) -> None:
        rule = _make_rule()
        result = rule.evaluate(
            _make_action("INSERT INTO users VALUES (1, 'alice')")
        )
        assert result.verdict == RuleVerdict.ALLOW

    def test_non_shell_action_allows(self) -> None:
        rule = _make_rule()
        action = Action(
            tool_name="write_file",
            parameters={"path": "x", "content": "DROP TABLE"},
            raw_response={},
        )
        result = rule.evaluate(action)
        assert result.verdict == RuleVerdict.ALLOW

    def test_priority_is_200(self) -> None:
        rule = _make_rule()
        assert rule.priority == 200

    def test_rule_name(self) -> None:
        rule = _make_rule()
        assert rule.rule_name == "DBDestructiveRule"

    def test_evidence_contains_command(self) -> None:
        rule = _make_rule()
        result = rule.evaluate(_make_action("DROP TABLE users"))
        assert result.evidence["command"] == "DROP TABLE users"
        assert "pattern" in result.evidence
