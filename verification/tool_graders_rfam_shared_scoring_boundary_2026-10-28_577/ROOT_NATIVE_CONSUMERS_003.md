# Root native consumer integration

Implementation detail for the accepted shared-scoring repair, not a goal or
scope amendment. HANDOFF.md and ROOT_IMPLEMENTATION_CONTRACT_002.md remain
unchanged. Root owns these edits and their tests.

The existing native publication path deliberately avoids hydrating complete
sheets or datasets on the host. Preserve that boundary. The existing bounded
native_infernal_result_worker parses captured bytes, calculates the common
sheet, validates the v2 saved score relationships, and selects requested rows.
The host retains and authenticates its artifacts and copies selected values.
Do not introduce a new full-sheet host read or a second calculation at return.

For each captured search tblout, the worker compares the actual byte hash and
size with the original bundle's output descriptor. A mismatch is a specific
reading failure and cannot become a verified source. A verified descriptor
carries the actual hash/size and captured artifact identity into the shared
sheet; text-only parser callers retain their unverified-byte distinction.
Search outputs use the new shared schema. cmalign remains unchanged.

The legacy tools.py::_publish_cmsearch path will parse its retained actual
format-3 table into that same sheet using the original selected sequence length
and CM header. It calculates once and retains the sheet/scores as source grading
artifacts. Existing CMSEARCH_MATCH fields are copied from the common native
cells and intervals. bitscore, evalue, query_start/query_end and query_coverage
come from the corresponding saved hit; query_coverage keeps its physical
sequence-span meaning. No ratio or span calculation remains in publication.
Original subject/model identity checks, strict observation fields, full raw
artifacts, the 12-row preview and completed-action accounting are preserved.
Malformed rows retain the common sheet and valid published siblings with
specific feedback. No native rerun is required to test this repair.

Verification uses actual retained cmsearch/cmscan bytes, saved recalculation,
tampered captured-byte rejection, equality of selected/published measurements
to common scores, and existing bounded native publication/replay checks.
Deliberately composed identities or malformed rows are labeled synthetic test
inputs. Tests run only through the existing bounded lifecycle. All historical
receipts remain unchanged; new checks do not claim a new live resource run.
