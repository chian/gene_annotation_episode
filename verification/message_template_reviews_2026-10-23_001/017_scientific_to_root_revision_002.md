# 017 — scoped scientific child → annotation parent, revision 002

## Proposed receiving prompt composition

This boundary inserts a received result into the annotation parent's next
prompt. It does not assign a new task to the parent. The first fill below
expands to the parent's complete detailed TASK from its own iteration template,
unchanged; it is not a role heading or a summary of those instructions.

```text
TASK

{complete_annotation_parent_TASK_in_full_unchanged}

STEERING

{parent_own_other_decision_relevant_steering_tables}

Received investigation: {original_parent_commissioned_question}

| Requested distinction | Returned result | Actual subject and conditions | Material qualification | Attribution |
| --- | --- | --- | --- | --- |
{only_originally_requested_admitted_scientific_result_rows}

{only_if_other_requested_information_was_returned:
| Requested information | Returned value | Material qualification |
| --- | --- | --- |
{other_originally_requested_admitted_value_rows}
}

{only_if_approach_results_were_requested_and_admitted:
| Returned approach | Origin | Initial / closing local progress and meaning | Completed own actions | Closing expected next yield | Uncertainty |
| --- | --- | --- | ---: | --- | --- |
{requested_actual_process_result_rows}
}

{only_if_requested_partial_work_or_failure_affects_the_next_choice:
| Requested result | Useful partial result | Specific limitation or failure |
| --- | --- | --- |
{requested_actual_partial_or_failure_rows}
}
```

All braced conditional sections are renderer instructions, not text sent to
the model. The result contributes only the compact tables above. The parent's
existing TASK supplies its annotation-integration responsibilities, scientific
reasoning guidance, permitted decisions and response instructions. Do not
repeat or replace them with a return-specific instructional paragraph.

## Exact fill and receiving-decision trace

| Fill | Source and selection | Receiving use |
| --- | --- | --- |
| Complete TASK | The annotation parent's own complete recurring TASK. | Preserve the actual annotation assignment and how to reason about it; child closure changes no parent instructions. |
| Other parent STEERING | The parent's separately constructed iteration update, using its own actual outcomes, action-category yield estimates, current candidate annotations and relevant pending work. | Compare the return with the parent's current information and choices. This return renderer does not rebuild that update or replace parent yields with child yields. |
| Commissioned question | Original `child.request.goal.objective`, associated with the original contract's declared decision purpose. | Identify which commissioned uncertainty the result addresses. Copy the original question; do not synthesize a retrospective task description. |
| Requested distinction and returned result | Exactly the admitted `ParentReport.values` fields and their original `ReportContract.information` meanings. A requested finding reference supplies only the scientific field contents expressly allowed by that original meaning. | Assess whether the result strengthens, qualifies or corrects a candidate claim, distinguishes alternatives, or motivates further investigation. Preserve measured values and native units. |
| Actual subject, conditions and qualification | Only the originally requested and admitted observation, source-claim, assessment or interpretation fields: actual studied subject/construct/organism; relevant conditions; declared relation, qualification, negative result or correction. | Distinguish evidence on a homolog from a target measurement, and comparable evidence from a transfer limitation. Preserve requested content and limitations together. Unknown stays unknown. |
| Attribution | Only identifying source metadata permitted by the requested result, such as the publication label, accession or exact allowed location. | Attribute the proposition. A citation does not supply source contents or grant source access. |
| Other requested values | Other admitted fields in the parent's exact original form. | Preserve their specific scientific, timing or operational meanings. A timing value is not scientific support; a scope-wide score is not a per-candidate annotation score. |
| Approach | Explicitly requested `scientific_process_results` rows, resolved to the pinned support, thought-pattern and actual operation names. | Show which returned approach produced the actual local result. Do not append a library body, tool manual or private decision history. |
| Origin | The same row's authenticated `origin_kind` and original parent/preparation relationship. | Distinguish an ordinary commissioned child from an explicitly prepared `process.revise` alternative. Display its originating approach by an already known meaningful name; do not infer that relationship merely because tools differ. |
| Initial / closing progress | The same requested row's unchanged `initial_credit`, `credit` and actual binding meaning/units, when known. | Keep the approaches' actual contributions separate. These are child-local values, not an added parent score, referral bonus, normalized productivity or candidate annotation score. State an unavailable meaning rather than guessing it from `credit_kind`. |
| Completed actions and closing yield | The same row's original `completed_actions` and `episode_yield.expected_next_gain`; nullable or unavailable values retain that status. | Report actual count, final value and original band. Decode status/method codes into readable meanings; never expose sentinel coordinates as negative forecasts, refit the values or infer a trend from one closing estimate. |
| Partial result or failure | Only an originally requested and admitted partial-work/failure field. | Preserve useful results and the specific missing or failed contribution that can inform repair. A missing result is unavailable, not biological negative evidence. |

Only columns whose meanings are actually declared by the original requested
form are rendered. If a declared result lacks its requested subject, conditions
or qualification, show that part as unavailable; do not recover it by traversing
unrequested linked records. A generic changed-record reference does not silently
authorize the whole scientific finding table. Where the original form cannot
supply the needed contents, this proposal exposes that contract gap rather
than constructing a new scientific summary.

Optional process rows can include an alternative child's result only if that
result was actually forwarded through every intervening requested form and
admitted for this parent. One child result remains separate from another. There
is no arbitrary descendant lookup, inferred referral score or added parent
credit. The parent's own action-category table continues to use its own saved
observations; child internal actions never become parent observations.

The return adds no annotation snapshots from shared storage. Each candidate
annotation remains its own persistent entity through revisions, with its own
actual annotation score when available. The parent uses its own current received
candidate information; historical revisions are not alternative candidates.

## Construction and status

The existing typed JSON response and original parent return form are unchanged.
The host freezes recorded fact fields and existing interpretation fields through
`DecisionSource.finish` / `form_with_facts`; admission supplies the direct return
to this parent. A deterministic text renderer selects the declared contents and
builds the tables. It adds no model call to compose or restate a report.

The relevant path remains `DecisionSource.finish` → `Workflow.facts` →
`ScientificProcessEpisodes.facts` → original-form admission / `receive_form` →
the annotation parent's next decision inputs. `ScientificProcessReports`
preserves original process closure values; provenance forwarding selects only
successfully admitted fields explicitly sourced as `scientific_process_results`.
`method_loop._model_inputs` restricts received reports to those admitted for this
parent. Host reference validation and receipt traversal are not content-disclosure
instructions.

Read for this correction: `docs/TASK_AND_STEERING.md`, the preserved 017 draft,
the corrected 001 parent TASK, complete `scientific_process_reports.py` and
`episode_reports.py`, and the relevant complete closure, fact-construction,
process-forwarding and model-input functions. Original broader path inspection
is recorded in the preserved draft. This revision changes only this document;
no application code, schemas, tests, model calls or run state changed. It remains
a proposal for the user's running feedback.
