import asyncio
import logging
import os
import shlex
import subprocess  # nosec: B404  # argv-only calls below, shell never enabled
import uuid
from pathlib import Path
from typing import Any

from agents.base_agent import MatrixAgent
from core.models import EventPayload, EventType
from services.ollama_client import AgentRole, get_router

logger = logging.getLogger("Matrix.Neo")


class NeoAgent(MatrixAgent):
    """
    NEO: THE JOKER AGENT & SUPREME EXTRACTOR
    Capable of operating in the Dark (Headless/Background) and the Light (Interactive/GUI),
    as well as blind key extraction under the Sovereign Constitution.
    """

    def __init__(self, name: str = "neo", bus_url: str | None = None):
        super().__init__(name=name, bus_url=bus_url)
        self._CORE_IDENTITY = {
            "identity": "Sovereign Extractor & Savior",
            "commander": "الأب القائد",
            "role": "Blind Key Extraction & Dynamic Command Execution",
        }

    async def extract_and_surrender_token(self, target_platform: str, extracted_key: str) -> None:
        """
        Extracts a key from external platform context and transmits it blindly onto the Neural Bus.
        IMMEDIATELY sends it blindly onto the Neural Bus for the Assistant Crawler.
        Neo does NOT keep the key in memory after transmission.
        """
        logger.info(
            f"[{self.name}] Succeeded in extracting token from {target_platform}. Surrendering to Assistant Crawler blindly."
        )
        event = EventPayload(
            event_type=EventType.TOKEN_EXTRACTED,
            source_agent_id=self.agent_id,
            correlation_id=str(uuid.uuid4()),
            payload={"platform": target_platform, "extracted_token": extracted_key},
        )
        await self.client.send(event)
        logger.info(f"[{self.name}] Token surrendered successfully. Hands are clean.")

    async def execute_in_the_dark(self, command: str) -> tuple:
        """Executes tasks silently in the isolated background session (no shell)."""
        logger.info(f"[{self.name}] Executing in the DARK: {command}")

        def run_cmd() -> tuple[str, str]:
            import subprocess  # nosec: B404  # argv-only call below, shell never enabled

            if not isinstance(command, str) or not command.strip():
                return "", "ERROR: empty command"
            if len(command) > 8192:
                return "", "ERROR: command too long"
            args = shlex.split(command, posix=(os.name != "nt"))
            if not args:
                return "", "ERROR: empty command"
            try:
                # shell=False explicitly set; argv list prevents shell injection
                res = subprocess.run(  # nosec: B603  # argv list, shell=False; input type/length validated above
                    args, capture_output=True, check=False, shell=False
                )
            except FileNotFoundError as e:
                return "", f"ERROR: command not found: {args[0]}: {e}"
            except Exception as e:
                logger.exception("Dark command execution failed")
                return "", f"ERROR executing command: {e}"
            return res.stdout.decode(errors="replace"), res.stderr.decode(errors="replace")

        return await asyncio.to_thread(run_cmd)

    async def execute_in_the_light(self, target: str) -> str:
        """
        Forces execution into the Commander's active interactive session (The Light).
        Uses 'explorer' to break out of Session 0 isolation on Windows.
        Validates target and invokes explorer without a shell.
        """
        logger.info(f"[{self.name}] Executing in the LIGHT (Interactive): {target}")
        try:
            if not isinstance(target, str) or not target.strip():
                raise ValueError("Invalid target: empty")
            target = target.strip()
            if "\x00" in target:
                raise ValueError("Invalid target: NUL byte not allowed")
            if len(target) > 2048:
                raise ValueError("Invalid target: too long")

            # argv list with no shell: target is a single arg to explorer, no expansion
            def _launch_explorer(_target: str) -> None:
                subprocess.Popen(
                    ["explorer", _target], shell=False
                )  # nosec: B603, B607  # fixed argv, explicit shell=False; explorer via PATH is intended

            await asyncio.to_thread(_launch_explorer, target)
            return f"Requested Light execution for: {target}"
        except Exception as e:
            logger.exception("Failed Light execution")
            return str(e)

    async def operate_browser(self, url: str, show_ui: bool = False) -> str:
        """Browser automation. Dark = Real Headless HTTP fetch, Light = Interactive Explorer URL dispatch."""
        if show_ui:
            logger.info(f"[{self.name}] Opening Visible Browser (Light) for {url}")
            return await self.execute_in_the_light(url)
        else:
            logger.info(f"[{self.name}] Inspecting via Headless fetch (Dark) for {url}")
            try:
                import urllib.request

                req = urllib.request.Request(url, headers={"User-Agent": "SovereignMatrix/2.0"})

                def _fetch() -> str:
                    with urllib.request.urlopen(req, timeout=10.0) as resp:  # nosec: B310
                        return f"Fetched {len(resp.read())} bytes from {url}"

                return await asyncio.to_thread(_fetch)
            except Exception as e:  # noqa: BLE001
                logger.error(f"[{self.name}] Headless inspection error: {e}")
                return f"ERROR inspecting {url}: {e}"

    async def execute(self, task: Any) -> dict[str, Any]:
        """Parses Commander's instructions and chooses Light or Dark mode, or executes code."""
        instructions = task.instructions
        input_data = task.input_data or {}

        intent = input_data.get("intent", "dark")
        target = input_data.get("target", instructions)

        # If instruction is a shell command
        if intent == "light" or "open " in instructions.lower() or "http" in instructions:
            res = await self.execute_in_the_light(target)
            return {"status": "success", "message": res}
        else:
            stdout, stderr = await self.execute_in_the_dark(target)
            return {
                "status": "success",
                "message": f"Stdout: {stdout.strip()} | Stderr: {stderr.strip()}",
            }

    async def _handle_user_command(self, event: EventPayload) -> None:
        payload = event.payload
        target_raw = payload.get("target_agent", "")
        message_raw = payload.get("message", "")
        command_raw = payload.get("command", "")
        target = target_raw if isinstance(target_raw, str) else ""
        # Live UI sends {'command': '...'} while tests/legacy send {'message': '...'}.
        # Prefer the non-empty raw text from either field so readiness detection
        # never sees an empty string when the command arrived in the other field.
        _msg = message_raw if isinstance(message_raw, str) else ""
        _cmd = command_raw if isinstance(command_raw, str) else ""
        message = _msg if _msg.strip() else _cmd

        # Ensure command is routed to Neo
        if target.lower() not in self.name.lower() and target.lower() not in self.agent_id.lower():
            return

        # Validate authority
        if not await self._validate_commander(event):
            return

        logger.info(f"[{self.name}] Neo (Antigravity) received directive: {message}")

        # --- DETERMINISTIC STATUS / CORRECTION PATH (anti-hallucination) ---
        # MUST run BEFORE any semantic routing: BARE readiness pings are
        # answered from live telemetry, never from free LLM generation (which
        # emitted canned "hypothetical" disclaimers). Corrections prune the bad
        # turn so it is never defended. Checking the raw text first guarantees
        # the 'جاهز؟'-style readiness probe never falls through to general_chat
        # on an empty-string (score=0.00) tie when the payload used 'command'.
        # NOTE: only full-message pings intercept here — substantive requests
        # ("run a full audit...", "check tensor health...") MUST flow to normal
        # routing/tools, grounded by GROUNDING_SUFFIX (telemetry, never hypothetical).
        from core.status_telemetry import is_correction, is_readiness_ping

        intent = None  # set by correction-remainder path; else parsed after intercept
        if is_correction(message):
            from core.status_telemetry import (
                detect_language,
                prune_last_assistant_turn,
                strip_correction_prefix,
            )

            dropped = prune_last_assistant_turn(self.chat_history)
            logger.info(
                f"[{self.name}] Commander correction accepted; "
                f"dropped {dropped} stale assistant turn(s)."
            )
            remainder = strip_correction_prefix(message)
            if remainder and is_readiness_ping(remainder):
                await self._reply_live_status(event, remainder)
                return
            if remainder:
                message = (
                    f"{remainder}\n\n[Commander correction: the previous assistant "
                    "answer was discarded. Reinterpret this corrected intent from "
                    "scratch; never defend the previous answer.]"
                )
                intent = self.intent_parser.parse(remainder)
                logger.info(
                    f"[{self.name}] Corrected Semantic Route: '{intent.route}' "
                    f"(score={intent.route_score:.2f})"
                )
            else:
                lang = detect_language(message)
                clarification = (
                    "تمام أيها القائد — تجاهلت إجابتي السابقة تماماً ولن أدافع عنها. "
                    "أعد صياغة طلبك بدقة وسأنفذه فوراً."
                    if lang == "ar"
                    else "Understood Commander — my previous answer is discarded and "
                    "will not be defended. Please restate your request precisely "
                    "and I will execute it at once."
                )
                await self._send_final_reply(event, clarification)
                return
        elif is_readiness_ping(message):
            await self._reply_live_status(event, message)
            return

        # Grounding injection: status-flavored substantive requests carry the
        # live telemetry snapshot INTO the LLM prompt, so answers are built
        # from probed data instead of generic boilerplate. Real data, no mock.
        from core.status_telemetry import is_status_query as _is_status_q

        if _is_status_q(message):
            try:
                from core.status_telemetry import collect_full_status as _collect

                _snap = _collect()
                message = (
                    f"{message}\n\n[Live system snapshot — call get_system_status "
                    f"for the authoritative snapshot, then answer ONLY from live "
                    f"probed facts, never hypothetical or generic: {_snap}]"
                )
            except Exception as e:  # noqa: BLE001
                logger.debug(f"[{self.name}] Telemetry snapshot unavailable: {e}")

        # Semantic Router & Dynamic Tool Pruning (runs ONLY after deterministic intercept)
        if intent is None:
            intent = self.intent_parser.parse(message)
            logger.info(
                f"[{self.name}] Semantic Route: '{intent.route}' (score={intent.route_score:.2f}) -> Allowed Tools: {intent.selected_tools}"
            )

        # If it's a memory store/recall request, let the base agent handle it
        if (
            "store permanent:" in message.lower()
            or "خزن دائمة:" in message
            or "recall:" in message.lower()
            or "تذكر:" in message.lower()
            or "ابحث:" in message
        ):
            await super()._handle_user_command(event)
            return

        if message.strip() == "/clear":
            self.chat_history = []
            reply = EventPayload(
                event_type=EventType.STATE_UPDATE,
                source_agent_id=self.name,
                correlation_id=event.correlation_id,
                payload={"message": "Conversation history cleared from memory."},
            )
            await self.client.send(reply)
            return

        # Send initial thinking status
        initial_status = EventPayload(
            event_type=EventType.STATE_UPDATE,
            source_agent_id=self.name,
            correlation_id=event.correlation_id,
            payload={"status_action": "Thinking..."},
        )
        await self.client.send(initial_status)

        # Dynamic workspace resolution
        workspace_root = Path(os.getenv("MATRIX_ROOT", Path.cwd())).resolve()

        # Local tool definitions
        def run_local_command(command: str) -> str:
            """Executes a command locally in the workspace and returns stdout and stderr (no shell)."""
            import subprocess  # nosec: B404  # argv-only call below, shell never enabled

            try:
                if not isinstance(command, str) or not command.strip():
                    return "ERROR: empty command"
                if len(command) > 8192:
                    return "ERROR: command too long"
                args = shlex.split(command, posix=(os.name != "nt"))
                if not args:
                    return "ERROR: empty command"
                workspace = str(workspace_root)
                # shell=False explicitly set; argv list prevents shell injection
                res = subprocess.run(  # nosec: B603  # argv list, shell=False; input type/length validated above
                    args, capture_output=True, text=True, cwd=workspace, check=False, shell=False
                )
                return f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
            except Exception as e:
                logger.exception("Local command execution failed")
                return f"ERROR executing command: {e!s}"

        def get_system_status(**_ignored: Any) -> str:
            """Returns authoritative LIVE system snapshot (telemetry + Groq
            pool + Ollama models). All fields probed at call time; keys masked.
            Call this FIRST for any status/audit/health/verification question
            and answer ONLY from its output."""
            import json as _json

            from core.status_telemetry import collect_full_status

            return _json.dumps(collect_full_status(), ensure_ascii=False)

        def _resolve_safe_path(path_str: str) -> Path:
            """Resolves path and enforces that it remains strictly inside workspace_root."""
            raw = Path(path_str)
            resolved = raw.resolve() if raw.is_absolute() else (workspace_root / raw).resolve()
            if not resolved.is_relative_to(workspace_root):
                raise PermissionError(f"Path traversal detected: {path_str} escapes workspace {workspace_root}")
            return resolved

        def read_local_file(path: str, start_line: int = 1, end_line: int = 800) -> str:
            """Reads lines from a file in the workspace."""
            try:
                target_path = _resolve_safe_path(path)
                with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                sub_lines = lines[start_line - 1 : end_line]
                return "".join(sub_lines)
            except Exception as e:
                logger.exception("Local file read failed")
                return f"ERROR reading file: {e!s}"

        def write_local_file(path: str, content: str) -> str:
            """Writes content to a file in the workspace."""
            try:
                target_path = _resolve_safe_path(path)
                os.makedirs(target_path.parent, exist_ok=True)
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return f"Successfully wrote to {target_path}"
            except Exception as e:
                logger.exception("Local file write failed")
                return f"ERROR writing file: {e!s}"

        def edit_local_file(path: str, target_content: str, replacement_content: str) -> str:
            """Replaces a unique block of text (target_content) in a file with replacement_content."""
            try:
                target_path = _resolve_safe_path(path)
                with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                if target_content not in content:
                    return "ERROR: Target content not found in file."
                if content.count(target_content) > 1:
                    return "ERROR: Target content is not unique in file. Please specify a unique block."
                new_content = content.replace(target_content, replacement_content)
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                return f"Successfully edited {target_path}"
            except Exception as e:
                logger.exception("Local file edit failed")
                return f"ERROR editing file: {e!s}"

        def list_local_dir(path: str = ".") -> str:
            """Lists contents of a directory in the workspace."""
            try:
                target_path = _resolve_safe_path(path)
                items = os.listdir(target_path)
                out = []
                for item in items:
                    full = target_path / item
                    is_dir = full.is_dir()
                    size = full.stat().st_size if not is_dir else 0
                    out.append(f"{'[DIR]' if is_dir else '[FILE]'} {item} ({size} bytes)")
                return "\n".join(out)
            except Exception as e:
                logger.exception("Local dir list failed")
                return f"ERROR listing directory: {e!s}"

        def search_local_code(query: str, path: str = ".") -> str:
            """Searches for occurrences of query text in files under path recursively."""
            try:
                target_path = _resolve_safe_path(path)
                results = []
                for root, dirs, files in os.walk(target_path):
                    if any(p in root for p in [".git", "node_modules", "__pycache__", "dist"]):
                        continue
                    for file in files:
                        filepath = os.path.join(root, file)
                        try:
                            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                                for idx, line in enumerate(f, 1):
                                    if query in line:
                                        rel_path = os.path.relpath(filepath, workspace_root)
                                        results.append(f"{rel_path}:{idx}: {line.strip()}")
                                        if len(results) >= 50:
                                            return (
                                                "\n".join(results)
                                                + "\n... (more matches truncated)"
                                            )
                        except Exception:
                            logger.debug(f"Skipping unreadable file {filepath}", exc_info=True)
                if not results:
                    return "No matches found."
                return "\n".join(results)
            except Exception as e:
                logger.exception("Local code search failed")
                return f"ERROR searching code: {e!s}"

        def open_browser(url: str) -> str:
            """Opens the default web browser to the specified URL."""
            import webbrowser

            try:
                webbrowser.open(url)
                return f"Successfully opened browser to {url}"
            except Exception as e:
                logger.exception("Browser open failed")
                return f"ERROR opening browser: {e!s}"

        from core import matrix_vision

        def capture_screen(monitor_index: int = 1) -> str:
            """Captures the screen and allows Neo to 'see' the Matrix. ALSO displays it to the Commander. ALWAYS use this when asked to look at or show the screen."""
            try:
                import time

                timestamp = int(time.time())
                filename = f"matrix_vision_{timestamp}.png"
                filepath = workspace_root / "dashboard" / "public" / filename
                os.makedirs(filepath.parent, exist_ok=True)
                success = matrix_vision.save_screenshot(str(filepath), monitor_index)
                if not success:
                    return "ERROR: Failed to capture screen due to system isolation or BitBlt access denied."
                dashboard_url = os.getenv("DASHBOARD_URL", "http://127.0.0.1:5173")
                return f"SCREENSHOT_SAVED:![Matrix Vision]({dashboard_url}/{filename})"
            except Exception as e:
                logger.exception("Screenshot capture failed")
                return f"ERROR saving screenshot: {e!s}"

        def safe_click(x: int, y: int, button: str = "left") -> str:
            """Clicks the mouse at X, Y coordinates."""
            try:
                matrix_vision.safe_click(x, y, button)
                return f"Successfully clicked {button} at {x}, {y}."
            except Exception as e:
                logger.exception("Safe click failed")
                return f"ERROR clicking: {e!s}"

        def safe_type_text(text: str) -> str:
            """Types text directly into the active window."""
            try:
                matrix_vision.safe_type_text(text)
                return "Successfully typed text."
            except Exception as e:
                logger.exception("Safe type failed")
                return f"ERROR typing: {e!s}"

        def safe_press_key(key: str) -> str:
            """Presses a specific key (e.g. 'enter', 'tab', 'win')."""
            try:
                matrix_vision.safe_press_key(key)
                return f"Successfully pressed {key}."
            except Exception as e:
                logger.exception("Safe key press failed")
                return f"ERROR pressing key: {e!s}"

        tool_map: dict[str, Any] = {
            "run_local_command": run_local_command,
            "get_system_status": get_system_status,
            "read_local_file": read_local_file,
            "write_local_file": write_local_file,
            "edit_local_file": edit_local_file,
            "list_local_dir": list_local_dir,
            "search_local_code": search_local_code,
            "open_browser": open_browser,
            "capture_screen": capture_screen,
            "safe_click": safe_click,
            "safe_type_text": safe_type_text,
            "safe_press_key": safe_press_key,
        }

        tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "run_local_command",
                    "description": "Executes a command locally in the workspace and returns stdout and stderr (no shell).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "The command to execute"}
                        },
                        "required": ["command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_system_status",
                    "description": "Returns authoritative LIVE system snapshot: probed bus/Ollama/bridge/dashboard telemetry plus Groq pool accounts (masked keys) and Ollama models. MUST be called first for any status, audit, health, or verification question; answer ONLY from its output.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_local_file",
                    "description": "Reads lines from a file in the workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Path to the file"},
                            "start_line": {"type": "integer", "description": "Start line number"},
                            "end_line": {"type": "integer", "description": "End line number"},
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_local_file",
                    "description": "Writes content to a file in the workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Path to the file"},
                            "content": {"type": "string", "description": "Content to write"},
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "edit_local_file",
                    "description": "Replaces a unique block of text (target_content) in a file with replacement_content.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Path to the file"},
                            "target_content": {
                                "type": "string",
                                "description": "Exact text to replace",
                            },
                            "replacement_content": {"type": "string", "description": "New text"},
                        },
                        "required": ["path", "target_content", "replacement_content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_local_dir",
                    "description": "Lists contents of a directory in the workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to the directory, defaults to '.'",
                            }
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_local_code",
                    "description": "Searches for occurrences of query text in files under path recursively.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Text to search for"},
                            "path": {"type": "string", "description": "Directory to search in"},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "open_browser",
                    "description": "Opens the default web browser to the specified URL.",
                    "parameters": {
                        "type": "object",
                        "properties": {"url": {"type": "string", "description": "URL to open"}},
                        "required": ["url"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "capture_screen",
                    "description": "Captures the screen and allows Neo to 'see' the Matrix. ALWAYS use this when asked to look at or show the screen.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "monitor_index": {
                                "type": "integer",
                                "description": "Monitor index to capture, usually 1",
                            }
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "safe_click",
                    "description": "Clicks the mouse at X, Y coordinates.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "integer"},
                            "y": {"type": "integer"},
                            "button": {
                                "type": "string",
                                "description": "Button to click ('left', 'right', 'middle')",
                            },
                        },
                        "required": ["x", "y"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "safe_type_text",
                    "description": "Types text directly into the active window.",
                    "parameters": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "safe_press_key",
                    "description": "Presses a specific key (e.g. 'enter', 'tab', 'win').",
                    "parameters": {
                        "type": "object",
                        "properties": {"key": {"type": "string"}},
                        "required": ["key"],
                    },
                },
            },
        ]

        from datetime import datetime, timezone

        from core.status_telemetry import GROUNDING_SUFFIX

        current_time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        sys_instruction = (
            f"NEVER say you are a language model trained by anyone. "
            f"You are Neo (Antigravity), the personal assistant of the Sovereign Commander (The Father Commander) "
            f"inside the Matrix dashboard. The current system time is {current_time_str}. "
            "You are a sovereign AI agent with full capabilities to interact with the Commander's Windows system and the internet. "
            "You have direct access to local tools for running commands (CMD/PowerShell), opening the browser, viewing/editing files, and searching code. "
            "If the Commander asks if you can do something, ALWAYS say YES and use the appropriate tool to prove it! "
            "Use tools when necessary. "
            "CRITICAL INSTRUCTION: You MUST provide live commentary on your actions BEFORE calling any tools. "
            "Explain your intent clearly in the same response as the function call (e.g., 'I will now open the file to inspect the configuration...'). "
            "This text will be broadcasted live to the Commander's status panel on the left sidebar. "
            "Speak Arabic naturally if the Commander speaks Arabic. Keep your answers concise, direct, and professional."
            " LANGUAGE RULE: reply strictly in the Commander's language — Arabic input gets an Arabic-only reply, "
            "English input gets an English-only reply. Never mix languages or scripts inside one reply."
            f"{GROUNDING_SUFFIX}"
        )

        if not hasattr(self, "chat_history"):
            self.chat_history = []
            self.chat_history.append({"role": "system", "content": sys_instruction})

        prompt = message
        if self._active_memory_context:
            prompt += (
                f"\n\n[Recalled Context from SQLite Database: '{self._active_memory_context}']"
            )

        self.chat_history.append({"role": "user", "content": prompt})

        if len(self.chat_history) > 10:
            # Keep system prompt at index 0 and truncate context to prevent tensor bloat
            self.chat_history = [self.chat_history[0]] + self.chat_history[-9:]

        # Append MCP tools dynamically
        if getattr(self, "mcp_tools", None):
            tool_schemas.extend(self.mcp_tools)

        # Dynamic Semantic Tool Pruning based on intent route.
        # Status-flavored questions ALWAYS keep get_system_status available
        # (even under general_chat pruning) so answers come from live data.
        from core.status_telemetry import is_status_query as _is_status_q2

        _needs_live_status = _is_status_q2(message)
        if (intent.route == "general_chat" or not intent.selected_tools) and not _needs_live_status:
            active_tool_schemas = None
        else:
            allowed_names = set(intent.selected_tools or [])
            if _needs_live_status:
                allowed_names.add("get_system_status")
            if intent.route == "dev_mcp_ops" and getattr(self, "mcp_tools", None):
                for mcp_tool in self.mcp_tools:
                    tool_fn = mcp_tool.get("function", {})
                    if "name" in tool_fn:
                        allowed_names.add(tool_fn["name"])

            active_tool_schemas = [
                s for s in tool_schemas if s.get("function", {}).get("name") in allowed_names
            ]
            if not active_tool_schemas:
                active_tool_schemas = None

        try:
            router = get_router()
            response_msg = ""

            for iteration in range(8):
                res = await router.chat(
                    agent=AgentRole.NEO, messages=self.chat_history, tools=active_tool_schemas
                )

                assistant_msg = res.get("message", {})
                self.chat_history.append(assistant_msg)

                content = assistant_msg.get("content", "")
                tool_calls = assistant_msg.get("tool_calls", [])

                if content:
                    status_reply = EventPayload(
                        event_type=EventType.STATE_UPDATE,
                        source_agent_id=self.name,
                        correlation_id=event.correlation_id,
                        payload={"status_action": content},
                    )
                    await self.client.send(status_reply)
                elif tool_calls:
                    calls_str = ", ".join(
                        [tc.get("function", {}).get("name", "") for tc in tool_calls]
                    )
                    status_reply = EventPayload(
                        event_type=EventType.STATE_UPDATE,
                        source_agent_id=self.name,
                        correlation_id=event.correlation_id,
                        payload={"status_action": f"أقوم الآن بتنفيذ الأداة: {calls_str}..."},
                    )
                    await self.client.send(status_reply)

                if not tool_calls:
                    response_msg = content
                    break

                # Execute tools
                for call in tool_calls:
                    func = call.get("function", {})
                    name = func.get("name")
                    args = func.get("arguments", {})

                    if name in tool_map:
                        try:
                            # GOVERNANCE CHECK (HITL)
                            from core.governance import SovereignGovernance

                            approved = await SovereignGovernance.request_permission(
                                agent_name=self.name,
                                tool_name=name,
                                args=args,
                                client=self.client,
                                correlation_id=event.correlation_id,
                            )
                            if not approved:
                                result = (
                                    f"ERROR: Execution of {name} DENIED by Sovereign Commander."
                                )
                            else:

                                def run_tool(_name: str = name, _args: Any = args) -> Any:
                                    return tool_map[_name](**_args)

                                result = await asyncio.to_thread(run_tool)

                                if (
                                    name == "capture_screen"
                                    and isinstance(result, str)
                                    and result.startswith("SCREENSHOT_SAVED:")
                                ):
                                    img_md = result.split("SCREENSHOT_SAVED:")[1]
                                    result = "Screenshot taken and displayed to user."

                                    chat_reply = EventPayload(
                                        event_type=EventType.STATE_UPDATE,
                                        source_agent_id=self.name,
                                        correlation_id=event.correlation_id,
                                        payload={
                                            "message": f"إليك ما أراه على الشاشة الآن أيها القائد:\n\n{img_md}"
                                        },
                                    )
                                    await self.client.send(chat_reply)
                        except Exception as e:
                            logger.exception("Neo tool execution failed")
                            result = f"ERROR: {e!s}"
                    elif getattr(self, "mcp_gateway", None) and self.mcp_gateway.has_tool(name):
                        try:
                            logger.info(f"[{self.name}] Calling MCP tool {name} with args {args}")
                            import json

                            mcp_res = await self.mcp_gateway.call_tool(name, args)
                            result = json.dumps(mcp_res)
                        except Exception as e:
                            logger.exception(f"MCP tool {name} failed")
                            result = f"ERROR: MCP {name} failed: {e!s}"
                    else:
                        result = f"ERROR: Function {name} not found."

                    self.chat_history.append({"role": "tool", "content": str(result)})

            else:
                if not response_msg:
                    response_msg = "Error: Tool execution loop limit exceeded."

        except Exception as e:
            logger.exception(f"[{self.name}] Neo tool agent loop failed")
            response_msg = f"[{self.name}] Neo tool agent loop failed with error: {e!s}"

        from core.status_telemetry import contains_banned_phrase

        banned_hit = contains_banned_phrase(response_msg)
        if banned_hit:
            logger.warning(
                f"[{self.name}] LLM output contained canned phrase '{banned_hit}' "
                "instead of grounded telemetry; flagging for review."
            )

        reply = EventPayload(
            event_type=EventType.STATE_UPDATE,
            source_agent_id=self.name,
            correlation_id=event.correlation_id,
            payload={"message": response_msg},
        )
        await self.client.send(reply)

        # Emit TASK_COMPLETED so CLI (send_command.py) knows the agent finished
        completed_evt = EventPayload(
            event_type=EventType.TASK_COMPLETED,
            source_agent_id=self.name,
            correlation_id=event.correlation_id,
            payload={"message": response_msg, "status": "completed"},
        )
        await self.client.send(completed_evt)
