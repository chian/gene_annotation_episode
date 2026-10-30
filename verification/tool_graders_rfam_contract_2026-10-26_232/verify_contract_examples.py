"""Check this planning packet's fixture bytes and elementary expected arithmetic.

This deliberately does not import a production Rfam reader, grader or service.
It is not evidence of implemented parsing, live execution or episode integration.
"""
from pathlib import Path
import hashlib
import json


ROOT = Path(__file__).resolve().parent
EXAMPLES = ROOT / "examples"


def read(name):
    return json.loads((EXAMPLES / name).read_bytes())


def digest(value):
    # Same encoding as execution_contracts.canonical; all current example text
    # is ASCII, so the domain.canonical encoding yields the same bytes here.
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main():
    manifest = read("fixture-manifest.json")
    for item in manifest:
        data = (EXAMPLES / item["file"]).read_bytes()
        assert len(data) == item["byte_length"]
        assert hashlib.sha256(data).hexdigest() == item["sha256"]
        assert item["successful_live_capture"] is False
    native_bytes = (EXAMPLES / "official-single-result.json").read_bytes()
    rst = (ROOT / "source_evidence/rfam-docs-api.rst").read_bytes()
    assert native_bytes in rst
    native = read("official-single-result.json")
    identity = read("single-input-identity.json")
    query = native["searchSequence"]
    assert len(query) == 119 == identity["submitted_length_nt"]
    assert hashlib.sha256(query.encode("ascii")).hexdigest() == identity["submitted_sequence_sha256"]
    assert query == identity["submitted_sequence"]
    assert native["jobId"] == identity["expected_job_id"]
    hit = native["hits"]["5S_rRNA"][0]
    assert (hit["score"], hit["E"], hit["GC"]) == (104.9, 4.5e-24, 0.49)
    span = abs(hit["end"] - hit["start"]) + 1
    assert span == 119 and span / len(query) == 1.0
    assert sum(symbol in "GC" for symbol in query) == 58
    model = hit["alignment"]["hit_seq"].split()[2].upper().replace("T", "U")
    displayed = hit["alignment"]["user_seq"].split()[2].upper().replace("T", "U")
    assert len(model) == len(displayed) == 119
    assert displayed == query.replace("T", "U")
    assert sum(a == b for a, b in zip(model, displayed)) == 79

    empty = read("synthetic-empty.json")
    assert empty["numHits"] == 0 and empty["hits"] == {}
    assert empty["searchSequence"] == query and empty["jobId"] == native["jobId"]
    partial = read("synthetic-partial.json")
    rows = partial["hits"]["5S_rRNA"]
    assert partial["numHits"] == len(rows) == 3
    assert rows[0] == hit and rows[1]["end"] == 120 > len(query)
    assert (rows[2]["start"], rows[2]["end"], rows[2]["strand"]) == (110, 10, "-")
    reverse_span = abs(rows[2]["end"] - rows[2]["start"]) + 1
    assert reverse_span == 101
    assert rows[2]["alignment"] == hit["alignment"]  # deliberate conflict
    duplicate = read("synthetic-duplicate-hits.json")
    assert duplicate["numHits"] == 2
    assert duplicate["hits"]["5S_rRNA"] == [hit, hit]
    duplicate_sum, duplicate_union = 2 * span, span
    assert (duplicate_sum, duplicate_union, duplicate_sum - duplicate_union) == (238, 119, 119)

    assert read("synthetic-conflicting-job.json")["jobId"] != native["jobId"]
    changed = read("synthetic-conflicting-sequence.json")["searchSequence"]
    assert len(changed) == len(query) and changed != query
    assert read("synthetic-conflicting-count.json")["numHits"] == 2
    assert len(read("synthetic-conflicting-count.json")["hits"]["5S_rRNA"]) == 1
    assert read("synthetic-conflicting-strand.json")["hits"]["5S_rRNA"][0]["strand"] == "-"
    assert isinstance(read("synthetic-untyped-multiple-envelope.json")["hits"], list)
    assert "<[30]*" in read("synthetic-unsupported-display.json")["hits"]["5S_rRNA"][0]["alignment"]["hit_seq"]

    sheet = read("proposed-single-sheet.json")
    calculation = read("proposed-single-calculation.json")
    assert sheet["source"]["evidence_kind"] == "official_documentation_example"
    assert sheet["source"]["http_status"] is None
    assert sheet["source"]["source_sha256"] == hashlib.sha256(native_bytes).hexdigest()
    assert calculation["sheet_digest"] == digest(sheet)
    assert calculation["hits"][0]["query_span_nt"] == span
    assert calculation["hits"][0]["model_length_positions"] is None
    assert calculation["hits"][0]["model_coverage_fraction"] is None
    assert calculation["hits"][0]["model_consensus_equal_count"] is None  # parser not supplied

    old = json.loads((ROOT / "source_evidence/official-old-job.result.json").read_bytes())
    assert old["searchSequence"] == "" and old["numHits"] == 0
    assert (ROOT / "source_evidence/official-old-job.status").read_bytes() == b"NOT_FOUND"
    assert (ROOT / "source_evidence/official-old-job.tblout").read_bytes() == b""
    assert (ROOT / "source_evidence/official-old-job.out").read_bytes() == b""
    for manifest_name in ("source-manifest.json", "old-job-get-manifest.json"):
        records = json.loads((ROOT / "source_evidence" / manifest_name).read_bytes())
        for item in records:
            path = ROOT / "source_evidence" / item["file"]
            data = path.read_bytes()
            assert hashlib.sha256(data).hexdigest() == item["sha256"]

    print(json.dumps({
        "status": "passed",
        "checks": "fixture provenance, source extraction, explicit mutations and elementary expected arithmetic",
        "fixture_count": len(manifest),
        "source_example_query_length_nt": len(query),
        "source_example_native_score_bits": hit["score"],
        "source_example_native_evalue": hit["E"],
        "source_example_query_span_fraction": span / len(query),
        "conditional_simple_display_compared_count": len(model),
        "conditional_simple_display_equal_count": 79,
        "reverse_scalar_span_fraction": reverse_span / len(query),
        "duplicate_sum_union_excess_nt": [duplicate_sum, duplicate_union, duplicate_sum - duplicate_union],
        "production_reader_or_grader_executed": False,
        "production_episode_integration_tested": False,
        "new_job_submitted": False,
        "successful_live_result_captured": False,
    }, indent=2))


if __name__ == "__main__":
    main()
