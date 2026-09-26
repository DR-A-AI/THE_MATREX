"""Safe Shell Execution and Capability Validator for Sovereign Matrix."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess  # nosec: B404
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

logger = logging.getLogger("Sovereign.SafeShell")


class SafeShellError(Exception):
    """Base exception for safe shell errors."""


class DisallowedCommandError(SafeShellError):
    """Raised when an executable command or argument is not on the allowlist."""


class WorkspaceEscapeError(SafeShellError, ValueError):
    """Raised when a path escapes the designated workspace root."""


class CommandTimeoutError(SafeShellError):
    """Raised when execution exceeds the configured timeout."""


class ScriptExecutionError(SafeShellError, FileNotFoundError):
    """Raised when a workspace script fails validation or execution."""


class ShellCapabilityValidator:
    """Validates and executes allowlisted shell commands safely."""

    workspace_root: Path
    timeout_s: int

    SHELL_ALLOWLIST: ClassVar[dict[str, dict[str, Any]]] = {
        "python": {
            "description": "Python executed with specific safe modules only",
            "allowed_modules": {"compileall", "pytest", "unittest"},
            "max_args": 10,
        },
        "git": {
            "description": "Git read-only diagnostic commands",
            "allowed_subcommands": {"status", "log", "diff"},
            "allowed_flags": {
                "--short",
                "--oneline",
                "-10",
                "--stat",
                "-n",
                "-s",
                "--name-only",
                "--name-status",
            },
        },
    }

    CLI_ALLOWLIST: ClassVar[dict[str, dict[str, Any]]] = {
        "check": {"description": "Check workspace syntax", "approval": False},
        "verify": {"description": "Verify runtime state", "approval": False},
        "models": {"description": "List available models", "approval": False},
        "status": {"description": "Show runtime status", "approval": False},
        "run": {"description": "Run approved tasks", "approval": True},
    }

    def __init__(
        self,
        workspace_root: Path | str | None = None,
        timeout_s: int = 60,
    ) -> None:
        """Initializes the capability validator scoped to workspace_root."""
        if workspace_root is not None:
            self.workspace_root = Path(workspace_root).resolve()
        elif os.environ.get("MATRIX_ROOT"):
            self.workspace_root = Path(os.environ["MATRIX_ROOT"]).resolve()
        else:
            self.workspace_root = Path.cwd().resolve()
        self.timeout_s = timeout_s

    def resolve_workspace_path(self, path: str | Path) -> Path:
        """Resolves path against workspace_root, rejecting NUL bytes,

        path traversal (../), and directory escapes.
        Raises WorkspaceEscapeError on violation.
        """
        path_str = str(path)
        if "\x00" in path_str:
            raise WorkspaceEscapeError("Path contains NUL byte")
        if not path_str.strip():
            raise WorkspaceEscapeError("Path cannot be empty")

        candidate = Path(path_str)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (self.workspace_root / candidate).resolve()

        if resolved != self.workspace_root and not resolved.is_relative_to(self.workspace_root):
            raise WorkspaceEscapeError(
                f"Path '{path_str}' escapes workspace root '{self.workspace_root}'"
            )

        return resolved

    def _record_audit(
        self,
        audit_sink: Callable[..., Any] | None,
        action: str,
        target: str,
        risk: str,
        result: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Records structured audit entry to logger and optional audit sink."""
        logger.info(
            "SafeShell Audit: action=%s target=%s risk=%s result=%s details=%s",
            action,
            target,
            risk,
            result,
            details or {},
        )
        if audit_sink is not None:
            try:
                audit_sink(
                    action=action,
                    target=target,
                    risk=risk,
                    result=result,
                    details=details or {},
                )
            except TypeError:
                try:
                    audit_sink(
                        action=action,
                        target=target,
                        risk=risk,
                        result=result,
                    )
                except (ValueError, RuntimeError, OSError) as exc:
                    logger.warning("audit_sink callback failed: %s", exc)

    def validate_shell_command(self, command: str, args: list[str]) -> tuple[bool, str]:
        """Validate shell command name and arguments against allowlist."""
        if command not in self.SHELL_ALLOWLIST:
            return False, f"Command '{command}' not in allowlist"

        spec = self.SHELL_ALLOWLIST[command]

        if command == "python":
            return self._validate_python_args(args, spec)
        if command == "git":
            return self._validate_git_args(args, spec)

        return False, f"Command '{command}' not supported"

    def _validate_python_args(self, args: list[str], spec: dict[str, Any]) -> tuple[bool, str]:
        """Validate python command arguments."""
        if not args:
            return False, "Python command requires arguments"

        if "-m" not in args:
            return False, "Python command requires '-m' flag"

        m_idx = args.index("-m")
        if m_idx + 1 >= len(args):
            return False, "Python '-m' flag requires a module name"

        module = args[m_idx + 1]
        allowed_modules: set[str] = spec.get("allowed_modules", set())
        if module not in allowed_modules:
            return (
                False,
                f"Python module '{module}' not allowed (allowed: {sorted(allowed_modules)})",
            )

        max_args: int = spec.get("max_args", 10)
        if len(args) > max_args:
            return False, f"Too many arguments for python (max {max_args}, got {len(args)})"

        return True, ""

    def _validate_git_args(self, args: list[str], spec: dict[str, Any]) -> tuple[bool, str]:
        """Validate git command arguments (read-only diagnostics only)."""
        if not args:
            return False, "Git command requires a subcommand"

        subcommand = args[0]
        allowed_subcommands: set[str] = spec.get("allowed_subcommands", set())
        if subcommand not in allowed_subcommands:
            return (
                False,
                f"Git subcommand '{subcommand}' not allowed (allowed: {sorted(allowed_subcommands)})",
            )

        allowed_flags: set[str] = spec.get("allowed_flags", set())
        for arg in args[1:]:
            if arg.startswith("-") and arg not in allowed_flags:
                return (
                    False,
                    f"Git flag '{arg}' not allowed (allowed: {sorted(allowed_flags)})",
                )

        return True, ""

    def validate_bash_command(
        self, script_path: str, args: list[str] | None = None
    ) -> tuple[bool, str]:
        """Validate bash execution of workspace scripts only."""
        if "\x00" in script_path:
            return False, "Path contains NUL byte"
        try:
            resolved = self.resolve_workspace_path(script_path)
        except WorkspaceEscapeError as exc:
            return False, str(exc)

        if not resolved.exists():
            return False, f"Script not found: {script_path}"

        if resolved.is_dir():
            return False, f"Script path is a directory: {script_path}"

        try:
            if resolved.stat().st_size > 1_048_576:
                return False, "Script exceeds size limit (1MB)"
        except OSError as exc:
            return False, f"Cannot stat script: {exc}"

        return True, ""

    def validate_cli_command(self, command: str, args: list[str] | None = None) -> tuple[bool, str]:
        """Validate Matrix CLI command against allowlist."""
        if command not in self.CLI_ALLOWLIST:
            return False, f"CLI command '{command}' not in allowlist"

        spec = self.CLI_ALLOWLIST[command]
        if command == "run" and spec.get("approval") and (not args or len(args) < 1):
            return False, "CLI run command requires task argument"

        return True, ""

    def execute_shell_command(
        self,
        command: str,
        args: list[str],
        cwd: Path | str | None = None,
        audit_sink: Callable[..., Any] | None = None,
        raise_on_error: bool = False,
    ) -> dict[str, Any]:
        """Executes allowlisted shell command with shell=False.

        Returns {'ok': bool, 'returncode': int, 'output': str, 'error': str | None}.
        """
        valid, error_msg = self.validate_shell_command(command, args)
        if not valid:
            self._record_audit(
                audit_sink,
                action="capability.shell",
                target=command,
                risk="HIGH",
                result="blocked",
                details={"args": args, "reason": error_msg},
            )
            if raise_on_error:
                raise DisallowedCommandError(error_msg)
            return {"ok": False, "returncode": 1, "output": "", "error": error_msg}

        if cwd is None:
            exec_cwd = self.workspace_root
        else:
            try:
                exec_cwd = self.resolve_workspace_path(cwd)
            except WorkspaceEscapeError as exc:
                self._record_audit(
                    audit_sink,
                    action="capability.shell",
                    target=command,
                    risk="HIGH",
                    result="blocked",
                    details={"args": args, "reason": str(exc)},
                )
                if raise_on_error:
                    raise
                return {"ok": False, "returncode": 1, "output": "", "error": str(exc)}

        if command == "python":
            cmd = [sys.executable] + args
        else:
            cmd = [command] + args

        try:
            completed = subprocess.run(  # nosec: B603, B607
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                shell=False,
                cwd=str(exec_cwd),
                check=False,
            )
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
            output = (stdout[-2000:] + stderr[-500:]).strip()
            ok = completed.returncode == 0
            error_str = (
                None
                if ok
                else (stderr.strip() or f"Process exited with code {completed.returncode}")
            )
            self._record_audit(
                audit_sink,
                action="capability.shell",
                target=command,
                risk="LOW",
                result="success" if ok else "failed",
                details={"returncode": completed.returncode, "cmd": cmd},
            )
            return {
                "ok": ok,
                "returncode": completed.returncode,
                "output": output,
                "error": error_str,
            }
        except subprocess.TimeoutExpired as exc:
            self._record_audit(
                audit_sink,
                action="capability.shell",
                target=command,
                risk="MEDIUM",
                result="timeout",
                details={"timeout_s": self.timeout_s, "cmd": cmd},
            )
            if raise_on_error:
                raise CommandTimeoutError(f"Command timeout after {self.timeout_s}s") from exc
            return {
                "ok": False,
                "returncode": -1,
                "output": "",
                "error": f"Command timeout after {self.timeout_s}s",
            }
        except Exception as exc:
            self._record_audit(
                audit_sink,
                action="capability.shell",
                target=command,
                risk="HIGH",
                result="error",
                details={"error": str(exc), "cmd": cmd},
            )
            if raise_on_error:
                raise SafeShellError(f"Execution error: {exc}") from exc
            return {
                "ok": False,
                "returncode": -1,
                "output": "",
                "error": str(exc)[:200],
            }

    def execute_bash_command(
        self,
        script_path: str,
        args: list[str] | None = None,
        cwd: Path | str | None = None,
        audit_sink: Callable[..., Any] | None = None,
        raise_on_error: bool = False,
    ) -> dict[str, Any]:
        """Executes a workspace script via bash with shell=False."""
        if "\x00" in script_path:
            error_msg = "Path contains NUL byte"
            self._record_audit(
                audit_sink,
                action="capability.bash",
                target=script_path,
                risk="CRITICAL",
                result="blocked",
                details={"reason": error_msg},
            )
            if raise_on_error:
                raise WorkspaceEscapeError(error_msg)
            return {"ok": False, "returncode": 1, "output": "", "error": error_msg}

        try:
            resolved_script = self.resolve_workspace_path(script_path)
        except WorkspaceEscapeError as exc:
            self._record_audit(
                audit_sink,
                action="capability.bash",
                target=script_path,
                risk="CRITICAL",
                result="blocked",
                details={"reason": str(exc)},
            )
            if raise_on_error:
                raise
            return {"ok": False, "returncode": 1, "output": "", "error": str(exc)}

        if not resolved_script.exists():
            error_msg = f"Script not found: {script_path}"
            self._record_audit(
                audit_sink,
                action="capability.bash",
                target=script_path,
                risk="MEDIUM",
                result="blocked",
                details={"reason": error_msg},
            )
            if raise_on_error:
                raise ScriptExecutionError(error_msg)
            return {"ok": False, "returncode": 1, "output": "", "error": error_msg}

        if resolved_script.is_dir():
            error_msg = f"Script path is a directory: {script_path}"
            self._record_audit(
                audit_sink,
                action="capability.bash",
                target=script_path,
                risk="MEDIUM",
                result="blocked",
                details={"reason": error_msg},
            )
            if raise_on_error:
                raise ScriptExecutionError(error_msg)
            return {"ok": False, "returncode": 1, "output": "", "error": error_msg}

        try:
            if resolved_script.stat().st_size > 1_048_576:
                error_msg = "Script exceeds size limit (1MB)"
                self._record_audit(
                    audit_sink,
                    action="capability.bash",
                    target=script_path,
                    risk="HIGH",
                    result="blocked",
                    details={"reason": error_msg},
                )
                if raise_on_error:
                    raise ScriptExecutionError(error_msg)
                return {"ok": False, "returncode": 1, "output": "", "error": error_msg}
        except OSError as exc:
            error_msg = f"Cannot stat script: {exc}"
            if raise_on_error:
                raise ScriptExecutionError(error_msg) from exc
            return {"ok": False, "returncode": 1, "output": "", "error": error_msg}

        bash_exe = shutil.which("bash")
        if not bash_exe:
            error_msg = "bash executable not found on host"
            self._record_audit(
                audit_sink,
                action="capability.bash",
                target=script_path,
                risk="HIGH",
                result="error",
                details={"reason": error_msg},
            )
            if raise_on_error:
                raise ScriptExecutionError(error_msg)
            return {"ok": False, "returncode": 1, "output": "", "error": error_msg}

        if cwd is None:
            exec_cwd = self.workspace_root
        else:
            try:
                exec_cwd = self.resolve_workspace_path(cwd)
            except WorkspaceEscapeError as exc:
                self._record_audit(
                    audit_sink,
                    action="capability.bash",
                    target=script_path,
                    risk="HIGH",
                    result="blocked",
                    details={"reason": str(exc)},
                )
                if raise_on_error:
                    raise
                return {"ok": False, "returncode": 1, "output": "", "error": str(exc)}

        cmd = [bash_exe, str(resolved_script)] + (args or [])

        try:
            completed = subprocess.run(  # nosec: B603, B607
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                shell=False,
                cwd=str(exec_cwd),
                check=False,
            )
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
            output = (stdout[-2000:] + stderr[-500:]).strip()
            ok = completed.returncode == 0
            error_str = (
                None
                if ok
                else (stderr.strip() or f"Process exited with code {completed.returncode}")
            )
            self._record_audit(
                audit_sink,
                action="capability.bash",
                target=script_path,
                risk="MEDIUM",
                result="success" if ok else "failed",
                details={"returncode": completed.returncode, "cmd": cmd},
            )
            return {
                "ok": ok,
                "returncode": completed.returncode,
                "output": output,
                "error": error_str,
            }
        except subprocess.TimeoutExpired as exc:
            self._record_audit(
                audit_sink,
                action="capability.bash",
                target=script_path,
                risk="HIGH",
                result="timeout",
                details={"timeout_s": self.timeout_s, "cmd": cmd},
            )
            if raise_on_error:
                raise CommandTimeoutError(f"Script timeout after {self.timeout_s}s") from exc
            return {
                "ok": False,
                "returncode": -1,
                "output": "",
                "error": f"Script timeout after {self.timeout_s}s",
            }
        except Exception as exc:
            self._record_audit(
                audit_sink,
                action="capability.bash",
                target=script_path,
                risk="HIGH",
                result="error",
                details={"error": str(exc), "cmd": cmd},
            )
            if raise_on_error:
                raise ScriptExecutionError(f"Execution error: {exc}") from exc
            return {
                "ok": False,
                "returncode": -1,
                "output": "",
                "error": str(exc)[:200],
            }

    def execute_cli_command(
        self,
        command: str,
        args: list[str] | None = None,
        audit_sink: Callable[..., Any] | None = None,
        raise_on_error: bool = False,
    ) -> dict[str, Any]:
        """Executes allowlisted Matrix CLI command."""
        valid, error_msg = self.validate_cli_command(command, args)
        if not valid:
            self._record_audit(
                audit_sink,
                action="capability.cli",
                target=command,
                risk="HIGH",
                result="blocked",
                details={"args": args, "reason": error_msg},
            )
            if raise_on_error:
                raise DisallowedCommandError(error_msg)
            return {"ok": False, "returncode": 1, "output": "", "error": error_msg}

        self._record_audit(
            audit_sink,
            action="capability.cli",
            target=command,
            risk="HIGH" if command == "run" else "LOW",
            result="success",
            details={"args": args or []},
        )
        return {
            "ok": True,
            "returncode": 0,
            "command": command,
            "args": args or [],
            "output": f"Matrix CLI '{command}' validated with args {args or []}",
            "error": None,
        }

    def run_safe_command(
        self,
        command: str,
        args: list[str] | None = None,
        cwd: Path | str | None = None,
        audit_sink: Callable[..., Any] | None = None,
    ) -> dict[str, Any]:
        """Convenience execution method enforcing strict exception raising

        (DisallowedCommandError, WorkspaceEscapeError, ScriptExecutionError, CommandTimeoutError).
        """
        if command in self.SHELL_ALLOWLIST:
            return self.execute_shell_command(
                command,
                args=args or [],
                cwd=cwd,
                audit_sink=audit_sink,
                raise_on_error=True,
            )
        if command in self.CLI_ALLOWLIST:
            return self.execute_cli_command(
                command,
                args=args or [],
                audit_sink=audit_sink,
                raise_on_error=True,
            )
        if command == "bash":
            if not args or len(args) < 1:
                error_msg = "Bash execution requires script_path as first argument"
                self._record_audit(
                    audit_sink,
                    action="capability.bash",
                    target=command,
                    risk="HIGH",
                    result="blocked",
                    details={"reason": error_msg},
                )
                raise DisallowedCommandError(error_msg)
            return self.execute_bash_command(
                args[0],
                args=args[1:],
                cwd=cwd,
                audit_sink=audit_sink,
                raise_on_error=True,
            )
        if command.endswith(".sh") or "/" in command or "\\" in command or "\x00" in command:
            return self.execute_bash_command(
                command,
                args=args,
                cwd=cwd,
                audit_sink=audit_sink,
                raise_on_error=True,
            )

        error_msg = f"Command '{command}' not in allowlist"
        self._record_audit(
            audit_sink,
            action="capability.shell",
            target=command,
            risk="HIGH",
            result="blocked",
            details={"args": args, "reason": error_msg},
        )
        raise DisallowedCommandError(error_msg)

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Returns JSON function schemas for Ollama tool calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "shell",
                    "description": (
                        "Execute an allowlisted diagnostics command ('python -m <module>' or "
                        "'git <subcommand>') safely within workspace boundaries."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": (
                                    "The command executable to invoke ('python' or 'git')"
                                ),
                                "enum": ["python", "git"],
                            },
                            "args": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Command line arguments",
                            },
                        },
                        "required": ["command", "args"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "bash",
                    "description": (
                        "Execute a workspace-scoped bash script safely with size limits "
                        "and process isolation."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "script_path": {
                                "type": "string",
                                "description": (
                                    "Path to the bash script relative to the workspace root"
                                ),
                            },
                            "args": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional script arguments",
                            },
                        },
                        "required": ["script_path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "cli",
                    "description": (
                        "Execute an allowlisted Matrix runtime CLI command "
                        "(check, verify, models, status, run)."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "Matrix CLI command",
                                "enum": ["check", "verify", "models", "status", "run"],
                            },
                            "args": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional CLI arguments",
                            },
                        },
                        "required": ["command"],
                    },
                },
            },
        ]


__all__ = [
    "CommandTimeoutError",
    "DisallowedCommandError",
    "SafeShellError",
    "ScriptExecutionError",
    "ShellCapabilityValidator",
    "WorkspaceEscapeError",
]
