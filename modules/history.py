import json
import os

HISTORY_FILE = "output/history.json"

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_history(history):
    os.makedirs("output", exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4)

def is_seen(url):
    history = load_history()
    return url in history

def mark_seen(url):
    history = load_history()
    if url not in history:
        history.append(url)
        save_history(history)
