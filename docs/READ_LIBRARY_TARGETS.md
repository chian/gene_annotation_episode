# Fixed original read libraries

This binding extends the original-material unit of the annotator. It does
not turn a library into a genome, assign one organism to a file, or turn a read
into a gene. Decisions about biological interpretation, useful investigations,
alternatives and subsequent work remain with the responsible Episode. The same
method_loop owns action accounting, numerical continuation and typed forms.

## Identity, custody and fixed geometry

A caller target FASTQ, or caller target collection declared `role=read`, binds to
one `input` descriptor with `target_kind=read_library`. Explicit `target_records`
continues to select actual scalar fragments instead. Files share a library only
when the caller supplies the same `library` declaration; no sample, pairing,
organism or duplicate-molecule inference follows. Acquired/evidence collections
do not become original targets. The binding keeps exact collection/material/source
identities and original bytes, including repeated identifiers and qualities.

The descriptor has `binding_version=fixed_original_read_position_measure_v1`,
`member_count`, `position_mass`, `membership_sha256`, `collection_refs` and
`complete_file_membership`. It has `sequence_ref=null`, and **no** linear `length`
or `unit`. `position_mass` sums original member symbol positions. Its meaning is
coverage of observed supplied material, not unique functions, independent genes,
independent molecules, genome completeness or abundance estimation. Repeated
reads retain multiplicity. Quality/header bytes are provenance, not extra units.

A partial parse freezes only its actual indexed valid members and explicitly
retains `complete_file_membership=false`, parser feedback and unknown/unparsed
remainder. Later evidence registration or reparsing cannot expand this original
membership or an active Episode denominator. Unparsed original bytes survive.
This binding does not implement incremental parser checkpoints or efficient
interrupted FASTQ parsing; the existing returned-prefix/reopen contract remains.

An original read has a lazy identity
`read_subject_<24hex library input ID><24hex original member ID>`. The existing
native member index and library descriptor resolve that pair. No second table
of original reads, per-read input rows, per-read scientific records or sequence
files is created at binding or inventory. Resolving a selected read verifies its
actual original membership. Its namespace differs from `collection_member`,
external `reference` and original library `input`.

Each local footprint is:

```json
{"target_ref":"input_<library>","member_ref":"member_<original>",
 "start":3,"end":12,"unit":"nt"}
```

Bounds are half-open on that actual read. Different original members' equal
local coordinates never merge. Existing scalar input footprints omit
`member_ref`. A read's physical derivation mapping names its actual `read_subject`
and retains the established ordered extraction/orientation/codon arithmetic.
Projection to original geometry adds the original library/member pair, without
inventing adjacency between reads. An assembled consensus is not an exact
extraction path; no assembly/consensus adapter or fake concatenation is supplied.

## Store interfaces

| Interface | Meaning |
| --- | --- |
| `get(read_subject_ref)` | Resolve selected original read metadata lazily from its original member. |
| `read_subject_ref(library_ref, member_ref)` | Validate membership and return the stable invertible scientific ID. |
| `coverage(read_subject_ref)` | Actual member-local original footprint. |
| `coverage(library_ref)` | Empty physical footprint: a container has no local sequence. |
| `footprint_from_mapping(mapping)` | Exact scalar/read-local original projection of actual physical path. |
| `footprint_dimension(span)` | `{id,target_ref,member_ref?,length,unit}` for one actual original scalar/read dimension. |
| `scope_dimension_segments(scope, dimension_ref)` | Merged selected local intervals for that one dimension; empty when excluded. |
| `scope_measure(scope,target_ref)` | Fixed scalar/selected-member position mass without untouched member expansion. |
| `iter_scope_coverage(scope,target_ref=None)` | Explicit streaming enumeration of fixed geometry when required. |
| `scope_covers(spans,scope)` | Exact ownership containment, including original member identity. |
| `iter_current_annotations(scope,page_size=100)` | Bounded current-revision pages. |
| `current_assessment_subset(refs)` | Only requested actual current assessment revisions. |

The old list-returning `scope_coverage` raises
`library_scope_requires_streamed_geometry` for implicit full-library scopes. It
continues to return explicit small member-local segments or scalar geometry.
That operational representation error prevents accidental unbounded expansion;
it is not a scientific assessment or continuation rule.

Parent scopes retain few immutable original `subject_refs`. An optional
`read_selection_refs` names fixed original-member selections. These selections
have immutable count/mass/digest and disk-indexed selected read IDs in the same
Store; they do not create another original membership authority. Explicit
`segments` can narrow selected read-local intervals. A child cannot enlarge its
parent's fixed selection or intervals. Selection inventories are paged. Large
selection creation can scan/sort native index rows on disk; adequate throughput
has not been established merely by implementing the interface.

## Ordinary tools and parent forms

`library.members` returns an explicitly bounded page of lazy read subjects in
native member order (caller file order for an explicitly grouped library) and `next_query`. Automatic working state includes library
descriptors/access instructions, not every original read.

`library.select` freezes caller/episode-chosen original `member_refs` or library
inventory `ordinal_ranges`. Inventory ranges are row positions, not genomic
coordinates. Equivalent selections reuse the same descriptor. The tool returns
its exact immutable scope for possible commission; it does not commission a
child or choose an investigation for the Episode.

`library.read` returns one actual original read's bounded sequence/quality
window. It retains the caller molecule and quality encoding. Existing ordinary
sequence viewing, translation, native gene prediction, alignments, selected
searches and downstream scientific commits accept actual read subjects. They
reject the library container as `library_is_not_a_sequence_operand`.

`reads.inspect` executes an explicitly selected batch of original read subjects
as one ordinary action, with a source JSONL, separate member-local observations
and bounded preview. It supplies measurements, not annotation or automatic
credit. Each selected operation has its existing durable replay identity; batch
members are not Episodes or extra parent action observations. The caller-selected
batch list, publication list and current scientific records can still be large;
there is no demonstrated arbitrary-size batch throughput claim.

`reads.align` executes the owner's explicitly selected original reads against one
actual registered reference under the chosen pairwise model. It reuses the exact
same native alignment/publication helper as `sequence.align`; each result retains
its own native source, operand intervals and usable `sequence.sites` mapping.
Independent basic failures identify the affected row/reference and preserve all
successful rows and native partial publications. The batch is one selected action,
with no private Episode loop, nested tool journals or additional score observations.
It assigns no organism, orthology or molecular function.

`reads.map` additionally provides native indexed genomic placements for an
explicit immutable read selection and actual chosen reference operands.
`sequence.sites` can inspect its original-strand local bases, gaps and insertion
boundaries without correction or consensus. Search custody preserves the exact
selection even when no placement is reported. See [NATIVE_READ_MAPPING.md](NATIVE_READ_MAPPING.md)
for caller resources, provenance, controlled previews and current limits.

Hypotheses, assessments, structural/product records and current annotations can
refer to actual read subjects and retain the same source-bound meanings.
Read-local assessment footprints validate original membership, bounds, hypothesis
coverage and assigned scope together. A match on one read cannot name the
library to acquire the other reads' physical extent. Form reference resolution
recognizes `read_subject` and `subject` namespace aliases while excluding disjoint
members under a child's fixed selection. Existing broader scientific accounts
remain visible on their actual member-local overlap, so a child inherits their
current contribution on its own fixed positions. Scientific publications retain
actual member ownership and bounded attribution. Native observed bounds can
localize an assessment of a broader existing hypothesis without an invented
extra footprint; missing inferred attribution remains valid science with its
existing notice and zero spatial credit. Replacing a current assessment cannot
erase its prior outside attribution. Read visibility is not permission to enlarge
a child scope. Unattached custody handles remain
outside scientific forms.

An actual `read_selection` can cross the parent form as a requested typed data
handle, including an examined broader selection. It cannot stand for a biological
entity in an ATOM value or grant authority to change the child's fixed scope.
Logical context ownership follows the actual related original members and
explicit library containers; this does not manufacture physical credit geometry.
Local context remains revisable by its owning child. Whole-library current
annotations require ownership of the full fixed library, even though their
physical footprint is empty.

## Export and remaining binding work

Current JSON keeps the original library descriptor, actual selected scientific
read subjects/records, source/provenance closure, compact fixed selection index
and existing full packed native index/chunks. Unexamined original reads do not
become main JSON scientific nodes or tiny component files. The checksummed
`read_library_indexes` SQLite sidecar retains descriptors and exact selected
membership. The full original membership stays in its portable native indexes.
Move JSON and its `.materials`/`.artifacts` directories together.

For implicit library scopes, `eligible_footprint=null` and `eligible_geometry`
describe original targets, fixed mass and optional selection handles explicitly.
An explicit small scope can retain its actual member-local footprint array.
The null does not mean an empty denominator. Read-local coordinates remain in
authoritative JSON; GFF3 emits no library chromosome or guessed read coordinate
model and records the specific projection exclusion.

A nonmolecular `whole_input_context` account can allocate actual sample, handling
or physiology evidence to a compact fixed original-position set. It does not
broadcast a molecular claim or manufacture a `[0,position_mass)` interval.
`context_account_scope` is the immutable nonempty lineage domain;
`context_scope` is the actual revisable allocation. Frozen selection handles in a
context mask union by original member identity. Whole-library, select-all and
equivalent unions denote the same set; equal mass alone does not establish
identity. Episode scopes retain their nonempty, one-selection-per-library rule.

A `context_allocation` assessment preserves its actual observation kind, source
subjects, direct/transfer/contextual applicability and conditions. Its allocation
is distinct from measured residue mappings. Context annotations on the actual
sample/context subject have `footprint=[]`; detailed credit rows separately name
`contributing_context_segments`. Missing allocation remains valid unlocalized
science with a notice and zero allocation. Explicit `{"subject_refs":[]}` withdraws
only that current allocation while retaining the biological interpretation and
history. A revision must own its old and new allocation. An immutable account
domain is identity, not blanket permission. Narrower children may retain separate
narrower accounts without overwriting a broader owner's current lineage.

Projection v7 partitions actual eligible positions into disjoint cells and uses
the existing best whole coherent account on each cell. Full-library context is
an implicit baseline; exceptional member groups and real local intervals are
resolved on disk. Summary does not instantiate untouched original-read subjects.
Explicit operand pages preserve native measured bounds separately from context
allocation. The axes, weights, softened hypervolume and fixed scope denominator
are unchanged. [EPISODE_CREDIT.md](EPISODE_CREDIT.md) describes the run-bound read.

This engineering implementation is not evidence of intelligent raw-read
annotation or completed adaptive capability. An actual investigation must still
demonstrate useful successive reasoning and parent use of child forms. It adds
no scientific gates, mandatory assembly/stages/children, quality cutoffs, hidden
budgets, extra composer, artificial yields or stopping rules.
