# 055 proposal: source repetition numerals without invented independence

Status: proposal only. No production module or test has been edited. The only
executed work is a synthetic, pure046 capability probe. No paper, retained
scientific packet,051 selection/sheet, private provider history, database or
historical code pin has been opened.

## Observed gap and purpose

`reproduce_count_gap.py` called the actual current `read_kinetic_inputs` on ten
invented source statements. Decimal `3` returned canonical count3. The other
nine cases failed before returning any extraction. Exact `three`,
`twenty-one` and `one hundred and three` all raised
`literal_source_number_required`. Qualified decimal `at least 3` raised
`plain_source_point_required`. Written qualification, alternatives, a decimal
point, zero and a clipped word also failed. The complete exact selected
synthetic text and terminal errors are retained in
`SYNTHETIC_BASELINE_RECEIPT_001.json`.

This is a targeted input capability for the existing kinetic component, not a
new grader, scoring sheet, axis, independence score or source-processing credit.
Its consumer is the literature episode selecting relevant experiments/claims.
Neither a paper router nor a fixed order of selected components is introduced.

## Scientific and numerical boundary

Reading a cardinal numeral answers only what count was reported. It does not
answer what was counted, whether repetitions were independent, whether there
were separate biological preparations, whether a spread is SD/SEM, or whether a
sampling model applies. Existing witnessed `repetition_basis` and
`estimate_basis` interpretations retain those separate responsibilities.

The045 canonical uncertainty count remains a nullable positive integer. Only an
exact, unqualified, complete positive count literal supplies it. A qualified,
range, alternative or unsupported count leaves that exact count null while
retaining the selected source and a finite extraction status. Native parameter
values and descriptive contrasts remain usable when the count is unresolved.
No count creates covariance, a normal model, independent-preparation count or
annotation credit.045 calculations remain unchanged: a synthetic8/2 parameter
comparison still supplies difference6, ratio4 and log contrastln4; its
model-dependent cells remain null without an applicable supplied model.

## Proposed pure reader interface and grammar

Keep the selected operation and argument structure unchanged. The existing
`count` selector still contains only an exact witness, `number_start` and
`number_end`; these names designate the selected numeral span and may cover a
written numeral. All outer source offsets are UTF8 bytes; positions inside the
authenticated quotation remain Unicode character positions. No scientific
number or rewritten source is supplied as an argument.

Implement a small private count reader inside
`literature_kinetic_inputs.py`, reusing `_Sources.witness`, `_index` and the
actual field-aware source-context boundary. Keeping it inline avoids a new C7
dependency file and avoids changing the shared decimal scalar parser used by
other component families. The decimal positive-integer fast path retains
existing scalar guards and values.

The written-numeral grammar is explicit English cardinal notation:

- Atomic words `zero` through `nineteen`, and `twenty`, `thirty`, `forty`,
  `fifty`, `sixty`, `seventy`, `eighty`, `ninety`.
- A tens word may have one unit word1–9 separated by one ordinary hyphen or
  whitespace. Hyphenation elsewhere is unsupported.
- A group1–999 is a1–99 numeral, or one unit word1–9 followed by `hundred`,
  optionally followed by a1–99 group. A single optional `and` may occur between
  `hundred` and its nonzero remainder.
- A complete numeral may contain a1–999 group followed by `million`, then an
  optional1–999 group followed by `thousand`, then an optional1–999 remainder.
  Scales occur once in descending order; missing higher groups are allowed.
  A single optional `and` is permitted before a final remainder below100 when
  at least one scale group preceded it. Bare scales and arbitrary concatenated
  number words are unsupported.
- Matching is case-insensitive, with whitespace normalized only for lexical
  recognition. Original source bytes and the complete raw selected string are
  retained. The supported cardinal grammar spans0–999999999; this is an
  explicit reader-language limit, not a limit imposed on scientific counts.
  Zero is recognized but cannot populate a positive count.

Existing positive decimal digit strings retain their existing supported range
and guards; the written-numeral grammar does not cap decimal counts. A complete
larger or unfamiliar word form is retained with an unsupported-syntax status,
not rounded, silently truncated or converted to zero/one. Articles, `single`,
`duplicate`, `triplicate`, `dozen`, ordinals, Roman numerals, fractions and
scientific expressions are not cardinal source literals under this proposal.
Their interpretation is a separate future capability rather than an implicit
numeric guess.

## Count result and partial behavior

A selected count produces one detached record with these exact keys:

| Field | Meaning |
| --- | --- |
| `selector` | Original selected span plus authenticated artifact identity |
| `raw_number` | Exact source substring; words remain words |
| `value` | Parsed integer numeral when supported, otherwise null |
| `notation` | `decimal_digits`, `english_cardinal`, or `unsupported` |
| `relation` | `point`, `lt`, `le`, `gt`, `ge`, or `unresolved` |
| `approximate` | Recognized approximation boolean, or null when unresolved |
| `status` | One finite state in the table below |
| `unavailable_reason` | Null for exact counts; one declared reason otherwise |

`count=None` remains a missing selection, not a finding that the source omitted
the count. It creates no fabricated count record. Parent-visible count status
is then `not_selected` and has no source-unreported assertion.

| State | Canonical exact count | Retained result |
| --- | --- | --- |
| `exact` | Positive parsed integer | Original numeral, point relation, false approximation |
| `qualified` | null | Parsed numeral if recognized, actual bound/approximation, `exact_count_qualified` |
| `range_or_alternatives` | null | Original selected expression and witness, unresolved relation, null value, `count_range_or_alternatives` |
| `unsupported` | null | Original selected expression and witness, unresolved relation, null value, `unsupported_count_literal` |
| `not_positive` | null | Recognized zero/negative integer where supported, `positive_count_required` |

Recognize count qualifiers using actual source context on both sides, including
outside a narrowed witness and across inline markup. Prefix/suffix comparison,
approximation and negation guards apply to words as well as digits. Reuse the
existing finite comparator spellings, including at least/at most, greater/less
than, no more/less than and suffix or more/less. Compound, negated or conflicting
qualifiers retain an unresolved qualified reading; they cannot establish an
exact count or a confident bound. Count ranges/alternatives recognize adjacent
`to`, dash, `or`, and `between ... and ...` patterns without treating a distinct
following technical-repetition statement as the same count. If the finite
syntax is unresolved, the result stays unavailable rather than choosing an
endpoint, averaging counts or multiplying repetitions.

Authentic but unsupported whole count syntax is a partial scientific input.
Malformed selectors, false quotations, unauthorized source reads, byte or
character-boundary errors, a clipped token (`three` inside `threefold`, or
`three` inside `thirty-three`), and an explicitly selected physical quantity
such as3nM remain actionable caller errors. They are not converted into missing
scientific information. Decimal clipping, arithmetic, unit-role and custody
guards remain effective. Failures retain their specific selected-span details.

The canonical count is obtained only as:

`count_reading.value if status == exact else None`.

It is never obtained with `int(raw_number)` for written numerals and never from
the number of witness records, source representations, papers or model calls.
The native record's integer value is a numeral conversion of a reported count;
the subject's measurement origin remains reported/synthetic as before. Exact
raw wording, notation, selector and implementation fingerprint disclose that
conversion without relabelling it as a new measurement.

## Concrete synthetic inputs and outputs

All examples below are invented; numerical operands are actual source spans in
the synthetic input, not model-authored values passed to the calculator.

| Actual selected source wording | Count-reading result | Canonical count | Preparation independence |
| --- | --- | ---: | --- |
| `three independent experiments` (select `three`) | exact, value3, English cardinal |3| Unspecified unless separately witnessed |
| `TWENTY-ONE technical measurements` (select numeral) | exact, value21, English cardinal |21| Technical meaning remains technical |
| `one hundred and three repeats` | exact, value103, English cardinal |103| Unknown |
| `at least three independent experiments` (select `three`) | qualified, value3, ge, false approximation | null | Unknown |
| `about three experiments` | qualified, value3, point, true approximation | null | Unknown |
| `three or four experiments` | range/alternatives, raw wording retained | null | Unknown |
| `zero experiments` | not_positive, value0 retained | null | Unknown; no zero fallback |
| `triplicate` | unsupported, raw wording retained | null | Unknown |
| `3.0 independent experiments` | unsupported whole count notation | null | Unknown |
| `threefold` with selected `three` | Specific clipped-token caller failure | No population | No inference |

In the synthetic8/2 comparison, each valid partial count case still supplies
raw parameters8 and2, difference6, ratio4 andln4. Unknown count information does
not erase these measurements or manufacture any model-dependent score.

## Saved contracts, typed delivery and display

Count-reading records have an extended shape, so the extraction and saved
validation versions must advance to v2. The selected argument version remains
v1 because its shape does not change.045 canonical input/calculator formats and
all scientific arithmetic remain unchanged. The kinetic storage record version
advances to v2 to identify its extended returned metadata explicitly. Historical
pins and saved generations remain untouched; current code does not migrate,
repin or claim cross-generation reopening of old saved sheets.

`literature_kinetic_validation.py` needs a separate count-selection validator;
generic parameter/spread `_numeric_selection` must retain its strict finite
numeric behavior. The count validator checks exact selector/witness association,
raw substring, finite enums, integer-or-null types, positive exact-state
relationships, and equality of the canonical count with the original saved
count reading. It validates the saved original result rather than invoking the
count parser, reacquiring source text or doing new word interpretation.

Storage retains the extended count record in the existing uncertainty entry.
Its published count reference still uses the original numeral anchor, including
the literal word; it never uses a fabricated digit quotation. Existing numeric
token bindings must include this reference so broad source labels cannot leak
an unrequested count through words.054's bounded display helper and full exact
anchor handling remain unchanged.

The typed uncertainty metadata gains only these finite, nonnumeric fields:
`count_reading_status`, `count_unavailable_reason`, `count_notation`,
`count_relation`, `count_approximate`. The existing nullable integer
`uncertainty_values.count` remains the exact canonical count. Add
`uncertainty_values.count_reported_value` as a nullable integer for the parsed
reported numeral in a qualified case. Like all other uncertainty numbers, it is
populated only on the corresponding requested raw-parameter row; otherwise it
is null with `delivery_status=not_requested`. Status/relation preserve why that
numeral is not an exact sample count. No count operand appears in a derived-only
row or becomes an additional scoring contribution.

The mechanical `_kinetic_received` renderer must display those finite meanings
and only the already permitted requested numerical fields. It must not add a
scientific TASK instruction or expose raw count tokens/context through hidden
labels. No scientific prompt constant, C7 service/callable name, episode route,
controller, parent assignment or annotation-credit formula changes. Inline
reader logic is already covered by C7's046 fingerprint, so no C7 source edit or
new fingerprint entry is required. Storage's expected046 hash must be updated
to the exact released bytes; validator/storage hashes remain dynamically bound.

## Prospective ownership requiring root release

No production release is claimed. After root approves this concrete contract,
the proposed existing-file scope is:

1. `gene_annotation_episode/literature_kinetic_inputs.py`: inline count reader,
   count integration, v2 extraction identifier, mechanically accurate count
   selector description if needed; no TASK string.
2. `gene_annotation_episode/literature_kinetic_validation.py`: detached count
   record/association checks and v2 validator identifier only.
3. `gene_annotation_episode/literature_kinetic_storage.py`: v2 record identifier,
   exact046 fingerprint, count binding/projection/schema fields only, after054
   ownership is explicitly transferred. Preserve054's accepted helper exactly.
4. `gene_annotation_episode/literature_experimental_prompt.py`: only finite
   count metadata display within `_kinetic_received`, after explicit shared-file
   ownership transfer; preserve all TASK strings and masking functions.
5. `tests/test_literature_kinetic_inputs.py`: revise only the existing negative
   count expectation where a legitimate qualified/nonpositive count now returns
   a useful partial rather than rejecting the entire operation. Existing
   clipping cases still fail. No unrelated test weakening.

One new dedicated test file is proposed:
`tests/test_literature_kinetic_count_inputs.py`. All research receipts and patches
remain in this055 directory. The root may release input/validation work first
and hold shared storage/rendering until its ownership is available; full native
delivery remains part of this workload rather than being declared complete at
the pure-reader stage.

Read-only:045 calculator, shared scalar/custody readers,052 binding reader,
amount/optical/storage families, C7/services, base044, domain/Store, communication,
runtime/controller, scientific TASK constants, original source papers and all
historical pins/runs. No generic count migration or all-family refactor.

`BASELINE_001.json` preserves16 exact code/test snapshots.046 is
`1176033e44bb7e2ff065aecd6f1d335fbcab531069e99490cd293dd8a8edb844`;
validator is
`2f21acdab795ba3917d3ce8202d0621c5c222e64cc75f7823a1f31a92d6e71c2`.
The captured054 storage is already its root-accepted final bytes
`599606c6e40f00e587934b0a7fcd1c550b46253974dd5b123cfdde228245759e`,
but ownership remains with root until explicit release.

## Verification after release

- Exact word grammar: atomic, tens/hyphen, hundreds/optional and, descending
  scales, case/whitespace variants and maximum supported grammar. Compare with
  explicit expected integers, without a model or external parser.
- Preserve decimal canonical counts and all pre-existing parameter/spread/unit,
  context, identity, calculation and uncertainty values. Compare complete045
  outputs for unchanged canonical inputs; do not add overlapping suite totals.
- Exact UTF8 source bytes and Unicode inner indices with non-ASCII prefixes,
  both source representations, inline markup, narrowed witnesses and qualifiers
  outside the quote. Wrong quotations/authorization/clipping remain failures.
- Qualified, conflicting/negated qualifier, range, alternatives, zero,
  unsupported/noninteger/expression forms preserve raw source and valid
  parameter components without selecting a count endpoint or asserting source
  omission. Absent selection is explicitly not_selected.
- Count3 with repetition basis unspecified, technical and separately witnessed
  biological meanings never creates covariance, preparation count or credit.
- Actual selected LiteratureEpisodes execution and ordinary typed child return
  using synthetic sources: one selected population, exactly ordinary action
  observations, no extraction/reporting observations or automatic second model
  call. Request contrasting subsets and preserve exact parent possession.
- Actual provider presentation: requested count numerals may appear only on
  the matching requested raw-parameter row. Derived-only rows, full/broad labels,
  off-page references and count words cannot leak unrequested numbers/words.
  Finite count statuses remain available and distinct from scientific absence.
- Actual SQLite mode=ro reconstruction of the original saved sheets and exact
  parent admission, with original source artifacts, count reader,046 reader,
  045 calculator, receive and credit projection forbidden before reconstruction.
  Whole SQL and observation counts stay unchanged; display is saved metadata.
- Tampered raw words, reading statuses, canonical counts, owner identities,
  count references, unrequested values and original typed receipts fail the
  actual saved/authentication boundaries. No detached proof substitutes for
  original-operation custody.

Run the dedicated tests first, then all four current kinetic suites and054's
dedicated publication tests. Run relevant mechanical rendering/parent tests if
new boundary checks expose a concern. Report exact terminal evidence and
limitations; engineering success is not configured-model extraction, scientific
source validation or completion of A105.

## Actual inspection record

Fully read: active goal; root AGENTS/GOAL; full EPISODE_STRUCTURE,
TIME_AWARE_ESTIMATION and TASK_AND_STEERING; full W04 amendment; research AGENTS;
all four current kinetic implementation modules; all four kinetic tests;
experimental contracts; latest039 and both040 direction files, with those latest
human directions reread last before this proposal. One aggregate W04 display
was truncated; the complete amendment was then reread alone before proceeding.

Relevant complete paths read: `_Sources` custody and helper functions;
`number_selector_schema`, source contexts, comparator/scope parser and scalar
reader; native rate schema/context/scalar and its uncertainty/count extraction
and saved count checks; kinetic C7 catalog/implementation fingerprint, argument
authorization/dispatch and typed-fact routes; kinetic service accessor;
`_kinetic_rows`, token masking and complete received renderer; base044 original
runtime-delivery authentication, owner/received-subset validation and received
cell reconstruction. Large generic modules are not claimed fully read.

No paper was opened, so this code-only proposal does not claim a post-paper
reset or new scientific source coverage. Two overly broad early filename-only
searches returned excessive historical pin/artifact names; no contents were
opened, and subsequent discovery was restricted to direct root names. No skill,
network search, model, private history, Git operation or external message ran.
