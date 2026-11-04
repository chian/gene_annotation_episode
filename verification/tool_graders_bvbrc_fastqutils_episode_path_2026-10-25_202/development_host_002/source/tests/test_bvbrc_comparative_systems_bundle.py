"""Real N/D/C provider integration with labelled source-executed fixtures.

These wrappers are synthetic unit inputs, not actual host admission or a live
ComparativeSystems service run. Every scientific number comes through N/D/C.
"""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import socket
import subprocess
import urllib.request

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import bvbrc_comparative_systems_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_comparative_systems_bundle_projection import validate_saved_comparative_systems_projection
from gene_annotation_episode.bvbrc_comparative_systems_handoff_contracts import canonical_sha256

FIXTURES = Path(__file__).parent / "fixtures" / "bvbrc_comparative_systems_bundle"
INPUTS = json.loads((FIXTURES / "inputs.json").read_text())


def field(name, selector, availability="typed_state", cardinality=1):
    return {"field_id": name, "selector": selector, "expected_cardinality": cardinality,
            "availability_requirement": availability}


def form(*fields):
    return adapter.requested_form_schema({"version": "bvbrc_comparative_systems_requested_selection_v1", "fields": list(fields)})


def arguments(name="pathway_subsystem", *, native_only=False):
    saved = deepcopy(INPUTS[name])
    saved.pop("classification")
    saved["artifact_bytes"] = {key: (FIXTURES / filename).read_bytes() for key, filename in saved.pop("byte_files").items()}
    for key in ("qualified_data_inputs", "qualified_producer_evidence"):
        saved[key] = tuple(saved[key])
    if native_only:
        saved["parameters"]["supplied_data_selection"] = None
        saved["qualified_data_inputs"] = ()
        saved["parameters"]["calculation_parameters"]["requests"] = [row for row in saved["parameters"]["calculation_parameters"]["requests"]
            if row["view_selection"]["kind"] == "native_view"]
    requests = saved["parameters"]["calculation_parameters"]["requests"]
    saved["requested_form"] = form(*(field(row["component_id"], {"kind": "computed_measurement", "component_id": row["component_id"]}) for row in requests))
    return saved


def empty_failure_context():
    return {"retained_requirements": [], "retained_diagnostics": [], "failure_status": None}


def save_validate(result, args, *, failure_context=None):
    validate_saved_comparative_systems_projection(result["sheet"], result["components"],
        **{key: result[key] for key in ("facts", "status", "missing_requirements", "diagnostics")},
        **{key: args[key] for key in ("requested_form", "parameters", "bundle")}, original_task=args["bundle"]["original_task"],
        failure_context=empty_failure_context() if failure_context is None else failure_context)


def replace_bytes(args, document_id, raw):
    selected = next(row for row in args["parameters"]["document_selection"]["documents"] if row["document_id"] == document_id)
    member = next(row for row in args["bundle"]["artifacts"] if row["source_ref"] == selected["input"]["source_ref"])
    member.update(byte_count=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    member["transfer"]["total_size"] = len(raw)
    args["artifact_bytes"][member["raw_artifact_ref"]] = raw


def measurement(args, *, field_id="native", view="pathway_summary", native_field="reported_ec_conservation_percent", availability="typed_state", cardinality=1):
    request = next(row for row in args["parameters"]["calculation_parameters"]["requests"] if row["entity"]["kind"] == "pathway")
    return field(field_id, {"kind": "measurement", "view_id": view, "entity": request["entity"], "native_field": native_field}, availability, cardinality)


def forbidden(*args, **kwargs):
    raise AssertionError("acquisition, process, storage or model call forbidden")


def replace_data(args, *, docs=None, total=None, exact=True, partial=False, complete=True):
    """Build a changed real Data reader result; no ComparativeSystems mock."""
    from gene_annotation_episode.acquisition import SourceSnapshot
    from gene_annotation_episode.bvbrc_data_calculators import calculate_page_counts
    from gene_annotation_episode.bvbrc_data_readers import parse_data_snapshot
    wrapper = args["qualified_data_inputs"][0]
    grading = wrapper["qualified_result"]["grading"]
    prepared = grading["prepared"]
    rb = wrapper["raw_binding"]
    body = json.loads(args["artifact_bytes"][rb["bytes_key"]])
    if docs is not None:
        body["response"]["docs"] = docs
    body["response"].update(numFound=len(body["response"]["docs"]) if total is None else total, numFoundExact=exact)
    body["responseHeader"]["partialResults"] = partial
    raw = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode()
    source = SourceSnapshot("bvbrc_data", prepared["native_request"]["url"], prepared["effective_request"],
        "SYNTHETIC_NOT_ACQUIRED", raw, "application/solr+json", {
            "request": {key: prepared["native_request"][key] for key in ("method", "url", "headers", "body")},
            "effective_url": prepared["native_request"]["url"], "automatic_redirects": False,
            "response": {"status": 200, "headers": [], "body_complete": complete}})
    parsed = parse_data_snapshot(source, prepared=prepared)
    grading.update(parse_result=parsed, page_components=calculate_page_counts(parsed["sheet"]) if parsed["sheet"] else None)
    rb.update(sha256=hashlib.sha256(raw).hexdigest(), byte_count=len(raw))
    wrapper["qualified_result"]["binding"]["native_sha256"] = rb["sha256"]
    binding = next(item for item in args["bundle"]["supplied_contents"] if item["source_ref"] == rb["source_ref"])
    binding.update(sha256=rb["sha256"], byte_count=len(raw))
    args["artifact_bytes"][rb["bytes_key"]] = raw
    return body["response"]["docs"]


def add_reference_data(args, docs, *, collection="pathway_ref", total=None, partial=False,
                       source="synthetic_reference", offset=0, select_existing=False, filters=None):
    """Supply labelled native bytes through the delivered Data reader and D port."""
    from gene_annotation_episode.acquisition import SourceSnapshot
    from gene_annotation_episode.bvbrc_data_calculators import calculate_page_counts
    from gene_annotation_episode.bvbrc_data_query import encode_native_query
    from gene_annotation_episode.bvbrc_data_readers import parse_data_snapshot
    from gene_annotation_episode.execution_contracts import digest
    template = INPUTS["pathway_subsystem"]["qualified_data_inputs"][0]
    wrapper = deepcopy(template)
    grading = wrapper["qualified_result"]["grading"]
    request = deepcopy(grading["prepared"]["original_request"])
    fields = (["id", "pathway_id", "ec_number", "map_name", "map_type"] if collection == "pathway_ref" else
              ["id", "subsystem_id", "subsystem_name", "superclass", "class", "subclass", "role_id", "role_name"])
    entity_field, identifier = ("pathway_id", "P_TEST") if collection == "pathway_ref" else ("subsystem_id", "S_TEST")
    request.update(collection=collection, offset=offset, fields=fields,
                   filters=filters if filters is not None else [{"field": entity_field, "operator": "eq", "value": identifier}])
    prepared = encode_native_query(request, base_url="https://www.bv-brc.org/api")
    body = {"responseHeader": {"status": 0, "partialResults": partial}, "response": {
        "start": offset, "numFound": len(docs) if total is None else total, "numFoundExact": True, "docs": docs}}
    raw = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode()
    snapshot = SourceSnapshot("bvbrc_data", prepared["native_request"]["url"], prepared["effective_request"],
        "SYNTHETIC_NOT_ACQUIRED", raw, "application/solr+json", {
            "request": {key: prepared["native_request"][key] for key in ("method", "url", "headers", "body")},
            "effective_url": prepared["native_request"]["url"], "automatic_redirects": False,
            "response": {"status": 200, "headers": [], "body_complete": True}})
    parsed = parse_data_snapshot(snapshot, prepared=prepared)
    grading.update(prepared=prepared, parse_result=parsed, page_components=calculate_page_counts(parsed["sheet"]))
    artifact = source + "_bytes"
    sha = hashlib.sha256(raw).hexdigest()
    wrapper["qualified_result"]["binding"].update(source_ref=source, native_artifact_ref=artifact,
        native_sha256=sha, grading_artifact_ref=source + "_grade", collection=collection,
        selector_sha256=digest(grading["selector"]))
    wrapper["raw_binding"] = {"source_ref": source, "raw_artifact_ref": artifact,
        "sha256": sha, "byte_count": len(raw), "bytes_key": artifact}
    args["qualified_data_inputs"] += (wrapper,)
    args["artifact_bytes"][artifact] = raw
    args["bundle"]["supplied_contents"].append({"source_ref": source, "artifact_field": "artifact_ref", "artifact_ref": artifact,
        "sha256": sha, "byte_count": len(raw)})
    selected = deepcopy(INPUTS["pathway_subsystem"]["parameters"]["supplied_data_selection"]["record_sets"][0])
    selected.update(record_set_id=source + "_records", collection=collection, source_refs=[source],
        query_population_key=prepared["query_population"]["population_key"], selected_fields=fields,
        sort=request["sort"], annotation_filter="none", release=None,
        roles=["pathway_reference" if collection == "pathway_ref" else "subsystem_reference"])
    population = selected["declared_genome_population"]
    population.update(population_id=source + "_genomes", members=[])
    for key in ("raw_occurrence_count", "distinct_valid_member_count"):
        population[key].update(value=0, population_id=population["population_id"])
    location = {"source_ref": source, "raw_artifact_ref": artifact, "document_id": None,
                "json_pointer": "/response/docs", "table": None, "row_ordinal": None,
                "column_ordinal": None, "native_field": None}
    selected["snapshot_evidence"] = {"kind": "single_complete_response", "snapshot_id": None,
                                     "source_locations": [deepcopy(location)]}
    if args["parameters"]["supplied_data_selection"] is None:
        args["parameters"]["supplied_data_selection"] = {
            "version": "bvbrc_comparative_systems_data_selection_v1", "record_sets": []}
    records = args["parameters"]["supplied_data_selection"]["record_sets"]
    if select_existing:
        records[-1]["source_refs"].append(source)
        records[-1]["snapshot_evidence"] = {"kind": "unknown", "snapshot_id": None, "source_locations": []}
    else:
        records.append(selected)
    return location


def reference_arguments(*, docs=None, collection="pathway_ref", members=None, map_id=None, total=None, partial=False, filters=None):
    args = arguments()
    subsystem = collection == "subsystem_ref"
    if docs is None:
        docs = ([{"id": "reference_roles", "subsystem_id": "S_TEST", "subsystem_name": "Synthetic subsystem",
                  "superclass": "synthetic", "class": "Synthetic class", "subclass": "Synthetic subclass",
                  "role_id": ["r2", "r1", "r3"], "role_name": ["independent third", "independent first"]}] if subsystem else
                [{"id": "ref_" + str(i), "pathway_id": "P_TEST", "ec_number": f"{i}.{i}.{i}.{i}",
                  "map_name": "Synthetic pathway", "map_type": "KEGG"} for i in range(1, 5)])
    location = add_reference_data(args, docs, collection=collection, total=total, partial=partial, filters=filters)
    requests = args["parameters"]["calculation_parameters"]["requests"]
    native = deepcopy(next(row for row in requests if row["component_id"] ==
                           ("retained_subsystem_percent" if subsystem else "retained_pathway_percent")))
    reference = {"membership_id": "verified_reference", "component_kind": "role_id" if subsystem else "ec_number",
        "entity": deepcopy(native["entity"]), "members": members if members is not None else
            (["r1", "r2", "r3"] if subsystem else [f"{i}.{i}.{i}.{i}" for i in range(1, 5)]),
        "map_id": map_id, "release": None, "completeness": "complete_for_declared_population",
        "basis": "supplied_data_api", "source_locations": [location], "qualification_codes": []}
    args["parameters"]["reference_memberships"] = [reference]
    native.update(component_id="native_reference", quantity="reference_component_representation",
                  reference_membership_id="verified_reference")
    requests.append(native)
    if not subsystem:
        later = deepcopy(next(row for row in requests if row["component_id"] == "later_pathway_percent"))
        later.update(component_id="later_reference", quantity="reference_component_representation",
                     reference_membership_id="verified_reference")
        requests.append(later)
    args["requested_form"] = form(measurement(args, availability="available_value"),
        field("reference", {"kind": "ratio", "component_id": "native_reference"}, "available_complete_population"),
        *( [field("later", {"kind": "ratio", "component_id": "later_reference"}, "available_complete_population")] if not subsystem else []))
    return args


def test_actual_provider_numbers_keep_native_and_later_populations_separate(monkeypatch):
    args = arguments()
    args["requested_form"] = form(measurement(args), field("retained", {"kind": "ratio", "component_id": "retained_pathway_percent"}),
        field("later", {"kind": "ratio", "component_id": "later_pathway_percent"}),
        field("active", {"kind": "computed_measurement", "component_id": "unambiguous_active_genomes"}),
        field("status", {"kind": "request_status"}))
    snapshot = deepcopy(args)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    result = adapter.consume_bundle(**args)
    assert args == snapshot
    assert result["status"] == "ok"
    native, retained, later = [result["facts"][name]["values"][0] for name in ("native", "retained", "later")]
    assert native["value"] == retained["output"]["value"] == 75
    assert retained["numerator"]["value"] == 3 and retained["denominator"]["value"] == 2 * 2
    assert later["numerator"]["value"] == 4 and later["denominator"]["value"] == 3 * 3
    assert later["output"]["value"] == pytest.approx(400 / 9)
    assert retained["genome_population_id"] != later["genome_population_id"]
    assert result["facts"]["active"]["values"][0]["value"] == 0
    assert result["facts"]["active"]["values"][0]["state"] == "available"
    assert result["facts"]["status"]["values"] == [{"status": "satisfied", "affected_field_ids": []}]
    assert not list(Draft202012Validator(args["requested_form"]).iter_errors(result["facts"]))
    save_validate(result, args)


@pytest.mark.parametrize("name,expected", [("families", (2 / 3, 3 / 2, math.sqrt(20000 / 3) / 200)),
    ("hex_256", (1, 257 / 2, None))])
def test_actual_family_components_survive_ambiguous_hex(name, expected):
    args = arguments(name)
    result = adapter.consume_bundle(**args)
    assert result["status"] == "ok"
    for key, value in zip(("family_occupancy", "family_occurrence_mean", "family_cv"), expected):
        if value is not None:
            assert result["facts"][key]["values"][0]["value"] == pytest.approx(value)
    if name == "hex_256":
        assert all(row["reported_occurrences"]["state"] == "incompatible" for row in result["sheet"]["family_rows"][0]["genome_counts"])
        assert result["sheet"]["family_rows"][0]["reported_feature_occurrences"]["value"] == 257


def test_native_only_needs_no_data_extractor(monkeypatch):
    import gene_annotation_episode.bvbrc_comparative_systems_bundle_resolution as resolution
    args = arguments(native_only=True)
    monkeypatch.setattr(resolution, "extract_comparative_systems_data_inputs", forbidden)
    result = adapter.consume_bundle(**args)
    assert result["status"] == "ok" and result["sheet"]["supplied_record_sets"] is None


@pytest.mark.parametrize("change", ["missing", "ambiguous", "bad_bytes", "bad_format", "invalid_json"])
def test_unrelated_artifact_failure_preserves_valid_siblings(change):
    args = arguments(native_only=True)
    args["requested_form"] = form(measurement(args, availability="available_value"))
    member = next(row for row in args["bundle"]["artifacts"] if row["role"] == "subsystem_variants")
    if change == "missing":
        args["bundle"]["artifacts"].remove(member)
    elif change == "ambiguous":
        args["bundle"]["artifacts"].append(deepcopy(member))
    elif change == "bad_bytes":
        args["artifact_bytes"][member["raw_artifact_ref"]] = b"tampered"
    elif change == "bad_format":
        member["declared_format"]["format"] = "json"
    else:
        replace_bytes(args, "variants", b"invalid")
    result = adapter.consume_bundle(**args)
    assert result["status"] == "ok" and result["facts"]["native"]["values"][0]["value"] == 75
    assert result["diagnostics"]
    save_validate(result, args)


@pytest.mark.parametrize("availability,expected", [("typed_state", "ok"), ("available_value", "partial"), ("available_complete_population", "partial")])
def test_missing_requested_native_value_is_typed_and_never_measured_zero(availability, expected):
    args = arguments(native_only=True)
    args["requested_form"] = form(measurement(args, availability=availability))
    args["bundle"]["artifacts"] = [row for row in args["bundle"]["artifacts"] if row["role"] != "pathway_summary"]
    result = adapter.consume_bundle(**args)
    assert result["status"] == expected
    assert result["facts"]["native"]["values"][0]["state"] == "missing"
    assert result["facts"]["native"]["values"][0]["value"] is None
    assert any(row["code"] == "missing_document_selection" for row in result["missing_requirements"])


def test_missing_data_keeps_requested_available_ratio_partial_and_preserves_native():
    args = arguments()
    args["qualified_data_inputs"] = ()
    args["requested_form"] = form(measurement(args, availability="available_value"),
        field("later", {"kind": "ratio", "component_id": "later_pathway_percent"}, "available_complete_population"))
    result = adapter.consume_bundle(**args)
    assert result["status"] == "partial" and result["facts"]["native"]["status"] == "satisfied"
    assert result["facts"]["later"]["values"][0]["output"]["value"] is None
    assert any(row["code"] == "data_input_unavailable" for row in result["missing_requirements"])
    save_validate(result, args)


@pytest.mark.parametrize("variant", ["more_pages", "inexact_total", "partial_results", "incomplete_body", "missing_bytes", "tampered_bytes", "changed_saved_rows"])
def test_actual_data_partial_or_invalid_inputs_never_satisfy_complete_request(variant):
    args = arguments()
    if variant == "more_pages":
        replace_data(args, total=10)
    elif variant == "inexact_total":
        replace_data(args, exact=False)
    elif variant == "partial_results":
        replace_data(args, partial=True)
    elif variant == "incomplete_body":
        replace_data(args, complete=False)
    elif variant == "missing_bytes":
        del args["artifact_bytes"][args["qualified_data_inputs"][0]["raw_binding"]["bytes_key"]]
    elif variant == "tampered_bytes":
        args["artifact_bytes"][args["qualified_data_inputs"][0]["raw_binding"]["bytes_key"]] += b"tamper"
    else:
        args["qualified_data_inputs"][0]["qualified_result"]["grading"]["parse_result"]["sheet"]["rows"][0]["native_id"] = "changed"
    args["requested_form"] = form(measurement(args, availability="available_value"),
        field("later", {"kind": "ratio", "component_id": "later_pathway_percent"}, "available_complete_population"))
    result = adapter.consume_bundle(**args)
    assert result["status"] == "partial"
    assert result["facts"]["native"]["status"] == "satisfied"
    assert result["facts"]["later"]["values"][0]["output"]["state"] != "available"
    assert result["missing_requirements"]
    assert not list(Draft202012Validator(args["requested_form"]).iter_errors(result["facts"]))
    save_validate(result, args)


def test_complete_empty_data_has_zero_records_and_missing_ratio_denominator():
    args = arguments()
    replace_data(args, docs=[])
    args["requested_form"] = form(field("records", {"kind": "population", "population_id": "later_pathway_records"}, "available_complete_population"),
                                 field("ratio", {"kind": "ratio", "component_id": "later_pathway_percent"}, "available_value"))
    result = adapter.consume_bundle(**args)
    record = result["facts"]["records"]
    ratio = result["facts"]["ratio"]["values"][0]
    assert record["status"] == "satisfied" and record["values"][0]["raw_occurrence_count"]["value"] == 0
    assert ratio["numerator"]["value"] == ratio["denominator"]["value"] == 0
    assert ratio["output"]["state"] == "missing" and "empty_denominator" in ratio["output"]["qualification_codes"]
    assert result["status"] == "partial"


def test_broader_acquisition_and_exact_local_filter_counts_stay_separate():
    args = arguments()
    rb = args["qualified_data_inputs"][0]["raw_binding"]
    docs = json.loads(args["artifact_bytes"][rb["bytes_key"]])["response"]["docs"]
    docs[0]["annotation"] = "patric"
    replace_data(args, docs=docs)
    result = adapter.consume_bundle(**args)
    record = result["sheet"]["supplied_record_sets"]["record_sets"][0]
    assert record["original_query_record_count"]["value"] == 5
    assert record["locally_included_record_count"]["value"] == 4
    assert len(record["rows"]) == 5
    assert record["rows"][0]["filter_state"] == "excluded_by_explicit_filter"
    assert "unsupported_server_filter" in {row["code"] for row in result["diagnostics"]}


def test_original_group_expansion_remains_unknown_and_native_descriptive_value_survives():
    args = arguments(native_only=True)
    args["bundle"]["original_task"]["submitted_parameters"]["genome_groups"] = ["/original/group"]
    args["parameters"]["population_assignments"]["assignments"].append({"population_id": "executed", "kind": "executed_genomes", "view_id": None, "entity": None, "component_kind": None})
    args["requested_form"] = form(measurement(args, availability="available_value"),
        field("executed", {"kind": "population", "population_id": "executed"}, "available_complete_population"))
    result = adapter.consume_bundle(**args)
    assert result["status"] == "partial" and result["facts"]["native"]["status"] == "satisfied"
    original = result["sheet"]["original_request"]
    assert original["executed_genome_ids"] is None and original["executed_population_evidence"] == []
    assert "group_membership_unknown" in result["facts"]["executed"]["values"][0]["qualification_codes"]


def test_requirement_resolution_never_uses_first_source_or_filename():
    args = arguments(native_only=True)
    for selected in args["parameters"]["document_selection"]["documents"]:
        selected["input"] = {"kind": "requirement", "requirement_id": "requirement:" + selected["document_id"]}
    args["requested_form"] = form(measurement(args, availability="available_value"))
    good = adapter.consume_bundle(**args)
    assert good["status"] == "ok"
    member = deepcopy(next(row for row in args["bundle"]["artifacts"] if row["role"] == "pathway_summary"))
    member["source_ref"] = "unrelated_but_same_name"
    args["bundle"]["artifacts"].append(member)
    result = adapter.consume_bundle(**args)
    assert result["status"] == "partial"
    assert any(row["code"] == "ambiguous_document_selection" for row in result["missing_requirements"])
    assert not result["sheet"]["pathway_rows"]


@pytest.mark.parametrize("mutation", ["selection", "wrapper_task", "source", "bytes", "value", "basis", "duplicate"])
def test_producer_evidence_requires_all_exact_bindings(mutation):
    args = arguments("families")
    wrapper = args["qualified_producer_evidence"][0]
    if mutation == "selection":
        args["parameters"]["producer_evidence_selections"][0]["record_path"] = "/another"
    elif mutation == "wrapper_task":
        wrapper["qualification"]["original_task_ref"] = "other_task"
    elif mutation == "source":
        wrapper["qualification"]["evidence_source_refs"] = ["other_source"]
    elif mutation == "bytes":
        key = args["parameters"]["producer_evidence_selections"][0]["raw_artifact_ref"]
        args["artifact_bytes"][key] += b"tampered"
    elif mutation == "value":
        args["supplied_values"][0]["value"]["commit"] = "0" * 40
    elif mutation == "basis":
        wrapper["qualification"]["basis"] = "source_only"
    else:
        args["qualified_producer_evidence"] *= 2
    with pytest.raises(ValueError, match="comparative_systems_"):
        adapter.consume_bundle(**args)


def test_null_mapping_does_not_borrow_unrelated_selected_producer():
    args = arguments(native_only=True)
    next(row for row in args["parameters"]["document_selection"]["documents"] if row["document_id"] == "pathways")["producer_evidence_id"] = None
    result = adapter.consume_bundle(**args)
    native = next(row for row in result["sheet"]["native_documents"] if row["document"]["document_id"] == "pathways")
    codes = {row["code"] for row in native["diagnostics"]}
    assert "producer_version_unverified" in codes and "native_first_object_discard" not in codes
    assert native["document"]["basis"] == "service_artifact"


def test_source_only_does_not_claim_executed_version():
    args = arguments(native_only=True)
    wrapper = args["qualified_producer_evidence"][0]
    wrapper["qualification"].update(basis="source_only", original_task_ref=None)
    wrapper["evidence"].update(identity_kind="source_examined", runtime_version=None, dependency_version=None)
    value = deepcopy(wrapper["evidence"])
    args["supplied_values"][0]["value"] = value
    raw = json.dumps({"producer_evidence": value}).encode()
    content = args["bundle"]["supplied_scientific_metadata"][0]["content"]
    content.update(sha256=hashlib.sha256(raw).hexdigest(), byte_count=len(raw))
    args["supplied_values"][0]["evidence"] = deepcopy(args["bundle"]["supplied_scientific_metadata"][0])
    args["artifact_bytes"][content["artifact_ref"]] = raw
    result = adapter.consume_bundle(**args)
    assert "native_first_object_discard" not in {row["code"] for row in result["diagnostics"]}
    assert "producer_version_unverified" in {row["code"] for row in result["diagnostics"]}


def test_arbitrary_reference_array_does_not_establish_completeness():
    args = arguments(native_only=True)
    entity = args["parameters"]["calculation_parameters"]["requests"][0]["entity"]
    args["parameters"]["reference_memberships"] = [{"membership_id": "unbound", "component_kind": "ec_number", "entity": entity,
        "members": ["1.1.1.1"], "map_id": None, "release": None, "completeness": "complete_for_declared_population",
        "basis": "supplied_data_api", "source_locations": [], "qualification_codes": []}]
    result = adapter.consume_bundle(**args)
    assert result["sheet"]["reference_memberships"] == []
    assert any(row["code"] == "reference_membership_missing" for row in result["missing_requirements"])


def test_actual_reference_binding_preserves_native_two_of_four_and_later_three_of_four(monkeypatch):
    args = reference_arguments()
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    result = adapter.consume_bundle(**args)
    assert result["status"] == "ok"
    native, later = [result["facts"][key]["values"][0] for key in ("reference", "later")]
    assert (native["numerator"]["value"], native["denominator"]["value"], native["output"]["value"]) == (2, 4, .5)
    assert (later["numerator"]["value"], later["denominator"]["value"], later["output"]["value"]) == (3, 4, .75)
    reference = result["sheet"]["reference_memberships"][0]
    assert reference["members"] == args["parameters"]["reference_memberships"][0]["members"]
    assert reference["release"] is None and "reference_release_unknown" in reference["qualification_codes"]
    assert "reference_release_unknown" in native["output"]["qualification_codes"]
    save_validate(result, args)


def test_reference_role_ids_are_not_zipped_with_independent_role_names():
    args = reference_arguments(collection="subsystem_ref")
    result = adapter.consume_bundle(**args)
    assert result["status"] == "ok"
    ratio = result["facts"]["reference"]["values"][0]
    assert (ratio["numerator"]["value"], ratio["denominator"]["value"]) == (2, 3)
    assert ratio["output"]["value"] == pytest.approx(2 / 3)
    assert result["sheet"]["reference_memberships"][0]["members"] == ["r1", "r2", "r3"]
    supplied = result["sheet"]["supplied_record_sets"]["record_sets"][-1]["rows"][0]
    assert supplied["association"]["identifiers"]["role_id"] is None
    assert [cell["atoms"] for cell in supplied["native_row"]["cells"] if cell["field"] == "role_name"][0][0]["string_value"] == "independent third"
    save_validate(result, args)


@pytest.mark.parametrize("map_id,expected", [(None, "partial"), ('["KEGG","A"]', "ok"), ('["KEGG", "A"]', "partial"), ('["KEGG","missing"]', "partial")])
def test_reference_map_context_is_explicit_canonical_and_never_first_match(map_id, expected):
    docs = [{"id": "ref_" + name, "pathway_id": "P_TEST", "ec_number": "1.1.1.1",
             "map_type": "KEGG", "map_name": name} for name in ("A", "B")]
    args = reference_arguments(docs=docs, members=["1.1.1.1"], map_id=map_id)
    result = adapter.consume_bundle(**args)
    assert result["status"] == expected
    assert result["facts"]["native"]["values"][0]["value"] == 75
    assert bool(result["sheet"]["reference_memberships"]) == (expected == "ok")
    if expected == "ok":
        assert result["facts"]["reference"]["values"][0]["output"]["value"] == 1
    save_validate(result, args)


@pytest.mark.parametrize("variant", ["fabricated_member", "wrong_source", "wrong_pointer", "uncovered_cell",
    "wrong_entity", "changed_bytes", "missing_bytes", "non_null_release", "duplicate_members", "false_qualifier",
    "incomplete", "partial_response", "omitted_page", "unknown_multi_page", "conflicting_id", "invalid_ec",
    "missing_map", "unidentified_row", "unsupported_basis", "wrong_location_metadata"])
def test_unverified_reference_preserves_available_native_sibling(variant):
    docs = [{"id": "ref_" + str(i), "pathway_id": "P_TEST", "ec_number": f"{i}.{i}.{i}.{i}",
             "map_name": "Synthetic pathway", "map_type": "KEGG"} for i in range(1, 5)]
    if variant == "conflicting_id":
        docs[-1]["id"] = docs[0]["id"]
    elif variant == "invalid_ec":
        docs[-1]["ec_number"] = 5
    elif variant == "missing_map":
        del docs[-1]["map_name"]
    elif variant == "unidentified_row":
        del docs[-1]["pathway_id"]
    args = reference_arguments(docs=docs, total=8 if variant in {"incomplete", "omitted_page", "unknown_multi_page"} else None,
                               partial=variant == "partial_response")
    reference = args["parameters"]["reference_memberships"][0]
    location = reference["source_locations"][0]
    if variant == "fabricated_member":
        reference["members"].append("9.9.9.9")
    elif variant == "wrong_source":
        location["source_ref"] = "unbound"
    elif variant == "wrong_pointer":
        location["json_pointer"] = "/response/docs/40"
    elif variant == "uncovered_cell":
        location["json_pointer"] = "/response/docs/0/ec_number"
    elif variant == "wrong_entity":
        reference["entity"]["pathway_id"] = "OTHER"
    elif variant == "changed_bytes":
        args["artifact_bytes"][location["raw_artifact_ref"]] += b"tampered"
    elif variant == "missing_bytes":
        del args["artifact_bytes"][location["raw_artifact_ref"]]
    elif variant == "non_null_release":
        reference["release"] = "self_authored_release"
    elif variant == "duplicate_members":
        reference["members"].append(reference["members"][0])
    elif variant == "false_qualifier":
        reference["qualification_codes"] = ["native_first_object_discard"]
    elif variant in {"omitted_page", "unknown_multi_page"}:
        second_docs = [dict(row, id="second_" + row["id"]) for row in docs]
        second = add_reference_data(args, second_docs, source="synthetic_second_reference", offset=4, total=8, select_existing=True)
        if variant == "unknown_multi_page":
            reference["source_locations"].append(second)
    elif variant == "unsupported_basis":
        reference["basis"] = "source_executed_synthetic"
    elif variant == "wrong_location_metadata":
        location.update(json_pointer="/response/docs/0/ec_number", row_ordinal=3, native_field="ec_number")
    result = adapter.consume_bundle(**args)
    assert result["status"] == "partial"
    assert result["facts"]["native"]["values"][0]["value"] == 75
    assert result["sheet"]["reference_memberships"] == []
    assert result["facts"]["reference"]["values"][0]["output"]["state"] != "available"
    assert any(row["required_input_role"] == "reference_membership" for row in result["missing_requirements"])
    if variant == "unknown_multi_page":
        record = result["sheet"]["supplied_record_sets"]["record_sets"][-1]
        assert record["page_coverage"] == "complete" and record["snapshot_consistency"] == "unknown"
    save_validate(result, args)


@pytest.mark.parametrize("total,expected_membership", [(0, True), (4, False)])
def test_complete_empty_reference_differs_from_incomplete_reference(total, expected_membership):
    args = reference_arguments(docs=[], members=[], total=total)
    result = adapter.consume_bundle(**args)
    assert bool(result["sheet"]["reference_memberships"]) == expected_membership
    ratio = result["facts"]["reference"]["values"][0]
    assert ratio["output"]["value"] is None and result["status"] == "partial"
    if expected_membership:
        assert ratio["denominator"]["value"] == 0
        assert "empty_denominator" in ratio["output"]["qualification_codes"]
    else:
        assert ratio["denominator"]["state"] != "available"
    save_validate(result, args)


def test_reference_member_cell_locations():
    args = reference_arguments()
    reference = args["parameters"]["reference_memberships"][0]
    source = reference["source_locations"][0]
    reference["source_locations"] = [dict(source, json_pointer=f"/response/docs/{i}/ec_number",
        row_ordinal=i, column_ordinal=2, native_field="ec_number") for i in range(4)]
    result = adapter.consume_bundle(**args)
    assert result["status"] == "ok"
    save_validate(result, args)


def test_reference_broader_population_filters_exact_entity_and_keeps_repeated_occurrences():
    docs = [{"id": "ref_" + str(i), "pathway_id": "P_TEST", "ec_number": f"{i}.{i}.{i}.{i}",
             "map_name": "Synthetic pathway", "map_type": "KEGG"} for i in range(1, 5)]
    docs.extend([dict(docs[0], id="repeated_ec"), dict(docs[0], id="other_entity", pathway_id="OTHER", ec_number="9.9.9.9")])
    docs.sort(key=lambda row: row["id"])
    args = reference_arguments(docs=docs, filters=[])
    result = adapter.consume_bundle(**args)
    assert result["status"] == "ok"
    assert len(result["sheet"]["supplied_record_sets"]["record_sets"][-1]["rows"]) == 6
    assert result["facts"]["reference"]["values"][0]["denominator"]["value"] == 4
    save_validate(result, args)


@pytest.mark.parametrize("variant", ["wrong_hierarchy", "conflicting_context", "scalar_role", "invalid_role_atom", "map_id"])
def test_reference_subsystem_context_and_native_role_array_are_required(variant):
    docs = [{"id": "reference_roles", "subsystem_id": "S_TEST", "subsystem_name": "Synthetic subsystem",
             "superclass": "synthetic", "class": "Synthetic class", "subclass": "Synthetic subclass",
             "role_id": ["r1", "r2", "r3"], "role_name": ["separate"]}]
    if variant == "wrong_hierarchy":
        docs[0]["class"] = "Other class"
    elif variant == "conflicting_context":
        docs.append(dict(docs[0], id="conflicting_context", subclass="Other subclass"))
    elif variant == "scalar_role":
        docs[0]["role_id"] = "r1"
    elif variant == "invalid_role_atom":
        docs[0]["role_id"][-1] = 9
    args = reference_arguments(docs=docs, collection="subsystem_ref", map_id="unsupported" if variant == "map_id" else None)
    result = adapter.consume_bundle(**args)
    assert result["status"] == "partial" and result["sheet"]["reference_memberships"] == []
    assert result["facts"]["native"]["values"][0]["value"] == 75
    save_validate(result, args)


@pytest.mark.parametrize("mutation", ["wrong_application", "wrong_task", "unverified_path", "wrong_data_binding"])
def test_original_task_and_data_binding_conflicts(mutation):
    args = arguments()
    if mutation == "wrong_application":
        args["bundle"]["original_task"].update(required_application_id="GenomeComparison", native_application_id="GenomeComparison")
    elif mutation == "wrong_task":
        args["bundle"]["artifacts"][0]["task_association"]["task_id"] = "wrong"
    elif mutation == "unverified_path":
        args["requested_form"] = form(measurement(args, availability="available_value"))
        args["bundle"]["artifacts"][0]["task_association"]["kind"] = "unverified_original_path"
        result = adapter.consume_bundle(**args)
        assert result["status"] == "partial"
        assert any(row["code"] == "original_task_mismatch" for row in result["missing_requirements"])
        return
    else:
        args["bundle"]["supplied_contents"][0]["source_ref"] = "wrong"
    with pytest.raises(ValueError):
        adapter.consume_bundle(**args)
