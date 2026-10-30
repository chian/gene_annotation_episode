The final B002 integration suite passed **15 tests in 89.97 seconds** against unchanged source files. This worker changed only `tests/test_minimap2_grading_integration.py` and this verification directory. No production code, inventory rows, resource binding or continuation policy was changed by this worker.

The exact final command, run from `/home/chia/repos/gene_annotation_episode`, was:

```text
.venv/bin/python -m pytest -q tests/test_minimap2_grading_integration.py --basetemp=verification/tool_graders_minimap2_integration_2026-10-24/run-004
15 passed in 89.97s (0:01:29)
```

`run-004.log` retains the test output. `run-004-source-start.json` and `run-004-source-end.json` contain identical SHA256 values for all ten tracked implementation, instruction and test files. `EVIDENCE.json` contains the final exact native command arrays, selected settings, executable digest, original row byte locators, collection artifact references, numerical examples, per-query results and typed child return. Each case's original Store and immutable artifacts remain in `run-004/`.

The final suite contains ten actual pinned minimap2 `2.31-r1302` mapping operations and five explicitly synthetic process/failure operations. Real mapping used the existing bounded runner with **20 GiB RAM, 4 GiB scratch, one CPU, and no wall-time limit**. Every native phase's retained policy is checked. The intentionally waiting synthetic process alone uses its explicitly selected 256 MiB / 2 MiB / one-second fault-test policy.

All six presets were selected and executed: map-ont, map-pb, map-hifi, lr:hq, map-iclr and sr. Each preserved its actual mode, overrides, version, FASTA inputs and native output. The selected command includes `-c --cs=long --frag=no`; `sr` remains unpaired and the native mapper does not consume the original FASTQ quality values. These are tiny engineered inputs, not an accuracy benchmark or biological validation.

Each preset's gapped positive-strand result has query length 5,001, reference length 6,000, query span 5,001, reference span 5,000, **4,998 paired positions, 3 inserted bases, 2 deleted bases and 5,003 alignment columns**. Query paired coverage is `4998/5001 = 0.9994001199760048`; reference paired coverage is `4998/6000 = 0.833`; native identity is `4998/5003 = 0.9990005996402159`. Native AS remains mode-specific:

| Preset | Native AS for the gapped result |
| --- | ---: |
| map-ont | 9978 |
| map-pb | 9978 |
| map-hifi | 4976 |
| lr:hq | 9978 |
| map-iclr | 9966 |
| sr | 9962 |

The reverse-strand result has 5,000 paired positions, native identity 1, query paired coverage 1 and reference paired coverage `5000/6000 = 0.8333333333333334`. The current selected scientific-child test delivered both numerical observations to its parent.

The actual ambiguity fixture uses original query Y versus reference R at one paired position. Both normalize to N in native cs. Its four reported placements have **5,000 paired/cs-equal/alignment columns, 4,999 native matches, 4,999 native block length, nn=1 and MAPQ=0**. The grading result leaves original-symbol equality unavailable because its supplied metadata contains only explicit names and lengths. The selected site operation reads the retained original sequences and correctly reports Y versus R as substituted. Minus-strand site positions descend from original query position 4,999 to 0.

Two identical reference sequences keep separate reference identities. For each exact query, the native output contains one P and one S placement, two distinct references, 10,000 paired-position observations, a 5,000-position query union and 5,000 positions with alternative correspondences. No independence or function-confidence score is introduced. A separate synthetic repeated-row fixture places one exact query's rows at nonadjacent native lines 1 and 4: paired observations are 8, union positions 4, distinct correspondences 4, repeated correspondences 4 and exact duplicate count 1.

The exercised production path is selected `reads.map` → `_native_mapping_async` → bounded `run_mapping` → `project_output` → `_retain_mapping_grading` / `_publish_mapping` → Store native-row admission → the existing numerical placement observation → typed child record return → receiving parent's record receipts. Checks include:

- Original query/reference FASTA bytes and SHA256 values, explicit name/length metadata joins, complete PAF retention and exact original row byte intervals.
- Streamed placement sheets and query-score artifacts attached to the same `minimap2.mapping` source through its metadata artifact, which names the original PAF artifact.
- Saved-sheet placement and per-query recalculation after Store reopening, with socket connection, subprocess launch and native mapping prohibited; sheets remain unchanged.
- One selected native operation, existing placement/source-content observation counts, one parent action and one child action, and one local controller observation per episode. Two scripted decision calls occur; grading and result construction add none.
- Current three-slot scientific-child selection, the substantive selected minimap2 instructions and invocation contract, root execution remaining unavailable, numeric records admitted to the parent, and full sheets/raw rows absent from its working-state projection.
- Exact operation replay and repeated child-form admission without another native call, action, observation or receipt.
- Actual complete empty output with zero reported placements, retained submitted-query rows and an explicit absence-inference limitation.
- Synthetic malformed siblings, native exit 17, nonadjacent duplicates and resource termination. Valid rows retain their numerical sheets; failed/partial populations stay `output_complete=false`, including an unreported query. Resource termination creates no complete-search summary.
- A deliberately shifted grading-row join is rejected before numbers can be assigned to the wrong placement. Store rejects changed line boundaries and wrong reference identity.
- Actual retained ambiguous PAF through `sequence.sites` and `local_example.JobStore.extract`. The latter uses an explicitly synthetic completed-job registration solely to exercise the existing reader; it is not a new detached-job demonstration.

The inspected complete relevant paths include `read_mapping` staging settings, execution and projection; ToolRegistry staging, grading retention, publication, operation status/replay and mapping-site extraction; Store native-minimap2 admission; grading artifact custody; scientific tool-information construction and selected invocation resolution; and `local_example.JobStore.extract`. Native-source review covered minimap2 2.31 `mm_update_extra`, `write_cs_ds_core`, `write_cs_ds_or_MD`, `write_tags` and `mm_write_paf4`, including ambiguity in paired and gap columns, normalized cs symbols, native type categories and original coordinates.

The complete authoritative goal attachment, repository instructions and B002 contract were read before work. After native-source review and again after completing verification, the original objective and **entire DESIGN PRINCIPLES block were reread verbatim**, followed by the complete B002 contract.

Earlier runs remain as historical evidence: the first attempt failed at pytest setup because this verification parent directory did not yet exist and executed no tests; after creating it, run-001 passed 13 tests in 79.26 seconds. Run-002 passed three added/extended cases in 17.24 seconds. Run-003 passed all 15 in 92.49 seconds, but a parser file changed during that process, so run-004 was performed after the pure worker finished and verifies the final unchanged files. These overlapping passes are not added into a unique test count.

No actionable production defect was found in the final exercised paths. Configured-model scientific decisions, annotation-credit aggregation, API/HPC minimap2 deployment, large or multipart-index scaling, paired-end mapping and general site-extraction scoring are not established by this integration suite. No pending NCBI job was inspected, no database BLAST ran, and no HPC work was submitted.
