# Spike 1: can we fill real USCIS PDFs?

Run 2026-11-11 on the blank forms downloaded from uscis.gov. Scripts are in `spikes/` (read-only inspection plus a fill test). Downloads and outputs are git-ignored. Synthetic data only (the ICAO specimen person).

## What was tested

| | I-765 | I-539 |
|---|---|---|
| Source | uscis.gov/sites/default/files/document/forms/i-765.pdf | .../i-539.pdf |
| Size | 467,424 bytes | 495,022 bytes |
| SHA-256 | 9ac0eae2...0dc7d | 1bc54433...bd81f |
| Edition printed in the footer | **08/21/25** | **08/28/24** |
| Pages / fields | 7 / 180 | 7 / 176 |
| Structure | hybrid AcroForm + XFA | hybrid AcroForm + XFA |
| Encryption | yes, V4 R4, opens with an empty user password | same |
| Other | PDF417 barcode on every page, document-level JavaScript, SigFlags 2 | same |

Only the I-765 was filled. The I-539 shares the same structure, so I expect the same approach to work, but have not tried it.

## What worked

- `pypdf` plus `cryptography` opens the encrypted form, fills the AcroForm layer, and writes a file that renders correctly in PyMuPDF.
- Text fields, the A-Number comb field (digits land in the individual boxes), address fields, a state dropdown (two-letter codes), and checkboxes all filled and rendered correctly. Values read back match.
- Field names are descriptive (`Line1a_FamilyName`, `Pt2Line5_CityOrTown`) and each has a tooltip naming the form item, so a field map can be written and reviewed by a person.

## Findings that change the plan

1. **Checkbox on-states are not guessable.** Part 1 uses `/1`, `/2`, `/3`. Sex uses `/N` for Female and `/Y` for Male. Marital status uses `/Single`, `/Married` and so on. Setting the wrong one leaves the box unchecked with no error. The map must read each on-state from the form and every mapped checkbox needs a render test.
2. **XFA had to be removed.** If an XFA layer is present, Acrobat can prefer it over the AcroForm values. The fill removes `/XFA` so the AcroForm values apply. This changes how the form behaves in Acrobat and is not yet tested there.
3. **The barcodes are stale.** The PDF417 barcode on each page is copied from the blank form. Acrobat normally regenerates it from the entered data using the form's scripts. After removing XFA nothing updates it. **Unknown whether USCIS needs a correct barcode.** This is the main open risk.
4. **The output is unencrypted.** The owner-password restrictions on the original are dropped. Probably fine, but unverified.
5. **The editions on the site contradict my earlier research.** Secondary sources said new 09/15/26 editions of the I-765 and I-539 replaced these. The site served 08/21/25 and 08/28/24 on 2026-11-11. Either those sources were wrong or the site lags. Treat every edition date in `market-gaps.md` as unverified. The edition guard must read the date from the PDF itself and pin the SHA-256 of an approved blank, not rely on news.

## Not tested

- **Adobe Acrobat / Reader.** The real target viewer. Needs a person to open the output and check that it opens without warnings, values show, and what happens to the barcode.
- Printing, and whether USCIS accepts the output.
- The I-539, other forms, fields with scripts or validation, and repeating sections.
- Keeping the XFA layer and filling its data XML too, which may keep the barcode working in Acrobat. A second approach to compare.

## Tool notes

- `pypdf` (BSD) and `cryptography` are fine to depend on.
- `pymupdf` (AGPL) was used only to render pages in the spike. Do not ship it in a commercial product without checking the license. A permissive alternative such as pdfium (via `pypdfium2`) should be evaluated for rendering tests.

## Decision

Direct AcroForm filling is viable for field values. Do not build further on it until the Acrobat check and the barcode question are answered.

## Correction (2026-11-11): the barcode is missing, not stale

Earlier text in this file says the PDF417 barcodes are "stale". That was wrong. The blank form has
no barcode in its page content; the XFA template defines a `<barcode type="pdf417">` element that
only an XFA engine draws. Deleting `/XFA` therefore removes the barcode entirely. Filled output
shows only the printed footer text (`I-765|08/21/25|N`) where the barcode should be.

Verified by the user in Adobe Acrobat (macOS) on `i-765-filled4.pdf`:
- opens with no error bar; 1.a checkbox shows ticked
- no barcode at the bottom of the page

Fixed in `fill_spike3.py`, enforced by `spikes/check_output.py`:
- `/Perms /UR3` (Adobe usage-rights signature) removed. Left in place it makes Reader report the
  document as modified.
- leftover `!ADBE::` XFA version-check scripts removed.
- `NeedAppearances` set to True *after* `update_page_form_field_values(..., auto_regenerate=False)`,
  which otherwise resets it to False.

Open question, not answered: does USCIS require the barcode? Unknown. Alternative to test: keep the
XFA layer and fill its `datasets` XML so the viewer draws the barcode.

## Update (2026-11-11): the barcode does not carry applicant data

Reading the XFA template: the page barcode is the field `PDF417BarCode1`, `bind match="none"`, and
its content is built by script as `FormID + "|" + RevDate + "|" + page number` (e.g.
`I-765|08/21/25|2`). It identifies the form, edition and page; it does not encode anything the
applicant enters. So the earlier worry about a "stale" data barcode was misplaced. Keeping the XFA
layer is enough for Acrobat to draw it; nothing about the data has to feed it.

Consequence: the product keeps the XFA layer. `src/uscis_autofill/filler.py`:
- carries every XFA packet (template, config, ...) through unchanged and checks that on read-back;
- writes values only into the existing empty elements of the XFA `datasets` packet
  (global fields sit directly under `form1`, page-local ones under `form1/PageN`);
- mirrors the values into the AcroForm widgets so non-Adobe viewers agree;
- removes only the `/Perms /UR3` usage-rights signature (any edit invalidates it);
- keeps the XFA version-check scripts, since the XFA layer is kept.

Verified by tests: template/config/etc. byte-identical, values read back in both layers, checkbox
groups have exactly one on-state, a blank with an unknown SHA-256 is refused, invalid values are
refused before anything is written.

NOT yet verified (needs Adobe Acrobat): that Acrobat shows the filled values from the XFA data,
draws the barcode, and raises no warning. pdfium (used for our renders) has no XFA engine, so it
shows the AcroForm layer and no barcode. Open spikes/out/i-765-xfa-filled.pdf in Acrobat to check.
Also untested: real phone photos of passports (OCR was tried on synthetic images only).
