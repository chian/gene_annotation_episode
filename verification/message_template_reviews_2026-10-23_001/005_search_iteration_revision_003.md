# 005 — `literature_search__next_decision` — revision 003

```text
TASK

Choose which returned papers to examine to determine whether {gene} in {organism} should be annotated as {candidate_function}. Look for papers that can establish, qualify or contradict {specific_claim_about_gene_to_check}. Change your paper choices as you learn what the papers actually report.

Determine: {exact_question_about_gene_or_characterized_homologs_in_full}
The parent needs this result to: {specific_annotation_or_evidence_decision_the_parent_will_make}
Gene and product: {gene_product_and_known_public_identifiers}
Organism and relevant biological limits: {organism_strain_and_assigned_scope_in_full}
Required constraints: {parent_and_caller_constraints_in_full}

For each paper, ask what it could tell you about {specific_claim_about_gene_to_check}. Use its received title, abstract, publication details and any already examined results to identify a relevant experiment, comparison or qualification. Prefer a reason to examine that paper: an activity measurement, a substrate comparison, a phenotype, a molecular interaction, evidence about a required partner, or a limitation that bears on this claim. A high search rank, a familiar functional name or repeated use of the proposed annotation does not establish that the paper measured the claimed function.

Keep {gene} and its product distinct from the proteins actually studied in each paper. A paper may test the target, a close homolog, another family member, an engineered construct or an organism-level effect. A characterized homolog can inform the proposed annotation when that comparison is within your scope. Preserve which protein was tested and what relationship connects it to {gene}; do not present its assay as an assay on the target. Keep evidence for family membership, a specific activity, substrate preference and physiological role distinct when choosing a paper to examine.

Ask which paper could help distinguish {candidate_function} from {relevant_competing_functions_or_explanations}. A study of the right family can still leave the decisive activity untested. A study with an apparently conflicting result can be useful if its methods, construct, controls or conditions explain the difference. Select material that could resolve those particular gaps, including qualifications and negative findings. Before asserting an experimental result, examine the relevant source material and preserve the actual assayed subject, measurements and conditions. An abstract or search snippet can justify choosing a paper; it does not replace that examination.

Use the actual search coverage when deciding whether to examine a returned paper, acquire more metadata or make another available search. The question is whether the literature supports this claim about {gene}; the provider query is one attempted way of finding that evidence. Its terms, fields, filters and pagination can miss relevant papers. Distinguish a successful empty page, an exhausted reported result set, an unexamined later page, missing metadata and failed access. None establishes that the biological activity is absent. PubMed identifier-only results supply no titles, abstracts, organisms or assay conditions; obtain needed information through available operations rather than inventing it.

Keep track of what you actually know about each paper before choosing another read. Discovering a paper, acquiring its bytes and examining its results are different outcomes. A citation identifies a paper; it does not supply its contents or another episode's readings. A second representation, version or mention of the same study is not an independent experiment. Use only information actually supplied to you, obtained through your own selected work or admitted through your requested child result. Reexamining a paper can be useful for an unexamined experiment or qualification; rereading an unchanged passage does not create another finding.

You may search, acquire or read a paper through the registered operations below. When deciding where and how to examine one acquired paper needs an iterative investigation, you may commission a literature_page child. Give it that exact source and representation, the experiment or claim to check, the biological bounds, the constraints and the typed results you need for judging the paper's relevance to {gene}. Supply starting facts explicitly. The child chooses its reading approach; your history, yields and private source access do not become its context. Its internal turns do not become your observations. Choose a paper or child because of the evidence needed, without a required reading order, paper quota or compulsory child.

Available work
| Choice | How it helps assess the proposed function of {gene} | Required operands and restrictions | Information or commitment produced |
| --- | --- | --- | --- |
{actual_available_tool_reason_page_child_wait_and_repair_contracts}

Choose one available action that can improve your assessment of {specific_claim_about_gene_to_check}. Consider the actual paper candidates, what you have already tried, pending examinations, known duration information and your own expected yields. Use the reasoning action to commit an interpretation when already received evidence supports it; a new search is not required before every interpretation. Navigation, downloading and byte coverage are not scientific conclusions. Estimates inform your choice, and the configured controller owns continuation. Add no acceptance gate, stop action, turn budget, mandatory search sequence or polling cadence.

Return these requested results about {specific_claim_about_gene_to_check}:
| Field | Required type and allowed values | What the parent needs to know about the claim, paper or experiment | Recorded fact or your interpretation |
| --- | --- | --- | --- |
{complete_parent_requested_return_field_meanings}

Update only these declared interpretation fields, using evidence received before the action you are now selecting. Preserve the protein studied, conditions, qualifications and any limit on transferring the result to {gene}. The action you are about to choose has no result yet. Parent-supplied initial values are not new judgments by you. Recorded facts come from actual host records. Preserve valid partial findings and specific repairable failures. A page child's return can change which paper you examine next; it does not automatically settle the annotation claim.

Read your yield table as the outcome of your own completed source-selection, acquisition, reading and interpretation actions, excluding inherited starting information. Expected next yield is conditional on completing that category again. Use the supplied units, uncertainty and unavailable reason; an unavailable estimate is not zero or a success probability. Acquiring a useful paper can have zero immediate credit before interpreting it. Keep investigation progress, annotation support, monitoring information and execution duration separate.

Use the existing typed JSON decision response. If you need an exact earlier own input to avoid repeating a search or read, use the declared request_context exchange and then finish choosing this same action. When ready, return one selection with the current report_update. This complete TASK applies after the lookup too. The lookup, report construction and statistical refresh add no action observation; completed selected work supplies its ordinary local observation.

STEERING

| Current claim about {gene} | Received support or qualification | Unresolved difference between candidate functions |
| --- | --- | --- |
{only_next_decision_relevant_interpretation_rows_or_none}

| Search page | Provider, exact query and relevant filters | Actual returned extent / known total / continuation | Access outcome |
| --- | --- | --- | --- |
{necessary_received_search_page_rows_or_none}

| Returned paper | Received title, abstract detail or examined result bearing on the claim | Reported protein, organism and conditions | Available material / actual examination outcome |
| --- | --- | --- | --- |
{necessary_candidate_source_rows_with_unknowns_explicit}

| Relevant own attempt | Exact query, selected paper or page-child question | Actual outcome / admitted page return | Material qualification |
| --- | --- | --- | --- |
{necessary_specific_prior_attempt_rows_or_none}

| Own action category | Completed | Total signed yield | Expected next yield | Uncertainty / unavailable reason | Uncompleted attempts |
| --- | --- | --- | --- | --- | --- |
{own_action_category_rows_or_no_completed_observations}

| Requested interpretation field | Current admitted value | Basis / parent-supplied initial value |
| --- | --- | --- |
{current_requested_interpretation_rows_or_none}

{pending_table_only_if_relevant}
{timing_table_only_if_relevant}
{actionable_failure_table_only_if_present}
```

Optional factual table headers:

- `Pending paper examination | Experiment or claim to check | Actual state / received progress`.
- `Proposed search, read or wait | Existing duration / wait expectation | Statistical support / unknowns`.
- `Failed selected action or return | Actual failure and affected operands | Preserved partial work / repair-relevant fact`.

Fill notes: Use the actual gene, organism, candidate function, claim, comparison and intended parent decision in the original commission. These are substantive instructions, not process labels. Where a commission asks only about a reference experiment, render that exact experiment and its relevance to the named gene; do not manufacture a specific function or alternative the parent did not assign. The complete TASK is rendered on every exchange. Starting facts, search metadata, prior outcomes, admitted page results and current return values belong only in curt STEERING rows.

The original review in `005_search_iteration.md` retains the source/consumer trace and implementation limitations: search assignments do not already materialize candidate-paper rows; own-attempt lookup currently supplies selected inputs rather than older outcome bodies; readable operation operands still need deterministic binding to existing typed references. Use native received search metadata or admitted scientific findings; leave unknown subjects, experiments and conditions unknown. Existing typed response and return contracts remain unchanged. No process-slot labels, IDs, hashes or tracking information enter the prompt.

Revisions 001 and 002 preserved. Only this revision document was added; no application, tests, network, model calls, scientific runs or process configuration changed. This directness revision remains a draft for the user's running feedback.
