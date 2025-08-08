# 🚀 Guía de Despliegue a Render.com

## ✅ Checklist Pre-Despliegue

### 1. Obtener API Keys
- [ ] **Telegram Bot Token** (de @BotFather)
- [ ] **Gemini API Key** (de Google AI Studio)  
- [ ] **OpenRouter API Key** (opcional, de OpenRouter.ai)
- [ ] **Google credentials.json** (de Google Cloud Console)

### 2. Configurar Google OAuth Localmente
```bash
# 1. Colocar credentials.json en el directorio del proyecto
# 2. Ejecutar script de configuración
python setup_google_auth.py

# 3. Codificar archivos para Render
python encode_google_files.py
```

### 3. Subir a GitHub
```bash
git init
git add .
git commit -m "Initial commit: Telegram Morning Bot v2.0"
git remote add origin https://github.com/TU-USUARIO/telegram-morning-bot.git
git push -u origin main
```

### 4. Configurar en Render.com

#### Variables de Entorno Requeridas:
```env
TELEGRAM_BOT_TOKEN=tu_token_aqui
GEMINI_API_KEY=tu_gemini_key_aqui
OPENROUTER_API_KEY=tu_openrouter_key_aqui (opcional)
OPENROUTER_MODEL=gpt-4
AI_PROVIDER=gemini
TIMEZONE=America/Mexico_City
SYNC_GOOGLE_TASKS=false
GMAIL_ACCOUNTS=tu_email@gmail.com
GOOGLE_CREDENTIALS_PATH=credentials.json
GOOGLE_TOKEN_PATH=token.json
CREDENTIALS_JSON_BASE64=resultado_del_script_encode
TOKEN_JSON_BASE64=resultado_del_script_encode
```

#### Configuración del Servicio:
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python bot.py`
- **Environment**: Python 3
- **Plan**: Free (para empezar)

## 🔧 Comandos del Bot

Una vez desplegado, tu bot tendrá estos comandos:

### Comandos Básicos:
- `/start` - Iniciar bot y mostrar teclado interactivo
- `/brief` - Brief matutino completo
- `/tasks` - Ver tareas del día
- `/prefs` - Ver/modificar preferencias

### Comandos de Tareas:
- `/add <descripción>` - Crear tarea con IA
- `/recur <descripción>` - Crear tarea recurrente
- `/done <id>` - Marcar tarea como completada
- `/ia <instrucción>` - Comando universal con IA

### Comandos de IA:
- `/aiinfo` - Ver configuración actual de IA
- `/aiconfig` - Cambiar proveedor/modelo de IA

### Teclado Interactivo:
- **Brief 🗞** - Generar brief matutino
- **Tareas de hoy ✅** - Ver tareas pendientes
- **Añadir tarea ➕** - Crear nueva tarea
- **Recurrente ♻️** - Crear tarea recurrente
- **Configurar IA 🤖** - Cambiar configuración de IA
- **Preferencias ⚙️** - Ajustar preferencias

## 🎯 Funcionalidades Implementadas

### ✅ Multi-Proveedor IA (9 modelos):
- **Gemini**: 1.5-flash, 1.5-pro
- **OpenRouter**: GPT-4, GPT-3.5, Claude-3 (Opus/Sonnet/Haiku), Llama-3-70b, Mixtral-8x7b

### ✅ Gestión Completa de Tareas:
- Tareas locales con persistencia JSON
- Soporte completo RRULE para recurrencia
- Sincronización opcional con Google Tasks
- Prioridades y ordenamiento inteligente

### ✅ Brief Matutino Optimizado:
- Procesamiento paralelo (< 25 segundos)
- Multi-cuenta Gmail
- Noticias RSS resumidas por IA
- Eventos de Google Calendar
- Tareas pendientes integradas

### ✅ Interfaz Interactiva:
- Teclado principal con botones
- Configuración dinámica de IA desde Telegram
- Paginación automática de mensajes largos
- Botones contextuales para acciones

### ✅ Fallbacks Robustos:
- Sistema funciona sin APIs de IA
- Fallbacks automáticos con notificación
- Heurística local para casos críticos

## 🔍 Troubleshooting

### Bot no responde:
1. Verificar TELEGRAM_BOT_TOKEN en Render
2. Revisar logs en Render Dashboard
3. Confirmar que el servicio está "Running"

### Error de Google APIs:
1. Verificar que credentials.json y token.json están decodificados
2. Confirmar scopes en Google Cloud Console
3. Revisar GMAIL_ACCOUNTS en variables de entorno

### Error de IA:
1. Verificar GEMINI_API_KEY
2. Probar cambiar AI_PROVIDER a 'openrouter'
3. Los fallbacks deberían activarse automáticamente

## 📊 Monitoreo

### Render Dashboard:
- **Logs**: Ver errores en tiempo real
- **Metrics**: CPU/Memory usage
- **Environment**: Verificar variables

### Telegram:
- Usar `/aiinfo` para ver estado de IA
- Probar `/brief` para verificar todas las integraciones
- Usar `/tasks` para confirmar persistencia

## 🎉 ¡Listo!

Tu bot está ahora desplegado en Render.com con:
- ✅ 24/7 uptime
- ✅ Escalabilidad automática  
- ✅ HTTPS seguro
- ✅ Logs centralizados
- ✅ Variables de entorno seguras

**URL del bot**: Busca tu bot en Telegram por el username que configuraste con @BotFather