# Workload G handoff

The bounded pure-provider workload is complete in its three owned staged files:

- `staging/gene_annotation_episode/bvbrc_gene_tree_inputs.py`
- `staging/gene_annotation_episode/bvbrc_gene_tree_grader.py`
- `staging/tests/test_bvbrc_gene_tree_provider.py`

`extract_gene_tree_sheet` has the exact six keyword-only inputs: documents,
inputs, observed_run, joins, assembly, parameters. It calls the real shared
extractor, adds the fixed GeneTree header and deterministic locus table, and
preserves the complete associated scientific data. `validate_gene_tree_sheet`
checks the actual shared shape and the full locus relationships.
`calculate_gene_tree(sheet, parameters)` validates the saved sheet, dispatches
the exact seven common parameter fields to the real shared calculator, and
retains the complete original calculation parameter object.

The final actual shared-plus-GeneTree run passed **102 tests** (50 GeneTree
cases). `TEST_RUN_007.txt` is captured stdout. It used
`/home/chia/repos/gene_annotation_episode/.venv/bin/python`, the real staging
cwd and staging `PYTHONPATH`. Tests assert the origins of provider, shared,
format, calculator and calculation-contract modules. No substitute shared
implementation was used.

`EXPORT_RUN_002.txt` records **8 complete examples** and equal JSON saved-sheet
replay with file/network/process I/O disabled. `examples_002/` is the final
export: ordinary and concatenated matrices, original J-to-X digests, null
alignment with valid tree, both native XML examples, raw-tree-required XML,
and malformed independent alignment with preserved tree. An invalid complete
locus-membership fixture is saved separately. Raw bytes, artifact associations,
control/code hashes, full sheets/parameters/components and metric summaries
are retained. `examples_001/` remains the earlier historical export.

`FINAL_VERIFICATION_001.json` records every final command and relevant code
hash, and verifies that code did not change during the test/export run. Final
provider SHA256 values are:

- inputs: `f99179802bf2be328e8867f5f1808f139678038883de03269fafe7c792f0cf11`
- grader: `f3f382822d3f589295bdde68bb3d2a2e9d07efa59a4468bf82850fdac17d7ac9`

`EVIDENCE_001.md` explains the hand arithmetic, native sources and precise
limits. `FAILURE_HISTORY_001.md` preserves actual failures and labels the two
earlier shared-worker transcript-only receipts explicitly. No failed stdout
was reconstructed or overwritten. Four original authority hashes match their
frozen values in `FROZEN_AUTHORITY_HASHES_001.json`.

Before this handoff, the immutable objective and all sixteen design principles
were reread verbatim, followed by the exact current workload and GeneTree
sheet/input/output contracts, including the accepted additive nullable-alignment,
assembly/read-outcome, taxonomy and transformation-digest clarifications.

No production integration, C4 adapter, library, registry, parent-return resolver,
model prompt, runtime policy, credit, W05 or goal/checklist file was changed.
Live service execution, original-task content custody and full episode
communication remain unverified by this workload. Root retains installation
and those integration responsibilities, including one pure call for every
originally selected analysis and complete multi-analysis wrapper retention.
