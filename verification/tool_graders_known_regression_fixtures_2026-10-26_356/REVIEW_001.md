# U04: nine obsolete regression expectations corrected

The original two modules reproduced all nine recorded failures: nine failed,
17 passed. After correcting their expectations, those two modules plus the
existing scorer-retirement module passed all 40 tests. Both runs used the actual
local_jobs implementation with 20 GiB RAM, 4 GiB scratch and no wall-time cap.
Their source snapshots were unchanged during each run.

Only tests/test_numeric_bounds.py and
tests/test_execution_tool_contract_declarations.py changed. The five captured
production modules remain byte-identical to the before run. No annotation
formula, evidence-axis sheet, runtime implementation or historical receipt was
changed.

The numeric tests retain the full bounded-value transport, commit, query,
export and reopen checks. The retired category-based scorer now correctly
raises AnnotationScoringUnavailable instead of being expected to invent a zero
or empirical/comparative scores. Seven cases exercise the actual downstream
geometry consumer: a censored coverage or coordinate value cannot supply an
exact extent, while the original observations, assessments and annotation remain
retained. Both received findings still contribute to investigation progress;
repeating the reads creates no runtime observations. These checks do not bind
or verify a replacement annotation scorer.

The BV-BRC tests now distinguish the full declared legacy-plus-v2 operation
catalog from the single operation available for an actual request. Both request
versions are checked, including exact selected descriptors, explicit preparation,
wrong-version rejection and unchanged original request/selector values. All
acquisition methods are disabled. These are declaration/preparation checks,
not BV-BRC network execution.

U04's nine known failures are closed by this targeted verification. The older
321 broad-run receipt remains a failed historical run; the full repository
suite has not been rerun or declared passing. This repair adds no completed
scientific tool to the 108/308 count.

Evidence: before001 and after001 retain exact commands, source copies, before/
after hashes, stdout, stderr and actual job receipts. after001 reports
40 passed in 82.15 seconds with process exit zero.
