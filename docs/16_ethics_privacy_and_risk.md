# 16 — Ethics, Privacy & Risk

Emotion technology reads something personal. Bhaav is designed so that the easiest way to use it is
also the safest way.

---

## 1. Principles
1. **Data minimisation** — we don't keep what we don't need. No text storage by default.
2. **On-device first for personal data** — chat analysis defaults to Privacy Mode.
3. **Honesty about uncertainty** — calibrated confidence, "unsure" state, visible limitations.
4. **No judgements about people** — we describe emotions *in text*, never traits, diagnoses or risk scores of persons.
5. **Consent** — for chat uploads, feedback, and any collected research data.

## 2. Privacy design
| Data | Where it goes | Stored? |
|---|---|---|
| Text in Server mode | Cloud Run memory for the request | No (logs redacted; cache keyed by hash, in-memory, evicted) |
| Text in Privacy mode | Browser only | No |
| Chat exports | Parsed in browser | No |
| Batch CSV | Browser; batches sent to API in Server mode | No |
| Feedback (later) | Supabase, only with explicit consent tick | Yes, with deletion on request |
| Analytics | None in v1 (or cookieless aggregate page views only) | — |

Privacy notice page in plain language (English + Hinglish). Under India's **Digital Personal Data
Protection Act, 2023** (DPDP), avoiding storage keeps obligations minimal; if feedback storage is
enabled, add notice, purpose, consent and deletion flows **[have a knowledgeable person review before enabling]**.

## 3. Misuse scenarios & mitigations
| Scenario | Mitigation |
|---|---|
| Analysing someone else's private chat to "expose" them | Consent modal; pseudonymised outputs; no server upload; neutral wording (no "toxic person" labels) |
| Employer/school surveillance of staff/students | Terms of use prohibit; API rate limits; no bulk monitoring features; docs state unsuitable |
| Mental-health screening / diagnosis | Prominent disclaimer; no "depression/risk score"; wellbeing card points to professionals |
| Political profiling / targeting | Out of scope; no social-media ingestion; ToU prohibits |
| Over-trust in outputs | Calibration, unsure state, explanation, limitations on every result page footer |
| Harmful/abusive inputs | We still return emotions; no content echoed into shareable cards by default |

## 4. Wellbeing card (FR-25)
Trigger: (sadness or fear intensity ≥ 2) **and** a match in a small curated phrase list indicating
self-harm or crisis (Hinglish/Hindi/English, e.g. variants of "marna chahta hu", "jeene ka mann nahi",
"khatam kar dunga khud ko", "want to die") — list maintained in `configs/wellbeing_terms.yaml`,
reviewed by a human, matched on normalised text.
Card copy (no alarm, no diagnosis):
> "It sounds like things might be really heavy right now. You don't have to deal with it alone.
> In India you can talk to **Tele-MANAS** for free, 24×7: **14416** or **1-800-891-4416**.
> If you're in immediate danger, call **112**."
**[Verify numbers on the official Tele-MANAS / MoHFW site before launch.]**
The match is computed but **never logged or returned** beyond `wellbeing.show`. In Privacy Mode the
same logic runs locally.

## 5. Bias & fairness checks (paper + model card)
- Report performance by script, CMI bucket, and (where gold metadata allows) source register.
- **Template probe**: 200 templated sentences varying only names/places/religious or regional terms
  ("<NAME> aaj ghar aaya") → check emotion predictions don't shift systematically (expected: neutral).
  Report max mean-shift; mitigate with counterfactual augmentation if large.
- Note dialect coverage gaps (Bhojpuri/Haryanvi-flavoured Hinglish, Hinglish from South India).

## 6. Annotator welfare
Content warning before sessions; right to skip any item; batches ≤ 100 items; offensive items
pre-flagged; fair compensation/credit (acknowledgements or co-authorship as agreed); annotators
never see usernames.

## 7. Research data ethics
- Use datasets per their licenses; cite; release only what's allowed.
- If the institution has an ethics/IRB process for collecting donated messages, follow it **before** Phase 2 collection (👤 human to check).
- Exclude the mental-health counselling dataset (`healer26`) from v1 training due to sensitivity.

## 8. Security
OWASP basics: input validation, size limits, rate limits, dependency scanning, CSP, no secrets in
repo, least-privilege deploy identity, non-root container. No user accounts → no password risk.

## 9. Terms of use (summary for the site)
Free for personal, educational and research use; no use for surveillance, profiling, employment,
credit, insurance, legal or medical decisions; outputs may be wrong; no warranty.
