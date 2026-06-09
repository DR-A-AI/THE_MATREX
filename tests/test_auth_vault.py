import sys
import os
import time
sys.path.append(r"J:\THE_MATRIX")

import pytest
from core.auth_vault import AuthVault, SecretToken

def test_auth_vault_token_lifecycle():
    vault = AuthVault()
    
    # 1. Issue token
    token_id = vault.issue_token(scope="test_scope", secret_data="my_super_secret", ttl_minutes=1)
    assert token_id in vault.active_tokens
    
    # 2. Consume token
    secret = vault.consume_token(token_id)
    assert secret == "my_super_secret"
    
    # 3. Verify single-use policy (should raise PermissionError on second consumption)
    with pytest.raises(PermissionError):
        vault.consume_token(token_id)

def test_auth_vault_invalid_token():
    vault = AuthVault()
    with pytest.raises(PermissionError):
        vault.consume_token("non_existent_token")

def test_auth_vault_garbage_collection():
    vault = AuthVault()
    
    # Issue a token with 0 TTL (instantly expired)
    token_id = vault.issue_token(scope="expired_scope", secret_data="dead_secret", ttl_minutes=-5)
    
    # Run garbage collection
    vault._garbage_collect()
    
    # The expired token should be purged
    assert token_id not in vault.active_tokens
