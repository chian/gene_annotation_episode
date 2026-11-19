# Axis wave A108 (sample_context_evidence): blockers and open points (19 November 2026)

No missing system operation blocked the A108 grading route. The leaf (`source_coverage_improvement`) ran to its
yield stop with the real model, and its parent (`source_evidence_examination`) ran with the real model and
commissioned it. The runner (`episode_runtime/`) was not edited.

## Found and fixed while running (episode or library, new paradigm)

1. `ToolRegistry(store, clients=PublicClients, job_limits=...)` cannot be built from `ctx.settings`: `clients` is an
   object of the outside world, not JSON settings, so every access tool of every A108 episode raised `TypeError` at
   its first real call (`ctx.settings.get('tool_registry', {})`). Each A108 episode now declares the service
   `public_clients` (`SERVICES = ('public_clients',)`) and builds the registry with
   `ToolRegistry(ctx.store, clients=ctx.services['public_clients'], **ctx.settings['tool_registry'])`; the setting
   `tool_registry` holds only JSON (`job_limits`, executables). The run's caller supplies
   `{'public_clients': lambda: PublicClients(...)}`. The same pattern exists in every other axis (not touched).
2. The A108 sheet repositories take `(store, read_cells=...)`; the episodes still passed a `run_id`
   (`LiteratureA108GradingRepository(store, run_id)`): `TypeError` at the first grading. Fixed in all eight episodes.
3. `passage_evidence_extraction`'s library context had no `assignment`, which `A108SheetRepository.populate` and
   `literature_sheet_updates` read: added (`{}`: the passage child is never asked for cells).
4. A parent's credit (`assessment_answers`) reads the observation of each assessment a child returned; a pass
   carries only the records it names (decision T5), so the first parent run ended with
   `CustodyError: record_not_held:...:observation_...`. The finding now carries `observation_refs` (the observations
   the returned assessments rest on).

## Model-provider failure seen in a real run (system, not edited)

`runs/ma108_6`: the parent commissioned `source_coverage_improvement`; the child read the paper, then its `reason`
answer degenerated into an endless string of hex digits until the provider stopped it. `ModelProvider.complete`
raised `ModelCallError("model_turn_failed: {'message': 'Incomplete response returned, reason: max_output_tokens',
...}")` (`gene_annotation_episode/model_provider.py`), which ended the whole run (25 min 52 s). An incomplete answer
never reaches the episode's `action`, so it cannot be rejected like any other invalid answer (`Rejected` and a new
decision). Suggested fix (system owner): return a truncated answer as a response that the episode's `action`
rejects (for example a response marked incomplete that `decode_response` refuses), so the decision is made again
with feedback; or document that a truncated answer ends the run.

## Open (not blockers of this route; reported, not worked around)

- The head's decision context shows `records.reasoning_view(scope)` (`working_state`), which lists every held
  record, including assessments its children returned with their `investigation_finding`. The received-fact
  displays of the literature episodes leave returned records out (receipt `how == 'returned'`); the head's
  reasoning view has no such filter in the system (`reasoning_view` takes no receipt filter). Wanted, if the owner
  wants the head strictly controlled: `RecordReader.reasoning_view(scope, limit, *, how=('entry', 'commissioned',
  'produced'))` or an equivalent filter in `episode_runtime/store_scope.py`.
- `ChildCall` arguments carry the parent model's `objective` text to the child as the `ChildMessage` objective. It is
  parent-to-child prose (outside the grading scope of this wave).
- The real parent model did not commission its child when the commissioner's message reached it only inside
  `literature_goal_plan`; it read and graded the source itself. `source_evidence_examination` now shows the
  commissioner's message at the top of its decision context (`commission_message`).
