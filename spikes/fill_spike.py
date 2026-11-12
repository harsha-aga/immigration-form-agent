"""Fill spike: synthetic data into the I-765 AcroForm layer, drop XFA, verify, render."""
import sys
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject

src, out = sys.argv[1], sys.argv[2]
r = PdfReader(src); r.decrypt("")
w = PdfWriter(clone_from=r)

acro = w._root_object["/AcroForm"]
had_xfa = "/XFA" in acro
if had_xfa:
    del acro["/XFA"]                      # make AcroForm authoritative
acro[NameObject("/NeedAppearances")] = BooleanObject(True)

values = {
    "form1[0].Page1[0].Line1a_FamilyName[0]": "ERIKSSON",
    "form1[0].Page1[0].Line1b_GivenName[0]": "ANNA",
    "form1[0].Page1[0].Line1c_MiddleName[0]": "MARIA",
}
page1 = w.pages[0]
w.update_page_form_field_values(page1, values, auto_regenerate=False)
w.write(out)
print("xfa removed:", had_xfa, "->", out)

# verify by re-reading
r2 = PdfReader(out)
got = {k: v.get("/V") for k, v in (r2.get_fields() or {}).items() if k in values}
for k in values: print("readback", k.split(".")[-1], "=", got.get(k))
