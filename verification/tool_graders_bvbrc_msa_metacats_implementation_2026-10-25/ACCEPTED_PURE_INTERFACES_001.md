# MSA and MetaCATS: accepted first implementation boundaries

This additive root decision accepts the pure parsing and calculation interfaces
specified below. It does not replace the immutable goal, claim complete tools,
or accept unfinished provider/bundle/projection schemas. Original proposals are
unchanged. Required provider assembly, invocation, tool information, production
binding, requested returns, full episode verification and live resource checks
remain on the original C-L204-MSA and C-L205-MetaCATS rows.

## Authority and concrete inputs

Read the entire immutable goal before coding:
`/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`.
Its SHA256 is `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
After substantial native-output/source examination and after each tool, reread
its purpose and all sixteen DESIGN PRINCIPLES verbatim before translating facts
into this contract. Read AGENTS.md, the grader principles and the BLAST grader
as the existing separation example. No literature, W05, evidence-axis redesign,
new episode types, execution decisions or controller/credit changes belong here.

Accepted serialized records are the applicable parser and calculation records in
`../tool_graders_bvbrc_msa_metacats_boundaries_2026-10-25/INTERFACE_VALUES.md`
(SHA256 `94da6824842d494b2e08f37e05f612bd1a947fd63b8e8706c8e727e9b84ffe09`).
Accepted numerical meanings and pure signatures are sections 2–7 of that
directory's `PROPOSED_CONTRACT.md`
(SHA256 `3cf7065155b22cdaf76a7855c4c64e1511cf1329f9540b35d5d2afb7e0c038f9`),
with explicit amendments below. No unspecified record may be invented in one
worker and silently imposed on another. Report any missing boundary to root.

Native MSA DNA/protein outputs are retained under that boundary directory's
`native_examples/`. Original producers and application wrappers are retained
there under `retained_sources/`; official examples are under `additional_sources/`.
MetaCATS has seven actual native Perl/R numerical/export runs in
`../tool_graders_bvbrc_metacats_native_execution_2026-10-25/cases/` and their
receipts. These are actual native components on stated synthetic/official inputs,
not full AppService, aligner or live API execution. Preserve the distinction.

## Exclusive workloads and actual handoffs

**A — MSA frequency parsing and alignment calculations.** Own only new
`gene_annotation_episode/bvbrc_msa_formats.py`,
`gene_annotation_episode/bvbrc_msa_format_contracts.py`,
`gene_annotation_episode/bvbrc_msa_calculators.py`,
`gene_annotation_episode/bvbrc_msa_calculation_contracts.py`, corresponding new
`tests/test_bvbrc_msa_*.py`, and `verification/tool_graders_bvbrc_msa_pure_2026-10-25/`.
Implement the exact `parse_msa_frequency_table`, `msa_native_entropy` and
`msa_reference_differences` signatures and records. DNA/protein and tables with
or without reference columns are distinct declared modes. Reuse existing
aligned FASTA parsing and shared alignment calculations without editing them.
Export `validate_msa_frequency_table(value)` and validators for both component
records; validators return detached values. Pure functions must validate saved
inputs, preserve source-backed partial measurements and be replayable offline.
The future MSA provider consumes these exact documents/components; root owns
that provider contract separately. No worker edits host hooks or other tools.

**B — MetaCATS native tables and metadata parsing.** Own only new
`gene_annotation_episode/bvbrc_metacats_formats.py`,
`gene_annotation_episode/bvbrc_metacats_format_contracts.py`, corresponding new
`tests/test_bvbrc_metacats_formats.py` and `test_bvbrc_metacats_format_contracts.py`,
and `verification/tool_graders_bvbrc_metacats_formats_2026-10-25/`.
Implement all five proposed parsers: current/legacy omnibus, current pairwise,
optional raw R omnibus/pairwise, ordered metadata, and adjusted matrices.
Each returns the exact ParseResult and document shape. Export validators named
`validate_metacats_chisq_table`, `validate_metacats_pair_table`,
`validate_metacats_raw_r_table`, `validate_metacats_metadata`, and
`validate_metacats_adjusted_matrix`; each takes one value and returns a detached
validated value. This worker does not calculate significance, infer native
group identities, silently split ambiguous pair labels, or change producer bytes.
The future metadata association/provider functions consume its ordered records.
Root statistics depend on the documented group-count record, not these parser
implementations, so both workloads can code independently.

**Root — numerical value primitives and MetaCATS calculation functions.** Own
new `gene_annotation_episode/bvbrc_alignment_values.py`,
`gene_annotation_episode/bvbrc_metacats_calculators.py`,
`gene_annotation_episode/bvbrc_metacats_calculation_contracts.py`, matching tests
except B's two filenames, and this implementation verification directory.
Own exact `metacats_group_counts`, `metacats_statistics`, `metacats_effects`,
`adjust_p_values` signatures/records and their validators. No executor behavior
changes are required. Both fresh workers import only the agreed primitives below.

## Shared primitives — exact interface

`bvbrc_alignment_values` supplies ordinary Python functions, not an expression
language or generic scoring engine:

```
native_number(raw_token: str, *, source_location: dict,
              integer: bool = False, minimum=None, maximum=None) -> NativeNumber
validate_native_number(value: dict) -> dict
numeric_cell(value, *, state: str, unit: str, origin: str,
             population_id: str, method_id: str, numerator=None,
             denominator=None, evidence=(), uncertainty=None,
             requirement_ids=()) -> NumericCell
validate_numeric_cell(value: dict) -> dict
document_id(kind: str, *, artifact: dict, parameters: dict) -> str
diagnostic(code: str, *, phase='association', path='',
           severity='qualification', evidence_refs=()) -> Diagnostic
requirement(requirement_id: str, *, kind: str, role: str|None,
            source_refs=(), reason_code: str) -> AcquisitionRequirement
```

NativeNumber retains all six proposed fields. Add `overflow` to token_kind.
Parse decimal syntax exactly before binary conversion. Blank -> missing/null;
literal NA -> not_measured/null; NaN/Inf -> failed/null/nonfinite; malformed ->
failed/null/malformed; nonzero decimal lost to binary zero -> failed/null/underflow;
finite decimal overflowing binary -> failed/null/overflow. Exact integer inputs
remain Python integers without float rounding. A syntactically finite value
outside an explicitly supplied bound, or fractional value in an integer field,
retains that value with state incompatible. Never clamp or substitute zero.
Native parsers check integer/range semantics for their particular fields.

NumericCell has exactly the proposed twelve fields. Available requires a finite
value. Other states require null, except incompatible native_observation may
retain a finite invalid native measurement. Evidence uses the unchanged shared
phylogeny evidence list. Counts normally have null numerator/denominator; a
ratio explicitly retains both operands, including zero denominators when null.
Unit and method_id are nonempty literal identifiers supplied by ordinary code;
no interpretation of expressions occurs. Uncertainty is null for these native
inputs. If supplied, it has exactly kind, lower, upper, value, method_id, with
kind confidence_interval|standard_error|standard_deviation|native_unknown and
finite-or-null numbers; interval bounds must be ordered. All values detach.

document_id is kind + ':' + SHA256 of UTF-8 canonical JSON (sorted keys, compact
separators, ensure_ascii=True, allow_nan=False) of `{artifact,parameters}`.
Parameters include actual reader layout/alphabet/category/encoding where
applicable. IDs are internal storage identities, never substituted for evidence
or dumped into model prompts. SourceLocation/Artifact and host Diagnostic and
AcquisitionRequirement shapes/enums remain unchanged. Helpers perform no I/O.

## Corrections and settled arithmetic

1. StatisticalCalculation field `original_category_group_count` is renamed
   **`r_table_group_count`**. K is represented R columns, excluding metadata-only
   groups, including represented groups whose observed site count is zero.
   The older single table sentence saying original category group count is
   superseded. Never align metadata ordinals with R positions by sorted order.
2. MSA `native_rounding` accepts **`binary64_fixed_2_ties_to_even` or None**.
   The selected ordinary calculation is `float(format(H, '.2f')) * 100`, retaining
   unrounded H. Its method identity is `msa_literal_entropy_binary64_fixed2_v1`.
   This is a declared offline rounding implementation, not a universal claim
   about Perl/libc or a deployed version. Compare against retained native outputs
   and preserve residuals; native observation stays unchanged. None leaves this
   derived field null/not_measured; entropy/counts still calculate. Do not add a
   proof gate for independent literal entropy.
3. Root chooses the installed SciPy dependency for chi-square tails. Backend
   input is exactly `{name:'scipy_chi2_integer_df_logtail_v1',version:<installed
   scipy.__version__>}`. Reject unknown implementation/version; callers cannot
   supply executable code. Use scipy.stats.chi2.sf; if sf underflows, retain null
   mathematical_p and a stable finite log tail for integer df. Derive Q(df/2,x/2)
   using log-space incomplete-gamma recurrence with base Q(1,z)=exp(-z) for even
   df and Q(1/2,z)=2*Phi(-sqrt(x)) for odd df. Use log_ndtr and logaddexp. Native
   zero-rule emulation is a separate value using this declared backend, not a
   claim that its underflow boundary equals R's. No p-value floor.
4. All group pairs are explicit. No automatic all-pairs or category pooling.
   Native AA pair df=(r_table_group_count-1)*(augmented_symbol_count-1);
   standard_pair df=augmented_symbol_count-1. NA uses the latter either way.
   Native source and standard_pair have different method IDs. Epsilon is finite
   and >=0; changed epsilon is recalculation, never rewritten native history.
5. Raw observed counts are nonnegative integers. Augmentation is separate.
   Empty and conserved sites produce explicit exclusions, not positive-df tests.
   Keep negative signed effect differences; no arbitrary clipping. Mathematical
   probabilities and native values are not function-confidence estimates.
6. GroupAssignment.member_key is nullable or exactly
   `{input_binding_id,member_id,occurrence_index}`. A missing identity cannot
   establish membership. Native original `#` and terminal '-' masks stay separate.
   The existing FASTA parser cannot represent '#'; the adjusted parser preserves
   it separately. Do not edit the shared FASTA parser to accommodate an unrelated
   format. Root association work will explicitly handle adjusted matrix inputs.
7. TestFamily assumption is null or exactly
   `{kind:'independently_known_count'|'parent_declared_upper_bound',count:int,
   evidence:[Evidence]}`. complete requires matching complete test IDs and p-vector;
   known_count_only/declared_upper_bound are usable only for Bonferroni with their
   corresponding explicit assumption. No count can come from significant rows.
8. Parser structural failures return invalid/null when no readable document;
   otherwise preserve valid rows and mark partial. Retain malformed NativeNumber
   tokens in their row. A final missing newline alone does not prove truncation.
   Evidence of truncation/ragged rows does. Unknown source semantics is partial,
   not a fabricated measurement. Caller contract misuse raises a finite ValueError.

## Required concrete verification and handoff

A: actual retained DNA column2 counts A2/deletion1, n3, H=0.9182958340544896,
Score92; DNA column3 C3/T1 H=0.8112781244591328, Score81; protein Del2/Gly2,
H1, Score100 and tie consensus X. Verify canonical-only entropy differs;
terminal vs internal gaps, column-subset invariance, all-gap/ambiguous/empty sites,
reference gaps and staged/original coordinates, missing original maps, duplicate
native coordinates, changed rows/score residuals, malformed/ragged/partial tables,
and offline saved-document replay without parsing, network, native execution or
file access. Retained native and deliberately synthetic cases remain labeled.

B: all seven root native runs, the official legacy file, exact original token
and source ranges, ordered duplicate/extra metadata rows, significant-only empty
tables, raw conserved placeholders, actual metadata-only group label shift,
actual padded twelve-group tokens, native pair p1 in the underflow case, malformed
counts/p/df, scientific notation underflow/overflow, bad digest/layout/encoding,
raw-R wrapper parsing as data (never evaluation), no dropping unknown columns
or ambiguous pair labels, no sorting IDs to infer associations.

Root: raw 6A/6C gives omnibus X2=8.330556481172945, p=.00389837142433717;
pair X2=11.99600133288904, p=.000533148220906465. Three groups give pair
source df4/p=.017381025135296442 versus standard df2/p=.00248371298657324.
Underflow example keeps finite log tail and native emulation1 separately.
Compare all312 variable official-input tests with retained native output.
Test effects and multiplicity against explicit hand calculations, missing
populations, wrong group order, duplicates, incomplete vector, zero denominators,
changed epsilon/df policy and saved-data recalculation with no I/O/parsing.

Each workload supplies installed owned modules, meaningful test results, complete
saved examples, source/test hashes and an explicit unfinished-work list. It does
not declare either tool complete. Root reviews exact outputs before the separate
provider and production return integration assignments.
