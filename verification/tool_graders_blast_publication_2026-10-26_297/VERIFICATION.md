# Workload 297: retained paired BLAST publication

Implemented contracts 007 and 009 for blastn, blastp, blastx, tblastn and
tblastx pairwise results: reusable numerical fields and reader/calculator
functions, storage of complete scoring sheets/calculations, and delivery of
requested numerical results with frozen validation. Filled sheets are
verification examples. Workload 298 owns selected Workflow execution, result action
receipts and authenticated immediate-child/ancestor communication.

## Implemented ports and custody

- `blast_pairwise_result_views.py`: exact selector, the two closed numerical
  row schemas, family metric enumerations and x-source definitions. Original
  artifact keys and search pointers use the bounded-return identifier namespaces
  `native_blast_artifact_key` and `native_blast_search_pointer`; the consuming
  result adapter authenticates their exact selected/received values.
- `prepare_native_blast_grading`: qualifies the captured original manifest and
  each retained artifact digest/length, snapshots actual Store sequence identity,
  and invokes the deterministic worker under the supplied LocalJobPolicy.
  Completed preparation replays its original artifacts. Interrupted preparation
  and changed/lost retained bytes are explicit failures, not retries.
- `native_blast_result_worker.py`: constructs the 293 invocation from the
  original selected job and parsed captured FASTA records, calls the 294 sheet
  population and calculator separately for each search, and retains the complete
  collection, sheets, components, native ordinal maps and diagnostics. Traceback
  symbols are checked against actual full operands, with original orientation,
  selected intervals and genetic codes for translated axes.
- `publish_selected_native_blast_rows`: requalifies frozen source/prepared/row
  custody and actual Store sequence/scope bindings. Each genuine selected HSP
  creates at most one stable comparison observation containing all available HSP
  components. Metric/page selection changes neither that record nor its original
  source. An absent supplied reference can be created from actual captured FASTA
  identity and complete sequence, never from length alone.
- `validate_native_blast_publication`: checks frozen selected rows, complete
  observation payloads and exact reference records without Store publication,
  scientific parsing, recalculation, process launch or producer-path access.
- `domain.py` and the narrow `Store._validate_record` branch: new tool metric
  names and the host-only `native_blast_pairwise` marker, excluded from reasoning
  inputs. Store requires actual tool/source origin, provider/version, comparison
  kind, exact bundle artifact and matching original selected program/pairwise
  mode; the API-only native BLAST marker cannot coexist.

Union rows have null observation references. Their record_refs contain only the
original source, even when the row identifies an actual source reference.
Repeated/overlapping mappings remain explicit diagnostics; they do not create
another scientific observation or a confidence score. A conflicting aggregate
identity stays unavailable. Valid requested HSP numbers and observed union counts
can be numerically complete despite alternative mappings; requesting the missing
aggregate identity explicitly reports unavailable calculations. No scientific
acceptance threshold or credit formula was introduced.

## Artifact shapes

The exact public prepared record is the 007 shape. Its source grading artifact
is selector independent and retains `sheet_artifact_ref`, `scores_artifact_ref`,
`complete_rows_artifact_ref`, both actual normalized sequence artifact references,
and exact captured artifact identities. The selected grading artifact adds the
exact selector, selected rows artifact, failures, completeness and worker receipt.

`sheet.json` is `native_blast_sheet_collection_v1` with the complete 293
collection, per-search 294 sheets or explicit failures, and actual publication
inputs. `scores.json` is `native_blast_scores_collection_v1` with per-search
294 components, complete HSP/union scalar rows and concrete metric definitions.
`complete-rows.ndjson` retains complete frozen row values/bindings/intervals in
original order. `selected-rows.ndjson` contains only selected identities and
requested scalar values/missingness. Full native files, original JSON numerical
precision and original tabular lexemes remain retained independently.

## Verification evidence

All tests and deterministic workers used `.venv/bin/python` through `local_jobs`
with 20 GiB RAM, 4 GiB scratch and no wall cap. No native search, network request,
new installation, database search, HPC job or model call was performed by this
workload. The twenty unchanged reports were produced by workload 294's actual
native programs. Tests explicitly rebind placeholder Store handles in copied
manifests; this is not claimed as another native run or lifecycle proof.

| Run | Outcome | Scope |
| --- | --- | --- |
| check001 | 65 passed, 4 failed, 163.66 s | Initial retained evidence; failures were two genuine zero-hit fixtures misclassified by name, full reference length 190 confused with 160 covered positions, and an incorrect synthetic native failure code. |
| check002 | 75 passed, 363.49 s | All twenty native cases, exact numerical answers, closed row schemas, paging/metric identity, union behavior, sequence/scope/traceback custody, malformed HSP siblings, native/missing report failures, replay and Store marker checks. |
| check003 | 1 passed, 75 deselected, 6.08 s | Added malformed `hits: null` search followed by a surviving valid original search and exact pointer. |
| check004 | 23 passed, 55 deselected, 104.42 s | All twenty native cases, paging, and two targeted checks confirming alternative union mappings do not invalidate available requested numbers. |

These runs overlap; their pass counts are not additive. Every current test in
the two owned files has passed in a full or applicable focused run. Earlier
receipts, artifacts and their original completeness values remain unchanged.
`FINAL_FILLED_EXAMPLES.json` reflects check004; the earlier
`FILLED_EXAMPLES.json` preserves check002. `FINAL_SOURCE_HASHES.json` records
the final seven production/test file hashes; earlier hashes are preserved.

Saved-sheet recalculation and frozen-publication replay were tested with network
and process construction blocked. Recalculation additionally blocks file reads;
frozen validation blocks Store.put and Store.artifact. Exact source/query/value/
observation/interval mutations are rejected. Same-length wrong query/reference
sequences remain invalid while surviving native numerical measurements remain
visible. Native failure, malformed output, missing capture and zero results stay
distinct. Full producer arrays and ordinal maps are retained for invalid siblings.

## Concrete native numbers

| Retained case | Numerical answer |
| --- | --- |
| blastp gaps JSON15 | 253 columns, 243 paired positions, 238 identities, 5 substitutions, 10 reference gap columns; query coverage 243/253; reference coverage 243/243; paired identity 238/243; bit score 486.878, raw score 1252, E-value 0. |
| blastx reverse JSON15 | 80 amino-acid pairs cover 240/244 query nt and 80/80 reference aa; native bit score 170.629. |
| tblastn reverse JSON15 | 80 amino-acid pairs cover 80/80 query aa and 240/243 reference nt; native bit score 170.629. |
| tblastx frames JSON15 | First HSP covers 240/243 nt on each operand with 80 pairs and bit score 200.846. All 10 HSPs remain retained; the observed union covers 242/243 nt on each operand with 411 distinct pairs, 2953 explicit conflict-list entries, and unavailable aggregate paired identity. |
| blastn selected forward | 180 paired nt; full query/reference denominators 240/240 give 0.75 each; selected denominators 180/210 give 1 and 180/210 respectively. |
| blastp multiple HSPs | Two 80-position HSPs; union covers 80/80 query positions and 160/190 reference positions, with 80 alternative mapping entries. Aggregate paired identity remains unavailable. |

Native tabular precision remains its actual reported precision (for example,
BLASTX JSON 170.629 bits versus table 170), without altering either representation.
The JSON15 no-hit example has zero observed pairs and zero selected coverage.
An empty tabular6 report has unavailable observed counts, not successful zeros.

No claim is made here about complete episode communication, API/HPC deployment,
database identification, other BLAST programs, literature grading, W05 or
configured-model annotation benefit. Those are separate owned work.
