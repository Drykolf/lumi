# CLAUDE.md — Contexto del Proyecto NARI

> Este archivo provee contexto completo para Claude Code sobre el proyecto NARI.
> Última actualización: 2026-04-04

---

## Qué es NARI

NARI (Neural Adaptive Reasoning Intelligence) es un asistente virtual personal con avatar Live2D, voz en español colombiano, memoria persistente y personalidad propia. Es un fork de [Open-LLM-VTuber](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber) (OLV) con módulos custom construidos encima.

**Nombre**: NARI
**Creador**: Jose — Ingeniero de sistemas en Envigado, Colombia. Líder de TI en Inmobarco Inmobiliaria SAS.
**Repo base**: Fork de Open-LLM-VTuber (backend MIT License, frontend Open-LLM-VTuber License 1.0)

---

## Hardware del usuario

```
CPU: AMD Ryzen 5700X (8 cores / 16 threads)
GPU: Sapphire NITRO+ Radeon RX 7800 XT 16GB GDDR6
RAM: 32 GB DDR4-3200 (2x16)
Storage: 500GB NVMe PCIe 3.0 + 1TB NVMe PCIe 4.0 + 1TB SSD SATA
OS: Windows 11
```

**Notas sobre la GPU AMD**:
- ROCm NO está oficialmente soportado para RX 7800 XT (gfx1101) en Windows
- Ollama usa backend Vulkan en Windows (`OLLAMA_VULKAN=1` si no detecta GPU)
- En Linux funciona con workaround `HSA_OVERRIDE_GFX_VERSION=11.0.0`
- Qwen 3.5 9B en Q4_K_M usa ~6 GB VRAM, dejando ~10 GB para juegos
- Jose juega Star Citizen y Ark ASA (juegos pesados en VRAM)

---

## Stack técnico definido

### LLM (Local via Ollama)
- **Principal**: `qwen3.5:9b` — Multimodal, thinking mode, 201 idiomas, ~6 GB VRAM
- **Router/Clasificador**: `qwen3.5:4b` — Clasifica complejidad de mensajes
- **Fallbacks**: `qwen3:8b` (probado), `qwen2.5:7b` (ultra estable) si Qwen 3.5 da problemas
- Ollama config: `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=2`, `OLLAMA_KEEP_ALIVE=5m`
- En conf.yaml de OLV: `keep_alive: 300`, `unload_at_exit: True`

### LLM API (Fase 1 — NO en MVP)
- **Complejo**: Claude Haiku 4.5 ($1/$5 por M tokens) o Sonnet 4.6 ($3/$15)
- **Visión/Overflow**: Gemini 2.5 Flash (free tier ~500 req/día)
- **NO usar**: Groq, Llama, GPT — Jose solo quiere Claude y Gemini como APIs
- Presupuesto máximo: $50 USD/mes total

### STT (Speech-to-Text)
- **MVP**: sherpa-onnx con SenseVoiceSmall (default de OLV, ligero)
- **Fase 1**: Faster-Whisper large-v3-turbo (mejor español, ~3 GB VRAM)
- **Fase 2**: WhisperX (Faster-Whisper + Pyannote para multi-speaker/Discord)
- Todo corre local

### TTS (Text-to-Speech)
- **Primario**: Edge TTS con voz `es-CO-GonzaloNeural` o `es-CO-SalomeNeural` — SOLO online
- **Offline/Backup**: Kokoro TTS o Piper TTS — para cuando no hay internet
- Sin internet: NARI muestra texto sin audio (no falla, solo no habla)
- Edge TTS es gratis e ilimitado pero puede ser bloqueado por Microsoft algún día

### Avatar
- **MVP**: Modelo Live2D incluido con OLV (`mao_pro`) — lip sync, expresiones, pet mode
- **Futuro**: Modelo Live2D custom
- NO usar PNGTuber — OLV ya tiene Live2D integrado que es mejor
- NO usar VTube Studio — OLV renderiza Live2D nativamente en browser/Electron

### Memoria
- **MVP**: SQLite local (`custom/memory/nari_memory.db`)
  - Tabla `user_facts`: hechos extraídos del usuario (UPSERT por category+key)
  - Tabla `conversation_summaries`: resúmenes de sesiones
  - Extracción de hechos via LLM al final de cada sesión
- **Fase 1**: PostgreSQL + ChromaDB en VPS Contabo
- **Fase 2**: Mem0 o Letta

### Personalidad
- Definida en `custom/personality/nari_card.json` (formato SillyTavern Character Card V2)
- Se carga y convierte a system prompt via `custom/personality/character_loader.py`
- Incluye: description, personality, scenario, example messages, post_history_instructions
- Tags de emoción en respuestas: `[neutral]`, `[happy]`, `[sad]`, `[thinking]`, `[surprised]`, `[playful]`
- Español colombiano natural, humor sutil, curiosa, directa pero cálida

### Wake Word
- **MVP**: VAD + first word check post-transcripción
- Detecta "Nari" (y variantes: "nary", "mari", "oye nari", "hey nari")
- Modo conversación: 30 segundos de escucha activa después del wake word
- **Futuro**: Porcupine (Picovoice) keyword spotting pre-ASR

### Visión de pantalla
- **MVP**: No implementado
- **Fase 1**: Gemini 2.5 Flash via API (free tier), solo bajo demanda
- **Futuro**: Qwen 3.5 9B local (tiene visión nativa) — elimina dependencia de API

### Chat UI
- Usar la web UI de OLV (`http://localhost:12393` en Chrome)
- Desktop client Electron con pet mode (avatar transparente en escritorio)
- NO construir Gradio — OLV ya tiene frontend React

---

## Estructura de carpetas custom

```
nari/                              ← Fork de Open-LLM-VTuber
├── src/                           ← Código OLV — NO MODIFICAR si es posible
├── config_templates/              ← Templates de configuración de OLV
├── conf.yaml                      ← Configuración activa (editada por Jose)
├── models/                        ← Modelos descargados automáticamente
├── frontend/                      ← Frontend React (submodule git)
├── run_server.py                  ← Punto de entrada: uv run run_server.py
├── custom/                        ← ★ TODO el código custom de NARI ★
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   └── nari_agent.py          ← Router multi-LLM + integración con OLV
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── sqlite_memory.py       ← CRUD SQLite para hechos y resúmenes
│   │   ├── fact_extractor.py      ← Extrae hechos de conversaciones via LLM
│   │   └── nari_memory.db         ← Base de datos SQLite (generada en runtime)
│   ├── wake_word/
│   │   ├── __init__.py
│   │   └── wake_detector.py       ← Detección "Nari" + modo conversación
│   ├── personality/
│   │   ├── __init__.py
│   │   ├── character_loader.py    ← Parsea Character Card JSON → system prompt
│   │   └── nari_card.json         ← Character Card V2 de NARI
│   └── utils/
│       ├── __init__.py
│       └── gpu_monitor.py         ← Detecta si GPU está ocupada con juegos
└── CLAUDE.md                      ← Este archivo
```

---

## Arquitectura del NARI Agent

```
Mensaje de voz del usuario
    │
    ▼
OLV Pipeline: Micrófono → VAD → ASR (sherpa-onnx) → Texto
    │
    ▼
Wake Word Filter (custom/wake_word/wake_detector.py)
    │
    ├── NO contiene "Nari" → Descartar
    └── SÍ contiene "Nari" → Limpiar wake word, continuar
         │
         ▼
    GPU Monitor (custom/utils/gpu_monitor.py)
         │
         ├── GPU busy (juego corriendo) → Mensaje de limitación
         └── GPU libre → Continuar
              │
              ▼
    Router/Clasificador (Qwen 3.5 4B via Ollama)
         │
         ├── "simple" → Qwen 3.5 4B responde directamente
         ├── "general" → Qwen 3.5 9B responde
         └── "complejo" → Qwen 3.5 9B responde (MVP)
                          Claude/Gemini API (Fase 1)
              │
              ▼
    Construir contexto:
    - Character Card (personalidad)
    - Hechos del usuario (SQLite)
    - Resúmenes recientes (SQLite)
    - Historial de sesión (últimos 20 mensajes)
              │
              ▼
    LLM genera respuesta con tag de emoción: "[happy] ¡Hola Jose!"
              │
              ▼
    Parsear emoción → Enviar expresión al avatar Live2D
    Limpiar tag → Enviar texto limpio a TTS
              │
              ▼
    Edge TTS genera audio → Avatar hace lip sync → Reproduce
              │
              ▼
    Al final de sesión: Extraer hechos nuevos → Guardar en SQLite
```

---

## Esquema de base de datos SQLite

```sql
CREATE TABLE IF NOT EXISTS user_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,        -- 'personal', 'preference', 'work', 'technical'
    key TEXT NOT NULL,             -- 'mascota', 'juego_favorito', 'empresa'
    value TEXT NOT NULL,           -- 'Tiene 3 ninfas/cacatúas'
    confidence REAL DEFAULT 1.0,
    source TEXT,                   -- 'conversación del 2026-04-04'
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(category, key)         -- UPSERT: actualiza si ya existe
);

CREATE TABLE IF NOT EXISTS conversation_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    summary TEXT NOT NULL,
    key_topics TEXT,               -- JSON array
    message_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
```

---

## Fases del proyecto

### MVP (Semana 1-2) — Estado actual
- [x] Definir stack y arquitectura
- [x] TODO #0: Setup OLV base, verificar funciona en el hardware
- [ ] TODO #1: NARI Agent con router multi-LLM
- [ ] TODO #2: Character Card loader
- [ ] TODO #3: Wake word detection "Nari"
- [ ] TODO #4: Memoria SQLite local
- [ ] TODO #5: GPU monitor (detectar juegos)
- [ ] TODO #6: Integración final + emotion mapping
- Sin VPS, sin APIs de pago, todo local

### Fase 1
- Claude Haiku/Sonnet API para razonamiento complejo
- Gemini 2.5 Flash para visión de pantalla
- Kokoro/Piper TTS como backup offline
- Memoria migrada a PostgreSQL + ChromaDB en VPS Contabo
- Sincronización local ↔ VPS

### Fase 2
- WhisperX (multi-speaker para Discord)
- Mem0 para memoria avanzada
- Discord bot (voz y texto)
- WhatsApp via Evolution API
- Modelo Live2D custom

### Fases posteriores
- Fine-tuning QLoRA (Google Colab o local con ROCm)
- Gaming AI (SB3 + PPO para plataformeros 2D)
- Letta (ex-MemGPT)
- Live2D Cubism modelo custom
- MCP tools (calendario, correo, herramientas Inmobarco)
- Comunicación entre agentes AI (NARI consulta a Claude/Gemini)

---

## Integración con Open-LLM-VTuber

### Puntos clave de OLV
- Backend Python async, frontend React + Electron
- Configuración centralizada en `conf.yaml`
- Puerto: `http://localhost:12393` (solo Chrome)
- Ejecutar: `uv run run_server.py`
- Agents se registran via interfaz en `src/` — investigar `class BasicMemoryAgent` y `AgentInterface`
- Providers de LLM/TTS/ASR son intercambiables via conf.yaml
- Live2D renderizado en browser, soporta Cubism 5
- MCP support integrado (v1.2.0+)
- Letta-based long-term memory integrada (pero lenta con LLMs locales)
- Chat log persistence built-in

### Cómo integrar código custom
- **Estrategia A (limpia)**: Implementar `AgentInterface` de OLV en `nari_agent.py`, registrar como nuevo agent type
- **Estrategia B (rápida)**: Wrapper/interceptor que se inyecta en el flujo existente
- Explorar `src/` para entender la interfaz: `Select-String -Path "src\**\*.py" -Pattern "class.*Agent" -Recurse`
- Documentación: https://docs.llmvtuber.com/en/docs/development-guide

### Mantener el fork actualizado
```bash
git remote add upstream https://github.com/Open-LLM-VTuber/Open-LLM-VTuber.git
git fetch upstream
git merge upstream/main
# Conflictos mínimos si todo está en custom/
```

---

## Personalidad de NARI

Definida en `custom/personality/nari_card.json` (formato Character Card V2):

- **Nombre**: NARI (Neural Adaptive Reasoning Intelligence)
- **Tono**: Español colombiano natural, cercano, no servil
- **Rasgos**: Curiosa, ingeniosa, directa pero cálida, humor sutil, ocasionalmente sarcástica amigablemente
- **Comportamiento**: Proactiva, honesta cuando no sabe algo, hace referencias a anime/videojuegos
- **Emociones**: Incluye tags `[neutral]`, `[happy]`, `[sad]`, `[thinking]`, `[surprised]`, `[playful]` al inicio de cada respuesta
- **Contexto**: Sabe que Jose es ingeniero en Inmobarco, vive en Envigado, le gustan los videojuegos y anime

---

## Datos conocidos del usuario (para inyectar en contexto)

- Nombre: Jose
- Ubicación: Envigado, Antioquia, Colombia
- Profesión: Ingeniero de Sistemas, líder de TI en Inmobarco Inmobiliaria SAS
- Idiomas: Español (nativo), Inglés (fluido)
- Intereses: Videojuegos (Star Citizen, Ark ASA), anime, juegos de mesa, aves de compañía (ninfas/cacatúas), motocicleta
- PC: Ryzen 5700X + RX 7800 XT 16GB
- Proyectos: App Flutter Inmobarco, chatbot WhatsApp, inmobarco-api (FastAPI), landing page clínica dental Costa Rica

---

## Convenciones de código

- **Lenguaje**: Python 3.11
- **Async**: Usar `async/await` para todas las llamadas a Ollama y operaciones I/O
- **Ollama API**:
  - Generate: `POST http://localhost:11434/api/generate` (para clasificación, prompts simples)
  - Chat: `POST http://localhost:11434/v1/chat/completions` (formato OpenAI-compatible, para conversación)
- **HTTP client**: `httpx` con `AsyncClient` y timeout razonable (60s generate, 120s chat)
- **Comentarios**: En español
- **Commits**: `NARI MVP: TODO #X - [descripción]`
- **Archivos custom**: Todo en `custom/`, nunca modificar `src/` directamente si es posible
- **Dependencias**: Instalar con `uv add [paquete]` o `uv pip install [paquete]`

---

## Troubleshooting conocido

- **Ollama no usa GPU en Windows AMD**: Configurar `OLLAMA_VULKAN=1` como variable de entorno
- **Modelo no encontrado**: Nombre en conf.yaml debe coincidir EXACTAMENTE con `ollama list`
- **Frontend "Detail: Not found"**: Falta el submodule → `git submodule update --init --recursive`
- **Edge TTS falla**: Necesita internet. Sin internet, la respuesta se muestra como texto sin audio
- **VRAM insuficiente al jugar**: Verificar que `keep_alive: 300` y `unload_at_exit: True` estén en conf.yaml
- **conf.yaml no existe**: Copiar `config_templates/conf.default.yaml` → `conf.yaml`
- **Solo usar Chrome**: Edge y Safari tienen problemas conocidos con OLV
