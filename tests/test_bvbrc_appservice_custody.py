"""Read-only AppService custody, with real Store/Journal and return shapes.

Most cases deliberately construct saved selections using the production goal,
contract and receipt classes. One case runs the existing shared Workflow with
a synthetic native Data response to check actual commission/return shapes.
Neither kind of check claims an AppService native invocation or live service.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json

import pytest

from method_loop.episode import EpisodeGoal, EpisodeRequest
from method_loop.identities import EpisodeRef

from gene_annotation_episode.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.bvbrc_appservice_custody import AppServiceCustody, AppServiceCustodyError
from gene_annotation_episode.bvbrc_application_definitions import get_application_spec, prepare_application
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.runtime import Record, TypedReportContract
from gene_annotation_episode.state import Store


def refs_schema(namespace="source"):
    return {"type": "object", "properties": {"refs": {"type": "array", "items": {
        "type": "string", "format": "reference", "x-reference-namespace": namespace},
        "x-source": "committed_record_refs"}}, "required": ["refs"], "additionalProperties": False}


def request():
    return {"version": "bvbrc_appservice_request_v1", "effect_contract": "selected_api_effects_v1",
        "required_application_id": "Homology", "parameters": {
            "output_path": "/synthetic/work/output", "output_file": "selected", "input_type": "dna",
            "input_source": "fasta_data", "input_fasta_data": ">q\nACGT\n", "db_type": "fna",
            "db_source": "fasta_data", "db_fasta_data": ">s\nACGA\n", "blast_program": "blastn", "blast_max_hits": 2},
        "start_parameters": {}, "definition_inputs": [], "input_bindings": [], "workspace_targets": []}


def api_assignment(query=None, resource="selected-api"):
    return {"version": "api_service_assignment_v1", "service": "bvbrc_appservice", "resource_id": resource,
        "endpoint": "usable_handoff", "request": request() if query is None else deepcopy(query), "constraints": {}}


def launch_assignment(query=None):
    return {"version": "execution_launch_assignment_v1", "requests": {
        "selected-api": api_assignment(query), "second-api": api_assignment(query, "second-api")},
        "immutable_input_versions": [], "constraints": {"allowed_kinds": ["api"]}}


def selector():
    return {"version": "bvbrc_appservice_result_selector_v1", "endpoint": "requested_artifacts",
        "requirements": [{"requirement_id": "native", "role": "native_output", "required": True,
            "declared_format": {"format": "json", "version": None, "mode": None,
                "producer_source_ref": None, "transformation_evidence": []},
            "producer_rule_evidence": None, "exact_object": None}], "adapter": None,
        "requested_schema": refs_schema(), "supplied_metadata": [], "supplied_capabilities": []}


def content(binding, *, pointer=""):
    return {"content": deepcopy(binding), "pointer": pointer}


class SavedRecords:
    """Controlled historical records; no fake transport response is a measurement."""

    def __init__(self, store, *, manifest_path=None):
        self.store, self.run_id = store, "appservice-custody-fixture"
        self.journal = Journal(store, self.run_id)
        if manifest_path is None:
            self.scope = {"subject_refs": store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]}
        else:
            self.scope = {"subject_refs": store.create_problem(manifest_path=manifest_path)["subject_refs"]}
        self.receipts = EpisodeReceipts(store, self.run_id)
        self.custody = AppServiceCustody(store, self.run_id)
        goal = EpisodeGoal.root(objective="Test exact input custody", result_contract={"role": "annotation"})
        self.root = self.save_context("annotation", (("annotation", "root"),), {}, goal, None)

    def save_context(self, role, path, assignment, goal, contract, *, parent=None, save=True):
        episode_id = EpisodeRef(self.run_id, path).episode_id
        inherited = self.receipts.bind(episode_id, None if parent is None else parent.episode_id)
        message = {"scope": deepcopy(self.scope), "initial_report": {}, "episode_assignment": deepcopy(assignment),
            "knowledge_inheritance": inherited}
        req = EpisodeRequest(goal, Record(message), contract).as_record()
        ctx = BindingContext(self.run_id, episode_id, role, path, self.scope, assignment, req)
        if save:
            self.journal.save("runtime_episodes", {"episode_id": episode_id, "path": canonical(path),
                "request": canonical(req), "initial_credit": 0, "state": "active", "completion": None, "archive": None})
        return ctx

    def child(self, parent, role, assignment, index, *, schema=None, save=True, action=True, model=True, encoded=False):
        schema = refs_schema() if schema is None else schema
        contract = TypedReportContract("Return only the requested source references", schema, lambda *_: True)
        goal = EpisodeGoal.child(EpisodeGoal.from_record(plain(parent.request)["goal"]),
                                objective="Perform selected fixture work", result_contract=schema)
        path = (*parent.path, (role, "child_" + str(index)))
        ctx = self.save_context(role, path, assignment, goal, contract, parent=parent, save=save)
        selection = {"kind": "episode_child", "role": role, "assignment": deepcopy(assignment),
            "scope": deepcopy(self.scope), "goal": "Perform selected fixture work",
            "purpose": contract.decision, "schema_json": canonical(schema), "initial_report_json": "{}"}
        if model:
            response = {"selection": deepcopy(selection), "report_update": {}}
            if encoded:
                response["selection"]["assignment"] = canonical(assignment)
            original_schema = {"type": "object", "properties": {"selection": {"type": "object",
                "properties": {"kind": {"const": "episode_child"}, "assignment": {"type": "object"}},
                "required": list(selection)}}}
            self.journal.save("runtime_model_calls", {"episode_id": parent.episode_id, "call_index": index,
                "purpose": "decision", "request": canonical({"context": {}, "schema": original_schema}),
                "response": canonical(response)})
        if action:
            self.journal.save("runtime_actions", {"episode_id": parent.episode_id, "decision_index": index,
                "action": canonical(selection), "result": None, "credit": None})
        return ctx

    def source(self, raw=b'{"native": [0, 1.25]}', **fields):
        artifact = self.store.artifact(raw, "application/json")
        source = self.store.put("source", {"provider": "custody.fixture", "accession": None, "uri": None,
            "artifact_ref": artifact, "text_ref": artifact, "request_ref": None, "version": None,
            "retrieved_at": "2026-10-24T00:00:00+00:00", **fields}, origin="tool")
        return {"source_ref": source["id"], "artifact_field": "artifact_ref", "artifact_ref": artifact,
                "sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw)}

    def own(self, context, reference, index=0, *, status="completed", tool="source.inspect"):
        result = {"status": status, "record_refs": [reference], "changed_record_refs": [reference], "result": {}}
        self.journal.save("runtime_actions", {"episode_id": context.episode_id, "decision_index": index,
            "action": canonical({"kind": "tool", "tool": tool, "arguments": {}}),
            "result": canonical(result), "credit": None})
        if status in {"completed", "partial"}:
            self.receipts.receive(context.episode_id, [reference], kind="own_action", source_index=index)
        return result

    def admit(self, parent, child, reference):
        index = int(child.path[-1][1][6:])
        contract = plain(child.request)["report_contract"]
        form = {"refs": [reference]}
        self.journal.save("runtime_forms", {"episode_id": child.episode_id,
            "facts": canonical({"committed_record_refs": [reference]}), "form": canonical(form)})
        self.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id,
            "decision_index": index, "delivery_ref": "delivery_" + digest([parent.episode_id, index])[:24],
            "child_episode_id": child.episode_id, "contract": canonical(contract), "form": canonical(form), "failure": None})
        self.receipts.receive(parent.episode_id, [reference], kind="child_form", source_index=index)
        return form

    def supplied_request(self, binding):
        query = request()
        query["definition_inputs"] = [{"binding_id": "original-definition", "evidence": content(binding)}]
        return query

    def tree(self, query=None, *, launch_index=2):
        launch = self.child(self.root, "launch", launch_assignment(query), launch_index)
        # This is exactly the initial delivery performed by Workflow.build.
        self.receipts.receive(launch.episode_id, self.custody.initial_references(launch), kind="initial")
        api = self.child(launch, "launch_api", api_assignment(query), 0)
        return launch, api


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("custody verification attempted a network request")
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", forbidden)


@pytest.fixture
def saved(tmp_path):
    with Store(tmp_path / "state") as store:
        yield SavedRecords(store)


def test_exact_own_completed_action_and_before_index(saved):
    binding = saved.source()
    ref = binding["source_ref"]
    with pytest.raises(AppServiceCustodyError, match="input_not_possessed"):
        saved.custody.possession(saved.root, ref)
    saved.own(saved.root, ref, 1)
    assert saved.custody.possession(saved.root, ref, before=2) == "own_completed_action"
    with pytest.raises(AppServiceCustodyError, match="input_not_possessed"):
        saved.custody.possession(saved.root, ref, before=1)
    assert saved.custody.content(saved.root, binding) == b'{"native": [0, 1.25]}'


@pytest.mark.parametrize("before", [True, False, 1.0, -1, "2"])
def test_before_index_has_exact_integer_type(saved, before):
    with pytest.raises(AppServiceCustodyError, match="before_index_invalid"):
        saved.custody.possession(saved.root, saved.source()["source_ref"], before=before)


@pytest.mark.parametrize("status", ["pending", "invalid", "failed", "interrupted"])
def test_uncompleted_action_is_not_possession(saved, status):
    binding = saved.source()
    saved.own(saved.root, binding["source_ref"], status=status)
    with pytest.raises(AppServiceCustodyError, match="input_not_possessed"):
        saved.custody.possession(saved.root, binding["source_ref"])


def test_partial_completed_work_is_retained(saved):
    binding = saved.source()
    saved.own(saved.root, binding["source_ref"], status="partial")
    assert saved.custody.content(saved.root, binding) == saved.store.get_artifact(binding["artifact_ref"])


def test_parent_assignment_authenticates_both_boundaries_without_expansion(saved):
    binding = saved.source()
    saved.own(saved.root, binding["source_ref"])
    launch, api = saved.tree(saved.supplied_request(binding))
    assert saved.custody.initial_references(launch) == [binding["source_ref"]]
    assert saved.custody.initial_references(api) == [binding["source_ref"]]
    assert saved.custody.possession(api, binding["source_ref"]) == "parent_assignment"
    with pytest.raises(AppServiceCustodyError, match="input_not_possessed"):
        saved.custody.possession(api, binding["artifact_ref"])


def test_inherited_ledger_and_received_record_refs_are_not_assignment(saved):
    binding = saved.source()
    saved.own(saved.root, binding["source_ref"])
    launch, api = saved.tree()
    assert binding["source_ref"] in saved.receipts.known(api.episode_id)
    assert saved.custody.initial_references(api) == []
    forged = replace(api, received_record_refs=(binding["source_ref"],))
    with pytest.raises(AppServiceCustodyError, match="input_not_possessed"):
        saved.custody.possession(forged, binding["source_ref"])


def test_post_commission_parent_action_is_not_an_original_input(saved):
    binding = saved.source()
    query = saved.supplied_request(binding)
    launch = saved.child(saved.root, "launch", launch_assignment(query), 2)
    saved.own(saved.root, binding["source_ref"], 3)
    with pytest.raises(AppServiceCustodyError, match="input_not_possessed"):
        saved.custody.initial_references(launch)


def test_earlier_selected_child_returning_late_cannot_retroactively_supply_input(saved):
    binding = saved.source()
    producer = saved.child(saved.root, "results", {}, 0)
    launch = saved.child(saved.root, "launch", launch_assignment(saved.supplied_request(binding)), 2)
    saved.own(producer, binding["source_ref"])
    saved.admit(saved.root, producer, binding["source_ref"])
    assert saved.custody.possession(saved.root, binding["source_ref"]) == "admitted_return"
    with pytest.raises(AppServiceCustodyError, match="input_not_received_before_commission"):
        saved.custody.initial_references(launch)


def test_ref_only_immediate_child_return_and_sibling_isolation(saved):
    binding = saved.source()
    producer = saved.child(saved.root, "results", {}, 0)
    sibling = saved.child(saved.root, "results", {}, 1)
    saved.own(producer, binding["source_ref"])
    saved.admit(saved.root, producer, binding["source_ref"])
    history = list(saved.store.db.iterdump())
    assert saved.custody.possession(saved.root, binding["source_ref"]) == "admitted_return"
    assert saved.custody.evidence(saved.root, content(binding, pointer="/native/1")) == 1.25
    assert list(saved.store.db.iterdump()) == history
    assert json.loads(saved.journal.row("runtime_forms", producer.episode_id)["facts"]) == {
        "committed_record_refs": [binding["source_ref"]]}
    with pytest.raises(AppServiceCustodyError, match="input_not_possessed"):
        saved.custody.possession(sibling, binding["source_ref"])


def test_ordinary_scientific_child_reference_uses_shared_original_return_contract(saved):
    binding = saved.source()
    # This legacy action-only record has no conflicting episode_child response.
    child = saved.child(saved.root, "improvement", {}, 0, model=False)
    request_record = plain(child.request)
    del request_record["message"]["episode_assignment"]
    child = replace(child, request=request_record)
    row = saved.journal.row("runtime_episodes", child.episode_id)
    saved.journal.save("runtime_episodes", {**row, "request": canonical(request_record)})
    row = saved.journal.row("runtime_actions", saved.root.episode_id, 0)
    selection = json.loads(row["action"])
    selection["kind"] = "child"
    del selection["role"], selection["assignment"]
    saved.journal.save("runtime_actions", {**row, "action": canonical(selection)})
    saved.own(child, binding["source_ref"])
    saved.admit(saved.root, child, binding["source_ref"])
    assert saved.custody.possession(saved.root, binding["source_ref"]) == "admitted_return"


@pytest.mark.parametrize("field", ["scope", "assignment", "request"])
def test_changed_context_never_matches_saved_context(saved, field):
    _, api = saved.tree()
    value = plain(getattr(api, field))
    value["changed"] = True
    with pytest.raises(AppServiceCustodyError, match="context_conflict"):
        saved.custody.initial_references(replace(api, **{field: value}))


@pytest.mark.parametrize("encoded", [False, True])
def test_unsaved_initialization_uses_exact_saved_model_selection(saved, encoded):
    binding = saved.source()
    saved.own(saved.root, binding["source_ref"])
    ctx = saved.child(saved.root, "launch", launch_assignment(saved.supplied_request(binding)),
        1, save=False, action=False, encoded=encoded)
    assert saved.custody.initial_references(ctx) == [binding["source_ref"]]
    assert saved.journal.row("runtime_episodes", ctx.episode_id) is None
    assert saved.journal.row("runtime_actions", saved.root.episode_id, 1) is None


@pytest.mark.parametrize("change", ["missing", "assignment", "scope", "goal", "purpose", "schema_json", "initial_report_json"])
def test_unsaved_context_cannot_forge_parent_selection(saved, change):
    ctx = saved.child(saved.root, "launch", launch_assignment(), 1, save=False, action=False)
    if change == "missing":
        saved.store.db.execute("DELETE FROM runtime_model_calls")
    else:
        row = saved.journal.row("runtime_model_calls", saved.root.episode_id, 1)
        response = json.loads(row["response"])
        if change == "assignment":
            response["selection"][change]["constraints"]["allowed_kinds"] = ["local"]
        elif change == "scope":
            response["selection"][change]["intervals"] = []
        elif change == "schema_json":
            response["selection"][change] = canonical(refs_schema("execution_result"))
        elif change == "initial_report_json":
            response["selection"][change] = '{"refs": []}'
        else:
            response["selection"][change] = "changed"
        saved.journal.save("runtime_model_calls", {**row, "response": canonical(response)})
    with pytest.raises(AppServiceCustodyError):
        saved.custody.initial_references(ctx)


def test_later_action_must_agree_with_saved_selection(saved):
    ctx = saved.child(saved.root, "launch", launch_assignment(), 1)
    row = saved.journal.row("runtime_actions", saved.root.episode_id, 1)
    action = json.loads(row["action"])
    action["assignment"]["requests"]["selected-api"]["request"]["parameters"]["blast_max_hits"] = True
    saved.journal.save("runtime_actions", {**row, "action": canonical(action)})
    with pytest.raises(AppServiceCustodyError, match="parent_selection_conflict"):
        saved.custody.initial_references(ctx)


def test_unsaved_context_requires_model_selection_even_when_an_action_exists(saved):
    ctx = saved.child(saved.root, "launch", launch_assignment(), 1, save=False, model=False)
    with pytest.raises(AppServiceCustodyError, match="saved_parent_selection_required"):
        saved.custody.initial_references(ctx)


def test_unsaved_context_cannot_use_selection_rejected_by_original_schema(saved):
    ctx = saved.child(saved.root, "launch", launch_assignment(), 1, save=False, action=False)
    row = saved.journal.row("runtime_model_calls", saved.root.episode_id, 1)
    sent = json.loads(row["request"])
    sent["schema"]["properties"]["selection"]["properties"]["role"] = {"const": "results"}
    saved.journal.save("runtime_model_calls", {**row, "request": canonical(sent)})
    with pytest.raises(AppServiceCustodyError, match="parent_selection_invalid"):
        saved.custody.initial_references(ctx)


@pytest.mark.parametrize("change", [None, "selection", "spec", "hash"])
def test_actual_durable_commission_intent_must_agree(saved, change):
    from gene_annotation_episode.episode_commissions import CommissionCoordinator
    child = saved.child(saved.root, "launch", launch_assignment(), 1)
    selected = json.loads(saved.journal.row("runtime_actions", saved.root.episode_id, 1)["action"])
    coordinator = CommissionCoordinator(saved.store, saved.journal, None)
    spec = coordinator.select(parent={"episode_id": saved.root.episode_id, "path": plain(saved.root.path),
        "goal_id": saved.root.request["goal"]["goal_id"]},
        child={"episode_id": child.episode_id, "path": plain(child.path), "role": child.role,
            "key": child.path[-1][1], "scope": plain(child.scope), "request": plain(child.request)},
        original_decision_index=1, selection=selected,
        runtime_binding={"factory_module": "synthetic_fixture", "factory_name": "unused",
            "arguments": {}, "implementation_sha256": "a" * 64, "settings_sha256": "b" * 64},
        input_versions=[], constraints={}, resource_selection=None,
        expectation_snapshot_refs=[], selected_at="2026-10-24T00:00:00+00:00")
    assert saved.custody.original_job_owner(child)["launch_episode_id"] == child.episode_id
    if change is None:
        assert saved.custody.initial_references(child) == []
        return
    if change == "selection":
        selected["goal"] = "replaced"
        saved.store.db.execute("UPDATE runtime_commission_intents SET selection=?", (canonical(selected),))
    elif change == "spec":
        spec["constraints"]["replaced"] = True
        saved.store.db.execute("UPDATE runtime_commission_intents SET spec=?", (canonical(spec),))
    else:
        saved.store.db.execute("UPDATE runtime_commission_intents SET commission_sha256=?", ("0" * 64,))
    with pytest.raises(AppServiceCustodyError, match="durable_commission_conflict"):
        saved.custody.initial_references(child)


@pytest.mark.parametrize("change", ["failed", "frozen", "contract", "untyped", "assignment"])
def test_return_requires_successful_original_typed_values(saved, change):
    binding = saved.source()
    producer = saved.child(saved.root, "results", {}, 0)
    saved.own(producer, binding["source_ref"])
    saved.admit(saved.root, producer, binding["source_ref"])
    if change == "failed":
        saved.store.db.execute("UPDATE runtime_report_attempts SET failure=?", ('{"code":"rejected"}',))
    elif change == "frozen":
        saved.store.db.execute("UPDATE runtime_forms SET facts=?", ('{"committed_record_refs":[]}',))
    elif change == "contract":
        contract = plain(producer.request)["report_contract"]
        contract["decision"] = "replacement form"
        saved.store.db.execute("UPDATE runtime_report_attempts SET contract=?", (canonical(contract),))
    elif change == "assignment":
        row = saved.journal.row("runtime_actions", saved.root.episode_id, 0)
        action = json.loads(row["action"])
        action["assignment"] = {"replaced": True}
        saved.journal.save("runtime_actions", {**row, "action": canonical(action)})
    else:
        # A literal string in a field is not a typed source delivery.
        schema = refs_schema()
        schema["properties"]["refs"]["items"] = {"type": "string", "enum": [binding["source_ref"]]}
        original = saved.child(saved.root, "results", {}, 1, schema=schema)
        saved.own(original, binding["source_ref"])
        saved.admit(saved.root, original, binding["source_ref"])
        saved.store.db.execute("DELETE FROM runtime_report_attempts WHERE decision_index=0")
    with pytest.raises(AppServiceCustodyError):
        saved.custody.possession(saved.root, binding["source_ref"])


def test_native_task_id_is_not_possession_or_original_ownership(saved):
    with pytest.raises(AppServiceCustodyError, match="reference_unavailable"):
        saved.custody.possession(saved.root, "native-task")
    with pytest.raises(AppServiceCustodyError, match="original_launch_context_required"):
        saved.custody.original_job_owner(saved.root)


def test_parent_resource_request_cannot_be_replaced(saved):
    launch = saved.child(saved.root, "launch", launch_assignment(), 0)
    altered = api_assignment()
    altered["request"]["parameters"]["blast_max_hits"] = True
    api = saved.child(launch, "launch_api", altered, 0)
    with pytest.raises(AppServiceCustodyError, match="original_request_conflict"):
        saved.custody.initial_references(api)


@pytest.mark.parametrize("field,value", [("byte_count", 1), ("byte_count", True),
    ("sha256", "0" * 64), ("artifact_field", "stderr_ref"), ("extra", "forged")])
def test_content_binding_is_exact(saved, field, value):
    binding = saved.source()
    saved.own(saved.root, binding["source_ref"])
    altered = {**binding, field: value}
    with pytest.raises(AppServiceCustodyError):
        saved.custody.content(saved.root, altered)


def test_matching_digest_in_different_source_field_is_not_the_selected_edge(saved):
    other = saved.store.artifact(b"other", "text/plain")
    binding = saved.source(stdout_ref=other)
    saved.own(saved.root, binding["source_ref"])
    with pytest.raises(AppServiceCustodyError, match="artifact_field_conflict"):
        saved.custody.content(saved.root, {**binding, "artifact_field": "stdout_ref"})
    exact = {**binding, "artifact_field": "stdout_ref", "artifact_ref": other,
             "sha256": hashlib.sha256(b"other").hexdigest(), "byte_count": 5}
    assert saved.custody.content(saved.root, exact) == b"other"


@pytest.mark.parametrize("change", ["absent_bytes", "changed_bytes", "source_field", "artifact_length", "artifact_sha"])
def test_actual_store_edges_and_bytes_are_verified(saved, change):
    binding = saved.source()
    saved.own(saved.root, binding["source_ref"])
    path = saved.store.path / "artifacts" / binding["sha256"][:2] / binding["sha256"]
    if change == "absent_bytes":
        path.unlink()
    elif change == "changed_bytes":
        path.write_bytes(b"changed")
    elif change == "source_field":
        source = saved.store.get(binding["source_ref"])
        source["text_ref"] = None
        saved.store.db.execute("UPDATE records SET data=? WHERE id=?", (canonical(source), source["id"]))
    elif change == "artifact_length":
        saved.store.db.execute("UPDATE artifacts SET size=size+1 WHERE id=?", (binding["artifact_ref"],))
    else:
        saved.store.db.execute("UPDATE artifacts SET sha256=? WHERE id=?", ("0" * 64, binding["artifact_ref"]))
    with pytest.raises(AppServiceCustodyError) as error:
        saved.custody.content(saved.root, binding)
    if change == "changed_bytes":
        assert error.value.code == "bvbrc_appservice_custody_input_bytes_mismatch"


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":{"a":1,"a":2}}', b'{"x":NaN}',
    b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":1e400}', b'[] trailing', b'\xff'])
def test_source_json_rejects_ambiguous_or_nonfinite_values(saved, raw):
    binding = saved.source(raw)
    saved.own(saved.root, binding["source_ref"])
    with pytest.raises(AppServiceCustodyError) as error:
        saved.custody.evidence(saved.root, content(binding))
    assert error.value.code.startswith("bvbrc_appservice_custody_")
    assert error.value.diagnostics == [{"code": error.value.code, "path": ""}]


@pytest.mark.parametrize("pointer,expected", [("", {"a/b": {"~": [0, False, None]}, "": "empty", "01": 5}),
    ("/a~1b/~0/0", 0), ("/a~1b/~0/1", False), ("/a~1b/~0/2", None), ("/", "empty"), ("/01", 5)])
def test_exact_rfc6901_pointer(saved, pointer, expected):
    binding = saved.source(b'{"a/b":{"~":[0,false,null]},"":"empty","01":5}')
    saved.own(saved.root, binding["source_ref"])
    actual = saved.custody.evidence(saved.root, content(binding, pointer=pointer))
    assert type(actual) is type(expected) and actual == expected


@pytest.mark.parametrize("pointer", ["/a~1b/~0/01", "/a~1b/~0/-", "/a~1b/~0/3", "/a~2b", "#", "/missing"])
def test_pointer_never_guesses_or_normalizes_missing_operands(saved, pointer):
    binding = saved.source(b'{"a/b":{"~":[0,false,null]}}')
    saved.own(saved.root, binding["source_ref"])
    with pytest.raises(AppServiceCustodyError):
        saved.custody.evidence(saved.root, content(binding, pointer=pointer))


def test_supplied_link_uses_actual_source_evidence_and_no_acquisition(saved):
    binding = saved.source(b'{"link":"https://example.invalid/input"}')
    saved.own(saved.root, binding["source_ref"])
    query = request()
    query["parameters"]["original_link"] = "https://example.invalid/input"
    query["input_bindings"] = [{"binding_id": "link", "parameter_pointer": "/original_link",
        "kind": "supplied_link", "content": None, "workspace_path": None,
        "inline_value": "https://example.invalid/input", "link_evidence": content(binding, pointer="/link"),
        "members": []}]
    _, api = saved.tree(query)
    assert saved.custody.initial_references(api) == [binding["source_ref"]]
    assert saved.custody.evidence(api, query["input_bindings"][0]["link_evidence"]) == "https://example.invalid/input"


def test_stable_original_owner_across_resources_and_distinct_commissions(saved):
    launch, first = saved.tree()
    second = saved.child(launch, "launch_api", api_assignment(resource="second-api"), 1)
    other_launch, other = saved.tree(launch_index=3)
    owner = saved.custody.original_job_owner(first)
    assert owner == saved.custody.original_job_owner(second) == saved.custody.original_job_owner(launch)
    assert owner != saved.custody.original_job_owner(other)
    assert owner == {"run_id": saved.run_id, "launch_episode_id": launch.episode_id,
        "parent_commission_operation_key": f"{saved.run_id}:{saved.root.episode_id}:2",
        "original_launch_assignment_sha256": digest(launch.assignment)}
    assert other_launch.episode_id != launch.episode_id


def result_context(saved):
    launch, api = saved.tree()
    binding = saved.source(b'{"task_id":"native-task"}')
    saved.own(api, binding["source_ref"], tool="api.bvbrc_appservice.submit")
    saved.admit(launch, api, binding["source_ref"])
    saved.admit(saved.root, launch, binding["source_ref"])
    results = saved.child(saved.root, "results", {"version": "execution_results_assignment_v1",
        "handoff_ref": binding["source_ref"], "selector": selector()}, 3)
    value = {"reference": binding["source_ref"], "origin_context": api,
             "original_job_owner": saved.custody.original_job_owner(api)}
    return results, value


def test_results_owner_uses_possessed_handoff_and_exact_callback(saved):
    results, value = result_context(saved)
    assert saved.custody.initial_references(results) == [value["reference"]]
    with pytest.raises(AppServiceCustodyError, match="original_handoff_reader_unbound"):
        saved.custody.original_job_owner(results)
    calls = []
    def read(reference):
        calls.append(reference)
        return {**value, "origin_context": value["origin_context"].as_record()}
    custody = AppServiceCustody(saved.store, saved.run_id, read_original_handoff=read)
    assert custody.original_job_owner(results) == value["original_job_owner"]
    assert calls == [value["reference"]]


@pytest.mark.parametrize("change", ["reference", "owner", "context", "support_action"])
def test_results_cannot_rebind_original_owner(saved, change):
    results, value = result_context(saved)
    if change == "reference":
        value["reference"] = "native-task"
    elif change == "owner":
        value["original_job_owner"] = {**value["original_job_owner"], "launch_episode_id": "different"}
    elif change == "context":
        value["origin_context"] = replace(value["origin_context"], run_id="different")
    else:
        saved.own(value["origin_context"], value["reference"], tool="api.bvbrc_appservice.workspace_create")
    custody = AppServiceCustody(saved.store, saved.run_id, read_original_handoff=lambda _: value)
    with pytest.raises(AppServiceCustodyError):
        custody.original_job_owner(results)


def test_packaged_definition_is_configuration_not_fabricated_inherited_source(saved):
    source_count = saved.store.count("source")
    launch, api = saved.tree()
    definition = get_application_spec("Homology")
    prepared = prepare_application("Homology", request()["parameters"], {})
    assert prepared["status"] == "ok"
    assert definition["required_id"] == "Homology"
    validate_contract("DefinitionSelection", {"kind": "packaged", "required_application_id": "Homology"})
    assert saved.custody.initial_references(launch) == saved.custody.initial_references(api) == []
    assert saved.store.count("source") == source_count


def test_actual_shared_workflow_action_and_ref_only_return_records(tmp_path, monkeypatch):
    from bvbrc_episode_fixture import EpisodeRun, Transport, envelope, request as data_request, result_form, selector as data_selector
    transport = Transport(monkeypatch, [envelope([], total=0)])
    with Store(tmp_path / "actual-state") as store:
        run = EpisodeRun(store, tmp_path / "actual-run", data_request(), data_selector(), result_form())
        archive = run.run()
        custody = AppServiceCustody(store, run.workflow.run_id)
        result_episode = archive["units"][1]["child"]["episode_id"]
        root = custody.context(archive["episode_id"])
        result = custody.context(result_episode)
        reference, = run.received_forms[0]["references"]
        assert custody.possession(result, reference) == "own_completed_action"
        assert custody.possession(root, reference) == "admitted_return"
        raw_ref = store.get(reference)["artifact_ref"]
        raw = store.get_artifact(raw_ref)
        binding = {"source_ref": reference, "artifact_field": "artifact_ref", "artifact_ref": raw_ref,
            "sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw)}
        assert custody.content(root, binding) == envelope([], total=0)
        assert len(transport.prepared) == 1
        assert store.count("annotation") == store.count("observation") == 0
