# Generic VDB execution consumers, 671

Implemented the assigned 670 generic-consumer boundary in
`execution_episodes.py`, `practical_execution_operations.py` and
`execution_progress.py`. The result assignment and dispatch recognize exactly
selector v1/v2, reuse the shared original-operation validator and existing
versioned result provider, and retain original source/artifact/child custody.
Practical admission uses the common job-v3 validator and actual bound variants;
its only new practical-source condition identifies an unbound v3 variant in the
existing diagnostic. V3 descriptors alone add `native_job_version`, the original
operation's `native_output_format`, exact v2 selector and deterministic reader/
projection/fact metadata. Complete legacy descriptor shapes remain unchanged.

The implementation keeps existing native attempt ownership, selected allocation,
managed two-stream output, capture, typed return, bundle acquisition credit and
ordinary completion paths. No prompt, TASK/STEERING, communication, historical
schema, score, episode type or retry policy changed. The source trace and exact
baseline diff are in `CONSUMER_TRACE_001.md` and `SOURCE_DIFF_001.patch`.

## Completed bounded verification

All application imports and tests ran through the existing bounded529 runner,
with explicit check005 dependencies, 20 GiB memory, 4 GiB scratch, zero swap and no
wall cap. The three original handles were collected terminal and quiescent;
source, dependency, standard-library and binary pins stayed unchanged within each
frozen attempt. All execution audits have no outside modules or unbound mappings,
and retained original fixtures stayed unchanged.

| Attempt | Cases | Passed | Failed | Return code |
| --- | ---: | ---: | ---: | ---: |
| check128_vdb_episode671 | 225 | 200 | 25 | 1 |
| check128b_vdb_episode671 | 23 | 23 | 0 | 0 |
| check128c_vdb_episode671 | 5 | 5 | 0 | 0 |

There are 228 distinct final passing cases: 44 new 671 consumer cases, 35 old 632
episode-wiring cases, 39 old 630 practical cases and 110 old 651 tool-information
cases. A passing case was not restarted to clear another failure. The original
25 failures remain recorded exactly in `VERIFICATION_001.json` and the original
case reports:

- 20 new catalog fixtures incorrectly unpacked the complete resource catalog as
 one utility row. Selecting the exact named utility row fixed the fixture;
 all 20 passed in check128b, together with three added cases.
- 5 old 651 descriptor fixtures could not find their explicitly required support
 files because the initial command omitted them. Only those five were rerun in
 check128c with `LEGACY_INFORMATION_001.json` and `TOOL_INFO_BEFORE.py.txt` staged.

No owned production code changed after the first snapshot. `SOURCE_PINS_001.json`
records the exact source/test relationship: the full-path test body and practical
fixture stayed unchanged; only the catalog test was corrected and three new
cases were added. `FINAL_SOURCE_COMPARISON_002.json` records the later comparison.

All four configured full-path cases passed: entry and paths_all with controlled
native return codes 0 and 7. They exercise actual practical reservation/receipt,
original handoff, capture, real worker logic within the bounded test process,
versioned publication, requested
v2 projection, immediate-child typed delivery, source/artifact/logical-reference
checks, one captured-bundle acquisition worth 2 configured operational units,
exact future expectation 0 and unchanged same-key replay. The controlled entry
returns normalized ACGT with native length 4, returned-symbol count 4 and explicit
returned-sequence length basis. The failed native cases preserve usable facts
while retaining native failure and failing the local successful-output validation.

## Evidence limits

The native lifecycle, wrapper output and worker launcher are explicitly controlled
fixtures. Real worker logic executes inline inside the bounded test service.
671 ran no bioinformatics executable, download, local database BLAST, remote job,
configured model or shared-method-loop Workflow. Direct consumer calls verify
that internals add no synthetic observations; they do not create a Workflow
observation. Authentic native/Workflow checks, ordinary one-action/one-observation,
and original 652/654 replay remain separately owned by root. The five material/
source dispatch entrypoints belong to root 666; 671 tests typed result and received
reference resolvers. The 659 selected-repair implementation was not edited here.

Root 674 subsequently changed worker observation factoring and the results provider
and added a failure-only publication route. The 671 frozen snapshots remain valid
historical evidence; this report does not claim verification of 674's new repair.
The final source comparison identifies the worker/results changes. No successful
671 suite was repeated for that separate work.

The collect-description wording proposal in `CONSUMER_TRACE_001.md` is draft-only.
No library instruction/template change was applied. The original objective and
entire OPERATING PRINCIPLES were reread, and ports 670, 664 and 665 were reread before
completion. No GOAL.md, replacement goal, formatter restoration, inventory update
or whole-tool completion claim is part of this work. Unmeasured native variants,
alias/accession mappings and remote resources remain unverified.
