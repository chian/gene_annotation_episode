"""Record existing test receipts and original example bytes; run no science."""
from pathlib import Path
import hashlib
import json

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]


def read(path):
    return json.loads(path.read_bytes())


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw)}


def write(name, value):
    with (PACKET / name).open("x") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")


expected = {
    "check001": (1, "3 failed, 29 passed"),
    "check002": (1, "1 failed, 43 passed"),
    "check003": (0, "44 passed"),
    "check004": (2, "1 error"),
    "check005": (1, "39 failed, 379 passed"),
    "check006": (1, "2 failed, 416 passed"),
    "check007": (0, "2 passed"),
    "check008": (0, "1 passed"),
}
attempts = []
for check, (returncode, summary) in expected.items():
    directory = PACKET / check
    receipt = read(directory / "receipt.json")
    assert receipt["returncode"] == returncode
    assert receipt["executed_source_pins_unchanged"] is True
    assert receipt["metadata"]["policy"] == {"memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}
    stdout = (directory / "stdout.txt").read_text()
    assert summary in stdout
    attempts.append({"check": check, "summary": stdout.strip().splitlines()[-1],
        "receipt": pin(directory / "receipt.json"), "stdout": pin(directory / "stdout.txt"),
        "executed_before": pin(directory / "source_pins_before.json"),
        "executed_after": pin(directory / "source_pins_after.json"),
        "checkout_source_drift": receipt["checkout_source_drift"]})

forms = list((PACKET / "check008/temporary").rglob("filled-form.json"))
assert len(forms) == 1
raw = forms[0].read_bytes()
with (PACKET / "FILLED_FORM_EXAMPLE_001.json").open("xb") as handle:
    handle.write(raw)
example = read(forms[0])
assert set(example["form"]) == {"the_comparison", "reuse_later", "selected_sequence", "unavailable"}
cells = example["form"]["the_comparison"][0]["delivery"]["rows"][0]["values"]
display = [{"field": cell["field"], "value": cell["value"]["value"], "unit": cell["value"]["unit"],
    "population": cell["population"]} for cell in cells]
write("FILLED_FORM_PROVENANCE_001.json", {"original": pin(forms[0]),
    "copied_unchanged": pin(PACKET / "FILLED_FORM_EXAMPLE_001.json"),
    "origin": "Actual expand_fact_form, saved-form validation and typed-form admission in check008; synthetic custody, retained393 native measurements; no original runtime authority claim.",
    "selected_numbers": display, "model_prompt": False})

owned = ["gene_annotation_episode/protein_structure_authority.py",
    "gene_annotation_episode/protein_structure_selection.py",
    "gene_annotation_episode/protein_structure_publication.py",
    "gene_annotation_episode/communication.py", "tests/test_protein_structure_selection.py",
    "tests/test_protein_structure_publication.py", "tests/test_protein_structure_form_boundary.py",
    "tests/test_native_blast_fact_forms.py"]
pins = {}
for check in ("check003", "check006", "check007", "check008"):
    manifest = {row["path"]: row for row in read(PACKET / check / "source_pins_before.json")}
    pins[check] = [manifest[path] for path in owned if path in manifest]
write("SOURCE_PINS_001.json", {"tested_snapshot_pins": pins,
    "note": "check003 precedes the communication edit.400 later owns publication extensions; these pins claim only the original pure payload. check008 changes the form test solely to retain its admitted example."})
write("VERIFICATION_001.json", {"schema": "protein_structure_shared_boundary_verification_v1",
    "attempts": attempts, "selector_and_source_payload_checks": 44,
    "form_and_regression_checks": 418, "form_and_regression_basis": "416 passes in check006 plus its two fixture-data failures passed in check007; no shared production-code change between those snapshots.",
    "example_capture_repeat": {"check": "check008", "passed": 1, "additional_unique_cases": 0},
    "scope": "Pure selectors/source payload, structured error, exact registered form resources and existing communication regressions.",
    "not_verified": ["original protein result runtime authority", "selected resource to receiving episode integration", "scientific or annotation credit", "protein prompt templates", "new protein tool acceptance"],
    "remaining_tools_outside_tally": 196, "numerical_grader_progress_tally": 112})
print(json.dumps({"attempts_retained": len(attempts), "selector_payload_passes": 44,
    "form_regression_distinct_passes": 418, "selected_numbers": display,
    "tally": "112/308"}))
