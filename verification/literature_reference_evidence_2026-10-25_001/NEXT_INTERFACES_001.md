# Next source-aspect and presentation handoffs

Current goal: GOAL_VERBATIM.txt. Continue source reference evidence only; do not
implement alignment/structural transfer, phylogeny or combined annotation credit.

## Presentation interface and scientific meaning

`literature_experimental_prompt.py` owns:

- `is_literature_experimental_context(state)`: true only for a mapping with
  `literature_experimental_work.version == literature_experimental_task_v1`.
- `render_literature_experimental_prompt(state, instructions, *, lookup_results=())`:
  complete TEXT TASK and concise TEXT STEERING. The structured input is the same
  ordinary decision state/frame used by the existing provider; it remains saved
  unchanged. The renderer has no acquisition, arithmetic, model call, action,
  controller, persistence or source interpretation side effects.
- `EXPERIMENTAL_TASK`: detailed recurring scientific guidance. It addresses
  the actual source reference/experiment assignment, molecular activity claims,
  controls, comparability, attribution, units, uncertainty and missingness.
  It does not paste a sheet/calculator or infer a target transfer.

`literature_experimental_work` marker contains only:
`{version: literature_experimental_task_v1, aspect: source_rate_comparison}`.
Assignment, goal, scope, actual tool contracts and requested typed return remain
in their existing ordinary state fields. No fourth construction slot is added.

TASK selects the actual goal objective/task context; literature assignment and
source selectors; relevant supplied material/scoped access; role-specific
instructions and permitted child alternatives; actual tool invocation schemas;
requested form meanings. It repeats in full for every model call, including
lookup, delta reconstruction and provider restart.

STEERING selects the own action category/yield/expectation table and current
continuation uncertainty; last selected source result or numerical cells;
actionable feedback; requested child numerical returns; decision-relevant
pending work; explicitly requested lookup results. Source quotations are scoped
evidence, not permission to dump all state, source inventories or histories.
Host hashes, frame revisions, bookkeeping and parent/child private histories
are excluded. Unknown information is displayed as unknown, not zero.

## Ownership before parallel work

- Fresh renderer worker: only new literature_experimental_prompt.py and
  tests/test_literature_experimental_prompt.py. Pure rendering/fixtures only;
  no primary-paper packets, provider or runtime changes.
- Fresh native-presentation test worker: only
  tests/test_literature_experimental_prompt_delivery.py. Controlled transport
  tests using the real existing provider, no network/inference.
- Fresh source worker: only new primary_csid/ files below this verification
  directory. Read CsiD original primary source/needed supplement and mandated
  full post-paper authority reset; identify exact original numerical/source
  fields and scientifically justified components. No coding or old-record edits.
- Coordinator: provider/binding integration, actual source extraction adapter,
  shared interfaces and assembled verification. No competing provider/shared
  file edits by workers. Existing unrelated sessions/tool graders stay separate.

## Provider integration contract

The coordinator will extend only the existing `_SessionConnection._presentation`
state-frame handling to recognize this marker alongside published scientific
contexts. Same bootstrap/update/lookup reconstruction and exact output schema;
full detailed task supplied each call. No extra model composer or conversation.
The enabled LiteratureEpisodes binding supplies the marker and aspect guidance
through its ordinary instructions/context ports. Parent prompts remain theirs;
admitted typed source cells remain factual steering, not child task/history.

Source-native extraction details will be defined from inspected primary source
fields before its coding workload. Do not assume an original source has the
normalized CSV/TSV fields used by the first implementation increment.
