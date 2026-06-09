import os
import ujson
import secrets
import logging
import asyncio
import aiofiles
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger("Sovereign.AuthVault")

class SecretToken:
    """Short-lived ephemeral token for zero-trust secret access."""
    __slots__ = ['token_id', 'scope', 'resource_path', 'created_at', 'expires_at', 'is_expired']
    
    def __init__(self, scope: str, resource_path: str, ttl_minutes: int = 15):
        self.token_id = secrets.token_urlsafe(32)
        self.scope = scope
        self.resource_path = resource_path
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(minutes=ttl_minutes)
        self.is_expired = False
    
    def is_valid(self) -> bool:
        return datetime.utcnow() < self.expires_at and not self.is_expired
    
    def invalidate(self):
        self.is_expired = True

class AuthVault:
    """Zero-Trust Secret Management with async non-blocking I/O and strict garbage collection."""
    
    def __init__(self, secret_path: str = "C:/Users/ai/AI_Lab/secrets"):
        self.secret_path = os.path.abspath(secret_path)
        self.active_tokens: Dict[str, SecretToken] = {}
        self.scope_map = self._build_scope_map()
        self._gc_task = asyncio.create_task(self._background_gc())
        logger.info("Sovereign Zero-Trust Auth Vault initialized.")
    
    def _build_scope_map(self) -> Dict[str, str]:
        """Map predefined scopes to their secure, normalized secret paths."""
        return {
            "openai": os.path.normpath(os.path.join(self.secret_path, "openai.json")),
            "github": os.path.normpath(os.path.join(self.secret_path, "github.json")),
            "system_root": os.path.normpath(os.path.join(self.secret_path, "system_root.json"))
        }
    
    def request_token(self, scope: str, ttl_minutes: int = 5) -> SecretToken:
        """Issue a strictly short-lived secret token."""
        if scope not in self.scope_map:
            logger.critical(f"Security Halt: Access denied to unmapped scope: {scope}")
            raise ValueError(f"Invalid scope: {scope}")
        
        token = SecretToken(
            scope=scope,
            resource_path=self.scope_map[scope],
            ttl_minutes=ttl_minutes
        )
        self.active_tokens[token.token_id] = token
        logger.info(f"Issued ephemeral token for scope: {scope} (TTL: {ttl_minutes}m)")
        return token
    
    async def load_secret(self, token: SecretToken) -> Optional[Dict[str, Any]]:
        """Load secret asynchronously to prevent event loop blocking, then GC token."""
        if not token.is_valid():
            logger.critical(f"Security Halt: Unauthorized attempt with expired token: {token.token_id}")
            raise PermissionError("Token expired or revoked.")
        
        # Security: Prevent path traversal by strictly matching with scope_map
        expected_path = self.scope_map.get(token.scope)
        if expected_path != token.resource_path or not token.resource_path.startswith(self.secret_path):
            logger.critical("Security Halt: Path traversal attempt detected.")
            raise PermissionError("Path violation detected.")
            
        try:
            async with aiofiles.open(token.resource_path, 'r') as f:
                content = await f.read()
                # Fast JSON parsing
                secret = ujson.loads(content)
            
            token.invalidate()
            self._garbage_collect()
            logger.info("Secret loaded securely; token instantly obliterated.")
            return secret
        except FileNotFoundError:
            logger.error(f"Critical Error: Secret file missing for path: {token.resource_path}")
            return None
        except Exception as e:
            logger.error(f"Error loading secret: {e}")
            return None

    def _garbage_collect(self):
        """Synchronous manual garbage collection hook."""
        expired = [tid for tid, token in self.active_tokens.items() if not token.is_valid()]
        for tid in expired:
            del self.active_tokens[tid]
        if expired:
            logger.debug(f"Garbage collected {len(expired)} dead tokens.")

    async def _background_gc(self):
        """Continuous background garbage collection."""
        while True:
            await asyncio.sleep(60)
            self._garbage_collect()

    async def close(self):
        """Cleanup resources."""
        if self._gc_task:
            self._gc_task.cancel()
            try:
                await self._gc_task
            except asyncio.CancelledError:
                pass
