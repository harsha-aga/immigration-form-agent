import json
from datetime import date
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from uscis_autofill import extract
from uscis_autofill.session import Session

L1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
L2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"
TODAY = date(2026, 11, 11)
L2_BAD = L2[:13] + "0" + L2[14:]   # birth-date digit changed 7 -> 0, so its check digit fails
BLANK = Path(__file__).resolve().parents[1] / "forms" / "i-765.pdf"


def test_mrz_lines_are_found_in_noisy_text():
    text = f"PASSPORT\nSurname ERIKSSON\n{L1}\n{L2}\nfooter"
    assert extract.find_mrz_lines(text)[0] == (L1, L2)


def test_ocr_style_spacing_and_guillemets_are_normalised_but_nothing_is_repaired():
    spaced = L1.replace("<", "«", 3) + "\n" + " ".join(L2)
    assert extract.find_mrz_lines(spaced)[0] == (L1.replace("<", "«", 3).translate(extract._FILLER), L2)
    # a line two characters short is NOT padded out: the missing characters might be in the name
    lines, note = extract.find_mrz_lines(L1[:-2] + "\n" + L2)
    assert lines is None and "not 44" in note
    # characters missing from the data itself are never invented
    lines, note = extract.find_mrz_lines(L1 + "\n" + L2[:-3])
    assert lines is None and "not 44" in note
    lines, note = extract.find_mrz_lines(L1[:30] + "\n" + L2)
    assert lines is None


def test_facts_split_given_names_and_carry_the_check_status():
    ex = extract.extraction_from_lines("p.png", "abc", L1, L2, today=TODAY)
    got = {f.key: f.value for f in ex.facts}
    assert got["given_name"] == "ANNA" and got["middle_name"] == "MARIA"
    assert got["birth_date"] == "1974-08-12" and got["sex"] == "F"
    by = {f.key: f for f in ex.facts}
    covered = {"birth_date", "passport_number", "passport_expiry"}
    assert all(by[k].verified is True for k in covered)             # check digits cover these three
    assert all(f.verified is None for k, f in by.items() if k not in covered)   # names, sex: no check digit
    assert "no check digit" not in by["birth_date"].note and "check digit" in by["family_name"].note
    assert any("expired" in w for w in ex.warnings)                 # the specimen expired in 2012


def test_failed_check_digits_mark_every_fact_unverified():
    ex = extract.extraction_from_lines("p.png", "abc", L1, L2_BAD, today=TODAY)
    assert ex.facts and not any(f.verified for f in ex.facts)
    assert any("check digits FAILED" in w for w in ex.warnings)


def test_session_blocks_filling_until_an_unverified_passport_is_replaced(tmp_path):
    s = Session(BLANK if BLANK.exists() else None, today=TODAY)
    s.add_mrz_text(L1, L2_BAD)
    assert s.state()["blockers"]
    r = s.fill(str(tmp_path / "o.pdf"))
    assert r["ok"] is False and "Resolve" in r["error"]
    s.add_mrz_text(L1, L2)                                          # the good reading as well
    assert s.state()["blockers"]                                    # now two readings disagree


def test_two_files_that_disagree_are_a_conflict_and_typing_resolves_it():
    s = Session(None, today=TODAY)
    s.add_mrz_text(L1, L2)
    other = L1.replace("ANNA<MARIA", "ANNE<MARIA")
    s.add_mrz_text(other, L2)
    row = next(r for r in s.resolve() if r["key"] == "given_name")
    assert row["status"] == "conflict"
    s.set_value("given_name", "ANNA")
    assert next(r for r in s.resolve() if r["key"] == "given_name")["status"] == "entered"


def test_typing_over_the_passport_is_allowed_but_flagged():
    s = Session(None, today=TODAY)
    s.add_mrz_text(L1, L2)
    s.set_value("family_name", "ERICSSON")
    row = next(r for r in s.resolve() if r["key"] == "family_name")
    assert row["status"] == "overridden" and "ERIKSSON" in row["detail"]


def test_invalid_typed_value_is_rejected_with_a_message():
    s = Session(None, today=TODAY)
    out = s.set_value("zip", "12")
    assert "error" in out and "zip" not in s.typed


@pytest.mark.skipif(not BLANK.exists(), reason="blank I-765 not present")
def test_end_to_end_fill_writes_output_and_manifest(tmp_path):
    s = Session(BLANK, today=TODAY)
    s.add_mrz_text(L1, L2)
    s.set_value("a_number", "123456789")
    s.set_value("marital_status", "Single")
    res = s.fill(str(tmp_path / "o.pdf"))
    assert res["ok"], res
    assert (tmp_path / "o.pdf").exists() and (tmp_path / "o.manifest.json").exists()
    manifest = json.loads((tmp_path / "o.manifest.json").read_text())
    assert manifest["fields"]["family_name"]["source"].endswith("(passport MRZ)")   # provenance per field
    assert manifest["fields"]["a_number"]["source"] == "entered by you"


@pytest.mark.skipif(not extract.ocr_available(), reason="tesseract not installed")
def test_ocr_reads_a_synthetic_passport_image(tmp_path):
    font_path = "/System/Library/Fonts/Menlo.ttc"
    if not Path(font_path).exists():
        pytest.skip("Menlo font not available")
    img = Image.new("RGB", (1400, 900), "white")
    d = ImageDraw.Draw(img)
    d.text((60, 60), "PASSPORT SPECIMEN", fill="black", font=ImageFont.truetype(font_path, 28))
    f = ImageFont.truetype(font_path, 36)
    d.text((40, 700), L1, fill="black", font=f)
    d.text((40, 760), L2, fill="black", font=f)
    p = tmp_path / "passport.png"
    img.save(p)
    ex = extract.extract_file(p, today=TODAY)
    assert ex.kind == "passport" and ex.mrz.valid and ex.mrz.surname == "ERIKSSON"
