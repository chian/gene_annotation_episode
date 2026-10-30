# Workload 223: Infernal original-result acquisition

Implemented only the new acquisition module, dedicated tests/fixtures, and this
verification directory. Original goals, contracts, producer/bridge files,
scientific graders, shared runtime files, inventory, prompts, scores and episode
structures were not changed by this workload.

The complete immutable goal attachment was read first. Its original objective
and all 16 design principles were reread verbatim after source study and again
after retained-native verification, followed by the complete workload contract.
`RESET_RECEIPT_001.json` identifies the authoritative attachment and read stages.

## Exact handoff

`gene_annotation_episode/native_infernal_acquisition.py` exports the five
functions and two constants from `WORKLOAD_001.md` without changing signatures
or the returned capture/source fields.

- `is_native_infernal_target` recognizes the explicit local/HPC request branch;
  `capture_local_bundle` accepts actual local targets only.
- `validate_original_bundle` is pure. It validates the finite original plan,
  full identity/request, explicit software declaration versus measured hash,
  program/table format, bindings, exact staged paths, original input records,
  selected output roles/paths, compiled argv/environment, typed actual values,
  failure relationships and sealed ordered timezone-aware timestamps.
- A capture freezes `capture-intent.json` containing the original target,
  `capture-plan.json` containing its validated original plan, and `capture.json`
  containing the exact public capture result. These are canonical immutable
  records through the existing practical-state helpers.
- The target is the existing complete `execution_target_v1`. The run, originating
  child episode, resource, execution, requested-job digest and original workspace
  relationships must match the frozen producer plan. The bridge remains the
  authority for the initial native reservation lookup.
- Complete original manifest bytes and complete actual selected input/output
  files go to the existing Store. Copying uses the existing streaming artifact
  helper through a held regular-file descriptor; relative path components may
  not be symlinks. Actual captured hashes and byte counts must match the sealed
  manifest. Mismatched or subsequently appearing unlisted selected files remain
  in `invalid_artifacts`, excluded from validated `artifacts`.
- Replay checks the stored target/plan, manifest, artifact identities, actual
  stored digests/sizes, role/format/path relationships, valid versus invalid
  partitions, failure accounting and completeness. It does not read the original
  native plan, reservation or file paths. A saved unavailable-manifest result
  stays that original result even if the original files are later repaired.
- `original_source_payload` uses provider `episode.execution_result`, original
  identity accession, original finish time and sorted unique complete/invalid
  artifact references plus the separate prepared grading artifact when supplied.
  Projection and page choices do not enter source identity. Publication checks
  that the supplied bundle is the actual captured manifest before storing the
  source with tool origin.

`_staged_relative` from workload 222's producer is reused because it is a pure
path construction helper with identical meaning. No producer execution function
is called. The initial `local_infernal_plan` lookup is supplied by 222's bridge;
all subsequent receipt replay uses the saved plan.

Capture `complete` means complete custody. It can be true when the native
returncode is nonzero or no native execution occurred. Original native failures,
partial bytes, measured zero and unknown values remain in the bundle. Numerical
preparation/publication must continue to evaluate those native facts separately.
The exported existing `ORIGIN.completion_basis` mentions an observed successful
attempt; the root consumer must require native success before presenting that
qualification, as communicated to root.

## Verification actually executed

Both runs used `run_tests_001.py`, which calls the existing
`local_jobs.run_local_job` with `LocalJobPolicy(21474836480, 4294967296, None)`.
The native lifecycle verified cgroup memory maximum 20 GiB, swap maximum zero,
process-tree control and unlimited runtime. Scratch remains the existing
monitored visible allocated-byte enforcement with possible overshoot and a hard
per-file size limit. No new resource controller or wall-time budget was added.

The pytest child used repository `.venv/bin/python`, `-p no:cacheprovider`,
`PYTHONDONTWRITEBYTECODE=1` and dedicated temporary/cache directories.

| Run | Result | Actual pytest duration |
| --- | --- | --- |
| `tests_001` | 96 passed | 97.85 seconds |
| `boundary_tests_002` | 4 passed, 95 deselected | 4.85 seconds |

The second run contains three additional cases plus one repeated affected
recognition/identity case after making recognition robust to a malformed resource
value. There are 99 distinct tested cases, not 100 independent cases. Full native
cases were not rerun for that small correction. Each directory contains its
`tests.xml`, full stdout/stderr, and `verification-receipt.json` with actual
command, policy, service-wall measurement and enforcement facts. Service-wall
duration is not relabeled as native-program runtime or queue wait.

Synthetic verification covers all three programs; complete bytes; pure/no-I/O
validation; independent returned values; every original identity field; original
request/program/format/binding/software changes; wrong input/output roles, paths,
hashes, sizes and types; duplicate rows; malformed/duplicate-key/nonfinite JSON;
missing requested outputs; failed-native partial outputs; missing/partial input
captures; retained mismatched bytes; FIFO/directory/symlink/path escapes;
unavailable manifests; immutable target reuse; altered saved capture association,
partition, failure and completion fields; corrupted Store bytes/metadata; source
identity across projection changes; and replay with original files removed and
original lookup/acquisition functions forbidden. Native subprocess and network
entry points are forbidden in the test contexts.

## Retained real native examples

The following workload 222 attempts were acquired through the actual
`local_infernal_plan` reader. No Infernal program was run or rerun by workload 223.
All captured bytes were compared with the existing original files. Source
publication and replay with original acquisition forbidden passed for all four.

| Original attempt | Native returncode | Input files/bytes | Output files/bytes | Captured file rows |
| --- | ---: | ---: | ---: | ---: |
| cmsearch, table format 3 | 0 | 2 / 257218 | 4 / 24759 | 6 |
| cmscan, table format 2 | 0 | 6 / 529502 | 3 / 32036 | 9 |
| cmalign | 0 | 2 / 50932 | 7 / 60473 | 9 |
| cmalign, actual native failure | 1 | 2 / 50932 | 2 / 414 | 4 |

Each complete original manifest is retained in addition to the file rows above.
The failed cmalign retains the 414-byte stdout diagnostic and its measured
zero-byte stderr, the original nonzero-returncode failure, and five explicit
missing-output failures. Its capture is complete custody and does not claim
scientific success. `NATIVE_CAPTURES_001.json` contains exact original execution
paths, captured manifest references, all output sizes and hashes, and failure
records. Test state directories retain the captured Store artifacts.

## Inspection and remaining verification

Read the entire original immutable goal; AGENTS.md; GOAL.md;
EPISODE_STRUCTURE.md; TIME_AWARE_ESTIMATION.md; PRACTICAL_EXECUTION.md and its
original additive contract; TOOL_KNOWLEDGE.md; workload 221's original contract
and native corrections; workloads 222 and 223; complete native_hmmer_acquisition,
native_infernal_contracts, native_infernal_driver, native_infernal_local and
native_hmmer_results; the complete called artifact/state/source publication
helpers and schemas; and the local policy/runner adapter. The HMMER code was read
as an implementation mechanism, not scientific authority.

This workload establishes original local capture and saved replay. It does not
establish numerical parser/calculator correctness, selected projection behavior,
annotation credit, live HPC access, full episode communication or configured-model
scientific work. Root owns the results/publication integration. The module adds
no network calls, retries, execution selection, scientific parser/calculator,
model invocation, scoring or additional completed-action observation.
