"""Metadata-only copy of retained C/B fixtures; performs no scientific work."""
from pathlib import Path
import hashlib
import json

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
SOURCE = REPO / "verification/tool_graders_protein_structure_execution_2026-10-27_390"
CALCULATIONS = REPO / "verification/tool_graders_protein_structure_calculations_2026-10-27_389/examples"
DESTINATION = PACKET / "fixtures"
DESTINATION.mkdir(exist_ok=True)
rows = []


def retain(label, source, raw=None, note="unchanged original bytes"):
    original = source.read_bytes()
    raw = original if raw is None else raw
    target = DESTINATION / (label + ".json")
    if target.exists():
        assert target.read_bytes() == raw
    else:
        with target.open("xb") as stream:
            stream.write(raw)
    rows.append({"label": label, "original_path": str(source.relative_to(REPO)),
        "original_sha256": hashlib.sha256(original).hexdigest(), "original_byte_length": len(original),
        "retained_path": str(target.relative_to(PACKET)), "retained_sha256": hashlib.sha256(raw).hexdigest(),
        "retained_byte_length": len(raw), "copy_operation": note,
        "qualification": "synthetic_native_format_engineering_fixture_not_biological_measurement"})


base = SOURCE / "check007/temporary/pytest"
retain("inspect", base / "test_actual_supplied_byte_work0/inspect-native.json")
retain("extract", base / "test_actual_supplied_byte_work1/extract_sequence-native.json")
for row in json.loads((SOURCE / "FILLED_NATIVE_EXAMPLES_001.json").read_bytes()):
    name = row["native_result_path"]
    label = ("held_out" if "/held-out/" in name else "supplied" if "/supplied/" in name
             else "zero_available" if "test_actual_partial_science" in name else "mixed_partial")
    retain(label, SOURCE / name)
paths = list((base / "test_unavailable_sequence_is_a0").rglob("result.json"))
assert len(paths) == 1
retain("extract_unavailable", paths[0])
retain("saved_sheet", CALCULATIONS / "held_out_saved_sheet.json")
source = CALCULATIONS / "held_out_components.json"
values = json.loads(source.read_bytes())
raw = json.dumps(values["one"], sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
retain("original_components", source, raw, "select unchanged original one record and serialize canonical UTF-8; no calculation")
provenance = {"version": "result_worker_fixture_provenance_v1", "records": rows}
target = PACKET / "FIXTURE_PROVENANCE_001.json"
raw = json.dumps(provenance, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
if target.exists():
    assert target.read_bytes() == raw
else:
    target.write_bytes(raw)
print(json.dumps({"retained_fixture_count": len(rows), "path": str(target)}))
