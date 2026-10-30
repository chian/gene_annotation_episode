# Final independent B004 result verification

51 tests passed in 363.62 seconds. All production Python files and both owned test modules were unchanged during the final run. The hash manifest records 124 loaded host repository modules and the before/after hashes of production files used by bounded child processes.

Exact invocation from the repository root:

```text
.venv/bin/python verification/tool_graders_native_hmmer_results_integration_2026-10-24/run_verification.py
```

The runner invoked pytest with:

```text
-q tests/test_native_hmmer_acquisition.py tests/test_native_hmmer_results_integration.py --tb=short --basetemp=/home/chia/repos/gene_annotation_episode/verification/tool_graders_native_hmmer_results_integration_2026-10-24/final-pytest
```

## Coverage and results

- 30 capture tests: all 12 retained 064 producer modes, complete-byte custody/replay, wrong original identity, malformed manifest, changed sizes/digests, missing files, symlinks, retained artifact corruption, omitted selected outputs and truthful partial failure.
- 21 fresh tiny native Workflow cases: all six programs and 11 nonempty modes plus zero hits, original replay, selected rows/metrics, duplicate delivery, explicit status, unrequested returns and faults. These cases total 110 selected actions, 110 controller observations and 110 scripted decision calls. No model-service call is part of the fixtures.
- The original source, full native custody, populated numerical sheet, score artifact, actual numerical observation and requested typed parent receipt are connected through production execution/result bindings. Main mode checks compare all available family scalars with exact-associated B003 saved rows and recalculate each saved sheet offline.
- Practical complete cases immediately retain their final actual result gain and obtain exact zero expected future gain. Zero-hit completion returns an empty row array and the original source. Missing exact keys, changed native bytes and explicit wrong biological bindings do not obtain practical completion.
- Re-selecting a row by its exact native key with different metrics preserves source/observation identity. Result gains are 6, 0, 2 for first row, duplicate row and new sibling respectively; the receiving parent gains are 0, 1, 0, 1 including launch. The full four-domain sheet is retained while only two numerical observations are admitted.
- Completed original action replay succeeds after deleting the mutable native attempt directory with capture, grading, status acquisition and process launch prohibited. No controller observation is added.
- False same-provider sources, unselected native row keys, altered numerical returns, original action substitution and altered receipt/capture/preparation/publication journals are rejected.

## Small actual numerical examples

| Native result | Preserved quantities | Result acquisition gain | Parent received-observation gain |
|---|---|---:|---:|
| hmmscan | 20 paired positions; model coverage 20/20 = 1; 72.1 bits; independent E-value 1.1e-24 | 6 | 1 |
| nhmmer profile, forward/reverse | 100 paired positions; sequence span coverage 100/120; 120.9 bits; E-value 6e-39; reverse biological interval [10,110) | 10 | 3 |
| hmmalign trim, test4 | original length 26; model length 20; 20 match residues; 6 trimmed residues; occupancy 1; sequence match coverage 20/26; biological start 3 | 12 | 4 |

Each single-collection example has five total selected actions, five controller observations and five scripted calls: two parent commissions, one launch commission, one resource start and one results collection. The results episode itself has one completed own action and one local observation. The parent count is a disclosed engineering fixture projection, not W05.

## Native mode populations

| Mode | Returned row statuses | Results actual gain | Parent gain |
|---|---|---:|---:|
| hmmalign_align_mapali | 4 published, 10 unbound | 12 | 4 |
| hmmalign_align_ordinary | 4 published | 12 | 4 |
| hmmalign_align_trim | 4 published | 12 | 4 |
| hmmscan_search_ordinary | 1 published | 6 | 1 |
| hmmsearch_search_ordinary | 4 published | 12 | 4 |
| jackhmmer_search_ordinary | 8 published | 20 | 8 |
| nhmmer_alignment_ordinary | 3 published | 10 | 3 |
| nhmmer_profile_ordinary | 3 published | 10 | 3 |
| nhmmer_profile_watson | 2 published | 8 | 2 |
| nhmmer_sequence_ordinary | 3 published | 10 | 3 |
| nhmmscan_search_ordinary | 3 published | 10 | 3 |

The ten mapali seed rows retain their actual inherited measurements and remain unbound because this fixture binds only the four new input sequences. Those ten rows do not manufacture biological observations.

## Evidence and limits

- `VERIFICATION.json`: exact command, pytest arguments, outcomes and source/test hashes.
- `pytest-final.log`: unchanged final passing log.
- `NUMERICAL_EXAMPLES.json`: actual typed rows, returned references, retained artifact IDs and per-case action/gain counts.
- `final-pytest/*/CASE.json`: complete per-case summaries with native plan, capture/prepared records, failures, requested forms and explicit partial-case fixture estimator flags; neighboring Store/action journals retain the actual path.
- `METHOD.md`: inspected paths, actual native versus retained versus synthetic coverage, scope exclusions and fixture limitations.
- `FAILURE_HISTORY.md` and the preserved first-failure logs: three production defects, owners’ repairs and separately attributed fixture mistakes.

All fresh native work used the existing local lifecycle under 20 GiB RAM, 4 GiB scratch and no wall limit. Scripted choices and parent continuation are fixtures; incomplete fault cases explicitly use a fixture base estimator while retaining actual operational credit and completion validation. No LLM investigation, API, HPC, authentication, pending NCBI RID, literature or W05 coverage is claimed. This completed the assigned B004 verification workload, not the broader immutable tool-library goal.

## Critical production hashes from the final run

```text
5f0654cd1f449b2a094a06eadee2fc666dd2a42d845c1feea76767bdafb26f87  gene_annotation_episode/native_hmmer_acquisition.py
83bfa33d7a7032876df20c499c075d3273b65dfc39174824ab46abbaad20799d  gene_annotation_episode/native_hmmer_results.py
56a9136b2d8aea78546f2a7fad45d53ffbdf4267b589369ad07d361d5e737490  gene_annotation_episode/native_hmmer_result_publication.py
7c5d0a30d0e0a8f6bef547aa983c0ab542e9f035e82f640e28b70d41a5c10430  gene_annotation_episode/native_hmmer_result_worker.py
b4a7f8de2bfc75df80a516ebfb824fcd428c45ad2fe2d0594cd336090849a8f2  gene_annotation_episode/hmmer_native_result_views.py
6de292d42386f9185799757cb9b8562595962e0b6f67c82fe08dc248198b058c  gene_annotation_episode/execution_episodes.py
```
