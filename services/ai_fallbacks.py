import functools
import logging
from typing import Callable, Any, Dict, List

logger = logging.getLogger(__name__)

def with_ai_fallback(fallback_function: Callable):
    """Decorator that wraps AI functions with fallback mechanisms"""
    def decorator(ai_function: Callable):
        @functools.wraps(ai_function)
        async def wrapper(*args, **kwargs):
            try:
                return await ai_function(*args, **kwargs)
            except Exception as e:
                logger.warning(f"AI function {ai_function.__name__} failed: {e}, using fallback")
                try:
                    return await fallback_function(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(f"Fallback function also failed: {fallback_error}")
                    return get_safe_default(ai_function.__name__)
        return wrapper
    return decorator

def get_safe_default(function_name: str) -> Any:
    """Get safe default return value based on function name"""
    if "summarize" in function_name.lower():
        return "Resumen no disponible (error en IA y fallback)"
    elif "rank" in function_name.lower():
        return {"emails": [], "found": 0, "considered": 0, "selected": 0, "rationale": "Error en ranking"}
    elif "route" in function_name.lower():
        return {"intent": "clarify", "message": "Error en procesamiento de IA"}
    else:
        return "Error en función de IA"

async def fallback_summarize_news(news_items: List[Dict]) -> str:
    """Fallback for news summarization"""
    if not news_items:
        return "No hay noticias disponibles."
    
    fallback = "📰 **Resumen de noticias (modo fallback):**\n\n"
    for i, item in enumerate(news_items[:5], 1):
        title = item.get('title', 'Sin título')
        source = item.get('source', 'Fuente desconocida')
        fallback += f"{i}. {title} ({source})\n"
    return fallback

async def fallback_rank_emails(emails: List[Dict], top_k: int = 10) -> Dict:
    """Fallback for email ranking using basic heuristics"""
    if not emails:
        return {"emails": [], "found": 0, "considered": 0, "selected": 0, "rationale": "No hay correos"}
    
    # Simple heuristic: prioritize shorter subjects and avoid automated emails
    scored_emails = []
    for email in emails:
        score = 0
        sender = email.get('sender', '').lower()
        subject = email.get('subject', '').lower()
        
        # Higher score for urgent keywords
        if any(word in subject for word in ['urgent', 'importante', 'meeting', 'reunión']):
            score += 5
        
        # Lower score for automated emails
        if any(word in sender for word in ['noreply', 'no-reply', 'automated']):
            score -= 5
        
        # Higher score for shorter subjects
        if len(subject) < 50:
            score += 2
        
        scored_emails.append((email, score))
    
    scored_emails.sort(key=lambda x: x[1], reverse=True)
    selected_emails = [email for email, score in scored_emails[:top_k]]
    
    return {
        "emails": selected_emails,
        "found": len(emails),
        "considered": len(emails),
        "selected": len(selected_emails),
        "rationale": "Selección usando heurística básica (IA no disponible)"
    }

async def fallback_route_instruction(instruction: str) -> Dict:
    """Fallback for instruction routing using regex patterns"""
    instruction_lower = instruction.lower()
    
    if any(word in instruction_lower for word in ['add', 'añadir', 'crear', 'necesito']):
        return {"intent": "add", "args": {"title": instruction, "priority": "medium"}}
    elif any(word in instruction_lower for word in ['recur', 'repetir', 'cada', 'diario']):
        return {"intent": "recur", "args": {"title": instruction, "rrule": "FREQ=DAILY", "priority": "medium"}}
    elif any(word in instruction_lower for word in ['list', 'mostrar', 'tareas']):
        return {"intent": "listar", "args": {}}
    elif any(word in instruction_lower for word in ['done', 'hecho', 'completar']):
        import re
        id_match = re.search(r't_[a-f0-9]{8}', instruction)
        if id_match:
            return {"intent": "completar", "args": {"id": id_match.group(0)}}
        else:
            return {"intent": "clarify", "message": "No pude identificar el ID de la tarea"}
    elif any(word in instruction_lower for word in ['brief', 'resumen', 'noticias']):
        return {"intent": "brief", "args": {}}
    elif any(word in instruction_lower for word in ['bloquear', 'preferencias', 'ajustar']):
        return {"intent": "ajustar_prefs", "args": {"preference_instruction": instruction}}
    else:
        return {"intent": "clarify", "message": "No pude entender la instrucción (modo fallback)"}
