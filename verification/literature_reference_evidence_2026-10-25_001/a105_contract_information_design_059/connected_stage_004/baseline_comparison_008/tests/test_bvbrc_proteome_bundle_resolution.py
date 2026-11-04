"""Real pure constructors over retained synthetic bytes and valid host shapes.

Transport identities and an effective-parameter record are deliberately synthetic.
These fixtures do not claim a service task, custody decoder, or episode delivery.
The production submitted request_ref route is tested as unavailable separately.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode import bvbrc_proteome_bundle_contracts as c
from gene_annotation_episode import bvbrc_proteome_bundle_resolution as provider
from gene_annotation_episode.bvbrc_proteome_fact_contracts import requested_form_schema
from gene_annotation_episode.bvbrc_proteome_bundle_projection import validate_saved_projection
from gene_annotation_episode.bvbrc_proteome_calculators import calculate_native_components


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "verification/tool_graders_bvbrc_proteome_data_contracts_2026-10-25/construction_example_001"


def binding(raw, name):
    return dict(source_ref=name, artifact_field="artifact_ref", artifact_ref=name,
                sha256=hashlib.sha256(raw).hexdigest(), byte_count=len(raw))


def declaration(fmt):
    return dict(format=fmt, version=None, mode=None, producer_source_ref=None, transformation_evidence=[])


def member(raw, name="synthetic-native", fmt="genome_comparison_json_v1", role="proteome_native_projection"):
    content = binding(raw, name)
    return dict(role=role, source_ref=name, raw_artifact_ref=name, sha256=content["sha256"], byte_count=len(raw),
        workspace_object=dict(path="/synthetic/" + name, uuid="uuid-" + name, type="json", metadata_receipt_ref="metadata-" + name),
        task_association=dict(kind="task_result_manifest", evidence_ref="synthetic-manifest", pointer="/output_files/0",
            task_id="synthetic-task", output_path="/synthetic/" + name, output_uuid="uuid-" + name,
            byte_version_status="unknown", version_evidence=[]),
        transfer=dict(receipt_ref="receipt-" + name, body_complete=True, requested_range=None, observed_range=None,
                      total_size=len(raw), object_complete="yes"), declared_format=declaration(fmt))


def form(include_missing=False):
    selections = {
        "identity_mean": dict(kind="measurement", target="summary", track_key="comp_genome_2", summary="first_hsp_identity_summary", metric="mean"),
        "endpoint_mean": dict(kind="measurement", target="summary", track_key="comp_genome_2", summary="subject_endpoint_difference_summary", metric="mean"),
        "selected": dict(kind="measurement", target="selection_count", track_key="comp_genome_2", metric="pass"),
        "zero_identity": dict(kind="measurement", target="association", association_key="comp_genome_2/row/1", metric="first_hsp_alignment_identity_percent"),
    }
    if include_missing:
        selections["executed_reference_count"] = dict(kind="measurement", target="track_count", track_key="comp_genome_2", metric="reference_input_record_count")
    return requested_form_schema(selections)


def fixture(*, supplementary=True, effective=True):
    source = json.loads((SOURCE / "SUPPLIED_VALUES.json").read_text())
    task = json.loads((SOURCE / "SYNTHETIC_ORIGINAL_TASK.json").read_text())
    native_raw = (SOURCE / "input_000.bin").read_bytes()
    artifact = member(native_raw)
    raw = {artifact["raw_artifact_ref"]: native_raw}
    bundle = dict(version="bvbrc_appservice_artifact_bundle_v1", original_task=task, artifacts=[artifact],
        input_bindings=[], query_bindings=[], supplied_scientific_metadata=[], supplied_contents=[],
        acquisition_receipt_refs=[artifact["transfer"]["receipt_ref"]], requested_selector_sha256="1" * 64,
        status="ok", missing_requirements=[], diagnostics=[])
    parameters = dict(version="bvbrc_proteome_bundle_parameters_v1", analysis_id="synthetic-proteome-provider",
        native_documents=[dict(document_id="native", source_ref=artifact["source_ref"], raw_artifact_ref=artifact["raw_artifact_ref"],
            role="proteome_native_projection", declared_format=deepcopy(artifact["declared_format"]), source_contract=source["native"]["source_contract"])],
        primary_document_id="native", supplied_data_evidence=None,
        calculation_parameters=dict(version="bvbrc_proteome_native_parameters_proposal_v1", track_keys=["comp_genome_2"],
            minimum_identity_fraction=.6, minimum_subject_endpoint_difference_fraction=.7, allowed_hit_categories=None))
    values = []
    if supplementary:
        supplied = dict(version="bvbrc_proteome_supplied_data_v1", original_input_index=None, inventories=[],
            feature_snapshots=[], genome_snapshots=[], sequence_snapshots=[], execution_links=source["execution_links"],
            native_links=source["native_links"], metadata_links=source["metadata_links"], representation_links=[])
        parameter_raw = (SOURCE / "input_001.bin").read_bytes()
        parameter_content = binding(parameter_raw, "synthetic-effective-parameters" if effective else task["submission_source_ref"])
        raw[parameter_content["artifact_ref"]] = parameter_raw
        bundle["supplied_contents"].append(parameter_content)
        parameter_evidence = dict(content=parameter_content, pointer="/parameters")
        if effective:
            # Conditional pure-provider support only: the current production
            # TaskHandoff builder sets effective_parameters to null.
            task["effective_parameters"] = dict(value=deepcopy(task["submitted_parameters"]), evidence=parameter_evidence)
            values.append(dict(evidence=parameter_evidence, value=deepcopy(task["submitted_parameters"])))
        supplied["original_input_index"] = dict(mode="construct", parameter_source=dict(kind="effective" if effective else "submitted",
            source_field=dict(source_ref=parameter_content["source_ref"], sha256=parameter_content["sha256"],
                pointer="/parameters", row_ordinal=None, field_name=None)), additional_parameter_sources=[])
        for i, inventory in enumerate(source["inventories"]):
            raw_input = (SOURCE / f"input_{i + 2:03d}.bin").read_bytes()
            content = deepcopy(inventory["source"]["content"])
            raw[content["artifact_ref"]] = raw_input
            bundle["supplied_contents"].append(content)
            index = 1 if i == 0 else 2
            input_binding = dict(binding_id="input-" + inventory["inventory_key"], parameter_pointer=f"/user_genomes/{index}",
                kind="retained_bytes", content=content, workspace_path=task["submitted_parameters"]["user_genomes"][index],
                inline_value=None, link_evidence=None, members=[])
            bundle["input_bindings"].append(input_binding)
            supplied["inventories"].append(dict(mode="raw", inventory_key=inventory["inventory_key"], declared_format=inventory["format"],
                source=dict(kind="original_retained_input", input_binding_id=input_binding["binding_id"])))
        for i, name in enumerate(("feature_snapshots", "genome_snapshots", "sequence_snapshots")):
            snapshot = source[name][0]
            content = deepcopy(snapshot["source"]["content"])
            raw[content["artifact_ref"]] = (SOURCE / f"input_{i + 4:03d}.bin").read_bytes()
            bundle["supplied_contents"].append(content)
            row = dict(mode="raw", snapshot_key=snapshot["snapshot_key"], declared_format=snapshot["format"],
                source=dict(kind="supplied_snapshot", content=content, completeness_evidence=None), population=snapshot["population"])
            if name == "feature_snapshots":
                row["coordinate_convention"] = snapshot["coordinate_convention"]
            supplied[name].append(row)
        supplied_raw = c.canonical(supplied).encode()
        evidence = dict(content=binding(supplied_raw, "synthetic-supplied-data"), pointer="")
        values.insert(0, dict(evidence=evidence, value=supplied))
        parameters["supplied_data_evidence"] = evidence
    bundle["supplied_scientific_metadata"] = [deepcopy(r["evidence"]) for r in values]
    validate_contract("ArtifactBundle", bundle)
    return dict(bundle=bundle, artifact_bytes=raw, supplied_values=values, requested_form=form(), parameters=parameters)


def sync_supplied(case):
    """Make a new synthetic selected metadata artifact after editing a fixture."""
    value = case["supplied_values"][0]["value"]
    evidence = dict(content=binding(c.canonical(value).encode(), "synthetic-supplied-data"), pointer="")
    case["supplied_values"][0]["evidence"] = evidence
    case["parameters"]["supplied_data_evidence"] = deepcopy(evidence)
    case["bundle"]["supplied_scientific_metadata"] = [deepcopy(r["evidence"]) for r in case["supplied_values"]]


def consume(case):
    before = deepcopy(case)
    result = provider.consume_bundle(**case)
    assert case == before
    assert set(result) == {"adapter_id", "adapter_version", "status", "facts", "missing_requirements", "diagnostics", "sheet", "components"}
    assert c.validate_provider_sheet(result["sheet"]) == result["sheet"]
    return result


def codes(result):
    return {d["code"] for d in result["diagnostics"]}


def test_real_all_constructor_composition_and_saved_recalculation(monkeypatch):
    case = fixture()
    called = Counter()
    for name in ("parse_genome_comparison", "index_original_inputs", "read_protein_fasta", "read_feature_metadata",
                 "read_genome_metadata", "read_feature_sequences", "build_native_joins", "build_native_sheet", "calculate_native_components"):
        actual = getattr(provider, name)
        def call(*args, _name=name, _actual=actual, **kwargs):
            called[_name] += 1
            return _actual(*args, **kwargs)
        monkeypatch.setattr(provider, name, call)
    monkeypatch.setattr(provider, "_INPUTS", tuple((*row[:-1], getattr(provider, row[-1].__name__)) for row in provider._INPUTS))
    result = consume(case)
    assert result["status"] == "ok"
    assert result["facts"]["identity_mean"]["cell"]["value"] == .4375
    assert result["facts"]["endpoint_mean"]["cell"]["value"] == .625
    assert result["facts"]["zero_identity"]["cell"]["value"] == 0
    assert result["facts"]["selected"]["cell"]["value"] == 1
    assert called == Counter(parse_genome_comparison=1, index_original_inputs=1, read_protein_fasta=2,
        read_feature_metadata=1, read_genome_metadata=1, read_feature_sequences=1, build_native_joins=1,
        build_native_sheet=1, calculate_native_components=1)
    native_sheet = result["sheet"]["native_sheet_result"]["value"]
    assert all(b["input_record_count"]["value"] is None for b in native_sheet["joins"]["track_bindings"])
    assert [j["state"] for j in native_sheet["joins"]["reference_joins"]] == ["joined", "joined"]
    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected acquisition or construction")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    for name in called:
        monkeypatch.setattr(provider, name, forbidden)
    revised = calculate_native_components(native_sheet, parameters={**case["parameters"]["calculation_parameters"], "minimum_identity_fraction": .9})
    assert revised["value"]["tracks"][0]["selection_counts"]["pass"]["value"] == 0
    assert revised["value"]["sheet_sha256"] == result["components"]["value"]["sheet_sha256"]
    checked = validate_saved_projection(result["sheet"], result["components"], facts=result["facts"], status=result["status"],
        missing_requirements=tuple(result["missing_requirements"]), diagnostics=tuple(result["diagnostics"]),
        requested_form=case["requested_form"], parameters=case["parameters"], original_task=case["bundle"]["original_task"],
        bundle_sha256=c.digest(case["bundle"]))
    assert checked["facts"] == result["facts"]


def test_current_host_submitted_parameter_source_is_explicit_unfinished_dependency():
    case = fixture(effective=False)
    result = consume(case)
    assert result["status"] == "ok" and result["sheet"]["input_index_result"] is None
    assert "proteome_parameter_source_unbound" in codes(result)
    assert result["facts"]["identity_mean"]["cell"]["value"] == .4375


def test_narrow_native_only_values_survive_full_report_and_denominator_requirements():
    case = fixture(supplementary=False)
    result = consume(case)
    assert result["status"] == "ok" and result["sheet"]["supplied_values"] == []
    assert {"full_reports_not_retained", "input_arrays_unavailable"} <= {r["reason_code"] for r in result["missing_requirements"]}
    case["requested_form"] = form(include_missing=True)
    result = consume(case)
    assert result["status"] == "partial"
    assert result["facts"]["executed_reference_count"]["cell"]["value"] is None
    assert result["facts"]["identity_mean"]["availability"] == "available"


@pytest.mark.parametrize("field,value,code", [
    ("required_application_id", "Homology", "proteome_bundle_invalid"),
    ("task_id", "wrong", "proteome_original_task_conflict"),
])
def test_global_wrong_task_contract_is_rejected(field, value, code):
    case = fixture(supplementary=False)
    case["bundle"]["original_task"][field] = value
    with pytest.raises(c.ProteomeBundleError) as error:
        provider.consume_bundle(**case)
    assert error.value.code == code


def test_matching_wrong_application_is_rejected():
    case = fixture(supplementary=False)
    case["bundle"]["original_task"].update(required_application_id="Homology", native_application_id="Homology")
    with pytest.raises(c.ProteomeBundleError, match="application_mismatch"):
        provider.consume_bundle(**case)


@pytest.mark.parametrize("change,code", [
    ("missing", "proteome_artifact_bytes_missing"), ("digest", "proteome_artifact_digest_mismatch"),
    ("format", "proteome_artifact_format_incompatible"), ("role", "proteome_artifact_binding_conflict"),
    ("duplicate", "proteome_document_ambiguous"), ("primary", "proteome_primary_document_missing"),
    ("deployed", "proteome_deployment_evidence_unverified"), ("different", "proteome_source_contract_incompatible"),
])
def test_native_selection_failures_never_substitute_another_primary(change, code):
    case = fixture(supplementary=False)
    artifact = case["bundle"]["artifacts"][0]
    if change == "missing":
        case["artifact_bytes"].clear()
    elif change == "digest":
        case["artifact_bytes"][artifact["raw_artifact_ref"]] += b"x"
    elif change == "format":
        artifact["declared_format"]["format"] = "blast_json"
    elif change == "role":
        artifact["role"] = "other"
    elif change == "duplicate":
        case["bundle"]["artifacts"].append(deepcopy(artifact))
    elif change == "primary":
        case["parameters"]["primary_document_id"] = "absent"
    else:
        case["parameters"]["native_documents"][0]["source_contract"]["deployment_match"] = "demonstrated" if change == "deployed" else "different"
    result = consume(case)
    assert code in codes(result) and result["components"] is None
    assert result["status"] == "partial"


def replace_native(case, raw, fmt):
    artifact = member(raw, fmt=fmt)
    case["bundle"]["artifacts"] = [artifact]
    case["artifact_bytes"] = {artifact["raw_artifact_ref"]: raw}
    selection = case["parameters"]["native_documents"][0]
    selection["declared_format"] = deepcopy(artifact["declared_format"])
    return artifact


def tsv():
    from gene_annotation_episode.bvbrc_proteome_native_contracts import REFERENCE_FIELDS, COMPARISON_FIELDS
    fields = ["ref_genome_" + n for n in REFERENCE_FIELDS] + ["comp_genome_2_" + n for n in COMPARISON_FIELDS]
    displays = ["same label"] + [""] * 11 + ["same label"] + [""] * 9
    data = ["", "", "4", "r1", "", "", "", "", "", "", "", "", "bi (<->)", "", "", "4", "s1", "", "", "", "0.875", "0.750"]
    return ("\t".join(displays) + "\n" + "\t".join(fields) + "\n" + "\t".join(data) + "\n").encode()


def test_zero_start_partial_tsv_preserves_complete_prefix_rows():
    case = fixture(supplementary=False)
    raw = tsv() + b"partial-final-fragment"
    artifact = replace_native(case, raw, "genome_comparison_tsv_v1")
    artifact["transfer"].update(object_complete="no", total_size=len(raw) + 100,
        requested_range=[0, len(raw) - 1], observed_range=dict(start=0, end_inclusive=len(raw) - 1, total_size=len(raw) + 100))
    case["requested_form"] = requested_form_schema({"mean": dict(kind="measurement", target="summary", track_key="comp_genome_2", summary="first_hsp_identity_summary", metric="mean")})
    result = consume(case)
    assert result["status"] == "ok" and result["facts"]["mean"]["cell"]["value"] == .875
    assert result["sheet"]["native_results"][0]["value"]["projection_completeness"] == "complete_prefix_only"
    assert len(result["sheet"]["native_results"][0]["value"]["reference_rows"]) == 1


def test_nonzero_response_range_is_not_parsed_and_full_200_ignoring_range_is_allowed():
    case = fixture(supplementary=False)
    artifact = case["bundle"]["artifacts"][0]
    size = artifact["byte_count"]
    artifact["transfer"].update(object_complete="no", total_size=size + 9, requested_range=[9, size + 8],
        observed_range=dict(start=9, end_inclusive=size + 8, total_size=size + 9))
    result = consume(case)
    assert "proteome_nonzero_range_unsupported" in codes(result) and not result["sheet"]["native_results"]
    artifact["transfer"].update(object_complete="yes", total_size=size, observed_range=None)
    assert consume(case)["facts"]["identity_mean"]["cell"]["value"] == .4375


def test_partial_json_is_not_repaired():
    case = fixture(supplementary=False)
    artifact = replace_native(case, b'{"genome_names":', "genome_comparison_json_v1")
    artifact["transfer"].update(object_complete="unknown", body_complete=False, total_size=None)
    result = consume(case)
    assert result["components"] is None and "native_json_invalid" in codes(result)
    assert result["sheet"]["native_results"][0]["status"] == "invalid"


def test_malformed_optional_metadata_keeps_unchanged_reader_failure_and_native_values():
    case = fixture()
    selected = case["supplied_values"][0]["value"]["feature_snapshots"][0]
    content = binding(b'{"not":"array"}', "optional-invalid")
    selected["source"]["content"] = content
    case["bundle"]["supplied_contents"].append(content)
    case["artifact_bytes"][content["artifact_ref"]] = b'{"not":"array"}'
    sync_supplied(case)
    result = consume(case)
    assert result["status"] == "ok" and result["facts"]["identity_mean"]["cell"]["value"] == .4375
    assert result["sheet"]["feature_results"][0]["status"] == "invalid"
    assert result["sheet"]["feature_results"][0]["value"] is None
    assert result["sheet"]["supplied_values"] == case["supplied_values"]


def test_supplied_snapshot_completeness_and_execution_time_flags_are_not_proof():
    case = fixture()
    snapshot = case["supplied_values"][0]["value"]["feature_snapshots"][0]
    snapshot["population"].update(origin="execution_time_snapshot", population_complete="yes")
    sync_supplied(case)
    result = consume(case)
    actual = result["sheet"]["feature_results"][0]["value"]
    assert actual["source"]["object_complete"] == "unknown"
    assert actual["population"]["origin"] == "unknown" and actual["population"]["population_complete"] == "unknown"
    assert "proteome_completeness_evidence_unverified" in codes(result)
    assert result["sheet"]["supplied_values"][0]["value"]["feature_snapshots"][0]["population"]["origin"] == "execution_time_snapshot"


def test_parsed_inventory_is_retained_but_not_admitted_without_decoder():
    case = fixture()
    actual = consume(case)["sheet"]["inventory_results"][0]
    evidence = dict(content=binding(b'{"validated":true}', "unverified-construction"), pointer="")
    case["supplied_values"].append(dict(evidence=evidence, value=dict(validated=True)))
    supplied = case["supplied_values"][0]["value"]
    supplied["inventories"][0] = dict(mode="parsed", inventory_key="ref", result=actual, construction_evidence=evidence)
    sync_supplied(case)
    result = consume(case)
    assert result["status"] == "ok" and "proteome_parsed_construction_evidence_unverified" in codes(result)
    assert len(result["sheet"]["inventory_results"]) == 1
    assert result["sheet"]["inventory_results"][0]["value"]["inventory_key"] == "subject"
    assert result["sheet"]["supplied_values"] == case["supplied_values"]


def test_original_input_content_must_be_explicitly_supplied():
    case = fixture()
    case["bundle"]["supplied_contents"] = [b for b in case["bundle"]["supplied_contents"] if b["source_ref"] != "synthetic-ref"]
    result = consume(case)
    assert "proteome_input_binding_missing" in codes(result)
    assert len(result["sheet"]["inventory_results"]) == 1 and result["status"] == "ok"


def test_wrong_native_link_source_does_not_join_and_preserves_neighbors():
    case = fixture()
    case["supplied_values"][0]["value"]["native_links"][0]["native"]["source_ref"] = "wrong-source"
    sync_supplied(case)
    result = consume(case)
    joins = result["sheet"]["joins_result"]["value"]["reference_joins"]
    assert [j["state"] for j in joins] == ["conflicting", "joined"]
    assert result["facts"]["identity_mean"]["cell"]["value"] == .4375


def test_duplicate_supplied_evidence_is_ambiguous_without_first_match():
    case = fixture()
    case["supplied_values"].append(deepcopy(case["supplied_values"][0]))
    case["bundle"]["supplied_scientific_metadata"] = [r["evidence"] for r in case["supplied_values"]]
    result = consume(case)
    assert "proteome_supplied_data_ambiguous" in codes(result) and result["sheet"]["inventory_results"] == []
    assert len(result["sheet"]["supplied_values"]) == 3


def test_wrong_source_digest_in_optional_snapshot_fails_locally():
    case = fixture()
    snapshot = case["supplied_values"][0]["value"]["feature_snapshots"][0]
    replacement = deepcopy(snapshot["source"]["content"])
    replacement["source_ref"] = "synthetic-native"
    case["bundle"]["supplied_contents"].append(replacement)
    snapshot["source"]["content"] = replacement
    sync_supplied(case)
    result = consume(case)
    assert result["sheet"]["feature_results"] == [] and "proteome_supplied_source_conflict" in codes(result)
    assert result["facts"]["identity_mean"]["cell"]["value"] == .4375


def test_empty_materialized_population_distinguishes_zero_from_no_mean():
    case = fixture(supplementary=False)
    raw = json.dumps(dict(genome_names={"ref_genome": "r", "comp_genome_2": "c"}, feature_matches=[])).encode()
    replace_native(case, raw, "genome_comparison_json_v1")
    case["requested_form"] = requested_form_schema({
        "count": dict(kind="measurement", target="track_count", track_key="comp_genome_2", metric="source_association_record_count"),
        "sum": dict(kind="measurement", target="summary", track_key="comp_genome_2", summary="first_hsp_identity_summary", metric="sum"),
        "mean": dict(kind="measurement", target="summary", track_key="comp_genome_2", summary="first_hsp_identity_summary", metric="mean")})
    result = consume(case)
    assert result["status"] == "partial"
    assert result["facts"]["count"]["cell"]["value"] == result["facts"]["sum"]["cell"]["value"] == 0
    assert result["facts"]["mean"]["cell"]["state"] == "not_applicable"


@pytest.mark.parametrize("field", ["version", "mode"])
def test_explicit_unsupported_native_declaration_is_not_inferred(field):
    case = fixture(supplementary=False)
    case["parameters"]["native_documents"][0]["declared_format"][field] = "unsupported"
    case["bundle"]["artifacts"][0]["declared_format"][field] = "unsupported"
    result = consume(case)
    assert result["components"] is None and "proteome_artifact_format_incompatible" in codes(result)


def test_duplicate_document_sources_are_not_selected_by_list_order():
    case = fixture(supplementary=False)
    duplicate = deepcopy(case["parameters"]["native_documents"][0])
    duplicate["document_id"] = "another-description"
    case["parameters"]["native_documents"].append(duplicate)
    result = consume(case)
    assert result["sheet"]["native_results"] == [] and result["components"] is None
    assert [r["state"] for r in result["sheet"]["input_resolution"]] == ["invalid", "invalid"]


def test_supplied_fasta_snapshot_last_occurrence_stays_incomplete():
    case = fixture()
    selected = case["supplied_values"][0]["value"]["inventories"][0]
    content = case["bundle"]["input_bindings"][0]["content"]
    selected["source"] = dict(kind="supplied_snapshot", content=deepcopy(content), completeness_evidence=None)
    sync_supplied(case)
    result = consume(case)
    inventory = result["sheet"]["inventory_results"][0]["value"]
    assert inventory["observed_header_count"] == 2 and inventory["complete_record_count"] == 1
    assert inventory["records"][1]["sequence"] is None
    assert result["components"]["value"]["tracks"][0]["reference_input_record_count"]["value"] is None


def test_supplied_completeness_assertion_is_retained_but_not_promoted():
    case = fixture()
    evidence = dict(content=binding(b'{"complete":true}', "claimed-complete"), pointer="")
    case["supplied_values"].append(dict(evidence=evidence, value=dict(complete=True)))
    selected = case["supplied_values"][0]["value"]["feature_snapshots"][0]
    selected["source"]["completeness_evidence"] = evidence
    sync_supplied(case)
    result = consume(case)
    assert result["sheet"]["feature_results"][0]["value"]["source"]["object_complete"] == "unknown"
    assert "proteome_completeness_evidence_unverified" in codes(result)


def test_shape_valid_parsed_result_key_conflict_is_not_an_unverified_success():
    case = fixture()
    actual = consume(case)["sheet"]["inventory_results"][0]
    evidence = dict(content=binding(b"{}", "constructor-claim"), pointer="")
    case["supplied_values"][0]["value"]["inventories"][0] = dict(mode="parsed", inventory_key="different-key", result=actual, construction_evidence=evidence)
    sync_supplied(case)
    result = consume(case)
    assert "proteome_parsed_result_mismatch" in codes(result) and result["status"] == "ok"


def test_unbound_population_source_pointer_is_not_native_evidence():
    case = fixture()
    selected = case["supplied_values"][0]["value"]["feature_snapshots"][0]
    content = selected["source"]["content"]
    selected["population"]["query_source"] = dict(source_ref=content["source_ref"], sha256=content["sha256"],
        pointer="/not-retained", row_ordinal=None, field_name=None)
    sync_supplied(case)
    result = consume(case)
    assert result["sheet"]["feature_results"] == [] and "proteome_source_field_unbound" in codes(result)
    assert result["facts"]["identity_mean"]["cell"]["value"] == .4375


def test_effective_parameter_record_must_match_actual_retained_bytes():
    case = fixture()
    case["supplied_values"][1]["value"]["reference_genome_index"] = 1
    result = consume(case)
    assert result["sheet"]["input_index_result"] is None and "proteome_parameter_source_conflict" in codes(result)
    assert result["status"] == "ok"


def test_host_value_list_must_match_actual_bundle_evidence_list():
    case = fixture()
    case["supplied_values"] = case["supplied_values"][::-1]
    with pytest.raises(c.ProteomeBundleError, match="supplied_source_conflict"):
        provider.consume_bundle(**case)


def test_duplicate_fasta_identifiers_keep_occurrences_and_ambiguity():
    case = fixture()
    raw = b">r1\nACDE\n>r1\nCCCC\n"
    replacement = binding(raw, "synthetic-ref")
    case["artifact_bytes"]["synthetic-ref"] = raw
    case["bundle"]["input_bindings"][0]["content"] = replacement
    case["bundle"]["supplied_contents"] = [replacement if b["source_ref"] == "synthetic-ref" else b for b in case["bundle"]["supplied_contents"]]
    result = consume(case)
    inventory = result["sheet"]["inventory_results"][0]["value"]
    assert inventory["observed_header_count"] == 2
    assert inventory["duplicate_identifier_groups"] == [dict(identifier="r1", record_ordinals=[0, 1])]
    assert result["sheet"]["joins_result"]["value"]["reference_joins"][0]["state"] == "ambiguous"


@pytest.mark.parametrize("different", [False, True])
def test_explicit_representation_links_keep_primary_values_and_disagreement(different):
    case = fixture()
    raw = case["artifact_bytes"]["synthetic-native"]
    if different:
        raw = raw.replace(b'0.875', b'0.500')
    alternate = member(raw, "synthetic-alternate")
    case["bundle"]["artifacts"].append(alternate)
    case["bundle"]["acquisition_receipt_refs"].append(alternate["transfer"]["receipt_ref"])
    case["artifact_bytes"]["synthetic-alternate"] = raw
    selected = deepcopy(case["parameters"]["native_documents"][0])
    selected.update(document_id="alternate", source_ref="synthetic-alternate", raw_artifact_ref="synthetic-alternate")
    case["parameters"]["native_documents"].append(selected)
    case["supplied_values"][0]["value"]["representation_links"] = [dict(left_source_ref="synthetic-native", right_source_ref="synthetic-alternate",
        relation="alternate_full_projection", reference_pairs=[dict(left_row_ordinal=i, right_row_ordinal=i) for i in range(2)],
        association_pairs=[dict(left_association_key=f"comp_genome_2/row/{i}", right_association_key=f"comp_genome_2/row/{i}") for i in range(2)], source_fields=[])]
    sync_supplied(case)
    result = consume(case)
    assert result["facts"]["identity_mean"]["cell"]["value"] == .4375
    comparisons = result["sheet"]["native_sheet_result"]["value"]["representation_comparisons"]
    assert comparisons[0]["state"] == ("conflicting" if different else "equal_observed_cells")
    if different:
        assert len(comparisons[0]["conflict_source_fields"]) == 2


def test_parsed_result_with_known_conflicting_retained_source_is_scoped_error():
    case = fixture()
    actual = consume(case)["sheet"]["inventory_results"][0]
    evidence = dict(content=binding(b"{}", "constructor-claim"), pointer="")
    case["supplied_values"][0]["value"]["inventories"][0] = dict(mode="parsed", inventory_key="ref", result=actual, construction_evidence=evidence)
    # The parsed result is genuinely parser-produced; its available byte binding
    # now contradicts it, and must not be reduced to merely missing provenance.
    changed = binding(b">changed\nAAAA\n", "synthetic-ref")
    case["bundle"]["supplied_contents"] = [changed if b["source_ref"] == "synthetic-ref" else b for b in case["bundle"]["supplied_contents"]]
    case["artifact_bytes"]["synthetic-ref"] = b">changed\nAAAA\n"
    sync_supplied(case)
    result = consume(case)
    assert any(d["code"] == "proteome_supplied_source_conflict" and d["severity"] == "error" for d in result["diagnostics"])
    assert result["facts"]["identity_mean"]["cell"]["value"] == .4375


def test_non_utf8_json_key_is_a_finite_validation_error():
    case = fixture(supplementary=False)
    case["bundle"]["original_task"]["submitted_parameters"]["\ud800"] = "value"
    with pytest.raises(c.ProteomeBundleError, match="bundle_invalid"):
        provider.consume_bundle(**case)
