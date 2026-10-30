# Rfam source custody and typed episode returns

Fresh worker owns only `gene_annotation_episode/rfam_batch_returns.py`,
`tests/test_rfam_batch_returns.py`, and new verification ending 240. Root owns
all shared integration and table numerical modules. Publisher239 owns the
publication writer and its tests. Read its exact PUBLICATION_WORKLOAD_003.md
contract and current module, original goal, AGENTS and full common
EpisodeReturnRecords implementation. Read existing native Infernal and Homology
returns for the design; do not assume Rfam uses AppService custody or imports
its service-specific record formats.

Implement `RfamBatchReturns(execution)` where execution is APIServiceExecution:
`read(reference, scope, *, episode_id=None)`, `facts(context, schema)`,
`received_facts(context, schema)`, `resolve_own(context, reference, namespace)`,
`resolve_received(context, reference, namespace)`,
`validate_received_report(context, form, schema)`, and
`record_admission(context, form, schema, operation_key)` with the established
EpisodeReturnRecords meanings. Root wires them into the existing API and
ExecutionEpisodes owners. Do not create a new episode, database or model call.

read must call existing APIServiceExecution.read_result to prove original
action/receipt/response custody, then validate the result's grading source and
manifest against the original publication, submission snapshot/native handle,
scope, assigned request and exact selector. Root will add `publication_result`
to read_result's returned body: an exact deep copy of saved outcome['result'].
This enables proof without finding arbitrary source records. Require raw source
artifact equals original snapshot, submission source equals retained original
submission, grading source provider rfam_batch.grading and origin tool with
result/submission parents. Full parse, sheet and calculator artifacts must match
their retained hashes and declared schemas/bindings. Read canonical JSON and
validate relationships; do not recalculate scientific quantities. The table
calculation wrapper is rfam_batch_table_calculation_v1, with sheet_digest,
parse_digest, explicit parameters, unchanged native_calculation, common hit
metrics, query_strands and population_complete. JSON uses its existing format.
No sources found by scanning provider names or guessed IDs are authorized.

Expose TWO fact sources via `rfam_fact_sources()` and FACT_SOURCES:

1. `rfam_result_rows`: array of closed records
   {source_ref, record_key, query_occurrence_key, family_accession, strand,
    measured, unavailable, population_complete}.
   These copy ONLY the rows in the original saved projection, with its
   population_complete flag. measured/unavailable use the existing closed
   Rfam metric/unit/reason lists. A foreign/unbound table row has nullable
   query_occurrence_key and no attributed measurements; keep its unavailable
   identity_rejected cells. Never manufacture an original input key.
2. `rfam_result_populations`: array of closed records
   {source_ref, family, available_row_count, selected_row_count, more_rows,
    population_complete}, copied from the same projection. A complete zero-row
   result can therefore return its zero population without inventing a hit.

source_ref is the original native source in execution_result namespace.
record_key, query_occurrence_key and family_accession are format=identifier in
namespaces rfam_record, rfam_query and rfam_family, respectively; the latter
two allow null for explicit missing associations. Resolve them only against
the actually available own projection or values received through an admitted
child form. Strand is +|-|null. Native family accession is an entity label,
not an annotation probability. Metrics/reasons/units are enums, not free prose.
Parent schema x-source selects which fact families it receives; neither source
access nor a source ref in a different form authorizes expanding the projection.

Authenticate original commissions, child scopes, frozen forms, selected actions,
admission and forwarding using existing EpisodeReturnRecords. Reject forged
values, wrong source/query/metric associations, omitted/expanded rows, changed
selector, unreceived values and unsupported owner roles. No full sheet, native
report or source text appears in facts. Returning data does not create new
scientific observations or formula changes. Preserve exact original forms and
no automatic source widening on later requests.

Test the read against publisher239 artifacts/real Store and actual generic API
receipt where practical; pure supplied-record cases cannot establish custody.
Test results->scientific_process->annotation, restrictive original requested
forms, missing/empty/partial cells, forged metadata/refs/numbers, wrong child,
replay with unchanged observations and no network/calculation on return.
Report exact coverage and unfinished full Workflow proof. Use the established
bounded runner 20GiB RAM/4GiB scratch/no wall cap. No new live requests.
Reread the immutable goal objective and all sixteen principles verbatim after
substantial outside/native study and at closure, then these exact interfaces.
