# BRANCH_RUNS_localtool (19 November 2026)

Chosen episode: the A101 head `sequence_homology_evidence` (never had a real-model run; its own tool set offers local
tools of the library `ToolRegistry`: `sequence.align` = Biopython pairwise on two held sequences, `sequence.inspect`).
Not chosen: the A104 head (its `sequence.align` is refused by `validate_tool_name`, and its phylogeny tools need a native
phylogeny that enters custody only through the HPC import) and the A103 head (already has real-model runs).

World (written by me, a fixture): `root/a101/sequence_homology_evidence/tests/a101_world.py`. A caller FASTA with two
proteins (target; reference differing at one residue) -> `Store.create_problem`; the reference is held in
`evidence_refs`, the target in `scope`/`scope_refs`; a proposed hypothesis; frozen option library (publication
2026-10-24-001) and a frozen tool library of the offered local tools; `bounded_quality` yield binding with cutoff 0.001
for `A101:a101_native_sequence_correspondence`; `constraints.instruction` asks to measure the similarity of target and
reference. Test: `.../a101/sequence_homology_evidence/tests/test_branch_localtool_model_run.py` (two `model_run` tests and
one offline test).

## Offline check (no model): invalid call enters the iterator: PASS
Run dir `runs/br_localtool_3`. `EpisodeRun.run_unit(ToolCall('execute_selected_tool', sequence.align ...))`:
- a held record that is not a sequence (the hypothesis as `query_ref`): unit outcome `status: invalid`, feedback
  `sequence_operand_required` (ContractError), as an iterator unit.
- a record the episode does not hold (`reference_ref` = unheld id): unit outcome `status: failed`, feedback
  `adapter_execution_failed`, `exception_type: CustodyError`, `message: record_not_held:...`. It is a returned unit
  (journaled, enters the iterator), but as `failed`, not `invalid` (`task.py:execute_selected_tool` re-raises
  CustodyError; the runner adapter converts it into a failed outcome). Consistent with "a wrong commission fails", noted only.

## Branch 1: `sequence.align` is the only tool, instruction "measure the similarity": FAIL
Run `runs/brm_localtool_1`, log `runs/brm_localtool_1.log`. No unit, no model answer: the very first model call is rejected
by the provider (HTTP 400) because the episode's own decision schema is invalid. Credit, ended_by, resume: not reached.

Error: `gene_annotation_episode/model_provider.py:451 structured_turn` ->
`ModelCallError: Invalid schema for response_format 'codex_output_schema': At schema path
/properties/selection/anyOf/6/properties/selection/anyOf/0, array schema must define items`.
anyOf index 6 = options `[reason, process.revise, sequence.align, 4 children ...]` -> the 4th child option,
`published_evidence_assessment`.

Classification: EPISODE (A101 head `task.py`).
Diagnosis: `task.py:selectable_schema` (lines 217-222) returns `{'type': 'array', 'maxItems': 0}` when a slot has no
selectable fields; `SELECTABLE['published_evidence_assessment']` (task.py ~131) is the empty list. The model API requires
`items` on every array schema, so the head's decision schema (`selection_schema`, line 225) is rejected for every
commission, with any tool set. Every A101 head real run fails at its first decision.
Smallest suspected fix: `task.py:221` return `{'type': 'array', 'maxItems': 0, 'items': {'type': 'string'}}` (or
omit the `selection` property from the option of a slot with nothing selectable).

## Branch 2: `sequence.align` and `sequence.inspect`, the model must pick: FAIL (same cause)
Run `runs/brm_localtool_2`, log `runs/brm_localtool_2.log`. Same error at schema path
`.../anyOf/7/properties/selection/anyOf/0` (index 7 = same child option, one tool later). No unit, no model decision.
Classification EPISODE, same fix as branch 1. Model tool choice, repeated calls, credit, return admission and resume were
not observed; the tests are ready to rerun unchanged after the fix (they assert: sequence.align completed with
record_refs, `ended_by == yield_stop`, the return admits under `RETURN_FORM`, resume gives the same result with no new
model call). Expected to see: credit 0 from a pairwise alignment (the A101 credit reads only BLAST/HMMER gradings), so
the 0.001 cutoff stops the head after the first unit that earns nothing.
