# Aurora software, preparation and reuse

The saved 2026-10-22 workspace directory and manual execution record identify
these existing preparations. These are historical observations to verify when
needed, not proof of present availability or compatibility.

| Component | Observed location |
| --- | --- |
| Source, `chrisagrams/gentner-ave` | `/lus/flare/projects/BioReason-Aurora-Test/gentner-pipeline/repos/gentner-ave` |
| Python environment | `/lus/flare/projects/BioReason-Aurora-Test/gentner-pipeline/venvs/gentner/bin/python` |
| Personal workspace | `/lus/flare/projects/BioReason-Aurora-Test/chian` |
| Run artifacts | `/lus/flare/projects/BioReason-Aurora-Test/chian/runs` |
| Data-lake directory; contents uninspected | `/lus/flare/projects/BioReason-Aurora-Test/cgrams/gentner-data-lake` |

Job `8953621.aurora-pbs-0001.hostmgmt.cm.aurora.alcf.anl.gov` used Python 3.12.12,
Biopython 1.87 and Gentner's `AnalysisExecutor` for 17 global BLOSUM62 protein
comparisons. The historical source/input hashes, scores, return code and timings
are retained in `verification/aurora_bioinformatics_2026-10-22_001/`. That evidence
does not validate other stages, databases or present compatibility. Read the
deployment's own `AGENTS.md`, `MEMORY.md` and relevant instructions before changes.
Do not reinstall or recalculate simply because a new episode started.

The assignment fixes `requested_job`, `workspace`, `initial_context`,
`constraints`, `progress_requirements` and `completion_keys`. A generic
requested job contains its exact `argv` and `environment`; registered native
jobs instead use their own closed software and input contracts. The remote
worker uses the configured `python_executable`. Retain the actual executable,
source revision/hash, package versions, database release/hash and validated
inputs needed by the assigned job.

Use the supplied `inventory_snapshot` and declared path/hash predicates to
decide whether inspection, reuse, preparation or repair would be useful.
Inventory metadata does not establish present compatibility. A selected
preparation command retains its actual operands and outcome. Reusing a valid
setup does not itself satisfy requested output predicates, and repairing setup
does not authorize a replacement for active or uncertain native work.

The persistent context supplies `cwd` and `environment` for preparation work.
A subprocess's directory or exports do not alter the next action; use
`practical.context.set` for a selected persistent change. The requested job
retains its original explicit environment and execution identity.

Aurora's [Python guide](https://docs.alcf.anl.gov/aurora/data-science/python/)
describes module-provided environments and extending them with a venv. Such
documentation supplies technical options, not proof that a module, interpreter
or environment is available in the selected configuration. Choose any needed
preparation within the actual assignment workspace and retain its result.
Modules must be loaded again in a new shell when required. The historical manual
run encountered system Python 3.6 in a diagnostic wrapper; neither `python3` nor
an old path proves a suitable version. Keep new environments, package caches and
temporary builds under `/lus/flare/projects/BioReason-Aurora-Test`.
