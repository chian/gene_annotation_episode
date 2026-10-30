# Own-acquisition STEERING — additive decision-relevance correction 003

These are **illustrative rendering fixtures**, not API results, saved runs,
scientific measurements or executed tests. The acquisition states and counts
come from the invented fixtures in 002. Yield and controller cells remain
placeholders for existing inputs; no yield has been invented or calculated.
The partial example additionally stipulates that no repair-enabling event or
pending work was supplied to this decision. Real rendering must inspect the
actual received information before making that statement.

Use the complete recurring TASK in `TASK_TEMPLATE_002.md` unchanged. This
additive correction replaces only the own-decision STEERING and intermediate
selection. All earlier drafts remain preserved. The original typed return
still contains every requested native value and qualification. This episode's
next-decision message does not repeat those values merely because its parent
requested them at closure.

## A. Completed acquisition

This is a conditional rendering example. When the existing practical endpoint
is validated, the controller closes the episode without dispatching this
extra prompt. No completion-composition call or additional observation is added.

--- BEGIN COMPLETE STEERING FIXTURE ---

STEERING

| Own action category | Completed | Total signed yield | Expected next yield | Uncertainty / unavailable reason | Uncompleted attempts |
| --- | --- | --- | --- | --- | --- |
| tool/api.uniprot.collect | <saved completed count> | <saved signed total> | <saved category estimate or unavailable> | <saved band or unavailable reason> | <saved uncompleted count> |

| Current continuation | Supplied value |
| --- | --- |
| Expected next gain; uncertainty; cost | <existing controller values, including exact zero only when actually validated> |

| Latest own acquisition | Decision facts |
| --- | --- |
| Status | Completed; complete JSON; parser complete |
| Requested extent | 1 of 1 requested record usable; all selected fields available |

--- END COMPLETE STEERING FIXTURE ---

## B. Partial acquisition using the retained response

The original empty results selector makes another collect reuse the same
retained response. It cannot replace malformed native content, change an absent
field, resolve fuzzy native data or alter the original requested windows. The
episode still owns its next choice among available operations; this statement
adds no stopping rule. Publication/binding failure and a native-data limitation
remain separate conditions.

--- BEGIN PARTIAL STEERING FIXTURE ---

STEERING

| Own action category | Completed | Total signed yield | Expected next yield | Uncertainty / unavailable reason | Uncompleted attempts |
| --- | --- | --- | --- | --- | --- |
| tool/api.uniprot.collect | <saved completed count> | <saved signed total> | <saved category estimate or unavailable> | <saved band or unavailable reason> | <saved uncompleted count> |

| Current continuation | Supplied value |
| --- | --- |
| Expected next gain; uncertainty; cost | <existing controller values> |

| Latest own acquisition | Decision facts |
| --- | --- |
| Status | Partial; complete JSON; parser partial |
| Acquisition input | Retained response; another collect uses these same bytes |
| Requested extent | 2 of 3 requested records usable; other selected fields available except as qualified below |

| Requested item | Availability and unresolved qualification |
| --- | --- |
| Native position 1: all selected fields | Unavailable: native record is not an object |
| Native position 0: protein-name window | Requested window available; legacy label and term cannot represent the native name |
| Native position 0: GO cross-reference collection | Usable partial collection: 2 matched members; 1 membership indeterminate because its database field is invalid |
| Native position 0: overlapping-feature collection | Usable partial collection: 1 matched member; 1 membership indeterminate because its location is fuzzy |
| Native position 2: taxon ID and protein-name window | Native fields absent; their absence is preserved in the requested return |

The available catalog supplies no native-content or parser-repair operation.
No repair-enabling wait condition was supplied for this attempt.

--- END PARTIAL STEERING FIXTURE ---

## Why these facts reach this receiver

The detailed action/information trace is `DECISION_INFORMATION_TRACE_002.md`.
Acquisition status and qualified extent distinguish a whole acquisition problem
from valid partial work. Each qualification locates the exact original request
affected and states whether there is useful acquired material or an unresolved
native/binding limitation. Retained-input behavior and the actual catalog bound
what another collect could change. Received wait conditions, when present, can
support a wait choice. None of these facts selects work on the episode's behalf.

Returned accessions, taxon values, sequence lengths and letters, native name
text/lengths, GO identifiers, feature coordinates and excluded-member counts
are omitted here. They do not change the available action or its immutable
operands. Requested biological values remain exact in the parent-defined typed
return and full native publication. The field labels above identify requests;
they are not a copy of biological return values.

Next-page links, total-query counts, release metadata and whole-query
completeness are also omitted. This results child cannot select another page;
its endpoint is the originally assigned response. No pagination detail in these
fixtures supports a different action or a repair. Those facts remain in their
original internal/typed locations when requested.

The complete example contains no repair rows because it has no unresolved
acquisition problem. The partial example contains no recommended retry, new
page, fabricated delay, parent yield, private history, host/source/witness ID,
new numerical score or model-composed return.

## Other conditions within the same boundary

* A binding omission is identified as a binding omission at its original native
  position. Do not relabel it as malformed source data. Keep any actually
  supplied binding-repair condition; do not invent a repair operation.
* Missing publication gives `publication_unavailable` and unknown selected
  extent, preserving the real acquisition. It does not become an empty result.
* A present empty selected collection needs no exception row. It is already
  covered by “selected fields available.” An absent, null or invalid requested
  field retains its corresponding specific qualification.
* An unmatched original selector retains its exact request location and
  no-match/indeterminate qualification. It supplies no fabricated record and
  no new selection. Known selector operands already belong in TASK.
* An unavailable explicitly requested material grant is a return-availability
  qualification. It does not grant or print the material or advertise a new read.
* A new repair-enabling event or actual wait target is included only if already
  supplied and usable with the current catalog. A timer choice remains possible
  under the shared wait contract; a missing service job is not a promised future
  change to the retained response.

These are requirements for later integration verification, not executed checks.
