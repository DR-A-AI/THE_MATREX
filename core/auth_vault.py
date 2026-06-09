import os
import json
import secrets
import logging
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet

logger = logging.getLogger("Sovereign.AuthVault")

class SecretToken:
    """Ephemeral, strongly encrypted token for strict Zero-Trust access."""
    
    def __init__(self, scope: str, secret_data: str, ttl_minutes: int = 15):
        self.token_id = secrets.token_urlsafe(32)
        self.scope = scope
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(minutes=ttl_minutes)
        self.is_expired = False
        
        # Encrypt the secret in memory
        self._encryption_key = Fernet.generate_key()
        cipher = Fernet(self._encryption_key)
        self._encrypted_payload = cipher.encrypt(secret_data.encode("utf-8"))
    
    def is_valid(self) -> bool:
        return datetime.utcnow() < self.expires_at and not self.is_expired
    
    def reveal(self) -> str:
        if not self.is_valid():
            raise PermissionError("Token expired or revoked.")
        cipher = Fernet(self._encryption_key)
        decrypted = cipher.decrypt(self._encrypted_payload).decode("utf-8")
        self.invalidate() # Single-use strictly enforced
        return decrypted

    def invalidate(self):
        self.is_expired = True
        # Cryptographic wipe of the key
        self._encryption_key = secrets.token_bytes(32)
        self._encrypted_payload = secrets.token_bytes(64)

class AuthVault:
    """Zero-Trust In-Memory Secret Management."""
    
    def __init__(self):
        self.active_tokens: Dict[str, SecretToken] = {}
        logger.info("Sovereign Zero-Trust Auth Vault initialized.")
    
    def issue_token(self, scope: str, secret_data: str, ttl_minutes: int = 5) -> str:
        """Issue an ephemeral in-memory encrypted token, return the token_id."""
        token = SecretToken(scope=scope, secret_data=secret_data, ttl_minutes=ttl_minutes)
        self.active_tokens[token.token_id] = token
        logger.info(f"Issued single-use ephemeral token for scope: {scope}")
        return token.token_id
    
    def consume_token(self, token_id: str) -> Optional[str]:
        """Consume a token securely. Purges after use."""
        token = self.active_tokens.get(token_id)
        if not token:
            logger.warning(f"Security Alert: Invalid or unknown token attempted: {token_id}")
            raise PermissionError("Token invalid.")
        
        secret = token.reveal()
        del self.active_tokens[token_id]
        self._garbage_collect()
        return secret
        
    def _garbage_collect(self):
        """Purge invalid tokens from memory. Sovereign Razor compliance."""
        expired = [tid for tid, token in self.active_tokens.items() if not token.is_valid()]
        for tid in expired:
            self.active_tokens[tid].invalidate()
            del self.active_tokens[tid]
            
        if expired:
            logger.debug(f"Garbage collected {len(expired)} dead tokens.")

