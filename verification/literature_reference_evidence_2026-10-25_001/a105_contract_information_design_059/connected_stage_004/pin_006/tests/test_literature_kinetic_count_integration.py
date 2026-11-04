"""Selected synthetic Episodes, actual provider text and original typed custody."""
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
from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_admission import ReceiverBindingV1, admit_return
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_kinetic_storage import LiteratureKineticRepository, kinetic_cells_schema
from gene_annotation_episode.runtime import run_workflow, TypedReportContract
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_episode_admission import Value, seal_return
from test_literature_experimental_prompt_delivery import LiteratureWire, complete, snapshot
from test_literature_kinetic_count_inputs import bind_count
from test_literature_kinetic_inputs import Source
from test_literature_kinetic_integration import reason
from test_literature_kinetic_storage import setup, project
from test_literature_rate_episode_integration import service_binding
from test_runtime import FixtureController, ScriptedProvider


FORM = obj({"numbers": kinetic_cells_schema()})


def count_setup(path, expression="three", numeral="three", *, broad=False):
    extra = "Synthetic count " + ("plain context " * 70 if broad else "") + expression + " independent experiments"
    store, context, args = setup(path, extra=extra)
    raw = store.get_artifact(store.get(args["source_ref"])["artifact_ref"]).decode()
    bind_count(args, raw, extra, numeral)
    if broad:
        witness = Source(raw).witness(extra)
        witness["source_ref"] = args["source_ref"]
        args["numerator"]["context"]["conditions"] = witness
    return store, context, args


def forbid_science(monkeypatch):
    def forbidden(*_a, **_kw):
        raise AssertionError("Saved parent reconstruction must not reacquire source, read counts, recalculate, receive or reprice")
    monkeypatch.setattr("gene_annotation_episode.literature_kinetic_inputs._count_reading", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_kinetic_storage.read_kinetic_inputs", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_kinetic_storage.populate_kinetic_contrast", forbidden)
    monkeypatch.setattr(LiteratureKineticRepository, "receive_cells", forbidden)
    return forbidden


def make_readonly(store, path):
    store.db.close()
    store.db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, isolation_level=None)
    store.db.row_factory = sqlite3.Row
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        store.db.execute("CREATE TABLE forbidden_count_reconstruction_write(value TEXT)")


@pytest.mark.parametrize("expression,numeral,exact,status", [
    ("three", "three", 3, "exact"), ("at least three", "three", None, "qualified"),
    ("triplicate", "triplicate", None, "unsupported"),
    ("three or four", "three or four", None, "range_or_alternatives"),
])
def test_selected_episode_returns_count_meaning_without_internal_observations(tmp_path, monkeypatch, expression, numeral, exact, status):
    path = tmp_path / "state"
    store, seed, args = count_setup(path, expression, numeral)
    try:
        assignment = {**plain(seed.assignment), "requested_kinetic_components": ["numerator_parameter", "parameter_ratio"]}
        received, controllers = [], []
        def consume(inputs):
            form, = inputs["child_reports"]
            received.append(deepcopy(form))
            raw, ratio = form["numbers"]
            assert [raw["component"], ratio["component"]] == ["numerator_parameter", "parameter_ratio"]
            assert raw["value"] == 8 and ratio["value"] == 4
            assert raw["numerator"]["uncertainty_values"]["count"] == exact
            assert raw["numerator"]["uncertainty"]["count_reading_status"] == status
            assert raw["numerator"]["uncertainty"]["repetition_basis"] == "unspecified"
            assert ratio["numerator"]["uncertainty_values"]["count"] is None
            assert ratio["numerator"]["uncertainty_values"]["count_reported_value"] is None
            return reason(store, args["source_ref"])
        provider = ScriptedProvider([
            {"selection": {"kind": "episode_child", "role": "literature", "assignment": assignment,
                "goal": "Return the requested synthetic kinetic comparison and preserve the reported repetition meaning",
                "scope": plain(seed.scope), "purpose": "Return exact saved values and source count qualifications",
                "schema_json": json.dumps(FORM), "initial_report_json": "{}"}, "report_update": {}},
            {"selection": {"kind": "tool", "tool": "literature.kinetic.populate", "arguments": args}, "report_update": {}},
            consume,
        ])
        def controller(path, initial):
            item = FixtureController(str(path), initial, 1 if len(path) == 2 else 2)
            controllers.append(item)
            return item
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path / "run",
            controller_factory=controller, project_credit=scorer, initial_known_record_refs=list(seed.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=[args["source_ref"]]),), binding_definitions={"credit": scorer.as_record()}))
        assert summary["credit"] == 0
        assert len(received) == 1 and len(provider.contexts) == 3
        assert [c.scores for c in controllers] == [[0, 0], [0]]
        assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 3
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 3
        assert store.db.execute("SELECT count(*) FROM literature_kinetic_operations").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM literature_kinetic_received").fetchone()[0] == 1
        assert not store.list("observation") and not store.list("assessment")
        operation = store.db.execute("SELECT outcome FROM literature_kinetic_operations").fetchone()
        outcome = json.loads(operation["outcome"])
        saved = LiteratureKineticRepository(store, summary["run_id"]).read(outcome["result"]["sheet_ref"])
        assert saved["calculation"]["independent_preparation_count"] is None
        assert saved["calculation"]["model"] is None
        admission = store.db.execute("SELECT episode_id,cells FROM literature_kinetic_received").fetchone()
        assert json.loads(admission["cells"]) == received[0]["numbers"]
        parent = BindingContext(summary["run_id"], admission["episode_id"], "annotation", (("annotation", "root"),),
            seed.scope, {}, {}, tuple(dict.fromkeys([*seed.received_record_refs, *outcome["record_refs"]])))
        before = list(store.db.iterdump())
        source_artifact = store.get(args["source_ref"])["artifact_ref"]
        store.close()
        forbidden = forbid_science(monkeypatch)
        with Store(path) as reopened:
            make_readonly(reopened, path / "state.sqlite3")
            get = reopened.get_artifact
            monkeypatch.setattr(reopened, "get_artifact", lambda ref: forbidden() if ref == source_artifact else get(ref))
            rebuilt_repo = LiteratureKineticRepository(reopened, summary["run_id"])
            _, rebuilt = service_binding(reopened, parent)
            assert rebuilt_repo.read(outcome["result"]["sheet_ref"]) == saved
            assert rebuilt.received_report_facts(parent)["literature_kinetic_cells"] == received[0]["numbers"]
            assert list(reopened.db.iterdump()) == before
            assert reopened.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 3
    finally:
        store.close()


@pytest.mark.parametrize("qualified", [False, True])
@pytest.mark.parametrize("raw_requested,off_page,parent", [(False, False, False), (False, True, False),
    (False, False, True), (False, True, True), (True, False, False), (True, True, True)])
def test_actual_provider_transport_preserves_count_qualification_and_masks_unrequested_words(tmp_path, qualified, raw_requested, off_page, parent):
    word = "seventy-three"
    store, context, args = count_setup(tmp_path / "state", "at least " + word if qualified else word, word, broad=True)
    try:
        repo = LiteratureKineticRepository(store, context.run_id)
        outcome = repo.populate(context, args, "count-text")
        components = ["numerator_parameter"] if raw_requested else ["parameter_ratio"]
        rows = project(repo, outcome, components)
        condition = store.get(rows[0]["numerator"]["context"]["conditions"])
        assert len(condition["anchor"]["quote"]) > 512
        assert word in condition["anchor"]["quote"] and word not in condition["label"]
        assert condition["label"].startswith("[source witness preview] ")
        records = store.list("reference")
        hidden = {token["ref"] for row in rows for role in ("numerator", "denominator") for token in row[role]["numeric_tokens"]} if off_page else set()
        unrelated_raw = b"unrelated experimental definition"
        unrelated_artifact = store.artifact(unrelated_raw, "text/plain")
        other = store.put("source", {"provider": "synthetic_unrelated", "accession": None, "uri": None,
            "artifact_ref": unrelated_artifact, "text_ref": unrelated_artifact, "request_ref": None,
            "version": None, "retrieved_at": None}, origin="caller")
        unrelated = store.put("reference", {"reference_type": "literature_result", "source_ref": other["id"],
            "accession": "unrelated", "label": unrelated_raw.decode(), "sequence_ref": None, "molecule": None,
            "length": None, "term_refs": [], "context_refs": [], "anchor": {"source_ref": other["id"],
                "artifact_ref": unrelated_artifact, "start": 0, "end": len(unrelated_raw), "quote": unrelated_raw.decode()}}, origin="tool")
        state = snapshot()
        state["goal"]["objective"] = "Evaluate the admitted synthetic source contrast and count qualification"
        state["child_reports"] = [{"requested_numbers": rows}]
        state["requested_form"] = FORM
        state["literature_assignment"] = {**plain(context.assignment), "requested_kinetic_components": components}
        state["working_state"] = {"references": [row for row in [*records, unrelated] if row["id"] not in hidden]}
        state["current_report_basis_refs"] = [unrelated["id"]]
        if parent:
            state.pop("literature_assignment")
            state["literature_experimental_work"]["aspect"] = "reference_evidence_parent"
            state["reference_evidence_parent"] = {"version": "reference_evidence_parent_v1", "source_refs": [args["source_ref"]],
                "source_custody": [], "child_population_operations": []}
        wire = LiteratureWire(tmp_path / "wire")
        asyncio.run(complete(wire, state_frame(state)))
        shown = wire.turns_sent()[0]["input"][0]["text"]
        assert "| count_reading_status | " + ("qualified" if qualified else "exact") + " |" in shown
        assert "| count_relation | " + ("ge" if qualified else "point") + " |" in shown
        assert "| count_notation | english_cardinal |" in shown
        assert word not in shown and "unrelated experimental definition" in shown
        assert "kinetic_source_token_" not in shown
        if raw_requested:
            assert "| count_reported_value | 73 |" in shown
            assert "| count | " + ("unknown" if qualified else "73") + " |" in shown
        else:
            assert "| count_reported_value | 73 |" not in shown and "| count | 73 |" not in shown
    finally:
        store.close()


def test_original_c4_count_admission_reopens_readonly_without_reinterpretation_or_receipt(tmp_path, monkeypatch):
    path = tmp_path / "state"
    store, seed, args = count_setup(path, "at least seventy-three", "seventy-three")
    run = seed.run_id
    root_goal = EpisodeGoal.root(objective="Evaluate a synthetic counted source estimate", result_contract={})
    child_goal = EpisodeGoal.child(root_goal, objective="Return only the requested source parameter", result_contract={})
    parent_path, child_path = [["annotation", "root"]], [["annotation", "root"], ["literature", "count"]]
    parent_id, child_id = EpisodeRef(run, parent_path).episode_id, EpisodeRef(run, child_path).episode_id
    assignment = {**plain(seed.assignment), "requested_kinetic_components": ["numerator_parameter"]}
    child = replace(seed, episode_id=child_id, path=tuple(tuple(p) for p in child_path), assignment=assignment)
    parent = replace(seed, episode_id=parent_id, role="annotation", path=(("annotation", "root"),), assignment={})
    repo = LiteratureKineticRepository(store, run)
    outcome = repo.populate(child, args, "count-selected")
    child = replace(child, received_record_refs=(*child.received_record_refs, *outcome["record_refs"]))
    _, binding = service_binding(store, child)
    rows = binding.facts(child, {"committed_record_refs": [outcome["result"]["sheet_ref"]]})["literature_kinetic_cells"]
    assert len(rows) == 1
    assert rows[0]["numerator"]["uncertainty_values"]["count"] is None
    assert rows[0]["numerator"]["uncertainty_values"]["count_reported_value"] == 73
    assert rows[0]["numerator"]["uncertainty"]["count_relation"] == "ge"
    form = {"numbers": rows}
    contract = TypedReportContract("Receive the requested synthetic parameter and count qualification", FORM, lambda *_: True)
    parent_request = {"goal": root_goal.as_record(), "message": {"scope": plain(seed.scope)}, "report_contract": None}
    request = {"goal": child_goal.as_record(), "message": {"scope": plain(seed.scope), "episode_assignment": assignment},
        "report_contract": contract.as_record()}
    journal = Journal(store, run)
    for eid, path_parts, req, state in ((parent_id, parent_path, parent_request, "active"), (child_id, child_path, request, "yielded")):
        journal.save("runtime_episodes", {"episode_id": eid, "path": canonical(path_parts), "request": canonical(req),
            "initial_credit": 0, "state": state, "completion": None, "archive": None})
    spec = {"version": "episode_commission_v1", "handle": "original-count-handle", "operation_key": "original-count-commission", "run_id": run,
        "parent": {"episode_id": parent_id, "goal_id": root_goal.goal_id, "path": parent_path},
        "child": {"episode_id": child_id, "role": "literature", "key": "count", "path": child_path, "request": request, "scope": plain(seed.scope)},
        "input_versions": [], "runtime_binding": {"factory_module": "fixture", "factory_name": "open_commission", "arguments": {},
            "implementation_sha256": "a" * 64, "settings_sha256": "b" * 64}, "constraints": {}, "resource_selection": None,
        "expectation_snapshot_refs": []}
    journal.save("runtime_actions", {"episode_id": parent_id, "decision_index": 7,
        "action": canonical({"kind": "episode_child", "role": "literature"}),
        "result": canonical({"status": "pending", "pending_handle": spec["handle"]}), "credit": None})
    journal.save("runtime_forms", {"episode_id": child_id,
        "facts": canonical({"literature_kinetic_cells": rows, "changed_record_refs": outcome["changed_record_refs"]}), "form": canonical(form)})
    archive = JsonArchive(tmp_path / "archive")
    returned = {"version": "returned_episode_v1", "handle": spec["handle"], "return_id": "", "commission_sha256": content_digest(spec),
        "returned_at": "2026-10-26T12:00:00+00:00", "outcome": "closed",
        "completion": {"ended_by": "yield_stop", "end_reason": "", "units_consumed": 1},
        "episode_archive": archive.store({"synthetic": True}).descriptor(), "result_archive": archive.store({"form": form}).descriptor(),
        "form": form, "facts_archive": archive.store({"literature_kinetic_cells": rows}).descriptor(), "pending_handles": [], "failure": None}
    seal_return(returned)
    key = run + ":" + parent_id + ":7:typed_form"
    def receive(value):
        binding.received_form_references(parent, value, FORM, key)
        return outcome["record_refs"]
    receiver = ReceiverBindingV1(store, journal, 7, contract, lambda value: binding.validate_report(child, value, FORM),
        receive, lambda: 0, lambda index, credit: Value({"credit": credit, "estimation_action_index": index}))
    try:
        bound_repo = binding.services.literature_kinetic_repository()
        original = bound_repo.receive_cells
        def interrupted(*a, **kw):
            original(*a, **kw)
            raise OSError("interrupted after count receipt")
        monkeypatch.setattr(bound_repo, "receive_cells", interrupted)
        with pytest.raises(OSError):
            admit_return(spec, returned, receiver)
        assert repo.received_cells(parent) == []
        monkeypatch.setattr(bound_repo, "receive_cells", original)
        admitted = admit_return(spec, returned, receiver)
        assert admitted["state"] == "admitted" and admitted["report"] == form
        parent = replace(parent, received_record_refs=tuple(dict.fromkeys([*parent.received_record_refs, *admitted["received_record_refs"]])))
        assert binding.received_report_facts(parent)["literature_kinetic_cells"] == rows
        forged = deepcopy(rows)
        forged[0]["numerator"]["uncertainty_values"]["count_reported_value"] = 999
        store.db.execute("UPDATE literature_kinetic_received SET cells=?", (canonical(forged),))
        store.db.execute("UPDATE literature_kinetic_delivery_bindings SET cells_digest=?", (repo._delivery_digest(forged),))
        with pytest.raises(ContractError, match="delivery_binding_mismatch"):
            repo.received_cells(parent)
        store.db.execute("UPDATE literature_kinetic_received SET cells=?", (canonical(rows),))
        store.db.execute("UPDATE literature_kinetic_delivery_bindings SET cells_digest=?", (repo._delivery_digest(rows),))
        before = list(store.db.iterdump())
        source_artifact = store.get(args["source_ref"])["artifact_ref"]
        store.close()
        forbidden = forbid_science(monkeypatch)
        with Store(path) as reopened:
            make_readonly(reopened, path / "state.sqlite3")
            get = reopened.get_artifact
            monkeypatch.setattr(reopened, "get_artifact", lambda ref: forbidden() if ref == source_artifact else get(ref))
            restored = LiteratureKineticRepository(reopened, run)
            _, rebuilt = service_binding(reopened, child)
            restored_journal = Journal(reopened, run)
            # First reconstruction occurs after source/science prohibition and
            # the actual mode=ro connection; no facts/receipt cache is prewarmed.
            assert rebuilt.received_report_facts(parent)["literature_kinetic_cells"] == rows
            assert restored.received_cells(parent) == rows
            rebound = replace(receiver, store=reopened, journal=restored_journal, receive_references=forbidden,
                project_received_credit=forbidden, validate_semantics=forbidden, make_controller_input=forbidden)
            with reopened.read_snapshot():
                assert admit_return(spec, returned, rebound) == admitted
            assert list(reopened.db.iterdump()) == before
            assert reopened.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
    finally:
        store.close()
