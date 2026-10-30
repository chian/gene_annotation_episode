# Additive proposal changes before coding

No production coding is authorized by this packet. No original goal, fixed
scope/status row, approved historical design, production module or other agent's
file was edited. CONTRACT.md was a working planning draft, not goal authority.
The following review-driven clarifications supersede its earlier incomplete
interface sketches without changing the stated scientific scope or formulas.

The first reviewed schema/worked-record snapshot is preserved as
RECORD_SCHEMA_DRAFT_001.json and WORKED_RECORDS_DRAFT_001.json. Its document-only
validation reports are preserved as DOCUMENT_VALIDATION_001.json and
DOCUMENT_VALIDATION_JOB_001.json; the original document_validation_job directory
and logs remain in place. That snapshot passed 121-definition/60-record/9-negative
structural checks, but such checks did not expose the semantic interface gaps
that the parent review identified. Later document validation is separately run.

1. The initial extraction sketch exposed `raw_records`/array iterators for C3 to
   serialize. It left iterator consumption/failure timing unclear. Final native
   readers receive explicit output streams and NormalizationSpec, write bounded
   tables and return finalized metadata/TableDrafts only. C3 reads and seals one
   selected population before advancing, using the same immutable source bytes.
2. The initial TableDraft had shape/extent but no file and no explicit absence
   state. Final TableDraft/Descriptor adds availability and absence_reason. A
   present empty encoded array, unrequested weights, absent dense representation
   and a failed required table are distinct before capture.
3. The initial `ContactTables` JSON shape used full row lists while the proposed
   runtime promised memory mapping. Final JSON example records are explicitly
   named ContactTableFixture. The actual in-process ContactTables has fixed
   read-only NumPy arrays, dtypes, order and repeatable access, documented in
   RECORD_INTERFACES.pyi and RECORD_SHAPES.md. It is never whole-matrix prompt JSON.
4. The initial `read_chromatin_sheet_tables -> ContactTables` return lacked a
   mapping lifetime. It is now a standard ContextManager[ContactTables]; the
   loader owns mappings while the caller owns supplied stream lifetime.
5. Parent review found the initial build_chromatin_sheet signature circular:
   extraction metadata/descriptors did not supply raw bins/cells, yet the saved
   table loader required a sheet. The final lower-level
   open_chromatin_contact_tables(descriptors,streams) context manager is shared;
   build_chromatin_sheet receives table_views explicitly. C1 owns all three ports.
   C3 can build and calculate from one context over already retained tables.
6. The initial standalone calculator signatures omitted normalization, although
   saved recalculation could change it. Both standalone calculators now require
   that explicit keyword; the aggregate passes CalculationParameters unchanged.
7. Closed schema definitions replace prose-only native metadata, references,
   populations, components, selector rows and locator shapes. Units retain their
   actual source symbol separately from the closed dimensional kind. Supplied
   uncertainty is explicitly retained but unused. Undefined folds are counted
   separately from negative threshold flags through fold_defined_pair_count.
8. A failed header now permits null native metadata/version/storage facts. The
   selected parser format is not relabeled as an observed valid format. These
   nulls preserve the requirement that missing/malformed data cannot become zero.

Source repairs remain explicit and unchanged: no fabricated zero matrix, hidden
raw fallback, representative first chromosome, inferred whole-genome scope,
name-inferred biological class or dropped pair population. Source HIC support
remains absent; the independent HIC reader/fixtures and actual deployment remain
open. No HIC format variant or local runtime capability is added by data shapes.
