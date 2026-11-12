"""Passport machine-readable zone (ICAO Doc 9303, TD3: two lines of 44 characters).

Parsing is deterministic, with every check digit verified. A result whose check
digits fail is returned with ``valid=False`` so the review screen can flag it;
it is never silently corrected.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

_WEIGHTS = (7, 3, 1)
_LINE = re.compile(r"[A-Z0-9<]{44}")


class MrzError(ValueError):
    pass


def _value(ch: str) -> int:
    if ch.isdigit():
        return int(ch)
    if ch == "<":
        return 0
    if "A" <= ch <= "Z":
        return ord(ch) - ord("A") + 10
    raise MrzError(f"invalid MRZ character {ch!r}")


def check_digit(text: str) -> int:
    return sum(_value(c) * _WEIGHTS[i % 3] for i, c in enumerate(text)) % 10


def _clean(text: str) -> str:
    return text.replace("<", " ").strip()


def _date(yymmdd: str, *, birth: bool, today: date) -> date | None:
    if not yymmdd.isdigit():
        return None
    yy, mm, dd = int(yymmdd[:2]), int(yymmdd[2:4]), int(yymmdd[4:])
    # A birth year later than this year's two digits must be last century.
    year = (1900 + yy) if (birth and yy > today.year % 100) else 2000 + yy
    try:
        return date(year, mm, dd)
    except ValueError:
        return None


@dataclass(frozen=True)
class PassportMrz:
    issuing_country: str
    surname: str
    given_names: str
    document_number: str
    nationality: str
    birth_date: date | None
    sex: str
    expiry_date: date | None
    checks: dict[str, bool] = field(default_factory=dict)
    # The name field is 39 characters. A name that reaches the last one may have been cut,
    # and the printed zone of the passport is then the only complete record of it.
    name_possibly_truncated: bool = False
    birth_raw: str = ""        # the six characters as printed, YYMMDD
    expiry_raw: str = ""

    @property
    def valid(self) -> bool:
        return all(self.checks.values())


def parse_td3(line1: str, line2: str, *, today: date | None = None) -> PassportMrz:
    today = today or date.today()
    l1, l2 = line1.strip().upper(), line2.strip().upper()
    if not (_LINE.fullmatch(l1) and _LINE.fullmatch(l2)):
        raise MrzError("a TD3 MRZ is two lines of exactly 44 characters from A-Z, 0-9 and '<'")
    if l1[0] != "P":
        raise MrzError("not a passport MRZ (document type must start with 'P')")

    def check(value: slice, digit_pos: int) -> bool:
        return l2[digit_pos].isdigit() and check_digit(l2[value]) == int(l2[digit_pos])

    # An empty optional field may carry '<' instead of a check digit.
    personal_empty = set(l2[28:42]) == {"<"} and l2[42] == "<"
    checks = {
        "document_number": check(slice(0, 9), 9),
        "birth_date": check(slice(13, 19), 19),
        "expiry_date": check(slice(21, 27), 27),
        "personal_number": personal_empty or check(slice(28, 42), 42),
        "composite": l2[43].isdigit()
        and check_digit(l2[0:10] + l2[13:20] + l2[21:43]) == int(l2[43]),
    }
    surname, _, given = l1[5:44].partition("<<")
    return PassportMrz(
        issuing_country=l1[2:5].replace("<", ""),
        surname=_clean(surname),
        given_names=_clean(given.replace("<", " ")),
        document_number=l2[0:9].replace("<", ""),
        nationality=l2[10:13].replace("<", ""),
        birth_date=_date(l2[13:19], birth=True, today=today),
        sex=l2[20] if l2[20] in "MF" else "X",
        expiry_date=_date(l2[21:27], birth=False, today=today),
        checks=checks,
        name_possibly_truncated=l1[43] != "<",
        birth_raw=l2[13:19], expiry_raw=l2[21:27],
    )


def parse_mrv(line1: str, line2: str, *, today: date | None = None) -> PassportMrz:
    """Machine-readable visa (ICAO 9303 part 7): MRV-A is 2x44, MRV-B is 2x36.

    The first 28 characters of line 2 follow the passport layout (document number, nationality,
    birth date, sex, expiry date, each with its check digit); a visa has no composite digit.
    The result reuses ``PassportMrz``: ``document_number`` is the visa number.
    """
    today = today or date.today()
    l1, l2 = line1.strip().upper(), line2.strip().upper()
    size = len(l1)
    if size not in (36, 44) or len(l2) != size:
        raise MrzError("a visa MRZ is two lines of 44 (MRV-A) or 36 (MRV-B) characters")
    if not (re.fullmatch(r"[A-Z0-9<]+", l1) and re.fullmatch(r"[A-Z0-9<]+", l2)):
        raise MrzError("MRZ lines may only contain A-Z, 0-9 and '<'")
    if l1[0] != "V":
        raise MrzError("not a visa MRZ (document type must start with 'V')")

    def check(value: slice, digit_pos: int) -> bool:
        return l2[digit_pos].isdigit() and check_digit(l2[value]) == int(l2[digit_pos])

    checks = {
        "document_number": check(slice(0, 9), 9),
        "birth_date": check(slice(13, 19), 19),
        "expiry_date": check(slice(21, 27), 27),
    }
    surname, _, given = l1[5:].partition("<<")
    return PassportMrz(
        issuing_country=l1[2:5].replace("<", ""),
        surname=_clean(surname),
        given_names=_clean(given.replace("<", " ")),
        document_number=l2[0:9].replace("<", ""),
        nationality=l2[10:13].replace("<", ""),
        birth_date=_date(l2[13:19], birth=True, today=today),
        sex=l2[20] if l2[20] in "MF" else "X",
        expiry_date=_date(l2[21:27], birth=False, today=today),
        checks=checks,
        name_possibly_truncated=l1[-1] != "<",
        birth_raw=l2[13:19], expiry_raw=l2[21:27],
    )
