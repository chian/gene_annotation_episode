# Root execution regressions after B004 integration

The retained `run_verification.py` invoked the existing execution-family,
execution-progress and configured-tool-declaration tests. The final result was
**32 passed in 77.87 seconds**. All production Python files remained unchanged
during the run; 130 repository modules were actually loaded. Exact commands,
before/after hashes and test outcomes are in `VERIFICATION.json`, with pytest
output in `pytest-final.log`.

The declaration checks include two resource bindings for the same native
program with different supported modes and instructions, and preservation of
the original parent request when its resource identity comes from the declared
request map. They do not launch a new scientific job.

These regressions check existing generic execution and progress behavior.
Native numerical publication, complete output capture and actual numerical
parent admission are separately verified by the B004 publication and results
integration workloads. No new live API or HPC verification, configured-model
scientific investigation, or pending NCBI BLAST job check is claimed here.

The earlier 30-test root run overlapped source changes and is not the final
stable-source evidence. Its count must not be added to this overlapping run.
