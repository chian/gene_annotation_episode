"""Offline D2 verification; retained native bytes, explicitly synthetic bindings.

Run from the repository with:
    python3 verification/tool_graders_bvbrc_native_data_2026-10-24/verify.py
This verification script may read/write evidence. Production readers and
calculators do neither. It makes no network call or native-program invocation.
"""
from copy import deepcopy
import hashlib
import inspect
import json
from pathlib import Path
import socket
import subprocess
import sys
import urllib.request
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode import bvbrc_data_calculators as calculators
from gene_annotation_episode import bvbrc_data_readers as readers
from gene_annotation_episode import bvbrc_data_schema as shapes
from gene_annotation_episode.bvbrc_data_query import encode_native_query

OUT = Path(__file__).resolve().parent
NATIVE = ROOT / "verification/tool_graders_bvbrc_data_contract_2026-10-24"
EXAMPLES = json.loads((NATIVE / "FILLED_EXAMPLES.json").read_text())
POLICY = "same_response_exact_document_count"
checks, inputs = [], []


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def request(collection, fields=None, **kwargs):
    value = dict(version="bvbrc_data_request_v2", collection=collection, mode="page", filters=[])
    if fields is not None:
        value["fields"] = fields
    value.update(kwargs)
    return encode_native_query(value, base_url="https://www.bv-brc.org/api")


def retained(name, prepared, *, synthetic_v2_binding=False):
    meta = json.loads((NATIVE / (name + ".meta.json")).read_text())
    content = (NATIVE / (name + ".body")).read_bytes()
    check(name + " exact retained byte hash", hashlib.sha256(content).hexdigest() == meta["sha256"])
    check(name + " exact retained byte length", len(content) == meta["byte_count"])
    media = next(value for key, value in meta["headers"] if key.lower() == "content-type")
    transport = {"status": meta["status"], "header_items": meta["headers"],
                 "automatic_redirects": False, "effective_url": meta["effective_url"],
                 "request": {"method": meta.get("method", "GET"), "url": meta["url"],
                             "headers": meta["request_headers"]}}
    if "body_complete" in meta:
        transport["body_complete"] = meta["body_complete"]
    if synthetic_v2_binding:
        transport["request"] = deepcopy(prepared["native_request"])
    source = SourceSnapshot("bvbrc_data", meta["url"], prepared["effective_request"] if synthetic_v2_binding else {},
                            meta["retrieved_at"], content, media, transport)
    result = (readers.parse_data_snapshot(source, prepared=prepared) if synthetic_v2_binding
              else readers._decode_native_payload(source, prepared=prepared))
    inputs.append({"artifact": str((NATIVE / (name + ".body")).relative_to(ROOT)),
                   "sha256": meta["sha256"], "byte_count": len(content),
                   "evidence_kind": "retained_native_response_bytes",
                   "binding_kind": "synthetic_v2_transport_binding" if synthetic_v2_binding else "actual_legacy_capture_unqualified_for_v2"})
    return result


def numbers(sheet):
    return [{"native_id": row["native_id"], "values": {
        cell["field"]: {"value": cell["value"], "status": cell["status"], "reason": cell["reason"],
                        "unit_code": cell["unit_code"], "unit_basis": cell["unit_basis"]}
        for cell in row["numerical_cells"]}} for row in sheet["rows"]]


facet_prepared = EXAMPLES["qualified_result_fixture"]["grading"]["prepared"]
facet = retained("feature_facet_solr_zero", facet_prepared, synthetic_v2_binding=True)
check("native facet sheet exactly equals frozen expected sheet under synthetic transport", facet["sheet"] == EXAMPLES["facet_expected_sheet"])
facet_numbers = calculators.calculate_facet_fractions(facet["sheet"], denominator_policy=POLICY)
check("hand fractions 1/2, 1/2, 0/2", [item["fraction"] for item in facet_numbers["fractions"]] == [0.5, 0.5, 0.0])
count_request = deepcopy(facet_prepared["original_request"])
count_request["mode"] = "count"
del count_request["facet"]
count_prepared = encode_native_query(count_request, base_url="https://www.bv-brc.org/api")
count = retained("feature_count_solr", count_prepared, synthetic_v2_binding=True)
count_numbers = calculators.calculate_page_counts(count["sheet"])
check("count2 is distinct from empty docs", count_numbers["native_row_count"] == 0 and count_numbers["reported_population_count"] == 2)

genome = retained("genome_page", request("genome", ["genome_id", "genome_length", "gc_content", "plasmids"]))
check("unrecorded body completeness remains false", genome["sheet"]["transport"]["body_complete"] is False)
genome_extraction = readers.extract_collection_rows(genome["sheet"], fields=("genome_id", "genome_length", "gc_content", "plasmids"))
check("hand genome measurements include present zero", [item["value"] for item in genome_extraction["rows"][0]["numerical_cells"]] == [4639675, 50.8, 0])
expression = retained("expression_page", request("bioset_result", ["id", "feature_id", "exp_id", "bioset_id", "counts", "fpkm", "tpm", "log2_fc", "p_value", "z_score", "other_value"]))
expression_numbers = numbers(expression["sheet"])
check("native signed fold changes", [row["values"]["log2_fc"]["value"] for row in expression_numbers] == [-0.132, -0.129])
check("native signed z scores", [row["values"]["z_score"]["value"] for row in expression_numbers] == [-0.544, -0.556])
check("missing counts remain missing", all(row["values"]["counts"]["reason"] == "native_field_absent" for row in expression_numbers))
protein = retained("protein_feature_page", request("protein_feature", ["id", "score", "e_value"]))
ppi = retained("ppi_page", request("ppi", ["id", "score"]))
check("hand protein E value text projection", numbers(protein["sheet"])[0]["values"]["e_value"]["value"] == 1.25e-9)
check("hand PPI numeric exception has unknown scale", numbers(ppi["sheet"])[0]["values"]["score"]["value"] == 7.9219284 and numbers(ppi["sheet"])[0]["values"]["score"]["unit_code"] is None)
join = EXAMPLES["feature_sequence_expected_sheet"]
join_numbers = calculators.calculate_feature_sequence_counts(join)
check("independent hand feature/sequence relation count", join_numbers == {
    "version": "bvbrc_feature_sequence_components_v1", "selected_feature_count": 2,
    "retained_feature_row_count": 2, "native_sequence_record_count": 2,
    "distinct_joined_aa_sequence_count": 1, "distinct_joined_na_sequence_count": 1,
    "relation_count": 4, "missing_key_count": 0, "missing_record_count": 0,
    "conflicting_relation_count": 0, "length_agreement_count": 4})

filled = {"interpretation": "Native measurements from exact historical response bytes. New v2 transport bindings and the feature join sheet are labeled test fixtures, not live execution or host admission.",
          "count_with_synthetic_v2_transport": {"parse_result": count, "components": count_numbers},
          "facet_with_synthetic_v2_transport": {"parse_result": facet, "components": facet_numbers},
          "legacy_genome_extraction": genome_extraction,
          "legacy_native_expression": {"parse_result": expression, "numerical_rows": expression_numbers},
          "legacy_protein_feature": {"parse_result": protein, "numerical_rows": numbers(protein["sheet"])},
          "legacy_ppi": {"parse_result": ppi, "numerical_rows": numbers(ppi["sheet"])},
          "frozen_native_derived_feature_join_fixture": {"sheet": join, "components": join_numbers}}
(OUT / "FILLED_RESULTS.json").write_text(json.dumps(filled, indent=2, allow_nan=False) + "\n")
saved = json.loads((OUT / "FILLED_RESULTS.json").read_text())


def prohibited(*_args, **_kwargs):
    raise AssertionError("offline recalculation attempted network or subprocess")


with patch.object(urllib.request, "urlopen", prohibited), patch.object(urllib.request.OpenerDirector, "open", prohibited), patch.object(socket, "socket", prohibited), patch.object(subprocess, "run", prohibited), patch.object(subprocess, "Popen", prohibited):
    check("saved facet recalculation has no network or native command", calculators.calculate_facet_fractions(saved["facet_with_synthetic_v2_transport"]["parse_result"]["sheet"], denominator_policy=POLICY) == facet_numbers)
    check("saved page count recalculation has no network or native command", calculators.calculate_page_counts(saved["count_with_synthetic_v2_transport"]["parse_result"]["sheet"]) == count_numbers)
    check("saved sequence count recalculation has no network or native command", calculators.calculate_feature_sequence_counts(saved["frozen_native_derived_feature_join_fixture"]["sheet"]) == join_numbers)

files = [ROOT / "gene_annotation_episode" / (module.__name__.rsplit(".", 1)[1] + ".py") for module in (shapes, readers, calculators)]
files += [ROOT / "tests" / name for name in ("test_bvbrc_data_schema.py", "test_bvbrc_data_readers.py", "test_bvbrc_data_calculators.py")]
report = {"version": "bvbrc_native_data_verification_v1", "status": "passed", "checks": checks,
          "check_count": len(checks), "native_inputs": inputs,
          "source_sha256": {str(path.relative_to(ROOT)): digest(path) for path in files},
          "contract_sha256": {name: digest(NATIVE / name) for name in ("CONTRACT_SHAPES.json", "D1_QUERY_CONTRACT_FROZEN.json", "FILLED_EXAMPLES.json", "REPORT.json")},
          "exact_exports": {module.__name__: list(module.__all__) for module in (shapes, readers, calculators)},
          "signatures": {name: str(inspect.signature(getattr(module, name))) for module in (shapes, readers, calculators) for name in module.__all__ if inspect.isfunction(getattr(module, name))},
          "executed": ["offline retained-native byte hash/length checks", "native array/header and Solr payload decoding", "synthetic v2 transport binding around exact historical native bytes", "independent hand numerical checks", "saved-sheet recalculation with network/subprocess methods prohibited"],
          "not_executed": ["live network calls", "remote jobs or native scientific programs", "host admission", "selected resource child execution", "model-facing delivery", "complete episode communication"],
          "remaining_integration": "D5/D6 own qualified projections, host source/receipt custody, child-owned call binding, durable admission and actual receiver delivery. D2 unit and native-fixture checks do not establish these capabilities.",
          "evidence_limits": ["Historical native bytes remain historical; no new v2 API invocation occurred.", "Legacy array receipts and their actual transport are not upgraded to v2.", "The genome native capture omitted body_complete; its parser sheet conservatively records incomplete/unknown capture status.", "All318 registered field types derive from observed native schemas, not populated live measurements for every field.", "No scientific confidence or expression statistical analysis is manufactured for acquisition."]}
(OUT / "REPORT.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
print(json.dumps({"checks": len(checks), "status": "passed", "native_count": 2,
                  "facet_fractions": [0.5, 0.5, 0.0], "feature_relations": 4,
                  "filled_results_sha256": digest(OUT / "FILLED_RESULTS.json")}, indent=2))
