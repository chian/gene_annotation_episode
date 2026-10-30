# Infernal selected-resource binding verification, workload 229

All **47 tests passed in 255.89 seconds**. This is selection and commissioning
verification using retained exact contracts. No Infernal or HMMER program was
rerun, and no new scientific output was generated. No production defect was
found in the exercised interfaces; no production file was edited by workload
229.

## Owned changes and evidence

- `tests/test_native_infernal_local_binding.py`: 47 cases in 13 test functions.
- `run_tests.py`: uses the existing `run_local_job` with
  `LocalJobPolicy(20*1024**3, 4*1024**3, None)`.
- `run_001/receipt.json`: exact pytest command, environment overrides, Python and
  package versions, source/input-contract hashes before and after, exit status
  and actual resource metadata.
- `run_001/tests.xml`, `stdout.log`, `stderr.log`: complete test results;
  47 passed, no failures, errors or skips; stderr is empty.
- `SOURCE_QUALIFICATION_001.json`: exact qualification of the concurrent
  production edit described below.

The observed runner used 21,474,836,480 bytes of cgroup memory limit,
4,294,967,296 bytes of monitored scratch limit, zero swap and no wall-time
limit. Its measured systemd service-wall duration was 256.72617863 seconds;
observed scratch allocation was 24,948,736 bytes. These are verification-run
measurements, not scientific program timings.

## Actual consumers exercised

The tests instantiate the real `ExecutionEpisodes`, its per-resource
`PracticalResourceEpisodes`, `LocalPracticalOperations`, `Store`, `Journal` and
immutable `BindingContext`. They persist the original launch request in
`runtime_episodes`, then call the actual launch/resource `assignment_schema`,
`prepare_assignment` and `initialize` paths. There is no substitute registry.
Initialization is checked against the durable parent's original request even
when the test attempts to bypass `prepare_assignment`.

Accepted assignments preserve the exact requested job, caller allocation,
resource and working context in practical state. Initialization creates no
action receipts and no completion proof; none of these tests claim that a job
has run or completed.

| Boundary | Verified cases |
| --- | --- |
| Tool information | `native.cmsearch`, `native.cmscan`, `native.cmalign` have nonempty name, description, resources and instructions, the exact native request schema, and a `launch` → `launch_local` route naming the selected resource. |
| Shared configuration | Retained `hmmsearch` plus all three Infernal requests remain separate callable alternatives on one local resource. Each request matches only its own tool entry. All four cross preparation and practical initialization. HMMER cannot replace the parent's selected Infernal job. |
| No Infernal binding | Both an absent `native_infernal` key and an empty binding list expose no Infernal tool/result binding. Infernal selection and initialization reject; the configured HMMER request remains usable. |
| Multiple deployments | Each Infernal program is tested on two explicit local resources with different executable, SHA-256 and version declarations. Both request alternatives and routes survive the combined catalog. Cross-resource software swaps reject in local validation, preparation and durable initialization. |
| Original selected work | Changed program, executable, digest, engine version, resource, compiled argv, original options, environment and allocation reject through the actual parent boundary. |
| Parent constraints | A valid alternative on another local resource cannot bypass `allowed_resource_ids`; a forbidden kind cannot be selected. A scientific parent cannot directly commission a resource role that belongs to launch. |
| Declared immutable inputs | The actual Store subject reference, content hash and revision are checked. Out-of-scope declared input, wrong content hash and wrong version reject during preparation and initialization. |
| Unsupported resources | `api`, `hmmer_api` and `pbs_ssh` Infernal configurations reject explicitly. Direct API/HPC tool-contract creation also rejects. Availability remains `unknown` for declared local configurations. |
| Capability separation | Construction, capability information, resource contracts, assignment schemas and result descriptors complete while network, process launch, native preparation, acquisition, parsing and calculation entry points are guarded against use. No acquisition or scientific calculation occurs. |
| Result selection | The actual `ExecutionEpisodes._selector` consumer retains explicit row offset/limit or record keys and named metrics for the applicable program. Invalid family, metric, row-selection, mode/acquisition and extra-field choices reject without changing the supplied selector. |
| Five report descriptors | Actual result and scientific-receiver descriptors expose the five closed family schemas with exact metric names and separate sequence/model identifier namespaces, subject references and model-reference associations. |

`LocalPracticalOperations.validate_assignment` checks the bound program/software,
compiled request consistency and allocation, and requires a supplied resource
identity. `ExecutionEpisodes` owns matching that identity and the exact request
to the original parent's resource map and constraints. The tests preserve this
division; they do not add a new local validator restriction on valid native
options or a new scope gate.

## Retained inputs and result-contract scope

The Infernal requests are copied exactly from the existing sealed fixture
bundles under `tests/fixtures/native_infernal_result_worker/{cmsearch,cmscan,cmalign}`.
The retained `cmsearch` contract selects table format 3, `cmscan` format 2 and
`cmalign` its Stockholm/score/insertion outputs. The HMMER request comes from
`verification/tool_graders_native_hmmer_producer_2026-10-24/runs/hmmsearch_search_ordinary/plan.json`.
Each request is recompiled only to assert identity; no executable is probed.
The second-deployment identities are declared selection fixtures, not verified
software installations.

Result families preserve these exact receiver vocabularies:

| Family | Named numerical quantities | Applicable programs |
| --- | --- | --- |
| `search_hit` | 10, including bit score, E-value, model/sequence spans and their separate denominators | `cmsearch`, `cmscan` |
| `search_sequence` | 7, including hit count, union numerator/denominator and selection/geometry qualifications | `cmsearch`, `cmscan` |
| `alignment_sequence` | 22, including native score/posterior, occupancy, retained/omitted nucleotides and distinct gap/local-end quantities | `cmalign` |
| `alignment_column` | 7, including row count and occupancy numerator/denominator | `cmalign` |
| `alignment_pair` | 11, including canonical/noncanonical counts, unambiguous denominator and exclusion counts | `cmalign` |

The report-shape checks use explicitly unavailable placeholder rows with no
measurements. They are schema cases, not fabricated scientific results.

## Concurrent source edit qualification

`execution_episodes.py` changed during the run, from
`c5f8ad9c28bde6d92db22cd419877f962157f2099ba8e816e0e55d8224580374`
to `04ab8ad3e770290b0a196c8b1f05ed6400edb58086054605f8a8ecc573d1ffba`.
All other tracked source and request-contract hashes were unchanged.

Root recorded the exact patch in
`../tool_graders_infernal_root_2026-10-26_228/BINDING_TEST_SOURCE_CHANGE_001.json`.
Workload 229 independently reversed its two exact edits, matched the runner's
before hash, matched the current after hash, and compared every top-level
function and class method's source through the AST. The only changed method was
`ExecutionEpisodes.received_form_references`, which reuses already authenticated
Infernal return references.

These 47 tests do not run `Workflow`, a selected execution action, result
admission or that callback. The inspected selection, preparation,
initialization, catalog, capability, selector and descriptor paths do not call
it. This passing run therefore covers the unchanged selection paths and does
not verify the admission patch. No redundant rerun was performed. Workload 226
owns the live Workflow path and workload 227 owns return authentication.

## Limits and required handoffs

This workload does not establish native deployment or execution, parser or
calculator numerical correctness, actual result acquisition/publication,
authenticated child-to-parent numerical delivery, model-driven investigation,
API/HPC deployment or scientific credit. It tests declared immutable input
references at the commissioning boundary; it does not substitute for validating
native operand-to-subject/model relationships during result publication.
The actual result selector is called with an explicit unexecuted target record;
target custody/authentication is separate coverage.

The complete source functions for the affected selection paths were inspected,
together with the original tool-grader goal, AGENTS.md, required episode,
estimation, practical-execution and task/steering documents, and the relevant
fixed inventory rows. The original objective and all sixteen design principles
were reread verbatim after substantial examination and before this handoff.
No inventory completion row, historical receipt, existing test or other
subagent's file was edited by workload 229.
