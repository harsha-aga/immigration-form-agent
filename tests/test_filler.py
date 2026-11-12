from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from uscis_autofill.filler import EditionError, FillError, fill_i765, verify_i765
from uscis_autofill.forms import i765, xfa

BLANK = Path(__file__).resolve().parents[1] / "forms" / "i-765.pdf"
pytestmark = pytest.mark.skipif(not BLANK.exists(), reason="blank I-765 not present")

VALUES = {
    "family_name": "ERIKSSON", "given_name": "ANNA", "middle_name": "MARIA", "sex": "F",
    "birth_date": "1974-08-12", "passport_number": "L898902C3", "passport_expiry": "2012-04-15",
    "a_number": "123456789", "marital_status": "Single", "reason": "1",
    "street": "100 TEST STREET", "city": "SPRINGFIELD", "state": "IL", "zip": "62701",
}


@pytest.fixture(scope="module")
def filled(tmp_path_factory):
    out = tmp_path_factory.mktemp("o") / "out.pdf"
    return out, fill_i765(BLANK, VALUES, out)


def test_every_spec_field_is_fillable_and_read_back(filled):
    out, report = filled
    assert report.edition.startswith("I-765")
    assert set(VALUES) == {s.key for s in i765.SPEC}


def test_xfa_layer_is_kept_and_only_the_data_packet_differs(filled):
    out, _ = filled
    a = PdfReader(BLANK)
    a.decrypt("")
    pa, pb = xfa.xfa_packets(a.trailer["/Root"]), xfa.xfa_packets(PdfReader(out).trailer["/Root"])
    assert set(pa) == set(pb)
    assert [n for n in pa if pa[n] != pb[n]] == ["datasets"]
    assert b'<barcode type="pdf417"' in pb["template"]


def test_both_layers_hold_the_values(filled):
    out, _ = filled
    r = PdfReader(out)
    data = xfa.read_values(r.trailer["/Root"])
    assert data["Line1a_FamilyName"] == "ERIKSSON"
    assert data["Line9_Checkbox"] == "N" and data["Line10_Checkbox"] == "Single"
    assert data["Page3/Line19_DOB"] == "1974-08-12"          # XFA stores ISO dates
    f = r.get_fields()
    assert f["form1[0].Page3[0].Line19_DOB[0]"]["/V"] == "08/12/1974"   # the page shows US dates
    assert f["form1[0].Page7[0].Line1a_FamilyName[0]"]["/V"] == "ERIKSSON"
    assert f["form1[0].Page2[0].Line9_Checkbox[0]"]["/V"] == "/N"
    assert f["form1[0].Page2[0].Line9_Checkbox[1]"]["/V"] == "/Off"


def test_usage_rights_signature_removed_but_xfa_scripts_kept(filled):
    out, _ = filled
    root = PdfReader(out).trailer["/Root"]
    assert "/UR3" not in (root.get("/Perms") or {})
    assert "/XFA" in root["/AcroForm"]
    assert "/JavaScript" in root["/Names"]


def test_a_blank_with_a_different_hash_is_refused(tmp_path):
    other = tmp_path / "other.pdf"
    w = PdfWriter()
    w.add_blank_page(612, 792)
    w.write(other)
    with pytest.raises(EditionError):
        fill_i765(other, VALUES, tmp_path / "x.pdf")
    assert not (tmp_path / "x.pdf").exists()


@pytest.mark.parametrize("key, bad", [
    ("a_number", "12AB"), ("zip", "6270"), ("state", "Illinois"), ("sex", "X"),
    ("birth_date", "1974-13-40"), ("marital_status", "Complicated"), ("nonsense", "1"),
])
def test_invalid_values_are_refused_before_anything_is_written(tmp_path, key, bad):
    with pytest.raises(FillError):
        fill_i765(BLANK, {key: bad}, tmp_path / "x.pdf")
    assert not (tmp_path / "x.pdf").exists()


def test_verification_catches_a_value_that_does_not_match(filled):
    out, _ = filled
    with pytest.raises(FillError):
        verify_i765(BLANK, out, {**VALUES, "family_name": "SOMEONE ELSE"})


def test_partial_fill_leaves_other_fields_empty(tmp_path):
    out = tmp_path / "p.pdf"
    fill_i765(BLANK, {"family_name": "ERIKSSON"}, out)
    assert xfa.read_values(PdfReader(out).trailer["/Root"]) == {"Line1a_FamilyName": "ERIKSSON"}
