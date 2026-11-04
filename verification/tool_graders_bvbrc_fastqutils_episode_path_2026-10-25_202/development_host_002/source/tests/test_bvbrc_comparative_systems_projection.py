"""Finite saved projection tests: selectors, custody comparisons and no regrade."""
from copy import deepcopy
import ast
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import urllib.request

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import bvbrc_comparative_systems_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_comparative_systems_bundle_projection import project_comparative_systems_facts
from gene_annotation_episode.bvbrc_comparative_systems_fact_contracts import FACT_SOURCES, validate_requested_form
from gene_annotation_episode.bvbrc_comparative_systems_handoff_contracts import canonical_sha256
from test_bvbrc_comparative_systems_bundle import arguments, empty_failure_context, field, form, forbidden, measurement, replace_bytes, save_validate


@pytest.fixture(scope="module")
def saved():
    args = arguments()
    result = adapter.consume_bundle(**args)
    return args, result


def test_seven_families_copy_exact_requested_values(saved):
    args, result = deepcopy(saved)
    sheet, components = result["sheet"], result["components"]
    entity = next(row["entity"] for row in sheet["pathway_rows"])
    quals = [row for row in sheet["diagnostics"] + components["diagnostics"] if row["code"] == "native_first_object_discard"]
    # Exact duplicates are one retained diagnostic value, never extra facts.
    n = len({canonical_sha256(row) for row in quals})
    requested = form(measurement(args), field("ratio", {"kind": "ratio", "component_id": "later_pathway_percent"}),
        field("population", {"kind": "population", "population_id": "later_pathway_genomes"}),
        field("membership", {"kind": "membership", "entity": entity, "genome_id": "1.1", "member_id": "1.1.1.1", "population_id": "later_pathway_genomes"}),
        field("requirements", {"kind": "requirement", "required_input_role": "reference_membership"}, cardinality=0),
        field("qualification", {"kind": "qualification", "code": "native_first_object_discard"}, cardinality=n),
        field("status", {"kind": "request_status"}))
    projected = project_comparative_systems_facts(sheet, components, requested_form=requested)
    assert len(set(FACT_SOURCES.values())) == 7
    assert set(projected) == set(requested["properties"])
    assert all(row["status"] == "satisfied" for row in projected.values())
    assert projected["native"]["values"] == [sheet["pathway_rows"][0]["reported_ec_conservation_percent"]]
    assert projected["membership"]["values"][0]["presence_state"] == "recorded_positive"
    assert "members" not in projected["population"]["values"][0]
    assert not list(Draft202012Validator(requested).iter_errors(projected))


def test_saved_projection_forbids_readers_extractors_calculators_and_io(saved, monkeypatch):
    args, result = deepcopy(saved)
    import gene_annotation_episode.bvbrc_comparative_systems_native as native
    import gene_annotation_episode.bvbrc_comparative_systems_sheet as builder
    import gene_annotation_episode.bvbrc_comparative_systems_calculators as calculators
    import gene_annotation_episode.bvbrc_comparative_systems_data_inputs as extractor
    import gene_annotation_episode.bvbrc_comparative_systems_bundle_resolution as resolution
    for module, names in ((native, ["parse_comparative_systems_document"]), (builder, ["build_comparative_systems_sheet"]),
                           (calculators, ["calculate_comparative_systems_components"]), (extractor, ["extract_comparative_systems_data_inputs"]),
                           (resolution, ["parse_comparative_systems_document", "build_comparative_systems_sheet", "calculate_comparative_systems_components", "extract_comparative_systems_data_inputs"])):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    before = deepcopy(result)
    for _ in range(2):
        assert project_comparative_systems_facts(result["sheet"], result["components"], requested_form=args["requested_form"]) == result["facts"]
        save_validate(result, args)
    assert result == before


@pytest.mark.parametrize("change", ["facts", "components", "sheet", "status", "requirements", "diagnostics", "parameters", "task", "form", "source", "hash", "transfer", "population_selection", "data_selection"])
def test_saved_projection_rejects_tampered_values_and_bindings(saved, change):
    args, result = deepcopy(saved)
    if change == "facts":
        result["facts"]["retained_pathway_percent"]["values"][0]["value"] = 74
    elif change == "components":
        component = result["components"]["components"][0]
        component["value"]["value"] = 74
        component["ratio"]["output"]["value"] = 74
    elif change == "sheet":
        result["sheet"]["pathway_rows"][0]["reported_ec_conservation_percent"]["value"] = 74
    elif change == "status":
        result["status"] = "partial"
    elif change == "requirements":
        result["missing_requirements"].append({"garbage": True})
    elif change == "diagnostics":
        result["diagnostics"].pop()
    elif change == "parameters":
        args["parameters"]["calculation_parameters"]["absolute_tolerance"] = 0.1
    elif change == "task":
        args["bundle"]["original_task"]["submitted_parameters"]["genome_ids"].append("999.1")
    elif change == "form":
        args["requested_form"]["properties"]["retained_pathway_percent"]["x-bvbrc-comparative-systems"]["selector"]["component_id"] = "later_pathway_percent"
    elif change == "source":
        args["bundle"]["artifacts"][0]["source_ref"] = "unrelated"
    elif change == "hash":
        args["bundle"]["artifacts"][0]["sha256"] = "0" * 64
    elif change == "transfer":
        args["bundle"]["artifacts"][0]["transfer"]["object_complete"] = "unknown"
    elif change == "population_selection":
        args["parameters"]["population_assignments"]["assignments"][1]["view_id"] = "pathway_raw"
    else:
        args["parameters"]["supplied_data_selection"]["record_sets"][0]["annotation_filter"] = "none"
    with pytest.raises(ValueError):
        save_validate(result, args)


def test_scalar_requires_computed_selector_and_ratio_requires_ratio(saved):
    args, result = deepcopy(saved)
    requested = form(field("count", {"kind": "computed_measurement", "component_id": "unambiguous_active_genomes"}),
                     field("bad_ratio", {"kind": "ratio", "component_id": "unambiguous_active_genomes"}))
    projection = project_comparative_systems_facts(result["sheet"], result["components"], requested_form=requested)
    assert projection["count"]["values"][0]["value"] == 0
    assert projection["bad_ratio"]["status"] == "invalid" and projection["bad_ratio"]["values"] == []


@pytest.mark.parametrize("state", ["partial", "invalid"])
def test_null_saved_objects_preserve_failures_and_forbid_available_values(saved, monkeypatch, state):
    from gene_annotation_episode.bvbrc_comparative_systems_bundle_contracts import issue, requirement
    from gene_annotation_episode.bvbrc_comparative_systems_bundle_projection import assemble_projection
    import gene_annotation_episode.bvbrc_comparative_systems_bundle_resolution as resolution
    args, original = deepcopy(saved)
    args["requested_form"] = form(
        field("computed", {"kind": "computed_measurement", "component_id": "retained_pathway_percent"}, "available_value"),
        field("failure", {"kind": "requirement", "required_input_role": "pathway_summary"}),
        field("qualification", {"kind": "qualification", "code": "format_incompatible"}),
        field("status", {"kind": "request_status"}))
    missing = requirement("format_incompatible", role="pathway_summary", document_id="pathways",
                          refs=["synthetic_source_pathways"])
    diagnostic = issue("format_incompatible", role="pathway_summary", document_id="pathways",
                       refs=["synthetic_source_pathways"], phase="decode")
    context = {"retained_requirements": [missing], "retained_diagnostics": [diagnostic], "failure_status": state}
    result = assemble_projection(None, None, requested_form=args["requested_form"], failure_context=context)
    assert result["status"] == state
    assert result["facts"]["computed"]["values"] == []
    assert result["facts"]["computed"]["status"] == "partial"
    assert result["facts"]["failure"]["values"] == [missing]
    assert result["facts"]["qualification"]["values"] == [diagnostic]
    assert result["facts"]["status"]["values"][0]["status"] == ("invalid" if state == "invalid" else "unavailable")
    for name in ("parse_comparative_systems_document", "build_comparative_systems_sheet",
                 "calculate_comparative_systems_components", "extract_comparative_systems_data_inputs"):
        monkeypatch.setattr(resolution, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    save_validate(result, args, failure_context=context)
    fabricated = deepcopy(result)
    fabricated["facts"]["computed"]["values"] = [original["components"]["components"][0]["value"]]
    fabricated["facts"]["computed"]["status"] = "satisfied"
    with pytest.raises(ValueError, match="saved_projection_mismatch"):
        save_validate(fabricated, args, failure_context=context)
    for change in ("source", "document", "field"):
        changed = deepcopy(result)
        record = changed["missing_requirements"][0]
        if change == "source":
            record["source_refs"] = ["unbound_source"]
        elif change == "document":
            record["document_id"] = "unbound_document"
        else:
            record["affected_field_ids"] = ["unbound_field"]
        with pytest.raises(ValueError):
            save_validate(changed, args, failure_context=context)


def test_saved_sheet_without_components_keeps_native_value_and_missing_calculation(saved):
    from gene_annotation_episode.bvbrc_comparative_systems_bundle_projection import assemble_projection
    args, original = deepcopy(saved)
    args["requested_form"] = form(measurement(args, availability="available_value"),
        field("computed", {"kind": "computed_measurement", "component_id": "retained_pathway_percent"}, "available_value"))
    result = assemble_projection(original["sheet"], None, requested_form=args["requested_form"], failure_context=empty_failure_context())
    assert result["status"] == "partial" and result["facts"]["native"]["values"][0]["value"] == 75
    assert result["facts"]["computed"]["values"] == []
    save_validate(result, args)
    result["components"] = original["components"]
    result["sheet"] = None
    with pytest.raises(ValueError, match="components_without_sheet"):
        save_validate(result, args)


def test_null_saved_membership_has_no_invented_native_identifier(saved):
    from gene_annotation_episode.bvbrc_comparative_systems_bundle_projection import assemble_projection
    args, original = deepcopy(saved)
    args["requested_form"] = form(field("membership", {"kind": "membership",
        "entity": original["sheet"]["pathway_rows"][0]["entity"], "genome_id": "1.1",
        "member_id": "9.9.9.9", "population_id": "later_pathway_genomes"}))
    result = assemble_projection(None, None, requested_form=args["requested_form"], failure_context=empty_failure_context())
    assert result["status"] == "partial" and result["facts"]["membership"]["values"] == []
    save_validate(result, args)


@pytest.mark.parametrize("count,expected", [(1, "invalid"), (2, "ok"), (3, "partial")])
def test_exact_cardinality_never_selects_first_or_truncates(count, expected):
    args = arguments(native_only=True)
    member = next(row for row in args["bundle"]["artifacts"] if row["role"] == "pathway_summary")
    native = json.loads(args["artifact_bytes"][member["raw_artifact_ref"]])
    lines = native["pathway"].splitlines()
    native["pathway"] = "\n".join([*lines, lines[1]])
    replace_bytes(args, "pathways", json.dumps(native).encode())
    args["requested_form"] = form(measurement(args, availability="available_value", cardinality=count))
    result = adapter.consume_bundle(**args)
    assert result["status"] == expected
    assert len(result["facts"]["native"]["values"]) == 2
    if expected != "invalid":
        assert not list(Draft202012Validator(args["requested_form"]).iter_errors(result["facts"]))


def test_native_selector_needs_view_and_exact_entity(saved):
    args, result = deepcopy(saved)
    selection = measurement(args)
    del selection["selector"]["view_id"]
    with pytest.raises(ValueError):
        form(selection)
    selection = measurement(args)
    selection["selector"]["entity"]["pathway_id"] = "NOT_THE_RETAINED_PATHWAY"
    value = project_comparative_systems_facts(result["sheet"], result["components"], requested_form=form(selection))
    assert value["native"]["values"][0]["state"] == "missing"
    assert value["native"]["values"][0]["value"] is None


@pytest.mark.parametrize("mutation", ["extra", "missing", "marker", "cardinality", "availability", "field_id", "relaxed_value"])
def test_requested_form_cannot_relax_original_closed_contract(mutation):
    args = arguments(native_only=True)
    value = form(measurement(args))
    if mutation == "extra":
        value["additionalProperties"] = True
    elif mutation == "missing":
        value["required"] = []
    elif mutation == "marker":
        value["properties"]["native"].pop("x-bvbrc-comparative-systems")
    elif mutation == "cardinality":
        value["properties"]["native"]["properties"]["values"]["maxItems"] = 10
    elif mutation == "availability":
        value["properties"]["native"]["x-bvbrc-comparative-systems"]["availability_requirement"] = "anything"
    elif mutation == "field_id":
        value["properties"]["native"]["x-bvbrc-comparative-systems"]["field_id"] = "another"
    else:
        value["properties"]["native"]["properties"]["values"]["items"] = {}
    with pytest.raises(ValueError):
        validate_requested_form(value)


def test_requested_form_and_projection_survive_durable_canonical_serialization(saved):
    args, result = deepcopy(saved)
    requested = form(field("z_computed", {"kind": "computed_measurement", "component_id": "retained_pathway_percent"}),
                     measurement(args, field_id="a_native"), field("m_status", {"kind": "request_status"}))
    persisted = json.loads(json.dumps(requested, sort_keys=True, separators=(",", ":")))
    assert validate_requested_form(persisted) == requested
    assert requested["required"] == ["a_native", "m_status", "z_computed"]
    assert project_comparative_systems_facts(result["sheet"], result["components"], requested_form=persisted) == \
           project_comparative_systems_facts(result["sheet"], result["components"], requested_form=requested)


@pytest.mark.parametrize("names", [("qualification", "requirements"), ("z_qualification", "a_requirements")])
def test_metadata_selectors_share_snapshot_and_retain_own_cardinality_failures(names):
    # I's actual seven-family form expects four unknown-producer diagnostics.
    # This P fixture has bound source-execution evidence instead. Its missing
    # qualification remains partial without inventing a source requirement.
    args = arguments("families")
    entity = args["parameters"]["calculation_parameters"]["requests"][0]["entity"]
    qualification_name, requirement_name = names
    args["requested_form"] = form(
        field("occurrences", {"kind": "measurement", "view_id": "plfam", "entity": entity,
                               "native_field": "reported_feature_occurrences"}),
        field("occupancy", {"kind": "ratio", "component_id": "family_occupancy"}),
        field("population", {"kind": "population", "population_id": "families_native_genomes"}),
        field("member", {"kind": "membership", "entity": entity, "population_id": "families_native_genomes",
                          "genome_id": "1.1", "member_id": "PLF_TEST"}),
        field(requirement_name, {"kind": "requirement", "required_input_role": "native_document"}, cardinality=0),
        field(qualification_name, {"kind": "qualification", "code": "producer_version_unverified"}, cardinality=4),
        field("status", {"kind": "request_status"}))
    result = adapter.consume_bundle(**args)
    assert result["status"] == "partial"
    assert result["facts"][requirement_name]["values"] == []
    assert result["facts"][requirement_name]["status"] == "satisfied"
    assert result["facts"][qualification_name]["values"] == []
    assert any(row["affected_field_ids"] == [qualification_name] and row["code"] == "missing_required_field"
               for row in result["missing_requirements"])
    assert not list(Draft202012Validator(args["requested_form"]).iter_errors(result["facts"]))
    save_validate(result, args)


def test_null_saved_metadata_cardinality_failure_does_not_become_its_own_input(saved):
    from gene_annotation_episode.bvbrc_comparative_systems_bundle_projection import assemble_projection
    args, _ = deepcopy(saved)
    args["requested_form"] = form(
        field("qualification", {"kind": "qualification", "code": "producer_version_unverified"}),
        field("requirements", {"kind": "requirement", "required_input_role": "native_document"}, cardinality=0),
        field("status", {"kind": "request_status"}))
    result = assemble_projection(None, None, requested_form=args["requested_form"], failure_context=empty_failure_context())
    assert result["status"] == "partial" and result["facts"]["requirements"]["values"] == []
    assert result["missing_requirements"]
    save_validate(result, args)


def test_original_and_generated_failure_identity_collision_is_losslessly_replayed(saved, monkeypatch):
    from gene_annotation_episode.bvbrc_comparative_systems_bundle_contracts import issue, requirement
    from gene_annotation_episode.bvbrc_comparative_systems_bundle_projection import assemble_projection, validate_projection_failure_context
    import gene_annotation_episode.bvbrc_comparative_systems_bundle_resolution as resolution
    args, _ = deepcopy(saved)
    args["requested_form"] = form(
        field("qualification", {"kind": "qualification", "code": "producer_version_unverified"}),
        field("requirements", {"kind": "requirement", "required_input_role": "native_document"}),
        field("status", {"kind": "request_status"}))
    missing = requirement("missing_required_field", fields=["qualification"])
    diagnostic = issue("missing_required_field", fields=["qualification"])
    context = {"retained_requirements": [missing], "retained_diagnostics": [diagnostic], "failure_status": "partial"}
    result = assemble_projection(None, None, requested_form=args["requested_form"], failure_context=context)
    assert result["facts"]["requirements"]["values"] == [missing]
    assert result["facts"]["requirements"]["status"] == "satisfied"
    assert result["missing_requirements"] == [missing] and result["diagnostics"] == [diagnostic]
    detached = validate_projection_failure_context(context)
    detached["retained_requirements"].clear()
    assert context["retained_requirements"] == [missing]
    for name in ("consume_bundle", "parse_comparative_systems_document", "build_comparative_systems_sheet",
                 "calculate_comparative_systems_components", "extract_comparative_systems_data_inputs"):
        monkeypatch.setattr(resolution, name, forbidden)
    monkeypatch.setattr(adapter, "consume_bundle", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    save_validate(result, args, failure_context=context)
    with pytest.raises(ValueError, match="saved_projection_mismatch"):
        save_validate(result, args, failure_context=empty_failure_context())
    changed = deepcopy(context)
    changed["failure_status"] = "invalid"
    with pytest.raises(ValueError, match="saved_projection_mismatch"):
        save_validate(result, args, failure_context=changed)
    changed = deepcopy(context)
    changed["retained_requirements"][0]["source_refs"] = ["unbound_original_source"]
    with pytest.raises(ValueError, match="saved_failure_source_mismatch"):
        save_validate(result, args, failure_context=changed)


@pytest.mark.parametrize("mutation", ["missing", "extra", "tuple", "status", "boolean", "record", "nonfinite"])
def test_projection_failure_context_is_strict_finite_and_detached(mutation):
    from gene_annotation_episode.bvbrc_comparative_systems_bundle_projection import validate_projection_failure_context
    context = empty_failure_context()
    if mutation == "missing":
        del context["failure_status"]
    elif mutation == "extra":
        context["extra"] = []
    elif mutation == "tuple":
        context["retained_requirements"] = ()
    elif mutation == "status":
        context["failure_status"] = "ok"
    elif mutation == "boolean":
        context["failure_status"] = False
    elif mutation == "record":
        context["retained_requirements"] = [{"requirement_id": "untyped"}]
    else:
        context["retained_diagnostics"] = [{"bad": float("nan")}]
    with pytest.raises(ValueError):
        validate_projection_failure_context(context)


def test_saved_validator_requires_original_failure_context(saved):
    from gene_annotation_episode.bvbrc_comparative_systems_bundle_projection import validate_saved_comparative_systems_projection
    args, result = deepcopy(saved)
    with pytest.raises(TypeError, match="failure_context"):
        validate_saved_comparative_systems_projection(result["sheet"], result["components"],
            **{key: result[key] for key in ("facts", "status", "missing_requirements", "diagnostics")},
            **{key: args[key] for key in ("requested_form", "parameters", "bundle")}, original_task=args["bundle"]["original_task"])


@pytest.mark.parametrize("mutation", [None, "unbound_artifact", "different_artifact", "different_document"])
def test_failure_context_locations_bind_exact_source_artifact_and_document(saved, mutation):
    from gene_annotation_episode.bvbrc_comparative_systems_bundle_contracts import issue
    from gene_annotation_episode.bvbrc_comparative_systems_bundle_projection import assemble_projection
    args, _ = deepcopy(saved)
    args["requested_form"] = form(field("qualification", {"kind": "qualification", "code": "format_incompatible"}))
    diagnostic = issue("format_incompatible", document_id="pathways", refs=["synthetic_source_pathways"], phase="decode")
    location = {"source_ref": "synthetic_source_pathways", "raw_artifact_ref": "synthetic_artifact_pathways",
        "document_id": "pathways", "json_pointer": "", "table": None,
        "row_ordinal": None, "column_ordinal": None, "native_field": None}
    diagnostic["locations"] = [location]
    if mutation == "unbound_artifact":
        location["raw_artifact_ref"] = "unbound_artifact"
    elif mutation == "different_artifact":
        location["raw_artifact_ref"] = "synthetic_artifact_subsystems"
    elif mutation == "different_document":
        location["document_id"] = "subsystems"
    context = {"retained_requirements": [], "retained_diagnostics": [diagnostic], "failure_status": "partial"}
    result = assemble_projection(None, None, requested_form=args["requested_form"], failure_context=context)
    if mutation is None:
        save_validate(result, args, failure_context=context)
    else:
        with pytest.raises(ValueError, match="saved_failure_location_mismatch"):
            save_validate(result, args, failure_context=context)


def test_complete_population_state_and_membership_do_not_infer_biological_absence(saved):
    args, result = deepcopy(saved)
    entity = result["sheet"]["pathway_rows"][0]["entity"]
    # EC 3 exists in the retained later population for another genome. The
    # query's complete population supports zero assignment for genome 1.
    selectors = [field("native_membership", {"kind": "membership", "entity": entity, "genome_id": "1.1", "member_id": "9.9.9.9", "population_id": "pathway_native_genomes"}),
                 field("later_absence", {"kind": "membership", "entity": entity, "genome_id": "1.1", "member_id": "3.3.3.3", "population_id": "later_pathway_genomes"})]
    value = project_comparative_systems_facts(result["sheet"], result["components"], requested_form=form(*selectors))
    assert value["native_membership"]["status"] == "partial" and value["native_membership"]["values"] == []
    assert value["later_absence"]["values"][0]["presence_state"] == "zero_in_qualified_record_population"


@pytest.mark.parametrize("population", ["later_pathway_genomes", "pathway_native_ecs"])
def test_unbound_membership_genome_never_becomes_native_identifier(saved, population):
    args, result = deepcopy(saved)
    requested = form(field("membership", {"kind": "membership", "entity": result["sheet"]["pathway_rows"][0]["entity"],
        "genome_id": "unbound.genome", "member_id": "1.1.1.1", "population_id": population}))
    projection = project_comparative_systems_facts(result["sheet"], result["components"], requested_form=requested)
    assert projection["membership"]["values"] == []
    assert projection["membership"]["status"] in {"invalid", "partial"}


def test_family_membership_with_no_genome_selects_observed_aggregate():
    args = arguments("families")
    original = adapter.consume_bundle(**args)
    population = next(row for row in original["sheet"]["population_assignments"]["assignments"]
                      if row["kind"] == "native_view_represented_genomes")
    entity = original["sheet"]["family_rows"][0]["entity"]
    requested = form(field("membership", {"kind": "membership", "entity": entity,
        "genome_id": None, "member_id": entity["family_id"], "population_id": population["population_id"]}))
    projection = project_comparative_systems_facts(original["sheet"], original["components"], requested_form=requested)
    assert projection["membership"]["values"][0]["presence_state"] == "recorded_positive"
    assert projection["membership"]["values"][0]["source_locations"]


def test_pin_covers_every_transitive_package_module_and_frozen_data_asset():
    directory = Path(adapter.__file__).parent
    pending, found = [Path(adapter.__file__).stem], set()
    while pending:
        name = pending.pop()
        if name in found:
            continue
        found.add(name)
        for node in ast.walk(ast.parse((directory / (name + ".py")).read_text())):
            if isinstance(node, ast.ImportFrom) and node.level == 1:
                children = [node.module] if node.module else [item.name for item in node.names]
                pending.extend(name for name in children if name and (directory / (name + ".py")).is_file())
    assert {name + ".py" for name in found} <= set(adapter._DEPENDENCIES)
    assert {"bvbrc_comparative_systems_handoff_schemas.json", "bvbrc_appservice_schemas.json"} <= set(adapter._DEPENDENCIES)
    assert len(adapter.implementation_sha256()) == 64
