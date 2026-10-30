"""Synthetic nested shared-loop returns and actual C4 transaction/reopen tests.

No model inference or primary paper is represented. The shared-loop test uses
scripted choices; the separate C4 test controls immutable commission envelopes.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
import sqlite3

import pytest

from method_loop import EpisodeGoal
from method_loop.archive import JsonArchive
from method_loop.durable import content_digest
from method_loop.identities import EpisodeRef
from gene_annotation_episode.communication import ReportBoundaryError, plain
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_admission import ReceiverBindingV1, admit_return
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_rate_storage import COMPONENTS, LiteratureRateRepository, rate_cells_schema
from gene_annotation_episode.runtime import TypedReportContract, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_episode_admission import Value, seal_return
from test_literature_rate_episode_integration import service_binding
from test_literature_rate_storage import setup_store
from test_runtime import FixtureController, ScriptedProvider


SUBSET = ["rate_difference", "difference_se"]
FORM = obj({"numbers": rate_cells_schema()})


def reason(store, source_ref):
    raw = store.get_artifact(store.get(source_ref)["artifact_ref"])
    token = b"source construct"
    start = raw.index(token)
    commit = {field: [] for field in store.reasoning_schema()["required"]}
    commit["source_subjects"] = [{"alias": "source_subject", "reference_type": "assay",
        "source_ref": source_ref, "label": token.decode(), "anchor": {"source_ref": source_ref,
            "artifact_ref": store.get(source_ref)["artifact_ref"], "start": start,
            "end": start + len(token), "quote": token.decode()}}]
    return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}


def test_nested_shared_loop_preserves_admitted_known_and_unknown_cells_without_extra_observations(tmp_path):
    store, context, args = setup_store(tmp_path / "state")
    try:
        outer = {"version": "literature_assignment_v1", "question_context_refs": [],
            "source_refs": [args["source_ref"]], "requested_rate_components": list(COMPONENTS)}
        inner = {"version": "strategy_assignment_v1", "question_context_refs": [],
            "prior_search_refs": [args["source_ref"]], "requested_rate_components": SUBSET}
        def commission(role, assignment):
            return {"selection": {"kind": "episode_child", "role": role, "assignment": assignment,
                "goal": "Evaluate the synthetic source preparation contrast", "scope": plain(context.scope),
                "purpose": "Return the admitted source-rate components", "schema_json": json.dumps(FORM),
                "initial_report_json": "{}"}, "report_update": {}}
        received = []
        def receive(inputs):
            form, = inputs["child_reports"]
            assert [row["component"] for row in form["numbers"]] == SUBSET
            assert [row["value"] for row in form["numbers"]] == [1, None]
            assert form["numbers"][1]["unavailable_reason"] == "dependence_unknown"
            received.append(deepcopy(form))
            return reason(store, args["source_ref"])
        provider = ScriptedProvider([commission("literature", outer), commission("literature_strategy", inner),
            {"selection": {"kind": "tool", "tool": "literature.rate.populate", "arguments": args}, "report_update": {}},
            receive, receive])
        controllers = []
        def controller(path, initial):
            value = FixtureController(str(path), initial, 1 if len(path) == 3 else 2)
            controllers.append(value)
            return value
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path / "run",
            controller_factory=controller, project_credit=scorer, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={"credit": scorer.as_record()}))
        assert result["credit"] == 0
        assert len(provider.contexts) == 5 and len(received) == 2
        assert [c.scores for c in controllers] == [[0, 0], [0, 0], [0]]
        assert received[0] == received[1]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 5
        assert store.db.execute("SELECT count(*) FROM literature_rate_operations").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM literature_rate_received").fetchone()[0] == 2
        assert store.db.execute("SELECT count(*) FROM literature_rate_delivery_bindings").fetchone()[0] == 2
        forms = [json.loads(row[0]) for row in store.db.execute("SELECT form FROM runtime_forms")]
        assert len(forms) == 2 and forms == received
        saved = json.loads(store.get_artifact(store.get(received[0]["numbers"][0]["sheet_ref"])["artifact_ref"]))
        assert len(saved["sheet"]["cells"]) == 10
        assert not store.list("observation") and not store.list("assessment")
    finally:
        store.close()


def c4_setup(path):
    store, context, args = setup_store(path / "state")
    run = context.run_id
    root_goal = EpisodeGoal.root(objective="Evaluate a synthetic reference", result_contract={})
    mid_goal = EpisodeGoal.child(root_goal, objective="Evaluate the preparation contrast", result_contract={})
    leaf_goal = EpisodeGoal.child(mid_goal, objective="Read the requested preparation-rate components", result_contract={})
    paths = [[["annotation", "root"]], [["annotation", "root"], ["literature", "middle"]],
             [["annotation", "root"], ["literature", "middle"], ["literature_strategy", "leaf"]]]
    ids = [EpisodeRef(run, p).episode_id for p in paths]
    scope = plain(context.scope)
    def resolve(ref, namespace=None):
        return bool(store.reference_subset([ref], scope)) and (namespace is None or store.get(ref)["record_type"] == namespace)
    contract = TypedReportContract("Return requested source rate cells", FORM, resolve)
    assignments = [{}, {"version": "literature_assignment_v1", "question_context_refs": [],
        "source_refs": [args["source_ref"]], "requested_rate_components": list(COMPONENTS)},
        {"version": "strategy_assignment_v1", "question_context_refs": [],
         "prior_search_refs": [args["source_ref"]], "requested_rate_components": SUBSET}]
    contexts = [replace(context, episode_id=eid, role=p[-1][0], path=tuple(tuple(part) for part in p),
        assignment=a) for eid, p, a in zip(ids, paths, assignments)]
    repo = LiteratureRateRepository(store, run)
    outcome = repo.populate(contexts[2], args, "selected-source-rate")
    refs = tuple(dict.fromkeys([*context.received_record_refs, *outcome["record_refs"]]))
    contexts = [replace(c, received_record_refs=refs) for c in contexts]
    _, binding = service_binding(store, contexts[2])
    # Freeze the actual C7 closure facts, establishing its current complete
    # bound view tables before testing a later old-state reconstruction.
    rows = binding.facts(contexts[2], {"committed_record_refs": [outcome["result"]["sheet_ref"]]})["literature_rate_cells"]
    requests = [{"goal": goal.as_record(), "message": {"scope": scope, "episode_assignment": assignment},
                 "report_contract": None if i == 0 else contract.as_record()}
        for i, (goal, assignment) in enumerate(zip((root_goal, mid_goal, leaf_goal), assignments))]
    journal = Journal(store, run)
    for i in range(3):
        journal.save("runtime_episodes", {"episode_id": ids[i], "path": canonical(paths[i]),
            "request": canonical(requests[i]), "initial_credit": 0, "state": "yielded" if i == 2 else "active",
            "completion": None, "archive": None})
    specs = []
    for i, index in ((0, 7), (1, 8)):
        spec = {"version": "episode_commission_v1", "handle": "original-rate-handle-" + str(i),
            "operation_key": "original-commission-" + str(i), "run_id": run,
            "parent": {"episode_id": ids[i], "goal_id": requests[i]["goal"]["goal_id"], "path": paths[i]},
            "child": {"episode_id": ids[i+1], "role": paths[i+1][-1][0], "key": paths[i+1][-1][1],
                "path": paths[i+1], "request": requests[i+1], "scope": scope},
            "input_versions": [], "runtime_binding": {"factory_module": "fixture", "factory_name": "open_commission",
                "arguments": {}, "implementation_sha256": "a" * 64, "settings_sha256": "b" * 64},
            "constraints": {}, "resource_selection": None, "expectation_snapshot_refs": ["original-expectation"]}
        journal.save("runtime_actions", {"episode_id": ids[i], "decision_index": index,
            "action": canonical({"kind": "episode_child", "role": paths[i+1][-1][0], "assignment": assignments[i+1]}),
            "result": canonical({"status": "pending", "pending_handle": spec["handle"]}), "credit": None})
        specs.append(spec)
    archive = JsonArchive(path / "archive")
    form = {"numbers": rows}
    journal.save("runtime_forms", {"episode_id": ids[2], "facts": canonical({"literature_rate_cells": rows,
        "changed_record_refs": outcome["changed_record_refs"]}), "form": canonical(form)})
    return store, contexts, args, repo, outcome, binding, journal, contract, specs, archive, form


def closed_return(spec, archive, form):
    value = {"version": "returned_episode_v1", "handle": spec["handle"], "return_id": "",
        "commission_sha256": content_digest(spec), "returned_at": "2026-10-26T12:00:00+00:00", "outcome": "closed",
        "completion": {"ended_by": "yield_stop", "end_reason": "", "units_consumed": 1},
        "episode_archive": archive.store({"synthetic": True}).descriptor(),
        "result_archive": archive.store({"form": form}).descriptor(), "form": form,
        "facts_archive": archive.store({"literature_rate_cells": form["numbers"]}).descriptor(),
        "pending_handles": [], "failure": None}
    seal_return(value)
    return value


def test_nested_c4_atomic_admission_original_form_tamper_and_read_only_old_receipt_reopen(tmp_path, monkeypatch):
    store, contexts, args, repo, outcome, binding, journal, contract, specs, archive, form = c4_setup(tmp_path)
    run = contexts[0].run_id
    root, middle, leaf = contexts
    sheet = outcome["result"]["sheet_ref"]
    row_components = list(COMPONENTS)
    def receiver(parent, child, index):
        def receive(value):
            binding.received_form_references(parent, value, FORM, run + ":" + parent.episode_id + ":" + str(index) + ":typed_form")
            return [sheet]
        return ReceiverBindingV1(store, journal, index, contract,
            lambda value: binding.validate_report(child, value, FORM), receive, lambda: 0,
            lambda original_index, credit: Value({"credit": credit, "estimation_action_index": original_index}))
    try:
        original_child_return = closed_return(specs[1], archive, form)
        mid_receiver = receiver(middle, leaf, 8)
        service_repo = binding.services.literature_rate_repository()
        original_receive = service_repo.receive_cells
        def interrupted(*args, **kwargs):
            original_receive(*args, **kwargs)
            raise OSError("interrupted after numerical receipt")
        monkeypatch.setattr(service_repo, "receive_cells", interrupted)
        with pytest.raises(OSError, match="after numerical receipt"):
            admit_return(specs[1], original_child_return, mid_receiver)
        assert store.db.execute("SELECT count(*) FROM literature_rate_received").fetchone()[0] == 0
        binding_table = store.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_rate_delivery_bindings'").fetchone()
        assert binding_table is None or store.db.execute("SELECT count(*) FROM literature_rate_delivery_bindings").fetchone()[0] == 0
        monkeypatch.setattr(service_repo, "receive_cells", original_receive)
        admitted_middle = admit_return(specs[1], original_child_return, mid_receiver)
        assert admitted_middle["state"] == "admitted" and admitted_middle["report"] == form
        assert binding.facts(middle, {"committed_record_refs": [sheet]})["literature_rate_cells"] == form["numbers"]
        all_rows = repo.project_cells([sheet], permitted_record_refs=leaf.received_record_refs)
        assert repo.fact_cells(leaf, [sheet], components=row_components) == all_rows
        with pytest.raises(ReportBoundaryError, match="cell_not_received"):
            binding.validate_report(middle, {"numbers": all_rows}, FORM)
        # Close the original middle form using its actual received facts only.
        journal.save("runtime_forms", {"episode_id": middle.episode_id,
            "facts": canonical({"literature_rate_cells": form["numbers"], "changed_record_refs": []}), "form": canonical(form)})
        middle_row = journal.row("runtime_episodes", middle.episode_id)
        journal.save("runtime_episodes", {key: middle_row[key] for key in
            ("episode_id", "path", "request", "initial_credit", "completion", "archive")} | {"state": "yielded"})
        root_receiver = receiver(root, middle, 7)
        original_middle_return = closed_return(specs[0], archive, form)
        admitted_root = admit_return(specs[0], original_middle_return, root_receiver)
        assert admitted_root["state"] == "admitted"
        assert binding.received_report_facts(root)["literature_rate_cells"] == form["numbers"]
        def forbidden(*_args, **_kwargs):
            raise AssertionError("replay cannot receive, recalculate, call a model or reprice")
        for spec, returned, bound, admitted in ((specs[1], original_child_return, mid_receiver, admitted_middle),
                (specs[0], original_middle_return, root_receiver, admitted_root)):
            assert admit_return(spec, returned, replace(bound, receive_references=forbidden,
                project_received_credit=forbidden, validate_semantics=forbidden)) == admitted
        # A forged complete saved row and matching forged digest do not replace
        # the exact runtime admitted form.
        key = run + ":" + middle.episode_id + ":8:typed_form"
        forged = [next(row for row in all_rows if row["component"] == "retained_fraction")]
        store.db.execute("UPDATE literature_rate_received SET cells=? WHERE episode_id=? AND operation_key=?",
            (canonical(forged), middle.episode_id, key))
        store.db.execute("UPDATE literature_rate_delivery_bindings SET cells_digest=? WHERE episode_id=? AND operation_key=?",
            (repo._delivery_digest(forged), middle.episode_id, key))
        with pytest.raises(ContractError, match="delivery_binding_mismatch"):
            binding.facts(middle, {"committed_record_refs": [sheet]})
        store.db.execute("UPDATE literature_rate_received SET cells=? WHERE episode_id=? AND operation_key=?",
            (canonical(form["numbers"]), middle.episode_id, key))
        # Pre044's current bound C7 has operation/receive/view tables, but no
        # new nonoptical delivery-binding TABLE. Original successful forms and
        # contracts remain; no table, receipt or digest may be backfilled.
        store.db.execute("DROP TABLE literature_rate_delivery_bindings")
        before = list(store.db.iterdump())
        assert repo.received_cells(middle) == form["numbers"]
        repo.receive_cells(middle, form["numbers"], key)
        assert list(store.db.iterdump()) == before
        source_artifacts = {store.get(args["source_ref"])["artifact_ref"]}
        original_dump = list(store.db.iterdump())
        # C4 creates an original controller input, not a controller observation.
        # The separate shared-loop test verifies actual observation accounting.
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM literature_rate_operations").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM runtime_return_admissions").fetchone()[0] == 2
        store.close()
        with Store(tmp_path / "state") as reopened:
            reopened.db.close()
            reopened.db = sqlite3.connect(f"file:{tmp_path / 'state' / 'state.sqlite3'}?mode=ro", uri=True)
            reopened.db.row_factory = sqlite3.Row
            get = reopened.get_artifact
            def saved_only(ref):
                assert ref not in source_artifacts
                return get(ref)
            monkeypatch.setattr(reopened, "get_artifact", saved_only)
            monkeypatch.setattr("gene_annotation_episode.literature_rate_storage.read_rate_table", forbidden)
            monkeypatch.setattr("gene_annotation_episode.literature_rate_storage.populate_rate_contrast", forbidden)
            restored = LiteratureRateRepository(reopened, run)
            _, rebuilt = service_binding(reopened, middle)
            reopened.db.execute("PRAGMA query_only=ON")
            assert rebuilt.facts(middle, {"committed_record_refs": [sheet]})["literature_rate_cells"] == form["numbers"]
            assert restored.received_cells(root) == form["numbers"]
            # C4 always opens a transactional boundary. A read transaction
            # permits nested replay savepoints while query_only forbids writes.
            with reopened.read_snapshot():
                restored_journal = Journal(reopened, run)
                for spec, returned, bound, admitted in ((specs[1], original_child_return, mid_receiver, admitted_middle),
                        (specs[0], original_middle_return, root_receiver, admitted_root)):
                    rebound = replace(bound, store=reopened, journal=restored_journal,
                        receive_references=forbidden, project_received_credit=forbidden, validate_semantics=forbidden)
                    assert admit_return(spec, returned, rebound) == admitted
            assert list(reopened.db.iterdump()) == original_dump
    finally:
        store.close()


@pytest.mark.parametrize("tamper", ["purpose", "delivery", "original_contract", "selection_conflict", "model_purpose", "schema"])
def test_selected_revised_contract_authenticates_redelivery_and_rejects_forged_identity(tmp_path, tamper):
    store, contexts, _, repo, _, binding, journal, contract, specs, archive, form = c4_setup(tmp_path)
    root, middle, leaf = contexts
    try:
        # This models the actual runtime.redeliver selection/attempt records.
        # The revised contract is authorized by that selected decision only.
        original = closed_return(specs[1], archive, form)
        delivery_ref = "original-failed-delivery"
        journal.save("runtime_report_attempts", {"parent_episode_id": middle.episode_id, "decision_index": 8,
            "delivery_ref": delivery_ref, "child_episode_id": leaf.episode_id,
            "contract": canonical(contract.as_record()), "form": None, "failure": canonical({"reason": "maxItems"})})
        revised_schema = deepcopy(FORM)
        revised_schema["properties"]["numbers"]["maxItems"] = 2
        repaired = TypedReportContract("Receive original saved rate subset", revised_schema, lambda *_: True)
        selected = {"kind": "redeliver_report", "delivery_ref": delivery_ref,
            "purpose": repaired.decision, "schema_json": json.dumps(revised_schema)}
        # Actual report repair occurs before runtime_actions publication. Only
        # its selected public decision is durable at this receiving boundary.
        journal.save("runtime_model_calls", {"episode_id": middle.episode_id, "call_index": 9,
            "purpose": "decision", "request": canonical({"synthetic": True}),
            "response": canonical({"selection": selected})})
        journal.save("runtime_report_attempts", {"parent_episode_id": middle.episode_id, "decision_index": 9,
            "delivery_ref": delivery_ref, "child_episode_id": leaf.episode_id,
            "contract": canonical(repaired.as_record()), "form": canonical(form), "failure": None})
        key = middle.run_id + ":" + middle.episode_id + ":9:typed_form"
        repo.receive_cells(middle, form["numbers"], key)
        assert repo.received_cells(middle) == form["numbers"]
        if tamper == "purpose":
            selected["purpose"] = "unselected purpose"
            store.db.execute("UPDATE runtime_model_calls SET response=? WHERE episode_id=? AND call_index=9",
                (canonical({"selection": selected}), middle.episode_id))
        elif tamper == "delivery":
            store.db.execute("UPDATE runtime_report_attempts SET delivery_ref=? WHERE parent_episode_id=? AND decision_index=9",
                ("another-original-delivery", middle.episode_id))
        elif tamper == "original_contract":
            store.db.execute("UPDATE runtime_report_attempts SET contract=? WHERE parent_episode_id=? AND decision_index=8",
                (canonical(repaired.as_record()), middle.episode_id))
        elif tamper == "selection_conflict":
            selected["purpose"] = "conflicting action purpose"
            journal.save("runtime_actions", {"episode_id": middle.episode_id, "decision_index": 9,
                "action": canonical(selected), "result": None, "credit": None})
        elif tamper == "model_purpose":
            store.db.execute("UPDATE runtime_model_calls SET purpose='another_purpose' WHERE episode_id=? AND call_index=9", (middle.episode_id,))
        else:
            selected["schema_json"] = json.dumps(FORM)
            store.db.execute("UPDATE runtime_model_calls SET response=? WHERE episode_id=? AND call_index=9",
                (canonical({"selection": selected}), middle.episode_id))
        with pytest.raises(ContractError, match="delivery_binding_mismatch"):
            repo.received_cells(middle)
    finally:
        store.close()
