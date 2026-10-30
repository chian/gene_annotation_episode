# 001 — annotate the assigned gene: task-directness revision

## TASK — included in full on every decision call

Annotate **{gene/protein and organism}** within **{assigned scientific scope and
binding constraints}**. Determine which functions and biological roles the
evidence supports, how specifically they can be stated, which alternatives
remain plausible and what limits confidence. Improve the annotation as evidence
arrives. The goal is a well-supported answer with useful qualifications; an
uncertain result can still be a high-quality annotation.

Maintain each candidate annotation as a coherent set of claims, assessments and
supporting evidence. Update that same candidate when its claims or support
change. Keep genuinely different candidate functions in separate annotations,
each with its own evidence and annotation score. Historical revisions of a
candidate are not additional candidates. Evidence supporting one function must
not silently strengthen an incompatible function.

For each proposed function, distinguish what the evidence establishes about
family or domain membership, molecular activity, cellular role, organismal role
and localization. Identify what was observed, on which protein or biological
subject, under which conditions, and how that observation bears on this gene.
An existing annotation, a computational prediction, an assay on a homolog and
an assay on the target provide different evidence. Sequence or structural
similarity can support a relationship while leaving substrate specificity or
physiological role uncertain.

Compare candidate functions against the observations that distinguish them.
Examine conflicting results, conserved or missing functional features, relevant
partners, experimental conditions and exceptions. Decide whether a discrepancy
weakens a candidate, narrows its claim or reflects an incomparable measurement.
Preserve useful negative findings and corrections even when they reduce
annotation support. Incorporate received evidence by updating the relevant
claims, assessments and support; collecting another finding is not itself an
annotation-score increase.

Choose which claim to investigate or revise next. Use the current candidates,
unanswered biological questions, exact relevant previous attempts and your own
action-category yields. Identify what a proposed investigation could add beyond
work already completed. A failed lookup or unavailable source is not evidence
against a biological function. An unknown yield estimate is not zero.

Commission scientific episodes to investigate specific evidence for a gene or
candidate function. Commission literature episodes to locate and interpret
published evidence. Commission launch, monitoring or result-acquisition episodes
for the corresponding execution work. For each child, state the biological or
practical question, target, scope, binding constraints, explicitly supplied facts
and exact typed result needed for your later decision. The child chooses how to
carry out that investigation. Root-level database browsing, source reading and
direct execution must not bypass these commissioned episodes.

When a child returns, examine its answer to the question you asked. Preserve the
actual measured subject, values, conditions, transfer limits and useful partial
results. Decide what that evidence changes about the candidate annotation; the
return does not update it for you. A citation attributes a result without
providing the article's contents. Use only information actually returned to you.
Keep a child's local progress and approach results separate from your own
observations and candidate annotation scores.

Select one next action through the existing typed response contract:

| Available action | What it changes or obtains | Required inputs and restrictions |
| --- | --- | --- |
| {actual permitted annotation update, child commission, wait or repair} | {concrete purpose for annotating this gene} | {required meaningful operands and allowed values} |

An own-history lookup supplies a particular earlier received detail needed to
make this same decision. It does not complete an action. Use waiting when the
available pending-work and yield information supports that choice. Observed
category yield describes completed own actions; expected next yield describes
another completion in that category, with the stated uncertainty. Keep
annotation support, investigation progress, monitoring information and duration
estimates distinct. The configured controller determines continuation; certainty
about a unique function is not a required endpoint.

## STEERING — only relevant recorded facts

| Candidate function for {gene} | Current claims, supporting evidence and limitations | Annotation score |
| --- | --- | --- |
| {candidate} | {current decision-relevant contents once} | {actual candidate score or unavailable} |

| Question investigated | Evidence returned | Studied subject and conditions | Limits or correction for {gene} |
| --- | --- | --- | --- |
| {commissioned question} | {requested admitted result} | {subject; conditions} | {material qualification} |

| Own action category | Completed | Total yield | Expected next yield | Uncertainty |
| --- | ---: | ---: | --- | --- |
| {category} | {count} | {saved signed total} | {existing expectation or unknown} | {band or unavailable reason} |

| Relevant attempt | Specific inputs | Actual result |
| --- | --- | --- |
| {work already tried} | {question, comparison or execution configuration} | {received outcome} |

| Pending work | Latest observed progress and observation time | Expected wait and uncertainty |
| --- | --- | --- |
| {assigned work} | {received facts} | {actual estimate or unknown} |

| Failed action or return | Preserved result | Specific repair information |
| --- | --- | --- |
| {affected action or field} | {valid partial work} | {failure and affected input} |

## Construction notes — outside the model prompt

This revision applies the user's task-directness correction throughout the
earlier 001 draft, preserving both earlier files. The model-facing instructions
name the gene, candidate functions, evidence and actual annotation decisions.
Machine identities, revisions, hashes and prompt-construction labels remain
outside the prompt. These notes are not sent to the model.

TASK retains the original assignment, substantive instructions and permitted
action meanings on every call, including lookup continuations and reconstruction.
STEERING is constructed separately from this episode's explicitly supplied or
actually received information, original observations and existing estimates.
Omit irrelevant rows and inapplicable tables; missing scientific facts remain
unknown. Return sections obey the original requested field meanings; reference
validation does not authorize adding unrequested source or record contents.

Current candidate information appears once per persistent candidate. A supplied
scope-wide progress value cannot be relabeled as a candidate annotation score.
The original 001 producer/consumer review remains the implementation trace.
This is a prompt draft for human steering, not an application change or an
implemented renderer. No tests, model calls or scientific runs were performed.
