"""Real information, preparation and retrieval contracts; no live service run."""
from copy import deepcopy
import builtins
import io
from pathlib import Path
import socket
import subprocess
import urllib.request

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import bvbrc_alignment_bundle_contracts as contracts
from gene_annotation_episode.api_bvbrc_appservice import BVBRCAppServiceService
from gene_annotation_episode.bvbrc_alignment_tool_info import alignment_tool_contracts
from gene_annotation_episode.bvbrc_application_definitions import prepare_application
from gene_annotation_episode.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.execution_contracts import API_SERVICE_ASSIGNMENT_SCHEMA
from gene_annotation_episode.execution_episodes import RESULTS_SCHEMA
from gene_annotation_episode.providers import ModelConnection
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary


CASES = (
    ("msa", "ordinary_alignment", "ordinary_new_alignment"),
    ("msa", "prealigned_analysis", "ordinary_prealigned"),
    ("msa", "segment_alignment", "segment_alignment"),
    ("msa", "segment_concatenation", "segment_concatenation"),
    ("msa", "mauve_alignment", "mauve_first_block_projection"),
    ("msa", "mauve_alignment", "mauve_blocks"),
    ("metacats", "files", "files"),
    ("metacats", "groups", "groups"),
    ("metacats", "auto", "auto"),
)
LAUNCH_CASES = tuple(row for row in CASES if row[1] != "prealigned_analysis")


def assignment_schema():
    value = deepcopy(API_SERVICE_ASSIGNMENT_SCHEMA)
    value["properties"]["service"] = {"const": "bvbrc_appservice"}
    value["properties"]["request"] = deepcopy(BVBRCAppServiceService.request_schema)
    return value


def entry_for(provider, name):
    return next(row for row in alignment_tool_contracts(resource_id="selected-api",
        assignment_schema=assignment_schema(), provider="bvbrc_" + provider)
        if row["name"] == "bvbrc." + provider + "." + name)


def launch_payload(provider, name):
    parameters = {"output_path": "/synthetic/work/output", "output_file": "selected"}
    if provider == "msa":
        parameters.update(alphabet="dna", aligner="Mafft", strategy="auto")
        if name.startswith("segment_"):
            parameters.update(genome_list=["1.1", "2.2"], genome_selection={
                "selected_segments": ["1", "2"], "concat_segments": name == "segment_concatenation"})
            field, kind, value = "genome_list", "inline_parameter", parameters["genome_list"]
        else:
            parameters["fasta_keyboard_input"] = ">a\nACGT\n>b\nACCT\n"
            field, kind, value = "fasta_keyboard_input", "inline_parameter", parameters["fasta_keyboard_input"]
            if name == "mauve_alignment":
                parameters["aligner"] = "progressiveMauve"
    else:
        parameters.update(input_type=name, alphabet="na", p_value=0.05)
        if name == "files":
            parameters.update(alignment_file="/synthetic/work/alignment.afa", group_file="/synthetic/work/groups.tsv",
                alignment_type="aligned_dna_fasta")
            field, kind, value = "alignment_file", "workspace_object", parameters["alignment_file"]
        elif name == "groups":
            parameters["groups"] = ["/synthetic/work/groupA", "/synthetic/work/groupB"]
            field, kind, value = "groups", "inline_parameter", parameters["groups"]
        else:
            parameters["auto_groups"] = [{"id": "featureA", "grp": "A"}, {"id": "featureB", "grp": "B"}]
            field, kind, value = "auto_groups", "inline_parameter", parameters["auto_groups"]
    binding = {"binding_id": "original-input", "parameter_pointer": "/" + field, "kind": kind,
        "content": None, "workspace_path": value if kind == "workspace_object" else None,
        "inline_value": value if kind == "inline_parameter" else None, "link_evidence": None, "members": []}
    return {"version": "api_service_assignment_v1", "resource_id": "selected-api", "service": "bvbrc_appservice",
        "request": {"version": "bvbrc_appservice_request_v1", "effect_contract": "selected_api_effects_v1",
            "required_application_id": "MSA" if provider == "msa" else "MetaCATS", "parameters": parameters,
            "start_parameters": {}, "definition_inputs": [], "input_bindings": [binding], "workspace_targets": []},
        "endpoint": "usable_handoff", "constraints": {}}


def result_payload(provider, mode):
    slot = {"analysis_id": "analysis", "slot_id": "matrix"}
    analysis = {"analysis_id": "analysis", "mode": mode, "alignment_id": deepcopy(slot), "output_role_evidence": []}
    if provider == "msa":
        analysis.update(frequency_table_id=None, consensus_alignment_id=None, tree_id=None,
            full_xmfa_slot_id=None, xmfa_document_id=None, segment_ids=[], reference=None)
    else:
        analysis.update(metadata_document_id=None, category_ids=[], adjusted_matrix_ids=[],
            chisq_table_ids=[], pair_table_ids=[], raw_r_table_ids=[])
    selection = {**slot, "semantic_role": "alignment", "source": {"kind": "acquired_role", "bundle_role": "analysis.matrix"},
        "reader": {"reader": "aligned_fasta", "id_rule": "first_whitespace_token", "encoding": "ascii"}}
    populations = [{"kind": "whole_alignment", "population_id": "matrix-population", "alignment": deepcopy(slot)}]
    requests = [{"kind": "alignment", "request_id": "matrix-counts", "population_id": "matrix-population",
        "alphabet": "dna", "case_policy": "uppercase", "pairs": [[0, 1]]}]
    fields = {"gaps": {"kind": "measurement", "analysis_id": "analysis", "request_id": "matrix-counts",
        "metric": "gap_fraction", "selector": {}}, "requirements": {"kind": "missing_requirements"}}
    if mode == "mauve_blocks":
        analysis.update(alignment_id=None, full_xmfa_slot_id="matrix", xmfa_document_id=deepcopy(slot))
        selection.update(semantic_role="full_xmfa", reader={"reader": "mauve_xmfa_v1", "dialect": "mauve1", "alphabet": "dna", "encoding": "ascii"})
        populations = []
        requests = [{"kind": "xmfa_interval_coverage", "request_id": "coverage", "document_id": deepcopy(slot),
            "selection": {"population_id": "block-population", "document_id": deepcopy(slot), "block_columns": [
                {"block_index": 0, "columns_0based": [0, 1]}], "member_numbers": [1, 3], "completeness": "complete", "evidence": []},
            "use_source_bindings": True, "basis": "cooccupied_column"}]
        fields = {"coverage": {"kind": "xmfa_coverage", "analysis_id": "analysis", "request_id": "coverage",
            "member_numbers": [1, 3], "include_intervals": True, "include_original_coverage": False},
            "requirements": {"kind": "missing_requirements"}}
    parameters = {"version": "bvbrc_alignment_bundle_parameters_v1", "artifact_selection": [selection],
        "analyses": [{"analysis": analysis, "population_plans": populations, "scientific_inputs": [],
            "read_parameters": {"source_dialect": "retained_bvbrc_" + provider},
            "calculation_parameters": {"version": "bvbrc_" + provider + "_components_v1", "requests": requests}}],
        "multiplicity_families": []}
    form = contracts.requested_form_schema(fields, provider=provider)
    requirement = {"requirement_id": "matrix-output", "role": "analysis.matrix", "required": True,
        "declared_format": {"format": selection["reader"]["reader"], "version": None,
            "mode": mode, "producer_source_ref": None, "transformation_evidence": []},
        "producer_rule_evidence": None, "exact_object": None}
    return {"version": "execution_results_assignment_v1", "handoff_ref": "synthetic-original-handoff",
        "selector": {"version": "bvbrc_appservice_result_selector_v1", "endpoint": "requested_projection",
            "requirements": [requirement], "adapter": {"adapter_id": "bvbrc_" + provider, "adapter_version": "1", "parameters": parameters},
            "requested_schema": form, "supplied_metadata": [], "supplied_capabilities": []}}


@pytest.mark.parametrize("provider,name,mode", CASES)
def test_real_mode_results_and_information_contract(provider, name, mode):
    row = entry_for(provider, name)
    assert set(row) == {"name", "description", "resources", "instructions", "input_schema", "invocation_route"}
    assert row["resources"] == "api"
    roles = [r["entry_role"] for r in row["invocation_route"]["routes"]]
    assert roles == (["results"] if name == "prealigned_analysis" else ["launch", "results"])
    assert all(r["resource_id"] == "selected-api" for r in row["invocation_route"]["routes"])
    Draft202012Validator.check_schema(row["input_schema"])
    payload = result_payload(provider, mode)
    assert Draft202012Validator(row["input_schema"]).is_valid(payload)
    selector = payload["selector"]
    assert validate_contract("ResultSelector", selector) == selector
    assert contracts.validate_parameters(selector["adapter"]["parameters"], provider=provider) == selector["adapter"]["parameters"]
    assert contracts.validate_requested_form(selector["requested_schema"], provider=provider) == selector["requested_schema"]


@pytest.mark.parametrize("provider,name,mode", LAUNCH_CASES)
def test_launch_schema_and_real_native_preparation(provider, name, mode):
    payload = launch_payload(provider, name)
    before = deepcopy(payload)
    assert Draft202012Validator(entry_for(provider, name)["input_schema"]).is_valid(payload)
    request = payload["request"]
    assert validate_contract("AppServiceRequest", request) == request
    prepared = prepare_application(request["required_application_id"], request["parameters"], request["start_parameters"])
    assert prepared["status"] == "ok", prepared
    assert prepared["value"]["native_params"] == [request["required_application_id"], request["parameters"], {}]
    assert payload == before
    assert any(d["code"] == "deployment_not_verified" for d in prepared["diagnostics"])


def test_prealigned_is_results_only_and_input_status_does_not_create_a_bypass():
    row = entry_for("msa", "prealigned_analysis")
    payload = launch_payload("msa", "ordinary_alignment")
    payload["request"]["parameters"]["input_status"] = "aligned"
    assert not Draft202012Validator(row["input_schema"]).is_valid(payload)
    # The actual definition accepts the status field, but not the file type
    # needed by the inspected producer's bypass. Enumeration cannot fix that.
    native = payload["request"]["parameters"]
    assert prepare_application("MSA", native, {})["status"] == "ok"
    native["fasta_files"] = [{"file": "/synthetic/a.fa", "type": "aligned_dna_fasta"}]
    prepared = prepare_application("MSA", native, {})
    assert prepared["status"] == "invalid"
    assert any(d["code"] == "value_not_in_native_enum" for d in prepared["diagnostics"])


@pytest.mark.parametrize("change", ["segments_missing", "segments_empty", "genomes_empty", "mixed_file", "mixed_features", "mixed_keyboard", "mauve", "protein"])
def test_segment_launch_rejects_wrong_native_branch(change):
    payload = launch_payload("msa", "segment_alignment")
    parameters = payload["request"]["parameters"]
    if change == "segments_missing":
        del parameters["genome_selection"]
    elif change == "segments_empty":
        parameters["genome_selection"]["selected_segments"] = []
    elif change == "genomes_empty":
        parameters["genome_list"] = []
    elif change == "mixed_file":
        parameters["fasta_files"] = [{"file": "/synthetic/a.fa", "type": "feature_dna_fasta"}]
    elif change == "mixed_features":
        parameters["feature_list"] = ["a"]
    elif change == "mixed_keyboard":
        parameters["fasta_keyboard_input"] = ">a\nAC\n"
    elif change == "mauve":
        parameters["aligner"] = "progressiveMauve"
    else:
        parameters["alphabet"] = "protein"
    assert not Draft202012Validator(entry_for("msa", "segment_alignment")["input_schema"]).is_valid(payload)


@pytest.mark.parametrize("value", [None, False, 1, "true"])
def test_concatenation_requires_explicit_native_boolean(value):
    payload = launch_payload("msa", "segment_concatenation")
    if value is None:
        del payload["request"]["parameters"]["genome_selection"]["concat_segments"]
    else:
        payload["request"]["parameters"]["genome_selection"]["concat_segments"] = value
    assert not Draft202012Validator(entry_for("msa", "segment_concatenation")["input_schema"]).is_valid(payload)


def test_one_concatenated_job_can_supply_separate_segment_view():
    payload = launch_payload("msa", "segment_concatenation")
    assert Draft202012Validator(entry_for("msa", "segment_alignment")["input_schema"]).is_valid(payload)
    assert not Draft202012Validator(entry_for("msa", "ordinary_alignment")["input_schema"]).is_valid(payload)
    assert not Draft202012Validator(entry_for("msa", "mauve_alignment")["input_schema"]).is_valid(payload)


@pytest.mark.parametrize("name,field,wrong", [("files", "group_file", None), ("files", "alignment_file", ""),
    ("groups", "groups", []), ("auto", "auto_groups", []), ("auto", "auto_groups", [{"id": "f"}])])
def test_metacats_modes_require_their_real_inputs(name, field, wrong):
    payload = launch_payload("metacats", name)
    if wrong is None:
        del payload["request"]["parameters"][field]
    else:
        payload["request"]["parameters"][field] = wrong
    assert not Draft202012Validator(entry_for("metacats", name)["input_schema"]).is_valid(payload)


@pytest.mark.parametrize("provider,name,mode", LAUNCH_CASES)
@pytest.mark.parametrize("field", ["resource_id", "service", "application"])
def test_launch_cannot_switch_configured_owner_or_application(provider, name, mode, field):
    payload = launch_payload(provider, name)
    if field == "application":
        payload["request"]["required_application_id"] = "Homology"
    else:
        payload[field] = "not-selected"
    assert not Draft202012Validator(entry_for(provider, name)["input_schema"]).is_valid(payload)


@pytest.mark.parametrize("provider,name,mode", CASES)
@pytest.mark.parametrize("change", ["adapter", "version", "mode", "extra_parameter", "reader"])
def test_results_preserve_exact_provider_and_analysis_mode(provider, name, mode, change):
    payload = result_payload(provider, mode)
    adapter = payload["selector"]["adapter"]
    if change == "adapter":
        adapter["adapter_id"] = "bvbrc_homology"
    elif change == "version":
        adapter["adapter_version"] = "2"
    elif change == "mode":
        adapter["parameters"]["analyses"][0]["analysis"]["mode"] = (
            "ordinary_new_alignment" if mode != "ordinary_new_alignment" else "ordinary_prealigned")
    elif change == "extra_parameter":
        adapter["parameters"]["analyses"][0]["analysis"]["scientific_mode"] = mode
    else:
        adapter["parameters"]["artifact_selection"][0]["reader"]["encoding"] = "invented"
    assert not Draft202012Validator(entry_for(provider, name)["input_schema"]).is_valid(payload)


def test_schemas_and_caller_constraints_remain_independent():
    caller = assignment_schema()
    caller["allOf"] = [{"properties": {"constraints": {"maxProperties": 0}}}]
    before, results_before = deepcopy(caller), deepcopy(RESULTS_SCHEMA)
    base = contracts.parameters_schema(provider="msa")
    rows = alignment_tool_contracts(resource_id="selected-api", assignment_schema=caller, provider="bvbrc_msa")
    launch = rows[0]["input_schema"]["oneOf"][0]
    assert launch["allOf"][0] == caller["allOf"][0]
    payload = launch_payload("msa", "ordinary_alignment")
    payload["constraints"] = {"unapproved": True}
    assert not Draft202012Validator(rows[0]["input_schema"]).is_valid(payload)
    launch["properties"]["service"] = {"const": "changed"}
    assert caller == before and RESULTS_SCHEMA == results_before
    assert contracts.parameters_schema(provider="msa") == base


def test_no_execution_or_io_during_information_enumeration(monkeypatch):
    caller = assignment_schema()
    # Production contract JSON is loaded before the prohibited operation region.
    # Sentinels prohibit actions; no scientific result is mocked.
    from gene_annotation_episode.bvbrc_appservice_contracts import contract_schema
    contract_schema("ResultSelector")
    def forbidden(*args, **kwargs):
        raise AssertionError("information enumeration attempted an operation")
    with monkeypatch.context() as patch:
        for owner, name in ((builtins, "open"), (io, "open"), (Path, "read_text"), (Path, "read_bytes"),
                (Path, "open"), (socket, "create_connection"), (socket.socket, "connect"),
                (urllib.request, "urlopen"), (subprocess, "Popen"), (subprocess, "run"),
                (BVBRCAppServiceService, "prepare"), (BVBRCAppServiceService, "invoke"), (ModelConnection, "complete")):
            patch.setattr(owner, name, forbidden)
        rows = [row for provider in ("bvbrc_msa", "bvbrc_metacats") for row in
            alignment_tool_contracts(resource_id="selected-api", assignment_schema=caller, provider=provider)]
    assert len(rows) == 8


def test_library_selects_multiple_real_tools_and_delivers_exact_instructions(tmp_path):
    rows = [row for provider in ("bvbrc_msa", "bvbrc_metacats") for row in alignment_tool_contracts(
        resource_id="selected-api", assignment_schema=assignment_schema(), provider=provider)]
    library = ScientificToolLibrary.freeze(tmp_path / "library", catalog=[], tool_info=True,
        resource_catalogs={"api": rows})
    parent = library.parent_tool_info(rows)
    assert len(parent) == 8
    assert all(set(row) == {"name", "description", "resources"} for row in parent)
    selected = [{"name": "bvbrc.msa.mauve_alignment", "resources": "api"},
        {"name": "bvbrc.metacats.files", "resources": "api"}]
    information = library.resolve_tool_info(selected, rows)
    invocations = library.resolve_invocations(selected, rows)
    assert [row["name"] for row in information] == [row["name"] for row in selected]
    assert all(set(row) == {"name", "description", "resources", "instructions"} for row in information)
    for info, invocation in zip(information, invocations):
        original = next(row for row in rows if row["name"] == info["name"])
        assert invocation == original and info["instructions"] == original["instructions"]
    forged = deepcopy(information)
    forged[0]["instructions"] = "Invent new tools"
    with pytest.raises(ValueError, match="scientific_tool_info_changed"):
        library.resolve_tool_info(forged, rows)


@pytest.mark.parametrize("resource", [None, "", " ", "bad\0id", 1])
def test_explicit_resource_required(resource):
    with pytest.raises(ValueError, match="alignment_explicit_api_resource_required"):
        alignment_tool_contracts(resource_id=resource, assignment_schema=assignment_schema(), provider="bvbrc_msa")


@pytest.mark.parametrize("provider", [None, "msa", "bvbrc_homology", [], 1])
def test_exact_provider_required(provider):
    with pytest.raises(ValueError, match="alignment_provider_invalid"):
        alignment_tool_contracts(resource_id="selected-api", assignment_schema=assignment_schema(), provider=provider)


def test_actual_assignment_schema_required():
    with pytest.raises(ValueError, match="alignment_api_assignment_schema_required"):
        alignment_tool_contracts(resource_id="selected-api", assignment_schema=[], provider="bvbrc_msa")
