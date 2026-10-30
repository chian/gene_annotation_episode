# Source and path audit

This audit supports [CONTRACT.md](CONTRACT.md). It records observations, not implementation completion. Sources were inspected on 2026-10-26 UTC. The workspace is not a Git checkout with a `.git` directory; no commit/diff identity is claimed. Only this additive verification directory was written.

## Authority read before proposing execution behavior

Read complete `AGENTS.md`, `GOAL.md`, the immutable original goal attachment `/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`, `docs/TASK_AND_STEERING.md`, `docs/EPISODE_STRUCTURE.md`, `docs/TIME_AWARE_ESTIMATION.md`, `docs/PRACTICAL_EXECUTION.md`, `docs/PRACTICAL_EXECUTION_CONTRACT_2026-10-22_001.md`, and `docs/TOOL_GRADER_GOAL_AND_PRINCIPLES_2026-10-24_001.md`. Read the relevant information-library construction/resource sections of `docs/TOOL_KNOWLEDGE.md` and the fixed/inventory row records. The original objective and all 16 original principles were reread verbatim after substantial source study and again at closure. Mutable summaries and tests did not substitute for them.

Fixed scope remains `A-L068-rfam-batch`, API route. The local Infernal result path belongs to separate work; it is consulted here only to establish matching versus nonmatching formats/math. `public.rfam.model` belongs to a separate acquisition/model-information concern; its tests do not prove batch scanning.

## Authoritative external sources and retained bytes

| Source | Evidence used | Limitation |
|---|---|---|
| [Official Rfam API documentation](https://docs.rfam.org/en/latest/api.html) | Multipart field `sequence_file`, accepted handle shape, old result polling description, complete single JSON example, one-week retention statement | Documentation example, not current successful run; prose/table method conflict for 202 status; old XML mention not exposed in current OpenAPI |
| [Current deployed OpenAPI](https://batch.rfam.org/openapi.json) | Exact submit/status/result/table/report endpoints, multipart email/id optional properties, JSON union and all typed single-hit fields | No value enums for status; `MultipleSequences.hits.items={}`; does not reveal command, database release, Infernal version, cutoff/search-space or model lengths |
| [Official Rfam docs source](https://raw.githubusercontent.com/Rfam/rfam-docs/master/docs/source/api.rst) | Exact extractable complete example JSON, same native scalar/display fields | Source-example fixture, not live output |
| [Rfam FAQ: model hit scores](https://docs.rfam.org/en/latest/faq.html#what-do-the-scores-for-hits-to-rfam-models-mean) | Rfam model hit scores are Infernal log-odds bit scores | Does not establish deployed options or a calibrated annotation probability |
| [Official Rfam genome annotation guide](https://docs.rfam.org/en/latest/genome-annotation.html) | E-value and native score meanings; explicitly selected `--cut_ga`, `-Z`, `--fmt 2` illustrate that these are command-dependent facts | Its local tutorial command is **not** the remote server's observed command; no such defaults imported into the proposal |
| [Rfam internal website documentation](https://rfam-internal-docs.readthedocs.io/en/latest/website.html) and linked repository | Official source pointer is `Rfam/rfam-website` | Repository API returned 404 without credentials; current FastAPI producer implementation not established |
| Installed upstream Infernal 1.1.5 guide `resources/software/infernal-1.1.5/documentation/userguide/tutorial.tex` (alignment portions near 645–685 and 1090–1205) | Posterior bins, optional PP, CM consensus/query axes, local-end and truncation display examples | Native Infernal display semantics; not proof that the current remote wrapper emits every variant unchanged |

`source_evidence/source-manifest.json` contains exact URL, effective URL, HTTP status/headers, retrieval time, bytes and SHA256 for the main docs, OpenAPI, Swagger page, documentation source and Rfam public repo-list lookup. The public repo list/source lookup did not establish the deployed producer. `rfam-site-search.html` is an ancillary source-discovery read; its later move to `/search/batch` does not define the API schema. `source_evidence/old-job-get-manifest.json` separately preserves the exact expired-job probes and the website-source 404.

Important exact retained native absence responses, all GETs of the **pre-existing documented** ID `infernal_cmscan-R20240522-154022-0777-68207895-p1m`:

| URL suffix | HTTP | Retained body | Meaning established |
|---|---:|---|---|
| `/status/{id}` | 200 | `NOT_FOUND` (9 bytes) | Current token for this old handle; no complete search result |
| `/result/{id}` | 200 | 141 bytes: `searchSequence:""`, `numHits:0`, correct jobId, empty timestamps, `hits:{}` | Empty identity-bearing field is an unavailable result representation; no measured zero for the requested sequence |
| `/result/{id}/tblout` | 200 | 0 bytes | Endpoint exists, actual successful table dialect not observed |
| `/result/{id}/out` | 200 | 0 bytes | Endpoint exists, actual successful report dialect not observed |

No POST to Rfam was performed. These HTTP 200 bodies must not become example successful no-hit searches. GET observation does not submit or repair an old job.

## Current complete Rfam acquisition and publication path

The following relevant complete functions/modules were read, including their error/recovery branches, before assessing ownership:

| Path and function | Observed current behavior | Consequence for new boundary |
|---|---|---|
| `acquisition.py`: `SourceSnapshot`, `AcquisitionError`, `PublicClients._http` (~358), `rfam_submit` (421), `rfam_result` (441) | Submit is one multipart HTTP call; result is one GET. Exact raw body metadata exists. `_http` uses redirect-following `urlopen`; successful interrupted-read partial bytes are not fully modeled | Reuse envelope, preserve all bytes; Rfam-scoped one-request transport must not silently follow redirects and must distinguish partial read |
| `rfam_discovery.py`: complete module | Fixed origin and ID/URL validation; exact job/query digest match; native row mapping; E/score/GC validation; partial rows; length-limit feedback | Useful pure validation facts, but no numerical sheet/calculator and no full alignment parser. Add strand/endpoint consistency, count and completeness distinctions |
| `provider_jobs.py`: `RemoteSearches.search`, `collect`, durable snapshot/update/failure and describe paths | Durable intent before POST; original response saved before parse; no uncertain resubmission. Rfam search sleeps then calls collect; collect runs GET/sleep `while True`; BLAST shares implementation | Preserve durable facts and legacy replay, replace new Rfam compound decisions with episode-selected operations. Do not change BLAST under this task |
| `tools.py`: tool declarations; `_check_sequence_operand`, `_sequence`, `_acquire_async`, `_import`, `_import_rfam_discovery` (1817–1880), relevant execute/publication/error paths | Exact original selected sequence/member scope; Rfam direct tools route through RemoteSearches. Importer requires provider_jobs row to find submission. All valid rows/alignments retained; public preview only first12. Native query interval and score/E/GC; family has no physical reference sequence/length | New API publisher needs explicit original submission, not fake provider_jobs state. Preserve full results and distinguish receiver preview from native completeness |
| `api_execution.py`: complete legacy `HMMERAPIExecution` | Dedicated HMMER API assumptions and request schema | Not an appropriate class to broaden into Rfam |
| `api_service_execution.py`: complete module | Actual selected-operation intent checks; single service invocation; immutable snapshot-before-decode; existing handoff/result receipts/custody; monitor observes one prepared call; generic completion and caller-owned operational credit | This is the correct shared route. Extend Rfam facts/publication/custody, not a private loop. Keep rejected identity raw source and partial status |
| `api_services.py`: complete protocol/build/config/publication helper | Exact `APIServicePrimitive` signatures; configured services do not yet include Rfam. `publish_existing_acquisition` publishes a supplied snapshot without new acquisition | Add Rfam to the actual builder/config branch; use explicit publisher callback |
| `api_blast.py`: complete service | Existing individually selected API operation pattern and original handle/result binding | Reuse mechanics, not BLAST scientific model, rate policy, or arbitrary status names |

`_sequence(..., molecule_model="rna")` returns existing bytes for ordinary sequence/read inputs. It only uses the processing model where needed for a feature reverse complement; it does not automatically rewrite all T to U. A selected `sequence.view` has a distinct registered mapping. This matters to exact submitted-response hashes and original input coordinates.

The saved importer preserves native opened/started/closed values. Historical documentation notes one old capture's started/opened time later than its closed time; this workload cannot verify the absent capture and will not repair its clock or infer execution duration. No forecast, timing sample, throughput or completion percentage is manufactured from a job label or status token.

## Existing numerical readers/calculators and receiver patterns inspected

- `infernal_search_inputs.py`, complete: `populate_infernal_search_sheet(artifacts, *, operation, sequence_metadata=None, model_metadata=None)` parses actual supported Infernal tblout dialects, table version/completeness, query/model identities and typed lengths. Its CM/HMM, bias, inclusion, pass, truncation and overlap fields are absent from current remote JSON. The actual `tblout` endpoint's bytes could later qualify for reuse; its name alone cannot.
- `infernal_search_grader.py`, complete: `calculate_infernal_search_scores(sheet, *, parameters=None)` expects its Infernal sheet and population `reported|included`. Its interval union/span/ratio mathematics can be reused semantically. Do not silently relabel remote JSON rows as included/reported native tblout records.
- `blast_pairwise_grader.py`, complete, including `alignment_components`: physical residue geometry and translation units differ from model-consensus displays and Infernal shorthand.
- `blast_database_grader.py`: sheet/calculation and dependency/function-weight sections read, including `build_database_sheet` and `calculate_database_probabilities`; not claimed a full-file reread. Source/identity association and explicit parameter patterns are useful; its candidate-function probability model is not justified for Rfam family-model scores.
- `infernal_native_result_views.py`, complete: explicit row/metric selection and measured/unavailable typed values are reusable interface ideas. Keep Rfam result family/version distinct.
- `native_infernal_returns.py`: initial custody/forwarding patterns inspected, not claimed complete. Rfam implementation must read all changed shared consumers before coding.
- `resource_tool_information.py`, complete, `tool_information.py` relevant declarations/catalog construction, `execution_contracts.py`, and exact relevant `ExecutionEpisodes`/`ExecutionTargetReader` consumers listed in CONTRACT section7: actual configured binding is separate from catalog/source aliases. Existing typed parent/child custody must carry any new numerical facts.

## Exact named tests read and what they do not prove

| Test file | Evidence preserved | Limitation / new required checks |
|---|---|---|
| `test_rfam_negotiation.py`, complete | Model download content negotiation, retained HTTP failure and broad Accept; no fabricated family from nonmodel content | Separate model-acquisition mode. Does not verify batch result API or grading |
| `test_rfam_identity_feedback.py`, complete | Distinguishes empty/missing/wrong/contradictory query identity; preserves known handle; recovery needs explicit action; failed action has no completed yield observation | Reads absent saved fixture directory. Synthetic identities remain useful contract cases, not native capture proof |
| `test_library_rfam.py`, complete | Two original reads share first-token name `same`, distinct headers `same first`/`same second`; selected member mapping and RNA view keep original scope and credit operands | Imports absent old native fixtures. Name or digest alone cannot join a future batch result |
| `test_rfam_discovery.py`, complete | Exact multipart, no uncertain repeated POST, handle URL custody, pending/hold/deletion, partial rows, source forwarding, original query scope | Tests explicitly encode multiple protocol polls as one hidden action; latest episode-ownership instructions override that behavior. Reverse synthetic hit copies a forward alignment, so scalar interval validity does not establish alignment consistency |

These tests were read, **not executed**. No passing-test claim is made. Files under the absent validation directories were searched for; they were not restored from any source, and documentation examples were not substituted under historical filenames. The inventory's existing absence warning is consistent with this inspection.

## Verification performed for this planning packet

The small local `verify_contract_examples.py` checks fixture provenance hashes, exact documented query/score/coordinates, independently calculates expected elementary arithmetic, and checks that each named synthetic mutation is what its manifest says. It is not a production parser, grader, service, or episode integration test. Its result is retained in `example-verification.json`.

All output files for this task are within `verification/tool_graders_rfam_contract_2026-10-26_232`. No current fixed row status or completion tally is changed by this planning record.
