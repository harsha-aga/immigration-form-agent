"""Fill an approved blank I-765 and prove the result is what we meant to write.

The USCIS form is left as published: the XFA template, config and the rest of the packets are
carried over byte-for-byte (decoded). We write field values into the XFA ``datasets`` packet,
which is what makes Adobe Acrobat draw the form's own page barcode, and mirror them into the
AcroForm widgets so other viewers agree. The one thing removed is Adobe's usage-rights
signature (``/Perms /UR3``): it signs the original bytes, so any edit invalidates it and
Reader then warns that the document was modified.

After writing, the output is read back from disk and checked. If anything differs, the output
file is deleted and ``FillError`` is raised: a wrong form is worse than no form.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import BooleanObject, NameObject

from .forms import i765, xfa


class EditionError(ValueError):
    """The blank is not a form edition this tool has an approved field map for."""


class FillError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass
class FillReport:
    blank_sha256: str
    edition: str
    output_sha256: str
    values: dict[str, str]
    notes: list[str] = field(default_factory=list)


def _widget_name(annot) -> str:
    parts, node = [], annot
    while node is not None:
        if node.get("/T") is not None:
            parts.append(str(node["/T"]))
        parent = node.get("/Parent")
        node = parent.get_object() if parent is not None else None
    return ".".join(reversed(parts))


def _widgets(pdf_pages):
    for page in pdf_pages:
        for a in page.get("/Annots", []) or []:
            a = a.get_object()
            if a.get("/Subtype") == "/Widget":
                yield a


def _on_states(widget) -> set[str]:
    ap = widget.get("/AP")
    if not ap or "/N" not in ap:
        return set()
    n = ap["/N"].get_object()
    return {str(k) for k in n.keys() if str(k) != "/Off"} if hasattr(n, "keys") else set()


def fill_i765(blank: Path, values: Mapping[str, str], out: Path) -> FillReport:
    blank, out = Path(blank), Path(out)
    digest = sha256_file(blank)
    edition = i765.APPROVED_BLANKS.get(digest)
    if edition is None:
        raise EditionError(
            f"{blank.name} (sha256 {digest[:12]}…) is not an approved blank. This tool only "
            "fills blanks it has a verified field map for; a new edition needs a new map."
        )
    problems = [p for k, v in values.items() if (p := i765.validate(k, v))]
    if problems:
        raise FillError("; ".join(problems))

    src = PdfReader(blank)
    src.decrypt("")
    writer = PdfWriter(clone_from=src)
    root = writer._root_object

    xfa_values: dict[str, str] = {}
    acro_text: dict[str, str] = {}
    check_targets: dict[str, str] = {}   # acro_base -> on-state to select
    for key, value in values.items():
        spec = i765.BY_KEY[key]
        if isinstance(spec, i765.Text):
            xfa_values[spec.xfa] = spec.xfa_value(value)
            for name in spec.acro:
                acro_text[name] = spec.acro_value(value)
        else:
            on = spec.on_state(value)
            xfa_values[spec.xfa] = on
            check_targets[spec.acro_base] = on

    # AcroForm layer: text fields
    for page in writer.pages:
        writer.update_page_form_field_values(page, acro_text, auto_regenerate=False)
    # AcroForm layer: checkbox groups. The on-state is read from each widget, never assumed.
    for base, on in check_targets.items():
        found_target = False
        for w in _widgets(writer.pages):
            if not _widget_name(w).startswith(base + "["):
                continue
            if f"/{on}" in _on_states(w):
                w[NameObject("/V")] = NameObject(f"/{on}")
                w[NameObject("/AS")] = NameObject(f"/{on}")
                found_target = True
            else:
                w[NameObject("/V")] = NameObject("/Off")
                w[NameObject("/AS")] = NameObject("/Off")
        if not found_target:
            raise FillError(f"no checkbox with value {on!r} in {base}")

    xfa.write_values(writer, xfa_values)

    if "/Perms" in root:
        root["/Perms"].pop("/UR3", None)
        if not root["/Perms"]:
            del root["/Perms"]
    # set last: update_page_form_field_values(auto_regenerate=False) resets it to False
    root["/AcroForm"][NameObject("/NeedAppearances")] = BooleanObject(True)

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as fh:
        writer.write(fh)
    try:
        notes = verify_i765(blank, out, values)
    except Exception:
        out.unlink(missing_ok=True)
        raise
    return FillReport(digest, edition, sha256_file(out), dict(values), notes)


def verify_i765(blank: Path, out: Path, values: Mapping[str, str]) -> list[str]:
    """Re-read ``out`` from disk and compare against the blank and the intended values."""
    a = PdfReader(blank)
    a.decrypt("")
    b = PdfReader(out)
    if b.is_encrypted:
        raise FillError("output is unexpectedly encrypted")
    broot = b.trailer["/Root"]

    # 1. Everything in the XFA layer except the data packet is unchanged.
    pa, pb = xfa.xfa_packets(a.trailer["/Root"]), xfa.xfa_packets(broot)
    if set(pa) != set(pb):
        raise FillError("XFA packet list changed")
    for name in pa:
        if name != "datasets" and pa[name] != pb[name]:
            raise FillError(f"XFA packet {name!r} was modified")
    if b"<barcode" not in pb["template"]:
        raise FillError("page barcode definition missing from template")

    # 2. XFA data holds exactly what was meant.
    got = xfa.read_values(broot)
    for key, value in values.items():
        spec = i765.BY_KEY[key]
        want = spec.xfa_value(value) if isinstance(spec, i765.Text) else spec.on_state(value)
        if got.get(spec.xfa) != want:
            raise FillError(f"XFA {spec.xfa}: wrote {want!r}, read back {got.get(spec.xfa)!r}")
    extra = set(got) - {i765.BY_KEY[k].xfa for k in values}
    if extra:
        raise FillError(f"unexpected values in XFA data: {sorted(extra)}")

    # 3. AcroForm layer agrees.
    fields = b.get_fields() or {}
    for key, value in values.items():
        spec = i765.BY_KEY[key]
        if isinstance(spec, i765.Text):
            for name in spec.acro:
                v = fields.get(name, {}).get("/V")
                if v != spec.acro_value(value):
                    raise FillError(f"AcroForm {name}: expected {spec.acro_value(value)!r}, got {v!r}")
        else:
            on = f"/{spec.on_state(value)}"
            vs = {n: f.get("/V") for n, f in fields.items() if n.startswith(spec.acro_base + "[")}
            if list(vs.values()).count(on) != 1 or any(v not in (on, "/Off", None) for v in vs.values()):
                raise FillError(f"checkbox group {spec.key}: expected exactly one {on}, got {vs}")

    # 4. The things that make Acrobat complain are gone; the things that must stay are present.
    notes = []
    if "/UR3" in (broot.get("/Perms") or {}):
        raise FillError("usage-rights signature still present")
    na = broot["/AcroForm"].get("/NeedAppearances")
    if getattr(na, "value", na) is not True:
        raise FillError("NeedAppearances is not True")
    notes.append("usage-rights signature removed (the edit would have invalidated it)")
    return notes


def write_manifest(report: FillReport, out: Path, inputs: Mapping[str, str], sources: Mapping[str, str]) -> Path:
    """A small record next to the output: what blank, what inputs, what went into each field."""
    path = Path(out).with_suffix(".manifest.json")
    path.write_text(json.dumps({
        "form": report.edition,
        "blank_sha256": report.blank_sha256,
        "output_sha256": report.output_sha256,
        "input_files_sha256": dict(inputs),
        "fields": {k: {"value": v, "source": sources.get(k, "")} for k, v in report.values.items()},
        "notes": report.notes,
    }, indent=2) + "\n")
    return path
