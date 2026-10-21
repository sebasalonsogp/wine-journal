# C05a — Barcode number lookup and vintage confirmation

Browse Wines now includes a collapsible **Look up a barcode** panel. Guests enter
the printed number, inspect the offering and its sourced bottle sizes, choose the
vintage/edition on their label, and confirm before opening public wine details.
Even a single release requires an explicit choice. Viewing never logs a drink;
the existing **I tried this wine** flow handles draft recovery, sign-in and saving.

This is a bounded first browser slice of C05, using the curated C04 API. Camera
capture, image decoding and physical iPhone verification remain separate. The
small reviewed barcode dataset is not universal wine identification. C04/C05 and
their broader coverage gates remain open; the parent task count is unchanged.

## Behavior and boundaries

- No match, too many matches, missing years and absent release options offer
  name search and manual capture. No release is inferred from a barcode.
- Invalid input, unavailable service and exhausted budgets have recovery copy.
  Retry-After delays submissions; there is no automatic retry. A 409 invalidates
  the displayed candidates and requires another lookup.
- Changing the number or repeating lookup clears selection. Closing the panel or
  leaving aborts pending requests; late responses cannot replace current state.
- Browser requests use the server-validated public API origin, omit credentials,
  disable caching and redirects, and have a ten-second deadline. Codes stay in
  POST bodies and component memory, never in URLs or persistent storage. No new
  environment variable, credential, dependency or database migration is needed.
- Lookup does not read or modify capture drafts. Manual fallback retains existing
  unfinished notes. Confirmation sends the exact selected release ID, vintage
  status, year and edition for server revalidation.
- The existing cream/burgundy design, typography, native controls and keyboard
  focus treatment are retained. Barcode provenance remains available in an
  expandable reference list.

## Verification

The new browser regression first failed against the old production build because
the barcode panel was absent. API-client tests cover credential omission, exact
confirmation fields, sanitized failures and no automatic retries. Four browser
journeys cover real curated lookup/confirmation, explicit saving after sign-in,
invalid/unknown codes, changed selection, single-match confirmation, throttling,
overflow, aborted requests, network failure and manual draft preservation.

Fault responses and the single-release case use deterministic browser fixtures;
they do not establish provider coverage. The happy path uses the actual local API
and reviewed Seven Oaks evidence. CI seeds the five reviewed barcode observations
from `assets/catalog/barcode-evidence.json` after catalog identities. Accessibility and width checks cover the
expanded panel, with screenshot inspection at desktop and mobile sizes.

Local closeout: all 39 frontend unit tests and all 38 browser journeys pass;
lint, type checks, formatting and the production build pass. The npm audit finds
zero vulnerabilities; staged Gitleaks and generated-browser-credential scans pass.
The first broad browser run found four photo publication timeouts. Restarting the
long-running local worker restored processing; the complete rerun passed without
photo code changes or weakened assertions. Remote CI remains the integration gate.

The first remote run rejected the CI seed input: it pointed at evaluation
observations rather than the curator import manifest. The workflow now uses the
existing validated catalog evidence file; the application contract is unchanged.

Shared ingress quotas, broader catalog evidence, physical-device scanning and
label recognition retain their existing roadmap gates. This change does not
activate a camera, call an external recognition provider or claim those tasks done.
