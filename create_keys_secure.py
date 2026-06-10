"""
Secure key creation script — writes directly to .env, never prints keys.
"""
import subprocess, json, sys

def create_key(display_name, project):
    result = subprocess.run(
        ["gcloud", "alpha", "services", "api-keys", "create",
         f"--display-name={display_name}",
         f"--project={project}",
         "--api-target=service=generativelanguage.googleapis.com",
         "--format=json"],
        capture_output=True, text=True
    )
    # gcloud prints progress to stderr, JSON result to stdout
    try:
        data = json.loads(result.stdout)
        return data.get("keyString") or data.get("key", {}).get("keyString")
    except Exception:
        # Try extracting from stderr (some versions print JSON there)
        try:
            data = json.loads(result.stderr)
            return data.get("keyString")
        except Exception:
            print(f"[WARN] Could not parse JSON for {display_name}.")
            print("STDOUT:", result.stdout[:200])
            print("STDERR:", result.stderr[:200])
            return None

project = "matrix-sovereign-2026"
neo_key = create_key("NEO_KEY_SECURE_2", project)
tri_key = create_key("TRINITY_KEY_SECURE_2", project)

if not neo_key or not tri_key:
    print("[FAIL] One or more keys could not be created.")
    sys.exit(1)

env_content = f"""# ============================================================================
# THE MATRIX: Environment Configuration
# ============================================================================

ZMQ_ENDPOINT=tcp://127.0.0.1:5555
ZMQ_HEARTBEAT_INTERVAL=2
ZMQ_HEARTBEAT_TIMEOUT=5

# API Keys — Project: matrix-sovereign-2026
# Created securely — never echoed to chat
NEO_API_KEY={neo_key}
GEMINI_API_KEY={neo_key}
GOOGLE_API_KEY={neo_key}
TRINITY_API_KEY={tri_key}
MORPHEUS_API_KEY={tri_key}
"""

with open(r"J:\THE_MATRIX\.env", "w", encoding="utf-8") as f:
    f.write(env_content)

print("[OK] Keys created and written to .env — values NOT displayed.")
print(f"[INFO] NEO key UID starts with: {neo_key[:8]}***")
print(f"[INFO] TRINITY key UID starts with: {tri_key[:8]}***")
