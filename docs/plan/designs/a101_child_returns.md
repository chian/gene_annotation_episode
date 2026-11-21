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
- Each episode's `internal_summary` builds its returned lists through it (`final_to_parent` receives only the summary, no
  reader, so the closing runs where the records are read): a BV-BRC child its `handoff_refs`, `check_refs`, `closure_refs`
  and `graded_refs`; `all_vs_all` its `graded_refs` only (below); the head its five lists (`returned_refs`, below).
- The head's summary `named_refs` covers every held reference, job rows included, through the same `named_records`; a
  commission that continues a held job (`msg_to_child._continued`) passes back the rows and, in `input_refs`, every held
  record they name. The head's `outstanding_handoff_count` is the number of held handoff rows whose closure row it does not
  hold (`job_records.outstanding_jobs`); its own profile scan's local job is closed in its unit and is not counted.
- Private names removed at the source: bvbrc_msa no longer stages `plan.json` as a job input (the job's identity is in the
  handoff row's estimates; the extract recomputes the plan from the held search for the grading, and names the group file the
  handoff row staged, below "A parked job's continuation"). Feature group,
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

### The hit metadata and the gradings (2026-11-21)

An independent check of run `runs/a101_goal7_run_cspa_e4721cd11` (workspace `runs/a101_goal7_ws_cspa`) found the head holding 11
labelled products and, unlabelled, two kinds of result the head reads: the BV-BRC hit metadata of the `bvbrc_blast` search (the
artifact of the `bvbrc_data` source, ~100 KB: the feature, family and genome records of the named hits, where the hits' product
names come from) and the 6 retained gradings (the graded sheets of the scan, the BLAST search, the two alignments, the clustering
and MetaCATS). Each is now labelled in the unit that makes it, with two new kinds (`records/data_products.py`, EDAM terms read in
EDAM.tsv on 2026-11-21, neither obsolete, the reasons in the comment beside each):

| Kind | EDAM data, format | Labelled in | `generated_by` | `used` | `derived_from` |
|---|---|---|---|---|---|
| `search_hit_metadata` | data_0896 Protein report (synonym "Gene product annotation"), format_3464 JSON | `bvbrc_blast_search.fetch_and_grade_search` (`record_metadata_product`) | the `bvbrc_data` source | the search report | the `sequence_search_results` row |
| `tool_grading_sheet` | data_2048 Report, format_3464 JSON | `tool_grading_artifacts.record_grading_product`, called beside each `retain_tool_grading` of `fetch_and_grade_search`, `hmmer_profile_scan`, the MSA and MetaCATS `extract`, `all_vs_all_run.commit_clustering` and `pairwise_blast_comparison` | the unit's source over the graded artifact | the artifacts the grader read (BLAST: report and hit metadata; scan: its three texts; MetaCATS: report and alignment) | their product rows |

The settings of a grading are its provider and sheet schema; of the hit metadata, the data service, the fields asked of each
collection, the batch and the settling step of the naming. Each new row goes into the unit's `graded_refs` (the head's own scan:
its `record_refs`), so each child's `returned_with_names` returns it with what it names, and the head's `data_product_refs` (every
held product row) lists it. No credit or grading value changes: the credits read sources, sheets and product kinds that are not
the new ones.

Direct check (not a real run): on a scratchpad copy of `runs/a101_goal7_ws_cspa`, the new labelling functions were run over the
stored hit metadata and the 6 gradings with a store stub that captures the rows they write: 7 rows (1 `search_hit_metadata`, 6
`tool_grading_sheet`), and every reference each row names was already held by the head in that run, so the closing adds only
the rows; the head would list 18 product rows (11 + 7).

## The head's own return is closed under naming (2026-11-21)

An independent check of run `runs/a101_goal8_run_cspa_2a5c36f0e` (workspace `runs/a101_goal8_ws_cspa`) found the head's return not closed
under naming: `committed_record_refs` listed its profile scan's source and three product rows but not the files they name, and
`data_product_refs` listed product rows without their artifacts; 13 held records were in no returned list. The head's `internal_summary`
now builds `returned_refs`, one entry per returned list (`committed_record_refs`, `execution_handoff_refs`, `execution_check_refs`,
`execution_closure_refs`, `data_product_refs`), each through `returned_with_names`, and `final_to_parent` returns the selected entries from
it. The unclosed `committed_record_refs`, `check_refs`, `closure_refs` and `data_product_refs` of the summary are gone; `handoff_refs`
stays as the handoffs shown to the head's model.

Direct check (not a real run): on a scratchpad copy of `runs/a101_goal8_ws_cspa`, the head's `internal_summary` and `final_to_parent` (every
list selected) run over a custody reader of the head's receipts. Before: 957 held, 944 in some returned list, 4 named by a returned record and
not returned (`committed_record_refs` 915 with 4 named outside it; `data_product_refs` 23 with all 23 artifacts named outside it). After:
named-but-not-returned 0 in each list and over their union (`committed_record_refs` 919, `data_product_refs` 46, handoff 18, check 26,
closure 29), 948 in some returned list. The 9 held records in no returned list are named by no returned record: the head's entry hypothesis,
one held artifact that nothing names, and the profile scan's local job (its handoff and closure rows and the five files only those rows
name: the staged query FASTA, the two replies, `result.json` and `stderr.log`; the scan's three graded texts are returned as its labelled
products), which the scan closes inside its unit.

## A parked job's continuation (2026-11-21)

Run `a101_goal11_run_cspa` (commit 3ec36ac4a, workspace `runs/a101_goal11_ws_cspa`) parked a `bvbrc_msa` job (child `bvbrc_msa_3`,
`until launched`), ran `all_vs_all`, then took the owed resume (`bvbrc_msa_5`, `until extracted`). The resume's monitor and its fetch
of `msa.afa` worked; its extract failed with `CustodyError record_not_held:...bvbrc_msa_5...:artifact_a32d5f68...`.

The record: none. `artifact_a32d5f68...` is in no table of the Store and no receipt: it is the reference the extract COMPUTED for
the alignment product's `used` (`feature_group_ref(plan)`, the digest of `group.json` rebuilt from the plan), and `record_product`
refuses a row that names a record the child does not hold. The plan named the references in the commission's candidate order. The
model's launch commission named CspA first; the job's identity (handoff row's `estimates.identity`) keeps the candidates sorted,
and the head's `resume_commission` is built from that identity, so the resume named "Cold shock protein of CSP family" first. Same
job (the head's check compares sorted candidates), different order, different `group.json` bytes, a reference to a file that was
never made. The `group.json` the job was given (`artifact_21441577...`) was held and passed: the parked child returned its handoff
row closed under naming (the staged `group.json` and `sequences.fasta` and the reply), and the resume commission passed all of them
back (`_continued`). Head returns and custody were not the cause.

Fix (`bvbrc_msa_alignment.py`): the plan is a function of the job's identity (`_plan` sorts the candidates), so a launch and any
later commission of the same job plan the same references and the same group file; and the extract names in `used` the group file
the handoff row staged (`detail.input_refs['group.json']`), the job's own fact, not a recomputed reference. Every continuation reads
only what the job's rows name and what the commission passes. The other two: `bvbrc_blast`'s continuation reads the query record and
its sequence artifact (passed with the query) and the rows; nothing it writes names a recomputed input (the real run resumed a
parked BLAST, `bvbrc_blast_2`, to its graded result). `bvbrc_metacats`'s job identity is the staged group file itself, the resume
selects the held alignment whose group file has that reference, and its extract's `used` is that same reference; the alignment and
its sheet come with the alignment's source, the derived alignment and group file with the handoff row.

Direct check (not a real run; `runs/a101_msa_resume_check_2`, script in the session scratchpad): on a copy of `runs/a101_goal11_ws_cspa`,
the head's `internal_summary` over a reader of its receipts, `resume_action` and `msg_to_child` give the resume commission the run
made (record fields equal, 9 records), and its custody holds the handoff row, the staged `group.json` and `sequences.fasta` and the
reply; no record a passed row names is left out. The child's extract run again over the child's real `Custody` and `ScopedStore`
(the fetch takes over the closure the crashed attempt wrote; a stub route raises if touched, none was): the old reference
`artifact_a32d5f68...` is not held; with the fix the extract completes (64 sequences, 70 columns, 4 candidates) and the product's
`used` is the target's sequence, the search source and `artifact_21441577...`. On a copy of `runs/a101_goal7_ws_reca` (a BLAST parked
and never resumed) the owed resume is `bvbrc_blast` `until extracted`; its custody (4 records) holds the handoff row, the staged
`query.fasta` and the reply, nothing missing. Import of the head's subtree: 5 bindings.

## What the head's credit does with what is returned

The graded records a child returns (`graded_refs`) are what the head's credit reads, as soon as they are held: the owner's differential credit, additive over tests and subscoring sheets (`a101_differential_credit.md`). The owner's rule, verbatim: "the graders should additively add to the subscoring sheets and then the subscoring sheets additively add to the score". One test is one graded source, `<kind>@<source reference>`. Every episode's credit also supplies `ceiling`; `UNBOUNDED` is used where an action's gain truly has no limit ("UNBOUNDED filled in everywhere is bad; UNBOUNDED where truly unbounded is right").

Run R1 (`runs/a101_returns_run_R1`, resumed as R1d) is described in `a101_conserved_sites.md`.
