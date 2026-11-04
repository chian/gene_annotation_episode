"""Saved projection over actual pure constructors, without API custody claims."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import bvbrc_proteome_bundle_contracts as contracts
from gene_annotation_episode import bvbrc_proteome_bundle_projection as projection
from gene_annotation_episode import bvbrc_proteome_fact_contracts as facts
from gene_annotation_episode import bvbrc_proteome_inputs as inputs
from gene_annotation_episode import bvbrc_proteome_native as native
from gene_annotation_episode import bvbrc_proteome_joins as joins
from gene_annotation_episode import bvbrc_proteome_sheet as sheets
from gene_annotation_episode import bvbrc_proteome_calculators as calculators
from test_bvbrc_proteome_construction import parameters as calculation_parameters
from test_bvbrc_proteome_joins import CONTRACT, case, source, native_result


MEAN = {"kind": "measurement", "target": "summary", "track_key": "comp_genome_2",
        "summary": "first_hsp_identity_summary", "metric": "mean"}


def saved_example(selections=None, *, mutate_native=None):
    """Actually construct each result; wrapper describes explicitly synthetic input."""
    data = case()
    original_parameters = {"genome_ids": [], "user_genomes": ["/unused.faa", "/ref.faa", "/subject.faa"],
        "user_feature_groups": [], "reference_genome_index": 2}
    # This saved-projection fixture has no actual host-retained submission.
    # Use a separate, explicitly synthetic effective record; the actual request
    # path is exercised by test_bvbrc_proteome_submitted_parameters instead.
    parameter_raw = facts.canonical({"parameters": original_parameters}).encode()
    parameter_content = source(parameter_raw, "synthetic-effective-parameters")["content"]
    parameter_evidence = dict(content=parameter_content, pointer="/parameters")
    task = dict(resource_id="synthetic-api", task_id="synthetic-task", required_application_id="GenomeComparison",
        native_application_id="GenomeComparison", submitted_parameters=original_parameters, submitted_start_parameters={},
        scheduler_returned_parameters=None,
        effective_parameters=dict(value=deepcopy(original_parameters), evidence=parameter_evidence),
        submission_receipt_ref="synthetic-receipt",
        submission_operation_key="synthetic-operation", submission_source_ref="synthetic-original-parameters")
    parameter_source = dict(kind="effective", source_field=dict(source_ref=parameter_content["source_ref"],
        sha256=parameter_content["sha256"], pointer=parameter_evidence["pointer"], row_ordinal=None, field_name=None))
    index_result = inputs.index_original_inputs(task, parameter_source=parameter_source, source_contract=deepcopy(CONTRACT))
    data["input_index"] = deepcopy(index_result["value"])
    inventory_results = [inputs.read_protein_fasta(raw, source=source(raw, "synthetic-" + key),
        declared_format="protein_fasta_utf8_v1", inventory_key=key) for key, raw in (
            ("ref", b">r1\nACDE\n>r2\nCCCC\n"), ("subject", b">s1\nACDE\n>s2\nAGG\n"))]
    parsed = native_result()
    if mutate_native is not None:
        parsed = mutate_native()
        data["native"] = parsed["value"]
        # Explicitly update source identity in the synthetic requested links.
        for link in data["native_links"]:
            link["native"]["sha256"] = parsed["value"]["source"]["content"]["sha256"]
    joined = joins.build_native_joins(**data)
    result = sheets.build_native_sheet([parsed], primary_source_ref=parsed["value"]["source"]["content"]["source_ref"],
        input_index=index_result["value"], inventories=[r["value"] for r in inventory_results],
        feature_snapshots=[], genome_snapshots=[], sequence_snapshots=[], joins=joined["value"], representation_links=[])
    assert result["value"] is not None
    components = calculators.calculate_native_components(result["value"], parameters=calculation_parameters())
    assert components["value"] is not None
    supplied = dict(version="bvbrc_proteome_supplied_data_v1",
        original_input_index=dict(mode="construct", parameter_source=parameter_source, additional_parameter_sources=[]),
        inventories=[dict(mode="raw", inventory_key=r["value"]["inventory_key"], declared_format="protein_fasta_utf8_v1",
            source=dict(kind="original_retained_input", input_binding_id="input-" + r["value"]["inventory_key"])) for r in inventory_results],
        feature_snapshots=[], genome_snapshots=[], sequence_snapshots=[],
        execution_links=deepcopy(data["execution_links"]), native_links=deepcopy(data["native_links"]),
        metadata_links=[], representation_links=[])
    supplied_raw = facts.canonical(supplied).encode()
    evidence = dict(content=source(supplied_raw, "synthetic-supplied")["content"], pointer="")
    binding = parsed["value"]["source"]["content"]
    params = dict(version="bvbrc_proteome_bundle_parameters_v1", analysis_id="synthetic-analysis",
        native_documents=[dict(document_id="primary", source_ref=binding["source_ref"], raw_artifact_ref=binding["artifact_ref"],
            role="proteome_native_projection", declared_format=dict(format=parsed["value"]["format"], version=None, mode=None,
                producer_source_ref=None, transformation_evidence=[]), source_contract=deepcopy(CONTRACT))],
        primary_document_id="primary", supplied_data_evidence=evidence, calculation_parameters=calculation_parameters())
    form = projection.requested_form_schema({"mean": MEAN} if selections is None else selections)
    resolutions = [dict(selector_kind="native_document", selection_index=0,
        state="resolved" if parsed["status"] == "ok" else "partial", content=binding,
        construction_evidence=None, result_index=0, requirement_ids=[]),
        dict(selector_kind="original_input_index", selection_index=0, state="resolved" if index_result["status"] == "ok" else "partial",
             content=parameter_content, construction_evidence=None, result_index=0, requirement_ids=[])]
    resolutions.extend(dict(selector_kind="inventory", selection_index=i, state="resolved" if r["status"] == "ok" else "partial",
        content=r["value"]["source"]["content"], construction_evidence=None, result_index=i, requirement_ids=[])
        for i, r in enumerate(inventory_results))
    wrapper = dict(version="bvbrc_proteome_provider_sheet_v1", analysis_id=params["analysis_id"], original_task=task,
        parameters=params, requested_form=form, bundle_sha256=hashlib.sha256(b"explicitly synthetic bundle").hexdigest(),
        supplied_values=[dict(evidence=evidence, value=supplied),
                         dict(evidence=parameter_evidence, value=deepcopy(original_parameters))],
        input_resolution=resolutions, native_results=[parsed],
        input_index_result=index_result, inventory_results=inventory_results, feature_results=[], genome_results=[], sequence_results=[],
        joins_result=joined, native_sheet_result=result, requirements=[], diagnostics=[])
    assert contracts.validate_provider_sheet(wrapper) == wrapper
    return wrapper, components, params, form


def project(example, *, missing_requirements=(), diagnostics=()):
    sheet, components, parameters, form = example
    return projection.project_requested_facts(sheet, components, missing_requirements=missing_requirements,
        diagnostics=diagnostics, requested_form=form, parameters=parameters)


def validate(example, result, **changes):
    sheet, components, parameters, form = example
    kwargs = dict(facts=result["facts"], status=result["status"], missing_requirements=tuple(result["missing_requirements"]),
        diagnostics=tuple(result["diagnostics"]), requested_form=form, parameters=parameters,
        original_task=sheet["original_task"], bundle_sha256=sheet["bundle_sha256"])
    kwargs.update(changes)
    return projection.validate_saved_projection(sheet, components, **kwargs)


def selected_fields():
    return {"mean": MEAN,
        "zero": {"kind": "measurement", "target": "association", "association_key": "comp_genome_2/row/1", "metric": "first_hsp_alignment_identity_percent"},
        "denominator": {"kind": "measurement", "target": "track_count", "track_key": "comp_genome_2", "metric": "reference_input_record_count"},
        "ratio": {"kind": "ratio", "track_key": "comp_genome_2", "metric": "complete_published_reference_fraction"},
        "population": {"kind": "population", "target": "summary", "track_key": "comp_genome_2", "summary": "first_hsp_identity_summary"},
        "inventory": {"kind": "population", "target": "inventory", "inventory_key": "ref"},
        "inventory_count": {"kind": "measurement", "target": "inventory_count", "inventory_key": "ref", "metric": "observed_header_count"},
        "association": {"kind": "association", "association_key": "comp_genome_2/row/0"},
        "selection": {"kind": "selection", "association_key": "comp_genome_2/row/0"},
        "requirements": {"kind": "requirements", "scope": "all"},
        "qualifications": {"kind": "qualifications", "scope": "all"},
        "denominator_status": {"kind": "request_status", "field": "denominator"}}


def test_actual_saved_numbers_zero_populations_and_qualified_missing_values():
    example = saved_example(selected_fields())
    before = deepcopy(example)
    result = project(example)
    values = result["facts"]
    assert values["mean"]["cell"]["value"] == .4375 and values["mean"]["unit"] == "fraction"
    assert values["zero"]["cell"]["value"] == 0 and values["zero"]["availability"] == "available"
    assert values["zero"]["unit"] == "percent" and values["zero"]["native_rounding_quantum"] == .1
    assert values["denominator"]["cell"]["value"] is None and values["denominator"]["availability"] == "unavailable"
    assert values["ratio"]["denominator"]["value"] is None and values["ratio"]["fraction"]["value"] is None
    assert values["population"]["association_keys"] == ["comp_genome_2/row/0", "comp_genome_2/row/1"]
    assert values["inventory"]["record_ordinals"] == [0, 1] and values["inventory_count"]["cell"]["value"] == 2
    assert values["association"]["reference_identifier"] == "r1" and values["association"]["subject_identifier"] == "s1"
    assert values["association"]["reference_join_ref"] and values["association"]["subject_join_ref"]
    assert values["selection"]["selection"] == "pass"
    assert values["denominator_status"]["state"] == "unavailable"
    assert result["status"] == "partial" and validate(example, result) == result
    assert example == before


def test_only_requested_mean_available_despite_wider_missing_scientific_operands():
    example = saved_example()
    result = project(example)
    assert set(result["facts"]) == {"mean"} and result["status"] == "ok"
    assert example[1]["value"]["tracks"][0]["reference_input_record_count"]["value"] is None
    assert result["facts"]["mean"]["qualification_refs"]
    assert validate(example, result) == result


def test_requested_failures_keep_actual_scope_and_do_not_attach_to_unrelated_fields():
    selections = selected_fields()
    selections["absent"] = {"kind": "measurement", "target": "track_count", "track_key": "comp_genome_999",
                            "metric": "reference_input_record_count"}
    example = saved_example(selections)
    result = project(example)
    values = result["facts"]
    requirements = {r["requirement_ref"]: r for r in values["requirements"]["requirements"]}
    qualifications = {r["qualification_ref"]: r for r in values["qualifications"]["qualifications"]}
    for field in ("denominator", "ratio", "absent"):
        refs = [ref for ref in values[field]["requirement_refs"]
                if requirements[ref]["code"].startswith("proteome_requested_")]
        assert len(refs) == 1
        scope = requirements[refs[0]]["scope"]
        assert scope["track_key"] == (None if field == "absent" else "comp_genome_2")
        assert scope["association_key"] is None
        assert refs[0] not in values["mean"]["requirement_refs"]
        assert all(refs[0] not in values[other]["requirement_refs"]
                   for other in ("denominator", "ratio", "absent") if other != field)
    assert all(not qualifications[ref]["code"].startswith("proteome_requested_")
               for ref in values["mean"]["qualification_refs"])
    assert values["denominator_status"]["requirement_refs"] == values["denominator"]["requirement_refs"]
    assert validate(example, result) == result


@pytest.mark.parametrize("selection", [
    {"kind": "association", "association_key": "comp_genome_2/row/99"},
    {"kind": "selection", "association_key": "comp_genome_2/row/99"},
    {"kind": "measurement", "target": "track_count", "track_key": "comp_genome_999", "metric": "native_bi_count"},
    {"kind": "population", "target": "inventory", "inventory_key": "absent"},
])
def test_missing_target_is_unavailable_not_arbitrary_other_row(selection):
    example = saved_example({"missing": selection, "mean": MEAN})
    result = project(example)
    assert result["facts"]["missing"]["availability"] == "unavailable"
    assert result["facts"]["mean"]["cell"]["value"] == .4375
    assert [r["reason_code"] for r in result["missing_requirements"]] == ["proteome_requested_target_missing"]
    assert validate(example, result) == result


@pytest.mark.parametrize("what", ["fact", "status", "task", "bundle", "components_digest", "components_parameters", "wrapper_parameters"])
def test_saved_corruption_rejected_without_recalculation(what):
    example = saved_example()
    result = project(example)
    extra = {}
    if what == "fact":
        result["facts"]["mean"]["cell"]["value"] = .9
    elif what == "status":
        result["status"] = "partial"
    elif what == "task":
        extra["original_task"] = {**example[0]["original_task"], "task_id": "other-task"}
    elif what == "bundle":
        extra["bundle_sha256"] = "0" * 64
    elif what == "components_digest":
        example[1]["value"]["sheet_sha256"] = "0" * 64
    elif what == "components_parameters":
        example[1]["value"]["parameters"]["minimum_identity_fraction"] = .9
    else:
        example[0]["parameters"]["analysis_id"] = "other-analysis"
    with pytest.raises(ValueError):
        validate(example, result, **extra)


def test_every_fact_reference_resolves_to_an_actual_saved_pointer():
    example = saved_example(selected_fields())
    result = project(example)
    root = dict(sheet=example[0], components=example[1], missing_requirements=result["missing_requirements"], diagnostics=result["diagnostics"])
    seen = []
    def walk(value):
        if type(value) is str and value.startswith("bvbrc_proteome_"):
            kind, analysis, pointer = facts.decode_reference(value)
            assert analysis == example[2]["analysis_id"]
            node = root
            for token in pointer.split("/")[1:]:
                token = token.replace("~1", "/").replace("~0", "~")
                node = node[int(token)] if type(node) is list else node[token]
            assert node is not None
            if kind == "source_field":
                assert set(node) == {"source_ref", "sha256", "pointer", "row_ordinal", "field_name"}
            seen.append(kind)
        elif type(value) is dict:
            for child in value.values():
                walk(child)
        elif type(value) is list:
            for child in value:
                walk(child)
    walk(result["facts"])
    assert set(seen) >= {"source_field", "join", "parameter", "population", "requirement", "qualification"}


def test_saved_projection_performs_no_parser_calculator_io_or_execution(monkeypatch):
    example = saved_example(selected_fields())
    result = project(example)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved projection attempted new scientific work or IO")
    with monkeypatch.context() as patch:
        for owner, name in ((Path, "read_text"), (Path, "read_bytes"), (io, "open"), (socket, "socket"),
                            (subprocess, "run"), (subprocess, "Popen"), (native, "parse_genome_comparison"),
                            (joins, "build_native_joins"), (sheets, "build_native_sheet"), (calculators, "calculate_native_components")):
            patch.setattr(owner, name, forbidden)
        patch.setattr("builtins.open", forbidden)
        for name in ("read_protein_fasta", "read_feature_metadata", "read_genome_metadata", "read_feature_sequences", "index_original_inputs"):
            patch.setattr(inputs, name, forbidden)
        assert validate(example, result) == result


def test_changed_parameter_result_keeps_previous_projection_unchanged():
    original = saved_example({"selected": {"kind": "measurement", "target": "selection_count", "track_key": "comp_genome_2", "metric": "pass"}})
    first = project(original)
    changed = deepcopy(original)
    changed[2]["calculation_parameters"]["minimum_identity_fraction"] = .9
    changed[0]["parameters"] = deepcopy(changed[2])
    changed_components = calculators.calculate_native_components(changed[0]["native_sheet_result"]["value"], parameters=changed[2]["calculation_parameters"])
    second = project((changed[0], changed_components, changed[2], changed[3]))
    assert first["facts"]["selected"]["cell"]["value"] == 1
    assert second["facts"]["selected"]["cell"]["value"] == 0
    assert original[1]["value"]["sheet_sha256"] == changed_components["value"]["sheet_sha256"]
    assert validate(original, first) == first
