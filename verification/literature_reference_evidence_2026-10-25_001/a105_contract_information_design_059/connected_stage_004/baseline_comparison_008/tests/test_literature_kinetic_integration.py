"""Controlled real Episode/C4/provider-text integration; no paper/model science."""
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
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_admission import ReceiverBindingV1, admit_return
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_kinetic_storage import LiteratureKineticRepository, COMPONENTS, kinetic_cells_schema
from gene_annotation_episode.runtime import run_workflow, TypedReportContract
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_episode_admission import Value, seal_return
from test_literature_experimental_prompt_delivery import LiteratureWire, complete, snapshot
from test_literature_kinetic_inputs import Source, SOURCE_REF
from test_literature_kinetic_storage import setup, project
from test_literature_rate_episode_integration import service_binding
from test_runtime import FixtureController, ScriptedProvider


FORM = obj({"numbers": kinetic_cells_schema()})


def reason(store, source_ref):
    raw = store.get_artifact(store.get(source_ref)["artifact_ref"])
    token = b"ProteinFixture"
    first = raw.index(token)
    commit = {k: [] for k in store.reasoning_schema()["required"]}
    commit["source_subjects"] = [{"alias": "source_molecule", "reference_type": "assay", "source_ref": source_ref,
        "label": token.decode(), "anchor": {"source_ref": source_ref, "artifact_ref": store.get(source_ref)["artifact_ref"],
            "start": first, "end": first + len(token), "quote": token.decode()}}]
    return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}


def test_nested_selected_episodes_preserve_only_requested_native_cells_without_extra_observations(tmp_path):
    store, context, args = setup(tmp_path / "state")
    try:
        outer = {**plain(context.assignment), "requested_kinetic_components": list(COMPONENTS)}
        inner = {"version": "strategy_assignment_v1", "question_context_refs": [], "prior_search_refs": [args["source_ref"]],
            "requested_kinetic_components": ["parameter_ratio", "log_parameter_contrast"]}
        def commission(role, assignment):
            return {"selection": {"kind": "episode_child", "role": role, "assignment": assignment,
                "goal": "Compare the synthetic source kinetic parameters", "scope": plain(context.scope),
                "purpose": "Return only requested native parameter contrasts", "schema_json": json.dumps(FORM),
                "initial_report_json": "{}"}, "report_update": {}}
        received = []
        def use(inputs):
            form, = inputs["child_reports"]
            assert [r["component"] for r in form["numbers"]] == ["parameter_ratio", "log_parameter_contrast"]
            assert form["numbers"][0]["value"] == 4
            assert all(r[role]["uncertainty_values"]["delivery_status"] == "not_requested" for r in form["numbers"]
                for role in ("numerator", "denominator"))
            assert all(r["model_reader_capability"] == "unimplemented" for r in form["numbers"])
            received.append(deepcopy(form))
            return reason(store, args["source_ref"])
        provider = ScriptedProvider([commission("literature", outer), commission("literature_strategy", inner),
            {"selection": {"kind": "tool", "tool": "literature.kinetic.populate", "arguments": args}, "report_update": {}}, use, use])
        controllers = []
        def controller(path, initial):
            value = FixtureController(str(path), initial, 1 if len(path) == 3 else 2)
            controllers.append(value)
            return value
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path / "run",
            controller_factory=controller, project_credit=scorer, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=[args["source_ref"]]),), binding_definitions={"credit": scorer.as_record()}))
        assert summary["credit"] == 0 and received[0] == received[1]
        assert len(provider.contexts) == 5 and [c.scores for c in controllers] == [[0, 0], [0, 0], [0]]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 5
        assert store.db.execute("SELECT count(*) FROM literature_kinetic_operations").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM literature_kinetic_received").fetchone()[0] == 2
        assert len([r for r in store.list("source") if r["provider"] == "literature.a105.kinetic_population"]) == 1
        assert not store.list("observation") and not store.list("assessment")
        forms = [json.loads(row[0]) for row in store.db.execute("SELECT form FROM runtime_forms")]
        assert forms == received
    finally:
        store.close()


def uncertainty_setup(path, statistic="sd"):
    extra = "spread SD 0.86421357 s^-1; n=73; technical measurements; CI [10.1357911, 14.2468022] s^-1; 95% confidence"
    store, context, args = setup(path, kind="kcat", unit="s^-1", n="13.57902468", d="1.2342468", extra=extra)
    raw = store.get_artifact(store.get(args["source_ref"])["artifact_ref"]).decode()
    source = Source(raw)
    def bound(value):
        if isinstance(value, dict):
            return {k: bound(v) for k, v in value.items()}
        if isinstance(value, list):
            return [bound(v) for v in value]
        return args["source_ref"] if value == SOURCE_REF else value
    unc = args["numerator"]["uncertainty"]
    def meaning(value):
        return {"value": value, "witnesses": [bound(source.witness(extra))]}
    unc.update(statistic=meaning(statistic), unit_relationship=meaning("same_as_parameter"),
        count=bound(source.number(extra, "73")), repetition_basis=meaning("technical_measurements"))
    if statistic == "sd":
        unc["magnitude"] = bound(source.number(extra, "0.86421357"))
    else:
        literal = "[10.1357911, 14.2468022]"
        unc["interval"] = {"witness": bound(source.witness(literal)), "lower_start": 1,
            "lower_end": literal.index(","), "upper_start": literal.index("14"), "upper_end": len(literal) - 1}
        unc["confidence_level"] = bound(source.witness("95%"))
    # An actual broad condition witness includes a hidden parameter token.
    args["numerator"]["context"]["conditions"] = deepcopy(args["numerator"]["measurement"]["number"]["witness"])
    return store, context, args


@pytest.mark.parametrize("statistic", ["sd", "ci"])
@pytest.mark.parametrize("off_page,parent", [(False, False), (True, False), (False, True), (True, True)])
def test_actual_provider_text_withholds_unrequested_native_canonical_uncertainty_and_broad_labels(tmp_path, statistic, off_page, parent):
    store, context, args = uncertainty_setup(tmp_path / "state", statistic)
    try:
        repo = LiteratureKineticRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        rows = project(repo, outcome, ["parameter_ratio"])
        allrows = project(repo, outcome)
        state = snapshot()
        state["goal"]["objective"] = "Evaluate the admitted source kinetic contrast"
        state["child_reports"] = [{"caller_chosen": rows}]
        state["requested_form"] = FORM
        state["literature_assignment"] = {**plain(context.assignment), "requested_kinetic_components": ["parameter_ratio"]}
        records = store.list("reference")
        unknown = set()
        if off_page:
            unknown = {t["ref"] for r in rows for role in ("numerator", "denominator") for t in r[role]["numeric_tokens"]}
        other_bytes = b"unrelated source definition"
        other_artifact = store.artifact(other_bytes, "text/plain")
        other = store.put("source", {"provider": "synthetic_other_source", "accession": None, "uri": None,
            "artifact_ref": other_artifact, "text_ref": other_artifact, "request_ref": None, "version": None, "retrieved_at": None}, origin="caller")
        label = store.put("reference", {"reference_type": "literature_result", "source_ref": other["id"], "accession": "unrelated",
            "label": "unrelated source definition", "sequence_ref": None, "molecule": None, "length": None, "term_refs": [], "context_refs": [],
            "anchor": {"source_ref": other["id"], "artifact_ref": other_artifact, "start": 0, "end": len(other_bytes), "quote": other_bytes.decode()}}, origin="tool")
        state["working_state"] = {"references": [r for r in [*records, label] if r["id"] not in unknown]}
        state["current_report_basis_refs"] = [label["id"]]
        if parent:
            state.pop("literature_assignment", None)
            state["literature_experimental_work"]["aspect"] = "reference_evidence_parent"
            state["reference_evidence_parent"] = {"version": "reference_evidence_parent_v1", "source_refs": [args["source_ref"]],
                "source_custody": [], "child_population_operations": []}
        wire = LiteratureWire(tmp_path / "wire")
        asyncio.run(complete(wire, state_frame(state)))
        text = wire.turns_sent()[0]["input"][0]["text"]
        assert "Admitted requested kinetic parameter components" in text
        assert str(rows[0]["value"]) in text and "unrelated source definition" in text
        assert "technical_measurements" in text
        for secret in ("13.57902468", "1.2342468", "0.86421357", "10.1357911", "14.2468022", "95%"):
            assert secret not in text
        for value in (allrows[0]["value"], allrows[1]["value"], allrows[2]["value"], allrows[4]["value"]):
            assert str(value) not in text
        assert "| count | 73" not in text and "kinetic_source_token_" not in text
        if not off_page:
            assert "ProteinFixture" in text and "constructX" in text
    finally:
        store.close()


def test_uncertainty_numbers_are_returned_only_with_requested_matching_raw_parameter(tmp_path):
    store, context, args = uncertainty_setup(tmp_path, "ci")
    with store:
        repo = LiteratureKineticRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        ratio, = project(repo, outcome, ["parameter_ratio"])
        for role in ("numerator", "denominator"):
            assert ratio[role]["uncertainty_values"] == {"delivery_status": "not_requested", "magnitude": None,
                "interval": None, "confidence_level": None, "count": None, "count_reported_value": None}
        numerator, = project(repo, outcome, ["numerator_parameter"])
        values = numerator["numerator"]["uncertainty_values"]
        assert values["count"] == 73 and values["confidence_level"] == .95
        assert values["count_reported_value"] == 73
        assert values["interval"] == pytest.approx([608.147466, 854.808132])
        assert numerator["denominator"]["uncertainty_values"]["delivery_status"] == "not_requested"


def test_explicit_uncertainty_unit_survives_missing_parameter_unit_and_saved_only_reopen(tmp_path, monkeypatch):
    store, context, args = uncertainty_setup(tmp_path / "state", "sd")
    args["numerator"]["measurement"]["unit"] = None
    # Select the actual spread unit, while retaining the parameter's unavailable
    # unit. The source reader, rather than the test, supplies all numerical values.
    unc = args["numerator"]["uncertainty"]
    raw = store.get_artifact(store.get(args["source_ref"])["artifact_ref"]).decode()
    extra = "spread SD 0.86421357 s^-1; n=73; technical measurements; CI [10.1357911, 14.2468022] s^-1; 95% confidence"
    start = raw.encode().index(extra.encode()) + len("spread SD 0.86421357 ".encode())
    unc["unit"] = {"source_ref": args["source_ref"], "representation": "original", "start": start,
        "end": start + len("s^-1"), "quote": "s^-1"}
    unc["unit_relationship"]["value"] = "explicit_unit"
    repo = LiteratureKineticRepository(store, context.run_id)
    try:
        outcome = repo.populate(context, args, "selected")
        row, = project(repo, outcome, ["numerator_parameter"])
        assert row["value"] is None and row["unit"] is None and row["numerator"]["canonical_unit"] is None
        assert row["numerator"]["uncertainty"]["canonical_unit"] == "per_min"
        assert row["numerator"]["uncertainty"]["unit_ref"]
        assert row["numerator"]["uncertainty_values"]["magnitude"] == pytest.approx(51.8528142)
        before = list(store.db.iterdump())
        source_artifact = store.get(args["source_ref"])["artifact_ref"]
        store.close()
        def forbidden(*_a, **_kw):raise AssertionError("Saved uncertainty units require no scientific reader/calculator/source")
        monkeypatch.setattr("gene_annotation_episode.literature_kinetic_storage.read_kinetic_inputs", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_kinetic_storage.populate_kinetic_contrast", forbidden)
        with Store(tmp_path / "state") as reopened:
            restored = LiteratureKineticRepository(reopened, context.run_id)
            get = reopened.get_artifact
            monkeypatch.setattr(reopened, "get_artifact", lambda ref: forbidden() if ref == source_artifact else get(ref))
            reopened.db.execute("PRAGMA query_only=ON")
            assert project(restored, outcome, ["numerator_parameter"]) == [row]
            assert list(reopened.db.iterdump()) == before
    finally:
        store.close()


def test_actual_c4_admission_rollback_original_receipt_tamper_and_read_only_reopen(tmp_path, monkeypatch):
    store, seed, args = setup(tmp_path / "state")
    run = seed.run_id
    root_goal = EpisodeGoal.root(objective="Evaluate synthetic native evidence", result_contract={})
    child_goal = EpisodeGoal.child(root_goal, objective="Compare native kinetic parameters", result_contract={})
    parent_path, child_path = [["annotation", "root"]], [["annotation", "root"], ["literature", "kinetic"]]
    parent_id, child_id = EpisodeRef(run, parent_path).episode_id, EpisodeRef(run, child_path).episode_id
    assignment = {**plain(seed.assignment), "requested_kinetic_components": ["parameter_ratio"]}
    child = replace(seed, episode_id=child_id, path=tuple(tuple(p) for p in child_path), assignment=assignment)
    parent = replace(seed, episode_id=parent_id, role="annotation", path=(("annotation", "root"),), assignment={})
    repo = LiteratureKineticRepository(store, run)
    outcome = repo.populate(child, args, "selected")
    child = replace(child, received_record_refs=(*child.received_record_refs, *outcome["record_refs"]))
    _, binding = service_binding(store, child)
    rows = binding.facts(child, {"committed_record_refs": [outcome["result"]["sheet_ref"]]})["literature_kinetic_cells"]
    form = {"numbers": rows}
    contract = TypedReportContract("Receive native kinetic contrast", FORM, lambda *_: True)
    parent_request = {"goal": root_goal.as_record(), "message": {"scope": plain(seed.scope)}, "report_contract": None}
    request = {"goal": child_goal.as_record(), "message": {"scope": plain(seed.scope), "episode_assignment": assignment}, "report_contract": contract.as_record()}
    journal = Journal(store, run)
    for eid, path, req, state in ((parent_id, parent_path, parent_request, "active"), (child_id, child_path, request, "yielded")):
        journal.save("runtime_episodes", {"episode_id": eid, "path": canonical(path), "request": canonical(req),
            "initial_credit": 0, "state": state, "completion": None, "archive": None})
    spec = {"version": "episode_commission_v1", "handle": "original-kinetic-handle", "operation_key": "original-commission", "run_id": run,
        "parent": {"episode_id": parent_id, "goal_id": root_goal.goal_id, "path": parent_path},
        "child": {"episode_id": child_id, "role": "literature", "key": "kinetic", "path": child_path, "request": request, "scope": plain(seed.scope)},
        "input_versions": [], "runtime_binding": {"factory_module": "fixture", "factory_name": "open_commission", "arguments": {},
            "implementation_sha256": "a" * 64, "settings_sha256": "b" * 64}, "constraints": {}, "resource_selection": None, "expectation_snapshot_refs": []}
    journal.save("runtime_actions", {"episode_id": parent_id, "decision_index": 7, "action": canonical({"kind": "episode_child", "role": "literature"}),
        "result": canonical({"status": "pending", "pending_handle": spec["handle"]}), "credit": None})
    journal.save("runtime_forms", {"episode_id": child_id, "facts": canonical({"literature_kinetic_cells": rows, "changed_record_refs": outcome["changed_record_refs"]}), "form": canonical(form)})
    archive = JsonArchive(tmp_path / "archive")
    returned = {"version": "returned_episode_v1", "handle": spec["handle"], "return_id": "", "commission_sha256": content_digest(spec),
        "returned_at": "2026-10-26T12:00:00+00:00", "outcome": "closed", "completion": {"ended_by": "yield_stop", "end_reason": "", "units_consumed": 1},
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
            raise OSError("interrupted after kinetic receipt")
        monkeypatch.setattr(bound_repo, "receive_cells", interrupted)
        with pytest.raises(OSError):
            admit_return(spec, returned, receiver)
        assert repo.received_cells(parent) == []
        monkeypatch.setattr(bound_repo, "receive_cells", original)
        admitted = admit_return(spec, returned, receiver)
        assert admitted["state"] == "admitted" and admitted["report"] == form
        parent = replace(parent, received_record_refs=tuple(dict.fromkeys([*parent.received_record_refs, *admitted["received_record_refs"]])))
        assert binding.received_report_facts(parent)["literature_kinetic_cells"] == rows
        forged = project(repo, outcome, ["numerator_parameter"])
        store.db.execute("UPDATE literature_kinetic_received SET cells=?", (canonical(forged),))
        store.db.execute("UPDATE literature_kinetic_delivery_bindings SET cells_digest=?", (repo._delivery_digest(forged),))
        with pytest.raises(ContractError, match="delivery_binding_mismatch"):
            repo.received_cells(parent)
        store.db.execute("UPDATE literature_kinetic_received SET cells=?", (canonical(rows),))
        store.db.execute("UPDATE literature_kinetic_delivery_bindings SET cells_digest=?", (repo._delivery_digest(rows),))
        before = list(store.db.iterdump())
        source_artifact = store.get(args["source_ref"])["artifact_ref"]
        store.close()
        def forbidden(*_a, **_kw):
            raise AssertionError("saved reconstruction must not read science, calculate, receive again or reprice")
        monkeypatch.setattr("gene_annotation_episode.literature_kinetic_storage.read_kinetic_inputs", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_kinetic_storage.populate_kinetic_contrast", forbidden)
        with Store(tmp_path / "state") as reopened:
            restored = LiteratureKineticRepository(reopened, run)
            _, rebuilt = service_binding(reopened, child)
            rebuilt.received_report_facts(parent)
            restored_journal = Journal(reopened, run)
            reopened.db.close()
            reopened.db = sqlite3.connect((tmp_path / "state/state.sqlite3").resolve().as_uri() + "?mode=ro", uri=True, isolation_level=None)
            reopened.db.row_factory = sqlite3.Row
            restored_journal.db = reopened.db
            get = reopened.get_artifact
            monkeypatch.setattr(reopened, "get_artifact", lambda ref: forbidden() if ref == source_artifact else get(ref))
            assert restored.received_cells(parent) == rows
            rebound = replace(receiver, store=reopened, journal=restored_journal, receive_references=forbidden,
                project_received_credit=forbidden, validate_semantics=forbidden)
            with reopened.read_snapshot():
                assert admit_return(spec, returned, rebound) == admitted
            assert list(reopened.db.iterdump()) == before
            assert reopened.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
    finally:
        store.close()
