"""Reading real specimen passport pages that have been made awkward the way real scans are.

Each case is a public-domain specimen (see fixtures/specimens/SOURCES.md) turned into a letter-size
scan, rotated, skewed, or wrapped in a PDF with a junk text layer. The test compares every value
with the truth, not just the check digits, because names carry no check digit.
"""

from datetime import date
from pathlib import Path

import pytest

import scans
from uscis_autofill import extract

pytestmark = pytest.mark.skipif(not extract.ocr_available(), reason="tesseract not installed")
TODAY = date(2026, 11, 11)
NOR, ROC = "norwegian-specimen", "roc-data-page"


def read(path):
    return extract.extract_file(Path(path), today=TODAY)


def values(ex):
    return {f.key: f.value for f in ex.facts}


def assert_correct(ex, stem, *, allow_flagged=False):
    """Check digits passed AND every value equals the truth AND nothing was marked untrustworthy."""
    assert ex.kind == "passport", ex.warnings
    assert ex.mrz.valid, ex.warnings
    truth = scans.TRUTH[stem]
    got = values(ex)
    wrong = {k: (got.get(k), v) for k, v in truth.items() if got.get(k) != v}
    flagged = {f.key for f in ex.facts if f.verified is False}
    # A wrong value must at least be flagged; a correct one should not be (unless allowed).
    assert not {k for k in wrong if k not in flagged}, f"silently wrong: {wrong}"
    if not allow_flagged:
        assert not wrong and not flagged, (wrong, flagged, ex.warnings)


# ---- the cases that failed before the search was added -----------------------------------

def test_clean_specimen_image(tmp_path):
    assert_correct(read(scans.save_png(scans.base(NOR), tmp_path / "a.png")), NOR)


def test_passport_small_on_a_letter_page_png(tmp_path):
    img = scans.letter_page(scans.base(NOR))
    assert_correct(read(scans.save_png(img, tmp_path / "a.png")), NOR)


def test_passport_small_on_a_letter_page_pdf(tmp_path):
    img = scans.letter_page(scans.base(NOR))
    assert_correct(read(scans.save_pdf(img, tmp_path / "a.pdf")), NOR)


def test_passport_small_in_the_middle_of_the_page(tmp_path):
    img = scans.letter_page(scans.base(NOR), 0.45, 0.30)
    assert_correct(read(scans.save_png(img, tmp_path / "a.png")), NOR)


@pytest.mark.parametrize("degrees", [90, 180, 270])
def test_rotated_scans(tmp_path, degrees):
    img = scans.rotated(scans.base(NOR), degrees)
    assert_correct(read(scans.save_png(img, tmp_path / "a.png")), NOR)


def test_slightly_skewed_scan_in_a_pdf(tmp_path):
    img = scans.rotated(scans.base(NOR), 3)
    assert_correct(read(scans.save_pdf(img, tmp_path / "a.pdf")), NOR)


def test_a_junk_text_layer_does_not_stop_the_image_being_read(tmp_path):
    """Scanner apps add invisible text. The reader used to see 'some text' and skip OCR."""
    pytest.importorskip("pymupdf")
    img = scans.letter_page(scans.base(NOR))
    ex = read(scans.save_pdf(img, tmp_path / "a.pdf", junk_text_layer=True))
    assert_correct(ex, NOR)


def test_small_low_resolution_specimen(tmp_path):
    assert_correct(read(scans.save_png(scans.base(ROC), tmp_path / "a.png")), ROC, allow_flagged=True)


# ---- never silently wrong ------------------------------------------------------------------

def test_nationality_is_never_left_with_a_digit_in_it(tmp_path):
    """OCR reads the O of NOR as 0; check digits do not cover nationality, so position decides."""
    ex = read(scans.save_png(scans.base(NOR), tmp_path / "a.png"))
    assert values(ex)["nationality_code"] == "NOR"


def test_unreadable_file_says_what_to_do_instead_of_failing(tmp_path):
    from PIL import Image

    p = tmp_path / "blank.png"
    Image.new("RGB", (800, 600), "white").save(p)
    ex = read(p)
    assert ex.kind == "unrecognized" and not ex.facts
    assert any("type the two lines" in w for w in ex.warnings)


def test_a_file_that_is_not_an_image_or_pdf_is_refused_politely(tmp_path):
    p = tmp_path / "notes.docx"
    p.write_bytes(b"not a real docx")
    ex = read(p)
    assert ex.kind == "unrecognized" and any("unsupported" in w for w in ex.warnings)


def test_a_corrupt_pdf_does_not_crash_the_reader(tmp_path):
    p = tmp_path / "broken.pdf"
    p.write_bytes(b"%PDF-1.4 this is not really a pdf")
    ex = read(p)
    assert ex.kind == "unrecognized" and ex.warnings


# ---- the pieces, without OCR ------------------------------------------------------------------

def test_trailing_padding_misread_as_K_is_rebuilt_without_touching_the_name():
    garbage = "P<TWNLIN<<MEI<HUA<K<<<<<<<<<<KKKKKKKKKKKKK<KK"          # 45 characters
    fixed = extract._rebuild_padding(garbage)
    assert len(fixed) == 44 and fixed == "P<TWNLIN<<MEI<HUA".ljust(44, "<")
    digits = "P<TWNLIN<<MEI<HUA<K<<" + "6" * 17 + "0"                    # 39 characters
    rebuilt = extract._rebuild_padding(digits)
    assert len(rebuilt) == 44 and rebuilt == "P<TWNLIN<<MEI<HUA".ljust(44, "<")


@pytest.mark.parametrize("name", ["P<UTOSMITH<<JESSE", "P<UTOSMITH<<MARK", "P<UTOSMITH<<SUN<LEE",
                                  "P<UTOSMITH<<ELSE", "P<UTOKUKKA<<KEKE", "P<UTOCLARK<<ELKE<LEE"])
def test_real_names_that_look_like_padding_garbage_are_never_touched(name):
    line = name.ljust(44, "<")
    assert extract._rebuild_padding(line) == line
    assert extract._rebuild_padding(line[:42]) == line[:42]            # short lines are not "fixed" either


def test_type_constrained_always_fixes_letter_positions_but_digits_only_on_request():
    l1 = "P<N0RHANSEN<<OLA<<<<<<<<<<<<<<<<<<<<<<<<<<<<"            # 0 where a country letter belongs
    l2 = "CCC0O2251" + "4" + "N0R" + "560423O" + "M" + "3004157" + "<" * 14 + "04"   # O in a date, O in the number
    only_letters = extract.type_constrained(l1, l2, "passport", digits=False)
    assert only_letters[0][2:5] == "NOR" and only_letters[1][10:13] == "NOR"
    assert only_letters[1][:9] == "CCC0O2251"                       # document number untouched
    assert only_letters[1][13:20] == "560423O"                      # date untouched until a check fails
    both = extract.type_constrained(l1, l2, "passport", digits=True)
    assert both[1][13:20] == "5604230" and both[1][:9] == "CCC0O2251"


def test_name_check_uses_transliteration_exactly_but_not_for_plain_names():
    from uscis_autofill.mrz import parse_td3

    l1 = "P<NOROESTENBYEN<<AASAMUND<SPECIMEN".ljust(44, "<")
    l2 = "CCC0022514NOR5604230M3004157" + "<" * 14 + "04"
    mrz = parse_td3(l1, l2, today=TODAY)
    page = "NORGE PASSPORT Etternavn ØSTENBYEN Fornavn ÅSAMUND SPECIMEN Nasjonalitet NORSK NORWEGIAN " * 2
    assert extract.names_not_on_page(mrz, page) == []                # Ø -> OE, Å -> AA
    wrong = parse_td3("P<NOROESTENBYEN<<AASAMUND<KSPECIMEN".ljust(44, "<"), l2, today=TODAY)
    missing = extract.names_not_on_page(wrong, page)
    assert missing == [("KSPECIMEN", "SPECIMEN")]                   # exact match required, hint given


def test_a_page_too_thin_to_read_is_not_treated_as_evidence():
    from uscis_autofill.mrz import parse_td3

    mrz = parse_td3("P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<", "L898902C36UTO7408122F1204159ZE184226B<<<<<10",
                    today=TODAY)
    assert extract.names_not_on_page(mrz, "xx yy") is None


@pytest.mark.parametrize("name_line, bad", [
    ("P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<", False),
    ("P<TWNLIN<<MEI<HUA<K<<GGGGGGGG<<<<<<<<<<<<<<<", True),          # repeated letters
    ("P<TWNLIN<<MEI<K<HUA<<<<<<<<<<<<<<<<<<<<<<<<<<", True),          # lone K
    ("P<TWNLINC<MEL<HUAR<K<<<<<<<<<<<<<<<<<<<<<<<<", True),
])
def test_implausible_names_are_recognised(name_line, bad):
    from uscis_autofill.mrz import parse_td3

    l2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"
    mrz = parse_td3(name_line.ljust(44, "<")[:44], l2, today=TODAY)
    assert bool(extract._implausible_name(mrz, "<<" in name_line[5:])) is bad


# ---- Apple Vision reader: the '<' filler it drops is put back, and only if the check digits agree --

def test_dropped_filler_is_rebuilt_only_when_every_check_digit_passes():
    from uscis_autofill import vision

    two_lines = "P<TWNLIN<<MEI<HUA<<<<<<<<<<<<<<<<<<<<<<<<<<\n8888003717TWN8801018F2712251A234567893<<<<10"
    # Vision's habit: line 1 short, a few fillers of line 2 gone
    damaged = "P<TWNLIN<<MEI<HUA<<<<<<<<<<<<<<<<<<<<<<<<\n8888003717TWN8801018F2712251A234567893<<<10"
    fixed = vision.repair_td3(damaged).splitlines()
    assert fixed[0] == "P<TWNLIN<<MEI<HUA".ljust(44, "<")
    assert fixed[1] == "8888003717TWN8801018F2712251A234567893<<<<10"
    assert vision.repair_td3(two_lines).splitlines()[1] == fixed[1]


def test_a_second_line_arriving_in_pieces_is_joined():
    from uscis_autofill import vision

    text = ("P<NOROESTENBYEN<<AASAMUND<SPECIMEN<<<<<<<<<<\n"
            "CCC0022514NOR5604230M3004157<<<\n<04")
    out = vision.repair_td3(text).splitlines()
    assert len(out[0]) == 44 and out[1] == "CCC0022514NOR5604230M3004157" + "<" * 14 + "04"


def test_repair_never_invents_a_line_that_fails_its_check_digits():
    from uscis_autofill import vision

    wrong_digit = "P<TWNLIN<<MEI<HUA<<<<<<<<<<<<<<<<<<<<<<<<\n8888003717TWN8801019F2712251A234567893<<<10"
    assert vision.repair_td3(wrong_digit) == wrong_digit          # returned untouched


@pytest.mark.skipif(not __import__("uscis_autofill.vision", fromlist=["x"]).available(),
                    reason="Apple Vision not available")
def test_vision_reads_a_clean_specimen_in_well_under_the_tesseract_time(tmp_path):
    import time

    img = scans.letter_page(scans.base(NOR))
    p = scans.save_png(img, tmp_path / "a.png")
    t = time.time()
    assert_correct(read(p), NOR)
    assert time.time() - t < 8


# ---- front and back of a passport uploaded separately -----------------------------------------------

def _text_page(tmp_path, name, lines, size=(1100, 800)):
    from pathlib import Path as _P

    from PIL import Image, ImageDraw, ImageFont

    font_path = "/System/Library/Fonts/Helvetica.ttc"
    if not _P(font_path).exists():
        pytest.skip("Helvetica font not available")
    img = Image.new("RGB", size, "white")
    d, f = ImageDraw.Draw(img), ImageFont.truetype(font_path, 34)
    for i, line in enumerate(lines):
        d.text((50, 50 + i * 70), line, fill="black", font=f)
    p = tmp_path / name
    img.save(p)
    return p


BACK_PAGE = ["Address: 12 MAIN ROAD, EXAMPLE CITY", "Name of Father / Legal Guardian: JOHN SPECIMEN",
             "Name of Mother: JANE SPECIMEN", "Old Passport No.: X1234567", "File No.: ABC123456"]
COVER = ["REPUBLIC OF EXAMPLE", "PASSPORT"]


@pytest.mark.parametrize("lines", [BACK_PAGE, COVER])
def test_the_back_or_cover_of_a_passport_is_recognised_not_reported_as_unreadable(tmp_path, lines):
    ex = read(_text_page(tmp_path, "back.png", lines))
    assert ex.kind == extract.PASSPORT_OTHER_PAGE and not ex.facts
    assert any("back or cover" in w for w in ex.warnings)


def test_front_and_back_uploaded_separately_work_together(tmp_path):
    from uscis_autofill.session import Session

    s = Session(None, today=TODAY)
    front = scans.save_png(scans.base(NOR), tmp_path / "front.png")
    back = _text_page(tmp_path, "back.png", BACK_PAGE)
    st = s.add_files([str(back), str(front)])             # back first: order must not matter
    kinds = {f["name"]: f["kind"] for f in st["files"]}
    assert kinds == {"front.png": "passport", "back.png": "passport-page"}
    assert st["notices"] == [] and st["blockers"] == []
    rows = {r["key"]: r for r in st["fields"]}
    assert rows["passport_number"]["value"] == "CCC002251"
    assert rows["passport_number"]["status"] == "from_document"


def test_the_back_alone_says_the_photo_page_is_still_needed(tmp_path):
    from uscis_autofill.session import Session

    st = Session(None, today=TODAY).add_files([str(_text_page(tmp_path, "back.png", BACK_PAGE))])
    assert any("photo page" in n for n in st["notices"])
    assert not any(r["value"] for r in st["fields"])


def test_an_unrelated_page_is_still_not_mistaken_for_a_passport(tmp_path):
    ex = read(_text_page(tmp_path, "bill.png", ["Electric bill", "Account 1234", "Amount due 52.10 USD"]))
    assert ex.kind == "unrecognized"


def test_passport_page_kind_from_text():
    assert extract.passport_page_kind("Name of Father  JOHN\nName of Mother  JANE\nAddress 1 Road") == "other"
    assert extract.passport_page_kind("Surname SMITH Given names ANN Nationality UTO Date of birth 01 JAN 1980 PASSPORT") == "data"
    assert extract.passport_page_kind("Electric bill account 1234 amount due " * 8) is None
