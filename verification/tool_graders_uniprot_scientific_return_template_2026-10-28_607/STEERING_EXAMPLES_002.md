# Proposed scientific-parent STEERING examples 002

2026-10-28. Review text only. This correction preserves
[STEERING_EXAMPLES_001.md](STEERING_EXAMPLES_001.md) and removes internal
completeness bookkeeping from the proposed model-facing display. It is not a
new API response, target annotation, admitted return or implemented prompt.

The authentic values come from the retained 2026-10-23 entity in
`tests/fixtures/uniprot_native/P0AAW1.json`. The fixture README and transport
metadata retain its provenance. Controlled variants below name their single
hypothetical mutation explicitly; they are not additional native observations.

Every example explicitly requests primary accession P0AAW1 and selects that
reference by accession. GO and feature requests use a database criterion or an
entry interval, never prior knowledge of native row indices. None requests a
whole-source or full-sequence-artifact grant. These questions do not depend on
release, so release is neither requested nor displayed. The seven exact
selections, retained internal qualifications and expected scientific values are
in [EXAMPLE_SELECTIONS_002.json](EXAMPLE_SELECTIONS_002.json).

The parent retains the entire TASK in
[TASK_CONSTRUCTION_001.md](TASK_CONSTRUCTION_001.md), including its original
supplied target and selected scientific guidance. Each block below is only the
UniProt insertion within STEERING, after the unchanged parent-owned yield
table. No parent history was supplied here; no yield or controller values have
been invented. Full typed extents, counts and state distinctions remain
internal even when their redundant bookkeeping is absent from this text.

## A. Requested sequence information: authentic retained values

Parent's decision question: What reference sequence window is available for
comparison with the supplied target, and is there a material length
qualification?

The request selects the protein name at offset 0 / limit 40 and the reference
sequence interval `[9,19)` aa. This does not require the target to have a name.

Proposed model-facing insertion:

---

Returned UniProt reference facts

Reference: **P0AAW1**.

| Requested value | Received value |
| --- | --- |
| Reference protein name | Uncharacterized protein YbhP |
| Reference sequence window [9,19) aa, zero-based half-open | `FKVLTINIHK` |
| Reference sequence length | 253 aa |

These values describe the reference. Target/reference correspondence has not
been established by this return.

---

The letters and length were checked directly against the retained fixture with
stdlib JSON/string operations. The selected protein-name text is the entire
native value. Its complete extent and agreeing observed/reported lengths stay
in the selected typed value; no character-count or zero-omission rows are
needed in STEERING. This is not a new alignment.

## B. Requested GO information: authentic retained values

Parent's decision question: Which GO links does the selected reference carry,
and what native term, attribution and associated evidence accompany them?

The request uses `database=GO`, includes associated native evidence and selects
offset 0 / limit 80 for `GoTerm` and `GoEvidenceType`. All four selected texts
are whole native values.

Proposed model-facing insertion:

---

Returned UniProt reference facts

Reference: **P0AAW1**.

| GO identifier | GoTerm | GoEvidenceType | Evidence on this GO cross-reference |
| --- | --- | --- | --- |
| GO:0005886 | C:plasma membrane | HDA:EcoCyc | ECO:0007005; PubMed 32127419. |
| GO:0003824 | F:catalytic activity | IEA:InterPro | Requested native evidence container absent. |

These are reference annotations and attribution metadata. The absent container
does not establish absence of supporting evidence elsewhere.

---

The database criterion and successful membership supply the GO relationship;
the identifier prefix is not used to infer it. `HDA:EcoCyc` and `IEA:InterPro`
remain exact native property text. The ECO/source tuple belongs only to the
first displayed GO cross-reference. No cited publication is read or graded;
no target annotation or new confidence number is inferred. Counts of other
native databases and the aggregate internal partial status add no further
scientific qualification beyond the affected evidence cell here.

## C. Requested feature positions: authentic retained values

Parent's decision question: Which entry-sequence features have positions
overlapping reference interval `[9,20)` aa, and are their positions exact?

The request uses entry-interval overlap, selects offset 0 / limit 40 for each
type and description, and does not request feature evidence.

Proposed model-facing insertion:

---

Returned UniProt reference facts

Reference: **P0AAW1**. Requested entry interval: **[9,20) aa**.
Intervals below use zero-based half-open aa coordinates.

| Feature type | Description | Exact entry interval |
| --- | --- | --- |
| Chain | Uncharacterized protein YbhP | [0,253) aa |

These positions belong to the reference entry; no target-coordinate mapping is
part of this return.

---

The exact interval is copied from the admitted typed value, not recalculated
by the presentation. The parser has established entry-sequence binding. Its
absent native sequence-ID leaf does not qualify that established relationship
and is not displayed. Exact native endpoints, complete text extents and
membership counts remain internal. The unrequested native feature ID is not
added.

## D. Controlled partial variant: nonexact feature position

**Illustrative mutation, not an authentic result:** change only the retained
chain feature's start modifier from `EXACT` to `BEFORE`. Use C's original
selection. The selected type and description are unchanged.

Proposed model-facing insertion:

---

Returned UniProt reference facts

Reference: **P0AAW1**. Requested entry interval: **[9,20) aa**, zero-based
half-open.

| Feature type | Description | Native endpoints, 1-based inclusive aa | Interval qualification |
| --- | --- | --- | --- |
| Chain | Uncharacterized protein YbhP | Start 1 (BEFORE); end 253 (EXACT) | Exact entry interval unavailable; overlap indeterminate. |

---

The native fuzzy endpoints explain the unresolved overlap. The display neither
converts the start to an exact boundary nor supplies a positive or negative
overlap conclusion. It does not invent a field failure when the typed value
instead carries a feature-location qualification and indeterminate membership.

## E. Controlled partial variant: database membership is unknown

**Illustrative mutation, not an authentic result:** replace the native database
field of the GO:0005886 cross-reference with JSON null. Leave its identifier,
requested properties and associated evidence intact. Use B's original
`database=GO` selection. The mutation's audit pointer is internal; the parent
does not request an array index.

Proposed model-facing insertion:

---

Returned UniProt reference facts

Reference: **P0AAW1**.

| GO membership | Native identifier | GoTerm | GoEvidenceType | Evidence on this cross-reference |
| --- | --- | --- | --- | --- |
| Indeterminate: native database is null | GO:0005886 | C:plasma membrane | HDA:EcoCyc | ECO:0007005; PubMed 32127419. |
| Matched | GO:0003824 | F:catalytic activity | IEA:InterPro | Requested native evidence container absent. |

These are reference annotations and attribution metadata. GO membership of the
first cross-reference is unresolved; its identifier text does not supply the
missing database value. The absent evidence container does not establish
absence of supporting evidence elsewhere.

---

The indeterminate member and its associated scientific values remain visible.
Counts of excluded non-GO cross-references are not needed for this decision.

## F. Controlled partial variant: requested sequence unavailable

**Illustrative mutation, not an authentic result:** remove only
`/sequence/value` from the retained input. Use A's original selection. The
requested accession and protein name remain present. No sequence window or
accompanying window-length tuple is returned.

Proposed model-facing insertion:

---

Returned UniProt reference facts

Reference: **P0AAW1**.

| Requested value | Received value |
| --- | --- |
| Reference protein name | Uncharacterized protein YbhP |
| Reference sequence window [9,19) aa, zero-based half-open | Unavailable: requested sequence material unavailable. |

---

The qualification comes from the selected `sequence_unavailable` failure. The
display does not infer a more specific native state than the selected return
contains. No letters, zero length or reconstructed length tuple are inserted.
A separately requested native reported-length field could remain available;
this selection did not request it separately.

## G. Controlled partial variant: reported and observed lengths conflict

**Illustrative mutation, not an authentic result:** change only
`/sequence/length` from 253 to 254, keeping the 253 native sequence letters
unchanged. Use A's original selection. This demonstrates a material
qualification; it is not a newly observed inconsistency in P0AAW1.

Proposed model-facing insertion:

---

Returned UniProt reference facts

Reference: **P0AAW1**.

| Requested value | Received value |
| --- | --- |
| Reference protein name | Uncharacterized protein YbhP |
| Reference sequence window [9,19) aa, zero-based half-open | `FKVLTINIHK` |
| Reference sequence length | Observed sequence 253 aa; native reported length 254 aa. Lengths conflict. |

These values describe the reference. Target/reference correspondence has not
been established by this return.

---

Both lengths are shown because their disagreement qualifies use of the returned
sequence. The selected letters and original interval are preserved; the display
does not repair either length or request a new calculation.

## Selection-to-text rules for remaining states

These examples are concise insertions, not an instruction to print every
internal cell. Every requested scientific value and material qualification
retains its meaning. Redundant internal extents, aggregate status and unrelated
collection counts stay internal.

| Admitted selected state | Model-facing meaning when relevant to the next decision |
| --- | --- |
| Whole text value | Exact value alone; no character-count or zero-omission row. |
| Truncated or interior text window | Exact returned text plus one concise excerpt qualification. Include actual window placement when it affects meaning; do not insert an ellipsis into the value. |
| Present empty text | Explicitly empty native text; distinguish it from a nonempty native value whose requested window is empty. |
| Window starts beyond native text | Empty requested window; give the requested offset and actual native length to explain why. |
| Requested native collection present and empty | No members in the requested native collection. |
| Requested native collection absent, null or invalid | Preserve that specific state; do not report a complete negative scientific result. |
| Native token present but requested representation unavailable | State that the requested representation is unavailable; do not invent text. |
| Requested sequence interval exceeds actual length | Requested interval unavailable with the relevant length qualification; no clipping or padding. |
| Feature location refers to another or an unresolved sequence | Retain that relationship when it limits the requested position interpretation. |
| Requested selection includes an indeterminate member | Show that member and the reason its membership is unresolved. |
| Partial acquisition limits completeness | State the material limitation on the requested set; retain available selected values. Do not print every unrelated count. |
| Unavailable publication or no completed acquisition | Requested facts unavailable for that reason; not an empty biological result. |
| Delivery rejected | Actionable delivery failure; no selected facts admitted by that attempt. |
| Release matters to the original scientific question | Request and display the selected native release; no automatic provenance row in other questions. |

Owner relationships use requested native identifiers and readable reference,
feature or property labels. Duplicate native IDs in distinct admitted entries
stay separate using minimal local association labels. Host authentication
identities never become displayed sources or available material. Explicit
source/sequence grants retain H's admitted meanings and do not establish an
unimplemented downstream tool binding.
