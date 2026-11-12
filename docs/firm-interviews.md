# Firm interviews: plan, script and pitch

Written 2026-11-06. Companion to `market-gaps.md`. Firms only; students and consumers are parked.

## 1. What we are trying to learn

The research gives us hypotheses, not facts. The interviews exist to confirm or kill them.

| # | Hypothesis | Where it came from | What would count as a signal |
|---|---|---|---|
| H1 | Form edition changes cause real, costly mistakes and anxiety | VisaVerge on the September 2026 editions; one DocketWise reviewer saw a one-month lag | The firm describes a specific rejected or near-missed filing from a stale edition, or a manual edition check they do on every filing |
| H2 | Re-typing client data (into forms and into the USCIS portal) is a major time sink | Two Capterra reviews; Docketwise calls manual entry a bottleneck | They can say roughly how many minutes per filing, and who does it |
| H3 | Inconsistent data between documents (names, dates, passport numbers) causes rework or RFEs | ABA Journal lists inconsistency detection as an AI use; the passport-first idea | They recall a concrete case, and describe how they catch it today |
| H4 | Confidentiality of client documents limits their use of cloud AI tools | ABA Opinion 512; 2021 Mitratech survey; only 8% have an AI policy (vendor figure) | They say they avoid or restrict putting passports into AI tools, or they have been asked by clients |
| H5 | A "proof of how this filing was prepared" document is valuable | My idea. Nothing in the research confirms demand | They would use it for RFEs, malpractice defense or client trust, without being prompted |
| H6 | They will not replace their case-management system, so we must fit beside it | Reviews show firms pair general and dedicated tools | They name a system they will not leave, and what they would need to import or export |
| H7 | They would pay, and the unit matters (per seat, per filing, per firm) | Incumbents charge about $59-$129 per user per month | A number they would pay without flinching, and who signs off |

**Decision rule (set before we start):** proceed if at least 6 of 10 firms (a) describe a concrete preventable error or recurring rework from H1, H2 or H3 in the last year, and (b) agree to trial a prototype. If fewer than 4 do, rethink the wedge. Between 4 and 6, change the focus to whichever hypothesis got the strongest reaction.

## 2. Who to talk to (8 to 10 people)

Do not interview only friendly contacts. Aim for this spread:

- 3 solo or 2-5 person firms doing mostly family-based cases
- 2 employment-based boutiques
- 2 paralegals or case managers (they do the typing; the attorney buys the software)
- 1 firm using LollyLaw, 1 using INSZoom, 2-3 using DocketWise, 1-2 using general tools plus Adobe
- If possible 1 firm that switched away from a tool, and why

Recruiting channels (suggestions, not verified for response rates): local AILA chapter contacts, state bar immigration sections, LinkedIn searches for small immigration firms, legal-tech communities, referrals at the end of each interview. Offer something useful in return: a short anonymized summary of what other firms said.

## 3. Rules for every conversation

- You are not selling. You are learning how they work now.
- Ask about the **last time** something happened, not what they would do.
- Never ask for client names or documents. Ask them to describe a case in general terms. If they offer to share a screen, ask them to use a dummy case.
- Ask permission before taking notes or recording. Do not give legal advice.
- Do not describe your idea until the "concept" section, or you will get polite answers.
- Do not mention competitor prices before asking what they pay.

## 4. The 30-minute script

**Opening (2 min).** "Thanks for your time. I'm researching how immigration firms prepare USCIS forms, because I'm thinking about building tools for it. I'm not selling anything, and I don't need any client details. Is it okay if I take notes?"

**Context (3 min)**
1. What kind of cases do you mostly handle, and how many filings go out in a typical month?
2. Who works on them: attorneys, paralegals, others?
3. What software do you use from intake to filing?

**Walk me through the last one (10 min).** Pick the most recent I-130, I-485, I-765 or similar, in general terms.
4. Where did the information come from, and how did it get into the forms?
5. Who typed what, and about how long did that take?
6. Who reviewed it, and what did they check?
7. Was there anything you had to fix before filing? What was it?
8. How did you pick the right form edition? Did you check anywhere?
9. Did you re-enter anything into the USCIS online portal?

**Mistakes and near misses (5 min)**
10. Tell me about the last time a filing was rejected, returned or got an RFE because of something preventable.
11. What was the cause, and what did it cost you (time, money, client trust)?
12. What changed afterwards?
13. How do you catch names or dates that differ between a passport and other documents?
14. How do you keep up with new form editions or fee changes?

**Tools and AI (4 min)**
15. What do you like about your current software, and what annoys you?
16. Have you tried AI for anything with client documents? How did it go?
17. Does your firm have a rule about putting client documents into AI or cloud tools? What worries you?

**Concept (4 min).** Read the pitch in section 6 aloud, then:
18. What is your first reaction?
19. What would you need to see before you would trust it with a real filing?
20. What would make you stop using it?
21. How would it have to fit with the software you already use?
22. Which part of this would you actually use, and which would you ignore?

**Money (2 min)**
23. What do you pay per month for software today, and who decides on new tools?
24. If a tool like this saved real time, how would you expect to pay: per user, per filing, per firm?
25. At what price would you say "too expensive"? At what price would you doubt it works?

**Close (1 min).** "Who else should I talk to? May I follow up when I have something to show?"

## 5. Reading the answers

| Strong signal | Weak signal (do not count) |
|---|---|
| A specific rejection, RFE or rework story with a cost | "That would be nice to have" |
| They already built a workaround (a checklist, a spreadsheet) | "AI is the future" |
| They ask when they can try it | They compliment the idea and change the subject |
| They name a number they would pay | "Depends" with no number |
| They volunteer a confidentiality rule | They agree confidentiality matters in general |

Record each interview in a row: firm size, tools, minutes per filing, top pain, edition incidents, confidentiality stance, price, who buys, best quote, and which hypotheses it supports or kills.

## 6. The concept pitch (read aloud, about 45 seconds)

"Imagine you drop a client's passport and I-94 into a tool on your computer. It reads them, fills the form, and checks the documents against each other, so a name spelled differently or a day and month swapped gets flagged with a plain explanation of what to check. It refuses to fill an out-of-date form edition. When you finish, it produces a one-page report showing where every field came from, what was checked and who reviewed it. Your files stay on your machine. It doesn't replace your case-management software; it sits in front of it."

This is a concept, not a product. Say so.

## 7. Outreach message (adapt, keep it short)

> Subject: 25 minutes on how you prepare USCIS forms?
>
> Hi [name], I'm researching how small immigration firms prepare and check USCIS forms, with a view to building something useful. I'm not selling anything and I don't need any client information. Could I ask you a few questions about your workflow for 25 minutes? I'll share an anonymized summary of what other firms tell me. [Your name, one line on who you are.]

## 8. Competitor bake-off (do alongside the interviews)

Free trials exist: DocketWise lists a 7-day trial and LollyLaw reports 7 or 14 days depending on source. Use them to replace opinion with observation. Use **synthetic data only** and check each product's terms.

For the same synthetic case in each tool, record:
- Minutes from blank to a filled draft.
- Which documents it reads automatically, and which fields it filled.
- What happens when you enter a day/month-swapped birth date, a one-letter surname typo, a middle name left off, and a stale form edition.
- Whether it tells you where each value came from.
- Whether it can export the data in a form another system could import.

## 9. Timeline

- Days 1-3: write the outreach list and send 25 to 30 messages (expect many to go unanswered).
- Days 4-12: run interviews and the bake-off.
- Days 13-14: fill the synthesis table, apply the decision rule, and write a one-page summary of what changed in our assumptions.
