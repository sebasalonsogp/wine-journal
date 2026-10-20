# Reviewed barcode seed

`barcode-evidence.json` is an explicit curator-approved import batch, separate
from provider outputs and recognition measurements. It contains five source
observations for four retail codes and four existing catalog offerings.

- Two Seven Oaks web listings associate the same code with the offering across
  different vintages. They retain separate URLs; neither supplies an exclusive
  barcode-to-vintage mapping.
- Three Ridge codes were read from the original producer images before the
  decoder/provider experiments. Their hashes refer to the original source bytes.
- The [source review](../../tasks/barcode-coverage-checkpoint.md) and
  [initial observations](../evaluation/barcode-observations.json) supply provenance.
  Evaluation fixture IDs, observed years and provider guesses are deliberately
  absent from this operational import format.

Use the [catalog operator commands](../../apps/api/src/wine_journal/catalog/README.md#reviewed-barcode-evidence-c04a).
There is no automatic import on server start or ingestion from public submissions.
Changing this file is a new curatorial decision; a conflicting source is rejected
by the importer and cannot silently replace existing evidence.
