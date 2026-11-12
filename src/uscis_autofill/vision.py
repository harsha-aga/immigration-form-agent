"""Apple's on-device text recognition (the Vision framework), used as the first reader on macOS.

It runs locally (nothing leaves the computer), takes a fraction of a second per page, and reads
printed text far more accurately than Tesseract on scans. Its one weakness on a passport is the
'<' filler of the machine-readable lines: it often drops some of them, or splits a line in two.
``repair_td3`` puts them back, and accepts the result only if every check digit then passes.
"""

from __future__ import annotations

import io
import re
from datetime import date

from .mrz import MrzError, parse_td3

try:                                   # absent off macOS, or when pyobjc-framework-Vision is not installed
    import Vision
    from Foundation import NSData
except Exception:                      # noqa: BLE001
    Vision = None


def available() -> bool:
    return Vision is not None


def read_text(img) -> str:
    """All text on the image, one recognised line per output line."""
    if Vision is None:
        return ""
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "PNG")
    raw = buf.getvalue()
    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setUsesLanguageCorrection_(False)      # language models "fix" names and codes into words
    request.setMinimumTextHeight_(0.0)
    handler = Vision.VNImageRequestHandler.alloc().initWithData_options_(
        NSData.dataWithBytes_length_(raw, len(raw)), None)
    ok, _err = handler.performRequests_error_([request], None)
    if not ok:
        return ""
    out = []
    for obs in request.results() or []:
        top = obs.topCandidates_(1)
        if top:
            out.append(str(top[0].string()))
    return "\n".join(out)


# ---- repairing the '<' filler ----------------------------------------------------------------

_FILLER = str.maketrans({"«": "<", "‹": "<", "〈": "<", "＜": "<"})
_CHARS = re.compile(r"[A-Z0-9<]+")
_DUMMY_L1 = "P<UTOA<<B".ljust(44, "<")
MAX_MISSING = 16


def _clean(line: str) -> str:
    return re.sub(r"\s+", "", line.translate(_FILLER).upper())


def _checks_pass(l2: str, today: date | None) -> bool:
    try:
        return parse_td3(_DUMMY_L1, l2, today=today).valid
    except MrzError:
        return False


def _compositions(total: int, parts: int):
    """Every way to split ``total`` into ``parts`` non-negative counts."""
    if parts == 1:
        yield (total,)
        return
    for first in range(total + 1):
        for rest in _compositions(total - first, parts - 1):
            yield (first,) + rest


def _insert(s: str, spots: list[int], counts: tuple[int, ...]) -> str:
    out, last = [], 0
    for pos, n in sorted(zip(spots, counts)):
        out.append(s[last:pos] + "<" * n)
        last = pos
    out.append(s[last:])
    return "".join(out)


def repair_line2(s: str, today: date | None = None) -> str | None:
    """Re-insert dropped '<' into a short second line. Only the position of fillers is guessed;
    every other character is kept as read, and the answer must pass all five check digits."""
    if len(s) == 44:
        return s if _checks_pass(s, today) else None
    missing = 44 - len(s)
    if not (0 < missing <= MAX_MISSING):
        return None
    spots = sorted({i for i, ch in enumerate(s) if ch == "<"} | {9, 28, 42, len(s)})
    spots = [p for p in spots if p <= len(s)]
    if len(spots) > 8:
        return None
    for counts in _compositions(missing, len(spots)):
        cand = _insert(s, spots, counts)
        if _checks_pass(cand, today):
            return cand
    return None


def repair_td3(text: str, today: date | None = None) -> str:
    """Text with a passport's two machine-readable lines rebuilt to 44 characters each, if that can
    be done and verified. Otherwise the text is returned unchanged."""
    lines = [_clean(ln) for ln in text.splitlines()]
    for i, a in enumerate(lines):
        if not (a.startswith("P") and "<<" in a and 28 <= len(a) <= 44 and _CHARS.fullmatch(a)):
            continue
        rest, joined = [], ""
        for b in lines[i + 1: i + 4]:               # the second line may arrive in pieces
            if not _CHARS.fullmatch(b):
                break
            joined += b
            rest.append(b)
            fixed = repair_line2(joined, today) if 30 <= len(joined) <= 44 else None
            if fixed:
                return "\n".join(lines[:i] + [a.ljust(44, "<"), fixed] + lines[i + 1 + len(rest):])
    return text
