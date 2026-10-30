# Own-decision relevance trace — additive correction 002

This corrects the information-selection conclusions of trace001 without
discarding its complete call/consumer trace. The boundary is still one UniProt
results episode's own completed/partial acquisition to its next decision.
TASK002 is preserved. Parent/ancestor scientific receiving messages and the
complete typed return are outside this correction.

## Actual operations and the discriminating choice

`UniProtService.result_catalog` validates the original request/selector and
returns `result_capabilities`: one empty-argument `api.uniprot.collect`.
`APIServiceExecution._context` resolves the original handoff and immutable
selector; `_manifest` checks the original episode assignment; `_selected`
checks the episode's selected action. `ExecutionEpisodes.permitted_common_actions`
allows tools and shared wait for this API results role, not a different child
commission, selector edit or model-composed return.

For this concrete TASK002 assignment, `UniProtService.prepare` sets
`cache_original=True` because the results selector is empty.
`APIServiceExecution._execute_locked` loads the original handoff snapshot in
that branch; it does not call `UniProtService.invoke` for a fresh service
response. `UniProtService.decode` and `publish` work on those retained bytes.
Replaying the same selected action returns its saved outcome. A newly selected
collect can reattempt publication for the same bytes under the existing
infrastructure; it cannot repair native missing/malformed/fuzzy values or choose
different fields/pages. The code does not expose a native-edit or parser-repair
operation. `UniProtService.prepare_observation` returns `None`; there is no
UniProt status job to poll.

Consequently, a returned taxon value or residue string does not choose an
argument, tool, resource, page or repair for this receiver. These values matter
to the scientific parent and remain in its exact typed return. The results
episode needs the failure's location and nature, usable acquired extent,
available operation semantics and actual repair/wait conditions to assess its
remaining choices. Knowledge reads can clarify actual operations or a specific
qualification. Waiting requires its ordinary episode-owned decision; a timer
does not change retained data by itself.

## Per-field inclusion test

| Included decision fact | Exact source / reduction | Actual distinction it supports |
| --- | --- | --- |
| Own action category, completed/uncompleted counts, signed total, category estimate and uncertainty | Existing `decision_history.yield_table` / reconstructed `action_yields.rows` | Compare another own acquisition with waiting/information choices using the episode's real history; no parent history or invented scientific score. |
| Current controller expectation, uncertainty and cost | Existing controller context, unchanged | Ordinary continuation comparison. It is separate from the category-conditional estimate and never derived from return values. |
| Outer acquisition status | Exact current saved outcome | Establish whether the original acquisition is recorded complete or partial; retain the existing completion semantics rather than asking the model to mark it scientifically complete. |
| Native body state and parser state | Authenticated P page | Distinguish retained usable JSON with a malformed sibling from a whole-response/format failure. That distinction controls what specific operation information or actual repair condition could help. |
| Retained input; another collect uses the same bytes | Original snapshot custody plus `prepare.cache_original` and `_execute_locked` | Distinguish a publication reattempt from fetching replacement native data. The model cannot treat missing/fuzzy native data as something this collect will refresh. |
| Requested/bound record-reply counts | Exact R replies for each original record clause, with `state == bound` counted separately | Distinguish a wholly unavailable acquisition from usable partial work that the typed return preserves. No count selects extra work or earns scientific credit. |
| Native position and selected field label for an exception | Original clause indices plus R/P native ordinal | Locate the exact unresolved request for a permitted instruction lookup or an actually supplied repair. Do not substitute a returned biological identifier or a witness ID. |
| Malformed-record versus binding-omitted condition | Existing R record state and P/B failure code | Distinguish fixed native-content limitations from publication/binding limitations; only a real available operation/condition can support a corresponding reattempt. |
| Requested name window available despite legacy label/term failure | R field availability plus both P/B legacy representation errors | Avoid treating an already acquired selected field as missing merely because outer publication is partial. The native text and its length add no action distinction. |
| Selected collection availability and matched/indeterminate/unavailable counts, only when qualified | R selected collection status/counts and existing qualification | Preserve the extent of valid partial acquisition and identify unresolved requested membership. This prevents a partial collection from being described as wholly unavailable or complete; exact member identities/coordinates cannot alter collect. |
| Native field absent/null/invalid | Original R failure and native state | Distinguish a legitimate qualified result from a missing read or binding failure; a fresh publish of the same bytes is not replacement native evidence. |
| Other selected fields available | Deterministic check of every selected reply outside explicit record/field conditions | State that no other requested acquisition gap was found without echoing each biological value or generating a model-written report. |
| Actual repair operation/event or relevant wait target; explicit none only when inspected/supplied | Current callable catalog and already received pending/waiting/progress information | Decide whether an actual repair or informed wait exists. No imagined API job, future change, fixed delay or parser-repair operation is supplied. |

“Supports a distinction” does not mean infrastructure chooses an action. The
episode remains free to select among its actual operations; the existing
controller decides continuation. A complete endpoint can close without a next
prompt. No return/stop tool or new validation gate is created.

## Removed from this own-decision message

| Omitted fact | Why it cannot discriminate an available action here | Where it remains |
| --- | --- | --- |
| Returned primary accession or taxon number | The source and selector are immutable; no biological branch or query-edit action exists. | Original selected typed return and publication. |
| Observed sequence length or residue letters | No sequence-analysis, interval-edit or replacement-sequence action is supplied. Availability of the requested window is sufficient. | Exact selected return and native/sequence material. |
| Native name text, native length and omitted prefix/suffix lengths | The selected extent is fixed. Native presence and selected-window availability already identify the representation problem. | Exact selected text-window return. |
| GO identifiers, feature coordinates, returned evidence/property text | The results episode neither interprets biology nor changes the fixed collection query. Membership qualifications identify the unresolved part. | Exact requested collection return. |
| Excluded member count and fully available empty collections as separate rows | Neither identifies an unfulfilled request or an available repair; complete availability already covers them. | Exact selected collection return, including its full count partition. |
| Next cursor, total-query count, whole-query completeness, release metadata | This child cannot select another page; no endpoint/repair condition in this concrete assignment depends on these values. | Native page/publication and typed page fields when originally requested. |
| Host IDs, native pointers, digests, witnesses and source/sequence grants | They support host authentication/typed delivery, not the next decision; they can also expose extra handles if copied. | Authentication, durable outcome and expressly requested typed grants. |

Pagination would need a concrete different decision dependency before appearing
in any other template. “Parent requested it” or “available in the response” is
not that dependency for this fixed-page child. The scientific parent's template
may have a different information need; this proposal does not define it.

## Complete consumer path and current availability

Trace001's affected functions remain relevant: `DecisionSource.execute` records
the full result; `DecisionSource.next` calls `Workflow.local_outcome_preview`
before `runtime._references_in`; `Workflow.working_state` for this specialist
role is assignment-only; `ExecutionEpisodes.decision_context` adds target and
execution-progress structures; `DecisionSource.call` freezes its context;
`decision_context.model_snapshot`, state frames and provider presentation
reconstruct/render it. `providers._SessionConnection._presentation` still needs
the narrowly selected text route rather than a raw JSON fallback. Generic
`scientific_process_prompt._outcome`/`_information` are not filters for this
boundary. None may reintroduce the biological values removed here through
duplicate outcome, form, target, feedback, schema, lookup or saved-state paths.

At reinspection, exact-operation `APIServiceExecution.read_result`,
`UniProtReturns.read_own` and `project_uniprot_page` are present in source. The
specific new availability-only reducer and context-aware preview/provider
wiring remain proposed. This correction inspected source and design artifacts;
it did not execute those implementations or read runtime databases.

The full native outcome remains the input to actual receipts and credit. The
original typed return still uses R's complete selected replies at closure.
`APIServiceExecution._completion`, `ExecutionEpisodes.verify_completion` and
`PracticalYieldEstimator` keep the existing endpoint/comparison behavior. No
selected-field requirement is added to the endpoint and no old observation is
rewritten. Future integration verification must assert both the omitted values
in every next-decision presentation path and their unchanged presence in the
requested typed return/full publication.
