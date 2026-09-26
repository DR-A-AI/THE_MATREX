"""Matrix Vision Subsystem — Sovereign screen capture and input automation."""

from __future__ import annotations

import logging
from typing import Any

import mss

logger = logging.getLogger(__name__)


def save_screenshot(filepath: str, monitor_index: int = 1) -> bool:
    """Capture screen using genuine mss engine and save to filepath."""
    try:
        with mss.MSS() as sct:
            monitors = sct.monitors
            idx = monitor_index if 0 < monitor_index < len(monitors) else 1
            sct.shot(mon=idx, output=filepath)
            return True
    except (mss.exception.ScreenShotError, OSError) as e:
        logger.error("Screenshot capture failed: %s", e)
        return False


def get_vision_part(monitor_index: int = 1) -> dict[str, Any]:
    """Return vision telemetry metadata for active monitor."""
    return {"status": "active", "monitor_index": monitor_index}


def safe_click(x: int, y: int, button: str = "left") -> None:
    """Safely click screen coordinates if input device available."""
    try:
        import pyautogui  # type: ignore[import-untyped]

        pyautogui.FAILSAFE = True
        pyautogui.click(x, y, button=button)
    except (ImportError, OSError) as e:
        logger.warning("safe_click unavailable: %s", e)


def safe_type_text(text: str) -> None:
    """Safely type text if input device available."""
    try:
        import pyautogui  # type: ignore[import-untyped]

        pyautogui.FAILSAFE = True
        pyautogui.write(text)
    except (ImportError, OSError) as e:
        logger.warning("safe_type_text unavailable: %s", e)


def safe_press_key(key: str) -> None:
    """Safely press key if input device available."""
    try:
        import pyautogui  # type: ignore[import-untyped]

        pyautogui.FAILSAFE = True
        pyautogui.press(key)
    except (ImportError, OSError) as e:
        logger.warning("safe_press_key unavailable: %s", e)
