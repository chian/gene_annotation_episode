# A101: what a child returns is returned for the head to use, and everything it names is returned too

## The rule (owner's decision, 2026-11-20)

"head cannot read child directly. child has to offer it up and head takes what it takes." The rule that follows: WHAT A
CHILD RETURNS, IT RETURNS FOR THE HEAD TO USE, AND EVERYTHING THE RETURNED RECORDS NAME IS ALSO RETURNED TO THE HEAD (or
already held by it). Anything private stays inside the child and is never named in what it returns. There is no sealed
or unread field.

## What was built

- `jobs/job_records.returned_with_names(reader, refs)`: the records the child chooses to return, with everything they name,
  recursively, among the records the child holds (the walk the head's `msg_to_child._custody` does). `named_records` is its
  one step: a Store record names what the Store's rule says (`reader.named_references`); an artifact names none; a job
  ledger row names its reply artifact (`source_ref`), `result_refs`, the artifacts a handoff staged (`detail.input_refs`, a
  mapping the Store rule does not follow) and the handoff a check or closure belongs to (`detail.handoff_ref`).
- Each child's `internal_summary` builds `handoff_refs`, `check_refs`, `closure_refs` and `graded_refs` through it (the
  child's `final_to_parent` receives only the summary, no reader, so the closing runs where the records are read; its
  return form is unchanged: the four fields of each list, now closed).
- The head's summary `named_refs` covers every held reference, job rows included, through the same `named_records`; a
  commission that continues a held job (`msg_to_child._continued`) passes back the rows and, in `input_refs`, every held
  record they name. The head's count of outstanding handoffs counts handoff rows (the returned lists now hold artifacts).
- Private names removed at the source: bvbrc_msa no longer stages `plan.json` as a job input (the job's identity is in the
  handoff row's estimates; the extract recomputes the plan from the held search, which is deterministic). Feature group,
  target FASTA, MetaCATS derived alignment and group TSV are shared data and are returned. BLAST: query FASTA is the
  head's own; report, metadata JSON and replies are returned. No other private name was found.
- `reusable_alignments` is order-independent (keyed over every element of `used`).
- C3's `TypeError: Strings must be encoded before hashing` in the MSA launch: `feature_group_bytes` returned text
  (`canonical` returns `str`) and `feature_group_ref` hashed it; it now returns bytes.
- Point fixes kept: the job identity in the handoff row's estimates (the row's own fact); `sequence_ref` None on references;
  `held_searches` matches the query among `input_` records; MetaCATS's head-side `plan` reads the sheet and not the
  alignment (harmless, equivalent; not rewritten without a run to verify).

## Run R1: prediction (written before the run)

Target: CspA P0A9X9 (70 residues), fresh workspace `runs/a101_returns_ws_R1`, run `runs/a101_returns_run_R1`, local and
BV-BRC bound, Pfam, the yield settings of H1, the global ledger. One `Homology`, one `MSA`, one `MetaCATS` submission at
most.

1. The head summarises after every child returns, with no `CustodyError`. After bvbrc_blast returns, the head holds the
   handoff, check and closure rows and the report, reply, metadata and query artifacts; after bvbrc_msa returns it holds
   `msa.afa`, `sequences.fasta`, `group.json`, replies.
2. The credit after each unit is the sum of the entry scores of the candidates admitted plus differentials (credit
   definition `a101_differential_credit_v1`). The search admits product candidates (H1 gave five products, scores
   0.80 to 0.96; the batched naming may change them); the profile scan admits the family CSD (0.82 in H1). No differential
   arises before the MSA. After the MSA unit the alignment's `alignment` observations are a second test every aligned
   product underwent: each underwent test 1 (search) and test 2 (MSA); a differential is the absolute difference of the
   two candidates' score moves in a test both underwent; I will compute each by hand from the scores before and after.
3. If the model commissions MetaCATS, the child opens `msa.afa` in `prepare` and `extract` because the head held and passed
   it; the groups are the aligned products with at least two sequences each.
4. Ledger rows: expected (the model's estimate), measured (the service task record's submit to completion) and observed
   (the first status showing the end), one row per launch.
5. Count check: every record each returned list names is held by the head (equal count, none missing).
