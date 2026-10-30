# A105 structural scalar context repair — workload 157

This is an implementation and synthetic verification record, not goal authority.
The original user-supplied goal remains authoritative. W04 responsibilities and
scientific scoring meanings are unchanged.

## Reproduced defect

Selecting the exact `7` in the synthetic source
`<table><tr><td>Partner</td><td>7</td></tr></table>` failed with
`partial_source_numeric_token`. The old edge-tag removal joined the visible
`Partner` label to `7`. Two adjacent numerical cells were likewise joined.
`synthetic_before_after.json` records independent executions of the prechange
reader from the root's immutable code pin and the changed reader. These are
synthetic source bytes only. No original paper or retained paper packet was read
for this workload.

## Exact ownership and changes

Only `gene_annotation_episode/literature_partner_source_fields.py` changes
production behavior. The new targeted test file is
`tests/test_literature_structural_scalar_contexts.py`. Full old/new hashes and
the exact unified production diff are retained beside this record.

- `_raw_contexts` preserves the original source-byte-to-Unicode position logic.
- `_edge_contexts` changes only edge tag runs. Actual structural table, block,
  paragraph and break tags contribute a space. Inline tags contribute no text.
  Original source whitespace is preserved. Tags are recognized before entity
  decoding, preserving encoded comparison markers and exact source witnesses.
- `_contexts` retains surrounding qualifier information rather than truncating
  it at a paragraph or line break. A manufactured newline would hide some
  interval guards, so structural replacements use spaces. Both endpoints of
  `between<br>1 and<br>2` remain rejected for rate, spread and condition roles.
- `_unit_contexts` bounds lexical unit continuation and explicit spread-unit
  scanning at actual table field/container tags. Scientific selection of the
  rate's common/header unit remains the caller's interpretation.
- `_rate_unit` rejects multiple nonempty visible fragments across table tags.
  A complete unit in one wrapped cell remains supported. Inline exponents and
  visual line breaks within one unit remain supported.
- `read_source_rate_unit` and `validate_source_spread_unit` use the unit-specific
  contexts. No consumer signature, parsed numerical record or formula changes.

No source bytes, witness offsets, unit multipliers, comparator meanings,
biological roles, annotation credit, controller, model prompt or episode
continuation logic were changed. Frozen configured006 was not restarted or
rewritten and no binding fingerprint check was bypassed. Future normal binding
descriptors fingerprint the changed source file.

## Path inspection and ownership trace

The complete affected reader, native partner inputs, source-defined unit reader,
partner numerical calculator and partner input dispatcher were read, together
with the complete `_Sources` custody implementation. Every direct `_contexts`
consumer was inspected: source-defined partner units, reaction native inputs and
context native inputs. The separate field-aware rate parser was inspected to
distinguish its existing behavior from this defect; it was not changed.

The partner storage writer, transaction and operation-key replay paths, source
scope/receipt checks, saved native/meaning validators, operand bindings,
numerical projection and typed return schema were traced. Relevant inherited
rate repository saved/read, owner/fact projection and admitted receipt paths
were read. Episode assignment validation, selected operation dispatch, facts,
report validation, exact admitted receipt forwarding, implementation descriptor
and binding reconstruction paths were inspected. Tests exercise the same path:

`selected operation -> authorized original HTML bytes -> exact number/unit
selectors -> existing partner calculator -> immutable sheet + operands ->
typed child facts -> ordinary parent form admission`.

The ordinary parent fixture records one selected partner population, one typed
receipt and three completed own runtime observations. Source-free replay adds
no action observation. These are engineering observations, not assays or new
scientific evidence.

## Verification and practical limits

The targeted suite includes adjacent labels/numbers, HTML case/attributes,
paragraph/break separators, same-cell comparison/uncertainty/relative-spread
guards, clipped inline digits/decimal/exponent/signs, UTF-8 byte custody,
supported inline exponents, unit line breaks, single-cell wrappers and rejected
cross-cell fabricated units. Synthetic tables populate numerical partner cells
through the actual selected operation. Strict upper-bound meaning is retained.

The final cold test closes the publishing Store and reopens it. Before binding
factory reconstruction it forbids scientific source artifact reads, exact
source/witness reads and actual parser/conversion/calculator entrypoints. It
leaves schema constructors executable and does not substitute a cached catalog.
The reconstructed catalog, operation replay, facts and report validation must
work against saved sheet/request artifacts under SQLite query-only mode.

The earlier full targeted run passed 77 tests in 34.19 seconds. After
strengthening the cold tests, their final two cases passed in 27.23 seconds.
The six-file synthetic regression group's final result is recorded separately
in `CHECKS.json`: 476 passed in 334.11 seconds. Test counts overlap and are not
assay counts.

The initial system Python lacked Biopython, so verification uses the existing
repository `.venv`. Earlier fixture failures correctly exposed an accidental
selection of `7` inside `37`, absent real whitespace in a verbal comparator,
and a no-op scripted parent action. Those test fixture errors were corrected
without weakening production validation.

This change does not infer the scientific ownership of a qualifier, condition,
row or shared table heading. Scalar qualifier context remains conservative
across separators; deciding the experimental meaning belongs to the episode.
General malformed HTML recovery, arbitrary expression parsing and broader
reader modernization are not implemented. No live model investigation was run
by this workload, and no claim about the frozen run's scientific outcomes is
made.

After finalizing the implementation, an additional synthetic boundary probe
confirmed that a structural break can separate a bare sign/exponent prefix
from a numerical token: selecting `7` in `<td>-<br>7</td>` and `-3` in
`<td>1e<br>-3</td>` accepts those separate visible tokens. Inline equivalents
remain rejected. Plain source whitespace already had this lexical behavior.
This distinction was reported to the root before acceptance; no further
source/test change is claimed here. The exact observed probes and review
status remain in `CHECKS.json`.
