"""Check the built wheel in an isolated Python process, without installing it."""
from pathlib import Path
import hashlib
import importlib
import json
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
wheel, = (HERE / "dist").glob("*.whl")
target = HERE / "unpacked_001"
target.mkdir(exist_ok=False)
assets = ["bvbrc_proteome_native_schemas.json", "bvbrc_proteome_data_schemas.json", "bvbrc_proteome_sheet_schemas.json"]
with zipfile.ZipFile(wheel) as archive:
    for name in assets:
        assert "gene_annotation_episode/" + name in archive.namelist(), name
    archive.extractall(target)
sys.path.insert(0, str(target))
names = ("native", "native_contracts", "data_contracts", "inputs", "joins", "sheet", "sheet_contracts", "calculators")
modules = {name: importlib.import_module("gene_annotation_episode.bvbrc_proteome_" + name) for name in names}
for name, module in modules.items():
    assert Path(module.__file__).resolve().is_relative_to(target.resolve()), (name, module.__file__)
example = ROOT / "verification/tool_graders_bvbrc_proteome_data_contracts_2026-10-25/construction_example_001"
supplied = json.loads((example / "SUPPLIED_VALUES.json").read_text())
saved_sheet = json.loads((example / "SHEET.json").read_text())
saved_components = json.loads((example / "COMPONENTS.json").read_text())
saved_changed = json.loads((example / "RECALCULATED_COMPONENTS.json").read_text())
joins = modules["joins"].build_native_joins(**supplied)
assert joins == json.loads((example / "JOINS.json").read_text())
sheet = modules["sheet"].build_native_sheet(saved_sheet["value"]["native_results"],
    primary_source_ref=saved_sheet["value"]["primary_source_ref"], joins=joins["value"], representation_links=[],
    **{key: supplied[key] for key in ("input_index", "inventories", "feature_snapshots", "genome_snapshots", "sequence_snapshots")})
assert sheet == saved_sheet
components = modules["calculators"].calculate_native_components(sheet["value"], parameters=saved_components["value"]["parameters"])
assert components == saved_components
changed = modules["calculators"].calculate_native_components(sheet["value"], parameters=saved_changed["value"]["parameters"])
assert changed == saved_changed
result = {"wheel": str(wheel.relative_to(ROOT)), "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
          "schema_assets": {name: hashlib.sha256((target / "gene_annotation_episode" / name).read_bytes()).hexdigest() for name in assets},
          "module_origins": {name: str(Path(module.__file__).relative_to(ROOT)) for name, module in modules.items()},
          "all_modules_from_wheel": True, "matching_constructed_joins_sheet_components_and_changed_parameters": True,
          "selected_before": components["value"]["tracks"][0]["selection_counts"]["pass"]["value"],
          "selected_after": changed["value"]["tracks"][0]["selection_counts"]["pass"]["value"],
          "live_or_episode_execution_claimed": False}
with (HERE / "WHEEL_VERIFICATION_001.json").open("x") as stream:
    json.dump(result, stream, indent=2)
    stream.write("\n")
print(json.dumps({key: result[key] for key in ("all_modules_from_wheel", "matching_constructed_joins_sheet_components_and_changed_parameters", "selected_before", "selected_after")}))
