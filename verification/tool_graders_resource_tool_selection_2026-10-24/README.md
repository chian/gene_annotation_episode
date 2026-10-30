# Resource tool selection verification, 2026-10-24

This is the bounded implementation of
`docs/TOOL_GRADER_RESOURCE_TOOL_SELECTION_2026-10-24.md`. It does not establish
completion of the full tool-grader goal or a configured-model investigation.

## Implemented path

`WorkflowServices.tool_information_catalog(scope)` joins the actual ordinary
registry with pure declarations from bound resource owners. Host-only
`invocation_route` distinguishes direct invocation from commissioning through
launch/results and identifies the configured resource. The scientific child's
declared child edges filter those routes. The ordinary `tool_catalog` remains
the direct invocation map.

Both literal and configured retrieval now receive the availability-filtered
information catalog. Initial child construction, validation and revised-child
preparation use that same catalog. Resource operations remain absent from the
scientific direct catalog and are rejected by direct execution. Reading
declarations does not call an assignment-dependent catalog, create a query,
submit work, contact a service, or probe a resource.

The public selected information remains exactly name, description, resources,
instructions. The frozen library preserves explicitly supplied substantive
instructions and rejects changed instruction bindings. The setup interface
accepts caller-bound `resource_catalogs`. The assembled factory supplies them
from its actual execution binding. Binding implementation identity includes
the new route/service modules and the retriever for all retrieval modes.

## Actual connected verification

The tests run the real assembled factory and Workflow with scripted decisions:
internal `process.tools` lookup → selected scientific child → launch → API child
→ results child → deterministic HMMER publication → requested typed numerical
record references admitted to the scientific child and its parent.

Two native-input cases each run with literal and configured fixture retrieval:

| Input | Published domain observations | Checkable returned quantity |
| --- | ---: | --- |
| Retained historical phmmer API response | 4 | A domain has 88 paired positions. |
| Explicitly synthetic hmmscan response | 1 | The domain has 3 paired positions. |

Each case completes 1 root action, 2 scientific actions, 1 launch action,
3 API actions, and 1 results action: 8 completed own actions and 8 controller
observations. There are 9 decision exchanges because the internal lookup
continues the unfinished root decision. Configured retrieval makes one
scripted FAST-provider call and no additional action or observation. The
synthetic transport receives exactly submit, status, result once each.
Reopening the original result action and reconstructing the scientific
commission preserve the observations and issue no new transport call.

The existing scientific text renderer and provider presentation include each
selected tool's exact frozen instructions in recurring TASK. Parent/root direct
tool exposure remains empty under its existing boundary. Schema, operation
identity, forged instructions/descriptions, unbound services, unavailable child
routes, multiple selected tools, local/HPC variants, original revision ownership,
and frozen snapshot restoration have dedicated checks.

## Test results

The final focused stable-source run passed **25 tests in 331.34 s**, exit code
0. It ran the 15 new selection checks, 6 existing child-information checks and
4 existing current-version revision/preparation checks. Its log is
`pytest-focused-stable.log`; `run_focused.py` contains the exact command inputs.
`production-source-audit.json` records before/after SHA-256 values for all
**133 actually loaded production source files**, with **0 changed files**.

The broad selection/regression run recorded 63 passed and 6 failed in 328.01 s.
All 15 new selection tests passed. Its complete output is retained in
`pytest-selection-and-regression.log`. Shared execution files changed while
that process was running; it is not the final stable-source verification.

The six failures occur in older tests with assumptions already incompatible
with source inspected before this change:

- Four tests in `test_semantic_actual_tool_retrieval_runtime.py` assert a v5
  descriptor although the pre-existing setup uses `tool_info=True` and returns
  v7 for a new snapshot.
- `test_mother_report_resolver_honors_process_metadata_and_validates_result_bodies`
  hits the pre-existing v2/v3 mismatch in the unchanged
  `scientific_process_results` schema. This workload returns ordinary requested
  numerical-record references; it does not repair that separate schema.
- `test_setup_freezes_descriptor_without_executable_services_and_reopens_original`
  supplies `fixture.inspect` without a resource kind. The unchanged
  `resource_kind` function cannot assign one.

Those historical tests and their conflicting behavior were not rewritten.
The broad and focused groups overlap; their counts must not be added as unique
coverage.

## Explicit remaining boundaries

The API/results children receive the original concrete request and result
selector through the existing launch/results contracts. Their generic
TASK/STEERING text renderer still does not incorporate the scientific child's
selected substantive tool instructions. The connected tests assert that gap
separately. No prompt was changed and no extra knowledge-read action was added
to conceal it; new prompt design still requires the user's template review.

The tests use retained native response bytes and deliberately synthetic
transport/choices. They perform no live API, native scientific computation,
HPC submission, or model inference. A declared API route establishes a bound
operation, not live authentication. Generic local/PBS preparation capabilities
do not establish a native scientific deployment. B004 native producer and
publication integration are separate work owned by their implementing workers.

Source review covered the complete selection/service/library modules, selection
records, provenance and report consumers, the existing scientific prompt
renderer, the affected Workflow retrieval/dispatch/commissioning paths, and
the execution declaration and launch/API/results ownership boundaries. The
authoritative objective and complete DESIGN PRINCIPLES were reread verbatim
after source study and again with the selection contract before final review.
