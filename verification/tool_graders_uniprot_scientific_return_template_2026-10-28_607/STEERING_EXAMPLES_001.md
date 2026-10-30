# Proposed scientific-parent STEERING examples

These are review text for the immediate results-child → scientific-parent
boundary. They are not model output, a new API response, a new target annotation,
or evidence that admission/presentation has run.

The authentic values are read from the retained 2026-10-23
`tests/fixtures/uniprot_native/P0AAW1.json` and its transport metadata. The
fixture README identifies the exact historical entity. The later controlled
cases change only the explicitly named input field; their hypothetical outputs
must never be represented as the authentic UniProt entry.

Every example requests the primary accession explicitly, selects the reference
by primary accession P0AAW1, requests native release, and requests no whole
source or full-sequence-artifact grant. GO and feature requests use a database
criterion or an entry interval, never foreknowledge of native member indices.
The exact six selection objects and provenance are in
[EXAMPLE_SELECTIONS_001.json](EXAMPLE_SELECTIONS_001.json).

The parent retains the entire TASK described in
[TASK_CONSTRUCTION_001.md](TASK_CONSTRUCTION_001.md). Its original supplied target
can remain unnamed and its function unresolved. The following blocks are only
the UniProt insertion within STEERING, after its unchanged own action/yield
table. No parent yield history was supplied for this design task, so no observed
yield, expected gain, uncertainty or controller value has been invented here.

## A. Requested sequence information: authentic retained values

Parent's decision question: What exact reference sequence window is available
for comparing with the supplied target, and does its length carry a conflict?

The request selects a protein-name text window with offset 0 / limit 40 and
sequence `[9,19)` aa. Neither requires the target to have this reference's name.

Proposed model-facing insertion:

---

Returned UniProt reference facts

Reference: **P0AAW1**. UniProtKB release: **2026_03**.

| Requested value | Received value | Extent or qualification |
| --- | --- | --- |
| Reference protein name | Uncharacterized protein YbhP | Characters [0,28) of 28; requested offset 0, limit 40; omitted prefix 0, suffix 0. |
| Reference sequence window | `FKVLTINIHK` | [9,19) aa, zero-based half-open. |
| Lengths carried with the window | Stored sequence 253 aa; native reported length 253 aa | Reported length present; lengths agree. |

The sequence letters and name describe the reference entry. Target/reference
correspondence has not been established by this return.

---

The ten letters, the 253-aa observed and reported lengths, and the 28-character
name were checked directly against the retained fixture with stdlib JSON/string
operations. This is not a new alignment or scientific calculation. Character
coordinates count decoded Unicode code points; residue coordinates count aa.

## B. Requested GO information: authentic retained values

Parent's decision question: Which GO links does the selected reference carry,
and what native term, attribution and associated evidence accompany them?

The request uses `database=GO`, includes owned evidence and selects offset 0 /
limit 80 for the exact properties `GoTerm` and `GoEvidenceType`. The original
native positions happen to be 31 and 32, but those indices are not request
operands and are unnecessary in this unambiguous display.

Proposed model-facing insertion:

---

Returned UniProt reference facts

Reference: **P0AAW1**. UniProtKB release: **2026_03**.

GO selection: **2 matched, 0 indeterminate, 0 unavailable, 40 excluded** from
42 native cross-references. Requested GO field: **partial** because one
requested evidence container is absent.

| Native database / identifier | GoTerm text | GoEvidenceType text | Owned native evidence |
| --- | --- | --- | --- |
| GO / GO:0005886 | C:plasma membrane | HDA:EcoCyc | ECO:0007005; source PubMed; source identifier 32127419. Owner: this GO cross-reference. |
| GO / GO:0003824 | F:catalytic activity | IEA:InterPro | Evidence container absent for this GO cross-reference. |

| Text field | Received characters / native length | Omitted prefix / suffix |
| --- | --- | --- |
| GO:0005886 GoTerm | [0,17) / 17 | 0 / 0 |
| GO:0005886 GoEvidenceType | [0,10) / 10 | 0 / 0 |
| GO:0003824 GoTerm | [0,20) / 20 | 0 / 0 |
| GO:0003824 GoEvidenceType | [0,12) / 12 | 0 / 0 |

All text windows requested offset 0, limit 80 Unicode code points. These are
native annotations and attribution metadata for the reference. The absent
container does not establish absence of supporting evidence elsewhere.

---

`HDA:EcoCyc` and `IEA:InterPro` remain exact native property text. The ECO tuple
belongs to the first GO cross-reference, not the second, the full protein or
the target. No cited publication is opened or interpreted. No mapping to a
confidence number or target annotation is performed. The partial status does
not erase the available identifiers or properties.

## C. Requested feature positions: authentic retained values

Parent's decision question: Which entry-sequence features have positions
overlapping reference interval `[9,20)` aa, and are their positions exact?

The request uses entry-interval overlap, selects offset 0 / limit 40 for each
type and description, and does not request feature evidence.

Proposed model-facing insertion:

---

Returned UniProt reference facts

Reference: **P0AAW1**. UniProtKB release: **2026_03**.

Requested entry interval: **[9,20) aa**, zero-based half-open.
Feature selection: **1 matched, 0 indeterminate, 0 unavailable, 0 excluded**
from 1 native feature.

| Feature type | Native start | Native end | Exact entry interval | Sequence relationship |
| --- | --- | --- | --- | --- |
| Chain | 1; EXACT | 253; EXACT | [0,253) aa | Entry sequence; native sequence identifier absent. |

Native endpoints use 1-based inclusive aa coordinates. The exact interval uses
zero-based half-open aa coordinates.

| Selected feature text | Received value | Characters / native length | Omitted prefix / suffix |
| --- | --- | --- | --- |
| Type | Chain | [0,5) / 5 | 0 / 0 |
| Description | Uncharacterized protein YbhP | [0,28) / 28 | 0 / 0 |

Both text windows requested offset 0, limit 40 Unicode code points. These
positions belong to the reference entry; a target-coordinate mapping is not
part of this return.

---

The returned exact interval is copied from P's derived value. The presentation
does not convert endpoints again. The absent native sequence identifier is
distinct from unresolved sequence binding: P explicitly binds this case to the
entry sequence. The unrequested native `featureId` is not automatically shown.

## D. Controlled partial variant: nonexact feature position

**Illustrative mutation, not an authentic result:** change only the retained
chain feature's start modifier from `EXACT` to `BEFORE`. Use the same criterion
and requested fields as C. The original feature's type and description remain
the same illustrative selected values. Do not treat the hypothetical body as a
new retained API observation.

Proposed replacement for C's membership and position rows:

---

Feature selection for **[9,20) aa**: **0 matched, 1 indeterminate, 0 unavailable,
0 excluded** from 1 native feature. Requested position field: **partial**.

| Feature type | Native start | Native end | Exact entry interval | Sequence relationship |
| --- | --- | --- | --- | --- |
| Chain | 1; BEFORE | 253; EXACT | Unavailable | Entry sequence. |

Native endpoints are 1-based inclusive aa coordinates. The nonexact start leaves
overlap indeterminate. No exact interval is supplied.

---

The primary accession, requested release and unchanged type/description windows
remain rendered exactly as in C. This variant supplies neither an overlap nor a
no-overlap conclusion. No new field failure is invented where the contract
supplies a native feature-location qualification and indeterminate membership.

## E. Controlled partial variant: database membership is unknown

**Illustrative mutation, not an authentic result:** replace the native database
field of the authentic GO:0005886 cross-reference with JSON null, leaving its
identifier, requested properties and owned evidence intact. Use the exact
selection from B. Mutation provenance uses its original array index only to
describe the controlled change; the parent still requests `database=GO`.

Proposed replacement for B's membership and value rows:

---

GO selection: **1 matched, 1 indeterminate, 0 unavailable, 40 excluded** from
42 native cross-references. Requested GO field: **partial**.

| Membership | Native database / identifier | GoTerm text | GoEvidenceType text | Owned native evidence |
| --- | --- | --- | --- | --- |
| Indeterminate | Database null / GO:0005886 | C:plasma membrane | HDA:EcoCyc | ECO:0007005; source PubMed; source identifier 32127419. Owner: this cross-reference. |
| Matched | GO / GO:0003824 | F:catalytic activity | IEA:InterPro | Evidence container absent for this GO cross-reference. |

The identifier text does not determine the missing database value. The first
member's GO membership remains indeterminate.

---

B's requested release and exact property-window extents still accompany these
values. The presentation does not infer `database=GO` from an identifier prefix
or silently discard the indeterminate member to claim a complete GO set.

## F. Controlled partial variant: requested sequence unavailable

**Illustrative mutation, not an authentic result:** remove only `/sequence/value`
from the retained input. Use A's original selection. Requested native identity
and protein name remain present. The unavailable sequence-window reply is null,
so its usual accompanying observed/reported-length tuple is not returned.

Proposed replacement for A's sequence and length rows:

---

| Requested value | Received value | Qualification |
| --- | --- | --- |
| Reference sequence window [9,19) aa | Unavailable | Requested sequence material unavailable. |

---

A's primary accession, release and selected name/window rows remain. No sequence
letters, zeros or reconstructed length tuple are inserted. An independently
requested native reported-length field could remain available, but this
selection did not request it independently and the display does not add it.

## Missing-state language and source relationships

The examples above are insertions, not a generic dumping format. For other
admitted selected cells, the same deterministic presentation keeps these exact
differences:

| Recorded selected state | Display meaning |
| --- | --- |
| Present empty collection with known count 0 | Empty requested native collection; no selected members. |
| Absent collection | Requested native collection absent. |
| Native null | Requested native value null. |
| Invalid native type | Requested native field invalid; no substituted value. |
| Present token, representation unavailable | Native value present; requested token representation unavailable. A text value is not invented. |
| Present empty text | Empty text; native length 0; extent and omission counts as supplied. |
| Window starts beyond native text | Empty requested window; supplied offset, native length and offset-past-end extent. |
| Requested sequence interval exceeds actual length | Requested interval unavailable; no clipping or padding. |
| Exact feature on another native sequence | Excluded from an entry-sequence overlap query; no entry interval invented. |
| Requested collection includes an indeterminate member | Preserve that member and its qualifications; no complete negative finding. |
| Unavailable native publication or no completed acquisition | Requested facts unavailable for that reason; not an empty biological result. |
| Delivery rejected | Actionable delivery failure; no selected facts admitted by that attempt. |

Owner relationships are retained with readable reference/feature/property
labels. If duplicate requested native IDs occur, distinct response/entry
occurrences remain separate; only local association labels are added. A literal
source grant supplies authorized material only when explicitly requested and
admitted. This display does not turn authentication witnesses into callable
materials or claim a new downstream sequence-tool binding.
