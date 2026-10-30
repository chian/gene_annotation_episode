# Task instructions and iteration steering

Mandatory user direction, 2026-10-23. This document adds the distinction without
replacing earlier permanent design records. The user's current direction takes
precedence where those records describe a different presentation.

The user said:

> One is providing instructional information that every single iteration needs.
> IT IS THE TASK ITSELF. The other is steering information based on prior
> iterations - that needs to be controlled and curt and dry and summarized.

And:

> ONE NEEDS DETAILS, THE OTHER STRIPS ONLY TO WHAT IS NECESSARY.

## One prompt, two different responsibilities

Every decision prompt has two separately constructed blocks, TASK and STEERING.
They have opposite verbosity policies. Reducing steering must never shorten the
task instructions. Expanding task instructions must never expand past-iteration
material into a transcript or narrative recap.

### TASK: detailed instructional information required on every iteration

TASK defines the work itself. It contains the episode's actual assignment,
scientific scope, binding constraints, responsibility, substantive problem-solving
instructions, available kinds of decisions, and the meaning of its requested
result. It explains how to make and revise those decisions, including relevant
distinctions, possible misleading cues, alternatives, and interpretation limits.

For a composed scientific episode it includes the selected scientific-support
problem and the substantive thought-pattern instructions, alternatives, and
outcome contingencies. A process name, tool list, goal heading, or one-line role
description does not supply these instructions. Selected instructions are not
evidence about the target.

The complete TASK is supplied on every decision call, including a call following
an internal information lookup or reconstruction. Its correctness cannot depend
on an earlier chat message surviving backend history or compaction. Parent
commissions construct the child's TASK from the scoped assignment and requested
return, not from the parent's entire task, private reasoning, or history.

TASK is not reduced using a history-summary budget. Detail is retained because
it specifies how to do this particular work; unrelated boilerplate and host
bookkeeping are not task detail.

### STEERING: controlled, curt, dry information derived from prior work

STEERING supplies only recorded information that affects the next decision under
the TASK. Use concise factual tables, including the episode's own action
categories, observed total yield, expected next yield, and uncertainty. Include
specific prior attempts or outcomes when needed to distinguish another useful
action from repetition. Include relevant returned findings, changed scientific
interpretations, pending work, timing information, and actionable failures only
when they affect that receiver's choice.

Do not repeat the task instructions here. Do not supply full histories, generic
narrative summaries, all stored records, raw source inventories, configuration
objects, fitting diagnostics, IDs, hashes, revision/frame metadata, or unrelated
facts. Unknown information stays unknown. Preserve material qualifications,
negative findings, units and uncertainty while removing irrelevant detail.

The current annotation is one persistent entity through its revisions. Show its
current decision-relevant contents once. Distinct candidate annotations have
their own contents and annotation scores; historical revisions are not additional
candidates. Do not relabel finding-count progress as annotation score.

## Every boundary

- Within an episode, TASK is the recurring instructional block; STEERING is
  updated from this episode's actual outcomes and permitted received information.
- Parent to child, construct a detailed child TASK. Select any initial supplied
  facts explicitly. Do not import parent histories, yields, receipts, or source
  access. A reference needed for host validation is not delivered knowledge.
- Child to parent, the parent's TASK remains its own. Render the requested
  admitted child result as concise parent STEERING with the declared meanings
  and necessary qualifications. Do not turn a return into another task prompt,
  extra model-composed report, or private child history.
- Lookup, repair, monitoring, execution, result acquisition, and tool-retrieval
  paths obey the same distinction at their actual receiving decision.

Each concrete template boundary needs its own decision/information analysis.
Templates may reuse mechanical rendering, not substitute a generic prompt for
the substantive reasoning instructions of a different task.

## JSON is the intermediate, not the prompt

Host records and typed handoffs remain structured JSON as appropriate. A
deterministic prompt builder selects declared information from those records,
renders the detailed TASK and terse STEERING as designed text and readable
tables, and sends that text. Serializing the intermediate object, wrapping it
in a JSON envelope, or merely renaming its keys does not implement this design.

Keep machine identities, custody, persistence, validation and recovery outside
the model-facing text. Existing typed response and parent-form contracts remain
separate; text input does not authorize changing them into free-form responses.

The user requires seeing each proposed template and providing running feedback
before it is treated as settled or implemented. Preserve prior drafts and append
corrections; do not silently replace permanent records or claim implementation
from a template review.

## Task directness: user correction, 2026-10-23

The user said:

> Why "Investigate the selected scientific-support problem" as opposed to the
> gene annotation or the candidate gene annotation or something direct to the
> task. Weak words steer poorly when they are too weak.

And then:

> Yes, and this critique applies to all prompts. edit for task directness everywhere

Apply this correction to every prompt, not just its opening sentence. Detailed
TASK instructions must name the actual job, its objects and the decisions the
episode makes. For a scientific investigation, name the gene and candidate
function, the evidence being evaluated and the comparison or judgment needed.
For literature, name the claim or experiment to find and examine. For execution,
name the assigned software job, inputs, environment and required validated
result. For monitoring, name the running work and the progress or timing
observations needed. For retrieval, name the investigation and the actual
available operations to select.

Slot names, process-construction labels and renderer terminology belong in
implementation notes. They do not substitute for direct instructions. For
example, write "Determine whether sequence homology supports annotating {gene}
as {candidate function}. Compare the target with experimentally characterized
homologs; examine alignment coverage, conserved functional residues and
differences that limit transfer of the measured activity." Do not replace this
with "Investigate the selected scientific-support problem" or "Use the selected
thought pattern."

Preserve the scientific-support, thought-pattern and tool slots in construction.
Render their substantive contents as direct instructions about the assigned
work. Keep the complete detailed TASK and curt factual STEERING separate. For a
child return, preserve the parent's own TASK and make the returned facts refer
directly to its requested question; do not create another task instruction.

## Episode task versus current service coverage

The user corrected the API template on 2026-10-23:

> API_execution, your label of phmmer or hmmscan is too narrow, yes? Otherwise
> I think your spirit is right, just watch your wording. this would eventually
> be tied to many api services, including BV-BRC, which you should have included.

The common API TASK addresses the assigned work through its selected service.
Expand the actual relevant service instructions and operation meanings into
that concrete assignment. Do not define API execution as the protocol of the
first service implemented, nor impose one service's job states, polling stages
or pagination on other services. An immediate response is not a remote job.
Keep current implementation coverage and missing authenticated capabilities in
implementation notes; they do not define the common episode's purpose. Adding
real services extends the available operations and instructions under this
episode rather than introducing a new handwritten episode for every API.
