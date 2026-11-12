import json
from datetime import date
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from uscis_autofill import extract, profile
from uscis_autofill.mrz import MrzError, check_digit, parse_mrv
from uscis_autofill.session import Session

TODAY = date(2026, 11, 11)
P1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
P2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"


def visa_lines(size=44, name="ERIKSSON<<ANNA<MARIA", number="12345678", dob="740812", exp="270415", sex="F"):
    """Build a valid MRV: the check digits are computed, never typed."""
    l1 = ("V<UTO" + name).ljust(size, "<")
    doc = number.ljust(9, "<")
    l2 = f"{doc}{check_digit(doc)}UTO{dob}{check_digit(dob)}{sex}{exp}{check_digit(exp)}".ljust(size, "<")
    return l1, l2


I94_TWO_LINE = """Most Recent I-94
Admission (I-94) Record Number
88888888AA1
Most Recent Date of Entry
2024-02-03
Class of Admission
F-1
Admit Until Date
D/S
Last/Surname
ERIKSSON
First (Given) Name
ANNA MARIA
Birth Date
1974-08-12
Document Number
L898902C3
Country of Citizenship
UTOPIA
"""
I94_ONE_LINE = """Get Most Recent I-94
Admission (I-94) Record Number: 88888888AA1
Most Recent Date of Entry: 02/03/2024
Class of Admission: F-1
Admit Until Date: 06/30/2026
Last/Surname: ERIKSSON
First (Given) Name: ANNA MARIA
Birth Date: 08/12/1974
Document Number: L898902C3
Country of Citizenship: UTOPIA
"""


# ---- visa ----------------------------------------------------------------------------

@pytest.mark.parametrize("size", [44, 36])
def test_visa_mrz_parses_in_both_sizes_and_check_digits_pass(size):
    l1, l2 = visa_lines(size)
    mrz = parse_mrv(l1, l2, today=TODAY)
    assert mrz.valid and mrz.document_number == "12345678"
    assert (mrz.surname, mrz.given_names) == ("ERIKSSON", "ANNA MARIA")
    assert mrz.expiry_date == date(2027, 4, 15)


def test_visa_with_a_changed_digit_fails_and_a_passport_is_not_a_visa():
    l1, l2 = visa_lines()
    assert not parse_mrv(l1, l2[:13] + "0" + l2[14:], today=TODAY).valid
    with pytest.raises(MrzError):
        parse_mrv(P1, P2)


def test_find_visa_lines_among_noise():
    l1, l2 = visa_lines()
    assert extract.find_mrv_lines(f"VISA\n{l1}\n{l2}\n")[0] == (l1, l2)
    assert extract.find_mrv_lines(f"{P1}\n{P2}")[0] is None


# ---- I-94 ----------------------------------------------------------------------------

@pytest.mark.parametrize("text", [I94_TWO_LINE, I94_ONE_LINE])
def test_i94_is_parsed_in_either_layout(text):
    assert extract.looks_like_i94(text)
    got, warnings = extract.parse_i94(text)
    assert not warnings
    assert got["i94_number"] == "88888888AA1" and got["class_of_admission"] == "F-1"
    assert (got["family_name"], got["given_name"], got["middle_name"]) == ("ERIKSSON", "ANNA", "MARIA")
    assert got["birth_date"] == "1974-08-12" and got["last_entry_date"] == "2024-02-03"
    assert got["passport_number"] == "L898902C3"


def test_i94_admit_until_accepts_ds_or_a_date():
    assert extract.parse_i94(I94_TWO_LINE)[0]["admit_until"] == "D/S"
    assert extract.parse_i94(I94_ONE_LINE)[0]["admit_until"] == "2026-06-30"


def test_a_bad_i94_number_is_reported_not_used():
    got, warnings = extract.parse_i94(I94_TWO_LINE.replace("88888888AA1", "123"))
    assert "i94_number" not in got and any("admission number" in w for w in warnings)


def test_unrelated_text_is_not_an_i94():
    assert not extract.looks_like_i94("Electric bill, account 1234")


# ---- reconciliation ------------------------------------------------------------------

def _session_with_i94(text):
    s = Session(None, today=TODAY)
    s.add_mrz_text(P1, P2)
    values, _ = extract.parse_i94(text)
    s.extractions.append(extract.Extraction(
        "i94.pdf", "i94sha", ["i94"], extract.facts_from_i94(values, "i94.pdf (I-94)")))
    return s


def row(s, key):
    return next(r for r in s.resolve() if r["key"] == key)


def test_matching_documents_agree_and_i94_only_fields_are_read_unchecked():
    s = _session_with_i94(I94_TWO_LINE)
    assert row(s, "family_name")["status"] == "read"                # names have no check digit
    assert row(s, "birth_date")["status"] == "from_document"        # date of birth does
    assert row(s, "birth_date")["value"] == "1974-08-12"
    r = row(s, "i94_number")
    assert r["status"] == "read" and r["value"] == "88888888AA1"      # no checksum, but not a blocker
    assert not s.state()["blockers"]


def test_an_i94_that_disagrees_with_the_passport_is_flagged_and_the_passport_wins():
    s = _session_with_i94(I94_TWO_LINE.replace("ERIKSSON", "ERIKSON").replace("1974-08-12", "1974-08-21"))
    fam = row(s, "family_name")
    assert fam["value"] == "ERIKSSON" and fam["status"] == "mismatch"
    assert "I-94 says ERIKSON" in fam["detail"]
    assert row(s, "birth_date")["value"] == "1974-08-12"
    assert "I-94 says 08/21/1974" in row(s, "birth_date")["detail"]     # shown the way the form asks
    assert len(s.state()["attention"]) == 2 and not s.state()["blockers"]


def test_name_spacing_and_case_do_not_count_as_a_mismatch():
    s = _session_with_i94(I94_TWO_LINE.replace("ANNA MARIA", "Anna  Maria"))
    assert row(s, "given_name")["status"] == "read"


def test_visa_and_passport_both_supply_shared_fields():
    s = Session(None, today=TODAY)
    s.add_mrz_text(P1, P2)
    s.add_mrz_text(*visa_lines())
    assert row(s, "visa_number")["value"] == "12345678"
    assert row(s, "family_name")["status"] == "read"


# ---- data sheet ----------------------------------------------------------------------

def test_data_sheet_shows_dates_as_the_portal_asks_and_lists_what_is_missing():
    s = _session_with_i94(I94_TWO_LINE)
    out = s.data_sheet("txt")
    assert out["ok"]
    t = out["text"]
    assert "Date of birth: 08/12/1974" in t and "Admit until (date, or D/S): D/S" in t
    assert "NOT FILLED IN:" in t and "A-Number" in t and "SHA-256" in t


def test_data_sheet_json_and_csv_carry_the_source_of_each_value():
    s = _session_with_i94(I94_TWO_LINE)
    data = json.loads(s.data_sheet("json")["text"])
    assert data["fields"]["family_name"]["source"].endswith("(passport MRZ)")
    assert data["fields"]["birth_date"]["shown_as"] == "08/12/1974"
    assert "i94sha" in json.dumps(data["inputs_sha256"]) or "typed passport MRZ" in data["inputs_sha256"]
    assert s.data_sheet("csv")["text"].startswith("section,field,value,source,status")


def test_data_sheet_is_refused_while_a_blocker_exists_or_nothing_was_read():
    assert not Session(None, today=TODAY).data_sheet()["ok"]
    s = Session(None, today=TODAY)
    s.add_mrz_text(P1, P2[:13] + "0" + P2[14:])
    out = s.data_sheet()
    assert not out["ok"] and "Resolve" in out["error"]


def test_typed_values_are_validated_by_the_catalogue():
    s = Session(None, today=TODAY)
    assert "error" in s.set_value("sevis_id", "123")
    assert "error" not in s.set_value("sevis_id", "N0012345678")
    assert profile.display("admit_until", "D/S") == "D/S"


# ---- OCR path ------------------------------------------------------------------------

@pytest.mark.skipif(not extract.ocr_available(), reason="tesseract not installed")
def test_an_i94_screenshot_is_read_by_ocr(tmp_path):
    font_path = "/System/Library/Fonts/Menlo.ttc"
    if not Path(font_path).exists():
        pytest.skip("Menlo font not available")
    img = Image.new("RGB", (1400, 1000), "white")
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(font_path, 30)
    for i, line in enumerate(I94_ONE_LINE.strip().splitlines()):
        d.text((50, 40 + i * 70), line, fill="black", font=f)
    p = tmp_path / "i94.png"
    img.save(p)
    ex = extract.extract_file(p, today=TODAY)
    assert "i94" in ex.kinds, ex.warnings
    got = {f.key: f.value for f in ex.facts}
    assert got.get("i94_number") == "88888888AA1" and got.get("family_name") == "ERIKSSON"


# ---- date formats shown next to the source ---------------------------------------------------

def test_mrz_dates_report_the_printed_text_and_the_century_assumed():
    s = Session(None, today=TODAY)
    s.add_mrz_text(P1, P2)
    dob, exp = row(s, "birth_date"), row(s, "passport_expiry")
    assert (dob["raw"], dob["fmt"], dob["display"]) == ("740812", "YYMMDD", "08/12/1974")
    assert (exp["raw"], exp["fmt"], exp["display"]) == ("120415", "YYMMDD", "04/15/2012")
    assert "read as 1974" in dob["detail"]


@pytest.mark.parametrize("printed, fmt, iso", [
    ("2024-02-03", "YYYY-MM-DD", "2024-02-03"),
    ("02/03/2024", "MM/DD/YYYY", "2024-02-03"),
    ("February 3, 2024", "Month D, YYYY", "2024-02-03"),
    ("03 Feb 2024", "D Mon YYYY", "2024-02-03"),
])
def test_i94_date_styles_are_named(printed, fmt, iso):
    got = extract.parse_date_format(printed)
    assert got and (got[0].isoformat(), got[1]) == (iso, fmt)


def test_i94_rows_carry_the_text_as_printed():
    s = _session_with_i94(I94_TWO_LINE)
    values, _ = extract.parse_i94(I94_TWO_LINE, printed := {})
    assert printed["last_entry_date"] == ("2024-02-03", "YYYY-MM-DD")
    assert printed["admit_until"][1] == "duration of status"
    s.extractions[-1].facts = extract.facts_from_i94(values, "i94.pdf (I-94)", printed)
    r = row(s, "last_entry_date")
    assert (r["raw"], r["fmt"]) == ("2024-02-03", "YYYY-MM-DD") and r["display"] == "02/03/2024"
    assert row(s, "family_name")["raw"] == ""        # only dates carry a format


def test_a_typed_date_says_which_format_to_use():
    s = Session(None, today=TODAY)
    s.set_value("last_entry_date", "2024-02-03")
    assert row(s, "last_entry_date")["fmt"].startswith("YYYY-MM-DD")


def test_i94_website_layout_with_arrival_issued_date():
    text = "Arrival/Issued Date: 2024 September 15\nClass of Admission: F1\nAdmit Until Date: D/S\n"
    assert extract.looks_like_i94(text)
    printed = {}
    got, warnings = extract.parse_i94(text, printed)
    assert not warnings
    assert got == {"last_entry_date": "2024-09-15", "issue_date": "2024-09-15",
                   "class_of_admission": "F1", "admit_until": "D/S"}
    assert printed["last_entry_date"] == ("2024 September 15", "YYYY Month D")


def test_issue_date_is_only_filled_when_the_i94_prints_arrival_issued_date():
    got, _ = extract.parse_i94(I94_TWO_LINE)          # older layout: "Most Recent Date of Entry"
    assert "last_entry_date" in got and "issue_date" not in got
    s = Session(None, today=TODAY)
    text = "Arrival/Issued Date: 2024 September 15\nClass of Admission: F1\nAdmit Until Date: D/S\n"
    printed = {}
    values, _ = extract.parse_i94(text, printed)
    s.extractions.append(extract.Extraction("i94.png", "x", ["i94"],
                                            extract.facts_from_i94(values, "i94.png (I-94)", printed)))
    a, i = row(s, "last_entry_date"), row(s, "issue_date")
    assert a["value"] == i["value"] == "2024-09-15" and i["display"] == "09/15/2024"
    assert (i["raw"], i["fmt"]) == ("2024 September 15", "YYYY Month D")


@pytest.mark.skipif(not extract.ocr_available(), reason="no OCR engine installed")
def test_a_cropped_i94_website_screenshot_is_read_by_ocr(tmp_path):
    """The layout the user showed: Arrival/Issued Date as 'YYYY Month D', class 'F1', admit until D/S."""
    font_path = "/System/Library/Fonts/Helvetica.ttc"
    if not Path(font_path).exists():
        pytest.skip("Helvetica font not available")
    img = Image.new("RGB", (900, 260), "white")
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(font_path, 34)
    for i, line in enumerate(["Arrival/Issued Date: 2024 September 15", "Class of Admission: F1",
                              "Admit Until Date: D/S"]):
        d.text((30, 20 + i * 70), line, fill="black", font=f)
    p = tmp_path / "i94-crop.png"
    img.save(p)
    ex = extract.extract_file(p, today=TODAY)
    assert "i94" in ex.kinds, ex.warnings
    got = {f.key: f.value for f in ex.facts}
    assert got["last_entry_date"] == got["issue_date"] == "2024-09-15"
    assert got["class_of_admission"] == "F1" and got["admit_until"] == "D/S"
