# Full recurring scientific-parent TASK construction

2026-10-28. Proposal-only source map for the immediate results-child return
boundary. This is not a replacement episode or a new acquisition assignment.
The actual scientific parent and its original TASK were not executed here.
Variable slots below must be populated from that parent's saved original inputs;
the examples do not invent those inputs or replace them with P0AAW1.

## Complete construction and source ownership

| TASK slot, expanded on every iteration | Actual source | Required content |
| --- | --- | --- |
| Scientific assignment | `DecisionSource.next`: `self.request.goal.as_record()` → `state.goal.objective`, `task_context`, `result_contract` | The original direct question about the supplied target, including any selected candidate only if one was actually supplied. Preserve detailed objective and requested result meanings; never replace them with “retrieve UniProt”. |
| Fixed scientific scope | Original request message scope → `state.scope` | Actual selected subject, material/region boundaries and allowed investigation scope. Names may be unknown. No arbitrary record selection or inferred complete sequence. |
| Binding constraints | `ScientificProcessEpisodes._assignment` / `decision_context` → `state.scientific_process.assignment.constraints` | Every parent's original resource, input, scope and result constraint, without strengthening or weakening it. |
| Supplied instructional context and input content | Original assignment `context` and `evidence_refs`; `state.working_state` subjects/materials/collections/material_links, target binding and actual supplied-content access | Full supplied instructional text and selected sequence/file/snippet content with original completeness, coordinates and provenance role. An opaque reference alone is not delivered content. Do not fetch an ungranted source to decorate the task. |
| Common scientific decision instructions | `DecisionSource.instructions` and `ScientificProcessEpisodes.instructions`, published-instruction branch | Full existing instructional body, shown below, together with applicable original conditional knowledge/resource instructions. The results child's assignment does not enter this slot. |
| Evidence axis | Original `assignment.selection.evidence_axis` resolved by the immutable `ScientificProcessLibrary`; `instruction_view` → `state.scientific_process.evidence_axis.investigation_instructions` | The entire selected investigation instruction, not its name/description or a scoring sheet. The A101 example below shows the full real slot body. |
| Thought pattern | Original selected thought entry → `state.scientific_process.thought_pattern` | Full `description`, `use_when`, every `live_alternatives` and `decision_guidance` item, every paired `outcome_contingencies.if_observed/then_consider`, and `boundary`. The P01 example below shows every substantive field. |
| Selected tools | `ScientificProcessEpisodes._assignment(materialize=True)` → `ScientificToolLibrary.resolve_tool_info` → original `selection.child_tool_info` → `decision_context` | Each selected tool's exact name, description, resource kind and full instructions. The host resolves these from the frozen actual tool information. Several tools can be selected; do not replace the whole set with UniProt because a UniProt return arrived. |
| Selected software/resource guidance | `DecisionSource.call` → `launch_instructions.materialize(original episode_assignment.launch_instructions)` → `selected_launch_instructions.sections[].text` | Full substantive text of each actually selected section, preserving caller constraints. Library/source identities and hashes stay internal. A return neither selects new instructions nor chooses a resource. |
| Available decisions and operands | `Workflow.catalog(scope, source=parent)`; actual `action_schema`; scientific binding `permitted_children`; existing `child_option_information(...).text` | Full meanings and actual typed constraints for the parent's available actions, child construction and waiting choices. Preserve actual callable operands separately from hidden custody witnesses. No fixed order, polling cadence or number of children. |
| Parent's own requested return | Original `request.report_contract.decision`, `.schema`; `requested_report_purpose`, `requested_form`, and used `available_report_facts` meanings | Every required field's type, constrained allowed interpretations and intended meaning. Mechanical facts stay mechanical. This is the return requested from the scientific parent by its assigner, not the child's completed UniProt form. Internal schema JSON or expanded witness definitions are not a TASK table. |
| Return timing and interpretation responsibility | Existing `report_lifecycle` plus original typed response contract | Preserve that interpretations are the last actual reasoning basis; later received facts do not automatically constitute a new judgment. Scientific interpretation remains this parent episode's work. |
| Decision exchange protocol | `DecisionSource.instructions`, `decision_context.TEXT_INSTRUCTIONS`, `scientific_process_prompt.text_instructions` | Full action/lookup/own-yield meanings, shown below. Reconstruction and a same-decision lookup receive the complete task again. Response schemas stay typed and are not replaced by free prose. |

No history budget shortens these slots. The actual final instruction string
passed into `render_scientific_process_prompt` is retained in full; conditional
knowledge/launch/event guidance remains present when the parent actually has
it. The table identifies content sources rather than asserting a new selection.

The literal assembly is:

```text
TASK

<FULL ORIGINAL COMMON/PROTOCOL INSTRUCTIONS, with applicable original conditional guidance>

Assigned work
<FULL ORIGINAL objective, instructional task_context and result meanings>

Fixed scope and parent constraints
<FULL ORIGINAL scope and constraints with exact selected material boundaries>

Supplied target and context
<FULL ORIGINALLY DELIVERED sequence, selected file content/snippets and context>
<ACTUALLY AUTHORIZED operands, with their scientific/material roles>

Investigate the supplied target
<FULL SELECTED evidence_axis.investigation_instructions>

Reason about the evidence
<FULL SELECTED thought_pattern.description and use_when>
<ALL live_alternatives>
<ALL decision_guidance>
<ALL outcome_contingency pairs>
<FULL boundary>

Selected tools and resource instructions
<FOR EACH ORIGINAL child_tool_info: exact name, description, resources, FULL instructions>
<FULL originally selected software/resource section texts, when present>
<ACTUAL available operation meanings and typed operand constraints>

Child decisions and requested results
<ORIGINAL permitted children, child construction and typed requested-fact meanings>
<FULL ORIGINAL requested_report_purpose and semantic return-field constraints>
<ORIGINAL return interpretation timing>

STEERING
<EXISTING PARENT OWN action-category/yield/expectation/uncertainty table>
<EXISTING relevant parent state, pending work and distinct measures>
<ONCE: admitted selected UniProt reference facts and material qualifications>
```

Angle-bracketed slots are specification notation, never text to send instead of
their contents. The receiving return changes only the final factual insertion.
The original target need not be a public gene name and need not have a candidate
annotation. The native reference name returned below belongs only to that
reference.

## Existing common scientific instructions, in full

Source: `ScientificProcessEpisodes.instructions`, published-instruction branch.

Determine what the supplied target does within the parent's assigned question, scope and constraints. Start with the supplied sequence, selected file contents or snippets, preserving their boundaries, completeness and known context. No initial candidate annotation or publicly searchable name is required. Possible functions can emerge from the evidence and be compared or revised. Apply the complete selected investigation instructions and thought-pattern guidance on every decision. Use actual outcomes and received child results to choose and revise your approach. Selected instructions describe how to investigate; they are not evidence about this target. Preserve the measured subject, conditions, controls, native measurements, uncertainty and limits of inference when interpreting evidence. Missing information remains unknown.

Choose an available tool action, commit a scientific interpretation through the reasoning action, commission a scoped child with its own typed return form, or wait for selected pending work when that informs the investigation. Use only the selected actual tools and their supplied resource instructions; choose callable operands through the declared response contract. Preserve the parent's exact requested result meanings and allowed values. Recorded facts come from actual records. Keep inherited information distinct from new findings and completed work distinct from attempts. Return valid partial findings and specific failures through the requested form.

Keep the assigned evidence axis, thought pattern and selected tools for this episode. process.revise prepares a different thought pattern and/or tool selection for a new child; it does not change this episode or start that child. To commission that alternative, copy its selection and revision_origin into a separately selected child assignment with the child's job, scope, constraints and typed return. Children own their iterative choices. The configured controller owns continuation. Waiting and unchanged observations do not manufacture progress.

## Existing text exchange instructions, in full

Source: `decision_context.TEXT_INSTRUCTIONS` followed by the existing
`scientific_process_prompt.text_instructions` substitution. These are mechanics
of the same decision, not an additional autonomous loop.

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

Each request supplies the complete task and current decision-relevant information. Current values replace earlier values, including yield expectations; prior estimates remain historical. A requested own-history lookup continues this same pending decision. Previously answered lookups remain answered after reconstruction; do not repeat them merely to restore memory.

action_yields describes your OWN completed action categories. total_yield is
observed signed gain, excluding inherited credit. Expected category yield is
conditional on choosing and completing that category again; unavailable is not
zero. Approximate model bands are not calibrated next-outcome guarantees. Useful
evidence acquisition can have zero immediate credit when a later interpretation
earns the credit. Failed or unexecuted attempts have no completed-action gain.
Use recorded inputs and result references to distinguish specific prior attempts.

## Fully expanded example evidence-axis slot

This real library example is used only to demonstrate that the slot retains
substantive instructions. It does not select A101 for an actual parent. Source:
`research/slotted_process_library/publications/2026-10-24-001/entries/A101.json`,
`investigation_instructions`. Library evidence/provenance rows are not target
evidence and are not copied into the TASK.

Determine what functions the supplied gene or protein may perform by comparing its sequence with relevant homologs and family profiles. Start from the supplied sequence, selected file record or region, or snippets. No candidate annotation or searchable public name is required. Preserve the selected material and its boundaries; do not infer a complete sequence from snippets or choose an arbitrary record from a multi-record file.

Use the comparisons to identify plausible families and distinguish their functions. Examine what was experimentally characterized in relevant homologs, including close relatives with different functions, and map the features bearing on those differences to the supplied target. Retain the identity of the experimentally studied subject separately from the sequence or profile used in a search. A database description or inherited family label is not experimental characterization.

Retain actual alignment or profile scores, bit scores, E-values, identity, matched spans and coverage when available, with the method, search space, score units, denominators and reported uncertainty or bounds. Keep query and comparator coverage distinct, and distinguish a matched domain from the whole protein. Compare numbers only where their methods and scales permit the comparison; a sequence score is not a probability of a particular function.

Examine catalytic and recognition residues, missing or additional domains, and substitutions or insertions that distinguish possible activities. High overall identity can coexist with different substrate specificity; a short match or conserved cofactor-binding region can support only a broader conclusion. Preserve negative results, function-changing differences and unresolved regions. Revise the possible functions as the comparisons become informative, keeping family membership, exact reaction, substrate specificity and physiological role distinct.

## Fully expanded example thought-pattern slot

This is the complete substantive P01 content, without its instruction-provenance
rows. Source: `research/slotted_process_library/entries/P01.json`. The runtime
uses the exact entry already selected in the parent's immutable library; this
example does not reselect or replace it.

Use similarity to a characterized system to form bounded explanations. Choose which sequence, local structural machinery, domain architecture, genomic context or organismal circumstance makes the reference informative for the disputed property; revise misleading comparators.

A nearest hit, fold, motif or similar biological context suggests an annotation, but exact chemistry, recognition or role remains open.

Alternatives to distinguish:

- A relevant shared relationship supports transfer of the disputed property.
- Only a partial core is shared; recognition, partners or role differ.
- The comparator or short match is uninformative for this question.

How to choose and revise the investigation:

- Prefer references that separate plausible alternatives, not simply the most familiar name or highest global score. Alignments, structures and context searches are ways to inspect a chosen relationship.
- When a comparison is weak, consider a biologically better reference before treating it as evidence against all relationship.
- Keep catalytic compatibility, target recognition and native role as separate transfer claims; absent catalytic machinery can overturn an inherited chemistry.

How outcomes affect the next choice:

| If observed | Then consider |
| --- | --- |
| Relevant machinery corresponds but specificity differs | Retain the supported relationship and investigate the differing recognition or contextual features. |
| Expected catalytic machinery is incompatible | Reopen chemistry and preserve only the relationship actually supported. |
| No informative correspondence is found | Keep function unresolved; absence of an informative match is not absence of function. |

Choose a comparator for transfer of a disputed biological property. P02 instead tests an explicit feature-to-function implication against discordant cases. A better sequence score, fold match or neighborhood is a tool result, not the transfer conclusion.

## Fully expanded example tool-instruction slot

One actual tool entry is shown to make the slot concrete; it is not a replacement
for the parent's complete original tool set or an assertion of configured live
availability. Source: `api_uniprot.UniProtService.capabilities`, passed through
`ScientificToolLibrary._tool_information` / `resolve_tool_info`. Its resource
kind is `api` only when that exact actual profile was selected.

Tool: `query_uniprot`.

Description: Retrieve the assigned UniProtKB JSON record or one selected JSON
search page from its explicit endpoint, retaining complete native data and
source associations.

Full instructions:

Commission this operation through the configured UniProt API resource with request.operation=query_uniprot and the original endpoint. Endpoint and optional max_results are immutable service-request operands; the selected action has empty arguments. Supported endpoints are /uniprotkb/{accession} (optionally .json or format=json) and /uniprotkb/search?query=... with optional size, cursor and format=json; relative paths and https://rest.uniprot.org are accepted. A supplied max_results of 1..500 selects a search page size and must agree with any URL size. Omission or null leaves the explicit URL size or the existing default of 10. A record endpoint accepts no non-null max_results. Preserve the exact accession, decoded query and opaque cursor. Each selection makes one existing client call; api.uniprot.collect with an empty selector publishes its retained response, and an explicit cursor/size selector requests one page of that same query. Invalid rows and field issues remain visible alongside valid native rows. Source annotations describe the retrieved entries, not the investigated target. Other datasets, formats, parameters, streaming and ID mapping are unsupported in this contract; no natural-language query generation or page traversal is provided.

The exact original assignment values, selected tool set, resource bindings and
requested scientific-parent form are not supplied by a fixture-derived example.
They remain required runtime inputs. This task does not propose a handwritten
scientific episode for UniProt, a source-annotation-to-target-function rule,
a score, or an LLM step that reparses or filters an already validated return.
