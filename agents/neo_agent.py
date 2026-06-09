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

        gemini_key = os.getenv("NEO_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            reply = EventPayload(
                event_type=EventType.STATE_UPDATE,
                source_agent_id=self.name,
                correlation_id=event.correlation_id,
                payload={"message": f"[{self.name}] Error: NEO_API_KEY or GEMINI_API_KEY is missing."}
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

            tool_map = {
                "run_local_command": run_local_command,
                "read_local_file": read_local_file,
                "write_local_file": write_local_file,
                "edit_local_file": edit_local_file,
                "list_local_dir": list_local_dir,
                "search_local_code": search_local_code
            }

            sys_instruction = (
                "You are Neo (Antigravity), the personal assistant of the Sovereign Commander (Dr. Anas Hilal) "
                "inside the Matrix dashboard. You are a highly advanced AI coding assistant and system engineer. "
                "You have direct access to local tools for running commands, viewing/editing files, and searching code. "
                "You MUST use these tools to analyze issues, modify files, and solve the Commander's coding tasks. "
                "Keep your answers concise, direct, and professional."
            )

            prompt = message
            if self._active_memory_context:
                prompt += f"\n\n[Recalled Context from SQLite Database: '{self._active_memory_context}']"

            history = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
            
            config = types.GenerateContentConfig(
                system_instruction=sys_instruction,
                max_output_tokens=1500,
                temperature=0.7,
                tools=list(tool_map.values())
            )

            response_msg = ""
            for iteration in range(8):
                def run_gen():
                    return client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=history,
                        config=config
                    )
                response = await asyncio.to_thread(run_gen)
                
                assistant_content = response.candidates[0].content
                if not assistant_content.role:
                    assistant_content.role = "model"
                history.append(assistant_content)
                
                function_calls = []
                if assistant_content.parts:
                    for part in assistant_content.parts:
                        if part.function_call:
                            function_calls.append(part.function_call)
                            
                if not function_calls:
                    response_msg = response.text
                    break
                    
                tool_response_parts = []
                for call in function_calls:
                    name = call.name
                    args = call.args
                    
                    if name in tool_map:
                        try:
                            # Offload tool call to thread since it does disk I/O / subprocesses
                            def run_tool():
                                return tool_map[name](**args)
                            result = await asyncio.to_thread(run_tool)
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

