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
    
    def __init__(self, secret_path: str = "J:\\مجلد الاسرار\\1"):
        self.secret_path = os.path.abspath(secret_path)
        self.active_tokens: Dict[str, SecretToken] = {}
        self.scope_map = self._build_scope_map()
        self._gc_task = asyncio.create_task(self._background_gc())
        logger.info("Sovereign Zero-Trust Auth Vault initialized.")
    
    def _build_scope_map(self) -> Dict[str, str]:
        """Map predefined scopes to their secure, normalized secret paths."""
        return {
            "gcp_p12": "J:\\مجلد الاسرار\\1\\theai-world-ff9cafd706c1.p12",
            "firebase_admin": "J:\\مجلد الاسرار\\1\\theai-world-firebase-adminsdk-fbsvc-d96be6f9b6.json",
            "gcp_client_secret": "J:\\مجلد الاسرار\\1\\client_secret_759852947193-9upqqb6ljgh22oi45lqrcp9i3814nrsc.apps.googleusercontent.com.json",
            "gcp_text": "J:\\مجلد الاسرار\\1\\Google Cloud  G SuitGoogle Cloud  G.txt",
            "gcp_service_account": "J:\\مجلد الاسرار\\1\\theai-world-443058ed6fa2.json"
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
    
    async def load_secret(self, token: SecretToken) -> Any:
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
            if token.resource_path.endswith('.p12'):
                async with aiofiles.open(token.resource_path, 'rb') as f:
                    secret = await f.read()
            elif token.resource_path.endswith('.txt'):
                async with aiofiles.open(token.resource_path, 'r', encoding='utf-8') as f:
                    secret = await f.read()
            elif token.resource_path.endswith('.json'):
                async with aiofiles.open(token.resource_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    secret = ujson.loads(content)
            else:
                logger.error(f"Critical Error: Unsupported file format for path: {token.resource_path}")
                return None
            
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
