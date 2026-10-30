# Common HMMER alignment-map integration — authoring packet 526

Status: implementation and tests authored; static Python parsing passed.
No application/scientific import, pytest collection/execution, compiler, native
program, network request or job was run by this agent. Numerical conformance,
new native formats, requested episode returns and live-resource verification
remain pending root execution. No R1–R7 accounting or inventory row changed.
This is the accepted R1 shared-reconstruction repair and specific R2 declared
GSC/BLOSUM/sampled-PB gap. It is not a new HMMER family implementation.

Authority remains the original user attachment
`/home/chia/.codex/attachments/6960b4a1-b2e0-46d4-8003-fcb7685a2232/pasted-text-1.txt`.
AGENTS.md and the complete 581-line 516 implementation contract were read.
The objective and all ten operating principles were reread verbatim after
native/source examination and before handoff. GOAL.md was not read; no goal or
scope replacement was created. The relevant inventory's still-pending
native/alimask and native/hmmbuild rows were inspected as historical evidence,
not as proof that their already implemented algorithms were absent.

## Implemented boundary

The original nine-field `hmmer_alignment_preparation_sheet_v1` and
`hmmer_alignment_preparation_components_v1` remain. The only optional input
record addition is `map_reconstruction_context` on the first alimask source
alignment, also retained in the grading envelope metadata. Existing row keys,
WT/RF/MM events, complete original artifact bytes, native mapping rows,
requested/returned endpoints and coordinate tags stay authoritative.

`hmmer_alignment_preparation_calculations.py` owns common digitization, ordered
Easel Kahan DSum, divide then separate scale, PB consensus/counting/weighting,
fragment marking and float32 occupancy/map. It calls the independently owned
524 raw GSC/BLOSUM helpers and 525 row sampler through their accepted ports.
Neither helper normalizes weights. PB sampled consensus never supplies the
weight denominators: the implementation rebuilds counts over all source rows.
Sampling occurs only above 50,000 rows, uses 10,000 rows, rejects more than 5,000
sample fragments, and retains sample/all-sequences/all-columns fallback state.
The selected CLI seed and internal PB seed are distinct retained quantities.

The shared normalization trace contains raw finite nonnegative weights, the
ordered raw sum, population N and zero-sum flag. Zero raw sum uses the native
`(1.0/N)*N` operation sequence rather than substituting literal one. GSC tree
and BLOSUM cluster arrays remain auxiliary derived operands, not biological
phylogenies or confidence scores. Sample ordinals are zero-based, sorted and
joined to exact source-row record keys. Final map/occupancy positions are
one-based. Final weights, weighted residue counts and occupancy fractions
remain dimensionless; no new score or observation is introduced.

`native_hmmer_preparation_driver.py` now calls the common parser and
reconstruction. Its competing `_stockholm_for_map`, `_alimask_map`, float32
helper and weighting calculations were removed. Preflight reads original
staged bytes, checks the first MSA and preserves a malformed/non-UTF8 later
suffix as unprocessed evidence. Genuine first-record failures, partial/orphan/
malformed WT, ambiguous identity, empty maps and after-last-match native
ali2model requests retain explicit failure behavior. An MM grading issue is
not a new execution gate. The new closed preflight reason is
`map_configuration_unavailable`; acquisition imports the same reason/context
sets, so no acquisition or native-contract edit was required. Legacy reasons
remain readable.

The existing hmmbuild native MAP/resaved alignment route is unchanged. Fast
mapping without an explicit alphabet and non-Stockholm/Pfam source grammars
remain specific unsupported prerequisites; no broader format-completion claim
is made. No reconstruction replaces available native MAP values. Pure readers/calculators
perform no acquisition, execution, Store writes, model calls or credit work.

## Original producer association and compatibility

`resolve_alimask_map_context` consumes only the authenticated original
operation, software record, eight-field input occurrence and selected CLI
tokens. Binding requires the original actual and expected executable hashes
to equal the profile's recorded digest. The exact source-profile registry is
retained in the context, not inferred from the current installation or version
banner. Effective PB seed 42 is a fact of that profile, independent of CLI seed
0, 42 or 17. Unsupported known actual digests remain recorded literally and
produce unavailable profile/configuration.

Root accepted this precise clarification to the 516 implementation contract:
`producer.executable_sha256` is null only when the original bundle's
`software.actual_sha256` is null, and then binding is unavailable, profile is
null and effective_pb_config is null. The expected hash stays in its original
bundle field and is never substituted for an unobserved actual hash. This
clarification does not alter the goal or choose another producer.

`effective_metadata(..., include_map_context=True)` is explicit for new
result-worker grading and publication preparation. Saved publication validation
opts in only if the original retained stable metadata already has the field.
Thus an old frozen publication is not upgraded or numerically recomputed.
Every caller was traced: production `_grade`, new publication preparation,
`validate_prepared_grading`, and test plan constructors. The result-worker's
saved receipt path still bypasses `_grade` entirely.

The distinction between semantic partial work and envelope validation is
intentional:

- A valid-shaped context whose SHA, occurrence, source-profile hash, effective
  PB seed or selected CLI seed conflicts yields dependent reconstruction
  `map_context_invalid`. The source-defined example in
  `test_semantic_context_conflicts_preserve_counts_and_native_endpoints` retains
  3 source sequences, 4 columns, one native mapping row and native returned
  source/target spans 4/2; the derived mapped-position count remains unavailable.
- A structurally malformed or illegally placed context invalidates the saved
  sheet shape. `_Saved` also rejects illegal context placement in non-alimask
  rows/native rows, by root's explicit follow-up coordination.
- Saved projection does not authenticate a changed numerical operand merely
  because it has a valid JSON shape. `_Saved._map_context` rejects disagreement
  between metadata, first source record, original occurrence or settings,
  including both metadata and sheet being altered together. It also checks an
  artifact-only grading envelope with no numerical sheet. The publisher
  independently compares retained metadata with the authenticated original
  bundle. These checks do not recalculate saved values or erase their original
  retained artifacts.

The narrow publisher compatibility edit was explicitly authorized by root
because unconditional metadata derivation would reject all old alimask saved
publications. A real closed 277 alignment-to-model publication was found and
pinned for the copy-only regression. It originally retained metadata `{}` and
published `[3,14,12,1,1,null]` for the six selected quantities (source sequences,
source columns, RF columns, requested intervals, native mapping rows, requested
union). The test preserves these exact frozen values and absent context while
forbidding native work, acquisition and grading. This author only inspected
that retained fixture; the new replay test has not run.

## Full consumer trace inspected

The complete relevant production paths were inspected, including native
preparation contracts/compiler, driver, acquisition, pure worker, result
worker, publisher, saved views, result `execute`/`facts`/`credit_view` and
`NativeHmmerPreparationReturns`. The common Stockholm parser/checksum path in
`hmmalign_inputs.py` and the actual existing Workflow harness were read.
`EPISODE_STRUCTURE.md`, `TIME_AWARE_ESTIMATION.md` and the tool-grader goal/
principles document informed the unchanged execution/credit boundaries.

The resulting path remains selected original job/options/software -> existing
local execution -> original native bundle -> qualified captured occurrences ->
new grading metadata context -> common parser/sheet/calculator -> immutable
numerical artifacts -> saved scalar projection -> parent-requested typed facts.
The original native attempt remains one acquired contribution. Added weights,
columns, diagnostics and validation checks add no action, observation, score,
continuation rule, episode type, prompt/template or resource substitution.
No shared runtime/communication, model binary/HMMER2 decoder, helper-owner,
literature or W05 files were edited.

Native inspection covered the complete alimask translation unit and complete
relevant PB/GSC-normalization/fragment entrypoints and configuration in the
retained Easel sources. Source identity does not prove execution equivalence.
The 524 and 525 owners retain their independent source/harness evidence.
`SOURCE_MANIFEST.json` pins support files and dependency hashes.

## Checks and pending evidence

`AST_CHECK.json` records successful stdlib AST parsing of all 13 changed owned
Python files and no trailing whitespace. `OWNED_DIFF.patch` compares original
owned before snapshots with final source. The checkout has no .git metadata,
so no Git baseline was substituted for the pre-edit snapshots.

There are 24 new test functions and 54 literal parametrized cases, all
unexecuted: 48 context/numerical/preflight cases, three new weighting Workflow
cases, two saved publication cases and one metadata compatibility case.
`UNEXECUTED_TESTS.json` lists exact selectors and retained-regression targets.
The three Workflow cases reuse the existing `run_case(job_override=...)`
harness, request mapped count/source counts/native mapping checks, assert
original custody and sheet/return equality, then make original native paths
unavailable and forbid work during replay. Existing action/observation and
received-fact accounting assertions remain part of those cases.

Constructed numerical examples are explicitly synthetic, not authentic native
measurements. `AAAA,AAAA,C--C` gives expected raw GSC `.25,.25,.5` and BLOSUM
`.5,.5,1`, normalized `.75,.75,1.5`, map `[1,4]` at final symfrac .6/fragthresh
0. A float32 accumulation test uses weights `16777216,1,1` in different source
orders and distinguishes established empty map `[]` from unavailable `null`.
PB tests include N=50,000/50,001/130,001, strict 5,000/5,001 fragment boundaries,
sample/all-row/all-column fallback, all-row denominators and source-row joins.
These expectations still require root execution and native conformance.

`native_map_oracle.c` and `ORACLE_RECIPE.md` are uncompiled/unexecuted diagnostic
recipes. They complement 525 sampler and 528 raw-weight oracles. Root must
retain actual native/library/compiler identities and lifecycle receipts before
claiming authentic agreement. Existing completed native fixture generators
must not be rerun merely to stage retained dependencies.

All implementation accounting stays unchanged until that evidence exists.
The prior `PRODUCTION_FROZEN_MANIFEST.json` is retained for root's already
frozen MinHash check004. Root then authorized the single additional saved-view
placement check; `FROZEN_MANIFEST.json` records the final handoff, including that
new view hash and final tests. No other production changes followed that first
freeze.
