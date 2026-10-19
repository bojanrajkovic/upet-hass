"""Pure decisions for the persistent MQTT connection, free of Home Assistant imports so tests can load them."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class Presence:
    """Whether a cat is in the box, as best the box's state pushes can tell."""

    inside: bool
    # The cover came off since the box was last idle. Removing it jostles the scale,
    # which reports toilet_state=1 until things settle, so scale readings don't count.
    cover_off: bool


def next_presence(previous: Presence | None, state: dict[str, Any]) -> Presence:
    """Fold one state push into presence.

    The box reports toilet_state=1 while something weighs on the scale. That's a cat,
    unless the cover is off, or was off and the box hasn't been idle since.
    """
    on_scale = state.get("toilet_state") == 1
    cover_off = state.get("lid_state") == 1 or (previous is not None and previous.cover_off and on_scale)
    return Presence(inside=on_scale and not cover_off, cover_off=cover_off)
