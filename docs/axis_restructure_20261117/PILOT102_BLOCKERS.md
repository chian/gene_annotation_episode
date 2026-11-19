# Pilot 102: what stops or limits the A102 literature structure grading route (19 November 2026)

Scope: the seven literature episodes under `root/a102/structural_homology_evidence/published_evidence_assessment/`
and the A102 head's summary rule. What was built is in `LOST_CONTENT_a102.md` rows 1 to 13 and
`INVESTIGATION_FINDING_FEATURES_a102.md` section 2.13.

## 1. Missing system operation: run an Episode to its first decision, or one tool unit, without a model call

The leaf tests (`source_coverage_improvement/tests/test_structure_grading.py`) link the real run and then have to
reach into runner and loop internals, because `EpisodeRun` offers only `run()`, whose next step after the first
`decide` is the model call:

```python
linked = link(registry, path, entry, run_id=..., journal=..., collaborators=...)
episode, ctx = linked.episode, linked.context
scope = ctx.enter(episode.grain, episode.key)                 # builds the yield controller
bound = episode.source._bound
view = episode._view(ctx, scope, records)
bound.position.begin(position)
request = task.decide(summary, None, bound.decision_context(position))
item = episode.source._unit(view, position, ToolCall('structure_populate', arguments), None)
await episode._acquire_unit_async(ctx, scope, records, item)
```

Wanted: `EpisodeRun.next_decision()` (enter, build the controller, return the summary and what `decide` returned)
and `EpisodeRun.run_unit(ToolCall(...))` (one journaled tool unit with its controller step), both in
`episode_runtime/`, which this pilot may not edit.

## 2. The model call

No test asks the model. The step after the first decision is `RecordedModel.complete` through the run's
`ModelProvider` (`codex app-server`), which needs credentials that the test HOME does not have. A `-m model_run`
test of the leaf (the model selecting `structure_populate` with a real deposited structure) is not written.

## 3. Library imports that were broken before the pilot (repointed, not carried)

`episode_support/tools/structural_homology_evidence/tools.py` imported
`records.documents.structural_homology_evidence.materials_packing` and `...materials.source_window(_selection)`,
which were deleted (store-access.md: the nine copies become the Store's one copy). The leaf could not be imported.
The imports now name `gene_annotation_episode.materials_packing` and `gene_annotation_episode.materials`. Those
functions take a `store` argument; whether they work on `ctx.store` (custody) is not exercised by the pilot tests
(no access tool runs in them). This belongs to the stage-2 carry-over of `tools/`.

## 4. Head tests that fail for a reason outside this route

`root/a102/structural_homology_evidence/tests/test_episode_binding.py`: 3 failures (`[hpc]` slot and
`test_a_wrong_commission_fails_with_its_own_error`), all from
`hpc_work_planning/task.py` importing `episode_support.jobs.hpc.structural_homology_evidence.hpc_ledger.HPCLedger`,
which does not exist (the HPC ledger is a stage-1 job service, `LAUNCH_MONITOR_EXTRACT_MECHANICS.md` "Not provided
yet").

## 5. Return fields still carrying model text (not changed by the pilot)

The selectable `literature_source_lead_dispositions` of every literature episode still returns the validated lead
records, which hold model text (`relevance_rationale`, witness quotations). The feature table (section 4.1) wants
`relevant_lead_count` and `lead_source_refs` (and `examined_span_count`, `commissioned_spans_covered` for
`literature_screening_answers`). Changing them changes each parent's `credit.py`, which merges the children's lead
contents into `verified_source_leads`; left for the credit pass.

## 6. Reduced, by design of the A102 policy

`literature_sheet_updates.py` (A102 copy at `97308b94c`) registered each sheet's dependencies and reran dependent
calculations when an input sheet changed. A102's policy was `None` and the structure arguments name no input
sheet (`sheet_ref`), so a sheet's family is its provider and arguments and nothing depends on it. What remains is
the work table `CURRENT` (latest sheet per family) plus the experiment-assessment revision rule
(`revises_sheet_ref` must name the current head; it supersedes it). No rerun machinery was carried.
