"""Unit tests for services/safe_shell.py covering all 17 security and capability scenarios."""

from __future__ import annotations

import ast
import subprocess  # nosec: B404
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from services.safe_shell import (
    CommandTimeoutError,
    DisallowedCommandError,
    ScriptExecutionError,
    ShellCapabilityValidator,
    WorkspaceEscapeError,
)


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Creates a temporary workspace root for isolated testing."""
    ws = tmp_path / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


@pytest.fixture
def validator(temp_workspace: Path) -> ShellCapabilityValidator:
    """Provides a ShellCapabilityValidator scoped to temp_workspace."""
    return ShellCapabilityValidator(workspace_root=temp_workspace, timeout_s=5)


# 1. Unknown command rejected and raises DisallowedCommandError
def test_unknown_command_rejected_and_raises(validator: ShellCapabilityValidator) -> None:
    valid, msg = validator.validate_shell_command("rm", ["-rf", "/"])
    assert not valid
    assert "rm" in msg

    # Non-strict mode returns error dict
    res = validator.execute_shell_command("rm", ["-rf", "/"], raise_on_error=False)
    assert not res["ok"]
    assert res["returncode"] != 0
    assert "rm" in (res["error"] or "")

    # Strict execution raises DisallowedCommandError
    with pytest.raises(DisallowedCommandError) as exc_info:
        validator.execute_shell_command("cat", ["file.txt"], raise_on_error=True)
    assert "cat" in str(exc_info.value)

    # run_safe_command raises DisallowedCommandError
    with pytest.raises(DisallowedCommandError):
        validator.run_safe_command("powershell", ["-Command", "Get-Process"])


# 2. Python compileall allowed with sys.executable
def test_python_compileall_allowed(
    validator: ShellCapabilityValidator, temp_workspace: Path
) -> None:
    test_file = temp_workspace / "sample.py"
    test_file.write_text("x = 1\n", encoding="utf-8")

    valid, msg = validator.validate_shell_command("python", ["-m", "compileall", "."])
    assert valid
    assert msg == ""

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[sys.executable, "-m", "compileall", "."],
            returncode=0,
            stdout="Listing '.'...\nCompiling 'sample.py'...\n",
            stderr="",
        )
        res = validator.execute_shell_command("python", ["-m", "compileall", "."])
        assert res["ok"]
        assert res["returncode"] == 0

        # Assert sys.executable was used as binary
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd[0] == sys.executable
        assert called_cmd[1:] == ["-m", "compileall", "."]


# 3. Python pytest allowed
def test_python_pytest_allowed(validator: ShellCapabilityValidator) -> None:
    valid, msg = validator.validate_shell_command("python", ["-m", "pytest", "--help"])
    assert valid
    assert msg == ""

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[sys.executable, "-m", "pytest", "--help"],
            returncode=0,
            stdout="pytest usage help text\n",
            stderr="",
        )
        res = validator.run_safe_command("python", ["-m", "pytest", "--help"])
        assert res["ok"]
        assert "pytest usage" in res["output"]


# 4. Python disallowed module rejected
def test_python_disallowed_module_rejected(validator: ShellCapabilityValidator) -> None:
    for bad_mod in ["subprocess", "os", "sys", "shutil", "socket", "urllib"]:
        valid, msg = validator.validate_shell_command("python", ["-m", bad_mod])
        assert not valid
        assert bad_mod in msg

        with pytest.raises(DisallowedCommandError) as exc_info:
            validator.run_safe_command("python", ["-m", bad_mod])
        assert bad_mod in str(exc_info.value)


# 5. Python without -m flag rejected
def test_python_without_m_flag_rejected(validator: ShellCapabilityValidator) -> None:
    # Direct script execution disallowed
    valid, msg = validator.validate_shell_command("python", ["arbitrary_script.py"])
    assert not valid
    assert "-m" in msg

    with pytest.raises(DisallowedCommandError):
        validator.run_safe_command("python", ["arbitrary_script.py"])

    # Empty args disallowed
    valid_empty, msg_empty = validator.validate_shell_command("python", [])
    assert not valid_empty
    assert "requires arguments" in msg_empty

    # Too many args disallowed (max 10)
    too_many = ["-m", "pytest"] + [f"--opt{i}" for i in range(12)]
    valid_many, msg_many = validator.validate_shell_command("python", too_many)
    assert not valid_many
    assert "Too many arguments" in msg_many


# 6. Git status allowed
def test_git_status_allowed(validator: ShellCapabilityValidator) -> None:
    valid, msg = validator.validate_shell_command("git", ["status"])
    assert valid
    assert msg == ""

    valid_short, _ = validator.validate_shell_command("git", ["status", "--short"])
    assert valid_short

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "status", "--short"],
            returncode=0,
            stdout=" M services/safe_shell.py\n",
            stderr="",
        )
        res = validator.execute_shell_command("git", ["status", "--short"])
        assert res["ok"]
        assert res["returncode"] == 0
        assert "services/safe_shell.py" in res["output"]


# 7. Git write subcommands rejected
def test_git_write_subcommands_rejected(validator: ShellCapabilityValidator) -> None:
    for write_cmd in ["push", "commit", "checkout", "rebase", "reset", "merge", "clean"]:
        valid, msg = validator.validate_shell_command("git", [write_cmd])
        assert not valid
        assert write_cmd in msg

        with pytest.raises(DisallowedCommandError):
            validator.run_safe_command("git", [write_cmd])

    # Disallowed flag rejected
    valid_flag, msg_flag = validator.validate_shell_command("git", ["status", "--dangerous-flag"])
    assert not valid_flag
    assert "--dangerous-flag" in msg_flag


# 8. Workspace path traversal rejected
def test_workspace_path_traversal_rejected(
    validator: ShellCapabilityValidator, temp_workspace: Path
) -> None:
    traversal_paths = [
        "../outside.sh",
        "../../etc/passwd",
        "/etc/passwd",
        "/var/run/secret",
        "subdir/../../../../outside",
    ]
    for bad_path in traversal_paths:
        with pytest.raises(WorkspaceEscapeError):
            validator.resolve_workspace_path(bad_path)

        with pytest.raises(WorkspaceEscapeError):
            validator.run_safe_command(bad_path)

        with pytest.raises(WorkspaceEscapeError):
            validator.execute_bash_command(bad_path, raise_on_error=True)

        res = validator.execute_bash_command(bad_path, raise_on_error=False)
        assert not res["ok"]


# 9. NUL byte in path rejected
def test_null_byte_in_path_rejected(validator: ShellCapabilityValidator) -> None:
    nul_path = "script\x00malicious.sh"

    # WorkspaceEscapeError subclasses ValueError to satisfy both exception expectations
    with pytest.raises(WorkspaceEscapeError) as exc_info:
        validator.resolve_workspace_path(nul_path)
    assert isinstance(exc_info.value, ValueError)

    with pytest.raises(WorkspaceEscapeError):
        validator.execute_bash_command(nul_path, raise_on_error=True)

    with pytest.raises(WorkspaceEscapeError):
        validator.run_safe_command(nul_path)

    res = validator.execute_bash_command(nul_path, raise_on_error=False)
    assert not res["ok"]
    assert "NUL" in (res["error"] or "")


# 10. Bash workspace script execution
def test_bash_workspace_script_execution(
    validator: ShellCapabilityValidator, temp_workspace: Path
) -> None:
    script_file = temp_workspace / "run_diagnostic.sh"
    script_file.write_text(
        "#!/usr/bin/env bash\necho 'SOVEREIGN_DIAGNOSTIC_PASS'\n", encoding="utf-8"
    )
    script_file.chmod(0o755)

    valid, msg = validator.validate_bash_command("run_diagnostic.sh")
    assert valid
    assert msg == ""

    with (
        patch("shutil.which", return_value="/bin/bash"),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["/bin/bash", str(script_file)],
            returncode=0,
            stdout="SOVEREIGN_DIAGNOSTIC_PASS\n",
            stderr="",
        )
        res = validator.execute_bash_command("run_diagnostic.sh")
        assert res["ok"]
        assert res["returncode"] == 0
        assert "SOVEREIGN_DIAGNOSTIC_PASS" in res["output"]


# 11. Nonexistent script raises ScriptExecutionError
def test_nonexistent_script_raises(validator: ShellCapabilityValidator) -> None:
    missing_script = "nonexistent_diag_test_99999.sh"

    valid, msg = validator.validate_bash_command(missing_script)
    assert not valid
    assert "not found" in msg

    # ScriptExecutionError subclasses FileNotFoundError
    with pytest.raises(ScriptExecutionError) as exc_info:
        validator.execute_bash_command(missing_script, raise_on_error=True)
    assert isinstance(exc_info.value, FileNotFoundError)

    res = validator.execute_bash_command(missing_script, raise_on_error=False)
    assert not res["ok"]
    assert "not found" in (res["error"] or "")


# 12. CLI allowed commands validated
def test_cli_allowed_commands(validator: ShellCapabilityValidator) -> None:
    for cmd in ["check", "verify", "models", "status"]:
        valid, msg = validator.validate_cli_command(cmd)
        assert valid
        assert msg == ""
        res = validator.execute_cli_command(cmd)
        assert res["ok"]
        assert res["command"] == cmd

    # Run command with argument
    valid_run, msg_run = validator.validate_cli_command("run", ["test_task"])
    assert valid_run
    assert msg_run == ""
    res_run = validator.execute_cli_command("run", ["test_task"])
    assert res_run["ok"]
    assert res_run["args"] == ["test_task"]


# 13. CLI disallowed command rejected
def test_cli_disallowed_command_rejected(validator: ShellCapabilityValidator) -> None:
    for bad_cli in ["destroy", "rm", "reboot", "kill", "deploy"]:
        valid, msg = validator.validate_cli_command(bad_cli)
        assert not valid
        assert bad_cli in msg

        with pytest.raises(DisallowedCommandError):
            validator.execute_cli_command(bad_cli, raise_on_error=True)

        res = validator.execute_cli_command(bad_cli, raise_on_error=False)
        assert not res["ok"]

    # Run without arguments
    valid_no_args, msg_no_args = validator.validate_cli_command("run", [])
    assert not valid_no_args
    assert "requires task argument" in msg_no_args

    with pytest.raises(DisallowedCommandError):
        validator.execute_cli_command("run", [], raise_on_error=True)


# 14. Audit logging calls audit_sink
def test_audit_logging_calls_sink(validator: ShellCapabilityValidator) -> None:
    audit_events: list[dict[str, Any]] = []

    def test_sink(
        action: str, target: str, risk: str, result: str, details: dict[str, Any] | None = None
    ) -> None:
        audit_events.append(
            {"action": action, "target": target, "risk": risk, "result": result, "details": details}
        )

    # 1. Allowed shell execution
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "status"], returncode=0, stdout="clean", stderr=""
        )
        validator.execute_shell_command("git", ["status"], audit_sink=test_sink)

    assert len(audit_events) == 1
    assert audit_events[0]["action"] == "capability.shell"
    assert audit_events[0]["target"] == "git"
    assert audit_events[0]["result"] == "success"

    # 2. Blocked shell execution
    validator.execute_shell_command("rm", ["-rf", "/"], audit_sink=test_sink)
    assert len(audit_events) == 2
    assert audit_events[1]["result"] == "blocked"
    assert audit_events[1]["risk"] == "HIGH"

    # 3. CLI execution
    validator.execute_cli_command("status", audit_sink=test_sink)
    assert len(audit_events) == 3
    assert audit_events[2]["action"] == "capability.cli"
    assert audit_events[2]["target"] == "status"
    assert audit_events[2]["result"] == "success"


# 15. Timeout enforcement terminating hung process
def test_timeout_enforcement(validator: ShellCapabilityValidator) -> None:
    audit_events: list[dict[str, Any]] = []

    def sink(
        action: str, target: str, risk: str, result: str, details: dict[str, Any] | None = None
    ) -> None:
        audit_events.append({"result": result})

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["python"], timeout=5)):
        # raise_on_error=False
        res = validator.execute_shell_command(
            "python", ["-m", "compileall", "."], audit_sink=sink, raise_on_error=False
        )
        assert not res["ok"]
        assert "timeout" in (res["error"] or "").lower()
        assert audit_events[-1]["result"] == "timeout"

        # raise_on_error=True
        with pytest.raises(CommandTimeoutError) as exc_info:
            validator.execute_shell_command(
                "python", ["-m", "compileall", "."], audit_sink=sink, raise_on_error=True
            )
        assert "timeout" in str(exc_info.value).lower()


# 16. shell=False enforced in all executions
def test_shell_false_enforced_in_all_executions(
    validator: ShellCapabilityValidator, temp_workspace: Path
) -> None:
    script_file = temp_workspace / "check.sh"
    script_file.write_text("echo ok\n", encoding="utf-8")

    with (
        patch("shutil.which", return_value="/bin/bash"),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "status"], returncode=0, stdout="", stderr=""
        )

        # Shell execution
        validator.execute_shell_command("git", ["status"])
        assert mock_run.call_count == 1
        assert mock_run.call_args.kwargs.get("shell") is False

        # Bash execution
        validator.execute_bash_command("check.sh")
        assert mock_run.call_count == 2
        assert mock_run.call_args.kwargs.get("shell") is False

    # AST check: Verify services/safe_shell.py contains zero shell=True occurrences
    source_path = Path(__file__).resolve().parent.parent / "services" / "safe_shell.py"
    source_text = source_path.read_text(encoding="utf-8")
    assert "shell=True" not in source_text

    tree = ast.parse(source_text)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.keyword)
            and node.arg == "shell"
            and isinstance(node.value, ast.Constant)
        ):
            assert node.value.value is False, "shell parameter must be explicitly False"


# 17. Tool definitions formatted for agent function calling
def test_tool_definitions_ollama_format(validator: ShellCapabilityValidator) -> None:
    tools = validator.get_tool_definitions()
    assert isinstance(tools, list)
    assert len(tools) == 3

    tool_names = {t["function"]["name"] for t in tools}
    assert tool_names == {"shell", "bash", "cli"}

    for tool in tools:
        assert tool["type"] == "function"
        fn = tool["function"]
        assert "name" in fn
        assert "description" in fn
        assert "parameters" in fn
        params = fn["parameters"]
        assert params["type"] == "object"
        assert "properties" in params
        assert "required" in params
        assert isinstance(params["required"], list)
