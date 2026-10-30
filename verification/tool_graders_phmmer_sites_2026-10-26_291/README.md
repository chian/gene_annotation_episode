# phmmer selected-site publication and native-version verification

Independent workload 291, 2026-10-26. This worker changed only
`tests/test_phmmer_site_publication.py` and this verification directory. It did
not change production code, existing tests, progress accounting or requirements.
The authoritative goal, all sixteen principles, the adopted 282 proposals and
both frozen 284 contracts were read. The objective and all sixteen principles
were reread verbatim after native examination and before handoff, followed by
the current contracts. Permanent documents are unchanged.

## Verification results

| Run | Result | Meaning |
| --- | --- | --- |
| check001 | 9 passed, 5 failed; 45.84 s | Initial new-test error: passed a frozen BindingContext schema instead of detached `plain` JSON. Production metadata rejection and saved-version tampering cases passed. |
| check002 | 14 passed, 1 failed; 66.25 s | All retained-output checks passed. The first tiny Workflow completed the entire scientific return, then a final test assertion incorrectly expected a child-action journal `result` field. |
| check003 | No tests collected; exit 4 | A relative explicit test path was resolved against the isolated run directory. No native job ran. |
| check004 | 1 passed; 2.53 s | Independently reconstructed the already completed check002 Workflow and verified original parent admission, exact replay, frozen validation, tamper rejection and redelivery without another submission. |
| check005 | 15 passed; 75.77 s | Corrected full suite, including a second explicitly authorized tiny Workflow run. |
| check006 | 9 passed; 38.84 s | Focused original-metadata rejection cases, including newly requested missing/non-object `operation` cases, against the final stable production source. No new phmmer search. |

These runs overlap; their pass counts must not be added as unique coverage.
Each directory preserves full stdout/stderr, JUnit, local execution metadata,
before/after source and input hashes, and the exact command. Every test process
ran through `gene_annotation_episode.local_jobs.run_local_job` with
`.venv/bin/python`, 20 GiB RAM, 4 GiB scratch and no wall-time cap. The actual
HomologyResults parser and both tiny native jobs used those same resource limits.

All recorded sources were unchanged during check001–check004 and check006.
During check005, root hardened `alignment_site_native.py` so missing/non-object
original HMMER `operation` metadata raises `site_native_operation_invalid`.
That single changed hash is preserved in its receipt. The targeted check006
tested the final implementation with `changed_sources=[]`; another live native
run was not needed for this validation-only change.

## Exact verified paths

The historical retained path uses the existing `test_homology_results.prepared`
helper, the original query FASTA, complete reviewed-reference FASTA, stdout,
hit table, domain table and job manifest from `cases/gene_001/jobs/homology_001`.
`NativePhmmerInput` feeds the actual bounded `HomologyResults.extract` publisher,
which publishes all 20 original alignment observations. This is retained real
native evidence, not a new full-reference search. The original manifest describes
an empirical inspection, so no episodic launch receipt was fabricated for it.

Selected real alignments then pass through `ToolRegistry.sequence.sites` →
retained `tool_grading_artifact_v1` → `AlignmentSiteActionRecords.own_action_results`
→ `requested_site_projections` / `project_site_action_return` →
`form_with_facts` / closed-schema validation → saved frozen facts. This branch
uses explicit journal/context fixtures from the existing host-boundary tests;
it does not by itself claim Workflow commissioning.

The new full Workflow test uses `test_resource_episode_branches.resources`:
one 253-aa query, one `reference_self_fixture` sequence, actual HomologyJobs
executable and caller-owned CPU 2. The original `HomologyEpisodes` selected
`job_launch` performs environment/configure/stage/submit/handoff operations;
the separate `job_results` selects `homology.extract`; the parent receives the
actual alignment reference and commissions a scientific child selecting
`sequence.sites`; its requested typed form reaches the parent. The root has no
scientific tools and no initial alignment receipt. No operation receipt or
caller source ID was fabricated or preloaded to satisfy this path.

Each tiny Workflow has one physical submission, three parent actions, one
scientific-site-child action and ten total completed actions/controller
observations/scripted decision records. The two physical jobs belong to separate
test runs; the second was explicitly authorized to repair the final test
assertion. Direct selected-operation replay and parent redelivery add no actions,
observations, records, model calls or physical submissions. Frozen return
validation succeeds with live site-record access and the calculator disabled.
An altered frozen numerical return is rejected.

## Numerical examples and version identity

Complete sheets, scores and typed forms are retained under
`check005/examples/`:

- `retained_self_sites.json`: positions `[2,0,252,2]` produce four requested
  rows, three unique positions and three identical paired sites. Identity is
  3/3; each whole-protein paired coverage is 3/253. Row order and the duplicate
  are retained; the duplicate does not increase the numerical population.
- `retained_nonidentical_and_gapped_sites.json`: the actual ANGEL2 reference
  window `[197,203)` compares `RFILPE` to `SFRFPN`: six paired sites, two
  identical, four substituted, identity 2/6, query coverage 6/253 and reference
  coverage 6/544. The complete `[197,354)` selection retains all 157 rows despite
  its 12-row preview: 147 pairs, 45 identical, 102 substituted, ten query-gap
  positions, and three query insertion events totaling five residues.
  Selected alignment identity is 45/(147+10+5); paired identity is 45/147.
- `tiny_real_phmmer_workflow.json`: full actual native handle, retained selected
  sheet/scores and admitted parent form from the successful fresh tiny run.

The observed original HMMER engine is `3.4`, read from the original bound
`hmmer_search_sheet_v1.operation.engine_version`, not hardcoded in the assertions.
The original parser version remains
`phmmer_printed_alignment_with_hmmer_sheet_v1`. The selected sheet preserves the
original alignment/native-artifact identities, full native input, exact query
and reference operands, 253-aa/544-aa lengths where applicable, native geometry,
original-source coordinate mappings and complete numerical ratios.

Deliberately synthetic copies of original grading metadata separately test:
absent grading, absent/null engine version, wrong program, two competing sheets,
empty/numeric/boolean engine versions, and missing/null/string/array `operation`.
Unknown engine version stays null without using the parser version. Invalid or
ambiguous original metadata cannot publish a site source or observation.
Changing a saved site version to the parser version, another engine string or
null is rejected by the own-action host. Original native records remain intact.

Saved-sheet recalculation exactly reproduces the stored scores without mutation
while file I/O, sockets, subprocess creation, HomologyResults extraction and
ToolRegistry execution are disabled. No acquisition or alignment reruns.

## Limits

This verifies the existing flat `HomologyEpisodes` launch/results route plus
the actual scientific site child and immediate parent return. It does not
establish the separate accepted nested resource-branching design, detached
multi-process episodes, a configured-model scientific investigation, production
credit policy, API availability or HPC deployment. Decisions and zero credit
are explicit engineering fixtures. There were no installs, network/HPC calls,
database BLAST runs, literature work, W04/W05 work, prompt changes, controller
changes or annotation-score changes.

No remaining production defect was observed within this verification scope.
