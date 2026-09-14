# Personal tasting notes and optional guidance

Research date: September 13, 2026. Status: product/UX discussion draft. The user wants both free-form notes and guided suggestions, particularly for people new to wine. Basic guidance is now part of MVP direction (TJ-07); exact prompts and controls remain proposals.

## Research findings

WSET's tasting education separates observations about appearance, aroma, palate, and overall assessment. Its public article describes moving from broad impressions toward more specific language, and distinguishes aroma from texture and structure. The useful product lesson is to offer a path through observations without demanding specialist vocabulary. [WSET: How to train your palate](https://www.wsetglobal.com/knowledge-centre/blog/2026/how-to-train-your-palate)

WSET also explains acidity through the mouth-watering sensation and tannin through a drying sensation. These provide useful concrete explanations for unfamiliar terms. They are sensory observations, not measures of how much the user likes a wine. [WSET: Wine tasting information](https://www.wsetglobal.com/knowledge-centre/blog/2019/november/how-to-build-your-wine-tasting-skills)

The Wine Aroma Wheel's publisher teaches a broad-to-specific progression: first an aroma family, then a narrower category, then a familiar reference if the taster can identify one. Its guidance allows broad descriptions and terms beyond those on the wheel. This supports optional suggestions with custom input. [Wine Aroma Wheel: How to use it](https://www.winearomawheel.com/how-to-use-the-wine-aroma-wheel.html)

These sources inform our original prompts. They do not validate our exact interface or establish that every suggested field belongs in the first release. We are not reproducing their complete charts, assessment forms, or branded visual designs.

## Recommended MVP experience

Free-form notes are always available on a drinking entry, whether standalone or linked to an occasion. Beside them, offer an optional **Help me describe it** control. Opening it reveals a small amount of guidance at a time; the user can skip any prompt, use broad terms, or write their own description. Saving still requires only wine identity and consumed date.

| Prompt area | Proposed original prompt | Optional support |
| --- | --- | --- |
| First impression | What stood out about this wine? | Open text; useful even when entered days later |
| Aroma and flavour | What familiar smells or flavours did it bring to mind? | Start with a few broad categories; allow more specific examples and custom words |
| Feel | How did it feel in your mouth? | Short explanations of body, acidity, and tannin; reveal only the topic the user chooses |
| Enjoyment | What did you enjoy, or what would you change? | Open text; optional return to the wine's existing rating control |

Candidate help text to review:

- **Body:** the sense of weight or fullness in the mouth.
- **Acidity:** notice how much it makes your mouth water.
- **Tannin:** notice a drying or gripping feeling on the gums.

The first two prompts and concise term explanations are a reasonable starting set. Appearance, finish, sweetness, food context, and more detailed attribute controls can be evaluated without making a complete tasting form mandatory. Final prompt wording and selection need a low-fidelity walkthrough.

## Product rules

- Free-form notes and optional guided observations belong to the selected drinking entry. An occasion is optional; general dinner memories can belong to the occasion when one exists.
- Recording another encounter with the same release starts with that entry's own observations; do not copy prior notes as if newly perceived.
- The wine's current personal rating/history stays independent. Completing guided notes does not calculate a score or create another rating revision.
- Guidance helps the user express an observation. Examples are not assertions about this particular bottle, and none are selected automatically.
- Producer tasting descriptions stay visibly sourced wine information. Do not insert them into personal notes or treat agreement with them as a correctness test.
- Keep custom words and broad categories valid. Unanswered means unrecorded, not a low score or absence of a sensation. Users can remove a previously chosen descriptor.
- Opening/closing guidance must not erase existing free text. Any action that inserts wording should be user initiated and editable.
- Notes and descriptions remain private. Their contribution to a future taste profile requires separately defined aggregation rules; noticing an aroma alone does not mean liking it.
- Guidance can use a small curated set of prompts and definitions. An AI service is not a prerequisite for this MVP capability.

## Journey E: Add notes with optional help

Stories: TJ-01, TJ-03, TJ-07, TP-04, HB-02, HB-05.

1. Open a wine's history and select the relevant drinking entry, or open an optional occasion scrapbook and choose a linked entry.
2. See the selected wine/release and date while writing personal notes.
3. Optionally open Help me describe it. Start with an impression; explore vocabulary or a term explanation if useful.
4. Save any amount of writing or selected observations. Notes appear in My Wines and, when the entry is linked, its occasion scrapbook. Linking an entry later does not duplicate its notes.
5. If the user wants to change their current opinion of that release, offer a clearly separate rating update. Keep the previous score in its rating history.

Example: a dinner contains Barrel Selection 2023 and Sonoma County Reserve 2023. The user records different impressions for each wine. A general note about the birthday dinner and its photo album stays on the shared occasion. Updating one wine's rating later does not rewrite either set of dinner notes.

## Acceptance examples

1. A user can save only wine/date, later add free text, and never open guidance.
2. A beginner can open guidance, choose a broad description or write a custom one, skip unfamiliar terms, and save without completing a checklist.
3. Existing notes survive opening/closing guidance, and revisiting the saved entry shows the user's chosen content even without an occasion.
4. In a multi-wine occasion, guidance applies to the selected wine and leaves other wines' notes unchanged.
5. A skipped attribute is unrecorded. Suggested words are not stored as the user's observations unless chosen.
6. Guided observations neither update the catalog's producer description nor change the user's current rating automatically.
7. Later shared occasion notes are separate contributions; inviting participants does not expose or grant editing rights over a person's private entry notes or current wine rating.

## Scope and next UX decisions

**MVP target:** free-form writing, optional beginner prompts/suggestions, and short terminology help. **Proposals to test:** collapsible guidance, selectable descriptors, custom vocabulary, and whether prompted answers sit beside notes or are explicitly inserted into them. Guidance can be useful without implementing every proposed control.

**Later:** detailed sensory scales, full structured assessment, side-by-side comparisons, deeper learning content, and analysis of changing observations. These remain TP-03; optional beginner help has moved into TJ-07.

The walkthrough covers both a person who wants to write one sentence and a person who opens optional prompts. The user also requested a standalone Guides section for styles, notes, pairings, and regions. [UX review 02](ux-review-02.md) proposes a small curated set alongside in-entry help, with deeper and personalized learning later. Reading a guide is not evidence that the user liked or drank a wine. Guide breadth remains a scope decision.
