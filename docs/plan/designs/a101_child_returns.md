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
- Each child's `internal_summary` builds its returned lists through it (the child's `final_to_parent` receives only the
  summary, no reader, so the closing runs where the records are read): a BV-BRC child its `handoff_refs`, `check_refs`,
  `closure_refs` and `graded_refs`; `all_vs_all` its `graded_refs` only (below).
- The head's summary `named_refs` covers every held reference, job rows included, through the same `named_records`; a
  commission that continues a held job (`msg_to_child._continued`) passes back the rows and, in `input_refs`, every held
  record they name. The head's `outstanding_handoff_count` is the number of held handoff rows whose closure row it does not
  hold (`job_records.outstanding_jobs`); its own profile scan's local job is closed in its unit and is not counted.
- Private names removed at the source: bvbrc_msa no longer stages `plan.json` as a job input (the job's identity is in the
  handoff row's estimates; the extract recomputes the plan from the held search, which is deterministic). Feature group,
  target FASTA, MetaCATS derived alignment and group TSV are named by the BV-BRC handoff rows, which the head reads, and
  are returned. BLAST: query FASTA is the head's own; report, metadata JSON and replies are returned.
- `reusable_alignments` is order-independent (keyed over every element of `used`).
- C3's `TypeError: Strings must be encoded before hashing` in the MSA launch: `feature_group_bytes` returned text
  (`canonical` returns `str`) and `feature_group_ref` hashed it; it now returns bytes.
- Point fixes kept: the job identity in the handoff row's estimates (the row's own fact); `sequence_ref` None on references;
  `held_searches` matches the query among `input_` records; MetaCATS's head-side `plan` reads the sheet and not the
  alignment (harmless, equivalent; not rewritten without a run to verify).

## Every result the head holds is a labelled data product (2026-11-21)

Goal criterion: "every result held is a labelled data product". An independent check of run `runs/a101_goal5_run_cspa_c60596441`
(workspace `runs/a101_goal5_ws_cspa`) found the head holding 25 labelled products and also the job-output files that the
children's job ledger rows name, pulled in by the closing rule because the children returned those rows. Each kind of file was
decided from what the head's code reads (`messages/internal_summary.py`, `final_to_parent.py`, `msg_to_child.py`, `task.py`,
`credit.py`, `candidate_measurements.py`):

| File (count in that run) | Who named it to the head | Route |
|---|---|---|
| `db/prepared.p*` (~36), `receipt.json` (4), `build.stdout`, `info.stdout` (4 each), `plan.json` of the preparation | `all_vs_all` closure rows and the `prepared_data` row in `graded_refs` | Not needed: the head reads none of `all_vs_all`'s job rows and not the prepared-data row; the database is already the `blast_protein_database` product (one TAR). |
| `graph.tsv` (4), `graph.abc` (8), `plan.json`, `driver.py`, `result.json` and `stderr.log` of the `all_vs_all` jobs | `all_vs_all` handoff and closure rows | Not needed: the jobs are waited for and closed inside the child's units; the head only excluded them from its handoff count. |
| `group-mcTable.tsv` (1) | the MetaCATS closure row | Not needed by anyone: the extract grades the chi-square table only, so it now fetches only that file. |
| `hmmscan.tblout`, hmmscan's standard output (the report) | the head's own scan (source's auxiliary artifacts) | Used: the scan grades both. Labelled as `profile_scan_sequence_hits` (EDAM data_0858, format_2330) and `profile_scan_report` (data_0858, format_1421), terms read in EDAM.tsv on 2026-11-21. |

What changed: `all_vs_all` returns `graded_refs` only (its labelled products and the committed clustering's source and grading;
the head's `REQUIRED_RETURN` asks for nothing else and the child no longer declares handoff or closure fields); its
`prepare_database` keeps the prepared-data row in the unit's records and out of `graded_refs`; the MetaCATS extract fetches
`group-chisqTable.tsv` only; `hmmer_profile_scan` labels all three graded texts. Every returned list is still closed by
`returned_with_names`.

Direct check (not a real run): on a scratchpad copy of `runs/a101_goal5_ws_cspa`, the children's returns were recomputed under
the new code and the head's `internal_summary`, `credit` and `final_to_parent` were run over a custody reader limited to the
recomputed holding: no `record_not_held`, credit 14.128848 (equal to the run's), `outstanding_handoff_count` 0 (the old code
gave 1), 975 records held (was 1132), 62 artifacts of which 27 are labelled products. None of the listed job outputs of the
children remains. Still held and not labelled: the reply artifacts of the BV-BRC job rows (the route's replies: 12) and the
inputs those handoff rows stage (query FASTA, feature group, target FASTA, derived alignment, group TSV), which the head holds
because it reads the BV-BRC rows (a parked job is resumed by passing them back); and, of the head's own profile scan, the local
route's `result.json` and `stderr.log`, the staged query FASTA and the two replies: the system's `job_access.run` fetches every
file of a job it waits for, so a unit that waits for a local job holds them. Removing those needs a system change (a `names`
argument of `job_access.run`) or the BV-BRC rows replaced by controlled facts, which would change how a parked job is resumed.

## What the head's credit does with what is returned

The graded records a child returns (`graded_refs`) are what the head's credit reads, as soon as they are held: the owner's differential credit, additive over tests and subscoring sheets (`a101_differential_credit.md`). The owner's rule, verbatim: "the graders should additively add to the subscoring sheets and then the subscoring sheets additively add to the score". One test is one graded source, `<kind>@<source reference>`. Every episode's credit also supplies `ceiling`; `UNBOUNDED` is used where an action's gain truly has no limit ("UNBOUNDED filled in everywhere is bad; UNBOUNDED where truly unbounded is right").

Run R1 (`runs/a101_returns_run_R1`, resumed as R1d) is described in `a101_conserved_sites.md`.
