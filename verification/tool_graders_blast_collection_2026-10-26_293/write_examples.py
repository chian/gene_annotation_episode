"""Offline evidence export; this script is run through local_jobs."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.blast_report_collection import parse_blast_report_collection

PACKET = Path(__file__).resolve().parent


def save(path, value):
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


native = json.loads((PACKET / "native_fixtures/manifest.json").read_text())
summaries = []
for row in native:
    raw = (ROOT / row["path"]).read_bytes()
    result = parse_blast_report_collection({"report": raw}, artifacts=[row["artifact"]], invocation=row["invocation"])
    save(PACKET / "filled_native" / (row["name"] + ".json"), result)
    item = result["searches"][0]
    summaries.append({"name": row["name"], "search_key": item["search_key"],
        "native_hits": item["reporting"]["native_hit_count"], "original_rows": item["row_map"],
        "reported_query_length": item["normalized"]["query"]["length"],
        "bound_query_length": item["operand_binding"]["length"] if item["operand_binding"] else None,
        "issues": [issue["code"] for issue in item["issues"]]})

source = next(row for row in native if row["name"] == "blastp_gaps_json15")
body = json.loads((ROOT / source["path"]).read_bytes())
report = body["BlastOutput2"][0]["report"]
search = report["results"]["bl2seq"][0]
invocation = deepcopy(source["invocation"])
invocation.update(execution_program="psiblast", scientific_mode="database", resource_kind="hpc")
invocation["request"] = {"fixture_kind": "synthetic_format_and_partial_data_example"}
invocation["completion"] = {"native_returncode": 2, "producer_complete": False}
report.update(program="psiblast", version="PSIBLAST 2.17.0+", search_target={"db": "synthetic_db"})
bad_search = deepcopy(search)
bad_search["hits"].insert(0, "deliberately malformed native hit")
bad_search["hits"][1]["hsps"].insert(0, None)
report["results"] = {"iterations": [{"iter_num": 1, "search": search}, None,
    {"iter_num": 3, "search": bad_search}]}
raw = json.dumps(body, indent=2).encode()
(PACKET / "filled_synthetic").mkdir(exist_ok=True)
(PACKET / "filled_synthetic/multi_round_partial.native.json").write_bytes(raw)
collection = parse_blast_report_collection({"report": raw}, artifacts=[source["artifact"]], invocation=invocation)
save(PACKET / "filled_synthetic/multi_round_partial.collection.json", collection)

paths = [
    ROOT / "gene_annotation_episode/blast_program_context.py",
    ROOT / "gene_annotation_episode/blast_report_collection.py",
    ROOT / "gene_annotation_episode/blast_grading_inputs.py",
    ROOT / "gene_annotation_episode/blast_search.py",
    ROOT / "tests/test_blast_program_context.py",
    ROOT / "tests/test_blast_report_collection.py",
    ROOT / "verification/tool_graders_blast_programs_2026-10-26_292/CONTRACT_001.md",
    ROOT / "verification/tool_graders_blast_programs_2026-10-26_292/CONTRACT_ADDENDUM_002.md",
    ROOT / "verification/tool_graders_blast_programs_2026-10-26_292/CONTRACT_ADDENDUM_003.md",
    ROOT / "verification/w04_blast_graders_2026-10-24_001/live_api/result.body",
    Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt"),
]
save(PACKET / "SOURCE_HASHES.json", {"captured_utc": datetime.now(timezone.utc).isoformat(),
    "files": [{"path": str(path), "size_bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in paths]})
save(PACKET / "EXAMPLE_SUMMARY.json", summaries)
for row in summaries:
    if row["name"] in ("blastp_gaps_json15", "blastp_multiple_hsps_tabular7", "blastn_range_forward_json15", "blastn_no_hits_tabular6"):
        print(json.dumps(row))
print("Saved 20 complete native collections and a separately labeled synthetic partial iterative collection.")
