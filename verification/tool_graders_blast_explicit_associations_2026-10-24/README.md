# H1 shared BLAST explicit-association verification

All new numerical examples are synthetic. This workload changed only
`gene_annotation_episode/blast_database_grader.py`, added
`tests/test_blast_explicit_associations.py`, and wrote this verification directory.
It did not execute BLAST, submit or acquire any remote job, use an LLM, change
annotation scoring, or touch the separate completed NCBI RID verification.

## Implemented contract

`build_database_sheet` accepts keyword-only `description_bindings` and
`sequence_identity_bindings`. Both omitted/None preserve the legacy branch.
Both lists select the explicit branch; one missing list raises
`blast_explicit_binding_pair_required`. Empty lists prove no metadata link or
cross-hit identity. The calculator formulas and native alignment geometry are
unchanged.

Each exact metadata link uses the original report/hit/description ordinal, the
literal four-field native identity snapshot, actual metadata namespace/value,
source and JSON pointer, and linkage provenance. Associations retain
`native_identifier`, the bound metadata row's actual `accession`,
`metadata_identifier`, `description_binding`, and the original `source_locator`.
Malformed/contradictory links have localized diagnostics; the original bindings
and metadata stay saved. An unbound record cannot attach through accession
matching. Contradictory identifiers/taxa at one exact metadata source/pointer
remain unavailable. Other independent records and usable HSPs survive.

Cross-hit grouping uses only compatible explicit SHA256 full-sequence records
with matching reference molecule and observed native length when present.
Literal labels, accession equality, partial traceback equality and
`reference_metadata.sequence_group` cannot merge explicit-path hits. Conflicts
within a hit, at one source record, or between digest/operand declarations are
exposed without selecting a winning record. The full original input binding
arrays remain in the saved sheet. Unresolved groups are explicitly described
in calculator assumptions as separate model components, with no claim of
measured sequence identity or independent experiments.

The builder validates supplied relationships. Artifact custody, authorization,
and evidence that a supplied full-sequence record belongs to the actual hit are
the caller's responsibility. It neither acquires those records nor recomputes a
digest from unavailable sequence bytes.

## Checkable numbers

The saved `synthetic_sheet.json` retains native hit indices 4 and 9, original
description ordinals 2 and 3, and functions F and G. Native preferred identifiers
`4` and `9` bind to actual source identifiers `fig|562.1.peg.7` and
`fig|562.2.peg.7`. Both HSPs have 5 paired/identical positions in operands of
length 10: query and reference paired coverage are both 0.5. Native E-values
are measured zero. Maximum native bit scores are 20 and 18.

| Saved-sheet calculation | F kernel mass | G kernel mass | Conditional F weight | Conditional G weight |
| --- | ---: | ---: | ---: | ---: |
| Temperature 2, equal priors | 1 | 0.5 | 0.6666666666666666 | 0.3333333333333333 |
| Temperature 1, equal priors | 1 | 0.25 | 0.8 | 0.2 |

These are the existing conditional reference-function kernel weights, not
calibrated annotation confidence. No database population profile is supplied,
so representation adjustment remains unavailable.

`counterexamples.json` preserves full inputs, sheets and calculations for:

- Compatible full-sequence bindings: two native hits form one group, maximum
  bit score stays 20, and the two distinct functions each receive mass/weight 0.5.
- A wrong original description ordinal: only that metadata link is unavailable;
  the native 20-bit alignment and 0.5 paired coverage remain.
- A native/metadata taxon conflict: the conflicting source assignment is excluded
  while the native taxon, alignment and independent function survive.
- Partial geometry: 5 observed paired query positions remain available, but
  complete paired coverage is null when another HSP lacks traceback.

Recalculate only from the saved sheet:

```sh
.venv/bin/python verification/tool_graders_blast_explicit_associations_2026-10-24/recalculate.py
```

This writes `recalculated.json`, checks both numerical answers, checks that the
saved sheet bytes did not change, and prohibits parser calls, sheet rebuilding,
socket creation and subprocess execution during recalculation.

## Regression provenance

`legacy_prechange.json` contains ten complete synthetic pre-edit input/output
snapshots and calculations, captured before changing production code. The
tests compare full legacy outputs with both omitted binding arguments and
both explicitly None. No new keys or changed numeric results appear in those
legacy outputs.

The original production module hash captured with those snapshots is
`cb023aff2d9acde35587cb50773b14ba18203557452d1af0fa9d085b21fa0da8`.
An original source copy was not retained at snapshot time. For the historical
caller baseline, `reconstruct_prechange.py` reversed only this workload's edits
in a separate verification file and required that exact original hash before
writing `blast_database_grader.prechange.py` (39,143 bytes).
`run_prechange_callers.py` verifies the hash again, loads that copy under the
canonical module name in a fresh Python process, and runs only the historical
`tests/test_blast_binding.py`. Production files are never replaced. The saved
`implementation.diff` compares the verified original with this implementation.

The initial wider run is retained as `regression.log` / `regression.junit.xml`.
One new test fixture initially assigned contradictory sequences to the same
source pointer when intending to test different source records; its pointer
was corrected. All 84 new tests then passed. The final affected regression is
`current_callers.log` / `current_callers.junit.xml`: 218 passed in 37.71 seconds.
It covers the new contract, all shared BLAST graders/readers, the existing API
service, source views, publication, and typed episode returns. The source and
tests outside this workload were left untouched. `verification.json` records
the exact historical before/after comparison and commands.

## Inspection and limits

Read the complete database grader, pairwise grader, native grading readers,
BLAST native protocol/geometry, reference metadata readers, convenience grader,
grading artifact storage/resolution, and relevant tests. Read the complete
affected publication functions `_grade_supplied_result`, `_source` and
`_import_blast`, including their grading, native retention and typed result
construction. Read the immutable authority, repository AGENTS.md, grader goal
record, relevant work-status row, H1 contract and proposal section 5.

Existing regressions include retained native BLAST pairwise JSON/tabular output
and offline API/episode communication fixtures. The new explicit association
path uses synthetic inputs; actual BV-BRC native execution and its new
selected-tool-to-child integration are separate H2/host work. No live resource
availability or new full BV-BRC episode path is claimed here.

The pre-change historical caller run finished with 11 passes and 15 failures.
All 15 failure identities **and failure messages** exactly match the historical
file's failures in the after-change wider run. Eleven concern the retired
annotation scorer, two concern exhausted scripted runtime choices, and two
expect a removed CLI attribute. `prechange_historical.log` and its JUnit file
retain the baseline. No historical tests or unrelated production modules were
changed to address these failures.
