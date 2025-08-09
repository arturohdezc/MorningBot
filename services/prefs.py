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

async def update_prefs_from_instruction(instruction: str) -> Dict:
    """
    Update preferences from natural language instruction using AI
    
    Args:
        instruction: Natural language instruction
    
    Returns:
        Updated preferences dict
    """
    prefs = load_preferences()
    
    try:
        # Use AI to interpret the instruction
        from .ai_client import ai_client
        
        system_prompt = f"""
Eres un asistente que interpreta instrucciones para filtros de email.

Preferencias actuales:
- Dominios bloqueados: {prefs.get('blocked_domains', [])}
- Remitentes bloqueados: {prefs.get('blocked_senders', [])}
- Palabras clave bloqueadas: {prefs.get('blocked_keywords', [])}
- Dominios prioritarios: {prefs.get('priority_domains', [])}
- Remitentes prioritarios: {prefs.get('priority_senders', [])}

Instrucción del usuario: "{instruction}"

Responde SOLO con un JSON válido con los cambios a aplicar:
{{
  "action": "block" | "prioritize" | "unblock" | "modify",
  "type": "domain" | "sender" | "keyword",
  "values": ["valor1", "valor2"],
  "explanation": "Explicación de lo que se hizo"
}}

Ejemplos:
- "no me des correos de oracle" → {{"action": "block", "type": "keyword", "values": ["oracle"], "explanation": "Bloqueado emails que contengan 'oracle'"}}
- "prioriza emails de mi jefe juan@empresa.com" → {{"action": "prioritize", "type": "sender", "values": ["juan@empresa.com"], "explanation": "Priorizados emails de juan@empresa.com"}}
"""
        
        response = await ai_client.generate_content(instruction, system_prompt)
        
        # Parse AI response
        import json
        try:
            ai_response = json.loads(response.strip())
        except:
            # Fallback to basic parsing
            return update_prefs_basic(instruction, prefs)
        
        # Apply changes based on AI interpretation
        action = ai_response.get('action')
        pref_type = ai_response.get('type')
        values = ai_response.get('values', [])
        
        if action == 'block':
            if pref_type == 'domain':
                prefs['blocked_domains'].extend([v for v in values if v not in prefs['blocked_domains']])
            elif pref_type == 'sender':
                prefs['blocked_senders'].extend([v for v in values if v not in prefs['blocked_senders']])
            elif pref_type == 'keyword':
                prefs['blocked_keywords'].extend([v for v in values if v not in prefs['blocked_keywords']])
        
        elif action == 'prioritize':
            if pref_type == 'domain':
                prefs['priority_domains'].extend([v for v in values if v not in prefs['priority_domains']])
            elif pref_type == 'sender':
                prefs['priority_senders'].extend([v for v in values if v not in prefs['priority_senders']])
        
        elif action == 'unblock':
            if pref_type == 'domain':
                prefs['blocked_domains'] = [d for d in prefs['blocked_domains'] if d not in values]
            elif pref_type == 'sender':
                prefs['blocked_senders'] = [s for s in prefs['blocked_senders'] if s not in values]
            elif pref_type == 'keyword':
                prefs['blocked_keywords'] = [k for k in prefs['blocked_keywords'] if k not in values]
        
        save_preferences(prefs)
        prefs['_ai_explanation'] = ai_response.get('explanation', 'Preferencias actualizadas')
        return prefs
        
    except Exception as e:
        print(f"Error using AI for preferences: {e}")
        # Fallback to basic parsing
        return update_prefs_basic(instruction, prefs)

def update_prefs_basic(instruction: str, prefs: Dict) -> Dict:
    """Fallback basic preference parsing"""
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
    prefs['_ai_explanation'] = 'Preferencias actualizadas con análisis básico'
    return prefs