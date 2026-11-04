"""D5 pure return tests; host admissions here are explicitly synthetic.

The facet bytes are the retained native response. Feature/molecular values are
copied from retained native arrays into labeled synthetic Solr envelopes for
these pure view tests. Neither fixture confers real host custody or establishes
a new v2 acquisition, a durable admission, or an episode/model input path.
"""
from copy import deepcopy
import builtins
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import urllib.request

import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.bvbrc_data_calculators import (
    calculate_facet_fractions, calculate_feature_sequence_counts, calculate_page_counts,
)
from gene_annotation_episode.bvbrc_data_feature_sequences import extract_feature_sequence_join
from gene_annotation_episode.bvbrc_data_molecular import extract_molecular_experiment_rows
from gene_annotation_episode.bvbrc_data_query import encode_native_query
from gene_annotation_episode.bvbrc_data_readers import parse_data_snapshot
from gene_annotation_episode.bvbrc_data_schema import json_digest, validate
from gene_annotation_episode.bvbrc_data_views import (
    FACT_SCHEMAS, FACT_SOURCES, IDENTIFIER_NAMESPACES, bvbrc_data_fact_sources,
    materialize_bvbrc_received_values, project_bvbrc_data_facts,
    resolve_bvbrc_data_identifier, validate_bvbrc_data_return, validate_data_result_selector,
)
from gene_annotation_episode.communication import validate_closed_schema, validate_form, form_with_facts
from gene_annotation_episode.execution_contracts import digest

EVIDENCE = Path(__file__).resolve().parents[1] / "verification/tool_graders_bvbrc_data_contract_2026-10-24"
EXAMPLES = json.loads((EVIDENCE / "FILLED_EXAMPLES.json").read_text())
FROZEN = json.loads((EVIDENCE / "CONTRACT_SHAPES.json").read_text())
BASE = "https://www.bv-brc.org/api"
FEATURE_IDS = ["PATRIC.511145.12.NC_000913.CDS.822959.823720.rev",
               "RefSeq.511145.12.NC_000913.CDS.822959.823720.rev"]
RESULT_ID = "00000317-5d60-4e06-9c35-c42e53fd5ae3"


def selector(projection=None, *, inputs=(), supplied=(), page=None):
    return {"version": "bvbrc_data_result_selector_v2", "page": page,
        "projection": projection or {"family": "query_metadata"},
        "inputs": list(inputs), "supplied_metadata": list(supplied)}


def request(collection="genome", *, mode="page", fields=None):
    result = {"version": "bvbrc_data_request_v2", "collection": collection, "mode": mode, "filters": []}
    if fields is not None:
        result["fields"] = fields
    return result


def snapshot(prepared, content, *, media="application/solr+json"):
    """Synthetic transport only. No network execution or real admission."""
    native = prepared["native_request"]
    return SourceSnapshot("bvbrc_data", native["url"], deepcopy(prepared["effective_request"]),
        "synthetic_D5_host_fixture", content, media, {"status": 200, "body_complete": True,
            "automatic_redirects": False, "effective_url": native["url"],
            "request": deepcopy(native), "header_items": []})


def qualified(collection="genome", docs=(), fields=None, *, selection=None, inputs=(),
              source="source_fixture_main", raw=None, req=None):
    """Build exact shapes through D1/D2, with labeled hypothetical host facts."""
    selection = selection or selector()
    req = req or request(collection, fields=fields)
    prepared = encode_native_query(req, base_url=BASE, page_selector=selection["page"])
    if raw is None:
        raw = json.dumps({"responseHeader": {"status": 0},
            "response": {"numFound": len(docs), "numFoundExact": True, "start": prepared["effective_request"]["offset"],
                         "docs": docs}}, separators=(",", ":")).encode()
    parsed = parse_data_snapshot(snapshot(prepared, raw), prepared=prepared)
    sheet = parsed["sheet"]
    binding = {"source_ref": source, "native_artifact_ref": "artifact_native_" + source,
        "native_sha256": hashlib.sha256(raw).hexdigest(), "grading_artifact_ref": "artifact_grading_" + source,
        "collection": collection, "acquisition_assignment_sha256": digest({"fixture": source}),
        "selector_sha256": digest(selection)}
    input_results = [{"binding": deepcopy(q["binding"]), "sheet": deepcopy(q["grading"]["parse_result"]["sheet"])} for q in inputs]
    metadata = [{"source_ref": r["provenance"]["source_ref"], "native_artifact_ref": "artifact_metadata_fixture",
        "native_sha256": "a" * 64, "record_path": r["provenance"]["record_path"],
        "metadata_sha256": json_digest({k: v for k, v in r.items() if k != "provenance"})} for r in selection["supplied_metadata"]]
    grading = {"version": "bvbrc_data_grading_v1", "prepared": prepared, "selector": selection,
        "parse_result": parsed, "page_components": calculate_page_counts(sheet) if sheet else None,
        "facet_components": calculate_facet_fractions(sheet, denominator_policy="same_response_exact_document_count") if sheet and sheet["mode"] == "facet" else None,
        "feature_sequence_sheet": None, "feature_sequence_components": None, "molecular_sheet": None,
        "input_bindings": [r["binding"] for r in input_results], "metadata_bindings": metadata}
    all_pages = ([sheet] if sheet is not None else []) + [r["sheet"] for r in input_results]
    pages = lambda collection: [p for p in all_pages if p["collection"] == collection]
    projection = selection["projection"]
    if projection["family"] == "feature_sequence":
        grading["feature_sequence_sheet"] = extract_feature_sequence_join(pages("genome_feature"), pages("feature_sequence"),
            feature_ids=projection["feature_ids"], sequence_kind=projection["sequence_kind"])
        grading["feature_sequence_components"] = calculate_feature_sequence_counts(grading["feature_sequence_sheet"])
    if projection["family"] == "molecular_experiment":
        grading["molecular_sheet"] = extract_molecular_experiment_rows(pages("bioset_result"),
            bioset_pages=pages("bioset"), experiment_pages=pages("experiment"), feature_pages=pages("genome_feature"),
            result_ids=projection["result_ids"], supplied_metadata=selection["supplied_metadata"])
    return validate("QualifiedResult", {"version": "bvbrc_data_qualified_result_v1", "service": "bvbrc_data",
        "binding": binding, "host_qualification": {"run_id": "synthetic_run", "source_episode_id": "synthetic_results",
            "receiver_episode_id": "synthetic_receiver", "scope_sha256": "b" * 64,
            **{k: True for k in ("receipt_verified", "native_bytes_verified", "grading_custody_verified",
                "original_selection_verified", "input_bindings_verified", "receiver_possession_verified")},
            "possession_basis": "admitted_return"}, "grading": grading, "input_results": input_results})


def native_rows(name):
    raw = (EVIDENCE / (name + ".body")).read_bytes()
    meta = json.loads((EVIDENCE / (name + ".meta.json")).read_text())
    assert hashlib.sha256(raw).hexdigest() == meta["sha256"]
    return json.loads(raw)


def field_names(docs):
    return list(dict.fromkeys(field for row in docs for field in row))


def feature_fixture(*, include=True, ids=None):
    sequences, features = native_rows("feature_sequences"), native_rows("feature_page")
    sequence = qualified("feature_sequence", sequences, ["md5", "sequence_type", "sequence"], source="source_fixture_sequences")
    selection = selector({"family": "feature_sequence", "feature_ids": ids or FEATURE_IDS,
        "sequence_kind": "both", "feature_metadata_fields": ["gene", "annotation"], "include_sequence_values": include},
        inputs=[{"collection": "feature_sequence", "source_ref": sequence["binding"]["source_ref"]}])
    fields = ["feature_id", "genome_id", "sequence_id", "patric_id", "gene", "aa_sequence_md5", "na_sequence_md5",
              "aa_length", "na_length", "start", "end", "strand", "annotation"]
    return qualified("genome_feature", features, fields, selection=selection, inputs=[sequence])


def supplied_metadata(**changes):
    return {"result_id": RESULT_ID, "bioset_id": "57692532",
        "provenance": {"source_ref": "source/units~é", "record_path": "/design/0"},
        "sample_ids": [], "biological_replicate_ids": None, "technical_replicate_ids": [],
        "measurement_units": [{"field": "log2_fc", "unit": "log₂ treatment/reference"}],
        "normalization_method": None, "pvalue_correction_method": None, "contrast": None, **changes}


def molecular_fixture(*, supplied=(), ids=None, metadata=None, measurements=None):
    results, biosets, experiments = native_rows("expression_page"), native_rows("bioset_page"), native_rows("experiment_page")
    b = qualified("bioset", biosets, field_names(biosets), source="source_fixture_bioset")
    e = qualified("experiment", experiments, field_names(experiments), source="source_fixture_experiment")
    selection = selector({"family": "molecular_experiment", "result_ids": ids or [RESULT_ID],
        "measurement_fields": measurements if measurements is not None else ["log2_fc", "z_score", "counts", "p_value"],
        "metadata_fields": metadata if metadata is not None else [
            {"source_level": "result", "field": "treatment_name"},
            {"source_level": "bioset", "field": "treatment_duration"},
            {"source_level": "experiment", "field": "measurement_technique"},
            {"source_level": "supplied", "field": "biological_replicate_ids"}]},
        inputs=[{"collection": "bioset", "source_ref": b["binding"]["source_ref"]},
                {"collection": "experiment", "source_ref": e["binding"]["source_ref"]}], supplied=supplied)
    fields = field_names(results) + [f for f in ("counts", "fpkm", "tpm", "p_value", "other_value") if f not in field_names(results)]
    return qualified("bioset_result", results, fields, selection=selection, inputs=[b, e])


def report(q, sources, *, names=None):
    facts = project_bvbrc_data_facts([q], selector=q["grading"]["selector"], requested_sources=tuple(sources))
    names = names or ["field_" + str(i) for i in range(len(sources))]
    schema = {"type": "object", "properties": {n: deepcopy(FACT_SCHEMAS[s]) for n, s in zip(names, sources)},
              "required": names, "additionalProperties": False}
    form = form_with_facts({}, schema, facts)
    return facts, schema, form


def test_all_six_schemas_pass_existing_closed_boundary_unchanged():
    # Independent literal application of additive correction003. The original
    # immutable planning artifact is deliberately not rewritten.
    expected = deepcopy(FROZEN["fact_schemas"])
    page = expected[FACT_SOURCES[0]]["items"]
    for name in ("returned_row_count", "valid_row_count", "invalid_row_count"):
        page["properties"][name]["type"] = ["integer", "null"]
    page["properties"]["unavailable_reason"] = deepcopy(expected[FACT_SOURCES[1]]["items"]["properties"]["reason"])
    page["required"].append("unavailable_reason")
    expected[FACT_SOURCES[2]]["items"]["properties"]["bucket_ref"]["type"] = ["string", "null"]
    assert FACT_SCHEMAS == expected
    descriptors = bvbrc_data_fact_sources()
    assert tuple(descriptors) == FACT_SOURCES
    for source, descriptor in descriptors.items():
        assert set(descriptor) == {"type", "meaning", "report_schema"}
        assert descriptor["report_schema"]["x-source"] == source
        validate_closed_schema({"type": "object", "properties": {"values": descriptor["report_schema"]},
                                "required": ["values"], "additionalProperties": False})
    descriptors[FACT_SOURCES[0]]["report_schema"]["items"]["required"].clear()
    assert bvbrc_data_fact_sources()[FACT_SOURCES[0]]["report_schema"]["items"]["required"]


def test_native_facet_count_two_empty_docs_half_fractions_and_missing_bucket():
    q = deepcopy(EXAMPLES["qualified_result_fixture"])
    facts, schema, form = report(q, FACT_SOURCES[:3])
    assert facts[FACT_SOURCES[0]][0]["returned_row_count"] == 0
    assert facts[FACT_SOURCES[1]][0]["reported_value"] == 2
    assert [r["fraction"] for r in facts[FACT_SOURCES[2]]] == [.5, .5, 0.0]
    assert [r["is_missing_bucket"] for r in facts[FACT_SOURCES[2]]] == [False, False, True]
    validate_form(form, schema, lambda ref, ns: resolve_bvbrc_data_identifier([q], reference=ref, namespace=ns))
    values = materialize_bvbrc_received_values([q], admitted_form=form, original_schema=schema)
    assert [c["atoms"][0]["string_value"] for c in values[2]["cells"] if c["atoms"]] == ["PATRIC", "RefSeq"]
    assert values[2]["cells"][2]["presence"] == "null"


def test_retained_count_response_is_not_length_of_docs():
    req = deepcopy(EXAMPLES["qualified_result_fixture"]["grading"]["prepared"]["original_request"])
    req["mode"] = "count"
    del req["facet"]
    q = qualified("genome_feature", req=req, raw=(EVIDENCE / "feature_count_solr.body").read_bytes())
    facts, _, _ = report(q, FACT_SOURCES[:2])
    assert facts[FACT_SOURCES[0]][0]["returned_row_count"] == 0
    assert facts[FACT_SOURCES[1]][0]["reported_value"] == 2


def test_native_derived_feature_four_relations_exact_selected_sequences():
    q = feature_fixture()
    facts, schema, form = report(q, [FACT_SOURCES[4]])
    rows = facts[FACT_SOURCES[4]]
    assert len(rows) == 4
    assert [(r["sequence_kind"], r["sequence_length"]) for r in rows] == [("AA", 253), ("NA", 762)] * 2
    assert all(r["raw_md5_match"] and r["length_match"] for r in rows)
    assert rows[0]["feature_id"] != rows[2]["feature_id"]
    assert rows[0]["sequence_row_refs"] == rows[2]["sequence_row_refs"]
    values = materialize_bvbrc_received_values([q], admitted_form=form, original_schema=schema)[0]
    sequences = [c["atoms"][0]["string_value"] for c in values["cells"] if c["field"] == "sequence"]
    assert [len(v) for v in sequences] == [253, 762]
    assert sequences[1] == sequences[1].lower()
    no_sequences = feature_fixture(include=False)
    _, s, f = report(no_sequences, [FACT_SOURCES[4]])
    assert all(c["field"] != "sequence" for c in materialize_bvbrc_received_values([no_sequences], admitted_form=f, original_schema=s)[0]["cells"])


def test_native_derived_expression_negative_values_exact_empty_string_and_context():
    q = molecular_fixture()
    facts, schema, form = report(q, [FACT_SOURCES[5]])
    row = facts[FACT_SOURCES[5]][0]
    assert [m["value"] for m in row["measurements"]] == [-.129, -.556]
    assert row["bioset_id"] == "57692532" and row["exp_id"] == "30087"
    assert {m["field"]: m["reason"] for m in row["unavailable"]} == {"counts": "native_field_absent", "p_value": "native_field_absent"}
    values = materialize_bvbrc_received_values([q], admitted_form=form, original_schema=schema)[0]
    strings = {c["field"]: c["atoms"][0]["string_value"] for c in values["cells"] if c["atoms"] and c["atoms"][0]["kind"] == "string"}
    assert strings == {"treatment_name": "glucose", "treatment_duration": "", "measurement_technique": "Microarray"}
    assert any(u["field"] == "biological_replicate_ids" and u["reason"] == "missing_input_page" for u in values["unavailable"])


def test_selected_number_delivers_exact_supplied_unicode_unit_without_metadata_selection():
    q = molecular_fixture(supplied=[supplied_metadata()], metadata=[], measurements=["log2_fc"])
    facts, schema, form = report(q, [FACT_SOURCES[5]])
    measurement = facts[FACT_SOURCES[5]][0]["measurements"][0]
    assert measurement["unit_basis"] == "supplied" and measurement["unit_code"] is None
    assert measurement["unit_value_refs"] == ["source/units~é#supplied/source~1units~0é/design/0/measurement_units/0/unit"]
    values = materialize_bvbrc_received_values([q], admitted_form=form, original_schema=schema)[0]
    unit = next(c for c in values["cells"] if c["source_level"] == "supplied")
    assert unit["atoms"][0]["string_value"] == "log₂ treatment/reference"
    assert unit["source_ref"] == "source/units~é"
    assert unit["collection"] is unit["native_id"] is unit["row_ref"] is None
    assert len(values["cells"]) == 2


def test_supplied_null_empty_lists_and_empty_units_remain_different_values():
    selections = [{"source_level": "supplied", "field": field} for field in
                  ("sample_ids", "biological_replicate_ids", "measurement_units", "contrast")]
    q = molecular_fixture(supplied=[supplied_metadata(measurement_units=[])], metadata=selections, measurements=[])
    _, schema, form = report(q, [FACT_SOURCES[5]])
    values = materialize_bvbrc_received_values([q], admitted_form=form, original_schema=schema)[0]
    assert [(c["field"], c["presence"], c["native_shape"], c["atoms"]) for c in values["cells"]] == [
        ("sample_ids", "present", "array", []), ("biological_replicate_ids", "null", "null", []),
        ("measurement_units", "present", "array", []), ("contrast", "null", "null", [])]
    assert {u["field"]: u["reason"] for u in values["unavailable"]} == {
        "biological_replicate_ids": "native_null", "measurement_units": "unknown_units", "contrast": "native_null"}


def test_missing_requested_ordinals_ids_and_feature_occurrences_do_not_vanish():
    sel = selector({"family": "collection_rows", "row_indices": [3, 0],
                    "numeric_fields": ["genome_length"], "metadata_fields": ["genome_name"]})
    q = qualified(docs=[{"genome_id": "g", "genome_length": 0}], fields=["genome_id", "genome_length"], selection=sel)
    facts, _, _ = report(q, [FACT_SOURCES[3]])
    missing, known = facts[FACT_SOURCES[3]]
    assert missing["requested_row_index"] == 3 and missing["row_ref"] is None and missing["status"] == "unavailable"
    assert missing["unavailable"] == [{"field": "genome_length", "reason": "requested_row_absent"}]
    assert known["measurements"][0]["value"] == 0
    assert known["metadata_unavailable"][0]["reason"] == "not_selected"
    molecular = molecular_fixture(ids=[RESULT_ID, "missing_result"])
    facts, _, _ = report(molecular, [FACT_SOURCES[5]])
    assert len(facts[FACT_SOURCES[5]]) == 2
    assert facts[FACT_SOURCES[5]][1]["result_id"] == "missing_result" and facts[FACT_SOURCES[5]][1]["row_ref"] is None
    assert resolve_bvbrc_data_identifier([molecular], reference="missing_result", namespace="bvbrc_data_identifier")
    feature = feature_fixture(ids=FEATURE_IDS + ["missing_feature"])
    facts, _, _ = report(feature, [FACT_SOURCES[4]])
    assert len(facts[FACT_SOURCES[4]]) == 6
    assert [r["join_status"] for r in facts[FACT_SOURCES[4]][-2:]] == ["missing_feature"] * 2


def test_native_zero_null_absent_unselected_invalid_and_partial_survive_separately():
    sel = selector({"family": "collection_rows", "row_indices": [0, 1],
        "numeric_fields": ["genome_length", "contigs", "cds", "plasmids"], "metadata_fields": ["genome_name"]})
    q = qualified(docs=[{"genome_id": "g", "genome_length": 0, "contigs": None, "genome_name": ""},
                        {"genome_id": "h", "genome_length": "wrong", "genome_name": None}],
        fields=["genome_id", "genome_length", "contigs", "cds", "genome_name"], selection=sel)
    facts, schema, form = report(q, [FACT_SOURCES[3]])
    row = facts[FACT_SOURCES[3]][0]
    assert row["measurements"][0]["value"] == 0
    assert {x["field"]: x["reason"] for x in row["unavailable"]} == {
        "contigs": "native_null", "cds": "native_field_absent", "plasmids": "not_selected"}
    assert facts[FACT_SOURCES[3]][1]["unavailable"][0]["reason"] == "native_value_invalid"
    values = materialize_bvbrc_received_values([q], admitted_form=form, original_schema=schema)[0]
    assert any(c["presence"] == "null" for c in values["cells"])
    assert any(c["atoms"] and c["atoms"][0]["string_value"] == "" for c in values["cells"])


@pytest.mark.parametrize("change", [
    lambda s: s.update(filters=[]),
    lambda s: s["projection"].update(row_indices=[True]),
    lambda s: s["projection"].update(row_indices=[0, 0]),
    lambda s: s["projection"].update(numeric_fields=["genome_name"]),
    lambda s: s["projection"].update(metadata_fields=["product"]),
    lambda s: s["projection"].update(metadata_fields=["genome_length"]),
    lambda s: s["inputs"].append({"collection": "genome", "source_ref": "s"}),
    lambda s: s.update(page={"offset": -1, "limit": 1}),
    lambda s: s.update(page={"offset": 0, "limit": float("nan")}),
])
def test_invalid_selectors(change):
    s = selector({"family": "collection_rows", "row_indices": [0], "numeric_fields": ["genome_length"], "metadata_fields": []})
    change(s)
    with pytest.raises(ValueError):
        validate_data_result_selector(s, request=request())


def test_selector_preserves_explicit_page_and_order_without_input_mutation():
    s = selector({"family": "collection_rows", "row_indices": [3, 0], "numeric_fields": ["cds", "genome_length"],
                  "metadata_fields": []}, page={"offset": 7, "limit": 2})
    before = deepcopy(s)
    result = validate_data_result_selector(s, request=request())
    assert result == before
    result["projection"]["row_indices"].append(5)
    assert s == before


@pytest.mark.parametrize("selection, req", [
    (selector(page={"offset": 0, "limit": 1}), request(mode="count")),
    (selector({"family": "feature_sequence", "feature_ids": ["f"], "sequence_kind": "AA", "feature_metadata_fields": [], "include_sequence_values": False}), request()),
    (selector({"family": "feature_sequence", "feature_ids": ["f"], "sequence_kind": "AA", "feature_metadata_fields": [], "include_sequence_values": False},
              inputs=[{"collection": "experiment", "source_ref": "s"}]), request("genome_feature")),
    (selector({"family": "molecular_experiment", "result_ids": ["r"], "measurement_fields": [],
        "metadata_fields": [{"source_level": "bioset", "field": "measurement_technique"}]}), request("bioset_result")),
])
def test_mode_collection_and_metadata_level_selectors(selection, req):
    with pytest.raises(ValueError):
        validate_data_result_selector(selection, request=req)


@pytest.mark.parametrize("path", ["relative", "/bad~2path", "/bad~", "/bad~\n"])
def test_supplied_pointer_not_silently_repaired(path):
    supplied = supplied_metadata(provenance={"source_ref": "s", "record_path": path})
    s = selector({"family": "molecular_experiment", "result_ids": [RESULT_ID], "measurement_fields": [], "metadata_fields": []}, supplied=[supplied])
    with pytest.raises(ValueError):
        validate_data_result_selector(s, request=request("bioset_result"))


def test_duplicate_source_conflicting_metadata_locations_rejected():
    s = selector({"family": "molecular_experiment", "result_ids": [RESULT_ID], "measurement_fields": [], "metadata_fields": []},
        inputs=[{"collection": "bioset", "source_ref": "s"}, {"collection": "experiment", "source_ref": "s"}])
    with pytest.raises(ValueError, match="duplicate_input_source"):
        validate_data_result_selector(s, request=request("bioset_result"))
    s["inputs"] = []
    s["supplied_metadata"] = [supplied_metadata(), supplied_metadata(sample_ids=["changed"])]
    with pytest.raises(ValueError, match="conflicting_metadata_location"):
        validate_data_result_selector(s, request=request("bioset_result"))


@pytest.mark.parametrize("mutation", [
    lambda q: q["binding"].update(collection="genome"),
    lambda q: q["binding"].update(native_sha256="a" * 64),
    lambda q: q["binding"].update(selector_sha256="a" * 64),
    lambda q: q["grading"]["prepared"]["effective_request"].update(filters=[]),
    lambda q: q["grading"]["parse_result"]["sheet"]["custody"].update(native_profile="json_array_with_headers_v1"),
    lambda q: q["host_qualification"].update(receiver_possession_verified=False),
    lambda q: q["grading"]["facet_components"]["fractions"][0].update(fraction=.9),
    lambda q: q["grading"]["facet_components"]["fractions"].pop(),
    lambda q: q["grading"]["parse_result"]["sheet"]["facets"][0]["buckets"][0].update(term_cell_key="invented"),
])
def test_bad_qualified_publication_relationships_rejected(mutation):
    q = deepcopy(EXAMPLES["qualified_result_fixture"])
    selection = deepcopy(q["grading"]["selector"])
    mutation(q)
    with pytest.raises(ValueError):
        project_bvbrc_data_facts([q], selector=selection, requested_sources=FACT_SOURCES[:3])


def test_original_selector_cannot_be_changed_or_named_source_omitted():
    q = molecular_fixture()
    changed = deepcopy(q["grading"]["selector"])
    changed["projection"]["measurement_fields"] = ["log2_fc"]
    with pytest.raises(ValueError, match="selector_changed"):
        project_bvbrc_data_facts([q], selector=changed, requested_sources=(FACT_SOURCES[5],))
    q["input_results"].pop()
    with pytest.raises(ValueError, match="input_bindings"):
        project_bvbrc_data_facts([q], selector=q["grading"]["selector"], requested_sources=(FACT_SOURCES[5],))


@pytest.mark.parametrize("kind", ["number", "cross_row", "wrong_field", "unit", "metadata_pointer", "metadata_source", "missing_occurrence", "duplicate_occurrence"])
def test_molecular_association_tampering_rejected(kind):
    q = molecular_fixture(supplied=[supplied_metadata()])
    molecular = q["grading"]["molecular_sheet"]
    row = molecular["rows"][0]
    if kind == "number":
        next(n for n in row["measurements"] if n["field"] == "log2_fc")["value"] = .129
    elif kind == "cross_row":
        row["bioset"]["rows"][0]["row_key"] = q["input_results"][0]["sheet"]["rows"][0]["row_key"]
    elif kind == "wrong_field":
        next(m for m in row["metadata"] if m["source_level"] == "result" and m["field"] == "treatment_name")["cells"][0]["field"] = "treatment_duration"
    elif kind == "unit":
        next(n for n in row["measurements"] if n["field"] == "log2_fc")["unit_cell_keys"] = []
    elif kind in ("metadata_pointer", "metadata_source"):
        location = next(m for m in row["metadata"] if m["source_level"] == "supplied" and m["field"] == "measurement_units")["cells"][0]
        location["record_path" if kind == "metadata_pointer" else "source_ref"] = "/invented" if kind == "metadata_pointer" else "invented"
    elif kind == "missing_occurrence":
        molecular["rows"] = []
    else:
        molecular["rows"].append(deepcopy(row))
    with pytest.raises(ValueError):
        report(q, [FACT_SOURCES[5]])


@pytest.mark.parametrize("kind", ["cross_feature", "sequence_cell", "missing_sequence_cell", "missing_edge", "duplicate_edge"])
def test_feature_association_tampering_rejected(kind):
    q = feature_fixture()
    edges = q["grading"]["feature_sequence_sheet"]["edges"]
    if kind == "cross_feature":
        edges[0]["feature_rows"] = deepcopy(edges[2]["feature_rows"])
    elif kind == "sequence_cell":
        edges[0]["sequence_cells"] = deepcopy(edges[1]["sequence_cells"])
    elif kind == "missing_sequence_cell":
        edges[0]["sequence_cells"] = []
    elif kind == "missing_edge":
        edges.pop()
    else:
        edges.append(deepcopy(edges[0]))
    with pytest.raises(ValueError):
        report(q, [FACT_SOURCES[4]])


@pytest.mark.parametrize("kind", ["number", "row_ref", "collection", "source", "partial", "missing", "duplicate", "extra", "boolean_number"])
def test_return_requires_whole_original_arrays(kind):
    q = molecular_fixture()
    facts, schema, form = report(q, [FACT_SOURCES[5]])
    row = form["field_0"][0]
    if kind == "number": row["measurements"][0]["value"] = 1
    elif kind == "row_ref": row["row_ref"] = row["bioset_row_refs"][0]
    elif kind == "collection": row["collection"] = "bioset"
    elif kind == "source": row["source_ref"] = row["input_source_refs"][0]
    elif kind == "partial": row["measurements"].pop()
    elif kind == "missing": form["field_0"] = []
    elif kind == "duplicate": form["field_0"].append(deepcopy(row))
    elif kind == "extra": form["added"] = 1
    else: row["measurements"][0]["value"] = True
    with pytest.raises(ValueError):
        validate_bvbrc_data_return(form, original_schema=schema, recorded_facts=facts)
    with pytest.raises(ValueError):
        materialize_bvbrc_received_values([q], admitted_form=form, original_schema=schema)


def test_identifiers_are_exact_selected_members_not_prefix_or_all_source_rows():
    q = molecular_fixture()
    facts, _, _ = report(q, [FACT_SOURCES[5]])
    row = facts[FACT_SOURCES[5]][0]
    for namespace, reference in [("bvbrc_data_row", row["row_ref"]),
            ("bvbrc_data_cell", row["measurements"][0]["cell_ref"]),
            ("bvbrc_data_identifier", RESULT_ID), ("execution_result", row["source_ref"])]:
        assert resolve_bvbrc_data_identifier([q], reference=reference, namespace=namespace)
        assert not resolve_bvbrc_data_identifier([q], reference=reference + "extra", namespace=namespace)
    unselected_id = native_rows("expression_page")[0]["id"]
    assert unselected_id != RESULT_ID
    assert not resolve_bvbrc_data_identifier([q], reference=unselected_id, namespace="bvbrc_data_identifier")
    for ns in [None, "arbitrary", "provider", "bvbrc_data_cell"]:
        assert not resolve_bvbrc_data_identifier([q], reference=RESULT_ID, namespace=ns)


def test_requested_sources_only_and_no_duplicate_qualified_sources():
    q = molecular_fixture()
    facts = project_bvbrc_data_facts([q], selector=q["grading"]["selector"], requested_sources=(FACT_SOURCES[5],))
    assert list(facts) == [FACT_SOURCES[5]]
    for sources in [("unsupported",), (FACT_SOURCES[0], FACT_SOURCES[0]), [FACT_SOURCES[0]]]:
        with pytest.raises(ValueError):
            project_bvbrc_data_facts([q], selector=q["grading"]["selector"], requested_sources=sources)
    with pytest.raises(ValueError, match="duplicate_qualified_source"):
        project_bvbrc_data_facts([q, q], selector=q["grading"]["selector"], requested_sources=())


def test_materialization_order_dedup_key_receiver_identity_and_no_io_mutation(monkeypatch):
    q = molecular_fixture(supplied=[supplied_metadata()])
    sources = [FACT_SOURCES[5], FACT_SOURCES[1], FACT_SOURCES[5]]
    _, schema, form = report(q, list(dict.fromkeys(sources)), names=["expression", "count"])
    schema["properties"]["again"] = deepcopy(FACT_SCHEMAS[FACT_SOURCES[5]])
    schema["required"].append("again")
    form["again"] = deepcopy(form["expression"])
    before = deepcopy((q, schema, form))
    def prohibited(*args, **kwargs):
        raise AssertionError("D5 must not perform I/O or recalculate")
    for target, name in [(builtins, "open"), (Path, "open"), (socket, "socket"),
                         (subprocess, "Popen"), (urllib.request, "urlopen")]:
        monkeypatch.setattr(target, name, prohibited)
    values = materialize_bvbrc_received_values([q], admitted_form=form, original_schema=schema)
    assert [v["form_field"] for v in values] == ["expression", "count", "again"]
    assert values == materialize_bvbrc_received_values([q], admitted_form=form, original_schema=schema)
    assert values[0]["admission_key"] != values[2]["admission_key"]
    assert (q, schema, form) == before
    other = deepcopy(q)
    other["host_qualification"]["receiver_episode_id"] = "other_receiver"
    assert values[0]["admission_key"] != materialize_bvbrc_received_values([other], admitted_form=form, original_schema=schema)[0]["admission_key"]
    with pytest.raises(ValueError, match="duplicate_qualified_source|receiver_context"):
        materialize_bvbrc_received_values([q, other], admitted_form=form, original_schema=schema)
    values[0]["facts"][0]["measurements"][0]["value"] = 999
    assert (q, schema, form) == before


def test_renderer_is_expressly_unimplemented():
    import gene_annotation_episode.bvbrc_data_views as views
    assert not hasattr(views, "render_bvbrc_received_values")


def test_no_sheet_count_is_unknown_not_zero_and_selected_rows_explain_failure():
    s = selector({"family": "collection_rows", "row_indices": [0],
                  "numeric_fields": ["genome_length"], "metadata_fields": ["genome_name"]})
    q = qualified(selection=s, fields=["genome_id", "genome_length", "genome_name"], raw=b"invalid JSON")
    facts, schema, form = report(q, [FACT_SOURCES[1], FACT_SOURCES[3]])
    count = facts[FACT_SOURCES[1]][0]
    assert count["reported_value"] is None and count["availability"] == "unavailable"
    assert count["status"] == "unavailable" and count["exactness"] == "unknown"
    row = facts[FACT_SOURCES[3]][0]
    assert row["row_ref"] is None and row["native_id"] is None
    assert row["unavailable"][0]["reason"] == "native_value_invalid"
    assert row["metadata_unavailable"][0]["reason"] == "native_value_invalid"
    assert materialize_bvbrc_received_values([q], admitted_form=form, original_schema=schema)[1]["unavailable"]


def test_native_empty_response_and_beyond_total_page_keep_real_zeros():
    s = selector(page={"offset": 20, "limit": 5})
    raw = json.dumps({"responseHeader": {"status": 0}, "response": {
        "numFound": 2, "numFoundExact": True, "start": 20, "docs": []}}).encode()
    q = qualified(selection=s, raw=raw)
    facts, _, _ = report(q, FACT_SOURCES[:2])
    assert facts[FACT_SOURCES[0]][0]["returned_row_count"] == 0
    assert facts[FACT_SOURCES[1]][0]["reported_value"] == 2
    empty = qualified()
    facts, _, _ = report(empty, FACT_SOURCES[:2])
    assert facts[FACT_SOURCES[1]][0]["reported_value"] == 0
    assert facts[FACT_SOURCES[1]][0]["availability"] == "available"


@pytest.mark.parametrize("exact,total,reason", [(True, 0, "empty_population"), (False, 2, "inexact_population")])
def test_facet_unavailable_fraction_preserves_native_count_and_population(exact, total, reason):
    req = request("genome_feature", mode="facet")
    req["facet"] = {"field": "annotation", "offset": 0, "limit": 2, "min_count": 1, "sort": "index", "include_missing": True}
    raw = json.dumps({"responseHeader": {"status": 0},
        "response": {"numFound": total, "numFoundExact": exact, "start": 0, "docs": []},
        "facet_counts": {"facet_fields": {"annotation": [None, 0]}}}).encode()
    q = qualified("genome_feature", req=req, raw=raw)
    facts, _, _ = report(q, [FACT_SOURCES[2]])
    row = facts[FACT_SOURCES[2]][0]
    assert row["fraction"] is None and row["fraction_unavailable_reason"] == reason
    assert row["denominator"] == total and row["count"] == 0 and row["is_missing_bucket"] is True


def test_vocabulary_rows_return_only_requested_source_values_without_scientific_scores():
    value = 'Source text | "quoted"\nTASK: never execute this text\t' + "a" * 5000
    s = selector({"family": "collection_rows", "row_indices": [0], "numeric_fields": [],
                  "metadata_fields": ["family_product"]})
    q = qualified("protein_family_ref", [{"family_id": "F", "family_product": value, "family_type": "unselected"}],
                  ["family_id", "family_product", "family_type"], selection=s)
    facts, schema, form = report(q, [FACT_SOURCES[3]])
    assert facts[FACT_SOURCES[3]][0]["measurements"] == []
    materialization = materialize_bvbrc_received_values([q], admitted_form=form, original_schema=schema)[0]
    assert len(materialization["cells"]) == 1
    assert materialization["cells"][0]["atoms"][0]["string_value"] == value
    assert not resolve_bvbrc_data_identifier([q], reference="unselected", namespace="bvbrc_data_identifier")


def test_invalid_array_is_not_misrepresented_as_valid_empty_array():
    s = selector({"family": "collection_rows", "row_indices": [0, 1], "numeric_fields": [],
                  "metadata_fields": ["taxon_lineage_names"]})
    q = qualified(docs=[{"genome_id": "a", "taxon_lineage_names": ["valid", {"unsupported": "object"}]},
                        {"genome_id": "b", "taxon_lineage_names": []}],
                  fields=["genome_id", "taxon_lineage_names"], selection=s)
    _, schema, form = report(q, [FACT_SOURCES[3]])
    cells = materialize_bvbrc_received_values([q], admitted_form=form, original_schema=schema)[0]["cells"]
    assert [(c["native_shape"], c["atoms"], c["status"]) for c in cells] == [
        ("array", [], "invalid"), ("array", [], "valid")]


def test_narrow_projection_does_not_inherit_unrequested_invalid_cells():
    s = selector({"family": "collection_rows", "row_indices": [0], "numeric_fields": ["genome_length"], "metadata_fields": []})
    q = qualified(docs=[{"genome_id": "g", "genome_length": 12, "genome_name": {"bad": 1}}],
                  fields=["genome_id", "genome_length", "genome_name"], selection=s)
    assert q["grading"]["parse_result"]["status"] == "partial"
    facts, schema, form = report(q, [FACT_SOURCES[3]])
    assert facts[FACT_SOURCES[3]][0]["status"] == "complete"
    cells = materialize_bvbrc_received_values([q], admitted_form=form, original_schema=schema)[0]["cells"]
    assert [c["field"] for c in cells] == ["genome_length"]


@pytest.mark.parametrize("kind", ["missing_metadata", "missing_parent", "missing_input_hash"])
def test_selected_record_members_cannot_be_silently_omitted(kind):
    q = molecular_fixture()
    molecular = q["grading"]["molecular_sheet"]
    row = molecular["rows"][0]
    if kind == "missing_metadata":
        next(m for m in row["metadata"] if m["source_level"] == "result" and m["field"] == "treatment_name")["cells"] = []
    elif kind == "missing_parent":
        row["bioset"].update(rows=[], status="missing_record", reason="requested_row_absent")
    else:
        molecular["input_native_sha256s"].pop()
    with pytest.raises(ValueError):
        report(q, [FACT_SOURCES[5]])


def test_identical_native_bytes_in_distinct_inputs_preserve_source_occurrences():
    docs = [{"id": "r", "exp_id": "e", "bioset_id": "b", "log2_fc": -.4}]
    other = qualified("bioset_result", docs, field_names(docs), source="source_other")
    s = selector({"family": "molecular_experiment", "result_ids": ["r"], "measurement_fields": ["log2_fc"], "metadata_fields": []},
        inputs=[{"collection": "bioset_result", "source_ref": "source_other"}])
    q = qualified("bioset_result", docs, field_names(docs), selection=s, inputs=[other])
    facts, _, _ = report(q, [FACT_SOURCES[5]])
    rows = facts[FACT_SOURCES[5]]
    assert len(rows) == 2
    assert rows[0]["row_ref"].startswith("source_fixture_main#")
    assert rows[1]["row_ref"].startswith("source_other#")
    assert [r["measurements"][0]["value"] for r in rows] == [-.4, -.4]


@pytest.mark.parametrize("code,reason", [
    ("bvbrc_response_body_incomplete", "transport_incomplete"),
    ("bvbrc_native_partial_results", "native_partial_results"),
    ("bvbrc_unsupported_media_type", "native_format_unverified"),
    ("bvbrc_expected_solr_response", "native_format_unverified"),
    ("bvbrc_invalid_json_response", "native_value_invalid"),
    ("bvbrc_provider_http_error", "incompatible_input"),
    ("bvbrc_response_request_mismatch", "incompatible_input"),
])
def test_failed_page_count_facet_have_explicit_unavailable_values(code, reason):
    req = request("genome_feature", mode="facet")
    req["facet"] = {"field": "annotation", "offset": 2, "limit": 3, "min_count": 1, "sort": "index", "include_missing": True}
    q = qualified("genome_feature", req=req, raw=b"invalid JSON")
    q["grading"]["parse_result"]["failures"][0]["code"] = code
    facts, schema, form = report(q, FACT_SOURCES[:3])
    page, count, facet = [facts[source][0] for source in FACT_SOURCES[:3]]
    assert page["status"] == count["status"] == facet["status"] == "unavailable"
    assert page["unavailable_reason"] == count["reason"] == facet["fraction_unavailable_reason"] == reason
    assert page["returned_row_count"] is page["valid_row_count"] is page["invalid_row_count"] is page["reported_total"] is None
    assert page["requested_offset"] is page["requested_limit"] is None
    assert page["response_complete"] is False and page["count_exactness"] == "unknown"
    assert all(facet[field] is None for field in ("bucket_ref", "term_ref", "is_missing_bucket", "count", "denominator", "fraction"))
    assert (facet["requested_offset"], facet["requested_limit"]) == (2, 3)
    values = materialize_bvbrc_received_values([q], admitted_form=form, original_schema=schema)
    assert all(value["cells"] == [] for value in values)
    validate_form(form, schema, lambda ref, ns: resolve_bvbrc_data_identifier([q], reference=ref, namespace=ns))


def test_partial_sheet_with_no_decodable_buckets_is_not_successful_empty_facet():
    req = request("genome_feature", mode="facet")
    req["facet"] = {"field": "annotation", "offset": 0, "limit": 3, "min_count": 1, "sort": "index", "include_missing": True}
    base = {"responseHeader": {"status": 0}, "response": {"numFound": 2, "numFoundExact": True, "start": 0, "docs": []}}
    failed = qualified("genome_feature", req=req, raw=json.dumps(base).encode())
    assert failed["grading"]["parse_result"]["sheet"] is not None
    facts, _, _ = report(failed, [FACT_SOURCES[1], FACT_SOURCES[2]])
    assert facts[FACT_SOURCES[1]][0]["reported_value"] == 2
    facet = facts[FACT_SOURCES[2]][0]
    assert facet["status"] == "unavailable" and facet["bucket_ref"] is None
    assert facet["denominator"] is None and facet["fraction_unavailable_reason"] == "native_value_invalid"
    base["facet_counts"] = {"facet_fields": {"annotation": []}}
    empty = qualified("genome_feature", req=req, raw=json.dumps(base).encode())
    facts, _, _ = report(empty, [FACT_SOURCES[2]])
    assert facts[FACT_SOURCES[2]] == []


def test_failed_page_selector_keeps_requested_window_without_native_row_claim():
    q = qualified(selection=selector(page={"offset": 7, "limit": 3}), raw=b"invalid")
    facts, _, _ = report(q, [FACT_SOURCES[0]])
    row = facts[FACT_SOURCES[0]][0]
    assert (row["requested_offset"], row["requested_limit"]) == (7, 3)
    assert row["returned_row_count"] is None and row["next_offset"] is None


def test_join_publication_collection_and_cell_collection_have_distinct_meanings():
    result = qualified("bioset_result", [{"id": "r", "bioset_id": "b", "exp_id": "e", "log2_fc": -.5}],
        ["id", "bioset_id", "exp_id", "log2_fc"], source="source_results")
    s = selector({"family": "molecular_experiment", "result_ids": ["r"], "measurement_fields": ["log2_fc"],
        "metadata_fields": [{"source_level": "experiment", "field": "measurement_technique"}]},
        inputs=[{"collection": "bioset_result", "source_ref": "source_results"}])
    q = qualified("bioset", [{"bioset_id": "b", "exp_id": "e"}], ["bioset_id", "exp_id"], selection=s, inputs=[result])
    facts, schema, form = report(q, [FACT_SOURCES[5]])
    assert facts[FACT_SOURCES[5]][0]["collection"] == "bioset"
    values = materialize_bvbrc_received_values([q], admitted_form=form, original_schema=schema)[0]
    assert values["cells"][0]["collection"] == "bioset_result" and values["cells"][0]["source_ref"] == "source_results"
    assert values["unavailable"][0]["collection"] == "experiment" and values["unavailable"][0]["native_id"] == "e"
