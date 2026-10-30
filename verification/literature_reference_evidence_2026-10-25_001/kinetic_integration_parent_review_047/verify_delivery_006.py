"""Independent root patch, preservation and detached-regression verification."""
import ast
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import re

from test_literature_kinetic_inputs import fixture
from gene_annotation_episode.literature_kinetic_inputs import read_kinetic_inputs
from gene_annotation_episode.literature_kinetic_calculations import populate_kinetic_contrast
from gene_annotation_episode.literature_kinetic_validation import validate_saved_kinetic
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_episodes import _population_catalog

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
OWNER = OUT.parent / "a105_kinetic_integration_047"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_chunk(original, chunk):
    """Apply exact unified hunks, validating every old/context line ourselves."""
    old = original.splitlines(keepends=True)
    result, cursor, lines, index = [], 0, chunk.splitlines(keepends=True), 0
    while index < len(lines):
        match = re.fullmatch(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@\n", lines[index])
        assert match, lines[index]
        start, count = int(match[1]), int(match[2] or 1)
        offset = start - 1 if count else start
        assert cursor <= offset <= len(old)
        result.extend(old[cursor:offset])
        cursor, consumed, produced = offset, 0, 0
        index += 1
        while index < len(lines) and not lines[index].startswith("@@ "):
            line = lines[index]
            assert line[0] in " +-", line
            if line[0] in " -":
                assert cursor < len(old) and old[cursor] == line[1:]
                cursor += 1
                consumed += 1
            if line[0] in " +":
                result.append(line[1:])
                produced += 1
            index += 1
        assert consumed == count and produced == int(match[4] or 1)
    result.extend(old[cursor:])
    return "".join(result).encode()


def constants(path):
    tree = ast.parse(path.read_text())
    return [ast.dump(n, include_attributes=False) for n in tree.body
            if isinstance(n, (ast.Assign, ast.AnnAssign))]


def main():
    manifest = json.loads((OWNER / "MANIFEST_006.json").read_bytes())
    assert digest(OWNER / manifest["patch"]) == manifest["patch_sha256"]
    for name, expected in manifest["files"].items():
        assert digest(ROOT / name) == expected, name
        assert digest(OWNER / "snapshot_006" / name) == expected, name
    reconstructed = []
    patch = (OWNER / manifest["patch"]).read_text()
    for part in re.split(r"(?m)^--- ", patch)[1:]:
        header, new, body = part.split("\n", 2)
        assert new.startswith("+++ b/")
        name = new[6:]
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        if header == "/dev/null":
            original = ""
        else:
            assert header == "a/" + name
            original = (OWNER / "baseline" / name).read_text()
            assert digest(OWNER / "baseline" / name) == manifest["changed_existing_files"][name]["before"]
        content = apply_chunk(original, body)
        assert content == (ROOT / name).read_bytes(), name
        target = OUT / "reconstructed_006" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(content)
        reconstructed.append(name)
    assert set(reconstructed) == set(manifest["files"])
    baseline = json.loads((OWNER / "BASELINE_SHA256.json").read_bytes())
    changed = {name for name, expected in baseline.items() if digest(ROOT / name) != expected}
    assert changed == set(manifest["changed_existing_files"])
    for name, expected in manifest["base_and_frozen_sources"].items():
        assert digest(ROOT / name) == expected
    for name in changed:
        if name.startswith("gene_annotation_episode/"):
            assert constants(ROOT / name) == constants(OWNER / "baseline" / name), name
    original_catalog_tree = ast.parse((OWNER / "baseline/gene_annotation_episode/literature_episodes.py").read_text())
    original_catalog_function = next(n for n in original_catalog_tree.body
                                    if isinstance(n, ast.FunctionDef) and n.name == "_population_catalog")
    namespace = {"__package__": "gene_annotation_episode"}
    exec(compile(ast.Module(body=[original_catalog_function], type_ignores=[]), "baseline_catalog", "exec"), namespace)
    old_catalog, current_catalog = namespace["_population_catalog"](), _population_catalog()
    assert len(old_catalog) == 17 and len(current_catalog) == 18
    assert old_catalog == current_catalog[:17]
    source, selection = fixture()
    extraction = read_kinetic_inputs(selection, read_source=source.read)
    calculation = populate_kinetic_contrast(extraction["calculation_inputs"])
    rejected = []
    for field, value in (("relation", "gt"), ("approximate", True), (None, None)):
        e, c = deepcopy(extraction), deepcopy(calculation)
        if field:
            e["operands"]["numerator"]["number"][field] = value
        else:
            c["cells"]["numerator_parameter"]["unavailable_reason"] = "source_measurement_unreported"
        try:
            validate_saved_kinetic(selection, e, c)
        except ExperimentalContractError as error:
            rejected.append({"mutation": field or "populated_unavailable_reason", "error": str(error)})
        else:
            raise AssertionError("Detached semantic inconsistency survived")
    validate_saved_kinetic(selection, extraction, calculation)
    result = {"passed": True, "files_reconstructed": reconstructed,
        "existing_files_checked": len(baseline), "expected_existing_files_changed": sorted(changed),
        "all_first_17_catalog_entries_exact": True, "task_constants_unchanged": True,
        "base_and_frozen_hashes_exact": True, "synthetic_detached_mutations_rejected": rejected,
        "original_valid_detached_state_preserved": True,
        "test_suite_repeated": False, "scientific_source_or_live_model_proof": False,
        "parent_review_scope": "Full new storage/validator/test reads plus exact reviewed shared deltas; synthetic runtime evidence separately authenticated by terminal receipts"}
    with (OUT / "DELIVERY_REVIEW_006.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k in (
        "passed", "existing_files_checked", "all_first_17_catalog_entries_exact", "task_constants_unchanged")}))


if __name__ == "__main__":
    main()
