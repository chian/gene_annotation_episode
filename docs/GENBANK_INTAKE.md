# Native GenBank material intake

GenBank uses the same original material custody, parser attempts, source-bound
member index and fixed sequence-target binding as other supplied formats.
GenBank was added by parser v3; the current adapter version is
`supplied_material_parsing_v5.biopython_<installed version>`. V4 changes physical
read-library storage; v5 retains explicitly incomplete native gzip output
([gzip prefix custody](GZIP_PREFIX_CUSTODY.md)). Neither changes GenBank's
source-assertion semantics.
Original bytes are preserved before parsing. Reusing an acquired source retains
that source's origin, request and accession; wrapping or parsing it adds no target
and no scientific credit. Caller declarations remain unchanged by native molecule,
taxon, topology, transl_table or other supplied assertions.

Each GenBank parse has one normalized UTF-8 JSONL tool source. Optional
`parse_attempt.native_source_ref` names it; its parent is the actual parsed input
source. Its request identifies material, parser/version, parse key, original
material source and parsed input artifact. Gzip retains both original compressed
bytes and the decoded input source. The JSONL source's representation is
`native_genbank_assertions_jsonl_v1`.

`material_annotations` is an authoritative SQLite offset index into that single
artifact, not a second copy of full metadata or a competing annotation table.
`export_annotation` streams the same index as `native_material_annotations`, and
source/artifact closure retains both native JSONL and original bytes. Portable
exports preserve those exact bytes. No native feature is automatically copied
to `Store.current_annotations()`, a structural proposal, or GFF3.

## Ordinary access

```python
store.material_annotations(parse_ref, record_ordinal=None,
                           kind="record", offset=0, limit=50)
# tool: material.annotations; only parse_ref is required
```

Kind `record` returns native record entries; `feature` returns native feature
entries, optionally restricted to a source record ordinal. Pages preserve source
record/feature order, with total and exact `next_query`. Each entry has bounded
previews, native ordinals, actual source/artifact refs, and exact `start`/`end`
byte bounds with an ordinary `source.read` request. Default previews are bounded;
full selected metadata remains available without header/qualifier-length rejection.
`source.read` continuation is relative to the entire JSONL source: the entry's
`end` identifies where that selected JSON line finishes. Non-GenBank attempts
report `native_annotations_not_available` and unknown total, rather than claiming
that their native feature inventory was searched and empty.

Those byte bounds are normalized JSONL coordinates, never original GenBank
positions. A native record's separate `source_frame` uses actual parsed-input
byte bounds; for gzip these refer to decoded bytes. Exact source extraction must
anchor the selected actual source/artifact, not substitute the original file's
identity for a normalized JSONL quote. GenBank header access retains the actual
Biopython identifier with marker `biopython_genbank_identifier`; description is
separate, and `material.header` explicitly says these are not original file bytes.

## Native meanings and partial results

The native projection retains id/name/description, annotations and references,
dbxrefs, letter annotations, sequence availability and feature count. Reference
attributes remain complete. Features retain native id/type, ordered qualifiers,
and exact Biopython location structure: class, text, native strand including
unknown/0, compound operator and part order, remote refs, position classes,
nominal positions and fuzzy attributes. A nominal fuzzy position is not an exact
biological boundary. No location is fabricated for an unparsed native location.
Literal `transl_except`, codon_start and translation qualifiers remain source
values, not newly inferred coordinates or accepted translation models.

Biopython normalizes some native text (for example wrapped notes and translation
whitespace); the projection describes what that installed parser returned. The
unchanged source file remains the authority for original formatting. Unsupported
metadata/feature values produce specific partial feedback; exact exception class
and message remain in their native source entry. No unknown type is silently
converted to an authoritative biological string.

Records are framed only at actual left-aligned `LOCUS ` and `//` lines, so a
missing terminator can recover at the next record, while indented `//` inside a
quoted qualifier does not split a native record. Native warnings and parser
failures remain exact durable diagnostics alongside typed ordinal/code feedback.
An affected feature or record does not erase valid independent projections.

Undefined/CONTIG-only sequence records retain full native metadata and specific
`genbank_record_sequence_unavailable` feedback without filling N bases, inventing
a sequence member or binding a target. Their parse can be partial metadata-only.
Malformed frames remain inspectable in original bytes and native failure entries.
Reading these assertions can inform later ordinary reasoning; no compulsory
review, confidence gate or scientific interpretation follows from parsing them.

## Limits

The adapter materializes one record frame and native SeqRecord at a time, not the
entire multi-record file; a single very large record/feature is still materialized.
Windows use bounded reads, but artifact integrity verification streams the full
artifact. Indexed paging bounds returned records and previews, not every form of
large-state memory growth. These local checks establish representation/custody
behavior, not a model's successful annotation or a new sample/read-library credit
binding. There is no model or network call in intake.
