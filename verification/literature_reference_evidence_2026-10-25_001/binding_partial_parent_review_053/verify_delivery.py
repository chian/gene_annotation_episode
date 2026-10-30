"""Root audit of the reviewed additive partial-uncertainty correction."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
OWNER = OUT.parent / "a105_binding_partial_uncertainty_053"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    receipt = json.loads((OWNER / "RELEASE_RECEIPT_002.json").read_bytes())
    for name, expected in receipt["artifact_sha256"].items():
        assert digest(OWNER / name) == expected, name
    for name, row in receipt["production_files"].items():
        assert digest(ROOT / name) == row["released_sha256"], name
        assert digest(OWNER / row["snapshot"]) == row["released_sha256"], name
        assert digest(OWNER / "baseline_001" / name) == row["baseline_sha256"], name
        assert digest(OUT.parent / "binding_interaction_parent_review_048/reconstructed_001" / name) == row["baseline_sha256"]
    helper = OUT.parent / "kinetic_integration_parent_review_047/verify_delivery_006.py"
    function = next(n for n in ast.parse(helper.read_text()).body
                    if isinstance(n, ast.FunctionDef) and n.name == "apply_chunk")
    namespace = {"re": re}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(helper), "exec"), namespace)
    rebuilt = []
    for part in re.split(r"(?m)^--- ", (OWNER / "FULL_PATCH_002.diff").read_text())[1:]:
        old, new, body = part.split("\n", 2)
        assert new.startswith("+++ b/")
        name = new[6:]
        assert name in receipt["production_files"] and old == "a/" + name
        raw = namespace["apply_chunk"]((OWNER / "baseline_001" / name).read_text(), body)
        assert raw == (ROOT / name).read_bytes()
        target = OUT / "reconstructed_002" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)
        rebuilt.append(name)
    assert set(rebuilt) == set(receipt["production_files"])
    comparisons = json.loads((OWNER / "BASELINE_COMPARISON_002.json").read_bytes())
    assert len(comparisons["comparisons"]) == 84
    for row in comparisons["comparisons"]:
        assert row["baseline_output"] == row["corrected_output"]
        assert json.dumps(row["baseline_output"], sort_keys=True, allow_nan=False) == json.dumps(
            row["corrected_output"], sort_keys=True, allow_nan=False)
    name = "gene_annotation_episode/literature_binding_interaction_calculations.py"
    functions = []
    for path in (OWNER / "baseline_001" / name, ROOT / name):
        functions.append({n.name: n for n in ast.parse(path.read_text()).body
                          if isinstance(n, ast.FunctionDef)})
    old, new = functions
    assert set(new) - set(old) == {"_uncertainty_qualifications"}
    for name in set(old) - {"_uncertainty", "populate_binding_interaction"}:
        assert ast.dump(old[name]) == ast.dump(new[name]), name
    populate = deepcopy(new["populate_binding_interaction"])
    index = next(i for i, n in enumerate(populate.body)
                 if ast.unparse(n) == "qualifications.extend(_uncertainty_qualifications(inputs))")
    del populate.body[index]
    assert ast.dump(old["populate_binding_interaction"]) == ast.dump(populate)
    terminal = (OWNER / "TERMINAL_002.txt").read_text()
    assert "99 passed in 0.38s\nExit code: 0\n" in terminal
    result = {"passed": True, "reconstructed_files": rebuilt,
        "saved_complete_output_pairs_equal": 84,
        "unchanged_original_functions": len(old) - 2,
        "populate_changed_only_by_finite_qualifications": True,
        "old_048_immutable_bytes_preserved": True,
        "parent_full_patch_and_new_tests_read": True,
        "test_suite_repeated": False,
        "scope": "Pure nullable source-metadata correction; source interpretation/custody/selected integration remain separate"}
    with (OUT / "RECEIPT_002.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k in (
        "passed", "saved_complete_output_pairs_equal", "unchanged_original_functions")}))


if __name__ == "__main__":
    main()
