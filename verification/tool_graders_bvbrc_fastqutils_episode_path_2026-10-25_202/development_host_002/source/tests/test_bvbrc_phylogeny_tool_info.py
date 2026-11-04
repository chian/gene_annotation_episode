"""Real information/provider contracts; synthetic inputs do not claim a live run."""
from copy import deepcopy
import builtins
import io
from pathlib import Path
import socket
import subprocess
import urllib.request

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import bvbrc_codon_tree_bundle_adapter as codon
from gene_annotation_episode import bvbrc_gene_tree_bundle_adapter as gene
from gene_annotation_episode import bvbrc_phylogeny_bundle_contracts as contracts
from gene_annotation_episode import bvbrc_phylogeny_bundle_projection as projection
from gene_annotation_episode import bvbrc_phylogeny_bundle_resolution as resolution
from gene_annotation_episode import phylogeny_formats
from gene_annotation_episode.api_bvbrc_appservice import BVBRCAppServiceService
from gene_annotation_episode.bvbrc_application_definitions import prepare_application
from gene_annotation_episode.bvbrc_appservice_contracts import ContractValidationError, validate_contract
from gene_annotation_episode.bvbrc_phylogeny_tool_info import phylogeny_tool_contracts
from gene_annotation_episode.execution_contracts import API_SERVICE_ASSIGNMENT_SCHEMA
from gene_annotation_episode.execution_episodes import RESULTS_SCHEMA
from gene_annotation_episode.providers import ModelConnection
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from test_bvbrc_phylogeny_bundle_resolution import fixture, slot


CASES = (
    ("bvbrc_gene_tree", "gene_tree", "GeneTree", gene),
    ("bvbrc_gene_tree", "concatenated_sequence_loci", "GeneTree", gene),
    ("bvbrc_codon_tree", "core_genome_codon_protein", "CodonTree", codon),
)
GENOME_IDS = ["1075089.3", "1171377.3", "1222034.3", "1232659.5", "1249526.3",
              "1249531.3", "1261658.3", "1263829.3", "1263831.3"]


def assignment_schema():
    # The same existing schema owners used by APIServiceExecution.assignment_schema.
    schema = deepcopy(API_SERVICE_ASSIGNMENT_SCHEMA)
    schema["properties"]["service"] = {"const": "bvbrc_appservice"}
    schema["properties"]["request"] = deepcopy(BVBRCAppServiceService.request_schema)
    return schema


def entry_for(provider, mode, *, resource="selected-api"):
    return next(row for row in phylogeny_tool_contracts(resource_id=resource,
        assignment_schema=assignment_schema(), provider=provider)
        if row["name"].endswith("." + mode))


def native_request(mode):
    app = "CodonTree" if mode == "core_genome_codon_protein" else "GeneTree"
    parameters = {"output_path": "/synthetic/work/output", "output_file": "selected"}
    if app == "CodonTree":
        parameters.update(genome_ids=deepcopy(GENOME_IDS), genome_groups=[], optional_genome_ids=[],
            number_of_genes=10, bootstraps=100, max_genomes_missing=1, max_allowed_dups=0)
        inputs = [{"binding_id": "genomes", "parameter_pointer": "/genome_ids", "kind": "inline_parameter",
            "content": None, "workspace_path": None, "inline_value": deepcopy(GENOME_IDS),
            "link_evidence": None, "members": []}]
    else:
        parameters.update(alphabet="Protein", recipe="RAxML", sequences=[{
            "type": "aligned_protein_fasta", "filename": "/synthetic/work/locusA.fa"}])
        if mode == "concatenated_sequence_loci":
            parameters["genome_selection"] = {"concat_segments": True}
            parameters["sequences"].append({"type": "feature_protein_fasta", "filename": "/synthetic/work/locusB.fa"})
        inputs = [{"binding_id": "locus" + str(i), "parameter_pointer": f"/sequences/{i}/filename",
            "kind": "workspace_object", "content": None, "workspace_path": item["filename"],
            "inline_value": None, "link_evidence": None, "members": []}
            for i, item in enumerate(parameters["sequences"])]
    return {"version": "bvbrc_appservice_request_v1", "effect_contract": "selected_api_effects_v1",
        "required_application_id": app, "parameters": parameters, "start_parameters": {},
        "definition_inputs": [], "input_bindings": inputs, "workspace_targets": []}


def launch_payload(mode):
    return {"version": "api_service_assignment_v1", "resource_id": "selected-api",
        "service": "bvbrc_appservice", "request": native_request(mode),
        "endpoint": "usable_handoff", "constraints": {}}


def result_payload(provider, mode, adapter):
    bundle, data, values, parameters = fixture(provider.removeprefix("bvbrc_"))
    parameters["analyses"][0]["analysis"]["mode"] = mode
    for artifact in bundle["artifacts"]:
        artifact["declared_format"]["mode"] = mode
    form = adapter.requested_form_schema({
        "tips": {"metric": "tree_tip_count", "analysis_id": "a", "population_id": "leaves", "tree": slot("tree", tree=True)},
        "gap_fraction": {"metric": "alignment_gap_fraction", "analysis_id": "a", "population_id": "matrix"},
        "sites": {"metric": "site_rows", "analysis_id": "a", "population_id": "matrix", "columns_0based": [0, 1]},
        "branches": {"metric": "branch_rows", "analysis_id": "a", "population_id": "leaves", "tree": slot("tree", tree=True), "node_indices": [2, 5]},
        "requirements": {"metric": "missing_requirements"},
        "qualifications": {"metric": "qualifications", "analysis_id": "a", "slot_id": None},
    })
    selector = {"version": "bvbrc_appservice_result_selector_v1", "endpoint": "requested_projection",
        "requirements": [{"requirement_id": row["role"], "role": row["role"], "required": True,
            "declared_format": deepcopy(row["declared_format"]), "producer_rule_evidence": None,
            "exact_object": None} for row in bundle["artifacts"]],
        "adapter": {"adapter_id": adapter.ADAPTER_ID, "adapter_version": adapter.ADAPTER_VERSION,
                    "parameters": parameters}, "requested_schema": form,
        "supplied_metadata": deepcopy(bundle["supplied_scientific_metadata"]), "supplied_capabilities": []}
    return ({"version": "execution_results_assignment_v1",
             "handoff_ref": "synthetic-original-handoff", "selector": selector},
            (bundle, data, values, parameters))


@pytest.mark.parametrize("provider,mode,application,adapter", CASES)
def test_real_launch_and_results_contracts(provider, mode, application, adapter):
    entry = entry_for(provider, mode)
    assert set(entry) == {"name", "description", "resources", "instructions", "input_schema", "invocation_route"}
    assert entry["name"] == "bvbrc." + provider.removeprefix("bvbrc_") + "." + mode
    assert entry["resources"] == "api"
    assert entry["invocation_route"] == {"kind": "commission", "routes": [
        {"entry_role": "launch", "resource_id": "selected-api", "resource_role": "launch_api"},
        {"entry_role": "results", "resource_id": "selected-api", "resource_role": "results"}]}
    Draft202012Validator.check_schema(entry["input_schema"])
    validate = Draft202012Validator(entry["input_schema"])
    launch = launch_payload(mode)
    assert validate.is_valid(launch), list(validate.iter_errors(launch))
    assert validate_contract("AppServiceRequest", launch["request"]) == launch["request"]
    prepared = prepare_application(application, launch["request"]["parameters"], {})
    assert prepared["status"] == "ok"
    assert prepared["value"]["native_application_id"] == application
    assert prepared["value"]["native_params"] == [application, launch["request"]["parameters"], {}]
    result, _ = result_payload(provider, mode, adapter)
    assert validate.is_valid(result), list(validate.iter_errors(result))
    assert validate_contract("ResultSelector", result["selector"]) == result["selector"]
    assert adapter.validate_parameters(result["selector"]["adapter"]["parameters"]) == result["selector"]["adapter"]["parameters"]
    assert adapter.validate_requested_form(result["selector"]["requested_schema"]) == result["selector"]["requested_schema"]


@pytest.mark.parametrize("provider,mode,application,adapter", CASES)
@pytest.mark.parametrize("field", ["resource", "service", "application", "missing_request", "version"])
def test_malformed_launch_envelopes_rejected(provider, mode, application, adapter, field):
    value = launch_payload(mode)
    if field == "application":
        value["request"]["required_application_id"] = "Homology"
    elif field == "missing_request":
        del value["request"]
    else:
        value["resource_id" if field == "resource" else field] = "not-selected"
    assert not Draft202012Validator(entry_for(provider, mode)["input_schema"]).is_valid(value)


@pytest.mark.parametrize("value", [None, False, "true", 1, {}])
def test_concatenated_launch_requires_actual_explicit_boolean(value):
    request = launch_payload("concatenated_sequence_loci")
    if value is None:
        del request["request"]["parameters"]["genome_selection"]
    else:
        request["request"]["parameters"]["genome_selection"]["concat_segments"] = value
    assert not Draft202012Validator(entry_for("bvbrc_gene_tree", "concatenated_sequence_loci")["input_schema"]).is_valid(request)


def test_one_native_concatenated_job_can_still_supply_a_per_locus_view():
    launch = launch_payload("concatenated_sequence_loci")
    for mode in ("gene_tree", "concatenated_sequence_loci"):
        assert Draft202012Validator(entry_for("bvbrc_gene_tree", mode)["input_schema"]).is_valid(launch)


@pytest.mark.parametrize("provider,mode,application,adapter", CASES)
def test_native_parameter_and_input_binding_validation_keeps_actual_owners(provider, mode, application, adapter):
    native = native_request(mode)
    native["input_bindings"][0]["parameter_pointer"] = "/output_file"
    with pytest.raises(ContractValidationError, match="input_parameter_value_conflict"):
        validate_contract("AppServiceRequest", native)
    bad = deepcopy(native["parameters"])
    if application == "GeneTree":
        bad["alphabet"] = "RNA"
        bad["sequences"][0]["type"] = "invented_sequence_type"
    else:
        bad["number_of_genes"] = "ten"
        bad["genome_ids"] = []
    prepared = prepare_application(application, bad, {})
    assert prepared["status"] == "invalid" and prepared["value"] is None


@pytest.mark.parametrize("provider,mode,application,adapter", CASES)
@pytest.mark.parametrize("change", ["mode", "adapter", "adapter_version", "extra", "reader", "missing_analyses", "population"])
def test_malformed_result_parameters_rejected(provider, mode, application, adapter, change):
    value, _ = result_payload(provider, mode, adapter)
    selected = value["selector"]["adapter"]
    parameters = selected["parameters"]
    if change == "mode":
        parameters["analyses"][0]["analysis"]["mode"] = "core_genome_codon_protein" if application == "GeneTree" else "gene_tree"
    elif change == "adapter":
        selected["adapter_id"] = "bvbrc_homology"
    elif change == "adapter_version":
        selected["adapter_version"] = "2"
    elif change == "extra":
        parameters["analyses"][0]["analysis"]["scientific_mode"] = mode
    elif change == "reader":
        parameters["artifact_selection"][0]["reader"]["encoding"] = "invented"
    elif change == "missing_analyses":
        del parameters["analyses"]
    else:
        parameters["analyses"][0]["population_plans"][0]["alignment"]["slot_id"] = 17
    assert not Draft202012Validator(entry_for(provider, mode)["input_schema"]).is_valid(value)
    if change not in {"adapter", "adapter_version"}:
        with pytest.raises(ContractValidationError):
            adapter.validate_parameters(parameters)


def test_gene_result_modes_are_distinct_without_silently_filtering_analyses():
    for mode in ("gene_tree", "concatenated_sequence_loci"):
        value, _ = result_payload("bvbrc_gene_tree", mode, gene)
        parameters = value["selector"]["adapter"]["parameters"]
        assert gene.validate_parameters(parameters) == parameters
        other = "gene_tree" if mode == "concatenated_sequence_loci" else "concatenated_sequence_loci"
        assert not Draft202012Validator(entry_for("bvbrc_gene_tree", other)["input_schema"]).is_valid(value)


@pytest.mark.parametrize("provider,mode,application,adapter", CASES)
def test_actual_parsers_providers_calculators_and_typed_requests(provider, mode, application, adapter):
    payload, (bundle, data, values, parameters) = result_payload(provider, mode, adapter)
    form = payload["selector"]["requested_schema"]
    before = deepcopy((bundle, data, values, parameters, form))
    result = adapter.consume_bundle(bundle, artifact_bytes=data, supplied_values=values,
        requested_form=form, parameters=parameters)
    assert result["status"] in {"ok", "partial"}
    assert result["facts"]["tips"] == 4
    assert result["facts"]["gap_fraction"] == 0.125
    assert result["facts"]["sites"][1]["gap_count"] == 1
    assert result["facts"]["branches"][0]["length"] == 0
    assert result["facts"]["branches"][1]["length"] == -0.1
    assert all(row["length_unit"] == "native_unknown" for row in result["facts"]["branches"])
    assert Draft202012Validator(form).is_valid(result["facts"])
    sheet = result["sheet"]["analyses"][0]["sheet"]
    assert sheet["mode"] == mode and len(sheet["read_outcomes"]) == 2
    assert result["components"]["analyses"][0]["components"]["alignments"][0]["cell_count"]["value"] == 16
    assert (bundle, data, values, parameters, form) == before
    forged_form = deepcopy(form)
    forged_form["properties"]["tips"]["type"] = "string"
    with pytest.raises(ContractValidationError, match="phylogeny_requested_form_invalid"):
        adapter.validate_requested_form(forged_form)


@pytest.mark.parametrize("provider,mode,application,adapter", CASES)
def test_schema_narrowing_retains_actual_provider_contract_and_caller_schema(provider, mode, application, adapter):
    caller = assignment_schema()
    caller["allOf"] = [{"properties": {"constraints": {"maxProperties": 0}}}]
    before = deepcopy(caller)
    base_parameters = contracts.parameters_schema(provider=provider.removeprefix("bvbrc_"))
    base_before = deepcopy(base_parameters)
    results_before = deepcopy(RESULTS_SCHEMA)
    rows = phylogeny_tool_contracts(resource_id="selected-api", assignment_schema=caller, provider=provider)
    entry = next(r for r in rows if r["name"].endswith("." + mode))
    selector = entry["input_schema"]["oneOf"][1]["properties"]["selector"]
    narrowed = deepcopy(selector["allOf"][0]["properties"]["adapter"]["properties"]["parameters"])
    del narrowed["$id"]
    mode_properties = narrowed["properties"]["analyses"]["items"]["properties"]["analysis"]["properties"]
    assert mode_properties["mode"] == {"const": mode}
    mode_properties["mode"] = deepcopy(base_parameters["properties"]["analyses"]["items"]["properties"]["analysis"]["properties"]["mode"])
    assert narrowed == base_parameters == base_before
    assert entry["input_schema"]["oneOf"][0]["allOf"][0] == caller["allOf"][0]
    entry["input_schema"]["oneOf"][0]["properties"]["service"] = {"const": "mutated"}
    assert caller == before and RESULTS_SCHEMA == results_before
    assert phylogeny_tool_contracts(resource_id="selected-api", assignment_schema=caller, provider=provider) != rows


def test_enumeration_has_no_io_job_model_or_scientific_action(monkeypatch):
    caller = assignment_schema()
    # These are forbidden-action sentinels, never scientific return mocks.
    def forbidden(*args, **kwargs):
        raise AssertionError("information enumeration attempted an action")
    with monkeypatch.context() as patch:
        for owner, name in ((builtins, "open"), (io, "open"), (Path, "read_text"),
                (Path, "read_bytes"), (Path, "open"), (socket, "create_connection"),
                (socket.socket, "connect"), (urllib.request, "urlopen"),
                (urllib.request.OpenerDirector, "open"), (subprocess, "Popen"),
                (subprocess, "run"), (BVBRCAppServiceService, "prepare"),
                (BVBRCAppServiceService, "invoke"), (ModelConnection, "complete"), (gene, "consume_bundle"),
                (codon, "consume_bundle"), (projection, "consume_bundle"),
                (resolution, "parse_reader"), (phylogeny_formats, "parse_newick")):
            patch.setattr(owner, name, forbidden)
        rows = [row for provider in ("bvbrc_gene_tree", "bvbrc_codon_tree")
            for row in phylogeny_tool_contracts(resource_id="selected-api", assignment_schema=caller, provider=provider)]
    assert len(rows) == 3


def test_information_retrieval_keeps_instructions_and_invocations_separate(tmp_path):
    rows = [row for provider in ("bvbrc_gene_tree", "bvbrc_codon_tree")
        for row in phylogeny_tool_contracts(resource_id="selected-api", assignment_schema=assignment_schema(), provider=provider)]
    library = ScientificToolLibrary.freeze(tmp_path / "library", catalog=[], tool_info=True,
        resource_catalogs={"api": rows})
    selected = [{"name": row["name"], "resources": "api"} for row in rows]
    instructions = library.resolve_tool_info(selected, rows)
    invocations = library.resolve_invocations(selected, rows)
    assert all(set(row) == {"name", "description", "resources", "instructions"} for row in instructions)
    assert [row["instructions"] for row in instructions] == [row["instructions"] for row in invocations]
    assert [row["input_schema"] for row in invocations] == [row["input_schema"] for row in rows]
    for row in instructions:
        assert "supplied_contents" in row["instructions"]
        assert "calibrated annotation probabilities" in row["instructions"]
        assert "process liveness" in row["instructions"]


@pytest.mark.parametrize("resource", [None, "", "bad\0id", 1])
def test_explicit_resource_required(resource):
    with pytest.raises(ValueError, match="phylogeny_explicit_api_resource_required"):
        phylogeny_tool_contracts(resource_id=resource, assignment_schema=assignment_schema(), provider="bvbrc_gene_tree")


@pytest.mark.parametrize("provider", [None, "gene_tree", "bvbrc_homology", [], 1])
def test_exact_provider_identity_required(provider):
    with pytest.raises(ValueError, match="phylogeny_provider_invalid"):
        phylogeny_tool_contracts(resource_id="selected-api", assignment_schema=assignment_schema(), provider=provider)


def test_actual_assignment_schema_required():
    with pytest.raises(ValueError, match="phylogeny_api_assignment_schema_required"):
        phylogeny_tool_contracts(resource_id="selected-api", assignment_schema=[], provider="bvbrc_gene_tree")
