"""Independently repeat audit041 in a fresh parent-owned synthetic Store.

No existing audit files or live runs are modified. This checks the existing
adapter defect, not primary-source science or full method_loop execution.
"""
import hashlib
import json
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
SCRIPT = BASE / "a105_grader_coverage_041/reproduce_subset_expansion.py"
EXPECTED = "54027c865772d2904d0cf6cb19f3307690bb9521401df71ebb1908a0b6bc2747"


def main():
    assert hashlib.sha256(SCRIPT.read_bytes()).hexdigest() == EXPECTED
    modules = ("literature_rate_storage.py", "literature_episodes.py",
               "literature_optical_storage.py")
    package = Path(__file__).resolve().parents[3] / "gene_annotation_episode"
    before = {name: hashlib.sha256((package / name).read_bytes()).hexdigest()
              for name in modules}
    target = runpy.run_path(str(SCRIPT))["main"]
    target.__globals__["HERE"] = HERE
    target()
    assert before == {name: hashlib.sha256((package / name).read_bytes()).hexdigest()
                      for name in modules}
    receipt = {
        "status": "reproduced", "synthetic_only": True,
        "original_audit_script_sha256": EXPECTED,
        "shared_source_sha256": before,
        "shared_sources_unchanged": True,
        "model_calls": 0, "full_method_loop_run": False,
        "scope": "Actual selected rate operation and trusted manual subset admission; source IO and calculation forbidden during projection",
    }
    with (HERE / "BASELINE_RECEIPT.json").open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
