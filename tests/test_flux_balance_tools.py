"""Actual registry contracts and pre-read custody controls; no model execution.

Additional publication rows below are explicitly engineered metadata, not
registered FBA/native production. They use real Store artifacts, receiving
contexts/receipts and selected byte tools, without parsing scientific values.
"""
import asyncio
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.flux_balance_tools import (
    ARGUMENT_VERSION, FBA_TOOL, RESULT_VERSION, OrdinaryFluxBalanceTools,
)
from gene_annotation_episode import flux_balance_tools as ordinary
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.molecular_reference_privacy import molecular_reference_restriction
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_flux_balance_ordinary_configuration import environments, resources
from test_flux_balance_ordinary import explicit_request
from test_molecular_reference_privacy import (
    publication, source_alias, byte_registry, byte_arguments, selected_byte_call,
)


def view():
    return {"snapshot_phase": "loaded_original", "collection": "reactions", "ordinals": None,
        "row_window": {"offset": 0, "limit": 10}}


def parameters():
    return {"version": "fba_calculation_parameters_v1", "reaction_bound_tolerances": [],
        "constraint_tolerances": [], "active_flux_thresholds": [], "objective_absolute_tolerance": None,
        "variable_bound_tolerances": [], "reaction_flux_tolerances": [], "constraint_activity_tolerances": []}


def arguments(mode):
    value = {"version": ARGUMENT_VERSION, "mode": mode}
    selection = explicit_request()["model_input"]["file"]
    projection = {"version": "flux_balance_projection_selector_v1", "view": "run_diagnostics",
        "fields": ["native_run"], "row_window": {"offset": 0, "limit": 1}}
    if mode != "read_stored":
        value.update(resource_id="selected-local", binding_ordinal_0based=0)
    if mode in {"inspect", "edit"}:
        value.update(model=selection, edits=None, view=view(), return_edited_model=False)
        if mode == "edit":
            value["edits"] = {"output_format": "cobra_json", "add_metabolites": [],
                "add_reactions": [], "bounds": [], "objective": {"kind": "preserve"}}
    elif mode == "solve":
        value.update(request=explicit_request(), calculation_parameters=parameters(), projection=projection,
            return_saved_sheet=True)
    elif mode == "calculate_saved":
        value.update(sheet={**selection, "format": "flux_balance_sheet_v1"},
            calculation_parameters=parameters(), projection=projection, return_saved_sheet=False)
    else:
        value.update(result_ref="source_" + "a" * 24, view={"kind": "model", "selector": view()})
    return value


@pytest.mark.parametrize("mode", ["inspect", "edit", "solve", "read_stored", "calculate_saved"])
def test_actual_registry_exposes_one_closed_direct_contract_for_all_modes(tmp_path, mode):
    with Store(tmp_path / "store") as store:
        registry = ToolRegistry(store)
        assert FBA_TOOL not in registry.catalog()
        configured = resources(tmp_path)
        registry.configure_flux_balance_resources(configured, environments())
        registry.configure_flux_balance_resources(deepcopy(configured), deepcopy(environments()))
        entry = registry.catalog()[FBA_TOOL]
        assert entry["invocation_route"] == {"kind": "direct"} and entry["resources"] == "local"
        validator = Draft202012Validator(entry["input_schema"])
        validator.check_schema(entry["input_schema"])
        assert validator.is_valid(arguments(mode))
        malformed = {**arguments(mode), "hidden_workflow": True}
        assert not validator.is_valid(malformed)
        if mode != "read_stored":
            assert not validator.is_valid({**arguments(mode), "resource_id": "unselected"})
        assert registry.ordinary_flux_balance_backend is not None
        assert not store.list("source")


@pytest.mark.parametrize("fault", ["ordinal_bool", "ordinal_missing", "resource", "kind", "policy", "environment", "duplicate"])
def test_actual_registry_rejects_bad_explicit_resource_choices(tmp_path, fault):
    configured, table = resources(tmp_path), environments()
    if fault == "ordinal_bool": table[0]["binding_ordinal_0based"] = False
    elif fault == "ordinal_missing": table[0]["binding_ordinal_0based"] = 1
    elif fault == "resource": table[0]["resource_id"] = "not-selected"
    elif fault == "kind": configured["selected-local"]["kind"] = "hpc"
    elif fault == "policy": configured["selected-local"]["policy"]["memory_bytes"] = 1
    elif fault == "environment": table[0]["environment"] = {"PYTHONPATH": "/guessed"}
    else: table += deepcopy(table)
    with Store(tmp_path / "store") as store:
        registry = ToolRegistry(store)
        with pytest.raises((ContractError, ValueError)):
            registry.configure_flux_balance_resources(configured, table)
        assert registry._flux_balance_configuration is None


def test_received_shaped_source_cannot_trigger_private_capsule_read_without_producer(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        registry = ToolRegistry(store)
        public = store.artifact(b"{}", "application/json")
        private = store.artifact(b"private capsule must not be opened", "application/json")
        source = store.put("source", {"provider": FBA_TOOL, "accession": None, "uri": None,
            "artifact_ref": public, "text_ref": None, "request_ref": private,
            "version": RESULT_VERSION, "retrieved_at": None}, origin="tool")
        def forbidden(*args, **kwargs):
            raise AssertionError("Source shape was used as producer authority")
        monkeypatch.setattr(store, "get_artifact", forbidden)
        with pytest.raises(ContractError, match="publication_owner_required"):
            OrdinaryFluxBalanceTools(registry).read_publication(None, source["id"])


def test_manual_key_cannot_create_a_selected_ordinary_scientific_action(tmp_path):
    with Store(tmp_path / "store") as store:
        registry = ToolRegistry(store)
        registry.configure_flux_balance_resources(resources(tmp_path), environments())
        with pytest.raises(ContractError, match="current_invocation_required"):
            asyncio.run(registry.execute_async(FBA_TOOL, arguments("inspect"),
                scope={"subject_refs": []}, operation_key="invented-run:invented-episode:0"))
        assert not store.list("source")


def _file(store, reference, format_):
    metadata = store.get(reference)
    return {"artifact_ref": reference, "sha256": metadata["sha256"], "size_bytes": metadata["size"], "format": format_}


def _explicit_file_publication(value, *, field="saved_sheets", format_="flux_balance_sheet_v1",
        status="completed", reference=None, fault=None):
    """Engineered committed metadata; this does not validate a native producer."""
    reference = reference or value.refs["grade"]
    source = value.store.put("source", {"provider": FBA_TOOL, "accession": field + ":" + str(fault), "uri": None,
        "artifact_ref": value.refs["native"], "text_ref": None, "request_ref": None,
        "version": RESULT_VERSION, "retrieved_at": None}, origin="tool")
    file = _file(value.store, reference, format_)
    mode = "edit" if field == "edited_models" else "solve"
    result = {"version": RESULT_VERSION, "mode": mode, "source_ref": source["id"], field: [file]}
    refs = [source["id"], reference]
    if fault == "missing_file": refs.remove(reference)
    elif fault == "missing_source": refs.remove(source["id"])
    elif fault == "failed": status = "failed"
    elif fault == "mode": result["mode"] = mode = "inspect"
    elif fault == "version": result["version"] = "not_the_ordinary_fba_version"
    elif fault == "format": file["format"] = "cobra_json"
    elif fault == "size": file["size_bytes"] += 1
    elif fault == "sha": file["sha256"] = "0" * 64
    key = "engineered-explicit-fba-file:" + field + ":" + format_ + ":" + status + ":" + str(fault)
    value.store.db.execute("INSERT INTO tool_operations VALUES(?,?,?,?,?,?)", (key, key, FBA_TOOL,
        canonical({"mode": mode}), canonical(value.scope), canonical({"status": status,
            "operation_ref": key, "record_refs": refs, "result": result, "feedback": None})))
    return source, file


def test_owned_output_index_uses_only_finite_retained_ports_and_excludes_inputs(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        def file(label):
            return _file(store, store.artifact(label.encode(), "application/json"), "engineered_" + label)
        caller, prior, unrelated = (file(label) for label in ("caller", "prior", "unrelated"))
        selected, model, problem, solution, csv, log, manifest = (file(label) for label in
            ("selected", "model", "problem", "solution", "csv", "log", "manifest"))
        owner, started, environment, source_action, closure, binding = (file(label) for label in
            ("owner", "started", "environment", "source_action", "closure", "binding"))
        plan, execution, worker_result, sheet, calculations, projection, diagnostics = (file(label) for label in
            ("plan", "execution", "worker_result", "sheet", "calculations", "projection", "diagnostics"))
        handle, request_file, stdout, stderr, edited = (file(label) for label in
            ("handle", "request", "stdout", "stderr", "edited"))
        owned = [selected, model, problem, solution, csv, log, manifest, owner, started, environment,
            source_action, closure, binding, plan, execution, worker_result, sheet, calculations,
            projection, diagnostics, handle, request_file, stdout, stderr, edited]
        capture = {"files": [{"role": role, "retained": {"file": value}} for role, value in
            zip(("original_model", "selected_request", "effective_model", "effective_problem", "solution", "flux_csv", "native_log", "manifest"),
                (caller, selected, model, problem, solution, csv, log, manifest))],
            "prior_sources": [{"file": prior}], "controls": {role: {"file": value} for role, value in
                zip(("owner", "started", "environment"), (owner, started, environment))},
            "source_action_receipt_ref": source_action["artifact_ref"],
            "writer_closure_receipt_ref": closure["artifact_ref"], "input_binding_file": binding}
        worker = {"capture": {"plan_file": plan, "execution_receipt_file": execution,
            "worker_result_file": worker_result, "outputs": [{"observed": value} for value in
                (sheet, calculations, projection, diagnostics, None)]},
            "execution": dict(zip(("handle_file", "request_file", "stdout_file", "stderr_file"), (handle, request_file, stdout, stderr))),
            "files": dict(zip(("sheet", "calculations", "projection", "diagnostics"), (sheet, calculations, projection, diagnostics)))}
        prepared = {"resolved_inputs": [{"file": caller}, {"file": prior}], "capture": capture, "worker": worker,
            "model": {"result": {"files": [{"file": unrelated}]}}, "unrelated": unrelated}
        before, changes = canonical(prepared), store.db.total_changes
        def forbidden(*args, **kwargs): raise AssertionError("output indexing opened an artifact payload")
        monkeypatch.setattr(store, "get_artifact", forbidden)
        monkeypatch.setattr(Path, "open", forbidden)
        actual = ordinary._owned_output_references(store, prepared, {"edited_models": [edited]})
        assert actual == [value["artifact_ref"] for value in owned]
        assert len(actual) == len(set(actual)) == 25
        assert all(value["artifact_ref"] not in actual for value in (caller, prior, unrelated))
        assert canonical(prepared) == before and store.db.total_changes == changes


@pytest.mark.parametrize("field", ["sha256", "size_bytes"])
def test_owned_output_index_rejects_catalog_identity_conflict_before_payload_read(tmp_path, monkeypatch, field):
    with Store(tmp_path / "store") as store:
        ref = store.artifact(b"engineered retained output", "application/json")
        file = _file(store, ref, "cobra_json")
        file[field] = "0" * 64 if field == "sha256" else file[field] + 1
        def forbidden(*args, **kwargs): raise AssertionError("identity conflict opened payload")
        monkeypatch.setattr(store, "get_artifact", forbidden)
        with pytest.raises(ContractError, match="owned_output_identity_conflict"):
            ordinary._owned_output_references(store, {"resolved_inputs": [], "worker": None}, {"edited_models": [file]})


@pytest.mark.parametrize("field,format_", [("saved_sheets", "flux_balance_sheet_v1"),
    ("edited_models", "cobra_json"), ("edited_models", "sbml")])
@pytest.mark.parametrize("status", ["completed", "partial"])
def test_later_explicit_file_publication_does_not_revoke_identical_earlier_private_output(tmp_path, monkeypatch, field, format_, status):
    with publication(tmp_path, provider=FBA_TOOL, version=RESULT_VERSION) as value:
        reference = value.refs["grade"]  # An earlier unrequested FBA auxiliary.
        assert molecular_reference_restriction(value.store, value.context, reference, "artifact") is False
        _explicit_file_publication(value, field=field, format_=format_, status=status)
        known, changes = set(value.receipts.known(value.context.episode_id)), value.store.db.total_changes
        def forbidden(*args, **kwargs): raise AssertionError("metadata permission read payloads or traversed refs")
        with monkeypatch.context() as readonly:
            readonly.setattr(value.store, "get_artifact", forbidden)
            readonly.setattr(value.store, "_refs", forbidden)
            readonly.setattr(Path, "open", forbidden)
            assert molecular_reference_restriction(value.store, value.context, reference, "artifact") is False
            assert molecular_reference_restriction(value.store, None, reference, "artifact", private_only=True) is None
            assert molecular_reference_restriction(value.store, None, reference, "artifact") is False
            assert known == set(value.receipts.known(value.context.episode_id)) and value.store.db.total_changes == changes
        # Deliver precisely the File through an existing semantic receipt.
        value.receipts.receive(value.context.episode_id, [reference], kind="decision_input", source_index=0)
        with monkeypatch.context() as readonly:
            readonly.setattr(value.store, "get_artifact", forbidden)
            readonly.setattr(value.store, "_refs", forbidden)
            readonly.setattr(Path, "open", forbidden)
            assert molecular_reference_restriction(value.store, value.context, reference, "artifact") is True
            assert molecular_reference_restriction(value.store, value.context, reference, "source") is False


@pytest.mark.parametrize("fault", ["missing_file", "missing_source", "failed", "mode", "version", "format", "size", "sha"])
def test_malformed_or_unpublished_file_metadata_cannot_open_a_private_auxiliary(tmp_path, monkeypatch, fault):
    with publication(tmp_path, provider=FBA_TOOL, version=RESULT_VERSION, grant=("grade",)) as value:
        _explicit_file_publication(value, fault=fault)
        before, changes = set(value.receipts.known(value.context.episode_id)), value.store.db.total_changes
        def forbidden(*args, **kwargs): raise AssertionError("private classifier opened payloads")
        monkeypatch.setattr(value.store, "get_artifact", forbidden)
        monkeypatch.setattr(Path, "open", forbidden)
        for context, private_only in ((value.context, False), (None, True)):
            assert molecular_reference_restriction(value.store, context, value.refs["grade"], "artifact", private_only=private_only) is False
        assert before == set(value.receipts.known(value.context.episode_id)) and changes == value.store.db.total_changes


def test_explicit_file_publication_keeps_original_frozen_receipt_prefix(tmp_path):
    with publication(tmp_path, provider=FBA_TOOL, version=RESULT_VERSION) as value:
        _explicit_file_publication(value)
        value.receipts.receive(value.parent.episode_id, [value.refs["grade"]], kind="initial")
        assert molecular_reference_restriction(value.store, value.context, value.refs["grade"], "artifact") is False
        newer = value.child(2)
        assert molecular_reference_restriction(value.store, newer, value.refs["grade"], "artifact") is True
        assert molecular_reference_restriction(value.store, value.parent, value.refs["grade"], "artifact") is True


@pytest.mark.parametrize("kind", ["control", "diagnostic"])
def test_capsules_and_failed_diagnostics_remain_private_even_with_file_receipts(tmp_path, kind):
    with publication(tmp_path, provider=FBA_TOOL, version=RESULT_VERSION, grant=(kind,)) as value:
        _explicit_file_publication(value, reference=value.refs[kind])
        assert molecular_reference_restriction(value.store, value.context, value.refs[kind], "artifact") is False
        assert molecular_reference_restriction(value.store, None, value.refs[kind], "artifact", private_only=True) is False


@pytest.mark.parametrize("tool", ["source.read", "source.locate"])
def test_actual_byte_tools_deny_private_fba_output_alias_before_open(tmp_path, monkeypatch, tool):
    with publication(tmp_path, provider=FBA_TOOL, version=RESULT_VERSION, grant=("grade",)) as value:
        source = source_alias(value, value.refs["grade"])
        registry, original_open = byte_registry(value), Path.open
        private = value.store.path / "artifacts" / value.refs["grade"][9:11] / value.refs["grade"][9:]
        def checked(path, *args, **kwargs):
            assert path != private, "private FBA auxiliary reached the byte port"
            return original_open(path, *args, **kwargs)
        monkeypatch.setattr(Path, "open", checked)
        result, _ = selected_byte_call(value, registry, tool, byte_arguments(value, tool, source))
        assert result["status"] == "invalid" and result["result"] is None
        assert result["feedback"]["code"] == "molecular_source_artifact_not_granted"


def test_actual_byte_tool_keeps_an_explicit_file_readable_after_earlier_private_capture(tmp_path):
    with publication(tmp_path, provider=FBA_TOOL, version=RESULT_VERSION, grant=("grade",)) as value:
        _explicit_file_publication(value)
        source = source_alias(value, value.refs["grade"])
        registry = byte_registry(value)
        result, _ = selected_byte_call(value, registry, "source.read", byte_arguments(value, "source.read", source))
        assert result["status"] == "completed"
        assert result["result"]["text"] == "engineered grading " + FBA_TOOL
