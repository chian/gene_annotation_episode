# Proposed full recurring TASK for this boundary

Design status: awaiting the user's running feedback under
`docs/TASK_AND_STEERING.md`. This is not implemented. The template is for the
existing results episode after its own UniProt acquisition; it creates no new
episode type or parent/ancestor message. Braced slots below are filled from the
original assignment and registered contract, not model-written recaps. Each
filled selected instruction section is repeated in full on every decision and
lookup continuation. Optional blocks appear only when the actual corresponding
context/protocol exists.

The paragraph beginning “Acquire the original” is the complete current
`ExecutionEpisodes.instructions` results body. The following two library
paragraphs are the complete current additions from `tool_knowledge.INSTRUCTIONS`
and `launch_instructions.INSTRUCTIONS`. The exchange block uses the existing
text variant from `decision_context.TEXT_INSTRUCTIONS`, with the existing
`text_instructions` replacement of “After its decision_lookup_result arrives”.
This preserves the current detailed instruction content while adding the
specific assignment and requested-information meanings. No generic scientific
annotation instructions are substituted for the results role.

The delimiter lines mark model-facing text. Source paths and design notes above
and below them are not prompt text.

--- BEGIN TASK TEMPLATE ---

TASK

Acquire the original selected execution results through the original handoff.
Choose bounded status or requested file/page reads using actual preceding
outcomes. Preserve partial bytes and native scores. Native paths expose the
current resource filesystem: the exact attempt observation does not establish
that current file bytes were produced by that attempt. Separate read windows
are not an atomic file snapshot. The scientific parent interprets the returned
records. Original work, resource and selector stay fixed. Only actual complete
acquisition establishes this endpoint.

Acquire and return the following UniProtKB information for the assigned molecular
investigation: {original full objective and information need}. Use the supplied
inputs and selected request below. Retrieved entry annotations are claims about
those entries; they do not by themselves establish the supplied target's function.

| Fixed assignment | Supplied value |
| --- | --- |
| Molecular investigation and supplied target/input | {full assigned target/input description and relevant supplied contents or snippets} |
| Scope | {full assigned scope and any original coordinate limits, in their stated units} |
| Parent constraints | {all original applicable constraints, as meaningful text} |
| Service and representation | UniProtKB; one JSON record or one selected JSON search page |
| Original operation | {record or search; retain the original alias's exact endpoint meaning when applicable} |
| Original accession or query | {exact assigned accession or query; never infer it from the response} |
| Assigned page | {the immutable cursor/size selection; or retained original response when the selector is empty} |
| Requested result | {the parent's complete original requested result meaning} |

Use `api.uniprot.collect` with no action arguments to obtain this assignment's
result. With an empty assigned selector it publishes the retained original
response; with the original explicit cursor/size selector it obtains that one
page of the same query. This operation does not traverse pages automatically.
A continuation link describes an available page; it does not change your assigned
selector. The same episode cannot replace the original accession, query, page,
resource or parent constraints. Repeating a selection is a new choice about the
same assigned work; recovery of an existing selected action uses its original
recorded result.

Use actual acquired outcomes to distinguish a complete response, valid partial
records, a missing requested field, an unavailable representation, and an
unsuccessful attempt. Keep the native response's parser state separate from the
number of records bound into stored results and from the acquisition's outer
status. A complete selected page does not establish that the whole query is
complete. Missing pagination metadata leaves query completeness unknown. A
malformed or unbound record does not invalidate its valid siblings. A long valid
native name can remain available through its requested text window even when a
legacy name column cannot represent it.

The parent requested the following data. Each row is a binding requirement,
including selected units, coordinates, meanings and permitted interpretations:

| Requested page/record or collection | Requested field | Exact extent and meaning |
| --- | --- | --- |
| {original selected page} | {each selected page field} | {total-results count, release, release date, or selected continuation/query value; preserve recorded availability} |
| {each original record clause: known primary accession, all native records, or an explicitly supplied position} | {each selected scalar/token/text field} | {native meaning; exact text offset/limit and Unicode-character unit where selected; numerical unit/origin where applicable} |
| {each original selected record clause} | {each selected cross-reference collection} | {exact database criterion such as GO, all members, or original position; selected property keys and exact text windows; whether associated evidence is requested} |
| {each original selected record clause} | {each selected feature collection} | {exact entry interval in zero-based half-open aa coordinates, all members, or original position; selected type/description windows; whether associated evidence is requested} |
| {each original selected record clause} | {each selected evidence collection or EC assignment} | {exact owning name/feature/xref/component and selected local member or all-members meaning} |
| {each original selected record clause} | {each selected sequence window} | {exact zero-based half-open start/end in aa; no padding or isoform substitution} |
| {each original selected page or record clause} | {explicit whole-source or full-sequence-artifact grant, if requested} | {exact requested material and availability; do not expand a metadata-only request} |

Select by the parent's stated criteria, which may use a known primary accession,
the GO cross-reference database, or sequence positions without prior knowledge
of native row indices. Keep original row and owner relationships after selection.
Exact primary-accession selection returns every matching native row. Do not
reinterpret a secondary accession as a primary match. A malformed identity can
make the requested selection indeterminate; it does not establish absence.

For a cross-reference database selection, retain every matching database/identifier
pair and explicitly requested associated values. Distinguish matches,
indeterminate members, unavailable selected members and excluded members. For a
feature-overlap selection, exact entry-sequence intervals determine overlap;
fuzzy or unresolved intervals remain indeterminate, and explicit other-sequence
features remain separate. Native positions are one-based inclusive aa; supplied
derived intervals are zero-based half-open aa. Do not invent an exact interval.
Evidence belongs to its actual native owner. ECO codes and native evidence
properties are source metadata, not confidence scores or independent-experiment
counts. An EC number belonging to a component is not automatically a whole-chain
function assignment.

Return only the original selected typed facts and material grants. Text windows
retain their exact selected characters, full native character count and omitted
prefix/suffix extents; sequence windows retain exact selected residues and
coordinates. Preserve absent, null, invalid, present empty and unavailable
representation separately. Valid partial values remain returnable with the
specific qualification. The host populates recorded fact fields from actual
records. Maintain only the constrained interpretation fields requested by the
original form in `report_update`: {complete original interpretation field names,
types, allowed values and meanings; or “No interpretation fields requested.”}.
Do not compose a replacement narrative report or supply a new numerical score.

Choose among the actual available operations using your own prior outcomes and
yield information. Information retrieval, a selected wait and acquisition retain
their separate meanings. UniProt returns an immediate response; this assignment
does not supply a remote UniProt job or a service polling action. Consider a wait
only using an available wait condition and actually received pending/progress
information. Preserve a specific failure when no available operation can repair
it within the original assignment. The configured controller owns continuation.
When actual completion of the original practical assignment is validated, its
future expectation becomes exactly zero immediately through the existing
controller comparison, retaining the final actual gain. No extra final decision,
stop action or return-composition call is required. The original requested form
is returned at closure, including valid partial information if the episode yields.

Tool-specific and resource instructions are available through knowledge.search,
knowledge.entry and knowledge.read. The tool_knowledge context identifies the
run-frozen library. Retrieve sections when useful; these instructions do not
select work, supply scientific evidence or add execution capabilities. Use the
actual tool schemas and caller-owned configuration for execution. Knowledge
reads use line coordinates, not scientific source-byte anchors. No manual read
is mandatory.

Launch software/resource instructions have their own run-frozen library:
launch.instructions.search, launch.instructions.entry, launch.instructions.read
and launch.instructions.select. The launch_instruction_library context gives
its identity. Select any relevant sections from one or several entries; pass
the returned selection as launch_instructions in the child assignment.
selected_launch_instructions contains exact sections already selected for this
assignment. Instructions describe ways to work; they do not select resources,
enable tools, override caller constraints, establish current availability or
supply scientific evidence. Inventory and fresh observations remain separate.
No instruction read or selection is mandatory.

Assigned software and resource instructions:

{Every substantive section already selected for this assignment, expanded in
full as meaningful instruction text. Preserve the selected process guidance and
outcome contingencies where present. A section heading or library entry name
does not substitute for its text. Do not insert a parent history or yield table.}

Callable operations and response meanings:

| Operation | Meaning and operands |
| --- | --- |
| api.uniprot.collect | Publish the retained original UniProt response, or obtain the explicitly selected cursor page of the original query. No automatic page traversal or target annotation. No action arguments. |
| {each other operation actually present in this decision's catalog} | {complete relevant description and operand names, types, allowed values and meanings} |
| {wait, only when present in the actual action contract} | {actual available condition names, typed fields and their meanings; no invented cadence or event} |

{For the configured decision-exchange protocol, include this complete block:}

Your internal decision may take several model exchanges. Return the required
closed response object. Use response_type=request_context to request your own
prior attempts through the declared lookup form. This only retrieves information
you already received; it does not perform new scientific work or complete an
action. After the requested information arrives, continue the SAME decision.
For this protocol, use request_context for own history; episode.history is not
an available action. This replaces the older history-tool instruction.
Use response_type=select_action with selection and report_update when ready to
dispatch an actual action. Only that action's actual completion supplies an
observation to your configured continuation controller.

Each request supplies the complete task and current decision-relevant information.
Current values replace earlier values, including yield expectations; prior
estimates remain historical. A requested own-history lookup continues this same
pending decision. Previously answered lookups remain answered after
reconstruction; do not repeat them merely to restore memory.

action_yields describes your OWN completed action categories. total_yield is
observed signed gain, excluding inherited credit. Expected category yield is
conditional on choosing and completing that category again; unavailable is not
zero. Approximate model bands are not calibrated next-outcome guarantees. Useful
evidence acquisition can have zero immediate credit when a later interpretation
earns the credit. Failed or unexecuted attempts have no completed-action gain.
Use recorded inputs and result references to distinguish specific prior attempts.

--- END TASK TEMPLATE ---

## Conditional existing native-event paragraph

If `Workflow.native_event_information` is actually bound, preserve this existing
full paragraph as an additional TASK paragraph; it does not imply UniProt has a
native remote job. The actual event handles/cursors stay in the typed action
context and are rendered only when meaningful to an available selected wait.

> The separate native_event_targets input names native notification targets
> assigned or actually received by this episode. A target is registration
> metadata, not proof that submission succeeded. Its state_changed event means
> the original service exit receipt was committed; the service may still be
> closing, so this does not establish result readiness or a child episode return.
> after_cursor records an event cursor actually received, initially zero. Select
> your own wait condition and subsequent status/monitor/result work. Request the
> native_event_targets source in original child forms when that handoff is needed.
> No event probability, gain or scientific credit follows from registration or
> passing time alone.

## Presentation rules for filled slots

The original typed output/return schemas remain authoritative and unchanged.
Expand their selected field meanings into the table above; do not dump schema
JSON, `x-uniprot-selection` custody witnesses, host source IDs, run IDs, hashes,
revisions or implementation module names. Native scientific identifiers are
displayed only where requested or already part of the original assignment.

The complete task appears once per message. STEERING below it contains only
current selected facts, necessary qualifications and the existing own-yield
table. Do not append raw `execution_progress`, working state, outcome, event
history or `requested_form` as another context block.
