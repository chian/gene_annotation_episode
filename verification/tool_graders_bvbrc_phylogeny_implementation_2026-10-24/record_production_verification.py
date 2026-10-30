"""Record actual production-module verification without asserting a provider path."""
from pathlib import Path
import hashlib
import importlib
import json
import sys
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
installation = json.loads((HERE / "PRODUCTION_INSTALLATION_001.json").read_text())
files = []
for row in installation["files"]:
    path = ROOT / row["destination"]
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if row["destination"] != "tests/test_phylogeny_calculators.py":
        assert sha == row["sha256"]
    files.append({"path": row["destination"], "sha256": sha})
origins = {}
for name in ("phylogeny_formats", "phylogeny_format_contracts", "phylogeny_calculators",
             "phylogeny_calculation_contracts", "phylogeny_raxml_inputs"):
    module = importlib.import_module("gene_annotation_episode." + name)
    actual = Path(module.__file__).resolve()
    assert actual == ROOT / "gene_annotation_episode" / (name + ".py")
    origins[name] = str(actual)


def suite_result(filename):
    suite = ET.parse(HERE / filename).getroot().find("testsuite")
    return {key: int(suite.attrib[key]) for key in ("tests", "failures", "errors", "skipped")}


before = suite_result("production-shared-tests-001.xml")
after = suite_result("production-shared-tests-002.xml")
# Pytest's XML counts the nine subtests in addition to the 150 test cases.
assert before == {"tests": 159, "failures": 0, "errors": 3, "skipped": 0}
assert after == {"tests": 159, "failures": 0, "errors": 0, "skipped": 0}
report = {
    "scope": "Five installed shared phylogeny modules; format-to-calculator and native-log tests",
    "tests": {"passed": 150, "failed": 0, "errors": 0, "subtests_passed": 9},
    "initial_production_run": {"passed": 147, "failed": 0, "errors": 3,
        "cause": "Calculator native-fixture lookup assumed staging location. Production test now locates the retained repository fixture directory; scientific code and assertions unchanged."},
    "module_origins": origins,
    "files": files,
    "logs": [{"path": str((HERE / name).relative_to(ROOT)),
              "sha256": hashlib.sha256((HERE / name).read_bytes()).hexdigest()}
             for name in ("production-shared-tests-001.log", "production-shared-tests-001.xml",
                          "production-shared-tests-002.log", "production-shared-tests-002.xml")],
    "retained_native_example": {"alignment_rows": 9, "alignment_sites": 15300,
        "cell_count": 137700, "literal_gaps": 17308, "literal_gap_fraction": 17308 / 137700,
        "partition_sites": [3825] * 4, "bootstrap_trees": 100,
        "six_split_frequencies": [1.0] * 6,
        "raxml_final_log_likelihood": -56958.397755,
        "raxml_native_gap_undetermined_percent": 12.57},
    "native_origin": "Retained official repository examples, not new service execution",
    "saved_input_calculations_without_io_tested": True,
    "provider_sheet_assembly_complete": False,
    "selected_tool_to_episode_return_verified": False,
    "live_execution_verified": False,
}
with (HERE / "PRODUCTION_VERIFICATION_001.json").open("x") as stream:
    stream.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
print(json.dumps(report["tests"]))
