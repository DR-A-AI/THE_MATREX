import os
import time
import logging

logger = logging.getLogger("Matrix.KeyRouter")

class APIKeyRouter:
    _keys = []
    _exhausted_keys = {}  # key -> timestamp when it was exhausted
    _current_index = 0
    _COOLDOWN_SECONDS = 60
    
    @classmethod
    def initialize(cls):
        """Loads all available Gemini API keys from the environment variables."""
        if cls._keys:
            return
            
        from dotenv import load_dotenv
        load_dotenv(os.path.join(r"J:\THE_MATRIX", ".env"))
        
        # Discover all keys that look like Google API keys
        for k, v in os.environ.items():
            if ("API_KEY" in k or "POOL_KEY" in k) and v and v.startswith("AIza"):
                if v not in cls._keys:
                    cls._keys.append(v)
                    
        if not cls._keys:
            logger.warning("No valid API keys found in .env! Agents may fail.")
        else:
            logger.info(f"Initialized API Key Router with {len(cls._keys)} keys.")
            
    @classmethod
    def get_key(cls) -> str:
        """Returns the next available API key in a round-robin fashion, skipping exhausted ones."""
        cls.initialize()
        
        if not cls._keys:
            return None
            
        # Cleanup exhausted keys whose cooldown has expired
        current_time = time.time()
        for k in list(cls._exhausted_keys.keys()):
            if current_time - cls._exhausted_keys[k] > cls._COOLDOWN_SECONDS:
                del cls._exhausted_keys[k]
                
        # Try to find a healthy key
        for _ in range(len(cls._keys)):
            key = cls._keys[cls._current_index]
            key_index = cls._current_index + 1
            cls._current_index = (cls._current_index + 1) % len(cls._keys)
            
            if key not in cls._exhausted_keys:
                cls._log_telemetry(f"SUCCESS: Assigned Key #{key_index} for request.")
                return key
                
        # If all keys are exhausted, return the next one anyway and hope for the best
        logger.warning("ALL API KEYS EXHAUSTED! Falling back to the next key.")
        key = cls._keys[cls._current_index]
        key_index = cls._current_index + 1
        cls._current_index = (cls._current_index + 1) % len(cls._keys)
        cls._log_telemetry(f"WARNING: Forced to use exhausted Key #{key_index}.")
        return key
        
    @classmethod
    def _log_telemetry(cls, msg: str):
        """Writes live telemetry to monitor consumption."""
        try:
            with open(os.path.join(r"J:\THE_MATRIX", "request_monitor.log"), "a", encoding="utf-8") as f:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {msg}\n")
        except Exception:
            pass
        
    @classmethod
    def report_exhausted(cls, key: str):
        """Mark a key as exhausted (429 Rate Limit) so it won't be used for 60s."""
        if key:
            cls._exhausted_keys[key] = time.time()
            logger.warning(f"API Key marked as EXHAUSTED (Rate Limited). Cooldown: 60s.")
            cls._log_telemetry(f"ERROR: Key Exhausted (Rate Limit Hit). Added to cooldown list.")
