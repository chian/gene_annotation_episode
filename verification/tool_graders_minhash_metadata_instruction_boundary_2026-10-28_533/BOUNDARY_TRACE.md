# MinHash instruction and provider boundary trace — 2026-10-28 / 533

Read-only source inspection and draft preparation. Only this new verification
directory is owned by this workload. No production code, tests, prompts,
published manuals, numerical outputs, progress rows or goal files were changed.
No application/scientific imports, tests, native programs, model calls or
network requests were run. This is not an overall-completion claim.

Authority read in full: the user-entered attachment
`/home/chia/.codex/attachments/6960b4a1-b2e0-46d4-8003-fcb7685a2232/pasted-text-1.txt`.
Also read: `AGENTS.md`, `docs/TASK_AND_STEERING.md`, `docs/TOOL_KNOWLEDGE.md`,
`docs/EPISODE_STRUCTURE.md`, `docs/TIME_AWARE_ESTIMATION.md`, and accepted 517
`CONTRACT.md` plus `ROOT_INTERFACE_CLARIFICATION_001.md`. The original goal and
ten principles were reread during source examination; final reset is recorded
in the handoff. No `GOAL.md` was read.

## Exact demonstrated gaps and reused implementations

1. `api_bvbrc_minhash.py:124`, `result_capabilities()`, still says distance and
   p-value recomputation “remains unavailable here”.
2. `knowledge/bvbrc-minhash.md:19` limits results to selector `{}`; its following
   paragraphs say that the production path lacks pair inputs and describe only
   matches/counts. `knowledge/index.json:68` does not expose the new choices in
   discovery text.
3. `ExecutionEpisodes.instructions()` at `execution_episodes.py:1111` describes
   all results as acquisition. Saved-sheet calculation already exists, and
   should be described accurately. Draft D changes only that generic wording.
4. The actual `ModelConnection` execution-child presentation path does not yet
   build recurring text TASK plus curt STEERING for the MinHash launch/API/results
   roles. Source proof is below. An updated manual alone cannot close this gap.
5. Published scientific parents do use text TASK/STEERING, but their child-return
   renderer has no MinHash-specific selection of requested scientific values.
   `_steering()` flattens admitted child reports through `_values()` after the
   unrelated alignment presentation adapter. A clean illustrative value table
   is a proposed display, not evidence that such a renderer is already wired.

Reused numerical authority: `bvbrc_minhash_sheet_v1`,
`parse_minhash_result`, `calculate_minhash_components`, and
`calculate_minhash_shared_hash_fraction` in `bvbrc_minhash_grader.py`.
The same sheet/calculator serves both native modes and saved recalculation.
The complete current contracts, service, views and host were read. Their typed
selector, scalar-evidence custody, publication and requested-return interfaces
are already implemented and are not redesigned here. The host includes root's
new `validate_commission_inputs`; no independent replay repair is proposed.

The saved calculator's internal validation may call the existing pure native
parser, as clarified in 517. It does not rerun native analysis or reacquire
anything. Ordinary saved-publication read/replay copies frozen results and
does not run the full calculator. Do not introduce a parser-disabled requirement
for a newly selected saved-sheet recalculation.

## Actual information construction and insertion paths

### Scientific parent discovery and selected scientific child

`BVBRCMinhashService.capabilities/result_capabilities` declare real operations.
`APIServiceExecution.operation_contracts` supplies them for configured API
resources. `ExecutionEpisodes.resource_tool_contracts` associates each with its
actual launch/API or results commission route. `resource_tool_information` checks
those declarations rather than inventing a deployment.

`scientific_tool_library._tool_information` combines declared profiles. For a
profile lacking explicit `instructions`, `tool_information.make_tool_info`
constructs exactly name, description, resources and instructions. `_documents`
matches all three MinHash names to `knowledge/index.json` and reads the single
`bvbrc-minhash.md` section. The complete instructions include the operation
description, existing generic API resource instructions, original input-schema
guidance and that manual body. No MinHash entry is in the packaged
`launch_instruction_library/index.json`; the HMMER-specific `launch-api` entry
must not be represented as MinHash guidance.

`ScientificToolLibrary.freeze` freezes that information for a run.
`parent_tool_info` / `tool_information.parent_view` expose only name,
description and resources to the selecting parent. `resolve_tool_info` fills
the selected child's full instructions from that original frozen entry.
`ScientificProcessEpisodes._assignment(materialize=True)` retains the resolved
`child_tool_info`; `decision_context()` supplies it alongside the existing
`evidence_axis`, `thought_pattern`, job, constraints and requested return.
`scientific_process_prompt._task` at lines 157–233 renders:

- detailed assigned work, fixed scope, constraints and selected supplied context;
- the full investigation and thought-pattern guidance;
- `Selected tool: <name> (api)` with description and full instructions;
- any explicitly pinned software/resource sections, actual operations and
  operand schemas, permitted children, requested form and recorded-fact meanings.

All three scientific slots survive. There is no new LibraryEpisode, grading
episode, model scientific grader, hand-designed complete MinHash episode or
controller layer. Drafts A–C change information content, not these mechanisms.
Existing snapshots remain original; changes would apply to later frozen runs.

### Resource children and ordinary manual retrieval

`ExecutionEpisodes.catalog` sends `launch_api` to `APIServiceExecution.catalog`.
Its selected service is `bvbrc_minhash`; the RFAM-only branch does not apply.
`launch_catalog` keeps only the assigned genome or FASTA operation. For results,
the handoff identifies the same configured service and `result_catalog` validates
the fixed selector before returning the result capability.

`Workflow.catalog` (`runtime.py:3091`) adds `knowledge_entry_ids` from the frozen
knowledge library and the ordinary `knowledge.*` operations. Thus the resource
child can explicitly retrieve the MinHash manual. Catalog entries do not
automatically inline that body. `launch.instructions.*` is a distinct library:
`DecisionSource.call` at 972–978 materializes only explicitly selected sections
from it into `selected_launch_instructions`. It does not manufacture a MinHash
section from the knowledge library or pass the scientific parent's private
history or full `child_tool_info` into a resource child.

This distinction must survive implementation. A manual edit establishes
retrievable tool information, not automatic recurring instruction delivery to
all receiving resource decisions. The common text renderer must expose the
current actual capability descriptions, assigned inputs and explicitly supplied
or selected frozen instructions; any further instruction binding needs an
explicit original frozen input, not a read of a mutable current file at render
time. No new mandatory manual-read action is proposed.

## Complete provider call path and dispatch conditions

The following proof is source inspection, not a live-model execution:

1. `DecisionSource.next` (`runtime.py:1394`) builds the decision context from
   the actual goal, scope, working state, current own outcome, requested form,
   actual tools, controller state and admitted child reports. At 1492–1494 it
   adds the specialist's `decision_context`.
2. `Workflow.specialist` at 2209 selects the role's registered binding.
   `ExecutionEpisodes` owns `launch`, `launch_api`, `launch_local`, `launch_hpc`
   and `results`, and declares `replaces_default_instructions = True` at 95.
   Therefore its launch/API/results guidance replaces the unrelated default
   scientific runtime instructions; it is not appended to that scientific TASK.
3. `ExecutionEpisodes.instructions` has specialized results wording only for
   the two RNA paths. MinHash selectors are `{}` or
   `bvbrc_minhash_result_selector_v2`, so those branches do not match. Local/HPC
   delegate branches do not match the MinHash API route. `launch_api` receives
   the generic API paragraph naming `bvbrc_minhash`; `results` receives the
   generic results paragraph; `launch` receives the generic launch paragraph.
4. `ExecutionEpisodes.decision_context` supplies the fixed `execution_assignment`
   and actual execution progress. Results use the original target plus
   `ExecutionTargets.describe_target` / `_describe_api`. The MinHash branch at
   `execution_progress.py:761` already supplies the chosen selector, explicit
   pair inputs, requested fact families and unestablished equivalence. Saved
   mode names the authenticated saved sheet and removes independent native
   extraction descriptions. API launch also receives
   `APIServiceExecution.decision_context` at 1002: original request and latest
   recorded API facts. None supplies a scientific or RNA TASK marker.
5. `DecisionSource.call` adds explicit selected manuals, initial binding
   information, child-option information and applicable actual timing/pending
   facts. `EpisodeBindings.initial_decision_context` gathers declared fields.
   Execution's RNA receiving markers are supplied only for annotation or
   scientific-process roles. Literature's initial marker is restricted to its
   configured annotation root; its contract-information profile is limited to
   literature roles or that root. Practical initial information is resource
   information, not a text-TASK marker. These dispatches do not convert a
   MinHash execution child to one of the text-rendered roles.
6. Direct protocol: `call` applies `instructional_model_context` and dispatches
   unchanged instructions/context at `runtime.py:1087`. That projection removes
   irrelevant evidence-axis sheet material; it does not construct TASK/STEERING.
7. Decision-exchange protocol: `exchange_decision` at 1260 freezes the original
   instructions and `model_snapshot(context, yield_table)`. The snapshot replaces
   raw own histories with action-category facts; `state_frame` makes a bootstrap
   or top-level delta. Lookup continuations receive a lookup frame. Original
   saved inputs survive reconstruction. Dispatch at 1337 passes those fields
   and instructions to the same provider. A frozen contract-information profile
   preserves the same instructions plus exchange guidance; it adds no renderer.
8. `ModelConnection.complete` forwards to its `_SessionConnection.complete`.
   The latter calls `_presentation` at `providers.py:228` before model dispatch.
   All six `has_text_task` alternatives at 317–323 are checked:

| Predicate | Required input | MinHash execution child |
| --- | --- | --- |
| Published scientific | `scientific_process.evidence_axis.instruction_status` equals published marker | Absent |
| Experimental literature | `literature_experimental_work.version` equals its marker | Absent |
| RNA comparison results | Results selector equals RNA-comparison selector version | Different selector |
| Original RNA results | Selector equals an original RNA selector version | Different selector |
| Original RNA receiver | Explicit `received_rna_structure_values` list | Not supplied to execution roles |
| RNA comparison receiver | Explicit `received_rna_comparison_values` list | Not supplied to execution roles |

9. Consequently no text presentation state is created for a MinHash execution
   bootstrap or direct context. Subsequent update/lookup frames have no prior
   text state. The fallback at 376–379 returns
   `json.dumps(presented, allow_nan=False), instructions`. For a frame,
   `presented` is the entire frame; for direct context, only the unrelated
   Infernal receiver projection precedes serialization.
10. `_SessionConnection.complete` makes
    `turn_input = [{"type": "text", "text": model_text}]` at 230 and passes it
    directly to `turn/start` at 251–254 with the original output schema. It
    passes `model_instructions` to `_session`; `thread/start` uses those as
    `developerInstructions` at 193. There is no later MinHash/role/service
    renderer. The recorded provider `request.json.input` would be the exact
    inspectable boundary for future verification, but none was executed here.

Established implication: the generic role instructions exist, but their assigned
objects and later facts remain JSON model text. On a delta or lookup, the full
assignment/instructions are not rebuilt as a recurring text TASK. Revising only
the manual or result description does not resolve that specific R2 message gap.

## Concrete decision/information trace at each receiving boundary

| Actual boundary and current rendered location | Owning decision and information needed | Required change / sufficient current content |
| --- | --- | --- |
| Tool retrieval → selecting scientific parent: `parent_tool_info`, `process.tools` lookup; published scientific `_lookup` / `_values` | Choose whether MinHash acquisition or retained-data calculation can answer the molecular comparison; select actual name/resource and the result families needed. Needs the available native/saved choices and limitations before commission. | Draft A exposes choices; C supports discovery. Full scalar-evidence detail stays in selected instructions. No parent histories sent to children. |
| Parent → constructed scientific child: `_assignment(materialize=True)` → `_task`, `Selected tool: … (api)` | Child chooses its next useful investigation action within original focus, thought pattern, scope and selected tools. Needs the complete operation instructions and metadata limitations while planning a results commission. | Draft B replaces obsolete claims. Existing detailed scientific TASK and all three slots remain unchanged. |
| Scientific parent → launch: `execution_assignment` plus `ExecutionEpisodes.instructions` launch paragraph; currently provider JSON fallback | Launch chooses among the parent-permitted concrete requests/resources, retaining exact native request and parent constraints. Needs actual allowed request alternatives, resource instructions, meaningful timing information and requested handoff. Does not choose or manufacture pair metadata. | Existing launch capability descriptions and full generic launch instructions suffice. Common text construction is missing; no new MinHash launch TASK wording is needed. |
| Launch → API resource child: generic API paragraph plus `api_request`, `api_service`, actual operation catalog; currently fallback | Execute the fixed genome or Workspace-FASTA request, then use actual outcome to decide useful available actions. Needs all eight unchanged operands, original resource, uncertainty meaning and requested completed-response handoff. | Existing launch descriptions and first two manual paragraphs suffice. Text-render the original inputs and full generic API TASK; no service job, polling sequence or new monitoring instructions. |
| API child → launch → scientific parent: actual handoff fact sources/admitted return, then own receiver context | Decide whether an original response is available and whether to request results or other permitted work. Needs only requested request-outcome/handoff facts; no match/calculation facts yet. | Preserve current typed meanings. Proposed common STEERING should render only admitted requested facts; never treat response availability as scientific equivalence or data already read. |
| Scientific parent → results with legacy `{}` or V2 native mode: fixed results assignment, target description, result capability; currently fallback | Execute the assigned result extraction/calculation. Parent chooses original handoff, metadata occurrences/evidence and requested families; child uses that fixed selection. Needs native-vs-derived meaning, joint row identity and availability rules. | Drafts A/B, generic D, and native/legacy section E. The selector and host validation are already present; do not add a ninth native operand or implicit metadata acquisition. |
| Scientific parent → results with saved mode: same renderer location, saved-result descriptor | Recalculate from the explicitly received original sheet using only newly selected retained inputs. Needs same-request/response association, original sheet preservation, and calculation-vs-acquisition distinction. | Drafts A/B, D and saved section E. No original fit/search repeat, no fresh result credit or change to earlier history. |
| Results → immediate scientific parent, and that parent → annotation receiver: `BVBRCMinhashHost.facts/received_context/received_facts`, typed admission, scientific `_steering` `Admitted child returns` | Interpret only requested native measurements, derived components or diagnostics in the molecular investigation; decide follow-up independently. Needs requested numerical values, paired row identity and material limitations. | Example F is proposed display. Pure display must consume admitted fields and saved values; no source expansion, recalculation, extra model composition or confidence score. Each onward parent receives only its requested admitted families. |
| Own next decision, lookup continuation and restart: `model_snapshot`/`state_frame` → `_presentation` | Use this episode's actual own category yields, current facts and actionable failure to choose the next action. Needs full TASK every call and terse STEERING; a lookup is not another turn. | The missing common execution text renderer must rebuild the full original TASK and select current facts after host reconstruction, hiding frame hashes/revisions. Preserve response schemas and saved observations. |

## Smallest common rendering port to review next

The shared insertion point is `_SessionConnection._presentation`, after
authoritative frame reconstruction and before `turn/start`. A pure common
execution text renderer can consume the existing complete `execution_assignment`,
goal, scope, exact generic role instructions, selected frozen instructions,
actual catalog, requested return schema, current own yields and received facts.
This is a presentation function for the existing execution roles, not a new
episode or workflow. Existing `apply_state_frame`, `text_instructions`, schema
and table mechanics can be reused; the scientific `_task` cannot be used as-is
because it requires a scientific process and its A/P/tool construction slots.

Proposed port, for later coding ownership only:

`render_execution_prompt(state, instructions, *, lookup_results=()) -> str`

The dispatch condition must identify original execution assignments/roles and
avoid taking ownership of existing RNA-specific templates. `launch` uses
`execution_launch_assignment_v1`; API uses `api_service_assignment_v1`; results
uses `execution_results_assignment_v1` with the actual API target. Selection of
the renderer must be stable on bootstrap, updates, lookup continuations and
restoration. No source/store/metadata/parser/calculator call belongs here.

Do not simply pass the complete raw context through `_values`. The concrete
text selections for MinHash are:

| Block | Selected text/facts |
| --- | --- |
| TASK — launch | Full existing generic launch instructions; original assignment objective, scope/constraints; every permitted request alternative and explicit resource constraint; selected software/resource guidance; available child kinds and requested handoff meanings. |
| TASK — API | Full existing generic API instructions; assigned MinHash mode and all eight unchanged operand values in a factual table; selected configured API resource; exact available operation description/instructions and empty action arguments; requested handoff meanings. |
| TASK — results | Full corrected generic results instructions D; original request and fixed result selection; section E for the actual selection; complete supplied pair-input/evidence meanings from B; requested return families and closed meanings. |
| STEERING — all three | Own action category/completed count/total signed yield/expected next yield/uncertainty; current outcome or actionable failure; only relevant pending work and measured timing facts. No parent yields or private histories. |
| STEERING — API/launch return | Requested completed-response availability or unknown issued-call outcome, resource/request qualification and admitted handoff. No numerical match expansion. |
| STEERING — results/scientific return | Only admitted requested calculation/match/count/diagnostic fields. Show parse status separately from null calculation cells and unestablished parameter equivalence. Example F is the proposed display, not an implemented renderer. |

The generic TASK remains detailed and recurring. The MinHash manual supplies
tool information; it does not replace that TASK. No new monitor prompt is needed:
MinHash supplies an immediate response and no remote job handle. Generic
resource-monitor guidance and actual deterministic status extraction remain the
monitoring boundary. An issued-call uncertainty is not permission to fabricate a
job or start polling.

## Proposed coding ownership after the wording receives feedback

This workload has no production ownership. Suggested narrow follow-on ownership:

| Change | Exact files/functions | Focused verification |
| --- | --- | --- |
| Tool information only | `api_bvbrc_minhash.py::BVBRCMinhashService.result_capabilities`; `knowledge/bvbrc-minhash.md`; MinHash summary in `knowledge/index.json` | Check descriptions/empty action schema, new frozen four-field information, discovery, and old frozen snapshot preservation; both native modes and legacy `{}` remain unchanged. |
| Common execution text boundary | New pure `execution_prompt.py::render_execution_prompt`; `providers.py::_SessionConnection._presentation`; minimal generic results wording in `execution_episodes.py::instructions` | Source-derived contexts for launch/API/legacy/native/saved selection, bootstrap/update/lookup/reconstruction, exact final `turn/start` text and unchanged output schemas. No provider/network/native execution needed for renderer tests. |
| MinHash requested-value presentation | New pure `bvbrc_minhash_presentation.py::select_minhash_presentation` and `render_minhash_return`; consumers `scientific_process_prompt.py::render_episode_steering` and the proposed `execution_prompt.py::render_execution_prompt`, using `minhash_fact_sources` meanings and admitted values | Counts-only/source-only have no additional numbers; duplicate rows retain indices; native and calculated values stay separate; null/mismatch/ambiguity paths display only requested diagnostics; no hashes/IDs/history dump. |

The last two rows need their own exact received-template feedback before coding.
They are identified because of the concrete source trace; they do not authorize
a rewrite of all other result families or existing numerical/custody paths.
`tool_information.py`, `scientific_tool_library.py`, contracts, views, host,
calculator, scoring, credit and controller need no numerical or ownership edit
for A–C. If actual resource-child instruction delivery is added beyond the
currently retrievable manual, freeze and bind it through the existing information
path and separately verify that exact boundary; do not quietly read current
manual bytes inside the renderer or copy a new manual into a per-tool TASK.

Suggested focused verification-file ownership, if those respective changes are
accepted: new `tests/test_bvbrc_minhash_tool_information.py`,
`tests/test_execution_prompt_minhash.py`, and
`tests/test_bvbrc_minhash_presentation.py`. These are proposed paths, not files
created or tests run here. They test meaningful receiving boundaries and frozen
instructions, not another numerical implementation.

Additional focused cases for accepted wording:

1. Parent description makes metadata/saved calculation discoverable without
   pretending any source/parameter was acquired. Selected child receives full
   original four-field tool information and unchanged evidence/thought slots.
2. Genome and FASTA modes retain original request operands. Explicit metadata
   is only a results-selector input. API/results action arguments remain `{}`.
3. With retained k=1, lengths 2/2, alphabet 2 and counts 2/3, displayed values
   equal saved components: distance 0.22314355131420976; p-value
   0.2592592592592592. Native reported 0.223144/0.259259 stay separate.
4. Saved k=2 selection displays the saved new distance 0.11157177565710488 and
   p-value 0.10400000000000001 without claiming a new search or overwriting the
   original publication. These are accepted expected examples, not new runs.
5. k-only input has a distance and null p-value; no inputs leave recalculations
   null; zero union preserves valid native fields and null derived fields.
   Row parse status does not stand for calculation success.
6. A source/field failure remains actionable structured feedback. Mismatched
   row identity and duplicate candidates remain calculator diagnostics. The
   prompt does not silently repair, acquire, default or merge metadata.
7. Metadata evidence is explicit source/artifact/RFC6901-field selection.
   Current genome lengths and upstream defaults never produce established
   remote equivalence. No LLM grader or new function-confidence score appears.
8. A reconstructed completed result displays frozen requested facts without
   parser/full-calculator/metadata extraction/provider calls. Root's replay
   verification 531 remains its own workload and evidence.
9. Prompt text contains full TASK at every actual model call and only own
   factual STEERING, preserving original raw credit, forecast and observation
   records. Rendering/report construction creates no action or observation.

Unverified here: all future edits/tests, final model-visible text execution,
live MinHash service behavior and remote sketch-parameter equivalence. Existing
metadata/custody/replay implementation is reused, not certified by this read-only
packet. Root must report its separate actual verification results.
