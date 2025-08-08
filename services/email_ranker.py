import os
import json
from typing import List, Dict, Tuple
from .ai_fallbacks import with_ai_fallback, fallback_rank_emails
from .ai_client import ai_client

def load_preferences() -> Dict:
    """Load email preferences"""
    try:
        if os.path.exists("preferences.json"):
            with open("preferences.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
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
    except Exception as e:
        print(f"Error loading preferences: {e}")
        return {"top_k": 10, "blocked_keywords": []}

def prefilter_by_prefs(emails: List[Dict]) -> Tuple[List[Dict], int]:
    """
    Pre-filter emails by preferences
    
    Args:
        emails: List of email data
    
    Returns:
        Tuple of (filtered_emails, original_count)
    """
    prefs = load_preferences()
    original_count = len(emails)
    
    filtered = []
    
    for email in emails:
        sender = email.get('sender', '').lower()
        subject = email.get('subject', '').lower()
        
        # Check blocked keywords
        blocked = False
        for keyword in prefs.get('blocked_keywords', []):
            if keyword.lower() in subject or keyword.lower() in sender:
                blocked = True
                break
        
        if blocked:
            continue
        
        # Check blocked domains
        for domain in prefs.get('blocked_domains', []):
            if domain.lower() in sender:
                blocked = True
                break
        
        if blocked:
            continue
        
        # Check blocked senders
        for blocked_sender in prefs.get('blocked_senders', []):
            if blocked_sender.lower() in sender:
                blocked = True
                break
        
        if blocked:
            continue
        
        filtered.append(email)
    
    return filtered, original_count

@with_ai_fallback(fallback_rank_emails)
async def rank_emails_with_gemini(emails: List[Dict], top_k: int = 10) -> Dict:
    """
    Rank emails using Gemini and return top_k
    
    Args:
        emails: Pre-filtered emails
        top_k: Number of top emails to return
    
    Returns:
        Dict with ranked emails and metadata
    """
    if not emails:
        return {
            "emails": [],
            "found": 0,
            "considered": 0,
            "selected": 0,
            "rationale": "No emails to process"
        }
    
    try:
        prefs = load_preferences()
        
        # Prepare email data for Gemini
        email_summaries = []
        for i, email in enumerate(emails[:50]):  # Limit to avoid token limits
            summary = f"""
Email {i+1}:
Remitente: {email.get('sender', 'Unknown')}
Asunto: {email.get('subject', 'No Subject')}
Para: {email.get('to', '')}
Fecha: {email.get('date', '')}
Cuerpo (primeras líneas): {email.get('body', '')[:200]}...
"""
            email_summaries.append(summary)
        
        emails_text = "\n".join(email_summaries)
        
        system_prompt = f"""
Eres un asistente que selecciona los correos más relevantes de AYER para un brief matutino.

Criterios de priorización:
1. Correos dirigidos directamente al usuario (To:) > Copia (Cc:)
2. Remitentes de dominios prioritarios: {prefs.get('priority_domains', [])}
3. Remitentes prioritarios: {prefs.get('priority_senders', [])}
4. Evitar newsletters, promociones, notificaciones automáticas
5. Priorizar urgencia, reuniones, decisiones pendientes
6. Contenido relevante para trabajo/personal importante

Selecciona los correos MÁS importantes y devuelve SOLO un JSON con este formato:
{{
  "selected": [1, 3, 5, 7, 9],
  "rationale": "Breve explicación de por qué estos correos son los más importantes"
}}

Los números deben corresponder a los Email 1, Email 2, etc. de la lista.
"""
        
        prompt = f"Selecciona los {top_k} correos más importantes de esta lista:\n\n{emails_text}"
        
        response_text = await ai_client.generate_content(prompt, system_prompt)
        result_text = response_text
        
        # Clean up JSON response
        if result_text.startswith("```json"):
            result_text = result_text[7:-3]
        elif result_text.startswith("```"):
            result_text = result_text[3:-3]
        
        result = json.loads(result_text)
        
        # Extract selected emails
        selected_emails = []
        for idx in result.get("selected", []):
            if 1 <= idx <= len(emails):
                selected_emails.append(emails[idx - 1])  # Convert to 0-based index
        
        # Get unique accounts
        accounts = list(set(email.get('account', 'me') for email in emails))
        
        return {
            "emails": selected_emails[:top_k],
            "found": len(emails),
            "considered": min(len(emails), 50),
            "selected": len(selected_emails),
            "accounts": accounts,
            "rationale": result.get("rationale", "Selección basada en relevancia")
        }
        
    except Exception as e:
        # Let the decorator handle the fallback
        raise e