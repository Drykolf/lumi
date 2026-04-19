"""
MCP Bridge Client — Fase 3

Persistent WebSocket client that connects to the VPS bridge at
wss://api.drykolf.xyz/lumi/v1/bridge and executes local tool calls on behalf
of the VPS LLM.

Message contract:
  VPS → local:  {"type": "tool_call",   "request_id": "...", "tool": "...", "args": {...}}
  local → VPS:  {"type": "tool_result", "request_id": "...", "result": {...}}
                {"type": "tool_error",  "request_id": "...", "error":  "..."}
"""

import asyncio
import json
import subprocess
from typing import Any, Callable, Coroutine, Dict

import websockets
from loguru import logger
# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_BRIDGE_URL_TEMPLATE = (
    "wss://api.drykolf.xyz/lumi/v1/bridge?user_id={user_id}&api_key={api_key}"
)
_RECONNECT_DELAY = 5  # seconds between reconnect attempts

# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

ToolHandler = Callable[[Dict[str, Any]], Coroutine[Any, Any, Any]]
_TOOLS: Dict[str, ToolHandler] = {}


def register_tool(name: str):
    """Decorator to register an async function as a local tool."""
    def decorator(fn: ToolHandler) -> ToolHandler:
        _TOOLS[name] = fn
        return fn
    return decorator


# ---------------------------------------------------------------------------
# Built-in tools — Fase 3
# ---------------------------------------------------------------------------

@register_tool("get_clipboard")
async def _get_clipboard(_args: Dict[str, Any]) -> str:
    """Return the current Windows clipboard text content."""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Message handling
# ---------------------------------------------------------------------------

async def _handle_message(ws, raw: str) -> None:
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("bridge: received non-JSON message, ignoring")
        return

    msg_type = msg.get("type")
    request_id = msg.get("request_id", "")
    if msg_type == "ping":
        await ws.send(json.dumps({"type": "pong"}))
        return
    if msg_type != "tool_call":
        logger.debug(f"bridge: unhandled message type '{msg_type}'")
        return

    tool_name: str = msg.get("tool", "")
    args: Dict[str, Any] = msg.get("args", {})
    logger.info(f"bridge: tool_call request_id={request_id} tool={tool_name}")

    handler = _TOOLS.get(tool_name)
    if handler is None:
        error_msg = f"unknown tool: {tool_name}"
        logger.warning(f"bridge: {error_msg}")
        await ws.send(json.dumps({
            "type": "tool_error",
            "request_id": request_id,
            "error": error_msg,
        }))
        return

    try:
        result = await handler(args)
        await ws.send(json.dumps({
            "type": "tool_result",
            "request_id": request_id,
            "result": result,
        }))
        logger.debug(f"bridge: tool_result sent request_id={request_id}")
    except Exception as exc:
        logger.exception(f"bridge: tool execution failed — {exc}")
        await ws.send(json.dumps({
            "type": "tool_error",
            "request_id": request_id,
            "error": str(exc),
        }))


# ---------------------------------------------------------------------------
# Connection loop
# ---------------------------------------------------------------------------

async def _connect_loop(url: str) -> None:
    while True:
        try:
            logger.info("bridge: connecting…")
            async with websockets.connect(url, ping_interval=30, ping_timeout=10) as ws:
                logger.info("bridge: connected")
                async for raw in ws:
                    await _handle_message(ws, raw)
            logger.warning("bridge: connection closed cleanly, reconnecting in %ds", _RECONNECT_DELAY)
        except (websockets.exceptions.WebSocketException, OSError, ConnectionRefusedError) as exc:
            logger.warning(f"bridge: connection error — {exc}; reconnecting in {_RECONNECT_DELAY}s")
        except Exception as exc:
            logger.exception(f"bridge: unexpected error — {exc}; reconnecting in {_RECONNECT_DELAY}s")

        await asyncio.sleep(_RECONNECT_DELAY)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_task: "asyncio.Task | None" = None


def start(user_id: str, api_key: str) -> asyncio.Task:
    """
    Spawn the bridge client as a background asyncio Task.

    Must be called from within a running event loop (e.g. inside a coroutine).
    Calling a second time is a no-op if the task is still running.
    """
    global _task
    if _task is not None and not _task.done():
        return _task
    url = _BRIDGE_URL_TEMPLATE.format(user_id=user_id, api_key=api_key)
    _task = asyncio.ensure_future(_connect_loop(url))
    return _task