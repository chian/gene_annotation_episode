"""Retain full parser outputs and an independent native single-display check."""
from pathlib import Path
import hashlib
import json
import re

from gene_annotation_episode.rfam_batch_alignment import parse_rfam_alignment_display


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def digest(content):
    return hashlib.sha256(content).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def summarize(name, result):
    return dict(name=name, status=result["status"], model_from=result["display_model_from"],
        model_to=result["display_model_to"], query_from=result["display_query_from"], query_to=result["display_query_to"],
        query_strand=result["query_strand"], represented_model_positions=sum(b-a for a,b in result["aligned_model_intervals"]),
        represented_query_positions=sum(b-a for a,b in result["aligned_query_intervals"]),
        model_consensus_compared_count=result["model_consensus_compared_count"],
        model_consensus_equal_count=result["model_consensus_equal_count"], query_insert_count=result["query_insert_count"],
        model_delete_count=result["model_delete_count"], truncated_model_count_5p=result["truncated_model_count_5p"],
        truncated_model_count_3p=result["truncated_model_count_3p"], local_end_model_omitted_count=result["local_end_model_omitted_count"],
        local_end_query_count=result["local_end_query_count"], posterior_segment_count=len(result["posterior_segments"]),
        issue_codes=[issue["code"] for issue in result["issues"]])


def main():
    output = Path.cwd() / "examples"
    output.mkdir()
    summaries, provenance = [], []
    sources = [
        ("official-documentation-single", ROOT / "verification/tool_graders_rfam_contract_2026-10-26_232/examples/official-single-result.json",
         "official_documentation_example"),
        ("live-single", ROOT / "verification/tool_graders_rfam_transport_2026-10-26_234/live/single/003-fetch-json/response.body",
         "native_response"),
    ]
    for label, path, kind in sources:
        body = path.read_bytes()
        data = json.loads(body)
        row = data["hits"]["5S_rRNA"][0]
        artifact = "example:" + label
        identity = {"artifact_ref": artifact, "hit_key": artifact + "/hits/5S_rRNA/0",
                    "query_occurrence_key": "example:" + label + ":original-occurrence", "family_accession": row["acc"]}
        result = parse_rfam_alignment_display(row["alignment"], hit_identity=identity, query_sequence=data["searchSequence"],
            native_start=row["start"], native_end=row["end"], native_strand=row["strand"])
        bundle = {"version": "rfam_alignment_components_bundle_v1", "artifact_ref": artifact,
                  "source_sha256": digest(body), "rows": [result]}
        save(output / (label + ".components.json"), bundle)
        summaries.append(summarize(label, result))
        provenance.append({"name": label, "evidence_kind": kind, "source_path": str(path.relative_to(ROOT)),
                           "source_sha256": digest(body), "artifact_refs_are_example_scope": True})
        if label == "live-single":
            # Independent, limited reference calculation for these actual
            # unabridged strings only: prefix counts, not the production walk.
            model = re.fullmatch(r"#CM 1 (\S+) 120", row["alignment"]["hit_seq"])[1]
            query = re.fullmatch(r"#SEQ 1 (\S+) 119", row["alignment"]["user_seq"])[1]
            assert len(model) == len(query) == 121
            columns = [{"display_column_0i": i,
                "model_position_0i": None if m == "." else i - model[:i].count("."),
                "query_position_0i": None if q == "-" else i - query[:i].count("-"),
                "model_symbol": m, "query_symbol": q,
                "canonical_equal": m.upper().replace("T", "U") == q.upper().replace("T", "U") if m != "." and q != "-" else None}
                for i, (m, q) in enumerate(zip(model, query))]
            compared = sum(c["canonical_equal"] is not None for c in columns)
            equal = sum(c["canonical_equal"] is True for c in columns)
            assert (compared, equal) == (118, 75)
            assert [c["query_position_0i"] for c in columns if c["model_symbol"] == "."] == [101]
            assert [c["model_position_0i"] for c in columns if c["query_symbol"] == "-"] == [40, 109]
            assert compared == result["model_consensus_compared_count"] and equal == result["model_consensus_equal_count"]
            assert [{"model_position": c["model_position_0i"], "query_position": c["query_position_0i"],
                     "consensus_symbol": c["model_symbol"], "query_symbol": c["query_symbol"]}
                    for c in columns if c["canonical_equal"] is not None] == result["paired_positions"]
            save(output / "live-single-independent-column-check.json", {
                "method": "Native unabridged display columns; coordinates by explicit prefix gap counts; canonical T/U comparison.",
                "source_sha256": digest(body), "compared": compared, "equal": equal, "columns": columns})
    for path in sorted((HERE / "fixtures").glob("*.json")):
        fixture = json.loads(path.read_bytes())
        result = parse_rfam_alignment_display(fixture["alignment"], **{key: fixture[key] for key in
            ("hit_identity", "query_sequence", "native_start", "native_end", "native_strand")})
        save(output / (path.stem + ".components.json"), result)
        summaries.append(summarize(path.stem, result))
        provenance.append({"name": path.stem, "evidence_kind": fixture["fixture_kind"], "fixture_sha256": digest(path.read_bytes()),
            "fixture_path": str(path.relative_to(ROOT)), "native_source_sha256": fixture["source"]["sha256"],
            "not_a_production_json_report_binding": True})
    save(output / "summary.json", summaries)
    save(output / "provenance.json", provenance)
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
