# BV-BRC v2 host custody and replay verification

This directory records the focused host tests implemented in
`tests/test_bvbrc_data_recovery.py` with the exclusive helper
`tests/bvbrc_host_fixture.py`.

The fixture uses actual `EpisodeRef(run_id, path)` identities, complete
`EpisodeRequest` and `ReportContract` records, exact selected Journal actions,
`APIServiceExecution`, `BVBRCDataService`, native readers/calculators, retained
artifacts and the host's own qualification/admission methods. The launch API
owner is structurally below a launch child. Transport returns controlled
`SourceSnapshot` bytes; no `QualifiedResult` or qualification flag is fabricated.

This is engineering verification with synthetic responses and selected Journal
records. It does not run Workflow or a model and does not prove live API
deployment, native biological measurements, scientific annotation, or the
complete parent model-input path. Those remain separately accountable. Network
access is forbidden in every test. Saved-data replay additionally forbids query
compilation, numerical calculators, transport and subprocess execution.

The supplied-metadata cases retain a deliberately synthetic extra JSON envelope
member so their source bytes are acquired and admitted through the real host.
They do not claim this member is part of the deployed Solr response. Exact JSON
Pointer values, Unicode hashes, provenance exclusion, nulls and empty containers
are then checked against that received source.

Coverage includes persisted preparation and complete grading; interrupted
launch/results decode, pre-publication and saved-publication recovery; source,
raw, grading, selector, request, action, and input custody; run/scope/receiver
possession; exact successful original child returns; explicit shared-sequence
joins; supplied molecular metadata; and separate acquisition identity/credit.
Two feature identities sharing one native sequence remain two feature rows.
Different local projections of the same acquired bytes earn zero new acquired
record credit; one explicitly changed page earns one acquisition unit.

Two production defects were reported to the production owner and fixed there:

1. `read_result` compared the plain receipt selector directly to frozen
   `BindingContext` tuples. The v2 selector arrays caused a false
   `api_result_acquisition_receipt_conflict`.
2. The admission source walker recognized `reference` but omitted the existing
   `identifier` reference format used by BV-BRC facts. Page-only returns then
   recorded no received source and later explicit joins failed with
   `bvbrc_host_reference_not_received`.

Fixture corrections (not production defects) included supplying the required
action column to Journal's upsert, using `PageComponents.native_row_count`, and
retaining the durable JSON newline in deliberate semantic-tamper fixtures.

`pytest.log` and `pytest.xml` contain the final full focused run. `REPORT.json`
records its exit status, case count, source hashes and explicit limits.
