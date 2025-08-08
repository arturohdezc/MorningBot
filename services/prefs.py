import json
import os
from typing import Dict

PREFS_FILE = "preferences.json"

def load_preferences() -> Dict:
    """Load preferences from JSON file"""
    try:
        if os.path.exists(PREFS_FILE):
            with open(PREFS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return get_default_preferences()
    except Exception as e:
        print(f"Error loading preferences: {e}")
        return get_default_preferences()

def save_preferences(prefs: Dict) -> bool:
    """Save preferences to JSON file"""
    try:
        with open(PREFS_FILE, 'w', encoding='utf-8') as f:
            json.dump(prefs, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving preferences: {e}")
        return False

def get_default_preferences() -> Dict:
    """Get default preferences"""
    return {
        "top_k": 10,
        "only_unread": False,
        "min_importance": "any",
        "priority_domains": [],
        "priority_senders": [],
        "blocked_domains": [],
        "blocked_senders": [],
        "blocked_keywords": ["newsletter", "promo", "boletín", "no-reply"]
    }

def update_prefs_from_instruction(instruction: str) -> Dict:
    """
    Update preferences from natural language instruction (placeholder)
    
    Args:
        instruction: Natural language instruction
    
    Returns:
        Updated preferences dict
    """
    prefs = load_preferences()
    
    instruction_lower = instruction.lower()
    
    # Basic pattern matching for common preference changes
    if "no me des" in instruction_lower or "bloquear" in instruction_lower:
        # Extract domain or keyword to block
        words = instruction_lower.split()
        for word in words:
            if "@" in word or "." in word:
                # Looks like a domain
                if word not in prefs["blocked_domains"]:
                    prefs["blocked_domains"].append(word)
            elif len(word) > 3 and word not in ["correos", "emails", "de"]:
                # Looks like a keyword
                if word not in prefs["blocked_keywords"]:
                    prefs["blocked_keywords"].append(word)
    
    save_preferences(prefs)
    return prefs