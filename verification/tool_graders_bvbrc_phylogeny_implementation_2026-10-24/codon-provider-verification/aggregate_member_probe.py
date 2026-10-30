"""Concrete shared-container-evidence regression; all contents are synthetic."""
import json
import runpy
import sys

from run_tests import HERE, STAGING, establish_overlay

establish_overlay()
test = runpy.run_path(str(STAGING / "tests" / "test_bvbrc_codon_tree_provider.py"))
args = test["fixture"]()
shared = test["evidence"]("synthetic-shared-container", "")
args["inputs"][0]["members"][0]["evidence"] = shared
args["documents"]["parsed"]["store"]["source_records"] = [
    {"source_record_id": "genome-source-" + gid, "subject": {"kind": "genome", "id": gid,
        "source_record_id": "genome-source-" + gid}, "artifact": None, "evidence": [shared],
        "pointer": "/genomes/" + str(i), "source_database": None, "source_version": None}
    for i, gid in enumerate(("G1", "G2"))]
result = test["provider"].extract_codon_tree_sheet(**args)
receipt = {"case": "synthetic_shared_aggregate_evidence_is_not_member_identity", "inputs": args,
    "status": result["status"], "value_present": result["value"] is not None,
    "diagnostics": result["diagnostics"], "expected": "inline G1 remains exact; aggregate SourceRecord evidence adds no genome identity"}
label = sys.argv[1] if len(sys.argv) > 1 else "before"
assert label in {"before", "after"}
(HERE / ("aggregate-member-" + label + ".json")).write_text(json.dumps(receipt, indent=2) + "\n")
if label == "after":
    (HERE / "aggregate-member-after.sheet.json").write_text(json.dumps(result["value"], indent=2) + "\n")
print(json.dumps({k: receipt[k] for k in ("case", "status", "value_present", "diagnostics", "expected")}))
