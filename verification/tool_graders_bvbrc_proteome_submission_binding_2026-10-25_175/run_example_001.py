"""Reproduce the candidate's actual host custody → pure input-index example."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

AREA = Path(__file__).resolve().parent
CANDIDATE = AREA / "candidate"
sys.path[:0] = [str(CANDIDATE), str(CANDIDATE / "tests")]

from gene_annotation_episode import bvbrc_proteome_bundle_resolution as provider
from gene_annotation_episode import bvbrc_proteome_bundle_contracts as contracts
from gene_annotation_episode.bvbrc_proteome_bundle_adapter import implementation_sha256
from gene_annotation_episode.bvbrc_proteome_bundle_projection import validate_saved_projection
from gene_annotation_episode.bvbrc_proteome_calculators import calculate_native_components
from test_bvbrc_appservice_request_content import retained_submission
from test_bvbrc_proteome_submitted_parameters import submitted_case, selected_source
from test_bvbrc_proteome_bundle_resolution import sync_supplied


def forbidden(*args, **kwargs):
    raise AssertionError("unexpected acquisition or native execution")


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def main():
    assert Path(provider.__file__).resolve().is_relative_to(CANDIDATE)
    out = AREA / "example_001"
    out.mkdir(exist_ok=False)
    with patch("socket.create_connection", forbidden), patch("urllib.request.OpenerDirector.open", forbidden):
        source = retained_submission(out / "actual_host_state")
        try:
            case = submitted_case(source)
            case["artifact_bytes"][source.binding["artifact_ref"]] = source.driver.custody.content(source.context, source.binding)
            assert source.driver.custody.evidence(source.context, source.evidence) == source.task["submitted_parameters"]
            with patch.object(source.store, "get", forbidden), patch.object(source.store, "get_artifact", forbidden), patch("subprocess.run", forbidden):
                result = provider.consume_bundle(**case)
                missing = deepcopy(case)
                missing["bundle"]["supplied_contents"].remove(source.binding)
                missing_result = provider.consume_bundle(**missing)
                wrong_pointer = deepcopy(case)
                selected_source(wrong_pointer)["pointer"] = "/prepared/native_operands/request/parameters"
                sync_supplied(wrong_pointer)
                wrong_result = provider.consume_bundle(**wrong_pointer)
                revised = calculate_native_components(result["sheet"]["native_sheet_result"]["value"], parameters={
                    **case["parameters"]["calculation_parameters"], "minimum_identity_fraction": .9})
                checked = validate_saved_projection(result["sheet"], result["components"], facts=result["facts"], status=result["status"],
                    missing_requirements=tuple(result["missing_requirements"]), diagnostics=tuple(result["diagnostics"]),
                    requested_form=case["requested_form"], parameters=case["parameters"], original_task=case["bundle"]["original_task"],
                    bundle_sha256=contracts.digest(case["bundle"]))
            assert checked["facts"] == result["facts"]
            for filename, value in {
                "ORIGINAL_TASK.json": source.task, "TASK_HANDOFF.json": source.handoff,
                "NATIVE_SOURCE_RECORD.json": source.source, "PARAMETER_EVIDENCE.json": source.evidence,
                "BUNDLE.json": case["bundle"], "PARAMETERS.json": case["parameters"],
                "SUPPLIED_VALUES.json": case["supplied_values"], "REQUESTED_FORM.json": case["requested_form"],
                "RESULT.json": result, "SHEET.json": result["sheet"], "COMPONENTS.json": result["components"],
                "RECALCULATED_COMPONENTS.json": revised, "MISSING_SOURCE_RESULT.json": missing_result,
                "WRONG_POINTER_RESULT.json": wrong_result,
            }.items():
                write_json(out / filename, value)
            manifest = {}
            for i, (reference, raw) in enumerate(case["artifact_bytes"].items()):
                filename = f"input_{i:03d}.bin"
                (out / filename).write_bytes(raw)
                manifest[reference] = dict(path=filename, sha256=hashlib.sha256(raw).hexdigest(), byte_count=len(raw))
            (out / "retained_request_ref.bin").write_bytes(source.raw)
            (out / "retained_response_artifact_ref.bin").write_bytes(source.snapshot.content)
            write_json(out / "RAW_MANIFEST.json", manifest)
            index = result["sheet"]["input_index_result"]["value"]
            receipt = dict(
                executable=sys.executable, provider_file=provider.__file__, implementation_sha256=implementation_sha256(),
                native_transport="controlled fixture, no live service", scientific_bytes="retained synthetic native-format fixture",
                host_storage="actual Store/Journal/AppServiceRecords/TaskHandoff", source_custody="actual AppServiceCustody.content/evidence",
                pure_constructor="real provider and A/B1/B2/B3/B4; no successful result stubs",
                source_ref=source.task["submission_source_ref"], parameter_pointer=source.evidence["pointer"],
                reference_original_index=index["reference_original_index"], original_input_order=[row["original_index"] for row in index["inputs"]],
                identity_mean=result["facts"]["identity_mean"]["cell"]["value"],
                endpoint_difference_mean=result["facts"]["endpoint_mean"]["cell"]["value"],
                selected_count=result["facts"]["selected"]["cell"]["value"],
                revised_selected_count=revised["value"]["tracks"][0]["selection_counts"]["pass"]["value"],
                unchanged_sheet_digest=revised["value"]["sheet_sha256"] == result["components"]["value"]["sheet_sha256"],
                missing_source_index=missing_result["sheet"]["input_index_result"], missing_source_identity_mean=missing_result["facts"]["identity_mean"]["cell"]["value"],
                wrong_pointer_index=wrong_result["sheet"]["input_index_result"], wrong_pointer_identity_mean=wrong_result["facts"]["identity_mean"]["cell"]["value"],
                submission_transport_calls=len(source.driver.client.calls),
                runtime_observations=source.store.db.execute("SELECT COUNT(*) FROM runtime_observations").fetchone()[0],
                production_applied=False, live_service_verified=False, full_episode_result_binding_verified=False)
            write_json(out / "RECEIPT.json", receipt)
            print(json.dumps(receipt, indent=2))
        finally:
            source.store.close()


if __name__ == "__main__":
    main()
