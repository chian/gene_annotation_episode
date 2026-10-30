# Workload 299: existing BLAST regression verification

The scoped repair is complete: **34 passed, 0 failed, 0 errors** in 140.80 seconds through `local_jobs.run_local_job`, with 20 GiB RAM, 4 GiB scratch and no wall-time cap. Final source hashes were unchanged between launch and the postrun observation. No production file, scoring-sheet definition, calculator, annotation-credit function, episode prompt or runtime task choice was changed.

## Implementation

Updated two owned test modules. `test_blast_result_views.py` is unchanged. Retired annotation scoring now has explicit `AnnotationScoringUnavailable` assertions separate from native-result, extent, source custody and typed-return assertions. Protein fixtures now declare protein operands and forward protein intervals. Translated fixtures use coherent 6 nt / 2 aa correspondence. The CLI test patches the actual shared construction port.

The legacy `public.blast.search/collect` fixtures still check retained native bytes, a single original provider handle, cancellation recovery, protocol waiting and exact receipt replay. They also verify that annotation root rejects those execution selections without a completed action. Runtime coverage is preserved through the actual current API child: separate selected status requests, cancellation after retained submission response, same-run reconstruction, exact one-submit behavior, one observation per completed own action, original fetched-result replay and the requested native HSP form reaching its parent. No default annotation formula is supplied.

## Verification

| Run | Passed | Failed | Errors | Meaning |
| --- | ---: | ---: | ---: | --- |
| checks_001 | 17 | 15 | 0 | Unmodified three-module reproduction; original tests and failing logs retained.|
| checks_002 | 33 | 1 | 0 | Repaired contracts; one added test had an incorrect retained-snapshot glob.|
| checks_003 | 34 | 0 | 0 | All three modules, including corrected cancellation recovery.|

The initial 15 failures comprise 11 retired-scorer expectations, 2 obsolete root execution selections and 2 stale CLI monkeypatch locations. Each has a separate entry and production-path trace in `DIAGNOSIS.json`.

These are numerical test examples from the existing scoring-sheet fields and functions, not new grader implementations:

| Program | Identical pairs | Query paired coverage | Reference paired coverage |
| --- | ---: | ---: | ---: |
| blastn | 7 | 0.5833333333333334 | 0.3888888888888889 |
| blastp | 7 | 0.5833333333333334 | 0.3888888888888889 |
| blastx | 2 | 0.5 | 0.1111111111111111 |
| tblastn | 2 | 0.16666666666666666 | 0.3333333333333333 |
| tblastx | 2 | 0.5 | 0.3333333333333333 |

All five examples retain bit score 0, raw score 12 and E-value 0 as measured zero. Function probabilities remain null without function assignments. Saved database-sheet recalculation matches the retained calculator output. The actual API-child example returns bit score 31.5, raw score 60, E-value 0.00001 and native identity 6/8; its selected three-column window has 2 identical pairs and 1 substitution, query coverage 3/8. Source-only references remain without an invented full sequence. ZIP bytes, malformed/partial native results, unreceived-HSP rejection, scope checks and tampered-record rejection remain covered.

## Original broad run: read-only diagnosis

Worker 1674733 and pytest 1674741 were verified against their command lines and original lifecycle identity. At 14:17:08Z, the earlier Homology state still contained 15 actions/model calls/observations, but all five episodes had yielded. The same pytest process had an open database and active archive writes in `composed-r8cqvo0o`, a subsequent composed-workflow case. This proves progress into other work. No Python stack or per-validator timing was obtained; an infinite loop or a particular expensive validator is not established.

The original native result ended at 14:19:49.872702Z with exit 1, no resource or execution failure, and 103,907,328 observed scratch bytes. Its unchanged result is **226 passed, 15 failed, 5 errors** in 2310.71 seconds. Root recovered its terminal receipt in `RECOVERED_RECEIPT_001.json`; 299 did not signal, restart, cancel or collect the original job. Its three large fixture timings were 457.585 s, 832.920 s and 692.090 s, covering distinct Homology, pairwise and composed cases.

All five setup errors share the pairwise fixture's before/after provenance assertion at line 438, after its workflow and numerical-output writes. Exact manifests show nine changed source files:

- `domain.py`
- `execution_episodes.py`
- `execution_progress.py`
- `infernal_result_presentation.py`
- `literature_experimental_prompt.py`
- `literature_optical_storage.py`
- `native_blast_acquisition.py`
- `practical_execution_operations.py`
- `state.py`

Exact before/after hashes are in `broad_source_provenance_differences.json`. These source changes prevent treating that fixture as stable-source verification. They do not alone prove a numerical defect. No broad-run end-of-run source snapshot is reconstructed.

## Evidence and limits

- Full failure diagnosis: `DIAGNOSIS.json`.
- Initial tests: `initial/tests/`; initial native receipt and failures: `checks_001/`.
- Final command, native receipt, JUnit and complete logs: `checks_003/`.
- Numerical example artifact identities: `NUMERICAL_VERIFICATION_EXAMPLES.json`.
- Reviewable test changes: `CHANGES.patch`; final evidence and authority review: `FINAL_REVIEW.json`.
- Original run observations: `live_observation_001.json`, `live_observation_002_terminal.json` and copied original evidence with its manifest.
- Every production Python source and owned test has a retained launch SHA-256; the final postrun comparison is empty. Authority documents have separate hashes.

Final owned test hashes:

- `tests/test_blast_binding.py`: `a2744af7df3bcbe1b38e539d345070278b2387e8a1fdfb690b422fbe3075f1e6`
- `tests/test_blast_result_views.py`: `cae752a1174f4db7486e46b43fdcb4e910b3e9e4b8f3148ef9ade4bcefee0a9c`
- `tests/test_blast_typed_return_integration.py`: `911a5bb051cfca380cea14eaee529e5579f757d9df480d42359c635f548134fc`

No new production defect was established by 299. This is offline regression verification with synthetic protocol/native-format data. It does not establish live API/HPC operation, arbitrary transport-cancellation recovery, every BLAST program or resource route, or completion of workloads 297/298. The original broad failures remain preserved and separately qualified.
