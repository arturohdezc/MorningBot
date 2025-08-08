import json
import re
import os
from typing import Dict, Any
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_date
from .ai_fallbacks import with_ai_fallback, fallback_route_instruction
from .ai_client import ai_client

@with_ai_fallback(fallback_route_instruction)
async def route_instruction(instruction: str) -> Dict[str, Any]:
    """
    Analyze instruction with AI and return JSON with intent and arguments
    
    Args:
        instruction: User instruction in natural language
    
    Returns:
        Dict with format: {"intent": "add|recur|listar|completar|ajustar_prefs|brief", "args": {...}}
        If ambiguous: {"intent": "clarify", "message": "..."}
        If AI fails: uses fallback heuristic
    """
    
    system_prompt = """Eres un asistente que analiza instrucciones de usuario para un bot de Telegram de gestión de tareas.

Debes clasificar la instrucción en uno de estos intents:
- "add": crear tarea simple
- "recur": crear tarea recurrente 
- "listar": mostrar tareas
- "completar": marcar tarea como hecha
- "ajustar_prefs": modificar preferencias
- "brief": generar resumen matutino

Para cada intent, extrae los argumentos relevantes:

ADD/RECUR args:
- title: título de la tarea
- due: fecha en formato YYYY-MM-DD (si menciona "hoy" usa fecha actual, "mañana" usa mañana)
- time: hora en formato HH:MM (24h)
- priority: "high", "medium", o "low"
- rrule: para recurrentes, formato iCal (ej: "FREQ=DAILY", "FREQ=WEEKLY;BYDAY=MO", "FREQ=MONTHLY;BYMONTHDAY=1")

COMPLETAR args:
- id: ID de la tarea

AJUSTAR_PREFS args:
- preference_instruction: instrucción completa para modificar preferencias

Si la instrucción es ambigua o no está clara, devuelve:
{"intent": "clarify", "message": "Descripción de qué necesitas aclarar"}

Responde SOLO con JSON válido, sin explicaciones adicionales."""

    prompt = f'Instrucción del usuario: "{instruction}"'
    
    try:
        response_text = await ai_client.generate_content(prompt, system_prompt)
        
        # Clean up the response to extract JSON
        result_text = response_text
        if result_text.startswith("```json"):
            result_text = result_text[7:-3]
        elif result_text.startswith("```"):
            result_text = result_text[3:-3]
        
        result = json.loads(result_text)
        
        # Validate the response format
        if "intent" not in result:
            raise ValueError("Missing intent in response")
        
        return result
        
    except Exception as e:
        # Let the decorator handle the fallback
        raise e

