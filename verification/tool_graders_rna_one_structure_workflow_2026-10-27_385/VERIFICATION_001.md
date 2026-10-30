# One retained RNA structure: Workflow and provider verification

## Scope and exact change

This packet verifies the existing retained-comparison route for one explicitly
selected saved RNA input. It adds no selector version, calculation mode, episode,
scientific source, credit rule, or continuation rule. The only production change
owned by 385 is the opening branch in `rna_structure_comparison_prompt.py`.
The released diff is retained in `PRODUCTION_DIFF_001.patch`.

The predicate requires one saved baseline, `question.kind="scan"`, no comparisons,
no selected energy, no selected topology sites, and only structures projections
for that baseline. Any valid subset/order of requested structure fields matches.
The new opening, printed by root for user feedback before coding, is:

> Return the requested sequence or structure information for the parent’s single selected RNA input supplied-RNA. Include only the explicitly selected fields below.

The rest of that TASK is unchanged. Other pair/scan TASKs are byte-identical to
the retained baseline. The actual request uses the existing complete schema,
with `fields=["original_sequence","dot_bracket"]`; pure checks also cover reversed
order, dot-bracket alone, other valid field subsets, multiple structure
projections, and exclusion of energy/alias/non-structure modes from this branch.

## Actual path and returned information

`helpers.py` reuses original 360's actual Workflow and 372's registered comparison
form/selector builders. Only the controlled parent's third chosen commission
changes from the earlier saved-sheet example to this one-input request. Original
assignment validation, actual received-form inheritance, saved-source authority,
collection, typed report admission, practical completion and provider rendering
remain production operations.

The original setup runs `analyze_rna_secondary_structure_features` in
`supplied_features` mode with `energy_mode="none"`, sequence `GGGAAACCC`, supplied
dot-bracket `(((...)))`, and no energy model. It completes successfully with native
return code 0. This is a supplied structure, not a newly predicted fold or measured
energy. `ORIGINAL_SETUP_BUNDLE_001.json` and the case's `original-setup-run/` preserve
that actual subprocess separately from the later retained calculation.

The parent actually receives the full original saved descriptor before the third
commission. The test matches its actual `runtime_report_attempts` form and digest
to the new child's frozen received-report prefix. No descriptor shorthand,
invented second member, synthetic producer result, or source-authority bypass is
used in this one-input case.

The returned scientific payload contains exactly:

| Selected field | Value | State |
| --- | --- | --- |
| original_sequence | GGGAAACCC | present |
| dot_bracket | (((...))) | present |

Existing typed origin/availability qualifications accompany those fields:
`structure_origin="supplied_unknown"`, with `unknown_source_origin`. The parent
forwards only the requested structures fact group. No energy, pair-change,
site-change, rank, second structure or saved-input descriptor is added to that
forwarded form.

The deterministic retained-input worker still executes. Its sheet has one
operand and zero comparisons; components have zero comparisons, empty scan
energy/site components, and `baseline_rank_class="not_requested"`. The one scan
member has `energy_state="not_requested"` and null energy, delta and ranks.
This is not a calculator-free route.

## Accounting, custody and model boundary

The original producer directory and supplied input are removed after an evidence
copy is retained. New capture, original local-plan opening and target observation
are then replaced by test failures during the retained stage. Collection and
replay succeed from retained custody. The original receipt bytes, saved-sheet
bytes and completed observations remain unchanged.

The collect-only result episode has one action, one own observation, actual gain 0,
operational credit 0, zero new handoffs and zero newly acquired records. Its next
expectation is exact 0 immediately after validated completion. No extra zero turn
or model-composed completion is required. Sources remain 3→3. The
`native_execution` table remains 0→0, but that table is not proof that no subprocess
ran: the separate original supplied-features subprocess and retained calculation
worker are both explicitly recorded above.

The actual completion proof verifies selected original operand authority,
retained operand custody, and requested projection or explicit unavailability.
Replay of the same selected collect returns the same receipt with no new worker
or observation. `ACCOUNTING_AND_COMPLETION_001.json` contains the original proof,
controller record and exact credit view.

The real results assignment passes through the existing controlled provider
transport. TASK and STEERING are captured in `ACTUAL_PROVIDER_INITIAL_001.txt`.
A second real Workflow chooses status then collect; it has exactly two own
observations and closes immediately after collect. Full TASK is identical across
its actual provider calls and across bootstrap, update, lookup and restored
frames. Output schemas and fixed instructions are preserved. Lookup/restoration
transport checks replay the actual collected receipt; they add no Workflow
observations and are not new decisions after practical completion.

`DOMAIN_TRACE_001.md` records the existing `qualification.domain="pairwise"`
grouping tag. It is retained in typed JSON but neither controls calculation nor
appears in the captured rendered structures text. No pairwise scientific
comparison is claimed for the one-input request.

## Verification runs and source identity

Every pytest run uses `run_bounded.py` and `local_jobs`: 20GiB memory, 4GiB scratch,
`wall_seconds=None`, zero swap, runtime limit `infinity`, and packet-owned temporary
and cache locations. Actual original/retained workers use the same resource
policy. The original setup bundle and retained grading execution receipt are
preserved under check004.

The immutable goal was read in full. The objective and all 16 design principles
were reread verbatim before the production change, after the later source and
domain-consumer investigation, and again after final verification. Actual AGENTS.md, episode/time/practical/task
contracts, accepted 362 plans/addenda, and complete relevant prompt, provider,
comparison, original-source-authority and Workflow consumer paths were inspected.

The production baseline hash is
`42b5c62601af486942414872841ca003bccb1baf7eacdf26d2a556ac7607b1a4`.
The released/tested 385 prompt hash is
`b240339818992fb863a18e622f1147e4c1c3bede851908cd507f0ec6cbaa8525`.
Root may subsequently compose its separate original-RNA form presentation into
the shared file; this packet's tested snapshot and isolated diff remain exact.

- check001: fixture construction failed because an added field description did
  not match the exact registered source schema. Removed only that fixture addition.
- check002: four substantive Workflow tests passed; the provider assertion used
  `dot bracket` instead of the existing `dot-bracket` spelling. Corrected the
  test. Executed snapshot pins were stable. The only live drift was unrelated
  `protein_structure_contracts.py`, retained in the before/after manifests.
- check003: four substantive Workflow tests passed; a provider assertion looked
  for `result_receipt_key` on the receipt body rather than the projection row.
  Corrected only that test lookup. All 840 live and snapshot pins were stable.
- check004: **98 passed in 1325.11 seconds**: 18 new one-input tests, 34 existing
  results-TASK tests, 44 existing provider tests, and the two selected existing
  actual 372 pair/compact-scan Workflow tests. The bounded receipt reports return
  code 0, elapsed 1325.983545585 seconds and observed scratch 127594496 bytes.
  All 840 executed snapshot pins remained unchanged. The receipt SHA256 is
  `00e9c25c87501d1a73acc2ba58da7fc87b77a60453cfe78ae08bbb2bcd48d571`.

Concurrent work changed 14 live files among those 840 snapshot inputs. Exact
tested/end-of-run hashes are recorded in `LIVE_SOURCE_DRIFT_001.json`:
`communication.py`, `execution_episodes.py`, `literature_experimental_prompt.py`,
`literature_perturbation_storage.py`, `literature_perturbation_summary.py`,
`literature_perturbation_summary_storage.py`, `protein_structure_contracts.py`,
`protein_structure_formats.py`, `protein_structure_sequences.py`, `providers.py`,
`rna_structure_comparison_prompt.py`, `rna_structure_presentation.py`,
`scientific_process_prompt.py`, and `tests/test_rna_comparison_results_prompt.py`.
Package filenames in that list are under `gene_annotation_episode/`. The live
prompt at the end of this run had SHA256
`15cae025f7f802b85a832176711524fa33f17ed394c16fc4f32fb0a7d5a68f22`.
This successful run covers the executed snapshot, not those later live changes.
Root owns the subsequent check against current shared original-RNA wiring.

The two existing 372 compatibility cases use explicitly synthetic retained
producer values; their Workflow, selected actions, authorization and returns are
real. Their fixture energies are not presented as native measurements.

No live model, API/HPC request, new folding prediction, new energy evaluation,
literature grader, W05 aggregation or whole-RNA-tool completion is claimed.
Original single-input numerical presentation and root's later shared integration
remain separate work.
