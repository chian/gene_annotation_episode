# Same-input profile after416 schema reuse

The actual retained410 diagnostic still accepts the original typed report. Its
profiled wall time changed from48.274595s to32.511627s, a measured reduction of
15.762969s (32.6527%) for this diagnostic. Schema construction fell from295calls
to9; current payload, original-authority and scientific-byte checks remained in
the measured path. This is not a whole Workflow speedup or tool-completion claim.

This report is additive. The original `PROFILE_REPORT.md` and all933files under
`check001` remain byte-for-byte unchanged from the repeat's preflight manifest.
No production file was edited by415.

## Scope, command and source comparison

Root authorized this repeat after reporting416's focused85checks passed in55.20s.
Those checks are separate416 evidence and were not rerun or counted again here.
The current implementation and
`../tool_graders_protein_structure_shared_contract_2026-10-27_380/SCHEMA_REUSE_CONTRACT_026.md`
were read before execution. The full immutable objective and all16 principles
were reread verbatim after examining the results, then026's scope was reread.

The command was:

```sh
.venv/bin/python -B verification/tool_graders_protein_structure_validation_profile_2026-10-27_415/run_bounded.py check002
```

The exact launcher and diagnostic hashes match the baseline. The scientific
input remains the same closed410/check007/temporary/pytest/protein-workflow4100.
Between executed snapshots, the sole production source change is
`gene_annotation_episode/native_protein_structure_contracts.py`:
`13e1f7c4e9e60fed6283ab66aea03dd3b54de4767941d6509f496c2188cdaea0`
became
`e40bc91ce1c0c15017ec30b50d5cee1fd6b76e6afc6f1cf2c6637ab4d251a351`.
The only added snapshot file is the026contract.

Source inspection confirms the change consists of private strict-validator
construction reused by successful unbound type name, plus complete public schema
export deep-copying. `_checked` still validates the current supplied value and
returns a detached copy. Binding-specific construction and nested job/request
validation remain in place. No payload, receipt, permission or current-byte
verdict is cached by that change.

Both runs used fresh Python processes, cProfile, read-only source snapshots and
the same20GiB RAM/4GiB scratch/no-swap/no-wall-limit policy. Check002 verified the
original cgroup settings and used42,696,704bytes of observed scratch. Its service
wall duration was33.044875s; the separately measured profiled diagnostic interval
was32.511627s. The guard recorded no native subprocess or network attempt. Source
pins did not change during execution, and checkout drift was zero at completion.

## Exact retained result comparisons

`diagnostic.json` and stdout are byte-identical between runs. Catalog, target,
selector, returns authentication, receipt assignment, receipt intent and actual
typed admission all accepted. Shared assignment bytes still match the same
549-byte canonical document plus one newline.

All four retained-input manifests—before/after each run—are equal. The detached
databases contain byte-identical original episode ID, selected action, completed
result, request, report form and frozen facts. The scientific case is still one
4-residue extracted sequence descriptor, `completed=true`, and no failures.

| Compared original value | Bytes | Identical SHA256 in both runs |
| --- | ---: | --- |
| Selected action | 65 | `7d3ff18a97ca27db07b225160f232484771de4a99800776e4ae5659aa0c5aaf8` |
| Completed result | 67,611 | `a955bd925b20f24075ff4453bf5ed00d67d284e81cfd52faffb2ea6eed563230` |
| Typed form supplied to actual admission | 2,439 | `926a3865a20b90142d8da502aab348577f1231611f3f1a90d4f5c0885d9ba530` |
| Frozen facts | 3,790 | `78b24fde1a1817115f61aebe505da3a862f37eb8a78e9f648b33faf5e4b13a41` |
| Original request | 961,364 | `161d8c1860a1ed5cb125c170294a0b1db5e876b0c91d14cf984b629b7982a80a` |

The unchanged diagnostic passes that exact original form to real
`TypedReportContract.admit` with the actual resolver and semantic callback.
It does not serialize the returned `ParentReport` object. Therefore the measured
comparison is exact admission input/frozen-fact equality plus successful real
admission; no separate output-object byte comparison is claimed. The admitted
input form is retained at `check002/admitted_input_form.json`.

## Overall and stage measurements

| Measurement | Check001 | Check002 |
| --- | ---: | ---: |
| Total calls | 155,854,409 | 99,927,635 |
| Primitive calls | 129,318,934 | 84,096,872 |
| Summed cProfile self seconds | 48.200176 | 32.435445 |
| Measured diagnostic wall seconds | 48.274595 | 32.511627 |
| Measured process CPU seconds | 49.106171 | 33.281434 |

The total call count decreased by55,926,774. cProfile overhead is included in
both measurements; eliminating calls also changes that overhead. This single
before/after pair establishes neither a distribution nor unprofiled latency.
The OS file cache was not flushed or controlled. Snapshot/input hashing and final
profile serialization remain outside the measured diagnostic interval, while
production imports remain a named stage.

| Stage | Before wall s | After wall s | Before CPU s | After CPU s |
| --- | ---: | ---: | ---: | ---: |
| Imports | 0.800880 | 0.878124 | 1.638605 | 1.653133 |
| Copy retained state | 0.007553 | 0.008374 | 0.007554 | 0.008375 |
| Initialize detached Store | 0.000788 | 0.000980 | 0.000788 | 0.000981 |
| Read assignment | 0.001132 | 0.001279 | 0.001131 | 0.001280 |
| Construct execution owner | 1.422193 | 1.271979 | 1.422175 | 1.271861 |
| Construct authenticated context | 0.928393 | 0.975957 | 0.928387 | 0.975874 |
| Catalog | 0.000643 | 0.000548 | 0.000644 | 0.000548 |
| Target | 11.762410 | 6.702350 | 11.762301 | 6.701994 |
| Selector | 0.087081 | 0.032128 | 0.087083 | 0.032129 |
| Returns authenticate | 0.798726 | 0.805930 | 0.798719 | 0.805867 |
| Receipts assignment | 0.000579 | 0.000599 | 0.000579 | 0.000599 |
| Receipts intent | 1.867719 | 1.299818 | 1.867714 | 1.299649 |
| Shared assignment bytes | 0.000231 | 0.000236 | 0.000231 | 0.000235 |
| Construct typed contract | 5.693940 | 5.775619 | 5.692173 | 5.775538 |
| Actual typed report admission | 24.887866 | 14.742442 | 24.887462 | 14.741840 |
| Close detached Store | 0.000289 | 0.000204 | 0.000290 | 0.000204 |

## Function counts and remaining costs

The following cumulative times overlap. They cannot be added as independent
costs or converted into a promised next speedup.

| Function | Before calls | After calls | Before cumulative s | After cumulative s |
| --- | ---: | ---: | ---: | ---: |
| Native execution schema builder | 295 | 9 | 16.674157 | 0.847901 |
| Private validator constructor | absent | 7 | — | 0.670821 |
| Native `_checked` | 293 | 293 | 25.749576 | 9.724798 |
| Validate requested job | 26 | 26 | 20.797924 | 7.669407 |
| Validate native job | 58 | 58 | 20.546415 | 7.459792 |
| Validate scientific request | 125 | 125 | 10.896162 | 4.035673 |
| Compile native job | 32 | 32 | 11.225719 | 3.992985 |
| `referencing.Registry.crawl` | 294 | 294 | 8.376868 | 8.347450 |
| Closed-form `check_schema` | 1 | 1 | 5.068304 | 5.135837 |
| Returns authenticate | 17 | 17 | 12.252475 | 12.245964 |
| Base return-record authenticate | 54 | 54 | 4.757677 | 4.697993 |
| Original commission checks | 37 | 37 | 3.958573 | 3.920788 |
| Completed receipt traversal | 3 | 3 | 33.031844 | 18.397799 |
| Verify selected artifacts | 1 | 1 | 0.002262 | 0.001888 |
| Read/check current scientific bytes | 4 | 4 | 0.001824 | 0.001539 |

The seven constructor calls are actual cache misses. Nine public schema builds
include those seven and the two existing module constants. The profile confirms
that this change removed repeated schema building while retaining the same293
payload checks and the same nested validation/authority traversal counts.

Schema-related copying dropped substantially: `deepcopy` made5,575,438 total
calls before and807,218 after, with cumulative time10.310788s→1.544408s.
`communication.plain` made10,504,651 total calls before and5,388,683 after,
13.764430s→7.886726s cumulative. The standard-library copy module's exclusive
self time fell6.535033s→0.957786s; JSON functions fell1.827198s→0.828087s.
The remaining top self-time entries include `communication.plain`2.753696s,
`isinstance`2.619759s, typed-return equality1.533127s, ABC checks1.356176s and
1.343219s, registry crawling1.217479s, and `all`0.952518s.

Registry crawling remains294calls/8.347450s cumulatively. Reusing the validator
did not remove this cost in the actual library version/path. Closed parent-form
schema grammar checking also remains a single5.135837s cold cost. Original
metadata authentication and whole-request normalization are still substantial.
Those are distinct remaining measurements, not authorization to alter their
semantics. A later investigation can examine pure immutable resource preparation
or the previously documented local calculation seams; this packet implements
none of them.

The4scientific files still total47,111bytes. Their current bytes were validated
in the same selected use; no scientific parse, calculator or native execution
was repeated. SQLite calls remain2,026 in the exclusive grouping; selected OS/I/O
calls remain8,123. Their exclusive times were0.028811s and0.034345s respectively,
including imports/copy/control reads. These small values do not generalize to
larger structures or lost/mutated artifacts.

## Retained artifacts and limits

- [Structured exact comparison](check002/comparison.json),
  [repeat receipt](check002/receipt.json),
  [repeat binary profile](check002/diagnostic.prof),
  [stage measurements](check002/profile_stages.json),
  [all cumulative entries](check002/profile_all_cumulative.txt),
  [all self-time entries](check002/profile_all_tottime.txt).
- [Baseline preservation and authorization](CHECK002_AUTHORIZATION_AND_PREFLIGHT.json),
  [comparison script](compare_profiles.py),
  [analysis script](analyze_profile.py),
  [original baseline report](PROFILE_REPORT.md).

Reproduce the read-only analyses with:

```sh
.venv/bin/python -B verification/tool_graders_protein_structure_validation_profile_2026-10-27_415/analyze_profile.py check002
.venv/bin/python -B verification/tool_graders_protein_structure_validation_profile_2026-10-27_415/compare_profiles.py
```

There was no failed check002 diagnostic attempt. The initial source-difference
command returned diff's normal status1 because the expected source change exists;
the launcher was then read separately. No original file, baseline artifact,
control record or live test was modified. This profile covers existing retained
report admission only.416's mutation/strict-type tests, root's native Workflow
run and broader artifact-loss verification remain separate evidence.
