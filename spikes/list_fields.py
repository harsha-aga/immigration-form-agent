"""List fillable fields of a blank form with page, type, tooltip. Read-only."""
import sys
from pypdf import PdfReader
r = PdfReader(sys.argv[1]); r.decrypt("")
want = int(sys.argv[2]) if len(sys.argv) > 2 else 0
for pno, page in enumerate(r.pages, start=1):
    if want and pno != want: continue
    for a in page.get("/Annots", []) or []:
        a = a.get_object()
        if a.get("/Subtype") != "/Widget": continue
        name = a.get("/T"); parent = a.get("/Parent")
        full = []
        node = a
        while node is not None:
            t = node.get("/T")
            if t is not None: full.append(str(t))
            node = node.get("/Parent"); node = node.get_object() if node is not None else None
        ft = a.get("/FT") or (a["/Parent"].get_object().get("/FT") if "/Parent" in a else None)
        print(pno, ft, ".".join(reversed(full)), "|", str(a.get("/TU"))[:70])
