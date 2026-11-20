# blast_database_preparation: the episode subtree (addendum to blast_database_preparation.md, 2026-11-20)

The owner's approved view (this part):

```
blast_database_preparation   builds or masks a database from a sequence set; produces a prepared-data record that the head holds and passes on
├─ launch_local              (small sets)
├─ launch_hpc                (large sets)
├─ monitor
└─ results                   evidence-free: checks the build, writes the prepared-data record
```

Folder: `root/a101/sequence_homology_evidence/blast_database_preparation/` with four child folders of those names.
No episode here is a grading episode: the build's usable check is an automatic step inside `results`, coupled to
the fetch. Every decision that is not a real choice is made by code (no model request); the one model-driven
episode is `monitor` (what to look at in a running job), a copy of the generic monitor without dependency monitors.

## Step zero: what already exists for each function, and what is written here

| Function | Exists (called, not rewritten) | Written in the episodes |
|---|---|---|
| Validate controlled commission, count FASTA, compile job and plan, derive the kind | `blast_preparation_job` (`validate_commission`, `compile_preparation`), `blast_analysis_kind.derived_analysis_kind` | the assignment forms that carry the same controlled fields |
| Stage plan and driver, launch locally or as a PBS batch job | `blast_preparation_run.launch_preparation`, `pbs_batch_job`, `execute_on_local_resource` | the launch tools that call it |
| Check, fetch only the receipt, evaluate usable, write the prepared-data row | `blast_preparation_run.acquire_prepared_data`, `blast_preparation_receipt.evaluate`, `prepared_data.put_prepared` | the results tool that calls it |
| Credit for usable records, controlled features | `prepared_data.prepared_credit`, `prepared_features` | `credit.py` and the return form |
| Handoff and check rows | `jobs/job_records.py`, `episode_runtime/job_access.py` | `credit.py` reads them through `records` |
| Wait on a job, status reading, progress information | `jobs/job_wait.py` (`wait_for_job`), `jobs/job_progress.py` | the results wait tool; the monitor's tools |
| Completion and accumulation controllers | `yield_control` | `yield_estimator.py` of each episode |

Software identities (executable, digest, engine version) and the resource's Python are not in a commission (a
commission carries no path). Each launch episode reads them from its own settings (`settings['resources'][resource_id]`),
the run's configuration of that episode; the resource's scratch bound comes from `job_access.describe`.

## The commission (controlled values only)

Parent and launch leaves: `kind` (`database_build` or `masking`), `molecule`, `input_refs` (one record: the FASTA in
custody), for a build `parse_seqids`, `hash_index`, `db_version`; for masking `program`, `output_format` and the
numeric parameters of that program; `resource_id`; for a PBS resource the `allocation` record (account, queue,
select, walltime, filesystems: scheduler operands passed through, never chosen); `handoff_unit` and `prepared_unit`
(positive credit numbers). Results: `handoff_refs`, the declared `kind`, `prepared_unit`. Monitor: `handoff_refs`,
`known_progress_refs`, `requested_fields`, `information_unit`.

## Parent flow (all decided by code)

1. Commission `launch_local` (a local resource) or `launch_hpc` (a PBS resource), chosen from the resource's kind.
2. For a cluster job, commission `monitor` once the handoff is held.
3. Commission `results`; a job still running comes back as not yet established, and the parent commissions `results`
   again. A cluster job's results can follow hours later.
4. Return credit, a finding and, when selected, `prepared_data_refs` and `execution_handoff_refs`.

Credit: `handoff_unit` once a handoff row is held; `prepared_unit` once per distinct usable prepared record (D17: only
what is gained; a repeat or a failure earns nothing). Stopping is each episode's yield estimator alone.

## Real tests and what is not run

Leaf first, then parent: real runner, real local job (bundled BLAST+ `makeblastdb`, `blastdbcmd`, `blastdbcheck`,
`segmasker`), no pytest. `launch_hpc` and the cluster path of the parent need the owner's authenticated Aurora
session: they are built and validated offline (contract, compiled job, PBS operands) and are not run.
