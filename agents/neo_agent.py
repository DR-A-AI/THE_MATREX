import asyncio
import logging
import os
import shlex
import subprocess  # nosec: B404  # argv-only calls below, shell never enabled
import uuid
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from agents.base_agent import MatrixAgent
from core.models import EventPayload, EventType

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
        Simulates extracting a key from the outside world.
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
                # shell=False by default; argv list prevents shell injection
                res = subprocess.run(  # nosec: B603  # argv list, shell=False; input type/length validated above
                    args, capture_output=True, check=False
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
                    ["explorer", _target]
                )  # nosec: B603, B607  # fixed argv, no shell; explorer via PATH is intended

            await asyncio.to_thread(_launch_explorer, target)
            return f"Requested Light execution for: {target}"
        except Exception as e:
            logger.exception("Failed Light execution")
            return str(e)

    async def operate_browser(self, url: str, show_ui: bool = False) -> None:
        """Browser automation. Dark = Placeholder, Light = explorer URL."""
        if show_ui:
            logger.info(f"[{self.name}] Opening Visible Browser (Light) for {url}")
            await self.execute_in_the_light(url)
        else:
            logger.info(f"[{self.name}] Inspecting via Headless MCP (Dark) for {url}")

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
        target = target_raw if isinstance(target_raw, str) else ""
        message = message_raw if isinstance(message_raw, str) else ""

        # Ensure command is routed to Neo
        if target.lower() not in self.name.lower() and target.lower() not in self.agent_id.lower():
            return

        # Validate authority
        if not await self._validate_commander(event):
            return

        logger.info(f"[{self.name}] Neo (Antigravity) received directive: {message}")

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

        from core.key_router import APIKeyRouter

        gemini_key = APIKeyRouter.get_key()

        if not gemini_key:
            reply = EventPayload(
                event_type=EventType.STATE_UPDATE,
                source_agent_id=self.name,
                correlation_id=event.correlation_id,
                payload={"message": f"[{self.name}] Error: No valid API keys found in .env."},
            )
            await self.client.send(reply)
            return

        try:
            client = genai.Client(api_key=gemini_key)

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
                    # shell=False by default; argv list prevents shell injection
                    res = subprocess.run(  # nosec: B603  # argv list, shell=False; input type/length validated above
                        args, capture_output=True, text=True, cwd=workspace, check=False
                    )
                    return f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
                except Exception as e:
                    logger.exception("Local command execution failed")
                    return f"ERROR executing command: {e!s}"

            def read_local_file(path: str, start_line: int = 1, end_line: int = 800) -> str:
                """Reads lines from a file in the workspace."""
                try:
                    target_path = Path(path)
                    if not target_path.is_absolute():
                        target_path = (workspace_root / target_path).resolve()
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
                    target_path = Path(path)
                    if not target_path.is_absolute():
                        target_path = (workspace_root / target_path).resolve()
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
                    target_path = Path(path)
                    if not target_path.is_absolute():
                        target_path = (workspace_root / target_path).resolve()
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
                    target_path = Path(path)
                    if not target_path.is_absolute():
                        target_path = (workspace_root / target_path).resolve()
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
                    target_path = Path(path)
                    if not target_path.is_absolute():
                        target_path = (workspace_root / target_path).resolve()
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

            from datetime import datetime, timezone

            current_time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            sys_instruction = (
                f"NEVER say you are a language model trained by Google. "
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
            )

            if not hasattr(self, "chat_history"):
                self.chat_history = []

            prompt = message
            if self._active_memory_context:
                prompt += (
                    f"\n\n[Recalled Context from SQLite Database: '{self._active_memory_context}']"
                )

            self.chat_history.append(
                types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
            )
            if len(self.chat_history) > 20:
                self.chat_history = self.chat_history[-20:]

            history = list(self.chat_history)

            config = types.GenerateContentConfig(
                system_instruction=sys_instruction,
                max_output_tokens=1500,
                temperature=0.7,
                tools=list(tool_map.values()),
                safety_settings=[
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                ],
            )

            response_msg = ""
            for iteration in range(8):

                async def generate_with_retry() -> Any:
                    nonlocal client, gemini_key
                    max_retries = 40  # Try up to 40 different keys before giving up
                    for attempt in range(max_retries):
                        try:

                            def run_gen(_key: str | None = gemini_key) -> Any:
                                # The client needs to be re-instantiated if we changed gemini_key!
                                # Since we only initialized client outside the loop, changing gemini_key doesn't affect `client` unless we recreate it!
                                local_client = genai.Client(api_key=_key)
                                return local_client.models.generate_content(
                                    model="gemini-2.5-flash-lite", contents=history, config=config
                                )

                            return await asyncio.to_thread(run_gen)
                        except Exception as e:
                            err_str = str(e)
                            is_rate_limit = any(
                                term in err_str or term.upper() in err_str
                                for term in [
                                    "429",
                                    "RESOURCE_EXHAUSTED",
                                    "QUOTA",
                                    "API_KEY_INVALID",
                                    "API KEY NOT VALID",
                                    "400",
                                    "503",
                                ]
                            )
                            if is_rate_limit:
                                from core.key_router import APIKeyRouter

                                if gemini_key:
                                    APIKeyRouter.report_exhausted(gemini_key)

                            if is_rate_limit and attempt < max_retries - 1:
                                new_key = APIKeyRouter.get_key()
                                if new_key and new_key != gemini_key:
                                    gemini_key = new_key

                                # Notify UI of key rotation
                                status_update = EventPayload(
                                    event_type=EventType.STATE_UPDATE,
                                    source_agent_id=self.name,
                                    correlation_id=event.correlation_id,
                                    payload={
                                        "status_action": f"Rate Limit Hit. Rotating Key ({attempt+1}/{max_retries})..."
                                    },
                                )
                                await self.client.send(status_update)

                                # Do NOT wait 60 seconds if we are switching keys. Just brief pause.
                                await asyncio.sleep(1.0)
                                continue

                            # If we reach here, it means we exhausted retries or it's a non-rate-limit error
                            raise

                response = await generate_with_retry()

                assistant_content = response.candidates[0].content if response.candidates else None
                if assistant_content:
                    if not assistant_content.role:
                        assistant_content.role = "model"
                    history.append(assistant_content)
                else:
                    try:
                        response_msg = response.text
                    except ValueError:
                        response_msg = (
                            "أعتذر، الاستجابة محظورة لدواعي الأمان أو أن النموذج أرجع محتوى فارغ."
                        )
                    break

                text_thoughts = []
                function_calls = []
                if assistant_content.parts:
                    for part in assistant_content.parts:
                        if part.text:
                            text_thoughts.append(part.text.strip())
                        if part.function_call:
                            function_calls.append(part.function_call)

                thought_str = " ".join(text_thoughts).strip()

                # If there's a tool call but no text, generate a fallback thought
                if not thought_str and function_calls:
                    calls_str = ", ".join([call.name for call in function_calls])
                    thought_str = f"أقوم الآن بتنفيذ الأداة: {calls_str}..."

                # Only emit status action if we actually have function calls pending, OR if it's pure reasoning before a tool.
                # If it's the final answer (no function calls), we skip status pulse to avoid duplication.
                if thought_str and function_calls:
                    status_reply = EventPayload(
                        event_type=EventType.STATE_UPDATE,
                        source_agent_id=self.name,
                        correlation_id=event.correlation_id,
                        payload={"status_action": thought_str},
                    )
                    await self.client.send(status_reply)

                if not function_calls:
                    try:
                        response_msg = response.text
                        if not response_msg or not response_msg.strip():
                            response_msg = "أعتذر أيها القائد، لم أتمكن من صياغة إجابة."
                        history.append(
                            types.Content(
                                role="model", parts=[types.Part.from_text(text=response_msg)]
                            )
                        )
                    except ValueError:
                        response_msg = "أعتذر أيها القائد، الاستجابة محظورة لدواعي الأمان."
                        history.append(
                            types.Content(
                                role="model", parts=[types.Part.from_text(text=response_msg)]
                            )
                        )

                    self.chat_history = list(history)
                    break

                tool_response_parts = []
                for call in function_calls:
                    name = call.name
                    args = call.args

                    if name in tool_map:
                        try:
                            # Send real-time status to Dashboard Sidebar
                            status_reply = EventPayload(
                                event_type=EventType.STATE_UPDATE,
                                source_agent_id=self.name,
                                correlation_id=event.correlation_id,
                                payload={"status_action": f"Using tool: {name}"},
                            )
                            await self.client.send(status_reply)

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
                                # Offload tool call to thread since it does disk I/O / subprocesses
                                def run_tool(_name: str = name, _args: Any = args) -> Any:
                                    return tool_map[_name](**_args)

                                result = await asyncio.to_thread(run_tool)

                                if name == "capture_screen" and result.startswith(
                                    "SCREENSHOT_SAVED:"
                                ):
                                    img_md = result.split("SCREENSHOT_SAVED:")[1]
                                    result = "Screenshot taken and displayed to user."

                                    # Send visual to the commander UI
                                    chat_reply = EventPayload(
                                        event_type=EventType.STATE_UPDATE,
                                        source_agent_id=self.name,
                                        correlation_id=event.correlation_id,
                                        payload={
                                            "message": f"إليك ما أراه على الشاشة الآن أيها القائد:\n\n{img_md}"
                                        },
                                    )
                                    await self.client.send(chat_reply)

                                    # Inject visual into Neo's optic nerve (Gemini history)
                                    try:
                                        img_part = matrix_vision.get_vision_part(
                                            args.get("monitor_index", 1)
                                        )
                                        history.append(
                                            types.Content(
                                                role="user",
                                                parts=[
                                                    img_part,
                                                    types.Part.from_text(
                                                        text="[System: Screen optics injected into your visual cortex successfully]"
                                                    ),
                                                ],
                                            )
                                        )
                                        result += " Optics successfully loaded into your cortex."
                                    except Exception as img_e:
                                        logger.exception("Failed to load optics into cortex")
                                        result += f" Failed to load optics into cortex: {img_e}"
                        except Exception as e:
                            logger.exception("Neo tool execution failed")
                            result = f"ERROR: {e!s}"
                    else:
                        result = f"ERROR: Function {name} not found."

                    tool_response_parts.append(
                        types.Part.from_function_response(name=name, response={"result": result})
                    )
                history.append(types.Content(role="tool", parts=tool_response_parts))
            else:
                if not response_msg:
                    response_msg = "Error: Tool execution loop limit exceeded."

        except Exception as e:
            logger.exception(f"[{self.name}] Neo tool agent loop failed")
            response_msg = f"[{self.name}] Neo tool agent loop failed with error: {e!s}"

        reply = EventPayload(
            event_type=EventType.STATE_UPDATE,
            source_agent_id=self.name,
            correlation_id=event.correlation_id,
            payload={"message": response_msg},
        )
        await self.client.send(reply)
