"""Real Store/action/receipt bindings with deliberately synthetic native bytes.

The driver composes the selected-call, receipt and custody components. It is
not a model episode, live BV-BRC deployment or production acquisition callback.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, SourceSnapshot
from gene_annotation_episode.api_bvbrc_appservice import BVBRCAppServiceService
from gene_annotation_episode.api_selected_call import perform_selected_call
from gene_annotation_episode.api_selected_effects import SelectedAPIEffects, EffectConflict
from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.bvbrc_appservice_custody import AppServiceCustody
from gene_annotation_episode.bvbrc_appservice_inputs import AppServiceInputs, AppServiceInputError
from gene_annotation_episode.bvbrc_appservice_records import AppServiceRecords, provisional_receipt_ref
from gene_annotation_episode.bvbrc_appservice_receipt_values import build_appservice_receipt, confirm_appservice_effects
from gene_annotation_episode.bvbrc_application_definitions import get_application_spec
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.practical_execution_state import _immutable, _read
from gene_annotation_episode.state import Store
from test_api_bvbrc_appservice import CONFIG, PREFIX, OBJECT_UUID, SHOCK_UUID, Client, metadata
from test_bvbrc_appservice_custody import SavedRecords, request, selector, content, api_assignment


class NativeClient(Client):
    """In-memory native fixture; no network transport and no invented science."""

    def upload(self, url, supplied, *, filename):
        self.calls.append(("upload", url, supplied, filename))
        boundary = "gene-annotation-" + hashlib.sha256(filename.encode() + b"\x00" + hashlib.sha256(supplied).digest()).hexdigest()
        prefix = (f'--{boundary}\r\nContent-Disposition: form-data; name="upload"; '
            f'filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()
        sent = prefix + supplied + f"\r\n--{boundary}--\r\n".encode()
        body = json.dumps({"status": 200, "error": None, "data": {"id": SHOCK_UUID,
            "file": {"size": len(supplied), "checksum": {"sha256": hashlib.sha256(supplied).hexdigest()}}}}).encode()
        return SourceSnapshot("bvbrc_analysis", url, {"kind": "upload", "node_url": url,
            "filename": filename, "input_bytes": len(supplied), "input_sha256": hashlib.sha256(supplied).hexdigest(),
            "multipart_field": "upload", "multipart_boundary": boundary}, "2026-10-24T12:00:00+00:00",
            body, "application/json", {"status": 200, "body_complete": True, "received_body_bytes": len(body),
                "effective_url": url, "automatic_redirects": False, "headers": {},
                "request": {"method": "PUT", "url": url, "body_bytes": len(sent), "body_sha256": hashlib.sha256(sent).hexdigest()}})

    def download(self, url, *, max_bytes, byte_range=None):
        self.calls.append(("download", url, byte_range))
        body = self.body
        assert len(body) <= max_bytes, 'this complete-response fixture exceeds the selected byte limit'
        return SourceSnapshot("bvbrc_analysis", url, {"kind": "download", "url": url,
            "requested_byte_range": None if byte_range is None else list(byte_range), "max_bytes": max_bytes},
            "2026-10-24T12:00:00+00:00", body, "application/json", {"status": 200,
                "body_complete": True, "received_body_bytes": len(body), "effective_url": url,
                "response_byte_limit": max_bytes, "observed_body_bytes": len(body),
                "retained_body_bytes": len(body), "declared_body_bytes": len(body),
                "automatic_redirects": False, "headers": {"content-length": str(len(body))},
                "request": {"method": "GET", "url": url}})


class Driver:
    def __init__(self, store, tmp_path):
        self.saved = SavedRecords(store)
        self.store = store
        self.api = APIServiceExecution.__new__(APIServiceExecution)
        self.api.store, self.api.run_id, self.api.directory = store, self.saved.run_id, tmp_path / "execution"
        self.api.selected_effects = SelectedAPIEffects(tmp_path, run_id=self.saved.run_id)
        self.records = AppServiceRecords(self.api)
        self.custody = AppServiceCustody(store, self.saved.run_id, read_original_handoff=self.read_handoff)
        self.client = NativeClient()
        self.service = BVBRCAppServiceService(SimpleNamespace(store=store), CONFIG, client=self.client)
        self.bindings = AppServiceInputs(self.api, records=self.records, custody=self.custody)
        self.receipt_transform = None
        # Exact test-only target port for AppServiceRecords until root's outer
        # C4 host is assembled. It reads the real handoff and saved origin.
        self.api.read_target = self.target

    def read_handoff(self, reference):
        record = self.records.read(reference)
        assert record["contract"] == "TaskHandoff"
        value = record["value"]
        return {"reference": reference, "original_job_owner": value["original_job_owner"],
            "origin_context": self.custody.context(value["receipt"]["origin"]["episode_id"])}

    def target(self, reference, scope):
        origin = self.read_handoff(reference)["origin_context"]
        self.store.validate_scope(plain(origin.scope), parent_scope=plain(scope))
        return {"assignment": plain(origin.assignment), "resource_id": origin.assignment["resource_id"]}

    def tree(self, query=None):
        self.launch, self.context = self.saved.tree(query)
        self.api._manifest(self.context)
        return self.context

    def selection(self, suffix, args, *, context=None):
        context = self.context if context is None else context
        index = self.store.db.execute("SELECT COALESCE(MAX(decision_index),-1)+1 FROM runtime_actions "
            "WHERE run_id=? AND episode_id=?", (context.run_id, context.episode_id)).fetchone()[0]
        key = f"{context.run_id}:{context.episode_id}:{index}"
        self.saved.journal.save("runtime_actions", {"episode_id": context.episode_id, "decision_index": index,
            "action": canonical({"kind": "tool", "tool": PREFIX + suffix, "arguments": args}), "result": None, "credit": None})
        self.api._manifest(context)
        return context, key

    def bind(self, suffix, args, *, context=None):
        context, key = self.selection(suffix, args, context=context)
        value = self.bindings.bind_inputs(context, PREFIX + suffix, args, operation_key=key)
        query = self.target(context.assignment["handoff_ref"], context.scope)["assignment"]["request"] if context.role == "results" else plain(context.assignment)["request"]
        prepared = self.service.prepare(PREFIX + suffix, query, args, scope=plain(context.scope), previous_events=[],
            selector=plain(context.assignment)["selector"] if context.role == "results" else None, bound_inputs=value)
        return context, key, prepared

    def call(self, suffix, args, *, context=None, allow_failure=False):
        context, key, prepared = self.bind(suffix, args, context=context)
        directory = self.api._manifest(context) / "actions" / digest(key)
        directory.mkdir(exist_ok=True)
        _immutable(directory / "intent.json", {"run_id": context.run_id, "episode_id": context.episode_id,
            "operation_key": key, "name": PREFIX + suffix, "arguments": args,
            "assignment_sha256": digest(context.assignment), "prepared": prepared,
            "started_at": "2026-10-24T12:00:00+00:00"})
        call = asyncio.run(perform_selected_call(self.api, context, self.service, prepared,
            operation_key=key, directory=directory, fresh=True))
        assert allow_failure or call["failure"] is None
        snapshot = call["snapshot"]
        binding = None if snapshot is None else self.records.retain_snapshot(context, prepared, snapshot, operation_key=key)
        event = self.service.decode(prepared, snapshot)
        effects = call["effect_receipts"]
        if effects:
            effects = self.api.selected_effects.record_outcome(_read(directory / "effect_reservation.json"),
                confirm_appservice_effects(prepared, event, snapshot, snapshot_binding=binding, effect_receipts=effects))
        origin = self.records._origin(context, prepared, key)
        common = {"version": "bvbrc_appservice_support_receipt_v1", "receipt_ref": provisional_receipt_ref(origin),
            "purpose": prepared["purpose"], "origin": origin, "snapshot": binding,
            "effect_receipt_refs": [row["effect_ref"] for row in effects], "status": "ok", "diagnostics": []}
        if suffix == "download":
            return SimpleNamespace(context=context, key=key, prepared=prepared, directory=directory,
                snapshot=snapshot, binding=binding, event=event, common=common)
        value = build_appservice_receipt(prepared, event, snapshot, common_receipt=common, effect_receipts=effects)
        if self.receipt_transform is not None:
            value = self.receipt_transform(value)
            self.receipt_transform = None
        published = self.records.publish(context, value["contract"], value["value"], operation_key=key)
        refs = [published["source_ref"]]
        if binding is not None:
            refs.append(binding["source_ref"])
        if (directory / "definition_inputs.json").exists():
            refs.extend(_read(directory / "definition_inputs.json")["source_refs"])
        self.complete(context, key, directory, published, refs)
        return published

    def complete(self, context, key, directory, result, refs):
        outcome = {"status": "completed", "record_refs": refs, "changed_record_refs": refs,
            "result": result, "feedback": None}
        _immutable(directory / "outcome.json", outcome)
        index = int(key.rsplit(":", 1)[1])
        old = self.saved.journal.row("runtime_actions", context.episode_id, index)
        self.saved.journal.save("runtime_actions", {**old, "result": canonical(outcome), "credit": 0})
        self.saved.receipts.receive(context.episode_id, refs, kind="own_action", source_index=index)

    def launch_task(self):
        preparation = self.call("prepare", {"definition": {"kind": "packaged", "required_application_id": "Homology"}})
        self.client.value = {"id": "123", "application_id": "Homology", "state_code": "Q"}
        return self.call("submit", {"preparation_receipt_ref": preparation["source_ref"], "input_evidence_refs": []})

    def results(self, handoff, *, selection=None, index=3):
        self.saved.admit(self.launch, self.context, handoff["source_ref"])
        self.saved.admit(self.saved.root, self.launch, handoff["source_ref"])
        context = self.saved.child(self.saved.root, "results", {"version": "execution_results_assignment_v1",
            "handoff_ref": handoff["source_ref"], "selector": selector() if selection is None else selection}, index)
        self.api._manifest(context)
        return context

    def acquire(self, args, *, context):
        call = self.call("download", args, context=context)
        obj = call.prepared["bound_inputs"]["resolved"]["object"]
        projection = call.event["facts"]["projection"]
        artifact = {"role": args["role"], "source_ref": call.binding["source_ref"],
            "raw_artifact_ref": call.binding["content"]["artifact_ref"], "sha256": call.snapshot.sha256,
            "byte_count": len(call.snapshot.content), "workspace_object": obj["object"],
            "task_association": obj["task_association"], "declared_format": args["declared_format"],
            "transfer": {"receipt_ref": "fixture-self-reference", "body_complete": projection["body_complete"],
                "requested_range": projection["requested_range"], "observed_range": projection["observed_range"],
                "total_size": projection["total_size"], "object_complete": projection["object_complete"]}}
        receipt = {"version": "bvbrc_appservice_acquisition_v1", "origin": call.common["origin"],
            "original_handoff_ref": context.assignment["handoff_ref"], "selector_sha256": digest(context.assignment["selector"]),
            "snapshot": call.binding, "capability_selection": args["capability"], "object_selection": args["object"],
            "artifact": artifact, "requirement_ids": args["requirement_ids"], "publication_inputs_sha256": digest(call.prepared),
            "publication_ref": None, "valid_record_refs": [call.binding["source_ref"]], "status": "ok", "failure": None}
        encoded = deepcopy(receipt)
        del encoded["artifact"]["transfer"]["receipt_ref"]
        binding = self.saved.source(canonical(encoded).encode(), provider="inputs.fixture.acquisition")
        reference = binding["source_ref"]
        receipt["artifact"]["transfer"]["receipt_ref"] = reference
        validate_contract("AcquisitionReceipt", receipt)
        _immutable(call.directory / "fixture_acquisition.json", receipt)
        self.complete(context, call.key, call.directory, receipt, [reference, call.binding["source_ref"]])
        return reference

    def read_acquisition(self, reference):
        # Deliberately test-only callback, authenticating the retained selected
        # download above. It does not pretend production publication is bound.
        source = self.store.get(reference)
        assert source["provider"] == "inputs.fixture.acquisition"
        value = json.loads(self.store.get_artifact(source["artifact_ref"]))
        value["artifact"]["transfer"]["receipt_ref"] = reference
        origin = value["origin"]
        producer = self.custody.context(origin["episode_id"])
        self.custody.possession(producer, reference)
        directory = self.api._manifest(producer) / "actions" / digest(origin["operation_key"])
        assert _read(directory / "fixture_acquisition.json") == value
        assert _read(directory / "outcome.json")["result"] == value
        return validate_contract("AcquisitionReceipt", value)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("input binding verification attempted a network request")
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", forbidden)


@pytest.fixture
def driver(tmp_path):
    with Store(tmp_path / "state") as store:
        yield Driver(store, tmp_path)


def output_target(query):
    query["workspace_targets"].append({"target_id": "output", "path": query["parameters"]["output_path"],
        "type": "folder", "purpose": "output_parent", "input_binding_id": None, "metadata": {},
        "allow_overwrite": False, "allow_create_parents": True})
    return {"kind": "original_target", "target_id": "output"}


def receipt_row(receipt, pointer="/result/0/0"):
    return {"kind": "receipt_row", "receipt_ref": receipt["source_ref"], "row_pointer": pointer}


def download_args(obj, capability):
    return {"object": obj, "capability": capability, "byte_range": None, "max_bytes": 1048576, "requirement_ids": ["native"],
        "role": "native_output", "declared_format": selector()["requirements"][0]["declared_format"]}


def retained_input(driver):
    binding = driver.saved.source(b">q\nACGT\n")
    driver.saved.own(driver.saved.root, binding["source_ref"])
    query = request()
    query["parameters"]["input_source"] = "fasta_file"
    query["parameters"].pop("input_fasta_data")
    query["parameters"]["input_fasta_file"] = "/synthetic/work/input.fa"
    query["input_bindings"] = [{"binding_id": "query", "parameter_pointer": "/input_fasta_file",
        "kind": "retained_bytes", "content": binding, "workspace_path": "/synthetic/work/input.fa",
        "inline_value": None, "link_evidence": None, "members": []}]
    query["workspace_targets"] = [{"target_id": "query", "path": "/synthetic/work/input.fa", "type": "contigs",
        "purpose": "input", "input_binding_id": "query", "metadata": {}, "allow_overwrite": False, "allow_create_parents": True}]
    return query


def test_packaged_definition_retains_original_bytes_envelope_and_exact_selection(driver):
    context = driver.tree()
    count = driver.store.count("source")
    args = {"definition": {"kind": "packaged", "required_application_id": "Homology"}}
    _, key, prepared = driver.bind("prepare", args)
    bound = prepared["bound_inputs"]
    record = _read(driver.api._manifest(context) / "actions" / digest(key) / "definition_inputs.json")
    spec = get_application_spec("Homology")
    assert bound["resolved"]["definition_envelope"] == spec
    assert driver.store.get_artifact(record["retained_source"]["artifact_ref"]) == spec["source"]["content"].encode()
    assert json.loads(driver.store.get_artifact(bound["definition"]["content"]["artifact_ref"])) == spec["definition"]
    assert driver.store.count("source") == count + 2
    assert driver.client.calls == []
    assert prepared["native_operands"]["request"]["parameters"] == plain(context.assignment)["request"]["parameters"]
    assert driver.bindings.bind_inputs(context, PREFIX + "prepare", args, operation_key=key) == bound
    assert driver.store.db.execute("SELECT COUNT(*) FROM runtime_observations").fetchone()[0] == 0


def test_changed_or_missing_selected_action_never_retains_definition(driver):
    context = driver.tree()
    count = driver.store.count("source")
    args = {"definition": {"kind": "packaged", "required_application_id": "Homology"}}
    _, key = driver.selection("prepare", args)
    wrong = {"definition": {"kind": "packaged", "required_application_id": "Variation"}}
    with pytest.raises(ValueError, match="selected_action_conflict"):
        driver.bindings.bind_inputs(context, PREFIX + "prepare", wrong, operation_key=key)
    with pytest.raises(ValueError, match="selected_action_missing"):
        driver.bindings.bind_inputs(context, PREFIX + "prepare", args, operation_key=key.rsplit(":", 1)[0] + ":99")
    assert driver.store.count("source") == count


def test_supplied_definition_exact_escaped_pointer_and_origin_custody(driver):
    definition = {"id": "Homology", "parameters": []}
    supplied = driver.saved.source(canonical({"a/b": {"~": definition}, "other": {"id": "Variation"}}).encode())
    driver.saved.own(driver.saved.root, supplied["source_ref"])
    query = request()
    query["definition_inputs"] = [{"binding_id": "exact", "evidence": content(supplied, pointer="/a~1b/~0")}]
    driver.tree(query)
    _, key, prepared = driver.bind("prepare", {"definition": {"kind": "supplied", "definition_binding_id": "exact"}})
    env = prepared["bound_inputs"]["resolved"]["definition_envelope"]
    assert env["definition"] == definition
    retained = _read(driver.api._manifest(driver.context) / "actions" / digest(key) / "definition_inputs.json")
    assert retained["original_evidence"] == query["definition_inputs"][0]["evidence"]
    assert json.loads(env["source"]["content"]) == definition


def test_enumeration_extracts_explicit_index_not_first_same_id(driver):
    driver.tree()
    driver.client.value = [{"id": "Homology", "parameters": [], "selected": False},
                           {"id": "Homology", "parameters": [], "selected": True}]
    catalog = driver.call("enumerate_apps", {})
    assert catalog["contract"] == "CatalogReceipt"
    _, _, prepared = driver.bind("prepare", {"definition": {"kind": "enumerated",
        "catalog_receipt_ref": catalog["source_ref"], "record_index": 1}})
    assert prepared["bound_inputs"]["resolved"]["definition_envelope"]["definition"]["selected"] is True
    with pytest.raises(AppServiceInputError, match="definition_extraction_mismatch"):
        driver.bind("prepare", {"definition": {"kind": "enumerated", "catalog_receipt_ref": catalog["source_ref"], "record_index": 2}})


def test_create_upload_submit_require_original_input_and_selected_upload_evidence(driver):
    query = retained_input(driver)
    driver.tree(query)
    preparation = driver.call("prepare", {"definition": {"kind": "packaged", "required_application_id": "Homology"}})
    with pytest.raises(AppServiceInputError, match="input_evidence_missing"):
        driver.bind("submit", {"preparation_receipt_ref": preparation["source_ref"], "input_evidence_refs": []})
    driver.client.value = [metadata(shock_url="https://shock.example.invalid/node/" + SHOCK_UUID)["native_row"]]
    created = driver.call("workspace_create", {"objects": [{"target_id": "query", "data_binding_id": "query", "creation_time": None}],
        "options": {"createUploadNodes": 1}})
    upload = driver.call("upload", {"created_object": {"receipt_ref": created["source_ref"], "row_pointer": "/result/0/0"},
        "input_binding_id": "query", "filename": "original.fa"})
    assert upload["value"]["confirmation"] == "accepted_bytes_match"
    driver.client.value = {"id": "123", "application_id": "Homology", "state_code": "Q"}
    handoff = driver.call("submit", {"preparation_receipt_ref": preparation["source_ref"], "input_evidence_refs": [upload["source_ref"]]})
    assert handoff["contract"] == "TaskHandoff"
    assert [call[0] for call in driver.client.calls] == ["rpc", "upload", "rpc"]


def test_status_task_info_results_uuid_only_metadata_and_null_size(driver):
    driver.tree()
    handoff = driver.launch_task()
    driver.client.value = {"123": {"id": "123", "app": "Homology", "status": "running"}}
    observed = driver.call("status", {"handoff_ref": handoff["source_ref"]})
    assert observed["contract"] == "TaskObservation"
    results = driver.results(handoff)
    info = driver.call("task_info", {"handoff_ref": handoff["source_ref"], "file": "job_result_id"}, context=results)
    selection = {"kind": "task_info_object", "receipt_ref": info["source_ref"]}
    _, _, prepared = driver.bind("workspace_metadata", {"objects": [selection], "options": {}}, context=results)
    obj = prepared["bound_inputs"]["resolved"]["objects"][0]
    assert obj["native_reference"] == OBJECT_UUID
    assert obj["object"] == {"path": None, "uuid": OBJECT_UUID, "type": None, "metadata_receipt_ref": None}
    assert obj["metadata"] is None and obj["task_association"]["byte_version_status"] == "unknown"
    row = metadata("/synthetic/work/output/selected", type="job_result", size=None)
    driver.client.value = [[row["native_row"]]]
    metadata_receipt = driver.call("workspace_metadata", {"objects": [selection], "options": {}}, context=results)
    _, _, prepared = driver.bind("download_capability", {"objects": [receipt_row(metadata_receipt)], "generation": 0,
        "predecessor_receipt_ref": None}, context=results)
    obj = prepared["bound_inputs"]["resolved"]["objects"][0]
    assert obj["metadata"]["size"] is None
    assert obj["task_association"]["kind"] == "task_info_object"


def test_launch_can_use_its_exact_task_info_object_without_invented_path(driver):
    driver.tree()
    handoff = driver.launch_task()
    info = driver.call("task_info", {"handoff_ref": handoff["source_ref"], "file": "job_result_id"})
    _, _, prepared = driver.bind("workspace_metadata", {"objects": [
        {"kind": "task_info_object", "receipt_ref": info["source_ref"]}], "options": {}})
    obj = prepared["bound_inputs"]["resolved"]["objects"][0]
    assert prepared["bound_inputs"]["original_handoff_ref"] == handoff["source_ref"]
    assert obj["object"]["path"] is None and obj["native_reference"] == OBJECT_UUID


def test_results_metadata_can_inspect_original_input_without_claiming_task_output(driver):
    query = request()
    query["parameters"].update(input_source="fasta_file", input_fasta_file="/synthetic/work/existing.fa")
    del query["parameters"]["input_fasta_data"]
    query["input_bindings"] = [{"binding_id": "existing", "parameter_pointer": "/input_fasta_file",
        "kind": "workspace_object", "workspace_path": "/synthetic/work/existing.fa", "content": None,
        "inline_value": None, "link_evidence": None, "members": []}]
    driver.tree(query)
    results = driver.results(driver.launch_task())
    original = {"kind": "original_input", "input_binding_id": "existing"}
    row = metadata("/synthetic/work/existing.fa")["native_row"]
    row[7] = {"task_data": {"task_id": "earlier-input-producer", "app_id": "GenomeAssembly2"}}
    driver.client.value = [[row]]
    receipt = driver.call("workspace_metadata", {"objects": [original], "options": {}}, context=results)
    _, _, prepared = driver.bind("workspace_metadata", {"objects": [receipt_row(receipt)], "options": {}}, context=results)
    resolved = prepared["bound_inputs"]["resolved"]["objects"][0]
    assert resolved["native_reference"] == "/synthetic/work/existing.fa"
    assert resolved["task_association"] is None
    with pytest.raises(AppServiceInputError, match="output_association_missing"):
        driver.bind("download_capability", {"objects": [receipt_row(receipt)], "generation": 0,
            "predecessor_receipt_ref": None}, context=results)


def test_submission_input_metadata_can_follow_exact_prior_receipt_row(driver):
    query = request()
    query["parameters"].update(input_source="fasta_file", input_fasta_file="/synthetic/work/existing.fa")
    del query["parameters"]["input_fasta_data"]
    query["input_bindings"] = [{"binding_id": "existing", "parameter_pointer": "/input_fasta_file",
        "kind": "workspace_object", "workspace_path": "/synthetic/work/existing.fa", "content": None,
        "inline_value": None, "link_evidence": None, "members": []}]
    driver.tree(query)
    preparation = driver.call("prepare", {"definition": {"kind": "packaged", "required_application_id": "Homology"}})
    driver.client.value = [[metadata("/synthetic/work/existing.fa")["native_row"]]]
    first = driver.call("workspace_metadata", {"objects": [{"kind": "original_input", "input_binding_id": "existing"}], "options": {}})
    second = driver.call("workspace_metadata", {"objects": [receipt_row(first)], "options": {}})
    _, _, prepared = driver.bind("submit", {"preparation_receipt_ref": preparation["source_ref"], "input_evidence_refs": [second["source_ref"]]})
    assert prepared["native_operands"]["call"]["rpc_request"]["method"] == "AppService.start_app2"


@pytest.mark.parametrize("pointer", ["/rows/0", "/result/0/00", "/result/0/1"])
def test_native_row_pointer_is_exact_not_an_ordinal_guess(driver, pointer):
    query = request()
    obj = output_target(query)
    driver.tree(query)
    driver.client.value = [[metadata(query["parameters"]["output_path"], type="folder")["native_row"]]]
    receipt = driver.call("workspace_metadata", {"objects": [obj], "options": {}})
    with pytest.raises(AppServiceInputError, match="workspace_row_ambiguous"):
        driver.bind("workspace_metadata", {"objects": [receipt_row(receipt, pointer)], "options": {}})


def test_list_outputs_preserves_native_escaped_map_key_and_weak_association(driver):
    query = request()
    original = output_target(query)
    driver.tree(query)
    results = driver.results(driver.launch_task())
    key = query["parameters"]["output_path"]
    driver.client.value = {key: [metadata(key + "/a.json")["native_row"]]}
    listed = driver.call("list_outputs", {"objects": [original], "options": {}}, context=results)
    pointer = "/result/0/" + key.replace("~", "~0").replace("/", "~1") + "/0"
    assert listed["value"]["rows"][0]["pointer"] == pointer
    _, _, prepared = driver.bind("download_capability", {"objects": [receipt_row(listed, pointer)], "generation": 0,
        "predecessor_receipt_ref": None}, context=results)
    assoc = prepared["bound_inputs"]["resolved"]["objects"][0]["task_association"]
    assert assoc["kind"] == "unverified_original_path" and assoc["byte_version_status"] == "unknown"


def test_capability_alias_slot_and_exact_predecessor_survive_metadata(driver):
    query = request()
    original = output_target(query)
    driver.tree(query)
    results = driver.results(driver.launch_task())
    driver.client.value = ["https://download.example.invalid/capability0"]
    first = driver.call("download_capability", {"objects": [original], "generation": 0, "predecessor_receipt_ref": None}, context=results)
    driver.client.value = [[metadata(query["parameters"]["output_path"], type="folder")["native_row"]]]
    observed = driver.call("workspace_metadata", {"objects": [original], "options": {}}, context=results)
    _, key, same = driver.bind("download_capability", {"objects": [receipt_row(observed)], "generation": 0,
        "predecessor_receipt_ref": None}, context=results)
    with pytest.raises(EffectConflict):
        driver.api.selected_effects.reserve(results, key, same["effects"])
    _, _, next_generation = driver.bind("download_capability", {"objects": [receipt_row(observed)], "generation": 1,
        "predecessor_receipt_ref": first["source_ref"]}, context=results)
    refs = next_generation["bound_inputs"]["resolved"]["predecessor_effect_refs"]
    assert refs == first["value"]["receipt"]["effect_receipt_refs"]
    with pytest.raises(AppServiceInputError, match="capability_predecessor_conflict"):
        driver.bind("download_capability", {"objects": [receipt_row(observed)], "generation": 2,
            "predecessor_receipt_ref": first["source_ref"]}, context=results)


def test_selected_capability_download_matches_exact_object_and_keeps_null_url(driver):
    query = request()
    original = output_target(query)
    driver.tree(query)
    results = driver.results(driver.launch_task())
    driver.client.value = [None]
    capability = driver.call("download_capability", {"objects": [original], "generation": 0,
        "predecessor_receipt_ref": None}, context=results)
    args = download_args(original, {"kind": "acquired", "receipt_ref": capability["source_ref"], "input_index": 0})
    _, _, prepared = driver.bind("download", args, context=results)
    assert prepared["native_kind"] == "local_prepare"
    assert prepared["native_operands"]["local_failure"]["code"] == "capability_unavailable"
    assert prepared["bound_inputs"]["resolved"]["object"]["metadata"] is None


def test_unknown_capability_generation_uses_actual_possessed_failure_receipt(driver, monkeypatch):
    query = request()
    original = output_target(query)
    driver.tree(query)
    results = driver.results(driver.launch_task())
    def lost(_):
        raise AcquisitionError("synthetic_lost_reply", phase="transport")
    monkeypatch.setattr(driver.client, "rpc", lost)
    failed = driver.call("download_capability", {"objects": [original], "generation": 0,
        "predecessor_receipt_ref": None}, context=results, allow_failure=True)
    assert failed["contract"] == "CommonReceipt"
    refs = failed["value"]["effect_receipt_refs"]
    _, _, prepared = driver.bind("download_capability", {"objects": [original], "generation": 1,
        "predecessor_receipt_ref": failed["source_ref"]}, context=results)
    assert prepared["bound_inputs"]["resolved"]["predecessor_effect_refs"] == refs
    effect = driver.api.selected_effects.read(refs[0], original_job_owner=prepared["bound_inputs"]["original_job_owner"])
    assert effect["state"] == "issued_unknown"
    with pytest.raises(AppServiceInputError, match="capability_not_possessed"):
        driver.bind("download_capability", {"objects": [original], "generation": 1,
            "predecessor_receipt_ref": refs[0]}, context=results)


def test_same_fields_from_foreign_job_are_not_binding_evidence(driver):
    driver.tree()
    preparation = driver.call("prepare", {"definition": {"kind": "packaged", "required_application_id": "Homology"}})
    driver.saved.admit(driver.launch, driver.context, preparation["source_ref"])
    driver.saved.admit(driver.saved.root, driver.launch, preparation["source_ref"])
    other_launch, other = driver.saved.tree(launch_index=4)
    # Deliberate explicit delivery supplies possession but cannot change the
    # original scientific job owning the retained preparation.
    driver.saved.own(other, preparation["source_ref"], index=0)
    with pytest.raises(AppServiceInputError, match="original_task_mismatch"):
        driver.bind("submit", {"preparation_receipt_ref": preparation["source_ref"], "input_evidence_refs": []}, context=other)


def test_sibling_receipt_not_received_is_rejected(driver):
    driver.tree()
    preparation = driver.call("prepare", {"definition": {"kind": "packaged", "required_application_id": "Homology"}})
    sibling = driver.saved.child(driver.launch, "launch_api", api_assignment(), 1)
    with pytest.raises(ValueError, match="input_not_possessed"):
        driver.bind("submit", {"preparation_receipt_ref": preparation["source_ref"], "input_evidence_refs": []}, context=sibling)


def test_same_original_owner_does_not_allow_foreign_resource_receipt(driver):
    driver.tree()
    preparation = driver.call("prepare", {"definition": {"kind": "packaged", "required_application_id": "Homology"}})
    other = driver.saved.child(driver.launch, "launch_api", api_assignment(resource="second-api"), 1)
    assert driver.custody.original_job_owner(other) == driver.custody.original_job_owner(driver.context)
    driver.saved.own(other, preparation["source_ref"])
    with pytest.raises(AppServiceInputError, match="original_task_mismatch"):
        driver.bind("submit", {"preparation_receipt_ref": preparation["source_ref"], "input_evidence_refs": []}, context=other)


def test_preparation_bytes_must_still_exist_for_submission(driver):
    driver.tree()
    preparation = driver.call("prepare", {"definition": {"kind": "packaged", "required_application_id": "Homology"}})
    sha = preparation["value"]["definition_evidence"]["content"]["sha256"]
    (driver.store.path / "artifacts" / sha[:2] / sha).unlink()
    with pytest.raises(ValueError, match="input_bytes_unavailable"):
        driver.bind("submit", {"preparation_receipt_ref": preparation["source_ref"], "input_evidence_refs": []})


def test_manifest_consumer_without_callback_is_explicitly_unbound(driver):
    driver.tree()
    results = driver.results(driver.launch_task())
    source = driver.saved.source(b"{}")
    driver.saved.own(results, source["source_ref"])
    selected = {"kind": "manifest_member", "manifest_receipt_ref": source["source_ref"], "output_index": 0}
    with pytest.raises(AppServiceInputError, match="appservice_acquisition_reader_unbound") as error:
        driver.bind("workspace_metadata", {"objects": [selected], "options": {}}, context=results)
    assert validate_contract("Failure", error.value.failure)["effect_outcome"] == "not_sent"


def test_manifest_member_uses_actual_acquisition_and_exact_output_ordinal(driver):
    driver.tree()
    handoff = driver.launch_task()
    results = driver.results(handoff)
    info = driver.call("task_info", {"handoff_ref": handoff["source_ref"], "file": "job_result_id"}, context=results)
    driver.client.value = [[metadata("/synthetic/work/output/selected", type="job_result", size=None)["native_row"]]]
    observed = driver.call("workspace_metadata", {"objects": [{"kind": "task_info_object", "receipt_ref": info["source_ref"]}],
        "options": {}}, context=results)
    obj = receipt_row(observed)
    driver.client.value = ["https://download.example.invalid/manifest"]
    capability = driver.call("download_capability", {"objects": [obj], "generation": 0,
        "predecessor_receipt_ref": None}, context=results)
    args = download_args(obj, {"kind": "acquired", "receipt_ref": capability["source_ref"], "input_index": 0})
    member_uuid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    native = {"id": "123", "app": {"id": "Homology"}, "parameters": request()["parameters"],
        "output_files": [["/synthetic/work/output/result.json", member_uuid], ["malformed"]], "success": 0}
    driver.client.body = canonical(native).encode()
    acquisition = driver.acquire(args, context=results)
    driver.bindings = AppServiceInputs(driver.api, records=driver.records, custody=driver.custody,
                                      read_acquisition=driver.read_acquisition)
    selected = {"kind": "manifest_member", "manifest_receipt_ref": acquisition, "output_index": 0}
    _, _, prepared = driver.bind("workspace_metadata", {"objects": [selected], "options": {}}, context=results)
    row = prepared["bound_inputs"]["resolved"]["objects"][0]
    assert row["native_reference"] == native["output_files"][0][0]
    assert row["object"]["uuid"] == member_uuid and row["metadata"] is None
    assert row["task_association"]["pointer"] == "/output_files/0"
    assert row["task_association"]["byte_version_status"] == "unknown"
    with pytest.raises(AppServiceInputError, match="task_manifest_mismatch"):
        driver.bind("workspace_metadata", {"objects": [{**selected, "output_index": 1}], "options": {}}, context=results)
    for field, changed in (("id", "different-task"), ("app", {"id": "Variation"})):
        driver.client.body = canonical({**native, field: changed}).encode()
        wrong = driver.acquire(args, context=results)
        with pytest.raises(AppServiceInputError, match="task_manifest_mismatch"):
            driver.bind("workspace_metadata", {"objects": [{**selected, "manifest_receipt_ref": wrong}], "options": {}}, context=results)


def test_supplied_capability_uses_original_url_evidence_and_original_task(driver):
    query = request()
    original = output_target(query)
    driver.tree(query)
    handoff = driver.launch_task()
    binding = driver.saved.source(b'{"capability":"https://download.example.invalid/supplied"}')
    driver.saved.own(driver.saved.root, binding["source_ref"], index=3)
    selection = selector()
    association = {"kind": "unverified_original_path", "evidence_ref": None, "pointer": None,
        "task_id": "123", "output_path": query["parameters"]["output_path"], "output_uuid": None,
        "byte_version_status": "unknown", "version_evidence": []}
    selection["supplied_capabilities"] = [{"binding_id": "selected-url", "url_evidence": content(binding, pointer="/capability"),
        "original_handoff_ref": handoff["source_ref"], "object_selection": original, "task_association": association}]
    results = driver.results(handoff, selection=selection, index=4)
    _, _, prepared = driver.bind("download", download_args(original, {"kind": "supplied", "binding_id": "selected-url"}), context=results)
    entry = prepared["bound_inputs"]["resolved"]["capability"]["entry"]
    assert entry["url"] == "https://download.example.invalid/supplied"
    assert entry["expires_at"] is None and entry["expiry_evidence"] is None
    assert driver.client.calls[-1][1]["method"] == "AppService.start_app2"
    changed = deepcopy(selection)
    changed["supplied_capabilities"][0]["task_association"]["task_id"] = "other"
    other = driver.results(handoff, selection=changed, index=5)
    with pytest.raises(AppServiceInputError, match="original_task_mismatch"):
        driver.bind("download", download_args(original, {"kind": "supplied", "binding_id": "selected-url"}), context=other)


def test_duplicate_projected_pointer_is_rejected_even_with_actual_receipt(driver):
    query = request()
    original = output_target(query)
    driver.tree(query)
    driver.client.value = [[metadata(query["parameters"]["output_path"], type="folder")["native_row"]]]
    def duplicate(record):
        record["value"]["rows"].append(deepcopy(record["value"]["rows"][0]))
        return record
    driver.receipt_transform = duplicate
    observed = driver.call("workspace_metadata", {"objects": [original], "options": {}})
    with pytest.raises(AppServiceInputError, match="workspace_row_ambiguous"):
        driver.bind("workspace_metadata", {"objects": [receipt_row(observed)], "options": {}})


def test_workspace_task_metadata_cannot_override_original_task(driver):
    query = request()
    original = output_target(query)
    driver.tree(query)
    results = driver.results(driver.launch_task())
    row = metadata(query["parameters"]["output_path"], type="folder")["native_row"]
    row[7] = {"task_data": {"task_id": "different", "app_id": "Homology"}}
    driver.client.value = [[row]]
    observed = driver.call("workspace_metadata", {"objects": [original], "options": {}}, context=results)
    with pytest.raises(AppServiceInputError, match="task_manifest_mismatch"):
        driver.bind("download_capability", {"objects": [receipt_row(observed)], "generation": 0,
            "predecessor_receipt_ref": None}, context=results)


@pytest.mark.parametrize("mismatch", [False, True])
def test_original_supplied_link_content_is_exact_and_never_downloaded(driver, mismatch):
    binding = driver.saved.source(b'{"url":"https://input.example.invalid/original"}')
    driver.saved.own(driver.saved.root, binding["source_ref"])
    query = request()
    query["parameters"]["link"] = "https://input.example.invalid/changed" if mismatch else "https://input.example.invalid/original"
    query["input_bindings"] = [{"binding_id": "link", "parameter_pointer": "/link", "kind": "supplied_link",
        "inline_value": query["parameters"]["link"], "workspace_path": None, "content": None,
        "link_evidence": content(binding, pointer="/url"), "members": []}]
    query["workspace_targets"] = [{"target_id": "link", "path": "/synthetic/work/from-link", "type": "contigs",
        "purpose": "input", "input_binding_id": "link", "metadata": {}, "allow_overwrite": False, "allow_create_parents": True}]
    driver.tree(query)
    args = {"objects": [{"target_id": "link", "data_binding_id": "link", "creation_time": None}], "options": {"downloadFromLinks": 1}}
    if mismatch:
        with pytest.raises(AppServiceInputError, match="input_bytes_mismatch"):
            driver.bind("workspace_create", args)
    else:
        _, _, prepared = driver.bind("workspace_create", args)
        assert prepared["native_operands"]["call"]["rpc_request"]["params"][0]["objects"][0][3] == query["parameters"]["link"]
    assert driver.client.calls == []
