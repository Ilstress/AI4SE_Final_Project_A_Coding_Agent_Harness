"""CLI Entry Point — SPEC §7.1.2, §8.5, PLAN T11.1."""

from __future__ import annotations

import argparse
import asyncio
import sys

from harness.config.config_manager import load_config
from harness.credentials.credential_manager import CredentialManager
from harness.feedback.controllers.governance import GovernanceController
from harness.feedback.controllers.recovery import RecoveryController
from harness.feedback.coordination import CoordinationLayer
from harness.feedback.pipeline import FeedbackPipeline
from harness.guard.approval.terminal import TerminalApprovalProvider
from harness.guard.guardrail import Guardrail
from harness.guard.rule_engine import RuleEngine
from harness.guard.rules.dangerous_shell import DangerousShellRule
from harness.guard.rules.db_destructive import DBDestructiveRule
from harness.guard.rules.file_read_bound import FileReadBoundRule
from harness.guard.rules.network_exfil import NetworkExfilRule
from harness.guard.rules.path_boundary import PathBoundaryRule
from harness.guard.rules.shell_cwd_bound import ShellCWDBoundRule
from harness.llm.deepseek_adapter import DeepSeekAdapter
from harness.loop.main_loop import LoopState, MainLoop
from harness.tools.executor import ToolExecutor
from harness.tools.registry import ToolRegistry


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments and return the populated namespace."""
    parser = argparse.ArgumentParser(
        prog="ai4se-harness",
        description="AI4SE Coding Agent Harness — delegate coding tasks to an LLM-powered agent.",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Configure API credentials for an LLM provider.",
    )
    parser.add_argument(
        "--clear-credentials",
        action="store_true",
        help="Remove stored API credentials.",
    )

    subparsers = parser.add_subparsers(dest="command")
    run_parser = subparsers.add_parser("run", help="Execute a coding task.")
    run_parser.add_argument(
        "--task",
        required=True,
        help="Natural-language task description.",
    )
    run_parser.add_argument(
        "--config",
        default="./config.toml",
        help="Path to config.toml (default: ./config.toml).",
    )

    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """CLI entry point.  Parses arguments and dispatches to the appropriate
    handler.

    Exit codes:
        0 — COMPLETED
        1 — FAILED
        2 — CANCELLED
    """
    args = parse_args(argv)

    if args.setup:
        _handle_setup()
        sys.exit(0)
    elif args.clear_credentials:
        _handle_clear_credentials()
        sys.exit(0)
    elif args.command == "run":
        exit_code = asyncio.run(_handle_run(args))
        sys.exit(exit_code)
    else:
        # No recognised command or flag — print help and exit.
        parse_args(["--help"])
        sys.exit(0)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def _handle_setup() -> None:
    """Prompt the user for an API Key and store it securely."""
    cm = CredentialManager()
    cm.prompt_and_store("deepseek")


def _handle_clear_credentials() -> None:
    """Remove all stored API credentials."""
    cm = CredentialManager()
    cm.clear("deepseek")


def _build_default_rules(workspace_root: str) -> list:
    """Create the default set of guard rules (SPEC §3.4)."""
    return [
        PathBoundaryRule(workspace_root),
        ShellCWDBoundRule(workspace_root),
        FileReadBoundRule(workspace_root),
        DangerousShellRule(workspace_root),
        DBDestructiveRule(workspace_root),
        NetworkExfilRule(workspace_root),
    ]


async def _handle_run(args: argparse.Namespace) -> int:
    """Load config, wire dependencies, run the Main Loop, and return an exit code."""
    # 1. Load configuration
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        print(f"Error: config file not found at '{args.config}'", file=sys.stderr)
        return 1

    # 2. Credential manager
    cred_manager = CredentialManager()

    # 3. LLM adapter
    provider = config.llm.provider
    api_key = cred_manager.retrieve(provider)
    if api_key is None:
        print(f"Error: no API key found for provider '{provider}'. Run --setup first.", file=sys.stderr)
        return 1

    if provider == "deepseek":
        llm = DeepSeekAdapter(api_key=api_key, model=config.llm.model)
    else:
        print(f"Error: unsupported LLM provider '{provider}'", file=sys.stderr)
        return 1

    # 4. Tools
    registry = ToolRegistry()
    executor = ToolExecutor(workspace_root=config.workspace.root, registry=registry)

    # 5. Guardrail
    rules = _build_default_rules(config.workspace.root)
    rule_engine = RuleEngine(rules)
    approval = TerminalApprovalProvider()
    guardrail = Guardrail(rule_engine, approval)

    # 6. Feedback Pipeline
    recovery = RecoveryController()
    governance = GovernanceController()
    coordination = CoordinationLayer()
    pipeline = FeedbackPipeline(recovery, governance, coordination)

    # 7. Main Loop
    loop = MainLoop(
        config=config,
        llm=llm,
        guardrail=guardrail,
        tool_executor=executor,
        tool_registry=registry,
        feedback_pipeline=pipeline,
    )

    state = await loop.run(args.task)

    if state == LoopState.COMPLETED:
        return 0
    elif state == LoopState.FAILED:
        return 1
    elif state == LoopState.CANCELLED:
        return 2
    return 1
