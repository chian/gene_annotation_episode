# Import fix notes (19 November 2026)

Collection (`pytest --collect-only`) of root/a101..a110, `episode_support/` and `tests/` now has zero errors.

## Material implementation

Importers of the deleted `episode_support/records/documents/<axis>/{materials,materials_packing,material_gzip}` now
import the Store's single copy (`gene_annotation_episode.materials`, `.materials_packing`, `.material_gzip`):
the nine `tools/<axis>/tools.py` and `readers/partner_presence_evidence/received_inputs.py`.

A105/A106/A108 `materials_packing` private "received residue-byte reader" variants (read at `HEAD`, e.g.
`git show HEAD:.../records/documents/experimental_activity_evidence/materials_packing.py`): the tools only call
`packing.component_window`; the Store's copy has the same function with the same body. No behaviour lost. One
difference: the variants' `component_chunks` took `artifact_path` from the axis's `readers/<axis>/source_bytes`;
the Store's copy takes it from `gene_annotation_episode.materials`. The Store's copy still uses `store._db` and
`store.path` (not touched here).

## HPC ledger

The old `jobs/hpc/<axis>/hpc_ledger.py` (`HPCLedger`) importers are the `hpc_work_planning` task and
`hpc_allocation_execution` task of A102, A103 (planning), A104 (planning), A107 (execution), A110 (both). They import
`episode_support/jobs/hpc_ledger.HpcLedger`. Caller adaptations:

- `HPCLedger(directory, commission)` -> `HpcLedger.open(ctx.store, commission)`;
  `HPCLedger.open_existing(directory)` -> `HpcLedger.existing(ctx.store, arguments['ledger'])`.
  The ledger is found by its id, not a directory: `hpc_initialize` now returns `'ledger'` in its result, and every
  later tool (and the execution sister) reads `arguments['ledger']`. FOLLOW-UP: the tool schemas of the planning and
  execution tools do not yet declare a `ledger` argument, and the parent's `msg_to_child` must pass the ledger id.
- `ledger.once(identity, kind, calculate)` -> local `recorded(ledger, identity, kind, calculate)` in each task file
  (`put` of `calculate()` under the identity; the same evidence is the same row).
- `ledger.score(reference)` -> `ledger.score(reference, log_score=prediction.log_score, measured_value=measured_value,
  forecast_metric=forecast_metric)` (`measured_value` added to the `hpc_resource_prediction` import).
- `ledger.cached` / `save_action` were not used by these callers.
- `str(ledger.path)` in provenance -> `ledger.ledger`.
- A102 planning `ledger_directory` removed (no directory any more).

Not adapted (not an import failure; `ledger.path` has no replacement in the new ledger, so these raise
`AttributeError` when run): `launch_input_path(ledger, plan_id)` (`ledger.path.parent / 'launch-inputs'`) and
`closed_measurement(..., ledger_path=ledger.path)` in `export_closed`, in all of the six task files above. The
shared-history entry in `hpc_initialize` etc. is also unchanged.

## Other deleted names

- A105 `literature_assay_inputs.saved_text_witness_inputs` (read the old `repository.operations_table` /
  `store.db`; old-runner operation ledger): removed from the library. The five A105 tasks under
  `published_evidence_assessment/**/task.py` imported it in `materialize_text_arguments`; the import and the
  "saved operands" shortcut at the top of that function are deleted, so the ordinary
  `materialize_text_witness_inputs` path always runs.

## Collection errors not caused by a deleted module

None remained. The `--collect-only` run of `tests/` was already clean (0 errors) and the
`tests/test_bvbrc_proteome_host_integration.py` file was not run separately.
