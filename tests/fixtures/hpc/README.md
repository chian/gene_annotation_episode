These three JSON files retain selected fields from actual read-only Aurora
observations acquired on 2026-11-04 UTC: `qstat -f -F json`, `qstat -Qf -F json`,
and https://status.alcf.anl.gov/aurora/activity.json. They retain the three queued
debug jobs, debug queue rules, scheduling scores, and reservation quantities.
Names, user identities, arbitrary environment variables and paths are omitted.
They are historical parser inputs, not a simulated SSH service or live-job proof.

The full disposable acquisition is under `runs/hpc_design_20261104/observations/`.
Required parser fixtures live here so tests do not depend on that run directory.
