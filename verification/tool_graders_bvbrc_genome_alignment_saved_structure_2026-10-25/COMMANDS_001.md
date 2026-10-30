# Verification commands

Working directory: `/home/chia/repos/gene_annotation_episode`.

Existing strict E/F tests, terminal 6 passed / 107 deselected in 13.09s:

```bash
.venv/bin/python -m pytest -q tests/test_bvbrc_genome_alignment_bundle_projection.py tests/test_bvbrc_genome_alignment_returns.py -k strict --tb=short --junitxml=verification/tool_graders_bvbrc_genome_alignment_saved_structure_2026-10-25/STRICT_EF_001.xml >verification/tool_graders_bvbrc_genome_alignment_saved_structure_2026-10-25/STRICT_EF_001.log 2>&1
```

Initial new suite, terminal 119 passed / 2 failed in 29.26s (preserved; test dictionary-order assertions corrected subsequently):

```bash
.venv/bin/python -m pytest -q tests/test_genome_alignment_saved_structure.py --tb=short --junitxml=verification/tool_graders_bvbrc_genome_alignment_saved_structure_2026-10-25/STRUCTURE_001.xml >verification/tool_graders_bvbrc_genome_alignment_saved_structure_2026-10-25/STRUCTURE_001.log 2>&1
```

Complete bounded regression, terminal 1,160 passed in 287.36s:

```bash
.venv/bin/python -m pytest -q tests/test_genome_alignment_saved_structure.py tests/test_mauve_v4_formats.py tests/test_mauve_v4_calculators.py tests/test_mauve_backbone_formats.py tests/test_mauve_backbone_calculators.py tests/test_mauve_bbcols_calculators.py tests/test_xmfa_formats.py tests/test_xmfa_format_contracts.py tests/test_xmfa_sources.py tests/test_xmfa_coordinates.py tests/test_xmfa_calculators.py tests/test_bvbrc_genome_alignment_input_contracts.py tests/test_bvbrc_genome_alignment_sheet.py tests/test_bvbrc_genome_alignment_calculation_contracts.py tests/test_bvbrc_genome_alignment_calculators.py tests/test_bvbrc_genome_alignment_bundle_adapter.py tests/test_bvbrc_genome_alignment_bundle_contracts.py tests/test_bvbrc_genome_alignment_bundle_resolution.py tests/test_bvbrc_genome_alignment_bundle_projection.py tests/test_bvbrc_genome_alignment_returns.py tests/test_bvbrc_genome_alignment_returns_original.py --tb=short --durations=10 --junitxml=verification/tool_graders_bvbrc_genome_alignment_saved_structure_2026-10-25/REGRESSION_001.xml >verification/tool_graders_bvbrc_genome_alignment_saved_structure_2026-10-25/REGRESSION_001.log 2>&1
```

Receipt builder, terminal with 170 blocked aliases, 90 unchanged original function ASTs, four retained native artifacts and seven request families:

```bash
.venv/bin/python verification/tool_graders_bvbrc_genome_alignment_saved_structure_2026-10-25/build_receipts_001.py >verification/tool_graders_bvbrc_genome_alignment_saved_structure_2026-10-25/BUILD_RECEIPTS_001.log 2>&1
```

These are historical commands for the receipts above. A subsequent run must use new receipt names rather than overwriting them; the builder's fixed output names should likewise be versioned before reuse.
