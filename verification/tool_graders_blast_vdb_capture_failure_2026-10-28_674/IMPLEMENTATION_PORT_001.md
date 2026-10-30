# Return retained VDB artifacts when selected input qualification fails

This is a concrete repair of the668/669 missing-input boundary, not a goal or
scope change. Root owns the changes below. Existing operation counts do not
increase. No prompt, new episode, numerical grader, retry or acquisition is added.

## Demonstrated failure and preserved paths

With a missing selected metadata document, database-side list or operation input,
qualified_utility_context raises native_blast_utility_input_population_unavailable
before the original result worker starts. Results currently keeps the actual
capture but emits only a generic failure. Requested available stdout/stderr and
other original artifacts do not reach the parent. Existing successful, parsed
partial, prepared-without-result, legacy and later explicit-repair paths remain
unchanged. Invalid/corrupt capture or a different error does not enter this repair.

## Interfaces

Factor the existing worker's occurrence/outcome/failure reconstruction without
duplicating it. Add captured_utility_observations(capture: dict) -> dict containing
exactly operation, native_outcome, occurrences and failures. Its input remains the
closed validated capture; all selected-file association, ordinal, bundle identity
and failure checks still execute. It does not invent database/member/sample/
metadata context. qualified_utility_context retains its existing full signature,
validation and result for all successful callers.

Add native_blast_utility_capture_failure.py with a closed immutable record:
version=native_blast_utility_capture_failure_publication_v1, capture_sha256,
source_ref, selector, operational_failures, qualification_failure and projection.
It contains only a projection of actual captured facts and explicit unavailable
requests, never a parsed result or prepared-worker receipt. Public functions:

publish_capture_failure(store, *, capture, selector, operational_failures,
                        directory) -> dict
validate_capture_failure(store, *, capture, selector, operational_failures,
                         publication) -> dict

The functions authenticate the original retained capture through _validate_saved,
require operation-v3 and the exact missing-population qualification error, reuse
captured_utility_observations, and call the existing common projector with
result=None, prepared_database=None, context=None and saved_data=[]. The returned
publication binds the original capture digest, source, selector and operational
failure list. Validation compares exact canonical representations and the closed
original projection. It runs no native-result parser or calculator, creates no
worker, reads no original filesystem input and acquires no data.

When full metadata qualification is unavailable, a database-side list's artifact
grant cannot rely on unqualified database-membership context. Only the original
operation's explicit dbs_file list occurrence remains eligible as database_list.
Other database_list occurrences stay in the retained original capture but are
omitted from the available occurrences supplied to this failure-only projection.
An explicitly requested unavailable list therefore returns artifact_unavailable;
other requested captured artifacts still return. No source ID or nested metadata
automatically grants bytes. This is availability for the authenticated requested
return, not a claim that the retained file was physically deleted.

Keep this failure publication in capture-failure-publication.json beside the
existing selected-action receipt. Do not alter acquired-v1/v2 field sets or add
keys to old bodies. The existing prepared and publication types stay unchanged.

## Consumers and continuation

NativeBLASTUtilityResults.execute uses this route only when original preparation
fails with the exact missing-population ContractError and prepared is None. It
records the real diagnostic and operational failure first, then copies the
common projection fields. Failure-publication failure remains a separate
structured projection failure; it does not retry the native job or parsing.

_validate_body recognizes only the new immutable failure record, requires the
original collect, null prepared, same captured source/selector/diagnostics and
exact projected fields. Old receipts without that file follow their original
validation. Existing facts, received forms, shallow artifact grants and byte
access checks consume the same closed fields. A failure does not satisfy practical
completion. Acquisition credit still refers to the one actually acquired source;
same-key replay and a separately selected later collect preserve original
history and add no synthetic observation or reacquisition.

## Verification

Root owns new tests/test_blast_vdb_capture_failure_674.py and this evidence dir;
reserve bounded529 check132_vdb_capture_failure674 with suffixed attempts. Test
missing metadata, entry_batch, dbs_file and selected dependency-list cases; keep
present safe bytes and explicit missing selections. Reject other errors, invalid
captures, source/selector/digest/failure/projection tampering, invented rows and
unselected artifact grants. Include successful full-context regression cases and
old unchanged result shapes.

Exercise selected collect through real result provider, saved receipt validation,
deterministic facts, original immediate-parent form admission, explicit byte
grants, unchanged same-key replay and separately selected capture reuse. Controlled
native fixtures are labeled; this is not authentic helper execution. Run no
native output parser/worker on this route. All imports/tests/Store and content
work stay in bounded529,20GiB RAM/4GiB scratch/zero swap/no wall cap, explicit
check005 dependencies. Preserve failures and original handles. Read complete
affected consumers; reread the original user attachment objective and entire
OPERATING PRINCIPLES after each tool/substantial native reading and this port
before claiming completion.
