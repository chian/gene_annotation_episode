# A108 lost behaviour: HEAD (97308b94c) against the working tree

Scope: the 984 files at HEAD under `gene_annotation_episode/episodic_workflow/root/a108/`.
Excluded by the task: the top-level `published_evidence_assessment/` duplicate tree (201), `annotation_improvement/` (17),
`method_loop/` (3) and tests (45). That leaves 718 files judged. Per-row detail: `a108.tsv`.
Read-only work on 2026-11-18: `git show`/`git grep` on HEAD, `grep`/`diff` on the working tree. No test was run.

## Result

Six capabilities that an A108 episode was offered at HEAD no longer exist for it. Four are gone from the whole working
tree; two (the UniProt tools and image delivery) still have their support code but no path to the episode.
Seven more items are uncertain and need the owner's decision. Everything else is either present or an intended removal.

| Verdict | Files | Lines |
|---|---|---|
| lost_capability, whole files | 9 | 925 |
| lost_capability, part of a file that is otherwise present or intended | tools.py, providers.py, 3 `source_contracts.py`, 7 `decision_inputs.py` | – |
| uncertain | 10 whole files, plus part of the 7 literature `internal_summary.py` | 1,933 |
| present: placement target | 82 | 18,239 |
| present: shared or top-level copy | 27 | 6,275 |
| present: ported into the A108 literature binding/source/credit | 112 | 7,455 |
| present: ported into the A108 head | 3 | 155 |
| package markers and one empty index | 25 | 14 |
| intended removal: runner, runtime, registries, journals, receipts, receiving_context, waiting | 58 | 13,126 |
| intended removal: task/protocol layers (literature homes 68, head home 20, library helpers 16) | 104 | 9,366 |
| intended removal: `library/retained_input_authority` (receipts inheritance, duplicate of a101/a105/a106) | 281 | 47,323 |
| intended removal: per-axis model provider | 2 | 811 |
| intended removal: vendor | 5 | 2,894 |

## Lost capabilities

### 1. UniProt acquisition tools (`public.uniprot.search`, `public.uniprot.record`)

- **What it did.** Fetched a UniProt search page or record, retained it as a source, and projected it into reference and
  term records with partial-projection feedback and a bound `uniprot_publication`.
- **HEAD files.** `tools.py` lines 165-167, 502, 825, 838, 1033 and `_import_uniprot` (1074-1187);
  `_A108_ACQUISITION_TOOLS` in the `source_contracts.py` of the three acquiring literature homes.
- **Tests at HEAD.** `tests/test_private_source_scope.py`, 28/28 passed. It asserted that `public.uniprot.search` is in
  the catalog exactly for `literature`, `literature_strategy` and `literature_search`.
- **Offered at HEAD.** Yes, by those three literature bindings; the head could select the tools too.
- **How it was lost.** `tools.py` imported `gene_annotation_episode.api_uniprot`, which was deleted. rp108 still reported
  the missing import at 15:03 (`runs/rp108-chk5-1795035823`). By placement (17:40) the two tools and `_import_uniprot`
  were removed instead of the import being repointed. No record names this removal.
- **To bring back.** Restore the two catalog entries, the dispatch and `_import_uniprot` in
  `episode_support/tools/sample_context_evidence/tools.py`. Everything they call still exists:
  `episode_support/acquisition/sequence_and_context_sources/api_uniprot.py` (`parse_uniprot_snapshot`,
  `uniprot_page_metadata`), `episode_support/tools/sequence_and_context_sources/sample_context_evidence/uniprot_native.py`
  (`legacy_uniprot_records`), `episode_support/records/sequence_and_context_sources/sample_context_evidence/uniprot_publication.py`
  and `PublicClients.uniprot_search/uniprot_record`. Add both names to `ACQUISITION_TOOLS` in
  `root/a108/sample_context_evidence/published_evidence_assessment/literature_binding.py` (line 63). Seven other axis
  `tools.py` files still carry `_import_uniprot`, and the A110 literature binding still lists both tools.

### 2. Image evidence reaching the model (`image.view` pixels)

- **What it did.** After `image.view`, the selected image went into the next decision as `visual_evidence` and the
  provider attached the actual pixels to the model turn.
- **HEAD files.** `providers.py` lines 496-501 (resolver bound at `runtime.py` line 3761); `build_decision_inputs` in the
  literature `decision_inputs.py` (7 identical copies).
- **Tests at HEAD.** None in `a108/tests`.
- **Offered at HEAD.** Yes: `image.view` is in the access tools of all 7 literature bindings.
- **How it was lost.** The switch to one model provider (`runs/claude_ablate/model_provider_switch.md`: it has "no ...
  image resolver"), and the ported decision sources do not build `visual_evidence`.
- **State now.** `image.view` still returns `visual_inputs` and `ToolRegistry.resolve_image_input` still exists, but
  nothing delivers them. The instruction text still tells the model that `image.view` supplies pixels.
- **To bring back.** The shared `gene_annotation_episode/model_provider.py` must accept image inputs (this affects every
  axis with `image.view`, so it is not an A108-only change). `literature_source.LiteratureSource.decision_context` and the
  head's `runtime_source.py` then add `visual_evidence` from the last `image.view` outcome, resolved through
  `episode_support/findings/sample_context_evidence/image_evidence.py`.

### 3. Semantic tool retrieval (`process.tools`)

- **What it did.** One FAST-model call read the complete real tool map and returned the tools relevant to a stated child
  investigation; the result was saved once per operation and fed the child's tool selection.
- **HEAD files.** `scientific_tool_retrieval.py` (267), `library/scientific_catalog_operations.py` (29),
  `sample_context_evidence/library_operations.py` (14), `sample_context_evidence/library_services.py` (39).
- **Tests at HEAD.** None in `a108/tests` exercised the retriever.
- **Offered at HEAD.** Yes, to the head (`_COMMON_TOOLS`), when its binding was configured with `semantic_fast_v1`.
- **How it was lost.** rp108 reach prune (`runs/rp108-reach-1795035218/stdout.log`) and the head's second pass
  (`runs/claude_ablate/a108_needs.md`). The class is gone from every axis.
- **To bring back.** One shared `episode_support/tools/tool_retrieval.py` beside `tool_catalog.py` (which still has the
  `process.tools` catalog entry and the literal-test retrieval). The A108 head's `runtime_source.py` would offer it as a
  tool. It must record through `bound.recorder` instead of the `runtime_tool_retrievals` table, and drop the
  `provider.release` requirement. Owner decision first: the contract's `SubsetField` (C6) now lets the parent pick tools
  directly, which may be the intended replacement.

### 4. Parent/child information exchange (`shared.*`, five tools)

- **What it did.** A child told its parent which operand was missing and why; a parent or child offered evidence it had
  received; the receiver read it through the normal receipt boundary. Stored in two Store tables.
- **HEAD files.** `shared_information.py` (332), `shared_information_results.py` (78).
- **Tests at HEAD.** None real (one test stubbed it out).
- **Offered at HEAD.** Yes, to the head (`_COMMON_TOOLS`); participants were annotation, sample_context_evidence and
  improvement episodes.
- **How it was lost.** `shared_information.py` has no record; `shared_information_results.py` went in the rp108 reach prune.
- **To bring back.** A store in `episode_support/records/` and the tools offered by the head's `runtime_source.py`. It
  cannot return unchanged: it identified episodes through `EpisodeReturnRecords` and `runtime_episodes`, both deleted,
  and on the new runner a child runs to completion inside one unit, so a parent cannot answer a need while the child is
  still working. Owner decision needed.

### 5. Execution planning information (`process.execution`)

- **What it did.** For one selected tool/resource pair it returned the execution recipe, resource context, timing history
  for compatible profiles and open HPC commissions; `planning_context` added host capacity and cached queue state.
- **HEAD files.** `execution_planning.py` (64), `sample_context_evidence/execution_planning.py` (36).
- **Tests at HEAD.** None in `a108/tests`.
- **Offered at HEAD.** Yes, to the head when its tool library carried tool info.
- **How it was lost.** rp108 reach prune and the head's second pass. No definition of `host_capacity`,
  `planning_context` or the `process.execution` reader remains anywhere.
- **To bring back.** `episode_support/jobs/sample_context_evidence/execution_planning.py`, reading
  `episode_support/records/sample_context_evidence/execution_memory.py` and `episode_support/instructions/execution_guidance.py`
  (both present); offered by the head's `runtime_source.py`. The ported head commissions no jobs, so its use is limited to
  timing information for its own tools.

### 6. Examined-source inputs in the literature decision

- **What it did.** Collected, for the source being examined, every exact witness the episode had already located
  (source, representation, start, end, quote, context window) and every returned measurement selector, and showed them
  in each decision as `literature_examined_source_inputs`.
- **HEAD files.** `library/literature_source_inputs.py` (66); called from each literature home's `internal_summary.py`.
- **Tests at HEAD.** None in `a108/tests`.
- **Offered at HEAD.** Yes, by all 7 literature bindings.
- **How it was lost.** Deleted with the literature `internal_summary.py` in the port; no record. The ported decision
  context shows only the last page of own outcomes without their results, plus the last outcome.
- **To bring back.** `episode_support/literature/readers/sample_context_evidence/literature_source_inputs.py`, reading
  the episode's recorded outcomes (`LiteratureSource._state.outcomes`) instead of `runtime_actions`; offered by
  `LiteratureSource.decision_context`.

## Uncertain: needs the owner's decision

1. **Own-history lookup (`episode.history`)**, `decision_history.py` (636). It read the deleted journal. The instruction
   texts still tell the model to use it. The outcomes are now in the episode recorder with no tool to read them back.
2. **Completed-work and current-result presentation**, `episode_work_report.py`, `library/literature_work_report.py`,
   `library/literature_work_results.py`, `library/literature_current_results.py` (1,000 lines). The port passes current
   sheets and working state as records. The finding correction-link view and the completed-work account are not shown.
3. **Population task context**, part of the literature `internal_summary.py`, with `library/literature_task_families.py`.
   It selected the `A108_GRADING_TASK` / `A108_AGGREGATION_TASK` instructions. Those texts survive in
   `episode_support/literature/prompts/literature_prompt.py` but nothing reads them.
4. **Head instruction text**, `sample_context_evidence/goal.py`. The ported head sends the literature instructions
   instead. The original text survives for A103 and A106.
5. **Head assignment inputs**, `sample_context_evidence/scientific_contracts.py` and `from_parent.py`. The head no longer
   receives `proposed_annotation_ref`, `evidence_refs` or `constraints`. The root can hold all three; the A108 head does
   not declare them.
6. **Tool construction from configuration**, `tool_configuration.py` (33). Only the old runner called it, but nothing
   now builds `services['a108']['tools']` for `a108_home_factory`.
7. **`retained_input_authority`** (281 files). Judged an intended removal. 73 of its files have definitions that exist
   nowhere now; every one of those also lived at HEAD in a producer module of another scope (a102, a103, a104, a105,
   a107, a110, `root/library`), so whether they are lost is for those scopes to answer.

## Present, but no A108 binding offers it

- `knowledge.search`, `knowledge.entry`, `knowledge.read`: `episode_support/tools/tool_knowledge.py` and the knowledge
  files exist. The runner offered them at HEAD; the ported `ToolRegistry` lost its `knowledge_library_directory` argument.
- `process.search`, `process.entry`, `process.sources`: `SampleContextEvidenceLibrary.execute` exists in
  `episode_support/configuration/sample_context_evidence/process_options.py`. The head shows the axis entry and the chosen
  thought pattern but does not offer the library queries.

## Checked and not lost

- The literature homes: roles, children, role instructions, the acquisition/access split, page, table and window checks,
  required grading with its subscoring sheet, lead verification, screening, cell returns and task credit are all in
  `literature_binding.py`, `literature_source.py` and `literature_credit.py`. The only omission found is item 1.
- The functions rp108 cut from A108's placed copies (`runs/rp108-rm1` to `rm5`, 39 names) still exist in the shared
  top-level module or another axis copy, and their A108 callers were the runner, the old task layers or the deleted
  per-axis Store. Two names exist nowhere now: `ToolRegistry.retained_molecular_reference_access` (the guard the runner's
  resolver applied to retained molecular and Enrichr references; the privacy modules it called remain at top level) and
  `form_reference_validation.form_validation_value` (report-form check). Both served the removed receipt and
  report-form paths.
- `process.revise` is now the head's `episode_child` selection with `thought_pattern` and `tools`.
- The yield estimators are in `yield_control` under new names (`runs/claude_ablate/yield_control_switch.md`).

## Limits of this check

- Placed files were compared with their targets by definition, method and constant names and by line count, not line
  by line. `tools.py` was diffed in full.
- Prompt and instruction texts were not compared sentence by sentence beyond the items above.
- Deletions with no record: the UniProt tools, `shared_information.py`, `library/literature_source_inputs.py`,
  `decision_history.py`, `library/literature_work_report.py`.
