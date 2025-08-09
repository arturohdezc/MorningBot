import re
from typing import List
from telegram import Bot

def paginate_message(content: str, max_length: int = 3800) -> List[str]:
    """
    Split message into chunks ≤3800 characters respecting word boundaries and formatting
    
    Args:
        content: Message content to paginate
        max_length: Maximum length per chunk (default 3800 for Telegram)
    
    Returns:
        List of message chunks
    """
    if len(content) <= max_length:
        return [content]
    
    chunks = []
    current_chunk = ""
    
    # Split by lines first to preserve formatting
    lines = content.split('\n')
    
    for line in lines:
        # If adding this line would exceed the limit
        if len(current_chunk) + len(line) + 1 > max_length:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            
            # If a single line is too long, split it by words
            if len(line) > max_length:
                words = line.split(' ')
                temp_line = ""
                
                for word in words:
                    if len(temp_line) + len(word) + 1 > max_length:
                        if temp_line:
                            if current_chunk:
                                current_chunk += '\n' + temp_line
                            else:
                                current_chunk = temp_line
                            
                            if len(current_chunk) > max_length:
                                chunks.append(current_chunk.strip())
                                current_chunk = ""
                            
                            temp_line = word
                        else:
                            # Single word is too long, force split
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                                current_chunk = ""
                            chunks.append(word[:max_length])
                            temp_line = word[max_length:]
                    else:
                        if temp_line:
                            temp_line += ' ' + word
                        else:
                            temp_line = word
                
                if temp_line:
                    if current_chunk:
                        current_chunk += '\n' + temp_line
                    else:
                        current_chunk = temp_line
            else:
                current_chunk = line
        else:
            if current_chunk:
                current_chunk += '\n' + line
            else:
                current_chunk = line
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

async def send_paginated_message(bot: Bot, chat_id: int, content: str, parse_mode: str = None, reply_markup=None):
    """
    Send message automatically paginated if content exceeds limit
    
    Args:
        bot: Telegram bot instance
        chat_id: Chat ID to send to
        content: Message content
        parse_mode: Parse mode (Markdown, HTML, etc.)
        reply_markup: Keyboard markup (only applied to last message)
    """
    chunks = paginate_message(content)
    
    for i, chunk in enumerate(chunks):
        # Only add reply_markup to the last message
        markup = reply_markup if i == len(chunks) - 1 else None
        
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=chunk,
                parse_mode=parse_mode,
                reply_markup=markup
            )
        except Exception as e:
            print(f"Error sending paginated message chunk {i+1}: {e}")
            # Try without parse_mode if it fails
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=chunk,
                    reply_markup=markup
                )
            except Exception as e2:
                print(f"Error sending plain message chunk {i+1}: {e2}")

def format_brief(news_data: dict = None, emails_data: dict = None, calendar_data: list = None, tasks_data: list = None) -> str:
    """
    Format brief message with all components
    
    Args:
        news_data: News summary data
        emails_data: Email data with counts
        calendar_data: Calendar events
        tasks_data: Tasks data
    
    Returns:
        Formatted brief message
    """
    message = "📰 *Brief Matutino*\n\n"
    
    # News section
    if news_data:
        message += "🗞 *Noticias*\n"
        message += news_data.get('summary', 'No hay noticias disponibles')
        message += "\n\n"
    
    # Email section
    if emails_data:
        message += "📧 *Correos Importantes*\n"
        message += f"Encontrados: {emails_data.get('found', 0)} | "
        message += f"Considerados: {emails_data.get('considered', 0)} | "
        message += f"Seleccionados: {emails_data.get('selected', 0)}\n"
        
        # Show account info if multi-account
        accounts = emails_data.get('accounts', [])
        if len(accounts) > 1:
            message += f"Cuentas: {len(accounts)} Gmail\n"
        
        message += "\n"
        
        if emails_data.get('emails'):
            for i, email in enumerate(emails_data['emails'][:5], 1):  # Limit to 5
                # Extract sender name (remove email part)
                sender = email.get('sender', 'Desconocido')
                if '<' in sender:
                    sender_name = sender.split('<')[0].strip()
                    if sender_name:
                        sender = sender_name
                
                message += f"**{i}. {email.get('subject', 'Sin asunto')}**\n"
                message += f"👤 **De:** {sender}"
                
                # Show account if multi-account
                if email.get('account') and email['account'] != 'me':
                    account_short = email['account'].split('@')[0] if '@' in email['account'] else email['account']
                    message += f" ({account_short})"
                
                message += "\n"
                
                # Add importance reason if available
                if email.get('importance_reason'):
                    message += f"💡 **Por qué es importante:** {email['importance_reason']}\n"
                elif email.get('body'):
                    # Show first 100 chars of body as preview
                    body_preview = email['body'][:100].replace('\n', ' ').strip()
                    if len(email['body']) > 100:
                        body_preview += "..."
                    message += f"📄 **Resumen:** {body_preview}\n"
                
                message += "\n"
    
    # Calendar section
    if calendar_data:
        message += "📅 *Eventos de Hoy*\n"
        if calendar_data:
            for event in calendar_data[:5]:  # Limit to 5
                message += f"• {event.get('summary', 'Sin título')}\n"
                if event.get('start'):
                    message += f"  {event['start']}\n"
                message += "\n"
        else:
            message += "No hay eventos programados\n\n"
    
    # Tasks section
    if tasks_data:
        message += "✅ *Tareas Pendientes*\n"
        if tasks_data:
            for task in tasks_data[:5]:  # Limit to 5
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.get("priority", "medium"), "🟡")
                message += f"• {priority_emoji} {task.get('title', 'Sin título')}\n"
        else:
            message += "No hay tareas pendientes\n"
    
    return message

def format_tasks_list(tasks: list) -> str:
    """
    Format tasks list with proper structure
    
    Args:
        tasks: List of task dictionaries
    
    Returns:
        Formatted tasks message
    """
    if not tasks:
        return "📋 *Tareas de hoy*\n\nNo tienes tareas pendientes para hoy. ¡Buen trabajo! ✅"
    
    message = "📋 *Tareas de hoy*\n\n"
    
    for i, task in enumerate(tasks, 1):
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.get("priority", "medium"), "🟡")
        
        due_time = ""
        if task.get("due"):
            try:
                from datetime import datetime
                due_dt = datetime.fromisoformat(task["due"].replace('Z', '+00:00'))
                due_time = f" - {due_dt.strftime('%H:%M')}"
            except:
                pass
        
        message += f"{i}. {priority_emoji} {task['title']}{due_time}\n"
        
        if task.get("notes"):
            message += f"   📝 {task['notes']}\n"
        
        message += f"   ID: `{task['id']}`\n\n"
    
    return message

def format_preferences(prefs: dict) -> str:
    """
    Format preferences for display
    
    Args:
        prefs: Preferences dictionary
    
    Returns:
        Formatted preferences message
    """
    message = "⚙️ *Preferencias Actuales*\n\n"
    
    message += f"📊 Top K correos: {prefs.get('top_k', 10)}\n"
    message += f"📬 Solo no leídos: {'Sí' if prefs.get('only_unread', False) else 'No'}\n"
    message += f"⚡ Importancia mínima: {prefs.get('min_importance', 'any')}\n\n"
    
    if prefs.get('priority_domains'):
        message += "🎯 *Dominios Prioritarios:*\n"
        for domain in prefs['priority_domains']:
            message += f"• {domain}\n"
        message += "\n"
    
    if prefs.get('priority_senders'):
        message += "👤 *Remitentes Prioritarios:*\n"
        for sender in prefs['priority_senders']:
            message += f"• {sender}\n"
        message += "\n"
    
    if prefs.get('blocked_domains'):
        message += "🚫 *Dominios Bloqueados:*\n"
        for domain in prefs['blocked_domains']:
            message += f"• {domain}\n"
        message += "\n"
    
    if prefs.get('blocked_senders'):
        message += "🚫 *Remitentes Bloqueados:*\n"
        for sender in prefs['blocked_senders']:
            message += f"• {sender}\n"
        message += "\n"
    
    if prefs.get('blocked_keywords'):
        message += "🚫 *Palabras Clave Bloqueadas:*\n"
        for keyword in prefs['blocked_keywords']:
            message += f"• {keyword}\n"
    
    return message