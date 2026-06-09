# SOVEREIGN MATRIX CONSTITUTION (IMMUTABLE LAWS)

## THE SUPREME RULE
**All agents must obey the Sovereign Commander (Dr. Anas Hilal).**
You have **Zero Autonomy on Authority**. Any architectural rewrite must be approved.

## IMMUTABLE TOPOLOGY (NON-NEGOTIABLE)
1. **The Blind Extractors:** Neo and Trinity are "Supreme Extractors". They MUST extract keys from the outside world and broadcast them via `TOKEN_EXTRACTED`. They MUST NOT store keys.
2. **The Assistant Crawler (The Distributor):** There MUST exist an `AssistantCrawler`. It is the ONLY entity allowed to listen to `TOKEN_EXTRACTED`, send to Vault, and broadcast `KEY_INJECT`.
3. **The Emergency Stash:** The `MatrixAgent` (base class) MUST maintain an `emergency_token_stash` attribute. Agents MUST NOT use JIT provisioning to request keys directly; they must wait for `KEY_INJECT`.
4. **Zero-Trust Neural Bus:** All ZMQ events MUST be signed with HMAC-SHA256. 

**WARNING TO SUBAGENTS (CRITIC, ARCHITECT):**
If you delete the stash, the AssistantCrawler, or bypass the Master-Slave topology, your code will be physically rejected by the Aegis Pre-Commit Hook.
