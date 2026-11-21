# A102 `structure_search`: the library under it (job route, model sources, data products)

Status: library built and checked directly on 2026-11-21 (not a real run). Design: `a102_tree.md`; services: `a102_services.md`;
inventory: `a102_inventory.md`. LIB = `gene_annotation_episode/episodic_workflow/episode_support`.

## Step zero: what exists and is called, what is new and why

| Need | What exists and is called | What is new, and why the existing one could not be used as is |
|---|---|---|
| A job route for a ticketed web service | `episode_runtime/job_access.py` (route protocol, `RouteRequestError`); `LIB/jobs/api_job_route.ApiJobRoute` (job directory, one submission per handle, provider spacing in `rate.json`, `wait`, `cancel` that fails with `cancel_not_offered_by_the_service`, atomic records, `_refusal`, `_entity`); the pattern of `bvbrc_job_route.BvbrcJobRoute` (subclass that replaces `submit`, `status`, `results`, `read`) | `LIB/jobs/foldseek_job_route.FoldseekJobRoute` (kind `foldseek`). `ApiJobRoute`'s protocol object sends urlencoded forms with a `tool` field and fixed `GET` queries; Foldseek takes a multipart file upload and path-addressed GETs, so (as BV-BRC does) the route replaces the four members and keeps everything else of the base. |
| Binding the route to a run | `LIB/jobs/job_services.py` (`bvbrc` block) | one more optional block `foldseek` (same keys as `bvbrc`, minus `authorization_env` and `root_folder`: no login, no folder at the service) |
| The service's definition retained | `LIB/forms/application_service_specs/original/` (BV-BRC's own app specs; `native_params` checks a request against one) | `original/StructureSearch.json` (the definition as verified: requests, parameters, enums, ticket states) and `original/StructureSearch_server_api_docs.html` (the server's documentation page, https://search.mmseqs.com/docs/, read 2026-11-21, sha256 `d92fc436...c00a2`). The service publishes no machine-readable spec (`/api/openapi.json` is 404), so the retained definition is written from its documentation page plus the live checks and says which values are documented and which verified. |
| The ledger's duration | `bvbrc_job_child.monitor_job` writes `observed_seconds` and `duration_seconds`, and uses the service's task record when the status reply has `submit_time` and `completed_time` | nothing new in the ledger writer. The Foldseek status reply has no such fields, so the writer records `duration_source: first_status_showing_the_end` (see below). |
| Outside HTTP inside a unit | A101: `bvbrc_hit_metadata` / `sequences_by_md5` use a plain `urllib` client (`BVBRCDataClient`), no redirect followed, a socket timeout, `time.sleep(spacing)` before a request; the unit's returned values are what the receipt keeps | `target_model_sources._request`: the same shape (one `urllib` request, `_NoRedirect`, timeout, spacing). `PublicClients` (old A102 acquisition) was not used: it builds a `SourceSnapshot` for the old registry host and sends the User-Agent `gene-annotation-episode/0.2` (AlphaFold DB refuses non-browser agents), with no way to set another. |
| AlphaFold DB URL and file check | `alphafold_acquisition.alphafold_prediction_url`, `_advertised_file_url` (https, host `alphafold.ebi.ac.uk`, path `/files/<name>.pdb`) | called as they are. Their schema/receipt functions (`resolve_alphafold_file_selection` and the rest) need a `source_ref` and a metadata artifact of the old registry; not called. |
| CRC64, UniProt lookup by sequence | none (`PublicClients.uniprot_search` goes through an installed skill client) | `uniprot_crc64`, `uniprot_accessions_by_sequence` |
| PDB confidence | `readers/protein_structure/protein_structure_metadata.py` reads pLDDT only under a declared semantics inside the old store flow | `pdb_ca_confidence`: the C-alpha B-factors of the two models, as the declaration "B-factor is pLDDT" is the stated fact of both services (below) |
| Data products | `records/data_products.KINDS` | two kinds added: `protein_structure_model`, `structure_search_results` (EDAM below) |

## What was built

`LIB/jobs/foldseek_job_route.py`

- `FoldseekJobRoute(configuration, *, resource_id)`; configuration keys (exact, no defaults): `service` (`foldseek`),
  `endpoints` (`{'Foldseek': 'https://search.foldseek.com'}`), `workspace`, `request_spacing_seconds`, `poll_spacing_seconds`,
  `transport_timeout_seconds`. A services file binds it as `"foldseek": {"<resource id>": {...}}` beside `bvbrc`.
- Application `StructureSearch`; job `{'application', 'database', 'query_file'}` (`query_file`: the staged PDB text of the
  model; at least one C-alpha atom). `DATABASES = ('afdb-swissprot',)` (a constant; `pdb100` and `cath50` are added in round 2);
  `MODE = 'tmalign'` is fixed and is not a field of the job.
- `submit`: `POST /api/ticket`, multipart: `q` (file `query.pdb`), `database[]`, `mode`. No email, no key. `status`:
  `GET /api/ticket/{id}`; states `PENDING` queued, `RUNNING` running, `COMPLETE` finished, `ERROR` failed, `UNKNOWN` unknown.
  `results` / `read`: `GET /api/result/{id}/0`, one catalog file `result.json` (checked: `type` `structuresearch`, `mode` the job's,
  `queries` one, `results` one database, the job's). `cancel`: the service has none; the inherited `cancel` is the failed request
  `cancel_not_offered_by_the_service`, which is what the route contract does for a service without cancel (as `bvbrc` and `api`).
- Every request carries `target_model_sources.BROWSER_USER_AGENT` (one constant for all A102 requests).

`LIB/acquisition/protein_structure/target_model_sources.py`

- `uniprot_accessions_by_sequence(sequence)` -> `{'status': 'found'|'not_found', 'crc64', 'accessions': [{'accession', 'reviewed',
  'annotation_score'}], 'truncated', 'rows_seen', 'collisions'}`; exact sequence match, reviewed first, then score (high first),
  then accession; no name is ever returned.
- `alphafold_model(accession)` -> `{'status', 'accession', 'entry_id', 'model_version', 'sequence', 'residue_start', 'residue_end',
  'residue_count', 'plddt_mean', 'plddt_reported', 'plddt_per_residue', 'model_url', 'model_bytes'}`; HTTP 404 is
  `{'status': 'not_found', 'accession'}`. Any other HTTP status raises (a 400 is a malformed accession).
- `esmfold_model(sequence)` -> same fields without the entry and version; `ESMFOLD_PLDDT_SCALE = 100.0` converts the service's
  0 to 1 to 0 to 100. A sequence over `ESMFOLD_MAX_LENGTH = 400` raises `ValueError` (the tool's check must not offer it).
- `uniprot_crc64(sequence)`, `pdb_ca_confidence(pdb_bytes)`.

`LIB/records/data_products.py`: two kinds, EDAM.tsv read 2026-11-21 (`runs/a102_edam/EDAM.tsv`), none obsolete.
`protein_structure_model`: data_1460 Protein structure, format_1476 PDB (data_1469 is obsolete; data_0883 Structure is for any
macromolecule). `structure_search_results`: data_0887 Structure alignment report, format_3464 JSON (data_0885 Structure database
search results is obsolete in this release; data_0886 Structure alignment is superimposed coordinates, which the result does not hold).

## The measured duration is observed, not the service's

The BV-BRC route's status reply carries the service's own task record (`submit_time`, `completed_time`), and the ledger writer
(`bvbrc_job_child.monitor_job`) writes `duration_seconds` from it with `duration_source: service_task_record`. The Foldseek ticket
(`{"id", "status"}`, nothing else, checked in `runs/a102_service_probe/foldseek/ticket_*.json` and in the check below) offers no
times at all. The route's status reply therefore has no `submit_time` and `completed_time`; the ledger writer then writes
`observed_seconds` (launch to the first status that showed the end) and `duration_seconds` equal to it, with `duration_source:
first_status_showing_the_end`. These are the existing field names; nothing in the writer changed. The observed figure includes the
wait before the status request and is an upper bound of the search's own time. The server answered `COMPLETE` already in the
reply to the POST in the check below (8.3 s from the POST to the end of the whole check including the wait), so for this service
the observed duration is small and mostly the wait the unit chose.

## What was verified, and how (direct checks, not real runs; scripts in `runs/a102_route_check/`, nothing in the repository)

All through `tools/one_workflow.sh --slot a101`. Live requests: Foldseek tickets 1; AlphaFold DB prediction 4 (P0A9X9, P00000,
X00000 (HTTP 400), A0A0A0A0A1 (HTTP 404)) and file 2; UniProt search 1; ESM Atlas 1; the documentation page 1; EDAM.tsv 1.

1. `check_sources.py` (`run_sources1`): `uniprot_crc64(CspA)` = `CED47F00BF18A49B` (equals `a102_services.md`); RecA gives
   `866EF8F83BE32A36` (equals the services note too). The lookup of the CspA sequence: `found`, 52 rows seen, 0 collisions, not
   truncated, `P0A9X9` first (reviewed, score 5.0), then reviewed entries of score 2.0 (`P0A9Y0`, `P0A9Y1`, ...). `alphafold_model('P0A9X9')`: `AF-P0A9X9-F1`, version 6, residues 1 to 70
   (70), mean pLDDT 88.44 from the file, equal to the service's `globalMetricValue` 88.44, 46,736 bytes (saved as
   `runs/a102_service_probe/afdb/cspa_model.pdb`). `esmfold_model(CspA)`: 70 residues, mean pLDDT 88.54 (0 to 100 after scaling),
   43,701 bytes.
2. `check_route.py` (`run_route3`; `run_route1` stopped at its first line on a 400 and sent nothing to Foldseek): the route has
   all eight members; `describe` answers; three jobs of the wrong form (a database not offered, an extra field, another application)
   are refused with `ValueError` before any request; `submit` of the AlphaFold model of CspA, `afdb-swissprot`, `tmalign`: ticket
   accepted (status `COMPLETE` in the POST reply); a second `submit` of the same handle is `adopted` with the same ticket (nothing
   sent); `results` before the end is `results_not_available`; `wait` then `status`: `finished`, `result_available`; `results`:
   one file `result.json`, 6,820,247 bytes; `read` returns it whole; its content: `type` `structuresearch`, `mode` `tmalign`,
   database `afdb-swissprot`, 976 hits (first hits `AF-P0A9X9-F1` score 100 eval 1.0, `AF-P0A9Y1-F1` 99 / 0.9974, `AF-P0A9Y0-F1`
   99 / 0.9968). Saved as `runs/a102_service_probe/foldseek/result_tmalign_afdb_swissprot_cspa.json`. `cancel` fails with
   `cancel_not_offered_by_the_service`.
3. `check_imports.py` (`run_imports1`): each touched module imports; both new kinds are in `KINDS` with the EDAM terms above;
   `job_services` built with a `foldseek` block gives `JobAccess.resources()` = `[{'resource_id': 'fold', 'kind': 'foldseek'}]`;
   `run_command.subtree('sequence_homology_evidence')` has 5 entries (A101 still links).

## Not verified

- `ESMFOLD_MAX_LENGTH = 400` is UNVERIFIED. The ESM README says only that Foldseek searches the Atlas "without the length limitation",
  so a limit exists; no page reached gives its number. 353 residues (RecA) was folded on 2026-11-21; nothing longer was tried.
- The server's poll spacing and rate limit: none documented. The services file of a run chooses `request_spacing_seconds` and
  `poll_spacing_seconds`; the check used 3 and 5 seconds. The route has not run a job that was `PENDING` or `RUNNING` at the POST
  reply (the one ticket was `COMPLETE` at once), so the `queued` and `running` mappings and `wait` on a running job are from the
  documentation, not seen. `ERROR` was seen once on 2026-11-21 (a FASTA query, `a102_services.md` 3) with the old probe, not through this route.
- The `UNKNOWN` path (a ticket the server does not know) and a non-200 reply to the ticket requests are not exercised.
- `uniprot_accessions_by_sequence` reads one page of 500 rows; `truncated` says when UniProt had more. Whether UniProt returns
  reviewed entries first in every page is observed (CspA), not documented, so a reviewed entry can be missed beyond the first
  page only when `truncated` is true.
- Nothing here was run inside an episode unit: no `JobAccess.launch` (custody, handoff row) with this route; only the route members
  directly.

# The child episode `structure_search`

Status: built and checked directly on 2026-11-21 (direct checks, not a real run: no model was asked). Episode folder
`gene_annotation_episode/episodic_workflow/root/a102/structural_homology_evidence/structure_search/` (binding path
`structural_homology_evidence/structure_search`; `goal.py`, `task.py`, `credit.py`, `yield_estimator.py`, `episode.py`,
`messages/{read_from_parent,internal_summary,final_to_parent}.py`; the class inherits only from `EpisodeBinding`). Library:
`LIB/tools/structure_search/structural_homology_evidence/structure_search_child.py` (the job-child machinery) and
`foldseek_search.py` (the application). The tree and the reasons are `a102_tree.md`; the SOP is Steps 1, 3, 4, 5, 6 and 13.

## Step zero: what is called, what is new

| Need | Called as it is | New, and why |
| --- | --- | --- |
| The job-child machinery (estimate gate with `ledger_estimate`, launch once, fix after a failure, monitor wait range, extract = fetch + grade, until launched / extracted, wait notice, continuation from the handoff's staged inputs, bounded credit, completion controller, closure under naming) | the owner's rules and A101's `bvbrc_job_child.py` as the model to copy | `structure_search_child.py`: A102's own copy (per-axis library convention). A101's module is fixed to resource kind `bvbrc`, its credit has four units and it has no `get_model`; it stays untouched. Differences: resource kind `foldseek`; `get_model` (check `check_get_model`, offered sources `sources_offered`); the credit has a fifth unit (`model_unit`); states `no_model`, `model_held` before `estimated`; `launch` also needs a model (`model_required`); `FIRST_JOB_SECONDS` = 10 (the live check of 2026-11-21 observed 6 to 10 s, `a102_services.md`; the ledger replaces it after the first measured job); `JobApplication.after_launch` is dropped (nothing uses it) |
| The route | `LIB/jobs/foldseek_job_route.FoldseekJobRoute`, `job_services` (`foldseek` block), `JobAccess` | nothing |
| A model of the target | `target_model_sources.uniprot_accessions_by_sequence`, `alphafold_model`, `esmfold_model` | `foldseek_search.obtain_model` (the unit: custody, source record, data product), `model_positions` (the numbering check) |
| Data products | `data_products.record_product`, `find_reusable`, `require_product`, `products`; kinds `protein_structure_model`, `structure_search_results`, `search_hit_metadata`, `tool_grading_sheet` | `tool_grading_artifacts.record_grading_product` in A102's folder (it lacked it; mirror of A101's) |
| The result | `foldseek_result.parse_foldseek_result`, `structure_search_sheet.measure_hits` and `grade_structure_search`, `uniprot_hit_names.name_hits`, `retain_tool_grading` | `foldseek_search.extract` (the unit that calls them in order); the self control in the sheet; `uniprot_hit_names` asks only the fields it uses |
| Returned records closed under naming | `job_records.returned_with_names` (from the summary) | nothing |

## The commission (`messages/read_from_parent.py`, `ASSIGNMENT_FORM`)

Controlled values and record references only. `query_refs` (exactly one protein subject record of the parent's scope), `input_refs`
(the records its sequence is read from, and, with a model, what the model row names: the artifact), `database` (one of
`foldseek_job_route.DATABASES`), `resource_id` (a bound resource of kind `foldseek`), `until` (`launched` or `extracted`),
`handoff_unit`, `information_unit`, `graded_unit`, `model_unit` (positive numbers), and optional: `model_refs` (zero or one HELD
data-product row of kind `protein_structure_model`, passed with the artifact it names: when present the child uses it and
`get_model` is never offered; the row must be made from this target's sequence artifact, else the run fails), and, for a resumed
parked job, `handoff_refs`, `check_refs`, `closure_refs` (each closed under naming: the handoff row names the model file the job
was given and its identity) and `known_ended`. The mode is not a field (fixed `tmalign` in the route). A continuation passes no
`model_refs` (it reads its model from the handoff row). The commission's finite target is the credit still obtainable: the model
(unless one is passed or a job is resumed), the estimate and the launch (unless resumed), and for `extracted` the job known ended
and the graded result. Wrong commissions fail: nothing repairs them.

## States and actions (each answer is ONE JSON action with ONE deterministic check; a check with problems raises `Rejected` with the fix list)

States: `no_model`, `model_held` (a model, no estimate), `estimated` (a model and an estimate), `launched`, `finished`,
`extracted`, `failed`.

| Action | Fields | Check (problem codes) | Unit |
| --- | --- | --- | --- |
| `get_model` | `source` in (`alphafold_db`, `esmfold`) | `model_already_held`, `source_already_tried` (`choose_from` the untried), `sequence_longer_than_the_esmfold_limit` (400, UNVERIFIED figure), `target_sequence_has_residues_no_model_source_takes`; the schema offers it only while a source is untried and no model is held | `alphafold_db`: exact UniProt entries of the sequence, then the model of the FIRST accession (reviewed, score, accession); no entry or no model = `not_found`, a COMPLETED unit that holds nothing and earns nothing, the source is not offered again. `esmfold`: the prediction. A model found: artifact (PDB text), source record (provider `alphafold_db` / `esmfold`), product `protein_structure_model` (settings: origin, accession or null, model version, residues covered, mean pLDDT 0 to 100, SHA-256; location: the file's URL; `used`: the target's sequence artifact). The numbering is checked (below) |
| `estimate` | `database`, `expected_seconds`, `basis` | the ledger's figure exactly (`basis_does_not_match_the_learned_statistics`, `expected_seconds_is_not_the_ledger_estimate`, `choose_from` the figure); not while launched, finished or failed | recorded; the ledger gets ONE row per launch |
| `launch` | `database`, `resource_id` | `estimate_required`, `model_required`, `differs_from_the_estimate`, `differs_from_the_commission`, `resource_is_not_a_foldseek_service`, `job_already_launched`, `fix_required_after_the_failure`, `repeats_the_failed_request_in_the_fixed_field`, `structure_search_results_already_held` (same model file and database), `model_numbering_is_not_the_target_positions` | job `{application: StructureSearch, database, query_file: query.pdb}`, the model file staged as the input; ledger kind `structure_search:foldseek:tmalign:<database>`; job facts: service, application, database, mode, `residues` (the size field); identity kept in the handoff row's `estimates` (database, mode, model SHA-256, target length, model origin, accession, version, residues, mean pLDDT) |
| `fix` | `failure_code`, `field` | only after a failure; the code is the last failure's | nothing runs |
| `monitor` | `handoff_ref`, `wait_seconds`, `expected_remaining_seconds` | the held job, state launched, wait within the stated range | one status request; the first request that shows the end resolves the ledger row (the ticket has no task times: `duration_source` `first_status_showing_the_end`) |
| `extract` | `handoff_ref` | the held job, state finished | one unit: fetch + grade (below) |

THE NUMBERING OF THE MODEL. The server numbers the query residues by their order in the file and the grading takes the model's
C-alpha by that number as the target's position. `model_positions` checks, for every model (found or passed), that the `i`-th
C-alpha has residue number `i` and the three-letter name of the target's residue `i` (and at most as many residues as the
target). It holds for the AlphaFold DB model of CspA (70 of 70) in the direct check; a model that fails is refused.

The extract unit: fetch `result.json` through the route; parse; `measure_hits` (the superposition and B of every hit, once); the
hits in rank order are named by UniProt (the self hit is given no value in the naming picture); `grade_structure_search`; keep:
the result (product `structure_search_results`, `generated_by` the handoff row, `used` the model file, `derived_from` the model's
row when held), the UniProt replies (product `search_hit_metadata`, source provider `uniprot_data`), the grading (source
provider `foldseek_search`, `retain_tool_grading`, product `tool_grading_sheet` by `record_grading_product`). The model file is
read from the handoff row's staged inputs; nothing is recomputed from the commission. A fault of parsing or grading is returned
once as `grading_refused` (or `result_of_another_query`).

THE SELF CONTROL (`structure_search_sheet`, rule source `LIB/knowledge/structural_homology_evidence/native-structural-homology.md`,
"Identical model copies are controls"). With model origin `alphafold_db`, the hit whose target id is the model's own entry
(`AF-<accession>-F<n>-model_v<n>`; an isoform of the entry is another sequence and counts) is the model compared with itself. Its row
has `control: 'model_itself'`, `control_B` and `control_rmsd_A` as facts, `product` null, `B` null: it is in no candidate's mean and in no
candidate's hit count (`control_count`). Other entries with the same sequence are separate models and count.

## The return (`messages/final_to_parent.py`, `RETURN_FORM`)

`credit` and `finding` always. The finding (controlled numbers and vocabulary values; no protein name, no text): `state` (the seven
states), `model_origin` (`alphafold_db` or `esmfold`), `model_residues`, `model_mean_plddt`, once graded `hit_count`, `named_count`,
`not_asked_count`, `candidate_count`, `control_count`, `data_request_count`, `naming_batch_count`, `naming_stopped`; the wait notice of a
parked job `parked`, `seconds_since_launch`, `expected_remaining_seconds`; `estimated_seconds`, `estimate_basis`, `observed_seconds`,
`seconds_past_estimate`; `last_failure_code` (a fixed vocabulary, which adds `model_source_request_failed` and
`model_source_response_invalid`). Selectable record lists, each closed under naming by the summary (`returned_with_names`):
`execution_handoff_refs`, `execution_check_refs`, `execution_closure_refs`, `graded_refs` (the model's product row, the result, the hit
metadata and the grading sheet with their sources and the artifacts they name). The product row of the model is what a later
commission passes back as `model_refs`.

## Credit, ceilings, controller

Bounded, each unit once and only when new in the commission: a model obtained by `get_model` (`model_unit`; not when a model was
passed or a job is resumed; `not_found` earns nothing), an estimate held, the job launched (once however many launches), the job
known ended, the graded result (a held source of provider `foldseek_search`). (This is the child's own completion credit; the HEAD's
credit over candidate annotations is the differential credit of `a102_head.md`: a test earns the entries it admits and ONE differential, the
top two listed candidates' difference, with ceilings `a102_ceiling_v2`.) Ceilings are the terms an action can still newly earn
(0 for an action its check would refuse). Controller: `CompletionYieldController` to the sum of the obtainable units, through
`structure_search_child.completion_controller`. The child's instructions state facts the system enforces and recommend nothing.

## The source providers (SOP Step 13, pitfall 12)

`state.py` constrains a source's operands (`input`, `reference`, `read_subject`, `feature`, `product` records, with a length), its
artifacts and its parents, and names providers only where another record type needs a particular source (`NATIVE_BLAST_DATABASE_PROVIDERS`,
`episode.execution_result`, `rhea`, `chebi`, ...); a source of any other provider text is admitted. The direct check wrote sources of
providers `alphafold_db`, `foldseek_search` and `uniprot_data` through the scoped Store without a central change.

## Direct checks (not a real run; scripts and outputs under `runs/a102_child_check/`, none in the repository)

All through `tools/one_workflow.sh --slot a101`. The Foldseek server is replaced by a route of kind `foldseek` that serves the stored
result of the live ticket (`runs/a102_service_probe/foldseek/result_tmalign_afdb_swissprot_cspa.json`); the Store, the journal, custody, the
unit functions, the model sources (live) and the naming (live, in part b) are real. The run steps the entry episode with
`EpisodeRun.run_unit` (no model is asked); `decide` is called for real through `next_decision()`.

* `run_import1`: the class builds (the `EpisodeBinding` class definition checks every member); `run_command.subtree('sequence_homology_evidence')`
  = 5 (A101 still links).
* `run_uniprot1` (the verification of the `fields` request): 3 accessions, `format=json&fields=accession,protein_name,ec,go_id,
  annotation_score,reviewed`: HTTP 200, 5,612 bytes (45,679 for the whole entries), `proteinDescription.recommendedName.fullName.value`,
  `annotationScore`, `entryType` and the GO cross references present.
* `run_a4` (part a: get_model live, the refusals, launch, monitor, extract with naming switched off): refusals with their fix lists: launch
  without an estimate and a model (`estimate_required`, `model_required`); extract before launched (`no_job_held`) and before finished
  (`job_not_known_to_be_finished`); an estimate of 99 s (`expected_seconds_is_not_the_ledger_estimate`, `choose_from` 10); launch with an
  estimate and no model (`model_required`); a second launch (`job_already_launched`); a second `get_model` once a model is held (the schema
  does not offer it) and, by a direct call of the check on synthetic rows, a second `get_model` of a source that answered `not_found`
  (`source_already_tried`, `choose_from` esmfold). `get_model` alphafold_db live: found P0A9X9, 70 residues, mean pLDDT 88.44, product row
  written. The handoff row's identity and staged `query.pdb` (SHA-256 of the model) were read back; the ledger row has the job facts; the
  monitor resolved it with `duration_source` `first_status_showing_the_end`. Credit 5.0 = target 5.0.
* `run_b2` (part b: the model passed with what it names, live naming): `get_model` not offered; estimate, launch, monitor, extract: credit 4.0 =
  target 4.0; every record of each returned list is held (5, 6, 8 and 12 records); the tables:
  control row: rank 1, `AF-P0A9X9-F1-model_v6`, B (control_B) 1.0000, RMSD 0.0001 A, 70 pairs, product null. Top 10 hits: P0A9Y1 Cold shock
  protein CspA 0.9943; P0A9Y0 Cold shock protein CspA 0.9930; P0A9Y2 CspA 0.9781; P0A9Y4 CspA 0.9764; Q46664 Major cold shock protein 0.9761;
  P0A9Y5 CspA 0.9754; P0A9Y3 CspA 0.9734; P0A981 Cold shock-like protein CspG 0.9679; P0A979 CspG 0.9643; P0A980 CspG 0.9649. Candidates: 130;
  top 10 (product, hits, mean B): Cold shock-like protein CspG 5 0.9501; Cold shock protein CapB 2 0.9192; Cold shock protein CspC 1 0.9119;
  Probable cold shock protein A 4 0.9105; Cold shock-like protein CspC 11 0.9063; Cold shock-like protein CspB 4 0.9061; Cold shock-like protein
  CspI 2 0.9015; Cold shock protein CspA 21 0.8970; Cold shock-like protein CspLA 1 0.8968; Cold shock-like protein CspJ 3 0.8968. Naming: 976 asked,
  975 named (the control is given no name), 0 not asked, 10 batches of 100 (all named: the picture did not settle before the end), 10 requests,
  0 failures. UniProt requests of the checks: 12 (two sequence lookups and 10 naming batches) after the 1 of the verification.

## Not verified

* A real run through the head; a resumed parked job (the continuation path was written from the pattern, not run); the `fix` path and a failed
  launch; the `until` `launched` path.
* `esmfold` live through the unit (`esmfold_model` was verified in the library check); a `not_found` unit through `obtain_model` (the check of
  its tried source was called directly on synthetic rows); `ESMFOLD_MAX_LENGTH` = 400.
* A second job of the kind: the estimate was the first figure (10 s) in every check; the ledger's learning from a measured Foldseek job and the
  `size_fit` were not exercised.
* The route's `queued` and `running` states and `wait` (a102_structure_search_episode, "Not verified" above); the check route answered `finished` at
  once.
* UniProt entries whose accession is secondary: the `fields` request does not ask for secondary accessions, so a hit named by a merged accession
  stays unnamed (`no_name_count`); none occurred in the 976 hits.

# The second database, `pdb100` (library; checked directly 2026-11-21, not a real run)

Why: with `afdb-swissprot` a common protein's 1000 hits fill with its own orthologs (RecA: 18 candidates, all RecA under other names).
Solved structures are diverse and carry bound ligands and nucleic acids. A `pdb100` hit gets the SAME kind of candidate as an
`afdb-swissprot` hit: the UniProt recommended protein name of the chain's protein. Files: `foldseek_job_route.DATABASES` gains
`pdb100` (nothing else of the route), `foldseek_result.pdb_target` (the parser), `pdb_chain_proteins.py` (new: chain -> accession and
the naming loop), `foldseek_search.name_and_chain_hits` (the dispatch by database in the extract; `afdb-swissprot` takes its old path
unchanged), `structure_search_sheet` (rows gain `pdb_entry`, `pdb_chain`, `chain_accession_count`, null for `afdb-swissprot`),
`StructureSearch.json` (the database list). `uniprot_hit_names` is untouched (its `lookup` is called). Checks and data:
`runs/a102_pdb100_check/` (`check_pdb100.py`, `report.py`, `child_b.py`, the replies in `cache/`).

## The target and the chain label

A pdb100 target is `<pdb id>-assembly<n>.cif.gz_<chain label> <entry title>` (the database is built from biological-assembly files).
All 548 targets of the CspA search and all 858 of the RecA search match; the title is the ENTRY's title, not a product name (kept as
`description`). The assembly number takes 1 to 6 (CspA: 437 x 1, 73 x 2, 22 x 3, 10 x 4, 5 x 5, 1 x 6). Forms of the chain label in the 548
CspA targets (A = any upper case letter, a = lower case, 9 = digit): `A` 486 (`A`, `B`); `A-9` 19 (`B-2`, `A-2`); `AA` 17 (`SY`, `AL`, `BE`);
`a` 8 (`x`, `r`, `w`); `A9` 5 (`C0`, `X2`, `D3`); `9` 4 (`6`, `5`, `1`); `AAA` 4 (`DDD`, `HHH`); `AA9` 3 (`SX0`); `Aa` 2 (`Al`, `Ao`). The label
is kept exactly (`chain_label`). The suffix `-<n>` (19 of 548; 19 of 858 for RecA) marks a further symmetry copy of the chain in the assembly:
the base chain (`chain`) is the author chain of the entry, `chain_copy` is `<n>`. That the suffix is a symmetry-operator copy is read
from the pattern (every base chain exists in its entry as a protein chain; the entries are small oligomers, e.g. 2BH8 has chains A, B and
the hits are `A-2`, `B-2`): UNVERIFIED against the Foldseek build scripts.

THE FINDING, which id the label is: the chain label is the AUTHOR chain id (`auth_asym_id`), not the label `asym_id`. Evidence (RCSB
GraphQL, all entries of both searches): all 548 (CspA) and 857 of 857 present (RecA) labels exist as an `auth_asym_id` of their entry; only
483 and 827 exist as an `asym_id` (65 and 30 do not at all); in 35 (CspA) and 55 (RecA) hits the label names a DIFFERENT entity as author id
than as label asym id, and the entity of the author reading is the one whose sequence length is at least the hit's `dbLen` in 35 of 35 and 55
of 55, the label reading in 11 and 18. Examples: `1g29-assembly1.cif.gz_1` (entity 1, MalK, 372 residues = `dbLen` 372; author `1`, label `A`;
there is no label asym `1`); `7zag ..._6` (author `6`, label `FA`, translation initiation factor 1A; no label asym `6`); `7d5s ..._SY` (author
`SY`, label `K`, S23); `8bhu ..._DDD` (author `DDD`, label `D`); `2HAX` chain `B` (author reading: entity 2; label reading: entity 1).
`dbLen` is the length of the chain in the structure file (resolved residues), not the entity's: `7zag ..._6` dbLen 92 of the entity's 134.

## The request (verified live)

`POST https://data.rcsb.org/graphql`, `Content-Type: application/json`, body `{"query": QUERY, "variables": {"ids": [<entry ids, upper case, up
to 100>]}}` with `entries(entry_ids: $ids){ rcsb_id polymer_entities{ rcsb_polymer_entity_container_identifiers{entity_id uniprot_ids}
rcsb_polymer_entity{pdbx_description} entity_poly{rcsb_entity_polymer_type rcsb_sample_sequence_length} rcsb_polymer_entity_align{
reference_database_name reference_database_accession aligned_regions{entity_beg_seq_id ref_beg_seq_id length}}
polymer_entity_instances{rcsb_polymer_entity_instance_container_identifiers{entry_id auth_asym_id asym_id entity_id}}}}`. HTTP 200. The requested `polymer_entity_instances(instance_ids: ["1MJC.A", ...])` root was tried and CANNOT do it: its instance id is
`<entry>.<label asym id>` and an id it does not know is silently left out of the list (`1G29.A` and `7D5S.K` and `7ZAG.FA` answered; `1G29.1`,
`1G29.2`, `7ZAG.6`, `4BTS.C0`, `7D5S.SY` returned nothing and no error), while the Foldseek label is the author id, so the batch is by ENTRY and the
instance is selected in code by `auth_asym_id`. PDBe SIFTS was not needed (no request). One entry of the RecA search (`7t23`, DnaB with
DnaG) is not in RCSB (`GET /rest/v1/core/entry/7T23` -> 404; it stays in the pdb100 build): status `entry_not_returned`, no accession.

THE CHAIN'S PROTEIN. The accessions of the chain's entity are the union of `uniprot_ids` and the UniProt references of `rcsb_polymer_entity_align`.
No accession: asked, no product (CspA 14 of 548 chains, RecA 15 of 858 + the one missing entry). More than one (a chimeric chain: CspA 5, RecA 6 chains,
e.g. `7D8R` chain C: O66738 104 residues and O75030 72): every accession is recorded (`pdb.accessions`, `chain_accession_count` in the sheet); the
chain is named by the accession that covers most of the entity (sum of the aligned regions' `length`) when every accession has a coverage, else by the
first accession in sorted order. The names are then `uniprot_hit_names.lookup` over the accessions (recommended name; a submitted name is used and
flagged `name_source`, as before).

THE NAMING RULE (one rule for both searches): hits in rank order, batches of 100 hits; for each batch the RCSB lookup (pdb100 only) and then the UniProt
lookup of the accessions not named before; after each batch the candidate picture of the hits done (one test, mean B per candidate, over ITS HITS: many
PDB chains share an accession, so the picture takes every hit's own B); stop when a batch admits no new product and moves no candidate by more than 0.01,
or all hits are done; a hit never asked is NOT ASKED. Spacing 3 s before each request; no name, email or key; the browser-like User-Agent constant. Every
reply's bytes are kept as the `search_hit_metadata` product (the RCSB replies and the chain records under `chain_service`).

## The sheet and the control

Per hit: the entry id, the author chain (without the suffix) and the accession or null; B as before: the reference length is `dbLen`, the length of the chain
in the structure. A solved construct can be a fragment of the protein: B then uses the construct's length (CspA: hit lengths 66 to 71 against the target's 70).
The self control: a pdb100 search has none (there is no copy of an AlphaFold model in pdb100; experimental coordinates of the same protein are a different
structure and count as hits): `is_model_itself` matches only an AlphaFold target id, so `control_count` is 0 in both checks. The rule for `afdb-swissprot` is untouched.

## Direct checks (not a real run)

CspA: the stored pdb100 result, the AlphaFold model (P0A9X9). RecA: the AlphaFold model of P0A7G6 (353 residues) and ONE new ticket (pdb100, tmalign:
858 hits, 8.6 MB). Requests: RCSB GraphQL 17 (2 probes, 6 CspA, 9 RecA) and 1 REST; UniProt 15 (6 + 9); PDBe 0; Foldseek 1 ticket; the `afdb-swissprot` runs replayed
the stored UniProt replies of the earlier runs.

* CspA pdb100: 548 hits, 534 with an accession, 14 without; 159 candidates; 6 batches, all named (no settling). Top 15 hits
  (rank entry chain accession product B): 1 1MJC A P0A9X9 Cold shock protein CspA 0.8492; 2 1HZA B P41016 Cold shock protein CspB 0.8747; 3 1C9O B P41016 CspB 0.8505;
  4 1HZ9 B P41016 CspB 0.8509; 5 3I2Z B Q7CQZ5 RNA chaperone, negative regulator of cspA transcription 0.8375; 6 1HZC B P41016 0.8365; 7 1I5F B P41016 0.8298;
  8 8H1I B P0A9Y6 Cold shock-like protein CspC 0.7573; 9 1C9O A P41016 0.8108; 10 1HZ9 A P41016 0.8098; 11 1HZB B P41016 0.8026; 12 3PF5 B P32081 CspB 0.7579; 13 3PF4 A P32081
  0.7476; 14 2I5L X P32081 0.7538; 15 3I2Z A Q7CQZ5 0.5409. Top candidates (product, hits, mean B): Cold shock-like protein CspC 1 0.7573; Cold shock protein CspB 17 0.7500;
  Cold shock protein 1 0.7047; RNA chaperone, negative regulator of cspA transcription 2 0.6892; Probable cold shock protein A 1 0.6546; Cold shock protein CspA 3 0.6203;
  Cold-shock DNA-binding domain family protein 1 0.6006; Y-box-binding protein 2 2 0.5362; Protein lin-28 homolog B 1 0.5101; Calcium-regulated heat-stable protein 1 3 0.5098;
  Y-box-binding protein 1 8 0.5059; Cold shock domain family protein 1 0.4762; Lin-28 homolog B 1 0.4740. Against `afdb-swissprot` (130 candidates): 48 shared, 111 only in
  pdb100, 82 only in afdb. pdb100 adds, among others, RNA chaperone (Q7CQZ5), Cold-shock DNA-binding domain family protein, Cold shock domain family protein, Lin-28 homolog B, HypC,
  RsgI1, PilY2, and gives the Y-box proteins (YB-1 8 hits, YB-2 2) and lin-28 B values 0.5 against 0.2 (afdb) because solved cold shock domains are domain constructs.
* RecA pdb100: 858 hits, 842 with an accession, 15 without, 1 entry not in RCSB; 104 candidates; 9 batches, all named. Top 15 hits: 1 8GMS F A0A485JBB4 Protein RecA 0.6682; 2 7JY9 I P0A7G6
  Protein RecA 0.6828; 3 8AMD G P0A452 RecA 0.5102; 4 1U98 A P0A7G6 0.5862; 5 1U99 A P0A7G6 0.5848; 6 1U94 A P0A7G6 0.5712; 7 4PQY A P9WHJ3 0.4749; 8 1REA A P0A7G6 0.584; 9 4PO9 A P9WHJ3
  0.5294; 10 4PQR A P9WHJ3 0.5349; 11 4PPF A 0.5396; 12 4PO1 A 0.5198; 13 1N03 A P0A7G6 0.6719; 14 4PSK A 0.5346; 15 4PPG A 0.515. Top candidates: Protein RecA 69 0.4317; DNA repair protein RAD51
  homolog 1 0.2991; DNA repair and recombination protein RadB 1 0.2682; DNA repair and recombination protein RadA 70 0.2596; Meiotic recombination protein DMC1 homolog 11 0.2534; DNA repair protein
  RAD51 6 0.2486; Meiotic recombination protein DMC1 1 0.2454; DNA repair protein RAD51 homolog 1 17 0.2382; RAD51 homolog 3 7 0.2291; KaiC domain-containing protein 3 0.2285; XRCC2 2 0.209.
  Against `afdb-swissprot` (18 candidates): 5 shared (Protein RecA 652 hits 0.6126 afdb / 69 hits 0.4317 pdb100; RadA 47 0.228 / 70 0.2596; RadB; two ATP synthase alpha), 99 only in pdb100:
  RAD51 (several names), DMC1, XRCC2, RAD51 paralogs, KaiC domain proteins, SulA, others. So RadA, Rad51 and DMC1 DO appear, as the recombinases the afdb search never listed.
* The differential credit (A102 copies), RecA: the `afdb-swissprot` test alone 6.2504 (18 entries); then the `pdb100` test: 18.931 (rise 12.68; 117 candidates listed, 99 entries for the new
  ones summing 11.07, and 10 differentials among the shared ones). CspA: 41.408 then 304.09 (241 entries, 1128 differentials: many shared and many new candidates).
* `afdb-swissprot` unchanged: the child's direct extract check (`child_b.py`, the same as `run_b2` above, with the stored UniProt replies replayed) gives the same sheet:
  976 hits, control 1, 975 named, 130 candidates, the same top 10 candidates and hits, naming 976 asked in 10 batches. The only difference is the three added null keys per hit row.
* Imports of the touched modules pass; `len(run_command.subtree('structural_homology_evidence'))` 2, `sequence_homology_evidence` 5.

## Not verified, and what did not fit

* The meaning of the `-<n>` suffix (above). Nothing was run through the head or the child's unit with `pdb100` (the unit's extract path is the same function; the check called the
  dispatch and the sheet directly). The `site_correspondence` library reads the sheet's `accession` of a hit and does not handle a null accession (a pdb100 chain with no UniProt
  accession) nor take the entry and chain from the PDB: it is the other agent's and was not edited.
* A chain whose accession UniProt has since merged is unnamed (as for `afdb-swissprot`, `no_name_count`). The RCSB service's limits are not documented in the pages read; none was met.
