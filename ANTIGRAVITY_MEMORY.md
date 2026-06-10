# ANTIGRAVITY PERMANENT MEMORY & STATE TRACKER
**Project:** Sovereign Matrix Engine (THE_MATRIX)
**Commander:** Dr. Anas Hilal
**Role:** Main AI Architect & System Engineer (Antigravity)

## 1. System Architecture
- **Location:** `J:\THE_MATRIX`
- **Core Components:**
  - `matrix_main.py`: Bootstrapper and Agent process launcher.
  - `services/ui_bridge.py`: WebSocket server bridging ZMQ to the React frontend.
  - `dashboard/`: React + Vite frontend (running via `npm run dev`).
  - `core/key_router.py`: Rotates API keys to bypass rate limits.
  - `core/memory_crawler.py` & `sovereign_memory.db`: SQLite DB used by Agents (Neo, Trinity, etc.) for persistent context.

## 2. API Keys & Rate Limiting
- **The 20 Key Router:** 
  - 40 unique keys are stored on the Commander's desktop: `C:\Users\ai\Desktop\مجلد الاسرار\The_Sovereign_Commander\20 مشروع\dr` & `r11`.
  - The first 20 keys have been injected into `J:\THE_MATRIX\.env` (Variables: `EXTRA01_API_KEY` to `EXTRA20_API_KEY`).
  - `neo_agent.py` was updated to perform "Instant Key Rotation" (no 60s sleep) upon hitting a 429 Error, sending real-time `STATE_UPDATE` to the UI (`Rate Limit Hit. Rotating Key...`).

## 3. UI & State Persistence
- **React Frontend (`dashboard/src/pages/ChatPage.jsx`):**
  - Uses `localStorage` to save `globalMessages` and `globalStatuses`. A browser refresh or navigation will *not* delete the chat.
  - **New Chat Button:** Added to the UI. It clears `localStorage` and sends a `/clear` command via WebSocket to wipe the agent's Python memory (`self.chat_history = []`).
  - **Pulse Status Box:** UI displays `Agent IS WORKING... > Thinking...` actively underneath the messages.

## 4. Current Objectives & Known Context
- The Commander demands zero illusions, 100% transparency (Absolute Truth Protocol).
- Context truncation caused Antigravity to forget the original source of the 20 keys, but this has been resolved.
- This file acts as the ultimate reference for Antigravity. If confused, READ THIS FILE.

## 5. Startup Procedure
- `J:\THE_MATRIX\start_matrix.bat` is configured to launch the 3 detached windows (Engine, Bridge, Dashboard) correctly.

---
*End of Memory File. Update this file continuously whenever critical project changes occur.*
