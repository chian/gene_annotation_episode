"""Original FASTA transfer through real Workflow ownership and typed returns.

The decisions, parent/preparation continuation, and three native responses are
explicit synthetic fixtures. Parsing, custody, selected effects, receipts,
practical endpoint proof, ordinary operational continuation, and returns run
their production implementations. No model, network, or BLAST program runs.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest
from method_loop.archive import iter_json

from gene_annotation_episode.api_bvbrc_appservice import BVBRCAppServiceService
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_api_bvbrc_appservice import CONFIG, PREFIX, OBJECT_UUID, SHOCK_UUID, metadata
from test_bvbrc_appservice_custody import request
from test_bvbrc_appservice_inputs import NativeClient
from test_execution_episodes_family import launch_assignment
from test_execution_wiring import child, form
from test_practical_runtime import selected
from test_public_search import Client


FASTA = b">synthetic-query supplied transfer fixture\r\nacgtACGT\r\nNNtt\r\n"
REQUESTED_PATH = "/synthetic//work/input.fa"
RETURNED_PATH = "/synthetic/work/input.fa"
NODE_URL = "https://shock.example.invalid/node/" + SHOCK_UUID
FILENAME = "original-synthetic-query.fa"
TASK_ID = "225123"
RUN_ID = "appservice-transfer-shared-workflow"
GOAL = "Transfer the supplied synthetic FASTA and return the original Homology task handoff"
TABLES = ("runtime_actions", "runtime_model_calls", "runtime_observations",
    "runtime_estimation_contexts", "runtime_forms", "runtime_report_attempts",
    "runtime_record_receipts", "runtime_episodes")


def _controllers(path, initial):
    def parent_preparation_estimate(history, parameters, contexts):
        count = 2 if path[-1][0] == "annotation" else 1
        return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= count else 1),
            parameters, {"fixture": "parent_and_input_preparation_continuation_only"})
    return YieldController(str(path), initial, 0, YieldParameters(100, 50),
        estimate_with_context=parent_preparation_estimate
        if path[-1][0] in {"annotation", "improvement"} else None)


def _workflow(store, directory, provider, configuration):
    factory = ExecutionServiceFactory.from_record(configuration["factory"])
    return Workflow(store, ToolRegistry(store, clients=Client()), provider, directory / "run", RUN_ID,
        controller_factory=_controllers, project_credit=lambda *_: 0,
        episode_service_factory=factory, episode_service_binding=factory.as_record(),
        episode_service_inputs="actual_tool_registry_v1", annotation_child_roles=("improvement", "launch"),
        episode_record_receipts=True, initial_known_record_refs=[])


async def _run(episode, workflow):
    record = await episode.run_async(workflow.context)
    await episode.build_result(record)
    return json.loads("".join(iter_json(record.as_record())))


def _rows(store, table):
    return [dict(row) for row in store.db.execute("SELECT * FROM " + table + " WHERE run_id=? ORDER BY rowid", (RUN_ID,))]


def _read_json(path):
    return json.loads(path.read_text())


def _forbidden(*args, **kwargs):
    raise AssertionError("transfer fixture attempted live transport or repeated native work")


@pytest.fixture(scope="module")
def transfer_run(tmp_path_factory):
    directory = tmp_path_factory.mktemp("bvbrc-appservice-transfer-workflow")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("socket.create_connection", _forbidden)
        patch.setattr("socket.socket.connect", _forbidden)
        patch.setattr("socket.socket.connect_ex", _forbidden)
        patch.setattr("urllib.request.OpenerDirector.open", _forbidden)
        with Store(directory / "state") as store:
            target, = store.create_problem(raw_sequence="ACGTACGTNNTT", molecule="dna")["subject_refs"]
            scope = {"subject_refs": [target]}
            material = store.register_material(data=FASTA, name=FILENAME,
                format="fasta", molecule="dna", use="evidence")
            source = store.get(material["source_ref"])
            content = {"source_ref": source["id"], "artifact_field": "artifact_ref",
                "artifact_ref": source["artifact_ref"], "sha256": hashlib.sha256(FASTA).hexdigest(),
                "byte_count": len(FASTA)}
            original = request()
            original["parameters"].update(input_source="fasta_file", input_fasta_file=REQUESTED_PATH)
            del original["parameters"]["input_fasta_data"]
            original["start_parameters"] = {"parent_id": "synthetic-parent-225"}
            original["input_bindings"] = [{"binding_id": "query", "parameter_pointer": "/input_fasta_file",
                "kind": "retained_bytes", "content": content, "workspace_path": REQUESTED_PATH,
                "inline_value": None, "link_evidence": None, "members": []}]
            original["workspace_targets"] = [{"target_id": "query", "path": REQUESTED_PATH,
                "type": "contigs", "purpose": "input", "input_binding_id": "query",
                "metadata": {"fixture": "synthetic transfer only"}, "allow_overwrite": False,
                "allow_create_parents": True}]
            assignment = {"version": "api_service_assignment_v1", "resource_id": "selected-api",
                "service": "bvbrc_appservice", "request": original, "endpoint": "usable_handoff",
                "constraints": {"allowed_resource_ids": ["selected-api"], "allowed_kinds": ["api"]}}
            launch = launch_assignment({"selected-api": assignment}, constraints={
                "allowed_resource_ids": ["selected-api"], "allowed_kinds": ["api"]})
            handoff_form = form("execution_handoff_refs")
            handoff_form["properties"]["support"] = {"type": "array", "uniqueItems": True,
                "items": {"type": "string", "format": "reference", "x-reference-namespace": "bvbrc_appservice_support"},
                "x-source": "bvbrc_appservice_support_refs"}
            handoff_form["required"].append("support")
            factory = ExecutionServiceFactory({"selected-api": deepcopy(CONFIG)}, {}, 2, 3, .5)
            configuration = {"factory": factory.as_record(), "scope": scope, "goal": GOAL,
                "initial_known_record_refs": [], "assignment": assignment, "launch": launch,
                "handoff_form": handoff_form, "material": material, "content": content,
                "fixture": "Synthetic FASTA/native replies/scripted decisions; no algorithm, model, or live service"}
            (directory / "fixture-configuration.json").write_text(json.dumps(configuration, indent=2) + "\n")

            class Responses(NativeClient):
                def rpc(self, command):
                    if command["method"] == "Workspace.create":
                        assert command["params"] == [{"objects": [[REQUESTED_PATH, "contigs",
                            original["workspace_targets"][0]["metadata"], None, None]], "createUploadNodes": 1}]
                        self.value = [metadata(RETURNED_PATH, shock_url=NODE_URL)["native_row"]]
                    elif command["method"] == "AppService.start_app2":
                        assert command["params"] == ["Homology", original["parameters"], original["start_parameters"]]
                        self.value = {"id": TASK_ID, "application_id": "Homology", "state_code": "Q",
                            "parameters": deepcopy(original["parameters"]),
                            "start_parameters": deepcopy(original["start_parameters"])}
                    else:
                        raise AssertionError(command)
                    return super().rpc(command)

                def upload(self, url, supplied, *, filename):
                    assert (url, supplied, filename) == (NODE_URL, FASTA, FILENAME)
                    return super().upload(url, supplied, filename=filename)

                task_info = download = _forbidden

            native = Responses()
            constructor = BVBRCAppServiceService.__init__

            def configured(self, *args, **kwargs):
                constructor(self, *args, **kwargs)
                self.client = native

            patch.setattr(BVBRCAppServiceService, "__init__", configured)

            class Choices:
                def __init__(self):
                    self.counts, self.support_refs, self.before_failure = {}, [], None
                    self.failure = None

                def last(self, episode_id):
                    row = store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? "
                        "AND result IS NOT NULL ORDER BY decision_index DESC LIMIT 1", (RUN_ID, episode_id)).fetchone()
                    return json.loads(row["result"])

                async def complete(self, episode_id, role, instructions, current, schema):
                    self.counts[episode_id] = count = self.counts.get(episode_id, 0) + 1
                    execution = current.get("execution_assignment", {})
                    version = execution.get("version")
                    if version == "api_service_assignment_v1":
                        context = api.appservice.custody.context(episode_id)
                        if count == 5:
                            # An authentic upload receipt is deliberately presented
                            # as a preparation receipt at the actual selected boundary.
                            self.failure = deepcopy(current["feedback"])
                            assert self.failure["code"] == "appservice_receipt_contract_conflict"
                            assert native.calls == self.before_failure["calls"]
                            assert _rows(store, "runtime_observations") == self.before_failure["observations"]
                            assert store.count("source") == self.before_failure["source_count"]
                            assert api._completion(context) is None
                            assert [api.appservice.records.read(ref) for ref in self.support_refs] == self.before_failure["receipts"]
                            return selected(PREFIX + "submit", {"preparation_receipt_ref": self.support_refs[0],
                                "input_evidence_refs": [self.support_refs[2]]})
                        assert current.get("feedback") is None, current.get("feedback")
                        if count == 1:
                            assert api.appservice.custody.content(context, content) == FASTA
                            assert api.appservice.custody.possession(context, content["source_ref"]) == "parent_assignment"
                            return selected(PREFIX + "prepare", {"definition": {
                                "kind": "packaged", "required_application_id": "Homology"}})
                        self.support_refs.append(self.last(episode_id)["result"]["support_receipt_ref"])
                        assert api._completion(context) is None
                        assert api.facts(context, {})["execution_handoff_refs"] == []
                        assert api.facts(context, {})["execution_result_refs"] == []
                        if count == 2:
                            assert native.calls == []
                            return selected(PREFIX + "workspace_create", {"objects": [{"target_id": "query",
                                "data_binding_id": "query", "creation_time": None}], "options": {"createUploadNodes": 1}})
                        if count == 3:
                            return selected(PREFIX + "upload", {"created_object": {
                                "receipt_ref": self.support_refs[1], "row_pointer": "/result/0/0"},
                                "input_binding_id": "query", "filename": FILENAME})
                        assert count == 4
                        self.before_failure = {"calls": deepcopy(native.calls),
                            "observations": _rows(store, "runtime_observations"),
                            "source_count": store.count("source"),
                            "receipts": [api.appservice.records.read(ref) for ref in self.support_refs]}
                        return selected(PREFIX + "submit", {"preparation_receipt_ref": self.support_refs[2],
                            "input_evidence_refs": [self.support_refs[2]]})
                    assert current.get("feedback") is None, current.get("feedback")
                    if version == "execution_launch_assignment_v1":
                        assert count == 1
                        return child("launch_api", assignment, scope, handoff_form)
                    if episode_id != episode.source.episode_id:
                        assert count == 1
                        return selected("material.parse", {"material_ref": material["id"], "format": "fasta"})
                    if count == 1:
                        with pytest.raises(ValueError, match="input_not_possessed"):
                            api.appservice.custody.possession(workflow.binding_context(episode.source), content["source_ref"])
                        return {"selection": {"kind": "child", "goal": "Parse the supplied synthetic FASTA unchanged",
                            "scope": scope, "purpose": "Return actual retained input-source references",
                            "schema_json": json.dumps({"type": "object", "properties": {"refs": {
                                "type": "array", "items": {"type": "string", "format": "reference"},
                                "x-source": "committed_record_refs"}}, "required": ["refs"], "additionalProperties": False}),
                            "initial_report_json": "{}"}, "report_update": {}}
                    assert count == 2
                    assert content["source_ref"] in current["child_reports"][-1]["refs"]
                    assert api.appservice.custody.possession(workflow.binding_context(episode.source), content["source_ref"]) == "admitted_return"
                    return child("launch", launch, scope, handoff_form)

                async def release(self, episode_id):
                    pass

            choices = Choices()
            workflow = _workflow(store, directory, choices, configuration)
            api = workflow.episode_bindings.for_role("launch_api").api_execution
            episode = workflow.build("annotation", "root", GOAL, scope)
            archive = asyncio.run(_run(episode, workflow))
            preparation = archive["units"][0]["child"]
            launch_record = archive["units"][1]["child"]
            api_record = launch_record["units"][0]["child"]
            returned = json.loads(workflow.journal.row("runtime_forms", launch_record["episode_id"])["form"])
            handoff_ref, = returned["references"]
            receipts = [api.appservice.records.read(ref) for ref in [*choices.support_refs, handoff_ref]]
            summary = {"configuration": configuration, "archive": archive, "returned": returned,
                "api_returned": json.loads(workflow.journal.row("runtime_forms", api_record["episode_id"])["form"]),
                "counts": choices.counts, "failure": choices.failure, "receipts": receipts,
                "tables": {table: _rows(store, table) for table in TABLES},
                "native_calls": [{"kind": call[0], "rpc": call[1]} if call[0] == "rpc" else {
                    "kind": "upload", "url": call[1], "hex": call[2].hex(), "byte_count": len(call[2]),
                    "sha256": hashlib.sha256(call[2]).hexdigest(), "filename": call[3]} for call in native.calls]}
            (directory / "verified-records.json").write_text(json.dumps(summary, indent=2) + "\n")
            run = SimpleNamespace(directory=directory, configuration=configuration, archive=archive,
                preparation=preparation, launch=launch_record, api_record=api_record, returned=returned,
                summary=summary, receipts=receipts, native=native, handoff_ref=handoff_ref)
        yield run
        export = os.environ.get("BVBRC_TRANSFER_VERIFICATION_EXPORT")
        if export:
            # Opt-in engineering evidence export, after all Stores have closed.
            # A new destination is required; an earlier receipt is never replaced.
            shutil.copytree(directory, Path(export) / "retained-run")


def test_original_fasta_bytes_create_target_and_selected_upload_are_retained(transfer_run):
    run = transfer_run
    original = run.configuration["assignment"]["request"]
    content = run.configuration["content"]
    preparation, create, upload, handoff = run.receipts
    assert [row["contract"] for row in run.receipts] == ["PreparationReceipt", "WorkspaceReceipt", "UploadReceipt", "TaskHandoff"]
    assert preparation["value"]["native_parameters"] == original["parameters"]
    assert create["value"]["requested_objects"] == [{"kind": "original_target", "target_id": "query"}]
    row, = create["value"]["rows"]
    assert (row["pointer"], row["path"], row["uuid"], row["shock_url"], row["valid"]) == (
        "/result/0/0", RETURNED_PATH, OBJECT_UUID, NODE_URL, True)
    value = upload["value"]
    assert value["input_content"] == content
    assert value["create_receipt_ref"] == create["source_ref"]
    assert value["created_object"] == {"path": RETURNED_PATH, "uuid": OBJECT_UUID,
        "type": "contigs", "metadata_receipt_ref": create["source_ref"]}
    assert value["shock_node_id"] == value["observed_node_id"] == SHOCK_UUID
    assert value["filename"] == FILENAME
    assert value["observed_file_size"] == len(FASTA)
    assert value["observed_checksums"]["sha256"] == hashlib.sha256(FASTA).hexdigest()
    assert value["confirmation"] == "accepted_bytes_match"
    assert [call[0] for call in run.native.calls] == ["rpc", "upload", "rpc"]
    assert run.native.calls[1] == ("upload", NODE_URL, FASTA, FILENAME)
    with Store(run.directory / "state") as store:
        assert store.get_artifact(content["artifact_ref"]) == FASTA
        assert store.get(content["source_ref"])["artifact_ref"] == content["artifact_ref"]
        parse_action, = [row for row in run.summary["tables"]["runtime_actions"]
            if json.loads(row["action"]).get("tool") == "material.parse"]
        parse = json.loads(parse_action["result"])["result"]["parse_attempt"]
        assert parse["source_ref"] == content["source_ref"]
        assert parse["status"] == "completed" and parse["valid_records"] == 1
        assert store.get(parse["collection_ref"])["sequence_symbols"] == 12
        assert store.count("annotation") == 0


def test_typed_receipts_reach_parent_and_only_original_submission_completes(transfer_run):
    run = transfer_run
    assert run.returned["completed"] is True
    assert run.returned["support"] == [row["source_ref"] for row in run.receipts[:3]]
    assert {key: run.summary["api_returned"][key] for key in ("completed", "references", "support")} == {
        key: run.returned[key] for key in ("completed", "references", "support")}
    handoff = run.receipts[-1]["value"]
    task = handoff["original_task"]
    assert task["task_id"] == TASK_ID and task["resource_id"] == "selected-api"
    assert task["submitted_parameters"] == run.configuration["assignment"]["request"]["parameters"]
    assert task["submitted_start_parameters"] == {"parent_id": "synthetic-parent-225"}
    assert handoff["input_evidence_refs"] == [run.receipts[2]["source_ref"]]
    assert task["submission_operation_key"].endswith(":4")
    assert handoff["receipt"]["origin"]["name"] == PREFIX + "submit"
    assert task["submission_source_ref"] == handoff["receipt"]["snapshot"]["source_ref"]
    with Store(run.directory / "state") as store:
        workflow = _workflow(store, run.directory, SimpleNamespace(complete=_forbidden, release=_forbidden), run.configuration)
        api = workflow.episode_bindings.for_role("launch_api").api_execution
        context = api.appservice.custody.context(run.api_record["episode_id"])
        root = api.appservice.custody.context(run.archive["episode_id"])
        assert all(api.appservice.custody.possession(root, row["source_ref"]) == "admitted_return" for row in run.receipts)
        assert all(api.appservice.resolve(root, row["source_ref"], "bvbrc_appservice_support") for row in run.receipts[:3])
        assert all(not api.is_handoff_source(row["source_ref"]) for row in run.receipts[:3])
        target = api.read_target(run.handoff_ref, run.configuration["scope"])
        assert target["execution_id"] == TASK_ID
        assert api._submission_snapshot(target).request["rpc"]["method"] == "AppService.start_app2"
        proof = api._completion(context)
        assert api.verify_completion(context, proof)
        assert proof["operation_key"] == task["submission_operation_key"]
        effects = [api.selected_effects.read(row["value"]["receipt"]["effect_receipt_refs"][0],
            original_job_owner=handoff["original_job_owner"]) for row in run.receipts[1:]]
        assert [row["descriptor"]["kind"] for row in effects] == ["workspace_create", "shock_upload", "appservice_submit"]
        assert all(row["state"] == "confirmed" for row in effects)
        assert all(row["descriptor"]["original_job_owner"] == handoff["original_job_owner"]
            and row["descriptor"]["resource_id"] == "selected-api" for row in effects)
        assert effects[0]["native_effect_identifiers"]["target_path"] == REQUESTED_PATH
        assert effects[0]["native_effect_identifiers"]["workspace_path"] == RETURNED_PATH
        assert effects[0]["native_effect_identifiers"]["workspace_uuid"] == OBJECT_UUID
        assert effects[0]["native_effect_identifiers"]["shock_url"] == NODE_URL
        assert effects[1]["descriptor"]["slot"]["shock_node_id"] == SHOCK_UUID
        assert effects[1]["native_effect_identifiers"]["file_size"] == len(FASTA)
        assert effects[2]["native_effect_identifiers"]["task_id"] == TASK_ID
    assert run.archive["units_consumed"] == 2
    assert run.preparation["units_consumed"] == run.launch["units_consumed"] == 1
    assert run.api_record["units_consumed"] == 4
    assert [unit["controller_step"]["marginal_credit"] for unit in run.api_record["units"]] == [0, 0, 0, 2]
    for closed in (run.api_record, run.launch):
        assert closed["controller_state"]["estimate"]["expected_next_gain"] == NumericBand.exact(0).as_record()
        assert closed["units"][-1]["controller_step"]["marginal_credit"] == 2
    rows = run.summary["tables"]
    assert len(rows["runtime_observations"]) == 8
    assert len(rows["runtime_model_calls"]) == 9
    assert {row["purpose"] for row in rows["runtime_model_calls"]} == {"decision"}
    assert all(row["failure"] is None for row in rows["runtime_report_attempts"])
    observed = {(row["episode_id"], json.loads(row["observation"])["decision_index"])
        for row in rows["runtime_observations"]}
    completed = {(row["episode_id"], row["decision_index"]) for row in rows["runtime_actions"]
        if row["result"] is not None and json.loads(row["result"])["status"] in {"completed", "partial"}}
    assert observed == completed and len(observed) == len(rows["runtime_observations"])
    for row in rows["runtime_actions"]:
        action = json.loads(row["action"])
        if action.get("tool", "").startswith(PREFIX):
            assert row["episode_id"] == run.api_record["episode_id"]
        elif action.get("tool") == "material.parse":
            assert row["episode_id"] == run.preparation["episode_id"]
        call, = [item for item in rows["runtime_model_calls"] if
            (item["episode_id"], item["call_index"]) == (row["episode_id"], row["decision_index"])]
        assert action == json.loads(call["response"])["selection"]


def test_wrong_kind_receipt_fails_before_submission_without_progress(transfer_run):
    run = transfer_run
    actions = [row for row in run.summary["tables"]["runtime_actions"] if row["episode_id"] == run.api_record["episode_id"]]
    assert len(actions) == 5
    invalid, final = actions[3:]
    failure = json.loads(invalid["result"])
    assert failure["status"] == "invalid" and invalid["credit"] is None
    assert failure["feedback"]["code"] == "appservice_receipt_contract_conflict"
    assert failure["record_refs"] == failure["changed_record_refs"] == [] and failure["result"] is None
    assert run.summary["failure"]["code"] == failure["feedback"]["code"]
    assert json.loads(final["result"])["status"] == "completed"
    observed = [json.loads(row["observation"]) for row in run.summary["tables"]["runtime_observations"]
        if row["episode_id"] == run.api_record["episode_id"]]
    assert [row["decision_index"] for row in observed] == [0, 1, 2, 4]
    assert run.summary["counts"][run.api_record["episode_id"]] == 5
    assert sum(call[0] == "rpc" and call[1]["method"] == "AppService.start_app2" for call in run.native.calls) == 1


def test_reopened_store_and_workflow_replay_preserve_original_closed_records(transfer_run, monkeypatch):
    run = transfer_run
    monkeypatch.setattr(run.native, "rpc", _forbidden)
    monkeypatch.setattr(run.native, "upload", _forbidden)
    monkeypatch.setattr(run.native, "task_info", _forbidden)
    monkeypatch.setattr(run.native, "download", _forbidden)

    class NoNewDecisions:
        async def complete(self, *args, **kwargs):
            raise AssertionError("closed Workflow replay requested a new model decision")

        async def release(self, episode_id):
            pass

    configuration = _read_json(run.directory / "fixture-configuration.json")
    with Store(run.directory / "state") as store:
        before = {table: _rows(store, table) for table in TABLES}
        retained = {str(path.relative_to(run.directory)): path.read_bytes()
            for path in (run.directory / "run").rglob("*.json")}
        workflow = _workflow(store, run.directory, NoNewDecisions(), configuration)
        api = workflow.episode_bindings.for_role("launch_api").api_execution
        context = api.appservice.custody.context(run.api_record["episode_id"])
        for row in before["runtime_actions"]:
            if row["episode_id"] != context.episode_id or row["credit"] is None:
                continue
            selection = json.loads(row["action"])
            key = f"{RUN_ID}:{context.episode_id}:{row['decision_index']}"
            directory = api._manifest(context, create=False) / "actions" / digest(key)
            executor_outcome = _read_json(directory / "outcome.json")
            runtime_outcome = json.loads(row["result"])
            assert runtime_outcome == {**executor_outcome,
                "pending_work_after_action": runtime_outcome["pending_work_after_action"]}
            assert asyncio.run(api.execute(context, selection["tool"], selection["arguments"], key)) == executor_outcome
            assert dict(workflow.journal.row("runtime_actions", context.episode_id, row["decision_index"])) == row
        episode = workflow.build("annotation", "root", configuration["goal"], configuration["scope"])
        replay = asyncio.run(_run(episode, workflow))
        assert replay == run.archive
        assert {table: _rows(store, table) for table in TABLES} == before == run.summary["tables"]
        assert {str(path.relative_to(run.directory)): path.read_bytes()
            for path in (run.directory / "run").rglob("*.json")} == retained
        assert [api.appservice.records.read(row["source_ref"]) for row in run.receipts] == run.receipts
        assert store.get_artifact(configuration["content"]["artifact_ref"]) == FASTA
    (run.directory / "replay-verification.json").write_text(json.dumps({
        "reopened_store": True, "factory_reconstructed_from_saved_configuration": True,
        "closed_workflow_replayed": True, "new_native_calls": 0, "new_decisions": 0,
        "closed_archive_unchanged": True, "tables_unchanged": list(TABLES)}, indent=2) + "\n")
