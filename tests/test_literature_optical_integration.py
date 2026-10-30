"""Synthetic optical C7/shared-loop, actual provider text and original replay checks."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json

import pytest

from gene_annotation_episode.communication import ReportBoundaryError, form_with_facts, plain, validate_form
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.domain import ContractError, canonical, identity, obj
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_optical_storage import LiteratureOpticalRepository, optical_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_experimental_prompt_delivery import LiteratureWire, complete, snapshot
from test_literature_optical_storage import setup, projected, TEXT, SUFFIX
from test_literature_rate_episode_integration import service_binding
from test_runtime import FixtureController, ScriptedProvider


RAW_SENTINELS = ("-0.01357902468", "-0.0012342468", "5678.12345", "11.33377709", "337.6197531")


def sentinel_setup(path, *, broad=False):
    text = TEXT + SUFFIX
    for old, value in zip(("-0.012", "-0.002", "5000", "10 mm", "340 nm"), RAW_SENTINELS):
        text = text.replace(old, value + (" mm" if old == "10 mm" else " nm" if old == "340 nm" else ""))
    numbers = dict(zip(("sample", "blank", "epsilon", "path", "wavelength"),
        [(value + " " + unit, value, unit) for value, unit in zip(RAW_SENTINELS,
            ("AU/min", "AU/min", "M^-1 cm^-1", "mm", "nm"))]))
    change = (lambda a: a["signals"]["sample"].update(condition=deepcopy(a["relation"]["witnesses"][0]))) if broad else None
    return setup(path, text=text, operands=numbers, change=change)


def work(args):
    return {"selection": {"kind": "tool", "tool": "literature.optical.populate", "arguments": args}, "report_update": {}}


def received_subject_reason(store):
    source = next(row for row in store.list("source") if row["provider"] == "synthetic_optical_fixture")
    raw = store.get_artifact(source["artifact_ref"])
    label = "reference-RC"
    start = raw.index(label.encode())
    commit = {name: [] for name in store.reasoning_schema()["required"]}
    commit["source_subjects"] = [{"alias": "received_source_construct", "reference_type": "assay", "source_ref": source["id"],
        "label": label, "anchor": {"source_ref": source["id"], "artifact_ref": source["artifact_ref"],
        "start": start, "end": start + len(label.encode()), "quote": label}}]
    return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}


@pytest.mark.parametrize("components", [["net_rate"], ["variance_net_rate"], []])
def test_original_shared_loop_subset_admission_and_saved_forwarding(tmp_path, monkeypatch, components):
    store, context, args = setup(tmp_path / "state")
    try:
        schema = obj({"caller_selected_numbers": optical_cells_schema()})
        assignment = {**plain(context.assignment), "requested_optical_components": components}
        received, receiving_inputs, controllers = [], [], []
        commission = {"selection": {"kind": "episode_child", "role": "literature", "assignment": assignment,
            "goal": "Evaluate the selected synthetic optical endpoint without assigning product attribution.", "scope": plain(context.scope),
            "purpose": "Return only the chosen source endpoint inputs.", "schema_json": json.dumps(schema), "initial_report_json": "{}"}, "report_update": {}}
        def select(inputs):
            assert inputs["literature_assignment"] == assignment
            assert any(row["name"] == "literature.optical.populate" for row in inputs["tools"])
            return work(args)
        def use(inputs):
            report, = inputs["child_reports"]
            assert [row["component"] for row in report["caller_selected_numbers"]] == components
            received.append(deepcopy(report))
            receiving_inputs.append(deepcopy(inputs))
            return received_subject_reason(store)
        def unexpected(inputs):
            raise AssertionError(inputs.get("feedback"))
        provider = ScriptedProvider([commission, select, use, unexpected])
        def controller(path, initial):
            value = FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
            controllers.append(value)
            return value
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path / "run",
            controller_factory=controller, project_credit=scorer, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=[args["source_ref"]]),), binding_definitions={"credit": scorer.as_record()}))
        assert summary["credit"] == 0 and [c.scores for c in controllers] == [[0, 0], [0]]
        assert len(provider.contexts) == 3 and len(received) == 1
        wire = LiteratureWire(tmp_path / "actual-receiver-wire")
        asyncio.run(complete(wire, state_frame(receiving_inputs[0])))
        receiving_text = wire.turns_sent()[0]["input"][0]["text"]
        for token in ("-0.012", "-0.002", "5000", "10 mm"):
            assert token not in receiving_text
        if components:
            assert str(received[0]["caller_selected_numbers"][0]["value"]) in receiving_text
            assert "reference-RC" in receiving_text and "buffer-B" in receiving_text
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 3
        assert store.db.execute("SELECT count(*) FROM literature_optical_operations").fetchone()[0] == 1
        saved_form = store.db.execute("SELECT * FROM runtime_forms").fetchone()
        assert json.loads(saved_form["facts"])["literature_optical_cells"] == received[0]["caller_selected_numbers"]
        assert json.loads(saved_form["form"]) == received[0]
        operation = store.db.execute("SELECT * FROM literature_optical_operations").fetchone()
        outcome = json.loads(operation["outcome"])
        current = replace(context, run_id=operation["run_id"], episode_id=operation["episode_id"], assignment=assignment,
            received_record_refs=tuple([*context.received_record_refs, *outcome["record_refs"]]))
        services, binding = service_binding(store, current)
        rebuilt, = compose_episode_bindings(services, store=store, journal=Journal(store, current.run_id), execution_backend=None,
            descriptors=[binding.as_record()], job_episodes=None, resource_estimator=None, role_credit_bindings={}).bindings
        artifacts = {store.get(ref)["artifact_ref"] for ref in context.received_record_refs}
        get = store.get_artifact
        def saved_only(ref):
            assert ref not in artifacts, "saved forwarding read scientific bytes"
            return get(ref)
        def forbidden(*_a, **_k):
            raise AssertionError("saved forwarding cannot populate or invoke model")
        monkeypatch.setattr(store, "get_artifact", saved_only)
        monkeypatch.setattr("gene_annotation_episode.literature_optical_storage.read_optical_rate_operands", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_optical_storage.calculate_nadh_optical_rate", forbidden)
        monkeypatch.setattr(provider, "complete", forbidden)
        facts = rebuilt.facts(current, {"committed_record_refs": outcome["record_refs"]})
        assert form_with_facts({}, schema, facts) == received[0]
        rebuilt.validate_report(current, received[0], schema)
        assert asyncio.run(rebuilt.execute(current, "literature.optical.populate", args, operation["operation_key"])) == outcome
        parent_row = store.db.execute("SELECT parent_episode_id FROM runtime_report_attempts").fetchone()
        parent = replace(current, role="annotation", episode_id=parent_row[0], path=(("annotation", "root"),), assignment={})
        assert rebuilt.received_report_facts(parent).get("literature_optical_cells", []) == received[0]["caller_selected_numbers"]
        if components:
            rebuilt.received_form_references(parent, received[0], schema, "repeated-admission")
            rebuilt.received_form_references(parent, received[0], schema, "repeated-admission")
            forwarded = rebuilt.received_report_facts(parent)["literature_optical_cells"]
            assert forwarded == received[0]["caller_selected_numbers"]
            changed = deepcopy(received[0]); changed["caller_selected_numbers"][0]["value"] = -99
            with pytest.raises(ReportBoundaryError, match="differs_from_saved"):
                rebuilt.validate_report(current, changed, schema)
        if components == ["net_rate"]:
            # A forged received row containing a valid but unadmitted variance
            # still cannot forward, even if its receipt digest is also forged.
            original_receipt = store.db.execute("SELECT operation_key,cells FROM literature_optical_received WHERE episode_id=? AND operation_key LIKE '%:typed_form'", (parent.episode_id,)).fetchone()
            forged = services.literature_optical_repository().project_cells([outcome["result"]["sheet_ref"]],
                permitted_record_refs=outcome["record_refs"], components=["variance_net_rate"])
            store.db.execute("UPDATE literature_optical_received SET cells=? WHERE episode_id=? AND operation_key=?",
                (canonical(forged), parent.episode_id, original_receipt["operation_key"]))
            store.db.execute("UPDATE literature_optical_delivery_bindings SET cells_digest=? WHERE episode_id=? AND operation_key=?",
                (identity("optical_admitted_cells", forged), parent.episode_id, original_receipt["operation_key"]))
            with pytest.raises(ContractError, match="delivery_binding_mismatch"):
                rebuilt.received_report_facts(parent)
            original_cells = json.loads(original_receipt["cells"])
            store.db.execute("UPDATE literature_optical_received SET cells=? WHERE episode_id=? AND operation_key=?",
                (original_receipt["cells"], parent.episode_id, original_receipt["operation_key"]))
            store.db.execute("UPDATE literature_optical_delivery_bindings SET cells_digest=? WHERE episode_id=? AND operation_key=?",
                (identity("optical_admitted_cells", original_cells), parent.episode_id, original_receipt["operation_key"]))
        # No fact filling/forwarding/internal source arithmetic adds a turn.
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 3
        assert not store.list("observation") and not store.list("assessment")
    finally:
        store.close()


@pytest.mark.parametrize("components", [["net_rate"], ["variance_net_rate"]])
@pytest.mark.parametrize("parent", [False, True])
@pytest.mark.parametrize("record_page", ["complete", "missing_operand", "partial_overlap"])
def test_actual_receiving_provider_text_excludes_unrequested_operand_numbers(tmp_path, components, parent, record_page):
    store, context, args = sentinel_setup(tmp_path / "state", broad=True)
    try:
        # Distinct exact source tokens and output values make name-only checks
        # insufficient. Whole-source interpretation witnesses deliberately span
        # every raw operand; safe subject/condition witnesses remain narrow.
        repo = LiteratureOpticalRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        rows = projected(repo, outcome, components)
        saved = repo.read(outcome["result"]["sheet_ref"])
        state = snapshot()
        state["goal"]["objective"] = "Use the admitted source optical endpoint inputs and preserve attribution limits."
        state["child_reports"] = [{"chosen_optical_inputs": rows}]
        state["last_local_outcome"] = {"status": "completed", "record_refs": outcome["record_refs"], "changed_record_refs": [], "result": None}
        state["current_report_basis_refs"] = outcome["record_refs"]
        state["working_state"].update(references=store.list("reference"), contexts=store.list("context"))
        # A broad ordinary received reference also tries to expand all tokens.
        broad = deepcopy(store.list("reference")[0])
        broad.update(id="reference_broad_received", label=saved["selection"]["relation"]["witnesses"][0]["quote"],
            anchor={key: saved["extraction"]["relation"]["witnesses"][0][key] for key in ("source_ref", "artifact_ref", "start", "end", "quote")})
        if record_page != "complete":
            number = saved["extraction"]["signals"]["sample"]["number"]
            w = number["selector"]["witness"]
            quote = w["quote"] if record_page == "missing_operand" else RAW_SENTINELS[0][:-1]
            start = w["start"] + (0 if record_page == "missing_operand" else number["selector"]["number_start"])
            broad.update(label=quote, anchor={"source_ref": w["source_ref"], "artifact_ref": w["artifact_ref"],
                "start": start, "end": start + len(quote.encode()), "quote": quote})
        if record_page == "missing_operand":
            missing = rows[0]["operands"]["sample_slope"]["measurement_ref"]
            state["working_state"]["references"] = [r for r in state["working_state"]["references"] if r["id"] != missing]
        state["working_state"]["references"].append(broad)
        state["current_report_basis_refs"].append(broad["id"])
        # Independent admitted scientific information from a different source
        # must survive when an optical measurement falls off the record page.
        unrelated_text = "Unrelated source: cobalt-free buffer condition retained."
        artifact = store.artifact(unrelated_text)
        unrelated_source = store.put("source", {"provider": "synthetic_unrelated_source", "accession": None, "uri": None,
            "artifact_ref": artifact, "text_ref": artifact, "request_ref": None, "version": None, "retrieved_at": None}, origin="caller")["id"]
        unrelated = store.put("reference", {"reference_type": "literature_result", "source_ref": unrelated_source,
            "accession": "independent_condition", "label": "cobalt-free buffer", "sequence_ref": None, "molecule": None,
            "length": None, "term_refs": [], "context_refs": [], "anchor": {"source_ref": unrelated_source, "artifact_ref": artifact,
                "start": 0, "end": len(unrelated_text.encode()), "quote": unrelated_text}}, origin="tool")
        independent_form = {"independent_condition_ref": unrelated["id"]}
        validate_form(independent_form, obj({"independent_condition_ref": {"type": "string", "format": "reference", "x-reference-namespace": "reference"}}),
            lambda ref, ns: bool(store.reference_subset([ref], plain(context.scope))) and store.get(ref)["record_type"] == ns)
        state["child_reports"].append(independent_form)
        state["working_state"]["references"].append(unrelated)
        if parent:
            services, binding = service_binding(store, context)
            binding = LiteratureEpisodes(services, rate_population=True, reference_parent_sources=[args["source_ref"]])
            receiver = replace(context, role="annotation", path=(("annotation", "root"),), assignment={})
            state.pop("literature_assignment")
            state.pop("literature_source_custody")
            state.update(binding.initial_decision_context(receiver))
        wire = LiteratureWire(tmp_path / "wire")
        restarted = LiteratureWire(tmp_path / "restart")
        async def exercise():
            await complete(wire, state_frame(state))
            await complete(restarted, state_frame(state))
        asyncio.run(exercise())
        for turn in wire.turns_sent() + restarted.turns_sent():
            text = turn["input"][0]["text"]
            task, steering = text.split("\n\nSTEERING\n")
            assert "Admitted requested optical endpoint inputs" in steering
            assert "cobalt-free buffer" in steering
            assert str(rows[0]["value"]) in steering
            for token in (*RAW_SENTINELS, "5.67812345", "1.133377709"):
                assert token not in task + steering
            other_component = "variance_net_rate" if components == ["net_rate"] else "net_rate"
            assert str(saved["cells"][other_component]["value"]) not in task + steering
            for value in ("NADH_depletion", "matched_no_reaction_background", "reported_point", "known"):
                assert value in steering
            if record_page != "missing_operand":
                for value in ("reference-R", "reference-RC", "reference-RP", "buffer-B"):
                    assert value in steering
            if record_page == "partial_overlap":
                assert RAW_SENTINELS[0][:-1] not in task + steering
            assert "source-bound witness retained for scoped access" in steering
            assert "optical_owner_" not in text and "literature_optical_owner_" not in text
            if components == ["variance_net_rate"]:
                assert "(uM/min)^2" in steering
        assert store.get(rows[0]["operands"]["epsilon"]["measurement_ref"])["label"] == RAW_SENTINELS[2]
        # Raw records still support an explicit permitted later source read.
        assert RAW_SENTINELS[2].encode() in store.get_artifact(store.get(args["source_ref"])["artifact_ref"])
    finally:
        store.close()


def test_failed_population_is_feedback_without_completed_observation(tmp_path):
    store, context, args = setup(tmp_path / "state")
    try:
        assignment = {**plain(context.assignment), "requested_optical_components": ["net_rate"]}
        form = obj({"numbers": optical_cells_schema()})
        commission = {"selection": {"kind": "episode_child", "role": "literature", "assignment": assignment,
            "goal": "Read the synthetic optical inputs", "scope": plain(context.scope), "purpose": "Return q only",
            "schema_json": json.dumps(form), "initial_report_json": "{}"}, "report_update": {}}
        wrong = deepcopy(args)
        wrong["signals"]["sample"]["measurement"]["number"]["witness"]["quote"] = "wrong"
        def repair(inputs):
            assert inputs["feedback"]["code"].startswith("source_quote_mismatch")
            assert store.db.execute("SELECT count(*) FROM literature_optical_operations").fetchone()[0] == 0
            return work(args)
        controllers = []
        def controller(path, initial):
            c = FixtureController(str(path), initial, 1)
            controllers.append(c); return c
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        provider = ScriptedProvider([commission, work(wrong), repair])
        asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path / "run", controller_factory=controller,
            project_credit=scorer, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),), binding_definitions={"credit": scorer.as_record()}))
        assert len(provider.contexts) == 3
        assert [c.scores for c in controllers] == [[0], [0]]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 2
        assert store.db.execute("SELECT count(*) FROM literature_optical_operations").fetchone()[0] == 1
    finally:
        store.close()


@pytest.mark.parametrize("leaf_components", [["net_rate"], ["variance_net_rate"]])
def test_actual_grandchild_literature_parent_annotation_parent_exact_subset(tmp_path, leaf_components):
    store, context, args = sentinel_setup(tmp_path / "state", broad=True)
    try:
        schema = obj({"selected_optical": optical_cells_schema()})
        outer = {**plain(context.assignment), "requested_optical_components": ["net_rate", "variance_net_rate"]}
        inner = {"version": "strategy_assignment_v1", "question_context_refs": [],
            "prior_search_refs": [args["source_ref"]], "requested_optical_components": leaf_components}
        def commission(role, assignment):
            return {"selection": {"kind": "episode_child", "role": role, "assignment": assignment,
                "goal": "Evaluate the assigned synthetic optical endpoint", "scope": plain(context.scope),
                "purpose": "Return the received selected endpoint components", "schema_json": json.dumps(schema), "initial_report_json": "{}"}, "report_update": {}}
        receivers = []
        def receive(inputs):
            report, = inputs["child_reports"]
            assert [row["component"] for row in report["selected_optical"]] == leaf_components
            receivers.append(deepcopy(inputs))
            return received_subject_reason(store)
        provider = ScriptedProvider([commission("literature", outer), commission("literature_strategy", inner), work(args), receive, receive])
        controllers = []
        def controller(path, initial):
            c = FixtureController(str(path), initial, 1 if len(path) == 3 else 2)
            controllers.append(c); return c
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path / "run",
            controller_factory=controller, project_credit=scorer, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=[args["source_ref"]]),), binding_definitions={"credit": scorer.as_record()}))
        assert summary["credit"] == 0
        assert [c.scores for c in controllers] == [[0, 0], [0, 0], [0]]
        assert len(receivers) == 2
        for index, state in enumerate(receivers):
            wire = LiteratureWire(tmp_path / ("receiver-" + str(index)))
            asyncio.run(complete(wire, state_frame(state)))
            text = wire.turns_sent()[0]["input"][0]["text"]
            for token in (*RAW_SENTINELS, "5.67812345", "1.133377709"):
                assert token not in text
            assert "reference-RC" in text and "NADH_depletion" in text
            operation = json.loads(store.db.execute("SELECT outcome FROM literature_optical_operations").fetchone()[0])
            other_component = "variance_net_rate" if leaf_components == ["net_rate"] else "net_rate"
            assert str(operation["result"]["cells"][other_component]["value"]) not in text
        forms = [json.loads(row[0]) for row in store.db.execute("SELECT form FROM runtime_forms")]
        assert len(forms) == 2
        assert all([row["component"] for row in form["selected_optical"]] == leaf_components for form in forms)
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 5
        assert store.db.execute("SELECT count(*) FROM literature_optical_operations").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM literature_optical_received").fetchone()[0] == 2
    finally:
        store.close()


def test_interrupted_return_redelivery_uses_original_saved_subset_without_extra_observation(tmp_path, monkeypatch):
    store, context, args = setup(tmp_path / "state")
    try:
        form = obj({"numbers": optical_cells_schema()})
        form["properties"]["numbers"]["maxItems"] = 0
        repaired = deepcopy(form)
        repaired["properties"]["numbers"].pop("maxItems")
        assignment = {**plain(context.assignment), "requested_optical_components": ["net_rate"]}
        commission = {"selection": {"kind": "episode_child", "role": "literature", "assignment": assignment,
            "goal": "Evaluate the synthetic optical endpoint", "scope": plain(context.scope), "purpose": "Return q only",
            "schema_json": json.dumps(form), "initial_report_json": "{}"}, "report_update": {}}
        controllers = []
        def controller(path, initial):
            c = FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
            controllers.append(c); return c
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        options = dict(run_dir=tmp_path / "run", controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=[args["source_ref"]]),), binding_definitions={"credit": scorer.as_record()})
        with pytest.raises(KeyboardInterrupt):
            asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([commission, work(args), KeyboardInterrupt()]), **options))
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 2
        original = store.db.execute("SELECT outcome FROM literature_optical_operations").fetchone()[0]
        original_form = store.db.execute("SELECT form FROM runtime_forms").fetchone()[0]
        def forbidden(*_a, **_k):
            raise AssertionError("redelivery must not repopulate source inputs")
        monkeypatch.setattr("gene_annotation_episode.literature_optical_storage.read_optical_rate_operands", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_optical_storage.calculate_nadh_optical_rate", forbidden)
        def repair(inputs):
            assert inputs["feedback"]["reason"] == "maxItems"
            assert inputs["controller"]["scores"] == [0]
            return {"selection": {"kind": "redeliver_report", "delivery_ref": inputs["feedback"]["delivery_ref"],
                "purpose": "Receive the original saved optical subset", "schema_json": json.dumps(repaired)}, "report_update": {}}
        def received(inputs):
            assert inputs["controller"]["scores"] == [0]
            assert [row["component"] for row in inputs["child_reports"][0]["numbers"]] == ["net_rate"]
            return received_subject_reason(store)
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), resume=True,
            provider=ScriptedProvider([repair, received]), **options))
        assert summary["credit"] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 3
        assert store.db.execute("SELECT count(*) FROM runtime_report_attempts").fetchone()[0] == 2
        assert store.db.execute("SELECT count(*) FROM literature_optical_received").fetchone()[0] == 1
        assert store.db.execute("SELECT outcome FROM literature_optical_operations").fetchone()[0] == original
        assert store.db.execute("SELECT form FROM runtime_forms").fetchone()[0] == original_form
    finally:
        store.close()


def test_c4_atomic_original_fact_admission_repeated_and_saved_reopen(tmp_path, monkeypatch):
    """Actual C4 transaction over an original closed optical fact, no inference."""
    from method_loop import EpisodeGoal
    from method_loop.archive import JsonArchive
    from method_loop.durable import content_digest
    from method_loop.identities import EpisodeRef
    from gene_annotation_episode.episode_admission import ReceiverBindingV1, admit_return
    from gene_annotation_episode.runtime import TypedReportContract
    from gene_annotation_episode.state import Store
    from test_episode_admission import Value, seal_return

    store, context, args = setup(tmp_path / "state")
    try:
        run_id = context.run_id
        scope = plain(context.scope)
        parent_path = [["annotation", "root"]]
        child_path = parent_path + [["literature", "optical"]]
        parent_id, child_id = EpisodeRef(run_id, parent_path).episode_id, EpisodeRef(run_id, child_path).episode_id
        assignment = {**plain(context.assignment), "requested_optical_components": ["net_rate"]}
        child = replace(context, episode_id=child_id, path=tuple(tuple(p) for p in child_path), assignment=assignment)
        repo = LiteratureOpticalRepository(store, run_id)
        out = repo.populate(child, args, "original-optical-selection")
        child = replace(child, received_record_refs=tuple([*context.received_record_refs, *out["record_refs"]]))
        rows = projected(repo, out, ["net_rate"])
        form = {"chosen": rows}
        schema = obj({"chosen": optical_cells_schema()})
        parent_goal = EpisodeGoal.root(objective="Evaluate the synthetic reference", result_contract={})
        child_goal = EpisodeGoal.child(parent_goal, objective="Evaluate optical endpoint", result_contract={})
        resolver = lambda ref, namespace=None: bool(store.reference_subset([ref], scope)) and (namespace is None or store.get(ref)["record_type"] == namespace)
        contract = TypedReportContract("Return only q", schema, resolver)
        parent_request = {"goal": parent_goal.as_record(), "message": {"scope": scope}, "report_contract": None}
        child_request = {"goal": child_goal.as_record(), "message": {"scope": scope, "episode_assignment": assignment}, "report_contract": contract.as_record()}
        spec = {"version": "episode_commission_v1", "handle": "original-optical-child-handle", "operation_key": "original-commission",
            "run_id": run_id, "parent": {"episode_id": parent_id, "goal_id": parent_goal.goal_id, "path": parent_path},
            "child": {"episode_id": child_id, "role": "literature", "key": "optical", "path": child_path, "request": child_request, "scope": scope},
            "input_versions": [], "runtime_binding": {"factory_module": "synthetic_fixture", "factory_name": "open_commission",
                "arguments": {}, "implementation_sha256": "a" * 64, "settings_sha256": "b" * 64},
            "constraints": {}, "resource_selection": None, "expectation_snapshot_refs": []}
        journal = Journal(store, run_id)
        for eid, path, request, state in ((parent_id, parent_path, parent_request, "active"), (child_id, child_path, child_request, "yielded")):
            journal.save("runtime_episodes", {"episode_id": eid, "path": json.dumps(path), "request": json.dumps(request),
                "initial_credit": 0, "state": state, "completion": None, "archive": None})
        journal.save("runtime_actions", {"episode_id": parent_id, "decision_index": 7,
            "action": json.dumps({"kind": "episode_child", "role": "literature", "assignment": assignment}),
            "result": json.dumps({"status": "pending", "pending_handle": spec["handle"]}), "credit": None})
        journal.save("runtime_forms", {"episode_id": child_id, "facts": json.dumps({"literature_optical_cells": rows, "changed_record_refs": out["changed_record_refs"]}), "form": json.dumps(form)})
        archive = JsonArchive(tmp_path / "archive")
        returned = {"version": "returned_episode_v1", "handle": spec["handle"], "return_id": "", "commission_sha256": content_digest(spec),
            "returned_at": "2026-10-26T12:00:00+00:00", "outcome": "closed", "completion": {"ended_by": "yield_stop", "end_reason": "", "units_consumed": 1},
            "episode_archive": archive.store({"synthetic": True}).descriptor(), "result_archive": archive.store({"form": form}).descriptor(),
            "form": form, "facts_archive": archive.store({"literature_optical_cells": rows}).descriptor(), "pending_handles": [], "failure": None}
        seal_return(returned)
        _, binding = service_binding(store, child)
        parent = replace(context, episode_id=parent_id, role="annotation", path=tuple(tuple(p) for p in parent_path), assignment={})
        def receive(form):
            binding.received_form_references(parent, form, schema, run_id + ":" + parent_id + ":7:typed_form")
            return [rows[0]["sheet_ref"]]
        receiver = ReceiverBindingV1(store, journal, 7, contract, lambda form: binding.validate_report(child, form, schema),
            receive, lambda: 0, lambda index, credit: Value({"credit": credit, "estimation_action_index": index}))
        # C7's service instance has its own repository over the same Store.
        service_repo = binding.services.literature_optical_repository()
        original_receive = service_repo.receive_cells
        def interrupted(*args, **kwargs):
            original_receive(*args, **kwargs)
            raise OSError("synthetic admission interruption")
        monkeypatch.setattr(service_repo, "receive_cells", interrupted)
        with pytest.raises(OSError, match="admission interruption"):
            admit_return(spec, returned, receiver)
        assert store.db.execute("SELECT count(*) FROM literature_optical_received").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM literature_optical_delivery_bindings").fetchone()[0] == 0
        monkeypatch.setattr(service_repo, "receive_cells", original_receive)
        admitted = admit_return(spec, returned, receiver)
        assert admitted["state"] == "admitted" and admitted["report"] == form
        assert repo.received_cells(parent) == rows
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
        def forbidden(*_a, **_k):
            raise AssertionError("repeated admission cannot receive, parse or reprice")
        assert admit_return(spec, returned, replace(receiver, receive_references=forbidden, project_received_credit=forbidden)) == admitted
        source_artifacts = {store.get(ref)["artifact_ref"] for ref in context.received_record_refs}
        store.close()
        with Store(tmp_path / "state") as reopened:
            get = reopened.get_artifact
            def saved_only(ref):
                assert ref not in source_artifacts
                return get(ref)
            monkeypatch.setattr(reopened, "get_artifact", saved_only)
            monkeypatch.setattr("gene_annotation_episode.literature_optical_storage.read_optical_rate_operands", forbidden)
            monkeypatch.setattr("gene_annotation_episode.literature_optical_storage.calculate_nadh_optical_rate", forbidden)
            assert LiteratureOpticalRepository(reopened, run_id).received_cells(parent) == rows
            replay_receiver = replace(receiver, store=reopened, journal=Journal(reopened, run_id),
                receive_references=forbidden, project_received_credit=forbidden, validate_semantics=forbidden)
            assert admit_return(spec, returned, replay_receiver) == admitted
    finally:
        # Reopening above already closed the first connection.
        try:
            store.close()
        except Exception:
            pass
