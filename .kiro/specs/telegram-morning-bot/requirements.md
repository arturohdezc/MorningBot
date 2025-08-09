# Requirements Document - COMPLETADO ✅

## Project Status: FULLY IMPLEMENTED

**Completion Date:** August 8, 2025  
**Version:** 2.0 - Multi-Provider AI + Multi-Account Gmail  
**Status:** Production Ready

## Introduction

Bot de Telegram completamente funcional que actúa como asistente personal inteligente. Integra múltiples fuentes de información (RSS, Gmail multi-cuenta, Google Calendar, Google Tasks) y utiliza IA multi-proveedor (Gemini/OpenRouter) para procesamiento de lenguaje natural.

**Sistema implementado con:**
- ✅ 9 modelos de IA disponibles (Gemini + OpenRouter)
- ✅ Soporte multi-cuenta Gmail con procesamiento paralelo
- ✅ Gestión completa de tareas con recurrencia RRULE
- ✅ Interfaz interactiva para configuración de IA desde Telegram
- ✅ Fallbacks robustos que garantizan funcionamiento continuo
- ✅ Paginación universal y sincronización bidireccional

## Requirements

### Requirement 1: Brief Matutino con Soporte Multi-Gmail

**User Story:** Como usuario, quiero que el brief matutino soporte múltiples cuentas de Gmail y se ejecute más rápido usando procesamiento paralelo, para recibir información completa de todas mis cuentas.

#### Acceptance Criteria

1. WHEN el usuario ejecuta el comando /brief THEN el sistema SHALL usar asyncio.gather() para ejecutar lectura de noticias, Gmail, Calendar y Tasks en paralelo
2. WHEN se procesan correos THEN el sistema SHALL soportar múltiples cuentas de Gmail configuradas en GMAIL_ACCOUNTS
3. WHEN se leen múltiples cuentas Gmail THEN el sistema SHALL procesar cada cuenta en paralelo y combinar resultados
4. WHEN se ejecutan las operaciones en paralelo THEN el sistema SHALL mantener la funcionalidad existente de noticias RSS resumidas por IA
5. WHEN se ejecutan las operaciones en paralelo THEN el sistema SHALL mantener la funcionalidad existente de eventos de Google Calendar
6. WHEN se ejecutan las operaciones en paralelo THEN el sistema SHALL mantener la funcionalidad existente de tareas de Google Tasks
7. WHEN se genera el brief optimizado THEN el sistema SHALL responder inmediatamente y procesar en background para evitar timeout de Telegram
8. WHEN se procesa el brief en background THEN el sistema SHALL completar la operación en menos de 20 segundos con timeout de seguridad
9. WHEN se despliega en Render THEN el sistema SHALL cargar tokens Gmail desde MULTI_ACCOUNT_TOKENS_BASE64
10. WHEN ocurren errores en operaciones paralelas THEN el sistema SHALL manejar errores individualmente sin afectar otras operaciones

### Requirement 2: Sistema de Gestión de Tareas Locales

**User Story:** Como usuario, quiero gestionar tareas locales con soporte para recurrencia y sincronización opcional con Google Tasks, para tener control completo sobre mi organización de tareas.

#### Acceptance Criteria

1. WHEN se crea el servicio tasks_local.py THEN el sistema SHALL persistir tareas en tasks_db.json con campos: id, title, notes, priority (high|medium|low), due (ISO), completed, createdAt, updatedAt, source (local|google), rrule (opcional)
2. WHEN se llama add_task(title, notes, priority, due) THEN el sistema SHALL crear una nueva tarea local y persistirla en JSON
3. WHEN se llama add_recurrent_task(title, rrule, notes, priority, start_due) THEN el sistema SHALL crear una tarea recurrente usando formato RRULE de iCal
4. WHEN se llama expand_for_today(tz) THEN el sistema SHALL devolver instancias de tareas recurrentes aplicables al día actual
5. WHEN se llama list_today_sorted(tz) THEN el sistema SHALL ordenar tareas del día por prioridad (high>medium>low) y luego por hora
6. WHEN se llama complete_task(id) THEN el sistema SHALL marcar la tarea como completada en el JSON
7. IF SYNC_GOOGLE_TASKS=true AND se crea tarea local THEN el sistema SHALL crear también una copia en Google Tasks
8. IF SYNC_GOOGLE_TASKS=true AND es tarea recurrente expandida hoy THEN el sistema SHALL crear la instancia en Google Tasks

### Requirement 3: Router de IA con Soporte Multi-Proveedor

**User Story:** Como usuario, quiero que mis instrucciones sean analizadas por IA usando diferentes proveedores (Gemini o OpenRouter) para que el bot entienda mis intenciones y extraiga parámetros automáticamente, facilitando la interacción natural.

#### Acceptance Criteria

1. WHEN se configura AI_PROVIDER=gemini THEN el sistema SHALL usar Gemini 1.5 Flash para analizar instrucciones de usuario
2. WHEN se configura AI_PROVIDER=openrouter THEN el sistema SHALL usar OpenRouter con el modelo especificado en OPENROUTER_MODEL
3. WHEN el router procesa una instrucción THEN el sistema SHALL devolver JSON con formato: {"intent": "add|recur|listar|completar|ajustar_prefs|brief", "args": {...}}
4. WHEN se extraen argumentos THEN el sistema SHALL incluir datos como título, fecha, hora, prioridad, rrule, id, o instrucciones de preferencias según el intent
5. WHEN hay ambigüedad en la instrucción THEN el sistema SHALL devolver intent: "clarify" con mensaje explicativo
6. WHEN falla cualquier proveedor de IA THEN el sistema SHALL usar heurística local como fallback y notificar al usuario
7. WHEN se implementa fallback THEN el sistema SHALL usar regex y patrones básicos para detectar intents comunes

### Requirement 4: Comandos Nuevos de Telegram

**User Story:** Como usuario, quiero tener comandos específicos para gestionar tareas y usar el router de IA, para interactuar eficientemente con las nuevas funcionalidades.

#### Acceptance Criteria

1. WHEN se implementa /tasks THEN el sistema SHALL mostrar lista de tareas del día usando list_today_sorted() más Google Tasks si sync está habilitado
2. WHEN se implementa /add <texto> THEN el sistema SHALL pasar el texto por el router y crear la tarea correspondiente
3. WHEN se implementa /recur <texto> THEN el sistema SHALL pasar el texto por el router y crear una tarea recurrente
4. WHEN se implementa /done <id> THEN el sistema SHALL marcar la tarea local como completada usando complete_task()
5. WHEN se implementa /ia <instrucción> THEN el sistema SHALL pasar toda la instrucción por el router y ejecutar la acción detectada
6. WHEN se mantienen comandos existentes THEN el sistema SHALL preservar funcionalidad de /brief, /prefs, /ajusta sin modificaciones

### Requirement 5: Interfaz Interactiva con Configuración de IA

**User Story:** Como usuario, quiero tener botones de acceso rápido y poder cambiar el proveedor y modelo de IA desde Telegram, para personalizar la experiencia sin editar archivos de configuración.

#### Acceptance Criteria

1. WHEN se implementa el teclado en /start THEN el sistema SHALL mostrar ReplyKeyboard con botones: Brief 🗞, Tareas de hoy ✅, Añadir tarea ➕, Recurrente ♻️, Configurar IA 🤖
2. WHEN el usuario presiona "Brief 🗞" THEN el sistema SHALL ejecutar la funcionalidad de /brief
3. WHEN el usuario presiona "Tareas de hoy ✅" THEN el sistema SHALL ejecutar la funcionalidad de /tasks
4. WHEN el usuario presiona "Añadir tarea ➕" THEN el sistema SHALL solicitar texto para crear tarea usando /add
5. WHEN el usuario presiona "Recurrente ♻️" THEN el sistema SHALL solicitar texto para crear tarea recurrente usando /recur
6. WHEN el usuario presiona "Configurar IA 🤖" THEN el sistema SHALL mostrar menú de configuración de IA
7. WHEN se muestra configuración de IA THEN el sistema SHALL permitir elegir entre Gemini y OpenRouter con botones
8. WHEN se elige OpenRouter THEN el sistema SHALL mostrar lista de modelos disponibles (GPT-4, Claude, etc.)
9. WHEN se cambia configuración de IA THEN el sistema SHALL actualizar la configuración y confirmar el cambio
10. WHEN se muestran tareas en /tasks THEN el sistema SHALL incluir inline buttons contextuales como "Marcar como hecha"

### Requirement 6: Paginación Universal de Mensajes

**User Story:** Como usuario, quiero que todos los mensajes largos se dividan automáticamente en chunks manejables, para poder leer toda la información sin problemas de límites de Telegram.

#### Acceptance Criteria

1. WHEN cualquier respuesta del bot excede 3800 caracteres THEN el sistema SHALL dividir el mensaje en múltiples partes
2. WHEN se pagina un mensaje THEN el sistema SHALL respetar límites de palabras y formato para mantener legibilidad
3. WHEN se aplica paginación THEN el sistema SHALL funcionar en todas las respuestas: /brief, /tasks, /prefs, y cualquier otra función
4. WHEN se envían mensajes paginados THEN el sistema SHALL mantener el orden y contexto entre las partes
5. WHEN se implementa paginación THEN el sistema SHALL ser transparente para el usuario (envío automático de partes)

### Requirement 7: Sistema Completo Implementado y Validado

**User Story:** Como usuario, quiero un sistema completamente funcional con fallbacks robustos, documentación completa y todas las funcionalidades validadas.

#### Acceptance Criteria - ✅ TODOS CUMPLIDOS

1. ✅ IMPLEMENTED: Fallbacks globales para todas las funciones de IA (router, resumen, ranking)
2. ✅ IMPLEMENTED: Soporte completo para Gemini y OpenRouter con 9 modelos disponibles
3. ✅ IMPLEMENTED: Configuración dinámica de IA desde interfaz de Telegram
4. ✅ IMPLEMENTED: Multi-cuenta Gmail con procesamiento paralelo
5. ✅ IMPLEMENTED: Sistema de tareas con RRULE completo y sincronización
6. ✅ IMPLEMENTED: Paginación universal y interfaz interactiva
7. ✅ VALIDATED: Todas las funcionalidades probadas y funcionando
8. ✅ DOCUMENTED: README.md, especificaciones y ejemplos completos

## ✅ IMPLEMENTATION SUMMARY

**All 7 requirements have been successfully implemented and validated:**
- Brief matutino con multi-cuenta Gmail ✅
- Sistema de tareas locales con RRULE ✅  
- Router de IA multi-proveedor ✅
- Comandos nuevos de Telegram ✅
- Interfaz interactiva con configuración de IA ✅
- Paginación universal ✅
- Fallbacks globales y documentación ✅

**El sistema está listo para producción.**
