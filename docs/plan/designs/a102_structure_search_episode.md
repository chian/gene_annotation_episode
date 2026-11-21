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
known ended, the graded result (a held source of provider `foldseek_search`). Ceilings are the terms an action can still newly earn
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
