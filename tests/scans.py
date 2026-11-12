"""Build realistic bad scans from the public specimen images. Test helper only."""
from pathlib import Path

from PIL import Image

SPECIMENS = Path(__file__).parent / "fixtures" / "specimens"

TRUTH = {
    "norwegian-specimen": dict(
        family_name="OESTENBYEN", given_name="AASAMUND", middle_name="SPECIMEN", sex="M",
        birth_date="1956-04-23", passport_number="CCC002251", passport_expiry="2030-04-15",
        nationality_code="NOR", passport_country_code="NOR"),
    "roc-data-page": dict(
        family_name="LIN", given_name="MEI", middle_name="HUA", sex="F",
        birth_date="1988-01-01", passport_number="888800371", passport_expiry="2027-12-25",
        nationality_code="TWN", passport_country_code="TWN"),
}


def base(stem: str) -> Image.Image:
    return Image.open(SPECIMENS / f"{stem}.jpg").convert("RGB")


def letter_page(img, frac_w=0.72, top_frac=0.08, dpi=200):
    """The passport as part of a US Letter page, as a flatbed or phone-scan app produces."""
    w_page, h_page = int(8.5 * dpi), int(11 * dpi)
    page = Image.new("RGB", (w_page, h_page), "white")
    w = int(w_page * frac_w)
    page.paste(img.resize((w, int(img.height * w / img.width))), ((w_page - w) // 2, int(h_page * top_frac)))
    return page


def rotated(img, degrees):
    return img.rotate(degrees, expand=True, fillcolor="white")


def save_png(img, path):
    img.save(path)
    return path


def save_pdf(img, path, junk_text_layer=False):
    """Image-only PDF, or an image PDF with the invisible junk text layer scanner apps add."""
    if not junk_text_layer:
        img.save(path, resolution=200)
        return path
    import pymupdf  # AGPL: only used here, to build a test file; the app never imports it

    png = Path(str(path) + ".png")
    img.save(png)
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_image(page.rect, filename=str(png), keep_proportion=True)
    page.insert_text((40, 30), "Scanned with Scanner App 11/2026   Document 1 of 1", fontsize=9, render_mode=3)
    doc.save(path)
    return path
