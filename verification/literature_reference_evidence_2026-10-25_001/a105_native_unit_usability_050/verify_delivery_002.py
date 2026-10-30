"""Verify this description-only delivery against its exact captured baseline."""
from copy import deepcopy
import difflib
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.literature_episodes import _population_catalog


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASELINE = HERE / "baseline_002"
C7 = "gene_annotation_episode/literature_episodes.py"
NEW = ("gene_annotation_episode/literature_native_rate_operand_information.py",
       "tests/test_literature_native_rate_operand_information.py")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def strip_descriptions(value):
    if isinstance(value, dict):
        return {key: strip_descriptions(child) for key, child in value.items()
                if key != "description"}
    if isinstance(value, list):
        return [strip_descriptions(child) for child in value]
    return value


def main():
    captured = json.loads((BASELINE / "SHA256.json").read_bytes())
    original = (BASELINE / "literature_episodes.py").read_bytes()
    assert digest(original) == captured[C7] == "c05828092d992e23055ab53b43258969bcb6b9ed356549cf81e53bb8295d41d5"
    replacements = (
        (b"    from .literature_rate_native_inputs import rate_source_population_schema\n",
         b"    from .literature_native_rate_operand_information import rate_source_population_schema_with_information\n"),
        (b'        "input_schema": rate_source_population_schema()})\n',
         b'        "input_schema": rate_source_population_schema_with_information()})\n'),
        (b'                         "literature_rate_native_inputs.py",\n',
         b'                         "literature_rate_native_inputs.py",\n'
         b'                         "literature_native_rate_operand_information.py",\n'),
    )
    expected = original
    for before, after in replacements:
        assert expected.count(before) == 1
        expected = expected.replace(before, after)
    assert (ROOT / C7).read_bytes() == expected
    unchanged = []
    for relative, expected_hash in captured.items():
        if relative != C7:
            assert digest((ROOT / relative).read_bytes()) == expected_hash, relative
            unchanged.append(relative)

    before_catalog = json.loads((BASELINE / "population_catalog.json").read_bytes())
    after_catalog = _population_catalog()
    assert len(before_catalog) == len(after_catalog) == 18
    native = "literature.rate.source.populate"
    unchanged_schemas = []
    for before, after in zip(before_catalog, after_catalog):
        assert before["name"] == after["name"]
        assert before["description"] == after["description"]
        if before["name"] == native:
            assert before["input_schema"] != after["input_schema"]
            assert strip_descriptions(before["input_schema"]) == strip_descriptions(after["input_schema"])
        else:
            assert before == after
            unchanged_schemas.append(before["name"])
    assert len(unchanged_schemas) == 17

    snapshot = HERE / "snapshot_002"
    snapshot.mkdir(exist_ok=False)
    patch = []
    files = {}
    for relative in (C7, *NEW):
        data = (ROOT / relative).read_bytes()
        lines = data.decode("utf-8").splitlines(keepends=True)
        assert all(not line.rstrip("\r\n").endswith((" ", "\t")) for line in lines)
        copied = snapshot / relative
        copied.parent.mkdir(parents=True, exist_ok=True)
        copied.write_bytes(data)
        files[relative] = {"sha256": digest(data), "bytes": len(data),
                           "snapshot": str(copied.relative_to(ROOT))}
        old = original.decode().splitlines(keepends=True) if relative == C7 else []
        patch.extend(difflib.unified_diff(old, lines,
            fromfile="a/" + relative if relative == C7 else "/dev/null",
            tofile="b/" + relative))
    patch_path = HERE / "IMPLEMENTATION_002.patch"
    with patch_path.open("x") as stream:
        stream.write("".join(patch))
    receipt = {
        "status": "passed", "scope": "Description-only native rate argument information",
        "baseline_C7_sha256": captured[C7], "current_files": files,
        "exact_C7_changes": ["native catalog schema factory import", "native catalog schema factory call",
                              "new information module implementation fingerprint"],
        "read_only_dependencies_verified": unchanged,
        "all_18_operation_names_and_descriptions_unchanged": True,
        "other_17_catalog_entries_and_schemas_exact": unchanged_schemas,
        "native_validation_schema_unchanged_after_stripping_only_descriptions_from_both": True,
        "production_reader_calculator_storage_TASK_renderer_edits": [],
        "patch": str(patch_path.relative_to(ROOT)), "patch_sha256": digest(patch_path.read_bytes()),
        "targeted_test_command": "PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -p no:cacheprovider -q --tb=short tests/test_literature_native_rate_operand_information.py",
        "observed_targeted_test_result": "12 passed in 0.73s", "observed_test_exit_code": 0,
        "limits": ["Synthetic fixture and controlled repository dispatch only",
                   "No full LiteratureEpisodes controller/runtime execution in this workload",
                   "No source paper or source-specific arguments inspected",
                   "No successful actual model-backed numerical population established",
                   "Old pins/runs not accessed or modified"]}
    with (HERE / "DELIVERY_RECEIPT_002.json").open("x") as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": receipt["status"], "files": files,
        "read_only_dependencies_verified": len(unchanged), "unchanged_other_catalog_entries": len(unchanged_schemas),
        "patch_sha256": receipt["patch_sha256"]}))


if __name__ == "__main__":
    main()
