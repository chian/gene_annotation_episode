"""Synthetic witness display/publication boundaries; no paper or model science."""
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
from gene_annotation_episode.domain import ContractError, LABEL, canonical, identity, obj, validate_schema
from gene_annotation_episode.episode_admission import ReceiverBindingV1, admit_return
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_kinetic_calculations import populate_kinetic_contrast
from gene_annotation_episode.literature_kinetic_inputs import read_kinetic_inputs
from gene_annotation_episode.literature_kinetic_storage import LiteratureKineticRepository, COMPONENTS, kinetic_cells_schema
from gene_annotation_episode.runtime import TypedReportContract, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_episode_admission import Value, seal_return
from test_literature_experimental_prompt_delivery import LiteratureWire, complete, snapshot
from test_literature_kinetic_inputs import Source, SOURCE_REF
from test_literature_kinetic_integration import reason
from test_literature_kinetic_storage import setup, project
from test_literature_rate_episode_integration import service_binding
from test_runtime import FixtureController, ScriptedProvider


FORM = obj({"numbers": kinetic_cells_schema()})
PREVIEW = "[source witness preview] "


def witness_for(store, args, literal):
    raw = store.get_artifact(store.get(args["source_ref"])["artifact_ref"])
    witness = Source(raw.decode()).witness(literal)
    witness["source_ref"] = args["source_ref"]
    return witness


def expected_native(store, args):
    def read(reference, representation):
        source = store.get(reference)
        artifact = source["artifact_ref" if representation == "original" else "text_ref"]
        return {"artifact_ref": artifact, "content": store.get_artifact(artifact)}
    extraction = read_kinetic_inputs(args, read_source=read)
    return extraction, populate_kinetic_contrast(extraction["calculation_inputs"])


@pytest.mark.parametrize("literal", [
    "x" * 511, "x" * 512, "x" * 513,
    "Condition: " + "x" * 600,
    "Condition: first line\nsecond line",
    "Condition: first line\r\nsecond line",
    "μ Conditions\n" + "βγ " * 300,
    "μ" * 16000,
    "Short μ witness\twith  spacing",
])
def test_native_publication_preserves_full_witness_and_all_scientific_values(tmp_path, literal):
    store, context, args = setup(tmp_path, extra=literal)
    with store:
        witness = witness_for(store, args, literal)
        args["numerator"]["context"]["conditions"] = deepcopy(witness)
        # The same publication helper serves both literal and interpreted
        # source definitions, not just the conditions column that exposed it.
        args["numerator"]["subject"]["construct"] = deepcopy(witness)
        args["comparison"]["subject_relationship"]["witnesses"] = [deepcopy(witness)]
        for role in ("numerator", "denominator"):
            args[role]["measurement_identity"] = deepcopy(args[role]["measurement"]["number"]["witness"])
        expected_extraction, expected_calculation = expected_native(store, args)
        nominated = deepcopy(args)
        repo = LiteratureKineticRepository(store, context.run_id)
        outcome = repo.populate(context, args, "full-witness")
        saved = repo.read(outcome["result"]["sheet_ref"])
        assert args == nominated == saved["selection"]
        assert saved["extraction"] == expected_extraction
        assert saved["calculation"] == expected_calculation
        assert saved["cells"] == {k: expected_calculation["cells"][k] for k in COMPONENTS}
        assert saved["cells"]["parameter_ratio"]["value"] == 4
        refs = [saved["role_bindings"]["numerator"]["context"]["conditions"],
                saved["role_bindings"]["numerator"]["subject"]["construct"],
                saved["comparison_bindings"]["subject_relationship"]["witness_refs"][0]]
        for reference in refs:
            record = store.get(reference)
            validate_schema(record["label"], LABEL)
            anchor = record["anchor"]
            assert anchor == {k: expected_extraction["operands"]["numerator"]["context"]["conditions"][k]
                for k in ("source_ref", "artifact_ref", "start", "end", "quote")}
            assert anchor["quote"] == literal
            assert store.get_artifact(anchor["artifact_ref"])[anchor["start"]:anchor["end"]] == literal.encode()
            store._anchor(anchor, args["source_ref"])
            if len(literal) <= 512 and "\n" not in literal and "\r" not in literal:
                assert record["label"] == literal
            else:
                assert record["label"].startswith(PREVIEW)
                normalized = " ".join(literal.split())
                available = 512 - len(PREVIEW)
                assert record["label"] == PREVIEW + (normalized if len(normalized) <= available
                    else normalized[:available - 1] + "…")
        # Scientific accession identity still uses the complete original anchor.
        record = store.get(refs[0])
        assert record["accession"] == identity("kinetic_conditions", record["anchor"])
        for role in ("numerator", "denominator"):
            number = store.get(saved["role_bindings"][role]["measurement_ref"])
            assert number["label"] == number["anchor"]["quote"] == ("8" if role == "numerator" else "2")
        assert not store.list("observation") and not store.list("assessment")


def wide_setup(path):
    extra = "Context μ\n" + "condition " * 80 + (
        "spread SD 0.86421357 s^-1; n=73; technical measurements; "
        "CI [10.1357911, 14.2468022] s^-1; 95% confidence")
    store, context, args = setup(path, kind="kcat", unit="s^-1", n="13.57902468", d="1.2342468", extra=extra)
    source = Source(store.get_artifact(store.get(args["source_ref"])["artifact_ref"]).decode())
    def bound(value):
        if isinstance(value, dict):
            return {k: bound(v) for k, v in value.items()}
        if isinstance(value, list):
            return [bound(v) for v in value]
        return args["source_ref"] if value == SOURCE_REF else value
    def meaning(value):
        return {"value": value, "witnesses": [bound(source.witness(extra))]}
    args["numerator"]["uncertainty"].update(statistic=meaning("sd"),
        unit_relationship=meaning("same_as_parameter"),
        magnitude=bound(source.number(extra, "0.86421357")),
        count=bound(source.number(extra, "73")), repetition_basis=meaning("technical_measurements"))
    complete_source = bound(source.witness(source.raw.decode()))
    for role in ("numerator", "denominator"):
        args[role]["context"]["conditions"] = deepcopy(complete_source)
        args[role]["measurement_identity"] = deepcopy(args[role]["measurement"]["number"]["witness"])
    return store, context, args


def test_actual_selected_episode_delivery_has_only_original_actions_and_requested_cells(tmp_path):
    store, context, args = wide_setup(tmp_path / "state")
    try:
        assignment = {**plain(context.assignment), "requested_kinetic_components": ["parameter_ratio", "log_parameter_contrast"]}
        received = []
        def use(inputs):
            form, = inputs["child_reports"]
            assert [r["component"] for r in form["numbers"]] == assignment["requested_kinetic_components"]
            assert form["numbers"][0]["value"] == pytest.approx(13.57902468 / 1.2342468)
            assert all(row[role]["uncertainty_values"]["delivery_status"] == "not_requested"
                for row in form["numbers"] for role in ("numerator", "denominator"))
            received.append(deepcopy(form))
            return reason(store, args["source_ref"])
        provider = ScriptedProvider([
            {"selection": {"kind": "episode_child", "role": "literature", "assignment": assignment,
                "goal": "Compare synthetic source kinetic parameters", "scope": plain(context.scope),
                "purpose": "Return requested contrasts with source qualifications", "schema_json": json.dumps(FORM),
                "initial_report_json": "{}"}, "report_update": {}},
            {"selection": {"kind": "tool", "tool": "literature.kinetic.populate", "arguments": args}, "report_update": {}}, use])
        controllers = []
        def controller(path, initial):
            value = FixtureController(str(path), initial, 1 if len(path) == 2 else 2)
            controllers.append(value)
            return value
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path / "run",
            controller_factory=controller, project_credit=scorer, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=[args["source_ref"]]),), binding_definitions={"credit": scorer.as_record()}))
        assert summary["credit"] == 0 and len(received) == 1
        assert [c.scores for c in controllers] == [[0, 0], [0]]
        assert len(provider.contexts) == 3
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 3
        assert store.db.execute("SELECT count(*) FROM literature_kinetic_operations").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM literature_kinetic_received").fetchone()[0] == 1
        assert [json.loads(r[0]) for r in store.db.execute("SELECT form FROM runtime_forms")] == received
        assert not store.list("observation") and not store.list("assessment")
    finally:
        store.close()


@pytest.mark.parametrize("off_page,parent", [(False, False), (True, False), (False, True), (True, True)])
def test_full_anchor_masks_unrequested_numbers_before_and_beyond_display_preview(tmp_path, off_page, parent):
    store, context, args = wide_setup(tmp_path / "state")
    try:
        repo = LiteratureKineticRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        rows = project(repo, outcome, ["parameter_ratio"])
        allrows = project(repo, outcome)
        broad = store.get(rows[0]["numerator"]["context"]["conditions"])
        assert "13.57902468" in broad["label"]
        assert "0.86421357" not in broad["label"] and "0.86421357" in broad["anchor"]["quote"]
        assert broad["label"].startswith(PREVIEW) and broad["label"].endswith("…")
        state = snapshot()
        state["goal"]["objective"] = "Evaluate the admitted synthetic kinetic contrast"
        state["child_reports"] = [{"selected_numbers": rows}]
        state["requested_form"] = FORM
        state["literature_assignment"] = {**plain(context.assignment), "requested_kinetic_components": ["parameter_ratio"]}
        hidden = {token["ref"] for row in rows for role in ("numerator", "denominator")
            for token in row[role]["numeric_tokens"]} if off_page else set()
        state["working_state"] = {"references": [r for r in store.list("reference") if r["id"] not in hidden]}
        state["current_report_basis_refs"] = [broad["id"]]
        if parent:
            state.pop("literature_assignment")
            state["literature_experimental_work"]["aspect"] = "reference_evidence_parent"
            state["reference_evidence_parent"] = {"version": "reference_evidence_parent_v1",
                "source_refs": [args["source_ref"]], "source_custody": [], "child_population_operations": []}
        wire = LiteratureWire(tmp_path / "wire")
        asyncio.run(complete(wire, state_frame(state)))
        text = wire.turns_sent()[0]["input"][0]["text"]
        assert "Admitted requested kinetic parameter components" in text and str(rows[0]["value"]) in text
        assert "technical_measurements" in text
        for secret in ("13.57902468", "1.2342468", "0.86421357", "10.1357911", "14.2468022", "95%"):
            assert secret not in text
        for row in (allrows[0], allrows[1], allrows[2], allrows[4]):
            assert str(row["value"]) not in text
        assert "| count | 73" not in text
    finally:
        store.close()


@pytest.mark.parametrize("mismatch", ["quote", "offset"])
def test_preview_does_not_accept_wrong_source_bytes_or_intervals(tmp_path, mismatch):
    literal = "Condition μ\n" + "x" * 600
    store, context, args = setup(tmp_path, extra=literal)
    with store:
        witness = witness_for(store, args, literal)
        witness["quote"] = witness["quote"].replace("μ", "β") if mismatch == "quote" else witness["quote"]
        if mismatch == "offset":
            witness["start"] += 1
            witness["end"] += 1
        args["numerator"]["context"]["conditions"] = witness
        repo = LiteratureKineticRepository(store, context.run_id)
        before = list(store.db.iterdump())
        with pytest.raises(ValueError):
            repo.populate(context, args, "bad-witness")
        assert list(store.db.iterdump()) == before
        assert store.db.execute("SELECT count(*) FROM literature_kinetic_operations").fetchone()[0] == 0


@pytest.mark.parametrize("target", ["label", "anchor"])
def test_saved_preview_and_full_anchor_tampering_are_rejected(tmp_path, target):
    store, context, args = wide_setup(tmp_path)
    with store:
        repo = LiteratureKineticRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        saved = repo.read(outcome["result"]["sheet_ref"])
        reference = saved["role_bindings"]["numerator"]["context"]["conditions"]
        record = store.get(reference)
        if target == "label":
            record["label"] = "forged display preview"
        else:
            record["anchor"]["quote"] = record["label"]
        store.db.execute("UPDATE records SET data=? WHERE id=?", (canonical(record), reference))
        with pytest.raises(ContractError, match="binding_mismatch"):
            repo.read(outcome["result"]["sheet_ref"])


def test_actual_c4_saved_only_reconstruction_is_read_only_and_keeps_exact_witnesses(tmp_path, monkeypatch):
    store, seed, args = wide_setup(tmp_path / "state")
    run = seed.run_id
    root_goal = EpisodeGoal.root(objective="Evaluate synthetic source evidence", result_contract={})
    child_goal = EpisodeGoal.child(root_goal, objective="Compare synthetic parameters", result_contract={})
    parent_path, child_path = [["annotation", "root"]], [["annotation", "root"], ["literature", "kinetic"]]
    parent_id, child_id = EpisodeRef(run, parent_path).episode_id, EpisodeRef(run, child_path).episode_id
    assignment = {**plain(seed.assignment), "requested_kinetic_components": ["parameter_ratio"]}
    child = replace(seed, episode_id=child_id, path=tuple(map(tuple, child_path)), assignment=assignment)
    parent = replace(seed, episode_id=parent_id, role="annotation", path=tuple(map(tuple, parent_path)), assignment={})
    _, binding = service_binding(store, child)
    # Execute through the installed selected-operation binding, not a fake row.
    outcome = asyncio.run(binding.execute(child, "literature.kinetic.populate", args, "selected"))
    assert outcome["status"] == "completed"
    child = replace(child, received_record_refs=(*child.received_record_refs, *outcome["record_refs"]))
    repo = binding.services.literature_kinetic_repository()
    saved = repo.read(outcome["result"]["sheet_ref"])
    rows = binding.facts(child, {"committed_record_refs": [outcome["result"]["sheet_ref"]]})["literature_kinetic_cells"]
    form = {"numbers": rows}
    binding.validate_report(child, form, FORM)
    contract = TypedReportContract("Receive synthetic kinetic contrast", FORM, lambda ref, ns: binding.resolve(child, ref, ns))
    parent_request = {"goal": root_goal.as_record(), "message": {"scope": plain(seed.scope)}, "report_contract": None}
    request = {"goal": child_goal.as_record(), "message": {"scope": plain(seed.scope), "episode_assignment": assignment},
        "report_contract": contract.as_record()}
    journal = Journal(store, run)
    for eid, path, req, state in ((parent_id, parent_path, parent_request, "active"), (child_id, child_path, request, "yielded")):
        journal.save("runtime_episodes", {"episode_id": eid, "path": canonical(path), "request": canonical(req),
            "initial_credit": 0, "state": state, "completion": None, "archive": None})
    spec = {"version": "episode_commission_v1", "handle": "synthetic-witness-handle", "operation_key": "commission",
        "run_id": run, "parent": {"episode_id": parent_id, "goal_id": root_goal.goal_id, "path": parent_path},
        "child": {"episode_id": child_id, "role": "literature", "key": "kinetic", "path": child_path,
            "request": request, "scope": plain(seed.scope)}, "input_versions": [],
        "runtime_binding": {"factory_module": "fixture", "factory_name": "open_commission", "arguments": {},
            "implementation_sha256": "a" * 64, "settings_sha256": "b" * 64}, "constraints": {},
        "resource_selection": None, "expectation_snapshot_refs": []}
    journal.save("runtime_actions", {"episode_id": parent_id, "decision_index": 7,
        "action": canonical({"kind": "episode_child", "role": "literature"}),
        "result": canonical({"status": "pending", "pending_handle": spec["handle"]}), "credit": None})
    journal.save("runtime_forms", {"episode_id": child_id, "facts": canonical({"literature_kinetic_cells": rows,
        "changed_record_refs": outcome["changed_record_refs"]}), "form": canonical(form)})
    archive = JsonArchive(tmp_path / "archive")
    returned = {"version": "returned_episode_v1", "handle": spec["handle"], "return_id": "",
        "commission_sha256": content_digest(spec), "returned_at": "2026-10-26T12:00:00+00:00", "outcome": "closed",
        "completion": {"ended_by": "yield_stop", "end_reason": "", "units_consumed": 1},
        "episode_archive": archive.store({"synthetic": True}).descriptor(),
        "result_archive": archive.store({"form": form}).descriptor(), "form": form,
        "facts_archive": archive.store({"literature_kinetic_cells": rows}).descriptor(), "pending_handles": [], "failure": None}
    seal_return(returned)
    key = run + ":" + parent_id + ":7:typed_form"
    def receive(value):
        binding.received_form_references(parent, value, FORM, key)
        return outcome["record_refs"]
    receiver = ReceiverBindingV1(store, journal, 7, contract, lambda value: binding.validate_report(child, value, FORM),
        receive, lambda: 0, lambda index, credit: Value({"credit": credit, "estimation_action_index": index}))
    try:
        admitted = admit_return(spec, returned, receiver)
        assert admitted["state"] == "admitted" and admitted["report"] == form
        parent = replace(parent, received_record_refs=tuple(dict.fromkeys([*parent.received_record_refs, *admitted["received_record_refs"]])))
        assert binding.received_report_facts(parent)["literature_kinetic_cells"] == rows
        assert [r["component"] for r in rows] == ["parameter_ratio"]
        before = list(store.db.iterdump())
        source_artifact = store.get(args["source_ref"])["artifact_ref"]
        store.close()
        def forbidden(*_a, **_kw):
            raise AssertionError("saved reconstruction may not read source, parse, calculate, receive or reprice")
        monkeypatch.setattr("gene_annotation_episode.literature_kinetic_storage.read_kinetic_inputs", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_kinetic_storage.populate_kinetic_contrast", forbidden)
        with Store(tmp_path / "state") as reopened:
            # Constructors install their existing tables on the ordinary Store
            # connection. No scientific projection is prewarmed before the
            # actual mode=ro connection and forbidden source guard below.
            restored = LiteratureKineticRepository(reopened, run)
            _, rebuilt = service_binding(reopened, child)
            rebuilt._rate_facts(replace(child, received_record_refs=()), [])
            restored_journal = Journal(reopened, run)
            reopened.db.close()
            reopened.db = sqlite3.connect((tmp_path / "state/state.sqlite3").resolve().as_uri() + "?mode=ro",
                uri=True, isolation_level=None)
            reopened.db.row_factory = sqlite3.Row
            restored_journal.db = reopened.db
            get = reopened.get_artifact
            monkeypatch.setattr(reopened, "get_artifact", lambda ref: forbidden() if ref == source_artifact else get(ref))
            monkeypatch.setattr(rebuilt, "received_form_references", forbidden)
            monkeypatch.setattr(restored, "receive_cells", forbidden)
            assert restored.read(outcome["result"]["sheet_ref"]) == saved
            assert restored.populate(child, args, "selected") == outcome
            assert restored.received_cells(parent) == rows
            assert rebuilt.received_report_facts(parent)["literature_kinetic_cells"] == rows
            rebound = replace(receiver, store=reopened, journal=restored_journal, receive_references=forbidden,
                project_received_credit=forbidden, validate_semantics=forbidden)
            with reopened.read_snapshot():
                assert admit_return(spec, returned, rebound) == admitted
            assert list(reopened.db.iterdump()) == before
            assert reopened.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
            assert not reopened.list("observation") and not reopened.list("assessment")
    finally:
        store.close()
