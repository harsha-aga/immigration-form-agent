# Immigration forms: market research and gaps

Written 2026-11-06. Scope for now: **law firms only.** Students and consumers are parked (Appendix A).

**How much to trust this.** I have not used any of these products. Almost everything here comes from vendor pages, press releases, review aggregators and secondary articles. Where sources disagree, both are noted. "Evidence" ratings mean how well the gap is supported, not how big it is. Something missing from a vendor's page may still exist in the product, so confirm each gap in a demo or interview before building on it.

---

## 1. Corrections to things I said earlier

1. **Rasa Legal is not an immigration company.** It does criminal-record clearance and expungement (Pennsylvania, Utah, Arizona). It does not belong in the competitor set. The immigration AI firm that appeared next to it in search is **LegalOS** (Y Combinator W26, an "AI-native immigration law firm"; it claims a 100% approval rate, self-reported).
2. **Docketwise AI capture availability is unclear.** Docketwise's blog says its document assistant is offered to Pro and Advanced users. Its support-centre page says AI Data Capture is in *closed beta, select accounts only*. The ABA Journal (June 2025) also said closed beta. They may be different features, or the status may have changed. I earlier said extraction "already ships"; the accurate statement is "marketed, availability unconfirmed".
3. **Visalaw.ai funding:** one source says a $1.6M seed, another (the Valor Ventures release) gives no amount. They may be the same round or two.
4. **"VisaArchitect $42M Series B"** appeared on a single aggregator and is unverified. Do not use it.
5. **Rasa Legal's "$5M seed"** is also reported as "late stage" and "late seed raise" by other outlets, and its lead investor is named inconsistently. Irrelevant now.

---

## 2. Landscape in one table

| Company | Type | Competes on | Owner / funding (as reported) |
|---|---|---|---|
| 8am DocketWise | Case management + forms + AI | Forms, intake, extraction, e-sign | Owned by 8am (formerly AffiniPay). Bought via MyCase in 2022 (sources disagree on month). Rebranded Aug 2025 |
| Mitratech INSZoom | Case management | Forms, e-filing, corporate and global immigration | Acquired by Mitratech Nov 2020, price undisclosed |
| LollyLaw | Case management | Forms, intake, e-filing, client portal | Acquired by Paradigm in 2022 (per LawNext headline) |
| CaseBlink | AI drafting and case prep | Document understanding, research, drafting | $2M pre-seed (Tower Research Ventures, firms incl. Fakhoury), March 2025 |
| Visalaw.ai | AI research and drafting | Research, drafting, application construction | Seed led by Valor Ventures; amount undisclosed or $1.6M |
| Alvva | AI forms and extraction | Document extraction, guided forms, attorney review | Founded 2021, San Francisco, $425K total (Stanford CodeX index) |
| Glade (Noodle) | Practice tools + autofill | PDF autofill of government forms, retainers, questionnaires | Not stated |
| Boundless | Consumer + business immigration | Flat-fee filing help via affiliated law firm | About $45M total across 4 rounds (aggregator). Layoffs in 2025 (GeekWire) |
| CitizenshipWorks | Free nonprofit tool | N-400 for green card holders, nonprofit legal review | Immigration Advocates Network / Pro Bono Net |
| ~~Rasa Legal~~ | *Not immigration* | | |

Three kinds of competitor:

- **System of record with forms** (DocketWise, INSZoom, LollyLaw, Glade): where firms already work. These are the real competition for a forms engine.
- **Drafting and research AI** (CaseBlink, Visalaw.ai): focused on briefs, support letters and research, not form filling. More likely partners than rivals.
- **Consumer and nonprofit** (Boundless, CitizenshipWorks, Alvva partly): parked, but they teach us about legal structure and trust.

---

## 3. Company by company

### 8am DocketWise
- **What it is:** the main small-firm immigration platform: Smart Forms, multilingual adaptive intake questionnaires with validation queues, e-signature, case management. AI layer is "8am IQ".
- **AI capture:** passport, green card, EAD and I-94 only, with "more planned". The user uploads a file, reviews extracted values in a "Review & Edit" step, and nothing is written until they click Confirm & Import. Fields extracted are not listed. No accuracy figures. See correction 2 on availability.
- **Pricing (aggregators disagree):** about $59–$129 per user per month. Capterra shows Basic $69, Pro $99, Advanced $119. AI assistants are offered to Pro and Advanced.
- **Praise:** Capterra 4.8 of 5 from 99 reviews. Reviewers like the forms, constant updates, multilingual questionnaires and support.
- **Complaints found:**
  - Manually re-typing client data into the USCIS online portal (two reviewers).
  - One new form still unavailable a month after release.
  - IOLTA and accounting reports are not available (one consultant).
  - Clio integration said not to work as advertised (one reviewer).
  - Employment-based features were still rolling out (a 2018 review).
  - Training described as absent by one reviewer and excellent by others.
- **Unknown:** extraction accuracy, edition handling beyond "we update quickly", provenance, any local or private deployment.
- **Read for us:** strong incumbent, well liked. Beat it on one narrow thing, not breadth.

### Mitratech INSZoom
- **What it is:** immigration case management for corporations, law firms, staffing specialists and nonprofits, with global (US, Canada, other) programs, USCIS and DOL e-filing, and bulk LCA filing. Part of Mitratech's Tracker Corp suite (I-9 and E-Verify compliance). Founded 1999, Pleasanton CA, development in Bangalore.
- **Pricing:** inconsistent. GetApp shows $50 / $100 / $150 / $180 per user per month tiers; Capterra shows "from $50 per feature". Unit unclear.
- **Reviews:** only six found (SoftwareSuggest, 4 of 5). Pros: e-filing, translation, document checklists, business plan options. One request: better app support. No cons found.
- **Unknown:** almost everything about weaknesses. This is an evidence gap, not a clean bill of health.
- **Read for us:** aimed at corporate and global programs, so less overlap with small-firm, passport-first intake. Ask firms who use it what they dislike.

### LollyLaw
- **What it is:** immigration practice management: form library, "LollyForms" form-filling and client intake, e-filing (the ABA Journal says yes, one comparison site says not mentioned), billing, client portal, reminders and status automation. A guide says 125+ forms and 40+ customizable workflows.
- **Pricing:** conflicting, about $79–$120 per user per month; no official tiers found.
- **Reviews:** G2 4.5 of 5 from 119 reviews. G2's auto summary flags data management and document management (one review each) and low billing and e-signature scores. One low-authority page says document automation is limited.
- **No evidence found of AI document extraction.**
- **Read for us:** plausibly lacks the extraction and cross-check layer. Not verified.

### CaseBlink
- **What it is:** AI for case preparation: document understanding (sorting and summarizing), automated research, drafting of exhibit lists, briefs and support letters into one ready-to-file PDF. "Studio" custom drafting tool in beta.
- **Scale (March 2025 release):** over 50 firms, over 1,000 cases. Only named customer is Fakhoury Global Immigration, which is also an investor. No quantified time savings, no pricing, no forms named.
- **Read for us:** drafting-focused, not form-filling. Potential partner or integration. Gaps are unknown; the release lists none.

### Visalaw.ai
- **What it is:** AI legal research, assessment, drafting, summarization and "visa application construction" for immigration firms. Includes a law library and AILA's practice manual (co-founder Greg Siskind co-authored it). Claims it maintains attorney-client confidentiality.
- **Scale and claims:** an investor says "hundreds of immigration law firms". One firm reports up to a 90% reduction in drafting time, including 50+ page EB-1 petitions. No pricing, no forms named.
- **Read for us:** drafting and research, so also not a direct forms competitor. The confidentiality claim is worth testing against how data is actually handled.

### Alvva
- **What it is:** AI software for immigration applications combining document extraction, guided form workflows and attorney review, for consumers and law firms. Founded 2021, San Francisco, subscription model, $425K total funding.
- **No features, limits or customer counts found beyond that.**
- **Read for us:** closest in concept to our idea, but thinly funded and thinly documented. Check whether it is still active and who it really serves.

### Glade (Noodle)
- **What it is:** practice workflow tool with PDF autofill. Claims it saves "three hours on average" per autofilled form set. Also retainers, invoices with reminders, questionnaires, document checklists, 24/7 client chat, a master-PDF merge.
- **Gaps in what the vendor says:** does not say what data fills the forms, how a review step works, how editions are handled, what security applies, or what it costs. The forms list contains repeats and inconsistencies.
- **Read for us:** direct competitor on autofill, with the least visible provenance and review. Worth a demo.

### Boundless (consumer, parked)
- **What it is:** flat-fee immigration help. Not a law firm; works with Boundless Legal, a law firm licensed in Arizona and authorized under Utah's legal-innovation programme. Also a business product ("case management" for employers). 2025 layoffs reported; Klarna financing announced 2026.
- **Reviews conflict:** Trustpilot 4.8 of 5 (about 5,000 reviews) against BBB 2.83 of 5 (70 reviews, 33 complaints in three years). Complaints cite timing and difficulty reaching anyone after paying.
- **Read for us:** the affiliated-law-firm structure is the template for consumer-facing legal posture. Confirms support after sale is the weak point.

### CitizenshipWorks (nonprofit, parked)
- **What it is:** free online system: prescreen, N-400 interview, then review by a nonprofit's attorney or accredited representative. Run by the Immigration Advocates Network with the Immigrant Legal Resource Center, under Pro Bono Net. One source claims 60,000+ users.
- **Limits:** one form (N-400), green card holders only, no legal advice, English, Spanish and Chinese only, and the Spanish interview produces an English form. Partner nonprofits must enrol a licensed attorney or accredited representative.
- **Read for us:** shows the free ceiling for the single-form case, and that human legal review is the hard part to scale.

---

## 4. Market gaps (firm-side), with evidence

| # | Gap | Evidence | Strength |
|---|---|---|---|
| G1 | **Edition and filing-window guardrails.** New editions with no grace period (the I-539 and I-765 09/15/26 editions), paper judged by postmark and e-filing by submission date, new editions cannot be filed early, I-864 reportedly has a 30-day grace period, I-129 dates moved. One DocketWise reviewer saw a one-month lag | VisaVerge, Capterra review | Strong |
| G2 | **Provable provenance.** DocketWise capture has a review step but no published error rates; nobody I read describes tamper evidence | Docketwise support centre | Medium |
| G3 | **Local-only deployment.** No immigration-specific product found offering on-premises or no-cloud. ABA Opinion 512 (persuasive, not binding) says informed consent is generally needed before client information goes into self-learning AI tools. Mitratech survey (2021): 60% named client security the biggest issue | Slashdot on-prem list, Zuva summary, Mitratech | Medium to strong |
| G4 | **Wider document coverage.** DocketWise capture covers four document types. Not listed: I-797 notices, birth and marriage certificates, tax transcripts, pay stubs, foreign-language documents | Docketwise support centre, ABA Journal | Medium |
| G5 | **Portal-ready output** for USCIS online filing (re-typing complaint) | Capterra reviews | Medium |
| G6 | **Explained cross-document checks.** DocketWise has validation queues; nothing found on passport check digits, ICAO name rules or day/month-swap detection | Docketwise blog | Weak (absence from marketing) |
| G7 | **Published accuracy.** No vendor publishes extraction accuracy. Only 8% of immigration firms have a written AI policy (vendor-sourced, 8am) | Docketwise blog | Medium |
| G8 | **Reliable PDF save and fill.** One paralegal reports ImmPro save errors; XFA problems documented in forums | Reddit snapshot, DocuSign thread | Weak |
| G9 | **Interoperability.** One reviewer says DocketWise does not integrate with Clio as advertised | Capterra | Weak |
| G10 | **Client document collection and file sharing.** Receiving digital files from applicants is hard; 45% find file sharing troublesome (2021) | Mitratech survey | Medium (dated) |
| G11 | **Keeping up with policy and regulation.** 60% named it their biggest pain (2021); firms track executive orders and form changes by hand | Mitratech, ABA Journal | Medium (dated) |
| G12 | **AI governance and audit trail.** 64% have no AI policy (vendor figure) | Docketwise blog | Medium |
| G13 | **Onboarding friction.** Some firms do not adopt AI because they lack time to evaluate products | ABA Journal | Weak |
| G14 | **Client status communication.** Vendors say clients flood firms with status checks, but this is crowded (CaseStatus integrates with DocketWise) | Vendor blogs | Weak |

Context, not gaps: firms report being much busier (one New York firm "three times as busy"); unrepresented immigrants in court rose from 363,000 (2019) to nearly 2.3M (early 2024) per TRAC via the ABA Journal.

**Things to leave alone:** IOLTA and accounting reports, texting, billing, calendars, e-signature. They are practice-management features.

---

## 5. Market size (firm side)

- **IBISWorld:** about $10.6B US immigration law revenue (2026), about 18,400 businesses, average 2.5 employees, about 46,000 employed; no firm holds over 5% share (largest: Fragomen). Another IBISWorld page gives 19,969 businesses for 2025. Other sites give conflicting counts; ignore them.
- **My arithmetic, not sourced:** 46,000 employees at $60–$120 per seat per month is about $33M–$66M a year in seat software, as an upper bound if everyone had a seat. The software market is small beside $10.6B of revenue, so the pitch is labor saved per filing.
- **Adoption (vendor-sourced, 8am):** 82% of immigration professionals use AI personally, 40% use generative AI daily; drafting 58%, client communication 40%, summarization 40%, petition preparation 38%, intake 31%. The Federal Bar Association puts use at 47% (via Minnesota Lawyer).

---

## 6. What this suggests for a firm-only v1

Best-supported wedge: **edition-safe fill (G1), passport-first explained cross-checks (G6), provable provenance (G2), local processing (G3).** Watch: DocketWise can close G4 and G6 at any time because it owns the system of record.

## 7. Open questions

- Is DocketWise AI capture generally available? What do real users say about its accuracy?
- What do INSZoom users dislike? (almost no evidence)
- Is Alvva still active, and who does it serve?
- Does LollyLaw offer e-filing and any extraction?
- What is Glade's review and security story?
- What do 8 to 10 small firms say is slowest, and what would they pay?

## 8. Decisions so far

- Firms only for now; students and consumers parked.
- First attempt at the project was deleted; restarting from research.
- Open: hosted portal versus local-first; first form(s); legal posture. The earlier plan assumed local-first; a hosted S3 portal removes G3 as a differentiator and makes secure storage a cost of entry.

---

## Appendix A. Parked: students and consumers

Parked on request. Detail is kept here for later.

- **Audience:** F-1 students filing I-765 for OPT and STEM OPT.
- **Common errors:** wrong (c)(3) category, filing before the school official's recommendation, missing the 30-day window after it, unsigned form, blank "reason for applying", outdated edition, photo problems (selfies rejected; rules differ by source), wrong fee or payment, name errors that carry to the work permit, employer-name mismatch on STEM OPT.
- **Prices (third-party sources, verify):** USCIS $470 online or $520 paper; premium processing about $1,780; attorneys about $250–$800 for clean cases, up to $3,000 for STEM OPT; schools sometimes add $100–$300.
- **Volume:** 1,177,766 international students (Open Doors 2025); about 194,500 OPT and 95,400 STEM OPT authorizations in 2024 (secondary summary of SEVIS data); I-765 reportedly the highest-volume USCIS form (vendor-sourced figure).
- **Competitors:** Immiva (guided filing, "not a lawyer or law firm"), Boundless, Fillvisa (free), university guides.
- **Risks:** duration-of-status rule (reportedly final, injunction unconfirmed); an OPT fee proposal (comments reportedly due 9 Nov 2026); ICE and SEVP OPT fraud actions; unauthorized-practice-of-law exposure (Parsons case, Colorado discipline cases, H&R Block exit).
- **Hosted-storage risk example:** May 2026 UK visa-portal leak of over 100,000 passport scans and selfies from a misconfigured S3 bucket.
- **Illustrative sizing (my arithmetic):** about 290,000 filings x 10% share x $100 is about $2.9M a year.

## Appendix B. Sources

- Docketwise AI blog: https://docketwise.com/blog/ai-for-immigration-lawyers/
- Docketwise AI data capture: https://supportcenter.docketwise.com/en/articles/10247778-ai-data-capture
- Docketwise reviews (Capterra): https://capterra.com/p/172490/Docketwise/reviews/
- Docketwise pricing (Capterra): https://www.capterra.com/p/172490/Docketwise/pricing/
- 8am rebrand (LawNext): https://www.lawnext.com/2025/08/affinipay-parent-to-lawpay-mycase-and-others-rebrands-as-8am-to-signify-its-evolution-into-a-unified-professional-services-platform.html
- Mitratech acquires INSZoom: https://mitratech.com/resource-hub/pressreleases/mitratech-acquires-inszoom/
- Mitratech survey (2021): https://mitratech.com/resource-hub/blog/survey-three-areas-immigration-legal-teams/
- LollyLaw (Capterra): https://www.capterra.com/p/184685/Lolly-Law/
- LollyLaw (G2): https://www.g2.com/products/lollylaw/reviews
- Paradigm acquires LollyLaw (LawNext): https://lawnext.com/2022/04/practice-management-company-paradigm-acquires-immigration-case-management-software-lollylaw.html
- CaseBlink release: https://natlawreview.com/press-releases/caseblink-raises-2m-pre-seed-funding-transform-immigration-case-preparation
- Visalaw.ai release: https://www.newswire.com/news/visalaw-ai-accelerates-growth-with-seed-funding-led-by-valor-ventures-22521116
- Alvva (Stanford CodeX): https://techindex.law.stanford.edu/companies/alvva
- Glade autofill: https://glade.ai/blog/noodle-auto-fill-workflow/ and https://glade.ai/blog/immigration-forms/
- Boundless FAQ: https://www.boundless.com/boundless-faqs
- Boundless layoffs (GeekWire): https://www.geekwire.com/2025/boundless-immigration-cut-staff-days-before-it-announced-acquisition-of-european-competitor/
- Boundless reviews: https://ca.trustpilot.com/review/boundless.com and https://prod.bbb.org/us/wa/seattle/profile/immigration-consultant/boundless-immigration-inc-1296-1000047147/customer-reviews
- CitizenshipWorks: https://www.citizenshipworks.org/en/for-organizations
- Rasa Legal (not immigration): https://www.pulse.bot/venture-capital/news/rasa-legal-lands-5m-seed-round-4742bd08-1ff7-4ee9-9f91-cae34d9b2c52/
- ABA Journal on AI in immigration: https://www.abajournal.com/magazine/article/immigration-attorneys-are-turning-to-ai-to-help-with-an-abundance-of-cases
- Minnesota Lawyer: https://minnlawyer.com/2026/08/31/ai-and-immigration-law-are-forging-a-productive-working-relationship/
- IBISWorld: https://www.ibisworld.com/united-states/industry/immigration-lawyers-attorneys/4808/
- VisaVerge on September 2026 editions: https://www.visaverge.com/news/uscis-to-reject-outdated-form-editions-starting-sept-15-2026/
- ABA Opinion 512 summary: https://zuva.ai/blog/aba-formal-opinion-512/
- On-premises list (Slashdot): https://slashdot.org/software/law-practice-management/on-premise/
- UK visa portal leak: https://securityaffairs.com/192809/security/a-fake-uk-visa-site-left-100000-passports-wide-open-then-sent-lawyers-instead-of-a-fix.html

---

## Correction added 2026-11-11 (after spike 1)

The September 2026 edition dates quoted in section 4 (G1) and elsewhere came from secondary sources and are **unverified**. On 2026-11-11 uscis.gov served I-765 edition 08/21/25 and I-539 edition 08/28/24. See `spike-findings.md`.
