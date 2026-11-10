# A101 execution planning and shared operational memory

A101 uses the actual shared tool catalog. Every frozen tool/resource entry now
gets an execution recipe from `execution_instruction_library/`, including tools
with their own supplied instructions. It is not a hard-coded four-tool bundle.
The recipe covers resource selection, detached launch, monitoring, collection,
timing provenance and reuse. BLAST/HMMER entries also identify homology workload
sizes, database/setup state, operand direction and native result custody.

The scientific parent can call `process.execution` with `name`, `resources` and
`profiles` (an empty list discovers existing profile keys). It returns the exact
frozen ToolInfo, host/window capacity, Aurora queue freshness, available HPC
commissions, known timing profiles and selected compatible measurements. This
call performs no SSH, scientific computation, publication or credit assignment.
Ordinary decision context includes the same compact local/Aurora capacity view.

## Connecting the existing template

`bind_assembled_services` accepts `hpc_commissions` and
`shared_execution_memory`. With a commission configured, it registers the HPC
and prediction roles and makes the HPC child available to scientific parents.
The version-two assembled case configuration accepts these same fields. The
factory and detached reconstruction retain the explicit memory configuration.

An HPC child assignment can carry this request for any actual catalog entry:

```json
{
  "commission_id": "caller-configured-commission",
  "tool_request": {
    "name": "sequence.align",
    "resources": "local",
    "arguments_json": "<JSON matching that exact tool's input schema>",
    "result_reader": "<actual registered result operation>",
    "objective": "<the scientific parent's concrete requested computation>"
  }
}
```

The binding resolves the real frozen contract, validates its operands and checks
that the result reader exists. The HPC parent receives these exact operands and
instructions. Its episode owns discovery, setup and portfolio construction;
Launch owns preparation and original PBS submission. The shared library does
not relabel a local-only implementation as an available HPC adapter. Such a
tool's preparation must establish the remote producer and its compatible result
reader before launch. Existing native result contracts remain authoritative.
A compact allocation receipt alone does not earn A101 scientific credit.

For long local work, select the existing `launch -> launch_local` native binding
or detached homology binding. Return its durable handoff and let the parent do
other useful actions while it runs. A blocking ordinary-tool call remains
blocking; retrieving a recipe does not change its execution semantics. Local
workers retain their owning workflow's systemd lifetime. They must be collected
before that workflow exits; an HPC cron park must not strand a local worker.

## Shared memory and forgetting

The default SQLite library is `runs/shared-execution/memory.sqlite3`, shared
across runs and windows in this checkout. `GENE_EPISODE_EXECUTION_MEMORY` can
select a common library for multiple checkouts. This is a metadata database,
not a global workflow lock. Explicit factory configuration can pin its path and
forgetting policy for reconstruction. Use the same path for native exporters.
Each native handle retains its selected export path, so detached completion and
receipt recovery use the original library even if the caller's environment changes.

| Observation | Default use window |
|---|---|
| Host capacity | 15 seconds |
| PBS queue/status snapshot | 120 seconds |
| Exact successful discovery command | 24 hours |
| Queue timing history | 7 days, one-day half-life |
| Algorithm/setup timing history | 90 days, 14-day half-life |

Expiry removes an observation from current planning; it does not delete the
original receipt. Cache reuse never changes its capture time. Future-dated
observations do not establish current availability. There is no resource polling
daemon: episode-selected observations populate the library when needed.

Work timing transfers only across an explicit compatibility profile:
`resource_id`, `backend`, `tool`, `implementation`, `parameters`, `hardware`.
Use version/digest fingerprints for software, databases and algorithm options.
Input sizes and allocation shape are numerical model features. Queue observations
can transfer across tools on the same resource, but different PBS queues require
matching queues or explicit categorical model features.

The existing native statistics exporter writes its original measured receipt
into this library. HPC closure exports one record per physical allocation.
Failures, unknown results and censored durations remain distinct from successful
completion. Polls do not create extra training samples. `hpc.history.refresh`
freezes a dated library view for the episode. Model fitting uses fractional
precision from age weights; the original forecast and prospective validation
credit remain frozen. Shared history does not mint scientific or polling credit.

Previously completed HPC ledgers can be imported without SSH or rerunning work:

```bash
bash tools/one_workflow.sh runs/import-timing-UNIQUE -- \
  /path/to/python -m gene_annotation_episode.hpc_history \
  runs/ORIGINAL/episode/hpc/OWNER/hpc.sqlite \
  --resources examples/aurora_execution_resources.json
```

The importer opens the source database read-only and retains original times and
receipt provenance. Older runs without verified compatibility fingerprints are
kept as unclassified work measurements; they cannot silently calibrate an
unrelated algorithm. Their matching queue observations remain useful.

## Timing is information, not a runtime control

There is no local `wall_seconds` policy, systemd runtime maximum, HPC unit
timeout, application deadline or cumulative node-hour stopping budget. Obsolete
settings are rejected. CPU, RAM, scratch and process ownership/concurrency
protections remain. PBS allocation requests still describe scheduler resources;
the application adds no timer that kills work when a duration estimate is wrong.

Monitor intervals select observation times. Conditional forecasts and credit
estimates guide work/wait/collect/finish decisions. Activity advice does not
remove other actions. Multiple HPC allocations retain separate monitor owners,
and pending value is deduplicated by accomplishment obligation. These decisions
remain separate from machine protection.
