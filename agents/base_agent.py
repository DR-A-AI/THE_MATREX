import asyncio
import hmac
import json
import logging
import os
import time
import uuid
from typing import Any

from dotenv import load_dotenv

from core.cognitive_gate import CognitiveGate
from core.decision_log import get_logger as get_decision_logger
from core.intent_parser import IntentParser
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

        # Cognitive Engineering (R6)
        self.cognitive_gate = CognitiveGate(agent_id=self.name)

        # M3: MCP Gateway support
        self.mcp_gateway = None
        self.mcp_tools = []
        self.intent_parser = IntentParser()
        self.decision_logger = get_decision_logger(agent_id=self.name)

        # Skill-based training injection
        self._CORE_IDENTITY["cognitive_skills"] = (
            "Trained in agent-creator, agent-tool-builder, ai-engineer, and diagnosing-bugs (Rigorous feedback loops, reproducing, falsifiable hypotheses, minimizing, regression testing). "
            "Trained in agent-creator (persona gen, correct routing plugins) and agent-tool-builder (MCP schema perfection, zero silent failure)."
        )

    async def start(self) -> None:
        logger.info(
            f"[{self.name}] Booting and connecting to Neural Bus at {self.client.endpoint}..."
        )
        self.client.register_handler(EventType.KEY_INJECT.value, self._handle_key_inject)
        self.client.register_handler(EventType.USER_COMMAND.value, self._handle_user_command)
        self.client.register_handler(EventType.MEMORY_STORED.value, self._handle_memory_stored)
        self.client.register_handler(EventType.MEMORY_INJECT.value, self._handle_memory_inject)
        await self.client.start()

        # M3: Initialize MCP Gateway
        try:
            from pathlib import Path

            from services.mcp_gateway import MCPGateway

            manifest_root = os.getenv("MATRIX_ROOT", "/mnt/e/matrex-dev")
            manifest_path = Path(manifest_root) / "workspace.manifest.json"
            if manifest_path.exists():
                self.mcp_gateway = MCPGateway.from_manifest(manifest_path)
                discovered = await self.mcp_gateway.discover()
                self.mcp_tools = discovered
                logger.info(
                    f"[{self.name}] MCP Gateway initialized. Discovered {len(discovered)} tools."
                )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[{self.name}] MCP Gateway initialization failed: {e}")

        self._running = True

    async def stop(self) -> None:
        logger.info(f"[{self.name}] Halting agent operations.")
        self._running = False
        if self.mcp_gateway:
            try:
                await self.mcp_gateway.close()
            except Exception as e:  # noqa: BLE001
                logger.debug(f"Failed to close mcp gateway: {e}")
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
        """Validates that command comes from authorized Commander.

        Two tiers (defense in depth):
        1. When COMMANDER_AUTH_TOKEN is configured, the payload MUST carry
           a matching ``commander_token`` (constant-time compare). A wrong
           token rejects even whitelisted source names.
        2. When no token is configured (tests/dev), fall back to the
           whitelisted source-name list.
        Rejections are rate-limited per source (60s) to avoid log spam;
        the rejection itself always applies.
        """
        AUTHORIZED_COMMANDERS = ["Commander_UI", "dr-anas-hilal", "admin", "Commander_Tester"]
        # Rate-limit repeat alerts per source (60s) to avoid log spam
        # during scans/probes; the rejection itself always applies.
        _ALERT_WINDOW = 60.0

        source = event.source_agent_id
        payload = event.payload if isinstance(event.payload, dict) else {}
        presented = payload.get("commander_token", "")
        expected = os.getenv("COMMANDER_AUTH_TOKEN", "")

        authorized = False
        if expected:
            if isinstance(presented, str) and presented:
                authorized = hmac.compare_digest(presented, expected)
        else:
            authorized = source in AUTHORIZED_COMMANDERS

        if not authorized:
            now = time.time()
            last = self._unauth_alert_at.get(source, 0.0) if hasattr(self, "_unauth_alert_at") else 0.0
            if not hasattr(self, "_unauth_alert_at"):
                self._unauth_alert_at: dict[str, float] = {}
            if now - last >= _ALERT_WINDOW:
                self._unauth_alert_at[source] = now
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

    async def _send_final_reply(self, event: EventPayload, text: str) -> None:
        """Send a terminal text answer as STATE_UPDATE + TASK_COMPLETED."""
        reply = EventPayload(
            event_type=EventType.STATE_UPDATE,
            source_agent_id=self.name,
            correlation_id=event.correlation_id,
            payload={"message": text},
        )
        await self.client.send(reply)

        completed_evt = EventPayload(
            event_type=EventType.TASK_COMPLETED,
            source_agent_id=self.name,
            correlation_id=event.correlation_id,
            payload={"message": text, "status": "completed"},
        )
        await self.client.send(completed_evt)

    async def _reply_live_status(self, event: EventPayload, message: str) -> None:
        """Answer a status/readiness question from probed live telemetry.

        Never calls the LLM: guarantees no canned "hypothetical" disclaimers.
        """
        from core.status_telemetry import (
            build_status_reply,
            collect_live_telemetry,
            contains_banned_phrase,
            detect_language,
        )

        lang = detect_language(message)
        telemetry = await asyncio.to_thread(collect_live_telemetry)
        text = build_status_reply(telemetry, lang)
        hit = contains_banned_phrase(text)
        if hit:
            logger.error(
                f"[{self.name}] Banned phrase '{hit}' in telemetry reply; "
                "using minimal fallback."
            )
            text = (
                "جاهز أيها القائد — متصل الآن." if lang == "ar" else "Ready Commander — online now."
            )
        logger.info(f"[{self.name}] Status reply from live telemetry (lang={lang}).")
        await self._send_final_reply(event, text)

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

        # Ensure command is routed to this specific agent
        if target.lower() not in self.name.lower() and target.lower() not in self.agent_id.lower():
            return

        # Validate authority
        if not await self._validate_commander(event):
            return

        logger.info(f"[{self.name}] Received directive from Commander: {message}")

        # --- DETERMINISTIC STATUS / CORRECTION PATH (anti-hallucination) ---
        # MUST run BEFORE any semantic routing: status & readiness questions are
        # answered from live telemetry on the raw text (command or message),
        # never from free LLM generation. Checking first guarantees the
        # 'جاهز؟'-style probe never falls through to general_chat on an
        # empty-string (score=0.00) tie when the payload used 'command'.
        from core.status_telemetry import (
            is_correction,
            is_status_query,
            prune_last_assistant_turn,
            strip_correction_prefix,
        )

        intent = None  # set by correction-remainder path; else parsed after intercept
        if is_correction(message):
            dropped = prune_last_assistant_turn(self.chat_history)
            logger.info(
                f"[{self.name}] Commander correction accepted; "
                f"dropped {dropped} stale assistant turn(s)."
            )
            remainder = strip_correction_prefix(message)
            if remainder and is_status_query(remainder):
                await self._reply_live_status(event, remainder)
                return
            if remainder:
                message = (
                    f"{remainder}\n\n[Commander correction: the previous assistant "
                    "answer was discarded. Reinterpret this corrected intent from "
                    "scratch; never defend the previous answer.]"
                )
                intent = self.intent_parser.parse(remainder)
            else:
                from core.status_telemetry import detect_language

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
        elif is_status_query(message):
            await self._reply_live_status(event, message)
            return

        # --- COGNITIVE GATE (R6) ---
        # Semantic routing runs ONLY after the deterministic intercept above,
        # preserving any intent already parsed from the correction remainder.
        if intent is None:
            intent = self.intent_parser.parse(message)
        trace = self.cognitive_gate.deliberate(message)
        self.decision_logger.log(trace)

        await self.client.send(
            EventPayload(
                event_type=EventType.INTENT_PARSED,
                source_agent_id=self.name,
                correlation_id=event.correlation_id,
                payload={"intent": intent.inferred, "complexity": intent.complexity},
            )
        )

        if not trace.should_proceed:
            logger.warning(f"[{self.name}] Cognitive Gate blocked execution: {trace.flags}")
            await self.client.send(
                EventPayload(
                    event_type=EventType.STATE_UPDATE,
                    source_agent_id=self.name,
                    correlation_id=event.correlation_id,
                    payload={
                        "message": f"Execution halted. Intent unclear or risk too high. Flags: {trace.flags}"
                    },
                )
            )
            return

        await self.client.send(
            EventPayload(
                event_type=EventType.DECISION_LOGGED,
                source_agent_id=self.name,
                correlation_id=event.correlation_id,
                payload={"task_hash": trace.task_hash, "decision": "proceed"},
            )
        )
        # --- END COGNITIVE GATE ---

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

            from services.ollama_client import AgentRole, get_router

            agent_lower = self.name.lower()
            try:
                agent_role = AgentRole(agent_lower)
            except ValueError:
                agent_role = AgentRole.NEO

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

            from core.status_telemetry import GROUNDING_SUFFIX

            sys_instruction = f"{sys_instruction}{GROUNDING_SUFFIX}"

            # Append recalled context if present
            prompt = message
            if self._active_memory_context:
                prompt += (
                    f"\n\n[Recalled Context from SQLite Database: '{self._active_memory_context}']"
                )
                self._active_memory_context = ""  # Clear after use

            # Ensure system prompt is set correctly in history
            if not self.chat_history or self.chat_history[0].get("role") != "system":
                self.chat_history.insert(0, {"role": "system", "content": sys_instruction})
            else:
                self.chat_history[0]["content"] = sys_instruction

            self.chat_history.append({"role": "user", "content": prompt})

            if len(self.chat_history) > 20:
                # Keep system prompt at index 0
                self.chat_history = [self.chat_history[0]] + self.chat_history[-19:]

            def open_browser(url: str) -> str:
                """Opens the default web browser to the specified URL."""
                import webbrowser

                try:
                    webbrowser.open(url)
                    return f"Successfully opened browser to {url}"
                except Exception as e:
                    logger.exception("Failed to open browser")
                    return f"ERROR opening browser: {e!s}"

            base_tool_map = {"open_browser": open_browser}

            # Optimized tool schemas for llama3.2:3b
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "open_browser",
                        "description": "Opens the default web browser to the specified URL.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "description": "The URL to open (e.g., 'http://localhost:5173')",
                                }
                            },
                            "required": ["url"],
                        },
                    },
                }
            ]

            # Append MCP tools
            if getattr(self, "mcp_tools", None):
                tools.extend(self.mcp_tools)

            # Dynamic Semantic Tool Pruning based on intent route
            if intent.route == "general_chat" or not intent.selected_tools:
                active_tools = None
            else:
                allowed_names = set(intent.selected_tools)
                if intent.route == "dev_mcp_ops" and getattr(self, "mcp_tools", None):
                    for mcp_tool in self.mcp_tools:
                        tool_fn = mcp_tool.get("function", {})
                        if "name" in tool_fn:
                            allowed_names.add(tool_fn["name"])

                active_tools = [
                    t for t in tools if t.get("function", {}).get("name") in allowed_names
                ]
                if not active_tools:
                    active_tools = None

            response_msg = ""
            router = get_router()

            try:
                for iteration in range(5):
                    response = await router.chat(
                        agent=agent_role, messages=self.chat_history, tools=active_tools
                    )

                    message_obj = response.get("message", {})
                    content = message_obj.get("content", "")

                    self.chat_history.append(message_obj)

                    if content:
                        response_msg = content

                    tool_calls = message_obj.get("tool_calls", [])
                    if not tool_calls:
                        if not response_msg:
                            response_msg = "أعتذر، لم أتمكن من صياغة إجابة."
                        break

                    for tool_call in tool_calls:
                        func = tool_call.get("function", {})
                        name = func.get("name")
                        args = func.get("arguments", {})

                        if name in base_tool_map:
                            try:

                                def run_tool(_name: str = name, _args: Any = args) -> str:
                                    return base_tool_map[_name](**_args)

                                result = await asyncio.to_thread(run_tool)
                            except Exception as e:
                                logger.exception("Tool execution failed")
                                result = f"ERROR: {e!s}"
                        elif self.mcp_gateway and self.mcp_gateway.has_tool(name):
                            # M3: Call MCP Tool
                            try:
                                logger.info(
                                    f"[{self.name}] Calling MCP tool {name} with args {args}"
                                )
                                mcp_res = await self.mcp_gateway.call_tool(name, args)
                                result = json.dumps(mcp_res)
                            except Exception as e:
                                logger.exception(f"MCP tool {name} failed")
                                result = f"ERROR: MCP {name} failed: {e!s}"
                        else:
                            result = f"ERROR: Function {name} not found."

                        self.chat_history.append(
                            {"role": "tool", "content": str(result), "name": name}
                        )

                    if not response_msg:
                        response_msg = f"Executed tools: {[tc.get('function', {}).get('name') for tc in tool_calls]}"

            except Exception as e:
                logger.exception(f"[{self.name}] Ollama generation failed")
                response_msg = (
                    f"[{self.name}] AI generation failed. Direct answer: {message}\nError: {e!s}"
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
