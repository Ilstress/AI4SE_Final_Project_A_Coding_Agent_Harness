"""Tool handlers for the AI4SE Coding Agent Harness.

Each handler implements a built-in tool action per SPEC §3.5.
"""

from harness.tools.handlers.execute_shell import execute_shell
from harness.tools.handlers.read_file import read_file
from harness.tools.handlers.task_complete import task_complete
from harness.tools.handlers.write_file import write_file

__all__ = [
    "execute_shell",
    "read_file",
    "task_complete",
    "write_file",
]
