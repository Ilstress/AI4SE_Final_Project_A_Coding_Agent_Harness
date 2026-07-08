"""SPEC §3.3.1: Built-in tool definitions with JSON Schema parameters."""

from harness.models.tool_definition import ToolDefinition

_BUILTIN_TOOLS: dict[str, ToolDefinition] = {
    "read_file": ToolDefinition(
        name="read_file",
        description="Read the contents of a file at the given path.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read, relative to the workspace root.",
                }
            },
            "required": ["path"],
        },
    ),
    "write_file": ToolDefinition(
        name="write_file",
        description="Write content to a file at the given path.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to write, relative to the workspace root.",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file.",
                },
            },
            "required": ["path", "content"],
        },
    ),
    "execute_shell": ToolDefinition(
        name="execute_shell",
        description="Execute a shell command and return its output.",
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory for the command. Defaults to the workspace root.",
                },
            },
            "required": ["command"],
        },
    ),
    "task_complete": ToolDefinition(
        name="task_complete",
        description="Signal that the task has been completed successfully.",
        parameters={
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "A summary of what was accomplished.",
                }
            },
            "required": ["summary"],
        },
    ),
}
