# Rfam retained publication verification — 239

This workload implements `gene_annotation_episode/rfam_batch_publication.py`,
its dedicated test file, and this new verification directory. Shared service,
input construction, table calculator/view and authenticated episode returns
belong to the root integration workload. No shared implementation or historical
capture was edited here. No new live Rfam request was sent.

The public exports are:

```python
publish_rfam_batch_result(tools, *, request, selector, snapshot, scope,
    operation_key, submission_snapshot, handle)
validate_rfam_metadata_source_scope(store, reference, scope)
```

It uses the existing service's local prepare/decode validation and the existing
`publish_existing_acquisition` operation receipt. Request, selector, original
handle and complete submission/response snapshot identities participate in the
replay operands. Exact replay returns the original outcome; a different selector
or submission cannot reuse its operation key.

The publisher creates three source roles: original submission, exact native
result bytes, and an acyclic `rfam_batch.grading` source. The latter's closed
manifest retains the full parser outcome, full numerical sheet and separate
calculation as actual artifact references, plus the requested projection. A
selected metadata source is read explicitly and its named source/artifact
relationships checked. The pure source-scope validator reads records only and
checks operand and original-read-selection roots through transitive source
parents; Store source roots alone do not carry those relationships. Only a
selected source passing this check joins
grading lineage. Unknown or out-of-scope references remain in the saved selector
and diagnostics, and their artifact bytes are not read. A validated selected
source with an invalid or unreadable bundle stays in lineage with its failure.
Neither case suppresses independent native scores or query spans. Requested
model-dependent quantities return `model_metadata_conflict`; valid unbound
metadata still supplies no denominator.

For JSON, a metadata issue with field `model_metadata_ref` explicitly identifies
an omitted selected parent; field `model_metadata` identifies a validated source
whose metadata failed. The closed table wrapper uses code
`rfam_batch_model_metadata_invalid` and the corresponding fields
`model_metadata_ref` or `supplied_model_metadata`. These diagnostics preserve the
closed manifest and are distinct from projection-delivery failures.

JSON correspondence is parsed at exact validated native row pointers. Batch
tables use the existing pure table adapter and the root's additive
`rfam_batch_table_calculation_v1` wrapper, which contains the unchanged full
Infernal calculation. The shared view only selects saved fields. The additive
clarification in `PUBLICATION_WORKLOAD_003.md` supersedes its earlier direct
Infernal calculation storage sentence.

The returned result has exactly source_ref, submission_source_ref, artifact_ref,
format, sheet_ref, calculation_ref, projection, projection_errors and
grading_source_ref. `record_refs` contains the three actual source records;
artifact identifiers are not passed off as source records. No observation,
family reference, taxon, function, provider-job record, model call, episode,
turn, scientific credit or continuation rule is created by publication.

## Executed verification

`tests_005/verification-receipt.json` records **39 passed in 120.10 seconds**.
The existing bounded runner enforced 20 GiB RAM and 4 GiB scratch with no wall
limit. This timing describes local verification, not remote Rfam execution.
Its measured service-wall duration was 120.844129743 seconds and observed
scratch usage was 15,286,272 bytes. After adding the final original-read-selection
root check, `tests_006` passed its new Store test and the two direct/transitive
out-of-scope publication tests: **3 passed, 37 deselected in 6.23 seconds**.

The suite forbids network sockets, subprocess creation and sleeps. It exercises
actual Store records and artifacts, service input preparation/decoding, exact
source lineage, selector-bound replay, saved-Store reopening and offline
recalculation. Cases include:

- Unchanged retained native single JSON, scores, query-span arithmetic,
  alignment correspondence and unavailable full-model coverage.
- Original submission/result query, job and URL conflicts; malformed JSON,
  duplicate JSON keys, empty query, complete zero-hit output, repeated rows and
  selected rows smaller than the fully saved population.
- Invalid optional numerical/alignment cells and partial populations delivered
  as accurate unavailable/qualified values; incomplete acquisition and invalid
  requested keys retained as specific partial outcomes.
- Selected metadata source custody; missing, malformed, unreadable and
  out-of-scope metadata while preserving native cells; direct and inherited
  scope checks with prohibited out-of-scope byte reads; artifact-only
  table/report acquisition; and non-200 retention without a scientific sheet.
- Synthetic generated-name batch inputs, six native-format rows and a seventh
  distinct selected no-hit occurrence; both strands, reverse coordinates,
  complete-zero populations, absent closure, interrupted bodies, wrong native
  job/version, wrong submitted bytes and unsupported unattributable batch JSON.

`tests_001` is preserved: 15 passed and 6 failed because source-count assertions
omitted the Store's pre-existing input source. The tests were corrected to
measure the actual baseline; production code did not change for those failures.
`tests_002` then passed all 28 tests. The two additional persistence/complete-zero
tests are included in the 30-test `tests_003` checkpoint. Metadata preservation
and scope cases passed in `tests_004` (37 tests); malformed inner metadata
records for JSON and tables are included in the 39-test `tests_005` run. Every
receipt and the original Store artifacts remain available.

## Filled examples and provenance

`examples_003/examples/` exports full outcomes, manifests, parser records,
sheets, calculations, original submission/result bytes, source records and
request/transport artifacts from the completed `tests_005` Stores. `examples.json` records
their qualification and SHA256 values. The exporter reads SQLite in read-only
mode, verifies artifact hashes, and forbids acquisition/execution. Its bounded
run completed successfully. The earlier `examples_001` failed on an overly long
pytest directory-name pattern before exporting any example; that receipt is
preserved and the pattern was corrected.
The earlier successful `examples_002` export remains unchanged.

| Example | Native/fixture identity | Checkable numerical results |
| --- | --- | --- |
| `single_native` | Unchanged transport234 single submission/result bytes with fresh local scoped input bindings; no new HTTP request | 104.6 bits, E=1.4e-24, native GC=0.49, span 119/119, 120 represented model positions, 75 equal / 118 compared canonical pairs = 0.635593220338983, one query insertion, two model deletions |
| `batch_synthetic` | Native table numerical values retained, with explicitly synthetic generated query names and synthetic job identity | Six rows with bit scores 104.6, 104.6, 104.6, 51.3, 95.5, 95.2; each query-span fraction 1; seven input occurrences remain distinct |
| `batch_zero_synthetic` | All hit rows deliberately removed from a complete synthetic table | Zero retained hits; seven original input occurrences and fourteen query/strand rows with measured zero reported spans |

Full model length and model coverage remain unavailable in all three examples.
The native displayed endpoint 120 is never treated as the full model length.
No quantity is described as annotation probability or independent evidence.

The original multi capture has `rfam_example_*` query names and a different file
contract. It was not relabelled as a live v2 generated-header service submission.
Worker238 independently verifies that unchanged native table and its original
mapping. This publisher's new generated-header batch service path is verified
with explicitly qualified synthetic responses.

## Verification limits

These results establish the supplied-artifact publication path, not an actual
new selected HTTP submission, a configured-model episode, or the complete
authenticated child-to-parent return/credit/continuation path. Root owns those
shared checks. The whole Rfam fixed goal row is not declared complete here.

Batch JSON stays fully retained and unattributed; a numerical request returns
its specific unsupported reason rather than joining hit order to inputs.
Single unheaded tblout remains artifact-only until its original query-name
mapping is source-qualified. Reports remain separate artifacts; no report text
is fabricated into JSON alignment pointers. Original model release/digest and
full model lengths remain unknown.

The entire authoritative goal and AGENTS.md were read before coding. Its
objective and all sixteen original principles were reread verbatim after native
study and at closure, followed by the complete original Rfam contract, native
batch contract and current additive publication/batch contracts. No literature,
W05, HPC, local database BLAST, new policy gate or fixed wall-time cap was added.
