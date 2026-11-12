import sys
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject
src, out = sys.argv[1], sys.argv[2]
r = PdfReader(src); r.decrypt("")
w = PdfWriter(clone_from=r)
acro = w._root_object["/AcroForm"]
acro.pop("/XFA", None)
acro[NameObject("/NeedAppearances")] = BooleanObject(True)
P1, P2 = "form1[0].Page1[0].", "form1[0].Page2[0]."
vals = {
  P1+"Line1a_FamilyName[0]": "ERIKSSON", P1+"Line1b_GivenName[0]": "ANNA", P1+"Line1c_MiddleName[0]": "MARIA",
  P1+"Part1_Checkbox[0]": "/1",
  P2+"Line7_AlienNumber[0]": "123456789",
  P2+"Line9_Checkbox[0]": "/N", P2+"Line10_Checkbox[2]": "/Single",
  P2+"Pt2Line5_CityOrTown[0]": "SPRINGFIELD",
  P2+"Pt2Line5_State[0]": "IL",
  P2+"Pt2Line5_ZipCode[0]": "62701",
  P2+"Line4b_StreetNumberName[0]": "100 TEST STREET",
}
for i, page in enumerate(w.pages[:2]):
    w.update_page_form_field_values(page, {k: v for k, v in vals.items() if k.startswith(f"form1[0].Page{i+1}[0].")}, auto_regenerate=False)
w.write(out)
r2 = PdfReader(out); f = r2.get_fields()
for k in vals: print(k.split("[0].")[-1].replace("[0]",""), "=", f[k].get("/V"))
