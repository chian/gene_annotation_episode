"""Actual Workflow commissions and preparation returns, with scripted choices.

Preparation uses packaged application definitions; no BV-BRC submission, native
scientific result, model inference, live transport or credentials are involved.
Corruption cases copy that actual saved state instead of inventing a catalog.
"""
import asyncio
from copy import deepcopy
import json
import shutil
from types import SimpleNamespace

import pytest

from gene_annotation_episode.bvbrc_appservice_custody import AppServiceCustody, AppServiceCustodyError
from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.episode_contract_information import expand_fact_form, validate_saved_fact_form
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.practical_yield import PracticalYieldEstimator
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_api_bvbrc_appservice import CONFIG
from test_bvbrc_appservice_custody import api_assignment
from test_runtime_decision_exchanges import select


SOURCE = "bvbrc_appservice_support_refs"


class Provider:
    def __init__(self):
        self.script = iter(())

    async def complete(self, episode_id, role, instructions, context, schema):
        return deepcopy(next(self.script))

    async def release(self, episode_id):
        pass


def obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def forbidden(*args, **kwargs):
    raise AssertionError("Custody verification must not acquire, submit or rebuild current contracts")


def fixture_estimate(history, parameters):
    # Test-only continuation: yield partial preparation after one own action.
    # This neither proves a usable handoff nor changes the production estimator.
    return YieldEstimate(len(history), NumericBand.exact(0 if history else 1), parameters,
                         {"fixture": "one_selected_preparation_and_original_return"})


def build_run(directory, *, compact=True, durable=False):
    """Run ordinary method_loop through both real commissioning boundaries."""
    store = Store(directory / "state")
    factory = ExecutionServiceFactory({"selected-api": CONFIG}, {}, 2, 3, .5)
    provider = Provider()
    workflow = Workflow(store, ToolRegistry(store), provider, directory / "run", "custody479",
        controller_factory=lambda path, initial: YieldController(str(path), initial, 0,
            YieldParameters(100, 50), estimate_with_context=lambda history, parameters, _: fixture_estimate(history, parameters)),
        project_credit=lambda *_: 0, episode_service_factory=factory,
        episode_service_binding=factory.as_record(), episode_service_inputs="actual_tool_registry_v1",
        annotation_child_roles=("launch", "results"), episode_record_receipts=True,
        initial_known_record_refs=[], decision_protocol="decision_exchange_v1",
        execution_binding=None if not durable else {"factory_module": "synthetic_fixture",
            "factory_name": "unused", "arguments": {}, "implementation_sha256": "a" * 64,
            "settings_sha256": "b" * 64})
    scope = {"subject_refs": store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]}
    api = api_assignment()
    launch = {"version": "execution_launch_assignment_v1", "requests": {"selected-api": api},
              "immutable_input_versions": [], "constraints": {"allowed_kinds": ["api"]}}
    full = obj({"support": deepcopy(workflow.report_sources("launch_api")[SOURCE]["report_schema"])})
    submitted = obj({"support": {"$ref": "episode-fact:" + SOURCE}}) if compact else full
    def commission(role, assignment):
        return select({"selection": {"kind": "episode_child", "role": role,
            "assignment": canonical(assignment), "scope": scope,
            "goal": "Validate the selected synthetic Homology preparation operands",
            "purpose": "Return the original preparation receipt references",
            "schema_json": canonical(submitted), "initial_report_json": "{}"}, "report_update": {}})
    provider.script = iter([commission("launch", launch), commission("launch_api", api),
        select({"selection": {"kind": "tool", "tool": "api.bvbrc_appservice.prepare",
            "arguments": {"definition": {"kind": "packaged", "required_application_id": "Homology"}}},
            "report_update": {}})])
    observed_unsaved = set()
    authenticate = AppServiceCustody.authenticate
    def inspect(self, context, *, allow_unsaved=False):
        result = authenticate(self, context, allow_unsaved=allow_unsaved)
        if len(context.path) > 1 and self.db.execute("SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?",
                (self.run_id, context.episode_id)).fetchone() is None:
            observed_unsaved.add(context.role)
        return result
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(workflow, "contract_information_profile", lambda _: CONTRACT_INFORMATION_PROFILE)
        binding = workflow.episode_bindings.for_role("launch")
        patch.setattr(binding, "practical_estimator", lambda context: PracticalYieldEstimator(
            lambda proof: binding.verify_completion(context, proof), base_estimate=fixture_estimate))
        patch.setattr(AppServiceCustody, "authenticate", inspect)
        patch.setattr("socket.create_connection", forbidden)
        patch.setattr("socket.socket.connect", forbidden)
        patch.setattr("urllib.request.OpenerDirector.open", forbidden)
        root = workflow.build("annotation", "root", "Check the supplied synthetic preparation operands", scope)
        async def run():
            record = await root.run_async(workflow.context)
            await root.build_result(record)
            return record
        if durable:
            class IntentPublished(Exception):
                pass
            def stop_before_dispatch(*args, **kwargs):
                raise IntentPublished()
            patch.setattr(workflow, "dispatch_commission", stop_before_dispatch)
            with pytest.raises(IntentPublished):
                asyncio.run(run())
            row = store.db.execute("SELECT spec FROM runtime_commission_intents").fetchone()
            spec = json.loads(row["spec"])
            assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
            return SimpleNamespace(store=store, workflow=workflow, root=root, full=full,
                launch_id=spec["child"]["episode_id"], directory=directory)
        record = asyncio.run(run())
        assert record.units_consumed == 1
        assert observed_unsaved == {"launch", "launch_api"}
        original = store.db.execute("SELECT * FROM runtime_report_attempts WHERE parent_episode_id=?",
            (root.source.episode_id,)).fetchone()
        assert original["failure"] is None
        reference, = json.loads(original["form"])["support"]
        assert store.get(reference)["provider"] == "episode.bvbrc_appservice_receipt"
        counts = tuple(store.db.execute("SELECT (SELECT count(*) FROM runtime_actions),"
            "(SELECT count(*) FROM runtime_observations), (SELECT count(*) FROM records)").fetchone())
        # Explicit redelivery is an internal decision over the saved child.
        revised = obj({"again": {"$ref": "episode-fact:" + SOURCE}})
        provider.script = iter([select({"selection": {"kind": "redeliver_report",
            "delivery_ref": original["delivery_ref"], "purpose": "Read the same original preparation references",
            "schema_json": canonical(revised)}, "report_update": {}})])
        response, index, context, schema = asyncio.run(root.source.call(
            {"scope": scope, "visible_record_refs": [], "tools": workflow.catalog(scope, source=root.source)},
            workflow.action_schema(root.source)))
        redelivery = root.source.apply_response(response, index, context, schema)
        assert redelivery is not None, root.source.feedback
        assert tuple(store.db.execute("SELECT (SELECT count(*) FROM runtime_actions),"
            "(SELECT count(*) FROM runtime_observations), (SELECT count(*) FROM records)").fetchone()) == counts
    result = SimpleNamespace(store=store, workflow=workflow, root=root, full=full, reference=reference,
        redelivery_index=index, launch_id=original["child_episode_id"], directory=directory)
    return result


@pytest.fixture(scope="module")
def original(tmp_path_factory):
    case = build_run(tmp_path_factory.mktemp("compact479"))
    case.store.close()
    return case


@pytest.fixture(scope="module")
def durable_original(tmp_path_factory):
    case = build_run(tmp_path_factory.mktemp("durable479"), durable=True)
    case.store.close()
    return case


@pytest.fixture
def saved(original, tmp_path, monkeypatch):
    yield from saved_copy(original, tmp_path, monkeypatch)


@pytest.fixture
def durable_saved(durable_original, tmp_path, monkeypatch):
    yield from saved_copy(durable_original, tmp_path, monkeypatch)


def saved_copy(original, tmp_path, monkeypatch):
    shutil.copytree(original.directory / "state", tmp_path / "state")
    with Store(tmp_path / "state") as store:
        custody = AppServiceCustody(store, original.workflow.run_id)
        case = SimpleNamespace(**{**vars(original), "store": store, "custody": custody})
        case.parent = custody.context(original.root.source.episode_id)
        case.child = custody.context(original.launch_id)
        for name in ("report_sources", "catalog", "action_schema", "freeze_contract_information"):
            monkeypatch.setattr(Workflow, name, forbidden)
        monkeypatch.setattr("socket.create_connection", forbidden)
        monkeypatch.setattr("socket.socket.connect", forbidden)
        monkeypatch.setattr("urllib.request.OpenerDirector.open", forbidden)
        yield case


def rewrite_request(case, function):
    row = case.store.db.execute("SELECT request FROM runtime_episodes WHERE episode_id=?", (case.child.episode_id,)).fetchone()
    request = json.loads(row["request"])
    function(request)
    case.store.db.execute("UPDATE runtime_episodes SET request=? WHERE episode_id=?",
                         (canonical(request), case.child.episode_id))


def rewrite_frame(case, function, *, index=0):
    row = case.store.db.execute("SELECT request FROM runtime_model_calls WHERE episode_id=? AND call_index=?",
                               (case.parent.episode_id, index)).fetchone()
    sent = json.loads(row["request"])
    function(sent)
    case.store.db.execute("UPDATE runtime_model_calls SET request=? WHERE episode_id=? AND call_index=?",
                         (canonical(sent), case.parent.episode_id, index))


def test_actual_workflow_full_form_commission_and_compact_redelivery(tmp_path):
    case = build_run(tmp_path, compact=False)
    try:
        custody = AppServiceCustody(case.store, case.workflow.run_id)
        parent = custody.context(case.root.source.episode_id)
        assert custody._attempt(parent, 0)[1] == {"support": [case.reference]}
        assert custody._attempt(parent, case.redelivery_index)[1] == {"again": [case.reference]}
    finally:
        case.store.close()


def test_actual_compact_return_redelivery_and_readonly_replay(saved):
    before = list(saved.store.db.iterdump())
    saved.store.db.execute("PRAGMA query_only=ON")
    try:
        child, form, schema = saved.custody._attempt(saved.parent, 0)
        assert child.episode_id == saved.child.episode_id
        assert form == {"support": [saved.reference]} and schema == saved.full
        assert saved.custody._attempt(saved.parent, saved.redelivery_index)[1] == {"again": [saved.reference]}
        assert saved.custody.possession(saved.parent, saved.reference) == "admitted_return"
        assert list(saved.store.db.iterdump()) == before
    finally:
        saved.store.db.execute("PRAGMA query_only=OFF")


@pytest.mark.parametrize("field", ["role", "assignment", "scope", "goal", "purpose", "schema_json"])
def test_changed_original_selection_is_rejected(saved, field):
    row = saved.store.db.execute("SELECT action FROM runtime_actions WHERE episode_id=? AND decision_index=0",
                                (saved.parent.episode_id,)).fetchone()
    selected = json.loads(row["action"])
    if field == "assignment":
        selected[field]["constraints"] = {"allowed_kinds": ["local"]}
    elif field == "scope":
        selected[field]["subject_refs"] = []
    elif field == "schema_json":
        selected[field] = canonical(obj({"other": {"$ref": "episode-fact:" + SOURCE}}))
    else:
        selected[field] = "changed"
    saved.store.db.execute("UPDATE runtime_actions SET action=? WHERE episode_id=? AND decision_index=0",
                          (canonical(selected), saved.parent.episode_id))
    with pytest.raises(AppServiceCustodyError, match="parent_selection_conflict"):
        saved.custody.context(saved.child.episode_id)


@pytest.mark.parametrize("change", ["missing", "child_role", "expanded_schema_sha256", "submitted_schema_json", "source"])
def test_changed_or_missing_declaration_is_rejected(saved, change):
    def alter(request):
        declaration = request["message"]["report_contract_declaration"]
        if change == "missing":
            del request["message"]["report_contract_declaration"]
        elif change == "source":
            declaration["fact_references"][0]["source"] = "execution_result_refs"
        else:
            declaration[change] = "changed"
    rewrite_request(saved, alter)
    with pytest.raises(AppServiceCustodyError, match="commission_declaration_conflict"):
        saved.custody.context(saved.child.episode_id)


@pytest.mark.parametrize("change", ["digest", "roles", "context", "fact_source", "missing_frame", "purpose"])
def test_corrupt_original_frame_has_typed_failure(saved, change):
    if change == "missing_frame":
        saved.store.db.execute("DELETE FROM runtime_model_calls WHERE episode_id=? AND call_index=0", (saved.parent.episode_id,))
    elif change == "purpose":
        saved.store.db.execute("UPDATE runtime_model_calls SET purpose='report' WHERE episode_id=? AND call_index=0", (saved.parent.episode_id,))
    else:
        def alter(sent):
            record = sent["contract_information"]
            if change == "digest":
                record["fact_sources_sha256"] = "0" * 64
            elif change == "roles":
                record["permitted_child_roles"] = ["launch_api"]
            elif change == "context":
                sent["context"] = None
            else:
                record["fact_sources_by_role"]["launch"][SOURCE]["report_schema"]["x-source"] = "execution_result_refs"
                record["fact_sources_sha256"] = digest(record["fact_sources_by_role"])
        rewrite_frame(saved, alter)
    with pytest.raises(AppServiceCustodyError) as error:
        saved.custody.context(saved.child.episode_id)
    assert error.value.code.startswith("bvbrc_appservice_custody_")


def test_self_consistent_forged_expansion_cannot_replace_original_catalog(saved):
    def forge(request):
        declaration = request["message"]["report_contract_declaration"]
        altered = deepcopy(saved.full["properties"]["support"])
        altered["items"]["x-reference-namespace"] = "execution_result"
        result = expand_fact_form(declaration["submitted_schema_json"], child_role="launch",
            facts_by_role={"launch": {SOURCE: {"type": "array", "meaning": "forged", "report_schema": altered}}},
            permitted_child_roles=["launch"])
        request["report_contract"]["measurements"]["schema"] = result["expanded_schema"]
        request["message"]["report_contract_declaration"] = result["declaration"]
        # The pure relationship checker accepts this internally coherent forgery.
        validate_saved_fact_form(child_role="launch", submitted_schema_json=declaration["submitted_schema_json"],
            expanded_schema=result["expanded_schema"], declaration=result["declaration"])
    rewrite_request(saved, forge)
    with pytest.raises(AppServiceCustodyError, match="commission_declaration_conflict"):
        saved.custody.context(saved.child.episode_id)


@pytest.mark.parametrize("change", [None, "declaration", "selection", "inheritance"])
def test_compact_durable_commission_and_inheritance_keep_original_identity(durable_saved, change):
    saved = durable_saved
    row = saved.store.db.execute("SELECT * FROM runtime_commission_intents").fetchone()
    selected, spec = json.loads(row["selection"]), json.loads(row["spec"])
    if change == "declaration":
        spec["child"]["request"]["message"]["report_contract_declaration"]["expanded_schema_sha256"] = "0" * 64
        saved.store.db.execute("UPDATE runtime_commission_intents SET spec=?,commission_sha256=?",
                              (canonical(spec), digest(spec)))
    elif change == "selection":
        selected["purpose"] = "replaced"
        saved.store.db.execute("UPDATE runtime_commission_intents SET selection=?", (canonical(selected),))
    elif change == "inheritance":
        rewrite_request(saved, lambda request: request["message"]["knowledge_inheritance"].update(through_receipt_index=999))
    before = list(saved.store.db.iterdump())
    if change is None:
        parent, index = saved.custody._commission(saved.child)
        assert parent.episode_id == saved.parent.episode_id and index == 0
    else:
        with pytest.raises(AppServiceCustodyError):
            saved.custody.context(saved.child.episode_id)
    assert list(saved.store.db.iterdump()) == before


@pytest.mark.parametrize("change", ["frame", "purpose", "delivery_ref", "schema", "facts", "form"])
def test_redelivery_authenticates_original_decision_and_frozen_facts(saved, change):
    index = saved.redelivery_index
    if change == "frame":
        rewrite_frame(saved, lambda sent: sent["contract_information"].update(fact_sources_sha256="0" * 64), index=index)
    elif change in {"purpose", "delivery_ref", "schema"}:
        row = saved.store.db.execute("SELECT response FROM runtime_model_calls WHERE episode_id=? AND call_index=?",
            (saved.parent.episode_id, index)).fetchone()
        response = json.loads(row["response"])
        key = "schema_json" if change == "schema" else change
        response["selection"][key] = canonical(obj({"wrong": {"$ref": "episode-fact:" + SOURCE}})) if change == "schema" else "changed"
        saved.store.db.execute("UPDATE runtime_model_calls SET response=? WHERE episode_id=? AND call_index=?",
            (canonical(response), saved.parent.episode_id, index))
    elif change == "facts":
        row = saved.store.db.execute("SELECT facts FROM runtime_forms WHERE episode_id=?", (saved.child.episode_id,)).fetchone()
        facts = json.loads(row["facts"])
        facts[SOURCE] = []
        saved.store.db.execute("UPDATE runtime_forms SET facts=? WHERE episode_id=?", (canonical(facts), saved.child.episode_id))
    else:
        saved.store.db.execute("UPDATE runtime_report_attempts SET form=? WHERE parent_episode_id=? AND decision_index=?",
            ('{"again":[]}', saved.parent.episode_id, index))
    with pytest.raises(AppServiceCustodyError):
        saved.custody._attempt(saved.parent, index)
