"""Reproduce actual provider and native report examples from installed wheel bytes."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib
import io
import json
import socket
import subprocess
import sys
from unittest.mock import patch
import zipfile


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
wheel, = (HERE / "dist_002").glob("*.whl")
target = HERE / "unpacked_003"
target.mkdir(exist_ok=False)
assets = ["bvbrc_proteome_" + part + "_schemas.json" for part in
          ("native", "data", "sheet", "bundle", "directional")]
with zipfile.ZipFile(wheel) as archive:
    for name in assets:
        assert "gene_annotation_episode/" + name in archive.namelist(), name
    archive.extractall(target)
sys.path.insert(0, str(target))
names = ("native", "native_contracts", "data_contracts", "inputs", "joins", "sheet",
         "sheet_contracts", "calculators", "bundle_contracts", "bundle_adapter",
         "bundle_resolution", "bundle_projection", "fact_contracts", "directional", "directional_contracts")
modules = {name: importlib.import_module("gene_annotation_episode.bvbrc_proteome_" + name) for name in names}
for name, module in modules.items():
    assert Path(module.__file__).resolve().is_relative_to(target.resolve()), (name, module.__file__)
example = ROOT / "verification/tool_graders_bvbrc_proteome_bundle_2026-10-25_173/example_001"
case = json.loads((example / "CASE.json").read_text())
raw_inputs = {}
for row in json.loads((example / "ARTIFACT_BYTES.json").read_text()):
    raw = (example / row["path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == row["sha256"] and len(raw) == row["byte_count"]
    raw_inputs[row["artifact_ref"]] = raw
case["artifact_bytes"] = raw_inputs
expected = json.loads((example / "RESULT.json").read_text())
changed = json.loads((example / "RECALCULATED_COMPONENTS.json").read_text())
receipt = json.loads((example / "RECEIPT.json").read_text())
assert modules["bundle_adapter"].implementation_sha256() == receipt["implementation_sha256"]
for name, digest in receipt["dependency_sha256"].items():
    assert hashlib.sha256((target / "gene_annotation_episode" / name).read_bytes()).hexdigest() == digest

native_dir = ROOT / "verification/tool_graders_bvbrc_proteome_directional_2026-10-25_172"
native_inputs = json.loads((native_dir / "SOURCE_INPUTS_001.json").read_text())
native_cases = []
for release, row in zip(("2011", "2202", "2221"), native_inputs):
    expected_native = json.loads((native_dir / ("FILLED_NATIVE_" + release + "_001.json")).read_text())
    native_cases.append(((ROOT / row["file"]).read_bytes(), row["source"], expected_native))


def forbidden(*args, **kwargs):
    raise AssertionError("pure wheel function attempted acquisition, execution or file IO")


# Packaged schema initialization is program loading, not input acquisition.
# B1 loads its schema lazily; complete that setup before prohibiting IO.
modules["data_contracts"].proteome_data_schema("InputIndexResult")
before = deepcopy(case)
with ExitStack() as stack:
    for owner, name in ((Path, "read_text"), (Path, "read_bytes"), (io, "open"),
                        (socket, "socket"), (subprocess, "run"), (subprocess, "Popen")):
        stack.enter_context(patch.object(owner, name, forbidden))
    stack.enter_context(patch("builtins.open", forbidden))
    result = modules["bundle_adapter"].consume_bundle(**case)
    assert result == expected and case == before
    saved = modules["bundle_projection"].validate_saved_projection(
        result["sheet"], result["components"],
        facts=result["facts"], status=result["status"],
        missing_requirements=tuple(result["missing_requirements"]), diagnostics=tuple(result["diagnostics"]),
        requested_form=case["requested_form"], parameters=case["parameters"],
        original_task=case["bundle"]["original_task"], bundle_sha256=result["sheet"]["bundle_sha256"])
    assert saved == {k: result[k] for k in ("status", "facts", "missing_requirements", "diagnostics")}
    recalculated = modules["calculators"].calculate_native_components(
        result["sheet"]["native_sheet_result"]["value"], parameters=changed["value"]["parameters"])
    assert recalculated == changed
    native_outputs = []
    for raw, source, expected_native in native_cases:
        report = modules["directional"].parse_genome_comparison_directional_report(
            raw, source=source, declared_format=expected_native["declared_format"], report_key=expected_native["report_key"])
        assert report == expected_native
        assert modules["directional_contracts"].validate_directional_report(report) == report
        native_outputs.append(report)

summary = {
    "created_at": datetime.now(timezone.utc).isoformat(),
    "wheel": str(wheel.relative_to(ROOT)), "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
    "schema_assets": {name: hashlib.sha256((target / "gene_annotation_episode" / name).read_bytes()).hexdigest() for name in assets},
    "module_origins": {name: str(Path(module.__file__).relative_to(ROOT)) for name, module in modules.items()},
    "all_modules_from_wheel": True, "complete_provider_result_matches_saved_example": True,
    "matching_saved_reprojection_and_changed_parameter_calculation": True,
    "matching_retained_native_reports": len(native_outputs),
    "packaged_schema_initialization_completed_before_io_block": True,
    "io_network_execution_blocked_during_pure_calls": True,
    "identity_mean": result["facts"]["identity_mean"]["cell"]["value"],
    "subject_endpoint_difference_mean": result["facts"]["endpoint_mean"]["cell"]["value"],
    "selected_before": result["facts"]["selected"]["cell"]["value"],
    "selected_after": recalculated["value"]["tracks"][0]["selection_counts"]["pass"]["value"],
    "native_query_subject_hsp_counts": [[len(r["queries"]), sum(len(q["subjects"]) for q in r["queries"]),
        sum(len(s["hsps"]) for q in r["queries"] for s in q["subjects"])] for r in native_outputs],
    "live_or_episode_execution_claimed": False,
}
with (HERE / "WHEEL_VERIFICATION_003.json").open("x") as stream:
    json.dump(summary, stream, indent=2)
    stream.write("\n")
print(json.dumps({k: v for k, v in summary.items() if k not in {"schema_assets", "module_origins"}}))
