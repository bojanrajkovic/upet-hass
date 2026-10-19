"""Pure decisions for the persistent MQTT connection, free of Home Assistant imports so tests can load them."""

from __future__ import annotations

from typing import Any

MIN_RECONNECT_S = 60
MAX_RECONNECT_S = 1800
# A session that lasted this long was healthy, so the next drop starts the backoff over.
STABLE_SESSION_S = 600
# Our own REST login invalidates our IM session, so reconnect almost at once.
OWN_LOGIN_RECONNECT_S = 5


def reconnect_delay(previous_s: float, *, session_s: float, own_login: bool) -> float:
    """Seconds to wait before reconnecting after a session ended.

    Another login on the account (the phone app, a script) kicks us, and
    reconnecting kicks it back, so repeated short sessions back off from one
    minute to thirty. A session ended by our own token refresh reconnects in
    seconds instead.
    """
    if own_login:
        return OWN_LOGIN_RECONNECT_S
    if session_s >= STABLE_SESSION_S or previous_s <= 0:
        return MIN_RECONNECT_S
    return min(previous_s * 2, MAX_RECONNECT_S)


def presence_change(previous: dict[str, Any] | None, current: dict[str, Any]) -> bool | None:
    """True when a cat stepped in, False when it stepped out, None otherwise.

    The box reports `toilet_state=1` while a cat is inside and drops the field
    once it leaves, which is when the vendor writes the visit record. Without a
    previous state (right after a connect) there's no change to report.
    """
    if previous is None:
        return None
    was_inside, inside = previous.get("toilet_state") == 1, current.get("toilet_state") == 1
    return inside if was_inside != inside else None
