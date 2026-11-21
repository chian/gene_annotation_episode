# A101 head: reads of what the BV-BRC children return (audit)

Read-only audit of the working tree (other agents were editing `bvbrc_msa_alignment.py`, `bvbrc_blast_search.py`,
`bvbrc_hit_metadata.py`, `candidate_measurements.py` at the time). Rule: the head reads a child's job or result only from
job ledger rows (detail, estimates) or records the child RETURNED; never from an artifact or record that a row or returned
record only NAMES. Lead's rule for the children: what a child returns, it returns for the head to use; everything the
returned records name must itself be returned or already held by the head; anything private is never named.

Holding is exact: a record is held only if passed in, returned, or produced by the unit; holding a record or row does not
hold what it names (`store_scope.FOLLOWED`, `work_tables.py`).

## Returned lists today (all three children, and BLAST)

All four slots: `REQUIRED_RETURN = execution_handoff_refs, check_refs, closure_refs, graded_refs` (`msg_to_child.py`); the
head reads them through `read_from_child.RETURNED`. Graded lists (extract functions):

| child | graded_refs |
|---|---|
| bvbrc_blast | source, grading artifact, search row, metadata source, reference records, observations |
| bvbrc_msa | source, grading artifact, alignment data-product row, reference records, observations |
| bvbrc_metacats | source, grading artifact, report data-product row, reference records, observations |

## Head-side reads that open or follow something by a reference taken from a field

| # | file:line | what it reads | held by head? | verdict / smallest fix |
|---|---|---|---|---|
| 1 | `bvbrc_job_child.py` `held_jobs` -> msa `describe_identity` (old, commit before 2ae2578ea) | `get_artifact(handoff input_refs['plan.json'])` | NO (reproduced: `CustodyError record_not_held ...artifact_e5ab1ed9...`) | violation, fixed by 2ae2578ea (row estimates `identity`) |
| 2 | `bvbrc_msa_alignment.py` `describe_identity` (now) | `handoff['detail']['estimates']['identity']` | row only | OK. Rows written before the fix raise `KeyError 'identity'` (M2 rows reproduce it; expected) |
| 3 | `bvbrc_metacats_search.py` `describe_identity` | `estimates['request']['p_value']` and the NAME `input_refs['group.tsv']` (string, never opened) | row only | OK (no read). It uses a named artifact reference as the job identity, compared with `group_artifact_ref` (sha of the group file text computed from the sheet); works while that digest equals the staged artifact's ref |
| 4 | `bvbrc_blast_search.py:141-163` `held_searches` | `handoff['detail']['input_refs'][QUERY_FILE]` compared with the head's held `sequence_ref` strings | strings only; query.fasta is the head's own artifact | OK |
| 5 | `candidate_measurements.py` `_read` via `source_tool_grading_entries` | `store.get` and `get_artifact` of each held source's `auxiliary_artifact_refs` (grading artifact) | YES, grading artifact is in every child's graded_refs | OK |
| 6 | `candidate_measurements._pairwise` | `reader.get(source['operand_refs'][1])` | pairwise sources are the head's own | OK |
| 7 | `candidate_measurements._read` | `subject_length(target)`, `_regions` | target is the head's own | OK |
| 8 | `bvbrc_msa_alignment.msa_options`, `graded_rows`; `bvbrc_metacats_search.graded_rows` | grading artifact of held sources | yes (graded_refs) | OK |
| 9 | `bvbrc_metacats_search.plan` / `alignment_source` / `held_alignments` / `reusable_report` / `check_commission` | data-product row (held), source whose `artifact_ref` equals the row's `artifact_ref` (string compare), the source's grading artifact | row, source, grading all returned | OK; the alignment artifact itself is deliberately not opened in the head. Verified on M2 state: `held_alignments` returns the alignment |
| 10 | `native_correspondence.read_details` (head `internal_summary`) | held observations, their sources, gradings, `subject_refs` | observations, sources, gradings returned | OK (MSA/MetaCATS gradings are skipped as unsupported schema, not an error) |
| 11 | `internal_summary.py:121` `held_sequences` | `records.get(ref).get('sequence_ref')` for input/reference/product | reference records of all three children carry `sequence_ref None`, so excluded; no artifact is opened | OK (M1 fix) |
| 12 | `internal_summary.py` `data_products`, `reusable_alignments` | row fields `locations`, `settings`, `used[1]` | row only | OK; `used[1]` is the search source: relies on the order `[sequence_ref, search, feature_group_ref]` |
| 13 | `internal_summary._named` -> `records.named_references` | held records only; names filtered with `records.holds` | n/a | OK |
| 14 | `internal_summary._held_comparisons` | `get_artifact(source['auxiliary_artifact_refs'][0])` for pairwise sources | the head's own units | OK |
| 15 | `msg_to_child._bvbrc_metacats` / `_custody` | the commission passes the alignment ROW, the msa source, its named records that the head holds. The alignment artifact (`msa.afa`, the row's `artifact_ref` and the source's `artifact_ref`) is not held by the head | NOT HELD | will fail the metacats commission or the child: the child's `alignment_rows` does `get_artifact(planned['alignment_artifact'])`. Not a head read; no run reached it (C1 and C2 never ran the metacats child). Fix: bvbrc_msa returns the alignment artifact (`result_ref`) in `graded_refs`, then `_custody` passes it through the source's named refs |
| 16 | `bvbrc_msa_alignment.reusable_alignment` (working tree) | `_plan(reader, ...)`: `search_rows` reads search source, its grading and the target length | runs in the child on what the head passed (`_custody([query, search])` gives source, grading, target sequence) | OK if the commission passes them; not a head read |

No other head-side read of `input_refs`, `plan` files, report files, `locations`, `used` or `derived_from` was found. `locations`
is only copied into the summary. The head never reads `closure` row `results` or `reply_ref`.

## Reproduction (not a real run)

Copies of `runs/a101_msa_ws_M2` made under `runs/audit_head_reads/`, journal receipts restored to the crash state (the msa
return held: 672 refs; the runner drops those on recovery), run through the launcher with no network. The head readers run
one by one:

- held_searches (database, bvbrc), named_refs, read_details, held_candidate_table, msa_options, held_alignments, msa
  graded_rows, metacats graded_rows, reasoning_view, products: all OK.
- `held_jobs(msa)` with the current `describe_identity`: `KeyError 'identity'` (rows written before the fix).
- The old read `get_artifact(plan.json)`: `CustodyError record_not_held ...artifact_e5ab1ed9...` (the M2 error).
- metacats_ws_C1 was not probed (the lane stayed busy); its msa step is the same shape as M2.

So 2ae2578ea covers the plan.json read completely for rows written after it (the identity is in the row and nothing else is
opened); the one further crash found is #15 (child side, after the head commissions metacats).

## What each child's returned records NAME, and whether the head holds it (measured on M2)

| child | returned record | names | held by head |
|---|---|---|---|
| bvbrc_blast | handoff, check and closure rows (`job_ledger`) | `source_ref` and result/reply artifacts (4 distinct artifacts: staged `query.fasta` is held; the replies and the report are not) | NOT held: reply artifacts, the BLAST report artifact |
| bvbrc_blast | source `bvbrc_homology` | `artifact_ref` = the report JSON | NOT held (grading artifact and the query are held) |
| bvbrc_blast | metadata source `bvbrc_data` | `artifact_ref` = the metadata JSON | NOT held |
| bvbrc_blast | observation | one artifact (`b608ea3`, the report) | NOT held |
| bvbrc_msa | handoff row | `input_refs`: `sequences.fasta` (and `group.json` / `plan.json` in the working tree and older rows) and `source_ref` reply artifact | NOT held |
| bvbrc_msa | check row | `source_ref` reply artifact | NOT held |
| bvbrc_msa | closure row | `result_refs` and `results[msa.afa]` = the alignment artifact, `source_ref` reply artifact | NOT held |
| bvbrc_msa | alignment data-product row | `artifact_ref` (msa.afa); `derived_from` = the `protein_sequences` product row (written by `after_launch` in old rows, not returned); `used` = target sequence (held), search source (held), feature group artifact | msa.afa NOT held; protein_sequences row NOT held |
| bvbrc_msa | source `bvbrc_msa` | `artifact_ref` = msa.afa; grading artifact (returned); operand target (held) | msa.afa NOT held |
| bvbrc_msa | reference records, observations | source, subjects, reference records (all returned or held) | held |
| bvbrc_metacats | rows, source, product row | not measured (the child never ran); by code: handoff `input_refs` (alignment file and `group.tsv`, both produced in the child), `artifact_ref` of the report, `used` = group file artifact, `derived_from` = alignment row (held) | group file, alignment copy and report artifacts would NOT be held |

By the lead's rule each NOT held item above must either be returned (if the head is meant to use it) or not named in what is
returned. Items the head does use or must pass on: the alignment artifact `msa.afa` (MetaCATS needs it; see #15). The rest
(reply artifacts, staged inputs, plan, group file, metadata JSON, BLAST report) are private to their child today and are
named by returned rows and sources; the head uses none of them (it uses only the rows' `detail`/`estimates`).

## Smallest fixes

1. msa: return the alignment artifact (`result_ref`) in `graded_refs`; or have MetaCATS be given it another way (#15).
2. For each other private artifact: the rule says either return it or stop naming it. Rows and sources are written by
   `job_access` and `store.put`, so the names cannot be removed from them; the practical reading is that the head never
   opens them and only the heads' own reads (the table above) must stay inside what is returned.
3. Never add a head read of `input_refs`, plan or report files. Anything the head needs about the job goes into the handoff
   row's `estimates` at launch (as the msa `identity` does).
