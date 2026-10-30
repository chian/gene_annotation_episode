# Reproduction commands

Working directory: `/home/chia/repos/gene_annotation_episode`.

The executed profiling command was:

```sh
.venv/bin/python -B verification/tool_graders_protein_structure_validation_profile_2026-10-27_415/run_bounded.py check001
```

`check001` is retained and must not be overwritten. A separately authorized repeat
uses a fresh check name. The actual worker argv, cwd, environment and policy are
in `check001/selected_request.json`; verified cgroup settings and observed outcome
are in `check001/receipt.json`. Snapshot creation and retained-input hashing run
outside the measured diagnostic, just as the prior410 launcher prepares its own
snapshot before bounded execution. No native scientific work is dispatched by
the diagnostic. Its guard rejects subprocess and network dispatch.

Profile analysis can be reproduced without importing the workflow:

```sh
.venv/bin/python -B verification/tool_graders_protein_structure_validation_profile_2026-10-27_415/analyze_profile.py check001
```

The binary `check001/diagnostic.prof` is the full cProfile record. All-function
tables sorted by cumulative and self time, structured function rows, and selected
caller edges are retained beside it. Named stage wall and process CPU times are
in `check001/profile_stages.json`. Timing/profile helper startup and the final
profile serialization are outside the enabled profiling interval; measurement
metadata states this explicitly.

No profiled diagnostic failed. Three read-only examination mistakes are retained
in `analysis_failures.json`. They did not invoke native work or alter inputs.
