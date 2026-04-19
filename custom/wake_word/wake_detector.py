"""
Wake word detector — conversation window state machine (section 5.2).

States
------
CLOSED   No active conversation. Lumi only responds if "lumi" appears in the text.
ACTIVE   Conversation window open (refreshed on every response). Any text is processed.

Transitions
-----------
CLOSED  + "lumi" in text           → ACTIVE  (open window, process turn)
CLOSED  + no "lumi"                → CLOSED  (discard / observe passively)
ACTIVE  + "gracias lumi" in text   → CLOSED  (process turn then close)
ACTIVE  + any other text           → ACTIVE  (process turn, refresh window)
ACTIVE  + window expired (5 min)   → CLOSED  (timeout)
"""

import re
import time
from enum import Enum, auto

_WINDOW_SECONDS = 300  # 5 minutes

# "Gracias Lumi" variants — closes the conversation window.
_CLOSE_PATTERN = re.compile(r"\bgracias\s+lumi\b", re.IGNORECASE)

# Wake word — opens the window.
_WAKE_PATTERN = re.compile(r"\blumi\b", re.IGNORECASE)


class WindowState(Enum):
    CLOSED = auto()
    ACTIVE = auto()


class WakeDetector:
    """
    Lightweight state machine.  Called once per ASR transcription inside
    LumiAgent.chat() before any LLM call is made.
    """

    def __init__(self, window_seconds: int = _WINDOW_SECONDS) -> None:
        self._window_seconds = window_seconds
        self._state = WindowState.CLOSED
        self._window_expires: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> WindowState:
        self._check_timeout()
        return self._state

    def should_respond(self, text: str) -> bool:
        """
        Evaluate whether Lumi should respond to this transcription.
        Advances the state machine as a side effect.
        """
        self._check_timeout()
        text = text.strip()

        if self._state == WindowState.ACTIVE:
            if _CLOSE_PATTERN.search(text):
                # Process this turn, then close after response_sent() is called.
                self._pending_close = True
            return True

        # CLOSED state — only wake on "Lumi"
        if _WAKE_PATTERN.search(text):
            self._open_window()
            return True

        return False

    def on_response_sent(self) -> None:
        """
        Called by LumiAgent after a response has been fully streamed.
        Refreshes the window or closes it if a close was pending.
        """
        if getattr(self, "_pending_close", False):
            self._close_window()
            self._pending_close = False
        else:
            self._refresh_window()

    def force_close(self) -> None:
        """Close the window immediately (e.g. after explicit goodbye)."""
        self._close_window()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_timeout(self) -> None:
        if self._state == WindowState.ACTIVE and time.monotonic() > self._window_expires:
            self._close_window()

    def _open_window(self) -> None:
        self._state = WindowState.ACTIVE
        self._window_expires = time.monotonic() + self._window_seconds
        self._pending_close = False

    def _refresh_window(self) -> None:
        if self._state == WindowState.ACTIVE:
            self._window_expires = time.monotonic() + self._window_seconds

    def _close_window(self) -> None:
        self._state = WindowState.CLOSED
        self._window_expires = 0.0
