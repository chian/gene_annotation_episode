# Reproduction commands and observed outcomes

Working directory: `/home/chia/repos/gene_annotation_episode`.

```sh
.venv/bin/python -m pytest -q tests/test_bvbrc_genome_alignment_bundle_contracts.py tests/test_bvbrc_genome_alignment_bundle_resolution.py tests/test_bvbrc_genome_alignment_bundle_projection.py tests/test_bvbrc_genome_alignment_bundle_adapter.py --junitxml=verification/tool_graders_bvbrc_genome_alignment_bundle_2026-10-25/PYTEST_E_FINAL_001.xml
```

Observed exit 1: 159 passed, 3 failed in 24.17 seconds. All three failures are
the preserved strict saved-arithmetic regression. Exact output is retained in
`PYTEST_E_FINAL_001.log`.

```sh
.venv/bin/python -m pytest -q tests/test_bvbrc_genome_alignment_bundle_adapter.py::test_unrelated_adapter_and_downstream_consumer_bytes_are_not_pinned
```

Observed exit 0: 1 passed. Exact output is retained in
`PYTEST_PIN_EXCLUSION_002.log`. This was the only test added after the full run.

```sh
.venv/bin/python verification/tool_graders_bvbrc_genome_alignment_bundle_2026-10-25/BUILD_EXAMPLES_001.py
```

Observed exit 0. Saved complete facade inputs/results, fourteen-family saved
catalog example, and accepted012 edge results. The script performs verification
file writes outside the production facade.

The AST dependency audit and direct authoritative-goal SHA256 check are saved
in `PIN_AUDIT_CURRENT_004.json`. The audit compares actual reachable local
imports (including function-local imports), package initialization and local
file-loaded schema names with the facade's exact dependency tuple. Its
independent test and all 43 dependency-mutation checks passed in the full run.

The first focused strict replay probe patched
`mauve_v4_calculation_contracts.union_intervals` after building the actual saved
fixture; it failed through E → D → native validation, as recorded in
`REPLAY_UNION_BARRIER_001.txt`. A subsequent `sys.setprofile` trace over a saved
seven-family D fixture recorded all local calls and scientific helper/math
calls in `REPLAY_ARITHMETIC_TRACE_002.json`. The maintained strict pytest case
now covers all three E saved APIs and the full helper aliases.
