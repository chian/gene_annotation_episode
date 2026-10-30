"""Root independent focused verification from a fixed source snapshot."""
from pathlib import Path
import hashlib
import json
import sys
import time

OUT = Path(__file__).resolve().parent
PIN = OUT / "pin_137_001"
sys.path.insert(0, str(PIN))
sys.path.insert(0, str(PIN / "tests"))
import pytest

SELECTION = [
    "tests/test_literature_kinetic_model_inputs.py::test_exact_wire_model_binds_actual_bytes_and_preserves_owners",
    "tests/test_literature_kinetic_model_inputs.py::test_invalid_model_cannot_repair_owners_basis_or_covariance",
    "tests/test_literature_kinetic_model_storage.py::test_exact_subset_forwarding_and_query_only_saved_reconstruction",
    "tests/test_literature_kinetic_model_storage.py::test_global_source_ids_do_not_grant_receipt",
    "tests/test_literature_kinetic_model_storage.py::test_modified_saved_model_never_becomes_original_numeric_fact",
    "tests/test_literature_kinetic_model_integration.py::test_selected_child_to_parent_model_subset_and_ordinary_observations",
    "tests/test_literature_kinetic_model_integration.py::test_full_task_recurs_and_model_rows_do_not_expand_private_numbers",
    "tests/test_literature_kinetic_integration.py::test_nested_selected_episodes_preserve_only_requested_native_cells_without_extra_observations",
    "tests/test_literature_kinetic_integration.py::test_actual_c4_admission_rollback_original_receipt_tamper_and_read_only_reopen",
    "tests/test_literature_parent_population_information.py::test_all_child_population_entries_schemas_and_order_equal_prechange_catalog[literature]",
    "tests/test_literature_parent_population_information.py::test_explicit_initial_metadata_reconstructs_without_execution_or_episode_identity",
    "tests/test_joined_native_context_reaction_render_129.py::test_joined_own_outcomes_and_typed_native_returns_keep_family_meanings",
]


def main():
    manifest = json.loads((OUT / "PIN_137_001.json").read_text())["files"]
    before = time.monotonic()
    code = pytest.main(["-q", "--tb=short", "-p", "no:cacheprovider", "--junitxml=" + str(OUT / "ROOT_JOINED_137_001.xml"), *SELECTION])
    imports = {}
    for name, module in list(sys.modules.items()):
        file = getattr(module, "__file__", None)
        if file and (name.startswith(("gene_annotation_episode", "method_loop")) or name.startswith("test_literature")):
            imports[name] = str(Path(file).resolve())
    outside = {name: file for name, file in imports.items() if not Path(file).is_relative_to(PIN)}
    changed = [file for file, digest in manifest.items()
               if hashlib.sha256((PIN / file).read_bytes()).hexdigest() != digest]
    result = {"pytest_exit_code": int(code), "elapsed_seconds": time.monotonic()-before,
              "selected_functions": SELECTION, "pinned_file_count": len(manifest),
              "changed_snapshot_files": changed, "imported_module_count": len(imports),
              "imports_outside_snapshot": outside,
              "scope": "Independent synthetic engineering checks; not primary-source validation, actual-model science, a full suite or A105 completion"}
    (OUT / "ROOT_JOINED_137_IMPORTS_001.json").write_text(json.dumps(imports, indent=2)+"\n")
    (OUT / "ROOT_JOINED_137_RESULT_001.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))
    return int(code) or bool(outside) or bool(changed)


if __name__ == "__main__":
    raise SystemExit(main())
