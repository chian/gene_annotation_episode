# 016 — Root → scoped scientific episode: corrected commission draft

The complete proposed model-facing prompt follows. TASK is the child's detailed
recurring assignment; STEERING contains only explicitly supplied starting facts.
Braced positions are independently rendered text, not serialized source objects.

---

**TASK — included in full on every iteration**

Determine whether **{specified evidence relationship}** supports annotating
**{gene/protein and organism}** as **{candidate function}**. Establish
**{specific biological distinction needed to judge that annotation}**. Return
**{concrete evidence or comparison the parent needs to make that judgment}**.

The target is **{fixed gene/protein and organism}**. Examine **{assigned
biological subjects and original-coordinate bounds where relevant}**, within
**{all binding scientific and resource constraints}**. Choose how to answer this
question and revise your approach using the evidence you actually obtain.

The candidate function is **{assigned function or biological role}**. Determine
what the evidence supports, including evidence that qualifies or contradicts
that function. Compare **{explicitly assigned competing functions, or no
additional comparison}**. Improving the claims and evidence for one candidate
changes that annotation; it does not create an additional candidate. Genuinely
different candidate functions retain their own evidence and annotation scores.

{Detailed biological instructions for judging this candidate function from the
assigned evidence about this gene: relevant measurements, comparisons,
qualifications and inference limits.}

{Full instructions for comparing the actual biological alternatives or making
the other assigned judgment: what distinguishes the alternatives, what each
possible observed outcome would change, and where the inference stops.}

Use the supplied starting facts in STEERING as evidence, with their stated
qualifications. Illustrative examples in the instructions explain a way to
investigate; they are not observations about this gene. A citation attributes
a supplied finding; it does not provide the paper's other contents or access
to other records.

Keep the biological target fixed. For evidence about another protein, organism,
structure, genomic neighborhood or experiment, identify the actual studied
subject, measurements and conditions. Preserve the relationship that makes it
informative about the target, and the limits of that transfer. Distinguish
family membership, molecular activity, cellular or organismal role and
localization when those differences matter. An assay on a homolog can strengthen
an annotation through a justified homology relationship; it remains an assay
on that homolog.

Compare the relevant explanations using observations that could distinguish
them. Consider whether apparent agreement or disagreement concerns the same
proposition under comparable conditions. Preserve informative negative results,
conflicts, missing partners and condition differences. Failure to retrieve or
measure something is not itself a biological negative. A useful correction can
advance this investigation while reducing annotation support.

Choose the next search, comparison, evidence examination or interpretation that
could answer **{the concrete question about this gene and candidate}**, using
the available operations below. Before repeating an attempt, determine what a
changed query, comparison, coverage or configuration could reveal that the
earlier attempt did not. Interpret each result for the candidate function;
obtaining a measurement does not by itself establish that function.

| Available choice | Purpose and relevant instructions | Required inputs and limits |
| --- | --- | --- |
| {each actually selected tool or permitted common action} | {complete instructions needed to choose and use it} | {meaningful operand fields, allowed values and binding restrictions} |
| {each allowed child investigation} | {its actual scientific responsibility} | {commission question, scope, constraints, supplied information and requested typed result} |

If a narrower question warrants a child investigation, name the biological
question, its target, constraints, starting facts and exact result you need.
The child chooses how to investigate it. Use the returned measurements or
findings with their actual subjects, conditions and qualifications to judge
**{the assigned annotation claim}**.

Keep **{the assigned biological question and its original approach}** fixed for
this episode. If a different comparison or investigation approach becomes
useful, an explicit `process.revise` can prepare it for a separately commissioned
child. Preserve which approach produced each returned finding. Preparing an
alternative neither starts that child nor changes this episode's assignment.

Use your own action-category yield information as it becomes available. Observed
totals describe completed work; expected next yield concerns another completion
of that category, with the stated uncertainty. Unknown is not zero. Scientific
investigation progress, annotation support, monitoring information and duration
expectations have separate meanings. The configured controller governs
continuation. Choose actions within the assignment rather than following a
compulsory sequence or an invented search, tool or turn quota.

Return the following information about **{gene and candidate function}**:

| Requested field | Type and allowed values | Full scientific meaning and required qualifications | Recorded fact or your interpretation |
| --- | --- | --- | --- |
| {each original requested field} | {declared type, item and allowed-value constraints} | {original parent-defined meaning and meaningful relationships to other fields} | {actual fact source or interpretation responsibility} |

Keep those result meanings and the existing typed JSON response contract.
Update interpretation fields using information already received; an action you
are about to select has no interpreted outcome yet. Recorded fields come from
actual outcomes. Initial interpretation values supplied by the parent are
starting values, not new judgments by you. Preserve useful partial work and
specific failure information that permits repair. If an own-history lookup is
needed later, it supplies information for that same decision and creates no
completed-action observation.

**STEERING — explicitly supplied starting information**

| Assigned candidate or explicitly assigned comparison | Current selected claims | Parent-stated uncertainty |
| --- | --- | --- |
| {candidate's meaningful label} | {only explicitly supplied current claims} | {relevant uncertainty} |

| Supplied fact or prior interpretation | Actual observed subject and conditions | Selected result | Material qualification and provenance |
| --- | --- | --- | --- |
| {explicitly parent-selected proposition; distinguish fact from interpretation} | {actual subject and selected conditions} | {exact selected result, preserving native units} | {explicit limit; meaningful publication/location if supplied} |

| Requested interpretation | Starting value | Supplied basis or limitation |
| --- | --- | --- |
| {field} | {original supplied value} | {explicitly supplied basis or unknown} |

| Relevant prospective work | Supplied duration expectation or measured interval | Support and uncertainty |
| --- | --- | --- |
| {actual available configuration, only if supplied and relevant} | {value, units and interval meaning} | {actual supplied support or unknown} |

Only explicitly selected, decision-relevant rows are rendered. Omit inapplicable
tables. No parent action history, parent yields, private reasoning, source
inventory or automatically expanded reference contents enter this commission.
The child has no completed own-action observations at launch; its later steering
uses its own observations and received results.

---

## Construction and receiving-decision trace

| Block | Source → selection → use |
| --- | --- |
| TASK: assignment | Selected child objective, scope, binding constraints and original report purpose → render this child's complete assignment, not the root's whole task → child can choose within the scientific question it actually owns. |
| TASK: composed process | Resolved selected support proposition/operands/qualifications/boundary and selected thought description/use-when/live alternatives/decision guidance/outcome contingencies/boundary → render substantive instructions in full → child knows how to investigate and how different outcomes affect its choices. |
| TASK: capabilities | Actual selected tool names resolved against the real current catalog, plus permitted common actions and child roles → render callable meanings and operand restrictions → child chooses a real capability without fabricated operations or an imposed itinerary. |
| TASK: requested result | Original typed parent form, original field meanings and actual fact-source meanings → render requested scientific information and each field's responsibility → child interprets its assignment without replacing the return schema. |
| STEERING: starting facts | Finite parent-selected fact cells with actual subjects, conditions, selected results and qualifications → display exactly those cells → child receives the information needed to start, without receipt ancestry or reference closure becoming knowledge. |
| STEERING: current values | Explicitly supplied candidate claims, commissioned comparisons, starting interpretation values and relevant prospective timing facts → display only relevant actual values → child can identify the initial uncertainty without tracking the parent. |
| Later exchanges | Same complete TASK plus this child's newly selected terse STEERING → no dependence on old chat turns retaining instructions → original task remains complete while the update remains concise. |

The two instructional fill blocks expand the complete selected library content
into the biological assignment; they are not new abbreviated headings in the
actual prompt. Slot names, library references and construction commentary stay
in these fill notes. For example, a homology commission would open: “Determine
whether sequence homology supports annotating {gene} as {candidate function}.”
Its detailed instructions would then describe comparing characterized homologs,
preserving native match scores and units, inspecting alignment coverage and
functional correspondence, and distinguishing shared family membership from
the proposed specific function. The actual selected process supplies the full
reasoning and outcome contingencies. This example does not add a homology-only
restriction to other commissions or invent a threshold or scoring formula.

Current implementation does not yet provide the fixed parent-selected fact-cell
representation or a typed assigned-candidate input. `_ASSIGNMENT.context` is
unconstrained, `evidence_refs` are whole references, and current receipt handling
can inherit/expand other records. This template is a proposed boundary, not a
claim that those mechanics have been corrected. Candidate-specific scores are
not fabricated or copied from a scope-wide score. If the parent explicitly
supplies a relevant score, its exact candidate, value and declared meaning must
remain together in the supplied fact table.

The original template and its full boundary audit remain preserved. For this
revision, read the updated `AGENTS.md`, `docs/TASK_AND_STEERING.md`, the original
016 draft, the revised 002 role draft and the complete current
`gene_annotation_episode/scientific_process_episodes.py`. The original complete
runtime/commission/receipt/form-consumer trace remains the source for unchanged
mechanics. Opaque host identities, pins, hashes, revisions and validation metadata
stay internal; this revision adds no reference aliasing, output fields, scoring
formula or free-form response parser.

No application code, tests, model calls, network requests, run state or other
templates changed. This draft is ready to print for the user's running feedback;
it is not settled or implemented.
