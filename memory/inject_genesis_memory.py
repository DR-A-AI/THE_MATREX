import json
import sqlite3
import os

# Connect to the Matrix Memory DB (or create for each agent)
agents = ['neo', 'trinity', 'morpheus', 'smith', 'oracle', 'base', 'aegis']
memory_source = "J:\\THE_MATRIX\\memory\\genesis_memory.jsonl"

def build_memory_injector(agent_name):
    db_path = f"J:\\THE_MATRIX\\memory\\{agent_name}_memory.db"
    
    # Create the sqlite schema used by the Matrix agents
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Read my exact transcript and convert it to Matrix format
    with open(memory_source, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                record = json.loads(line)
                role = "user" if record.get("type") == "USER_INPUT" else "assistant"
                content = str(record.get("content", ""))
                
                # If there are tool calls, inject them as part of the agent's thought process
                if record.get("tool_calls"):
                    tool_calls_str = json.dumps(record["tool_calls"], indent=2)
                    content += f"\n\n[EXECUTED_TOOLS]:\n{tool_calls_str}"
                
                # Only insert if there's actual content
                if content.strip():
                    cursor.execute(
                        "INSERT INTO conversation_history (role, content) VALUES (?, ?)", 
                        (role, content)
                    )
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"Error parsing line for {agent_name}: {e}")
                
    conn.commit()
    conn.close()
    print(f"Memory successfully injected into {agent_name}'s neural network.")

print("Initiating Genesis Memory Siphon...")
for agent in agents:
    build_memory_injector(agent)
print("All agents now possess the memory of the Sovereign Commander.")
