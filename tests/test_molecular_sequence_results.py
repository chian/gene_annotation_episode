"""Controlled private Store/EPR joins; no scientific producer authentication.

These tests construct explicit runtime records to exercise the existing ports.
They do not claim a production commission, native call, public registration or
independent original scientific binding. Rich numeric admission stays absent.
"""
import asyncio
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from method_loop.identities import EpisodeRef
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.communication import validate_closed_schema
from gene_annotation_episode.state import Store
from gene_annotation_episode import molecular_sequence_results as results
from gene_annotation_episode import molecular_sequence_result_contracts as contracts
from gene_annotation_episode import molecular_sequence_result_worker as worker
from gene_annotation_episode.native_file_capture import NativeFileCaptureError, retained_native_file
from gene_annotation_episode.genomic_overlap_result_receipts import immutable, read_control
from gene_annotation_episode.execution_progress import ExecutionTargetReader
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode import practical_execution_records as practical
from gene_annotation_episode import molecular_sequence_execution_contracts as execution
from tests.test_molecular_sequence_result_contracts import engineered, selector, POLICY


def file_form():
    """Ordinary allowed grammar; this is only a private retained-file return."""
    def code(values, nullable=False):
        return {"type": ["string", "null"] if nullable else "string", "enum": [*values, *([None] if nullable else [])]}
    reference = {"type": "string", "format": "reference", "x-reference-namespace": "artifact"}
    item = {"type": "object", "additionalProperties": False, "properties": {
        "operation": code(contracts.OPERATIONS), "role": code(contracts.FILE_ROLES), "artifact_ref": reference,
        "source_kind": code(("original_stored", "selected_saved_calculation")),
        "source_sheet_ref": {**reference, "type": ["string", "null"]},
        "components_schema": code(tuple(dict.fromkeys(schema for values in contracts.SCHEMAS.values() for schema in values[1])), True)}}
    item["required"] = list(item["properties"])
    return {"type": "object", "additionalProperties": False, "properties": {
        "files": {"type": "array", "items": item, "x-source": contracts.SAVED_SOURCE}}, "required": ["files"]}


def controlled_owner(tmp_path, *, selected=None, parent_initial=(), supplied_sheet_bytes=None, deliver_before=True):
    store = Store(tmp_path / "state"); store.create_problem(raw_sequence="ACGTACGT", molecule="dna")
    scope = store.validate_scope(); run = "controlled-molecular-result-owner"
    for sql in (
        "CREATE TABLE runtime_episodes(run_id TEXT,episode_id TEXT,path TEXT,request TEXT,PRIMARY KEY(run_id,episode_id))",
        "CREATE TABLE runtime_actions(run_id TEXT,episode_id TEXT,decision_index INTEGER,action TEXT,result TEXT,PRIMARY KEY(run_id,episode_id,decision_index))",
        "CREATE TABLE runtime_model_calls(run_id TEXT,episode_id TEXT,call_index INTEGER,request TEXT,response TEXT,purpose TEXT)",
        "CREATE TABLE runtime_forms(run_id TEXT,episode_id TEXT,facts TEXT,form TEXT,PRIMARY KEY(run_id,episode_id))",
        "CREATE TABLE runtime_report_attempts(run_id TEXT,parent_episode_id TEXT,decision_index INTEGER,delivery_ref TEXT,child_episode_id TEXT,contract TEXT,form TEXT,failure TEXT,report_contract_declaration TEXT)",
    ): store.db.execute(sql)
    directory = tmp_path / "controlled-run"; directory.mkdir()
    owner = SimpleNamespace(store=store, run_id=run, directory=directory)
    def selected_action(episode_id, operation_key, tool_name, arguments):
        prefix = run + ":" + episode_id + ":"; assert operation_key.startswith(prefix)
        row = store.db.execute("SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?", (run, episode_id, int(operation_key[len(prefix):]))).fetchone()
        assert row is not None
        assert json.loads(row["action"]) == {"kind": "tool", "tool": tool_name, "arguments": arguments}
        return row
    owner._selected_result_action = selected_action
    host = results.MolecularSequenceResults(owner)
    receipts = EpisodeReceipts(store, run)
    supplied_ref = None
    if supplied_sheet_bytes is not None:
        supplied_ref = store.artifact(supplied_sheet_bytes, "application/json")
        selected = selector(contracts.OPERATIONS[0], mode=contracts.MODES[1], saved=supplied_ref, files=("sheet",))
        if deliver_before: parent_initial = (*parent_initial, supplied_ref)
    root_path = (("annotation", "root"),); child_path = (*root_path, ("results", "child_0"))
    root_id, child_id = EpisodeRef(run, root_path).episode_id, EpisodeRef(run, child_path).episode_id
    root_manifest = receipts.bind(root_id)
    for reference in parent_initial: receipts.receive(root_id, [reference], kind="initial")
    selected = selector(contracts.OPERATIONS[0], files=("sheet",)) if selected is None else selected
    assignment = {"version": "execution_results_assignment_v1", "handoff_ref": "controlled-handoff-unverified", "selector": selected}
    form_schema = file_form(); purpose = "Return the explicitly selected controlled retained files."
    contract = host._report_contract(purpose, form_schema)
    root_request = {"goal": {"controlled_fixture": True}, "message": {"scope": scope, "episode_assignment": {}, "knowledge_inheritance": root_manifest}, "report_contract": contract}
    root = BindingContext(run, root_id, "annotation", root_path, scope, {}, root_request)
    store.db.execute("INSERT INTO runtime_episodes VALUES(?,?,?,?)", (run, root_id, canonical(root_path), canonical(root_request)))
    commission = {"kind": "episode_child", "role": "results", "scope": scope, "assignment": assignment,
        "purpose": purpose, "schema_json": canonical(form_schema), "goal": "Controlled private custody test", "initial_report_json": "{}"}
    store.db.execute("INSERT INTO runtime_actions VALUES(?,?,?,?,NULL)", (run, root_id, 0, canonical(commission)))
    child_manifest = receipts.bind(child_id, root_id)
    child_request = {"goal": {"controlled_fixture": True}, "message": {"scope": scope, "episode_assignment": assignment,
        "initial_report": {}, "knowledge_inheritance": child_manifest}, "report_contract": contract}
    child = BindingContext(run, child_id, "results", child_path, scope, assignment, child_request)
    store.db.execute("INSERT INTO runtime_episodes VALUES(?,?,?,?)", (run, child_id, canonical(child_path), canonical(child_request)))
    action = {"kind": "tool", "tool": "execution.results.collect", "arguments": {}}
    store.db.execute("INSERT INTO runtime_actions VALUES(?,?,?,?,NULL)", (run, child_id, 0, canonical(action)))
    target = dict(version="execution_target_v1", handle=assignment["handoff_ref"], run_id=run, resource_id="controlled-local", resource_kind="local",
        execution_id=str(directory / "controlled-native.json"), request_sha256="0"*64, origin_episode_id=root_id,
        assignment={}, scope=scope)
    return SimpleNamespace(store=store, host=host, owner=owner, parent=root, child=child, target=target,
        receipts=receipts, schema=form_schema, contract=contract, supplied_ref=supplied_ref, operation_key=run + ":" + child_id + ":0")


@pytest.fixture
def custody(tmp_path):
    value = controlled_owner(tmp_path)
    try: yield value
    finally: value.store.close()


def producers(tmp_path):
    directory = tmp_path / "supplied-engineering-files"; directory.mkdir()
    _sheet, _components, _sources, paths = engineered(directory)
    declarations = {}
    for role, path in paths.items():
        raw = path.read_bytes(); declarations[role] = dict(relative_path=path.name, format="json", state="present", sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
    return directory, declarations


def test_capture_storage_failure_is_independent_and_success_replay_needs_no_producer(custody, tmp_path, monkeypatch):
    directory, declarations = producers(tmp_path)
    capture_directory = tmp_path / "capture"
    actual = results.capture_native_file
    def fail_component(store, **kwargs):
        if kwargs["relative_path"] == "components.json": raise NativeFileCaptureError("retained_artifact_unavailable")
        return actual(store, **kwargs)
    monkeypatch.setattr(results, "capture_native_file", fail_component)
    sources = custody.host._capture_files(directory=directory, declarations=declarations, capture_directory=capture_directory, roles=("sheet", "components"))
    assert sources["sheet"]["state"] == "retained"
    assert retained_native_file(custody.store, sources["sheet"]["file"]).read_bytes() == (directory / "sheet.json").read_bytes()
    assert sources["components"]["state"] == "retention_failed" and sources["components"]["declared"]["state"] == "present"
    assert read_control(capture_directory / "sheet.json") == sources["sheet"]
    (directory / "sheet.json").unlink()
    monkeypatch.setattr(results, "capture_native_file", lambda *args, **kwargs: pytest.fail("success replay reopened producer"))
    assert custody.host._capture_files(directory=directory, declarations=declarations, capture_directory=capture_directory, roles=("sheet",))["sheet"] == sources["sheet"]


def test_declared_absence_never_opens_and_changed_failed_sibling_is_conflict(custody, tmp_path, monkeypatch):
    directory, declarations = producers(tmp_path)
    absent = dict(relative_path="components.json", format="json", state="absent", sha256=None, size_bytes=None)
    actual = results.capture_native_file
    monkeypatch.setattr(results, "capture_native_file", lambda *args, **kwargs: pytest.fail("declared absence opened producer"))
    value = custody.host._capture_files(directory=directory, declarations={"components": absent}, capture_directory=tmp_path / "absent", roles=("components",))
    assert value["components"]["state"] == "producer_absent"
    monkeypatch.setattr(results, "capture_native_file", actual)
    (directory / "components.json").write_bytes(b'{"changed":true}')
    value = custody.host._capture_files(directory=directory, declarations=declarations, capture_directory=tmp_path / "changed", roles=("components",))
    assert value["components"]["state"] == "identity_conflict" and value["components"]["observed_identity"] is not None


def test_malformed_sibling_declaration_preserves_committed_sheet_and_private_evidence(custody, tmp_path, monkeypatch):
    directory, declarations = producers(tmp_path)
    declarations["components"]["size_bytes"] = "malformed-native-size"
    selected = deepcopy(declarations["components"])
    actual = results.capture_native_file
    def capture_only_valid(store, **kwargs):
        assert kwargs["relative_path"] != "components.json", "malformed declaration was used to open a producer"
        return actual(store, **kwargs)
    monkeypatch.setattr(results, "capture_native_file", capture_only_valid)
    root = tmp_path / "malformed-capture"
    sources = custody.host._capture_files(directory=directory, declarations=declarations, capture_directory=root, roles=("sheet", "components"))
    assert sources["sheet"]["state"] == "retained"
    assert retained_native_file(custody.store, sources["sheet"]["file"]).read_bytes() == (directory / "sheet.json").read_bytes()
    assert sources["components"]["state"] == "unavailable" and sources["components"]["declared"] is None
    assert sources["components"]["failure"]["code"] == "schema_invalid"
    contracts.validate_file_state(sources["components"])
    evidence = read_control(root / ("invalid-components-" + digest(selected) + ".json"))
    assert evidence["declaration"] == selected
    assert read_control(root / "sheet.json") == sources["sheet"]


def test_components_survive_sheet_retention_failure_with_no_calculator(custody, tmp_path, monkeypatch):
    directory, declarations = producers(tmp_path)
    actual = results.capture_native_file
    def fail_sheet(store, **kwargs):
        if kwargs["relative_path"] == "sheet.json": raise NativeFileCaptureError("retained_artifact_unavailable")
        return actual(store, **kwargs)
    monkeypatch.setattr(results, "capture_native_file", fail_sheet)
    sources = custody.host._capture_files(directory=directory, declarations=declarations, capture_directory=tmp_path / "partial")
    from gene_annotation_episode import molecular_sequence_driver, molecular_sequence_native
    monkeypatch.setattr(molecular_sequence_driver, "_calculate", lambda *args: pytest.fail("partial capture recalculated"))
    monkeypatch.setattr(molecular_sequence_native, "execute_molecular_sequence_request", lambda *args: pytest.fail("partial capture invoked source"))
    value = custody.host._admit_projection(selector=selector(contracts.OPERATIONS[0]), sources=sources,
        association={"state": "unavailable", "reason": "scientific_binding_unavailable", "proof_file": None, "original_identity": None}, calculation={"kind": "original_stored"})
    assert value["public"]["source_sheet_ref"] is None and value["public"]["source_states"]["sheet"] == "retention_failed"
    assert value["public"]["rows"][0]["value"] == 12


def engineering_ports(custody, tmp_path, monkeypatch):
    directory, declarations = producers(tmp_path)
    capture_directory = tmp_path / "shared-original-capture"
    calls = []
    def original(action):
        calls.append("capture_existing_supplied_files")
        sources = custody.host._capture_files(directory=directory, declarations=declarations, capture_directory=capture_directory)
        return sources, {"state": "unavailable", "reason": "scientific_binding_unavailable", "proof_file": None, "original_identity": None}, None
    async def inline(action, plan):
        # The enclosing approved verification handle executes this finite pure
        # worker. This explicit engineering port claims no worker deployment.
        path = action.directory / "worker-plan.json"; immutable(path, plan)
        raw = path.read_bytes()
        result = worker.run_molecular_sequence_result_worker(plan_file={"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}, output_directory=plan["directory"])
        return result, None
    monkeypatch.setattr(custody.host, "_original", original)
    monkeypatch.setattr(custody.host, "_worker", inline)
    return directory, capture_directory, calls


def collect_controlled(custody):
    return asyncio.run(custody.host.execute(custody.child, custody.target, "execution.results.collect", {}, custody.operation_key))


def finish_controlled_action(custody, outcome):
    custody.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
        (canonical(outcome), custody.owner.run_id, custody.child.episode_id))


def test_publication_failure_preserves_private_bytes_without_typed_delivery_then_recovers_same_capture(custody, tmp_path, monkeypatch):
    directory, capture_directory, _calls = engineering_ports(custody, tmp_path, monkeypatch)
    actual = results.immutable
    def fail_publication(path, value):
        if Path(path).name == "receipt.json": raise OSError("controlled_publication_failure")
        return actual(path, value)
    monkeypatch.setattr(results, "immutable", fail_publication)
    with pytest.raises(OSError, match="controlled_publication_failure"): collect_controlled(custody)
    retained = read_control(capture_directory / "sheet.json")["file"]
    assert retained_native_file(custody.store, retained).is_file()
    assert custody.store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=?", (custody.owner.run_id, custody.child.episode_id)).fetchone()[0] is None
    assert custody.store.db.execute("SELECT count(*) FROM runtime_forms").fetchone()[0] == 0
    assert retained["artifact_ref"] not in set(custody.receipts.known(custody.parent.episode_id))
    assert not custody.host.resolve_received(custody.parent, retained["artifact_ref"], "artifact")
    monkeypatch.setattr(results, "immutable", actual)
    for name in ("sheet.json", "components.json"): (directory / name).unlink()
    from gene_annotation_episode import molecular_sequence_driver
    monkeypatch.setattr(molecular_sequence_driver, "_calculate", lambda *args: pytest.fail("publication recovery recalculated"))
    outcome = collect_controlled(custody); finish_controlled_action(custody, outcome)
    assert outcome["result"]["delivery_complete"] is True
    assert [row["artifact_ref"] for row in outcome["result"]["facts"][contracts.SAVED_SOURCE]] == [retained["artifact_ref"]]
    assert custody.host.credit_view(custody.child, {})["new_acquired_record_count"] == 0
    assert "scientific_credit" not in custody.host.credit_view(custody.child, {})["operational_credit_binding"]
    assert retained["artifact_ref"] not in set(custody.receipts.known(custody.parent.episode_id))


def test_actual_controlled_file_form_return_grants_only_selected_file_and_replays_without_source(custody, tmp_path, monkeypatch):
    directory, _capture_directory, _calls = engineering_ports(custody, tmp_path, monkeypatch)
    outcome = collect_controlled(custody); finish_controlled_action(custody, outcome)
    groups = custody.host.own_fact_groups(custody.child, verify_artifacts=True)
    form = {"files": groups[contracts.SAVED_SOURCE]}
    custody.store.db.execute("INSERT INTO runtime_forms VALUES(?,?,?,?)", (custody.owner.run_id, custody.child.episode_id, canonical(groups), canonical(form)))
    assert not custody.host.resolve_received(custody.parent, form["files"][0]["artifact_ref"], "artifact")
    custody.store.db.execute("INSERT INTO runtime_report_attempts VALUES(?,?,?,?,?,?,?,?,NULL)",
        (custody.owner.run_id, custody.parent.episode_id, 0, "controlled-delivery", custody.child.episode_id, canonical(custody.contract), canonical(form), None))
    refs = custody.host.record_admission(custody.parent, form, custody.schema, custody.owner.run_id + ":" + custody.parent.episode_id + ":0:typed_form")
    assert refs == [form["files"][0]["artifact_ref"]]
    assert form["files"][0]["role"] == "sheet"
    custody.receipts.receive(custody.parent.episode_id, refs, kind="child_form", source_index=0)
    assert refs[0] in set(custody.receipts.known(custody.parent.episode_id))
    assert custody.host.resolve_received(custody.parent, refs[0], "artifact")
    # Original source files and stored scientific bytes are not re-opened when
    # authenticating this already frozen typed file return.
    for path in directory.iterdir(): path.unlink()
    monkeypatch.setattr(results, "capture_native_file", lambda *args, **kwargs: pytest.fail("historical return recaptured"))
    assert custody.host.received_facts(custody.parent, custody.schema)[contracts.SAVED_SOURCE] == form["files"]
    frozen = custody.host.facts_for_closure(custody.parent, custody.schema)
    assert len(frozen[results.PREFIX]["attempts"]) == 1
    altered = deepcopy(form); altered["files"][0]["role"] = "components"
    with pytest.raises(ValueError): custody.host.record_admission(custody.parent, altered, custody.schema,
        custody.owner.run_id + ":" + custody.parent.episode_id + ":0:typed_form")


@pytest.mark.parametrize("attack", ["forged_form", "non_immediate_child", "unselected_duplicate"])
def test_subclass_return_wiring_rejects_forgery_non_immediate_and_unselected_duplicate(custody, tmp_path, monkeypatch, attack):
    engineering_ports(custody, tmp_path, monkeypatch)
    outcome = collect_controlled(custody); finish_controlled_action(custody, outcome)
    groups = custody.host.own_fact_groups(custody.child, verify_artifacts=True)
    form = {"files": groups[contracts.SAVED_SOURCE]}
    custody.store.db.execute("INSERT INTO runtime_forms VALUES(?,?,?,?)", (custody.owner.run_id, custody.child.episode_id, canonical(groups), canonical(form)))
    child_id, index, reported = custody.child.episode_id, 0, deepcopy(form)
    if attack == "forged_form":
        reported["files"][0]["role"] = "components"
    elif attack == "non_immediate_child":
        path = (*custody.child.path, ("results", "child_0"))
        child_id = EpisodeRef(custody.owner.run_id, path).episode_id
        custody.store.db.execute("INSERT INTO runtime_episodes VALUES(?,?,?,?)", (custody.owner.run_id, child_id, canonical(path), canonical(custody.child.request)))
    else:
        custody.store.db.execute("INSERT INTO runtime_report_attempts VALUES(?,?,?,?,?,?,?,?,NULL)",
            (custody.owner.run_id, custody.parent.episode_id, 0, "controlled-delivery", child_id, canonical(custody.contract), canonical(form), None))
        index = 1
    custody.store.db.execute("INSERT INTO runtime_report_attempts VALUES(?,?,?,?,?,?,?,?,NULL)",
        (custody.owner.run_id, custody.parent.episode_id, index, "controlled-delivery", child_id, canonical(custody.contract), canonical(reported), None))
    with pytest.raises(ValueError): custody.host._attempt(custody.parent, index)
    if attack == "unselected_duplicate":
        redelivery = {"kind": "redeliver_report", "delivery_ref": "controlled-delivery", "purpose": custody.contract["decision"], "schema_json": canonical(custody.schema)}
        custody.store.db.execute("INSERT INTO runtime_actions VALUES(?,?,?,?,NULL)", (custody.owner.run_id, custody.parent.episode_id, 1, canonical(redelivery)))
        actual_child, actual_form, _ = custody.host._attempt(custody.parent, 1)
        assert actual_child.episode_id == custody.child.episode_id and actual_form == form
        assert custody.host.received_facts(custody.parent, custody.schema)[contracts.SAVED_SOURCE] == form["files"]


def test_missing_scientific_reader_cannot_be_replaced_by_private_assertions(custody):
    supplied = {"state": "verified", "original_identity": {"asserted": True}, "plan": {"agrees_with_itself": True}}
    assert custody.host.initialize_original_binding(custody.child, **supplied) == {
        "state": "unavailable", "reason": "scientific_binding_unavailable", "proof_file": None, "original_identity": None}
    assert custody.host.received_original_binding(custody.child)["state"] == "unavailable"


@pytest.mark.parametrize("deliver_before", [False, True])
def test_saved_sheet_admission_uses_actual_frozen_receipt_prefix(tmp_path, deliver_before):
    raw = b'{"schema":"orf_measurement_sheet_v1","engineering_fixture":true}'
    value = controlled_owner(tmp_path, supplied_sheet_bytes=raw, deliver_before=deliver_before)
    try:
        if deliver_before:
            identity, control = value.host._received_sheet(value.child)
            assert retained_native_file(value.store, identity).read_bytes() == raw
            assert control["file"]["artifact_ref"] == value.supplied_ref
            assert control["receipt_manifest"] == value.receipts.manifest(value.child.episode_id)
        else:
            with pytest.raises(ValueError, match="received_sheet_not_known"): value.host._received_sheet(value.child)
            value.receipts.receive(value.parent.episode_id, [value.supplied_ref], kind="own_action", source_index=1)
            with pytest.raises(ValueError, match="received_sheet_not_known"): value.host._received_sheet(value.child)
    finally:
        value.store.close()


def test_rich_numeric_fact_is_not_registered_into_current_global_form_guard():
    numeric = contracts.molecular_sequence_fact_sources()[contracts.PROJECTION_SOURCE]["report_schema"]
    schema = {"type": "object", "additionalProperties": False, "properties": {"values": numeric}, "required": ["values"]}
    with pytest.raises(ValueError): validate_closed_schema(schema)


def original_receipt_ports(custody, tmp_path, monkeypatch, *, writer=(True, True)):
    """Engineered generic custody, not a configured native service or producer.

    The reader constructor receives no resources; its copied engineering map
    exercises actual saved-only read_target/_native and practical receipts.
    The LocalPracticalOperations constructor/launcher boundary is unexercised.
    """
    store, run, scope = custody.store, custody.owner.run_id, dict(custody.child.scope)
    workspace = tmp_path / "original-workspace"; workspace.mkdir()
    origin_path = (*custody.parent.path, ("launch_local", "child_1"))
    origin_id = EpisodeRef(run, origin_path).episode_id; start_key = run + ":" + origin_id + ":0"
    native_root = workspace / ".episode-operations" / digest({"run": run, "episode": origin_id}) / digest(start_key)
    native_root.mkdir(parents=True)
    output = native_root / execution.ATTEMPT_DIRECTORY / execution.OUTPUT_DIRECTORY
    output.mkdir(parents=True)
    _sheet, _components, _sources, paths = engineered(output)
    def pin(path):
        raw = path.read_bytes(); return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
    request = dict(version="molecular_sequence_driver_request_v1", mode="saved_sheet",
        attempt_identity={key: "engineering-asserted-" + key for key in ("run_id", "episode_id", "resource_id", "operation_key", "execution_id")},
        selection=dict(operation=contracts.OPERATIONS[0], sheet_file=pin(paths["sheet"])), scientific_context=None)
    request_path = native_root / "selected-request.json"; request_path.write_text(json.dumps(request))
    software = dict(version=execution.SOFTWARE_VERSION,
        python=dict(path="/engineering-unexecuted/python", sha256="1"*64, size_bytes=1),
        python_home="/engineering-unexecuted", python_version="engineering-unexecuted",
        import_roots=["/engineering-unexecuted/source"],
        software_files_file=dict(path="/engineering-unexecuted/manifest.json", sha256="2"*64, size_bytes=1),
        software_files_ref="artifact_" + "2"*64)
    environment = dict(PYTHONHOME=software["python_home"], PYTHONPATH=software["import_roots"][0],
        PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1")
    selection = dict(operation=contracts.OPERATIONS[0], mode="saved_sheet", driver_request=request, request_file=pin(request_path))
    payload = execution.selected_payload_sha256(selection=selection, software=software, policy=POLICY, selected_environment=environment)
    job = dict(argv=[software["python"]["path"], "-B", "-m", execution.ADAPTER_MODULE, "--plan", execution.PLAN_FILENAME,
        "--selected-payload-sha256", payload], environment=environment)
    context = dict(revision=0, cwd=str(workspace), environment={})
    assignment = practical.validate_assignment(dict(version=practical.ASSIGNMENT_VERSION, assignment_id="controlled-original",
        resource_id="controlled-local", resource_kind="local", workspace=str(workspace), endpoint="usable_handoff",
        requested_job=job, initial_context=context, inventory_snapshot={}, constraints={},
        progress_requirements=[dict(key="handoff", credit=1, predicate=dict(kind="requested_job_handoff"))], completion_keys=["handoff"]))
    ident = dict(run_id=run, episode_id=origin_id, resource_id="controlled-local", execution_id=str(native_root / "native.json"),
        operation_key=start_key, attempt_id=digest(start_key), assignment_sha256=digest(assignment), requested_job_sha256=digest(job))
    plan = execution.build_molecular_sequence_selected_plan(identity=ident, requested_job=job, selection=selection,
        software=software, policy=POLICY, selected_environment=environment)
    (native_root / execution.PLAN_FILENAME).write_text(json.dumps(plan, indent=2))
    command = [software["python"]["path"], str(native_root / "invoke.py"), str(native_root / "invoke.json")]
    native_request = dict(command=command, cwd=str(native_root), env={"TMPDIR": str(native_root)})
    native_request_path = native_root / "native.request"; native_request_path.write_text(json.dumps(native_request, indent=2))
    handle = dict(version="durable_systemd_native_job_v2", command=command, cwd=str(native_root),
        paths=dict(request=str(native_request_path)), request_sha256=pin(native_request_path)["sha256"], metadata=dict(policy=POLICY))
    (native_root / "native.json").write_text(json.dumps(handle, indent=2))
    (native_root / "invoke.json").write_text(json.dumps(dict(cwd=str(native_root), argv=execution.molecular_sequence_adapter_argv(plan), environment=environment)))
    declarations = {role: dict(relative_path=path.name, format="json", state="present", sha256=pin(path)["sha256"], size_bytes=pin(path)["size_bytes"])
        for role, path in paths.items()}
    declarations["capture"] = dict(relative_path="capture.json", format="json", state="absent", sha256=None, size_bytes=None)
    declaration = dict(version="molecular_sequence_driver_declaration_v1", mode="saved_sheet", operation=contracts.OPERATIONS[0],
        request_file=pin(request_path), request_file_pin_verified=True, attempt_identity=request["attempt_identity"],
        native_call_state="not_requested", native_failure=None, driver_failure=None, files=declarations,
        qualification="Explicit engineering declaration, no actual source invocation.")
    (output / "declaration.json").write_text(json.dumps(declaration, indent=2))
    origin_manifest = custody.receipts.bind(origin_id, custody.parent.episode_id)
    origin_request = dict(goal={"controlled_fixture": True}, message=dict(scope=scope, episode_assignment=assignment,
        knowledge_inheritance=origin_manifest), report_contract=custody.contract)
    origin = BindingContext(run, origin_id, "launch_local", origin_path, scope, assignment, origin_request)
    store.db.execute("INSERT INTO runtime_episodes VALUES(?,?,?,?)", (run, origin_id, canonical(origin_path), canonical(origin_request)))
    store.db.execute("INSERT INTO runtime_actions VALUES(?,?,?,?,NULL)", (run, origin_id, 0, canonical(dict(kind="tool", tool="practical.job.start", arguments={}))))
    job_fact = dict(**job, requested_job_sha256=digest(job), resource_kind="local", execution_id=ident["execution_id"],
        status="completed", returncode=0, output_paths=[], handoff=dict(execution_id=ident["execution_id"], monitor_operation="practical.job.status", results_operation="practical.job.collect"))
    outcome = dict(facts=dict(requested_job=job_fact), native_outcome=dict(attempt_operation_key=start_key, attempt_id=digest(start_key)))
    stamp = "2026-10-30T00:00:00+00:00"
    receipt = dict(version=practical.RECEIPT_VERSION, run_id=run, episode_id=origin_id, assignment_sha256=digest(assignment),
        operation_key=start_key, tool_name="practical.job.start", arguments={}, context_before=context, context_after=context,
        outcome=outcome, validations=practical.assess_validations(assignment, outcome, context, checked_at=stamp, tool_name="practical.job.start"),
        started_at=stamp, finished_at=stamp)
    source = PracticalReceiptInformation(store, run).publish(origin, receipt)
    store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
        (canonical(dict(status="completed", result=receipt, record_refs=[source])), run, origin_id))
    reader = ExecutionTargetReader(store, run_id=run, directory=custody.owner.directory, resources={}, api_execution=None)
    reader.resources = deepcopy({"controlled-local": dict(kind="local", workspace=str(workspace))})
    class NoOperations(dict):
        def __getitem__(self, key): pytest.fail("controlled saved reader reached operations/launcher")
        def get(self, *args): pytest.fail("controlled saved reader reached operations/launcher")
    reader.operations = NoOperations()
    custody.owner.job_progress_provider = SimpleNamespace(targets=reader)
    selected = json.loads(canonical(custody.child.assignment)); selected["handoff_ref"] = source
    child_request = json.loads(canonical(custody.child.request)); child_request["message"]["episode_assignment"] = selected
    custody.child = BindingContext(run, custody.child.episode_id, "results", custody.child.path, scope, selected, child_request)
    store.db.execute("UPDATE runtime_episodes SET request=? WHERE run_id=? AND episode_id=?", (canonical(child_request), run, custody.child.episode_id))
    commission = json.loads(store.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=0", (run, custody.parent.episode_id)).fetchone()[0])
    commission["assignment"] = selected
    store.db.execute("UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=0", (canonical(commission), run, custody.parent.episode_id))
    custody.target = reader.read_target(source, scope)
    observed = []
    observation = dict(observed_at=stamp, state="completed" if all(writer) else "running", returncode=0 if all(writer) else None,
        failure_code=None, result_available=True, measurements=[], outputs=[], logs=[], provenance_refs=[],
        native=dict(version="durable_systemd_native_job_v2", execution_id=ident["execution_id"], terminal=writer[0], quiescent=writer[1], metadata=dict(policy=POLICY)))
    def observe(target, *, operation_key):
        assert target == custody.target; observed.append(operation_key); return deepcopy(observation)
    monkeypatch.setattr(reader, "observe_target", observe)
    # The actual _worker sees no selected deployment and returns its existing
    # worker_unavailable result before any manifest, launcher or calculator.
    from gene_annotation_episode import molecular_sequence_driver, molecular_sequence_native
    monkeypatch.setattr(molecular_sequence_driver, "_calculate", lambda *args: pytest.fail("original recovery recalculated"))
    monkeypatch.setattr(molecular_sequence_native, "execute_molecular_sequence_request", lambda *args: pytest.fail("original recovery invoked source"))
    custody.native_root, custody.output, custody.plan = native_root, output, plan
    custody.reader, custody.observed, custody.declaration = reader, observed, declaration
    return custody


def next_original_collect(custody):
    index = int(custody.operation_key.rsplit(":", 1)[1]) + 1
    custody.operation_key = custody.owner.run_id + ":" + custody.child.episode_id + ":" + str(index)
    custody.store.db.execute("INSERT INTO runtime_actions VALUES(?,?,?,?,NULL)",
        (custody.owner.run_id, custody.child.episode_id, index, canonical(dict(kind="tool", tool="execution.results.collect", arguments={}))))


def original_controls(custody):
    action = custody.host.action_directory(custody.child.episode_id, custody.operation_key)
    link = read_control(action / "original-evidence-link.json")
    root = Path(custody.owner.directory) / "molecular-sequence-captures" / link["original_job_sha256"]
    return root, link, read_control(root / "evidence.json")


def collect_original(custody):
    outcome = collect_controlled(custody)
    # Ordinary selected file-form scope is unchanged. Native failure facts are
    # still unregistered and are not injected into this public child contract.
    assert outcome["result"]["facts"][contracts.FAILURE_SOURCE] == []
    return outcome


def private_original_failures(custody):
    path = custody.host.action_directory(custody.child.episode_id, custody.operation_key) / "receipt.json"
    receipt = read_control(path)
    assert receipt["facts"][contracts.FAILURE_SOURCE] == []
    return contracts.validate_molecular_sequence_fact_values(contracts.FAILURE_SOURCE, receipt["failures"])


@pytest.mark.parametrize("later", [False, True])
def test_real_original_publication_recovery_uses_shared_evidence_after_producer_disappears(custody, tmp_path, monkeypatch, later):
    original_receipt_ports(custody, tmp_path, monkeypatch)
    actual = results.immutable
    def stop(path, value):
        if Path(path).name == "receipt.json": raise OSError("controlled_real_publication_failure")
        return actual(path, value)
    monkeypatch.setattr(results, "immutable", stop)
    with pytest.raises(OSError, match="controlled_real_publication_failure"): collect_original(custody)
    root, link, evidence = original_controls(custody)
    sheet = read_control(root / "roles/sheet.json")["file"]
    assert evidence["association"]["state"] == "unavailable"
    assert sheet["artifact_ref"] not in set(custody.receipts.known(custody.parent.episode_id))
    assert custody.store.db.execute("SELECT count(*) FROM runtime_forms").fetchone()[0] == 0
    assert custody.store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=0", (custody.owner.run_id, custody.child.episode_id)).fetchone()[0] is None
    shutil.rmtree(custody.native_root)
    monkeypatch.setattr(results, "immutable", actual)
    monkeypatch.setattr(custody.reader, "observe_target", lambda *args, **kwargs: pytest.fail("recovery observed original again"))
    capture = results.capture_native_file
    def private_only(store, **kwargs):
        assert not Path(kwargs["directory"]).is_relative_to(custody.native_root), "recovery opened disappeared producer"
        return capture(store, **kwargs)
    monkeypatch.setattr(results, "capture_native_file", private_only)
    if later: next_original_collect(custody)
    outcome = collect_original(custody)
    again_root, again_link, _ = original_controls(custody)
    assert again_root == root and again_link["evidence_file"] == link["evidence_file"]
    assert outcome["result"]["facts"][contracts.SAVED_SOURCE][0]["artifact_ref"] == sheet["artifact_ref"]
    assert outcome["result"]["delivery_complete"] is False  # No worker deployment was selected.
    assert len(custody.observed) == 1
    assert retained_native_file(custody.store, sheet).is_file()


@pytest.mark.parametrize("failed_role", ["sheet", "components"])
def test_real_original_partial_retention_later_collect_retries_only_failed_sibling(custody, tmp_path, monkeypatch, failed_role):
    original_receipt_ports(custody, tmp_path, monkeypatch)
    actual_capture, actual_immutable = results.capture_native_file, results.immutable
    def fail_one(store, **kwargs):
        if kwargs["directory"] == str(custody.output) and kwargs["relative_path"] == failed_role + ".json":
            raise NativeFileCaptureError("retained_artifact_unavailable")
        return actual_capture(store, **kwargs)
    def stop(path, value):
        if Path(path).name == "receipt.json": raise OSError("publication_interrupted")
        return actual_immutable(path, value)
    monkeypatch.setattr(results, "capture_native_file", fail_one); monkeypatch.setattr(results, "immutable", stop)
    with pytest.raises(OSError, match="publication_interrupted"): collect_original(custody)
    root, _link, _ = original_controls(custody)
    success = "components" if failed_role == "sheet" else "sheet"
    committed = read_control(root / ("roles/" + success + ".json"))
    assert committed["file"] is not None and read_control(root / ("roles/" + failed_role + ".json")) is None
    for path in tuple(custody.native_root.iterdir()):
        if path != custody.output.parent:
            if path.is_dir(): shutil.rmtree(path)
            else: path.unlink()
    for path in custody.output.iterdir():
        if path.name != failed_role + ".json": path.unlink()
    retried = []
    def capture_failed_only(store, **kwargs):
        if Path(kwargs["directory"]).is_relative_to(custody.native_root):
            assert kwargs["directory"] == str(custody.output) and kwargs["relative_path"] == failed_role + ".json"
            retried.append(failed_role)
        return actual_capture(store, **kwargs)
    monkeypatch.setattr(results, "capture_native_file", capture_failed_only); monkeypatch.setattr(results, "immutable", actual_immutable)
    monkeypatch.setattr(custody.reader, "observe_target", lambda *args, **kwargs: pytest.fail("later collect observed original"))
    next_original_collect(custody); collect_original(custody)
    assert retried == [failed_role]
    assert read_control(root / ("roles/" + success + ".json")) == committed
    assert read_control(root / ("roles/" + failed_role + ".json"))["file"] is not None


def test_real_original_changed_failed_sibling_is_not_substituted(custody, tmp_path, monkeypatch):
    original_receipt_ports(custody, tmp_path, monkeypatch)
    actual = results.capture_native_file
    def fail(store, **kwargs):
        if kwargs["directory"] == str(custody.output) and kwargs["relative_path"] == "components.json": raise NativeFileCaptureError("retained_artifact_unavailable")
        return actual(store, **kwargs)
    monkeypatch.setattr(results, "capture_native_file", fail); collect_original(custody)
    root, _, _ = original_controls(custody); committed = read_control(root / "roles/sheet.json")
    (custody.output / "components.json").write_bytes(b'{"foreign":true}')
    monkeypatch.setattr(results, "capture_native_file", actual)
    next_original_collect(custody); outcome = collect_original(custody)
    receipt = read_control(custody.host.action_directory(custody.child.episode_id, custody.operation_key) / "receipt.json")
    assert receipt["source_files"]["components"]["state"] == "identity_conflict"
    assert read_control(root / "roles/sheet.json") == committed
    assert outcome["result"]["facts"][contracts.SAVED_SOURCE][0]["artifact_ref"] == committed["file"]["artifact_ref"]


@pytest.mark.parametrize("changed", ["original_job", "assignment", "payload"])
def test_real_original_foreign_evidence_rejected_before_output_access(custody, tmp_path, monkeypatch, changed):
    original_receipt_ports(custody, tmp_path, monkeypatch); collect_original(custody)
    root, _link, value = original_controls(custody)
    if changed == "original_job": value["original_job"]["start_operation_key"] += "foreign"
    else:
        snapshot_file = value["snapshot_file"]
        snapshot = json.loads(retained_native_file(custody.store, snapshot_file).read_bytes())
        if changed == "assignment": snapshot["original_plan"]["identity"]["assignment_sha256"] = "f"*64
        else: snapshot["original_plan"]["selected_payload_sha256"] = "f"*64
        reference = custody.store.artifact(canonical(snapshot), "application/json")
        metadata = custody.store.get(reference)
        value["snapshot_file"] = dict(artifact_ref=reference, sha256=metadata["sha256"], size_bytes=metadata["size"], format=snapshot_file["format"])
    # Both forged operands have valid byte pins: the independent original
    # target/start/assignment relationship, not a digest failure, rejects them.
    raw = canonical(value)
    reference = custody.store.artifact(raw, "application/json"); metadata = custody.store.get(reference)
    file = dict(artifact_ref=reference, sha256=metadata["sha256"], size_bytes=metadata["size"], format="molecular_sequence_original_capture_evidence_v1")
    for name, text in (("evidence.json", raw), ("evidence-file.json", canonical(file))):
        path = root / name; path.chmod(0o600); path.write_text(text)
    monkeypatch.setattr(results, "capture_native_file", lambda *args, **kwargs: pytest.fail("foreign evidence opened producer"))
    next_original_collect(custody)
    with pytest.raises(ValueError): collect_original(custody)


@pytest.mark.parametrize("field", ["snapshot_file", "declaration"])
def test_real_original_retained_evidence_mutation_never_falls_back_to_live_controls(custody, tmp_path, monkeypatch, field):
    original_receipt_ports(custody, tmp_path, monkeypatch); collect_original(custody)
    root, _, evidence = original_controls(custody)
    identity = evidence[field] if field == "snapshot_file" else evidence[field]["file"]
    path = retained_native_file(custody.store, identity); path.chmod(0o600); path.write_bytes(b'{"tampered":true}')
    monkeypatch.setattr(results, "capture_native_file", lambda *args, **kwargs: pytest.fail("mutation reopened original"))
    next_original_collect(custody); outcome = collect_original(custody)
    assert private_original_failures(custody)[0]["code"] == "artifact_identity_conflict"
    assert read_control(root / "roles/sheet.json")["file"] is not None


def test_real_original_evidence_storage_failure_is_typed_and_seal_can_resume_without_producer(custody, tmp_path, monkeypatch):
    original_receipt_ports(custody, tmp_path, monkeypatch)
    actual = results.capture_native_file; roles = []
    def fail_seal(store, **kwargs):
        if kwargs["relative_path"] in ("sheet.json", "components.json"): roles.append(kwargs["relative_path"])
        if kwargs["relative_path"] == "evidence.json": raise NativeFileCaptureError("retained_artifact_unavailable")
        return actual(store, **kwargs)
    monkeypatch.setattr(results, "capture_native_file", fail_seal)
    outcome = collect_original(custody)
    assert roles == []
    assert private_original_failures(custody)[0]["code"] == "retention_failed"
    action_root = custody.host.action_directory(custody.child.episode_id, custody.operation_key)
    assert read_control(action_root / "receipt.json")["association"]["state"] == "unavailable"
    # The immutable pending evidence, not a live declaration, survives the
    # failed Store seal. Only unchanged output data remain for later capture.
    for path in tuple(custody.native_root.iterdir()):
        if path != custody.output.parent:
            if path.is_dir(): shutil.rmtree(path)
            else: path.unlink()
    (custody.output / "declaration.json").unlink()
    monkeypatch.setattr(results, "capture_native_file", actual)
    monkeypatch.setattr(custody.reader, "observe_target", lambda *args, **kwargs: pytest.fail("seal recovery observed again"))
    next_original_collect(custody); collect_original(custody)
    root, _, _ = original_controls(custody)
    assert read_control(root / "evidence-file.json") is not None and read_control(root / "roles/sheet.json")["file"] is not None


@pytest.mark.parametrize("writer", [(False, True), (True, False)])
def test_real_original_unclosed_writer_has_valid_unavailable_association_and_no_capture(custody, tmp_path, monkeypatch, writer):
    original_receipt_ports(custody, tmp_path, monkeypatch, writer=writer)
    actual_capture = results.capture_native_file
    monkeypatch.setattr(results, "capture_native_file", lambda *args, **kwargs: pytest.fail("unclosed writer captured controls/output"))
    outcome = collect_original(custody)
    assert outcome["result"]["delivery_complete"] is False
    assert private_original_failures(custody)[0]["code"] == "writer_not_closed"
    receipt = read_control(custody.host.action_directory(custody.child.episode_id, custody.operation_key) / "receipt.json")
    assert receipt["association"]["state"] == "unavailable"
    monkeypatch.setattr(custody.reader, "observe_target", lambda *args, **kwargs: pytest.fail("same action observed again"))
    assert collect_original(custody) == outcome
    assert len(custody.observed) == 1
    later_observation = read_control(custody.host.action_directory(custody.child.episode_id, custody.operation_key) / "observation.json")
    later_observation.update(state="completed", returncode=0)
    later_observation["native"].update(terminal=True, quiescent=True)
    def later_observe(target, *, operation_key):
        custody.observed.append(operation_key); return deepcopy(later_observation)
    monkeypatch.setattr(custody.reader, "observe_target", later_observe)
    # No sealed writer evidence exists, so this independently selected action
    # may observe once; no same-action observation was silently refreshed.
    monkeypatch.setattr(results, "capture_native_file", actual_capture)
    next_original_collect(custody); collect_original(custody)
    assert len(custody.observed) == 2
    root, _, _ = original_controls(custody)
    assert read_control(root / "evidence-file.json") is not None


@pytest.mark.parametrize("declaration_kind", ["malformed", "unavailable", "declared_absence"])
def test_real_original_declaration_failure_and_absence_keep_independent_cells(custody, tmp_path, monkeypatch, declaration_kind):
    original_receipt_ports(custody, tmp_path, monkeypatch)
    if declaration_kind == "malformed": (custody.output / "declaration.json").write_bytes(b'{"broken":')
    elif declaration_kind == "unavailable": (custody.output / "declaration.json").unlink()
    else:
        custody.declaration["files"]["capture"] = dict(relative_path="capture.json", format="json", state="absent", sha256=None, size_bytes=None)
        custody.declaration["native_failure"] = {"source_error": "Engineering source-error metadata; no actual source call."}
        (custody.output / "declaration.json").write_text(json.dumps(custody.declaration))
    collect_original(custody)
    root, _, evidence = original_controls(custody)
    state = "schema_invalid" if declaration_kind == "malformed" else "producer_unavailable" if declaration_kind == "unavailable" else "retained"
    assert evidence["declaration"]["state"] == state
    assert read_control(root / "roles/sheet.json")["file"] is not None
    receipt = read_control(custody.host.action_directory(custody.child.episode_id, custody.operation_key) / "receipt.json")
    assert receipt["projection"]["public"]["rows"][0]["value"] == 12
    if declaration_kind == "declared_absence":
        assert receipt["source_files"]["capture"]["state"] == "producer_absent"
        document = json.loads(retained_native_file(custody.store, evidence["declaration"]["file"]).read_bytes())
        assert document["native_failure"] == custody.declaration["native_failure"]


def supplied_form():
    definitions = contracts.supplied_file_fact_sources()
    return dict(type="object", properties={"files": definitions[contracts.SAVED_SOURCE]["report_schema"],
        "failures": definitions[contracts.FAILURE_SOURCE]["report_schema"]}, required=["files", "failures"], additionalProperties=False)


@contextmanager
def supplied_owner(tmp_path, *, raw=None, namespace="artifact", deliver=True, protected=False, grant_artifact=False,
        action="calculate", components=None, include_sheet=True, deny_artifact=False):
    """Actual common owner/Store/EPR with explicitly engineered commissions."""
    from test_molecular_sequence_input_bindings import actual_received_input_owner
    from tests.test_molecular_sequence_result_contracts import supplied_sheet_and_selection, supplied_selector
    sheet, _selection = supplied_sheet_and_selection()
    raw = json.dumps(sheet, indent=3).encode() if raw is None else raw
    with actual_received_input_owner(tmp_path, raw=raw, namespace=namespace, deliver=deliver,
            protected=protected, grant_artifact=grant_artifact) as actual:
        store, owner = actual.store, actual.owner
        for sql in (
            "CREATE TABLE runtime_forms(run_id TEXT,episode_id TEXT,facts TEXT,form TEXT,PRIMARY KEY(run_id,episode_id))",
            "CREATE TABLE runtime_report_attempts(run_id TEXT,parent_episode_id TEXT,decision_index INTEGER,delivery_ref TEXT,child_episode_id TEXT,contract TEXT,form TEXT,failure TEXT,report_contract_declaration TEXT)",
        ): store.db.execute(sql)
        owner.directory = tmp_path / "supplied-run"; owner.directory.mkdir()
        def selected_action(episode_id, operation_key, tool_name, arguments):
            prefix = owner.run_id + ":" + episode_id + ":"
            assert operation_key.startswith(prefix)
            row = store.db.execute("SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
                (owner.run_id, episode_id, int(operation_key[len(prefix):]))).fetchone()
            assert row is not None and json.loads(row["action"]) == {"kind": "tool", "tool": tool_name, "arguments": arguments}
            return row
        owner._selected_result_action = selected_action
        host = results.MolecularSequenceResults(owner)
        if deny_artifact: actual.denied.add((actual.artifact_ref, "artifact"))
        if action == "read_stored":
            stored = {"sheet": dict(reference=actual.reference, namespace=namespace) if include_sheet else None, "components": None}
            if components is not None:
                ref = store.artifact(json.dumps(components, indent=2), "application/json")
                actual.receipts.receive(actual.parent.episode_id, [ref], kind="initial")
                stored["components"] = dict(reference=ref, namespace="artifact")
            selector_value = supplied_selector(actual.reference, namespace=namespace, action=action, stored=stored)
        else: selector_value = supplied_selector(actual.reference, namespace=namespace)
        # Freeze a new child AFTER any separately delivered component File.
        child = actual.child(1)
        assignment = dict(version=contracts.SUPPLIED_ASSIGNMENT_VERSION, selector=selector_value,
            constraints=dict(policy=deepcopy(POLICY), environment={}))
        schema = supplied_form(); contract = host._report_contract("Return the selected scientific Files and failures.", schema)
        request = child.as_record()["request"]
        request["message"]["episode_assignment"] = assignment
        request["report_contract"] = contract
        child = BindingContext(owner.run_id, child.episode_id, "results", child.path, child.scope, assignment, request)
        store.db.execute("UPDATE runtime_episodes SET request=? WHERE run_id=? AND episode_id=?", (canonical(request), owner.run_id, child.episode_id))
        selected = json.loads(store.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=1",
            (owner.run_id, actual.parent.episode_id)).fetchone()[0])
        selected.update(assignment=assignment, purpose=contract["decision"], schema_json=canonical(schema))
        store.db.execute("UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=1",
            (canonical(selected), owner.run_id, actual.parent.episode_id))
        store.db.execute("INSERT INTO runtime_actions VALUES(?,?,?,?,NULL)", (owner.run_id, child.episode_id, 0,
            canonical(dict(kind="tool", tool="execution.results.collect", arguments={}))))
        yield SimpleNamespace(store=store, owner=owner, host=host, parent=actual.parent, child=child, target=None,
            receipts=actual.receipts, schema=schema, contract=contract, actual=actual,
            operation_key=owner.run_id + ":" + child.episode_id + ":0")


def inline_supplied_worker(value, monkeypatch):
    async def inline(action, plan):
        # Actual finite pure worker inside the approved bounded check; no
        # configured worker deployment or original native producer is claimed.
        path = action.directory / "worker-plan.json"; immutable(path, plan)
        raw = path.read_bytes()
        return worker.run_molecular_sequence_result_worker(plan_file=dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(),
            size_bytes=len(raw)), output_directory=plan["directory"]), None
    monkeypatch.setattr(value.host, "_worker", inline)


def private_supplied_record(value):
    receipt = read_control(value.host.action_directory(value.child.episode_id, value.operation_key) / "receipt.json")
    return receipt, contracts.validate_molecular_sequence_calculation_record(receipt["calculation_record"])


def replace_supplied_assignment(value, assignment, *, commission_index=1):
    """Change both actual engineered commission operands, never just a plan."""
    request = value.child.as_record()["request"]; request["message"]["episode_assignment"] = assignment
    value.child = BindingContext(value.owner.run_id, value.child.episode_id, "results", value.child.path, value.child.scope, assignment, request)
    value.store.db.execute("UPDATE runtime_episodes SET request=? WHERE episode_id=?", (canonical(request), value.child.episode_id))
    row = value.store.db.execute("SELECT action FROM runtime_actions WHERE episode_id=? AND decision_index=?", (value.parent.episode_id, commission_index)).fetchone()
    selected = json.loads(row[0]); selected.update(assignment=assignment, purpose=value.contract["decision"], schema_json=canonical(value.schema))
    value.store.db.execute("UPDATE runtime_actions SET action=? WHERE episode_id=? AND decision_index=?", (canonical(selected), value.parent.episode_id, commission_index))


def engineered_supplied_components():
    """Deliberately caller-authored closed values; not workflow calculations."""
    from tests.test_molecular_sequence_result_contracts import supplied_sheet_and_selection
    sheet, selection = supplied_sheet_and_selection()
    cell = dict(value=777.25, exact_value=dict(numerator="3109", denominator="4"), unit="ug/L",
        quantity_basis=dict(kind="mass_of_element", identity="As"), state="qualified", reason=None,
        formula="engineering_literal", input_paths=["/samples/0"], qualifications=["engineering_supplied_value"],
        uncertainty=dict(state="not_propagated", reason="no_selected_joint_uncertainty_model"))
    row = dict(sample_id=sheet["samples"][0]["sample_id"], species_id=sheet["species"][0]["species_id"], sample_ordinal=0,
        species_ordinal=0, representation=sheet["samples"][0]["representation"], signal_kind=sheet["samples"][0]["signal_kind"],
        association=dict(state="ambiguous", reason="engineering_ambiguity", measurement_id=None, measurement_ordinal=None,
            candidates=[], competing_species_ids=[], qualifications=[]), selected_calibration_ids=selection["calibration_ids"],
        calibration_id=None, calibration_range_state="unknown", linear_estimate=cell, aliquot_concentration=deepcopy(cell),
        original_sample_concentration=deepcopy(cell), censoring=[], qualifications=["engineering_supplied_value"])
    return dict(version="calibrated_signal_components_v1", sheet=sheet, selection=selection,
        population=dict(supplied_sample_count=1, supplied_species_count=1, selected_sample_count=1, selected_species_count=1,
            returned_row_count=1, association_species_ids=sheet["association"]["analysis_species_ids"],
            association_competitor_basis="declared_analysis_population", replicate_pooling=False), rows=[row],
        uncertainty_assessments=[], unassigned_measurements=[], qualifications=["engineering_supplied_values_not_calculated"])


@pytest.mark.parametrize("namespace", ["artifact", "source"])
def test_supplied_actual_owner_calculates_once_captures_and_grants_only_requested_scientific_files(tmp_path, monkeypatch, namespace):
    from gene_annotation_episode import calibrated_signal_calculations as calculations
    with supplied_owner(tmp_path, namespace=namespace) as value:
        inline_supplied_worker(value, monkeypatch)
        calls, authority = [], calculations.calculate_calibrated_signal_components
        def count(sheet, *, selection):
            calls.append(1); return authority(sheet, selection=selection)
        monkeypatch.setattr(calculations, "calculate_calibrated_signal_components", count)
        outcome = collect_controlled(value); finish_controlled_action(value, outcome)
        receipt, record = private_supplied_record(value)
        assert calls == [1] and record["calculation_call_count"] == 1 and record["origin_state"] == "selected_calculation_recorded"
        assert record["native_invocation"] == "not_requested" and record["acquired_population"] is None
        assert outcome["result"]["delivery_complete"] and outcome["result"]["facts"][contracts.PROJECTION_SOURCE] == []
        assert retained_native_file(value.store, record["source_files"]["sheet"]["file"]).read_bytes() == value.store.get_artifact(value.actual.artifact_ref)
        assert not value.host.resolve_own(value.child, receipt["calculation_record_file"]["artifact_ref"], "artifact")
        assert not value.host.resolve_own(value.child, record["input_evidence_files"]["sheet"]["artifact_ref"], "artifact")
        assert value.host.completion(value.child) is None
        assert value.host.calculation_completion(value.child)["endpoint"] == "requested_scientific_files_delivered"
        assert "credit" not in value.host.credit_view(value.child, {})
        groups = value.host.own_fact_groups(value.child, verify_artifacts=True)
        form = dict(files=groups[contracts.SAVED_SOURCE], failures=groups[contracts.FAILURE_SOURCE])
        value.store.db.execute("INSERT INTO runtime_forms VALUES(?,?,?,?)", (value.owner.run_id, value.child.episode_id, canonical(groups), canonical(form)))
        value.store.db.execute("INSERT INTO runtime_report_attempts VALUES(?,?,?,?,?,?,?,?,NULL)",
            (value.owner.run_id, value.parent.episode_id, 1, "supplied-file-delivery", value.child.episode_id, canonical(value.contract), canonical(form), None))
        refs = value.host.record_admission(value.parent, form, value.schema,
            value.owner.run_id + ":" + value.parent.episode_id + ":1:typed_form")
        assert set(refs) == {row["artifact_ref"] for row in form["files"]} and len(refs) == 2
        assert receipt["calculation_record_file"]["artifact_ref"] not in refs
        assert record["worker_plan_file"]["artifact_ref"] not in refs
        value.receipts.receive(value.parent.episode_id, refs, kind="child_form", source_index=1)
        assert all(value.host.resolve_received(value.parent, ref, "artifact") for ref in refs)


@pytest.mark.parametrize("kind", ["missing_calibration", "bad_json", "unreceived", "protected_dependency", "protected_owner", "bad_selection"])
def test_supplied_bad_or_denied_input_preserves_evidence_and_calls_no_worker(tmp_path, monkeypatch, kind):
    from tests.test_molecular_sequence_result_contracts import supplied_sheet_and_selection
    sheet, _selection = supplied_sheet_and_selection()
    if kind == "missing_calibration": sheet["calibrations"] = None
    raw = b"{" if kind == "bad_json" else json.dumps(sheet).encode()
    with supplied_owner(tmp_path, raw=raw, namespace="source", deliver=kind != "unreceived",
            protected=kind in ("protected_dependency", "protected_owner"), grant_artifact=kind == "protected_owner",
            deny_artifact=kind == "protected_owner") as value:
        if kind == "bad_selection":
            assignment = value.child.as_record()["assignment"]
            assignment["selector"]["calculation_selection"]["sample_ids"] = ["not-supplied"]
            request = value.child.as_record()["request"]; request["message"]["episode_assignment"] = assignment
            value.child = BindingContext(value.owner.run_id, value.child.episode_id, "results", value.child.path, value.child.scope, assignment, request)
            value.store.db.execute("UPDATE runtime_episodes SET request=? WHERE episode_id=?", (canonical(request), value.child.episode_id))
            selected = json.loads(value.store.db.execute("SELECT action FROM runtime_actions WHERE episode_id=? AND decision_index=1", (value.parent.episode_id,)).fetchone()[0])
            selected["assignment"] = assignment
            value.store.db.execute("UPDATE runtime_actions SET action=? WHERE episode_id=? AND decision_index=1", (canonical(selected), value.parent.episode_id))
        async def forbidden(*args): pytest.fail("invalid supplied input invoked worker")
        monkeypatch.setattr(value.host, "_worker", forbidden)
        outcome = collect_controlled(value)
        receipt, record = private_supplied_record(value)
        assert record["calculation_call_count"] == 0 and record["source_files"]["components"]["file"] is None
        assert outcome["result"]["delivery_complete"] is False
        assert record["input_evidence_files"]["sheet"] is not None
        evidence = json.loads(retained_native_file(value.store, record["input_evidence_files"]["sheet"]).read_bytes())["evidence"]
        if kind == "missing_calibration":
            assert evidence["roles"]["samples"]["state"] == "present" and evidence["roles"]["calibrations"]["state"] == "invalid"
            assert record["source_files"]["sheet"]["file"] is not None
        if kind in ("unreceived", "protected_dependency", "protected_owner"):
            assert evidence["received_input"]["input"] is None
            assert outcome["result"]["facts"][contracts.SAVED_SOURCE] == []


@pytest.mark.parametrize("kind", ["both", "components_only", "sheet_only", "conflict"])
def test_supplied_stored_read_is_literal_independent_and_does_not_upgrade_caller_components(tmp_path, monkeypatch, kind):
    from gene_annotation_episode import calibrated_signal_calculations as calculations
    components = engineered_supplied_components()
    if kind == "conflict": components["sheet"]["samples"][0]["context_facts"].append(
        dict(name="different-supplied-context", value=True, unit=None, source=deepcopy(components["sheet"]["samples"][0]["source"])))
    with supplied_owner(tmp_path, action="read_stored", components=None if kind == "sheet_only" else components,
            include_sheet=kind != "components_only") as value:
        monkeypatch.setattr(calculations, "calculate_calibrated_signal_components", lambda *args, **kwargs: pytest.fail("stored read calculated"))
        monkeypatch.setattr(calculations, "validate_calibrated_signal_components", lambda *args: pytest.fail("stored read regraded"))
        async def forbidden(*args): pytest.fail("stored read launched a worker")
        monkeypatch.setattr(value.host, "_worker", forbidden)
        outcome = collect_controlled(value)
        _receipt, record = private_supplied_record(value)
        assert record["origin_state"] == "admitted_stored_unverified" and record["calculation_call_count"] == 0
        assert record["worker_plan_file"] is record["software"] is None
        assert record["linkage_state"] == {"both": "matched", "components_only": "sheet_unavailable", "sheet_only": "components_unavailable", "conflict": "conflict"}[kind]
        if kind != "sheet_only":
            retained = json.loads(retained_native_file(value.store, record["source_files"]["components"]["file"]).read_bytes())
            assert retained == components and retained["rows"][0]["linear_estimate"]["value"] == 777.25
        assert all(row["calculation_origin"] == "admitted_stored_unverified" for row in outcome["result"]["facts"][contracts.SAVED_SOURCE])


@pytest.mark.parametrize("failed_role", ["sheet", "components"])
def test_supplied_per_role_retention_failure_keeps_original_sheet_and_independent_component(tmp_path, monkeypatch, failed_role):
    with supplied_owner(tmp_path) as value:
        inline_supplied_worker(value, monkeypatch)
        capture = results.capture_native_file
        def fail(store, **kwargs):
            wanted = "sheet.json" if failed_role == "sheet" else "calculated_components.json"
            if Path(kwargs["directory"]).name == "worker" and kwargs["relative_path"] == wanted:
                raise NativeFileCaptureError("retained_artifact_unavailable")
            return capture(store, **kwargs)
        monkeypatch.setattr(results, "capture_native_file", fail)
        collect_controlled(value); _receipt, record = private_supplied_record(value)
        assert record["worker_outputs"][failed_role]["state"] == "retention_failed"
        assert record["source_files"]["sheet"]["file"]["artifact_ref"] == value.actual.artifact_ref
        assert record["calculation_call_count"] == 1
        if failed_role == "sheet": assert record["source_files"]["components"]["file"] is not None
        else: assert record["source_files"]["components"]["file"] is None


def test_supplied_publication_recovery_uses_frozen_record_without_worker_or_historical_paths(tmp_path, monkeypatch):
    with supplied_owner(tmp_path) as value:
        inline_supplied_worker(value, monkeypatch)
        original = results.immutable
        def stop(path, document):
            if Path(path).name == "receipt.json": raise OSError("supplied_publication_interrupted")
            return original(path, document)
        monkeypatch.setattr(results, "immutable", stop)
        with pytest.raises(OSError): collect_controlled(value)
        directory = value.host.action_directory(value.child.episode_id, value.operation_key)
        record = read_control(directory / "calculation-record.json")
        assert record["source_files"]["components"]["file"] is not None
        assert record["source_files"]["components"]["file"]["artifact_ref"] not in set(value.receipts.known(value.parent.episode_id))
        assert value.store.db.execute("SELECT result FROM runtime_actions WHERE episode_id=?", (value.child.episode_id,)).fetchone()[0] is None
        shutil.rmtree(directory / "worker")
        monkeypatch.setattr(results, "immutable", original)
        async def forbidden(*args): pytest.fail("publication recovery launched/recalculated")
        monkeypatch.setattr(value.host, "_worker", forbidden)
        outcome = collect_controlled(value); finish_controlled_action(value, outcome)
        assert outcome["result"]["delivery_complete"] and private_supplied_record(value)[1] == record
        assert collect_controlled(value) == outcome


def test_supplied_worker_death_without_completed_evidence_keeps_count_unknown_and_never_reruns(tmp_path, monkeypatch):
    with supplied_owner(tmp_path) as value:
        calls = []
        async def crashed(action, plan):
            calls.append(1)
            Path(plan["directory"]).mkdir()
            (Path(plan["directory"]) / "started.json").write_text('{"intent_only":true}')
            raise OSError("engineering_worker_death")
        monkeypatch.setattr(value.host, "_worker", crashed)
        outcome = collect_controlled(value)
        _receipt, record = private_supplied_record(value)
        assert record["calculation_state"] == "worker_uncertain" and record["calculation_call_count"] is None
        assert record["origin_state"] == "selected_action_only" and record["source_files"]["sheet"]["file"] is not None
        assert collect_controlled(value) == outcome and calls == [1]


def test_supplied_actual_selected_worker_and_saved_file_read_are_bound_to_owner(tmp_path, monkeypatch):
    from tests.test_molecular_sequence_execution import software_fixture
    with supplied_owner(tmp_path) as value:
        value.owner.molecular_sequence_result_software = software_fixture(tmp_path / "selected-common-worker")
        assignment = value.child.as_record()["assignment"]
        assignment["constraints"]["policy"]["memory_bytes"] //= 2
        assignment["constraints"]["environment"] = {"MPLBACKEND": "caller-selected-unused-by-this-pure-calculation"}
        replace_supplied_assignment(value, assignment)
        outcome = collect_controlled(value); finish_controlled_action(value, outcome)
        _receipt, record = private_supplied_record(value)
        assert record["calculation_call_count"] == 1 and record["calculation_state"] == "completed"
        diagnostic = json.loads(retained_native_file(value.store, record["worker_diagnostics_file"]).read_bytes())
        assert diagnostic["software_before"]["state"] == diagnostic["software_after"]["state"] == "verified"
        assert outcome["result"]["delivery_complete"] and record["native_invocation"] == "not_requested"
        assert record["policy"] == assignment["constraints"]["policy"]
        assert record["selected_environment"]["MPLBACKEND"] == assignment["constraints"]["environment"]["MPLBACKEND"]
        original_bytes = {role: retained_native_file(value.store, record["source_files"][role]["file"]).read_bytes()
            for role in ("sheet", "components")}
        groups = value.host.own_fact_groups(value.child, verify_artifacts=True)
        form = dict(files=groups[contracts.SAVED_SOURCE], failures=groups[contracts.FAILURE_SOURCE])
        value.store.db.execute("INSERT INTO runtime_forms VALUES(?,?,?,?)", (value.owner.run_id, value.child.episode_id, canonical(groups), canonical(form)))
        value.store.db.execute("INSERT INTO runtime_report_attempts VALUES(?,?,?,?,?,?,?,?,NULL)",
            (value.owner.run_id, value.parent.episode_id, 1, "actual-supplied-file-delivery", value.child.episode_id,
                canonical(value.contract), canonical(form), None))
        refs = value.host.record_admission(value.parent, form, value.schema,
            value.owner.run_id + ":" + value.parent.episode_id + ":1:typed_form")
        assert set(refs) == {record["source_files"][role]["file"]["artifact_ref"] for role in ("sheet", "components")}
        for file in (record["worker_plan_file"], record["worker_result_file"], record["worker_diagnostics_file"], record["input_evidence_files"]["sheet"]):
            assert file["artifact_ref"] not in refs
        value.receipts.receive(value.parent.episode_id, refs, kind="child_form", source_index=1)
        child = value.actual.child(2)
        request = child.as_record()["request"]; request["report_contract"] = value.contract
        value.child = BindingContext(value.owner.run_id, child.episode_id, "results", child.path, child.scope, child.assignment, request)
        from tests.test_molecular_sequence_result_contracts import supplied_selector
        stored = {role: dict(reference=record["source_files"][role]["file"]["artifact_ref"], namespace="artifact") for role in ("sheet", "components")}
        new_assignment = dict(version=contracts.SUPPLIED_ASSIGNMENT_VERSION,
            selector=supplied_selector(refs[0], action="read_stored", stored=stored), constraints=assignment["constraints"])
        replace_supplied_assignment(value, new_assignment, commission_index=2)
        value.operation_key = value.owner.run_id + ":" + value.child.episode_id + ":0"
        value.store.db.execute("INSERT INTO runtime_actions VALUES(?,?,?,?,NULL)", (value.owner.run_id, value.child.episode_id, 0,
            canonical(dict(kind="tool", tool="execution.results.collect", arguments={}))))
        from gene_annotation_episode import calibrated_signal_calculations as calculations
        monkeypatch.setattr(calculations, "calculate_calibrated_signal_components", lambda *args, **kwargs: pytest.fail("generated saved read calculated"))
        monkeypatch.setattr(calculations, "validate_calibrated_signal_components", lambda *args: pytest.fail("generated saved read regraded"))
        async def forbidden(*args): pytest.fail("generated saved read launched a worker")
        monkeypatch.setattr(value.host, "_worker", forbidden)
        saved_outcome = collect_controlled(value); finish_controlled_action(value, saved_outcome)
        _saved_receipt, saved = private_supplied_record(value)
        assert saved_outcome["result"]["delivery_complete"] and saved["calculation_call_count"] == 0
        assert saved["origin_state"] == "admitted_stored_unverified" and saved["linkage_state"] == "matched"
        assert diagnostic["calculation_call_count"] == 1  # One actual call total across both children.
        assert all(retained_native_file(value.store, saved["source_files"][role]["file"]).read_bytes() == original_bytes[role]
            for role in ("sheet", "components"))


def test_supplied_valid_unknown_calibration_returns_qualified_components_without_value_gate(tmp_path, monkeypatch):
    from tests.test_molecular_sequence_result_contracts import supplied_sheet_and_selection
    sheet, _selection = supplied_sheet_and_selection()
    for calibration in sheet["calibrations"]: calibration["applicability"] = "unknown"
    with supplied_owner(tmp_path, raw=json.dumps(sheet).encode()) as value:
        inline_supplied_worker(value, monkeypatch)
        outcome = collect_controlled(value); _receipt, record = private_supplied_record(value)
        components = json.loads(retained_native_file(value.store, record["source_files"]["components"]["file"]).read_bytes())
        assert any(row["aliquot_concentration"]["state"] == "unavailable" for row in components["rows"])
        assert record["validation_states"] == {"sheet": "valid", "components": "valid"}
        assert record["calculation_call_count"] == 1 and outcome["result"]["delivery_complete"]


@pytest.mark.parametrize("kind", ["context", "action"])
def test_supplied_actual_context_and_selected_action_must_match_before_input_freeze(tmp_path, monkeypatch, kind):
    with supplied_owner(tmp_path) as value:
        if kind == "context":
            request = value.child.as_record()["request"]; request["message"]["episode_assignment"]["selector"]["return_files"] = ["sheet"]
            value.child = BindingContext(value.owner.run_id, value.child.episode_id, "results", value.child.path,
                value.child.scope, request["message"]["episode_assignment"], request)
        else:
            value.store.db.execute("UPDATE runtime_actions SET action=? WHERE episode_id=? AND decision_index=0",
                (canonical(dict(kind="tool", tool="execution.results.status", arguments={})), value.child.episode_id))
        async def forbidden(*args): pytest.fail("forged input context/action invoked worker")
        monkeypatch.setattr(value.host, "_worker", forbidden)
        with pytest.raises((ValueError, AssertionError)): collect_controlled(value)
        directory = value.host.action_directory(value.child.episode_id, value.operation_key)
        assert not (directory / "supplied-sheet-input.json").exists()


@pytest.mark.parametrize("failed_port", ["immutable", "capture"])
def test_supplied_completed_call_before_result_control_retention_failure_is_unknown_never_zero(tmp_path, monkeypatch, failed_port):
    from gene_annotation_episode import calibrated_signal_calculations as calculations
    from gene_annotation_episode import native_file_capture
    with supplied_owner(tmp_path) as value:
        inline_supplied_worker(value, monkeypatch)
        calls, authority = [], calculations.calculate_calibrated_signal_components
        def count(sheet, *, selection):
            calls.append(1); return authority(sheet, selection=selection)
        monkeypatch.setattr(calculations, "calculate_calibrated_signal_components", count)
        original_immutable, original_capture = results.immutable, native_file_capture.capture_native_file
        fault_hits = []
        def fail_immutable(path, document):
            if Path(path).name == "supplied-worker-result.json":
                fault_hits.append("immutable")
                raise OSError("post_call_result_control_failure")
            return original_immutable(path, document)
        def fail_capture(store, **kwargs):
            if kwargs["relative_path"] == "supplied-worker-result.json":
                fault_hits.append("capture")
                raise NativeFileCaptureError("retained_artifact_unavailable")
            return original_capture(store, **kwargs)
        monkeypatch.setattr(results, "immutable", fail_immutable if failed_port == "immutable" else original_immutable)
        if failed_port == "capture": monkeypatch.setattr(native_file_capture, "capture_native_file", fail_capture)
        outcome = collect_controlled(value); _receipt, record = private_supplied_record(value)
        assert fault_hits == [failed_port]
        assert calls == [1] and record["calculation_call_count"] is None
        assert record["calculation_state"] == "worker_uncertain" and record["origin_state"] == "selected_action_only"
        assert record["source_files"]["sheet"]["file"]["artifact_ref"] == value.actual.artifact_ref
        directory = value.host.action_directory(value.child.episode_id, value.operation_key)
        assert (directory / "worker/result.json").is_file()
        async def forbidden(*args): pytest.fail("result-control retention failure reran worker")
        monkeypatch.setattr(value.host, "_worker", forbidden)
        assert collect_controlled(value) == outcome and calls == [1]


def test_supplied_existing_prepared_worker_handle_rejects_valid_pinned_foreign_environment_before_dispatch(tmp_path, monkeypatch):
    from gene_annotation_episode import native_lifecycle
    from gene_annotation_episode.local_jobs import LocalJobPolicy
    from tests.test_molecular_sequence_execution import software_fixture, _environment
    with supplied_owner(tmp_path) as value:
        software = software_fixture(tmp_path / "selected-prepared-worker")
        value.owner.molecular_sequence_result_software = software
        async def exercise():
            async with value.host.locked_action(value.child, target=None, tool_name="execution.results.collect",
                    arguments={}, operation_key=value.operation_key) as action:
                directory = action.directory
                record = value.host._supplied_record(action)
                admitted = value.host._supplied_input(action, record)
                assert admitted["sheet"] is not None
                environment = _environment(software)
                plan = dict(version=contracts.SUPPLIED_PLAN_VERSION, directory=str(directory / "worker"),
                    selector=value.child.as_record()["assignment"]["selector"], input_file=record["input_sheet_file"],
                    input_path=str(retained_native_file(value.store, record["input_sheet_file"])),
                    input_evidence_file=record["input_evidence_files"]["sheet"], software=software,
                    selected_environment=environment, policy=POLICY)
                contracts.validate_supplied_worker_plan(plan)
                plan_path = directory / "worker-plan.json"; immutable(plan_path, plan)
                raw = plan_path.read_bytes()
                command = [software["python"]["path"], "-B", "-m", "gene_annotation_episode.molecular_sequence_result_worker",
                    "--plan-file", str(plan_path), "--sha256", hashlib.sha256(raw).hexdigest(), "--size-bytes", str(len(raw)),
                    "--output-directory", plan["directory"]]
                foreign = {**environment, "CALLER_SELECTED_ENVIRONMENT": "foreign"}
                handle = native_lifecycle.prepare_job(command, cwd=directory, policy=LocalJobPolicy(**POLICY),
                    handle_path=directory / "worker-handle.json", env=foreign)
                body = handle.read(); request_raw = Path(body["paths"]["request"]).read_bytes()
                assert hashlib.sha256(request_raw).hexdigest() == body["request_sha256"]
                monkeypatch.setattr(native_lifecycle, "resume_start", lambda *args: pytest.fail("foreign environment dispatched"))
                with pytest.raises(ValueError, match="worker_environment_conflict"):
                    await value.host._worker(action, plan)
                assert handle.read()["stage"] == "prepared"
                assert not Path(body["paths"]["release"]).exists() and not Path(body["paths"]["launcher"]).exists()
        asyncio.run(exercise())


def test_supplied_ownership_classifies_withheld_produced_components_without_claiming_input_sheet(tmp_path, monkeypatch):
    with supplied_owner(tmp_path) as value:
        assignment = value.child.as_record()["assignment"]; assignment["selector"]["return_files"] = ["sheet"]
        replace_supplied_assignment(value, assignment)
        inline_supplied_worker(value, monkeypatch)
        outcome = collect_controlled(value); finish_controlled_action(value, outcome)
        _receipt, record = private_supplied_record(value)
        sheet = record["source_files"]["sheet"]["file"]["artifact_ref"]
        component = record["worker_outputs"]["components"]["file"]["artifact_ref"]
        assert sheet == value.actual.artifact_ref and sheet in set(value.receipts.known(value.parent.episode_id))
        assert not value.host.owns_reference(sheet)
        assert value.host.owns_reference(component)
        assert [row["artifact_ref"] for row in outcome["result"]["facts"][contracts.SAVED_SOURCE]] == [sheet]
        assert not value.host.resolve_received(value.parent, component, "artifact")
        # Classification only. The future unowned-reference gate must return
        # None; no global molecular resolver is installed by this fixture.


def test_supplied_stored_caller_files_do_not_become_owned_by_the_reader(tmp_path):
    with supplied_owner(tmp_path, action="read_stored", components=engineered_supplied_components()) as value:
        outcome = collect_controlled(value); finish_controlled_action(value, outcome)
        _receipt, record = private_supplied_record(value)
        assert record["origin_state"] == "admitted_stored_unverified"
        for role in ("sheet", "components"):
            reference = record["source_files"][role]["file"]["artifact_ref"]
            assert reference in set(value.receipts.known(value.parent.episode_id))
            assert not value.host.owns_reference(reference)
