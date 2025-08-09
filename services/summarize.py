import os
from typing import List, Dict
from .ai_fallbacks import with_ai_fallback, fallback_summarize_news
from .ai_client import ai_client

@with_ai_fallback(fallback_summarize_news)
async def summarize_news_list(news_items: List[Dict]) -> str:
    """
    Summarize news list using Gemini
    
    Args:
        news_items: List of news items
    
    Returns:
        Summarized news text
    """
    if not news_items:
        return "No hay noticias disponibles."
    
    try:
        # Prepare news text for summarization
        news_text = ""
        for item in news_items[:15]:  # Limit to avoid token limits
            news_text += f"Título: {item.get('title', '')}\n"
            news_text += f"Fuente: {item.get('source', '')}\n"
            if item.get('summary'):
                news_text += f"Resumen: {item['summary'][:200]}...\n"
            news_text += f"Fecha: {item.get('published', '')}\n\n"
        
        system_prompt = """
Eres un asistente que resume noticias para un brief matutino ejecutivo mexicano.

ESTRUCTURA REQUERIDA (usa exactamente estos emojis y formato):

**TL;DR:** [1-2 líneas con lo más relevante del día]

**📈 ECONOMÍA:**
México: [noticias económicas de México]
US: [noticias económicas de Estados Unidos]  
Mundial: [noticias económicas internacionales]

**🌍 NOTICIAS GENERALES:**
México: [eventos importantes de México]
US: [eventos importantes de Estados Unidos]
Mundial: [eventos importantes internacionales]

**🤖 IA & TECH:**
[Innovaciones en inteligencia artificial, tecnología, startups]

**✈️ VIAJES:**
[Noticias de turismo, aerolíneas, hoteles, destinos]

REGLAS:
- Si no hay noticias de una subcategoría, escribe "Sin noticias relevantes"
- Máximo 2 bullets por subcategoría
- Tono profesional, conciso
- Enfócate en impacto económico y empresarial
- Máximo 400 palabras total
"""
        
        prompt = f"Noticias a resumir:\n{news_text}"
        
        response_text = await ai_client.generate_content(prompt, system_prompt)
        return response_text
        
    except Exception as e:
        # Let the decorator handle the fallback
        raise e