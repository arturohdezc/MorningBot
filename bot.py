import os
import logging
import base64
from datetime import datetime
from typing import Dict, List
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from dotenv import load_dotenv

# Import services
from services.tasks_local import list_today_sorted, add_task, add_recurrent_task, complete_task
from services.router import route_instruction
from services.formatter import send_paginated_message, format_tasks_list, format_preferences, format_brief
from services.news import fetch_news_from_rss
from services.summarize import summarize_news_list
from services.gmail_multi_account import fetch_yesterdays_emails
from services.email_ranker import prefilter_by_prefs, rank_emails_with_gemini
from services.calendar_reader import fetch_todays_events
from services.tasks_reader import fetch_pending_tasks
from services.prefs import load_preferences, update_prefs_from_instruction
from services.ai_client import ai_client
from services.ai_config import (
    get_current_config, update_ai_provider, get_available_models, 
    format_ai_config_message
)
import asyncio

# Load environment variables
load_dotenv()

# Setup Google credentials for Render deployment
def setup_google_credentials_for_render():
    """Decode Google credentials from environment variables for Render deployment"""
    try:
        # Decode credentials.json from base64 if available
        credentials_b64 = os.getenv('CREDENTIALS_JSON_BASE64')
        if credentials_b64:
            credentials_data = base64.b64decode(credentials_b64).decode('utf-8')
            with open('credentials.json', 'w') as f:
                f.write(credentials_data)
            print("✅ credentials.json decoded from environment")
        
        # Decode token.json from base64 if available  
        token_b64 = os.getenv('TOKEN_JSON_BASE64')
        if token_b64:
            token_data = base64.b64decode(token_b64).decode('utf-8')
            with open('token.json', 'w') as f:
                f.write(token_data)
            print("✅ token.json decoded from environment")
            
    except Exception as e:
        print(f"⚠️ Warning: Could not decode Google credentials: {e}")
        print("📋 Make sure CREDENTIALS_JSON_BASE64 and TOKEN_JSON_BASE64 are set in Render")

# Setup credentials for Render
setup_google_credentials_for_render()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get timezone from environment
TIMEZONE = os.getenv("TIMEZONE", "America/Mexico_City")

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Return ReplyKeyboard with main action buttons"""
    keyboard = [
        [KeyboardButton("Brief 🗞"), KeyboardButton("Tareas de hoy ✅")],
        [KeyboardButton("Añadir tarea ➕"), KeyboardButton("Recurrente ♻️")],
        [KeyboardButton("Configurar IA 🤖"), KeyboardButton("Preferencias ⚙️")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def get_task_inline_keyboard(task_id: str) -> InlineKeyboardMarkup:
    """Return inline keyboard for task actions"""
    keyboard = [
        [InlineKeyboardButton("Marcar como hecha ✅", callback_data=f"complete_{task_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    welcome_message = """
¡Hola! Soy tu asistente personal de Telegram 🤖

Usa los botones de abajo para acceso rápido o estos comandos:
• /brief - Resumen matutino completo
• /tasks - Ver tareas de hoy
• /add <descripción> - Crear nueva tarea
• /recur <descripción> - Crear tarea recurrente
• /done <id> - Marcar tarea como completada
• /ia <instrucción> - Procesar cualquier instrucción con IA
• /prefs - Ver preferencias actuales
• /ajusta <instrucción> - Modificar preferencias
• /aiinfo - Ver información del proveedor de IA

¡Empecemos a organizarte! 📋✨
"""
    await update.message.reply_text(welcome_message, reply_markup=get_main_keyboard())

async def cmd_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display today's tasks using list_today_sorted() plus Google Tasks if sync enabled"""
    try:
        # Get local tasks for today
        local_tasks = list_today_sorted(TIMEZONE)
        
        message = "📋 *Tareas de hoy*\n\n"
        
        if not local_tasks:
            message += "No tienes tareas pendientes para hoy. ¡Buen trabajo! ✅"
        else:
            for i, task in enumerate(local_tasks, 1):
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.get("priority", "medium"), "🟡")
                due_time = ""
                if task.get("due"):
                    try:
                        due_dt = datetime.fromisoformat(task["due"].replace('Z', '+00:00'))
                        due_time = f" - {due_dt.strftime('%H:%M')}"
                    except:
                        pass
                
                message += f"{i}. {priority_emoji} {task['title']}{due_time}\n"
                if task.get("notes"):
                    message += f"   📝 {task['notes']}\n"
                message += f"   ID: `{task['id']}`\n\n"
        
        # Add Google Tasks if sync is enabled
        if os.getenv("SYNC_GOOGLE_TASKS", "false").lower() == "true":
            try:
                from services.tasks_reader import fetch_pending_tasks
                google_tasks = await fetch_pending_tasks()
                if google_tasks:
                    message += "\n📱 *Google Tasks*\n\n"
                    for task in google_tasks[:5]:  # Limit to 5
                        message += f"• {task.get('title', 'Sin título')}\n"
            except Exception as e:
                logger.error(f"Error fetching Google Tasks: {e}")
        
        # Add inline keyboard if there are tasks
        reply_markup = None
        if local_tasks:
            # Create inline keyboard with complete buttons for first few tasks
            buttons = []
            for task in local_tasks[:3]:  # Limit to first 3 tasks to avoid too many buttons
                buttons.append([InlineKeyboardButton(
                    f"✅ Completar: {task['title'][:20]}...", 
                    callback_data=f"complete_{task['id']}"
                )])
            if buttons:
                reply_markup = InlineKeyboardMarkup(buttons)
        
        # Use paginated message sending
        await send_paginated_message(
            bot=context.bot,
            chat_id=update.effective_chat.id,
            content=message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in cmd_tasks: {e}")
        await update.message.reply_text("❌ Error al obtener las tareas. Intenta de nuevo.")

async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create task using router and add_task()"""
    if not context.args:
        await update.message.reply_text("❌ Uso: /add <descripción de la tarea>")
        return
    
    instruction = " ".join(context.args)
    
    try:
        # Route the instruction through AI
        result = await route_instruction(f"add {instruction}")
        
        if result["intent"] == "clarify":
            await update.message.reply_text(f"🤔 {result['message']}")
            return
        
        args = result.get("args", {})
        title = args.get("title", instruction)
        notes = args.get("notes", "")
        priority = args.get("priority", "medium")
        
        # Parse due date and time
        due = None
        if args.get("due") and args.get("time"):
            due_str = f"{args['due']} {args['time']}"
            due = datetime.fromisoformat(due_str)
        elif args.get("due"):
            due = datetime.fromisoformat(f"{args['due']} 09:00")
        
        # Create the task
        task_id = add_task(title, notes, priority, due)
        
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "🟡")
        message = f"✅ Tarea creada:\n\n{priority_emoji} {title}"
        
        if due:
            message += f"\n📅 {due.strftime('%Y-%m-%d %H:%M')}"
        
        message += f"\n🆔 ID: `{task_id}`"
        
        await send_paginated_message(
            bot=context.bot,
            chat_id=update.effective_chat.id,
            content=message,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in cmd_add: {e}")
        await update.message.reply_text("❌ Error al crear la tarea. Intenta de nuevo.")

async def cmd_recur(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create recurring task using router and add_recurrent_task()"""
    if not context.args:
        await update.message.reply_text("❌ Uso: /recur <descripción de la tarea recurrente>")
        return
    
    instruction = " ".join(context.args)
    
    try:
        # Route the instruction through AI
        result = await route_instruction(f"recur {instruction}")
        
        if result["intent"] == "clarify":
            await update.message.reply_text(f"🤔 {result['message']}")
            return
        
        args = result.get("args", {})
        title = args.get("title", instruction)
        notes = args.get("notes", "")
        priority = args.get("priority", "medium")
        rrule = args.get("rrule", "FREQ=DAILY")
        
        # Parse start due date
        start_due = None
        if args.get("due") and args.get("time"):
            due_str = f"{args['due']} {args['time']}"
            start_due = datetime.fromisoformat(due_str)
        elif args.get("due"):
            start_due = datetime.fromisoformat(f"{args['due']} 09:00")
        
        # Create the recurring task
        task_id = add_recurrent_task(title, rrule, notes, priority, start_due)
        
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "🟡")
        message = f"🔄 Tarea recurrente creada:\n\n{priority_emoji} {title}"
        message += f"\n📅 Patrón: {rrule}"
        
        if start_due:
            message += f"\n⏰ Inicio: {start_due.strftime('%Y-%m-%d %H:%M')}"
        
        message += f"\n🆔 ID: `{task_id}`"
        
        await send_paginated_message(
            bot=context.bot,
            chat_id=update.effective_chat.id,
            content=message,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in cmd_recur: {e}")
        await update.message.reply_text("❌ Error al crear la tarea recurrente. Intenta de nuevo.")

async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mark task as completed using complete_task(id)"""
    if not context.args:
        await update.message.reply_text("❌ Uso: /done <id_de_tarea>")
        return
    
    task_id = context.args[0]
    
    try:
        success = complete_task(task_id)
        
        if success:
            await update.message.reply_text(f"✅ Tarea `{task_id}` marcada como completada!")
        else:
            await update.message.reply_text(f"❌ No se encontró la tarea con ID `{task_id}`")
            
    except Exception as e:
        logger.error(f"Error in cmd_done: {e}")
        await update.message.reply_text("❌ Error al completar la tarea. Intenta de nuevo.")

async def cmd_ia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process full instruction through router and execute detected action"""
    if not context.args:
        await update.message.reply_text("❌ Uso: /ia <instrucción completa>")
        return
    
    instruction = " ".join(context.args)
    
    try:
        result = await route_instruction(instruction)
        intent = result["intent"]
        args = result.get("args", {})
        
        if intent == "clarify":
            await update.message.reply_text(f"🤔 {result['message']}")
            return
        
        elif intent == "add":
            # Execute add task
            title = args.get("title", instruction)
            notes = args.get("notes", "")
            priority = args.get("priority", "medium")
            
            due = None
            if args.get("due") and args.get("time"):
                due_str = f"{args['due']} {args['time']}"
                due = datetime.fromisoformat(due_str)
            elif args.get("due"):
                due = datetime.fromisoformat(f"{args['due']} 09:00")
            
            task_id = add_task(title, notes, priority, due)
            await update.message.reply_text(f"✅ Tarea creada: {title} (ID: `{task_id}`)", parse_mode='Markdown')
        
        elif intent == "recur":
            # Execute recurring task
            title = args.get("title", instruction)
            rrule = args.get("rrule", "FREQ=DAILY")
            notes = args.get("notes", "")
            priority = args.get("priority", "medium")
            
            task_id = add_recurrent_task(title, rrule, notes, priority)
            await update.message.reply_text(f"🔄 Tarea recurrente creada: {title} (ID: `{task_id}`)", parse_mode='Markdown')
        
        elif intent == "listar":
            # Execute list tasks
            await cmd_tasks(update, context)
        
        elif intent == "completar":
            # Execute complete task
            task_id = args.get("id")
            if task_id:
                success = complete_task(task_id)
                if success:
                    await update.message.reply_text(f"✅ Tarea `{task_id}` completada!")
                else:
                    await update.message.reply_text(f"❌ No se encontró la tarea `{task_id}`")
            else:
                await update.message.reply_text("❌ No se pudo identificar el ID de la tarea")
        
        elif intent == "brief":
            await cmd_brief(update, context)
        
        elif intent == "ajustar_prefs":
            instruction = args.get("preference_instruction", "")
            if instruction:
                try:
                    update_prefs_from_instruction(instruction)
                    await update.message.reply_text("✅ Preferencias actualizadas")
                except Exception as e:
                    await update.message.reply_text("❌ Error al actualizar preferencias")
            else:
                await update.message.reply_text("❌ No se pudo procesar la instrucción de preferencias")
        
        else:
            await update.message.reply_text(f"🤖 Intent detectado: {intent}, pero no implementado aún")
            
    except Exception as e:
        logger.error(f"Error in cmd_ia: {e}")
        await update.message.reply_text("❌ Error al procesar la instrucción. Intenta de nuevo.")

# Placeholder functions for existing commands (to be implemented later)
async def cmd_brief(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate morning brief with immediate response and background processing"""
    # Respond immediately to avoid Telegram timeout
    await update.message.reply_text("📰 Generando brief matutino... ⏳")
    
    # Process in background with shorter timeout
    task = asyncio.create_task(generate_brief_background(update, context))
    
    # Add error handling for the background task
    def handle_task_exception(task):
        if task.exception():
            logger.error(f"❌ Background task failed: {task.exception()}")
    
    task.add_done_callback(handle_task_exception)

async def generate_brief_background(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate brief in background to avoid Telegram timeouts"""
    try:
        logger.info("🔄 Starting brief generation in background")
        start_time = datetime.now()
        
        # For debugging, let's try a simpler approach first
        logger.info("📰 Starting simple sequential execution for debugging")
        
        # Initialize with default values
        news_data = {"summary": "📰 Noticias no disponibles", "count": 0}
        emails_data = {"found": 0, "considered": 0, "selected": 0, "emails": [], "rationale": "📧 Emails no disponibles"}
        calendar_data = []
        tasks_data = []
        
        # Try each operation individually with error handling
        try:
            logger.info("📰 Fetching news...")
            news_data = await asyncio.wait_for(fetch_and_summarize_news(), timeout=5.0)
            logger.info("✅ News fetched successfully")
        except Exception as e:
            import traceback
            logger.error(f"❌ News fetch failed: {e}")
            logger.error(f"📋 News traceback: {traceback.format_exc()}")
        
        try:
            logger.info("📧 Fetching emails...")
            emails_data = await asyncio.wait_for(fetch_and_rank_emails(), timeout=8.0)
            logger.info("✅ Emails fetched successfully")
        except Exception as e:
            import traceback
            logger.error(f"❌ Email fetch failed: {e}")
            logger.error(f"📋 Email traceback: {traceback.format_exc()}")
        
        try:
            logger.info("📅 Fetching calendar...")
            calendar_data = await asyncio.wait_for(fetch_todays_events(), timeout=3.0)
            logger.info("✅ Calendar fetched successfully")
        except Exception as e:
            logger.error(f"❌ Calendar fetch failed: {e}")
        
        try:
            logger.info("✅ Fetching tasks...")
            tasks_data = await asyncio.wait_for(fetch_all_tasks(), timeout=2.0)
            logger.info("✅ Tasks fetched successfully")
        except Exception as e:
            logger.error(f"❌ Tasks fetch failed: {e}")
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"⏱ Brief generation completed in {execution_time:.1f}s")
        
        # Format the brief
        logger.info("📝 Formatting brief message")
        brief_message = format_brief(news_data, emails_data, calendar_data, tasks_data)
        brief_message += f"\n⏱ Generado en {execution_time:.1f}s"
        
        # Send the final brief as a new message
        logger.info("📤 Sending brief message to user")
        await send_paginated_message(
            bot=context.bot,
            chat_id=update.effective_chat.id,
            content=brief_message,
            parse_mode='Markdown'
        )
        logger.info("✅ Brief sent successfully")
        
    except Exception as e:
        logger.error(f"❌ Error in generate_brief_background: {e}")
        import traceback
        logger.error(f"📋 Full traceback: {traceback.format_exc()}")
        
        # Send error message
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ Error al generar el brief: {str(e)}\nIntenta de nuevo."
            )
        except Exception as send_error:
            logger.error(f"❌ Failed to send error message: {send_error}")

async def fetch_and_summarize_news() -> Dict:
    """Fetch news and summarize with timeout"""
    try:
        logger.info("📰 Fetching news from RSS feeds")
        # Use default RSS feeds
        rss_urls = []  # Will use defaults in fetch_news_from_rss
        news_items = await fetch_news_from_rss(rss_urls)
        logger.info(f"📰 Found {len(news_items)} news items")
        
        if not news_items:
            logger.warning("📰 No news items found, using fallback")
            return {
                "summary": "📰 **Noticias no disponibles** - Error al obtener feeds RSS",
                "count": 0
            }
        
        logger.info("🤖 Summarizing news with AI")
        try:
            summary = await summarize_news_list(news_items)
            logger.info("✅ News summary completed")
        except Exception as ai_error:
            logger.warning(f"🤖 AI summarization failed: {ai_error}, using fallback")
            # Use fallback summarization
            from services.ai_fallbacks import fallback_summarize_news
            summary = await fallback_summarize_news(news_items)
        
        return {
            "summary": summary,
            "count": len(news_items)
        }
    except Exception as e:
        logger.error(f"❌ Error in fetch_and_summarize_news: {e}")
        return {
            "summary": "📰 **Error al obtener noticias** - Servicio temporalmente no disponible",
            "count": 0
        }

async def fetch_and_rank_emails() -> Dict:
    """Fetch and rank emails with timeout"""
    try:
        logger.info("📧 Fetching yesterday's emails")
        # Fetch yesterday's emails
        emails = await fetch_yesterdays_emails()
        logger.info(f"📧 Found {len(emails)} emails")
        
        if not emails:
            logger.warning("📧 No emails found")
            return {
                "found": 0,
                "considered": 0,
                "selected": 0,
                "emails": [],
                "rationale": "📧 **No hay correos de ayer** - Verifica configuración de Gmail"
            }
        
        # Pre-filter by preferences
        logger.info("🔍 Pre-filtering emails by preferences")
        filtered_emails, original_count = prefilter_by_prefs(emails)
        logger.info(f"🔍 Filtered to {len(filtered_emails)} emails from {original_count} total")
        
        # Rank with AI or fallback
        logger.info("🤖 Ranking emails with AI")
        try:
            ranked_result = await rank_emails_with_gemini(filtered_emails, top_k=10)
            logger.info(f"✅ Email ranking completed, selected {ranked_result.get('selected', 0)} emails")
        except Exception as ai_error:
            logger.warning(f"🤖 AI ranking failed: {ai_error}, using fallback")
            # Use fallback ranking
            from services.ai_fallbacks import fallback_rank_emails
            ranked_result = await fallback_rank_emails(filtered_emails, top_k=10)
        
        # Add original count
        ranked_result["found"] = original_count
        
        return ranked_result
        
    except Exception as e:
        logger.error(f"❌ Error in fetch_and_rank_emails: {e}")
        return {
            "found": 0,
            "considered": 0,
            "selected": 0,
            "emails": [],
            "rationale": "📧 **Error al procesar correos** - Servicio temporalmente no disponible"
        }

async def fetch_all_tasks() -> List[Dict]:
    """Fetch all tasks (local + Google Tasks if enabled)"""
    try:
        logger.info("✅ Fetching local tasks")
        # Get local tasks
        local_tasks = list_today_sorted(TIMEZONE)
        logger.info(f"✅ Found {len(local_tasks)} local tasks")
        
        # Get Google Tasks if sync enabled
        google_tasks = []
        if os.getenv("SYNC_GOOGLE_TASKS", "false").lower() == "true":
            try:
                logger.info("📱 Fetching Google Tasks")
                google_tasks = await fetch_pending_tasks()
                logger.info(f"📱 Found {len(google_tasks)} Google Tasks")
            except Exception as e:
                logger.error(f"❌ Error fetching Google Tasks: {e}")
        
        # Combine and limit
        all_tasks = local_tasks + google_tasks
        logger.info(f"✅ Total tasks: {len(all_tasks)}, limiting to 10 for brief")
        return all_tasks[:10]  # Limit to 10 for brief
        
    except Exception as e:
        logger.error(f"❌ Error in fetch_all_tasks: {e}")
        return []

async def cmd_prefs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current preferences"""
    try:
        prefs = load_preferences()
        message = format_preferences(prefs)
        
        await send_paginated_message(
            bot=context.bot,
            chat_id=update.effective_chat.id,
            content=message,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in cmd_prefs: {e}")
        await update.message.reply_text("❌ Error al obtener las preferencias.")

async def cmd_ajusta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adjust preferences using natural language"""
    if not context.args:
        await update.message.reply_text("❌ Uso: /ajusta <instrucción>\nEjemplo: /ajusta ya no me des correos de oracle")
        return
    
    instruction = " ".join(context.args)
    
    try:
        updated_prefs = update_prefs_from_instruction(instruction)
        await update.message.reply_text(
            f"✅ Preferencias actualizadas:\n\n"
            f"Instrucción: {instruction}\n\n"
            f"Cambios aplicados. Usa /prefs para ver el estado actual."
        )
    except Exception as e:
        logger.error(f"Error in cmd_ajusta: {e}")
        await update.message.reply_text("❌ Error al ajustar las preferencias.")

async def cmd_aiinfo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show AI provider information"""
    try:
        ai_info = ai_client.get_provider_info()
        
        message = "🤖 *Información del Proveedor de IA*\n\n"
        message += f"**Proveedor:** {ai_info['provider'].title()}\n"
        message += f"**Configurado:** {'✅ Sí' if ai_info['configured'] else '❌ No'}\n"
        
        if ai_info['provider'] == 'openrouter':
            message += f"**Modelo:** {ai_info.get('model', 'No especificado')}\n"
        
        if not ai_info['configured']:
            if ai_info['provider'] == 'gemini':
                message += "\n⚠️ Configura GEMINI_API_KEY en las variables de entorno"
            elif ai_info['provider'] == 'openrouter':
                message += "\n⚠️ Configura OPENROUTER_API_KEY en las variables de entorno"
        
        message += f"\n\n**Fallback:** Heurística local disponible si falla la IA"
        
        await send_paginated_message(
            bot=context.bot,
            chat_id=update.effective_chat.id,
            content=message,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in cmd_aiinfo: {e}")
        await update.message.reply_text("❌ Error al obtener información de IA.")

async def show_ai_config_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False) -> None:
    """Show AI configuration menu"""
    try:
        config = get_current_config()
        message = format_ai_config_message()
        
        # Create provider selection buttons
        keyboard = []
        
        # Provider buttons
        gemini_status = "✅" if config['gemini_configured'] else "❌"
        openrouter_status = "✅" if config['openrouter_configured'] else "❌"
        
        keyboard.append([
            InlineKeyboardButton(f"{gemini_status} Gemini", callback_data="ai_provider_gemini"),
            InlineKeyboardButton(f"{openrouter_status} OpenRouter", callback_data="ai_provider_openrouter")
        ])
        
        # Current config info
        current_provider = config['provider']
        current_model = config['model']
        keyboard.append([
            InlineKeyboardButton(f"📋 Actual: {current_provider.title()} ({current_model})", callback_data="ai_config_info")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(
                message, 
                parse_mode='Markdown', 
                reply_markup=reply_markup
            )
        else:
            await send_paginated_message(
                bot=context.bot,
                chat_id=update.effective_chat.id,
                content=message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error in show_ai_config_menu: {e}")
        await update.message.reply_text("❌ Error al mostrar configuración de IA.")

async def handle_provider_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, provider: str) -> None:
    """Handle AI provider selection"""
    try:
        models = get_available_models(provider)
        
        message = f"🤖 *Seleccionar Modelo para {provider.title()}*\n\n"
        message += "Elige el modelo que quieres usar:\n\n"
        
        keyboard = []
        for model in models:
            button_text = f"{model['name']}"
            callback_data = f"ai_model_{provider}_{model['id']}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        # Back button
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="ai_config_back")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in handle_provider_selection: {e}")
        await update.callback_query.edit_message_text("❌ Error al mostrar modelos.")

async def handle_model_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, provider: str, model: str) -> None:
    """Handle AI model selection"""
    try:
        # Update configuration
        config = update_ai_provider(provider, model)
        
        # Reload AI client with new configuration
        ai_client.reload_config()
        
        message = f"✅ *Configuración Actualizada*\n\n"
        message += f"**Proveedor:** {provider.title()}\n"
        message += f"**Modelo:** {model}\n\n"
        
        # Check if API key is configured
        current_config = get_current_config()
        if current_config['provider_configured']:
            message += "🟢 API Key configurada - IA activa\n"
        else:
            message += "🟡 Sin API Key - usando fallback heurístico\n"
        
        message += "\nLa configuración se aplicará inmediatamente."
        
        keyboard = [[InlineKeyboardButton("⬅️ Volver al menú", callback_data="ai_config_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in handle_model_selection: {e}")
        await update.callback_query.edit_message_text("❌ Error al actualizar configuración.")

# Button handlers
async def handle_button_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses from ReplyKeyboard"""
    text = update.message.text
    
    if text == "Brief 🗞":
        await cmd_brief(update, context)
    elif text == "Tareas de hoy ✅":
        await cmd_tasks(update, context)
    elif text == "Añadir tarea ➕":
        await update.message.reply_text(
            "📝 Escribe la descripción de tu nueva tarea:\n\n"
            "Ejemplo: 'Llamar al dentista mañana 3pm prioridad alta'"
        )
        context.user_data['waiting_for'] = 'add_task'
    elif text == "Recurrente ♻️":
        await update.message.reply_text(
            "🔄 Escribe la descripción de tu tarea recurrente:\n\n"
            "Ejemplo: 'Revisar correos cada día 9am' o 'Pagar renta cada primero de mes'"
        )
        context.user_data['waiting_for'] = 'recur_task'
    elif text == "Configurar IA 🤖":
        await show_ai_config_menu(update, context)
    elif text == "Preferencias ⚙️":
        await cmd_prefs(update, context)
    else:
        # Handle task creation from button flow
        if context.user_data.get('waiting_for') == 'add_task':
            # Process as add task
            try:
                result = await route_instruction(f"add {text}")
                if result["intent"] == "clarify":
                    await update.message.reply_text(f"🤔 {result['message']}")
                    return
                
                args = result.get("args", {})
                title = args.get("title", text)
                notes = args.get("notes", "")
                priority = args.get("priority", "medium")
                
                due = None
                if args.get("due") and args.get("time"):
                    due_str = f"{args['due']} {args['time']}"
                    due = datetime.fromisoformat(due_str)
                elif args.get("due"):
                    due = datetime.fromisoformat(f"{args['due']} 09:00")
                
                task_id = add_task(title, notes, priority, due)
                await update.message.reply_text(f"✅ Tarea creada: {title} (ID: `{task_id}`)", parse_mode='Markdown')
                context.user_data['waiting_for'] = None
                
            except Exception as e:
                logger.error(f"Error creating task from button: {e}")
                await update.message.reply_text("❌ Error al crear la tarea. Intenta de nuevo.")
                context.user_data['waiting_for'] = None
        
        elif context.user_data.get('waiting_for') == 'recur_task':
            # Process as recurring task
            try:
                result = await route_instruction(f"recur {text}")
                if result["intent"] == "clarify":
                    await update.message.reply_text(f"🤔 {result['message']}")
                    return
                
                args = result.get("args", {})
                title = args.get("title", text)
                rrule = args.get("rrule", "FREQ=DAILY")
                notes = args.get("notes", "")
                priority = args.get("priority", "medium")
                
                task_id = add_recurrent_task(title, rrule, notes, priority)
                await update.message.reply_text(f"🔄 Tarea recurrente creada: {title} (ID: `{task_id}`)", parse_mode='Markdown')
                context.user_data['waiting_for'] = None
                
            except Exception as e:
                logger.error(f"Error creating recurring task from button: {e}")
                await update.message.reply_text("❌ Error al crear la tarea recurrente. Intenta de nuevo.")
                context.user_data['waiting_for'] = None

async def handle_inline_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("complete_"):
        task_id = query.data.replace("complete_", "")
        
        try:
            success = complete_task(task_id)
            if success:
                await query.edit_message_text(f"✅ Tarea `{task_id}` marcada como completada!")
            else:
                await query.edit_message_text(f"❌ No se encontró la tarea `{task_id}`")
        except Exception as e:
            logger.error(f"Error completing task via inline button: {e}")
            await query.edit_message_text("❌ Error al completar la tarea.")
    
    elif query.data.startswith("ai_provider_"):
        provider = query.data.replace("ai_provider_", "")
        await handle_provider_selection(update, context, provider)
    
    elif query.data.startswith("ai_model_"):
        parts = query.data.replace("ai_model_", "").split("_", 1)
        if len(parts) == 2:
            provider, model = parts
            await handle_model_selection(update, context, provider, model)
    
    elif query.data == "ai_config_back":
        await show_ai_config_menu(update, context, edit=True)

async def main() -> None:
    """Start the bot."""
    try:
        # Get bot token
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
            raise ValueError("TELEGRAM_BOT_TOKEN not found")
        
        logger.info("🤖 Initializing Telegram bot...")
        
        # Check for existing instance lock
        lock_file = "/tmp/telegram_bot.lock"
        if os.path.exists(lock_file):
            logger.warning("⚠️ Lock file exists - checking if another instance is running")
            try:
                with open(lock_file, 'r') as f:
                    old_pid = f.read().strip()
                logger.info(f"🔍 Found old PID: {old_pid}")
                # Remove stale lock file
                os.remove(lock_file)
                logger.info("🧹 Removed stale lock file")
            except:
                pass
        
        # Create new lock file
        try:
            with open(lock_file, 'w') as f:
                f.write(str(os.getpid()))
            logger.info(f"🔒 Created lock file with PID: {os.getpid()}")
        except:
            logger.warning("⚠️ Could not create lock file")
        
        # Create the Application
        application = Application.builder().token(token).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("tasks", cmd_tasks))
        application.add_handler(CommandHandler("add", cmd_add))
        application.add_handler(CommandHandler("recur", cmd_recur))
        application.add_handler(CommandHandler("done", cmd_done))
        application.add_handler(CommandHandler("ia", cmd_ia))
        
        # Placeholder handlers for existing commands
        application.add_handler(CommandHandler("brief", cmd_brief))
        application.add_handler(CommandHandler("prefs", cmd_prefs))
        application.add_handler(CommandHandler("ajusta", cmd_ajusta))
        application.add_handler(CommandHandler("aiinfo", cmd_aiinfo))
        application.add_handler(CommandHandler("aiconfig", show_ai_config_menu))
        
        # Button handlers
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button_message))
        application.add_handler(CallbackQueryHandler(handle_inline_button))
        
        # Initialize and start the bot
        await application.initialize()
        await application.start()
        
        logger.info("✅ Telegram bot started successfully!")
        
        # Start polling with conflict handling
        try:
            await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            logger.info("✅ Bot polling started successfully!")
        except Exception as polling_error:
            if "Conflict" in str(polling_error):
                logger.warning("⚠️ Bot conflict detected - another instance may be running")
                logger.info("🔄 Waiting for other instance to stop...")
                await asyncio.sleep(10)  # Wait 10 seconds
                try:
                    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
                    logger.info("✅ Bot polling started after conflict resolution!")
                except Exception as retry_error:
                    logger.error(f"❌ Failed to start polling after retry: {retry_error}")
                    raise
            else:
                raise polling_error
        
        # Keep running
        import signal
        stop_signals = (signal.SIGTERM, signal.SIGINT)
        for sig in stop_signals:
            signal.signal(sig, lambda s, f: asyncio.create_task(shutdown(application)))
        
        # Run forever
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"❌ Error in bot main: {e}")
        import traceback
        traceback.print_exc()
        raise

async def shutdown(application):
    """Graceful shutdown"""
    logger.info("🛑 Shutting down bot...")
    
    # Clean up lock file
    lock_file = "/tmp/telegram_bot.lock"
    try:
        if os.path.exists(lock_file):
            os.remove(lock_file)
            logger.info("🧹 Removed lock file")
    except:
        pass
    
    # Stop bot
    try:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("✅ Bot shutdown complete")
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")

if __name__ == '__main__':
    asyncio.run(main())