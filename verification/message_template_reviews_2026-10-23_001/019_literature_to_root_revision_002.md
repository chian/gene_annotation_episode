# 019 — Literature episode → annotation parent: revised return presentation

```text
TASK

{The annotation parent's complete recurring TASK, included here in full.
 Keep its detailed instructions for investigating this gene, comparing candidate
 annotations, interpreting evidence and choosing work. Do not substitute the
 literature child's task or shorten the parent's task when inserting this return.}

STEERING

{The parent's other relevant factual steering tables, constructed separately.}

Literature return: {original commissioned biological question}
Gene and organism: {fixed target already known to this parent}
Requested use: {parent's original stated use of this result}

| Biological question | Published result, with native values and units | Protein/organism and experimental conditions | Relationship to this gene or candidate annotation; exact limits | Source |
| --- | --- | --- | --- | --- |
{Only originally requested, admitted scientific information. Preserve the actual
 source assertion, assay/prediction distinction, measured subject and conditions,
 transfer relationship, negative finding or correction, qualification and
 bibliographic attribution to the extent those cells were requested and returned.}

{Only when the original request includes other information:}

| Requested information | Returned value | Material limitation |
| --- | --- | --- |
{Exact admitted values under their original meanings; preserve explicit empty,
 null or unavailable results. Include useful partial work without treating
 inaccessible or unexamined evidence as a biological negative.}

{Only when the parent originally requested the child's available approach measures:}

| Requested approach measure | Recorded value | Meaning and uncertainty |
| --- | --- | --- |
{Requested closing local credit, completed-own-action count, saved next-yield
 expectation/band or continuation comparison, with its actual meaning and units.}

{Only when actual return/delivery feedback requires the parent's attention:}

| Affected question or returned field | Recorded failure | Preserved partial result | Repair-relevant fact |
| --- | --- | --- | --- |
{Actual constrained failure and affected scientific object or field, expressed by
 its meaningful name; no invented result or recovered unseen source content.}
```

The braces specify renderer fills, not literal instructions inserted into the
model message. The parent TASK is emitted completely, just as on an ordinary
parent iteration. This boundary adds the compact literature-return portion of
STEERING. It does not create another assignment, another episode or another
model call. The parent's existing task instructions explain how to evaluate and
integrate evidence; the return does not repeat them.

Omit unrequested columns, optional tables and irrelevant rows. Use the original
field's declared scientific meaning as the heading when it does not fit the
scientific table above. This is a presentation pattern for the existing form,
not a new universal return schema. A form containing only references does not
automatically permit the renderer to fill biological result cells from all
linked records. If no requested finding was returned, show that exact empty or
unavailable result, without inventing an exhaustive-search conclusion.

## Boundary-specific decision and information trace

The root's next decision concerns what the published result changes about the
annotation of the fixed gene: for example, whether evidence actually measures
the candidate activity, whether a homolog's result can transfer, whether a
different construct or condition explains a discrepancy, or whether a reported
negative weakens a claim. The return therefore preserves the requested measured
result, actual protein/organism and conditions, relationship to the target and
limits. It does not send the child's queries, reading route or private decisions.

| Fill | Actual producer and exact selection | Receiver use and limit |
| --- | --- | --- |
| Parent TASK | Parent's original assignment and complete recurring annotation instructions | Preserve the detailed biological investigation task on this call. No instruction compression, child-task substitution or dependence on earlier chat. |
| Question and requested use | Original child goal objective and frozen `ReportContract.decision` | Associate this return with the question the parent commissioned. No retrospective narrative about the child's work. |
| Scientific table | Exact admitted `ParentReport.values`, original `ReportContract.information`, and only the scientific fields explicitly permitted by that form's meanings | Preserve the source's proposition, actual subject/conditions, native result and target interpretation separately. The renderer selects recorded cells; it does not make a new biological judgment. Unknown or undeclared information stays unknown. |
| Source | Originally permitted identifying bibliographic information for that returned proposition | Attribution only. A title, DOI, PMID or PMCID neither supplies article contents nor grants source access. No automatic hydration of source bodies, quotes, anchors or linked records. |
| Other requested values | Exact admitted constrained fields, including partial/access/timing/pending facts only where requested | Preserve field meanings, material qualifications and unknowns. An access failure and an actual reported biological negative remain different results. |
| Approach measures | Only originally requested common `credit` or `episode_yield` facts that were actually returned | Preserve original saved closing values and availability. No inferred initial credit, net progress, trend, category history, process-revision lineage, success probability or scientific confidence. Child credit is not added to parent credit. |
| Failure/repair | Actual constrained admission or delivery feedback, plus preserved returned partial facts | Let the parent address the specific failed delivery without inventing unreturned scientific work. |
| Other parent steering | This parent's own recorded attempts, category estimates, current candidates and relevant pending information | Reuse the parent's decision-specific steering renderer. No child-private history enters those rows. Each candidate remains one entity through revisions with its own actually supplied score. |

## Checked implementation boundary

Read `docs/TASK_AND_STEERING.md` and the preserved original 019 review. Rechecked
the current complete literature binding, `DecisionSource.apply_response`,
`DecisionSource.finish`, the return-admission functions, `Workflow.receive_form`
and `Workflow.facts`, parent `DecisionSource.next`, `method_loop._model_inputs`
and the provider input construction. The required project goal/episode/time
design records were consulted; this revision changes presentation design only.

The literature binding supplies no separate summary fact source. Child closure
freezes the existing form from recorded facts and existing interpretation
values, with no report-composer call. Admission checks the original contract
and frozen facts. The parent model-input boundary selects admitted direct-child
reports. A returned commission supplies its one parent completion; its internal
turns do not become parent observations. Reference receipt traversal is not a
field-disclosure rule. The current provider still serializes the context object;
this draft does not claim a text renderer is implemented.

Detailed parent instructions and terse returned facts are deliberately different
parts of one prompt. Existing typed JSON output and parent-return contracts are
unchanged. No application code, tests, network requests, model calls or run state
were changed. The original review is preserved. This draft awaits the user's
running feedback before being settled or coded.
