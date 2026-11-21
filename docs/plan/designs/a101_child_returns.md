# A101: what a child returns is returned for the head to use, and everything it names is returned too

## The rule (owner's decision, 2026-11-20)

"head cannot read child directly. child has to offer it up and head takes what it takes." And: "either the child intends the head to use the file or not". The rule that follows: WHAT A
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

## What the head's credit does with what is returned

The graded records a child returns (`graded_refs`) are what the head's credit reads, as soon as they are held: the owner's differential credit, additive over tests and subscoring sheets (`a101_differential_credit.md`). The owner's rule, verbatim: "the graders should additively add to the subscoring sheets and then the subscoring sheets additively add to the score". One test is one graded source, `<kind>@<source reference>`. Every episode's credit also supplies `ceiling`; `UNBOUNDED` is used where an action's gain truly has no limit ("UNBOUNDED filled in everywhere is bad; UNBOUNDED where truly unbounded is right").

Run R1 (`runs/a101_returns_run_R1`, resumed as R1d) is described in `a101_conserved_sites.md`.
