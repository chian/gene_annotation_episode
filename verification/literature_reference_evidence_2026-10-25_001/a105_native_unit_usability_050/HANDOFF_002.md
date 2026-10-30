# Native rate operand information delivered

The existing `literature.rate.source.populate` catalog entry now explains the
actual selected-operand contract: source witnesses use half-open UTF-8 byte
positions, numeric subselectors use Unicode character positions within the
quote, and each defined unit reuses its own arm's endpoint witness exactly.
Contained entity/clause/amount/time relationships and complete-definition
selection are explicit. The supported finite unit-definition grammar appears
once at the schema parent; witness leaves do not repeat full instruction blocks.

The new `literature_native_rate_operand_information.py` adds descriptions to a
fresh copy of the existing schema. C7 changes only its native-rate schema-factory
import/call and the new module's implementation fingerprint. Native reader,
calculator, storage, numerical cells, dispatch, typed return, scientific TASK
constants, renderer, observation accounting and controller remain unchanged.

Root transferred C7 ownership from terminal047 against exact baseline SHA256
`c05828092d992e23055ab53b43258969bcb6b9ed356549cf81e53bb8295d41d5`.
`baseline_002/` retains that full file, all 18 catalog entries and 14 read-only
dependency hashes. `snapshot_002/` retains all three final code files.
`IMPLEMENTATION_002.patch` is the complete code delta from that baseline,
including both new files. Its SHA256 is
`4e9b8a31fc2306e04ccf93f8879f457216a75174c4619d53c21e7684744dca0e`.

Actual bounded verification: **12 targeted tests passed in 0.73s**. They cover
description-stripped validation equivalence, fresh detached builds, coordinate
and source-relationship information, synthetic full-definition success,
correct missing-definition partials, four retained rejection cases, actual
catalog-to-TASK rendering on initial/retry calls and one unchanged C7 native
repository dispatch. The initial fixture/assertion failures and their repairs
are recorded in `TEST_RECEIPT_002.txt`; no hidden broad rerun is claimed.

`DELIVERY_RECEIPT_002.json` proves exactly three allowed C7 substitutions,
unchanged 14 read-only files, all 18 operation names/descriptions, all 17 other
complete catalog entries/schemas, and unchanged native validation content after
stripping descriptions from both schemas. The current first 17 schemas therefore
intentionally differ from047's snapshot in this native-rate description overlay;
047's immutable006 snapshot remains the authority for its own earlier proof.

The code patch was actually applied in a fresh owned reconstruction directory;
all three reconstructed code hashes match the final snapshot. `MANIFEST_002.json`
records the delivered artifacts, baseline, patch, tests and immutable snapshots.

This implements operand explanations, not a scientific parser correction.
Synthetic examples show the existing finite parser can succeed and preserves
unsupported plain U/mg as unknown; they do not prove the causes of old model
failures. No source paper, source-specific scientific selection, private history,
run database or live pin was opened or changed. Successful actual model-backed
numerical evidence, broader A105 completion and paper-to-component selection
remain separate unfinished work. No routing implementation or new sheet was added.
