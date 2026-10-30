# Annotation root → literature: initial commission

## Proposed child instruction

Braces are fill placeholders. The full TASK remains available every iteration. STEERING contains only necessary, explicitly supplied facts from prior work and may be absent at initial commissioning. Populate both from the parent's exact selection and actually received information. Readable candidate and source labels resolve to original operands outside the prompt; each candidate label remains stable across updates.

```text
TASK — retain this complete assignment and these instructions every iteration.

You own an iterative literature investigation of this annotation question:
{exact_assigned_scientific_question}

The annotation parent needs the answer to decide: {parent_information_need}
Target: {fixed_target_name}; organism/strain: {supplied_organism_and_strain}; useful supplied query aliases: {target_aliases_and_biological_accessions}.
Assigned scope: {contained_subject_and_any_relevant_region_or_context}.
Binding constraints: {explicit_parent_constraints}.

Selected annotation candidates and the distinction to investigate:

| Candidate | Biological claim under investigation | Explicit qualification or alternative | Distinction the parent asks you to resolve |
| --- | --- | --- | --- |
{one_row_per_parent_selected_candidate}

Keep each candidate separate. Its label identifies the same global candidate across updates; an updated annotation does not create another candidate.

Scientific context supplied as part of this task:

| Received proposition or interpretation | Actual subject, organism and conditions | Qualification or unresolved distinction | Supplied basis label |
| --- | --- | --- | --- |
{explicitly_commissioned_task_context_rows}

These are supplied facts and interpretations. A citation or search result identifies a lead; it does not deliver the article body or establish that it was examined. Distinguish an unsuccessful search, unavailable access and a source-grounded negative finding. Select acquisition or examination when article content is useful.

Choose how to find published evidence that answers the assigned question. Establish what a relevant publication actually reports: its studied subject, organism/strain or construct, relevant assay or observation, experimental conditions and stated qualifications. Assess whether that evidence bears directly on the fixed target, requires a transfer assumption, or leaves the selected distinction unresolved. Preserve the distinction between a source's assertion, its experimental support and your inference for this target. A useful correction, qualification or source-grounded negative finding can answer part of the task without supporting a more specific annotation.

You can search or examine sources directly, or commission a narrower strategy investigation when that question warrants iteration. Choose queries, source leads and examinations in light of the assigned distinction; revise the approach using actual outcomes. Commit source-grounded interpretations through the common reasoning action with their actual basis. Navigation and repeated discovery or reading do not by themselves establish a new finding. No search order, source list or reading quota is prescribed.

The parent requests this closed return form:

| Required field | Type, allowed values and any reference kind | Parent's exact declared meaning | Initial interpretation value | Filled by child or recorded by runtime |
| --- | --- | --- | --- | --- |
{all_parent_return_fields_including_nested_constraints}

Update only the declared interpretation fields in the existing response, using information available before your selected next action. Parent-supplied initial values are the starting form. Record scientific interpretations through the common reasoning action. Runtime fact fields describe actual records; a later tool outcome does not automatically become an interpretation. The configured controller governs continuation.

Use the bound response form unchanged. The host executes the selected action.

STEERING — include only necessary supplied facts from prior work; omit if none.

| Candidate | Latest supplied claim/qualification relevant to this question | Its own supplied annotation-support score |
| --- | --- | --- |
{necessary_candidate_state_rows_if_supplied}

| Exact prior query/approach or source lead | Received result descriptor | Access/examination status | Supplied basis label |
| --- | --- | --- | --- |
{necessary_explicitly_commissioned_received_prior_work_rows}

A missing candidate score is unavailable. Keep annotation support separate from investigation progress. These rows carry no private parent history or unreceived article content.
```

## Source → selection → child decision

The receiver decides how to find published evidence for the specific assigned annotation question. The scientific parent supplies the detailed TASK: information need, claim distinctions, scope, constraints, supplied context and return meanings. This full instruction persists each iteration. Any STEERING is a separate terse selection of necessary received facts.

| Source | Selection and text presentation at this boundary | Receiving decision or consumer |
| --- | --- | --- |
| [runtime.py:2961](../../gene_annotation_episode/runtime.py#L2961) `action_schema`; [runtime.py:3055](../../gene_annotation_episode/runtime.py#L3055) `selected` | Parent selects `episode_child` with role `literature`, exact `goal`, contained `scope`, `purpose`, assignment and original return form/initial interpretation. Render the question and information need verbatim, with the declared constraints. | How to investigate this assigned literature question. |
| [literature_episodes.py:94](../../gene_annotation_episode/literature_episodes.py#L94) `assignment_schema`; [literature_episodes.py:153](../../gene_annotation_episode/literature_episodes.py#L153) `_validate_assignment`; [literature_episodes.py:180](../../gene_annotation_episode/literature_episodes.py#L180) `prepare_assignment` | Entry assignment selects `question_context_refs` and `source_refs`. Select only the exact scientific propositions, candidate distinctions and source descriptors the parent explicitly commissions and has received. Resolve their actual values into the corresponding tables. Validation of a reference grants no additional delivered content. | Which approach to try using this explicitly supplied context. |
| [state.py:1632](../../gene_annotation_episode/state.py#L1632) `reasoning_view`; [domain.py:195](../../gene_annotation_episode/domain.py#L195) hypothesis/assessment/annotation records; original scoped input metadata | Render target name, organism/strain and query-useful aliases from supplied input/context records. Render selected claim, actual evidence subject/conditions, recorded assessment relation/applicability and qualifications from the exact received records. Retain the parent's selected region/context. | Distinguishes target identity, competing claims and the question that publications could resolve. |
| Parent-selected candidate records and their actually supplied score values; [state.py:1390](../../gene_annotation_episode/state.py#L1390) `put`; [runtime.py:2331](../../gene_annotation_episode/runtime.py#L2331) `annotation_context` | One row per distinct candidate, with a readable label mapped to its stable global entity across updates and its own supplied score. Use only supplied values; keep a scope-wide annotation score distinct from any candidate's score. Preserve the exact received state internally. | Which publication could bear on the selected distinction between candidates. |
| Parent's selected completed search/read outcomes and supplied source metadata; [tools.py:1893](../../gene_annotation_episode/tools.py#L1893) `_import`; [acquisition.py:534](../../gene_annotation_episode/acquisition.py#L534) `literature_search` | Include an actual query/approach, returned title/accession/result descriptor and access status only when explicitly included in this commission and actually received by the parent. A known citation remains a source lead. Do not load the parent's action history or article body to fill these rows. | Lets the child consider known approaches and leads without asserting an unperformed examination. |
| [runtime.py:3384](../../gene_annotation_episode/runtime.py#L3384) `build`; [episode_bindings.py:204](../../gene_annotation_episode/episode_bindings.py#L204) `initial_references`; complete [episode_receipts.py](../../gene_annotation_episode/episode_receipts.py) | Preserve the exact request and explicitly selected starting information. Receipt prefixes, recursively referenced dependencies and inherited ledgers do not select prompt rows or count as delivered scientific context. `LiteratureEpisodes` itself supplies no `initial_references` hook. | First decision uses the commissioned information; inherited records do not automatically enter it. |
| [runtime.py:1631](../../gene_annotation_episode/runtime.py#L1631) `commission_child`; complete [episode_commissions.py](../../gene_annotation_episode/episode_commissions.py) | Freeze the selected child request, scope, original form, constraints and input pins for dispatch/recovery. Keep internal identities, hashes, versions, parent paths, configuration and pinning records outside the prompt. Pins validate operands; they do not deliver scientific information or source bytes. | Transport executes the parent's selection without expanding the literature assignment. |
| [literature_episodes.py:193](../../gene_annotation_episode/literature_episodes.py#L193) `instructions`; [literature_episodes.py:208](../../gene_annotation_episode/literature_episodes.py#L208) `decision_context`; [literature_episodes.py:222](../../gene_annotation_episode/literature_episodes.py#L222) `catalog` | Present the scientific ownership instructions and explicit assignment in text. Source custody is internal; it supplies no article content. Direct search/read choices and the optional strategy-child branch remain available. Raw content enters only through a child-selected acquisition/examination operation, dispatched by `execute` and the existing tool consumer. | Which direct operation or narrower strategy investigation to select first. |
| [communication.py:72](../../gene_annotation_episode/communication.py#L72) `validate_closed_schema`; `interpretation_schema`/`form_with_facts`; [runtime.py:3139](../../gene_annotation_episode/runtime.py#L3139) `TypedReportContract`; [runtime.py:3314](../../gene_annotation_episode/runtime.py#L3314) `facts`; [runtime.py:2125](../../gene_annotation_episode/runtime.py#L2125) `receive_form` | Render every original required field, nested constraints, allowed values/reference kinds, declared meaning, initial interpretation and recorded-fact ownership. Keep the machine response and typed return JSON unchanged. Interpretations use the existing response; recorded facts use the existing projection and admission path. | Child updates the parent's requested information; the parent receives only the admitted original form. No report composer or scoring rule is added. |

Only this initial directed commission is proposed. No application edits, tests, network requests, model calls or process changes were performed.
