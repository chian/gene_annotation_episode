# Compact storage of native read evidence

FASTQ and FASTA declared `role="read"` use `packed_member_components_v1` under
parser `supplied_material_parsing_v5.biopython_<installed version>`. The packed
layout was introduced in v4; v5 adds [gzip prefix custody](GZIP_PREFIX_CUSTODY.md)
without changing its component layout. Original
supplied bytes, parser-returned title, sequence, quality, order, repeated-name
occurrence, caller declarations and parse errors retain their meanings. There
is no biological classification, quality cutoff or read deduplication in this
storage path. Separate [fixed read-library binding](READ_LIBRARY_TARGETS.md)
defines original targets at initialization; component selection does not add
targets to an existing problem. Raw single sequences, ordinary non-read FASTA and GenBank keep their
existing sequence/target semantics. An explicitly selected read fragment remains
an honest possible input target; a library is not silently made into one target
per read, a joined chromosome, or a new credit denominator.

## One authoritative member index and physical chunk spans

`material_members` remains the immutable member metadata authority. Packed rows
retain full native names/descriptions and source identity, with explicit storage:

```json
{"header_ref":null,"sequence_ref":null,"quality_ref":null,
 "storage":{"representation":"packed_member_components_v1",
            "parse_key":"parse_<actual ID>",
            "components":{"header":{"sha256":"<exact title digest>","bytes":42},
                          "sequence":{"sha256":"<exact own-sequence digest>","bytes":150},
                          "quality":{"sha256":"<exact own-quality digest>","bytes":150}}}}
```

The null artifact fields mean packed physical custody, not absent sequence/title.
Absent quality is `storage.components.quality=null`. No nonexistent artifact ID
is registered for these components. Their own hashes/byte lengths are distinct
from chunk hashes. Member identity binds source/parse/ordinal and exact sequence/
quality content, independently of later selection or artifact caches.

The same SQLite Store has `material_component_spans(member_ref,component,part,
chunk_index,start,end)` and `material_pack_chunks(parse_key,chunk_index,artifact_ref)`.
The ordered spans index raw bytes in real content-addressed chunks. They do not
create biological coordinates or source-file offsets. Fields can cross chunks;
the host chunk budget is eight MiB and splits a field rather than rejecting it.
Native UTF-8 title bytes can split within a code point physically; ordinary title
windows reassemble bytes and enforce the existing exact UTF-8 boundary contract.

Only sealed chunks produce artifact files and filesystem synchronization during
normalization. Parser repeated-name bookkeeping uses indexed SQLite keys and is
removed when the attempt finalizes; no dictionary grows with distinct read names.
The immutable member rows retain the resulting native occurrence values, including
occurrences before an independently invalid record, as before.

## Existing ordinary selection APIs

`material.members` returns bounded metadata previews and exact member handles.
`Store.get(member_ref)` returns the full authoritative native row. Sequence and
quality presence/length come from component metadata rather than guessed artifact
files. `material.member` reads the selected relative window, then materializes the
real selected components and publishes its reusable reference in the **same**
existing tool operation. The reference's sequence artifact has its own exact
sequence digest and actual standalone bytes; existing sequence/native tools need
no virtual-file or chunk-as-sequence interpretation. Repeating or reopening that
selection reuses the same component artifacts and member/reference identities.

`material.header` uses the shared component materializer for its explicitly
selected title. Its artifact_ref names the real parser-returned UTF-8 title;
start/end are title-relative bytes, never mislabeled chunk or original-file
coordinates. Its source_ref preserves actual original/decoded source provenance.
It does not grant quote-anchor permission to pretend normalized title bytes are
the original source's artifact. Existing source.read and extraction-anchor rules
remain unchanged. Native FASTQ source offsets stay null; `@` in quality is not
guessed to be a record delimiter.

Initial caller `target_records` selection uses that same materializer before
creating any real input sequence_ref. No later member selection adds a target.
The immutable packed index is not changed to record cache state. Shared actual
component projection supplies reference validation, artifact ownership and
export. A header-only artifact stays outside the parent scientific form namespace
until an actual registered member reference makes it eligible, preserving the
existing boundary. Private diagnostics and unregistered native handles gain no
new eligibility.

Selected component windows verify the relevant bounded chunk artifacts; they do
not hash an entire read library on every call. Materialization streams component
bytes and verifies their own digest/length. Generic Store.artifact/get_artifact,
artifact_path, source-owned output streams, source.read anchors and native file
consumers keep their actual standalone-artifact meanings.

## Portable export

Unexamined packed members are not expanded into main JSON nodes or component
artifact files. `packed_material_indexes` lists one SQLite snapshot per collection:

```json
{"format":"gene_annotation_episode.packed_material_index","schema_version":1,
 "storage_representation":"packed_member_components_v1",
 "parse_ref":"parse_attempt_<actual ID>","parse_key":"parse_<actual ID>",
 "collection_ref":"collection_<actual ID>","member_count":50000,
 "relative_path":"current.json.materials/collection_<actual ID>.sqlite3",
 "sha256":"<actual snapshot digest>","bytes":12345,"chunk_count":2,
 "content_included":true}
```

The sidecar contains exact member rows, component spans, pack rows and chunk
artifact metadata. Its metadata table retains exact collection and parser-attempt
facts. It is a derived immutable export snapshot of the same SQLite authority,
not a second scientific inventory or live index. Original-source and chunk custody
remain in ordinary export reference closure. Real selected input/reference members
and their actually materialized artifacts remain in main scientific JSON; their
unchanged source/assay/assessment/annotation meanings are preserved. Header-only
cache bytes can be reconstructed from the index and chunks without promoting the
cache to a scientific record.

With `include_artifacts=True`, each distinct pack file is copied once, along with
the ordinary selected scientific artifact closure. Its relative_path and digest
describe exact **chunk** bytes. No component digest is paired with a whole-chunk
path. Move the JSON, its `.materials` directory and its `.artifacts` directory
together. With `False`, the index still contains full metadata while chunk/source
contents remain external; `content_included=false` makes that distinction explicit.
Sidecars are checksummed and replaced before JSON publication. Interruption can
leave a companion mismatch, detectable from the JSON checksum; retrying export
recreates the snapshot. No Store mutations occur during export.

## Partial work and limits

Native wrapped FASTQ parsing still retains an unambiguous valid prefix and marks
the remainder unparsed on malformed representation. FASTA retains independent
records at actual headers. Final chunk/index/collection/attempt publication uses
the same Store transaction. A returned partial attempt is reusable and exact
after reopening. Original custody survives a process interruption; incremental
parse checkpoints and efficient interrupted FASTQ resume are **not implemented**
by this storage slice. Uncommitted chunks may remain harmless orphan content files.

Large native individual records/titles and selected full component materialization
can still be large; native parsing materializes one record at a time. SQLite
metadata grows with supplied membership on disk. Fixed target inventories,
scientific records, form registries and detailed credit projection have other
growth limits. This storage change does not solve full read-library biological
target, scope, assembly, credit or workflow scaling; the separate binding above
addresses target/member geometry, while broader throughput remains unproven.
Measurements use explicitly
generated local read libraries; they are not biological validation or a claim of
million-read throughput.
