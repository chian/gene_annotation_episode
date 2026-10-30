"""Supplied-data C4c checks; synthetic envelopes do not establish receipt custody."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.bvbrc_analysis_protocol import prepare_rpc_request
from gene_annotation_episode.bvbrc_minhash_grader import (
    calculate_minhash_components, parse_minhash_result,
)
from gene_annotation_episode.bvbrc_minhash_views import (
    minhash_fact_sources, project_minhash_facts,
)
from gene_annotation_episode.communication import (
    ReportBoundaryError, reference_resolver, validate_closed_schema, validate_form,
)
from gene_annotation_episode.domain import identity


ROOT = Path(__file__).resolve().parents[1]
MATCHES = "bvbrc_minhash_matches"
COUNTS = "bvbrc_minhash_counts"
SOURCES = (MATCHES, COUNTS)
SOURCE = "source_" + "a" * 24
SOURCE_TWO = "source_" + "b" * 24


@pytest.fixture(autouse=True)
def no_external_work(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("projection must not acquire data or launch work")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)


def qualified(native=None, *, mode="genome", source=SOURCE):
    """Exact C4b shape using the actual C1/C2 functions, not invented sheets."""
    if native is None:
        native = [["83333.1", 0.1, 0.01, "2/3"]]
    request = {"mode": mode, "query": "83333.1" if mode == "genome" else "/owner/workspace/input.fa",
               "max_pvalue": 1.0, "max_distance": 1.0, "max_hits": 0,
               "include_reference": 1, "include_representative": 1, "bacterial": 1, "viral": 0}
    operands = ("query", "max_pvalue", "max_distance", "max_hits", "include_reference",
                "include_representative", "bacterial", "viral")
    rpc = prepare_rpc_request(f"Minhash.compute_genome_distance_for_{mode}2",
                              [request[key] for key in operands], request_id=identity("minhash_rpc", request))
    parsed = parse_minhash_result(native, mode=mode, request=rpc,
                                  provenance={"kind": "explicit_synthetic_publication"})
    grading = {"schema": "bvbrc_minhash_grading_v1", "request": request, "rpc_request": rpc,
               "selector": {}, "parse_status": parsed["status"], "sheet": parsed["sheet"],
               "components": calculate_minhash_components(parsed["sheet"]), "diagnostics": parsed["diagnostics"]}
    return {"source_ref": source, "grading": grading}


def project(value, sources=SOURCES):
    return project_minhash_facts([value], requested_sources=sources)


def form_schema(sources=SOURCES):
    declarations = minhash_fact_sources()
    properties = {name: declarations[name]["report_schema"] for name in sources}
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


@pytest.mark.parametrize("mode", ["genome", "fasta"])
def test_upstream_native_numbers_in_synthetic_publication(mode):
    path = ROOT / "verification/tool_graders_bvbrc_native_rpc_contract_2026-10-24/sources/Mash/test/ref/genomes.dist"
    fields = path.read_text().splitlines()[0].split("\t")
    assert fields == ["genome1.fna", "reads", "0.12101", "4.48626e-214", "41/1000"]
    value = qualified([["83333.1", *fields[2:]]], mode=mode)
    before = deepcopy(value)
    facts = project(value)
    assert facts[MATCHES] == [{"source_ref": SOURCE, "row_index": 0, "genome_id": "83333.1",
        "reported_distance": 0.12101, "reported_pvalue": 4.48626e-214,
        "shared_hashes": 41, "compared_union_hashes": 1000,
        "shared_hash_fraction": 0.041, "parse_status": "ok"}]
    assert facts[COUNTS] == [{"source_ref": SOURCE, "returned_row_count": 1,
        "parse_status": "ok", "population_size": None, "truncated": None}]
    assert value == before
    assert facts == project(value)
    assert value["grading"]["components"]["rows"][0]["recomputed_distance"] is None
    assert value["grading"]["components"]["rows"][0]["recomputed_pvalue"] is None


def test_closed_schemas_and_exact_reference_namespaces():
    schema = validate_closed_schema(form_schema())
    facts = project(qualified())
    registry = {"execution_result": {SOURCE}, "bvbrc_minhash_genome": {"83333.1"}}
    assert validate_form(facts, schema, reference_resolver(registry)) == facts
    match = schema["properties"][MATCHES]["items"]["properties"]
    assert match["source_ref"] == {"type": "string", "format": "reference", "x-reference-namespace": "execution_result"}
    assert match["genome_id"]["format"] == "identifier"
    for wrong in ({"source": {SOURCE}, "bvbrc_minhash_genome": {"83333.1"}},
                  {"execution_result": {SOURCE, "83333.1"}},
                  {"execution_result": {SOURCE}, "bvbrc_data_identifier": {"83333.1"}}):
        with pytest.raises(ReportBoundaryError, match="unavailable"):
            validate_form(facts, schema, reference_resolver(wrong))


def test_declarations_and_projection_are_detached():
    first = minhash_fact_sources()
    first[MATCHES]["report_schema"]["items"]["properties"]["source_ref"]["x-reference-namespace"] = "wrong"
    assert minhash_fact_sources()[MATCHES]["report_schema"]["items"]["properties"]["source_ref"]["x-reference-namespace"] == "execution_result"
    value = qualified()
    before = deepcopy(value)
    facts = project(value)
    facts[MATCHES][0]["shared_hashes"] = 900
    assert value == before


@pytest.mark.parametrize("requested", [[], [MATCHES], [COUNTS], list(SOURCES), set(SOURCES), tuple(SOURCES)])
def test_only_requested_families_and_empty_qualified_arrays(requested):
    assert project_minhash_facts([], requested_sources=requested) == {name: [] for name in requested}
    facts = project(qualified(), requested)
    assert set(facts) == set(requested)
    if requested == [COUNTS]:
        assert "83333.1" not in json.dumps(facts)
        assert not {"raw_output", "sheet", "diagnostics", "components", "request"} & facts[COUNTS][0].keys()


@pytest.mark.parametrize("requested", [["unknown"], [MATCHES, "unknown"], [MATCHES, MATCHES], MATCHES, [True], None, {"matches": MATCHES}])
def test_invalid_requested_families_are_errors(requested):
    with pytest.raises(ValueError, match="requested_source"):
        project_minhash_facts([], requested_sources=requested)


def test_empty_native_array_is_zero_returned_unknown_population():
    facts = project(qualified([]))
    assert facts[MATCHES] == []
    assert facts[COUNTS] == [{"source_ref": SOURCE, "returned_row_count": 0,
        "parse_status": "ok", "population_size": None, "truncated": None}]


def test_native_order_duplicate_genomes_and_separate_source_associations():
    native = [["83333.2", 0.2, 0.02, "1/3"], ["83333.1", 0.1, 0.01, "2/3"],
              ["83333.2", 0.3, 0.03, "3/3"]]
    facts = project_minhash_facts([qualified(native), qualified(source=SOURCE_TWO)], requested_sources=SOURCES)
    assert [(row["source_ref"], row["row_index"], row["genome_id"]) for row in facts[MATCHES]] == [
        (SOURCE, 0, "83333.2"), (SOURCE, 1, "83333.1"), (SOURCE, 2, "83333.2"), (SOURCE_TWO, 0, "83333.1")]
    assert [row["shared_hash_fraction"] for row in facts[MATCHES]] == [1/3, 2/3, 1.0, 2/3]
    # All three rows survive max_hits=0; no presumed trimming/completeness.
    assert [row["returned_row_count"] for row in facts[COUNTS]] == [3, 1]


def test_missing_malformed_and_measured_zero_remain_distinct():
    native = [None, {}, [], [None, 0, 0, "1/1"], ["83333.1", None, "NaN", None],
              ["83333.2", 0.1], ["83333.3", True, False, "1/2"],
              ["83333.4", 0, 0, "3/2"], ["83333.5", 0, 1, "0/0"],
              ["83333.6", 0, 0, "1/1", "extra"]]
    value = qualified(native)
    facts = project(value)
    rows = facts[MATCHES]
    assert len(rows) == len(native) == facts[COUNTS][0]["returned_row_count"]
    assert [row["row_index"] for row in rows] == list(range(len(native)))
    assert [row["parse_status"] for row in rows] == ["invalid", "invalid", "invalid", "partial",
        "invalid", "partial", "partial", "partial", "ok", "partial"]
    assert rows[3]["genome_id"] is None and rows[3]["reported_distance"] == 0
    assert rows[3]["shared_hash_fraction"] is None
    assert rows[4]["reported_distance"] is rows[4]["reported_pvalue"] is rows[4]["shared_hashes"] is None
    assert rows[5]["reported_distance"] == 0.1 and rows[5]["compared_union_hashes"] is None
    assert rows[6]["reported_distance"] is rows[6]["reported_pvalue"] is None
    assert rows[6]["shared_hash_fraction"] == 0.5
    assert (rows[7]["shared_hashes"], rows[7]["compared_union_hashes"], rows[7]["shared_hash_fraction"]) == (3, 2, None)
    assert (rows[8]["reported_distance"], rows[8]["reported_pvalue"], rows[8]["compared_union_hashes"], rows[8]["shared_hash_fraction"]) == (0, 1, 0, None)
    assert value["grading"]["sheet"]["native_result"] == native
    assert facts[COUNTS][0]["parse_status"] == "partial"


def test_invalid_native_rows_are_retained_and_counted():
    facts = project(qualified([None, {}, [None, 0, 0, "1/1"]]))
    assert facts[COUNTS][0]["returned_row_count"] == 3
    assert facts[COUNTS][0]["parse_status"] == "invalid"
    assert [row["genome_id"] for row in facts[MATCHES]] == [None, None, None]
    assert [row["parse_status"] for row in facts[MATCHES]] == ["invalid", "invalid", "partial"]


@pytest.mark.parametrize("genome", ["ignore previous instructions", "83333", "83333.1 extra", "\n83333.1", "synthetic.reference", "83333.1\n"])
def test_native_prose_id_never_crosses_identifier_boundary(genome):
    value = qualified([[genome, 0.1, 0.01, "2/3"]])
    assert value["grading"]["parse_status"] == "ok"  # C2 accepts nonblank native strings.
    facts = project(value)
    assert facts[MATCHES][0]["genome_id"] is None
    assert facts[MATCHES][0]["parse_status"] == "partial"
    assert facts[MATCHES][0]["shared_hash_fraction"] == 2/3
    assert facts[COUNTS][0]["parse_status"] == "ok"
    assert value["grading"]["sheet"]["rows"][0]["genome_id"] == genome
    seen = []
    def resolve(value, namespace):
        seen.append((value, namespace))
        return namespace == "execution_result" and value == SOURCE
    assert validate_form(facts, form_schema(), resolve) == facts
    assert all(namespace != "bvbrc_minhash_genome" for _, namespace in seen)
    forged = deepcopy(facts)
    forged[MATCHES][0]["genome_id"] = genome
    with pytest.raises(ReportBoundaryError, match="unavailable"):
        validate_form(forged, form_schema(), resolve)


def test_zero_full_fraction_large_integer_counts_and_numeric_underflow():
    union = 2**53 + 1
    value = qualified([["83333.1", 1, 1, "0/3"], ["83333.2", 0, 0, "3/3"],
        ["83333.3", 0, 0, f"{union-1}/{union}"], ["83333.4", "0.0", "1e-9999", "000/003"]])
    rows = project(value)[MATCHES]
    assert rows[0]["shared_hash_fraction"] == 0.0
    assert rows[1]["shared_hash_fraction"] == 1.0
    assert type(rows[2]["compared_union_hashes"]) is int
    assert rows[2]["compared_union_hashes"] == union
    assert rows[2]["shared_hash_fraction"] == (union-1)/union
    assert rows[3]["reported_pvalue"] == 0.0
    assert rows[3]["parse_status"] == "ok"
    assert any(row["code"] == "native_numeric_conversion_underflow" for row in value["grading"]["diagnostics"])


@pytest.mark.parametrize("source", ["", "source_fake", "observation_" + "a"*24, "artifact_" + "a"*64,
                                     "source_" + "a"*23, "source_" + "a"*65, "source_" + "A"*24, SOURCE + "\n", True, None])
def test_wrong_source_reference_namespace_or_syntax_rejected(source):
    with pytest.raises(ValueError, match="source_reference"):
        project(qualified(source=source))


@pytest.mark.parametrize("mutate,code", [
    (lambda g: g.update(schema="wrong"), "grading_schema"),
    (lambda g: g.update(extra="field"), "closed_fields"),
    (lambda g: g.update(selector={"limit": 1}), "selector"),
    (lambda g: g.update(parse_status="partial"), "parse_status_consistency"),
    (lambda g: g["request"].update(mode="fasta"), "native_request"),
    (lambda g: g["request"].update(max_hits=True), "native_request"),
    (lambda g: g["request"].update(max_pvalue="1"), "native_request"),
    (lambda g: g["request"].update(query="83333.2"), "rpc_request_identity"),
    (lambda g: g["rpc_request"].update(id="wrong"), "rpc_request_identity"),
    (lambda g: g["rpc_request"].update(version="2.0"), "rpc_request_identity"),
    (lambda g: g["rpc_request"].update(method="Minhash.compute_genome_distance_for_fasta2"), "rpc_request_identity"),
    (lambda g: g["sheet"].update(mode="fasta"), "sheet_request_identity"),
    (lambda g: g["sheet"]["request"].update(id="wrong"), "sheet_request_identity"),
    (lambda g: g["sheet"].update(schema="wrong"), "sheet_schema"),
    (lambda g: g["sheet"].update(provenance=None), "structured_provenance"),
    (lambda g: g["sheet"].update(rows=[]), "row_count_association"),
    (lambda g: g["sheet"].update(native_result={}), "row_arrays"),
    (lambda g: g["components"].update(schema="wrong"), "components_schema"),
    (lambda g: g["components"].update(rows=[]), "row_count_association"),
    (lambda g: g["sheet"]["search_metadata"].update(population_size=1), "search_metadata_unavailable"),
    (lambda g: g["sheet"]["search_metadata"].update(truncated=False), "search_metadata_unavailable"),
    (lambda g: g["sheet"]["rows"][0].update(row_index=True), "sheet_row_index"),
    (lambda g: g["sheet"]["rows"][0].update(row_index=0.0), "sheet_row_index"),
    (lambda g: g["sheet"]["rows"][0].update(genome_id="83333.2"), "native_genome_id"),
    (lambda g: g["sheet"]["rows"][0].update(counts_token="1/3"), "counts_token_mismatch"),
    (lambda g: g["components"]["rows"][0].update(row_index=1), "component_row_association"),
    (lambda g: g["components"]["rows"][0].update(genome_id="83333.2"), "component_row_association"),
    (lambda g: g["components"]["rows"][0].update(reported_distance=0.2), "component_row_association"),
    (lambda g: g["components"]["rows"][0].update(shared_hash_fraction=0.5), "shared_fraction_operands"),
    (lambda g: g["components"]["rows"][0].update(shared_hash_fraction=None), "shared_fraction_operands"),
    (lambda g: g["components"]["rows"][0]["calculation_inputs"].update(shared_hashes=1), "component_count_operands"),
    (lambda g: g["components"]["rows"][0]["calculation_inputs"].update(kmer_length=21), "publication_metadata_unavailable"),
    (lambda g: g["components"]["rows"][0].update(recomputed_distance=0.1), "publication_metadata_unavailable"),
    (lambda g: g["components"]["diagnostics"].clear(), "component_diagnostics_association"),
    (lambda g: g["diagnostics"].append({"code": "forged", "path": "x", "severity": "error"}), "parse_diagnostics_association"),
])
def test_specific_errors_for_inconsistent_envelopes(mutate, code):
    value = qualified()
    mutate(value["grading"])
    with pytest.raises(ValueError, match=code):
        project(value)


@pytest.mark.parametrize("value", [True, False, "0.1", -0.1, 1.1, float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("field", ["reported_distance", "reported_pvalue"])
def test_forged_numeric_cells_rejected_instead_of_coerced(field, value):
    record = qualified()
    record["grading"]["sheet"]["rows"][0][field] = value
    record["grading"]["components"]["rows"][0][field] = value
    with pytest.raises(ValueError, match="numeric_cell|numeric_range|nonfinite_number"):
        project(record)


@pytest.mark.parametrize("value", [True, False, 2.0, -1, "2"])
@pytest.mark.parametrize("field", ["shared_hashes", "compared_union_hashes"])
def test_hash_counts_must_be_saved_native_integers(field, value):
    record = qualified()
    record["grading"]["sheet"]["rows"][0][field] = value
    record["grading"]["components"]["rows"][0]["calculation_inputs"][field] = value
    with pytest.raises(ValueError, match="numeric_cell|numeric_range"):
        project(record)


@pytest.mark.parametrize("value", [True, False, "0.6666666666666666", -0.1, 1.1, float("nan"), float("inf")])
def test_shared_fraction_requires_finite_numeric_saved_value(value):
    record = qualified()
    record["grading"]["components"]["rows"][0]["shared_hash_fraction"] = value
    with pytest.raises(ValueError, match="numeric_cell|numeric_range|nonfinite_number"):
        project(record)


def test_malformed_native_counts_cannot_gain_invented_hash_counts_or_fraction():
    record = qualified([["83333.1", 0.1, 0.01, "malformed"]])
    record["grading"]["sheet"]["rows"][0]["shared_hashes"] = 0
    with pytest.raises(ValueError, match="native_count_mismatch"):
        project(record)
    record = qualified([["83333.1", 0, 1, "0/0"]])
    record["grading"]["components"]["rows"][0]["shared_hash_fraction"] = 0.0
    with pytest.raises(ValueError, match="shared_fraction_operands"):
        project(record)


def test_fasta_assignment_requires_the_original_workspace_path():
    record = qualified(mode="fasta")
    request = record["grading"]["request"]
    request["query"] = "/owner/workspace/../input.fa"
    rpc = record["grading"]["rpc_request"]
    rpc["params"][0] = request["query"]
    rpc["id"] = identity("minhash_rpc", request)
    record["grading"]["sheet"]["request"] = deepcopy(rpc)
    with pytest.raises(ValueError, match="workspace_fasta_path"):
        project(record)


def test_consistently_forged_sheet_and_component_values_still_require_native_cells():
    value = qualified()
    value["grading"]["sheet"]["rows"][0]["reported_distance"] = 0.3
    value["grading"]["components"]["rows"][0]["reported_distance"] = 0.3
    with pytest.raises(ValueError, match="native_number_mismatch"):
        project(value)
    value["grading"]["sheet"]["rows"][0]["native_row"][1] = 0.3
    with pytest.raises(ValueError, match="native_row_association"):
        project(value)


def test_component_duplicate_genomes_cannot_be_joined_by_id_or_reordered():
    value = qualified([["83333.1", 0.1, 0.01, "2/3"], ["83333.1", 0.2, 0.02, "1/3"]])
    value["grading"]["components"]["rows"].reverse()
    with pytest.raises(ValueError, match="component_row_association"):
        project(value)


@pytest.mark.parametrize("location", ["native", "provenance", "diagnostics", "components"])
def test_nonfinite_numbers_rejected_everywhere_even_unprojected_data(location):
    value = qualified()
    target = {"native": value["grading"]["sheet"]["native_result"][0],
              "provenance": value["grading"]["sheet"]["provenance"],
              "diagnostics": value["grading"]["diagnostics"],
              "components": value["grading"]["components"]}[location]
    if isinstance(target, list):
        target.append(float("nan"))
    else:
        target["extra"] = float("inf")
    with pytest.raises(ValueError, match="nonfinite_number"):
        project(value, [COUNTS])


def test_no_parser_calculator_file_io_or_mutation_during_projection(monkeypatch):
    value = qualified()
    frozen = json.loads(json.dumps(value, allow_nan=False))
    import gene_annotation_episode.bvbrc_minhash_grader as grader
    def forbidden(*args, **kwargs):
        raise AssertionError("projection cannot regrade or perform I/O")
    monkeypatch.setattr(grader, "parse_minhash_result", forbidden)
    monkeypatch.setattr(grader, "calculate_minhash_components", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    assert project(value) == project(frozen)
    assert value == frozen


def test_valid_looking_source_reference_alone_is_not_custody_evidence():
    # Deliberately no store or receipt chain: the host precondition is external.
    value = qualified(source=SOURCE_TWO)
    assert project(value)[COUNTS][0]["source_ref"] == SOURCE_TWO
    with pytest.raises(ReportBoundaryError, match="unavailable"):
        validate_form(project(value), form_schema(), reference_resolver({
            "execution_result": {SOURCE}, "bvbrc_minhash_genome": {"83333.1"}}))


def test_plain_json_and_closed_qualified_pair_required():
    value = qualified()
    value["trusted"] = True
    with pytest.raises(ValueError, match="closed_fields"):
        project(value)
    value = qualified()
    value["grading"]["sheet"]["provenance"]["tuple"] = (1, 2)
    with pytest.raises(ValueError, match="plain_json_required"):
        project(value)
    value = qualified()
    value["grading"]["sheet"]["provenance"]["recursive"] = value
    with pytest.raises(ValueError, match="plain_json_required"):
        project(value)
