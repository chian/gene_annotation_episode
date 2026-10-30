# First manual Aurora bioinformatics execution

PBS job `8953621.aurora-pbs-0001.hostmgmt.cm.aurora.alcf.anl.gov` finished with
`job_state=F` and `Exit_status=0`, using the `BioReason-Aurora-Test` allocation,
one node in the `debug` queue and a five-minute requested walltime.

The job ran on `x4418c4s1b0n0`. It reused the deployed
`chrisagrams/gentner-ave` source and its existing Python environment, without
installing software or launching a model service. Gentner's `AnalysisExecutor`
returned all 17 global protein comparisons of the existing 253-aa gene_001/ybhP
query against the existing reference FASTA, using BLOSUM62, gap opening -10 and
gap extension -0.5. These are native alignment scores; this test did not update
the annotation, annotation credit or scientific investigation state.

## Observed timings

| Measurement | Value | Source |
| --- | --- | --- |
| Current queue entry to scheduler start | 161 seconds | Completed PBS `qtime` to `stime`, on the same server clock |
| Scheduler cumulative eligible time | 162 seconds | PBS `eligible_time` |
| Executor script action | 6.796 seconds | Gentner `ExecResult.duration_s`; includes imports and output writing inside that action |
| Full Python driver | 58.91138992505148 seconds | Driver monotonic elapsed time; includes its setup and shutdown |
| PBS accounted walltime | 141 seconds | `resources_used.walltime` |
| Scheduler start to job obituary | 176 seconds | Completed PBS `stime` to `obittime`; not substituted for execution time |

This was an interactive test. Its allocation includes human/command delay and
setup, so the timing quantities are retained separately. It supplies one actual
run, not a fitted forecast or a scaling law. No workflow statistics or closed
yield histories were changed.

## Files and locations

The original run directory on Aurora is:

`/lus/flare/projects/BioReason-Aurora-Test/chian/runs/gene-annotation-aurora-20261022T151552Z`

`alignment_scores.json` contains all 17 native scores. `executor_result.json`
and `executor_trace.json` preserve the executor's received result and trace.
`execution.json` records the actual Python environment, package versions, input
and source hashes, node, job identity and driver timings. `allocation.json`
preserves the assigned node. `pbs_completed.json` is the final scheduler
receipt. Inputs and the exact driver/analysis sources are retained here too.

`submission_intent.json` is the immutable pre-submission snapshot; its
`prepared_not_submitted` value describes that earlier instant, not final job
state. The authoritative completed receipt is `pbs_completed.json`.

The attempted running-state query wrapper used a newer subprocess argument on
the system Python 3.6 interpreter and failed before querying PBS. That error is
retained in `pbs_running.json`. Final PBS state was subsequently collected with
compatible arguments. No running-state priority history was obtained.

Aurora's small index is `/home/chian/WORKSPACE_DIRECTORY.md`; its local copy is
`WORKSPACE_DIRECTORY.md` beside this record. It lists the existing personal
workspace, Gentner source/environment, data-lake directory, allocations and
storage observations. Long-term layout and backup destination remain open for
the user's guidance. The full episodic workflow has not been deployed to HPC
by this manual test.
