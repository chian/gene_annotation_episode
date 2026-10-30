# BV-BRC Data v2 service dispatch and publication

Bounded D6a implementation, 2026-10-24. This evidence does not declare section D
or the complete episode integration finished. The original user goal, frozen
contract and additive corrections remain authoritative.

Owned implementation files:

- `gene_annotation_episode/api_bvbrc.py`: explicit legacy/v2 dispatch, nested
  self-contained request/selector schemas, declared operations, persisted
  `prepared_query`, original native-request cache selection, v2 native decode,
  and the optional `publication_inputs` handoff.
- `gene_annotation_episode/bvbrc_data_publication.py`: exact supplied-input
  validation, D2/D3/D4 composition, complete grading retention, one external
  source, and pure requested-projection endpoint qualification.
- `tests/test_api_bvbrc_data_v2.py`: 52 service/publication checks, including
  22 collections with all three modes and direct pure D5 consumer conformance.

`BVBRCDataClient.query_prepared` was already provided by the integration owner.
Its one-GET transport and the legacy implementation were preserved. No host,
runtime, prompt, information-library, annotation-score or accounting file was
edited by this workload. No network request, live job or model call was run.

## Exact handoff

The prepared command retains `operation`, `mutates_remote=False`, and the
effective `request`. V2 additionally contains the exact D1 `prepared_query`.
Results preparation adds `cache_original` based only on equality of the actual
native request. Local projection/input selection does not trigger another GET.
An explicitly changed row window does.

V2 `publish(..., publication_inputs=...)` requires the exact `PublicationInputs`
record. The host owns its original receipt, scope, byte custody and actual
receiver-possession qualification. This publisher verifies explicit relationships
but does not claim that schema-valid JSON establishes host authorization. It does
not search Store or reopen input sources. The saved prepared record is consumed
without compiling the original request again.

The returned `result` has exactly:

`source_ref`, `raw_artifact_ref`, `grading_artifact_ref`, `collection`, `mode`,
`parse_status`, `qualification`, `requested_projection_complete`,
`projection_failures`.

The source's `artifact_ref` is the exact response bytes. Its `request_ref`
retains the complete snapshot metadata, native transport/request and persisted
preparation. Its `auxiliary_artifact_refs` links the `retain_tool_grading`
envelope with provider `bvbrc_data`. The enclosed exact `PublishedGrading` has no
self source reference. All original rows, supplied bindings, selected join and
all seven molecular measurement slots survive independently of a smaller view.

`requested_projection_failures(grading, *, input_results)` is a pure helper for
the host's endpoint check. It returns exact closed Issue records. Native absence,
unselected fields, unavailable join inputs and reported zero are valid typed
answers. Malformed requested values, contradictory selected relationships and
incomplete bytes remain partial. Unrelated unrequested native field errors stay
in the full sheet without invalidating a narrower requested projection.
`parse_status` and requested endpoint status therefore remain distinct.

A partial native sheet can provide a usable immediate-response handoff; event
state `completed` describes the completed native operation, with its partial
parse status explicit. A wholly unparseable launch response provides no handoff.
A results response with no sheet retains its failure bytes and failed grading
with outer `status=partial`. No remote job/status or scientific score is added.

## Verification actually performed

The final captured command was:

```text
.venv/bin/python -m pytest -q tests/test_api_bvbrc_data_v2.py tests/test_api_bvbrc.py tests/test_bvbrc_data_transport.py
88 passed in 46.99s
```

`TEST_RUN.json` contains the command, timestamps, exit status, log and matching
before/after SHA-256 values for the nine affected implementation/test consumers.
`pytest_service_publication.txt` preserves the actual output. Earlier overlapping
runs were 36 passed in 1.53s, 45 passed in 36.13s, and six focused checks passed in
9.09s. These are overlapping checks, not additional unique test coverage. No
pytest run in this workload failed. An attempted read-only `git diff --stat`
returned exit 129 because this directory is not a Git repository; no change or
test result is inferred from that command.

Checks cover actual nested `APIServiceExecution.assignment_schema` validation;
operation declarations on an unconstructed service; version separation; one
native GET; original-page reuse; one explicit changed-page request; complete
raw-byte custody; one source without target observations/assessments; repeat
content identity; exact frozen grading shape; native zero and unavailable states;
malformed field, population, facet, JSON, media, HTTP and partial-body cases;
selection/input/binding mismatches; and saved calculations with transport and
query compilation unavailable. Store source-search and input-source lookup are
forbidden during the tested feature publication.

The final source-stable run includes correction003's explicit unavailable page
and facet returns through the D5 consumer. It distinguishes those returns from a
successful zero result and from an actual native null-term/missing-field bucket.
Direct D5 tests use clearly labeled host-qualification fixtures, not a real host
admission or episode communication run.

Filled examples were generated with:

```text
.venv/bin/python verification/tool_graders_bvbrc_service_publication_2026-10-24/verify_examples.py
```

The script completed successfully with network entry points disabled. The
`example_store` directory retains its actual local source/grading artifacts.
`FILLED_EXAMPLES.json` and the four `*_grading.json` files retain production
publication results. They are local engineering examples: count/facet use
unchanged historical Solr bytes with synthetic v2 transport bindings;
feature/molecular joins use historical native row values reserialized into
synthetic Solr envelopes and explicit fixture input bindings.

Concrete numbers:

- Native count: 2 matching documents and zero requested document rows.
- Facets: numerator 1 / denominator 2 = 0.5 for each of PATRIC and RefSeq;
  the native null-term bucket has numerator 0 and fraction 0.0.
- Feature sequences: two distinct feature documents, four AA/NA relations,
  one distinct AA sequence of length 253, one distinct NA sequence of length
  762, and four native length agreements. This does not imply four independent
  biological observations.
- Molecular rows retain `log2_fc=-0.132,-0.129` and
  `z_score=-0.544,-0.556`. Their other five measurement slots remain missing.
  A separately labeled synthetic test retains fractional signed counts `-1.25`
  and directly materializes the explicit supplied unit `reported intensity µmol`
  from its actual metadata source pointer, without selecting extra metadata.

## Remaining D6 work

The integration owner must finish actual host construction/revalidation and
freezing of `PublicationInputs`; original receipt and result qualification;
same-native-acquisition credit identity across local re-projections; completion
qualification with the ordinary immediate zero-future controller path; incoming
child-return admission and reference resolution; interrupted replay; actual
parent and results-child selected-value insertion in saved provider requests;
and resource-bound tool information. Source bytes, same-scope visibility,
provider labels and fixture qualification flags alone establish none of those.
No current live access, new v2 service deployment or configured-model scientific
investigation is claimed.
