Packet 442 implements the C1 records, Cooler input reader, element/metadata
readers, numerical-sheet construction and saved-table contexts for the fixed
`B-L124-analyze_chromatin_interactions` assignment. It does not establish the
whole tool's episode integration or change any accounting row.

The original supplied attachment was read completely first. Its objective and
all sixteen design principles were reread verbatim after native-format
examination and again before this handoff, followed by the current439 interfaces,
sheet/table contract and441 addenda002/003. No GOAL.md was read or edited.

Implemented production ports are:

- `chromatin_interaction_contracts.py`: all439 named record exports,
  `ContactTables`/`ContactPopulationArrays`, strict object validation,
  duplicate-rejecting JSON decoding, canonical digest, and independent standalone
  2020-12 schema exports rooted at the selected name with reachable local defs.
  The production schema is a static literal; no verification packet is imported.
  PopulationSeal includes the accepted441/003 actual native header.
- `chromatin_cooler_inputs.py`: `read_cooler_contacts` takes the supplied native
  stream and exact output streams; `unavailable_chromatin_extraction` supplies
  explicit no-data records for a failed input. The reader validates actual HDF5
  Cooler schema3/group/header, axes and indexes, retains exact source-row
  locators and native value dtype, streams canonical NPY/TSV, and preserves
  partial independent populations. Symmetric square input requires actual
  reciprocal equality. No balancing or HIC adapter is implemented.
- `chromatin_interaction_inputs.py`: `parse_chromatin_elements`,
  `extract_chromatin_metadata(request=...,native=...,supplied=...,elements=...)`,
  `build_chromatin_sheet(...,tables=...,table_views=...)`, and saved-sheet
  relationship validation. BED occurrences, original lines/columns, assignments,
  anchors and supplied gene links remain joined. Native/supplied reference
  assertions and sample/dependence relations remain separate.
- `chromatin_interaction_tables.py`: context-managed
  `open_chromatin_contact_tables` and `read_chromatin_sheet_tables`. Regular-file
  NPY arrays use read-only mmap over supplied descriptors; compact bins use an
  exact numeric array. Callers own streams; contexts own mappings. Small explicit
  BytesIO fixtures are limited to16MiB, with no unbounded production fallback.
  File digest/length, header/dtype, declared availability, axes, locators,
  normalization, exceptional states and stored sheet numbers are checked before
  scientific use. Saved loading does not open original HDF5 or BED inputs.

All five table roles are declared exactly once per population. Present empty
arrays have real NPY headers. Missing/failed sources never create zero matrices.
Native zero rows differ from established sparse omissions. Duplicate rows,
negative values, NaN/Inf encodings and balancing masks remain retained with
located qualifications. A documented malformed lower-triangle native row stays
in the partial raw table. C2 consumes its qualification without legitimizing it.
Normal table keys use population_key:role; when that would exceed256 characters,
the population-key portion is replaced by `p` plus its complete SHA256 digest.
The exact population key remains a separate field. This is stable across C3's
separate per-population calls and does not change the schema.

The complete C1 verification is `tests_attempt6`:27 unittest tests, zero failures,
zero errors, terminal/quiescent exit0. Its immutable executed source snapshot,
selected request, complete stdout/stderr, durable native handle, source/binary
before/after pins and receipt are retained. Tests validate69 of the70 complete
authored439 records; the old PopulationSeal example is excluded because it lacks
the mandatory441/003 native field. This is schema evidence, separately from
the native-format checks below.

Actual input serialization was read using the existing reference interpreter:
Python3.12.3, NumPy2.5.0, h5py3.16.0/HDF52.0.0. Existing root-venv jsonschema and
its dependencies were explicitly appended after that interpreter's site-packages;
no environment was changed. The final run checked440's complete numerical
dependency and loaded-library pins, pinned the validator dependencies and both
original fixtures, and verified all pins unchanged afterward. The verified
limits were21,474,836,480 bytes RAM, zero swap,4,294,967,296 bytes scratch and
RuntimeMax=infinity. Scratch used3,203,072 bytes in the final receipt; enforcement
is monitored with possible overshoot, not a hard aggregate filesystem quota.

Concrete native measurements verified:

| Retained native synthetic input | Verified reader/sheet values |
|---|---|
|440 four-bin Cooler fixture | int32 counts widened losslessly to int64; ten stored upper rows, one explicit zero;16 directed/10 unordered cells; zero implicit directed cells; weights[1,2,1,2]; E–P raw6 at original pixel row2 and E–Q raw0 at row3. |
|440 six-bin Cooler fixture | Six stored rows, one explicit zero,25 implicit directed zero cells; all source row locators retained. |
| Complete empty synthetic sparse HDF5 | Four actual bins, zero stored pixels,16 established implicit directed zero cells and a real empty contacts NPY. |
| Corrupted HDF5 checksum chunk | Earlier two pixel rows remain retained with original row IDs[0,1]; selected population is partial and implicit-zero semantics are not established. |
| Corrupted requested weight chunk | Raw contact2 remains in a complete raw population; requested weights are unavailable, without raw fallback. |

Further targeted checks cover explicit group selection, variable-bin declaration,
short terminal fixed bin, square reciprocal/asymmetric input, bad indexes,
corrupt empty CSR ranges, external links, unsupported schema version, digest
mismatch, duplicate pixels, negative/nonfinite native values, missing/NaN/zero/
negative weights, unaligned populations, valid earlier population survival,
duplicate BED occurrences/names, original lines/extra columns, missing classes,
invalid anchors, conflicting references, exact sample/input joins, read-only
mmap lifetime, caller stream ownership, invalid NPY length/digest, forged saved
counts/weights/references/element joins/states/dense values/source locators,
projection field/population/page relations, and maximum-length population keys.
The final run retains generated native case bytes, canonical tables, extraction
records and saved numerical sheets under its `native_cases/` and `saved_sheets/`.
Synthetic serialization is never represented as biological observation.

All attempts are retained:

| Attempt | Terminal result | Scope/evidence |
|---|---|---|
|1 | exit1;17 tests,13 errors | Strict JSON validation rejected NumPy string scalars. Fixed explicit string conversion. Two unrelated C2 test source paths changed during this attempt; its exact snapshots are retained and the overbroad pin set was corrected. |
|2 | exit0;17 tests | Initial native, sheet, absence, metadata and lifetime checks; source pins unchanged. |
|3 | exit0;22 tests | Added projection relationships, reciprocal square input, corrupted native chunk and index checks; source pins unchanged. |
|4 | exit0;25 tests | Added failed weight chunk, native input aliasing and saved state/dense/locator checks; complete native dependency/fixture pins unchanged. |
|5 | exit0;26 tests | Added retention of the located malformed lower-triangle record; pins unchanged. |
|6 | exit0;27 tests | Added stable bounded table keys; all source/binary pins unchanged. |
|7 | exit0;4 targeted tests | Lower-triangle NaN/state retention plus all table context tests, after retaining duplicate-row locators as a NumPy view instead of a Python list; all source/binary pins unchanged. |

Every attempt was followed through its original durable handle to terminal
quiescence. No observation timeout caused a restart or replacement submission.

Final production source pins:

| File | Bytes | SHA256 |
|---|---:|---|
|chromatin_interaction_contracts.py |123853|038fa08566f0f3fc078d42925db425c6a2cfa4db2a6f985341df58f8d45680b7|
|chromatin_cooler_inputs.py |32249|3e121e89d10b0610faa1a66f46deda92baeb5b34b0b3398df2824609a2a5604b|
|chromatin_interaction_inputs.py |33130|8b3e945ebf765daef52fd657ea69dbed2f78ca9b5dab01f89ac81e2117b81e63|
|chromatin_interaction_tables.py |13893|8a54648815bf5cb2c061874314c5db6d3ee4fd04ec7bd1cf9eb04a448cbf04af|

The first three final production pins are unchanged from attempt6. Attempt7
records the final one-line table change and stronger native lower-NaN case;
attempt6's earlier table source remains immutable in its executed snapshot.
The targeted follow-up passed4/4 and did not rerun unrelated calculations.

Current consuming C3 extraction, sealed-population merge, native worker, saved
worker and C2 array/calculation/projection paths were inspected. C3 was notified
that capture loss must downgrade the current availability/read-evidence claims
while preserving immutable original seals and independent populations. C2
separately reported its successful actual-native reader→sheet→saved-table→
calculator joins, including the malformed lower-row case; those receipts remain
C2's verification, not this packet's execution claim.

Numerical availability at this handoff includes exact bins/coordinates, native
raw cells/zeros, native weights/masks, stored/native cell counts, anchor/bin
joins, complete occurrence pairs and their raw contacts. Replaceable enrichment
and insulation formulas are C2's work. C3 production launch/capture-loss recovery
and root's full selected-library→resource-child→typed-parent path remain separate
verification. HIC, schema2, retained biological native input, giant-matrix resource
exhaustion and Cooler-library cross-comparison were not verified here. External
or indirect HDF5 dependencies are rejected by the initial adapter. No shared
runtime, other tool, literature, evidence-axis/W05, prompt, goal or accounting
file was edited by C1.
