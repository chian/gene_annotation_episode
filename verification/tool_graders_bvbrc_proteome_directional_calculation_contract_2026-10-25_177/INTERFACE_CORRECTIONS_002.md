# Authoritative interface corrections — 177/002

This additive revision corrects the already reviewed001 interface document.
It is the current proposed signature/validation boundary for root review and
supersedes conflicting signatures in001. Numerical field meanings, native
values and independent implementation ownership remain those of001.

## 1. No hidden ratio-rendering defaults

The primitive returns RatioCells, so all parameters affecting them must be
explicit. Use this signature instead of the shorter001 version:

```python
def calculate_protein_block(
    block: dict, *, key: dict,
    query_length: dict, subject_length: dict,
    amino_acid_alphabet: str,
    ratio_decimal_places: int,
    rounding: str,
) -> dict:
    """Native TraceBlock + native lengths + explicit options -> BlockComponents."""
```

`ratio_decimal_places` is an integer excluding bool in0..30; `rounding` is
exactly `half_even`; alphabet is the declared enum. All are required keyword
arguments with no default. The top calculator passes the three corresponding
fields from its validated saved DirectionalCalculationParameters. It cannot
render18 places or select standard20 implicitly. The explicit-field signature
above is normative for this delivery; no silent rendering/classification
default is permitted.

## 2. Empty subject occurrences retain their explicit identity

```python
def inspect_protein_correspondence(
    hsp_components: list[dict], *, key: dict,
) -> dict:
    """HspComponents for the supplied SubjectKey -> CorrespondenceGraph."""
```

Key is an explicit SubjectKey and every supplied HspKey must have that parent.
An empty HSP list is representable and never borrows the prior/first subject's
identity. For an actual parsed subject with0HSPs, return its key, `edges=[]`,
`mapping_state=incomplete_geometry`, missing distinct-pair/repetition cells
with `missing_traceback`, and an empty Support. Its displayed-HSP count remains
measured0. Support completeness for the empty displayed block membership is
vacuously true; that flag alone never asserts usable geometry. Subject coverage
remains missing. A native no-hit query has no fabricated subject/graph row.

## 3. Semantic validation has the observations and parameters it needs

```python
def validate_directional_numerical(
    name: str, value: dict, *,
    sheet: dict | None = None,
    parameters: dict | None = None,
) -> dict:
    """Complete structural and semantic validation; independent copy on success."""
```

No successful semantic validation is merely a shape-only fallback when context
is missing. Missing required context raises the dedicated contract error with
code and argument pointer. The required contexts are:

| Named schema | Observed sheet required | Calculation parameters required |
|---|---|---|
| `DirectionalCalculationParameters` | No | The value is the parameters |
| `DirectionalSheet` | Embedded reader results and copied observations | No |
| `DirectionalSheetResult` with non-null sheet | Embedded sheet | No |
| `BlockComponents` | Explicit `sheet=` | Explicit `parameters=` |
| `HspComponents` | Explicit `sheet=` | Explicit `parameters=` |
| `CorrespondenceGraph` | Explicit `sheet=` | No: graph geometry/symbol conflicts do not use resolved alphabet or ratio rendering |
| `DirectionalComponents` | Explicit `sheet=` | Embedded in the components; if external parameters are supplied, they must equal the embedded object |
| `DirectionalComponentsResult` with non-null components | Explicit `sheet=` | Embedded in non-null components; external supplied value must match |
| `DirectionalScoringSheet` | Embedded `observed` sheet | Embedded `calculated.parameters` |

For embedded cases, any additionally supplied external sheet/parameters must
match the embedded applicable object exactly; do not silently prefer one.
For null-payload failure result variants, there are no scientific component
values to validate: shape, failure-state invariants and input-error diagnostics
are checked without an invented observed sheet. Scientific FieldRefs/ColumnKeys
are forbidden in a null-payload failure lacking a valid observed sheet.

Standalone block, HSP and graph checks validate all occurrence keys, literal
symbols, coordinate positions, support and conflicts against the supplied
observations. Block/HSP ratios and class labels additionally validate against
the supplied parameters. A digest on some other object is not a substitute.

To preserve useful invalid-argument failure locations separately from scientific
source references, the closed001 Issue shape gains exactly one required field:

```text
argument_pointer:string|null
```

It is null for scientific source/relationship Issues, and a JSON pointer rooted
at the function's argument object for invalid-input/parameter failures (for
example `/parameters/ratio_decimal_places`). It is not a source FieldRef or
freeform message. The allowed `IssueCode` enum gains
`semantic_context_missing` and `semantic_context_conflict`. Existing reader
Issues remain unchanged inside the retained native reader results.

## 4. Implementation and inspection status

These corrections are a response to root's interface review, not a production
implementation. No shared files or worker176/178 candidates were changed.
The P<I relationship remains a diagnostic with both native count fractions
preserved. The native-version/source basis and legacy-formatter limitation are
recorded in numerical contract001; no local BLAST was run for that question.
