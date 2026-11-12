"""Read and write the XFA ``datasets`` packet of a hybrid USCIS PDF.

The XFA ``template`` (layout, rules, the page barcode) and ``config`` are never modified. Only
the ``datasets`` packet, which holds field values, is rewritten, and only existing empty
elements are filled. A path that is not in the packet is an error, not something to create:
it means the form edition is not the one this map was written for.

Paths are relative to ``form1``: ``"Line1a_FamilyName"`` for a globally bound field and
``"Page2/Pt2Line5_State"`` for a page-local one.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Mapping

from pypdf.generic import ArrayObject, DecodedStreamObject

XFA_DATA_NS = "http://www.xfa.org/schema/xfa-data/1.0/"
ET.register_namespace("xfa", XFA_DATA_NS)


class XfaError(ValueError):
    pass


def _xfa_array(root) -> ArrayObject:
    acro = root.get("/AcroForm")
    if acro is None or "/XFA" not in acro:
        raise XfaError("this PDF has no XFA layer")
    return acro["/XFA"].get_object()


def xfa_packets(root) -> dict[str, bytes]:
    """Decoded bytes of every named XFA packet (template, config, datasets, ...)."""
    arr = _xfa_array(root)
    out = {}
    for i in range(0, len(arr) - 1, 2):
        obj = arr[i + 1].get_object()
        if hasattr(obj, "get_data"):
            out[str(arr[i])] = obj.get_data()
    return out


def _form_node(data_xml: bytes) -> tuple[ET.Element, ET.Element]:
    tree = ET.fromstring(data_xml)
    node = tree.find(f"{{{XFA_DATA_NS}}}data/form1")
    if node is None:
        raise XfaError("datasets packet has no xfa:data/form1 element")
    return tree, node


def read_values(root) -> dict[str, str]:
    """Every non-empty leaf in the data packet, keyed by its path under form1."""
    _, form = _form_node(xfa_packets(root)["datasets"])
    out: dict[str, str] = {}

    def walk(el: ET.Element, prefix: str) -> None:
        for child in el:
            path = f"{prefix}{child.tag}"
            if len(child):
                walk(child, path + "/")
            elif (child.text or "").strip():
                out[path] = child.text.strip()

    walk(form, "")
    return out


def write_values(writer, values: Mapping[str, str]) -> None:
    """Fill existing elements of the datasets packet; touch nothing else."""
    root = writer._root_object
    arr = _xfa_array(root)
    idx = next((i for i in range(0, len(arr) - 1, 2) if str(arr[i]) == "datasets"), None)
    if idx is None:
        raise XfaError("XFA array has no datasets packet")
    tree, form = _form_node(arr[idx + 1].get_object().get_data())
    for path, value in values.items():
        node = form
        for part in path.split("/"):
            nxt = node.find(part)
            if nxt is None:
                raise XfaError(f"datasets has no element {path!r} (different form edition?)")
            node = nxt
        if len(node):
            raise XfaError(f"{path!r} is a group, not a field")
        node.text = value
    stream = DecodedStreamObject()
    stream.set_data(ET.tostring(tree, encoding="utf-8", xml_declaration=False))
    ref = writer._add_object(stream)
    arr[idx + 1] = ref
