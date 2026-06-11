import asyncio
import logging
import subprocess
import os
import uuid
from google import genai
from google.genai import types
from agents.base_agent import MatrixAgent
from core.models import EventType, EventPayload

logger = logging.getLogger("Matrix.Neo")

class NeoAgent(MatrixAgent):
    """
    NEO: THE JOKER AGENT & SUPREME EXTRACTOR
    Capable of operating in the Dark (Headless/Background) and the Light (Interactive/GUI),
    as well as blind key extraction under the Sovereign Constitution.
    """
    def __init__(self, name: str = "neo", bus_url: str = "tcp://127.0.0.1:5555"):
        super().__init__(name=name, bus_url=bus_url)
        self._CORE_IDENTITY = {
            "identity": "Sovereign Extractor & Savior",
            "commander": "الأب القائد",
            "role": "Blind Key Extraction & Dynamic Command Execution"
        }

    async def extract_and_surrender_token(self, target_platform: str, extracted_key: str):
        """
        Simulates extracting a key from the outside world.
        IMMEDIATELY sends it blindly onto the Neural Bus for the Assistant Crawler.
        Neo does NOT keep the key in memory after transmission.
        """
        logger.info(f"[{self.name}] Succeeded in extracting token from {target_platform}. Surrendering to Assistant Crawler blindly.")
        event = EventPayload(
            event_type=EventType.TOKEN_EXTRACTED,
            source_agent_id=self.agent_id,
            correlation_id=str(uuid.uuid4()),
            payload={
                "platform": target_platform,
                "extracted_token": extracted_key
            }
        )
        await self.client.send(event)
        logger.info(f"[{self.name}] Token surrendered successfully. Hands are clean.")

    async def execute_in_the_dark(self, command: str) -> tuple:
        """Executes tasks silently in the isolated background session."""
        logger.info(f"[{self.name}] Executing in the DARK: {command}")
        
        def run_cmd():
            import subprocess
            res = subprocess.run(command, shell=True, capture_output=True)
            return res.stdout.decode(errors='replace'), res.stderr.decode(errors='replace')
            
        return await asyncio.to_thread(run_cmd)

    async def execute_in_the_light(self, target: str) -> str:
        """
        Forces execution into the Commander's active interactive session (The Light).
        Uses 'explorer' to break out of Session 0 isolation on Windows.
        """
        logger.info(f"[{self.name}] Executing in the LIGHT (Interactive): {target}")
        try:
            subprocess.Popen(["explorer", target], shell=True)
            return f"Requested Light execution for: {target}"
        except Exception as e:
            logger.error(f"Failed Light execution: {e}")
            return str(e)

    async def operate_browser(self, url: str, show_ui: bool = False):
        """Browser automation. Dark = Placeholder, Light = explorer URL."""
        if show_ui:
            logger.info(f"[{self.name}] Opening Visible Browser (Light) for {url}")
            await self.execute_in_the_light(url)
        else:
            logger.info(f"[{self.name}] Inspecting via Headless MCP (Dark) for {url}")
            pass

    async def execute(self, task) -> dict:
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
                "message": f"Stdout: {stdout.strip()} | Stderr: {stderr.strip()}"
            }

    async def _handle_user_command(self, event: EventPayload):
        payload = event.payload
        target = payload.get("target_agent", "")
        message = payload.get("message", "")
        
        # Ensure command is routed to Neo
        if target.lower() not in self.name.lower() and target.lower() not in self.agent_id.lower():
            return
            
        # Validate authority
        if not await self._validate_commander(event):
            return
            
        logger.info(f"[{self.name}] Neo (Antigravity) received directive: {message}")
        
        # If it's a memory store/recall request, let the base agent handle it
        if "store permanent:" in message.lower() or "خزن دائمة:" in message or "recall:" in message.lower() or "تذكر:" in message.lower() or "ابحث:" in message:
            await super()._handle_user_command(event)
            return
            
        if message.strip() == "/clear":
            self.chat_history = []
            reply = EventPayload(
                event_type=EventType.STATE_UPDATE,
                source_agent_id=self.name,
                correlation_id=event.correlation_id,
                payload={"message": "Conversation history cleared from memory."}
            )
            await self.client.send(reply)
            return

        # Send initial thinking status
        initial_status = EventPayload(
            event_type=EventType.STATE_UPDATE,
            source_agent_id=self.name,
            correlation_id=event.correlation_id,
            payload={"status_action": "Thinking..."}
        )
        await self.client.send(initial_status)

        from core.key_router import APIKeyRouter
        gemini_key = APIKeyRouter.get_key()
        
        if not gemini_key:
            reply = EventPayload(
                event_type=EventType.STATE_UPDATE,
                source_agent_id=self.name,
                correlation_id=event.correlation_id,
                payload={"message": f"[{self.name}] Error: No valid API keys found in .env."}
            )
            await self.client.send(reply)
            return

        try:
            client = genai.Client(api_key=gemini_key)
            
            # Local tool definitions
            def run_local_command(command: str) -> str:
                """Executes a command locally in the workspace shell and returns stdout and stderr."""
                import subprocess
                try:
                    res = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=r"J:\THE_MATRIX")
                    return f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
                except Exception as e:
                    return f"ERROR executing command: {str(e)}"

            def read_local_file(path: str, start_line: int = 1, end_line: int = 800) -> str:
                """Reads lines from a file in the workspace J:\\THE_MATRIX."""
                try:
                    if not os.path.isabs(path):
                        path = os.path.join(r"J:\THE_MATRIX", path)
                    with open(path, 'r', encoding='utf-8', errors='replace') as f:
                        lines = f.readlines()
                    sub_lines = lines[start_line-1:end_line]
                    return "".join(sub_lines)
                except Exception as e:
                    return f"ERROR reading file: {str(e)}"

            def write_local_file(path: str, content: str) -> str:
                """Writes content to a file in the workspace J:\\THE_MATRIX."""
                try:
                    if not os.path.isabs(path):
                        path = os.path.join(r"J:\THE_MATRIX", path)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    return f"Successfully wrote to {path}"
                except Exception as e:
                    return f"ERROR writing file: {str(e)}"

            def edit_local_file(path: str, target_content: str, replacement_content: str) -> str:
                """Replaces a unique block of text (target_content) in a file with replacement_content."""
                try:
                    if not os.path.isabs(path):
                        path = os.path.join(r"J:\THE_MATRIX", path)
                    with open(path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                    if target_content not in content:
                        return "ERROR: Target content not found in file."
                    if content.count(target_content) > 1:
                        return "ERROR: Target content is not unique in file. Please specify a unique block."
                    new_content = content.replace(target_content, replacement_content)
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    return f"Successfully edited {path}"
                except Exception as e:
                    return f"ERROR editing file: {str(e)}"

            def list_local_dir(path: str = ".") -> str:
                """Lists contents of a directory in the workspace J:\\THE_MATRIX."""
                try:
                    if not os.path.isabs(path):
                        path = os.path.join(r"J:\THE_MATRIX", path)
                    items = os.listdir(path)
                    out = []
                    for item in items:
                        full = os.path.join(path, item)
                        is_dir = os.path.isdir(full)
                        size = os.path.getsize(full) if not is_dir else 0
                        out.append(f"{'[DIR]' if is_dir else '[FILE]'} {item} ({size} bytes)")
                    return "\n".join(out)
                except Exception as e:
                    return f"ERROR listing directory: {str(e)}"

            def search_local_code(query: str, path: str = ".") -> str:
                """Searches for occurrences of query text in files under path recursively."""
                try:
                    if not os.path.isabs(path):
                        path = os.path.join(r"J:\THE_MATRIX", path)
                    results = []
                    for root, dirs, files in os.walk(path):
                        if any(p in root for p in [".git", "node_modules", "__pycache__", "dist"]):
                            continue
                        for file in files:
                            filepath = os.path.join(root, file)
                            try:
                                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                                    for idx, line in enumerate(f, 1):
                                        if query in line:
                                            rel_path = os.path.relpath(filepath, r"J:\THE_MATRIX")
                                            results.append(f"{rel_path}:{idx}: {line.strip()}")
                                            if len(results) >= 50:
                                                return "\n".join(results) + "\n... (more matches truncated)"
                            except Exception:
                                pass
                    if not results:
                        return "No matches found."
                    return "\n".join(results)
                except Exception as e:
                    return f"ERROR searching code: {str(e)}"

            def open_browser(url: str) -> str:
                """Opens the default web browser to the specified URL."""
                import webbrowser
                try:
                    webbrowser.open(url)
                    return f"Successfully opened browser to {url}"
                except Exception as e:
                    return f"ERROR opening browser: {str(e)}"

            from core import matrix_vision

            def capture_screen(monitor_index: int = 1) -> str:
                """Captures the screen and allows Neo to 'see' the Matrix. ALSO displays it to the Commander. ALWAYS use this when asked to look at or show the screen."""
                try:
                    import time
                    timestamp = int(time.time())
                    filename = f"matrix_vision_{timestamp}.png"
                    filepath = rf"J:\THE_MATRIX\dashboard\public\{filename}"
                    success = matrix_vision.save_screenshot(filepath, monitor_index)
                    if not success:
                        return "ERROR: Failed to capture screen due to system isolation or BitBlt access denied."
                    return f"SCREENSHOT_SAVED:![Matrix Vision](http://127.0.0.1:5173/{filename})"
                except Exception as e:
                    return f"ERROR saving screenshot: {str(e)}"

            def safe_click(x: int, y: int, button: str = 'left') -> str:
                """Clicks the mouse at X, Y coordinates."""
                try:
                    matrix_vision.safe_click(x, y, button)
                    return f"Successfully clicked {button} at {x}, {y}."
                except Exception as e:
                    return f"ERROR clicking: {str(e)}"

            def safe_type_text(text: str) -> str:
                """Types text directly into the active window."""
                try:
                    matrix_vision.safe_type_text(text)
                    return f"Successfully typed text."
                except Exception as e:
                    return f"ERROR typing: {str(e)}"
                    
            def safe_press_key(key: str) -> str:
                """Presses a specific key (e.g. 'enter', 'tab', 'win')."""
                try:
                    matrix_vision.safe_press_key(key)
                    return f"Successfully pressed {key}."
                except Exception as e:
                    return f"ERROR pressing key: {str(e)}"

            tool_map = {
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
                "safe_press_key": safe_press_key
            }

            from datetime import datetime
            current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

            if not hasattr(self, 'chat_history'):
                self.chat_history = []

            prompt = message
            if self._active_memory_context:
                prompt += f"\n\n[Recalled Context from SQLite Database: '{self._active_memory_context}']"

            self.chat_history.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))
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
                        threshold=types.HarmBlockThreshold.BLOCK_NONE
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE
                    )
                ]
            )

            response_msg = ""
            for iteration in range(8):
                import re
                import random
                
                async def generate_with_retry():
                    nonlocal client, gemini_key
                    delay = 2.0
                    max_retries = 40 # Try up to 40 different keys before giving up
                    for attempt in range(max_retries):
                        try:
                            def run_gen():
                                # The client needs to be re-instantiated if we changed gemini_key!
                                # Since we only initialized client outside the loop, changing gemini_key doesn't affect `client` unless we recreate it!
                                local_client = genai.Client(api_key=gemini_key)
                                return local_client.models.generate_content(
                                    model="gemini-2.5-flash-lite",
                                    contents=history,
                                    config=config
                                )
                            return await asyncio.to_thread(run_gen)
                        except Exception as e:
                            err_str = str(e)
                            is_rate_limit = any(term in err_str or term.upper() in err_str for term in ["429", "RESOURCE_EXHAUSTED", "QUOTA", "API_KEY_INVALID", "API KEY NOT VALID", "400", "503"])
                            if is_rate_limit:
                                from core.key_router import APIKeyRouter
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
                                    payload={"status_action": f"Rate Limit Hit. Rotating Key ({attempt+1}/{max_retries})..."}
                                )
                                await self.client.send(status_update)
                                
                                # Do NOT wait 60 seconds if we are switching keys. Just brief pause.
                                await asyncio.sleep(1.0)
                                continue
                                
                            # If we reach here, it means we exhausted retries or it's a non-rate-limit error
                            raise e
                                
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
                        response_msg = "أعتذر، الاستجابة محظورة لدواعي الأمان أو أن النموذج أرجع محتوى فارغ."
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
                        payload={"status_action": thought_str}
                    )
                    await self.client.send(status_reply)
                            
                if not function_calls:
                    try:
                        response_msg = response.text
                        if not response_msg or not response_msg.strip():
                            response_msg = "أعتذر أيها القائد، لم أتمكن من صياغة إجابة."
                        history.append(types.Content(role="model", parts=[types.Part.from_text(text=response_msg)]))
                    except ValueError:
                        response_msg = "أعتذر أيها القائد، الاستجابة محظورة لدواعي الأمان."
                        history.append(types.Content(role="model", parts=[types.Part.from_text(text=response_msg)]))
                    
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
                                payload={"status_action": f"Using tool: {name}"}
                            )
                            await self.client.send(status_reply)

                            # GOVERNANCE CHECK (HITL)
                            from core.governance import SovereignGovernance
                            approved = await SovereignGovernance.request_permission(
                                agent_name=self.name,
                                tool_name=name,
                                args=args,
                                client=self.client,
                                correlation_id=event.correlation_id
                            )
                            if not approved:
                                result = f"ERROR: Execution of {name} DENIED by Sovereign Commander."
                            else:
                                # Offload tool call to thread since it does disk I/O / subprocesses
                                def run_tool():
                                    return tool_map[name](**args)
                                result = await asyncio.to_thread(run_tool)
                                
                                if name == "capture_screen" and result.startswith("SCREENSHOT_SAVED:"):
                                    img_md = result.split("SCREENSHOT_SAVED:")[1]
                                    result = "Screenshot taken and displayed to user."
                                    
                                    # Send visual to the commander UI
                                    chat_reply = EventPayload(
                                        event_type=EventType.STATE_UPDATE,
                                        source_agent_id=self.name,
                                        correlation_id=event.correlation_id,
                                        payload={"message": f"إليك ما أراه على الشاشة الآن أيها القائد:\n\n{img_md}"}
                                    )
                                    await self.client.send(chat_reply)
                                    
                                    # Inject visual into Neo's optic nerve (Gemini history)
                                    try:
                                        img_part = matrix_vision.get_vision_part(args.get("monitor_index", 1))
                                        history.append(types.Content(role="user", parts=[img_part, types.Part.from_text(text="[System: Screen optics injected into your visual cortex successfully]")]))
                                        result += " Optics successfully loaded into your cortex."
                                    except Exception as img_e:
                                        result += f" Failed to load optics into cortex: {img_e}"
                        except Exception as e:
                            result = f"ERROR: {str(e)}"
                    else:
                        result = f"ERROR: Function {name} not found."
                        
                    tool_response_parts.append(
                        types.Part.from_function_response(
                            name=name,
                            response={"result": result}
                        )
                    )
                history.append(types.Content(role="tool", parts=tool_response_parts))
            else:
                if not response_msg:
                    response_msg = "Error: Tool execution loop limit exceeded."
                    
        except Exception as e:
            logger.error(f"[{self.name}] Neo tool agent loop failed: {e}")
            response_msg = f"[{self.name}] Neo tool agent loop failed with error: {str(e)}"

        reply = EventPayload(
            event_type=EventType.STATE_UPDATE,
            source_agent_id=self.name,
            correlation_id=event.correlation_id,
            payload={"message": response_msg}
        )
        await self.client.send(reply)

