"""Check044's final code scope without rerunning its episode test suites."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
OWNER = BASE / "a105_subset_forwarding_044"
OUT = Path(__file__).resolve().parent
CHANGED = {
    "gene_annotation_episode/literature_episodes.py",
    "gene_annotation_episode/literature_rate_storage.py",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def functions(path):
    result = {}
    def walk(node, prefix=()):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                result[(*prefix, child.name)] = ast.dump(child, include_attributes=False)
            elif isinstance(child, ast.ClassDef):
                walk(child, (*prefix, child.name))
    walk(ast.parse(path.read_text()))
    return result


def main():
    baseline = json.loads((OWNER / "BASELINE_SHA256.json").read_bytes())
    changed = {name for name, expected in baseline.items() if digest(ROOT / name) != expected}
    assert changed == CHANGED, changed
    expected_methods = {
        "literature_episodes.py": {
            ("LiteratureEpisodes", "_rate_facts"),
            ("LiteratureEpisodes", "validate_received_report"),
        },
        "literature_rate_storage.py": {
            ("LiteratureRateRepository", "__init__"),
            ("LiteratureRateRepository", "receive_cells"),
            ("LiteratureRateRepository", "received_cells"),
        },
    }
    method_changes, new_functions = {}, {}
    for name, permitted in expected_methods.items():
        old = functions(OWNER / "baseline/gene_annotation_episode" / name)
        new = functions(ROOT / "gene_annotation_episode" / name)
        assert set(old) <= set(new)
        modifications = {key for key in old if old[key] != new[key]}
        assert modifications <= permitted, modifications
        method_changes[name] = [".".join(key) for key in sorted(modifications)]
        new_functions[name] = [".".join(key) for key in sorted(set(new) - set(old))]
    frozen = {
        "literature_optical_calculations.py": "1242c0e58e83a1ef4e4e8f25bbf94737b33dc706e61794c6ff98b87ce3c5740e",
        "literature_optical_inputs.py": "6e956a39196800d2fe2e4e841a913f40ae4f2d1c44c1fd54fc6abdc6afd6b474",
        "literature_optical_validation.py": "4340cce4a7a659d167b15fcb707b646bd13f8d213e36e0957a454cc02eb54425",
        "literature_optical_storage.py": "07128e71f1976f03eb966d09b26ca0b53d285bb1b3ae1946cfa9d7f27ae806ac",
        "literature_kinetic_calculations.py": "1ca423165e40b99140bb1a1b431081e240d1ae788f7b5d933823817a6c397f50",
        "literature_kinetic_inputs.py": "1176033e44bb7e2ff065aecd6f1d335fbcab531069e99490cd293dd8a8edb844",
    }
    for name, expected in frozen.items():
        assert digest(ROOT / "gene_annotation_episode" / name) == expected, name
    result = {
        "status": "passed", "scope": "independent parent preservation audit",
        "baseline_files_checked": len(baseline),
        "changed_existing_files": sorted(changed),
        "unchanged_baseline_files": len(baseline) - len(changed),
        "existing_function_changes": method_changes,
        "new_functions": new_functions,
        "population_catalog_and_all_schema_functions_AST_unchanged": True,
        "frozen_optical_and_kinetic_sources_unchanged": True,
        "current_existing_source_sha256": {name: digest(ROOT / name) for name in sorted(changed)},
        "tests_rerun": False,
        "primary_source_or_model_history_read": False,
        "test_completion_claim": "separate owner terminal receipt; this audit verifies scope, not runtime behavior",
    }
    with (OUT / "PRESERVATION_RECEIPT_005.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
