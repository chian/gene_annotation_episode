# Wired execution episodes

`ExecutionServiceFactory` installs one `ExecutionEpisodes` binding for `launch`,
`launch_api`, `launch_local`, `launch_hpc` and `results`, plus the existing
recursive `MonitorEpisodes`. Execution decisions remain in `method_loop`.
It supplies the actual ToolRegistry's native API clients and internal scientific
publication port, rather than an ordinary submit-and-poll HMMER search tool.

The launch family exposes these existing decision owners. This is an allowed
structure, not an itinerary or a required polling sequence:

```text
Scientific episode: which uncertainty and work matter next?
├─ Launch: which permitted execution approach is useful?
│  ├─ API execution: how can this assigned service job be established?
│  ├─ Local execution: what preparation, reuse or repair does this job need?
│  └─ HPC execution: what environment, allocation and submission steps work here?
├─ Monitor: what exposed progress information is useful next?
│  └─ Monitor: what information about this exposed dependency is useful next?
└─ Results: what requested acquisition remains, and how can it be obtained?
```

Scientific and literature roles retain their existing separate construction and
ownership. This wiring changes neither scientific scores nor library slots.

## Where the work runs

The PBS/SSH binding runs selected preparation operations on the configured remote
host and submits the requested compute job to PBS. Its remote worker does not
contain an Episode controller or model loop. The existing independent Episode
worker is started by the caller's local durable execution store. Consequently,
proving an HPC job subtree does not establish remote placement of the investigation
workers, their model clients or their journals. Moving that entire subtree requires
a separate worker-placement and state-transfer path with the same original
commission and authenticated return boundary.

## Caller configuration

The established Aurora target and reuse-only transport are prepared in
[AURORA_HPC_SUBTREE.md](AURORA_HPC_SUBTREE.md), with an explicit example resource
dictionary. The user's charging and storage requirements remain distinct.

Use `ExecutionServiceFactory(resources, initial_information, handoff_unit,
acquired_record_unit, monitoring_information_unit, ...)` with
`episode_service_binding=factory.as_record()` and
`episode_service_inputs='actual_tool_registry_v1'`. The actual Workflow passes
its registry; no operation runs during setup. Resource IDs are caller-owned keys:

| Kind | Configuration |
| --- | --- |
| `local` | Exact workspace and existing `LocalJobPolicy` operands. |
| `pbs_ssh` | Exact project workspace, supplied SSH argv, remote Python and charging account. |
| `hmmer_api` | `kind: hmmer_api`, optional `service: ebi_hmmer`; the actual registry's native HMMER client owns transport configuration. |

Several resources of the same kind may be bound. No default host, allocation,
API endpoint substitution or dictionary-order resource choice is inferred.
Configured capability and recorded inventory arrive before the choosing turn;
availability remains unknown until observed. Existing caller-bound typed timing
expectations still inform decisions when configured; this integration does not
create a new statistics model or fabricate resource timing samples.

The assembled scientific caller selects `assembled_case_services_v2`, retaining
the existing service operands and adding explicit `execution_resources` and
`initial_execution_information`. Its descriptor list has scientific process,
literature, this execution family and monitor. Older saved caller versions retain
their original definitions. Do not register overlapping launch-family bindings.
An old unfinished `public.hmmer.*` selection cannot execute through a retained
bypass; those operations were deleted. Already saved outcomes keep their normal
journal replay path and original observations.

## Assignments and handoffs

`execution_launch_assignment_v1` contains `requests` keyed by permitted resource
ID, `immutable_input_versions`, `constraints` and optional `launch_instructions`.
Each request is the exact job representation for that resource. Launch explicitly
commissions a child with the selected request and resource ID, preserving all
parent constraints and instruction pins. Additional instruction sections are
allowed; inherited pins cannot be removed or replaced.

Local/HPC children keep `practical_assignment_v1`. API children receive
`api_execution_assignment_v1`: resource ID, service `ebi_hmmer`, scoped subject,
algorithm `phmmer` or `hmmscan`, exact database, parameters, positive page size,
endpoint `usable_handoff`, constraints and optional pinned instructions. API
work does not use invented shell argv.

The source returned at handoff qualifies one `execution_target_v1`: original
run, episode, resource, execution ID, request digest, assignment and scientific
scope. Native request identity hashes the original requested job; API target
identity hashes the API assignment. Submitted FASTA, parsed sequence and HTTP
request hashes remain distinct. PBS monitoring pins the original attempt ledger
rather than following a newer `current.json`.

`execution_results_assignment_v1` contains the original `handoff_ref` and a
selector: API `page` with optional `page_size`, or native paths and bounded byte
windows. Results cannot change the job. Parents request typed
`execution_handoff_refs`, `execution_result_refs` and `execution_completed` facts.
Native results additionally expose constrained `execution_result_origin` facts.

## Selected operations and accounting

`launch_api` offers `api.hmmer.databases`, `.prepare`, `.submit`, `.status` and
`.check_handoff`; API results offers `.result`. Each HTTP action performs at most
one request. There is no private polling, sleep or automatic retry loop. Submit
commits intent before its single POST and bytes before UUID parsing. An uncertain
submission does not authorize another POST. Saved selected actions replay their
original outcomes without another request. Ordinary `public.hmmer.databases`,
`.search`, `.collect` and `.page` catalogs and dispatch paths are deleted.

Native results offers `execution.results.status`, `.collect` and `.read`.
Acquired bytes, failure details and selector provenance are retained. Arbitrary
result paths are observed current filesystem bytes, with no historical
per-attempt output version asserted and no atomic snapshot across separate reads.
The acquisition endpoint means requested acquisition plus an observed successful
exact attempt; it does not certify unrecorded historical file ownership.

Actual selected outcomes publish episode-to-physical-execution dependencies only
after commit. Ordinary monitors may follow explicitly exposed direct dependencies
and return the original parent's typed form. Native logs preserve original bytes
including non-UTF-8 data. Monitoring has independent custody and never adds credit
or observations to a closed launch.

Caller units remain explicit. Resource progress uses original practical
requirements; launch credits received qualified handoffs; results credits new
received records; monitoring credits novel useful observations. Repeated records,
timestamps and unfinished elapsed time do not manufacture progress. Parent child
receipt is one own observation, regardless of internal child turns.

Verified launch/resource/acquisition endpoints set expected future credit to
exact zero immediately, preserving the final actual gain and existing completion
cost. Pending descendants survive parent closure. Saved C1 reconstruction restores
the same factory, actual client registry, original commission, forms and provider;
it does not resume the scientific root or choose new work.
