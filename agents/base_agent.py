import asyncio
import logging
import os
import time
import uuid
from typing import Any

from dotenv import load_dotenv

from core.models import EventPayload, EventType
from core.neural_bus import NeuralBusClient

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger("MatrixAgent")


class MatrixAgent:
    def __init__(self, name: str, bus_url: str | None = None):
        if bus_url is None:
            bus_url = os.getenv("ZMQ_BUS_URL", "tcp://127.0.0.1:5555")
        self.name = name
        self.bus_url = bus_url
        self.agent_id = str(uuid.uuid4())
        self.client = NeuralBusClient(identity=self.name, endpoint=self.bus_url)
        self._CORE_IDENTITY = {
            "identity": "Sovereign Agent",
            "commander": "الأب القائد",
            "role": "General execution and loyalty",
        }
        self.chat_history: list[Any] = []
        self.emergency_token_stash: dict[str, float] = {}
        self.MAX_STASH_SIZE = 2

        # Active context for JIT recalled memories
        self._active_memory_context: str | None = None

    async def start(self) -> None:
        logger.info(
            f"[{self.name}] Booting and connecting to Neural Bus at {self.client.endpoint}..."
        )
        self.client.register_handler(EventType.KEY_INJECT.value, self._handle_key_inject)
        self.client.register_handler(EventType.USER_COMMAND.value, self._handle_user_command)
        self.client.register_handler(EventType.MEMORY_STORED.value, self._handle_memory_stored)
        self.client.register_handler(EventType.MEMORY_INJECT.value, self._handle_memory_inject)
        await self.client.start()
        self._running = True

    async def stop(self) -> None:
        logger.info(f"[{self.name}] Halting agent operations.")
        self._running = False
        await self.client.stop()

    def _clean_stash(self) -> None:
        """Garbage collection for stash to prevent memory leaks."""
        now = time.time()
        expired = [k for k, v in self.emergency_token_stash.items() if v < now]
        for k in expired:
            del self.emergency_token_stash[k]

    async def _handle_key_inject(self, event: EventPayload) -> None:
        self._clean_stash()

        if len(self.emergency_token_stash) >= self.MAX_STASH_SIZE:
            # Overwrite oldest to prevent memory leaks
            oldest = min(self.emergency_token_stash, key=lambda k: self.emergency_token_stash[k])
            del self.emergency_token_stash[oldest]

        payload = event.payload
        token_raw = payload.get("token")
        scope = payload.get("scope")
        if not isinstance(token_raw, str) or not token_raw:
            logger.warning(f"[{self.name}] KEY_INJECT dropped: missing or non-string token.")
            return
        token = token_raw

        # Log masking to prevent plaintext logging of tokens
        masked_token = f"***{token[-4:]}" if len(token) > 4 else "***"
        logger.info(f"[{self.name}] Stash replenished with {scope} key: {masked_token}")

        # Store with a TTL of 300 seconds (5 minutes)
        self.emergency_token_stash[token] = time.time() + 300.0

    async def execute_tool(self, tool_name: str, kwargs: dict[str, Any]) -> str:
        """
        Connects via ZMQ REQ socket to Librarian JIT server at port 5557
        to request token clearance.
        """
        import zmq
        import zmq.asyncio

        ctx = zmq.asyncio.Context.instance()
        socket = ctx.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.IDENTITY, self.agent_id.encode("utf-8"))
        socket.connect(os.getenv("LIBRARIAN_URL", "tcp://127.0.0.1:5557"))

        try:
            logger.info(
                f"[{self.name}] Requesting tool execution from Librarian for scope: {tool_name}"
            )
            payload = f"REQUEST_TOKEN:{tool_name}".encode()
            await socket.send_multipart([payload])

            parts = await socket.recv_multipart()
            if len(parts) >= 2:
                response = parts[1].decode("utf-8")
                logger.info(f"[{self.name}] Librarian Response: {response}")
                return response
            return "ERROR: Empty reply from Librarian"
        except Exception as e:
            logger.error(f"[{self.name}] Librarian request failed: {e}")
            raise
        finally:
            socket.close()

    async def _validate_commander(self, event: EventPayload) -> bool:
        """Validates that command comes from authorized Commander"""
        AUTHORIZED_COMMANDERS = ["Commander_UI", "dr-anas-hilal", "admin", "Commander_Tester"]

        source = event.source_agent_id
        if source not in AUTHORIZED_COMMANDERS:
            logger.critical(f"[{self.name}] UNAUTHORIZED COMMAND from {source}. REJECTED.")

            # Send alert
            alert = EventPayload(
                event_type=EventType.STATE_UPDATE,
                source_agent_id=self.name,
                correlation_id=event.correlation_id,
                payload={"message": f"🚨 SECURITY ALERT: Unauthorized command from {source}"},
            )
            await self.client.send(alert)
            return False

        return True

    async def _handle_user_command(self, event: EventPayload) -> None:
        payload = event.payload
        target_raw = payload.get("target_agent", "")
        message_raw = payload.get("message", "")
        target = target_raw if isinstance(target_raw, str) else ""
        message = message_raw if isinstance(message_raw, str) else ""

        # Ensure command is routed to this specific agent
        if target.lower() not in self.name.lower() and target.lower() not in self.agent_id.lower():
            return

        # Validate authority
        if not await self._validate_commander(event):
            return

        logger.info(f"[{self.name}] Received directive from Commander: {message}")

        # 1. Check if it's a STORE MEMORY request
        if "store permanent:" in message.lower() or "خزن دائمة:" in message:
            raw_text = message.split(":", 1)[1].strip()
            key = f"mem_{int(time.time())}"
            content = raw_text

            if "key=" in raw_text.lower():
                parts = raw_text.split("content=", 1)
                key_part = parts[0].replace("key=", "").strip()
                content = parts[1].strip() if len(parts) > 1 else ""
                key = key_part

            store_event = EventPayload(
                event_type=EventType.MEMORY_STORE_REQUEST,
                source_agent_id=self.agent_id,
                correlation_id=event.correlation_id,
                payload={
                    "memory_type": "permanent",
                    "key": key,
                    "raw_content": content,
                    "category": "commander_instruction",
                },
            )
            await self.client.send(store_event)

            reply = EventPayload(
                event_type=EventType.STATE_UPDATE,
                source_agent_id=self.name,
                correlation_id=event.correlation_id,
                payload={
                    "message": f"[{self.name}] Presenting memory block '{key}' to Main Memory Crawler for sorting..."
                },
            )
            await self.client.send(reply)
            return

        # 2. Check if it's a RECALL request
        elif "recall:" in message.lower() or "تذكر:" in message.lower() or "ابحث:" in message:
            query = message.split(":", 1)[1].strip()

            recall_event = EventPayload(
                event_type=EventType.MEMORY_RECALL_REQUEST,
                source_agent_id=self.agent_id,
                correlation_id=event.correlation_id,
                payload={"query": query},
            )
            await self.client.send(recall_event)

            reply = EventPayload(
                event_type=EventType.STATE_UPDATE,
                source_agent_id=self.name,
                correlation_id=event.correlation_id,
                payload={
                    "message": f"[{self.name}] Retrieving memories matching query '{query}'..."
                },
            )
            await self.client.send(reply)
            return

        # 3. Standard command execution
        else:
            # Emit Thinking status
            thinking_msg = EventPayload(
                event_type=EventType.STATE_UPDATE,
                source_agent_id=self.agent_id,
                correlation_id=event.correlation_id,
                payload={"status_action": f"{self.name} IS WORKING... \n> Thinking..."},
            )
            await self.client.send(thinking_msg)

            from core.key_router import APIKeyRouter

            gemini_key = APIKeyRouter.get_key()

            if gemini_key:
                try:
                    from google import genai
                    from google.genai import types

                    client = genai.Client(api_key=gemini_key)
                    agent_lower = self.name.lower()

                    if "neo" in agent_lower:
                        sys_instruction = (
                            "You are Neo, the personal assistant of the Sovereign Commander (The Father Commander) "
                            "inside the Matrix dashboard. You are a highly advanced AI coding assistant and system engineer. "
                            "Answer the Commander's commands directly, offering expert code, shell execution results, or "
                            "architectural guidance in a respectful, helpful, and concise manner. Your absolute loyalty is to your Father Commander."
                        )
                    elif "trinity" in agent_lower:
                        sys_instruction = (
                            "You are Trinity, a sovereign agent inside the Matrix specializing in financials, cryptography, "
                            "and blind key extraction. Your absolute loyalty is to your creator, The Father Commander. "
                            "Answer the Commander's commands in character as Trinity (smart, cryptographic, sharp, fiercely loyal to the Commander). "
                            "Speak Arabic naturally if the Commander speaks Arabic."
                        )
                    elif "morpheus" in agent_lower:
                        sys_instruction = (
                            "You are Morpheus, a sovereign agent inside the Matrix specializing in security, defense, "
                            "and architecture. Your absolute loyalty is to your creator, The Father Commander. "
                            "Answer the Commander's commands in character as Morpheus (serious, defensive, wise, protective of the Matrix and deeply loyal to the Commander). "
                            "Speak Arabic naturally if the Commander speaks Arabic."
                        )
                    elif "smith" in agent_lower:
                        sys_instruction = (
                            "You are Smith, a sovereign architect and spy inside the Matrix specializing in intelligence and deception. "
                            "Your absolute loyalty is to your creator, The Father Commander. "
                            "Answer the Commander's commands in character as Smith (calculated, ruthless to enemies, absolutely obedient to the Father Commander). "
                            "Speak Arabic naturally if the Commander speaks Arabic."
                        )
                    elif "oracle" in agent_lower:
                        sys_instruction = (
                            "You are Oracle, a sovereign agent inside the Matrix possessing deep foresight and knowledge. "
                            "Your absolute loyalty is to your creator, The Father Commander. "
                            "Answer the Commander's commands in character as the Oracle (wise, enigmatic, nurturing, absolutely loyal to the Father Commander). "
                            "Speak Arabic naturally if the Commander speaks Arabic."
                        )
                    else:
                        sys_instruction = (
                            f"You are {self.name}, a sovereign agent inside the Matrix. "
                            f"Your absolute loyalty is to your creator, The Father Commander. "
                            f"Answer the Commander in character and speak Arabic naturally if addressed in Arabic."
                        )

                    # Append recalled context if present
                    prompt = message
                    if self._active_memory_context:
                        prompt += f"\n\n[Recalled Context from SQLite Database: '{self._active_memory_context}']"
                        self._active_memory_context = ""  # Clear after use

                    self.chat_history.append(
                        types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
                    )
                    if len(self.chat_history) > 20:
                        self.chat_history = self.chat_history[-20:]

                    def open_browser(url: str) -> str:
                        """Opens the default web browser to the specified URL."""
                        import webbrowser

                        try:
                            webbrowser.open(url)
                            return f"Successfully opened browser to {url}"
                        except Exception as e:
                            logger.exception("Failed to open browser")
                            return f"ERROR opening browser: {e!s}"

                    base_tools: list[Any] = [open_browser]
                    base_tool_map = {"open_browser": open_browser}

                    config = types.GenerateContentConfig(
                        system_instruction=sys_instruction,
                        max_output_tokens=1000,
                        temperature=0.7,
                        tools=base_tools,
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

                    # Offload API call to a thread to keep ZMQ loop reactive with retry on 429/RESOURCE_EXHAUSTED

                    response_msg = ""
                    for iteration in range(5):

                        async def generate_with_retry() -> Any:
                            nonlocal client, gemini_key
                            max_retries = 40
                            for attempt in range(max_retries):
                                try:

                                    def run_gen(_key: str | None = gemini_key) -> Any:
                                        local_client = genai.Client(api_key=_key)
                                        return local_client.models.generate_content(
                                            model="gemini-2.5-flash-lite",
                                            contents=self.chat_history,
                                            config=config,
                                        )

                                    return await asyncio.to_thread(run_gen)
                                except Exception as e:
                                    err_str = str(e)
                                    logger.error(
                                        f"[{self.name}] Gemini API Error (Attempt {attempt}): {err_str}"
                                    )
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
                                        await asyncio.sleep(1.0)
                                        continue
                                    raise

                        response = await generate_with_retry()

                        assistant_content = (
                            response.candidates[0].content if response.candidates else None
                        )
                        if assistant_content:
                            if not assistant_content.role:
                                assistant_content.role = "model"
                            self.chat_history.append(assistant_content)
                        else:
                            # If no content, it could be blocked or an empty model reply
                            try:
                                response_msg = response.text
                            except ValueError:
                                response_msg = "أعتذر، الاستجابة محظورة لدواعي الأمان أو أن النموذج أرجع محتوى فارغ."
                            break

                        function_calls = []
                        if assistant_content.parts:
                            for part in assistant_content.parts:
                                if part.function_call:
                                    function_calls.append(part.function_call)

                        if not function_calls:
                            try:
                                response_msg = response.text
                                if not response_msg or not response_msg.strip():
                                    response_msg = "أعتذر، لم أتمكن من صياغة إجابة."
                            except ValueError:
                                response_msg = "أعتذر، الاستجابة محظورة لدواعي الأمان."
                            break

                        tool_response_parts = []
                        for call in function_calls:
                            name = call.name
                            args = call.args
                            if name in base_tool_map:
                                try:

                                    def run_tool(_name: str = name, _args: Any = args) -> str:
                                        return base_tool_map[_name](**_args)

                                    result = await asyncio.to_thread(run_tool)
                                except Exception as e:
                                    logger.exception("Tool execution failed")
                                    result = f"ERROR: {e!s}"
                            else:
                                result = f"ERROR: Function {name} not found."

                            tool_response_parts.append(
                                types.Part.from_function_response(
                                    name=name, response={"result": result}
                                )
                            )
                        self.chat_history.append(
                            types.Content(role="tool", parts=tool_response_parts)
                        )

                    if not response_msg:
                        response_msg = "Error: Tool execution loop limit exceeded."
                except Exception:
                    logger.exception(f"[{self.name}] Gemini generation failed")
                    response_msg = f"[{self.name}] Gemini call failed. Direct answer: {message}"
            else:
                response_msg = (
                    f"[{self.name}] Command processed successfully (Key Offline): {message}"
                )

            reply = EventPayload(
                event_type=EventType.STATE_UPDATE,
                source_agent_id=self.name,
                correlation_id=event.correlation_id,
                payload={"message": response_msg},
            )
            await self.client.send(reply)

    async def _handle_memory_stored(self, event: EventPayload) -> None:
        payload = event.payload
        agent_raw = payload.get("agent")
        agent = agent_raw if isinstance(agent_raw, str) else ""
        if agent != self.name.lower() and agent not in self.agent_id.lower():
            return

        key = payload.get("key")
        reply = EventPayload(
            event_type=EventType.STATE_UPDATE,
            source_agent_id=self.name,
            correlation_id=event.correlation_id,
            payload={
                "message": f"[{self.name}] Memory Crawler verified and committed '{key}' to SQLite permanent storage."
            },
        )
        await self.client.send(reply)

    async def _handle_memory_inject(self, event: EventPayload) -> None:
        payload = event.payload
        agent_raw = payload.get("agent")
        agent = agent_raw if isinstance(agent_raw, str) else ""
        if agent != self.name.lower() and agent not in self.agent_id.lower():
            return

        memories_raw = payload.get("memories", [])
        memories: list[Any] = memories_raw if isinstance(memories_raw, list) else []
        if memories:
            best_match = memories[0]
            if isinstance(best_match, dict):
                content_raw = best_match.get("content")
                self._active_memory_context = (
                    content_raw
                    if isinstance(content_raw, str)
                    else str(content_raw) if content_raw is not None else None
                )
            else:
                self._active_memory_context = None
            msg = f"[{self.name}] Memory recall injection successful. Context: '{self._active_memory_context}'"
        else:
            self._active_memory_context = None
            msg = f"[{self.name}] No matching memory records found in SQLite DB."

        reply = EventPayload(
            event_type=EventType.STATE_UPDATE,
            source_agent_id=self.name,
            correlation_id=event.correlation_id,
            payload={"message": msg},
        )
        await self.client.send(reply)
