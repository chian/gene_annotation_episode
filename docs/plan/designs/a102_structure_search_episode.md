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
