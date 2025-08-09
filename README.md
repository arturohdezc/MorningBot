# Bot de Telegram - Asistente Personal Inteligente

Un bot de Telegram que proporciona un brief matutino personalizado y gestiona tareas con apoyo de Gemini 1.5 Flash. Todas las interacciones del usuario pasan por un router de IA antes de ejecutarse.

## 🚀 Características

### Brief Matutino Automatizado con Sistema Progresivo

- **Noticias Categorizadas**: Economía, Noticias Generales, IA & Tech, Viajes por región (México, US, Mundial)
- **Correos Multi-Cuenta**: Soporte para múltiples cuentas Gmail con formato mejorado
- **Calendario**: Eventos de Google Calendar del día actual
- **Tareas**: Tareas pendientes (locales + Google Tasks)
- **Sistema Progresivo**: Brief tipo "sprints" - muestra progreso cada 8s, sin timeouts de Telegram
- **Cache Inteligente**: Briefs instantáneos si son recientes (30 min)

### Gestión Inteligente de Tareas

- **Tareas locales**: Persistencia en JSON con soporte completo RRULE
- **Tareas recurrentes**: Formato iCal (ej: `FREQ=MONTHLY;BYMONTHDAY=1`)
- **Procesamiento de lenguaje natural**: "añadir cortarme el cabello mañana 5pm prioridad alta"
- **Sincronización opcional**: Con Google Tasks
- **Prioridades**: high/medium/low con ordenamiento automático

### Router de IA Multi-Proveedor (12 Modelos Disponibles)

- **Gemini**: 4 modelos incluyendo 2.0 Flash Experimental
- **OpenRouter**: 8 modelos GRATUITOS (Llama 3.2, Phi-3, Gemma 2, etc.)
- **Configuración Dinámica**: Cambio de modelo desde Telegram
- **Fallbacks robustos**: Heurística local cuando falla cualquier proveedor de IA
- **Intents soportados**: add, recur, listar, completar, ajustar_prefs, brief

### Interfaz Interactiva Avanzada

- **Teclado principal**: Botones de acceso rápido
- **Configuración de IA**: 12 modelos disponibles, cambio desde Telegram
- **Brief Progresivo**: Muestra avance en tiempo real con contenido parcial
- **Emails Mejorados**: Formato estructurado con razón de importancia
- **Botones contextuales**: Acciones inline para tareas
- **Paginación universal**: Mensajes largos divididos automáticamente

## 📋 Comandos Disponibles

### Comandos Principales

- `/start` - Mensaje de bienvenida y teclado principal
- `/brief` - Generar brief matutino completo
- `/tasks` - Ver tareas de hoy ordenadas por prioridad
- `/add <descripción>` - Crear nueva tarea
- `/recur <descripción>` - Crear tarea recurrente
- `/done <id>` - Marcar tarea como completada
- `/ia <instrucción>` - Procesar cualquier instrucción con IA

### Gestión de Preferencias y Configuración

- `/prefs` - Ver preferencias actuales
- `/ajusta <instrucción>` - Modificar preferencias por lenguaje natural
- `/aiinfo` - Ver información del proveedor de IA configurado
- `/aiconfig` - Configurar proveedor y modelo de IA con interfaz interactiva

## 🎯 Ejemplos de Uso

### Creación de Tareas

```
/add necesito llamar al dentista mañana 3pm prioridad alta
/add comprar leche
/add revisar informe el viernes 10am prioridad media
```

### Tareas Recurrentes

```
/recur revisar correos cada día 9am
/recur pagar renta cada primero de mes prioridad alta
/recur backup semanal los lunes 8pm
/recur llamar a mamá cada domingo 7pm
```

### Uso del Router de IA

```
/ia necesito recordar la reunión del proyecto mañana 2pm
/ia marca como hecha la tarea t_12345678
/ia ya no me des correos de newsletters
/ia muéstrame las tareas de hoy
```

### Ajuste de Preferencias

```
/ajusta ya no me des correos de oracle
/ajusta bloquear newsletters y promociones
/ajusta priorizar correos de mi jefe
```

## 🛠 Configuración

### Variables de Entorno (.env)

```env
TELEGRAM_BOT_TOKEN=tu_token_de_telegram
TIMEZONE=America/Mexico_City
GOOGLE_CREDENTIALS_PATH=credentials.json
GOOGLE_TOKEN_PATH=token.json
SYNC_GOOGLE_TASKS=false

# Gmail Multi-Account Support (comma separated)
GMAIL_ACCOUNTS=account1,account2

# Configuración de IA - Elige un proveedor
AI_PROVIDER=gemini
GEMINI_API_KEY=tu_api_key_de_gemini

# O usa OpenRouter
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=tu_api_key_de_openrouter
OPENROUTER_MODEL=gpt-4
```

### Dependencias (requirements.txt)

```
python-telegram-bot
google-generativeai
google-api-python-client
google-auth-oauthlib
feedparser
python-dateutil
pytz
openai
```

### Configuración de Google APIs

1. Crear proyecto en Google Cloud Console
2. Habilitar APIs: Gmail, Calendar, Tasks
3. Crear credenciales OAuth 2.0
4. Descargar `credentials.json`
5. Primera ejecución generará `token.json`

## 🔧 Instalación

1. **Clonar repositorio**

```bash
git clone <repo-url>
cd telegram-morning-bot
```

2. **Instalar dependencias**

```bash
pip install -r requirements.txt
```

3. **Configurar variables de entorno**

```bash
cp .env.example .env
# Editar .env con tus tokens y configuración de IA
```

### Configuración de Proveedores de IA

#### Opción 1: Usar Gemini (Google) - RECOMENDADO

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=tu_api_key_de_gemini
```

**Modelos Gemini disponibles:**
- `gemini-1.5-flash` - Rápido y eficiente (por defecto)
- `gemini-1.5-pro` - Más potente y preciso
- `gemini-2.0-flash-exp` - Última versión experimental
- `gemini-exp-1206` - Versión experimental diciembre

#### Opción 2: Usar OpenRouter (Solo Modelos Gratuitos)

```env
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=tu_api_key_de_openrouter
OPENROUTER_MODEL=meta-llama/llama-3.2-3b-instruct:free
```

**Modelos GRATUITOS soportados en OpenRouter:**
- `meta-llama/llama-3.2-3b-instruct:free` - Llama 3.2 3B
- `meta-llama/llama-3.2-1b-instruct:free` - Llama 3.2 1B  
- `microsoft/phi-3-mini-128k-instruct:free` - Phi-3 Mini
- `microsoft/phi-3-medium-128k-instruct:free` - Phi-3 Medium
- `google/gemma-2-9b-it:free` - Gemma 2 9B
- `huggingface/zephyr-7b-beta:free` - Zephyr 7B
- `openchat/openchat-7b:free` - OpenChat 7B
- `gryphe/mythomist-7b:free` - Mythomist 7B

4. **Configurar Google APIs**

- Colocar `credentials.json` en el directorio raíz
- Primera ejecución solicitará autorización OAuth

5. **Ejecutar bot**

```bash
python bot.py
```

## 📱 Teclado Interactivo

Al usar `/start`, aparece un teclado con botones:

- **Brief 🗞** - Generar brief matutino
- **Tareas de hoy ✅** - Ver tareas del día
- **Añadir tarea ➕** - Crear nueva tarea
- **Recurrente ♻️** - Crear tarea recurrente
- **Preferencias ⚙️** - Ver configuración actual

## 🔄 Tareas Recurrentes (RRULE)

### Patrones Soportados

- `FREQ=DAILY` - Diario
- `FREQ=WEEKLY` - Semanal
- `FREQ=MONTHLY` - Mensual
- `FREQ=YEARLY` - Anual
- `FREQ=WEEKLY;BYDAY=MO` - Cada lunes
- `FREQ=MONTHLY;BYMONTHDAY=1` - Cada primero de mes

### Ejemplos de Lenguaje Natural

- "cada día" → `FREQ=DAILY`
- "cada lunes" → `FREQ=WEEKLY;BYDAY=MO`
- "cada mes" → `FREQ=MONTHLY`
- "cada primero de mes" → `FREQ=MONTHLY;BYMONTHDAY=1`

## 🔗 Sincronización con Google Tasks

### Configuración

```env
SYNC_GOOGLE_TASKS=true
```

### Comportamiento

- **Tareas normales**: Se crean inmediatamente en Google Tasks
- **Tareas recurrentes**: Se crean en Google Tasks cuando se expande la instancia del día
- **IDs separados**: Mantiene IDs locales distintos a los de Google Tasks
- **Notas**: Incluye referencia al ID local para trazabilidad

## 🛡 Fallbacks de IA Multi-Proveedor

### Sistema Robusto

- **Router**: Regex patterns para intents básicos (funciona sin IA)
- **Resumen de noticias**: Primeros titulares si falla cualquier proveedor
- **Ranking de correos**: Heurística basada en remitente y asunto
- **Notificación**: Usuario informado cuando se usa fallback
- **Compatibilidad**: Funciona sin configurar ningún proveedor de IA

### Patrones de Fallback

- Detección de palabras clave
- Análisis de patrones regex
- Heurística basada en contexto
- Valores por defecto seguros

## 📊 Estructura de Datos

### tasks_db.json

```json
{
  "tasks": [
    {
      "id": "t_12345678",
      "title": "Pagar impuestos",
      "notes": "",
      "priority": "high",
      "due": "2025-09-01T09:00:00-06:00",
      "completed": false,
      "createdAt": "2025-08-08T10:30:00-06:00",
      "updatedAt": "2025-08-08T10:30:00-06:00",
      "source": "local",
      "rrule": "FREQ=MONTHLY;BYMONTHDAY=1"
    }
  ]
}
```

### preferences.json

```json
{
  "top_k": 10,
  "only_unread": false,
  "min_importance": "any",
  "priority_domains": [],
  "priority_senders": [],
  "blocked_domains": [],
  "blocked_senders": [],
  "blocked_keywords": ["newsletter", "promo", "boletín", "no-reply"]
}
```

## 🏗 Arquitectura

### Servicios Modulares

- `services/tasks_local.py` - Gestión de tareas locales
- `services/router.py` - Router de IA multi-proveedor
- `services/ai_client.py` - Cliente unificado de IA (Gemini/OpenRouter)
- `services/formatter.py` - Paginación y formato de mensajes
- `services/news.py` - Lectura de RSS feeds
- `services/gmail_multi_account.py` - Integración multi-cuenta Gmail
- `services/calendar_reader.py` - Integración con Google Calendar
- `services/tasks_reader.py` - Integración con Google Tasks
- `services/ai_fallbacks.py` - Sistema de fallbacks

### Flujo de Datos

1. Usuario envía comando/mensaje
2. Router de IA analiza intención
3. Servicio correspondiente procesa acción
4. Formatter pagina respuesta si es necesaria
5. Bot envía respuesta al usuario

## 🚨 Manejo de Errores

### Estrategias

- **Timeout de Telegram**: Respuesta inmediata + procesamiento en background
- **Timeouts de servicios**: 20 segundos máximo con resultados parciales
- **Fallbacks**: Heurística cuando falla IA
- **Validación**: Entrada de usuario y formatos
- **Logging**: Errores registrados para debugging
- **Graceful degradation**: Funcionalidad parcial si fallan servicios

## 📈 Optimizaciones

### Procesamiento Paralelo

- `asyncio.gather()` para operaciones simultáneas
- Timeouts individuales por operación
- Continuación si una operación falla

### Paginación Inteligente

- Límite de 3800 caracteres por mensaje
- Respeto de límites de palabras
- Preservación de formato Markdown

### Cache y Performance

- Reutilización de conexiones Google APIs
- Límites en cantidad de datos procesados
- Cleanup automático de tareas completadas

## 🤝 Contribución

1. Fork del repositorio
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 🆘 Soporte

Para reportar bugs o solicitar funcionalidades, crear un issue en el repositorio.

---

**Desarrollado con ❤️ usando Python, Telegram Bot API y Gemini 1.5 Flash**
