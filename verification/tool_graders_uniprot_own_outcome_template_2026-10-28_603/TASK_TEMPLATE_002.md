# UniProt own-outcome TASK — additive review correction 002

This corrects the same boundary proposed in 001. The original broad draft remains
preserved for comparison. Root's review asked for a concrete results task that
uses deterministic selected facts rather than instructing the model to parse
or filter them, and that carries only the assignment information needed by this
API results child. No application/runtime/prompt code is changed.

This review example uses exactly the field selection in the partial example of
`STEERING_FIXTURES_002.md`: all native records on the assigned search page, with
the seven selected field families shown below. It assumes the assigned page is
the original retained response and the form requests no interpretation fields.
These are illustrative assignment operands, not claims about a real run. The
actual query, page-size operand, resource constraints and additional selected
instruction sections were not supplied; their marked slots are filled only
from the original commission. No target sequence or parent scientific task is
needed to obtain this selected response.

The three responsibilities are explicit: the episode chooses its next useful
action; the original assignment specifies the fixed job and requested return;
the selected tool/resource information explains what actual operations do.
Deterministic readers populate the requested native fields. The complete text
between the delimiters is the proposed recurring TASK for this selection.

--- BEGIN TASK TEMPLATE ---

TASK

Acquire the assigned results and return the information requested below.
Choose each next action using the outcomes already obtained, the specific
remaining acquisition or representation problem, and your own yield information.
Preserve valid partial results and their qualifications. Keep the original job,
page selection, resource and parent constraints fixed throughout this episode.

Deterministic readers apply the original record and field selections, validate
the source associations, and populate the recorded return fields. Use their
values, availability states and qualifications to decide what further permitted
work is useful. Parsing native records, filtering collection members, deriving
coordinates and assigning numerical scores are not decisions assigned to you.

The fixed job and requested return are:

| Assignment | Required value or meaning |
| --- | --- |
| Service and input | UniProtKB; the original retained JSON search response |
| Original query | {exact original assigned search query} |
| Original page request | {exact original page-size operand and cursor, if one was supplied} |
| Acquisition selection | Publish that retained response through the original handoff; the results selector is empty |
| Resource and constraints | {original configured API resource's meaningful name and all constraints relevant to this acquisition} |
| Requested records | All native records on this assigned page, preserving their original positions and unavailable-record states |
| Return purpose | Supply the selected native values and the qualifications needed to understand their availability and extent |
| Interpretation fields | None requested; recorded fact fields are populated deterministically |
| Material delivery | Selected text and sequence windows only; no whole-source or full-sequence-artifact grant |

Each populated field has the following requested meaning:

| Selected field | Exact requested extent and meaning |
| --- | --- |
| Primary accession | The returned entry's native primary accession. It identifies the retrieved entry. A malformed record retains its unavailable-record qualification. |
| Taxon ID | The native organism taxon identifier. It is an identifier, not a score. Absent, null and invalid values remain distinct from a numerical value. |
| Observed sequence length | The deterministic reader's existing length of the retained entry sequence, in amino acids. It is distinct from any provider-reported length. |
| Protein name | The recommended full-name value, characters [20,60), counted as zero-based Unicode code points. The return includes the full native character count and omitted prefix/suffix lengths. A shorter or empty value retains its actual extent and state. |
| Sequence window | Exactly [9,19) of the retained entry sequence, using zero-based half-open amino-acid coordinates. An available window contains ten residues. Missing sequence or an out-of-range request remains unavailable. |
| GO cross-references | All native cross-references whose database value is GO, with each database/identifier association preserved. No property text or associated evidence was requested. The deterministic selection supplies matched, indeterminate, unavailable and excluded member counts. |
| Overlapping features | Native entry-sequence features selected for overlap with [9,20) in zero-based half-open amino-acid coordinates. The return preserves native one-based inclusive endpoints and any supplied exact derived interval. Fuzzy or unresolved membership remains indeterminate. Feature descriptions, type text and associated evidence were not requested. |

Use the supplied qualifications when judging whether another action can resolve
an outstanding problem. Native JSON validity, parser completeness, the number
of records bound into stored results, and the outer acquisition status describe
different things. A malformed sibling can leave valid requested records
available. A legacy label or term may be unavailable while the selected native
name window remains valid. A genuinely absent field is itself a result; it
does not call for an invented replacement value.

The response covers one assigned page. Whole-query completeness is a separate
recorded fact. An indicated next page does not change this assignment, and
unavailable pagination metadata leaves whole-query completeness unknown. An
indeterminate collection member does not establish absence. A present empty
selected collection is distinct from an absent, null or invalid collection.
Retrieved labels and cross-references describe the retrieved entries; their
presence is not a probability that a gene-function annotation is correct.

Selected tool and resource information:

`api.uniprot.collect` publishes the retained original UniProt response, or obtains
the explicitly selected cursor page of the original query. It performs no
automatic page traversal or target annotation. For this assignment the empty
results selector selects the retained original response. The action takes no
arguments. Replaying an already selected action reuses its original outcome;
choosing another acquisition is a new decision about this same fixed assignment.

{Full substantive text of any additional tool/resource instruction sections
actually selected for this acquisition. Omit this paragraph when none were
selected. Library headings, provenance and unrelated launch instructions are
not substitutes for those sections.}

The available operations relevant to this results decision are:

| Operation or action | Meaning and operands |
| --- | --- |
| api.uniprot.collect | Acquire/publish the original assigned response. No action arguments. |
| knowledge.search | Search the instruction index using literal query terms, a nonnegative offset and a positive result limit; an empty query lists entries. This discovers instructions, not molecular evidence. |
| knowledge.entry | Read a selected instruction entry's section index using its returned entry operand. A listed tool is not necessarily enabled for this episode. |
| knowledge.read | Read an identified instruction section using its returned entry/section operands, zero-based line offset and positive line count. Instructions inform choices; they do not change the assignment or enable operations. |
| episode.estimate_wait | Inspect the supported estimate for a proposed wait condition using received progress and original timing information. The operation selects no wait or work. |
| wait | Select an actually available event condition or reconsideration time using the supplied wait contract. Event targets and received cursors must come from the episode's actual available information. |

UniProt acquisition returns an immediate response. No remote UniProt job or
UniProt status-polling operation is supplied here. Consider waiting only from
the received facts and the available wait conditions. Instruction reads and
waiting are optional choices, with no required order or fixed cadence. If a
failure has no available repair within this assignment, preserve its specific
recorded qualification. The tool descriptions do not choose a retry, another
page or a substitute job.

Return the required closed decision response. In the configured exchange
protocol, `request_context` obtains explicitly requested information about your
own prior attempts and continues this same pending decision. It creates no
completed action. Use `select_action` with the selected action and
`report_update` when ready to dispatch work. This assignment's `report_update`
has no interpretation fields; the host supplies the requested recorded facts.
Do not add a narrative return or manually compose those facts.

The own-action table records your completed categories and signed gains,
excluding inherited credit. Expected category yield is conditional on completing
that category again; unavailable is not zero. Its uncertainty bands are not
guarantees. Keep category expectations distinct from the current controller
expectation. Only an actual completed own action supplies a controller
observation; field projection, report construction and reconstruction do not.

The configured controller owns continuation. Validated completion of the
original practical assignment makes future expected gain exactly zero through
the existing controller comparison, retaining the final actual gain. The
original typed form returns at closure, including valid partial facts if the
episode yields. No additional final decision or report-composition call is
required. Every decision and requested-information continuation receives this
complete TASK again; STEERING contains only the current facts needed for the
next choice.

--- END TASK TEMPLATE ---

## Matching STEERING for review

Use the partial block between `BEGIN PARTIAL STEERING FIXTURE` and
`END PARTIAL STEERING FIXTURE` in `STEERING_FIXTURES_002.md` unchanged. It remains
explicitly illustrative, contains the requested selected native values and
qualifications, and uses placeholders for existing own-yield/controller inputs.
The complete-response block remains a rendering example only; a validated
terminal endpoint does not dispatch an extra prompt.

## Exact expansion and limits

The query/page/resource slots carry only the original API assignment needed to
identify and acquire this response. They never contain a full target sequence,
the parent's scientific investigation, parent yields, unrelated molecular scope,
receipt/witness IDs, hashes or stored context.

The seven field rows are concrete to the accompanying fixture selection. For a
different original selected return, the deterministic prompt builder expands
the detailed meanings of the fields actually requested. Unselected field-family
guidance is omitted; no generic EC/evidence/isoform tutorial is appended. An
originally requested interpretation field would retain its exact declared type,
allowed values and meaning instead of this fixture's “None requested” row.

The collect description and empty-argument behavior are from the actual
`UniProtService.result_capabilities` / `prepare` path. Knowledge operations are
from the actual `tool_knowledge.catalog`; API results currently permits the
shared wait action and `episode.estimate_wait`. The renderer uses the actual
catalog for the dispatched decision; an unavailable operation gets no row.
It must not advertise launch/submission, a UniProt status poll, a local file
reader, or a parser-repair operation merely because another resource role has
one. Additional selected library information is copied in full from the actual
selected sections, not invented for this review fixture.

This additive text correction does not change the original response schema,
return schema, selected values, intermediate shape, credit or continuation.
It replaces the proposed TASK wording for review only. 001's verbatim broad
source instructions remain preserved and are not claimed to be the final
appropriate API-only task.
