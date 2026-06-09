import os
import json
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import stat

logger = logging.getLogger("Sovereign.AuthVault")

class SecretToken:
    """Short-lived ephemeral token for zero-trust secret access."""
    
    def __init__(self, scope: str, resource_path: str, ttl_minutes: int = 15):
        self.token_id = secrets.token_urlsafe(64) # Increased token strength
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
    """Zero-Trust Secret Management supporting strict garbage collection and file permission checks."""
    
    def __init__(self, secret_path: str = "C:/Users/ai/AI_Lab/secrets"):
        self.secret_path = secret_path
        self.active_tokens: Dict[str, SecretToken] = {}
        self.scope_map = self._build_scope_map()
        self._verify_vault_permissions()
        logger.info("Zero-Trust Auth Vault initialized.")
        
    def _verify_vault_permissions(self):
        """Strictly ensure the vault directory is readable only by the owner."""
        if not os.path.exists(self.secret_path):
            os.makedirs(self.secret_path, mode=0o700, exist_ok=True)
            logger.info(f"Created secret vault directory at {self.secret_path} with restricted permissions.")
            return

        # Simple cross-platform check (best effort on Windows, strict on POSIX)
        if os.name == 'posix':
            st = os.stat(self.secret_path)
            if bool(st.st_mode & stat.S_IRWXG) or bool(st.st_mode & stat.S_IRWXO):
                logger.warning("Security Alert: Secret vault has insecure permissions. Locking down.")
                os.chmod(self.secret_path, stat.S_IRWXU)
    
    def _build_scope_map(self) -> Dict[str, str]:
        """Map predefined scopes to their secure secret resource paths."""
        return {
            "openai": os.path.normpath(os.path.join(self.secret_path, "openai.json")),
            "github": os.path.normpath(os.path.join(self.secret_path, "github.json")),
            "system_root": os.path.normpath(os.path.join(self.secret_path, "system_root.json"))
        }
    
    def request_token(self, scope: str, ttl_minutes: int = 5) -> SecretToken:
        """Issue a strictly short-lived secret token."""
        if scope not in self.scope_map:
            logger.error(f"Security Alert: Attempted access to invalid scope: {scope}")
            raise ValueError(f"Invalid scope: {scope}")
        
        token = SecretToken(
            scope=scope,
            resource_path=self.scope_map[scope],
            ttl_minutes=ttl_minutes
        )
        self.active_tokens[token.token_id] = token
        logger.info(f"Issued ephemeral token for scope: {scope} (TTL: {ttl_minutes}m)")
        return token
    
    def load_secret(self, token: SecretToken) -> Optional[Dict[str, Any]]:
        """Load secret, validate strict JSON structure, and immediately garbage collect the token."""
        if not token.is_valid():
            logger.warning(f"Security Alert: Attempted to use expired/revoked token: {token.token_id}")
            raise PermissionError("Token expired or revoked.")
            
        if token.token_id not in self.active_tokens:
             logger.warning("Security Alert: Token not found in active registry. Possible replay or fabrication attack.")
             raise PermissionError("Invalid token origin.")
        
        try:
            # Ensure file is inside vault
            if not os.path.abspath(token.resource_path).startswith(os.path.abspath(self.secret_path)):
                logger.critical(f"Security Alert: Path Traversal Attempt Detected for resource: {token.resource_path}")
                raise PermissionError("Path Traversal Blocked.")

            with open(token.resource_path, 'r') as f:
                secret = json.load(f)
                
            if not isinstance(secret, dict):
                 logger.error(f"Critical: Secret file {token.resource_path} is not a valid JSON object.")
                 return None
            
            # Immediately invalidate to enforce one-time usage pattern
            token.invalidate()
            self._garbage_collect()
            logger.info(f"Secret loaded securely; token invalidated: {token.token_id}")
            return secret
        except json.JSONDecodeError as e:
            logger.error(f"Critical: Malformed JSON in secret file: {token.resource_path} - Error: {e}")
            token.invalidate()
            return None
        except FileNotFoundError:
            logger.error(f"Critical: Secret file missing for path: {token.resource_path}")
            token.invalidate()
            return None
            
    def _garbage_collect(self):
        """Purge invalid tokens from memory to enforce Automated Maintenance Policy."""
        expired = [tid for tid, token in self.active_tokens.items() if not token.is_valid()]
        for tid in expired:
            del self.active_tokens[tid]
            
        if expired:
            logger.debug(f"Garbage collected {len(expired)} dead tokens.")
