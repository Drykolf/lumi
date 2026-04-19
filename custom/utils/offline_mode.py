"""Canned messages and state for Lumi's offline / dormida mode (section 5.3)."""

# First message when Lumi loses connectivity mid-session.
MSG_OFFLINE = "[neutral] ...a ver... la señal está perdiendo el tempo... zzz... Jose, espera a que vuelva la luz... zzz..."

# Acknowledgement when connectivity is restored.
MSG_BACK_ONLINE = "A ver... ya recuperé el hilo. Ese silencio fue bastante poco estético. ¿En qué nos quedamos? Espero que no hayas hecho un desastre mientras no estaba."

class OfflineState:
    """
    Tracks whether the offline message has already been delivered this session
    so we send it exactly once per outage (section 5.3 rule 1).
    """

    def __init__(self) -> None:
        self._notified = False
        self._was_offline = False

    def should_notify(self, is_online: bool) -> bool:
        """Return True the first time we detect an offline event."""
        if not is_online and not self._notified:
            self._notified = True
            self._was_offline = True
            return True
        return False

    def on_reconnect(self) -> bool:
        """Return True if we should send the back-online message."""
        if self._was_offline:
            self._notified = False
            self._was_offline = False
            return True
        return False
