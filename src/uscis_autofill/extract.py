"""Read uploaded files and pull out facts. Everything runs on this machine.

Text comes from the file itself when it has any, otherwise from local Tesseract OCR; nothing is
sent over a network. Documents understood so far:

- passport and visa: through the machine-readable zone (MRZ)
- I-94 record (the printout from i94.cbp.dhs.gov): through its printed labels

A misread line is never repaired. What a check digit does and does not protect:
the MRZ check digits cover only the document number, date of birth and expiry date (and a
composite of those). Names, sex, nationality and the issuing country carry NO check digit, so an
OCR error there is invisible to the machine and those values are marked as unchecked.

Finding the MRZ in a scan is a search, because scans come rotated, skewed, small on the page, or
wrapped in a PDF that already carries an unrelated text layer: orientation, de-skew and
page regions are tried in order of cost until a pair of lines parses.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from . import vision
from .mrz import MrzError, PassportMrz, parse_mrv, parse_td3

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
MAX_PAGES = 5
MAX_OCR_RUNS_PER_PAGE = 40
_FILLER = str.maketrans({"«": "<", "‹": "<", "〈": "<", "＜": "<"})
_MRZ_CHARS = re.compile(r"[A-Z0-9<]+")

# Fields the MRZ check digits actually cover, by document.
_CHECKSUMMED = {"passport": {"birth_date", "passport_number", "passport_expiry"},
                "visa": {"birth_date", "visa_number", "visa_expiry"}}
_NO_CHECK_NOTE = "not covered by a check digit; compare with the printed page"


@dataclass(frozen=True)
class Fact:
    key: str                 # field key, see profile.FIELDS
    value: str
    source: str              # e.g. "passport.jpg (passport MRZ)"
    verified: bool | None    # True/False = a checksum passed/failed; None = no checksum covers it
    note: str = ""
    doc: str = ""            # "passport" | "visa" | "i94"
    raw: str = ""            # dates only: the text exactly as the document prints it
    fmt: str = ""            # dates only: the format that text is in, e.g. "YYMMDD"


@dataclass
class Extraction:
    path: str
    sha256: str
    kinds: list[str] = field(default_factory=list)
    facts: list[Fact] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    mrz: PassportMrz | None = None

    @property
    def kind(self) -> str:
        return "+".join(self.kinds) if self.kinds else "unrecognized"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ocr_available() -> bool:
    return vision.available() or shutil.which("tesseract") is not None


def _vision_mrz_text(gray, today=None) -> str:
    return vision.repair_td3(vision.read_text(gray), today)


# ---- images and OCR ---------------------------------------------------------------------

def _tesseract(image_path: Path, *, mrz: bool, psm: int = 6) -> str:
    cmd = ["tesseract", str(image_path), "stdout", "--psm", str(psm), "--dpi", "300"]
    if mrz:
        cmd += ["-c", "tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout


def _ocr_raw(gray, *, mrz: bool) -> str:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "page.png"
        gray.save(p)
        return _tesseract(p, mrz=mrz)


def _ocr(gray, *, mrz: bool) -> str:
    """OCR a grayscale image, enlarging small ones: Tesseract wants roughly 30 px letters."""
    if gray.width < 1800:
        from PIL import Image

        gray = gray.resize((1800, max(1, int(gray.height * 1800 / gray.width))),
                           Image.BICUBIC if mrz else Image.LANCZOS)
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "page.png"
        gray.save(p)
        return _tesseract(p, mrz=mrz)


def _visual_texts(gray) -> Iterator[str]:
    """The printed page as text, one OCR pass at a time. Small-print OCR accuracy swings with scale
    and resampling (one setting finds a word another misses), so several settings are offered and
    the caller stops as soon as what it is looking for has been found."""
    from PIL import Image

    if vision.available():
        yield vision.read_text(gray)
    if shutil.which("tesseract") is None:
        return
    yield _ocr_raw(gray, mrz=False)                                         # native size
    if gray.width < 1800:
        scaled = 1800 / gray.width
        for resample in (Image.BICUBIC, Image.LANCZOS):
            yield _ocr_raw(gray.resize((1800, int(gray.height * scaled)), resample), mrz=False)
    if gray.width * 2 <= 3600:
        yield _ocr_raw(gray.resize((gray.width * 2, gray.height * 2), Image.LANCZOS), mrz=False)


def _gray(img):
    from PIL import ImageOps

    return ImageOps.autocontrast(ImageOps.grayscale(img))


def _autocrop(gray):
    """Cut the white margin around a small document on a big page, so its text is larger."""
    mask = gray.point(lambda v: 255 if v < 225 else 0)
    box = mask.getbbox()
    if not box:
        return gray
    w, h = gray.size
    pad = int(0.02 * max(w, h))
    box = (max(0, box[0] - pad), max(0, box[1] - pad), min(w, box[2] + pad), min(h, box[3] + pad))
    if (box[2] - box[0]) * (box[3] - box[1]) > 0.95 * w * h or box[2] - box[0] < 200:
        return gray
    return gray.crop(box)


def _rot(gray, degrees: float):
    """Rotate counter-clockwise, smoothly: nearest-neighbour resampling roughens letter edges
    enough to cause OCR errors."""
    from PIL import Image

    return gray.rotate(degrees, resample=Image.BICUBIC, expand=True, fillcolor=255)


def _skew_angle(gray) -> float:
    """Estimate page skew in degrees: text lines are sharpest when the rows are level."""
    from PIL import Image, ImageOps, ImageStat

    small = gray.copy()
    small.thumbnail((600, 600))
    ink = ImageOps.invert(small.point(lambda v: 0 if v < 140 else 255))

    def sharpness(a: float) -> float:
        rows = ink.rotate(a, resample=Image.BILINEAR, fillcolor=0)
        return ImageStat.Stat(rows.resize((1, rows.height), Image.BOX)).var[0]

    coarse = max((x / 1.0 for x in range(-10, 11)), key=sharpness)
    return max((coarse + x / 4 for x in range(-4, 5)), key=sharpness)


def _osd_rotation(gray) -> int | None:
    """Tesseract's guess at the clockwise rotation needed to read the page upright."""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "page.png"
        g = gray if gray.width >= 1200 else gray.resize((1200, int(gray.height * 1200 / gray.width)))
        g.save(p)
        res = subprocess.run(["tesseract", str(p), "stdout", "--psm", "0"],
                             capture_output=True, text=True, timeout=60)
    m = re.search(r"Rotate:\s*(\d+)", res.stdout)
    return int(m.group(1)) if m else None


_MRZ_ALPHABET = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<")


def _locate_mrz(gray) -> tuple[int, int, int, int] | None:
    """Find the two long MRZ-looking lines on a page and return a tight crop box around them.

    Page-wide OCR without a character whitelist is poor at '<' but still returns the MRZ lines as
    long single tokens of capitals and digits; those are the only such tokens on a passport page.
    Cropping tightly lets the real read use the measured letter height instead of a guess.
    """
    scale = 2000 / gray.width
    g = gray.resize((2000, max(1, int(gray.height * scale))))
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "page.png"
        g.save(p)
        tsv = subprocess.run(["tesseract", str(p), "stdout", "--psm", "11", "--dpi", "300", "tsv"],
                             capture_output=True, text=True, timeout=120).stdout
    tokens = []
    for row in tsv.splitlines()[1:]:
        c = row.split("\t")
        if len(c) < 12:
            continue
        t = _norm(c[11])
        if len(t) < 25 or sum(ch in _MRZ_ALPHABET for ch in t) / len(t) < 0.9:
            continue
        left, top, w, h = (int(x) for x in c[6:10])
        tokens.append((top, left, w, h))
    if not tokens:
        return None
    tokens.sort()
    chosen = [tokens[-1]]
    if len(tokens) > 1 and tokens[-1][0] - tokens[-2][0] < 4 * tokens[-1][3]:
        chosen.append(tokens[-2])
    x0 = min(t[1] for t in chosen)
    x1 = max(t[1] + t[2] for t in chosen)
    y0 = min(t[0] for t in chosen)
    y1 = max(t[0] + t[3] for t in chosen)
    h = max(t[3] for t in chosen)
    pad_y, pad_x = int(1.3 * h), int(0.03 * 2000)
    box = (max(0, x0 - pad_x), max(0, y0 - pad_y), min(2000, x1 + pad_x), min(g.height, y1 + pad_y))
    return tuple(int(v / scale) for v in box), h / scale


def _ocr_located(gray) -> str | None:
    """OCR just the located MRZ region, enlarged so the letters are about 45 px tall."""
    hit = _locate_mrz(gray)
    if not hit:
        return None
    box, letter_h = hit
    crop = gray.crop(box)
    factor = max(0.5, min(4.0, 45 / max(letter_h, 1)))
    crop = crop.resize((max(1, int(crop.width * factor)), max(1, int(crop.height * factor))))
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "mrz.png"
        crop.save(p)
        return _tesseract(p, mrz=True)


# ---- passport pages that carry no machine-readable lines ------------------------------------------
# A passport is often photographed in parts: the photo page (with the two lines of '<' characters)
# and the back page or cover. Only the first holds data this app can verify.

PASSPORT_OTHER_PAGE = "passport-page"
_PASSPORT_WORDS = ("passport", "passeport", "pasaporte", "reisepass", "passaporto")
_BACK_CUES = ("name of father", "name of mother", "name of spouse", "legal guardian", "old passport",
              "file no", "address", "observations", "endorsement", "amendments", "emergency",
              "this passport", "the bearer", "holder")
_DATA_CUES = ("date of birth", "nationality", "surname", "given name", "date of expiry", "place of birth",
              "authority")


def passport_page_kind(text: str) -> str | None:
    """'other' for the back or cover of a passport (words of a passport, none of the data page's
    labels); 'data' when it has the data page's labels; None when it does not look like a passport."""
    low = re.sub(r"\s+", " ", text.lower())
    data = sum(c in low for c in _DATA_CUES)
    if data >= 3:
        return "data"
    words = any(w in low for w in _PASSPORT_WORDS)
    back = sum(c in low for c in _BACK_CUES)
    letters = len(re.findall(r"[a-z]", low))
    if back >= 2 or (words and back >= 1) or (words and letters < 120):
        return "other"
    return None


_WINDOWS = ((0.58, 1.0), (0.0, 1.0), (0.42, 0.72), (0.26, 0.56), (0.10, 0.40), (0.0, 0.30), (0.74, 1.0))


def mrz_text_candidates(img) -> Iterator[tuple[str, object]]:
    """Yield (OCR text, the page variant it came from) for progressively wider searches; the caller
    stops at the first success.

    Cheap first: the page as given, bottom region first. Then de-skewed, then rotated by what
    Tesseract's orientation detection says, then the other right angles.
    """
    base = _autocrop(_gray(img))
    runs = 0

    def regions(g) -> Iterator[tuple[str, object]]:
        nonlocal runs
        if runs < MAX_OCR_RUNS_PER_PAGE:
            runs += 2                       # one page-wide locate pass and one crop read
            located = _ocr_located(g)
            if located:
                yield located, g
        for top, bottom in _WINDOWS[:2]:    # fallback when the lines could not be located
            if runs >= MAX_OCR_RUNS_PER_PAGE:
                return
            runs += 1
            yield _ocr(g.crop((0, int(top * g.height), g.width, int(bottom * g.height))), mrz=True), g

    if vision.available():                  # fast and accurate, so it goes first, at every angle
        angle0 = _skew_angle(base)
        flat = _rot(base, angle0) if abs(angle0) >= 0.5 else None
        views = [base] + ([flat] if flat is not None else [])
        if base.width < 1600:               # small letters: Vision reads them better when enlarged
            from PIL import Image
            views.append(base.resize((base.width * 2, base.height * 2), Image.LANCZOS))
        texts = []
        for g in views:
            texts.append(_vision_mrz_text(g))
            yield texts[-1], g
        for rot in (90, 180, 270):
            turned = _autocrop(_rot(base, rot))
            texts.append(_vision_mrz_text(turned))
            yield texts[-1], turned
        # Vision read the page at every angle and found a passport's back or cover: no MRZ to hunt for
        kinds = {passport_page_kind(t) for t in texts}
        if "other" in kinds and "data" not in kinds:
            return
    if shutil.which("tesseract") is None:
        return
    yield from regions(base)
    angle = _skew_angle(base)
    if abs(angle) >= 0.5:
        yield from regions(_rot(base, angle))
    tried = {0}
    osd = _osd_rotation(base)
    order = ([(360 - osd) % 360] if osd else []) + [90, 180, 270]
    for rot in order:
        if rot in tried:
            continue
        tried.add(rot)
        turned = _autocrop(_rot(base, rot))
        yield from regions(turned)
        a = _skew_angle(turned)
        if abs(a) >= 0.5:
            yield from regions(_rot(turned, a))


def _page_images(path: Path) -> Iterator:
    from PIL import Image, ImageOps

    if path.suffix.lower() == ".pdf":
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(str(path))
        for i in range(min(len(pdf), MAX_PAGES)):
            w, h = pdf[i].get_size()
            scale = max(1.0, min(4.2, 3300 / max(w, h)))
            yield pdf[i].render(scale=scale).to_pil()
    else:
        im = Image.open(path)
        for i in range(min(getattr(im, "n_frames", 1), MAX_PAGES)):
            im.seek(i)
            yield ImageOps.exif_transpose(im.copy()).convert("RGB")


def _embedded_text(path: Path) -> tuple[list[str], list[str]]:
    """Text already in a PDF (a scanner app's text layer, or a real I-94 printout)."""
    if path.suffix.lower() != ".pdf":
        return [], []
    try:
        from pypdf import PdfReader

        r = PdfReader(path)
        if r.is_encrypted:
            r.decrypt("")
        return [(p.extract_text() or "") for p in r.pages[:MAX_PAGES]], []
    except Exception as exc:  # unreadable PDF: say so, then try OCR
        return [], [f"could not read the PDF's text: {exc}"]


# ---- machine-readable zones -------------------------------------------------------------

def _norm(line: str) -> str:
    return re.sub(r"\s+", "", line.translate(_FILLER).upper())


_PADDING_GARBAGE = set("K0123456789")


def _rebuild_padding(line: str) -> str:
    """Restore the '<' padding at the end of a name line that OCR misread as K or digits.

    Names never contain digits, and K is how OCR most often misreads '<', so a trailing region that
    starts at a real '<' and holds at least two K/digit characters is padding that was misread. The
    name itself is never touched: the cut is made at that first '<', so 'JESSE', 'LEE' and 'MARK'
    are safe, and ordinary '<' padding (no K or digit after it) is left exactly as read.
    Line 1 has no check digit, so this is the only safe place to do it.
    """
    if not (line[:1] in ("P", "V") and 38 <= len(line) <= 52 and "<<" in line):
        return line
    i = len(line)
    while i > 5 and (line[i - 1] == "<" or line[i - 1] in _PADDING_GARBAGE):
        i -= 1
    tail = line[i:]
    first = tail.find("<")
    if first < 0:
        return line
    pad = tail[first:]
    if sum(ch in _PADDING_GARBAGE for ch in pad) >= 2 and i + first <= 44:
        return line[: i + first].ljust(44, "<")
    return line


def _mrz_lines(text: str) -> list[str]:
    lines = [_rebuild_padding(_norm(ln)) for ln in text.splitlines()]
    return [ln for ln in lines if ln and _MRZ_CHARS.fullmatch(ln)]


# Letter/digit confusions OCR makes. The MRZ layout fixes which positions hold digits and which
# hold letters, so a wrong-type character there can be mapped back by position.
_TO_DIGIT = {"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1", "B": "8", "S": "5", "Z": "2", "G": "6"}
_TO_LETTER = {"0": "O", "1": "I", "2": "Z", "5": "S", "8": "B", "6": "G"}


def type_constrained(l1: str, l2: str, doc: str, *, digits: bool) -> tuple[str, str, int] | None:
    """Fix letter/digit confusions by position. Returns (line1, line2, characters changed) or None.

    Letters-only positions (always corrected, since a digit can never be right there): the issuing
    country and name field on line 1, nationality on line 2. Digit-only positions (corrected only
    when ``digits`` is set, i.e. after a check digit failed): the check digits, date of birth and
    expiry date. The document number and optional data are alphanumeric and never touched.
    A digit-position correction must be accepted only if every check digit then passes.
    """
    def fix(line: str, spans, table):
        chars, n = list(line), 0
        for a, b in spans:
            for i in range(a, min(b, len(chars))):
                if chars[i] in table:
                    chars[i], n = table[chars[i]], n + 1
        return "".join(chars), n

    f1, n1 = fix(l1, [(2, len(l1))], _TO_LETTER)
    f2, n2 = fix(l2, [(10, 13)], _TO_LETTER)
    n3 = 0
    if digits:
        spans = [(9, 10), (13, 20), (21, 28)] + ([(42, 44)] if doc == "passport" else [])
        f2, n3 = fix(f2, spans, _TO_DIGIT)
    total = n1 + n2 + n3
    return (f1, f2, total) if total else None


def find_mrz_lines(text: str) -> tuple[tuple[str, str] | None, str]:
    """Find two consecutive 44-character passport lines. Returns (lines, note).

    Lines are never repaired: a line of the wrong length is reported, not padded or trimmed.
    """
    lines = _mrz_lines(text)
    near = False
    for a, b in zip(lines, lines[1:]):
        if len(a) == 44 and len(b) == 44 and a.startswith("P"):
            return (a, b), ""
        if 38 <= len(a) <= 50 and 38 <= len(b) <= 50 and a.startswith("P") and "<<" in a:
            near = True
    return None, ("found text that looks like a passport MRZ but the lines are not 44 "
                  "characters; type the two lines in by hand" if near else "")


def find_mrv_lines(text: str) -> tuple[tuple[str, str] | None, str]:
    """Find a visa MRZ: two consecutive lines of 44 (MRV-A) or 36 (MRV-B) starting with V."""
    lines = _mrz_lines(text)
    near = False
    for a, b in zip(lines, lines[1:]):
        if a.startswith("V") and len(a) == len(b) and len(a) in (36, 44):
            return (a, b), ""
        if a.startswith("V") and "<<" in a and 30 <= len(a) <= 50 and 30 <= len(b) <= 50:
            near = True
    return None, ("found text that looks like a visa MRZ but the lines are not 36 or 44 "
                  "characters" if near else "")


MRZ_DATE_FORMAT = "YYMMDD"


def _century_note(raw: str, d: date) -> str:
    """An MRZ prints a two-digit year; say which century was assumed, since the page does not."""
    return f"the MRZ prints a 2-digit year ({raw[:2]}); read as {d.year}" if raw[:2].isdigit() else ""


def facts_from_mrz(mrz: PassportMrz, source: str, doc: str = "passport") -> list[Fact]:
    """Facts from an MRZ. Only fields a check digit covers can be 'verified'.

    If any check digit fails the whole reading is suspect, so every fact from it is marked failed.
    """
    covered = _CHECKSUMMED[doc]

    def fact(key, value, note="", raw="", fmt=""):
        if key in covered:
            verified = mrz.valid
            if not mrz.valid:
                note = (note + "; " if note else "") + "a check digit failed"
        else:
            verified = None if mrz.valid else False
            note = (note + "; " if note else "") + _NO_CHECK_NOTE
        return Fact(key, value, source, verified, note, doc, raw, fmt)

    given = mrz.given_names.split()
    out = [fact("family_name", mrz.surname)]
    if given:
        out.append(fact("given_name", given[0]))
    if len(given) > 1:
        out.append(fact("middle_name", " ".join(given[1:]),
                        "the document does not separate first and middle names; split on the first space"))
    out.append(fact("sex", mrz.sex))
    if mrz.birth_date:
        out.append(fact("birth_date", mrz.birth_date.isoformat(),
                        _century_note(mrz.birth_raw, mrz.birth_date), mrz.birth_raw, MRZ_DATE_FORMAT))
    if mrz.nationality:
        out.append(fact("nationality_code", mrz.nationality))
    if doc == "passport":
        if mrz.document_number:
            out.append(fact("passport_number", mrz.document_number))
        if mrz.expiry_date:
            out.append(fact("passport_expiry", mrz.expiry_date.isoformat(),
                            _century_note(mrz.expiry_raw, mrz.expiry_date), mrz.expiry_raw, MRZ_DATE_FORMAT))
        if mrz.issuing_country:
            out.append(fact("passport_country_code", mrz.issuing_country))
    else:
        if mrz.document_number:
            out.append(fact("visa_number", mrz.document_number))
        if mrz.expiry_date:
            out.append(fact("visa_expiry", mrz.expiry_date.isoformat(),
                            _century_note(mrz.expiry_raw, mrz.expiry_date), mrz.expiry_raw, MRZ_DATE_FORMAT))
    return out


def extraction_from_lines(path: str, sha: str, l1: str, l2: str, *, today: date | None = None,
                          doc: str = "passport") -> Extraction:
    ex = Extraction(path, sha)
    name, label = Path(path).name, ("passport MRZ" if doc == "passport" else "visa MRZ")
    try:
        mrz = parse_td3(l1, l2, today=today) if doc == "passport" else parse_mrv(l1, l2, today=today)
    except MrzError as exc:
        ex.warnings.append(f"not a valid {doc} MRZ: {exc}")
        return ex
    ex.kinds, ex.mrz = [doc], mrz
    ex.facts = facts_from_mrz(mrz, f"{name} ({label})", doc)
    if not mrz.valid:
        bad = ", ".join(k.replace("_", " ") for k, v in mrz.checks.items() if not v)
        ex.warnings.append(
            f"{doc}: check digits FAILED for {bad}. The reading is not trustworthy; re-scan "
            "the page or type the two MRZ lines by hand.")
    bad = _implausible_name(mrz, "<<" in l1[5:])
    if bad and doc == "passport":
        ex.warnings.append(f"passport: {bad}, so the name was probably misread; type the name.")
        _flag_names(ex, "name line looks misread")
    if mrz.name_possibly_truncated:
        ex.warnings.append(f"{doc}: the name fills the whole MRZ name field and may be cut "
                           "short; compare it with the printed name")
    if mrz.sex == "X":
        ex.warnings.append(f"{doc}: sex is unspecified (X) in the MRZ")
    if doc == "passport" and mrz.expiry_date and mrz.expiry_date < (today or date.today()):
        ex.warnings.append(f"this passport expired on {mrz.expiry_date.isoformat()}")
    return ex


# ---- cross-check of names against the printed page ---------------------------------------

_TRANSLIT = {"Ø": "OE", "Å": "AA", "Æ": "AE", "Ä": "AE", "Ö": "OE", "Ü": "UE", "ß": "SS",
             "Œ": "OE", "Þ": "TH", "Ð": "D"}


def _letters(text: str) -> list[str]:
    """Words of A-Z only, using the ICAO transliteration (Ø becomes OE) and dropping accents."""
    import unicodedata

    text = "".join(_TRANSLIT.get(ch, ch) for ch in text.upper())
    text = unicodedata.normalize("NFKD", text)
    return re.findall(r"[A-Z]+", "".join(ch for ch in text if not unicodedata.combining(ch)))


_DIGRAPHS = (("AA", "A"), ("OE", "O"), ("UE", "U"), ("AE", "A"))


def _collapse(token: str) -> str:
    """Undo the ICAO digraph transliteration so 'OESTENBYEN' and an OCR'd 'OSTENBYEN' compare equal."""
    for long, short in _DIGRAPHS:
        token = token.replace(long, short)
    return token


def _distance(a: str, b: str, limit: int) -> int:
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def printed_text_without_mrz(text: str) -> str:
    """Drop machine-readable lines, so the comparison is against the printed zone only."""
    keep = []
    for ln in text.splitlines():
        if "<" in ln or any(len(w) >= 25 for w in ln.split()):
            continue
        keep.append(ln)
    return "\n".join(keep)


def names_not_on_page(mrz: PassportMrz, page_text: str) -> list[tuple[str, str | None]] | None:
    """Name parts from the MRZ that do not appear, exactly, on the printed page.

    Names carry no check digit, so this is the only independent evidence for them. Exact match
    only: a one-letter difference is precisely the kind of OCR error this exists to catch. The
    nearest page word is returned as a hint. Returns None when the page text is too thin to say
    anything (a poor OCR of the page is not evidence).
    """
    words = _letters(printed_text_without_mrz(page_text))
    if sum(len(w) for w in words) < 80:
        return None
    present = set(words)
    collapsed = {_collapse(w) for w in present}
    missing = []
    for token in _letters(mrz.surname) + _letters(mrz.given_names):
        if token in present or _collapse(token) in collapsed:
            continue
        # A transliterated letter (Ø became OE, Å became AA) prints with a diacritic that page OCR
        # often drops or garbles, so one wrong letter is tolerated there and only there.
        if _collapse(token) != token and any(_distance(_collapse(token), c, 1) <= 1 for c in collapsed):
            continue
        if True:
            near = min((w for w in present if len(w) >= 3 and _distance(token, w, 2) <= 2),
                       key=lambda w: _distance(token, w, 2), default=None)
            missing.append((token, near))
    return missing


def _implausible_name(mrz: PassportMrz, name_line_has_separator: bool) -> str | None:
    """Patterns no real transliterated name has: they mean the name line was misread."""
    if not name_line_has_separator:
        return "the name line has no '<<' between surname and given names"
    for token in _letters(mrz.surname) + _letters(mrz.given_names):
        if re.search(r"(.)\1{3,}", token) or (len(token) >= 2 and len(set(token)) == 1):
            return f"{token!r} is one letter repeated"
        if token == "K":
            return "a lone 'K' in the name, which is how OCR usually misreads the '<' filler"
    return None


def _flag_names(ex: Extraction, reason: str) -> None:
    from dataclasses import replace

    keys = {"family_name", "given_name", "middle_name"}
    ex.facts = [replace(f, verified=False, note=(f.note + "; " if f.note else "") + reason)
                if f.key in keys and f.doc == "passport" else f for f in ex.facts]


def _alnum_words(text: str) -> set[str]:
    return set(re.findall(r"[A-Z0-9]{5,}", text.upper()))


def crosscheck_passport_number(ex: Extraction, page_text: str) -> None:
    """The check digit cannot tell O from 0 in a document number; the printed page can."""
    if not ex.mrz or "passport" not in ex.kinds or not ex.mrz.document_number:
        return
    page = printed_text_without_mrz(page_text)
    if sum(len(w) for w in _letters(page)) < 80:
        return
    number = ex.mrz.document_number
    words = _alnum_words(page)
    if number in words:
        return
    near = next((w for w in words if len(w) == len(number) and _distance(number, w, 1) <= 1), None)
    if near:
        ex.warnings.append(f"passport number: the machine-readable lines say {number} but the printed "
                           f"page says {near}. Letters O and 0 look alike and the check digit cannot "
                           "tell them apart; check the number against the document.")


def _page_confirms(ex: Extraction, page_text: str) -> bool:
    """True when every name part and the passport number are on the printed page."""
    if not ex.mrz:
        return True
    if names_not_on_page(ex.mrz, page_text) != []:
        return False
    number = ex.mrz.document_number
    return not number or number in _alnum_words(printed_text_without_mrz(page_text))


def crosscheck_page(ex: Extraction, texts: Iterator[str]) -> None:
    """Pool OCR passes of the printed page until they confirm the MRZ, then report what they could
    not confirm. Stops early on a good page, so clean scans stay quick."""
    pooled = ""
    for text in texts:
        pooled += "\n" + text
        if _page_confirms(ex, pooled):
            break
    crosscheck_names(ex, pooled)
    crosscheck_passport_number(ex, pooled)


def crosscheck_names(ex: Extraction, page_text: str) -> None:
    """Compare passport names with the printed page; a name that is not there is untrustworthy."""
    if not ex.mrz or "passport" not in ex.kinds:
        return
    missing = names_not_on_page(ex.mrz, page_text)
    if missing is None:
        ex.warnings.append("the printed page could not be read well enough to compare the names "
                           "with the machine-readable lines; compare them yourself")
        return
    if not missing:
        return
    parts = "; ".join(f"the machine-readable lines say {t}" + (f", the page says {n}" if n else
                      ", which is not on the page") for t, n in missing)
    ex.warnings.append(f"passport name does not match the printed page ({parts}). One of the two "
                       "readings is wrong; type the correct name.")
    _flag_names(ex, "does not match the printed page")


# ---- I-94 record ------------------------------------------------------------------------

_I94_LABELS = {
    "i94_number": ("Admission (I-94) Record Number", "I-94 Number", "Admission Number"),
    "last_entry_date": ("Most Recent Date of Entry", "Arrival/Issued Date", "Arrival Date", "Date of Entry"),
    "class_of_admission": ("Class of Admission",),
    "admit_until": ("Admit Until Date", "Admit Until"),
    "family_name": ("Last/Surname", "Last Name", "Surname"),
    "given": ("First (Given) Name", "First Name", "Given Name"),
    "birth_date": ("Birth Date", "Date of Birth"),
    "passport_number": ("Document Number", "Passport Number"),
    "citizenship_name": ("Country of Citizenship",),
}
_LABEL_INDEX = sorted(((lab.lower(), key) for key, labs in _I94_LABELS.items() for lab in labs),
                      key=lambda t: -len(t[0]))
_DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%Y%m%d", "%B %d, %Y", "%b %d, %Y", "%d %b %Y", "%d-%b-%Y",
                 "%Y %B %d", "%Y %b %d")
# What each style is called on screen. 03/04/2024 is ambiguous on paper; US order is assumed.
_FORMAT_NAMES = {"%Y-%m-%d": "YYYY-MM-DD", "%m/%d/%Y": "MM/DD/YYYY", "%Y%m%d": "YYYYMMDD",
                 "%B %d, %Y": "Month D, YYYY", "%b %d, %Y": "Mon D, YYYY",
                 "%d %b %Y": "D Mon YYYY", "%d-%b-%Y": "D-Mon-YYYY",
                 "%Y %B %d": "YYYY Month D", "%Y %b %d": "YYYY Mon D"}


def parse_date_format(text: str) -> tuple[date, str] | None:
    """The date and the name of the style it was written in. 03/04/2024 is read as March 4 (US order)."""
    text = text.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date(), _FORMAT_NAMES[fmt]
        except ValueError:
            continue
    return None


def parse_date_loose(text: str) -> date | None:
    hit = parse_date_format(text)
    return hit[0] if hit else None


def _label_at(line: str):
    low = line.lower()
    for lab, key in _LABEL_INDEX:
        if low.startswith(lab):
            return key, line[len(lab):].lstrip(" :\t")
    return None


def looks_like_i94(text: str) -> bool:
    low = text.lower()
    if "arrival/issued date" in low and "admit until" in low:    # the I-94 website, even cropped
        return True
    return "i-94" in low and ("admission" in low or "most recent date of entry" in low)


def parse_i94(text: str, printed: dict[str, tuple[str, str]] | None = None) -> tuple[dict[str, str], list[str]]:
    """Label/value pairs from an I-94 printout, in either 'Label: value' or two-line layout.

    If ``printed`` is given it is filled with {key: (text as printed, format name)} for each date."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    raw: dict[str, str] = {}
    for i, line in enumerate(lines):
        hit = _label_at(line)
        if not hit:
            continue
        key, rest = hit
        if not rest and i + 1 < len(lines) and not _label_at(lines[i + 1]):
            rest = lines[i + 1]
        if rest and key not in raw:
            raw[key] = rest.strip()

    warnings: list[str] = []
    out: dict[str, str] = {}

    def date_field(key: str, label: str):
        if key in raw:
            hit = parse_date_format(raw[key])
            if hit:
                out[key] = hit[0].isoformat()
                if printed is not None:
                    printed[key] = (raw[key].strip(), hit[1])
            else:
                warnings.append(f"I-94: could not read the {label} date {raw[key]!r}")

    if "i94_number" in raw:
        num = re.sub(r"[\s-]", "", raw["i94_number"]).upper()
        if re.fullmatch(r"[A-Z0-9]{11}", num):
            out["i94_number"] = num
        else:
            warnings.append(f"I-94: the admission number {raw['i94_number']!r} is not 11 characters")
    date_field("last_entry_date", "most recent entry")
    # The I-94 website prints one "Arrival/Issued Date"; it is both the arrival and the issue date.
    if "last_entry_date" in out and re.search(r"(?i)arrival\s*/\s*issued\s+date", text):
        out["issue_date"] = out["last_entry_date"]
        if printed is not None and "last_entry_date" in printed:
            printed["issue_date"] = printed["last_entry_date"]
    date_field("birth_date", "birth")
    if "admit_until" in raw:
        v = raw["admit_until"]
        if re.fullmatch(r"(?i)d\s*/?\s*s|duration of status", v):
            out["admit_until"] = "D/S"
            if printed is not None:
                printed["admit_until"] = (v.strip(), "duration of status")
        else:
            date_field("admit_until", "admit-until")
    for key in ("class_of_admission", "family_name", "passport_number", "citizenship_name"):
        if key in raw:
            out[key] = raw[key].upper() if key != "citizenship_name" else raw[key]
    if "given" in raw:
        parts = raw["given"].upper().split()
        if parts:
            out["given_name"] = parts[0]
        if len(parts) > 1:
            out["middle_name"] = " ".join(parts[1:])
    return out, warnings


def facts_from_i94(values: dict[str, str], source: str,
                   printed: dict[str, tuple[str, str]] | None = None) -> list[Fact]:
    note = "no checksum on an I-94; compare with the document"
    printed = printed or {}
    return [Fact(k, v, source, None, note, "i94", *printed.get(k, ("", ""))) for k, v in values.items()]


# ---- entry point ------------------------------------------------------------------------

def extract_file(path: Path, *, today: date | None = None) -> Extraction:
    path = Path(path)
    ex = Extraction(str(path), sha256_file(path))
    notes: list[str] = []

    fallback: dict[str, Extraction] = {}   # first reading per document whose check digits failed

    def take_mrz(text: str, *, strict: bool = True) -> bool:
        """Accept an MRZ reading. While searching (strict) only a valid one counts: a reading that
        parses but fails its check digits is remembered and used only if nothing better turns up."""
        found = False
        for doc, finder in (("passport", find_mrz_lines), ("visa", find_mrv_lines)):
            lines, note = finder(text)
            if note:
                notes.append(note)
            if not lines or doc in ex.kinds:
                continue
            changed = 0
            letters = type_constrained(*lines, doc, digits=False)
            if letters:
                lines, changed = (letters[0], letters[1]), letters[2]
            sub = extraction_from_lines(str(path), ex.sha256, *lines, today=today, doc=doc)
            if not sub.kinds:
                continue
            if sub.mrz and not sub.mrz.valid:
                both = type_constrained(*lines, doc, digits=True)
                if both:
                    retry = extraction_from_lines(str(path), ex.sha256, both[0], both[1],
                                                  today=today, doc=doc)
                    if retry.mrz and retry.mrz.valid:       # accept only if every check digit passes
                        sub, changed = retry, both[2] + changed
            if changed:
                sub.warnings.insert(0, (
                    f"{doc}: {changed} character(s) were confused between letters and digits "
                    "(such as 0 and O) and were corrected by position. Check digits do not cover "
                    "names, so compare the name with the printed page."))
            if strict and not (sub.mrz and sub.mrz.valid):
                fallback.setdefault(doc, sub)
                continue
            ex.kinds += sub.kinds
            ex.facts += sub.facts
            ex.warnings += sub.warnings
            ex.mrz = ex.mrz or sub.mrz
            found = True
        return found

    def take_i94(text: str) -> bool:
        if "i94" in ex.kinds or not looks_like_i94(text):
            return False
        printed: dict[str, tuple[str, str]] = {}
        values, warns = parse_i94(text, printed)
        if len(values) < 3:
            return False
        ex.kinds.append("i94")
        ex.facts += facts_from_i94(values, f"{path.name} (I-94)", printed)
        ex.warnings += warns
        return True

    if path.suffix.lower() != ".pdf" and path.suffix.lower() not in IMAGE_SUFFIXES:
        ex.warnings.append(f"unsupported file type {path.suffix or '(none)'}")
        return ex

    # 1. Text already in the file. A scanner app's text layer is usually junk, so finding
    #    nothing here is not the end: the page images are searched next.
    embedded, warns = _embedded_text(path)
    ex.warnings += warns
    for blob in embedded:
        take_i94(blob)
        take_mrz(blob)
    if "passport" in ex.kinds and embedded:
        crosscheck_page(ex, iter(["\n".join(embedded)]))

    # 2. OCR the page images.
    seen: list[str] = []                     # page text as read, to recognise a passport's back or cover
    if not ex.kinds:
        if not ocr_available():
            ex.warnings.append("Tesseract is not installed, so scans and photos cannot be read")
        else:
            try:
                for img in _page_images(path):
                    page = _autocrop(_gray(img))
                    if vision.available():                      # the printed page, as text
                        vtext = vision.read_text(page)
                        seen.append(vtext)
                        if take_i94(vtext):
                            break
                    elif shutil.which("tesseract"):
                        ttext = _ocr(page, mrz=False)
                        seen.append(ttext)
                        if take_i94(ttext):
                            break
                    for text, variant in mrz_text_candidates(img):   # stops generating once one parses
                        seen.append(text)
                        if take_mrz(text):
                            # compare the names with the printed page in the orientation that worked
                            crosscheck_page(ex, _visual_texts(variant))
                            break
                    if ex.kinds:
                        break
            except Exception as exc:   # a damaged file must not crash the window
                ex.warnings.append(f"could not read the file's pages: {exc}")

    for doc, sub in fallback.items():
        if doc not in ex.kinds:
            ex.kinds += sub.kinds
            ex.facts += sub.facts
            ex.warnings += sub.warnings
            ex.mrz = ex.mrz or sub.mrz

    if not ex.kinds and seen:
        kinds = {passport_page_kind(t) for t in seen}
        if "other" in kinds and "data" not in kinds:
            ex.kinds.append(PASSPORT_OTHER_PAGE)
            ex.warnings.append(
                "This looks like the back or cover of a passport. It has no machine-readable lines, so "
                "nothing is read from it. Names, dates and the passport number come from the photo page "
                "(the one with the two lines of < characters at the bottom); upload that page too.")

    if not ex.kinds:
        ex.warnings.append(notes[0] if notes else
                           "no passport, visa or I-94 found. Passports, visas and I-94 records are "
                           "read so far; if this is a passport, try a sharper, upright photo of the "
                           "photo page (the page with your picture), or type the two lines at its "
                           "bottom in by hand.")
    return ex

