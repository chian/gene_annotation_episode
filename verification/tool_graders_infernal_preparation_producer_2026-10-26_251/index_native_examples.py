"""Index retained native producer evidence without modifying an original attempt."""
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.native_infernal_preparation_driver import validate_preparation_bundle_files

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SUITE = HERE / "producer_003"


def file_record(path):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


cases = []
for path in sorted((SUITE / "temporary/pytest").rglob("bundle.json")):
    bundle = json.loads(path.read_bytes())
    if (bundle.get("version") != "native_infernal_preparation_bundle_v1"
            or bundle.get("software", {}).get("declared_engine_version") != "1.1.5"):
        continue
    validate_preparation_bundle_files(bundle, path.parent)
    owner = path.parent / ".native-infernal-preparation-owner.json"
    cases.append({"program": bundle["program"], "mode": bundle["mode"],
        "returncode": bundle["returncode"], "failure_codes": [f["code"] for f in bundle["failures"]],
        "bundle": file_record(path), "plan": file_record(owner),
        "inputs": [{"role": row["role"], "ordinal": row["ordinal"], "artifact_ref": row["artifact_ref"],
            "expected_sha256": row["expected_sha256"], "staged_sha256": row["staged_sha256"],
            "final_sha256": row["final_sha256"], "file": file_record(path.parent / row["relative_path"])}
            for row in bundle["inputs"] if row["final_sha256"] is not None],
        "working_copies": [{"operand_role": row["operand_role"], "operand_ordinal": row["operand_ordinal"],
            "mutable": row["mutable"], "initial_sha256": row["initial_sha256"], "final_sha256": row["final_sha256"],
            "file": file_record(path.parent / row["relative_path"])}
            for row in bundle["working_copies"] if row["final_sha256"] is not None],
        "outputs": [{"role": row["role"], "format": row["format"],
            "file": file_record(path.parent / row["relative_path"])} for row in bundle["artifacts"]]})

reservations = []
for path in sorted((SUITE / "temporary/pytest").rglob("execution-target.json")):
    target = json.loads(path.read_bytes())
    action = Path(target["execution_id"]).parent
    plan_path = action / "infernal-preparation-plan.json"
    plan = json.loads(plan_path.read_bytes())
    bundle_path = Path(plan["attempt_directory"]) / "bundle.json"
    bundle = json.loads(bundle_path.read_bytes())
    case = "calibration_failure" if bundle["returncode"] else bundle["mode"]
    reservations.append({"case": case, "program": bundle["program"], "mode": bundle["mode"],
        "returncode": bundle["returncode"], "target": file_record(path),
        "assignment": file_record(path.with_name("assignment.json")), "plan": file_record(plan_path),
        "bundle": file_record(bundle_path), "native_handle": file_record(action / "native.json"),
        "native_receipt": file_record(path.with_name("native-lifecycle-receipt.json"))})

result = {"version": "infernal_preparation_producer_native_examples_v1",
    "qualification": "Actual selected local native commands under 20 GiB RAM and 4 GiB scratch with no wall cap. Direct producer cases and four genuine local reservations are recorded separately; no episode-path completion is asserted.",
    "suite_receipt": file_record(SUITE / "receipt.json"), "cases": cases, "reservations": reservations}
(HERE / "NATIVE_PRODUCER_INDEX_001.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps({"native_bundles": len(cases), "reservations": [r["case"] for r in reservations]}))
