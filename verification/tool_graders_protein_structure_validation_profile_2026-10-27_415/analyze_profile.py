"""Reproduce packet415 measured profile tables without importing the workflow."""
from collections import defaultdict
import io
import json
from pathlib import Path
import pstats
import sqlite3
import sys

packet = Path(__file__).resolve().parent
directory = packet / (sys.argv[1] if len(sys.argv) > 1 else "check001")
stats = pstats.Stats(str(directory / "diagnostic.prof"))
rows = []
for (filename, line, name), (primitive, calls, own, cumulative, callers) in stats.stats.items():
    rows.append({"file": filename, "line": line, "name": name,
        "primitive_calls": primitive, "total_calls": calls,
        "self_seconds": own, "cumulative_seconds": cumulative})
summary = {"total_calls": stats.total_calls, "primitive_calls": stats.prim_calls,
    "total_seconds": stats.total_tt,
    "top_cumulative": sorted(rows, key=lambda r: r["cumulative_seconds"], reverse=True)[:40],
    "top_self": sorted(rows, key=lambda r: r["self_seconds"], reverse=True)[:40]}
(directory / "profile_functions.json").write_text(json.dumps(rows, indent=2) + "\n")
(directory / "profile_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
for sort in ("cumulative", "tottime"):
    output = io.StringIO()
    pstats.Stats(str(directory / "diagnostic.prof"), stream=output).sort_stats(sort).print_stats()
    (directory / f"profile_all_{sort}.txt").write_text(output.getvalue())

selected_names = {"plain", "deepcopy", "protein_structure_execution_schema", "_definitions",
    "protein_structure_schema_definitions", "_checked", "validate_protein_structure_job",
    "validate_protein_structure_requested_job", "validate_protein_structure_request",
    "authenticate", "_commission", "completed_receipts", "read_completed",
    "retained_protein_structure_file", "validate_closed_schema", "check_schema",
    "_compile_closed_schema", "_artifact", "_file", "_verify_artifacts", "_bytes",
    "protein_structure_fact_sources", "_schema"}
selected = []
for function, values in stats.stats.items():
    if function[2] in selected_names:
        selected.append({"function": function, "stats": values[:4],
            "callers": [{"function": caller, "stats": measurement}
                for caller, measurement in sorted(values[4].items(), key=lambda r: r[1][3], reverse=True)]})
(directory / "selected_callers.json").write_text(json.dumps(selected, indent=2) + "\n")

# These groups sum exclusive function time only; they do not pretend that a
# containing authority/validation call is independent of its copying children.
categories = defaultdict(lambda: {"self_seconds": 0.0, "calls": 0, "functions": []})
for row in rows:
    filename, name = row["file"], row["name"]
    if "/jsonschema/" in filename or "/referencing/" in filename:
        category = "jsonschema_and_referencing_own_function_time"
    elif filename.endswith("/copy.py"):
        category = "stdlib_copy_own_function_time"
    elif filename.endswith("/communication.py") and name == "plain":
        category = "communication_plain_own_function_time"
    elif "/json/" in filename:
        category = "stdlib_json_own_function_time"
    elif filename.endswith("/episode_return_records.py") and name in {"equal", "<genexpr>"}:
        category = "typed_return_tree_equality_own_function_time"
    elif filename == "~" and ("sqlite3" in name or "_sqlite3" in name):
        category = "sqlite_own_function_time"
    elif filename == "~" and (name.startswith("<built-in method posix.")
            or name in {"<built-in method _io.open>", "<built-in method _io.open_code>"}
            or ("_io." in name and ("'read'" in name or "'write'" in name or "'readlines'" in name))):
        category = "selected_os_and_io_own_function_time_including_imports_copy_and_controls"
    else:
        category = "other_own_function_time"
    bucket = categories[category]
    bucket["self_seconds"] += row["self_seconds"]
    bucket["calls"] += row["total_calls"]
    bucket["functions"].append({"file": filename, "line": row["line"], "name": name})
for bucket in categories.values():
    bucket["percent_of_total_self"] = 100 * bucket["self_seconds"] / stats.total_tt
(directory / "profile_exclusive_categories.json").write_text(json.dumps(categories, indent=2) + "\n")

database = directory / "diagnostic-state/state.sqlite3"
connection = sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True)
connection.row_factory = sqlite3.Row
action = connection.execute("SELECT * FROM runtime_actions WHERE json_extract(action,'$.tool')="
    "'execution.results.collect' ORDER BY rowid LIMIT 1").fetchone()
form = json.loads(connection.execute("SELECT form FROM runtime_forms WHERE episode_id=?",
    (action["episode_id"],)).fetchone()[0])
request = json.loads(connection.execute("SELECT request FROM runtime_episodes WHERE episode_id=?",
    (action["episode_id"],)).fetchone()[0])
outcome = json.loads(action["result"])
receipt = outcome["result"]
native_file = receipt["body"]["qualified_files"]["native_file"]
descriptor, = form["sequences"]
inputs = {"episode_role": "results", "native_operation": receipt["body"]["bundle"]["requested_job"]["native_protein_structure"]["request"]["operation"],
    "report_fields": list(form), "completed": form["completed"], "failure_count": len(form["failures"]),
    "sequence_descriptor_count": len(form["sequences"]), "sequence_length": descriptor["sequence_length"],
    "scientific_files_checked": {"native_file": native_file,
        **{name: descriptor[name] for name in ("sequence_file", "residue_map_file", "structure_file")}},
    "request_json_bytes_compact": len(json.dumps(request, separators=(",", ":")).encode()),
    "report_schema_json_bytes_compact": len(json.dumps(request["report_contract"]["measurements"]["schema"], separators=(",", ":")).encode()),
    "form_json_bytes_compact": len(json.dumps(form, separators=(",", ":")).encode())}
connection.close()
(directory / "retained_input_summary.json").write_text(json.dumps(inputs, indent=2) + "\n")
print(json.dumps({"total_calls": stats.total_calls, "primitive_calls": stats.prim_calls,
    "total_self_seconds": stats.total_tt,
    "exclusive_groups": {k: {n: v for n, v in b.items() if n != "functions"} for k, b in categories.items()},
    "scientific_file_bytes": sum(v["byte_length"] for v in inputs["scientific_files_checked"].values())}, indent=2))
