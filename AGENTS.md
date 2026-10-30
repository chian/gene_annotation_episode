# Repository layout

Put disposable execution output in the single top-level `runs/` directory.
Use a separate directory beneath it for each run when needed. This includes
logs, execution databases, temporary results, test execution output, copied
environments, dependency copies, and source snapshots made for a run.

Set tool working, temporary, cache, and output paths beneath that run directory.
For pytest, use `--basetemp=runs/<run>/tmp`; its default cache is already under
`runs/`. Disable Python bytecode writes or set `PYTHONPYCACHEPREFIX` beneath
`runs/` so imports do not scatter generated files through the source tree.

Do not create run-output directories in `verification/`, application source,
tests, research, or documentation. Ignore `/runs/` as one directory in Git.

Keep required test inputs and reusable test helpers with the tests, and keep
application code in its source directories. A run directory must not be the
only home of code or fixtures required by the project. Preserve required assets
before removing old generated output; do not classify a file as disposable
solely because it lives in a dated directory.
