# Native HMMER local practical binding verification, 2026-10-24

This workload verifies selected local execution and practical completion. It does not establish numerical scientific-result publication. No production files were edited by this verification worker.

## Source and boundary inspection

Read the original active-goal attachment, its complete DESIGN PRINCIPLES, AGENTS.md, GOAL.md, EPISODE_STRUCTURE.md, TIME_AWARE_ESTIMATION.md, PRACTICAL_EXECUTION.md, the original practical contract, TASK_AND_STEERING.md and B004. The original objective and complete design principles were reread after substantial implementation/native study and before finalization. These reports do not redefine the goal.

Inspected the native request/compiler and configured tool declarations; native_hmmer_local; producer staging/sealing/replay; LocalPracticalOperations; PracticalResourceEpisodes; assignment/outcome validation, durable state, credit and exact-zero estimator; practical receipt publication; ExecutionEpisodes launch/delegation/facts/credit/completion; execution target/progress reading; actual native_lifecycle, LocalJobPolicy and _local_job_worker. Traced the shared Workflow selected-operation, typed-return, record-selection, credit, completion-evidence and controller-observation methods. The final Workflow fixture uses ExecutionServiceFactory with explicit episode_record_receipts=True and the existing receipt-enabled return path.

## Initial stable run and defects

Command:

```
.venv/bin/pytest -q tests/test_native_hmmer_local_binding.py --basetemp=verification/tool_graders_native_hmmer_local_binding_2026-10-24/initial-tmp --junitxml=verification/tool_graders_native_hmmer_local_binding_2026-10-24/initial.junit.xml
```

Initial result: **24 passed, 7 failed in 101.93 seconds**. All 17 recorded source hashes matched before/after. The exact failure log and JUnit report remain retained.

Six failures were production defects reported to root:

- `LocalPracticalOperations._execute` status/collect created a new requested-job fact without qualifying the original HMMER plan. Both selected operations accepted a plan whose native metadata had been changed after the original launch.
- `local_hmmer_plan` accepted changed run_id, episode_id, attempt_id and allocation policy. It lacked the original directory/attempt/handle comparisons.

Root repaired these production paths. A later debug run found that the new owner validation used practical `_read`, which requires compact canonical JSON, on the producer's indented JSON owner. Root corrected it to parse the producer JSON and compare its complete value.

The seventh initial failure was in this verification fixture: the parent had no episode receipt binding, so the actual received-record projector saw no received references and returned zero. Changing the fixture to the receipt-enabled existing ExecutionServiceFactory path establishes the intended explicit units; the expected production credit was not relaxed. Debug run failures are retained separately and are not final stable verification claims.

## Checks and actual native work

- Structural selection tests cover hmmscan, hmmsearch, jackhmmer, nhmmer sequence/profile/alignment, nhmmscan and hmmalign. They reject changed parent work and bindings with the wrong program, mode, executable, executable digest, engine version, resource, original argv or allocation. Native HPC remains explicitly unbound.
- Real native representatives are protein hmmsearch, nucleotide nhmmer profile search and hmmalign with its original mapali alignment. Every native execution uses the existing systemd lifecycle with **20 GiB RAM, 4 GiB scratch, no wall-time limit**. Tests verify actual cgroup memory/swap/runtime settings. All input files are the existing tiny synthetic B003/producer fixtures; algorithm outputs are actual HMMER output.
- Original argv/environment are distinct from realized staged argv. Retained input lengths/digests, complete declared output roles and artifact digests are checked against the sealed bundle.
- Same selected-action replay keeps the original native unit, handle, receipt and bundle timestamps. An unsealed attempt refuses producer replay. A pending practical intent with an unavailable original native outcome reopens its original handle and records unknown status without another process or invented completion.
- A closed usable_handoff launch passes its original receipt to later status/collect operations. An incomplete declared output set does not complete the output endpoint. A receiver naming the actual bundle path can complete its own original output assignment without changing launch history.
- Changed original plans, owners, allocation and native handle command/cwd/policy must reject. Changed native bytes are tested through producer sealed replay, where hashing belongs; no new whole-output scan is required on every status poll.
- The shared Workflow test commissions a real launch_local child from launch, returns a requested typed handoff, then opens a later practical output receiver. It checks one completed action per owning episode, preserved final gains, immediate exact-zero next-yield expectations and unchanged closed launch observations.

## Actual native numerical examples

These examples come directly from complete bundles produced by the real selected practical binding. They are **native-output examples only**, not verified numerical scientific-parent returns. Full original/staged argv, artifact counts and first native rows are in native_examples.json.

| Operation | Native measurement |
| --- | --- |
| hmmsearch | Query `test`, hit `test1`: full-sequence score 72.1 bits, E-value 4.2e-24, bias 0.1 bits; one domain reported and included. |
| nhmmer profile | Query `model`, target `forward`: score 120.9 bits, E-value 6e-39, bias 0.9 bits; model coordinates 1–100, target alignment 11–110 of length 120, forward strand. |
| hmmalign mapali | Stockholm retains 14 sequence rows, each 33 alignment columns, including 10 inherited mapali rows and 4 supplied sequence rows. |

## Remaining verification boundary

This workload does not run API, HPC, model inference, literature processing, BLAST database work or the excluded pending NCBI RID check. It does not change score policies. It does not prove independent subprocess episode reconstruction.

Root's numerical results branch was being wired during this workload. Complete native artifact acquisition through that branch, deterministic numerical publication, saved-sheet recalculation and the requested numerical scientific-parent return remain separate root verification responsibilities. Practical completed_job_outputs validates its exact original declared file predicates; it does not claim successful scientific parsing merely because a bundle exists.

## Final focused verification

Command:

```
.venv/bin/python verification/tool_graders_native_hmmer_local_binding_2026-10-24/run_verification.py
```

The runner calls `pytest.main` under `.venv/bin/python` with `-q tests/test_native_hmmer_local_binding.py` and the exact output-directory/JUnit arguments recorded in final_command.json. Result: **32 passed in 72.62 seconds**, no skips or failures. All **120 loaded local Python files** had identical before/after hashes. The final log, JUnit report, complete loaded-source hashes and source-stability summary are retained. Source hashes are computed before pytest begins and after it returns; the final comparison includes all local modules actually loaded by the test process.

The final shared Workflow contains three completed own-action observations: launch gain **3**, resource-child gain **7**, and later output-receiver gain **7**. Every final next-yield band has value/lower/upper **0**. The typed child form contains the requested verified `completed` fact and original handoff source. Launch and child observations remain byte-identical after the receiving episode finishes. See final_workflow_evidence.json.

The final native examples and complete original/staged commands are retained in final_native_examples.json; they agree with the numerical examples above. VERIFICATION.json records native handle count, exact test result and the explicit unverified numerical scientific-parent boundary. No passing test was skipped or changed to accept a production defect.
