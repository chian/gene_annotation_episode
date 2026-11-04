"""Engineered ordinary custody controls, not evidence of native ORF science.

Lifecycle preparation/status/collection are explicit unit replacements. The
literal JSON role fixtures are never presented as genuine source execution.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from types import MethodType, SimpleNamespace

import pytest
from jsonschema import Draft202012Validator
from method_loop.identities import EpisodeRef

from gene_annotation_episode.domain import identity
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.genomic_overlap_result_receipts import read_control
from gene_annotation_episode import molecular_sequence_ordinary as ordinary
from gene_annotation_episode import molecular_sequence_results as results
from gene_annotation_episode import molecular_sequence_result_contracts as contracts
from gene_annotation_episode.molecular_measurement_tools import MolecularOperationUnpublished
from gene_annotation_episode.native_file_capture import retained_native_file
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from tests.test_molecular_sequence_ordinary import selected_call, _lifecycle, _metadata_fixture, _write, _pin


@pytest.fixture
def ordinary_owner(tmp_path, monkeypatch, selected_call):
    store = Store(tmp_path / "state")
    store.create_problem(raw_sequence="ATGAAATAA", molecule="dna")
    registry = ToolRegistry(store)
    publication_token = registry._publications.set([])
    for sql in (
        "CREATE TABLE runtime_episodes(run_id TEXT,episode_id TEXT,path TEXT,request TEXT,PRIMARY KEY(run_id,episode_id))",
        "CREATE TABLE runtime_actions(run_id TEXT,episode_id TEXT,decision_index INTEGER,action TEXT,result TEXT,PRIMARY KEY(run_id,episode_id,decision_index))",
    ):
        store.db.execute(sql)
    scope = store.validate_scope()
    run, path = "engineering-ordinary-custody", (("scientific_process", "engineering-root"),)
    episode = EpisodeRef(run, path).episode_id
    assignment = {"engineering_fixture": "ordinary custody only"}
    request = {"message": {"scope": scope, "episode_assignment": assignment},
        "report_contract": {"measurements": {"schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}}}}
    context = BindingContext(run, episode, "scientific_process", path, scope, assignment, request)
    call, calls = selected_call
    call["context"], call["operation_key"] = context, run + ":" + episode + ":0"
    operand = registry._prepare_orf_sequence_operand(scope["subject_refs"][0], scope=scope)
    call["frozen_operand"] = operand
    call["arguments"] = dict(subject_ref=operand["subject"]["id"], min_length=0, search_reverse=True,
        filter_subsets=False, rows=[dict(row_id={"kind": "orf", "row_index": 0}, fields=[
            "native_row", "orf_source_path", "protein_source_path", "omitted_stop_source_path", "interval_length_nt"]),
            dict(row_id={"kind": "orf", "row_index": 1}, fields=["native_row"])])
    store.db.execute("INSERT INTO runtime_episodes VALUES(?,?,?,?)", (run, episode, canonical(path), canonical(request)))
    store.db.execute("INSERT INTO runtime_actions VALUES(?,?,?,?,NULL)", (run, episode, 0,
        canonical(dict(kind="tool", tool=ordinary.OPERATION, arguments=call["arguments"]))))
    directory = tmp_path / "execution-owner"; directory.mkdir()
    owner = SimpleNamespace(store=store, run_id=run, directory=directory, tool_registry=registry)
    owner._selected_result_action = MethodType(ExecutionEpisodes._selected_result_action, owner)
    host = results.MolecularSequenceResults(owner)
    receipts = EpisodeReceipts(store, run)
    receipts.bind(context.episode_id)
    store.db.commit()
    prepared = ordinary.prepare_ordinary_orf_attempt(**call)
    value = SimpleNamespace(store=store, registry=registry, host=host, owner=owner, context=context,
        call=call, prepared=prepared, calls=calls, operation_key=call["operation_key"], receipts=receipts)
    try:
        yield value
    finally:
        registry._publications.reset(publication_token)
        store.close()


def _roles(value):
    """Populate literal test cells and closed private adapter metadata only."""
    plan = value.prepared["plan"]
    bundle, declaration = _metadata_fixture(value.prepared)
    root = Path(plan["attempt_directory"])
    output = root / "driver-output"
    subject = value.call["arguments"]["subject_ref"]
    capture = dict(version="molecular_sequence_execution_v1", request=plan["selection"]["driver_request"]["selection"],
        request_canonical_sha256="0" * 64, stage="engineering_fixture", native_record=None,
        native_call_state="not_started", reference_data=None, execution_receipt=None, stdout="", stderr="",
        failure={"engineering_fixture": True})
    sheet = {"schema": "orf_measurement_sheet_v1", "engineering_fixture": True}
    components = {"schema": "orf_measurement_components_v1", "status": "partial", "native_outcome": "unknown",
        "summary": {"reported_row_count": 2, "usable_saved_row_count": 1, "retained_length_denominator_rows": 1},
        "rows": [{"row_index": 0, "native_row": ["ATGAAATAA", "MK", 0, 9, "+", 1],
            "orf_source_path": [{"subject_ref": subject, "start": 0, "end": 9, "unit": "nt", "strand": "+"}],
            "protein_source_path": [{"subject_ref": subject, "start": 0, "end": 6, "unit": "nt", "strand": "+"}],
            "omitted_stop_source_path": [{"subject_ref": subject, "start": 6, "end": 9, "unit": "nt", "strand": "+"}],
            "interval_length_nt": 9, "source_definition": "unknown", "translation": {"state": "unknown", "early_ambiguity_termination": None}},
            {"row_index": 1, "state": "incompatible", "saved_row": {"engineering_malformed_native_row": True}}]}
    documents = dict(capture=capture, sheet=sheet, components=components)
    def seal():
        for role, document in documents.items():
            path = output / (role + ".json"); _write(path, document)
            pin = _pin(path, path.read_bytes())
            declaration["files"][role] = dict(relative_path=role + ".json", format="json", state="present",
                sha256=pin["sha256"], size_bytes=pin["size_bytes"])
        _write(output / "declaration.json", declaration)
        for row in bundle["files"]:
            path = root / row["relative_path"]
            row["observed"] = _pin(path, path.read_bytes()) if path.exists() else None
            row["observed_state"] = "present" if path.exists() else "absent"
            row["declared"] = deepcopy(declaration["files"].get(row["role"]))
        _write(root / "attempt-bundle.json", bundle)
    seal()
    return SimpleNamespace(root=root, output=output, documents=documents, bundle=bundle, declaration=declaration, seal=seal)


def _execution(value, monkeypatch, *, code=0):
    _lifecycle(monkeypatch, value.prepared, views=("returned",), code=code)
    return ordinary.run_ordinary_orf_attempt(value.prepared)


def _capture(value, execution):
    async def run():
        async with value.host.locked_action(value.context, target=None, tool_name=ordinary.OPERATION,
                arguments=value.call["arguments"], operation_key=value.operation_key) as action:
            return value.host.capture_ordinary_orf(action, execution=execution)
    return asyncio.run(run())


def _publish(value, execution, *, pending=False):
    async def run():
        async with value.host.locked_action(value.context, target=None, tool_name=ordinary.OPERATION,
                arguments=value.call["arguments"], operation_key=value.operation_key) as action:
            custody = value.host.capture_ordinary_orf(action, execution=execution)
            with value.store.transaction():
                public, refs = value.host.publish_ordinary_orf(action, custody=custody)
                operation_ref = identity("operation", {"key": value.operation_key, "name": ordinary.OPERATION,
                    "arguments": value.call["arguments"]})
                outcome = dict(status="completed", operation_ref=operation_ref, record_refs=refs,
                    changed_record_refs=refs, result=public, feedback=None)
                value.registry._save(value.operation_key, ordinary.OPERATION, value.call["arguments"],
                    value.context.as_record()["scope"], outcome)
                if not pending:
                    value.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
                        (canonical({**outcome, "pending_work_after_action": {"engineering_fixture": True}}), value.context.run_id, value.context.episode_id))
            return custody, public, outcome
    return asyncio.run(run())


def test_real_owner_lock_retains_independent_roles_and_literal_structured_values(ordinary_owner, monkeypatch):
    value = ordinary_owner; roles = _roles(value)
    from gene_annotation_episode import molecular_sequence_driver
    monkeypatch.setattr(molecular_sequence_driver, "_calculate", lambda *a: pytest.fail("literal custody recalculated"))
    execution = _execution(value, monkeypatch)
    custody, public, outcome = _publish(value, execution)
    contracts.validate_ordinary_orf_custody(custody)
    assert all(custody["source_files"][role]["state"] == "retained" for role in ("capture", "sheet", "components"))
    assert public["selection"]["rows"] == value.call["arguments"]["rows"]
    rows = public["values"]["rows"]
    assert rows[0]["value"] == roles.documents["components"]["rows"][0]["native_row"]
    assert rows[1]["value"] == roles.documents["components"]["rows"][0]["orf_source_path"]
    assert rows[2]["unit"] == "per_segment_nt_or_symbol"
    assert rows[-1]["row_id"] == {"kind": "orf", "row_index": 1} and rows[-1]["value_state"] == "path_missing"
    assert public["values"]["original_attempt_association"] == "verified"
    assert outcome["record_refs"] == [public["source_ref"]]
    assert len(value.calls) == 1


@pytest.mark.parametrize("damage", ("invalid", "null_declaration", "wrong_path", "missing", "changed"))
def test_component_failure_keeps_valid_siblings_and_raw_declaration(ordinary_owner, monkeypatch, damage):
    value = ordinary_owner; roles = _roles(value)
    if damage == "invalid":
        roles.declaration["files"]["components"]["size_bytes"] = "engineering_invalid_size"
        _write(roles.output / "declaration.json", roles.declaration)
    elif damage == "null_declaration":
        roles.declaration["files"]["components"] = None
        _write(roles.output / "declaration.json", roles.declaration)
    elif damage == "wrong_path":
        roles.declaration["files"]["components"]["relative_path"] = "must-not-open.json"
        _write(roles.output / "declaration.json", roles.declaration)
    elif damage == "missing":
        (roles.output / "components.json").unlink()
    else:
        (roles.output / "components.json").write_bytes(b"changed engineering role bytes")
    if damage in ("invalid", "null_declaration", "wrong_path"):
        # This fixture represents original invalid native metadata, rather
        # than replacement of the declaration after the adapter observed it.
        observed = next(row for row in roles.bundle["files"] if row["role"] == "declaration")
        observed["observed"] = _pin(roles.output / "declaration.json", (roles.output / "declaration.json").read_bytes())
        _write(roles.root / "attempt-bundle.json", roles.bundle)
    expected_raw = (roles.output / "declaration.json").read_bytes()
    capture = results.capture_native_file
    def guarded(store, **kwargs):
        assert kwargs["relative_path"] != "must-not-open.json"
        return capture(store, **kwargs)
    monkeypatch.setattr(results, "capture_native_file", guarded)
    custody = _capture(value, _execution(value, monkeypatch))
    assert custody["source_files"]["capture"]["state"] == custody["source_files"]["sheet"]["state"] == "retained"
    assert custody["source_files"]["components"]["file"] is None
    assert retained_native_file(value.store, custody["original"]["declaration_file"]).read_bytes() == expected_raw
    assert all(row["value_state"] == "source_unavailable" for row in custody["projection"]["public"]["rows"])


@pytest.mark.parametrize("role", ("capture", "sheet"))
def test_missing_sibling_does_not_gate_component_rows(ordinary_owner, monkeypatch, role):
    value = ordinary_owner; roles = _roles(value)
    (roles.output / (role + ".json")).unlink()
    custody = _capture(value, _execution(value, monkeypatch))
    assert custody["source_files"][role]["file"] is None
    assert custody["source_files"]["components"]["state"] == "retained"
    assert custody["projection"]["public"]["rows"][0]["value"] == roles.documents["components"]["rows"][0]["native_row"]


def test_malformed_bundle_bytes_remain_private_without_discarding_roles(ordinary_owner, monkeypatch):
    value = ordinary_owner; roles = _roles(value)
    malformed = b"{engineered malformed bundle"
    (roles.root / "attempt-bundle.json").write_bytes(malformed)
    execution = _execution(value, monkeypatch)
    assert execution["bundle"] is None and execution["metadata_failures"]
    custody = _capture(value, execution)
    assert retained_native_file(value.store, custody["original"]["bundle_file"]).read_bytes() == malformed
    assert all(custody["source_files"][role]["state"] == "retained" for role in ("capture", "sheet", "components"))


@pytest.mark.parametrize("cell,expected", ((None, "stored_null"), ("wrong-type", "invalid_type"), (0, "stored_value"), ("missing", "path_missing")))
def test_literal_cell_states_preserve_null_invalid_zero_and_missing(ordinary_owner, monkeypatch, cell, expected):
    value = ordinary_owner; roles = _roles(value)
    row = roles.documents["components"]["rows"][0]
    if cell == "missing": del row["interval_length_nt"]
    else: row["interval_length_nt"] = cell
    roles.seal()
    custody = _capture(value, _execution(value, monkeypatch))
    stored = next(row for row in custody["projection"]["public"]["rows"] if row["field"] == "interval_length_nt")
    assert stored["value_state"] == expected
    assert stored["value"] == (0 if expected == "stored_value" else None)


def test_source_packet_and_report_schema_grant_only_source_and_keep_input_file_owner(ordinary_owner, monkeypatch):
    value = ordinary_owner; _roles(value)
    custody, public, outcome = _publish(value, _execution(value, monkeypatch))
    source = value.store.get(public["source_ref"])
    operand_file = value.call["frozen_operand"]["input_file"]["artifact_ref"]
    assert operand_file not in source["auxiliary_artifact_refs"]
    assert custody["request"]["input_binding_file"]["artifact_ref"] in source["auxiliary_artifact_refs"]
    assert source["artifact_ref"] == custody["public_packet_file"]["artifact_ref"]
    assert source["request_ref"] not in outcome["record_refs"]
    packet = json.loads(value.store.get_artifact(source["artifact_ref"]))
    assert "source_ref" not in packet and "frozen_operand" not in packet and "native_call_count" not in packet
    schema = contracts.ordinary_orf_fact_sources()[contracts.ORDINARY_ORF_FACT_SOURCE]["report_schema"]["items"]
    assert Draft202012Validator(schema).is_valid(public)
    semantic = []
    def visit(node):
        if type(node) is dict:
            if node.get("format") == "reference": semantic.append(node.get("x-reference-namespace"))
            for child in node.values(): visit(child)
        elif type(node) is list:
            for child in node: visit(child)
    visit(schema)
    assert semantic == ["source"]
    original = contracts.molecular_sequence_fact_sources()[contracts.PROJECTION_SOURCE]["report_schema"]
    semantic.clear(); visit(original)
    assert "artifact" in semantic  # Existing private-profile meanings remain intact.


@pytest.mark.parametrize("attack", ("float_argument", "different_argument", "wrong_key"))
def test_selected_action_is_type_sensitive_before_capture(ordinary_owner, monkeypatch, attack):
    value = ordinary_owner; _roles(value)
    execution = _execution(value, monkeypatch)
    if attack == "wrong_key":
        value.operation_key = value.context.run_id + ":" + value.context.episode_id + ":1"
    else:
        arguments = deepcopy(value.call["arguments"])
        arguments["min_length"] = 0.0 if attack == "float_argument" else 5
        value.store.db.execute("UPDATE runtime_actions SET action=?", (canonical(dict(kind="tool", tool=ordinary.OPERATION, arguments=arguments)),))
        value.store.db.commit()
    monkeypatch.setattr(value.host, "_ordinary_capture_path", lambda *a, **k: pytest.fail("unauthenticated native capture"))
    with pytest.raises(ValueError): _capture(value, execution)


def test_actual_writer_observation_is_required_even_for_self_consistent_carrier(ordinary_owner, monkeypatch):
    value = ordinary_owner; _roles(value)
    execution = _execution(value, monkeypatch)
    monkeypatch.setattr(ordinary.native, "status", lambda handle: dict(terminal=False, quiescent=False,
        state="running", metadata=execution["metadata"]))
    monkeypatch.setattr(value.host, "_ordinary_capture_path", lambda *a, **k: pytest.fail("live writer captured"))
    with pytest.raises(MolecularOperationUnpublished): _capture(value, execution)


@pytest.mark.parametrize("attack", ("selected_action", "operation_scope", "missing_operation"))
def test_publication_provenance_precedes_private_bytes(ordinary_owner, monkeypatch, attack):
    value = ordinary_owner; _roles(value)
    _custody, public, _outcome = _publish(value, _execution(value, monkeypatch))
    if attack == "selected_action":
        args = deepcopy(value.call["arguments"]); args["min_length"] = 0.0
        value.store.db.execute("UPDATE runtime_actions SET action=?", (canonical(dict(kind="tool", tool=ordinary.OPERATION, arguments=args)),))
    elif attack == "operation_scope":
        value.store.db.execute("UPDATE tool_operations SET scope='{}'")
    else:
        value.store.db.execute("DELETE FROM tool_operations")
    value.store.db.commit()
    from gene_annotation_episode import molecular_measurement_tools
    monkeypatch.setattr(molecular_measurement_tools, "_publication_bytes", lambda *a: pytest.fail("private bytes before provenance"))
    with pytest.raises(ValueError): value.host.read_ordinary_orf_publication(value.context, public["source_ref"])


def test_only_same_pending_own_action_can_recover_publication(ordinary_owner, monkeypatch):
    value = ordinary_owner; _roles(value)
    custody, public, _outcome = _publish(value, _execution(value, monkeypatch), pending=True)
    with pytest.raises(ValueError, match="completed_action_required"):
        value.host.read_ordinary_orf_publication(value.context, public["source_ref"])
    with pytest.raises(ValueError, match="completed_action_required"):
        value.host.read_ordinary_orf_publication(value.context, public["source_ref"], pending_operation_key=value.operation_key + "0")
    recovered = value.host.read_ordinary_orf_publication(value.context, public["source_ref"], pending_operation_key=value.operation_key)
    assert recovered["stored"] == public and recovered["control"] == custody


def test_closed_publication_replay_uses_retained_controls_without_historical_paths(ordinary_owner, monkeypatch):
    value = ordinary_owner; _roles(value)
    custody, public, _outcome = _publish(value, _execution(value, monkeypatch))
    shutil.rmtree(Path(value.prepared["handle_path"]).parent)
    monkeypatch.setattr(results, "capture_native_file", lambda *a, **k: pytest.fail("saved publication recaptured"))
    monkeypatch.setattr(ordinary.native, "status", lambda *a: pytest.fail("saved publication observed historical unit"))
    replay = value.host.read_ordinary_orf_publication(value.context, public["source_ref"])
    assert replay["stored"] == public and replay["control"] == custody
    assert replay["admission_kind"] == "source_only" and replay["grading_ref"] is None


def test_received_source_requires_actual_admission_before_private_bytes(ordinary_owner, monkeypatch):
    value = ordinary_owner; _roles(value)
    _custody, public, _outcome = _publish(value, _execution(value, monkeypatch))
    path = (("annotation", "engineering-receiver"),)
    episode = EpisodeRef(value.context.run_id, path).episode_id
    request = {"message": {"scope": value.context.as_record()["scope"], "episode_assignment": {}}}
    received = BindingContext(value.context.run_id, episode, "annotation", path, value.context.scope, {}, request)
    value.store.db.execute("INSERT INTO runtime_episodes VALUES(?,?,?,?)", (received.run_id, episode, canonical(path), canonical(request)))
    value.receipts.bind(episode)
    value.store.db.commit()
    from gene_annotation_episode import molecular_measurement_tools
    actual = molecular_measurement_tools._publication_bytes
    monkeypatch.setattr(molecular_measurement_tools, "_publication_bytes", lambda *a: pytest.fail("unreceived private publication"))
    with pytest.raises(ValueError, match="source_admission_required"):
        value.host.read_ordinary_orf_publication(received, public["source_ref"])
    with pytest.raises(ValueError, match="source_not_received"):
        value.host.read_ordinary_orf_publication(received, public["source_ref"], read_received=lambda *a, **k: {"failure": {"code": "not_received"}})
    # This explicit engineered Source-only initial receipt does not exercise
    # the provider stop-set wiring, which belongs to the enclosing integration.
    value.store.db.execute("INSERT INTO runtime_record_receipts(run_id,episode_id,record_ref,receipt_kind,source_index) VALUES(?,?,?,?,NULL)",
        (received.run_id, episode, public["source_ref"], "initial"))
    value.store.db.commit()
    assert set(value.receipts.known(episode)) == {public["source_ref"]}
    with pytest.raises(ValueError, match="source_not_received"):
        value.host.read_ordinary_orf_publication(received, public["source_ref"],
            read_received=lambda *a, **k: {"failure": {"code": "engineered_reader_denied"}})
    monkeypatch.setattr(molecular_measurement_tools, "_publication_bytes", actual)
    calls = []
    def reader(context, reference, namespace, **kwargs):
        calls.append((context.episode_id, reference, namespace, kwargs))
        return {"failure": None, "input": {"witness": {"record": value.store.get(reference)}}}
    admitted = value.host.read_ordinary_orf_publication(received, public["source_ref"], read_received=reader)
    assert admitted["stored"] == public
    assert calls == [(episode, public["source_ref"], "source", {"source_metadata_only": True})]


def test_sealed_custody_reuses_role_retention_without_duplicate_source_identity(ordinary_owner, monkeypatch):
    value = ordinary_owner; _roles(value)
    execution = _execution(value, monkeypatch)
    custody = _capture(value, execution)
    from gene_annotation_episode import molecular_sequence_driver
    monkeypatch.setattr(molecular_sequence_driver, "_calculate", lambda *a: pytest.fail("sealed custody recalculated"))
    monkeypatch.setattr(value.host, "_capture_files", lambda *a, **k: pytest.fail("sealed custody recaptured roles"))
    assert _capture(value, execution) == custody
    async def publish_twice():
        async with value.host.locked_action(value.context, target=None, tool_name=ordinary.OPERATION,
                arguments=value.call["arguments"], operation_key=value.operation_key) as action:
            first = value.host.publish_ordinary_orf(action, custody=custody)
            second = value.host.publish_ordinary_orf(action, custody=custody)
            return first, second
    first, second = asyncio.run(publish_twice())
    assert first == second and first[1] == [first[0]["source_ref"]]


@pytest.mark.parametrize("attack", ("native_row", "path_unit", "path_end", "field_unit", "selection", "file_state", "source"))
def test_public_schema_and_semantic_validator_reject_structured_corruption(ordinary_owner, monkeypatch, attack):
    value = ordinary_owner; _roles(value)
    _custody, public, _outcome = _publish(value, _execution(value, monkeypatch))
    public = deepcopy(public)
    rows = public["values"]["rows"]
    if attack == "native_row": rows[0]["value"].append("extra native field")
    elif attack == "path_unit": rows[1]["value"][0]["unit"] = "aa"
    elif attack == "path_end": rows[1]["value"][0]["end"] = 0
    elif attack == "field_unit": rows[1]["unit"] = "protein_coordinates"
    elif attack == "selection": public["selection"]["rows"][0]["fields"] = ["mean_retained_orf_length_nt"]
    elif attack == "file_state": public["file_states"]["components"] = "produced_unretained"
    else: public["source_ref"] = public["values"]["source_components_ref"]
    schema = contracts.ordinary_orf_fact_sources()[contracts.ORDINARY_ORF_FACT_SOURCE]["report_schema"]["items"]
    assert not Draft202012Validator(schema).is_valid(public)
    with pytest.raises(ValueError): contracts.validate_ordinary_orf_return(public)


def test_publication_requires_explicit_actual_registry_owner_port(ordinary_owner, monkeypatch):
    value = ordinary_owner; _roles(value)
    execution = _execution(value, monkeypatch)
    custody = _capture(value, execution)
    del value.owner.tool_registry
    async def publish():
        async with value.host.locked_action(value.context, target=None, tool_name=ordinary.OPERATION,
                arguments=value.call["arguments"], operation_key=value.operation_key) as action:
            return value.host.publish_ordinary_orf(action, custody=custody)
    with pytest.raises(ValueError, match="registry_port_required"): asyncio.run(publish())
    assert value.store.db.execute("SELECT count(*) FROM records WHERE record_type='source' AND json_extract(data,'$.provider')=?",
        (ordinary.OPERATION,)).fetchone()[0] == 0


def test_changed_original_sidecar_rejects_before_role_capture(ordinary_owner, monkeypatch):
    value = ordinary_owner; _roles(value)
    execution = _execution(value, monkeypatch)
    handle = json.loads(Path(value.prepared["handle_path"]).read_bytes())
    path = Path(handle["paths"]["request"])
    document = json.loads(path.read_bytes()); document["env"]["ENGINEERED_FOREIGN_OVERLAY"] = "changed"
    _write(path, document)
    handle["request_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    _write(value.prepared["handle_path"], handle)
    monkeypatch.setattr(value.host, "_ordinary_capture_path", lambda *a, **k: pytest.fail("changed sidecar captured outputs"))
    with pytest.raises(MolecularOperationUnpublished): _capture(value, execution)


@pytest.mark.parametrize("forgery", ("carrier_components", "carrier_bundle", "replaced_declaration"))
def test_raw_metadata_authenticates_carrier_before_sealing_and_original_attempt_recovers(ordinary_owner, monkeypatch, forgery):
    value = ordinary_owner; roles = _roles(value)
    original = _execution(value, monkeypatch)
    forged = deepcopy(original)
    component_path = roles.output / "components.json"
    original_component_bytes = component_path.read_bytes()
    original_declaration_bytes = (roles.output / "declaration.json").read_bytes()
    if forgery == "carrier_bundle":
        forged["bundle"]["software_verification"]["before"] = "conflict"
    else:
        replacement = deepcopy(roles.documents["components"])
        replacement["rows"][0]["interval_length_nt"] = 777
        _write(component_path, replacement)
        pin = _pin(component_path, component_path.read_bytes())
        for declared in (forged["declaration"]["files"]["components"], forged["declarations"]["components"]):
            declared["sha256"], declared["size_bytes"] = pin["sha256"], pin["size_bytes"]
        if forgery == "replaced_declaration":
            # Even a carrier matching replacement declaration B cannot erase
            # original bundle A's observed declaration identity.
            _write(roles.output / "declaration.json", forged["declaration"])
    contracts.validate_ordinary_orf_execution(forged)
    capture = value.host._capture_files
    monkeypatch.setattr(value.host, "_capture_files", lambda *a, **k: pytest.fail("forged metadata reached role capture"))
    with pytest.raises(MolecularOperationUnpublished, match="original_metadata_conflict"):
        _capture(value, forged)
    directory = value.host.action_directory(value.context.episode_id, value.operation_key)
    assert not (directory / "ordinary-execution.json").exists()
    assert not (directory / "ordinary-custody.json").exists()
    assert value.store.db.execute("SELECT count(*) FROM records WHERE record_type='source' AND json_extract(data,'$.provider')=?",
        (ordinary.OPERATION,)).fetchone()[0] == 0
    assert value.store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=0",
        (value.context.run_id, value.context.episode_id)).fetchone()[0] is None
    component_path.write_bytes(original_component_bytes)
    (roles.output / "declaration.json").write_bytes(original_declaration_bytes)
    monkeypatch.setattr(value.host, "_capture_files", capture)
    custody, public, _outcome = _publish(value, original)
    row = next(row for row in public["values"]["rows"] if row["field"] == "interval_length_nt")
    assert row["value"] == 9
    assert custody["source_files"]["components"]["declared"] == roles.declaration["files"]["components"]
    assert value.host._ordinary_value(custody["original"]["execution_file"]) == original
    assert len(value.calls) == 1  # Recovery reused the original native reservation.


@pytest.mark.parametrize("damage", ("malformed", "unavailable"))
def test_unverified_top_level_declaration_keeps_fixed_path_roles_explicitly_undeclared(ordinary_owner, monkeypatch, damage):
    value = ordinary_owner; roles = _roles(value)
    declaration_path = roles.output / "declaration.json"
    if damage == "malformed": declaration_path.write_bytes(b"{engineered malformed declaration")
    else: declaration_path.unlink()
    execution = _execution(value, monkeypatch)
    assert execution["declaration"] is None and execution["declarations"] == {}
    custody = _capture(value, execution)
    assert all(custody["source_files"][role]["state"] == "retained_undeclared"
        and custody["source_files"][role]["declared"] is None for role in ("capture", "sheet", "components"))
    if damage == "malformed":
        assert retained_native_file(value.store, custody["original"]["declaration_file"]).read_bytes() == declaration_path.read_bytes()
    else: assert custody["original"]["declaration_file"] is None
    public = contracts.ordinary_orf_packet(custody)
    assert "native_call_count" not in public and custody["failures"]


@pytest.mark.parametrize("declaration_state", ("malformed", "missing"))
def test_bundle_pin_rejects_changed_undeclared_role_and_saved_replay_keeps_qualified_state(ordinary_owner, monkeypatch, declaration_state):
    value = ordinary_owner; roles = _roles(value)
    path = roles.output / "declaration.json"
    if declaration_state == "malformed": path.write_bytes(b"{engineered malformed declaration")
    else: path.unlink()
    replacement = deepcopy(roles.documents["components"])
    replacement["rows"][0]["interval_length_nt"] = 777
    _write(roles.output / "components.json", replacement)
    replaced = _pin(roles.output / "components.json", (roles.output / "components.json").read_bytes())
    execution = _execution(value, monkeypatch)
    custody, public, _outcome = _publish(value, execution)
    state = custody["source_files"]["components"]
    assert state["state"] == "identity_conflict" and state["file"] is None and state["declared"] is None
    assert state["observed_identity"] == {key: replaced[key] for key in ("sha256", "size_bytes")}
    assert state["failure"]["source_ref"] == "artifact_" + replaced["sha256"]
    assert all(row["value_state"] == "source_unavailable" for row in public["values"]["rows"])
    assert custody["source_files"]["sheet"]["state"] == custody["source_files"]["capture"]["state"] == "retained_undeclared"
    source = value.store.get(public["source_ref"])
    assert state["failure"]["source_ref"] in source["auxiliary_artifact_refs"]
    metadata = value.store.get(state["failure"]["source_ref"])
    assert metadata["sha256"] == replaced["sha256"] and metadata["size"] == replaced["size_bytes"]
    # A self-consistent replacement projection cannot turn captured B into a
    # retained original role while the independent native bundle still pins A.
    forged = deepcopy(custody)
    directory = value.host.action_directory(value.context.episode_id, value.operation_key)
    forged["source_files"]["components"] = read_control(directory / "ordinary-role-capture" / "components.json")
    forged["projection"] = value.host._admit_projection(selector=custody["projection"]["selector"],
        sources=forged["source_files"], association=custody["projection"]["association"],
        calculation=custody["projection"]["calculation"])
    with pytest.raises(ValueError, match="bundle_role_identity_conflict"):
        value.host._validate_ordinary_orf_custody(forged, custody["intent"])
    shutil.rmtree(Path(value.prepared["handle_path"]).parent)
    replay = value.host.read_ordinary_orf_publication(value.context, public["source_ref"])
    assert replay["stored"] == public and replay["control"]["source_files"]["components"] == state


@pytest.mark.parametrize("observed_state,expected", (("present", "retained_undeclared"),
    ("absent", "identity_conflict"), ("unavailable", "retained_undeclared")))
def test_bundle_matching_pin_absence_and_unavailable_observation_are_distinct(ordinary_owner, monkeypatch, observed_state, expected):
    value = ordinary_owner; roles = _roles(value)
    (roles.output / "declaration.json").write_bytes(b"{engineered malformed declaration")
    row = next(row for row in roles.bundle["files"] if row["role"] == "components")
    row["observed_state"] = observed_state
    if observed_state != "present":
        row["observed"] = None; row["comparison"] = "unavailable"
    _write(roles.root / "attempt-bundle.json", roles.bundle)
    custody = _capture(value, _execution(value, monkeypatch))
    state = custody["source_files"]["components"]
    assert state["state"] == expected and state["declared"] is None
    assert (state["file"] is None) is (observed_state == "absent")
    assert custody["source_files"]["sheet"]["state"] == "retained_undeclared"
    if observed_state != "absent":
        assert next(row for row in custody["projection"]["public"]["rows"] if row["field"] == "interval_length_nt")["value"] == 9


@pytest.mark.parametrize("declaration_state", ("valid", "invalid", "wrong_path", "null"))
def test_private_auxiliary_index_includes_only_actually_captured_failed_output(ordinary_owner, monkeypatch, declaration_state):
    value = ordinary_owner; roles = _roles(value)
    replacement = deepcopy(roles.documents["components"]); replacement["rows"][0]["interval_length_nt"] = 888
    _write(roles.output / "components.json", replacement)
    replacement_ref = "artifact_" + hashlib.sha256((roles.output / "components.json").read_bytes()).hexdigest()
    if declaration_state != "valid":
        if declaration_state == "invalid": roles.declaration["files"]["components"]["size_bytes"] = None
        elif declaration_state == "wrong_path": roles.declaration["files"]["components"]["relative_path"] = "must-not-open.json"
        else: roles.declaration["files"]["components"] = None
        _write(roles.output / "declaration.json", roles.declaration)
        row = next(row for row in roles.bundle["files"] if row["role"] == "declaration")
        row["observed"] = _pin(roles.output / "declaration.json", (roles.output / "declaration.json").read_bytes())
        _write(roles.root / "attempt-bundle.json", roles.bundle)
    capture = results.capture_native_file
    def guarded(store, **kwargs):
        assert kwargs["relative_path"] != "must-not-open.json"
        return capture(store, **kwargs)
    monkeypatch.setattr(results, "capture_native_file", guarded)
    custody, public, _outcome = _publish(value, _execution(value, monkeypatch))
    state = custody["source_files"]["components"]
    source = value.store.get(public["source_ref"])
    assert state["file"] is None
    assert (replacement_ref in source["auxiliary_artifact_refs"]) is (declaration_state == "valid")
    if declaration_state != "valid":
        assert state["observed_identity"] is None and state["failure"]["source_ref"] is None


def test_captured_failure_hash_dedup_never_reclassifies_original_input_file(ordinary_owner, monkeypatch):
    value = ordinary_owner; roles = _roles(value)
    operand = value.call["frozen_operand"]
    (roles.output / "components.json").write_bytes(operand["sequence"].encode("ascii"))
    custody, public, _outcome = _publish(value, _execution(value, monkeypatch))
    state = custody["source_files"]["components"]
    assert state["state"] == "identity_conflict"
    assert state["failure"]["source_ref"] == operand["input_file"]["artifact_ref"]
    assert state["failure"]["source_ref"] in value.host._ordinary_failed_capture_refs(custody["source_files"])
    source = value.store.get(public["source_ref"])
    assert operand["input_file"]["artifact_ref"] not in source["auxiliary_artifact_refs"]


def _ordinary_fact_schema():
    from gene_annotation_episode.molecular_result_facts import molecular_fact_sources
    return {"type": "object", "properties": {"measurements": deepcopy(
        molecular_fact_sources()[contracts.ORDINARY_ORF_FACT_SOURCE]["report_schema"])},
        "required": ["measurements"], "additionalProperties": False}


def _ordinary_fact_tables(store):
    return {name: sorted((tuple(row) for row in store.db.execute(
        'SELECT * FROM "' + name.replace('"', '""') + '"')), key=repr)
        for name, in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}


def _ordinary_fact_forbidden(*args, **kwargs):
    raise AssertionError("frozen ORF facts must not reopen private data or calculate")


def _forbid_ordinary_frozen_work(value, monkeypatch):
    from gene_annotation_episode import molecular_measurement_tools, molecular_sequence_driver
    monkeypatch.setattr(value.store, "get_artifact", _ordinary_fact_forbidden)
    for name in ("read_ordinary_orf_publication", "_ordinary_value", "_admit_projection"):
        monkeypatch.setattr(value.host, name, _ordinary_fact_forbidden)
    monkeypatch.setattr(molecular_measurement_tools, "_publication_bytes", _ordinary_fact_forbidden)
    monkeypatch.setattr(molecular_sequence_driver, "_calculate", _ordinary_fact_forbidden)
    monkeypatch.setattr(ordinary, "run_ordinary_orf_attempt", _ordinary_fact_forbidden)
    monkeypatch.setattr(ordinary.native, "prepare_job", _ordinary_fact_forbidden)


def test_registered_orf_form_resolves_only_source_and_keeps_private_identity_strings_opaque(ordinary_owner, monkeypatch):
    """Actual shared form boundary over engineered publication metadata only."""
    from gene_annotation_episode.communication import validate_closed_schema, validate_form
    from gene_annotation_episode import molecular_result_facts as facts
    value = ordinary_owner; _roles(value)
    _custody, public, _outcome = _publish(value, _execution(value, monkeypatch))
    schema = _ordinary_fact_schema()
    assert schema["properties"]["measurements"] == contracts.ordinary_orf_fact_sources()[contracts.ORDINARY_ORF_FACT_SOURCE]["report_schema"]
    assert validate_closed_schema(schema) == schema
    assert facts.requested_molecular_fact_sources(schema) == (contracts.ORDINARY_ORF_FACT_SOURCE,)
    assert facts.requested_molecular_fact_fields(schema, fact_source=contracts.ORDINARY_ORF_FACT_SOURCE) == ["measurements"]
    assert public["values"]["source_components_ref"].startswith("artifact_")
    _forbid_ordinary_frozen_work(value, monkeypatch)
    calls = []
    def resolve(reference, namespace):
        calls.append((reference, namespace))
        return reference == public["source_ref"] and namespace == "source"
    before = _ordinary_fact_tables(value.store)
    assert validate_form({"measurements": [public]}, schema, resolve) == {"measurements": [public]}
    assert calls == [(public["source_ref"], "source")]
    assert _ordinary_fact_tables(value.store) == before


@pytest.mark.parametrize("damage", ("constraint", "source_type", "source_namespace", "nested"))
def test_registered_orf_schema_cannot_be_redefined_or_nested(damage):
    from gene_annotation_episode.communication import ReportBoundaryError, validate_form
    schema = _ordinary_fact_schema()
    if damage == "constraint": schema["properties"]["measurements"]["minItems"] = 1
    elif damage == "source_type": schema["properties"]["measurements"]["items"]["properties"]["source_ref"]["type"] = ["string", "null"]
    elif damage == "source_namespace": schema["properties"]["measurements"]["items"]["properties"]["source_ref"]["x-reference-namespace"] = "artifact"
    else:
        schema = {"type": "object", "properties": {"nested": schema}, "required": ["nested"], "additionalProperties": False}
    with pytest.raises(ReportBoundaryError) as error:
        validate_form({}, schema, _ordinary_fact_forbidden)
    assert error.value.diagnostic["code"] == "invalid_schema"


@pytest.mark.parametrize("cell,expected", ((0, "stored_value"), (None, "stored_null")))
def test_registered_orf_form_preserves_observed_zero_and_stored_null(ordinary_owner, monkeypatch, cell, expected):
    from gene_annotation_episode.communication import validate_form
    value = ordinary_owner; roles = _roles(value)
    roles.documents["components"]["rows"][0]["interval_length_nt"] = cell
    roles.seal()
    _custody, public, _outcome = _publish(value, _execution(value, monkeypatch))
    row = next(row for row in public["values"]["rows"] if row["field"] == "interval_length_nt")
    assert row["value"] == cell and row["value_state"] == expected
    assert public["values"]["rows"][1]["value"][0]["start"] == 0
    _forbid_ordinary_frozen_work(value, monkeypatch)
    assert validate_form({"measurements": [public]}, _ordinary_fact_schema(),
        lambda reference, namespace: (reference, namespace) == (public["source_ref"], "source")) == {"measurements": [public]}


@pytest.mark.parametrize("damage", ("bool_ordinal", "float_ordinal", "native_bool", "native_width", "path_float", "path_unit", "field_unit"))
def test_registered_orf_strict_cells_reject_before_any_reference_resolution(ordinary_owner, monkeypatch, damage):
    from gene_annotation_episode.communication import ReportBoundaryError, validate_form
    value = ordinary_owner; _roles(value)
    _custody, public, _outcome = _publish(value, _execution(value, monkeypatch))
    changed = deepcopy(public); rows = changed["values"]["rows"]
    if damage == "bool_ordinal": rows[0]["row_id"]["row_index"] = False
    elif damage == "float_ordinal": rows[0]["row_id"]["row_index"] = 0.0
    elif damage == "native_bool": rows[0]["value"][5] = True
    elif damage == "native_width": rows[0]["value"].append("not an original native tuple field")
    elif damage == "path_float": rows[1]["value"][0]["start"] = 0.0
    elif damage == "path_unit": rows[1]["value"][0]["unit"] = "aa"
    else: rows[1]["unit"] = "wrong_unit"
    _forbid_ordinary_frozen_work(value, monkeypatch)
    with pytest.raises(ReportBoundaryError):
        validate_form({"measurements": [changed]}, _ordinary_fact_schema(), _ordinary_fact_forbidden)


def test_registered_orf_form_denies_well_shaped_but_ungranted_source(ordinary_owner, monkeypatch):
    from gene_annotation_episode.communication import ReportBoundaryError, validate_form
    value = ordinary_owner; _roles(value)
    _custody, public, _outcome = _publish(value, _execution(value, monkeypatch))
    changed = deepcopy(public); changed["source_ref"] = "source_" + "f" * 24
    contracts.validate_ordinary_orf_return(changed)
    _forbid_ordinary_frozen_work(value, monkeypatch)
    seen = []
    def denied(reference, namespace):
        seen.append((reference, namespace)); return False
    with pytest.raises(ReportBoundaryError) as error:
        validate_form({"measurements": [changed]}, _ordinary_fact_schema(), denied)
    assert error.value.diagnostic["code"] == "unknown_reference"
    assert seen == [(changed["source_ref"], "source")]


def test_orf_merge_identity_includes_literal_selection_without_authenticating_a_second_publication(ordinary_owner, monkeypatch):
    """Pure DTO merge controls; the alternate view is not a new owned Source."""
    from gene_annotation_episode import molecular_result_facts as facts
    value = ordinary_owner; _roles(value)
    _custody, public, _outcome = _publish(value, _execution(value, monkeypatch))
    alternate = deepcopy(public)
    alternate["selection"]["rows"] = [{"row_id": {"kind": "orf", "row_index": 0}, "fields": ["native_row"]}]
    alternate["values"]["rows"] = [deepcopy(public["values"]["rows"][0])]
    alternate["values"]["failures"] = []; alternate["failures"] = []
    contracts.validate_ordinary_orf_return(alternate)
    _forbid_ordinary_frozen_work(value, monkeypatch)
    assert facts.merge_molecular_facts([public], [deepcopy(public), alternate], [deepcopy(alternate)],
        fact_source=contracts.ORDINARY_ORF_FACT_SOURCE) == [public, alternate]
    conflicting = deepcopy(public)
    next(row for row in conflicting["values"]["rows"] if row["field"] == "interval_length_nt")["value"] = 8
    contracts.validate_ordinary_orf_return(conflicting)
    with pytest.raises(ValueError, match="ordinary_orf_facts_source_conflict"):
        facts.merge_molecular_facts([public], [conflicting], fact_source=contracts.ORDINARY_ORF_FACT_SOURCE)


@pytest.mark.parametrize("input_identity_conflict", (False, True))
def test_real_orf_source_receipt_stops_private_dependencies_and_preserves_given_input_file(ordinary_owner, monkeypatch, input_identity_conflict):
    from gene_annotation_episode.molecular_reference_privacy import molecular_reference_restriction
    value = ordinary_owner; roles = _roles(value)
    input_ref = value.call["frozen_operand"]["input_file"]["artifact_ref"]
    if input_identity_conflict:
        (roles.output / "components.json").write_bytes(value.call["frozen_operand"]["sequence"].encode("ascii"))
    custody, public, _outcome = _publish(value, _execution(value, monkeypatch))
    source = value.store.get(public["source_ref"])
    value.receipts.receive(value.context.episode_id, [input_ref], kind="initial")
    assert set(value.receipts.known(value.context.episode_id)) == {input_ref}
    _forbid_ordinary_frozen_work(value, monkeypatch)
    value.receipts.receive(value.context.episode_id, [source["id"]], kind="own_action", source_index=0)
    assert set(value.receipts.known(value.context.episode_id)) == {input_ref, source["id"]}
    before = _ordinary_fact_tables(value.store)
    assert molecular_reference_restriction(value.store, value.context, source["id"], "source") is True
    assert molecular_reference_restriction(value.store, value.context, source["artifact_ref"], "artifact") is False
    for reference in {source["request_ref"], *source["auxiliary_artifact_refs"]}:
        assert molecular_reference_restriction(value.store, value.context, reference, "artifact") is False
        assert molecular_reference_restriction(value.store, None, reference, "artifact", private_only=True) is False
    assert input_ref not in source["auxiliary_artifact_refs"]
    assert molecular_reference_restriction(value.store, value.context, input_ref, "artifact") is None
    if input_identity_conflict:
        assert custody["source_files"]["components"]["failure"]["source_ref"] == input_ref
    assert _ordinary_fact_tables(value.store) == before


def test_generic_own_orf_facts_use_same_owner_and_original_action_publication(ordinary_owner, monkeypatch):
    """Getter is an explicit engineering seam; real assembly is tested elsewhere."""
    from gene_annotation_episode import molecular_result_facts as facts, molecular_measurement_tools
    value = ordinary_owner; _roles(value)
    _custody, public, _outcome = _publish(value, _execution(value, monkeypatch))
    seen = []
    def same_owner(run_id):
        seen.append(run_id); assert run_id == value.context.run_id; return value.host
    monkeypatch.setattr(value.registry, "molecular_sequence_results_for", same_owner)
    monkeypatch.setattr(molecular_measurement_tools, "read_retained_molecular_publication", _ordinary_fact_forbidden)
    monkeypatch.setattr(ordinary, "run_ordinary_orf_attempt", _ordinary_fact_forbidden)
    before = _ordinary_fact_tables(value.store)
    actual = facts.own_molecular_facts(value.registry, value.context, read_received=None,
        fact_source=contracts.ORDINARY_ORF_FACT_SOURCE)
    assert actual == [public] and seen == [value.context.run_id]
    assert _ordinary_fact_tables(value.store) == before


@pytest.mark.parametrize("damage", ("selected_arguments", "operation_arguments", "scope", "outcome", "missing_operation"))
def test_generic_own_orf_facts_reject_action_operation_conflicts_before_private_reads(ordinary_owner, monkeypatch, damage):
    from gene_annotation_episode import molecular_result_facts as facts
    value = ordinary_owner; _roles(value)
    _custody, _public, outcome = _publish(value, _execution(value, monkeypatch))
    if damage in ("selected_arguments", "operation_arguments"):
        arguments = deepcopy(value.call["arguments"]); arguments["min_length"] = 0.0
        if damage == "selected_arguments":
            value.store.db.execute("UPDATE runtime_actions SET action=?", (canonical(dict(kind="tool", tool=ordinary.OPERATION, arguments=arguments)),))
        else: value.store.db.execute("UPDATE tool_operations SET arguments=?", (canonical(arguments),))
    elif damage == "scope": value.store.db.execute("UPDATE tool_operations SET scope='{}'")
    elif damage == "outcome":
        changed = deepcopy(outcome); changed["feedback"] = {"engineering_conflict": True}
        value.store.db.execute("UPDATE tool_operations SET result=?", (canonical(changed),))
    else: value.store.db.execute("DELETE FROM tool_operations")
    value.store.db.commit()
    _forbid_ordinary_frozen_work(value, monkeypatch)
    monkeypatch.setattr(value.registry, "molecular_sequence_results_for", _ordinary_fact_forbidden)
    before = _ordinary_fact_tables(value.store)
    with pytest.raises(ValueError, match="ordinary_orf_action_conflict"):
        facts.own_molecular_facts(value.registry, value.context, read_received=None,
            fact_source=contracts.ORDINARY_ORF_FACT_SOURCE)
    assert _ordinary_fact_tables(value.store) == before


@pytest.mark.parametrize("state", ("absent", "empty", "values", "malformed"))
def test_frozen_orf_fact_rows_and_forms_need_no_private_bytes_or_calculation(ordinary_owner, monkeypatch, state):
    """Engineered own frozen-row control, not a child return or Workflow closure."""
    from gene_annotation_episode import molecular_result_facts as facts
    from gene_annotation_episode.communication import ReportBoundaryError, form_with_facts, validate_form
    value = ordinary_owner; _roles(value)
    _custody, public, _outcome = _publish(value, _execution(value, monkeypatch))
    source = contracts.ORDINARY_ORF_FACT_SOURCE
    value.store.db.execute("CREATE TABLE runtime_forms(run_id TEXT,episode_id TEXT,facts TEXT,form TEXT,PRIMARY KEY(run_id,episode_id))")
    group = [] if state == "empty" else None if state == "malformed" else [public]
    if state != "absent":
        value.store.db.execute("INSERT INTO runtime_forms VALUES(?,?,?,?)", (value.context.run_id,
            value.context.episode_id, canonical({source: group}), canonical({"measurements": group})))
    value.store.db.commit()
    _forbid_ordinary_frozen_work(value, monkeypatch)
    before = _ordinary_fact_tables(value.store)
    if state == "malformed":
        with pytest.raises(ValueError, match="ordinary_orf_frozen_source_invalid"):
            facts.frozen_molecular_facts(value.store, value.context.run_id, value.context, fact_source=source)
    else:
        frozen = facts.frozen_molecular_facts(value.store, value.context.run_id, value.context, fact_source=source)
        assert frozen == (None if state == "absent" else group)
        if state in ("empty", "values"):
            form = form_with_facts({}, _ordinary_fact_schema(), {source: frozen})
            assert validate_form(form, _ordinary_fact_schema(),
                lambda reference, namespace: (reference, namespace) == (public["source_ref"], "source")) == form
            facts.validate_frozen_molecular_return(form, _ordinary_fact_schema(), frozen, fact_source=source)
        if state == "values":
            changed = deepcopy(form)
            next(row for row in changed["measurements"][0]["values"]["rows"] if row["field"] == "interval_length_nt")["value"] = 8
            contracts.validate_ordinary_orf_return(changed["measurements"][0])
            with pytest.raises(ReportBoundaryError) as error:
                facts.validate_frozen_molecular_return(changed, _ordinary_fact_schema(), frozen, fact_source=source)
            assert error.value.diagnostic["code"] == "ordinary_orf_frozen_source_mismatch"
            frozen.clear()
            assert facts.frozen_molecular_facts(value.store, value.context.run_id, value.context, fact_source=source) == [public]
    assert _ordinary_fact_tables(value.store) == before


def test_ordinary_orf_fact_source_reaches_actual_runtime_form_compilation():
    from gene_annotation_episode.molecular_result_facts import molecular_fact_sources
    from gene_annotation_episode.runtime import _compile_form
    sources = molecular_fact_sources()
    source = contracts.ORDINARY_ORF_FACT_SOURCE
    assert sources[source]["type"] == "array"
    schema = _ordinary_fact_schema()
    assert _compile_form(canonical(schema), sources, include_runtime_sources=False) == schema
    wrong_type = deepcopy(sources)
    wrong_type[source]["type"] = "number"
    with pytest.raises(ValueError, match="different declared value type"):
        _compile_form(canonical(schema), wrong_type, include_runtime_sources=False)


def test_native_custody_cannot_claim_saved_calculation_kind(ordinary_owner, monkeypatch):
    value = ordinary_owner
    _roles(value)
    custody = _capture(value, _execution(value, monkeypatch))
    altered = deepcopy(custody)
    altered["projection"]["public"]["source_kind"] = "selected_saved_calculation"
    with pytest.raises(ValueError): contracts.validate_ordinary_orf_custody(altered)
