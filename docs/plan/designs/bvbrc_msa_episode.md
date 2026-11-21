# bvbrc_msa: a child episode of the A101 head (multiple sequence alignment through the BV-BRC application service)

Written 2026-11-20/21. Pattern: `bvbrc_blast_episode.md`. HEAD = `gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence`;
LIB = `gene_annotation_episode/episodic_workflow/episode_support`.

Owner: "wire up MSA and MetaCATS children to A101 head. Same pattern as blast_database with bv-brc with the multiple steps (and gate
requiring a time estimate)"; "don't you think you should get the design down ... just once? rather than in 3 parallel places?";
"you need a bv-brc tool to get the record and extract the sequence, yes?"; "MetaCATS needs to have a requirement that it needs an
input MSA, which means we need to start storing and labeling data and data products for reuse".

## What exists, and what is written

| written | the existing function it calls |
|---|---|
| `LIB/tools/.../bvbrc_job_child.py` (`JobApplication`, `output_schema`, `check_estimate/launch/fix/monitor/extract`, `check_resource_and_continuation`, `record_estimate`, `launch_job`, `monitor_job`, `service_seconds`, `episode_state`, `unit_row`, `job_view`, `held_jobs`, `resumed_rows`, `job_notice`, `read_common`, `bounded_credit`, `completion_controller`, `common_instructions`, `common_finding`, `learned`, `ledger_kind`) | generalised from `bvbrc_blast_search`; calls `JobAccess.launch/fetch` (rows in custody), `wait_for_job`, `duration_trend`, `job_records`, `CompletionYieldController`, and from `database_blast_search`: `search_facts`, `timing`, `seconds_until_allowed`, `failure_code`, `now_text`, `seconds_between`, `_failed`, `_ended`, `_choose` |
| `LIB/jobs/bvbrc_job_route.py`: table `APPLICATIONS` (`Homology`, `MSA`), `native_params` | the same transport, `start_app2`, `query_tasks`, Workspace calls, spacing, `prepare_application('Homology')`; `parse_sequences`; for `MSA`, `native_params` checks the parameters against the retained definition `forms/application_service_specs/original/MSA.json` (the global `prepare_application` knows only Homology) |
| `LIB/tools/.../bvbrc_hit_metadata.sequences_by_md5` | `encode_native_query`, `BVBRCDataClient.query_prepared`, `_ask` (batches of 100, 10 s apart): the `feature_sequence` collection (already in the A101 field registry: no registry change) |
| `LIB/grading/.../candidate_measurements.search_hits` (factored out of `_database_search`, same result) and the reading of `msa_alignment_sheet_v1` (`_held_msa`) | `route_native_grading`, `compile_native_sheet`, `_regions` |
| `LIB/grading/.../msa_alignment_sheet.grade_alignment` | `phylogeny_formats.parse_aligned_fasta` (the existing aligned-FASTA reader) |
| `LIB/tools/.../bvbrc_msa_alignment.py` (the binding `APPLICATION`, `plan_rows`, `prepare`, `after_launch`, `extract`, `check_commission`, `msa_options`, `graded_rows`, `reusable_alignment`) | `search_hits`, `sequences_by_md5`, `grade_alignment`, `retain_tool_grading`, `source_tool_grading_entries`, `record_product`, `find_reusable`, `products`, `measurements/number/ref` |
| `HEAD/bvbrc_msa/*` (the files `bvbrc_blast` has), head entries in `task.py`, `messages/msg_to_child.py`, `internal_summary.py`, `final_to_parent.py` | the shared module; `read_from_child.py` unchanged |

`bvbrc_blast` is NOT rebound: its module `bvbrc_blast_search.py` stays, with two one-line edits (its job names its application `Homology`; its
`held_searches` skips handoffs whose ledger kind is not `bvbrc_blast:`), because the route's job now names its application. Its BLAST report is
therefore not yet labelled `sequence_search_results`: the lead does it later.
`LIB/jobs/job_services.py` already carries the registration of `BvbrcJobRoute` inside someone else's uncommitted change; I did not edit it and did not commit it (the route class keeps its name).

## The shared module: how a child binds it

See the top of `bvbrc_job_child.py`. A child makes ONE `JobApplication(application, child, service, provider, product_kind, request_fields, estimate_fields,
field_schemas, size_field, kind, field_problems, prepare, extract, describe_identity, after_launch=None)` and its five files call the module's functions.
`estimates` of the handoff row carries the launch request (`estimates['request']`), so a resumed child and the head's `held_jobs` read the request from the row.

## Verified against the live service (outside a run, the route driven once: `runs/msa_oneoff_1`, task 24004887, MSA submission 1 of 4)

- Documentation: BV-BRC's `p3_msa` service script `App-MSA.pl` (github.com/BV-BRC/p3_msa) reads `fasta_keyboard_input` (written to `fasta_keyboard_input.fasta`),
  `fasta_files` (staged from the workspace), `alphabet` (protein if it begins with `p`) and `aligner` (`muscle`: `muscle -quiet -in input.fasta -fastaout output.afa`), and uploads the
  files by suffix (`.afa`, `.aln`, `.snp.tsv`, `.nwk`, `.html`, ...).
- Live: the application takes the sequences pasted as FASTA (`fasta_keyboard_input` with `input_type` `input_sequence`, `alphabet` `protein`, `aligner` `Muscle`, `output_path`, `output_file`);
  a 4-sequence job (the target and three CspA-family hits fetched by md5 from `feature_sequence`, each md5 checked) was submitted 02:03:58, started 02:03:59, completed 02:04:10 (11 s of service time) and the
  first status request after 65 s showed `completed`. Result folder `<output_path>/.msa/` (the same convention as Homology): `msa.afa` (the aligned FASTA), `msa.aln`, `msa.consensus.fasta`,
  `msa.entropy.svg`, `msa.nexus`, `msa.phy`, `msa.pir`, `msa.snp.tsv`, `muscle.job.log`. The `.afa` rows carry exactly the names given (`target`, `r1`...) but are NOT in the input order
  (the check reads rows by name). Not verified: `fasta_files` (an uploaded workspace file) as the input form (pasted FASTA is used), other aligners, DNA.
- `feature_sequence` by `md5` (public Data API, no login): returned the sequence for each of three md5s asked, each sequence's MD5 equal to its key (`runs/msa_seqcheck_*`).

## Records: what a later child is passed to find the alignment

The alignment is a row of the work table `data_products` (`records/data_products.py`; EDAM data_0863 / format_1984): columns `artifact_ref` (the local copy of `msa.afa`),
`kind` `multiple_sequence_alignment`, `generated_by` (the job's handoff row), `used` (`[the target's sequence artifact, the graded search's source record]`),
`derived_from` (the `protein_sequences` product row of the same job), `settings` (`{application: MSA, aligner: muscle, alphabet: protein, candidates: [sorted names], per_candidate: n}`),
`locations` (`[{service: bvbrc_workspace, path: <the path of msa.afa in the BV-BRC workspace>}]`) and `reuse_key`. The row's reference is in the child's `graded_refs` (and the head's `data_product_refs`);
the MetaCATS child reads the workspace path from `locations` and the local copy from `artifact_ref`. Deviations from the lead's wording: `settings` also holds the candidates and `per_candidate`
(otherwise two different alignments of the same search would have one reuse key), and `used` is the target's sequence artifact and the search source (the hit sequences are fetched only inside the launch, so
the reuse key must not depend on them; the hit sequences are `derived_from`, as the `protein_sequences` product).
The graded source (provider `bvbrc_msa`, artifact = the alignment, `operand_refs` = [target]) carries the sheet `msa_alignment_sheet_v1` and is what the head's credit reads.

## Run M1: prediction (written before the run)

Target CspA (P0A9X9, 70 residues), workspace `runs/a101_msa_ws_M1`, run `runs/a101_msa_run_M1`, local and BV-BRC resources, Pfam configured, global ledger, accumulation cutoff 0.1 (as H1).

1. The model's first choices (as in H1): `hmmer_profile_scan` and `bvbrc_blast` (until extracted or launched). One `Homology` submission (the only one allowed).
2. After the search the head holds five product candidates (scores near 0.959, 0.821, 0.811, 0.808, 0.805; they depend on the live search) and `bvbrc_msa` is offered. Prediction: the model commissions it
   (probability about 0.6; its description says what the test does), with 2 to 4 candidates, `per_candidate` 3 to 10, `until` extracted.
3. The child: `estimate` (no earlier measurement of this kind in the ledger: basis `no_earlier_measurement`, the model's number 30 to 120 s; the one-off check took 11 s of service time, which is not in the ledger),
   `launch`, `monitor` (wait at least 60 s: first status `finished`), `extract`: 4 units, credit 4.0 = target, stop at the extract. The ledger gets one row of kind `bvbrc_msa:bvbrc_msa:MSA:muscle:protein`
   with job facts `{service, application, sequences, residues, longest}` and a measured duration (service's own) of 10 to 30 s.
4. The alignment: sequences = 1 + (candidates x per_candidate, fewer where a candidate has fewer distinct sequences); columns 70 to 75; the target's own row present.
5. The credit: the MSA test is the second test of the product candidates that took part. Each took part candidate's value is the mean over its references of identical columns / 70, which I expect
   0.55 to 0.95 (CspA-like products near 0.9, the CspB/CspG/CspI family lower, near 0.65 to 0.8). the differential of a pair of
   candidates is |change of A's score - change of B's score| (nonzero unless both move equally); expected credit gain of the MSA extract unit 0.05 to 0.5. A candidate not chosen is unchanged.
6. The head's later units: reasoning commits until the estimator stops it (as H1: about 10 to 19 units).

## Run M1: observed (`runs/a101_msa_run_M1d`, workspace `runs/a101_msa_ws_M1`, journal `journal_M1.sqlite3`, report `report_M1.json`, run id `a101_msa_M1b`; the run FAILED in the head after the MSA child returned)

(Earlier launches of the same command failed at link time before any model call or submission: `continuation_settings_required:...bvbrc_metacats` (the other agent's folder), a wrong services directory (stopped by me) and a claimed run id.)

Actions of the head's model, in order, with the head's credit after each: (1) `hmmer_profile_scan` pfam_a: 0.8198; (2) child `bvbrc_blast` (blastp, bacteria-archaea, until extracted): 5.0243 (the same as run H1: 4.2045 + 0.8198); (3) child `bvbrc_msa` with four candidates (the CspA product, the CspB/CspG/CspI product, the CspC product, "Cold shock protein of CSP family"), `per_candidate` 10: the child ran its four units (estimate 120 s `no_earlier_measurement`, launch, monitor with wait 120 s: finished, extract) and closed with credit 4.0 = target, `yield_stop` at the extract, no wind-down. Then the head raised `CustodyError record_not_held: artifact_974f...` while building its summary: DEFECT (below). The head's credit after the MSA unit was not obtained.

Submissions: `Homology` 1 (job_f089...), `MSA` 1 in this run (job_88af..., 41 sequences, 2870 residues, longest 70) + 1 outside run = 2 of 4 MSA. Ledger row (kind `bvbrc_msa:bvbrc_msa:MSA:muscle:protein`, key job_88af...): expected 120 s (basis `no_earlier_measurement`), job facts `{service: bvbrc_msa, application: MSA, sequences: 41, residues: 2870, longest: 70}`, measured duration 15.0 s (`service_task_record`), observed 128.3 s, outcome finished.
Alignment: 41 sequences, 70 columns, the target's row 0; 10 references per candidate.

Data product row (the alignment; `state.sqlite3`, table `episode_work_rows`, work table `data_products`): `kind` multiple_sequence_alignment, `edam_data` http://edamontology.org/data_0863, `edam_format` http://edamontology.org/format_1984, `generated_by` row_e184... (the handoff), `used` [target sequence artifact, search source_c135...], `derived_from` [row_48c6... (the protein_sequences product)], `settings` {aligner muscle, alphabet protein, application MSA, candidates [4 names], per_candidate 10}, `locations` [{service bvbrc_workspace, path /<user>/home/gene_annotation_episode_a101/job_88af.../.msa/msa.afa}], `reuse_key` 04d4e3c1....

Values of the MSA test (the sheet, read directly from the grading artifact; mean over 10 references of identical columns / 70): CspA product 0.9814 (0.957 to 1.0), CspB/CspG/CspI 0.8486 (0.814 to 0.886), CspC 0.7557 (0.714 to 0.771), "Cold shock protein of CSP family" 0.8086 (0.771 to 0.900).

Against the prediction: chain as predicted (scan, search, MSA commissioned with 4 candidates, per_candidate 10, estimate basis `no_earlier_measurement`, 4 child units, credit 4.0); the estimate was 120 s (predicted 30 to 120) and the measured duration 15 s (predicted 10 to 30); the alignment had 41 sequences / 70 columns (predicted 70 to 75 columns: it is 70, the target's length); values 0.76 to 0.98 (predicted 0.55 to 0.95); the credit gain was predicted 0.05 to 0.5 and is, by hand, about 0.13. Not observed: the head's units after the child.

### Defect and fix

The MSA extract kept each reference with `sequence_ref` = the hit's sequence artifact. The head holds the reference records (returned in `graded_refs`) but not those artifacts (the child's launch kept them; they were not returned), so the head's summary read an artifact it does not hold (`CustodyError`). In the same summary `bvbrc_blast_search.held_searches` also failed ("too many values to unpack"): a CspA hit has the same sequence as the target, so two held sequence records had the same artifact (this was the first error, `ValueError`, in the run's failure line; the CustodyError came on the attempted resume). Fixes: the reference records of the alignment carry `sequence_ref` null (like the BLAST references; the sequences stay as artifacts of the launch and in `plan.json`), and `held_searches` matches the handoff's query among `input_` records only. A resume with the fix was tried (`runs/a101_msa_run_M1r`): it fails with the same custody error because the stored references already carry the artifact. The fixed path was NOT verified in a real run: a second run would need a second `Homology` submission (one allowed). So the head's credit and differential after an MSA unit, the head's return, `data_product_refs` selected, and the resume of a parked alignment are not verified.

## Run M2: prediction (written before the run; a FRESH workspace `runs/a101_msa_ws_M2`, run `runs/a101_msa_run_M2`, run id `a101_msa_M2`; same target CspA, same settings as M1; one more Homology and one more MSA submission)

Answer from the code first: no head path reads a `sequence_ref` the head may not hold. `internal_summary.held_sequences` keeps only records whose `sequence_ref` is set, so the alignment's and the BLAST's reference records (now `sequence_ref` null) are not held sequences and the pairwise tool and `held_searches` do not see them; the only artifact reads of sequences are of `input_` records (the target) and, in the child, of the target.

Prediction (the model may choose differently; not steered): scan, `bvbrc_blast`, then `bvbrc_msa` with 2 to 4 candidates and `per_candidate` 5 to 10. The head summarises after the MSA child with no custody error. Its credit after the MSA unit rises by the sum of the differentials, expected 0.05 to 0.3 (M1 by hand: 0.127 with four candidates at 10 each), equal to my hand arithmetic from the sheet and the search scores to within 0.001. The ledger gets a BLAST row (expected learned from earlier searches, measured about 60 to 120 s from the task record) and an MSA row (basis now `learned_from_earlier_jobs`, one measured job of 15 s; measured 10 to 30 s). The head's return carries `candidates` with the changed scores and `data_product_refs` with the `protein_sequences` and `multiple_sequence_alignment` rows.

## Run M2: observed (`runs/a101_msa_run_M2`, fresh workspace `runs/a101_msa_ws_M2`, run id `a101_msa_M2`; FAILED again in the head after the MSA child returned)

The chain went as in M1 (scan, `bvbrc_blast`, `bvbrc_msa`): the BLAST child and the MSA child both completed their units; the MSA job (job_76ba..., 21 sequences, 1470 residues) finished. Ledger rows (read from `resources/estimate_ledger.sqlite3`): BLAST `bvbrc_blast:bvbrc_homology:bacteria-archaea:blastp`: expected 75.23 s (`learned_from_earlier_searches`), measured 28.0 s (service task record), observed 81.05 s, finished; MSA `bvbrc_msa:bvbrc_msa:MSA:muscle:protein`: expected 14.5 s (`learned_from_earlier_jobs`; the model used the one measured job), measured 14.0 s, observed 23.09 s, finished, job facts {sequences 21, residues 1470, longest 70}.
The head then failed again with `CustodyError record_not_held: artifact_e5ab...`. That artifact is the job's `plan.json` (8248 bytes, application/json, produced by the MSA child): `held_jobs` read the job's identity through `describe_identity`, which opened the plan artifact named by the handoff row's `input_refs`; the head holds the row (returned) but not the artifact. So the M1 fix (references without `sequence_ref`) was necessary but not sufficient, and M1's second failure was this same read. The head's credit after the MSA unit, the differential it computes, its return with `data_product_refs` were NOT obtained. Submissions: Homology 2 of 2, MSA 3 of 4 (the lead's limit for this step reached).
Fix (committed, NOT verified in a real run): `prepare` returns the job's identity, `launch_job` keeps it in the handoff row's `estimates`, and `describe_identity` of the MSA binding reads only the row. Open: a resumed MSA child (a parked job continued by a later commission) reads `plan.json` through the handoff's `input_refs` in `extract` and `internal_summary` has nothing passing that artifact back: not verified and probably needs the plan artifact returned to the parent and passed back.
Code answer, re-checked: no head path reads a `sequence_ref` the head may not hold (`held_sequences` keeps records with a set `sequence_ref`; references of the BLAST and now of the MSA have none); the defect was a different kind: an artifact named by a returned ROW (`input_refs` of the handoff).

## Owner's follow-ons (after run M2)

### (1) How many hits to name (`bvbrc_hit_metadata.name_hits`, called by the BLAST extract)
Rule (deterministic, no model choice): hits ordered by the per-hit value the head's credit reads (`candidate_measurements.search_hits`; highest first, ties by accession); named in batches of 100 (the existing feature, family and genome lookups of a batch); after each batch the candidate list and scores of the hits named so far are computed with `differential_credit`; stop when a batch, against the picture before it, admits no new product and moves no candidate's score by more than 0.01 (`settled`), or when all hits are named (`all_named`). The first batch has no picture before it, so a second batch is always asked when hits remain. Hits not named are NOT ASKED (`not_asked_hit_count`), the metadata artifact of the sheet (`naming`) and the child's finding (`named_hit_count`, `not_asked_hit_count`, `naming_batch_count`, `naming_stopped`) say it. Two defects found by the direct call, fixed: `search_hits` met hits whose association has no metadata index.
Effect, by a direct call on the stored reports (NOT a real run; Data API lookups only, no submission; `runs/msa_naming_direct_2`): D1 (CspA, `runs/bvbrc_a101_run_D1`): 300 hits, 2 batches, 200 named, 100 not asked, `settled`, 6 requests; C1 (RecA, `runs/bvbrc_a101_run_C1`): 300 hits, 2 batches, 200 named, 100 not asked, `settled`. The lead expected one batch for C1; the rule as written needs two (the first batch is compared with nothing). If one batch is wanted when the first batch holds a single product, the rule needs a stated exception. The extract with the new naming was NOT run in a real run.

### (2) MSA from a feature group
Live check (a one-off through the route, `runs/msa_group_oneoff_1`, task 24004894; MSA submission 4 of 4, the last): the route created the folder and the feature group object `<job folder>/hits` with `Workspace.create` (`[path, 'feature_group', {}, {'id_list': {'feature_id': [ids]}}]`; ids are the hits' `feature_id` field, not `patric_id`) and started `MSA` with `input_type` `input_group`, `feature_groups` [that path] AND `fasta_keyboard_input` (the target) together: ACCEPTED. 4 sequences (3 group members + the target), completed in 17 s. BV-BRC read the members' sequences itself and named the rows `fig|<patric id>` (the target `target`). The grading, by a direct call on that alignment (labelled not a real run), checks each row, gaps removed, against the hit's `aa_sequence_md5` (all three matched) and gives the sheet (values 0.9, 0.986, 1.0).
Changes: the route's MSA job takes an optional `feature_group_file` (`group.json`); `submit` creates the group object; `bvbrc_msa_alignment.prepare` puts the hits in `group.json` and the target in `sequences.fasta`, no fetch; `grade_alignment` takes rows with an md5 instead of a sequence; the reference names are `fig|<accession>`; no `protein_sequences` product is made any more (nothing is fetched); the alignment product's `used` is [target sequence artifact, search source, the group's artifact (content-addressed, so it is known before the launch for the reuse key)]; the group's workspace path is `<folder of the alignment's path>/hits`, kept in the route's request record, not in a column. `sequences_by_md5` stays in the library; the MSA grading does NOT need the sequences. NOT verified in a real run through the head (no submission left): only the one-off and the direct grading call.
