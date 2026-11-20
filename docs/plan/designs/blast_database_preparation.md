# BLAST database and data preparation: design record, phase 1 (2026-11-20)

Fork F2. Nothing here has been run. No workload was started; the five new library modules were only syntax-checked
by reading. Marks: **[owner]** said by the owner; **[inference]** proposed by Claude and not yet accepted.

## 1. What this is and is not

- **[owner]** Masking and utilities are ways to set up BLAST databases and data for later work. The formatter is not
  needed (parsers are general). The VDB formatter is probably not needed because nothing is submitted. Database setup
  and job setup on a cluster make the most sense for a custom, non-NCBI database to search against, and for
  large-scale clustering of reads or sequences.
- **[inference]** So this kind produces **data for later work, not an evidence sheet.** Its result is a
  *prepared-data record* the Episode holds. Later database-search and all-vs-all commissions name that record by
  reference. Credit is earned when a usable prepared record is established.
- It is part of the one BLAST declared-kind field: pairwise and `database_search` already exist as values; this adds
  `database_build` and `masking` (the all-vs-all fork adds its own).

## 2. What the old code intended, read from content, and what is not carried

Read from the contracts, not the file names:

- **Masking** (dustmasker for nucleotide, segmasker for protein, windowmasker with a counts step, a converter to the
  mask format makeblastdb accepts): marks low-complexity stretches of a supplied FASTA. Outputs are intervals, a
  masked FASTA, or statistics. The old results also computed masked-fraction ratios.
- **Utilities**: `makeblastdb` builds a sequence database from a FASTA (multi-file output); `blastdbcmd` extracts
  sequences from a database or reports its information and metadata; `blastdbcheck` checks integrity; the alias tool
  makes subset or aggregate databases and converts identifier lists; `makembindex` makes a megablast index;
  `makeprofiledb` makes a profile (RPS) database; the VDB command line tools read VDB data.
- **Manifest of a prepared database**: a key, a kind (protein sequence, nucleotide sequence, RPS profile, delta, VDB),
  an identity (namespace, name, version, release), the files with sizes and digests, how it was prepared (program,
  version, argv, input manifest, receipt), whether the file inventory is complete, and an access mode
  (prepared local). Those facts are what a later search needs. They are carried as the new record below.
- **Not carried (old-runner machinery):** the attempt/plan/bundle/owner-file scheme of the native lifecycle, the
  "capture" of original files by a coordinator reading the resource's directories, absolute native paths held in the
  manifest, and the two-layer "practical state" plumbing. The new scheme reads facts the job itself produced, through
  the job service and custody.

## 3. Kinds and the controlled commission

The commission is controlled values only: a kind from a fixed vocabulary, record references, booleans, a value from a
fixed set and numbers in a range. No command, no path, no free text, no database title.

| Kind (declared) | Fields | Native program |
|---|---|---|
| `database_build` | `molecule` (protein or nucleotide), `input_ref` (the FASTA, a record reference), `parse_seqids` (boolean), `hash_index` (boolean), `db_version` (4 or 5) | `makeblastdb`; then `blastdbcmd -info` and `blastdbcheck -full` as checks |
| `masking` | `molecule`, `input_ref`, `program` (`dustmasker` nucleotide, `segmasker` protein), `output_format` (`interval` or `fasta`), plus that program's numeric parameters, each optional and in its native range | `dustmasker` or `segmasker` |

- The database's title is the record's own key (a digest of the input digest, the kind and every option), so there is
  no human-chosen name and the same build always has the same key.
- **Later additions, not in v1 code:** `windowmasker` with counts, the mask converter and a mask output usable by
  `makeblastdb` (needs a consumer-side check that the database build accepted it); `sequence_extraction`
  (`blastdbcmd` over a prepared database and a held list of entries, producing a *sequence set* record the
  all-vs-all fork needs). Nothing placeholder was written for them: a kind enters the vocabulary only when it has real
  behaviour.

## 4. Declared and derived kind

- The commission declares the kind (the shared declared-kind field of the results assignment; the vocabulary is the
  union of every BLAST use's kinds).
- **Derivation is from what was actually launched.** The job compiles to a *plan* (`plan.json`). The kind is read
  from the program the plan's first step runs: `makeblastdb` gives `database_build`; `dustmasker` or `segmasker`
  gives `masking`. At the launching side `compile_preparation` derives it from the plan it just built and refuses a
  difference. At the **results side** the plan is read from the handoff row's own staged inputs (the artifact staged
  under `plan.json`), its kind is derived and compared with the kind the results commission declares; a difference
  raises. This is the check that is not circular: it reads what ran, not what anyone says ran.
- A mismatch fails the run with its error. Nothing repairs it, retries it or falls back.

## 5. The job: one driver, one plan, one receipt

- **[inference]** Verification has to happen where the files are, so the same job works locally and on a cluster. A
  small standard-library-only driver (`driver.py`) is staged with the plan and the input. It runs the plan's steps in
  order and writes `receipt.json` last and atomically. The driver decides nothing: usability is decided later, on the
  coordinator, by one pure function.
- Steps of `database_build`: `makeblastdb` (build), `blastdbcmd -info` (the native summary), `blastdbcheck -full`
  (integrity). A failed step stops the rest. The receipt holds, for each step, whether it ran and its exit code; every
  produced file with its size and its digest (computed on the resource); the native summary (sequence count, letter
  count); for a mask, the masked residues counted from the produced output.
- **No stdout/stderr paths are declared [owner D10].** The contract declares no output path for logs. The driver's
  step logs are ordinary files in the job directory. Nothing in the contract or the route honours, writes or checks
  them.
- The job's command is `python driver.py plan.json` with the resource's own Python. The BLAST programs' paths and
  digests come from the resource's configuration, never from the commission.
- Exit status: 0 all steps returned 0; 1 a step failed (receipt still written); 2 the plan or the staged input is not
  what the plan says (nothing run, no receipt).

## 6. The prepared-data record (the interface for database search and all-vs-all)

A row of the declared work table `prepared_data`, written through the tool's scoped store, held by the Episode that
established it. Later episodes receive its reference in a `record_refs` field and read it through the custody reader.

| Column | Meaning |
|---|---|
| `data_key` | the record's key: a digest of the input digest, the kind and all options (same build, same key) |
| `prepared_kind` | `blast_protein_database`, `blast_nucleotide_database`, `masked_sequences` or `mask_intervals` |
| `state`, `usable` | `usable`, `failed` or `incomplete`; `usable` is true only for the first |
| `molecule` | protein or nucleotide |
| `input_ref`, `input_sha256`, `input_records`, `input_residues` | the FASTA the product was built from, by custody reference and digest, with its counted records and residues |
| `program`, `executable_sha256` | the producing program and the digest of its executable |
| `resource_id`, `job`, `placement_prefix` | **where the files are**: the resource, the job handle (its directory is the resource's workspace plus the handle), and the path prefix inside it (for a database, `db/prepared`) |
| `files` | every produced file: name, bytes, sha256 |
| `facts` | the checked facts (see 7) as numbers, booleans and fixed values |
| `failure_codes` | typed codes from a fixed vocabulary |
| `plan_ref`, `receipt_ref`, `handoff_ref`, `closure_ref` | the plan, the receipt, and the job's handoff and closure rows, all held |

**How a later search finds a database [inference, for the database-search fork]:** it is commissioned with the
`prepared_data` reference (a controlled record reference) and the resource. The builder reads the row through the
custody reader and requires `usable`, `prepared_kind` of the right molecule, and `resource_id` equal to the resource
the search runs on. The database's absolute path is the resource's workspace + `/` + `job` + `/` + `placement_prefix`,
taken from the resource's own description. The search job's driver should re-check each file's *size* against `files`
before it runs (a digest of a large database is too slow to recompute); a moved or truncated database then fails with
its own error. A database is never copied between resources by the system: it is searched where it was built.

## 7. What "usable" means: checked facts, all deterministic

A product is `usable` only if **every** one of these holds. Each is checked from the receipt and the route's own
listing of the job directory; none is assumed:

1. The receipt's plan digest equals the digest of the staged plan, and the staged input was verified against the plan
   (size, digest, record and residue counts).
2. Every step of the plan ran and returned 0.
3. Each file in the receipt appears in the route's listing with the same size.
4. **Database:** the native summary parses, its sequence count equals the input's record count and its letter count
   equals the input's residue count; the files are all there (the single set `.phr/.pin/.psq` or `.nhr/.nin/.nsq`, or
   every volume the alias file names); the full integrity check returned 0.
5. **Mask:** the output is present and parses; for a masked FASTA its record and residue counts equal the input's;
   masked residues cannot exceed the input's residues. Masked fraction is a computed number.

**States.** `failed`: a step returned nonzero, a fact contradicts the plan, or the job ended with no receipt (the
driver refused). `incomplete`: the job has not ended, or the receipt is absent or unreadable while it is still
running. A job that is still running is never read as a finished one, and absence is never inferred as success.

## 8. Credit, return and the episodes

- **Credit [inference]:** the commission's credit unit is earned once per distinct usable record (`data_key`),
  when that row is saved. A failed or incomplete record, a repeat of a held key and a status check earn nothing. The
  failure is still recorded, so the Episode learned something, but no progress is claimed. Stopping stays with the
  yield estimator alone; the profile key is `results:blast_preparation_v1`.
- **Return (controlled fields only).** Always: credit and a finding with `prepared_kind`, `state`, `usable`,
  `input_records`, `input_residues`, `files_count`, `bytes_total` and the facts that apply (`sequences`, `letters`,
  `integrity_ok`, `counts_match`, `inventory_complete`, `masked_residues`, `masked_fraction`), plus `failure_codes`
  from the fixed vocabulary. Selectable: `prepared_data_refs` (the row references). No path and no text leaves the
  Episode.
- **Episodes:** the launching leaf compiles and launches (a controlled commission in, a handoff row out); the monitor
  needs no change (it observes elapsed time and scratch use from the job's status replies); the results Episode gets
  one new family that acquires the receipt and writes the record.

## 9. Allocation and run mechanics (designed in, not ignored)

- **Window bounds.** One CPU, 5 GiB, no swap, one workload at a time, all enforced by the launcher's systemd slice
  and the local route's policy (`memory_bytes`, `scratch_bytes`; the policy has no elapsed-time setting). Nothing here
  adds a time or usage budget.
- **Local, small.** A protein database from a FASTA whose bytes are far below the policy's scratch bound. Staged input
  counts toward scratch. The only pre-launch check is the necessary one: the input alone must not exceed the
  resource's `scratch_bytes`, otherwise the commission fails with `input_exceeds_resource_scratch` (the work belongs
  on a cluster). Output size is not guessed. If the build exceeds the limits the route's enforcement ends the job,
  the route reports it failed, and the acquisition writes `failed` with `receipt_missing` and the observed scratch.
- **Cluster, large.** The PBS route takes `{mode: batch, script, arguments, env}`. The builder passes the commission's
  **allocation through unchanged**: `account`, `queue`, `select`, `walltime`, `filesystems`. All five are required
  and nothing is defaulted or chosen. **The walltime is a scheduler operand, separate from the Episode's
  continuation** (the launch library says the same), and the application sets none. The script changes into the job's
  directory and runs the driver with the cluster's own Python. The database stays on the cluster; the record names
  it. It can be validated offline (compile, the script text and the qsub operands) before the owner runs it.
- **Inputs.** Staged inputs travel with the launch request (a local file write, or one JSON request over the
  transport for PBS). That suits small and medium FASTA sets. **A very large set cannot be staged this way**; it
  must already be on the cluster as a prepared set (a "resident input"). Resident inputs are not in v1 (decision D-P3).
- **Outputs.** Only the receipt is fetched into custody. Database files never are, because the job service's fetch
  reads whole files into memory. The record keeps their sizes and digests, not their bytes. Keeping a small database
  in custody as artifacts too is possible but not designed (decision D-P5).
- **Durations.** Unknown for a kind with no history, and recorded as unknown. The launch records only what is known
  (input bytes, records, residues) as its estimates; the monitor observes elapsed time and scratch bytes from
  status replies. Later runs can use that history. No deadline anywhere.
- **Idempotency.** The job's handle comes from the unit's operation key, an abandoned handoff row is taken over, and
  the prepared-data row is keyed by `data_key`, so a resumed unit writes the same row (a new revision if its state
  changed) and never builds twice.
- **Incomplete is not finished.** A job that has not ended is reported as it stands and nothing is written.

## 10. The stubs in the A101 results episode: rebuild or delete

Families the carried code names and raises `NotImplementedError` for (forbidden by AGENTS.md):

| Family | Proposal |
|---|---|
| masking | **Rebuild** as `masking` (dustmasker, segmasker, intervals and masked FASTA) in the new family. Windowmasker counts and the converter: later, with the mask-for-makeblastdb consumer check. |
| utility: `makeblastdb` create | **Rebuild** as `database_build`. |
| utility: `blastdbcmd` info and metadata, `blastdbcheck` | **Absorbed** into the build's checks (step 3 of the job); no family of their own. |
| utility: `blastdbcmd` extract sequences | **Rebuild later** as `sequence_extraction` (the all-vs-all fork needs sequence sets). Delete the old family now. |
| utility: alias tool, `makembindex`, `makeprofiledb` | **Owner decision D-P2.** My lean: delete. Nothing named so far uses them. |
| utility: VDB tools (`blast_vdb_cmd`) | **Delete** (owner: nothing is submitted). |
| standard BLAST database, BLAST database | These are database **search** families: the database-search fork's area, not preparation. |
| HMMER preparation, HMMER (non-phmmer) | HMMER is later. Not touched. |
| API, local file source | Not BLAST preparation. Not touched. |

## 11. Library modules written (all new files, none edits an existing file)

- `forms/similarity_search/sequence_homology_evidence/blast_preparation_job.py`: kinds, the controlled commission
  validators, FASTA counting, `compile_preparation` (job, plan, staged inputs, estimates), `derive_kind`,
  `validate_plan`.
- `tools/similarity_search/sequence_homology_evidence/blast_preparation_driver.py`: the standard-library job program.
- `readers/similarity_search/sequence_homology_evidence/blast_preparation_receipt.py`: `evaluate`, the only place
  `usable` is decided; the typed failure codes.
- `records/similarity_search/sequence_homology_evidence/prepared_data.py`: the `prepared_data` work table, the row
  builder, the scoped write, credit and the controlled features.
- `jobs/similarity_search/sequence_homology_evidence/blast_preparation_run.py`: `launch_preparation` (stage and launch,
  local or PBS, with the allocation passed through), `pbs_job`, and `acquire_prepared_data` (check, fetch the receipt
  only, evaluate, write the row).

**What is unverified.** They were only read for syntax and consistency; none has run. These details depend on the real
programs and are to be checked in phase 2: the exact `blastdbcheck` flags (`-full` is assumed), the `blastdbcmd -info`
text (the parse looks for "N sequences; M total residues/bases"), the file set `makeblastdb` writes for each option
combination (only the base trio is required), the volume naming for large databases, and whether the native summary's
letter count equals the input's residue count.

**A hazard to know about.** During this work files created by other forks and by the main conversation (the A101
plan page, the deferred regions record, the pairwise library files) disappeared from the working tree, and tracked
A101 files returned to their Nov 19 state. One of my own modules was also deleted once and re-created. I could not
find the cause. Copies of my modules are kept in the scratchpad (`.../scratchpad/f2_backup/`).

## 12. Proposed patches to existing files (not applied)

All are in A101 only. The results-episode files below were also edited by the pairwise fork, and that work is
currently absent from the working tree, so these patches assume it is re-applied first and add a second family beside
the pairwise one.

1. **`root/a101/.../execution_result_acquisition/messages/read_from_parent.py`**
   - `family(target, selector)`: `if selector.get('version') == 'blast_preparation_return_request_v1': return
     'blast_preparation'` (placed before the others). Delete the branches for masking, utility, and for the
     `native_hmmer*`, standard database and database requested jobs that this episode must not carry.
   - `ASSIGNMENT_FORM`: the shared `analysis_kind` field's vocabulary gains `database_build` and `masking`.
   - `validated_selector`: `blast_preparation` returns the selector after checking it is the closed record
     `{'version': 'blast_preparation_return_request_v1', 'return_type': 'prepared_data'}`. The old masking and
     utility branches are deleted. For this family the `target` carries the handoff and resource only: the plan is
     read from the handoff row.
   - `read_from_parent`: for `blast_preparation`, require `analysis_kind`, and put `declared_kind` in the parent input.
2. **`.../task.py`**: add the tool and its catalog.
   ```python
   def prepared_data_acquire(arguments, ctx):
       return acquire_prepared_data(ctx, arguments['handoff_ref'], declared_kind=arguments['declared_kind'])
   PREPARED = {'name': 'prepared_data_acquire',
               'description': 'Ask the job once; when it has ended, fetch only its receipt and keep the prepared-data '
                              'record of what it built, usable or not. Nothing is done while the job is running.',
               'input_schema': obj({})}
   ```
   `_catalog` adds `if family == 'blast_preparation': return [PREPARED]`; `FAMILY_INSTRUCTIONS` adds a short
   instruction and the credit sentence ("earned once per usable record when it is saved"); register the tool in
   `TOOLS`. Delete the `raise NotImplementedError('unplaced:' ...)` for these families.
3. **`.../credit.py`**: `if family == 'blast_preparation': return prepared_credit(records, summary['acquired_record_unit'])`
   (imported from `records/.../prepared_data.py`); the `unplaced:` raise goes for this family.
4. **`.../messages/internal_summary.py`**: for this family hold `prepared_rows(records)` and the last outcome.
5. **`.../messages/final_to_parent.py`**: add the finding fields of section 8 (numbers, booleans, vocabulary values and
   the `failure_codes` list) and the selectable `prepared_data_refs`; keep credit and finding always returned.
6. **`.../yield_estimator.py`**: profile key `results:blast_preparation_v1`.
7. **`root/a101/.../execution_job_submission/local_job_execution/`** (the launch leaf): `read_from_parent` accepts
   `requested_job = {'blast_preparation': <controlled fields>}` and validates it with `validate_commission`;
   `action` returns a `ToolCall('launch_preparation', ...)` whose tool does
   `compiled = compile_preparation(fields, input_bytes=ctx.store.get_artifact(fields['input_ref']),
   software=<resource software>, python=<resource python>, scratch_bytes=<policy scratch>)`, then
   `await launch_preparation(ctx, resource_id, compiled)`. The model still writes no command; it chooses the action.
   Credit stays the handoff's. The cluster leaf needs the same branch through `launch_preparation(..., allocation=...)`;
   the HPC leaf's current design (the model writes shell commands) is outside this area and I changed nothing there.
8. **Resource configuration (`jobs/job_services.py`, `jobs/local_job_route.py`, `jobs/pbs_job_route.py`)**: the
   route's `describe()` gains `software` (`{program: {executable, sha256, engine_version}}`) and `python`, from the
   resource's configuration. Those files are already modified in the working tree by others, so I made no edit.
9. **`records/sequence_homology_evidence/practical_execution_records.py`**: in `validate_assignment`, delete the
   branches that import the old utility and masking contracts. The launch leaf's own check above replaces them.
10. **Deletions once approved (A101 copies only; other axes have their own copies):** the old masking and utility
    acquisition modules, their contracts, result views and local-plan modules, and the VDB utility ones, per the table
    in section 10.

## 13. Real-run recipe for phase 2, with predictions

Run through `bash tools/one_workflow.sh runs/<unique> -- $PWD/.venv/bin/python -B <script>`, one workload at a time,
real model, no pytest, bundled BLAST+ 2.17.0.

1. **Small protein database, local.** A FASTA of 12 distinct real protein sequences (50–400 residues, unique
   identifiers) held in custody. Commission `database_build`, protein, `parse_seqids` true, `hash_index` false,
   `db_version` 5.
   - *Predictions:* the launch leaf earns its handoff credit and ends by `yield_stop` after one unit; the job finishes in
     seconds; the receipt shows build, info and check each returning 0; the summary gives 12 sequences and the input's
     residue count; the integrity check passes; the prepared-data row is `usable`; the results Episode ends by
     `yield_stop` and earns the credit unit once; resume asks the model nothing and the row is unchanged.
   - *Inspect:* the produced file set against section 7; the exact summary text; the `blastdbcheck` flag; the staged
     names; that the route's listing and the receipt agree; that the receipt was the only file fetched.
2. **Masking.** A protein FASTA with one low-complexity run; `segmasker`, `interval` then `fasta`. *Predictions:*
   `usable`, masked fraction above zero and below one, counts equal for the masked FASTA.
3. **Failure and recovery cases (each real):** a commission whose declared kind differs from the staged plan (raises at
   acquisition); a FASTA with a repeated identifier and `parse_seqids` true (refused at commission); a job killed
   before its receipt (incomplete, then failed on a later acquisition); an input larger than the policy's scratch
   (refused). *Predictions:* each yields its named code and no credit.
4. **Offline for the cluster:** compile with a PBS allocation and check the script and qsub operands against the
   resource's described constraints. Do not run `ssh`, `scp` or `qsub`. The Aurora run waits for the owner's
   authentication.
5. **Handoff to the database-search fork:** the `prepared_data` reference of run 1 is the custom-database operand it
   needs; searching that database is the first use.

## 14. Decisions for the owner

- **D-P1 Software and Python identities.** Is it acceptable that a resource's configuration carries `software` and
  `python`, exposed by the route's `describe()`, so commissions need no path? (The files to change are already being
  edited elsewhere.)
- **D-P2 Which utilities stay.** Alias tool, megablast index and profile databases: my lean is delete. VDB: delete.
- **D-P3 Large inputs.** Should a v2 add *resident inputs* (an earlier prepared set that already lives on the cluster)
  for sets too large to stage?
- **D-P4 PBS walltime.** Where does it come from? (Shared with the database-search fork's D-DB-4.) The builder only
  passes through what the commission carries and fails if it is missing.
- **D-P5 Small databases in custody.** Should a small database also be kept as artifacts so it can be rebuilt on
  another resource?
- **D-P6 Integrity check scope.** The build uses a full check. Is a sampled check acceptable for very large databases
  (it would be recorded as sampled and its facts would say so)?
- **D-P7 Masking for databases.** Should v2 produce the mask format `makeblastdb` consumes, with a consumer-side check
  that the build accepted it?
- **D-P8 Sequence sets.** The all-vs-all fork's set operand: should it be a `prepared_data` kind
  (`sequence_set`, produced by extraction), so one record type serves both forks?
