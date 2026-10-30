# Supplied material, sequence targets and reusable evidence

This staged implementation separates three identities: the original supplied
asset, a mechanical representation of it, and the fixed annotation targets being
annotated. Registration or parsing supplies no scientific credit and does not
change an existing problem's target binding. Scientific interpretations still
belong to the reasoning Episode; the numerical controller still owns yielding.

## Caller registration and target binding

`Store.create_problem(input_path=..., format="auto")` captures the original file
as a content-addressed artifact and caller source before parsing it.
`raw_sequence=...` (CLI `--sequence`) explicitly requests a single raw sequence;
uncertain symbols and a caller declaration `role="read"` are retained. File
`--format raw` is also explicit. Neither operation infers molecule or taxon.

Automatic recognition distinguishes FASTA, FASTQ, GenBank and gzip compression.
Unrecognized reports, tables, JSON, GFF or binary data remain inspectable assets;
they do not acquire fake sequence positions. GenBank intake uses the installed
Biopython parser and retains native annotations as source assertions, separately
from sequence projections. Explicit `text` and `opaque` retain
material without a sequence projection. This is not an arbitrary dataset parser.

Manifest versions 1 and 2 accept sequence targets and evidence in one file:

```json
{"schema_version":2,"entries":[
  {"sequence":"MKWV","name":"unknown","molecule":"protein","use":"target"},
  {"path":"reads.fastq.gz","name":"left","use":"evidence","role":"read",
   "sample":"S1","library":"L1","quality_encoding":"unspecified",
   "links":[{"relation":"paired_with","name":"right"}]},
  {"path":"right.fastq.gz","name":"right","use":"evidence","role":"read",
   "sample":"S1","library":"L1"},
  {"path":"growth-report.txt","use":"evidence","format":"text"}
]}
```

Relative paths resolve against the manifest directory. `use` is `target`,
`evidence` or `unassigned`; it is independent of molecule and biological role.
Entries default to `target` for explicit sequence datasets. Sample/library labels
and declared links retain caller provenance; co-file membership invents neither
shared sample nor organism. A malformed entry does not erase valid independent
entries. The original manifest remains available even if its structure is invalid.

Initialization alone binds eligible targets. Ordinary FASTA target collections
retain their actual scalar record identities. Target FASTQ and file collections
declared `role=read` bind fixed original read libraries. Each library has a
member-position measure and lazy read subjects, rather than a fabricated joined
sequence or one input row per read. Explicit raw single sequences retain their
scalar identity even with `role=read`. An explicit caller `target_records:[1]`
can instead select an actual scalar fragment by zero-based source ordinal.
Shared caller library declarations can group files without inventing biological
sample, pairing or organism identity. See [READ_LIBRARY_TARGETS.md](READ_LIBRARY_TARGETS.md)
for scope, ordinary tools, credit meaning and unimplemented assembly/context work.
Nonsequence-only material can still be retained, but has no implemented biological
credit target; CLI `run` reports `biological_target_binding_unavailable` and
`scientific_completion:not_established` in that case. Raw-library biological
annotation capability is not established merely by this binding.

## Ordinary registered-material work

```python
store.register_material(path, use="evidence", format="auto") -> material
store.register_material(data=bytes, name="supplied", use="evidence") -> material
store.register_material(source_ref=existing_source_ref) -> material
store.parse_material(material_ref, format=None) -> parse_attempt
store.material_members(collection_ref, offset=0, limit=50) -> page
store.material_errors(parse_ref, offset=0, limit=50) -> page
store.material_read(material_ref, offset=0, limit=12000) -> base64_byte_window
store.material_member(member_ref, offset=0, limit=12000) -> sequence_quality_window
store.material_header(member_ref, offset=0, limit=12000) -> native_title_window
store.material_annotations(parse_ref, record_ordinal=None, kind="record", offset=0, limit=50) -> native_assertion_page
store.material_reference(member_ref) -> registered_sequence_reference
```

Only the caller registers filesystem paths. CLI `add-material` appends caller
evidence without changing the problem identity. Episodes select ordinary tools:

| Tool | Exact required fields | Optional fields |
| --- | --- | --- |
| `material.from_source` | `source_ref` | `format` |
| `material.parse` | `material_ref` | `format` |
| `material.read` | `material_ref` | `offset`, `limit` |
| `material.members` | `collection_ref` | `offset`, `limit` |
| `material.errors` | `parse_ref` | `offset`, `limit` |
| `material.member` | `member_ref` | `offset`, `limit` |
| `material.header` | `member_ref` | `offset`, `limit` |
| `material.annotations` | `parse_ref` | `record_ordinal`, `kind`, `offset`, `limit` |

`material.from_source` reuses the actual registered source, artifact, request,
origin and accession. It registers an evidence wrapper, without parsing or adding
targets. The model cannot pass a filesystem path, invented display label, taxon
or target membership. It can then select `material.parse` on the returned ID.

Member pages use actual original record order, not header sorting. They return
stable index handles and exact next-page arguments. `material.member` reads the
chosen sequence/quality window and publishes that actual member as a reusable
registered `reference` in the same call. Unknown molecules stay `unspecified`;
the reference remains evidence with no eligible input footprint. Subsequent
inspection, alignment or derivation uses that reference ID. Index handles do not
inflate the parent semantic-reference registry to every library member.

Member/page output and automatic input/reference context use explicit bounded
name/description previews. Full native identifiers and descriptions remain on
disk; parser v2 retains its exact returned title in a source-linked artifact.
`material.header` gives exact UTF-8 windows with provenance and continuation.
Native parser title and original file header bytes are distinct. See
[MATERIAL_HEADERS.md](MATERIAL_HEADERS.md) for the interface and limits.
Parser v3 extends that path to GenBank: its actual parser identifier is marked
`biopython_genbank_identifier`, with description kept separately. Native record
metadata/features have a single normalized JSONL source and an offset index;
`material.annotations` provides bounded previews and exact `source.read` windows.
These are supplied assertions, not `Store.current_annotations()`. See
[GENBANK_INTAKE.md](GENBANK_INTAKE.md) for native coordinates and partial records.

## Authority, provenance and failure meanings

The existing SQLite Store contains immutable `material`, `parse_attempt`,
`collection` and caller `material_link` records. Its `material_members` and
`material_errors` tables are the authoritative normalized indexes; the GenBank
`material_annotations` table indexes bytes in its one immutable native JSONL
source rather than creating another annotation authority. Immutable
collection counts describe that same transaction's rows. Artifacts hold exact
original bytes and separately normalized sequence/quality bytes. No second
inventory, review or annotation authority is introduced.

Parser v5 retains the v4 packed layout for native FASTQ and declared read-role FASTA components in bounded
immutable chunks with indexed exact hashes/spans. Explicit member/header or
target-fragment selection materializes real component artifacts through one
shared path. Unexamined read inventory exports as a compact SQLite sidecar rather
than per-read main JSON nodes/files. See [PACKED_MATERIALS.md](PACKED_MATERIALS.md)
for physical custody, ordinary API semantics and unresolved scaling limits.

Parse identity binds material, requested format and adapter/Biopython version.
An identical parse reuses the same immutable result. A new wrapper interpretation
has its own attempt. Gzip decoding keeps original compressed bytes and the actual
emitted decoded prefix, including on a later wrapper failure, with source lineage,
decoder provenance and explicit incomplete feedback. It does not certify the
failed wrapper or invent an unread suffix; see [GZIP_PREFIX_CUSTODY.md](GZIP_PREFIX_CUSTODY.md).
Parsers do not infer a
Phred encoding: quality characters, declared encoding, identifiers, duplicate
occurrence and source ordinal remain separate facts.

FASTA recovers at explicit later headers and retains valid independent records.
FASTQ uses the installed Biopython wrapped-record parser; after structural
ambiguity it retains the valid prefix and reports the remaining scope unparsed.
It does not guess that `@` in a quality string begins another record. Feedback
contains typed status/code, source ordinal and byte offset when known. Missing
FASTQ offsets are null, not fabricated. Detailed adapter diagnostics remain
private audit artifacts. GenBank native warnings, parse failures and projection
diagnostics also remain in their selected native JSONL source, with typed
ordinal/code feedback available to the owning Episode. Failed/unsupported representation never deletes the
already committed original custody.

Pages and byte/member windows use bounded-memory reads and indexed access.
Artifact verification currently streams the entire artifact before a window is
read; this bounds memory, not total I/O. Explicit one-sequence raw parsing and
native FASTQ record parsing materialize that selected record. Large-input
throughput/memory benchmarking is not established by the small synthetic checks.

JSON exports stream original materials, parse/collection facts, indexed member
metadata and source/artifact closure, with optional portable artifact files.
These remain evidence; GFF3 gains no fabricated read/protein CDS rows. Current
annotation/assessment and credit meanings are unchanged.
