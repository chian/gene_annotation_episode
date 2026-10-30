# Reproduce the079 receipt repair

From the repository root, verify the separate source/dependency/test pin:

```sh
.venv/bin/python verification/literature_reference_evidence_2026-10-25_001/a105_native_view_receipt_repair_079/verify_pin.py
```

The manifest seals the complete copied workflow package and method_loop, the six
selected test files, their five normative schema dependencies, relevant authority
documents and pyproject.toml. The pin excludes bytecode and caches. Its native
module is the reviewed working copy, not an imported older protected pin.

Run from this workload's `pin_001` directory using the repository virtualenv:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. RECEIPT_PIN_ROOT="$PWD" \
RECEIPT_IMPORT_AUDIT="$PWD/../PIN_ACTUAL_IMPORTS_RECHECK.json" \
/home/chia/repos/gene_annotation_episode/.venv/bin/python -m pytest \
-p no:cacheprovider -p receipt_import_audit \
tests/test_literature_ratio_source_runtime_receipt.py \
tests/test_literature_ratio_source_storage.py \
tests/test_literature_ratio_source_readonly.py \
tests/test_literature_ratio_source_inputs.py \
tests/test_literature_ratio_source_calculations.py \
tests/test_literature_ratio_source_validation.py \
--basetemp=../pin_test_tmp_recheck -q
```

Use a new basetemp/output name to preserve the original verification outputs.
PIN_ACTUAL_IMPORTS_001.json records original test collection/exit status, actual
import paths and hashes, Python executable/version and installed distribution
versions. The provenance plugin asserts that imported workflow, method_loop and
selected test modules come from this pin. The fresh readonly subprocess tests
explicitly set PYTHONPATH to this same pin and reject byte access, decoding,
population or mutation during saved reconstruction.

The bounded `probe_preserved_failure.py` can be rerun from the repository root
with a new output filename. It reads the declared frozen077 DB in mode=ro with
PRAGMA query_only=ON. PRE_FIX_ACTUAL_COUNTEREXAMPLE_001.json retains the genuine
pre-edit rejection; POST_FIX_ACTUAL_RECEIPT_001.json retains the post-edit receipt
over the same unmodified runtime and native records. Restoring old native code
is unnecessary to inspect the preserved counterexample; original bytes and the
minimal unified patch are supplied separately.

These are controlled engineering checks. They perform no model inference,
paper acquisition or scientific measurement. They do not substitute for077's
independent selected LiteratureEpisode/Workflow/C1/C4 verification or establish
completion of the full literature goal.
