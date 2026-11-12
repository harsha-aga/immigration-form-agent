"""Inspect a blank USCIS PDF: form type (AcroForm / XFA), fields, edition text. Read-only."""
import re
import sys
from collections import Counter

from pypdf import PdfReader

path = sys.argv[1]
r = PdfReader(path)
if r.is_encrypted:
    print("decrypt with empty user password ->", r.decrypt(""))
    enc = r.trailer["/Encrypt"]
    print("encryption: V", enc.get("/V"), "R", enc.get("/R"), "P(permission bits)", enc.get("/P"))
    try:
        print("permissions:", r.user_access_permissions)
    except Exception as e:
        print("permissions: unavailable", e)
print("file:", path)
print("pages:", len(r.pages), "| encrypted:", r.is_encrypted)
root = r.trailer["/Root"]
af = root.get("/AcroForm")
print("has AcroForm:", af is not None)
if af is not None:
    af = af.get_object()
    xfa = af.get("/XFA")
    print("has XFA:", xfa is not None)
    print("NeedAppearances:", af.get("/NeedAppearances"))
    print("SigFlags:", af.get("/SigFlags"))
    print("form-level JavaScript (/AA):", "/AA" in af)
print("document-level JS names:", "/Names" in root and "/JavaScript" in root["/Names"].get_object())
fields = r.get_fields() or {}
print("field count:", len(fields))
types = Counter(str(v.get("/FT")) for v in fields.values())
print("field types:", dict(types))
# edition text on page 1 footer and later pages
for i in (0, len(r.pages) - 1):
    t = r.pages[i].extract_text() or ""
    for m in re.finditer(r"Form\s+I-\d+[^\n]{0,60}(?:Edition|Ed\.)[^\n]{0,40}", t):
        print(f"page {i+1} edition text:", m.group(0).strip())
    for m in re.finditer(r"(?:Edition|Ed\.)\s*\d{1,2}/\d{1,2}/\d{2}", t):
        print(f"page {i+1} edition date:", m.group(0))
print("sample field names:")
for name in list(fields)[:8]:
    print("  ", name, "|", fields[name].get("/FT"), "|", str(fields[name].get("/TU"))[:60])
