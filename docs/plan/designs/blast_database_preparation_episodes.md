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

## Status of the build (2026-11-20, build fork)

**Owner hold, in force:** `launch_hpc` and `monitor` (the long-job, HPC and polling parts) are neither built nor edited
until one shared design for HPC launch, API launch and monitoring is written. `launch_hpc` exists as an earlier,
unreviewed copy and is left exactly as it was; `monitor` stays an empty package. The parent below therefore commissions
only `launch_local` and `results` and refuses a cluster resource with `blast_database_preparation_resource_must_be_local`.
Nothing pretends to handle the cluster path. The parent gets `launch_hpc`, `monitor`, an `allocation` commission field
and a cluster branch in `decide` when the shared design arrives.

### What exists now

| Episode | Files | State |
|---|---|---|
| `blast_database_preparation` (parent) | goal, task, credit, yield_estimator, episode, messages/{read_from_parent, msg_to_child, read_from_child, internal_summary, final_to_parent} | built this session; imports; its forms admit, its decisions and credit match the checks below; not run |
| `launch_local` | full set | reviewed; one defect fixed (below); imports; not run |
| `results` | full set | reviewed; one defect fixed (below); imports; not run |
| `launch_hpc` | full set | NOT reviewed, NOT edited (hold); imports |
| `monitor` | empty package | NOT built (hold) |

### The parent

Commission from the head (controlled values and one record reference): `kind` (`database_build` or `masking`),
`molecule`, `input_refs` (exactly one FASTA record in custody), the kind's switches and numeric parameters,
`resource_id` (local), `handoff_unit` and `prepared_unit` (positive credit numbers). It is checked with the library's
own `validate_commission`; a wrong commission fails with its stable `blast_preparation_*` error.

Every decision is made by code, no model request: no handoff held -> `launch_local`; handoff held and no prepared-data
record -> `results` (again if the job had not ended); a record held -> `state_read`, which earns nothing, and the yield
controller ends the episode. The commission to `launch_local` is the controlled commission itself; the commission to
`results` names the handoff row and the plan artifact `launch_local` returned (so the receipt is checked against what
ran), the sequence set, the declared kind and the credit unit.

Credit (D17): `handoff_unit` once a handoff is reported, plus `prepared_unit` per distinct usable prepared-data record
a results child reported. A refused launch, a product that is not usable, a repeat of a held record and a read earn
nothing. Stopping: the completion controller with target `handoff_unit + prepared_unit`.

Returns (the head selects): always `credit` and `finding` (launches, acquisitions, `state` of `usable` / `failed` /
`not_established` / `not_launched`, `usable`, `failure_codes`, and the receipt's checked facts, each absent when not
established); selectable `prepared_data_refs` (what the head holds and passes on to database search and all-vs-all)
and `execution_handoff_refs`. No path and no text.

### Defects fixed in the existing leaves

- A commission with the wrong number of records (two input records, two handoffs) failed with Python's raw "too many
  values to unpack". `launch_local` and `results` now raise `blast_preparation_exactly_one_input_record_required` and
  `blast_preparation_results_<field>_must_be_exactly_one`. The parent has the same check. `launch_hpc` has the same
  pattern and is untouched (hold).

### What was verified, and how

A throwaway script (kept outside the repository, run through lane a101) imported the parent and both leaves and
exercised them with synthetic values, with no job, no model and no resource: the parent's commission is admitted by its
own form; its `launch_local` and `results` commissions are admitted by those children's assignment forms; each child's
return, built by its own `final_to_parent`, is admitted by its return form and read by the parent's `read_from_child`;
the parent's credit is 7.0 for a handoff plus one usable record at units 4.0 and 3.0; its return is admitted;
`decide` gives `launch_local`, then `results`, then `state_read`; a cluster resource is refused; refusals: a kind
outside the vocabulary, a build without `db_version`, a zero unit, two input records. This is NOT a real run: it shows
the forms and functions fit each other, not that a job runs.

### Run-ready prediction (a real run is deferred until the owner defines the real entry)

Commission `database_build`, protein, `parse_seqids` true, `hash_index` false, `db_version` 5, one FASTA of 12 distinct
real proteins (50-400 residues) in custody, the local resource, units 4.0 and 3.0. Prediction: zero model calls at every
level (all code-decided); the parent commissions `launch_local` (one unit, credit 4.0, ends at handoff), then `results`
(status; while the job runs a wait and another status; once ended only the receipt is fetched, the receipt shows build,
info and check each returning 0 and 12 sequences with the input's residue count; the record is `usable`; credit 3.0);
the parent's credit is 7.0 and the completion controller ends it after those two commissions; resume asks nothing and
writes no second record. Refusals, each with its own error and no job started: a kind outside the vocabulary, a FASTA
with a repeated identifier and `parse_seqids` true, an input larger than the resource's scratch bound, two input
records, a cluster resource. A job killed before its receipt: the record is `failed` with `receipt_missing`, no credit.

### Open items

- The earlier fork reported that the `launch_local` leaf passed a real run and found that `blastdbcheck` fails on every
  valid database (commit `7e6611afd`). No run directory of it exists, so that is relayed, not verified here.
- Decisions: the shared HPC / API / monitor design (pending, owner); windowmasker (held); the three credit units are
  passed by the head (`handoff_unit`, `prepared_unit`; the monitor's information unit joins when the monitor exists);
  `action` is still required by the system and is unreachable in a code-decided episode (the pairwise pilot's open
  question 2, a system matter); the parent's finding repeats the results finding's fields by design (episodes do not
  import each other).
