# XLSX evidence as ordinary episode tools

`source.xlsx.sheets` and `source.xlsx.rows` read retained spreadsheet evidence.
They are ordinary selected tools within the existing episodes, not a new child
type, independent agent loop, annotation algorithm or report composer.

The actual configured-model investigation acquired PMC7055658's Table S3 XLSX
but had only archive/byte-window readers in its original catalog. The model
paged worksheet/shared-string XML. A direct inspection established a row matching
YBHP and P0AAW1, motivating a selected row reader rather than guessed biological
conclusions from the downloaded file or its name.

First obtain actual sheet relationship keys:

```json
{"source_ref":"ACTUAL_WORKBOOK_SOURCE_REFERENCE"}
```

Then select a sheet, page and optional literal cell filter. For example, on the
actual study workbook the sheet named `Average ratio and clustering` has the
returned relationship key `rId2`. The fixed query protein's accession occurs in
column B. These are properties of that source, not generic XLSX defaults:

```json
{
  "source_ref":"ACTUAL_WORKBOOK_SOURCE_REFERENCE",
  "sheet_key":"rId2",
  "offset":0,
  "limit":1,
  "header_row":1,
  "where":{"column":"B","match":"equals","value":"P0AAW1","case_sensitive":true}
}
```

All arguments are explicit. `where:null` requests an unfiltered page;
`header_row:null` requests no separate header. A null filter column searches all
actual cells. Offset is zero-based within matching rows; returned native grid
row numbers and cell addresses retain their own source meaning. `row_ordinal`
is document order and does not replace an absent/invalid native row number.

The implementation resolves package relationships instead of assuming sheet
numbers or names identify XML files. Shared strings use a disk SQLite index.
Rich text retains visible runs and excludes phonetic annotations. Numeric/date
lexical values and styles remain unchanged; formula text/attributes and cached
values remain distinct, with no recalculation. Missing values, unresolved shared
strings, ambiguous relationships and unknown row numbers are not silently guessed.
Valid rows/cells survive partial decoding with typed errors and unknown totals.

The selected native worker uses the existing caller-owned memory/scratch limits,
cancellation and protected lifecycle. It does not read/write the scientific Store
or choose another action. The host publishes a source derivative linked to the
resolved original source and input artifact. Its JSON artifact preserves the
selected data, worksheet package part and row/cell identities. JSON byte anchors
therefore refer to that derivative, not original compressed XLSX byte positions.

Source acquisition/decoding alone creates no assessment, annotation or scientific
credit. Parent/child interpretations still use the existing controlled forms and
source-linked scientific records. No duration from this parser is relabeled as a
homology search measurement.

Ten checks passed in 8.62 seconds, covering the actual study's matching row and
distinct prior-STEPdb/study-localization columns, relationship ambiguity, partial
rows/cells, formula/cache preservation, native limits, original-source lineage,
saved-operation replay and zero scientific credit from decoding alone. Independent
source review found two issues before their correction: ambiguous relationships
selected the last candidate, and missing/malformed row numbers could discard
previous rows. The corrected paths have focused tests and a separate reread.

Adding these tools also exposed a runtime recovery defect: reconstructing a saved
decision compared its schema to today's expanded catalog. Recovery now retains
the original saved schema/context for completed and interrupted decisions and
validates their responses under that same contract. New decisions use the new
catalog. Five focused recovery/expectation/scientific-binding checks passed in
19.01 seconds, including rejection of a new tool attempted under an old pending
contract. No historical action observation or score is manufactured by reload.

A separate recovery review found that regenerating an existing restoration index
could relabel a previously unavailable tool after it was added. Recovery now
preserves an existing index; newly needed indexes resolve each tool against that
decision's saved catalog. The runtime/recovery group passed 38 checks in 125.93
seconds, including recovery from providers with and without a prior session.
Independent source rereview found no remaining defect in that focused path.

The actual investigation resumed under its original run identity. All 44 prior
completed action/result/credit rows and all 44 controller observations matched
the pre-reload hashes after recovery. Its pending decision retains the original
57-tool contract and receives a bounded history index for the fresh conversation.
The new XLSX tools become available only at subsequent new decisions. This
recovery observation does not establish model use of the reader or new scientific
progress.

Subsequently, the configured model selected the sheet reader at decision 45 and
the row reader at decision 46. Its own case-insensitive literal `ybhP` filter on
sheet `rId2` returned one row, native row 1324, with YBHP/P0AAW1 and the actual
cell values. The JSON derivative is `source_5d026809f7b01607045a5ed7`, linked to
original XLSX source `source_56650c77da3e557469a4a6e7`. Both operations completed
under the configured limits. Scientific credit remained 0.175260350520701;
reading/decoding alone did not assert a biological conclusion.
