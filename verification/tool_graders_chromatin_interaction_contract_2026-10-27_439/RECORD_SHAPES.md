# Additive interface freeze for packet 439

This is an additive clarification of the planning proposal, not production code
or goal authority. The original attachment and explicit user instructions retain
authority. CONTRACT.md records the source examination and numerical meanings;
the closed [RECORD_SCHEMA.json](RECORD_SCHEMA.json) and
[RECORD_INTERFACES.pyi](RECORD_INTERFACES.pyi) fix the shared data and function
interfaces where that draft was incomplete. No production module reads these
verification files. Earlier proposed signatures are recorded in
[DRAFT_CHANGE_RECORD.md](DRAFT_CHANGE_RECORD.md), not silently treated as settled.

The schema has closed definitions for every nested JSON record, including
native metadata, reference/sample associations, population extent evidence,
table drafts/descriptors, element and pair rows, each calculator's components,
each selector/projection union, located failures, original producer records,
capture and worker handoffs. Formula implementations remain ordinary functions;
the schema does not encode executable scoring rules. All fields are required
unless the particular closed union or explicitly optional projection field map
says otherwise. Nullability is explicit. Arrays retain their declared order;
unique foreign keys and cross-record relations below require ordinary validators.

`validate_chromatin_record(kind,value)` accepts exactly the named scientific or
execution definitions in RECORD_SCHEMA.json, not arbitrary schema input. Existing
byte-to-JSON entry points in the worker/contracts decoding reject duplicate keys
before passing decoded objects; the object validator cannot recover keys already
lost during decoding. Validators reject nonfinite numbers, bool-as-integer values
and unknown fields before validating scientific relationships. No reference
resolution uses a network or unprovided file. A schema-valid fixture is not
native-format evidence, an authorized artifact or a successful execution.

## Finalized native extraction and output-role state

The two native readers take a read-only supplied seekable input stream, explicit
ContactSpec and NormalizationSpec, the exact selected populations and a mapping
from `(population_key,role)` to caller-opened writable seekable output streams.
No lazy iterator crosses their return boundary. They write the fixed table
encodings and return only finalized ContactExtraction metadata/TableDrafts.
Those records contain no Store-created output identities. Normalization is an
explicit argument so the reader knows which supplied vector to retain; it never
chooses another column or silently substitutes raw values.

Reader-return success is not matrix completeness. The returned per-population
extent/read evidence and failures describe the actual reads. If header decoding
fails, `native_metadata=null`, `format_version=null` and no chromosome rows are
asserted. `format` then records the caller-selected parser format only. Native
storage mode/bin counts remain null when unobserved. An empty chromosome list
with unavailable metadata means no chromosome metadata was decoded, never a
genome with zero chromosomes. Valid earlier populations retain their actual
metadata and arrays even if another population is unreadable.

TableDraft and TableDescriptor both have explicit `availability`:

| availability | Exact meaning and required fields |
| --- | --- |
| `present` | A syntactically complete retained table encoding exists. Encoding, shape, dtype and row_count are nonnull, absence_reason=null. Its scientific extent can still be partial. In TableDescriptor the file identity is nonnull. |
| `not_requested` | No table was produced because the selected request did not request it, such as weights in a raw-only extraction. File/encoding/shape/dtype/row_count are null; absence_reason=null; extent=unavailable. |
| `not_native_representation` | No such representation exists for this extraction, such as a whole dense array for a sparse Cooler population. The same null fields are required; absence_reason=null. |
| `unavailable` | A required table could not be produced. The same null fields are required and absence_reason is a specific Failure code. |

A present contacts or cell-states array with `shape=[0]` and `row_count=0` is a
real empty NPY with a header. It is not an absent role or a zero-byte pretend
NPY. Present empty contacts imply a zero contact matrix only when native axes,
indexes and selected-region read evidence independently establish complete
sparse absence. Failed partial NPY bytes may be retained as diagnostics, but are
not admitted as present numerical tables. The exact five roles occur once per
selected population, including absent roles; their keys are stable and unique.

C3 calls the native reader with **one selected population per call**, in the
already frozen order. It uses the same pinned original input inode/bytes. After
the reader returns, C3 flushes/closes that population's output streams, hashes
the actual outputs, writes its population seal and closes the seal before
advancing. Thus a later interruption can preserve a genuinely sealed earlier
population. The finite loop cannot choose new populations, retries or resources.
Parsing seeks or repeat scans of the same immutable supplied bytes are allowed;
reopening a mutable original source path is not. Every population remains part
of the original selected operation, not an extra episode action or observation.

The final batch extraction merges these finalized records without independently
sorting parallel lists: header/chromosome assertions must agree exactly; each
population retains its exact key, descriptors, normalization and source row
locators. A mismatch is a located failure, not a chosen representative header.
No extra merge API is required. C3 assembles the declared closed record. The
original full container and BED remain retained, independently of table output.

## Noncircular sheet construction and exact in-process array interface

The actual in-process ContactTables type is fixed in RECORD_INTERFACES.pyi.
It is **not** the nested row lists in the example JSON. Its version is
`chromatin_contact_arrays_v1`; `populations` is a read-only mapping keyed by the
exact population keys. Each value has exactly `population_key`, `bins`,
`contacts`, `weights`, `cell_states`, `dense_values`. Nonnull values are NumPy
ndarrays with `flags.writeable=False`, backed by read-only memory maps for large
binary tables. `None` corresponds to an absent/unavailable role, never an empty
array. No parser returns object-dtype arrays or a generator consumed once.

| In-process array | Exact shape, dtype and ordering |
| --- | --- |
| bins | `(n,)`, structured `bin_id:<i8,chromosome_index:<i8,start_bp:<i8,end_bp:<i8`; native genomic order, increasing global bin ID. TSV is decoded into this compact numeric array, never a Python dict per bin. |
| contacts | `(stored_rows,)`, structured `bin1_id:<i8,bin2_id:<i8,value:<i8\|<u8\|<f4\|<f8,source_block:<i8,source_row:<i8`; value dtype equals its descriptor. Rows sort lexicographically by `(bin1_id,bin2_id,source_block,source_row)`, preserving each entire source-linked row and all malformed duplicates. |
| weights | `(n,)`, float64, exactly aligned to bins. Source float32 widening is exact. Native nonfinite values remain native numeric encodings; the selected interpretation distinguishes masks from invalid weights. No independently sorted weight list is joined by position. |
| cell_states | `(m,)`, structured `bin1_id:<i8,bin2_id:<i8,state:\|u1`, ordered by the bin-ID pair. Tags retain CONTRACT's meanings. Whole missing regions remain separate extent facts; no huge synthetic list of missing cells is required. |
| dense_values | `(n,n)`, the descriptor's native numeric dtype, with the same ordered bin axis on both dimensions. It is present only for a genuine retained dense representation. If sparse and dense representations coexist, their known values/states must agree exactly before either is used. |

Arrays support repeated complete traversal, integer indexing, slices, NumPy
field access and repeatable random access for the full context lifetime. Slices
are ordinary views; algorithms must not materialize all pixels into Python
rows/lists or a whole chromosome into a new dense array. The sorted sparse pair
columns permit row-range search without a dict entry per pixel. Masking applies
to entire mathematical rows/columns, including sparse omissions. NaN masks are
not silently dropped by `nansum`/`nanmean`; denominator/extent rules still apply.
Memory mapping does not waive the caller's RAM/scratch limits. A compact bins
array or requested calculation that exceeds them returns a specific failure;
the worker does not choose a smaller region.

Final pure ports that close the original construction cycle:

```python
open_chromatin_contact_tables(
    descriptors: Sequence[TableDescriptor], *, streams: Mapping[str, BinaryIO]
) -> ContextManager[ContactTables]

build_chromatin_sheet(
    *, request: ChromatinRequest, contacts: ContactExtraction,
    elements: ParsedElements | None, metadata: MetadataRelations,
    tables: Sequence[TableDescriptor], table_views: ContactTables
) -> ContactSheet

read_chromatin_sheet_tables(
    sheet: ContactSheet, *, streams: Mapping[str, BinaryIO]
) -> ContextManager[ContactTables]
```

The lower-level loader receives descriptor-keyed **already supplied** read-only,
seekable regular-file streams. It verifies full bytes/digests, NPY header/dtype,
shape, lengths and TSV integer parsing, then maps those file descriptors. It
opens no additional path and owns no source resolver. It owns and releases its
array mappings on context exit; it does not close caller-owned supplied streams.
The caller must keep those streams open for the whole context. For tiny tests,
explicit in-memory streams may yield read-only in-memory arrays with identical
access semantics; production does not fall back to unbounded list loading.

C3 captures the closed tables first. Its result worker opens their exact retained
streams, enters the lower-level loader once, calls build_chromatin_sheet with
both descriptors and array views, then runs calculations before leaving that
context. Building the sheet can therefore join actual bins and raw cells to
element anchors/pairs without reparsing native input or requiring an already
constructed sheet. Scientific request/population/index validation belongs to
the sheet builder and subsequent saved-sheet validator, not a guessed data
access fallback. The saved-sheet loader wraps the same lower-level loader and
validates the saved sheet against its actual arrays. C1 owns both loader ports,
the sheet builder and their tests. C2 owns no loading or file retention code.

Returned ContactSheet/components/projections contain data-only records and exact
table identities, never live NumPy views, mmap handles, iterators or source-path
callbacks. C3 writes those records while retaining the exact table files; a
later saved calculation opens the saved bundle's streams in a fresh ordinary
context. It never reopens the original Cooler/HIC source to fill a missing vector.

`ContactTableFixture` and `PopulationTableFixture` in RECORD_SCHEMA.json are
**example serialization only**, version `chromatin_contact_table_fixture_v1`.
Their complete row lists make the hand-worked examples inspectable. A future
unit-test helper may explicitly convert these small records to the fixed arrays;
production calculator parameters are the in-process type above, never fixture
JSON. NativeScalar tags in fixture rows encode finite/NaN/Inf/no-value states
without illegal JSON numbers. That serialization does not replace native bytes.

## Parameter, numerical-field and relationship invariants

The two standalone calculators have explicit `normalization: NormalizationSpec`
keywords in addition to their ContactParameters/InsulationParameters. The
aggregate function passes `CalculationParameters.normalization` unchanged. This
closes the draft's missing normalization argument and permits a saved weighted
sheet to be recalculated as raw using its retained counts. A requested vector
not in the bundle remains missing; native metadata mentioning a vector does not
make it available. HIC normalization, when its unfinished adapter is eventually
enabled, requires divisive application. No caller request enables an unverified
HIC reader merely by passing a schema enum.

Units are closed `Unit={kind,source_unit}` records. `source_unit` is the actual
retained input unit string for contact-derived quantities, null for bp/kb/bin/
count/dimensionless fields. Normalized and squared kinds remain distinct. The
schema fixes integer count/coordinate types and every component's allowed unit
kinds. Calculated components currently have `uncertainty.kind=not_measured`.
Explicit supplied uncertainty is retained in MetadataSpec/SampleRelations with
its source, association, kind and units, and is not claimed as a calculator input.

Pair calculations retain raw_contact in both variants. For a raw calculation,
normalized_contact is null/not_measured because no weight transformation was
performed; the expected/fold fields use raw contact units. For a weighted
calculation, it has normalized state and normalized-contact units. Distance
`raw_distance_sum/raw_distance_sum_squares` use exactly the same eligible diagonal
bin pairs as the selected normalization, making mask exclusions inspectable;
the original complete raw matrix remains separately available for a raw rerun.

`requested_pair_count` counts the frozen occurrence population. `eligible_pair_count`
counts pairs meeting input/reference/cell/separation and complete-population
requirements before a zero expected denominator is considered.
`fold_defined_pair_count` counts defined fold values. `above_threshold_pair_count`
counts true flags among that explicitly reported fold-defined population; it is
not a claim that undefined folds are negative. If the comparison population is
unestablished, preserve known subset counts but mark the requested total
unavailable. `distinct_bin_pair_count` and multiplicity describe representation
dependence, never biological replication. Partial examples retain known raw
contacts/sums with `interpretation=known_subset`, and no full-population mean/fold.

The following checks are required in ordinary C1/C2/C3/C4 validators, beyond JSON
Schema's local field/type checks. They are implementation invariants, not new
runtime approval gates:

* ContactSpec format, actual header/version/group, resolution, native dtype and
  original source identity agree. Header facts never come from filename alone.
  Record native/source metadata separately from supplied assertions. A supplied
  reference label match remains `consistent_assertions`, not sequence identity.
* Population keys are unique and match requested order/regions exactly. End is
  greater than start. Axes, bin IDs, contig indices and lengths agree; bins are
  contiguous and align to the selected interval for these two initial modes.
  Declared fixed width permits only the genuine shorter terminal chromosome bin.
  Unknown metadata is null with extent/failure; zero counts require actual data.
* Exactly five role descriptors exist per population, with unique table keys.
  Availability/file/nullability, dtype field order, byte length, shape and array
  dimensions agree. Contacts use original global IDs and retained row/block
  locators. Sparse absence is zero only with complete read/index evidence.
  Stored duplicate coordinates are malformed, never silently summed.
* Source BED row ordinals, original line numbers, columns and assignment keys
  remain joined. Every assigned row exists; anchors lie inside actual intervals.
  Pair ordering is population order, enhancer source-row order, promoter
  source-row order. Pair keys and bin keys refer to those exact rows. Outside
  elements remain retained exclusions. Reference conflicts prevent association,
  not independent valid matrix measurements.
* Samples, contact/sample links, replicate/dependence-group keys and supplied
  uncertainty references all exist. Distinct sample labels do not imply
  independence. No sorting/position-based join across separate relationships.
* Integer and finite-number checks apply before arithmetic. Field units,
  numerator/denominator, selected normalization, mode and parameters match their
  source population. The schema's ordinary number range does not excuse NaN JSON.
  Nonfinite native arrays remain explicit source states, not JSON null-as-zero.
* Every component's canonical sheet digest and exact ordered table identities
  match the sheet. Inner mode parameters/normalization agree with the aggregate
  snapshot. Numerator/denominator meanings follow CONTRACT, never a schema rule
  evaluator. Boolean flags are nullable with a specific reason when undefined.
  Data/metadata retained but unused are not represented as confidence weights.
* Projection kind fixes its allowed row/field union. A row contains exactly the
  requested numerical fields plus mandatory keys/qualifications. `population_keys`
  appear only in ResultSelector, not repeated inside ProjectionSelection.
  Explicit keys and page selection are mutually exclusive. Flattened paging
  follows selected population order then the frozen mode-specific row order;
  offsets never cause a different native population to be analyzed. Requested
  unavailable fields return a qualified null Measurement/Boolean, not omission.
* Contact rows order by frozen occurrence pair. Distance rows order by increasing
  separation. Windows order by increasing boundary ordinal. Domains order by
  increasing adjacent boundary coordinates. Explicit-key selection returns keys
  in requested order, within each selected population. Numeric bin-ID/separation
  keys apply separately to each selected population and remain qualified by it.
  Population metric fields for an unselected mode are null/not_measured.
* Result page returned_count equals rows length; total is the established row
  population or null. Bounded projection is pagination, not truncated native
  data. Original parent selection and admitted return still own authorization.
* Software/input binding identities, original attempt, fixed output paths and
  selected request agree throughout producer/capture/worker. The bundle cannot
  declare its own hash inside itself; the host captures it separately. Population
  seals contain only closed output files and are authenticated against the
  original plan/closure. A header-only or failed file is never a successful seal.
* Native worker and selector modes agree. A saved plan contains only the exact
  retained sheet/table bundle, selector and worker directory/version. It has no
  producer/executable/source resolver. Worker-produced means files were emitted;
  it does not imply successful science or completion of requested delivery.

The complete [WORKED_RECORDS.json](WORKED_RECORDS.json) includes raw, explicitly
weighted, insulation and partial data chains from request/extraction through
sheet, full fixture arrays, components and requested projection. It includes
all five projection variants, saved recalculation, complete worker handoffs,
genuine zero and missing/malformed/missing-weight/partial/unsupported-format
failures. All identities/paths are explicitly symbolic fixtures; none are Store
registrations, native files or execution receipts. The literal numerical
expectations are authored examples, not evidence that a calculator exists.

Only data-only schema/record/hash checks are executed for this packet, through
existing local_jobs. Their exact result is in DOCUMENT_VALIDATION.json and their
resource enforcement evidence in DOCUMENT_VALIDATION_JOB.json. These checks do
not establish native-format parsing, scientific formulas, live workflow behavior
or production availability. HIC remains unfinished; Cooler/schema/math coding
can be reviewed independently of that unfinished adapter and deployment choice.
