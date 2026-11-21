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
   0.55 to 0.95 (CspA-like products near 0.9, the CspB/CspG/CspI family lower, near 0.65 to 0.8). The candidate's score becomes the mean of its search value and its MSA value; the differential of a pair of
   candidates is |change of A's score - change of B's score| (nonzero unless both move equally); expected credit gain of the MSA extract unit 0.05 to 0.5. A candidate not chosen is unchanged.
6. The head's later units: reasoning commits until the estimator stops it (as H1: about 10 to 19 units).
