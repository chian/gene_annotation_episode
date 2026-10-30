"""Collect already executed verification receipts and selected numerical examples."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET

from gene_annotation_episode.state import Store

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = Path(__file__).resolve().parent
tests = []
for label in ("002", "003", "004", "005"):
    receipt = json.loads((DIRECTORY / ("TEST_RECEIPT_" + label + ".json")).read_text())
    suite = ET.parse(DIRECTORY / ("tests_" + label + ".xml")).getroot().find("testsuite")
    tests.append({"label": label, "command": receipt["command"], "returncode": receipt["returncode"],
        "counts": dict(suite.attrib), "policy": receipt["metadata"]["policy"],
        "enforcement": receipt["metadata"]["enforcement"],
        "verified_cgroup": receipt["metadata"].get("verified_cgroup")})
examples = []
for index in range(6):
    case = DIRECTORY / "run_004/pytest" / ("test_native_five_families_and_" + str(index))
    grading = case / "grading/native-infernal-grading"
    plan = json.loads((grading / "plan.json").read_text())
    prepared = json.loads((grading / "prepared.json").read_text())
    selected = json.loads((grading / "selected-rows.ndjson").read_text().splitlines()[0])
    with Store(case / "store") as store:
        source = next(r for r in store.list("source") if r["provider"] == "episode.execution_result")
        observations = store.list("observation")
        references = [r for r in store.list("reference") if r["source_ref"] == source["id"]]
    examples.append({"program": plan["bundle"]["program"], "family": selected["family"],
        "record_key": selected["record_key"], "source_ref": source["id"],
        "observation_ref": observations[0]["id"] if observations else None,
        "reference_refs": [r["id"] for r in references],
        "measurements": selected["measurements"], "unavailable": selected["unavailable"],
        "subject_intervals": selected["subject_intervals"],
        "original_sequence_sha256": (selected["subject_operand"] or {}).get("sequence_sha256"),
        "prepared": prepared, "native_output_hashes": plan["bundle"]["artifacts"],
        "original_input_hashes": plan["bundle"]["inputs"]})
code_paths = ["gene_annotation_episode/native_infernal_result_publication.py",
    "tests/test_native_infernal_publication.py", "gene_annotation_episode/native_infernal_result_worker.py",
    "gene_annotation_episode/native_infernal_contracts.py", "gene_annotation_episode/infernal_native_result_views.py",
    "gene_annotation_episode/domain.py", "gene_annotation_episode/state.py"]
report = {"version": "infernal_publication_225_verification_v1", "tests": tests,
    "scope": "Retained real native outputs, explicit synthetic bindings/faults, actual bounded grading subprocess and Store publication. No native Infernal rerun, model call, network acquisition, new score or controller work.",
    "initial_launcher_failure": {"label": "001", "code": "local_job_output_must_be_in_job_directory",
        "test_process_started": False, "repair": "Put test stdout/stderr under its selected working directory."},
    "first_full_failure": "003 had 12 passing and 12 failing tests because root-owned Store measurement enum omitted Infernal quantities. Root added the exact metric names; 004 passed all 27 tests.",
    "final_followup": "005 passed four targeted tests after immutable receipt and source-version validation hardening; these overlap 004 and are not four additional unique cases.",
    "code_sha256": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in code_paths},
    "native_fixture_sha256": json.loads((ROOT / "tests/fixtures/native_infernal_publication/NATIVE_SHA256.json").read_text()),
    "examples": examples,
    "remaining_integration": "Root owns original capture/results operation and authenticated parent/grandparent returns, practical completion and credit. This workload does not claim a live new native run, configured-model episode, remote/HPC execution, literature grading or W05."}
(DIRECTORY / "VERIFICATION_RECEIPT.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"examples": len(examples), "report": str(DIRECTORY / "VERIFICATION_RECEIPT.json"),
    "tests": [{"label": t["label"], "counts": t["counts"]} for t in tests]}, indent=2))
