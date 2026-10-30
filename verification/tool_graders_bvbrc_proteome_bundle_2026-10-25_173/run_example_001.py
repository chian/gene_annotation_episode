"""Retain the actual provider composition over explicitly synthetic host inputs.

Every scientific byte comes from root's retained synthetic construction example;
the real provider, A/B1/B2/B3/B4 and real projector run unchanged. This is not an
AppService invocation, authenticated custody record or episode communication.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from test_bvbrc_proteome_bundle_resolution import fixture
from gene_annotation_episode.bvbrc_proteome_bundle_adapter import consume_bundle, implementation_sha256, _DEPENDENCIES
from gene_annotation_episode.bvbrc_proteome_calculators import calculate_native_components
from gene_annotation_episode.bvbrc_proteome_bundle_projection import validate_saved_projection
from gene_annotation_episode.bvbrc_proteome_bundle_contracts import digest

DEST = Path(__file__).parent / "example_001"
DEST.mkdir(exist_ok=False)


def save(name, value):
    (DEST / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


case = fixture()
result = consume_bundle(**case)
assert result["status"] == "ok"
track = result["components"]["value"]["tracks"][0]
assert track["first_hsp_identity_summary"]["mean"]["value"] == .4375
assert track["subject_endpoint_difference_summary"]["mean"]["value"] == .625
assert track["selection_counts"]["pass"]["value"] == 1
assert track["reference_input_record_count"]["value"] is None
recalculated = calculate_native_components(result["sheet"]["native_sheet_result"]["value"],
    parameters={**case["parameters"]["calculation_parameters"], "minimum_identity_fraction": .9})
assert recalculated["value"]["tracks"][0]["selection_counts"]["pass"]["value"] == 0
assert recalculated["value"]["sheet_sha256"] == result["components"]["value"]["sheet_sha256"]
replayed = validate_saved_projection(result["sheet"], result["components"], facts=result["facts"], status=result["status"],
    missing_requirements=tuple(result["missing_requirements"]), diagnostics=tuple(result["diagnostics"]),
    requested_form=case["requested_form"], parameters=case["parameters"], original_task=case["bundle"]["original_task"],
    bundle_sha256=digest(case["bundle"]))
assert replayed["facts"] == result["facts"]
raw_manifest = []
for i, (artifact_ref, raw) in enumerate(case["artifact_bytes"].items()):
    name = f"input_{i:03d}.bin"
    (DEST / name).write_bytes(raw)
    raw_manifest.append(dict(artifact_ref=artifact_ref, path=name, sha256=hashlib.sha256(raw).hexdigest(), byte_count=len(raw)))
save("ARTIFACT_BYTES.json", raw_manifest)
save("CASE.json", {key: value for key, value in case.items() if key != "artifact_bytes"})
save("RESULT.json", result)
save("SHEET.json", result["sheet"])
save("COMPONENTS.json", result["components"])
save("RECALCULATED_COMPONENTS.json", recalculated)
current = fixture(effective=False)
current_result = consume_bundle(**current)
assert current_result["sheet"]["input_index_result"] is None
assert current_result["facts"]["identity_mean"]["cell"]["value"] == .4375
save("CURRENT_HOST_SUBMITTED_GAP_RESULT.json", current_result)
receipt = dict(
    created_at=datetime.now(timezone.utc).isoformat(),
    origin="retained_synthetic_native_bytes_real_provider_A_B1_B2_B3_B4_projector_no_live_service_or_episode",
    conditional_index="synthetic_original_task_effective_parameters_bound_to_explicit_raw_source; production_current_TaskHandoff_sets_null",
    identity_mean=.4375, subject_endpoint_difference_mean=.625, selected_before=1, selected_after=0,
    executed_reference_count=None, saved_sheet_unchanged=recalculated["value"]["sheet_sha256"] == result["components"]["value"]["sheet_sha256"],
    current_submitted_source="proteome_parameter_source_unbound; request_ref_not_in_current_ContentBinding_enums",
    adapter_id=result["adapter_id"], adapter_version=result["adapter_version"], implementation_sha256=implementation_sha256(),
    dependency_sha256={name: hashlib.sha256((ROOT / "gene_annotation_episode" / name).read_bytes()).hexdigest() for name in sorted(_DEPENDENCIES)},
    files={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DEST.iterdir())},
)
save("RECEIPT.json", receipt)
print(json.dumps({key: receipt[key] for key in ("origin", "identity_mean", "subject_endpoint_difference_mean", "selected_before", "selected_after", "executed_reference_count", "saved_sheet_unchanged", "implementation_sha256")}))
