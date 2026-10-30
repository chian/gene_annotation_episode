# Root child-choice trace, 2026-10-23

Read-only investigation of `annotation_quality_rerun_003`. This is an additive
evidence record and prompt proposal, not an implemented or approved template.
No model calls, external requests, jobs or source-code changes were made for
this inspection. The run was stopped by the root at the user's direction.

## What the model was actually offered

Primary evidence is the public request:

`/home/chia/gene_annotation_episode_runs/annotation_quality_rerun_003/providers/62c95e36708d49c4a55a829a2fa0506a/session-0001/call-00001/request.json`

Its output schema offers 68 direct-tool alternatives and five `episode_child`
alternatives: `scientific_process`, `literature`, `launch`, `monitor`, `results`.
It also offers reasoning, waiting and report redelivery. The root therefore did
receive both direct-tool and child-commissioning choices.

At inspection, `workspace/state.sqlite3` contained 37 answered model selections:
34 tools and three reasoning commits. One further call was unanswered. None of
the public model responses selected a child; `runtime_commission_intents` had
zero rows and `runtime_episodes` had only the root. This also rules out a child
selection rejected before reaching the action journal in these answered calls.
The only nonempty decision feedback was `ncbi_contact_not_configured`.

The root's actual instruction says:

> Select one ordinary tool, one typed reasoning commitment based on available
> existing evidence, or one substantive child improvement. A tool lookup alone is
> not a child Episode. There are no biological departments or compulsory stages.

The root sees six configured resources: Aurora, local, EBI HMMER, UniProt,
BV-BRC and NCBI BLAST. Availability is explicitly unknown. NCBI BLAST's contact
precondition is explicitly false. These are configured capabilities, not probes
or successful deployment claims.

## Missing decision information and asymmetric construction burden

1. **Root instructions do not explain the two execution paths.** They describe
   a generic child improvement and typed forms, but do not explain that a launch
   episode chooses among permitted API/local/HPC requests, that its execution
   children own iterative preparation/repair, or that the parent can continue
   other work while a child runs. The launch-specific instructions exist in
   `ExecutionEpisodes.instructions`, but are supplied only after launch has
   already been commissioned. See `runtime.py:502`, `runtime.py:912`, and
   `execution_episodes.py:347`.

2. **Child-specific return facts are missing from the parent's discovery menu.**
   The root's `available_report_facts` has 15 general sources and no
   `execution_handoff_refs`, `execution_result_refs` or `execution_completed`.
   Its form instructions say to use facts named in that menu. However, a launch
   form is compiled against `report_sources('launch')`, which supports those
   execution facts. The menu uses `report_sources` for the parent role instead.
   Thus the host supports useful launch returns without telling the assigning
   parent their names and meanings. Common `changed_record_refs` remains
   available, so this does not make commissioning impossible. See
   `runtime.py:1176`, `runtime.py:2250`, `runtime.py:3023`, and
   `runtime.py:3105`.

3. **The launch alternative is mostly an encoded schema.** Its generated
   schema option is 23,426 characters, including a 15,937-character assignment
   schema embedded inside a string description. It requires a goal, scope,
   purpose, closed return schema, initial interpretation values and an
   assignment containing concrete resource-specific requests. Direct BLAST
   requires three operands. Local/Aurora request definitions require 11 fields,
   including progress requirements and completion keys; the generic API request
   definition requires six. This is an observable construction imbalance; it
   does not establish the model's private reason for its selections. See
   `runtime.py:3019` and `execution_episodes.py:133`.

The four relevant current modules (`runtime.py`, `execution_episodes.py`,
`scientific_process_episodes.py`, `episode_bindings.py`) have identical SHA256
values to their copies under this run's `implementation/` directory.

## Separate scientific-process construction block

The frozen scientific library contains 19 thought-pattern entries and zero
scientific-support entries. A scientific-process assignment requires an
`annotation_ref` selecting an existing A entry, and resolution rejects unknown
entries. Consequently this one advertised role cannot currently be validly
constructed from the frozen library. This does not block `launch` or `literature`,
whose schemas and assignment preparation do not resolve that scientific slot.
The root did not attempt process discovery or construction in the inspected
actions. See `scientific_process_episodes.py:63`,
`scientific_process_library.py:368`, and the run's
`scientific-process-library/index.json`.

## Proposed root TASK addition for user review

This is a proposed addition to the detailed recurring root TASK. It does not
replace its scientific interpretation instructions or belong in STEERING:

> You retain responsibility for the candidate annotation of ybhP/b0790. You can
> perform a selected operation here, or commission a child episode to own a
> narrower problem that contributes to that annotation. A tool call performs the
> operation you select. A child episode makes repeated choices within the job,
> scope and constraints you assign, using intermediate outcomes to decide what
> to try next. Choose which ownership fits the work you want done.
>
> A literature child investigates a question about published evidence. A launch
> child establishes execution of the computational work you assign: where your
> constraints leave the choice open, it chooses among the permitted API, local
> and HPC requests. Its resource-specific children own iterative preparation,
> submission, observation and repair in their assigned environments. Assign the
> work and preserve explicit input/resource constraints; request the typed
> handoff or result information you need for your next scientific decision.
>
> Define what the child's returned fields mean before commissioning it. Use the
> declared return facts for that child role, rather than asking for a narrative
> recap. You can continue other useful work while a commissioned child runs,
> inspect requested progress through monitoring, or choose a wait. Receive and
> assess the returned evidence before integrating it into this gene's annotation.
> These are available choices, with no required order or obligation to commission
> a child.

## Scoped follow-up proposal

- Review the root TASK addition and a parent-facing child-options presentation
  with the user before coding either. The presentation must explain each
  available child's responsibility, required commission inputs, supported return
  facts and actual construction availability. It must distinguish ownership of
  iterative work from a one-off operation.
- Expose `report_sources(child_role)` with its declared field types and meanings
  to the assigning parent for each available child. Render it as task/contract
  information; do not send child-private histories or force a return form.
- Review the launch commission's concrete-request burden separately before
  proposing any schema change. Preserve caller constraints, explicit allocations
  and the launch episode's resource choice. No adapter, automatic dispatcher or
  predefined itinerary is proposed.
- Treat the empty scientific-support slot as its own unfinished construction
  item. Do not invent support entries or claim launch depends on populating it.

No claim is made that child transport was exercised by this run, or that these
observations establish the model's private reason for choosing direct operations.

## Later user direction, preserved additively

After the preceding inspection/proposal, the user explicitly requested removing
ordinary root tools. The earlier proposal to explain two root execution paths is
therefore historical and is **not** the proposed TASK for the next run. The
inspection facts remain unchanged. The subsequent implementation-boundary plan
is `verification/root_tool_removal_scope_2026-10-23_001.md`. No change or relaunch
was performed by this workload.
