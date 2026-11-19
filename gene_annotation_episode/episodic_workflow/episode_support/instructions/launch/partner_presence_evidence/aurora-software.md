# Aurora software, preparation and reuse

These existing preparations were observed in the project workspace. Verify them
when needed; they are not proof of present availability or compatibility.

| Component | Observed location |
| --- | --- |
| Source, `chrisagrams/gentner-ave` | `/lus/flare/projects/BioReason-Aurora-Test/gentner-pipeline/repos/gentner-ave` |
| Python environment | `/lus/flare/projects/BioReason-Aurora-Test/gentner-pipeline/venvs/gentner/bin/python` |
| Personal workspace | `/lus/flare/projects/BioReason-Aurora-Test/chian` |
| Run artifacts | `/lus/flare/projects/BioReason-Aurora-Test/chian/runs` |
| Data-lake directory; contents uninspected | `/lus/flare/projects/BioReason-Aurora-Test/cgrams/gentner-data-lake` |

Read the
deployment's own `AGENTS.md`, `MEMORY.md` and relevant instructions before changes.
Do not reinstall or recalculate simply because a new episode started.

The assignment supplies the job, inputs, result requirements, workspace and
constraints. Choose scripts, an environment and commands to satisfy that job.
Preserve the scientific inputs and pinned software contracts when adapting
execution to Aurora. Retain the actual executable, source revision/hash,
package versions, database release/hash and validated inputs needed to identify
the calculation that produced the requested result.

Use the supplied `inventory_snapshot` and declared path/hash predicates to
decide whether inspection, reuse, preparation or repair would be useful.
Inventory metadata does not establish present compatibility. A selected
preparation command retains its actual operands and outcome. Reusing a valid
setup does not itself satisfy requested output predicates, and repairing setup
does not authorize a replacement for active or uncertain native work.

A command's directory or exports do not alter the next action. Supply the
working directory and environment for each selected command, or write a script
that prepares its own environment. Preserve any explicit environment requirement
of the scientific job and its original execution identity.

Aurora's [Python guide](https://docs.alcf.anl.gov/aurora/data-science/python/)
describes module-provided environments and extending them with a venv. Such
documentation supplies technical options, not proof that a module, interpreter
or environment is available in the selected configuration. Choose any needed
preparation within the actual assignment workspace and retain its result.
Modules must be loaded again in a new shell when required. Neither `python3` nor
an existing path proves a suitable version. Keep new environments, package caches and
temporary builds under `/lus/flare/projects/BioReason-Aurora-Test`.
