"""What the app can know about an applicant, independent of any USCIS form.

Values are stored in canonical form (ISO dates, F/M/X for sex, digits only for numbers) and
shown the way the USCIS online forms ask for them (MM/DD/YYYY). Each field says which documents
can supply it; fields no document can supply are typed by the preparer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    group: str
    kind: str = "text"                     # text | date | choice | date_or_ds
    choices: tuple[str, ...] = ()
    pattern: str | None = None
    docs: tuple[str, ...] = ()             # documents that can supply it; empty = typed by you


IDENTITY, PASSPORT, ARRIVAL, VISA, ADDRESS, APPLICATION = (
    "Identity", "Passport", "Last arrival (I-94)", "Visa", "Mailing address", "Application")

FIELDS: tuple[Field, ...] = (
    Field("family_name", "Family name (last name)", IDENTITY, docs=("passport", "visa", "i94")),
    Field("given_name", "Given name (first name)", IDENTITY, docs=("passport", "visa", "i94")),
    Field("middle_name", "Middle name", IDENTITY, docs=("passport", "visa", "i94")),
    Field("sex", "Sex", IDENTITY, "choice", ("F", "M", "X"), docs=("passport", "visa")),
    Field("birth_date", "Date of birth", IDENTITY, "date", docs=("passport", "visa", "i94")),
    Field("birth_city", "City or town of birth", IDENTITY),
    Field("birth_country", "Country of birth", IDENTITY),
    Field("nationality_code", "Citizenship (3-letter code on the passport)", IDENTITY,
          pattern=r"[A-Z]{3}", docs=("passport", "visa")),
    Field("citizenship_name", "Country of citizenship (as printed on the I-94)", IDENTITY, docs=("i94",)),
    Field("marital_status", "Marital status", IDENTITY, "choice",
          ("Single", "Married", "Divorced", "Widowed")),
    Field("a_number", "A-Number (digits only)", IDENTITY, pattern=r"\d{7,9}"),
    Field("passport_number", "Passport number", PASSPORT, docs=("passport", "i94")),
    Field("passport_expiry", "Passport expiration date", PASSPORT, "date", docs=("passport",)),
    Field("passport_country_code", "Passport issued by (3-letter code)", PASSPORT,
          pattern=r"[A-Z]{3}", docs=("passport",)),
    Field("i94_number", "I-94 admission number", ARRIVAL, pattern=r"[A-Z0-9]{11}", docs=("i94",)),
    Field("last_entry_date", "Date of last arrival", ARRIVAL, "date", docs=("i94",)),
    Field("issue_date", "Issue date (I-94 arrival/issued date)", ARRIVAL, "date", docs=("i94",)),
    Field("class_of_admission", "Class of admission", ARRIVAL, docs=("i94",)),
    Field("admit_until", "Admit until (date, or D/S)", ARRIVAL, "date_or_ds", docs=("i94",)),
    Field("sevis_id", "SEVIS number", ARRIVAL, pattern=r"N\d{10}"),
    Field("visa_number", "Visa number", VISA, docs=("visa",)),
    Field("visa_expiry", "Visa expiration date", VISA, "date", docs=("visa",)),
    Field("street", "Street number and name", ADDRESS),
    Field("city", "City or town", ADDRESS),
    Field("state", "State (2 letters)", ADDRESS, pattern=r"[A-Z]{2}"),
    Field("zip", "ZIP code", ADDRESS, pattern=r"\d{5}"),
    Field("reason", "Reason for applying (I-765)", APPLICATION, "choice", ("1", "2", "3")),
)

BY_KEY = {f.key: f for f in FIELDS}
GROUPS = tuple(dict.fromkeys(f.group for f in FIELDS))

# When two documents give different values, the lower number wins and the other is flagged.
DOC_RANK = {"passport": 0, "visa": 1, "i94": 2}
DOC_LABEL = {"passport": "passport", "visa": "visa", "i94": "I-94"}


def validate(key: str, value: str) -> str | None:
    f = BY_KEY.get(key)
    if f is None:
        return f"no such field {key!r}"
    if f.kind == "choice" and value not in f.choices:
        return f"{f.label}: must be one of {', '.join(f.choices)}"
    if f.kind == "date" or (f.kind == "date_or_ds" and value != "D/S"):
        try:
            date.fromisoformat(value)
        except ValueError:
            return f"{f.label}: use YYYY-MM-DD"
    if f.pattern and not re.fullmatch(f.pattern, value):
        return f"{f.label}: unexpected format"
    return None


def display(key: str, value: str) -> str:
    """The value as the USCIS online form expects to see it."""
    f = BY_KEY[key]
    if f.kind in ("date", "date_or_ds") and value != "D/S":
        d = date.fromisoformat(value)
        return f"{d.month:02d}/{d.day:02d}/{d.year:04d}"
    return value


def normalize(key: str, value: str) -> str:
    """Comparison form: ignores case, spacing and punctuation so 'ANNA-MARIA' equals 'Anna Maria'."""
    return re.sub(r"[^A-Z0-9]", "", value.upper())
