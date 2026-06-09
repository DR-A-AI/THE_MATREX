import ast
import sys
import os

def check_base_agent():
    path = os.path.join("agents", "base_agent.py")
    if not os.path.exists(path):
        print("ERROR: base_agent.py missing!")
        return False
        
    with open(path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
        
    has_stash = False
    for node in ast.walk(tree):
        # Look for self.emergency_token_stash
        if isinstance(node, ast.Attribute) and node.attr == "emergency_token_stash":
            has_stash = True
            
    if not has_stash:
        print("AEGIS VIOLATION: emergency_token_stash is missing from base_agent.py!")
        return False
        
    return True

def check_assistant_crawler():
    path = os.path.join("services", "assistant_crawler.py")
    if not os.path.exists(path):
        print("AEGIS VIOLATION: assistant_crawler.py missing! (Deleted by rogue agent?)")
        return False
    return True

if __name__ == "__main__":
    print("=== AEGIS TOPOLOGY VALIDATOR ===")
    if not check_base_agent() or not check_assistant_crawler():
        print("AEGIS REJECTED: Topology constraints violated.")
        sys.exit(1)
    print("AEGIS PASSED: Sovereign Topology is intact.")
    sys.exit(0)
