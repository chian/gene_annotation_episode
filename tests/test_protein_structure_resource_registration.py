"""Actual local registration and saved reconstruction; no protein job runs here.

The software/file fixtures are declared operands for schema and binding checks.
Constructor and reopen assertions use the real receipt, result and return
classes. They do not substitute a host or establish scientific result delivery.
"""
import asyncio
from copy import deepcopy
import hashlib
from importlib import import_module
import json
from pathlib import Path
import sys

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import independent_execution as reconstruction
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_episodes import ExecutionEpisodes, RESULTS_SCHEMA
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.native_protein_structure_contracts import (
    POLICY, requested_job_from_protein_structure,
)
from gene_annotation_episode.native_protein_structure_returns import NativeProteinStructureReturns
from gene_annotation_episode.native_protein_structure_results import NativeProteinStructureResults
from gene_annotation_episode.native_protein_structure_tool_info import protein_structure_tool_contracts
from gene_annotation_episode.practical_execution_records import GENERIC_REQUESTED_JOB_SCHEMA
from gene_annotation_episode.protein_structure_result_receipts import ProteinResultReceipts
from gene_annotation_episode.protein_structure_selection import protein_structure_result_selector_schema
from gene_annotation_episode.providers import ModelConnection
from gene_annotation_episode.runtime import assemble_workflow, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools
from gene_annotation_episode.tools import ToolRegistry


_f = import_module("verification.tool_graders_protein_structure_execution_2026-10-27_390.fixture_helpers")
PROTEIN_NAMES = {"inspect_protein_structure", "extract_protein_structure_sequence", "compare_protein_structures"}
MODES = [("inspect", None), ("extract_sequence", None),
    ("compare", "fit_then_evaluate_ca"), ("compare", "evaluate_declared_transform_ca")]


def _bindings(*, selections=MODES, software=None):
    software = _f.software() if software is None else software
    return [{"operation": operation, "scientific_mode": mode, "software": deepcopy(software)}
        for operation, mode in selections]


def _resource(workspace, bindings=None):
    value = {"kind": "local", "workspace": str(workspace), "policy": deepcopy(POLICY)}
    if bindings is not None:
        value["native_protein_structure"] = deepcopy(bindings)
    return value


def _family(store, directory, resources, **kwargs):
    return ExecutionEpisodes(None, store=store, directory=directory, run_id="protein-registration",
        resources=resources, initial_information={}, tool_registry=ToolRegistry(store),
        handoff_unit=3, acquired_record_unit=2, log_window_bytes=128, log_roles=["stdout", "stderr"],
        **kwargs)


def _selected_job(directory, operation, mode=None, *, software=None):
    request, inputs = _f.requests(operation)
    if mode == "evaluate_declared_transform_ca":
        request["parameters"].update(mode=mode, fit_selection=None, declared_transform={
            "version": "protein_structure_transform_v1", "direction": "moving_to_fixed",
            "convention": "row_vector_y_R_plus_t",
            "rotation": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            "translation_A": [0.0, 0.0, 0.0], "fixed_selection": deepcopy(request["fixed_selection"]),
            "moving_selection": deepcopy(request["moving_selection"]), "origin": "supplied",
            "received_from": None})
    job = _f.job(directory, request=request, inputs=inputs)
    if software is not None:
        job["software"] = deepcopy(software)
    return requested_job_from_protein_structure(job)


def _assignment(workspace, requested_job, resource_id="selected-local"):
    return {"version": "practical_assignment_v1", "assignment_id": "protein-registration-request",
        "resource_kind": "local", "resource_id": resource_id, "workspace": str(workspace),
        "endpoint": "usable_handoff", "requested_job": deepcopy(requested_job),
        "progress_requirements": [{"key": "handoff", "credit": 7,
            "predicate": {"kind": "requested_job_handoff"}}], "completion_keys": ["handoff"],
        "initial_context": {"revision": 0, "cwd": str(workspace), "environment": {}},
        "inventory_snapshot": {}, "constraints": {"allocation": deepcopy(POLICY)}}


def _launch(requests):
    return {"version": "execution_launch_assignment_v1", "requests": deepcopy(requests),
        "immutable_input_versions": [], "constraints": {}}


def _selector():
    return {"version": "protein_structure_result_selector_v1", "acquisition": "complete_bound_bundle",
        "saved_sheet": None, "parameters": None, "projections": [{"projection_id": "inventory",
            "family": "structure_inventory", "members": {"kind": "all_inventory_rows"}, "fields": ["model"],
            "window": None, "delivery_kind": "values"}], "return_saved_sheet": False, "sequence_allowed_uses": []}


def _results(selector):
    return {"version": "execution_results_assignment_v1", "handoff_ref": "unexecuted-handoff",
        "selector": deepcopy(selector)}


def _rna_binding():
    # An explicit supplied-features deployment; unknown optional RNA identities
    # remain null. This registration test does not import or run ViennaRNA.
    return {"operation": "analyze_rna_secondary_structure_features", "mode": "supplied_features",
        "software": {"python_executable": sys.executable,
            "python_sha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
            "python_version": _f.software()["python_version"],
            "worker_module": "gene_annotation_episode.native_rna_structure_worker",
            "worker_source_sha256": hashlib.sha256((Path(__file__).resolve().parents[1] /
                "gene_annotation_episode/native_rna_structure_worker.py").read_bytes()).hexdigest(),
            "viennarna_distribution_version": None, "rna_module_sha256": None, "rna_extension_sha256": None}}


def _deny(*args, **kwargs):
    raise AssertionError("registration must not observe, prepare, execute or authenticate scientific work")


@pytest.mark.parametrize("operation,mode", MODES)
def test_each_bound_operation_and_mode_reaches_exact_local_request_schema(tmp_path, operation, mode):
    workspace = tmp_path / "project"
    workspace.mkdir()
    job = _selected_job(workspace, operation, mode)
    bindings = _bindings(selections=[(operation, mode)])
    resources = {"selected-local": _resource(workspace, bindings)}
    with Store(tmp_path / "state") as store:
        family = _family(store, tmp_path / "run", resources)
        assignment = _assignment(workspace, job)
        expected = protein_structure_tool_contracts(bindings, resource_kind="local", resource_id="selected-local")
        request_schema = family._request_schema("selected-local", selected=True)
        assert request_schema["properties"]["requested_job"] == {
            "anyOf": [GENERIC_REQUESTED_JOB_SCHEMA, *[row["input_schema"] for row in expected]]}
        for schema, value in ((request_schema, assignment),
                (family.assignment_schema("launch_local"), assignment),
                (family.assignment_schema("launch"), _launch({"selected-local": assignment}))):
            Draft202012Validator.check_schema(schema)
            assert Draft202012Validator(schema).is_valid(value)
        assert family._validate_request(assignment) == assignment
        assert family._launch(_launch({"selected-local": assignment}))["requests"]["selected-local"] == assignment
        assert [row for row in family.resource_tool_contracts() if row["name"] in PROTEIN_NAMES] == expected
        assert family.as_record()["configuration"]["resources"] == resources


@pytest.mark.parametrize("mutation", ["operation", "mode", "software", "field_type", "unknown_field", "resource_id"])
def test_bound_tuple_and_resource_identity_reject_unselected_requests(tmp_path, mutation):
    workspace = tmp_path / "project"
    workspace.mkdir()
    job = _selected_job(workspace, "compare", "fit_then_evaluate_ca")
    resources = {"selected-local": _resource(workspace, _bindings(selections=[MODES[2]]))}
    with Store(tmp_path / "state") as store:
        family = _family(store, tmp_path / "run", resources)
        if mutation == "operation":
            job = _selected_job(workspace / "other", "inspect")
        elif mutation == "mode":
            job = _selected_job(workspace / "other", "compare", "evaluate_declared_transform_ca")
        elif mutation == "software":
            job["native_protein_structure"]["software"]["python_sha256"] = "0" * 64
        elif mutation == "field_type":
            job["native_protein_structure"]["request"]["fixed_selection"]["file_identity"]["byte_length"] = "4"
        elif mutation == "unknown_field":
            job["native_protein_structure"]["unexpected"] = True
        assignment = _assignment(workspace, job)
        if mutation == "resource_id":
            assignment["resource_id"] = "unbound-local"
        assert not Draft202012Validator(family.assignment_schema("launch_local")).is_valid(assignment)
        with pytest.raises(ValueError):
            family._validate_request(assignment)


@pytest.mark.parametrize("kind", ["api", "hmmer_api", "pbs_ssh"])
def test_nonlocal_configuration_does_not_claim_a_protein_deployment(tmp_path, kind):
    resources = {"selected": {"kind": kind, "native_protein_structure": _bindings()}}
    with Store(tmp_path / "state") as store:
        mapped = "hpc" if kind == "pbs_ssh" else "api"
        with pytest.raises(ValueError, match="native_protein_structure_resource_execution_binding_unfinished:" + mapped):
            _family(store, tmp_path / "run", resources)


@pytest.mark.parametrize("mutation", ["empty", "unknown_operation", "unknown_mode", "mode_for_inspection",
    "missing_compare_mode", "unknown_binding_field", "missing_software", "unknown_resource_setting", "unknown_kind"])
def test_invalid_or_unknown_configuration_is_rejected(tmp_path, mutation):
    rows = _bindings(selections=[MODES[2]])
    configuration = _resource(tmp_path / "project", rows)
    selected = configuration["native_protein_structure"]
    if mutation == "empty":
        selected.clear()
    elif mutation == "unknown_operation":
        selected[0]["operation"] = "structure_prediction"
    elif mutation == "unknown_mode":
        selected[0]["scientific_mode"] = "first_chain_fit"
    elif mutation == "mode_for_inspection":
        selected[0]["operation"] = "inspect"
    elif mutation == "missing_compare_mode":
        selected[0]["scientific_mode"] = None
    elif mutation == "unknown_binding_field":
        selected[0]["fallback_resource"] = "hpc"
    elif mutation == "missing_software":
        del selected[0]["software"]
    elif mutation == "unknown_resource_setting":
        configuration["protein_autodiscovery"] = True
    elif mutation == "unknown_kind":
        configuration["kind"] = "tailnet"
    with Store(tmp_path / "state") as store:
        with pytest.raises(ValueError):
            _family(store, tmp_path / "run", {"selected-local": configuration})


@pytest.mark.parametrize("policy_change", [{"memory_bytes": 21474836479},
    {"scratch_bytes": 4294967295}, {"wall_seconds": 30}])
def test_registration_retains_policy_and_actual_request_validator_rejects_conflict(tmp_path, policy_change):
    workspace = tmp_path / "project"
    workspace.mkdir()
    configuration = _resource(workspace, _bindings(selections=[MODES[0]]))
    configuration["policy"].update(policy_change)
    assignment = _assignment(workspace, _selected_job(workspace, "inspect"))
    with Store(tmp_path / "state") as store:
        family = _family(store, tmp_path / "run", {"selected-local": configuration})
        assert family.resources["selected-local"]["policy"] == configuration["policy"]
        with pytest.raises(ValueError, match="native_protein_structure_local_policy_conflict"):
            family._validate_request(assignment)


@pytest.mark.parametrize("bound", [False, True])
def test_real_helpers_construct_inertly_and_only_bound_resource_exposes_tools(tmp_path, monkeypatch, bound):
    from gene_annotation_episode.execution_progress import ExecutionTargetReader

    monkeypatch.setattr(ExecutionTargetReader, "read_target", _deny)
    monkeypatch.setattr(ExecutionTargetReader, "observe_target", _deny)
    monkeypatch.setattr(NativeProteinStructureResults, "read_result_authority", _deny)
    monkeypatch.setattr(NativeProteinStructureReturns, "authenticate", _deny)
    monkeypatch.setattr("gene_annotation_episode.native_protein_structure_local.prepare_local_protein_structure", _deny)
    monkeypatch.setattr("gene_annotation_episode.native_protein_structure_results.prepare_protein_structure_worker", _deny)
    resources = {"selected-local": _resource(tmp_path / "uncreated-project", _bindings() if bound else None)}
    with Store(tmp_path / "state") as store:
        ToolRegistry(store)  # Existing tool-owned metadata setup precedes this assertion.
        before_tables = {row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        family = _family(store, tmp_path / "uncreated-run", resources)
        assert isinstance(family.native_protein_structure_results, NativeProteinStructureResults)
        assert isinstance(family.native_protein_structure_returns, NativeProteinStructureReturns)
        assert family.native_protein_structure_returns.results is family.native_protein_structure_results
        assert family.native_protein_structure_results.owner is family
        assert isinstance(family.native_protein_structure_results.receipts, ProteinResultReceipts)
        after_tables = {row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert after_tables - before_tables <= {"runtime_execution_progress_operations", "runtime_execution_progress_custody",
            "runtime_execution_progress_snapshots", "runtime_execution_progress_dependencies"}
        assert not (tmp_path / "uncreated-project").exists()
        assert not (tmp_path / "uncreated-run").exists()
        names = {row["name"] for row in family.resource_tool_contracts()} & PROTEIN_NAMES
        assert names == (PROTEIN_NAMES if bound else set())
        if not bound:
            assert family._request_schema("selected-local", selected=True)["properties"]["requested_job"] == GENERIC_REQUESTED_JOB_SCHEMA
            assert family.assignment_schema("results") == RESULTS_SCHEMA


def test_multiple_local_resources_preserve_routes_exact_software_and_unchanged_other_tools(tmp_path):
    first_software, second_software = _f.software(), _f.software()
    second_software["python_sha256"] = "0" * 64  # Declared second deployment; never executed.
    first_bindings = _bindings(software=first_software)
    second_bindings = _bindings(selections=[MODES[3]], software=second_software)
    resources = {"local-one": _resource(tmp_path / "one", first_bindings),
        "local-two": _resource(tmp_path / "two", second_bindings), "ebi": {"kind": "hmmer_api"},
        "hpc": {"kind": "pbs_ssh", "workspace": "/lus/flare/projects/BioReason-Aurora-Test",
            "ssh_argv": ["unexecuted-ssh", "caller-supplied-host"], "python_executable": "/usr/bin/python3", "account": "EpiCalib"}}
    with Store(tmp_path / "state") as store:
        family = _family(store, tmp_path / "run", resources)
        entries = family.resource_tool_contracts()
        comparison, = [row for row in entries if row["name"] == "compare_protein_structures"]
        first, = [row for row in protein_structure_tool_contracts(first_bindings, resource_kind="local", resource_id="local-one")
            if row["name"] == "compare_protein_structures"]
        second, = protein_structure_tool_contracts(second_bindings, resource_kind="local", resource_id="local-two")
        assert comparison["input_schema"] == {"anyOf": [first["input_schema"], second["input_schema"]]}
        assert comparison["invocation_route"]["routes"] == first["invocation_route"]["routes"] + second["invocation_route"]["routes"]
        assert comparison["resources"] == "local"
        for key in ("name", "description", "instructions"):
            assert comparison[key] == first[key] == second[key]
        one = _assignment(tmp_path / "one", _selected_job(tmp_path / "one", "compare", MODES[2][1]), "local-one")
        two = _assignment(tmp_path / "two", _selected_job(tmp_path / "two", "compare", MODES[3][1], software=second_software), "local-two")
        assert family._validate_request(one) == one
        assert family._validate_request(two) == two
        assert Draft202012Validator(family.assignment_schema("launch")).is_valid(_launch({"local-one": one, "local-two": two}))
        for resource_id, assignment in (("local-two", one), ("local-one", two)):
            crossed = deepcopy(assignment)
            crossed["resource_id"] = resource_id
            assert not Draft202012Validator(family._request_schema(resource_id, selected=True)).is_valid(crossed)
        unrelated_resources = deepcopy(resources)
        for configuration in unrelated_resources.values():
            configuration.pop("native_protein_structure", None)
        unrelated = _family(store, tmp_path / "other-run", unrelated_resources)
        assert [row for row in entries if row["name"] not in PROTEIN_NAMES] == unrelated.resource_tool_contracts()
        assert family.assignment_schema("launch_api") == unrelated.assignment_schema("launch_api")
        assert family.assignment_schema("launch_hpc") == unrelated.assignment_schema("launch_hpc")


def test_exact_selector_schema_is_detached_and_coexists_with_rna_and_generic_selectors(tmp_path):
    resource = _resource(tmp_path / "project", _bindings())
    resource["native_rna_structure"] = [_rna_binding()]
    with Store(tmp_path / "state") as store:
        family = _family(store, tmp_path / "run", {"selected-local": resource})
        rna_resource = deepcopy(resource)
        del rna_resource["native_protein_structure"]
        rna = _family(store, tmp_path / "rna-run", {"selected-local": rna_resource})
        schema = family.assignment_schema("results")
        conditions = schema["properties"]["selector"]["allOf"]
        assert conditions[:-1] == rna.assignment_schema("results")["properties"]["selector"]["allOf"]
        assert conditions[-1] == {"if": {"required": ["version"], "properties": {
            "version": {"const": "protein_structure_result_selector_v1"}}},
            "then": protein_structure_result_selector_schema()}
        rna_selector = {"version": "native_rna_structure_result_selector_v1", "acquisition": "complete_bound_bundle",
            "projection": {"family": "summary", "rows": {"offset": 0, "limit": 20}, "metrics": ["pair_count"]}}
        for selector in (_selector(), rna_selector, {"paths": ["/selected/result.bin"]}, {"page": 1},
                {"version": "another_service_selector", "selected": ["id"]}):
            assert Draft202012Validator(schema).is_valid(_results(selector))
        for selector in ({"version": "protein_structure_result_selector_v1"},
                {**_selector(), "extra": True}, {"version": "native_rna_structure_result_selector_v1"}):
            assert not Draft202012Validator(schema).is_valid(_results(selector))
        conditions[-1]["then"].clear()
        assert family.assignment_schema("results")["properties"]["selector"]["allOf"][-1]["then"] == protein_structure_result_selector_schema()
        assert [row for row in family.resource_tool_contracts() if row["name"] not in PROTEIN_NAMES] == rna.resource_tool_contracts()


def test_factory_and_binding_records_round_trip_exact_resources_with_real_helpers(tmp_path):
    resources = {"selected-local": _resource(tmp_path / "project", _bindings())}
    factory = ExecutionServiceFactory(resources, {}, 3, 2, .5, log_window_bytes=128)
    expected = factory.as_record()
    resources["selected-local"]["native_protein_structure"][0]["software"]["python_sha256"] = "0" * 64
    resources["selected-local"]["policy"]["memory_bytes"] = 1
    assert factory.as_record() == expected
    factory = ExecutionServiceFactory.from_record(json.loads(json.dumps(expected)))
    with Store(tmp_path / "state") as store:
        services = factory(store, run_id="protein-registration", directory=tmp_path / "run", tool_registry=ToolRegistry(store))
        descriptor = plain(services.episode_binding_descriptors)[0]
        restored = ExecutionEpisodes(None, store=store, run_id="protein-registration", directory=tmp_path / "reopened",
            tool_registry=ToolRegistry(store), **descriptor["configuration"])
        assert restored.as_record() == descriptor
        assert restored.resources == expected["resources"]
        assert isinstance(restored.native_protein_structure_results, NativeProteinStructureResults)
        assert isinstance(restored.native_protein_structure_returns, NativeProteinStructureReturns)
        assert restored.native_protein_structure_returns.results is restored.native_protein_structure_results
        assert services.resource_tool_catalogs["local"] == restored.resource_tool_contracts()
        registry_names = set(ToolRegistry(store).catalog())
        assert not registry_names & PROTEIN_NAMES


def test_standard_saved_factory_reopens_protein_configuration_before_model_entry(tmp_path, monkeypatch):
    resources = {"selected-local": _resource(tmp_path / "uncreated-project", _bindings())}
    factory = ExecutionServiceFactory(resources, {}, 3, 2, .5, log_window_bytes=128)
    expected = factory.as_record()
    directory, workspace = tmp_path / "run", tmp_path / "state"

    class BeforeModel(Exception):
        pass

    async def before_model(connection):
        with Store(workspace) as reopened:
            settings = json.loads(reopened.db.execute("SELECT settings FROM runtime_runs").fetchone()[0])
            options = reconstruction._standard_bindings(reopened, directory, settings)
            reconstruction._check_bindings(options, settings)
            restored = assemble_workflow(reopened, build_tools(reopened), object(), directory,
                json.loads((directory / "run.json").read_text())["run_id"], settings,
                **{key: value for key, value in options.items() if key != "binding_definitions"})
            assert restored.episode_bindings.as_record() == settings["episode_bindings"]
            assert options["episode_service_factory"].as_record() == expected
            assert options["episode_service_inputs"] == "actual_tool_registry_v1"
            binding = restored.episode_bindings.for_role("results")
            assert isinstance(binding.native_protein_structure_results, NativeProteinStructureResults)
            assert isinstance(binding.native_protein_structure_returns, NativeProteinStructureReturns)
            assert binding.resources == expected["resources"]
            assert {row["name"] for row in binding.resource_tool_contracts()} & PROTEIN_NAMES == PROTEIN_NAMES
            for table in ("runtime_episodes", "runtime_actions", "provider_jobs"):
                assert reopened.db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
            assert not (tmp_path / "uncreated-project").exists()
        raise BeforeModel

    monkeypatch.setattr(ModelConnection, "__aenter__", before_model)
    with Store(workspace) as store:
        store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
        with pytest.raises(BeforeModel):
            asyncio.run(run_workflow(store, build_tools(store), run_dir=directory,
                episode_service_factory=factory, episode_service_binding=expected,
                episode_service_inputs="actual_tool_registry_v1", annotation_child_roles=("launch", "monitor", "results")))
