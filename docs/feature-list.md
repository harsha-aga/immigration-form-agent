# Feature list

Written 2026-11-06. Firms only; students and consumers parked. Tags like [G1] point to the numbered gaps in `market-gaps.md`. "My idea" means no research backs it yet.

Open decisions that can change this list: hosted portal versus local-first, which form comes first, and the legal posture (unauthorized practice of law review).

## Tier 1: the first version (the demo)

The goal of this tier is one clean path: passport and I-94 in, a checked and filled form out, with proof.

1. **Document import.** Drag in files and each is recognised as passport, I-94 and so on, using offline rules first. [G4]
2. **Passport reading.** Read the two machine-readable lines and verify every check digit. If the scan is poor, type them in with live check-digit validation. [G2, G6]
3. **I-94 reading.** Parse digital (text-layer) I-94 PDFs without OCR. Assumes these PDFs have a text layer; confirm in a spike. [G4]
4. **Guided questionnaire.** A typed intake for everything the documents don't supply, with validation as you go. [G10]
5. **Click-to-source review screen.** Source document beside the form, with only the exceptions listed. Click any field to see exactly where it came from. [G2]
6. **Passport-first reconciliation.** Compare every document with the passport. Findings are OK, INFO, WARN or BLOCK, each with a plain-language explanation and suggested next steps. A person resolves each one with a recorded reason. [G6]
7. **Name and date intelligence.** Handles accents, ICAO transliteration, cut-off names, name order, middle names left off, and swapped day and month.
8. **Form fill engine.** Fills the official PDF so it opens cleanly in Acrobat. First form to be decided. Needs an early spike because of XFA forms. [G8]
9. **Edition guard.** A signed registry of form editions with effective and sunset dates per filing method. Refuses to fill a stale edition and says why. [G1]
10. **Rejection pre-flight.** Checks for an unsigned form, wrong edition, missing fee and blank required fields before anything is exported. [G1]
11. **Filing evidence report.** One page per filing: sources by hash, checks run, discrepancies and how each was resolved, who reviewed, and the form edition used. [G2, G7, G12]
12. **Protected local storage.** Encrypted files, hashes re-verified on every read with no override, and a tamper-evident audit log. [G2, G3]
13. **Plain export.** Filled PDF plus the data as JSON and CSV, so it sits beside DocketWise, INSZoom or Clio. [G9]
14. **Portal copy sheet.** The data in the order of the USCIS online screens, with no automation of the portal. [G5]

## Tier 2: next

- **Two-person review.** Paralegal prepares, attorney signs off, with a signed attestation that goes invalid if anything changes.
- **More forms and bundles.** I-539, I-130, I-485, I-864, N-400, reusing the same data across a bundle, with cross-form consistency checks. *(my idea)*
- **History checks.** Gaps or overlaps in address, employment and travel history. *(my idea)*
- **Missing-evidence checklist** per form and category. *(my idea)*
- **Filing package builder.** G-28, cover letter, exhibit index and ordering. *(my idea)*
- **More document types.** I-797 notices, EAD, green card, birth and marriage certificates, tax transcripts, pay stubs. [G4]
- **New-edition alerts.** When USCIS publishes a new edition, show what changed in the field map and which tests fail. [G1]
- **Per-matter access and retention,** for ethical walls and deletion on request. *(my idea)*
- **Accuracy dashboard.** Per-document-type extraction accuracy on a synthetic benchmark, published. [G7]
- **AI-use log and policy template** showing which fields any AI touched. [G12]
- **Connectors** to existing case-management systems, starting with their import formats. [G9]

## Tier 3: later, bigger

- **Passport chip verification from the client's phone.** A link opens a native app, the client taps the passport, and the firm gets chip data verified against country certificates. Needs a native app, a verification service, a certificate trust store (the ICAO Master List's non-commercial terms need legal review) and a decision on how data gets from phone to firm. See `passport-chip-validation.md`.
- **Client document requests.** A secure link where clients upload, with a checklist of what is missing. [G10]
- **Foreign-language documents.** Translation hook and a tracker for certified translations. *(my idea)*
- **Server and multi-user mode,** with single sign-on.
- **Optional remote AI assist,** off by default, limited to document-type suggestions, with measured calibration before any threshold is trusted. See the earlier Jev discussion.
- **Regulatory-change monitoring** for policy and fee changes. [G11]

## Deliberately not doing

- Billing, IOLTA, calendars, texting and e-signature (practice-management features).
- Automating the USCIS portal or the CBP I-94 website.
- Claims of compliance (such as ABA Opinion 512) or of "no errors". Offer the evidence report instead.
- Students and consumers, for now.
