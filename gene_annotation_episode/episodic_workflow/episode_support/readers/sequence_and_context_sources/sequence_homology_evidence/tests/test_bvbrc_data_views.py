"""D5 pure return tests; host admissions here are explicitly synthetic.

The facet bytes are the retained native response. Feature/molecular values are
copied from retained native arrays into labeled synthetic Solr envelopes for
these pure view tests. Neither fixture confers real host custody or establishes
a new v2 acquisition, a durable admission, or an episode/model input path.
"""
from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.sequence_homology_evidence.acquisition import SourceSnapshot
from gene_annotation_episode.episodic_workflow.episode_support.calculations.sequence_homology_evidence.bvbrc_data_calculators import calculate_facet_fractions, calculate_feature_sequence_counts, calculate_page_counts
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_and_context_sources.sequence_homology_evidence.bvbrc_data_feature_sequences import extract_feature_sequence_join
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_and_context_sources.sequence_homology_evidence.bvbrc_data_molecular import extract_molecular_experiment_rows
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.sequence_and_context_sources.sequence_homology_evidence.bvbrc_data_query import encode_native_query
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_and_context_sources.sequence_homology_evidence.bvbrc_data_readers import parse_data_snapshot
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_and_context_sources.bvbrc_data_schema import json_digest, validate
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_and_context_sources.sequence_homology_evidence.bvbrc_data_views import FACT_SCHEMAS, FACT_SOURCES, materialize_bvbrc_received_values, project_bvbrc_data_facts, resolve_bvbrc_data_identifier, validate_data_result_selector
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.communication import validate_form, form_with_facts
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.execution_contracts import digest

BASE = "https://www.bv-brc.org/api"
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


def field_names(docs):
    return list(dict.fromkeys(field for row in docs for field in row))


def supplied_metadata(**changes):
    return {"result_id": RESULT_ID, "bioset_id": "57692532",
        "provenance": {"source_ref": "source/units~é", "record_path": "/design/0"},
        "sample_ids": [], "biological_replicate_ids": None, "technical_replicate_ids": [],
        "measurement_units": [{"field": "log2_fc", "unit": "log₂ treatment/reference"}],
        "normalization_method": None, "pvalue_correction_method": None, "contrast": None, **changes}


def report(q, sources, *, names=None):
    facts = project_bvbrc_data_facts([q], selector=q["grading"]["selector"], requested_sources=tuple(sources))
    names = names or ["field_" + str(i) for i in range(len(sources))]
    schema = {"type": "object", "properties": {n: deepcopy(FACT_SCHEMAS[s]) for n, s in zip(names, sources)},
              "required": names, "additionalProperties": False}
    form = form_with_facts({}, schema, facts)
    return facts, schema, form


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


def test_renderer_is_expressly_unimplemented():
    import gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_and_context_sources.sequence_homology_evidence.bvbrc_data_views as views
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
