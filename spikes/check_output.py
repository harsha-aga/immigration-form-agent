"""Fail loudly on the known ways a filled USCIS PDF trips Acrobat. Usage: check_output.py file.pdf"""
import sys
from pypdf import PdfReader

r = PdfReader(sys.argv[1])
if r.is_encrypted:
    r.decrypt("")
root = r.trailer["/Root"]
acro = root["/AcroForm"]
problems = []
if "/UR3" in (root.get("/Perms") or {}):
    problems.append("usage-rights signature /UR3 still present (Reader will warn: extended features lost)")
if "/XFA" in acro:
    problems.append("/XFA still present alongside edited AcroForm values")
_na = acro.get("/NeedAppearances")
# pypdf wraps booleans in BooleanObject; bool(obj) is always True, so read .value.
if getattr(_na, "value", _na) is not True:
    problems.append(f"NeedAppearances is {acro.get('/NeedAppearances')!r}, expected True")
js = (root.get("/Names") or {}).get("/JavaScript")
if js:
    for n in js.get_object().get("/Names", [])[::2]:
        if str(n).startswith("!ADBE::"):
            problems.append(f"leftover XFA version-check script {n}")
for p in problems:
    print("FAIL:", p)
print("OK" if not problems else f"{len(problems)} problem(s)")
sys.exit(1 if problems else 0)
