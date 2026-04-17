import json
import os

FILE = "ai_incident_state.json"

def save_incident_state(data: dict):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

def get_incident_state():
    if not os.path.exists(FILE):
        return None
    with open(FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def clear_incident_state():
    if os.path.exists(FILE):
        os.remove(FILE)
