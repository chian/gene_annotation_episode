# Exact native titles and bounded model metadata

Native title access preserves exact parser-returned header bytes and supplies
bounded metadata previews.

Parser v2 stores the full native name and description in the existing member
index and writes the exact title handed to `_record` into a content-addressed
UTF-8 artifact. The same row stores `header_ref`, `header_representation` and
`parser_version`. Identical title bytes share an artifact. No per-title semantic
source row, input target, quality judgment or length rejection is introduced.

For FASTA/FASTQ, representation is `parser_returned_title`. The FASTA adapter
already strips the line's outer whitespace before removing `>`; Biopython
returns its title without marker/line ending and strips trailing whitespace.
The artifact preserves that exact native title, including internal whitespace
and Unicode; it is not reconstructed from split fields. Raw sequence uses
`caller_material_name`. Original caller/source bytes remain unchanged and are
readable via material.read or source.read with representation=original.

Parser v3 preserves this interface and adds GenBank. That format has no native
FASTA-style title: its header artifact contains exactly Biopython's `record.id`,
marked `biopython_genbank_identifier`. The parser's full description remains a
separate member field and native record assertion. No synthesized id-plus-
description string is described as an exact native header. GenBank feature and
record metadata access is documented in [GENBANK_INTAKE.md](GENBANK_INTAKE.md).

Parser v4 stores FASTQ and read-role FASTA title/sequence/quality bytes in bounded
packed chunks, with exact component digests and ordered spans in the same SQLite
member index. Native header windows still return the actual explicitly selected
title artifact, not a chunk with invented relative coordinates. Unselected packed
member artifact fields are null with an explicit storage descriptor; this does
not mean the title is unavailable. Selected native title bytes, UTF-8 behavior,
parent form eligibility and original source identity remain unchanged. See
[PACKED_MATERIALS.md](PACKED_MATERIALS.md).

`material.members`, `material.member` and automatic input/reference views use
explicit previews instead of full native name/description strings:

```json
{"name_preview":{"text":"actual prefix","characters":100000,"utf8_bytes":100000,"complete":false},
 "description_preview":{"text":"description","characters":11,"utf8_bytes":11,"complete":true},
 "metadata_preview_characters":256,
 "header":{"representation":"parser_returned_title","utf8_bytes":200002,
           "read_with":{"member_ref":"member_<actual ID>","offset":0,"limit":12000}}}
```

Counts refer to the complete native field. These are display previews, never
replacement semantic identifiers. Automatic input views also replace nested
source_record.identifier with identifier_preview to close that duplicate path.
Full stored input IDs, records, names, descriptions, source identities, scope and
credit remain unchanged. Explicit Store.get/state.query exact-record access and
export stay full. The existing next-decision context consumes reasoning_view
directly; this header projection adds no controller or parent-form mechanism.

Member-bound references already have a 512-character label bound. The native
display prefix is now explicitly flagged by label_is_preview, with full character
and UTF-8 lengths. member_ref resolves the exact native name/title. Store verifies
these deterministic display facts against the native member. These host fields
do not enter the model source-subject extraction schema. Automatic reference
views expose label_preview rather than a clipped string as a full identifier.

The ordinary tool/API is:

```python
store.material_header(member_ref, offset=0, limit=12000) -> dict
# tool: material.header; required member_ref; optional offset and limit
```

It accepts a registered member ID, never a path. Output includes actual
member/material/collection/source/artifact references, parser version, ordinal,
representation, UTF-8 byte start/end/text/total, next_offset and exact next_query.
It returns original_header_bytes=false: offsets belong to the native title
artifact, never invented positions in the original file. UTF-8 continuation-byte
offsets and limits smaller than the first character receive precise
header_offset_not_utf8_boundary or header_window_too_small_for_character feedback.
The caller can follow next_query to reconstruct the exact title.

Full JSON exports retain native names/descriptions and title artifact/provenance,
original bytes, quality artifacts and typed parse errors. Portable bundles retain
the title bytes/hash. No GFF feature or new biological claim is inferred.

The earlier component checks passed eight new cases, including actual 100k identifiers/descriptions,
bounded default responses, exact Unicode reconstruction, native-versus-original
headers, partial FASTQ/export/reopen, source-row counts and native identity checks.
Thirty-five affected existing intake/export/state checks also passed. No broad
suite, network request or model call was performed for that component check.
The later frozen combined 359-test baseline had 355 passes and four outdated HTTP
fixture failures; those four passed after repair. These
overlapping results are not a final full-suite claim for the delivery and do not
establish a model's scientific use of the title access.

This does not bound every form of state growth. Fixed subject inventories,
reference registries and scientific record counts can still grow. Explicit
full-record reads/exports remain full; callers may request larger title windows.
Native parser records and selected SQLite JSON rows can be materialized; SHA
verification streams the full artifact before a window. Large-library resource
benchmarks are unestablished. Old indexes are not silently given reconstructed
title artifacts; parser v2 creates fresh provenance-bound parses.
