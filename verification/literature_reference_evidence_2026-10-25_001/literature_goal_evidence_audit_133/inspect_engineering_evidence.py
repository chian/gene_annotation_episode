"""Read-only fixed-goal audit; writes only this new audit's receipts.

No paper bytes, retained scientific packet, model history, source value or
production mutation is read/performed. Existing XML is inspected, not rerun.
"""
from pathlib import Path
import hashlib
import json
import sqlite3
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = HERE.parent
sys.path.insert(0, str(ROOT))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def xml_cases(path):
    rows = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        node = case.attrib["classname"].replace(".", "/") + ".py::" + case.attrib["name"]
        status = "failed" if case.find("failure") is not None or case.find("error") is not None else "skipped" if case.find("skipped") is not None else "passed"
        rows[node] = status
    return rows


coverage = json.loads((BASE / "a106_covariance_meaning_custody_128/REGRESSION_COVERAGE_010.json").read_text())
latest = {}
runs = []
for receipt in coverage["xml_runs"]:
    path = BASE / "a106_covariance_meaning_custody_128" / receipt["xml"]
    rows = xml_cases(path)
    assert digest(path) == receipt["sha256"]
    latest.update(rows)
    runs.append({"xml": str(path.relative_to(ROOT)), "sha256": digest(path), "counts": {s: list(rows.values()).count(s) for s in sorted(set(rows.values()))}})
selected = coverage["per_selected_node_latest"]
assert len({row["nodeid"] for row in selected}) == 433
assert all(latest[row["nodeid"]] == row["status"] == "passed" for row in selected)
hashes = {}
for rel, values in coverage["current_main_approved_hashes"].items():
    actual = digest(ROOT / rel)
    hashes[rel] = {"actual": actual, "approved": values["approved_sha256"], "matches": actual == values["approved_sha256"]}
applied126 = json.loads((BASE / "a108_native_report_reader_126/APPLICATION_001.json").read_text())
hashes126 = {rel: {"approved_after": expected, "actual": digest(ROOT / rel)} for rel, expected in applied126["after"].items()}
assert all(row["approved_after"] == row["actual"] for row in hashes126.values())
assert all(row["matches"] for rel, row in hashes.items() if rel != "gene_annotation_episode/literature_experimental_prompt.py")
manifest130 = json.loads((BASE / "a108_native_parent_review_130/PIN_MANIFEST_001.json").read_text())
assert hashes126["gene_annotation_episode/literature_experimental_prompt.py"]["actual"] == manifest130["files"]["gene_annotation_episode/literature_experimental_prompt.py"]
current130 = xml_cases(BASE / "a108_native_parent_review_130/TESTS_001.xml")
assert len(current130) == 8 and set(current130.values()) == {"passed"}
v125 = json.loads((BASE / "a110_reaction_meanings_125/FINAL_VERIFICATION_001.json").read_text())
checks125 = {}
for row in v125["groups"].values():
    checks125.update(xml_cases(BASE / "a110_reaction_meanings_125" / row["xml"]))
assert len(checks125) == 284 and set(checks125.values()) == {"passed"}

dbpath = BASE / "literature_model_run_030/live_001/state/state.sqlite3"
with sqlite3.connect("file:" + str(dbpath) + "?mode=ro", uri=True) as db:
    db.execute("pragma query_only=1")
    tables = {r[0] for r in db.execute("select name from sqlite_master where type='table'")}
    operations = {}
    for table in sorted(tables):
        if table.startswith("literature_") and (table.endswith("_operations") or table.endswith("_received")):
            operations[table] = db.execute("select count(*) from " + table).fetchone()[0]
    actual_model_metadata = {"path": str(dbpath.relative_to(ROOT)), "query_only": db.execute("pragma query_only").fetchone()[0], "total_changes": db.total_changes,
        "nonempty_literature_tables": {k: v for k, v in operations.items() if v},
        "selected_literature_tool_attempts": db.execute("select json_extract(action,'$.tool'),count(*) from runtime_actions where json_extract(action,'$.kind')='tool' and json_extract(action,'$.tool') like 'literature.%' group by json_extract(action,'$.tool')").fetchall(),
        "limits": "Public selected-tool names/table counts only. No source values, scientific interpretations, private/model request history or backend inference verification."}

from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_context_native_storage import native_observations_schema
state = {"literature_experimental_work": {"version": "literature_experimental_task_v1", "aspect": "source_experimental_evidence"},
    "goal": {"objective": "Examine constructed context evidence."}, "scope": {},
    "literature_assignment": {"version": "literature_assignment_v1", "source_refs": [], "question_context_refs": [],
        "requested_context_components": ["selected_point"], "requested_context_native_positions": [17]},
    "requested_form": {"type": "object", "properties": {"native": native_observations_schema()}, "required": ["native"], "additionalProperties": False}}
text = render_literature_experimental_prompt(state, "Examine only the assigned constructed context question.")
task = text.split("\n\nSTEERING\n", 1)[0]
probe = {"origin": "synthetic_fixture", "model_calls": 0, "source_reads": 0, "production_mutations": 0,
    "selected_position": 17, "requested_context_components_present": "requested_context_components" in task,
    "requested_context_native_positions_present": "requested_context_native_positions" in task,
    "selected_position_token_present": "17" in task,
    "native_contract_present": "observation_position" in task,
    "finding": "The recurring child TASK includes the actual selected native positions." if "requested_context_native_positions" in task else "The actual parent-selected native positions are enforced by the binding but omitted from the recurring child TASK assignment projection; root independently identified this and says pending129 patch repairs it."}
assert probe["requested_context_components_present"] and probe["native_contract_present"]
(HERE / "TASK_POSITION_PROBE_001.json").write_text(json.dumps(probe, indent=2) + "\n")
(HERE / "TASK_POSITION_PROBE_001.txt").write_text(task)
receipt = {"existing_xml_only_no_test_execution": True, "125_distinct_passing": len(checks125), "128_selected_distinct_passing": len(selected),
    "128_deliberately_excluded": coverage["excluded_nodeids"], "128_single_invocation": False, "128_xml_runs": runs,
    "128_current_approved_hashes": hashes, "126_current_applied_after_hashes": hashes126,
    "generation_note": "128 regression evidence predates approved126 prompt extension; current126 after hashes all match and current prompt matches130 verified manifest. Other five128 approved files still match.",
    "130_passing_checks": current130,
    "actual_model_metadata": actual_model_metadata,
    "fixed_goal_path": "/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt",
    "fixed_goal_sha256": digest(Path("/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt")),
    "limitations": "Does not independently verify scientific paper interpretation, all production paths, actual-model backend calls or an entire final combined test suite. Counts are engineering evidence, not completed sheets or independent experiments."}
(HERE / "ENGINEERING_EVIDENCE_001.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"125_distinct_passing": len(checks125), "128_selected_distinct_passing": len(selected), "130_passing": len(current130), "position_probe": probe, "actual_model_metadata": actual_model_metadata}, indent=2))
