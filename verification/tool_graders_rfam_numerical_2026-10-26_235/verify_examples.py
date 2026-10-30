"""Save full Rfam numerical examples and verify no-I/O saved-sheet replay."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import urllib.request
from unittest.mock import patch

from gene_annotation_episode.rfam_batch_contracts import RFAM_CALCULATION_PARAMETERS, RFAM_HIT_METRICS, rfam_digest
from gene_annotation_episode.rfam_batch_inputs import populate_rfam_batch_json_sheet
from gene_annotation_episode.rfam_batch_grader import calculate_rfam_batch_components
from gene_annotation_episode.rfam_batch_views import project_rfam_batch_result
from gene_annotation_episode.rfam_batch_alignment import parse_rfam_alignment_display


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "verification/tool_graders_rfam_contract_2026-10-26_232/examples"
LIVE = ROOT / "verification/tool_graders_rfam_transport_2026-10-26_234/live/single"
OUTPUT = Path(sys.argv[1])
OUTPUT.mkdir()


def save(name, value):
    path = OUTPUT / (name + ".json")
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n")
    return path


def forbidden(*args, **kwargs):
    raise AssertionError("saved numerical replay attempted IO, acquisition or execution")


examples = []
for name, source_kind, with_alignment in (
        ("documentation", "documentation", False), ("live_single", "live", False),
        ("documentation_alignment", "documentation", True), ("live_single_alignment", "live", True)):
    identity = json.loads((EXAMPLES / "single-input-identity.json").read_text())
    if source_kind == "documentation":
        path = EXAMPLES / "official-single-result.json"
        evidence_kind, status, source = "official_documentation_example", None, "fixture:documentation"
    else:
        path = LIVE / "003-fetch-json/response.body"
        source = "retained-native:single:003-fetch-json"
        evidence_kind, status = "native_response", 200
        manifest = json.loads((LIVE / "input-manifest.json").read_text())
        original = manifest["records"][0]
        identity.update({k: original[k] for k in ("query_occurrence_key", "original_record_ordinal", "original_header",
            "submitted_sequence", "submitted_sequence_sha256", "submitted_length_nt")})
        identity.update(expected_job_id=json.loads((LIVE / "original_handle.json").read_text())["job_id"],
            submission_source_ref="retained-native:single:001-submit", original_input_ref="retained-native:single:input.seq",
            subject_ref="fixture:public119")
    content = path.read_bytes()
    capture = {"artifact_ref": source + ":body", "source_ref": source,
        "source_sha256": hashlib.sha256(content).hexdigest(), "evidence_kind": evidence_kind,
        "representation": "json", "http_status": status, "body_complete": True,
        "request_job_id": identity["expected_job_id"], "request_sequence_sha256": identity["submitted_sequence_sha256"]}
    bundle = None
    if with_alignment:
        native = json.loads(content)
        components = []
        for family, hits in native["hits"].items():
            for index, hit in enumerate(hits):
                pointer = "/hits/" + family.replace("~", "~0").replace("/", "~1") + "/" + str(index)
                components.append(parse_rfam_alignment_display(hit["alignment"],
                    hit_identity={"artifact_ref": capture["artifact_ref"], "hit_key": capture["artifact_ref"] + pointer,
                        "query_occurrence_key": identity["query_occurrence_key"], "family_accession": hit["acc"]},
                    query_sequence=identity["submitted_sequence"], native_start=hit["start"], native_end=hit["end"],
                    native_strand=hit["strand"]))
        bundle = {"version": "rfam_alignment_components_bundle_v1", "artifact_ref": capture["artifact_ref"],
            "source_sha256": capture["source_sha256"], "rows": components}
        save(name + ".alignment_bundle", bundle)
    parse_result = populate_rfam_batch_json_sheet(content, input_identity=identity, capture=capture, alignment_components=bundle)
    assert parse_result["sheet"] is not None
    sheet = parse_result["sheet"]
    calculation = calculate_rfam_batch_components(sheet, parameters=deepcopy(RFAM_CALCULATION_PARAMETERS))
    selected = project_rfam_batch_result(sheet, calculation,
        projection={"family": "hit", "rows": {"offset": 0, "limit": 1}, "metrics": list(RFAM_HIT_METRICS)},
        artifact_bindings={"source_ref": source, "sheet_ref": name + ":sheet", "calculation_ref": name + ":calculation",
            "sheet_digest": rfam_digest(sheet), "calculation_digest": rfam_digest(calculation)})
    save(name + ".parse", parse_result)
    sheet_path = save(name + ".sheet", sheet)
    save(name + ".calculation", calculation)
    save(name + ".projection", selected)
    saved = json.loads(sheet_path.read_text())
    with patch("builtins.open", forbidden), patch("pathlib.Path.open", forbidden), patch.object(socket, "socket", forbidden), \
            patch.object(socket, "create_connection", forbidden), patch.object(urllib.request, "urlopen", forbidden), \
            patch.object(subprocess, "Popen", forbidden):
        recalculated = calculate_rfam_batch_components(saved, parameters=deepcopy(RFAM_CALCULATION_PARAMETERS))
    assert recalculated == calculation
    hit = calculation["hits"][0]
    examples.append({"example": name, "native_path": str(path.relative_to(ROOT)), "native_sha256": capture["source_sha256"],
        "evidence_kind": evidence_kind, "native_score_bits": hit["native_score_bits"], "native_evalue": hit["native_evalue"],
        "native_gc_fraction": hit["native_gc_fraction"], "query_span_nt": hit["query_span_nt"],
        "query_span_fraction": hit["query_span_fraction"], "model_length_positions": hit["model_length_positions"],
        "model_coverage_fraction": hit["model_coverage_fraction"], "alignment_components_supplied": with_alignment,
        "represented_model_positions": hit["represented_model_positions"],
        "model_consensus_compared_count": hit["model_consensus_compared_count"],
        "model_consensus_equal_count": hit["model_consensus_equal_count"],
        "model_consensus_equal_fraction": hit["model_consensus_equal_fraction"],
        "saved_sheet_recalculation_no_io": True})
save("manifest", {"examples": examples, "production_episode_path_verified_by_this_script": False})
print(json.dumps(examples, indent=2))
