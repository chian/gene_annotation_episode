"""Root review of the description-only rate operand delivery."""
import ast
import hashlib
import json
from pathlib import Path
import re

from gene_annotation_episode.literature_episodes import _population_catalog

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
OWNER = OUT.parent / "a105_native_unit_usability_050"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strip(value):
    if isinstance(value, dict):
        return {key: strip(item) for key, item in value.items() if key != "description"}
    if isinstance(value, list):
        return [strip(item) for item in value]
    return value


def main():
    manifest = json.loads((OWNER / "MANIFEST_002.json").read_bytes())
    for name, row in manifest["files"].items():
        path = OWNER / name
        assert digest(path) == row["sha256"] and path.stat().st_size == row["bytes"], name
    receipt = json.loads((OWNER / "DELIVERY_RECEIPT_002.json").read_bytes())
    for name, row in receipt["current_files"].items():
        assert digest(ROOT / name) == row["sha256"]
        assert digest(ROOT / row["snapshot"]) == row["sha256"]
    baseline = (OWNER / "baseline_002/literature_episodes.py").read_text()
    substitutions = (
        ("from .literature_rate_native_inputs import rate_source_population_schema\n",
         "from .literature_native_rate_operand_information import rate_source_population_schema_with_information\n"),
        ('"input_schema": rate_source_population_schema()}',
         '"input_schema": rate_source_population_schema_with_information()}'),
        ('                         "literature_rate_native_inputs.py",\n',
         '                         "literature_rate_native_inputs.py",\n                         "literature_native_rate_operand_information.py",\n'),
    )
    expected = baseline
    for old, new in substitutions:
        assert expected.count(old) == 1
        expected = expected.replace(old, new)
    assert expected == (ROOT / "gene_annotation_episode/literature_episodes.py").read_text()
    original_catalog = json.loads((OWNER / "baseline_002/population_catalog.json").read_bytes())
    current_catalog = _population_catalog()
    assert len(original_catalog) == len(current_catalog) == 18
    modified = []
    for before, after in zip(original_catalog, current_catalog):
        assert before["name"] == after["name"] and before["description"] == after["description"]
        if before != after:
            modified.append(after["name"])
            assert strip(before) == strip(after)
    assert modified == ["literature.rate.source.populate"]
    dependency_hashes = json.loads((OWNER / "baseline_002/SHA256.json").read_bytes())
    for name, expected_hash in dependency_hashes.items():
        if name == "gene_annotation_episode/literature_episodes.py":
            assert digest(OWNER / "baseline_002/literature_episodes.py") == expected_hash
        else:
            assert digest(ROOT / name) == expected_hash, name
    # Reuse only the already reviewed, source-independent unified-hunk verifier.
    helper = OUT.parent / "kinetic_integration_parent_review_047/verify_delivery_006.py"
    tree = ast.parse(helper.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "apply_chunk")
    namespace = {"re": re}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(helper), "exec"), namespace)
    rebuilt = []
    for chunk in re.split(r"(?m)^--- ", (OWNER / "IMPLEMENTATION_002.patch").read_text())[1:]:
        old, new, body = chunk.split("\n", 2)
        assert new.startswith("+++ b/")
        name = new[6:]
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        if old == "/dev/null":
            original = ""
        else:
            assert name == "gene_annotation_episode/literature_episodes.py" and old == "a/" + name
            original = baseline
        raw = namespace["apply_chunk"](original, body)
        assert raw == (ROOT / name).read_bytes()
        target = OUT / "reconstructed_002" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)
        rebuilt.append(name)
    assert set(rebuilt) == set(receipt["current_files"])
    assert receipt["observed_test_exit_code"] == 0
    assert receipt["observed_targeted_test_result"] == "12 passed in 0.73s"
    result = {"passed": True, "manifest_entries_verified": len(manifest["files"]),
        "reconstructed_files": rebuilt, "exact_c7_substitutions": 3,
        "unchanged_other_catalog_entries": 17, "validation_keywords_unchanged": True,
        "read_only_dependency_hashes_verified": len(dependency_hashes) - 1,
        "released_c7_baseline_hash_verified": True,
        "parent_full_read": ["146-line information module", "244-line test module", "proposal/repro/receipt", "handoff/manifest/delivery/terminal evidence", "all C7 delta hunks"],
        "test_suite_repeated": False,
        "not_proven": ["scientific source suitability", "cause of old live failures", "successful configured-model numerical extraction"]}
    with (OUT / "RECEIPT_002.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"passed": True, "manifest_entries": len(manifest["files"]),
                      "reconstructed_files": len(rebuilt), "read_only_dependencies": len(dependency_hashes) - 1}))


if __name__ == "__main__":
    main()
