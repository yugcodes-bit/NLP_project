# 13 — UI / UX Specification

Design goals: **instant, friendly, trustworthy, Indian.** Feels like a polished consumer app, not a
research demo. Mobile-first (most users arrive from WhatsApp/Instagram links on phones).

---

## 1. Brand & visual system
- Name: **Bhaav** · tagline: *"Feel the Hinglish."* / *"Aapke words, aapke emotions."*
- Logo idea: Devanagari **भा** inside a speech bubble.
- Type: **Inter** (UI) + **Noto Sans Devanagari** (Devanagari text), both via `next/font` (self-hosted).
- Colour tokens (CSS variables; light + dark):
  | Emotion | Token | Light | Dark |
  |---|---|---|---|
  | joy | `--emo-joy` | amber-500 | amber-400 |
  | sadness | `--emo-sadness` | blue-500 | blue-400 |
  | anger | `--emo-anger` | red-500 | red-400 |
  | fear | `--emo-fear` | violet-500 | violet-400 |
  | disgust | `--emo-disgust` | lime-600 | lime-500 |
  | surprise | `--emo-surprise` | pink-500 | pink-400 |
  | neutral | `--emo-neutral` | slate-400 | slate-500 |
  Colour is **never** the only carrier: every bar has a text label, percentage, and an emoji icon.
- Language tags in Code-Mix Lens: `hi` = saffron underline, `en` = teal underline, `univ` = grey, `ne` = dotted. Also shown as tiny superscript tags for accessibility.
- Motion: subtle (bars animate 200 ms); respects `prefers-reduced-motion`.

## 2. Information architecture
```
/            Analyse (home)         ← primary
/chat        Chat timeline
/batch       CSV batch
/playground  Robustness playground
/compare     Model comparison
/about       How it works · model card · data · limitations · cite
/api         API docs & snippets
```
Top nav (desktop) / bottom tab bar (mobile: Analyse · Chat · More). Footer: disclaimer, privacy, GitHub, paper.

## 3. Pages

### 3.1 Analyse (home)
```
┌───────────────────────────────────────────────┐
│ Bhaav  भाव                 [Server ⇄ Private] │
│ "Feel the Hinglish."                          │
│ ┌───────────────────────────────────────────┐ │
│ │ Type in Hinglish, Hindi or English…       │ │
│ │ e.g. "yaar aaj bahut bekaar din tha 😩"   │ │
│ └───────────────────────────────────────────┘ │
│ [Try an example ▾]   312/1000      [Analyse →]│
├───────────────────────────────────────────────┤
│ 😢 Sadness   ███████████░░  82%  ●●●○ high    │
│ 😠 Anger     ████░░░░░░░░░  31%  ●○○○ low     │
│ (others hidden — show all ▾)                  │
│                                               │
│ Code-mix lens   CMI 46 · 58% hi · 42% en       │
│ yaar  aaj  bahut  bekaar  din  tha  😩         │
│  hi    hi    hi     hi     hi   hi  univ      │
│ [Why? ✓]  highlighted: "bekaar"(+), "😩"(+)    │
│                                               │
│ Confidence: calibrated 0.82 · model v1.2 · 94ms│
└───────────────────────────────────────────────┘
```
States: **empty** (examples chips), **loading** (skeleton; after 1.5 s "Waking up the model… ☕ first
request can take ~10 s"), **result**, **unsure** (UnsureCard: "Hmm, Bhaav isn't sure 🤔 — maybe
*fear* or *surprise*?"), **error** (retry + "Switch to Private mode"), **wellbeing** card above results when triggered.
Keyboard: Ctrl/Cmd+Enter submits. Input auto-detects script and shows a tiny badge (Roman/देवनागरी/Mixed).

### 3.2 Chat timeline
1. Drop zone: "Drop your WhatsApp chat export (.txt or .zip)". Link: "How to export a chat" (Android/iOS steps).
2. **Consent modal** (must tick): "I'm part of this chat and I'll only use this for personal insight.
   Messages are analysed on your device in Private mode and never stored."
3. Parse summary: participants (auto-pseudonymised A, B, C — toggle to show real names locally), date range, message count.
4. Timeline chart: x = time (auto bucket: hour/day/week), y = share of each emotion, one line set per person (person selector chips). ⚡ markers at emotion shifts; hovering shows the window's top messages (only locally).
5. Cards: "Most joyful day", "Person A's top emotion", "Biggest mood shift" (fun but neutral phrasing; no judgemental labels).
6. Export: PNG of chart (names pseudonymised). No server upload.
Limits: ≤ 5,000 messages (sample evenly above that, with notice).

### 3.3 Batch CSV
Upload → preview first 5 rows → pick text column → run (progress bar, cancel) → results table
(sortable, filter by emotion, unsure flag) → distribution donut + top words per emotion (simple
counts) → download CSV. Default mode: Server (faster); Private mode available.

### 3.4 Robustness playground
Input → "Generate variants" → grid of cards: Original · Spelling variants · देवनागरी · Mixed script ·
No emoji · Typos → each with mini emotion bars + "same/different" badge → Stability score (e.g. 5/6 stable).
Explainer: "Hinglish has no fixed spelling — good models shouldn't care."

### 3.5 Compare
Table + bar chart of macro-F1 with CI whiskers for all models; toggles for metric (F1/ECE/latency/size);
note on test set; link to paper. Data from `public/compare.json` (generated).

### 3.6 About / model card
How it works (diagram), labels & definitions, data sources & licenses, metrics (gold), limitations,
intended/unintended uses, privacy, team, citation BibTeX (copy button), changelog.

### 3.7 API page
Endpoint table, curl / Python / JS snippets, rate limits, response example, link to OpenAPI `/docs`.

## 4. Components (shadcn/ui based)
`EmotionBars` · `IntensityDots` · `UnsureCard` · `WellbeingCard` · `CodeMixLens` · `ScriptBadge` ·
`ModeToggle` (Server/Private with tooltip + download size) · `ModelLoadProgress` · `ExampleChips` ·
`ChatDropzone` · `ConsentDialog` · `EmotionTimeline` (Recharts) · `ShiftMarker` · `VariantGrid` ·
`CompareChart` · `CopyButton` · `Disclaimer`.

## 5. Microcopy (bilingual flavour)
| Context | Copy |
|---|---|
| Placeholder | "Kuch bhi likho… Hinglish, Hindi ya English" |
| Button | "Analyse" / loading "Samajh raha hoon…" |
| Unsure | "Hmm, Bhaav pakka nahi hai 🤔" |
| Private mode on | "Private mode: text never leaves your phone 🔒" |
| Cold start | "Model so raha tha, utha rahe hain… ☕" |
| Disclaimer | "Bhaav guesses emotions from text. It can be wrong, and it is not a medical or psychological tool." |
Tone: warm, light, never mocking the user's feelings; never jokey on sad/fear results.

## 6. Accessibility
WCAG 2.1 AA: contrast ≥ 4.5:1; focus rings; all charts have a data-table alternative ("View as table");
ARIA live region announces results; `lang="hi"` spans on Devanagari text; touch targets ≥ 44 px.

## 7. Performance budget
Initial JS ≤ 200 KB gz; route-level code splitting (Recharts only on chat/batch/compare);
Transformers.js loaded only when Private mode toggled; fonts subset; no third-party trackers.
