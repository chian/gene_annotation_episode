# Episodic implementation principles

For episode diagrams, follow [docs/EPISODE_DIAGRAMS.md](docs/EPISODE_DIAGRAMS.md).

For checklist item W04, read
[the evidence-axis library instructions](docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md)
before doing that work. Preserve three separate responsibilities: investigation
prompt text; scoring rubric meaning the scoring sheet/format/template; and
separate grader/reader functions that POPULATE the sheet, deterministically
wherever possible. The sheet must contain actual numerical score components
usable to compile annotation credit; a table of source claims and metadata does
not satisfy this. Define how each number is obtained and what it evaluates.
Start the investigation from supplied sequence, selected file contents or
snippets; do not require a candidate annotation or publicly searchable name.
Possible functions can emerge from the evidence gathered during investigation.
Do not replace the sheet with grading rules or insert it
wholesale into prompts. W05 owns connection to the annotation-credit function.

These instructions record the user's design requirements. Read `GOAL.md` and
`docs/EPISODE_STRUCTURE.md` and `docs/TIME_AWARE_ESTIMATION.md` before changing execution, estimation or episode
behavior. Read the relevant complete implementation paths, not just descriptions
or snippets. Current user instructions supersede historical designs and tests.

## Episode ownership

- The unit of composition is an intelligence carrying out an iterative
  problem-solving process. The information library supplies processes that fill
  a common mother episode template and help construct a child's decision
  problem, including a small relevant set of alternatives on each turn. Do not
  substitute tool manuals for process definitions or require a handwritten
  episode implementation for every problem. Parents supply the job, scope,
  constraints and requested typed return form; children own their iterative choices. See
  docs/EPISODE_STRUCTURE.md and docs/TOOL_KNOWLEDGE.md for the design and the
  current missing construction path.
- An episode owns an iterative investigation within its assigned goal and scope.
  Later decisions use earlier outcomes and can revise the approach. A one-off
  operation is a tool call, not a new episode.
- Execution consists of agentic work and selected tool calls within episodes.
  Resource instructions, skills and capability discovery are information/tools
  available there. No additional autonomous workflow layer owns their decisions.
- The scientific parent assigns the requested job and its constraints. The
  launch episode chooses which execution approach to try where that choice is
  open. Its resource-specific children investigate API/external-service, local
  compute or HPC execution, receiving the selected job, software instructions,
  resource instructions and parent-defined handoff form. Preserve explicit
  parent constraints and caller-owned allocations; infrastructure cannot choose
  or substitute an approach. This is the user's latest resource-branching
  direction; the older flat homology launch is not proof it is implemented.
- Infrastructure executes and records the selection. It must not substitute,
  expand or cancel selected work by making an episode-owned decision itself.
- The accepted independent-execution design is in docs/EPISODE_STRUCTURE.md.
  Scientific ownership survives independent execution. Recursive monitors still
  return parent-defined forms at closure. Waiting is an explicit yield-informed
  action. Parent yielding does not cancel descendants or reprice closed history.
  Implement independence in shared method_loop and its durable binding rather
  than a private background agent loop. Existing blocking children do not prove it.
- Episode structure is not a prescribed itinerary. Do not hardcode child order,
  polling cadence or a number of monitoring children. Do not hide an agent's
  iterative work in a tool call or a private nested loop outside method_loop.

## Estimates inform decisions

- Time/resource estimation and its use in iterative episode decisions are the
  first implementation priority. Tool execution alone does not establish that
  episode behavior.
- Timing information updates time expectations and earns monitoring credit for
  having gained timing information. Scientific information earns scientific
  credit. These remain separate; a job label does not assign information value.
- Time-aware estimation supplies duration expectations and their statistical
  support. It does not select actions, resources, timers, probes or cancellation.
- The episode responsible for choosing work needs the relevant information
  before that choice. A forecast available only after commissioning does not
  establish informed initial planning.
- The parent can choose an inexpensive timing experiment. Do not require such
  an experiment or fabricate transfer from a small job to a larger one.
- Keep scientific credit, monitoring information credit, execution-duration
  estimates and local yield histories distinct. No master combined score or
  artificial rescaling/smoothing of raw completed-action credit changes.
- Distinguish annotation support from scientific investigation progress. Useful
  source-grounded qualifications, negative findings and corrections can advance
  the investigation while lowering the annotation-support hypervolume. That
  decrease alone is not a scoring defect. Scientific yield should observe
  investigation progress; report annotation support separately. Do not silently
  replace the hypervolume formula or reinterpret a saved run's observations.
- The configured local yield estimator/controller owns continuation. No hidden
  stopping rules, turn caps, scientific acceptance gates or approval mechanisms.
- Global history shares only typed run statistics. Preserve original expectation
  snapshots; future learning must not rewrite completed observations or closed
  child credit. Distinguish queue wait, execution and total turnaround by what
  was actually measured. Unknown information stays unknown.
- Monitoring should expose useful job progress when observable, including
  relevant log/status information that lets the episode assess loading,
  throughput or a possible stall. Process liveness alone does not establish
  productive execution. Preserve measured facts and their provenance; the
  episode interprets them. See `docs/TIME_AWARE_ESTIMATION.md` for the current
  interface limits and the distinction from monitoring model-service calls.

## Communication, state and credit

- Parents define the information requested from children through forms with
  declared types and constrained meanings. JSON alone does not constrain prose.
  Restricted strings are allowed; unrestricted findings/instructions are not.
- Recorded facts come from actual records. Child interpretations use the
  parent's allowed values. Validate references and meaningful field relationships;
  do not add a separate model call to compose or restate recorded facts.
- Actual work, authoritative state, the responsible episode's received
  information and credit must describe the same contribution.
- Record actual outcomes before projecting credit. Distinguish inherited
  information from new contributions, and completed work from attempted work.
  Unchanged polling and repeated records do not manufacture progress.
- One completed own action supplies one local observation. Internal child work
  does not become multiple parent observations. Timer firing, statistical
  refresh and report construction add no synthetic observations.
- Preserve valid partial work and return specific structured failures that
  permit meaningful repair. Termination is not scientific completion.
- Archive closed histories to disk and release their live logging/controller
  state. Keep durable identities and the active information still needed.

## Applying the principles

Trace each changed behavior through ownership, selected action, durable state,
communication, credit and continuation. Read every affected consumer. A correct
local function or a passing test does not prove that this complete path follows
the design; tests can encode an implementation mistake.

These are implementation responsibilities, not additional runtime gates. Do not
introduce a scheduler, reviewer or approval step to enforce them. Report precisely
what was inspected, tested and actually run, and what remains unverified.

The execution-tool checkout is at `reference/episode_tools`. Its terminology
cleanup is separate from this episode build. Its agent roster, procedure,
interpreter and stopping behavior are not this workflow's episode structure.

The retrievable instruction library is described in `docs/TOOL_KNOWLEDGE.md`.
`docs/EPISODE_STRUCTURE.md` distinguishes the accepted target structure from
the implemented tree. Categories can aid discovery without mandatory episode
levels. Literature and bioinformatics findings can motivate each other; no
fixed order or one-way scientific relationship is prescribed.

## Aurora storage and charging

User direction on 2026-10-22:

- Keep this workflow's software, environments, databases, caches, inputs, logs
  and run directories under `/lus/flare/projects/BioReason-Aurora-Test`.
- Charge new Aurora PBS jobs to `EpiCalib` using `-A EpiCalib`. The charging
  account does not change the BioReason storage location.
- The only workflow file allowed in Aurora home is the small tracking file
  `/home/chian/WORKSPACE_DIRECTORY.md`. Never create run folders or put job
  output, temporary files, environments, data or caches in home. Set job output,
  working and temporary locations explicitly in project storage.
- The user does not request backup work. Preserve historical receipts as facts;
  the earlier test's charging account is not retroactively changed.

## Practical terminal endpoints (2026-10-22 addendum)

Read docs/PRACTICAL_EXECUTION.md and the original additive contract
docs/PRACTICAL_EXECUTION_CONTRACT_2026-10-22_001.md for the user's later practical
execution direction. Validated completion of the original practical assignment
sets future expected credit to exact zero immediately. Preserve the final
actual gain and earlier observations; use the ordinary controller comparison,
with no extra zero turn or model-composed completion. This specific exception
does not introduce a scientific acceptance gate. The older read-only episode
structure document remains a permanent historical record.


## Mandatory task/steering distinction (2026-10-23)

Read docs/TASK_AND_STEERING.md before constructing or changing any episode
message or model prompt. Every prompt has TWO separately built blocks:

- TASK is the detailed instructional information defining the work itself.
  Supply it in full on EVERY iteration, including the substantive selected
  problem-solving guidance, scope, constraints and requested result meanings.
  Do not shorten it into a role heading when making steering concise.
- STEERING is controlled, curt, dry information derived from prior iterations.
  Select only what affects the next decision; use concise factual tables of
  own action categories, total yield, expected next yield and uncertainty, with
  necessary specific attempts, results and qualifications. No narrative recap
  or wholesale stored-context dump.

These blocks have opposite verbosity and purpose. Apply the distinction within
episodes and across BOTH directions of EVERY parent/child boundary. JSON is an
internal intermediate for selecting and rendering meaningful TEXT and tables;
it is not the model-facing context message. Host IDs, hashes, revisions and
tracking stay outside the prompt. Preserve typed response/return contracts.
Each concrete template needs its own decision/information trace and the user's
running feedback before being treated as settled or coded.

## Bioinformatics tool graders (2026-10-24)

For the expanded tool-grader work, read
`docs/TOOL_GRADER_GOAL_AND_PRINCIPLES_2026-10-24_001.md` and the relevant rows in
`research/tool_grader_inventory_2026-10-24/WORK_STATUS.json` before designing or
coding a grader. Tool information, internal numerical scoring sheets, and
deterministic readers/calculators have separate responsibilities. Keep literature
graders and W05 annotation-credit aggregation separate. Preserve existing BLAST
work, verify actual child-owned result-path bindings, and distinguish a source
catalog entry from an installed, bound and tested operation. Upstream mock or
placeholder outputs are not scientific measurements. Preserve the permanent
direction record; update the fixed progress rows without dropping unfinished work.
