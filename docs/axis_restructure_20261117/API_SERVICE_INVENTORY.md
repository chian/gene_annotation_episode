# Inventory of web API services used by the episodes (19 November 2026)

This lists every episode under `gene_annotation_episode/episodic_workflow/root/` (axes a101 to a110) that
works against a remote web service, and for each service says how the service answers, what the episodes do
with it today, and whether the API job route has a protocol for it.

It was made by reading the code and the documents of this repository only. No service was contacted and no
code was run. Where the code does not settle a point, the text says "not determinable from the code"; those
points are collected in the last section.

## Main findings

- **One service works on the new design: NCBI BLAST, in one episode (A101).** The route has one protocol,
  `ncbi_blast`. The A101 launch episode submits once and ends at the handoff.
- **The A101 monitor cannot yet read an API job.** Every monitor reads a status reply through a table that
  has entries for local and PBS jobs only; an API job raises `KeyError('api')`
  (`episode_support/jobs/job_progress.py:52-59`).
- **The other 14 `api_job_execution` episodes and the 3 `api_resource_work_execution` episodes do not run.**
  They call members of the job service that do not exist, or raise `NotImplementedError`.
- **Three more services have a status step and no protocol:** EBI HMMER, BV-BRC AppService and Rfam batch
  search. BV-BRC AppService needs a login, and the route sends no credential.
- **Three services answer in one reply but are named as services of a launch episode:** BV-BRC Data, BV-BRC
  Minhash and UniProt. Under the owner's rule they should be one blocking tool call, with no handoff.
- **All literature searching is one call per request**, against services that answer in one reply. This fits
  the rule. It is in 27 literature episodes (three per axis) and in the head episodes.
- **One blocking tool hides a job:** the tool `public.blast.search` submits a BLAST search, sleeps and asks
  status inside a single tool call. That does not fit the rule for a service with a status step.

## Words used

| Word | Meaning here |
|---|---|
| Episode | One folder under `root/` with its ten files (`goal.py`, `task.py`, and so on) |
| Head | The top episode of an axis, for example `root/a101/sequence_homology_evidence` |
| With a status step (asynchronous) | The service takes a request, returns an identifier, and the result is fetched later after asking for the status |
| In one reply (synchronous) | One request; the reply is the result |
| The rule | A service with a status step is used as launch, handoff, monitor, extract. A service that answers in one reply is one blocking call that returns the result, with no handoff and no monitor |
| Launch, handoff, monitor, extract | Launch: submit once. Handoff: the stored record of the accepted submission. Monitor: a later episode asks the status. Extract: a later episode fetches the result |
| Job service | `JobAccess` in `episode_runtime/job_access.py`. Its members are `resources`, `describe`, `launch`, `check`, `window`, `fetch`, `cancel`, `run` (lines 107-312) |
| Route | The part of the job service that reaches one kind of resource. The API route is `episode_support/jobs/api_job_route.py` |
| Protocol | A class in the route file that says, for one service, what a job is and how to build and read the three requests (submit, status, result). `PROTOCOLS` lists them (line 191) |
| Stub | Code that names a call that does not exist, or raises `NotImplementedError`, so the episode cannot run |
| Registry | The per-axis class `ToolRegistry` in `episode_support/tools/<axis name>/tools.py`. It maps a tool name such as `public.literature.search` to one client call |
| Commission | What a parent episode sends a child to start it |

Paths below are shortened: `root/` is `gene_annotation_episode/episodic_workflow/root/` and `support/` is
`gene_annotation_episode/episodic_workflow/episode_support/`.

## Table 1: the services

"Fits the rule" compares what the episodes do today with the rule above.

| Service (name in code) | How it answers, and where the code shows it | Episodes that use it | What they do today | Fits the rule | Route protocol |
|---|---|---|---|---|---|
| NCBI BLAST (`ncbi_blast`) | With a status step. `support/jobs/api_job_route.py:98-110, 148-169`: submit returns an identifier, then a status request, then a result request | A101 launch, monitor and extract episodes; the `api_job_execution` episodes of a102, a103, a104, a107; the registry tool `public.blast.search` | A101: launch works, monitor fails on an API job, extract has a path. Others: stubs. Registry tool: one blocking call that polls inside | A101 launch: yes. A101 monitor: not yet. Others: no | Yes: `NcbiBlastUrlApi` |
| EBI HMMER (`ebi_hmmer`) | With a status step. `support/acquisition/sequence_homology_evidence/acquisition.py:724-749`: `hmmer_submit`, `hmmer_status`, `hmmer_result` | The `api_job_execution` episodes of a103, a104, a107 | Stubs. No library code calls the three client methods | No (nothing runs) | No |
| BV-BRC AppService (`bvbrc_appservice`) | With a status step, and it needs a login. `support/tools/service_calls/gene_context_evidence/bvbrc_appservice_tool_info.py:44-57, 89-92`: submit returns a task identifier, then status, then download | Both a106 `api_job_execution` episodes and both a106 `execution_result_acquisition` episodes; also named in a103, a104, a107 API episodes | Stubs | No (nothing runs) | No. The route sends no credential (`api_job_route.py:6-7`) |
| Rfam batch search (`rfam_batch`) | With a status step. `support/acquisition/similarity_search/api_rfam.py:144-176, 329-353`: submit, status, fetch | No episode names it today | Library code only; nothing calls it | Not applicable | No |
| BV-BRC Data (`bvbrc_data`) | In one reply. `support/acquisition/service_calls/api_bvbrc.py:3`: "returns a page immediately. It has no remote job to submit or poll" | Named in the a103 and a104 `api_job_execution` episodes | Stubs, inside a launch episode | No: it is placed in a launch episode | No, and it needs none |
| BV-BRC Minhash (`bvbrc_minhash`) | In one reply. `support/acquisition/similarity_search/api_bvbrc_minhash.py:3-6`: "No job, polling loop ... for an immediate response" | Named in the a103 `api_job_execution` episodes | Stubs, inside a launch episode | No: same reason | No, and it needs none |
| UniProt (`uniprot`) | In one reply. `support/acquisition/sequence_and_context_sources/api_uniprot.py:1`; `acquisition.py:291-307` | As a lookup tool: heads, and literature episodes through `public.literature.sequence_identity`. As a named service: the a104 `api_job_execution` episodes; it also appears in return fields of two a103 copies and one a107 copy | Lookup tool: one call. Named service: stubs, inside a launch episode | Lookup: yes. Named service: no | No, and it needs none (`API_PORT_RECIPE.md:56-57`) |
| Europe PMC (`europepmc`) | In one reply. `acquisition.py:752-761` | 27 literature episodes; heads | One call per request | Yes | None needed |
| NCBI E-utilities (`ncbi_entrez`): PubMed search, sequence records, taxonomy | In one reply. `acquisition.py:763-789` | 27 literature episodes; heads | One call per request | Yes | None needed |
| PMC open-access file store (`pmc_cloud_*`) | In one reply. `acquisition.py:684-722`; address in `support/literature/readers/sequence_homology_evidence/literature_assets.py:13` | 27 literature episodes; heads | One call per request (the file listing makes two immediate requests) | Yes | None needed |
| Experimental databases: SABIO-RK, BRENDA, PubChem BioAssay, ChEMBL, MaveDB | In one reply. `support/acquisition/sequence_homology_evidence/experimental_database_acquisition.py:3`: "Each invocation performs one public read request" | Literature episodes of a102, a104, a105, a106, a110; heads of a102 and a105; six registries (note 9) | One call per request | Yes | None needed |
| NCBI GEO files, NCBI SRA files | In one reply. `support/tools/sequence_and_context_sources/partner_presence_evidence/geo_tools.py:1`; `support/acquisition/sequence_and_context_sources/ncbi_sra_acquisition_host.py:1` | Literature episodes of a106; a107 registry | One call per request | Yes | None needed |
| AlphaFold, RCSB PDB, EMDB | In one reply. `support/acquisition/protein_structure/alphafold_acquisition.py:22`, `rcsb_acquisition.py:23-24`, `emdb_acquisition.py:1` | a102 head | One call per request, but see note 9 | Yes | None needed |
| Ensembl BioMart, UCSC, STRING, ENCODE | In one reply. Module headers of `ensembl_acquisition.py`, `ucsc_acquisition.py`, `string_acquisition.py` under `support/acquisition/sequence_and_context_sources/gene_context_evidence/`; `support/tools/sequence_and_context_sources/encode_tools.py:1-8` | Registries of a103 and a107 only | One call per request when a head runs them | Yes | None needed |
| Rhea, ChEBI, KEGG, Reactome, PubChem compound | In one reply. `support/acquisition/biochemical_feasibility_evidence/acquisition.py:632-672`; `support/acquisition/chemical_source_acquisition.py:102-107` | Registry of a110 only | One call per request when the head runs them | Yes | None needed |
| Rfam model download | In one reply. `support/acquisition/partner_presence_evidence/acquisition.py:722` | Registry of a107 only (`public.rfam.model`) | One call per request when the head runs it | Yes | None needed |

## Table 2: the API episodes, one row each

There are 15 `api_job_execution` folders and 3 `api_resource_work_execution` folders. (`BRANCH_RUNS_api.md`
says 17 copies of `api_job_execution`; the folders on disk number 15.) a105 and a108 have none. a110 has
`execution_job_submission` with local and HPC children only.

"Services named" is what the episode's own files name today, and in brackets what its own files named at
commit `97308b94c` where that differs.

| Episode (under `root/`) | Services named | State today |
|---|---|---|
| `a101/sequence_homology_evidence/execution_job_submission/api_job_execution` | `ncbi_blast` (old files also named `ebi_hmmer`, `bvbrc_data`, `bvbrc_minhash`, `bvbrc_appservice`, `uniprot`) | Works on the new design: one tool `submit`, which calls `job_access.launch` once and returns the handoff (`task.py:206-222`). No wait, no status, no fetch |
| `a102/structural_homology_evidence/execution_job_submission/api_job_execution` | None in its files. The service is a name given by the parent. Its tests use `ncbi_blast` | Stub (`task.py:12-17, 158-174`): calls `read('api_catalog')`, `api_execute`, `wait_for_job`, none of which the job service has |
| `a102/.../hpc_work_planning/execution_job_submission/api_job_execution` | Same as the row above | Stub. `task.py` is byte-identical to the row above |
| `a102/.../hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution` | Same | Stub. `task.py` is byte-identical |
| `a103/gene_context_evidence/execution_job_submission/api_job_execution` | `ebi_hmmer`, `bvbrc_data`, `bvbrc_minhash` (old files also named `ncbi_blast`, `bvbrc_appservice`, `uniprot`) | Stub (`task.py:20-29`): `api_execute`, `wait_for_job`, `write_handoff_record` raises |
| `a103/.../hpc_work_planning/execution_job_submission/api_job_execution` | `bvbrc_appservice`, `bvbrc_data`, `bvbrc_minhash`, and `uniprot` in its return fields; its tests use `ncbi_blast` and `ebi_hmmer` | Stub (`task.py:12-13`): calls `job_access.api_capabilities`, `api_operation`, `api_wait`, which do not exist |
| `a103/.../hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution` | Same as the row above | Stub. `task.py` is identical to the row above |
| `a104/evolutionary_history_evidence/execution_job_submission/api_job_execution` | `ncbi_blast`, `bvbrc_appservice`, `bvbrc_data`, `ebi_hmmer`, `uniprot` (`messages/read_from_parent.py:15`) | Stub (`task.py:9-11, 77`): calls `job_access.launch_operation`, which does not exist; `_job_ledger` raises |
| `a104/.../hpc_work_planning/execution_job_submission/api_job_execution` | Same | Stub, same form |
| `a104/.../hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution` | Same | Stub. `task.py` is identical to the first a104 row |
| `a106/perturbation_evidence/execution_job_submission/api_job_execution` | `bvbrc_appservice` only | Stub (`task.py:19-27, 172-187`) |
| `a106/perturbation_evidence/published_evidence_assessment/execution_job_submission/api_job_execution` | `bvbrc_appservice` only | Stub (`task.py:14-16`): `api_capabilities`, `api_operation`, `api_wait` |
| `a107/partner_presence_evidence/execution_job_submission/api_job_execution` | `ebi_hmmer` (old files also named `ncbi_blast`); its tests use `ncbi_blast` | Stub (`task.py:19-27, 192-209`) |
| `a107/.../hpc_work_planning/execution_job_submission/api_job_execution` | `ebi_hmmer`; its tests use `ncbi_blast` | Stub (`task.py:13-19`) |
| `a107/.../hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution` | `ebi_hmmer`, `bvbrc_appservice`, and `uniprot` in its return fields | Stub (`task.py:11-12`): `api_capabilities`, `api_operation`, `api_wait` |
| `a101/sequence_homology_evidence/resource_work_submission/api_resource_work_execution` | None. Its tests use a resource called `ncbi_blast` | Old form, not ported (`task.py:18-27`). It needs a wrapper `support/jobs/resource_api.py`, which does not exist (`RESOURCE_PORT_RECIPE.md:197-206`) |
| `a102/structural_homology_evidence/resource_work_submission/api_resource_work_execution` | None. Same | Old form, not ported (`RESOURCE_PORT_RECIPE.md:229`) |
| `a103/gene_context_evidence/resource_work_submission/api_resource_work_execution` | None. Same | Old form, not ported (`RESOURCE_PORT_RECIPE.md:238`) |

Every stub above has the same old shape: the model picks one service operation per turn (prepare, submit,
status, fetch) and may pick a `wait`, all inside the launch episode. That shape does not fit the rule for
either kind of service: a job service must end at the handoff, and a one-reply service needs no launch
episode.

## Notes on each service

### 1. NCBI BLAST

- **Launch (A101).** Ported and described in `API_PORT_RECIPE.md`. The episode's only acting tool is
  `submit`. This fits the rule. The recipe states it ran offline against a local test server and, with the
  real model, against the public service; this inventory did not run it.
- **Launching parent (A101).** `root/a101/sequence_homology_evidence/execution_job_submission` builds the
  child's commission for the slot `launch_api` (`messages/msg_to_child.py:70-73`).
- **Monitor (A101).** `root/a101/sequence_homology_evidence/execution_progress_assessment` asks the status
  with `job_access.check(ctx, handoff_ref, assess=status_reading)` (`task.py:117`). `status_reading` looks
  up the handoff's kind in `READINGS = {'local': ..., 'pbs': ...}` (`support/jobs/job_progress.py:52-59`).
  An API handoff has kind `api` (`api_job_route.py:197`), so the check raises `KeyError`.
  `MONITOR_PORT_RECIPE.md:116-119` says the same and asks for the reading to be added first. The same gap
  holds for the top-level monitors of a102, a103, a104, a106, a107 and a110, which use the same function.
- **Extract (A101).** `root/a101/sequence_homology_evidence/execution_result_acquisition` fetches with
  `job_access.fetch` and grades the BLAST report (`task.py:135, 173, 187-219`; family `blast_graded`). For
  any other API result it raises `NotImplementedError('unplaced:api_execution.validate_result_selector')`
  (`messages/read_from_parent.py:141-142`). The a104 and a107 copies have the same raise and no BLAST
  grading path.
- **Other axes.** The API episodes of a102, a103, a104 and a107 are stubs (table 2). `ncbi_blast` already has
  a protocol, so these need only the episode port of `API_PORT_RECIPE.md`.
- **The registry tool `public.blast.search`.** It exists in the registries of a101, a102, a103, a104 and
  a107. Its own description says "Durable submission, same-job protocol wait and native results are one
  ordinary action" (`support/tools/sequence_homology_evidence/tools.py:237`). It calls
  `RemoteSearches.search` and `collect`, which sleep and ask status in a loop
  (`support/jobs/service_calls/sequence_homology_evidence/provider_jobs.py:276-322`). This is a job hidden
  inside one blocking call, which the rule does not allow for a service with a status step. The a102 head
  names this tool (`root/a102/structural_homology_evidence/task.py:324-326, 570-578`). The heads of a101,
  a103, a104 and a107 can run it only if their commission selects it.

### 2. EBI HMMER

- With a status step: `hmmer_submit` posts to `search/<algorithm>`, `hmmer_status` reads
  `search/<job id>`, `hmmer_result` reads `result/<job id>` (`acquisition.py:724-749`).
- No protocol in the route. `API_PORT_RECIPE.md:74-77` says what to add, including a JSON request body,
  which the route's sender does not have yet.
- No library code calls the three client methods today. The registry refuses HMMER with
  `hmmer_requires_api_execution_episode` (`provider_jobs.py:216-217, 290-291`).
- Episodes that name it: the API episodes of a103, a104 and a107 (table 2), all stubs. The launching parents
  of a101, a103, a104 and a107 send a resource of kind `hmmer_api` to the API child (`task.py`, `KINDS`).
  The A101 API child no longer accepts it: "no route to that service is bound"
  (`root/a101/.../api_job_execution/messages/read_from_parent.py:13`).

### 3. BV-BRC AppService

- With a status step: `submit` (one `start_app2` request, returns a task identifier), `status`
  (`query_tasks`), then listing and download of outputs (`bvbrc_appservice_tool_info.py:44-57, 89-92`).
- It needs a login. `api_bvbrc.py:4-6` calls it "a different, authenticated interface", and its transport
  reads an authorization header from an environment variable
  (`support/acquisition/service_calls/gene_context_evidence/bvbrc_analysis_transport.py:55-58`).
- The route is for services that answer anyone and sends no credential. `API_PORT_RECIPE.md:51-53` says
  BV-BRC AppService stays out of this route and that a106 is "not portable onto this route".
- Episodes: both a106 launch episodes and both a106 result episodes
  (`root/a106/perturbation_evidence/execution_result_acquisition` and
  `.../published_evidence_assessment/execution_result_acquisition`, identical files, stubs at `task.py:86`).
  It is also named in the a103 planning copies, the a104 copies and one a107 copy (table 2).

### 4. Rfam batch search

- With a status step: `prepare`, `submit` (returns a job identifier), `status`, `fetch`
  (`api_rfam.py:144-176`; the states at `329-353`).
- The a107 library can build it (`support/acquisition/service_calls/partner_presence_evidence/api_services.py:60, 92-94`),
  but nothing calls that builder, and no a107 episode file names Rfam today. At commit `97308b94c` the a107
  API child mentioned Rfam only to check a returned report (`to_parent.py:79-80`).
- No protocol in the route.

### 5. BV-BRC Data, 6. BV-BRC Minhash, 7. UniProt as a named service

- Each answers in one reply (table 1). The old library classes mark the single reply as both "handoff ready"
  and "result available" (`api_bvbrc.py:417`, `api_bvbrc_minhash.py:210-211`, `api_uniprot.py:202-203`),
  which is how the old launch episode treated an immediate answer.
- Today they are only names in stubbed launch episodes (table 2). Under the rule each should be one blocking
  tool call in the episode that needs the data. `API_PORT_RECIPE.md:56-57` says this for UniProt.
- BV-BRC Minhash accepts optional authorization settings
  (`support/acquisition/service_calls/gene_context_evidence/api_services.py:48-49`).
- The library builder `build_service` that makes these classes is not called by any episode or other library
  module.

### 8. Literature and lookup services (one reply each)

- **How a call is made.** The episode's tool calls the registry once
  (`root/a101/sequence_homology_evidence/published_evidence_assessment/task.py:256-260`), and the registry
  runs one client function (`support/tools/sequence_homology_evidence/tools.py:1295-1297, 1305-1342`). No
  handoff and no monitor. This fits the rule.
- **Which literature episodes.** In every axis (a101 to a108, a110) the three search-level episodes:
  `published_evidence_assessment`, its child `evidence_search_strategy_improvement`, and that child's
  `source_relevance_assessment`. That is 27 episodes.
- **The deeper literature episodes** (`source_evidence_examination` and its three children, in every axis)
  name no `public.*` tool. Their tools read documents the episode already holds (`source.*`, `state.query`,
  `image.view`, and local `literature.*.populate` tools).

Tools named in the three search-level literature episodes, by axis:

| Axis | Europe PMC search and read | PubMed search (`public.ncbi.search`) | PMC file store | Other |
|---|---|---|---|---|
| a101, a103, a107 | yes | yes | yes | UniProt search through `public.literature.sequence_identity` |
| a102, a104, a105, a110 | yes | yes | yes | the same, and the five experimental databases |
| a106 | yes | yes | yes | the same, the five experimental databases, `public.ncbi.entrez`, `public.ncbi.sequence`, `public.ncbi.geo`, `public.ncbi.sra.file` |
| a108 | yes | yes | yes | the same, `public.ncbi.sequence`, `public.taxonomy` |

`public.literature.sequence_identity` is a UniProt search
(`support/literature/readers/sequence_homology_evidence/literature_sequence_discovery.py:37-42`).

### 9. Head episodes

- The root episode (`root/episode.py`, `root/task.py:37-38`) has no tools and no services.
- **a102, a105, a108 heads** name their remote tools in `task.py`. The a102 head names the largest set,
  including AlphaFold, RCSB, EMDB, UniProt and `public.blast.search`. Reaching any library tool in the a102
  head is blocked on a missing `tool_catalog` service (`root/a102/structural_homology_evidence/task.py:43-47, 662-685`).
- **a101, a103, a104, a106, a107, a110 heads** run "the selected tools of the commission": the tool name
  arrives as an argument and is passed to the registry (for example
  `root/a101/sequence_homology_evidence/task.py:458-467`). They can therefore reach any remote tool of
  their axis's registry:

| Registry | Remote tools it defines (all `public.*`) |
|---|---|
| a101, a104 | `uniprot`, `ncbi` (search, sequence, entrez), `taxonomy`, `literature`, `pmc`, `blast.search`, `blast.collect`, `search.jobs` |
| a102 | the same, and `alphafold`, `rcsb`, `emdb` |
| a103 | the a101 set, and `ensembl.request`, `ucsc.request`, `string.network` |
| a105, a108 | `ncbi`, `taxonomy`, `literature`, `pmc` (a108 also `ncbi.entrez`) |
| a106 | `uniprot`, `ncbi` (also `geo`, `sra.file`), `taxonomy`, `literature`, `pmc` |
| a107 | the a103 set, and `ncbi.geo`, `ncbi.sra.file`, `encode`, `rfam.model` |
| a110 | `uniprot`, `ncbi`, `taxonomy`, `literature`, `pmc`, `rhea`, `chebi`, `kegg.reaction`, `reactome.record`, `pubchem.compound` |

The registries of a101, a102, a104, a105, a106 and a110 also define the tools of the five experimental
databases (they import `experimental_database_acquisition`); those of a103, a107 and a108 do not.

## The route today

- File: `support/jobs/api_job_route.py`. `PROTOCOLS = {'ncbi_blast': NcbiBlastUrlApi}` (line 191). A
  configuration naming any other service is refused with `api_route_service_has_no_protocol` (lines
  202-203).
- It is for public services only: "no login, token, cookie or `Authorization` header" (lines 6-7).
- It is bound through `support/jobs/job_services.py` under the configuration part `api` (lines 46-56).
- Protocols by service: `ncbi_blast` yes; `ebi_hmmer` no; `rfam_batch` no; `bvbrc_appservice` no and it
  cannot be added without a decision about credentials. The one-reply services need none.

## Documents that are out of date on this subject

- `LAUNCH_MONITOR_EXTRACT_MECHANICS.md:494`, `LAUNCH_PORT_RECIPE.md:161` and `EXTRACT_PORT_RECIPE.md:197`
  say no API route exists. One exists now, with the one protocol.
- Several stubbed episodes say in their `task.py` header that the job service "does not exist yet". It
  exists; what is missing is the members those stubs call (`api_execute`, `api_operation`,
  `launch_operation`, `wait_for_job`, `api_wait`, `api_capabilities`, and the reads `api_catalog`,
  `api_decision_context`, `received_bvbrc_context`).

## Not determinable from the code

1. **Which service a stubbed API episode would be asked to use in a real run.** In most of these episodes the
   service is a free name in the commission, set by the parent and by the run's configured resources. The
   three a102 API episodes name no service at all in their own files, old or new.
2. **Which service the three `api_resource_work_execution` episodes are meant for.** Their files name none.
3. **Which remote tools the heads of a101, a103, a104, a106, a107 and a110 actually run.** The tool is chosen
   by the commission from a frozen tool library, which is an input of the run.
4. **Which episode was meant to launch an Rfam batch search.** No current episode file names it.
5. **Whether the A101 chain (launch, monitor, extract) has run end to end on an API job.** The code says the
   monitor would raise on an API handoff. `API_PORT_RECIPE.md:157` says the model run used a test episode
   (`job_probe`) for the check and the fetch. Nothing was run for this inventory.
6. **Whether UniProt, BV-BRC Data and BV-BRC Minhash were meant to stay inside the API launch episodes.** The
   old code put them there; the recipe says UniProt is an ordinary tool; nothing in the code decides it for
   the two BV-BRC services.
7. **What each remote service requires or returns in fact** (rate limits, whether a contact address or a
   token is needed, current addresses). Only what the code and documents state is reported here.
8. **Whether the registry's remote tools run under the new runner today.** The call paths were read, not
   executed.
