# Fixture locations

Evidence-specific inputs and reusable fixture helpers live in each evidence axis’s `tests/fixtures/` or `tests/support/` directory. A fixture needed by multiple axes has independent local copies. Root receiving/composition tests keep their own copies here. Fixtures for standalone tools without a current evidence-axis binding also live here, rather than being assigned to an unrelated axis.

`fixture_locations.json` records original and current locations; tests use their direct local paths. It is an inventory, not a shared fixture loader. Required research inputs are copied beside their consuming tests while their research originals remain intact. Historical source snapshots, provenance labels and retained evidence payloads are preserved. Active fixture-helper imports and file-relative paths are updated for relocation.

The old top-level `tests/fixtures`, `tests/retained_workflow_fixtures` and `tests/support` directories are retired by this move. The canonical workflow directory is `gene_annotation_episode/episodic_workflow/`. No test workflow was run for this relocation.
