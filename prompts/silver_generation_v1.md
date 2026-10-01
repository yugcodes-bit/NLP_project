# Silver data generation prompt — v1 (AUG-4, rare classes)
Output is SILVER: flag `label_source: silver`. Filter by teacher agreement, dedupe vs gold, toxicity/PII
filter, and human-audit 200 items (report precision). Never mix silver into val or gold.

---
Write {N} short, realistic messages in Hinglish (Hindi-English code-mixed, mostly Roman script, informal,
like WhatsApp or Instagram comments by young Indians) in which the writer clearly expresses **{EMOTION}**
with intensity **{INTENSITY}** (1 = mild, 3 = strong).

Requirements:
- Vary topics: {TOPICS} (e.g. college, family, cricket, food, travel, jobs, movies, traffic, festivals, relationships).
- Vary spelling naturally (bahut/bohot, nahi/nhi), length (4–30 words), and include emoji in about half.
- About 10% may contain a few Devanagari words.
- No real names of public figures, no slurs, no personal data, no self-harm content.
- Do not use the word "{EMOTION}" or its direct Hindi translation in more than 20% of messages.

Return a JSON list of strings only.
