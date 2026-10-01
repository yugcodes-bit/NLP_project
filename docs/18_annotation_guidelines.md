# 18 — Annotation Guidelines (Gold Test Set) — v0.1 draft

For annotators fluent in Hindi and English. Expect ~4–6 s per easy item, ~20 s for hard ones.
Claude Code: expand §6 to 30 worked examples before the pilot; human reviews them.

---

## 1. Task
For each text, decide **which emotions the writer is expressing** (one or more, or Neutral), and
for each chosen emotion, **how strongly** (1 low · 2 moderate · 3 high).

Judge the **writer's expressed emotion**, not:
- how *you* feel reading it, or
- emotions of people mentioned ("Rahul bahut gusse mein tha" → the writer may just be reporting → often Neutral or mild Surprise, unless the writer shows feeling).

## 2. Labels
Anger · Disgust · Fear · Joy · Sadness · Surprise · Neutral — definitions and cue words in `12` §1.

## 3. Rules
1. Choose **all** emotions clearly present. Don't add weak guesses — if unsure about a label, leave it out.
2. **Neutral** only if no emotion is present. Never combine Neutral with others.
3. **Emoji count**: 😂 usually joy (or amusement → joy); 😭 can be joy ("😭❤️ finally!") or sadness — use context.
4. **Sarcasm/irony**: label the **intended** emotion ("wah kya service hai 🙂 3 ghante se wait" → Anger) and tick the **sarcasm** flag.
5. **Questions** ("kal exam hai kya?") are usually Neutral unless emotional cues exist ("kal exam hai kya?? 😰" → Fear).
6. **Intensity cues**: intensifiers (bahut, bohot, ekdum, bilkul, itna), repetition, CAPS, multiple !!!/emoji → higher; hedges (thoda, shayad, lagta hai) → lower.
7. **Love/affection** → Joy. **Pride** → Joy. **Disappointment** → Sadness (+Anger if blaming). **Worry/tension** → Fear. **Contempt/"ghatiya"** → Disgust (+Anger if hostile).
8. Profanity alone doesn't decide the label ("bc kya mast movie thi" → Joy).
9. If the text is not Hindi/English/Hinglish, or is unreadable → tick **skip: invalid**.
10. Flags (tick if applicable): sarcasm · needs context · offensive · contains PII (we'll scrub).

## 4. Interface fields
`labels[]` (multi-select) · `intensity{label: 1–3}` · `flags[]` · `confidence` (1–3, annotator's own certainty) · `comment` (optional).

## 5. Process
- Pilot 100 items × 3 annotators → discuss disagreements → update this doc (bump version) → main round.
- Batches of 100; take breaks; skip anything distressing.
- Do not discuss specific items with other annotators during the main round.
- Disagreements → third annotator adjudicates; persistent ambiguity → item marked `ambiguous` (kept for analysis, excluded from headline metric — report count).

## 6. Worked examples (to be expanded to 30)
| Text | Labels (intensity) | Why |
|---|---|---|
| yaar aaj ka din bahut bekaar tha 😩 | Sadness (3) | "bahut bekaar" + 😩; no blame → no anger |
| bhai result dekh ke dimaag kharab ho gaya, teachers ne galat check kiya | Anger (3), Sadness (1) | blame → anger; disappointment |
| kal interview hai, thodi tension ho rahi hai | Fear (1) | "thodi" lowers intensity |
| mummy ne finally haan bol diya 😭❤️ | Joy (3) | 😭 here = happy tears |
| wah kya service hai 🙂 3 ghante se wait kar raha hu | Anger (2) + sarcasm flag | ironic praise |
| ye khana dekh ke ulti aa gayi, ghatiya | Disgust (3) | |
| kya!! tu Canada ja raha hai?? | Surprise (2) | |
| meeting 5 baje shift ho gayi hai | Neutral | information |
| सच में बहुत खुश हूँ आज | Joy (3) | Devanagari is fine |
| Rahul bol raha tha ki wo gussa hai | Neutral | reporting someone else |
