"""The state behind the review screen: uploaded files, what was read from them, and what the
preparer typed. Pure Python, no GUI, so every rule here is testable.

Rules:
- The passport is the source of truth. Rank is passport, then visa, then I-94. When a lower-ranked
  document disagrees with the winning value the field is marked "mismatch": the passport's value
  is kept and the other document's value is shown, because a name or date that differs between
  documents is something the preparer needs to see, not something to quietly resolve.
- A value whose check digits fail is "unverified" and blocks the data sheet until replaced.
- Two documents of the same rank that disagree are a "conflict" and block until one is chosen.
- A value the preparer types over a document value is allowed, but is marked "overridden" and the
  document's value stays visible.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import date
from pathlib import Path

from . import extract, profile
from .filler import EditionError, FillError, fill_i765, write_manifest
from .forms import i765

BLOCKING = ("unverified", "conflict")


def default_blank() -> Path | None:
    p = Path(__file__).resolve().parents[2] / "forms" / "i-765.pdf"
    return p if p.exists() else None


class Session:
    def __init__(self, blank: Path | None = None, today: date | None = None):
        self.blank = Path(blank) if blank else default_blank()   # only used by the parked PDF filler
        self.today = today
        self.extractions: list[extract.Extraction] = []
        self.typed: dict[str, str] = {}          # values entered by the preparer

    # ---- inputs -------------------------------------------------------------------------
    def add_files(self, paths: list[str]) -> dict:
        for p in paths:
            sha = extract.sha256_file(Path(p))
            if any(e.sha256 == sha for e in self.extractions):
                continue
            self.extractions.append(extract.extract_file(Path(p), today=self.today))
        return self.state()

    def add_mrz_text(self, line1: str, line2: str) -> dict:
        """Typed machine-readable lines: a passport (44/44, starts with P) or a visa (starts with V)."""
        doc = "visa" if line1.strip().upper().startswith("V") else "passport"
        name = "typed lines"
        sha = extract.hashlib.sha256((line1 + "\n" + line2).encode()).hexdigest()
        self.extractions = [e for e in self.extractions if e.sha256 != sha]
        self.extractions.append(
            extract.extraction_from_lines(name, sha, line1, line2, today=self.today, doc=doc))
        return self.state()

    def remove(self, sha256: str) -> dict:
        self.extractions = [e for e in self.extractions if e.sha256 != sha256]
        return self.state()

    def set_value(self, key: str, value: str) -> dict:
        value = (value or "").strip()
        if not value:
            self.typed.pop(key, None)
        else:
            problem = profile.validate(key, value)
            if problem:
                return {**self.state(), "error": problem}
            self.typed[key] = value
        return self.state()

    # ---- resolution ---------------------------------------------------------------------
    def _facts(self, key: str) -> list[extract.Fact]:
        return [f for e in self.extractions for f in e.facts if f.key == key]

    def resolve(self) -> list[dict]:
        rows = []
        for f in profile.FIELDS:
            facts = self._facts(f.key)
            typed = self.typed.get(f.key)
            row = {"key": f.key, "label": f.label, "group": f.group, "value": "", "display": "",
                   "source": "", "status": "empty", "detail": "",
                   "choices": list(f.choices) if f.kind == "choice" else None,
                   "hint": "YYYY-MM-DD" if f.kind.startswith("date") else "",
                   "raw": "", "fmt": "",       # dates: as the document prints it, and in what format
                   "can_read": bool(f.docs)}
            best, others = [], []
            if facts:
                top = min(profile.DOC_RANK[x.doc] for x in facts)
                best = [x for x in facts if profile.DOC_RANK[x.doc] == top]
                others = [x for x in facts if profile.DOC_RANK[x.doc] != top]
            agree = {profile.normalize(f.key, x.value) for x in best}

            if typed is not None:
                row.update(value=typed, source="entered by you", status="entered")
                if f.kind.startswith("date") and typed != "D/S":
                    row.update(raw=typed, fmt="YYYY-MM-DD, as typed")
                if best and profile.normalize(f.key, typed) not in agree:
                    row.update(status="overridden",
                               detail=f"the {profile.DOC_LABEL[best[0].doc]} says {profile.display(f.key, best[0].value)}")
            elif len(agree) > 1:
                vals = sorted({profile.display(f.key, x.value) for x in best})
                row.update(status="conflict", detail="files disagree: " + " vs ".join(vals))
            elif best:
                x = best[0]
                status = "unverified" if x.verified is False else ("from_document" if x.verified else "read")
                row.update(value=x.value, source=x.source, status=status, detail=x.note,
                           raw=x.raw, fmt=x.fmt)
                if x.verified is False:
                    row["detail"] = (x.note + "; " if x.note else "") + "type the correct value, or re-scan the page"
                diff = [o for o in others if profile.normalize(f.key, o.value) != next(iter(agree))]
                if diff and status != "unverified":
                    row["status"] = "mismatch"
                    row["detail"] = "; ".join(
                        f"the {profile.DOC_LABEL[o.doc]} says {profile.display(f.key, o.value)}" for o in diff)
            if row["value"]:
                row["display"] = profile.display(f.key, row["value"])
            rows.append(row)
        return rows

    def notices(self) -> list[str]:
        kinds = [k for e in self.extractions for k in e.kinds]
        out = []
        if extract.PASSPORT_OTHER_PAGE in kinds and "passport" not in kinds:
            out.append("Only the back or cover of a passport has been uploaded. Upload its photo page "
                       "(the one with the two lines of < characters at the bottom) to read the details.")
        return out

    def state(self) -> dict:
        rows = self.resolve()
        return {
            "notices": self.notices(),
            "files": [{"name": Path(e.path).name, "sha256": e.sha256, "kind": e.kind,
                       "recognised": bool(e.kinds), "warnings": e.warnings} for e in self.extractions],
            "fields": rows,
            "groups": list(profile.GROUPS),
            "blockers": [f"{r['label']} ({r['status']})" for r in rows if r["status"] in BLOCKING],
            "attention": [f"{r['label']}: {r['detail']}" for r in rows
                          if r["status"] in ("mismatch", "overridden")],
            "empty": [r["label"] for r in rows if r["status"] == "empty"],
            "ocr": extract.ocr_available(),
        }

    # ---- data sheet ---------------------------------------------------------------------
    def _export_rows(self):
        return [r for r in self.resolve() if r["value"]]

    def data_sheet(self, fmt: str = "txt") -> dict:
        """The retrieved data, ready to type into the USCIS online form."""
        st = self.state()
        if st["blockers"]:
            return {"ok": False, "error": "Resolve these first: " + "; ".join(st["blockers"])}
        rows = self._export_rows()
        if not rows:
            return {"ok": False, "error": "Nothing has been read or entered yet."}
        when = (self.today or date.today()).isoformat()
        inputs = {Path(e.path).name: e.sha256 for e in self.extractions}
        if fmt == "json":
            body = json.dumps({
                "prepared": when,
                "inputs_sha256": inputs,
                "fields": {r["key"]: {"value": r["value"], "shown_as": r["display"], "source": r["source"],
                                      "source_text": r["raw"], "source_format": r["fmt"],
                                      "status": r["status"], "detail": r["detail"]} for r in rows},
                "needs_attention": st["attention"],
                "not_filled": st["empty"],
            }, indent=2) + "\n"
        elif fmt == "csv":
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["section", "field", "value", "source", "status"])
            for r in rows:
                w.writerow([r["group"], r["label"], r["display"], r["source"], r["status"]])
            body = buf.getvalue()
        else:
            out = [f"Applicant data sheet, prepared {when} on this computer. Not filed anywhere.",
                   "Check every value against the original document before entering it.", ""]
            if st["attention"]:
                out += ["NEEDS YOUR ATTENTION"] + [f"  - {a}" for a in st["attention"]] + [""]
            for g in profile.GROUPS:
                grp = [r for r in rows if r["group"] == g]
                if grp:
                    out.append(g.upper())
                    out += [f"  {r['label']}: {r['display']}" for r in grp]
                    out.append("")
            if st["empty"]:
                out.append("NOT FILLED IN: " + "; ".join(st["empty"]))
            out += ["", "Source files (SHA-256):"] + [f"  {n}  {h}" for n, h in inputs.items()]
            body = "\n".join(out) + "\n"
        return {"ok": True, "text": body, "format": fmt}

    # ---- parked: PDF filling -------------------------------------------------------------
    def fill(self, out_path: str) -> dict:
        """Fill the blank I-765. Parked: filing now happens on the USCIS portal."""
        st = self.state()
        if st["blockers"]:
            return {"ok": False, "error": "Resolve these before filling: " + "; ".join(st["blockers"])}
        rows = {r["key"]: r for r in self.resolve() if r["value"] and r["key"] in i765.BY_KEY}
        if not rows:
            return {"ok": False, "error": "Nothing to fill yet."}
        if not self.blank:
            return {"ok": False, "error": "No blank I-765 is set."}
        values = {k: r["value"] for k, r in rows.items()}
        try:
            report = fill_i765(self.blank, values, Path(out_path))
        except (EditionError, FillError) as exc:
            return {"ok": False, "error": str(exc)}
        inputs = {Path(e.path).name: e.sha256 for e in self.extractions}
        manifest = write_manifest(report, Path(out_path), inputs, {k: r["source"] for k, r in rows.items()})
        return {"ok": True, "output": str(out_path), "manifest": str(manifest),
                "edition": report.edition, "filled": len(values), "empty": st["empty"],
                "output_sha256": report.output_sha256}
