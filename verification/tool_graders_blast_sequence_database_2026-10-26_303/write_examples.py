"""Complete saved sheets/components; no tool execution or network acquisition."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from test_blast_sequence_database import inputs, collect, document, invocation, native_search, retained_api_inputs
from gene_annotation_episode.blast_sequence_database import populate_blast_sequence_database_sheet as populate
from gene_annotation_episode.blast_sequence_database import calculate_blast_sequence_database_components as calculate
from gene_annotation_episode.blast_report_collection import parse_blast_report_collection
from gene_annotation_episode.blast_pairwise_grader import alignment_components

DIRECTORY = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).parent
EXAMPLES = DIRECTORY / "examples"
EXAMPLES.mkdir(exist_ok=False)


def save(name, value):
    path = EXAMPLES / name
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    return str(path.relative_to(ROOT))


summary = []
cases = [("synthetic_sequence", inputs(), "synthetic PSI sequence database report and all supplied metadata")]
for kind in ("pssm", "msa"):
    cases.append(("synthetic_"+kind, inputs(collect(inv=invocation(query_kind=kind))["searches"][0]),
                  "synthetic PSI master coordinates; no biological sequence publication"))
partial = native_search()
partial["hits"][0]["hsps"].insert(0, None)
cases.append(("synthetic_partial_hsp", inputs(collect(document(search=partial))["searches"][0]), "synthetic malformed first HSP"))
unknown = inputs(collect(document("deltablast"), invocation("deltablast"))["searches"][0])
unknown["search_binding"]["stage"] = None
cases.append(("synthetic_delta_unknown_stage", unknown, "synthetic DELTA unresolved stage; no sequence weights"))
cases.append(("retained_ncbi_api", retained_api_inputs(), "unaltered retained NCBI API archive; explicit absent query/function/census bindings"))
for name, arguments, evidence in cases:
    sheet = populate(**arguments)
    components = calculate(sheet)
    saved = save(name+".sheet.json", sheet)
    calculated = save(name+".components.json", components)
    changed = calculate(json.loads(json.dumps(sheet)), model={"temperature_bits":2})
    save(name+".temperature2.components.json", changed)
    database = components["components"]["database_sheet"]
    weights = components["components"]["function_weights"]
    summary.append(dict(name=name, evidence=evidence, sheet=saved, components=calculated, status=components["status"],
        hits=len(database["hits"]) if database else None,
        bit_scores=[h["measurements"]["maximum_bit_score"] for h in database["hits"]] if database else None,
        function_weights=weights["unadjusted_probabilities"] if weights else None,
        selected_coverage=components["components"]["selected_query_coverage"]))

# These bytes came from real paired runs. They exercise shared geometry only;
# their mode is preserved and they never enter the sequence-population adapter.
manifest_path = ROOT / "verification/tool_graders_blast_collection_2026-10-26_293/native_fixtures/manifest.json"
native_summary = []
for case in json.loads(manifest_path.read_text()):
    raw = (ROOT / case["path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == case["sha256"]
    collection = parse_blast_report_collection({case["artifact"]["artifact_key"]: raw},
        artifacts=[case["artifact"]], invocation=case["invocation"])
    subject = next(row for row in case["invocation"]["operands"] if row["role"] == "subject")
    calculations = []
    for search in collection["searches"]:
        query = search["operand_binding"]
        calculations.append(dict(search_key=search["search_key"], hits=[dict(hit_index=hit["hit_index"],
            hsps=[alignment_components(hsp, program=search["program_context"]["geometry_program"],
                query_length=query["length"] if query else None, reference_length=subject["length"],
                coordinate_convention="blast_json2" if search["normalized"]["format"] == "json2" else "directional")
                for hsp in hit["hsps"]]) for hit in search["normalized"]["hits"]]))
    path = save("retained_paired/"+case["name"]+".json", dict(evidence="authentic retained paired bytes; shared geometry only",
        native_source=case["path"], sha256=case["sha256"], collection=collection, components=calculations))
    native_summary.append(dict(name=case["name"], source=case["path"], sha256=case["sha256"], example=path))
(DIRECTORY / "EXAMPLE_SUMMARY.json").write_text(json.dumps(dict(sequence_database=summary, retained_paired=native_summary), indent=2)+"\n")
print(json.dumps({"saved_sequence_examples":len(cases), "retained_paired_geometry_examples":len(native_summary), "summary":str(DIRECTORY / "EXAMPLE_SUMMARY.json")}))
