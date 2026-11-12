"""Field map for Form I-765 (Application for Employment Authorization).

Each entry names the same value in both layers of the hybrid PDF: the XFA data element (what
Adobe Acrobat reads, and what makes it draw the page barcode) and the AcroForm widget(s) (what
Preview, browsers and other viewers show). One table, so the layers cannot drift apart.

Only blanks whose SHA-256 is listed in APPROVED_BLANKS may be filled; the map was written
against exactly those bytes. A new edition needs a new map and a new entry, never an edit here.

Passport-derived keys are filled by the passport; everything else is entered by the preparer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

APPROVED_BLANKS = {
    "9ac0eae287749d4c2dfa0a591f464cc2124c18647c10e999b59484f090e0dc7d": "I-765 edition 08/21/25",
}

P1, P2, P3, P7 = "form1[0].Page1[0].", "form1[0].Page2[0].", "form1[0].Page3[0].", "form1[0].Page7[0]."


def _us_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.month:02d}/{d.day:02d}/{d.year:04d}"


@dataclass(frozen=True)
class Text:
    key: str
    xfa: str                       # path under form1 in the datasets packet
    acro: tuple[str, ...]          # AcroForm field names (a value can appear on several pages)
    pattern: str | None = None     # value must fully match this
    is_date: bool = False          # canonical ISO date; XFA stores ISO, AcroForm shows MM/DD/YYYY
    label: str = ""

    def xfa_value(self, v: str) -> str:
        return v

    def acro_value(self, v: str) -> str:
        return _us_date(v) if self.is_date else v


@dataclass(frozen=True)
class Choice:
    """A checkbox group. The XFA node holds one value; exactly one widget carries that on-state."""
    key: str
    xfa: str
    acro_base: str                 # widgets are acro_base + "[n]"
    allowed: tuple[str, ...]       # canonical value -> same string used as on-state
    translate: dict[str, str] = field(default_factory=dict)  # canonical value -> on-state
    label: str = ""

    def on_state(self, v: str) -> str:
        return self.translate.get(v, v)


SPEC: tuple[Text | Choice, ...] = (
    Text("family_name", "Line1a_FamilyName", (P1 + "Line1a_FamilyName[0]", P7 + "Line1a_FamilyName[0]"),
         label="Family name (last name)"),
    Text("given_name", "Line1b_GivenName", (P1 + "Line1b_GivenName[0]", P7 + "Line1b_GivenName[0]"),
         label="Given name (first name)"),
    Text("middle_name", "Line1c_MiddleName", (P1 + "Line1c_MiddleName[0]", P7 + "Line1c_MiddleName[0]"),
         label="Middle name"),
    Text("a_number", "Line7_AlienNumber", (P2 + "Line7_AlienNumber[0]", P7 + "Line7_AlienNumber[0]"),
         pattern=r"\d{7,9}", label="A-Number (digits only)"),
    Text("street", "Page2/Line4b_StreetNumberName", (P2 + "Line4b_StreetNumberName[0]",),
         label="Mailing address: street number and name"),
    Text("city", "Page2/Pt2Line5_CityOrTown", (P2 + "Pt2Line5_CityOrTown[0]",),
         label="Mailing address: city or town"),
    Text("state", "Page2/Pt2Line5_State", (P2 + "Pt2Line5_State[0]",), pattern=r"[A-Z]{2}",
         label="Mailing address: state (2 letters)"),
    Text("zip", "Page2/Pt2Line5_ZipCode", (P2 + "Pt2Line5_ZipCode[0]",), pattern=r"\d{5}",
         label="Mailing address: ZIP code"),
    Text("birth_date", "Page3/Line19_DOB", (P3 + "Line19_DOB[0]",), is_date=True,
         label="Date of birth"),
    Text("passport_number", "Page3/Line20b_Passport", (P3 + "Line20b_Passport[0]",),
         label="Passport number (last arrival)"),
    Text("passport_expiry", "Page3/Line20e_ExpDate", (P3 + "Line20e_ExpDate[0]",), is_date=True,
         label="Passport expiration date (last arrival)"),
    # F/M/X are the canonical values; the form's on-states for Female and Male are N and Y.
    # 'X' has no box on this edition, so it is deliberately not allowed.
    Choice("sex", "Line9_Checkbox", P2 + "Line9_Checkbox", ("F", "M"),
           translate={"F": "N", "M": "Y"}, label="Sex"),
    Choice("marital_status", "Line10_Checkbox", P2 + "Line10_Checkbox",
           ("Single", "Married", "Divorced", "Widowed"), label="Marital status"),
    Choice("reason", "Part1_Checkbox", P1 + "Part1_Checkbox", ("1", "2", "3"),
           label="Reason for applying (1 initial, 2 replacement, 3 renewal)"),
)

BY_KEY = {s.key: s for s in SPEC}

# Keys a passport can supply. Everything else is entered by the preparer.
PASSPORT_KEYS = ("family_name", "given_name", "middle_name", "sex", "birth_date",
                 "passport_number", "passport_expiry")


def validate(key: str, value: str) -> str | None:
    """Return a problem description, or None if the value is acceptable for this field."""
    spec = BY_KEY.get(key)
    if spec is None:
        return f"no such field {key!r} on this form"
    if isinstance(spec, Choice):
        if value not in spec.allowed:
            return f"{spec.label}: must be one of {', '.join(spec.allowed)}"
        return None
    if spec.is_date:
        try:
            date.fromisoformat(value)
        except ValueError:
            return f"{spec.label}: not a valid date"
    if spec.pattern and not re.fullmatch(spec.pattern, value):
        return f"{spec.label}: unexpected format"
    return None
