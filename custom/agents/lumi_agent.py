"""
LumiAgent — Fase 3

Sends the user's raw message to the VPS (/v1/chat).
The VPS owns the LLM, personality, and session memory.
Local responsibilities: wake gate, connectivity, interrupt, OLV pipeline.

Endpoints used:
  GET  {vps_url}/health       — connectivity oracle
  POST {vps_url}/v1/chat      — streaming chat
"""

from datetime import datetime
from typing import AsyncIterator, Callable, Dict, Any, Union

import httpx
from loguru import logger

from src.open_llm_vtuber.agent.agents.agent_interface import AgentInterface
from src.open_llm_vtuber.agent.input_types import BatchInput, TextSource
from src.open_llm_vtuber.agent.output_types import SentenceOutput
from src.open_llm_vtuber.agent.transformers import (
    actions_extractor,
    display_processor,
    sentence_divider,
    tts_filter,
)
from src.open_llm_vtuber.config_manager import TTSPreprocessorConfig

from custom.wake_word.wake_detector import WakeDetector
from custom.interruption.interrupt_handler import InterruptContext, classify
from custom.connectivity.vps_health import VpsHealthCheck
from custom.utils.offline_mode import OfflineState, MSG_OFFLINE, MSG_BACK_ONLINE

def _make_session_id() -> str:
    """Generate a session ID from current datetime: DDMMYYHHmmSS."""
    return datetime.now().strftime("%d%m%y%H%M%S")


class LumiAgent(AgentInterface):
    """
    Lumi's custom agent.  Sends raw user messages to the VPS and pipes the
    streamed response through OLV's standard output pipeline.
    """

    def __init__(
        self,
        vps_url: str,
        vps_api_key: str,
        user_id: str = "user",
        live2d_model=None,
        tts_preprocessor_config: TTSPreprocessorConfig = None,
        faster_first_response: bool = True,
        segment_method: str = "pysbd",
    ):
        super().__init__()

        self._chat_url = f"{vps_url.rstrip('/')}/v1/chat"
        self._headers = {"x-api-key": vps_api_key}
        self._user_id = user_id
        self._session_id = "jose_local"#_make_session_id()

        self._live2d_model = live2d_model
        self._tts_preprocessor_config = tts_preprocessor_config
        self._faster_first_response = faster_first_response
        self._segment_method = segment_method
        self._interrupted = False

        self._wake_detector = WakeDetector()
        self._interrupt_ctx = InterruptContext()
        self._health = VpsHealthCheck(vps_url)
        self._offline = OfflineState()

        self.chat = self._build_chat_pipeline()
        logger.info(
            f"LumiAgent initialized — session: {self._session_id} | "
            f"endpoint: {self._chat_url}"
        )

    # ------------------------------------------------------------------
    # AgentInterface implementation
    # ------------------------------------------------------------------

    def handle_interrupt(self, heard_response: str) -> None:
        """Cancel the active stream and record interrupt context."""
        self._interrupted = True
        interrupt_type = classify(heard_response)
        self._interrupt_ctx.record(heard_response, interrupt_type)
        logger.info(f"LumiAgent: interrupt — type={interrupt_type.name}")

    def set_memory_from_history(self, conf_uid: str, history_uid: str) -> None:
        logger.debug("LumiAgent.set_memory_from_history: no-op (VPS owns memory).")

    async def chat(
        self, input_data: BatchInput
    ) -> AsyncIterator[Union[SentenceOutput, Dict[str, Any]]]:
        # Replaced at __init__ time by _build_chat_pipeline().
        async for output in self._build_chat_pipeline()(input_data):
            yield output

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_chat_pipeline(
        self,
    ) -> Callable[[BatchInput], AsyncIterator[Union[SentenceOutput, Dict[str, Any]]]]:

        @tts_filter(self._tts_preprocessor_config)
        @display_processor()
        @actions_extractor(self._live2d_model)
        @sentence_divider(
            faster_first_response=self._faster_first_response,
            segment_method=self._segment_method,
            valid_tags=["think"],
        )
        async def _stream(
            input_data: BatchInput,
        ) -> AsyncIterator[Union[str, Dict[str, Any]]]:
            self._interrupted = False
            self._interrupt_ctx.clear()

            content = self._extract_text(input_data)

            # ── Connectivity check ──────────────────────────────────────
            is_online = self._health.is_online()

            if self._offline.should_notify(is_online):
                yield MSG_OFFLINE
                return

            if not is_online:
                return  # Already notified; stay silent.

            if self._offline.on_reconnect():
                yield MSG_BACK_ONLINE

            # ── Wake word gate ──────────────────────────────────────────
            input_medium = (input_data.metadata or {}).get("input_medium", "unknown")
            logger.info(f"LumiAgent: input_medium='{input_medium}' content='{content[:10]}'")
            if input_medium == "asr":
                return #ignore asr
            if not self._wake_detector.should_respond(content):
                logger.debug(f"LumiAgent: wake gate blocked — '{content[:60]}'")
                return

            logger.debug(f"LumiAgent: sending to VPS — '{content[:80]}'")

            # ── VPS call ────────────────────────────────────────────────
            try:
                async for chunk in self._stream_vps(content):
                    if self._interrupted:
                        logger.debug("LumiAgent: stream cancelled by interrupt.")
                        break
                    yield chunk

            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
                logger.error(f"LumiAgent: VPS error — {e}")
                if self._offline.should_notify(False):
                    yield MSG_OFFLINE
                return

            # ── Post-turn housekeeping ──────────────────────────────────
            if not self._interrupted:
                self._wake_detector.on_response_sent()

        return _stream

    async def _stream_vps(self, content: str) -> AsyncIterator[str]:
        """POST to /v1/chat, parse JSON response, yield the response text."""
        payload = {
            "content": content,
            "user_id": self._user_id,
            "session_id": self._session_id,
        }
        async with httpx.AsyncClient(
            headers=self._headers,
            timeout=httpx.Timeout(60.0, connect=5.0),
        ) as client:
            async with client.stream("POST", self._chat_url, json=payload) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_text():
                    if chunk:
                        yield chunk

    @staticmethod
    def _extract_text(input_data: BatchInput) -> str:
        parts = []
        for t in input_data.texts:
            if t.source == TextSource.INPUT:
                parts.append(t.content)
            elif t.source == TextSource.CLIPBOARD:
                parts.append(f"[Contenido del portapapeles: {t.content}]")
        return "\n".join(parts).strip()
