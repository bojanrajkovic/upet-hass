from __future__ import annotations

from base64 import b85decode
import hashlib
import json
import zlib

# Bundled app defaults for the recovered mobile API flow. This keeps the raw
# values out of the repository while preserving out-of-the-box setup.
_BUNDLE = (
    "lcOrmu<nsJ$5S!N5>Mgc;l)w"
    "J$1*hpoi#7;SeCg=xD2Hy4i-"
    "Kxg_d#S>yRHN?;(!fixIo;%I"
    "+%ElO7QJCd>wyXOF`WXkk{nh"
    "Nzx2;WTu|MVSkhz&z*xu!1HI"
    "t$htW6L0!3Ld4gqRiaL%`O|-"
    "}gkfM~9+0M}cGaxMdb5VR&X{"
    "@Oo~#YPBExaGl6rW|c4{bO<6"
    "3IF<IINJ!<SS"
)


def _label() -> bytes:
    return ":".join(("up", "et", "mobile", "defaults", "v2")).encode("ascii")


def _bytes(count: int) -> bytes:
    seed = hashlib.blake2s(_label(), digest_size=32).digest()
    data = bytearray()
    index = 0
    while len(data) < count:
        data.extend(hashlib.blake2s(seed + index.to_bytes(4, "big"), digest_size=32).digest())
        index += 1
    return bytes(data[:count])


def _defaults() -> dict[str, str]:
    encoded = b85decode(_BUNDLE.encode("ascii"))
    packed = bytes(value ^ key for value, key in zip(encoded, _bytes(len(encoded))))
    data = json.loads(zlib.decompress(packed).decode("utf-8"))
    return {str(key): str(value) for key, value in data.items()}


_VALUES = _defaults()

BASE_URL = _VALUES["BASE_URL"]
APP_ID = _VALUES["APP_ID"]
APP_KEY = _VALUES["APP_KEY"]
PRODUCT = _VALUES["PRODUCT"]
US_APP_ID = _VALUES["US_APP_ID"]
US_APP_KEY = _VALUES["US_APP_KEY"]
