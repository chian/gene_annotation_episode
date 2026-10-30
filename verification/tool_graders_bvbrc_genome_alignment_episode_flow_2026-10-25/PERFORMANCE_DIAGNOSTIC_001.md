# One saved-reference lookup on a private copy

Root requested one bounded diagnostic while original Workflow run001 remained
active. The original process was not stopped, signalled, rewritten or replaced.
The exact diagnostic command was:

```text
nice -n 10 .venv/bin/python verification/tool_graders_bvbrc_genome_alignment_episode_flow_2026-10-25/profile_saved_reference_001.py > verification/tool_graders_bvbrc_genome_alignment_episode_flow_2026-10-25/diagnostic-001.log 2>&1
```

The script copied SQLite through its backup API from a read-only connection and
copied existing run files and immutable artifacts into `diagnostic-snapshot-001`.
It reconstructed the production `ExecutionEpisodes` family with the original
saved configuration, then enabled SQLite `query_only`. It did not construct or
run another Workflow. It called the actual family resolver once, for the saved
coverage field in the already-closed results episode.

The operation returned `True` in **11.51230967999436 wall seconds**, using
**11.512217702 CPU seconds** under cProfile. The profile recorded **30,977,136
calls**, including **27,787,777 primitive calls**. The 30-second diagnostic alarm
did not fire. These are profiled cold-process validation timings, not a forecast
for the running Workflow or remote/scientific execution performance.

| Observed function | Calls | Cumulative seconds |
| --- | ---: | ---: |
| F `resolve_own` | 1 | 11.512210 |
| F `facts` | 1 | 11.499418 |
| `read_latest_adapter_result` | 1 | 10.659680 |
| `AppServicePublications.read` | 1 | 10.524318 |
| Publication `_validate_inputs` | 1 | 5.438545 |
| Custody `_commission` | 135 total / 82 primitive | 5.063006 |
| Custody `authenticate` | 179 total / 64 primitive | 4.620897 |
| F saved `project_genome_alignment_facts` | 1 | 0.575308 |

These nested cumulative times must not be added. The observed lookup read and
authenticated the complete original publication before checking the requested
field. Source inspection of F `resolve_own` shows it calls `facts(context,
schema)` on every accepted namespace/reference invocation. The generic form
validator visits individual typed-reference occurrences. This diagnostic
sampled one such invocation; it did not profile every field or the live parent
boundary, and it does not by itself measure the total Workflow bottleneck.

The strict saved-science barrier blocked 173 loaded scientific implementation
aliases, native parsers, source comparisons, full numerical validators and
calculation helpers, plus socket/process entry points. Saved structural
validation and custody remained real. There was no barrier error. Copied
action/model/observation/report/receipt counts and all copied run/artifact bytes
were unchanged. Every original before-hashed source still matched. The full
receipt, cProfile data, top-function listing and exact script are retained as
`diagnostic-001-receipt.json`, `diagnostic-001.prof`,
`diagnostic-001-profile.txt` and `profile_saved_reference_001.py`.
