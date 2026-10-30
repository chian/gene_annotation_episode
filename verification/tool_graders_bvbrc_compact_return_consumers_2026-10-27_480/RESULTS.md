# Verification results

This is implementation evidence, not a replacement goal. The original supplied
goal and all sixteen design principles retain their authority.

## Collected focused comparison

`check008` passed all seven nonempty numerical-row contract cases in 94.71 s.
`check009`, the same inputs with the seven original consumer files, failed all
seven cases in 81.61 s. Every failure is the original consumer's
`*_return_original_commission_conflict` at its literal comparison of compact
selected schema against the expanded child schema.

`NUMERICAL_COMPARISON.json` records the individual outcomes and verifies that
only the seven consumer source files differ between these snapshots. The full
dependency closure, interpreter and standard library are identical. Both
attempts were collected terminal and quiescent, with all before/after pins
unchanged. Their handles are:

- `check008/handle.json`: `gene-local-job-803989b4550f4df0b2496733f9fb97ac.service`
- `check009/handle.json`: `gene-local-job-e85671560c0142369f88063e2927b883.service`

These cases preserve the exact nonempty original numerical rows through each
actual family consumer's first compact return and explicit compact redelivery.
They use deliberately constructed historical communication records and existing
family numerical fixtures; they do not establish live native BV-BRC execution
or the complete scientific publication path.

The earlier `check002` compact admission/forwarding/redelivery smoke passed
(1 test, 12.33 s), also collected terminal and quiescent with unchanged pins.

## Preserved diagnostic attempts

`check001` exposed a test-helper error: `Journal.row` does not support the
report-attempt table's key names. The live test helper now uses the explicit
report-attempt SQL key, as exercised by `check002` and later snapshots.

`check007` correctly reproduced original consumer conflicts in five numerical
families, but its genome-alignment and proteome fixtures could not load their
retained example files. The runner now explicitly copies and pins those files,
plus the other saved return fixture dependencies. `check008` and `check009`
provide the complete paired comparison. `check007` remains collected with all
pins unchanged and return code 1.

`check005` failed during snapshot preparation because the copied original
consumer destination was read-only. No native handle was created. The runner
now makes only those destination copies writable before substitution and
freezes the completed snapshot before launch.

## Collected complete matrix and existing-test comparison

This section supersedes the earlier in-flight status. All nine original native
handles through `check010` are now collected terminal and quiescent, with all
source, dependency, interpreter and standard-library pins unchanged. `check005`
never created a native handle. No elapsed-time restart or cancellation occurred.
`COLLECTED_HANDLES.json` records every exact handle, unit and outcome.

| Attempt | Passed | Failed | Meaning |
| --- | ---: | ---: | --- |
| `check001` | 72 | 63 | Initial diagnostic: 61 helper lookup failures and two missing input files |
| `check003` | 133 | 2 | Complete new matrix; only genome-alignment/proteome missing fixture files failed |
| `check004` | 308 | 150 | Existing seven return test files with repaired consumers |
| `check006` | 308 | 150 | Same existing tests with original consumers and the same new custody |
| `check010` | 3 | 0 | Two corrected full-form redelivery fixtures and one conflicting-schema rejection |

The two actual Workflow-generated cases in `check003` passed: compact and full
original preparation forms followed by explicit redelivery through all seven
consumer classes. `COMPACT_MATRIX_COVERAGE.json` records the full 135-scenario
coverage across `check003` and the fixture-complete `check008`. Their application
and test source pins are identical. This is not a claim of one clean 135-test run.

`EXISTING_TEST_COMPARISON.json` proves identical test-node statuses and normalized
failure messages across all 458 existing cases. `EXISTING_TEST_FAILURES.json`
retains the traces. Of the 150 failures, 148 concern omitted retained fixture
files and remain unverified here. Two synthetic redelivery tests wrote an empty
model request instead of the original decision schema. Those newly exposed
fixture incompatibilities were corrected separately and narrowly as described
below; the original failed snapshots remain intact.

`EXISTING_SNAPSHOT_COMPARISON.json` verifies that the application/test inputs of
`check004` and `check006` differ only in the seven consumer files, with identical
dependencies, interpreter and standard library. Their copied launcher evidence
also differs by the three-line destination-permission correction described
above; that copied script is not imported by the tests.

Both existing-test snapshots contain workload 479's new custody implementation.
Matching results isolate the seven-consumer change only. They do not establish
that the failures predate the combined custody-and-consumer repair. The custody
owner must assess any custody-related failures against its original source.

## Narrow historical fixture correction

Workload 479 traced both current and retained pre-repair `DecisionSource.call`
writers: they saved a context and the original action schema. Its inspection
found no actual writer of a decision request equal to `{}`. The two existing
Homology and Phylogeny test cases had constructed that incomplete request.

The fixtures now save an explicitly authored historical direct-decision frame:
`context`, a closed action schema containing the `redeliver_report` branch and
`report_update`, and a corresponding complete response. These literal full-form
fixtures do not invent compact contract information. The Homology test also
restricts the saved purpose schema to a conflicting constant and verifies that
the original-schema check rejects the return without changing stored records.

`check010` passed all three cases in 18.05 s. Its unit is
`gene-local-job-d9ea3ca38ca946a0b8351c72609a2c0a.service` and its handle is
`check010/handle.json`. `fixture_changes.json` and `original_tests` preserve the
exact corrections and original inputs. No custody compatibility bypass or
other production change was made for these fixture incompatibilities.

## Remaining limits

The 148 artifact-dependent existing cases were not rerun after restoring the
runner's fixture closure and remain unverified in this packet. The completed
focused numerical comparison and actual Workflow preparation-return cases have
the narrower meanings stated above. No live BV-BRC API execution, native
scientific run, configured model, HPC execution or complete scientific
publication path is claimed.
