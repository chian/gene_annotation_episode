# Native paired BLAST selected columns: implementation and verification

The existing `result.blast.hsp` operation now accepts an explicitly received,
authenticated `native_blast_pairwise` observation from the 297/298 producer.
It fills the existing selected-column sheet and invokes the existing separate
calculator. This is an additional native source binding for the established
fields and functions, not another scientific grader or another observation.
Filled sheets below are verification examples.

## Production changes

| File | Implemented responsibility |
| --- | --- |
| `gene_annotation_episode/native_blast_hsp_views.py` | Exact seven-key host port `native_blast_pairwise_hsp(store, observation)`; authenticates immutable source/observation, original bundle and source-associated grading, complete original row and score measurements, original report/search/hit/HSP association, and actual complete query/reference sequences. Reuses 297 validation and scalar extraction; launches no worker, calculator or process and publishes nothing. |
| `gene_annotation_episode/blast_result_views.py` | Selects the mutually exclusive actual host marker after existing received-input/scope admission; preserves `_original_hsp`'s four-value return and the API submission/request path. Native output carries `native_blast_pairwise`. `blast_hsp_facts` stays API-specific. |
| `gene_annotation_episode/alignment_site_native.py` | Uses authenticated native program, operand lengths and report descriptor when populating the existing sheet. The grading envelope remains bound to the original bundle. |
| `gene_annotation_episode/alignment_site_action_records.py` | Validates the applicable marker, actual native units/program, original action/window, bundle-bound envelope and report-bound descriptor. Existing receipt order, original form and frozen-return validation remain in place. |
| `gene_annotation_episode/blast_hsp_site_inputs.py` | Admits only the explicit native JSON and declared tabular source/locator shapes; selects `blast_json2` versus `directional` from actual retained format, including saved-sheet validation. |
| `gene_annotation_episode/knowledge/blast-hsp-columns.md` | Explains the callable selected-column operation, actual native inputs, coordinate and score meanings, and partial-data behavior. |

The root agent separately updated the existing knowledge index summary and
added the helper to provenance. That final index is included in the final
source capture. This workload did not edit the index, 297/298 files, numerical
calculators, communication grammar, credit, continuation or resource policy.

The descriptor still has exactly `alignment_ref`, `source_ref`,
`native_artifact_ref`, `provider`, `format`, `native_version`, `native_locator`.
Native provider is `episode.execution_result`; format is
`native_blast_json_hsp` or `native_blast_tabular_hsp`; locator has exactly the
original `search_key`, `hit_ordinal`, `hsp_ordinal`. JSON keeps its real
`results.bl2seq` pointer. Actual report bytes, declared table fields and
original table lexemes are checked separately. No API RID or API search record
is manufactured. Engine version is the reported version or null.

## Reusable numerical fields and functions

`extract_blast_hsp_columns` retains the complete native HSP, whole-HSP native
measurements, full operands, requested/realized window, explicit availability
and issues, and complete selected column rows. Each row keeps original symbols,
native units, direction/frame, checked zero-based half-open operand intervals
and available ancestry. The existing bounded tool preview is separate from the
complete retained sheet.

`calculate_blast_hsp_column_components` consumes only that saved sheet. Its
signature, implementation and definitions are unchanged. It calculates:

| Component | Inputs and denominator | Meaning |
| --- | --- | --- |
| Window, paired, identical, substituted and operand-gap counts | Selected realized rows and their literal symbol relationships | Actual correspondence in the requested column window |
| Paired identity | Identical pairs / paired columns | Literal equality among paired selected symbols |
| Alignment identity | Identical pairs / all selected columns | Literal equality including gap columns in the denominator |
| Query/reference paired units | Union length of checked intervals for paired selected rows | Covered original operand units (`nt` or `aa`) |
| Query/reference paired coverage | Paired units / complete corresponding original operand length | Fraction of the complete operand covered by paired selected rows |

All ratios retain numerator and denominator. A translated amino-acid column
consumes three nucleotide units on its translated operand. Whole-HSP bit score,
raw score and E-value remain inherited whole-HSP facts and are not apportioned
to the selected window. No probability, uncertainty or composite relevance
score was added. An empty terminal page has measured zero counts and null
identity; missing or incompatible inputs remain distinct from zero.

## What was inspected and tested

The full immutable goal, applicable AGENTS instructions and required design
documents were read before editing. Complete relevant native publication,
worker, result, return, report-collection, pairwise grading, selected-column,
own-action and return implementations were inspected, plus the affected tool,
scientific-binding and service consumers. The original objective and all
sixteen design principles were reread verbatim after native/source study and
again before handoff, followed by the full 300 contract and addendum. The
immutable source identities and reread ranges are in `READ_AUDIT.json`.

Retained-native tests use all twenty original 294 reports through the existing
297 preparation/publication functions. These cover all five paired programs,
JSON15, declared tabular7 and empty tabular6, forward/reverse frames, selected
ranges, gaps, multiple HSPs and empty terminal windows. All 36 published HSPs
are read by their original ordinal. Four real reports have no HSPs; they remain
empty. Test Store handles replace placeholder bindings only in copied
manifests, exactly as in the existing 297 fixture. Native report bytes and
coordinates are unchanged. These cases establish retained-native publication
and reading, not new historical execution receipts.

Synthetic tests are explicitly labeled: changed measurements/intervals/row or
locator; an invalid sibling preserving the original surviving HSP ordinal;
wrong same-length operands through actual publication; unavailable strings,
one missing string, geometry and midline faults; strict provider/format/locator
validation; and negative-frame JSON versus directional table coordinates.
Readable string counts survive incompatible geometry while coverage is null.
No fabricated trustworthy native observation is used to claim an unavailable
native publication. The present producer rejects such invalid HSP rows before
publishing a received observation; the independent extractor behavior is tested
with supplied synthetic inputs.

The host-only port is tested with publication, grading worker, full collection
parser, calculators, process launch and network operations forbidden. Saved
sheet recalculation is tested with file access, process launch and networking
forbidden. Own-action checks reject marker substitution, wrong bundle/report
roles, changed window/program/locator and receipt at or after the action.

## One actual complete Workflow

As authorized only by `CONTRACT_ADDENDUM_002.md`, `workflow001` performs one
small actual local reverse BLASTX two-sequence execution with the existing 298
practical job path. The selected request uses `-query_loc 30-215`, minus strand,
genetic code 11 and one thread. Its synthetic derivative input sequences are
the existing retained 294 range example. It is not a database search.

The existing Workflow launches the selected practical job, waits for the
actual native result, returns the execution handoff, collects and publishes
through the 298 results child, and returns the real HSP to the scientific
parent. That parent explicitly supplies the received HSP when commissioning a
scientific child with `result.blast.hsp` and a selected-column return form. The
scientific child performs one column action at offset 1, limit 4 and returns
only the requested rows and numerical fields. It does not receive a full
private sheet as its parent return.

The check observes one native BLAST plan, one original scientific observation,
one site action, one site calculator invocation, three parent actions and seven
total completed actions with seven local observations. The site action has no
scientific record refs. The calculator is disabled immediately after its first
invocation, before initial child closure. Initial closure, cached operation
replay, form receipt, frozen report validation and frozen redelivery succeed.
A changed frozen count fails. Replay and redelivery leave the exact stored
state unchanged. No parser/worker or pairwise calculator runs during the
scientific read; no calculator runs at closure.

Model decisions, scientific credit and scientific controller horizons are
scripted engineering fixtures. Native execution/capture, practical completion,
publication, receipt lineage, scientific binding and typed communication are
the existing production paths. This verifies the stated communication path,
not autonomous scientific judgment, calibration, API/HPC execution or database
identification.

## Numerical examples

| Example | Measured answer |
| --- | --- |
| Actual reverse BLASTX selected columns 1–4 | Four paired and identical `K,V,L,T` residues; query intervals `[209,212)`, `[206,209)`, `[203,206)`, `[200,203)` nt with frame -3/direction -1; reference intervals `[10,11)` through `[13,14)` aa, direction +1 |
| Same actual selection | Paired identity `4/4 = 1`; query coverage `12/244 = 0.04918032786885246`; reference coverage `4/80 = 0.05` |
| Same complete HSP | 62 paired residues, 186 query nt; bit score 132.494, raw score 332, E-value 6.68493e-48, retained as whole-HSP facts |
| Retained BLASTP gapped HSP | 253 columns, 243 pairs, 238 identical, 5 substituted, 10 reference gaps; query coverage `243/253`, reference coverage `243/243` |
| Twelve selected columns across those ten gaps | Two pairs, two identical, ten reference gaps; paired identity `2/2`; alignment identity `2/12`; query coverage `2/253`; reference coverage `2/243` |
| Retained TBLASTX JSON and table | Ten original HSPs per report remain distinct; first HSP covers 80 paired amino-acid columns and 240/243 nt on each operand |

Native precision is preserved separately: the gapped BLASTP JSON reports bit
score 486.878 while its table reports 486.0; reverse-range BLASTX JSON reports
132.494 and 6.68493e-48, while its table reports 132.0 and 6.68e-48. No tolerance
or rounding makes these separate native facts artificially identical.

Complete examples are in `check003/examples/` (all twenty reports, full native
sheet/score/row data, selected-gap and labeled partial-input examples),
`check004/examples/synthetic_format_conventions.json`, and
`workflow001/examples/actual_reverse_blastx_workflow.json` (actual plan,
received HSP, full selected sheet/calculation, requested return and scripted
decisions). `NATIVE_INPUT_HASHES.json` checks all original retained input/report
bytes against their existing manifests and separately hashes the one actual
new execution. `VERIFICATION_INDEX.json` indexes cases, counts and receipts.

## Verification receipts and source coverage

Every pytest invocation uses `.venv/bin/python` through `local_jobs` with exact
20 GiB RAM, 4 GiB scratch and no wall cap. Receipts verify cgroup memory
21474836480 bytes, swap zero and runtime infinity. Scratch uses the existing
monitored allocated-byte mechanism with possible overshoot and the per-file
hard limit; this work adds no stronger isolation claim.

| Run | Result | Pytest elapsed |
| --- | --- | --- |
| `check001` | 4 passed; initial focused read/custody/reverse checks | 11.29 s |
| `check002` | 33 passed, 2 failed; initial test incorrectly inferred no-hit status from a filename | 97.85 s |
| `check003` | 287 passed: then-current 46 native tests plus existing BLAST-column, result-view, site-action and site-return regressions | 276.94 s |
| `workflow001` | 1 passed; the one actual native execution and full Workflow/closure/replay check | 33.25 s |
| `check004` | 8 passed; eight newly added exact-format/locator cases | 9.54 s |
| `final001` | Exit 4, zero tests collected: relative paths were resolved from the retained run directory | 0.002 s |
| `final002` | 27 passed: focused native custody, original API result-view checks, and default knowledge loading | 37.88 s |

The `check002` correction asserts the actual empty native hit arrays; it changes
no producer behavior. `final001` was corrected by supplying absolute paths,
with no source change. All failed and passing stdout, stderr, JUnit, intent and
local-service receipts remain. There are **297 distinct passing test cases**
across the final successful runs; overlapping reruns are not added as new tests.

Earlier per-run intent manifests honestly cover only the three production
`*blast*hsp*.py` paths. They are not comprehensive snapshots and have not been
rewritten. `SOURCE_BEFORE.json` separately records pre-edit hashes for the eight
owned paths and six producer/calculator paths; `SOURCE_AFTER.json` records the
final hashes. All six pinned unowned files are unchanged.

The final targeted check closes that capture gap: `final002/source_before.json`
and `source_after.json` cover all production Python, all test Python, every
knowledge file including the final root-owned index, and the test launcher:
1,235 files. `source_delta.json` is `{}`. The full 287-test regression and the
one actual Workflow are not retroactively described as running under this
later comprehensive manifest. The final focused check does not repeat BLAST.

A later handoff-time check found concurrent changes outside this workload in
`literature_kinetic_inputs.py` and its test. `POSTCHECK_SOURCE_STATUS.json`
records those differences separately. None of the owned BLAST paths or other
pinned BLAST producer/calculator paths changed after the final check. The
during-run empty delta does not claim that the whole shared checkout remains
permanently frozen.

## Limits

All five programs and both successful native format families are verified with
retained native output through real publication and the selected-column
functions. Only reverse BLASTX was newly executed through the entire Workflow
in this workload. Supplied synthetic partial/invalid fields are labeled as
such. No additional native database/API/HPC execution, model decision quality,
W05 aggregation, literature grading or scientific-credit calibration is claimed.
