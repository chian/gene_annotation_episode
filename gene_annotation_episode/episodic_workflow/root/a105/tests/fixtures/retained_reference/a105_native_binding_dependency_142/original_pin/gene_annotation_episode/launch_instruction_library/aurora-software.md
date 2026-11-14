# Reusing or preparing Aurora software

The saved 2026-10-22 workspace directory and successful manual execution record
identify an existing Gentner deployment:

| Component | Observed location |
| --- | --- |
| Source, `chrisagrams/gentner-ave` | `/lus/flare/projects/BioReason-Aurora-Test/gentner-pipeline/repos/gentner-ave` |
| Python environment | `/lus/flare/projects/BioReason-Aurora-Test/gentner-pipeline/venvs/gentner/bin/python` |
| Existing personal workspace | `/lus/flare/projects/BioReason-Aurora-Test/chian` |
| Existing run artifacts | `/lus/flare/projects/BioReason-Aurora-Test/chian/runs` |
| Existing data-lake directory; contents uninspected | `/lus/flare/projects/BioReason-Aurora-Test/cgrams/gentner-data-lake` |

Job `8953621.aurora-pbs-0001.hostmgmt.cm.aurora.alcf.anl.gov` actually used this
environment, Python 3.12.12, Biopython 1.87 and Gentner's `AnalysisExecutor` to
return 17 global BLOSUM62 protein comparisons. Its source/input hashes, scores,
return code and distinct timings are retained in
`verification/aurora_bioinformatics_2026-10-22_001/`. This does not establish
other algorithms, installed databases or current compatibility. Read that
deployment's own `AGENTS.md`, `MEMORY.md` and relevant instructions before
changing it; the test did not validate its other stages.

Use the actual assigned software and inventory to decide whether inspection,
reuse, preparation or repair is useful. Retain the exact executable, source
revision/hash, package versions, database release/hash and validated inputs
needed by this job. Do not reinstall or recalculate simply because a new episode
started. Missing or changed requirements can justify a selected preparation
action; their presence does not remove output validation.

Aurora's [Python guide](https://docs.alcf.anl.gov/aurora/data-science/python/)
describes module-provided environments and extending them with a venv. Modules
can change SDK/libraries and must be loaded again in a new shell when required.
Inspect the relevant module and interpreter; neither an old framework path nor
the name `python3` guarantees the desired version. The manual test encountered
system Python 3.6 in a diagnostic wrapper. Keep any new venv, package cache and
temporary build work in the required project workspace. Source rows A4–A6.
