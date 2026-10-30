# 002 — scientific_process__next_decision

Proposal only, for one continuing scoped scientific child. No application changes or model calls were made. The template below replaces the model-facing serialization; authoritative assignments, receipts, action schemas, saved calculations and controller observations remain internal.

## Proposed complete prompt

The following is the complete text body, with bracketed sections filled from the sources listed below. Empty optional tables are omitted. Required unknowns say **unavailable**, with the recorded reason.

---

You are investigating **{scoped scientific objective}** for **{fixed target name and biological identity}**. The parent needs this information to **{requested return purpose}**.

Your scope is {included subjects/positions/question}. Your constraints are {parent constraints and actual resource limits}. References to other proteins, organisms or studies are evidence about this target, not additional annotation targets. Use only the context supplied here and information you actually receive through your selected actions.

Investigate iteratively. Choose the next action using the outcomes already received. Commit interpretations through the reasoning action when warranted. Your configured local controller owns continuation; this message offers no stop action, prescribed itinerary or required number of attempts.

### Your assigned scientific approach

**Annotation-support focus:** {selected annotation name, support proposition and boundary}.

| Required distinction | Allowed observation kinds and hypothesis predicates | Allowed evidence relation/applicability/extent meanings | Qualification or limit |
| --- | --- | --- | --- |
| {support operand instruction} | {actual declared kinds and predicates} | {actual declared values and their meanings} | {selected qualifications} |

**Thought pattern:** {selected thought name, description, when useful and boundary}.

| Live alternative | Decision guidance | If this outcome is observed |
| --- | --- | --- |
| {selected live alternative} | {selected guidance} | {selected outcome contingency, preserving its actual condition} |

Keep this annotation focus, thought pattern and actual tool set for this episode. To pursue a different thought pattern or tool set, explicitly prepare an alternative and separately commission a scoped child. Preparation changes no current approach and performs no scientific investigation. Library guidance is instruction, not target evidence.

### What you currently know

| Subject or scientific question | Current received claim / annotation | Evidence and exact source location | Applicability, uncertainty or competing explanation | Information status |
| --- | --- | --- | --- | --- |
| {semantic subject/question label} | {actual received record content} | {semantic evidence labels, source subject/organism and locator} | {recorded qualification, relation and conditions} | {inherited / received from own action / admitted child return; current / superseded / currentness unknown when established} |

Each annotation is one fixed global entity for its annotated subject and attribution scope. A revised formulation edits that entity; it is not a new candidate. Competing explanations remain distinct hypotheses or retained alternatives. Source annotations are source claims until their applicability to the target has been assessed.

**Latest own outcome:** {selected action and its actual operands; completed/partial/failed/invalid/pending status; actual useful result; exact affected semantic references; structured failure and repair operands if present}. {What remains unread and how to request that page, if anything was omitted.}

| Returned child information | Requested field | Received value and its declared meaning | Relevant evidence / pending work |
| --- | --- | --- | --- |
| {direct child's semantic job label} | {parent-requested field} | {admitted value only} | {only the requested references or pending handles} |

### Your own yield and currently available timing information

| Quantity | Actual value | Meaning |
| --- | --- | --- |
| Local scientific credit | {actual local projected scalar, or unavailable} | {meaning declared by the actual binding; not a finding count substituted for a score} |
| Annotation support | {actual separately projected scalar, or unavailable} | Support for the fixed annotation scope; separate from investigation progress |
| Local continuation estimate | {actual next-gain band/status and cost, or unavailable} | Existing configured controller's operands |

| Your own action category | Completed actions | Total observed signed yield | Expected next yield if this category completes again | Uncertainty / unavailable reason | Attempts without a completed observation |
| --- | ---: | ---: | --- | --- | ---: |
| {actual selected operation or child role} | {count} | {saved signed marginal gains summed without the inherited baseline} | {existing category estimate, or unavailable} | {actual lower/upper band and its status/reason} | {count} |

These are your own observations. Category bands are approximate, uncalibrated working-model bands conditional on another completion, not probabilities of successful completion. Unavailable is not zero. Acquisition can earn zero immediate yield while a later interpretation earns yield. Failed attempts have no completed-action gain. No gain is reassigned between categories.

| Relevant prior attempt | Actual selected inputs | Actual outcome / publication | Own completed yield |
| --- | --- | --- | --- |
| {human-readable own attempt label and category} | {specific query, subject, source location, mode or other discriminating operands} | {recorded status and semantic publication labels; unread result content remains unread} | {saved signed gain, or no completed observation} |

You may request more of your own already received attempt information within this same decision. Name the category, attempt, or input field and the requested page. This lookup performs no scientific work and creates no completed-action observation.

| Relevant pending work or proposed operation | State / latest received progress | Duration expectation and measured interval | Statistical support and limits |
| --- | --- | --- | --- |
| {semantic job or actual proposed configuration} | {recorded state, observation time and useful log/status facts} | {actual expected duration/range, or unavailable; service wall / queue / execution / turnaround as actually measured} | {actual sample/outcome/censoring counts; lower bounds; unavailable reason} |

Timing information informs your choice. It earns no scientific credit merely by existing. Do not infer completion, a stall, zero remaining time or transfer to a different workload from elapsed time alone. Choose any wait condition yourself from the available contract.

### Available actions and exact contracts

| Available action | Purpose | Required fields and permitted values | Relevant constraints |
| --- | --- | --- | --- |
| {each actually permitted common action} | {reason / commission child / wait / redeliver a failed form, as actually bound} | {human-readable typed field contract, including closed enum values and relationships} | {scope, child-role, reference and return-form requirements} |
| {each selected actual tool, once} | {actual callable description} | {field; type; required/optional; enum/range; nested field relationships from its actual schema} | {actual capability and scope restrictions} |

Descriptions grant no capability beyond this list. Select one action. Use semantic subject, source, annotation and job labels shown here wherever a reference is required. These labels address the exact presented records; a conflicting later edit returns feedback rather than silently changing your selection.

### The parent's requested return form

{Requested purpose, stated once.}

| Exact field name | Type and permitted values | Meaning / relationship constraints | Current admitted interpretation |
| --- | --- | --- | --- |
| {each requested field} | {closed type, enum, item constraints and allowed semantic references} | {parent definition; recorded-fact source or interpretation; meaningful cross-field relationships} | {latest interpretation value; recorded facts are filled by the host at closure} |

Do not add fields or unrestricted findings. Recorded facts come from their original records, not a restatement. Keep uncertainty in the permitted fields. Tool outcomes do not silently replace your last admitted interpretation.

Reply in the declared text form: either **Request context** followed by the requested own-attempt fields/page, or **Select action** followed by the action name, its declared fields and the requested interpretation-field updates. Use the listed exact field names, types and allowed values; lists use Markdown rows. Do not emit JSON, audit identifiers, fingerprints or implementation metadata. The host resolves the displayed labels and validates the resulting internal action and return-form values.

---

## Exact fill map

| Prompt block | Existing producer and receiving consumer | Selection rule / required gap |
| --- | --- | --- |
| Objective, target, scope, constraints, requested purpose | `Workflow.selected` → `ScientificProcessEpisodes.prepare_invocation`/`_invocation`/`_assignment` → `Workflow.build` → `DecisionSource.next` | Use child's `goal.objective`, fixed scoped subject identity, assignment constraints and needed supplied context. Do not print the entire `EpisodeGoal.as_record()` or root `task_context`. |
| Annotation-support focus and operands | `ScientificProcessEpisodes.decision_context` resolves the pinned annotation entry; `support` contains proposition, operands, qualifications and boundary | Render the selected body. Do not invent scoring dimensions or equate an operand with realized credit. |
| Thought pattern | The same method resolves `name`, `description`, `use_when`, `live_alternatives`, `decision_guidance`, `outcome_contingencies`, `boundary` | Preserve the full selected guidance; render separate rows as needed without inventing pairings among independent lists. |
| Scientific working knowledge | `Workflow.working_state` → `Store.reasoning_view`, restricted by the receiver's receipt selection where bound; `DecisionSource.next` supplies the model view | Render relevant received records with actual subjects, locations, conditions and validity. Do not inherit all source bodies merely because a reference is mentioned. Preserve paging and explicit currentness. |
| Annotation identity/edit semantics | `Store.put` uses subject/context attribution as annotation key and `current_revisions`; `domain.REASONING_SCHEMA` requires `expected_revision` | Keep the exact presented record/revision in a frozen internal label map. Translate an edit against that snapshot; keep optimistic conflict validation. Never show a new candidate for an annotation revision. |
| Latest outcome and child returns | `DecisionSource.next` → `local_outcome_preview`; `EpisodeView.model_inputs` admits only this receiver's direct-child forms | Render actual outcome facts and admitted values, preserving partial results and feedback. No child's private history or parent yield history. |
| Credit and continuation | `Workflow.source_credit_view`, `source_credit_binding`, `annotation_context`; actual `view.controller_state` | Render actual scalars and declared meaning only. If math/score is unbound or not supplied, say unavailable. Do not label finding counts, support routes or a library focus as score. |
| Category yield table | `exchange_decision` → `decision_history.yield_table` → `_attempt_rows`, `_observations`, `_expectation`; parameters from `_category_yield_parameters` | Reuse saved signed gains, own completion order, conditional category estimates and existing uncertainty/status. No new formula, redistribution or controller effect. |
| Specific attempts | `lookup_attempts` / `_record` / `_lookup_detail`, scoped to this episode and `before=index` | Current lookup already retains exact selected inputs and actual publication arrays, but outcome bodies are only fingerprints and detail permits selected inputs only. Render semantic input/publication rows and explicitly mark unread content; do not pretend a hash supplies an outcome. Additional result-detail access would require a deliberate scoped interface, not invented prose. |
| Pending work, duration and wait | `DecisionSource.next` supplies `pending_work`; `DecisionSource.call` adds original execution/native expectations, resource estimates, native-event targets, waiting support and recorded initial binding information | Include only work/configurations pertinent to this child; preserve actual interval, timestamps, support/censoring and unknowns. Omit raw waiting training histories. Existing caller bindings determine availability. |
| Actual actions and tools | `ScientificProcessEpisodes.catalog`/`common_tool_names` plus `Workflow.catalog`/`action_schema` | Render only the final effective catalog and permitted common actions. Resolve selected tools against actual current callables; list each once. No unselected tool map or raw JSON Schema. |
| Return form and updates | Original `TypedReportContract`, `interpretation_schema`, current `report_values`; consumers `apply_response`, `validate_report`, `finish`/`form_with_facts` | Translate the exact original closed schema into field tables. Host facts remain host facts. Preserve independent scientific row admission and valid work when report repair fails. |

## Reuse, omissions and concrete gaps

Reuse immutable assignment/tool-contract checks, the common `method_loop` decision loop, receiver-specific receipts, admitted direct-child forms, separate credit projections, signed category history and exact saved decision/exchange replay. The change is presentation and deterministic addressing/parsing; it supplies no scheduler, scorer, stop gate or extra model composer.

Do not print `selection` reference objects, `initial_selection_sha256`, revision origins, invocation/goal/episode/run/session IDs, state-frame hashes, library bindings, implementation fingerprints, transport metadata or receipt machinery. Keep them internally for validation and replay. Show only scientific source provenance and semantic references required to assess evidence or select actual operands. Omit unrelated record categories, inherited source inventories, parent controller/yield history, all-source inheritance, launch-library indexes and unselected manuals. Include a selected manual's relevant instructions only when they constrain an available action or the assigned job.

The current final boundary is still JSON: `ScientificProcessEpisodes.decision_context` returns selection/assignment objects; `DecisionSource.next` adds broad state/contracts; `model_snapshot` mostly copies that context; `state_frame` adds revision hashes; `_SessionConnection.complete` sends `json.dumps(context)` as model text. Exchange mode removes controller scores and raw wait histories but does not implement this template. Its output envelope and lookup replies are also JSON. Required implementation gaps are (1) this receiver-specific text renderer, (2) a frozen semantic label map used by action/form translation, (3) typed text response parsing through the existing independent action/report validation, and (4) text rendering of lookup replies and restored pending decisions. New decisions may use a new presentation contract; completed or interrupted old decisions retain their original saved inputs. A table-header change alone does not solve these gaps.

Inspected: complete `scientific_process_episodes.py`, `decision_history.py`, `decision_context.py`, relevant provider dispatch, `DecisionSource.next/call/instructions/exchange_decision/apply_response/execute/finish`, assignment/build consumers, scientific service credit/routes, received-state/revision paths, and the required design/practical-execution documents. Test definitions were inspected for existing invariants; no tests, model calls, network requests or scientific processes were run. Other message boundaries were not reviewed here.
