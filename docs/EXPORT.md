# Current annotation exports

`gene_annotation_episode.export.export_annotation` writes an inspectable snapshot
of the scientific state. It does not choose an interpretation, manufacture a
functional label or change state, credit or continuation.

```python
from gene_annotation_episode.export import export_annotation

result = export_annotation(
    store, "exports/current.json", format="json", scope=None,
    include_credit=False, credit_policy=None,
    include_artifacts=False, page_size=128,
)
```

`scope` uses the Store's original input subjects, optional fixed original-unit
segments and original-read selections. `page_size` controls the export's memory batch, not its scientific
coverage. The result contains `status`, `format`, effective `scope`, `counts`,
`json` (`path`, `sha256`, `bytes`) and optional `artifact_directory`. GFF3 also
returns `gff3` with its path/hash/size and emitted/excluded feature counts.

## Authoritative JSON

The document format is `gene_annotation_episode.current_annotation`, schema
version 1. Its fields preserve these meanings:

| Field | Meaning |
|---|---|
| `problem`, `inputs` | Exact immutable problem and original input identities/declarations, including sample and supplied-context links. All original input metadata remains present so the problem identity and comparative references retain their meanings. |
| `scope`, `eligible_footprint`, `eligible_geometry` | The exported scientific scope in original scalar or read-member-local units. An implicit library scope has `eligible_footprint=null`; `eligible_geometry` retains its fixed mass/selection, without inventing a linear library length. Overlapping features retain their actual complete coordinates. |
| `membership.current_annotation_refs` | Exact current annotation revision identities intersecting the export scope. Their coherent sets, alternatives, dispositions and resolution are unchanged. |
| `membership.current_assessment_refs` | Exact current assessment revisions for the scoped scientific subjects. |
| `membership.candidate_feature_refs`, `candidate_product_refs` | Actual recorded structural/product proposals. Membership alone is not a selected interpretation or an assertion of biological correctness. |
| `membership.recorded_hypothesis_refs`, `recorded_observation_refs` | Scoped working hypotheses and observations, whether or not a current account uses them. |
| `membership.referenced_current_*_refs` | Additional current annotation/assessment records reached through dependencies, outside the scoped membership lists. |
| `membership.referenced_noncurrent_*_refs` | Specifically referenced older revisions. These remain historical dependencies; the exporter never silently substitutes a newer assessment. |
| `records` | Exact typed records needed for those memberships and their transitive reference closure. Source entities, actual assayed constructs, conditions, assumptions, source anchors and dependencies remain distinct from target attributions. |
| `artifacts` | Referenced artifact identities, SHA-256 digests, byte sizes and media types. Raw sequence/source bytes are external to the JSON. |
| `parse_errors` | Exact authoritative parser feedback with parse reference/key, local error index, native ordinal/offset/code, separate from scientific findings. |
| `native_material_annotations` | Streaming GenBank record/feature offset index, with parse/source/artifact identity, native ordinals and bounded previews. The referenced JSONL contains full native supplied assertions and exact parser/projection diagnostics; these are not current scientific annotations or GFF features. |
| `packed_material_indexes` | Checksummed SQLite sidecar descriptors for exact unexamined FASTQ/read-role FASTA member inventory and physical component spans. Selected member references/real artifacts remain in main closure. Pack hashes/paths describe chunk bytes, never falsely the bytes of one read. |
| `read_library_indexes` | Checksummed SQLite sidecar retaining immutable library descriptors and exact fixed selected membership. Original full membership remains in the portable native index; the library is not a sequence or organism. |
| `credit_projection` | Optional current projection under the explicitly recorded policy and the same read snapshot/scope. It is an operational evidence progress proxy, not biological accuracy, confidence or a saved run's historical score. |

Sources, typed terms and actual source labels are exported through their records;
there is no additional model-generated summary. An absent or broad interpretation,
weakened hypothesis, unresolved alternative and unavailable sequence remain what
the stored records say. The exporter does not transfer a reference protein's name
to the unknown target.

Reference closure includes all referenced original subjects, semantic records and
artifact metadata. It does not materialize runtime journals, closed child logs,
all prior annotation revisions, unreferenced search resources or unattached
execution diagnostics. An old assessment explicitly named by a current account
remains available and visibly noncurrent alongside its current replacement.
Native document sources may declare exact `stdout_ref` and `stderr_ref` artifact
fields. These source-owned streams participate in the same reference closure,
including successful native warnings; references embedded only inside arbitrary
request JSON are not interpreted as another graph. Custody records and streams
remain provenance, without new biological memberships or credit targets.

Optional credit preserves its policy, formula/projection versions, scope, signed
support/opposition semantics, inactive dependency diagnostics and extent modes.
Assessment `extent_basis` and optional target footprint remain exact stored fields.
Inferred contributions retain their actual source operand intervals and physical
source paths separately from target `contributing_segments`; exporting them never
creates a measured source-to-target map.
`projected_footprint_units` is a proxy extent; fractional product coverage does
not become a residue-level genomic mapping. The export never promotes the
highest-credit coherent set to the selected scientific account.

## Portable artifact bundle

`include_artifacts=True` writes a sibling `<json path>.artifacts/` directory.
Each artifact's `relative_path` resolves from the JSON's directory; names are its
content digest. Bytes are copied in bounded chunks and hash/size checked before
publication. This retains original supplied sequence/context, acquired sources
and extraction text without loading all those bodies into memory. Move the JSON
and sibling directory together. With the default `False`, provenance metadata is
complete but raw artifact contents must remain available from the original Store.
Packed read collections also have a sibling `.materials/` index directory that
must move with the JSON. This preserves full native member metadata without one
main JSON node or portable artifact file for every unexamined read component.
See [PACKED_MATERIALS.md](PACKED_MATERIALS.md) for its exact schema and limits.
The same directory carries fixed read-selection indexes when applicable; see
[READ_LIBRARY_TARGETS.md](READ_LIBRARY_TARGETS.md).

Scientific records are read in pages and their dependency index is temporarily
spooled to disk. A single SQLite read snapshot covers inventory, current pointers,
reference closure and optional credit. Export files are written to temporary files
and replaced after successful serialization; a failed artifact copy does not
replace an existing JSON document. The Store is never modified.

## GFF3 coordinate projection

Use `format="gff3"`. An authoritative `<gff path>.annotation.json` companion is
always written, and its SHA-256 is recorded in the GFF3 header. The pair preserves
interpretations that GFF3 cannot express. The JSON's `gff3_projection` lists emitted
feature identities and each excluded feature's exact reason.

Only actual features directly located on an original DNA/RNA input are eligible
for this representation. An input with role `gene`, a bare protein and a public
reference never acquire fabricated gene/CDS rows. Candidates remain identified
as candidates; direct current accounts carry exact annotation references,
resolution, dispositions, coherent-set references and retained alternatives.
Scores stay unspecified; no confidence or functional names are inferred.
Read-local features remain in authoritative JSON with their member identities;
GFF3 records their exclusion rather than inventing a library chromosome.

Stored coordinates convert from half-open zero-based to inclusive one-based.
Discontinuous segments retain their feature identity and explicit stored segment
index. No circularity is inferred. Feature types use their defined Sequence
Ontology equivalents; derived-product coordinates are not projected onto genomic
bases without the missing residue mapping.

The current structural schema has no recorded CDS phase. **CDS rows are excluded**
with `cds_phase_not_recorded`, without guessing a phase or relabeling the CDS.
They and their product/functional accounts remain intact in the companion JSON.
The GFF3 specification requires a CDS phase and supports repeated feature IDs for
discontinuous features. See the [Sequence Ontology GFF3 specification](https://github.com/The-Sequence-Ontology/Specifications/blob/master/gff3.md).

JSON and GFF3 are separate filesystem replacements. An interruption between their
publication can leave a mismatched pair; the header's companion checksum detects
that condition. Exporting again creates a new consistent pair. This limitation
never changes the authoritative scientific state.
