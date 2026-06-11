"""
Matrix Vision & Control Module
Codename: Nebuchadnezzar Optics
"""

import io
import base64
import logging
import pyautogui
import mss
from PIL import Image

# Matrix-themed logging setup
logger = logging.getLogger("Matrix_Construct")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('[NEBUCHADNEZZAR.SYS] %(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
ch.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(ch)

# Enable PyAutoGUI fail-safe (moving mouse to a corner raises an exception)
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5  # Add a tiny pause between actions to prevent matrix glitches

def get_vision_part(monitor_index=1):
    """
    Captures the specified screen and prepares it for Neo's vision.
    Returns a google.genai.types.Part if the SDK is installed,
    otherwise returns a base64 encoded string of the PNG data.
    
    monitor_index=1 usually corresponds to the primary monitor in mss.
    """
    logger.info("Initiating optic feed extraction from the Matrix...")
    try:
        monitor_index = int(monitor_index)
        with mss.mss() as sct:
            if monitor_index >= len(sct.monitors):
                logger.warning(f"Monitor {monitor_index} out of range. Falling back to primary (1).")
                monitor_index = 1
                
            monitor = sct.monitors[monitor_index]
            logger.debug(f"Capturing sector dimensions: {monitor}")
            
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            img_bytes = buffer.getvalue()
            
            logger.info("Optic feed digitized and compressed.")
            
            try:
                from google.genai import types
                logger.debug("google.genai SDK found. Formatting as Part.")
                return types.Part.from_bytes(data=img_bytes, mime_type='image/png')
            except ImportError:
                logger.warning("google.genai SDK not found. Defaulting to Base64 payload.")
                return base64.b64encode(img_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to extract optic feed: {e}")
        raise

def save_screenshot(filepath, monitor_index=1):
    """
    Captures the specified screen and saves it to a file.
    """
    logger.info(f"Saving optic feed to {filepath}...")
    try:
        with mss.mss() as sct:
            if monitor_index >= len(sct.monitors):
                monitor_index = 1
            monitor = sct.monitors[monitor_index]
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            img.save(filepath, format="PNG")
            logger.info("Optic feed saved successfully.")
            return True
    except Exception as e:
        logger.error(f"Failed to save optic feed: {e}")
        return False

def safe_click(x, y, button='left'):
    """
    Executes a physical click within the simulation constraints.
    """
    logger.info(f"Targeting coordinates [{x}, {y}] for '{button}' engagement.")
    try:
        pyautogui.click(x=x, y=y, button=button)
        logger.debug("Engagement successful.")
    except pyautogui.FailSafeException:
        logger.critical("FAILSAFE TRIGGERED. Mouse moved to simulation boundary.")
    except Exception as e:
        logger.error(f"Click engagement failed: {e}")

def safe_type_text(text, interval=0.05):
    """
    Injects textual data directly into the active matrix console.
    """
    logger.info(f"Injecting payload of length {len(text)} into current focus.")
    try:
        pyautogui.write(text, interval=interval)
        logger.debug("Payload injection complete.")
    except pyautogui.FailSafeException:
        logger.critical("FAILSAFE TRIGGERED during payload injection.")
    except Exception as e:
        logger.error(f"Payload injection failed: {e}")

def safe_press_key(key):
    """
    Triggers a specific simulated hardware interrupt (key press).
    """
    logger.info(f"Triggering hardware interrupt: '{key}'")
    try:
        pyautogui.press(key)
        logger.debug("Interrupt signal sent.")
    except pyautogui.FailSafeException:
        logger.critical("FAILSAFE TRIGGERED during key press.")
    except Exception as e:
        logger.error(f"Key interrupt failed: {e}")

if __name__ == "__main__":
    logger.info("Matrix Vision Engineer module loaded and standing by.")
