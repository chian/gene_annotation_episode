"""Retained-only rich liftover delivery through the real episode protocol.

The explicitly selected producer input contains actual plain/gzip native
publications. This new investigation uses scripted questions/choices and a test
stopping controller; it makes no model RPC, conversion or new publication.
Only its owned database/artifact/run copy is mutable or withdrawn for replay.
"""
import asyncio
import builtins
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import shutil

import pytest

from gene_annotation_episode import liftover_contracts as core
from gene_annotation_episode.communication import ReportBoundaryError, plain
from gene_annotation_episode.domain import canonical, obj
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.liftover_tools import LIFTOVER_TOOL
from gene_annotation_episode.molecular_result_facts import (
    received_molecular_facts, validate_frozen_molecular_return,
)
from gene_annotation_episode.runtime import TypedReportContract, Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import source_tool_grading_entries
from gene_annotation_episode.tools import ToolRegistry
from test_liftover_tool import _libraries, _Script, _tables
from test_runtime import FixtureController


QUESTION = ("What exact retained target positions, strands and native chain scores accompany the two "
    "supplied point-liftover Sources, and which full mapping populations and unknown assembly "
    "qualifications must accompany those values when they are returned onward?")


def _forbidden(*args, **kwargs):
    raise AssertionError("retained liftover delivery attempted new science, private bytes or a model call")


def _files(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in directory.rglob("*") if path.is_file()}


def _input_pins(directory):
    return dict(summary=hashlib.sha256((directory / "LIFTOVER_TOOL.json").read_bytes()).hexdigest(),
        database=hashlib.sha256((directory / "store/state.sqlite3").read_bytes()).hexdigest(),
        artifacts=_files(directory / "store/artifacts"), run=_files(directory / "run"))


def _clone(tmp_path):
    selected = os.environ.get("HMMER_NATIVE_ORACLE_LIFTOVER_RETAINED")
    assert selected, "an explicitly selected retained liftover producer root is required"
    original = Path(selected).resolve()
    assert original.is_dir()
    summary = json.loads((original / "LIFTOVER_TOOL.json").read_bytes())
    assert summary["version"] == "liftover_tool_verification_v1"
    assert summary["native_worker_count"] == 3 and summary["native_conversion_count"] == 2
    assert summary["saved_public_calculator_count"] == 1 and summary["closed_replay_unchanged"] is True
    references = summary["source_refs"]
    assert type(references) is list and len(references) == len(set(references)) == 2
    assert references == [row["source"]["id"] for row in summary["originals"]]
    assert summary["failure_source_ref"] not in references
    for suffix in ("-wal", "-shm"):
        path = original / ("store/state.sqlite3" + suffix)
        assert not path.exists() or path.stat().st_size == 0, "the selected database must be quiescent"
    pins = _input_pins(original)
    directory = tmp_path / "retained-liftover"
    (directory / "store").mkdir(parents=True)
    shutil.copyfile(original / "store/state.sqlite3", directory / "store/state.sqlite3")
    shutil.copytree(original / "store/artifacts", directory / "store/artifacts")
    shutil.copytree(original / "run", directory / "run")
    for path in (directory, *directory.rglob("*")):
        path.chmod(0o755 if path.is_dir() else 0o644)
    assert _input_pins(original) == pins
    return original, directory, summary, pins


def _guards(monkeypatch):
    from gene_annotation_episode import liftover_measurements, molecular_measurement_tools as ordinary
    from gene_annotation_episode import native_lifecycle, tool_grading_artifacts
    monkeypatch.setattr(liftover_measurements, "run_liftover_tool_request", _forbidden)
    monkeypatch.setattr(ordinary, "run_owned_molecular_worker", _forbidden)
    monkeypatch.setattr(ordinary, "retain_molecular_publication", _forbidden)
    monkeypatch.setattr(tool_grading_artifacts, "retain_tool_grading", _forbidden)
    monkeypatch.setattr(core, "calculate_liftover_components", _forbidden)
    monkeypatch.setattr(ToolRegistry, "_sequence_worker_async", _forbidden)
    for name in ("prepare_job", "resume_start", "collect", "wait_job"):
        monkeypatch.setattr(native_lifecycle, name, _forbidden)
    original_import = builtins.__import__

    def no_pyliftover(name, *args, **kwargs):
        assert name != "pyliftover" and not name.startswith("pyliftover."), "retained delivery imported native code"
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_pyliftover)


def _expected(store, summary):
    expected, private, inputs = [], set(), set()
    for reference, original in zip(summary["source_refs"], summary["originals"]):
        source = store.get(reference)
        assert canonical(source) == canonical(original["source"])
        stored = json.loads(store.get_artifact(source["artifact_ref"]))
        assert canonical(stored) == canonical(original["stored"])
        grading, = source_tool_grading_entries(store, reference)
        assert grading["artifact_ref"] == original["grading_ref"]
        assert canonical(grading["grading"]) == canonical(dict(sheet=stored["sheet"], scores=stored["components"]))
        projected = core.project_liftover_return(stored["components"], source_ref=reference)
        assert canonical(projected) == canonical(original["projection"])
        assert projected["selected_mapping_ordinals"] == [0]
        assert projected["rows"] == [dict(ordinal=0, state="valid", target_chromosome="literal.target",
            target_position_0based=19, target_strand="+", native_chain_score=9, qualification_codes=[])]
        assert projected["population"]["mapping_count"] == projected["population"]["conversion_call_count"] == 1
        assert all(value == dict(state="unavailable", label=None, reason="not_provided")
            for value in projected["assembly_context"].values())
        expected.append(projected)
        private.update((source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"]))
        inputs.add(stored["request"]["chain"]["file"]["artifact_ref"])
    return expected, private, inputs


def _workflow(store, directory, provider, descriptor, references):
    return Workflow(store, ToolRegistry(store), provider, directory, "retained-liftover-rich-forms",
        lambda path, initial: FixtureController(str(path), initial,
            2 if len(path) == 1 else 3 if path[-1][1] == "child_0" else 1),
        lambda store, scope, **kwargs: 0, project_child_credit=lambda store, scope, **kwargs: 0,
        episode_binding_descriptors=[descriptor], episode_record_receipts=True,
        initial_known_record_refs=list(references))


def _root(workflow, scope, form):
    contract = TypedReportContract("Return the original Source-owned mapping groups actually received for this question.",
        form, lambda reference, namespace: workflow.resolver(scope, source=root.source)(reference, namespace),
        semantic_validator=lambda value: workflow.validate_report(value, scope, grain="annotation",
            schema=form, source=root.source))
    root = workflow.build("annotation", "root", QUESTION, scope, contract=contract)
    return root


def test_retained_liftover_rich_workflow_onward_and_withdrawn_closed_replay(tmp_path, monkeypatch):
    original, directory, summary, original_pins = _clone(tmp_path)
    _guards(monkeypatch)
    with Store(directory / "store") as store:
        expected, private, input_files = _expected(store, summary)
        references, scope = summary["source_refs"], summary["scope"]
        run = tmp_path / "rich-run"; run.mkdir()
        descriptor, selected = _libraries(run, ToolRegistry(store))
        selected["child_tool_info"].append(dict(name="state.query", resources="local"))
        form = obj(dict(mappings=core.liftover_fact_sources()[core.FACT_SOURCE]["report_schema"]))
        received, inspected = [], []

        def commission(question, chosen):
            return dict(selection=dict(kind="episode_child", role="scientific_process", goal=question,
                scope=scope, purpose="Return the complete original mapping groups, including full-population and unknown-assembly qualifications.",
                schema_json=json.dumps(form), initial_report_json="{}", assignment=dict(selection=chosen,
                    evidence_refs=references, constraints=dict(native_conversion=False), context=dict(question=question))), report_update={})

        def read(reference, ordinals):
            return dict(selection=dict(kind="tool", tool=LIFTOVER_TOOL,
                arguments=dict(mode="read_stored", result_ref=reference, mapping_ordinals=ordinals)), report_update={})

        def onward(context):
            parent = workflow.binding_context(root.source)
            actual = workflow.services.molecular_received_facts(parent, fact_source=core.FACT_SOURCE)
            assert canonical(actual) == canonical(expected)
            received.append(deepcopy(actual))
            following = deepcopy(selected)
            following["child_tool_info"] = [dict(name="state.query", resources="local")]
            return commission("Which original point mappings and qualifications were explicitly received from the preceding child?", following)

        def inspect(context):
            row = store.db.execute("SELECT episode_id FROM runtime_episodes WHERE run_id=? "
                "AND json_extract(path,'$[1][1]')='child_1'", (workflow.run_id,)).fetchone()
            current = EpisodeReturnRecords(store, workflow.run_id, failure_prefix="test_").context(row[0])
            actual = workflow.services.molecular_received_facts(current, fact_source=core.FACT_SOURCE)
            assert canonical(actual) == canonical(expected)
            assert workflow.services.molecular_own_facts(current, fact_source=core.FACT_SOURCE) == []
            inspected.append(deepcopy(actual))
            return dict(selection=dict(kind="tool", tool="state.query", arguments=dict(refs=references)), report_update={})

        provider = _Script([commission(QUESTION, selected), read(references[0], [0]),
            read(references[1], []), read(references[0], []), onward, inspect])
        workflow = _workflow(store, run, provider, descriptor, references)
        root = _root(workflow, scope, form)
        record = asyncio.run(root.run_async(workflow.context)); asyncio.run(root.build_result(record))
        assert len(provider.contexts) == 6 and received == inspected == [expected]
        parent = workflow.binding_context(root.source)
        parent_form = json.loads(store.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (workflow.run_id, parent.episode_id)).fetchone()[0])
        assert canonical(parent_form["mappings"]) == canonical(expected)
        assert canonical(workflow.services.molecular_frozen_facts(parent, fact_source=core.FACT_SOURCE)) == canonical(expected)
        attempts = list(store.db.execute("SELECT decision_index,child_episode_id,form,contract "
            "FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND failure IS NULL ORDER BY decision_index",
            (workflow.run_id, parent.episode_id)))
        assert len(attempts) == 2
        contexts = [EpisodeReturnRecords(store, workflow.run_id, failure_prefix="test_").context(row["child_episode_id"])
            for row in attempts]
        actions = [json.loads(row[0]) for row in store.db.execute("SELECT result FROM runtime_actions "
            "WHERE run_id=? AND episode_id=? ORDER BY decision_index", (workflow.run_id, contexts[0].episode_id))]
        assert [row["result"]["selected_mapping_ordinals"] for row in actions] == [[0], [], []]
        assert [row["result"]["rows"] for row in actions[1:]] == [[], []]
        assert all(row["changed_record_refs"] == [] for row in actions)
        for attempt, current in zip(attempts, contexts):
            returned = json.loads(attempt["form"])
            assert canonical(returned["mappings"]) == canonical(expected)
            assert canonical(workflow.services.molecular_frozen_facts(current, fact_source=core.FACT_SOURCE)) == canonical(expected)
            validate_frozen_molecular_return(returned, json.loads(attempt["contract"])["measurements"]["schema"],
                expected, fact_source=core.FACT_SOURCE)
        for current in (parent, *contexts):
            known = set(workflow.receipts.known(current.episode_id))
            assert set(references) <= known
            assert not (private | input_files).intersection(known)
            assert summary["failure_source_ref"] not in known
            for reference in private:
                assert workflow.resolver(scope, context=current)(reference, "artifact") is False

        # Actual frozen forms protect both scalar types and literal Sources.
        for mutation in ("value", "float_alias", "source"):
            changed = deepcopy(parent_form)
            if mutation == "value": changed["mappings"][0]["rows"][0]["target_position_0based"] = 18
            elif mutation == "float_alias": changed["mappings"][0]["rows"][0]["target_position_0based"] = 19.0
            else: changed["mappings"][0]["source_ref"] = references[1]
            with pytest.raises(ReportBoundaryError):
                workflow.episode_bindings.validate_received_report(parent, changed, form)
        changed_schema = deepcopy(form); changed_schema["properties"]["mappings"]["maxItems"] = 2
        with pytest.raises(ValueError):
            validate_frozen_molecular_return(parent_form, changed_schema, expected, fact_source=core.FACT_SOURCE)
        forged = replace(parent, scope={**plain(parent.scope), "engineering_scope_substitution": True})
        with pytest.raises(ValueError):
            workflow.services.molecular_received_facts(forged, fact_source=core.FACT_SOURCE)

        onward_context = contexts[1]
        manifest = store.db.execute("SELECT received_report_prefix FROM runtime_receipt_inheritance "
            "WHERE run_id=? AND episode_id=?", (workflow.run_id, onward_context.episode_id)).fetchone()[0]
        prefix = json.loads(manifest)
        assert [item["decision_index"] for item in prefix["attempts"]] == [0]
        altered = deepcopy(prefix); altered["attempts"][0]["form_sha256"] = "0" * 64
        try:
            store.db.execute("UPDATE runtime_receipt_inheritance SET received_report_prefix=? WHERE run_id=? AND episode_id=?",
                (canonical(altered), workflow.run_id, onward_context.episode_id))
            with pytest.raises(ValueError, match="received_prefix_conflict"):
                received_molecular_facts(store, workflow.run_id, onward_context, fact_source=core.FACT_SOURCE)
        finally:
            store.db.execute("UPDATE runtime_receipt_inheritance SET received_report_prefix=? WHERE run_id=? AND episode_id=?",
                (manifest, workflow.run_id, onward_context.episode_id))
        late = json.loads(attempts[1]["form"]); late["mappings"][0]["rows"][0]["native_chain_score"] = 10
        try:
            store.db.execute("UPDATE runtime_report_attempts SET form=? WHERE run_id=? AND parent_episode_id=? AND decision_index=1",
                (canonical(late), workflow.run_id, parent.episode_id))
            assert canonical(received_molecular_facts(store, workflow.run_id, onward_context,
                fact_source=core.FACT_SOURCE)) == canonical(expected)
            with pytest.raises(ValueError):
                workflow.services.molecular_received_facts(parent, fact_source=core.FACT_SOURCE)
        finally:
            store.db.execute("UPDATE runtime_report_attempts SET form=? WHERE run_id=? AND parent_episode_id=? AND decision_index=1",
                (attempts[1]["form"], workflow.run_id, parent.episode_id))

        # Withdraw only the owned clone's private output/control/grade bodies.
        # Metadata and the actual admitted forms/receipt prefixes stay intact.
        for reference in private:
            path = store.path / "artifacts" / reference[9:11] / reference[9:]
            assert path.is_file()
            path.unlink()
        from gene_annotation_episode import molecular_measurement_tools as ordinary
        monkeypatch.setattr(store, "get_artifact", _forbidden)
        monkeypatch.setattr(ordinary, "read_retained_molecular_publication", _forbidden)
        for name in ("populate_liftover_sheet", "validate_liftover_sheet", "validate_liftover_components",
                "project_liftover_return", "_components", "_population"):
            monkeypatch.setattr(core, name, _forbidden)
        monkeypatch.setattr(provider, "complete", _forbidden)
        before, changes, archive, artifacts = _tables(store), store.db.total_changes, _files(run), _files(store.path / "artifacts")
        known_receipts = list(store.db.execute("SELECT run_id,episode_id,record_ref FROM runtime_record_receipts "
            "WHERE run_id=?", (workflow.run_id,)))
        receipt_prefix = ("INSERT OR IGNORE INTO runtime_record_receipts "
            "(run_id,episode_id,record_ref,receipt_kind,source_index) VALUES(")
        known_receipt_prefixes = [receipt_prefix + f"'{row[0]}','{row[1]}','{row[2]}'," for row in known_receipts]
        statements = []
        store.db.set_trace_callback(lambda statement: statements.append((statement, store.db.total_changes)))
        try:
            restored = _workflow(store, run, provider, descriptor, references)
            replay = _root(restored, scope, form)
            replay_record = asyncio.run(replay.run_async(restored.context)); asyncio.run(replay.build_result(replay_record))
        finally:
            final_changes = store.db.total_changes
            store.db.set_trace_callback(None)
        # Existing Episode.run_async re-closes each of the three episodes.
        # Journal.save issues an equal-value UPSERT even when history is exact.
        # Re-seeding already-known receipts also issues ignored, zero-effect SQL.
        counters = [count for _, count in statements] + [final_changes]
        deltas = [(statement, counters[index + 1] - count)
            for index, (statement, count) in enumerate(statements)]
        written = [(statement, delta) for statement, delta in deltas if delta]
        episode_ids = {parent.episode_id, *(current.episode_id for current in contexts)}
        assert len(written) == len(episode_ids) == 3
        assert final_changes - changes == len(written)
        written_ids = []
        for statement, delta in written:
            assert delta == 1 and statement.startswith("INSERT INTO runtime_episodes ")
            assert " ON CONFLICT DO UPDATE SET " in statement
            matches = [episode_id for episode_id in episode_ids
                if f"VALUES ('{workflow.run_id}','{episode_id}'," in statement]
            assert len(matches) == 1
            written_ids.extend(matches)
        assert len(set(written_ids)) == len(episode_ids)
        for statement, delta in deltas:
            if not delta and statement.lstrip().split(None, 1)[0].upper() in {"INSERT", "UPDATE", "DELETE", "REPLACE"}:
                assert any(statement.startswith(prefix) for prefix in known_receipt_prefixes)
        assert _tables(store) == before
        assert _files(run) == archive and _files(store.path / "artifacts") == artifacts
        assert canonical(restored.services.molecular_received_facts(restored.binding_context(replay.source),
            fact_source=core.FACT_SOURCE)) == canonical(expected)
        assert _input_pins(original) == original_pins
