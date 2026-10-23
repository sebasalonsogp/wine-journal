# L01 — Optional tasting guidance, October 23

The existing free-form notes now offer a collapsed **Help me describe it**
disclosure in quick/repeat capture, saved-entry editing and the occasion wine
composer. Three original questions help users recall familiar smells/flavors,
mouthfeel and the experience. A second disclosure explains body, acidity and
tannin. Users can skip everything and save only the wine and date.

## Design and data boundary

This is a small addition to the existing burgundy/olive/cream form design.
Native details/summary controls provide keyboard operation and expose expanded
state without a custom state machine. Guidance is placed immediately after the
notes field; terminology remains hidden until requested. Shared styling is scoped
to the component rather than expanding the global stylesheet.

The component accepts no props, reads no catalog or account data, and has no
storage, network or write handlers. Only text the user writes enters the existing
notes payload. Opening guidance cannot change notes, producer descriptions or
wine-level ratings. There are no selectable descriptors, generated observations,
new fields, migrations, dependencies, credentials or services in this slice.
Detailed sensory scales and profile inference remain separate work.

Original copy follows the product rules in [tasting research](tasting-notes.md).
The source guidance was rechecked October 23:
[WSET tasting information](https://www.wsetglobal.com/knowledge-centre/blog/2019/november/how-to-build-your-wine-tasting-skills)
supports distinguishing mouth-watering acidity from drying tannins; the
[Wine Aroma Wheel publisher's explanation](https://www.winearomawheel.com/how-to-use-the-wine-aroma-wheel.html)
supports broad familiar impressions without requiring a precise descriptor.
No chart, assessment form or source's full vocabulary is reproduced.

## Verification

The new minimal-save browser test first failed on the absent disclosure. With
the implementation, both new journeys and the extended multi-wine occasion
journey pass against real local authentication/API/database services:

- Enter/Space opens and closes the disclosure; prompts start hidden.
- Blank notes stay blank, including after exploring terminology and saving.
- Guest free text survives guidance toggles, sign-in and saving.
- Saved notes can be enriched and reloaded without changing the existing rating
  or adding a rating revision.
- Three different staged wines retain their own notes; help inserts no content.
  The existing occasion journey also exercises repeat entries and lost-save retry.
- Expanded guidance passes axe WCAG A/AA checks. Inspected 320px and 1440px captures
  show readable wrapping without horizontal overflow. This is browser/keyboard
  evidence, not a physical-iPhone or assistive-technology user test.

All 47 frontend unit tests, lint and the production build/type checking pass.
The Impeccable detector reports no findings. Exact-head CI and review remain the
merge gates. Full Guides content and the taste-profile summary remain L02/L03.
