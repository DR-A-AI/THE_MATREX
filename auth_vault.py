import os
import json
import secrets
import logging
import time
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet  # Real encryption at rest

logger = logging.getLogger("Sovereign.AuthVault")

class SecretToken:
    """Short-lived ephemeral token for zero-trust secret access."""
    
    __slots__ = ('token_id', 'scope', 'resource_path', 'expires_at', 'is_expired')
    
    def __init__(self, scope: str, resource_path: str, ttl_seconds: float = 900.0):
        self.token_id = secrets.token_urlsafe(32)
        self.scope = scope
        self.resource_path = resource_path
        self.expires_at = time.monotonic() + ttl_seconds
        self.is_expired = False
    
    def is_valid(self) -> bool:
        return time.monotonic() < self.expires_at and not self.is_expired
    
    def invalidate(self):
        self.is_expired = True
        # Overwrite sensitive memory fields if possible
        self.scope = ""
        self.resource_path = ""

class AuthVault:
    """Zero-Trust Secret Management supporting strict garbage collection and Encryption-at-Rest."""
    
    def __init__(self, secret_path: Optional[str] = None, master_key: Optional[bytes] = None):
        self.secret_path = secret_path or os.getenv("SOVEREIGN_VAULT_PATH", "/var/sovereign/secrets")
        
        # Enforce encryption at rest
        mk = master_key or os.getenv("SOVEREIGN_MASTER_KEY", "").encode()
        if not mk:
            logger.warning("No Master Key provided! Operating in highly insecure mock mode.")
            self.cipher = None
        else:
            self.cipher = Fernet(mk)
            
        self.active_tokens: Dict[str, SecretToken] = {}
        self.scope_map = self._build_scope_map()
        logger.info("Zero-Trust Auth Vault initialized.")
    
    def _build_scope_map(self) -> Dict[str, str]:
        """Map predefined scopes to their secure secret resource paths."""
        return {
            "openai": os.path.join(self.secret_path, "openai.enc"),
            "github": os.path.join(self.secret_path, "github.enc"),
            "system_root": os.path.join(self.secret_path, "system_root.enc")
        }
    
    def request_token(self, scope: str, ttl_seconds: float = 300.0) -> SecretToken:
        """Issue a strictly short-lived secret token."""
        if scope not in self.scope_map:
            logger.error(f"Security Alert: Attempted access to invalid scope: {scope}")
            raise ValueError(f"Invalid scope: {scope}")
        
        token = SecretToken(
            scope=scope,
            resource_path=self.scope_map[scope],
            ttl_seconds=ttl_seconds
        )
        self.active_tokens[token.token_id] = token
        logger.info(f"Issued ephemeral token for scope: {scope} (TTL: {ttl_seconds}s)")
        return token
    
    def load_secret(self, token: SecretToken) -> Optional[Dict[str, Any]]:
        """Load encrypted secret and immediately garbage collect the token."""
        if not token.is_valid():
            logger.warning("Security Alert: Attempted to use expired/revoked token.")
            raise PermissionError("Token expired or revoked.")
        
        try:
            with open(token.resource_path, 'rb') as f:
                encrypted_data = f.read()
            
            if self.cipher:
                decrypted_data = self.cipher.decrypt(encrypted_data)
                secret = json.loads(decrypted_data.decode('utf-8'))
            else:
                # Insecure fallback for demonstration without master key
                secret = json.loads(encrypted_data.decode('utf-8'))
            
            # Zero out token state
            token.invalidate()
            self._garbage_collect()
            logger.info("Secret loaded securely; token instantly incinerated.")
            return secret
        except FileNotFoundError:
            logger.error(f"Critical: Secret file missing for path: {token.resource_path}")
            return None
        except Exception as e:
            logger.error(f"Security Exception during decryption: {e}")
            return None
            
    def _garbage_collect(self):
        """Purge invalid tokens from memory to enforce Automated Maintenance Policy."""
        expired = [tid for tid, token in self.active_tokens.items() if not token.is_valid()]
        for tid in expired:
            del self.active_tokens[tid]
            
        if expired:
            logger.debug(f"Garbage collected {len(expired)} dead tokens.")
