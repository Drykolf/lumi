"""
Interrupt handler — Level 1 heuristic (section 9.19.1, Fase 2).

Decides the interrupt type locally in <50 ms without calling any LLM.
Level 2+ (LLM classification, resume logic) are added in Fase 3 and 5.
"""

from enum import Enum, auto


class InterruptType(Enum):
    HARD_PAUSE = auto()   # Cancel immediately; wait for Jose to speak
    SOFT_PAUSE = auto()   # Finish current sentence then yield
    IGNORE = auto()       # Likely noise; keep speaking


# Keywords that signal Jose wants Lumi to stop right now.
_STOP_KEYWORDS = {
    "espera", "para", "detente", "stop", "no", "calma",
    "lumi para", "lumi espera", "para lumi",
}

# Minimum token count below which we treat the fragment as noise.
_NOISE_THRESHOLD = 3


def classify(heard_response: str, interrupting_text: str = "") -> InterruptType:
    """
    Level 1 heuristic classification (section 9.19.1).

    Args:
        heard_response:    The part of Lumi's response delivered before the cut.
        interrupting_text: ASR transcription of Jose's interrupting speech
                           (empty in Fase 2 — not available at interrupt time).
    """
    words = interrupting_text.lower().split()

    # Too short to be intentional speech → noise
    if interrupting_text and len(words) < _NOISE_THRESHOLD:
        return InterruptType.IGNORE

    # Explicit stop keywords present → hard pause
    if any(kw in interrupting_text.lower() for kw in _STOP_KEYWORDS):
        return InterruptType.HARD_PAUSE

    # Default for Fase 2: always treat as soft pause (finish sentence, then yield)
    return InterruptType.SOFT_PAUSE


class InterruptContext:
    """
    Carries interrupt state between handle_interrupt() and the next chat() turn.
    Consumed by LumiAgent to build the memory entry and decide how to resume.
    """

    def __init__(self) -> None:
        self.active = False
        self.heard_response: str = ""
        self.interrupt_type: InterruptType = InterruptType.SOFT_PAUSE

    def record(self, heard_response: str, interrupt_type: InterruptType) -> None:
        self.active = True
        self.heard_response = heard_response
        self.interrupt_type = interrupt_type

    def clear(self) -> None:
        self.active = False
        self.heard_response = ""
        self.interrupt_type = InterruptType.SOFT_PAUSE
