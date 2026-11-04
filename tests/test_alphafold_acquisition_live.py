"""Two separately selected live stages; ordinary collection performs no HTTP.

Stage one retains an active metadata prefix for a subsequent explicit file
choice. Stage two resumes a backup of that prefix, leaving its original files
untouched. Scripted choices and test-only controllers establish integration,
not live model decisions, coordinate interpretation or annotation support.
"""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

import pytest

from method_loop import Context, EpisodeGoal
from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode import alphafold_acquisition as af
from gene_annotation_episode import alphafold_acquisition_host as host
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.runtime import TypedReportContract, Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider
from test_scientific_process_runtime import Scenario, action


PREFIX_REPORT = "ALPHAFOLD_PENDING_METADATA.json"
FILE_REPORT = "ALPHAFOLD_SELECTED_FILE.json"
METADATA_LIMIT = 2 * 1024**2
FILE_LIMIT = 10 * 1024**2
TIMEOUT = 90


class ExpectedMetadataChoicePending(RuntimeError):
    """Deliberate test interruption before the child's second selection."""


def _credit(*args, **kwargs):
    return 0


def _controller(path, initial):
    # Test-only continuation seam, shared unchanged by both live stages.
    return FixtureController(str(path), initial, 1 if len(path) == 1 else 2)


def _forbidden(*args, **kwargs):
    raise AssertionError("selected AlphaFold proof attempted forbidden work")


def _explicit(name):
    if name not in os.environ:
        pytest.skip("requires explicit " + name)
    return os.environ[name]


def _outputs(tmp_path, monkeypatch):
    attempt = Path(os.environ["HMMER529_ATTEMPT"]).resolve(strict=True)
    assert Path(__file__).resolve().parents[1] == attempt / "source_snapshot"
    assert tmp_path.resolve().is_relative_to(attempt / "tmp")
    temporary = tmp_path / "tmp"
    temporary.mkdir()
    for name in ("TMPDIR", "TMP", "TEMP"):
        monkeypatch.setenv(name, str(temporary))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setattr(tempfile, "tempdir", str(temporary))


def _workflow(store, tools, provider, directory, run_id, descriptors):
    return Workflow(store, tools, provider, directory, run_id, _controller, _credit,
        project_child_credit=_credit, episode_binding_descriptors=descriptors,
        episode_record_receipts=True, initial_known_record_refs=[])


def _tables(db):
    return {row[0]: sorted((tuple(value) for value in db.execute(
        'SELECT * FROM "' + row[0].replace('"', '""') + '"')), key=repr)
        for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}


def _files(directory):
    return {str(path.relative_to(directory)): {"size": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for path in sorted(directory.rglob("*")) if path.is_file()}


def _pins():
    root = Path(__file__).resolve().parents[1]
    paths = [Path(__file__).resolve(), *(root / name for name in (
        "gene_annotation_episode/alphafold_acquisition.py",
        "gene_annotation_episode/alphafold_acquisition_host.py",
        "gene_annotation_episode/acquisition.py", "gene_annotation_episode/tools.py",
        "gene_annotation_episode/runtime.py", "gene_annotation_episode/episode_services.py",
        "method_loop/episode.py"))]
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def _episodes(db):
    rows = [dict(row) for row in db.execute(
        "SELECT * FROM runtime_episodes ORDER BY json_array_length(path),episode_id")]
    assert len(rows) == 2
    parent, child = rows
    parent_path, child_path = json.loads(parent["path"]), json.loads(child["path"])
    assert len(parent_path) == 1 and child_path[:-1] == parent_path
    assert parent_path[-1][0] == "annotation" and child_path[-1][0] == "scientific_process"
    assert parent["run_id"] == child["run_id"]
    return parent, child


def _counts(db):
    return {name: db.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in (
        "runtime_episodes", "runtime_actions", "runtime_observations", "runtime_model_calls",
        "tool_operations", "runtime_forms", "runtime_report_attempts")}


def _observe_http(client, monkeypatch, *, expected_url, limit):
    calls, actual = [], client._http
    def observed(service, url, params, media_type, **kwargs):
        assert service == af.SERVICE and url == expected_url and params == {}
        assert kwargs["max_bytes"] == limit and kwargs["follow_redirects"] is False
        assert kwargs["timeout_seconds"] == TIMEOUT
        calls.append({"service": service, "url": url, "max_bytes": kwargs["max_bytes"],
            "follow_redirects": kwargs["follow_redirects"], "timeout_seconds": kwargs["timeout_seconds"]})
        assert len(calls) == 1
        return actual(service, url, params, media_type, **kwargs)
    monkeypatch.setattr(client, "_http", observed)
    return calls


def _build_root(workflow, parent):
    path, request = json.loads(parent["path"]), json.loads(parent["request"])
    return workflow.build(path[-1][0], path[-1][1], request["goal"]["objective"],
        request["message"]["scope"])


def test_live_alphafold_metadata_retains_pending_explicit_file_choice(tmp_path, monkeypatch):
    if os.environ.get("HMMER_NATIVE_ORACLE_ALPHAFOLD_LIVE_METADATA") != "1":
        pytest.skip("requires HMMER_NATIVE_ORACLE_ALPHAFOLD_LIVE_METADATA=1")
    identifier = _explicit("HMMER_NATIVE_ORACLE_ALPHAFOLD_IDENTIFIER")
    arguments = af.validate_alphafold_prediction_arguments({"identifier": identifier, "max_bytes": METADATA_LIMIT})
    _outputs(tmp_path, monkeypatch)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", _forbidden)
    client = PublicClients(timeout=TIMEOUT)
    calls = _observe_http(client, monkeypatch, expected_url=af.alphafold_prediction_url(identifier), limit=METADATA_LIMIT)
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=client)
        case = Scenario(tmp_path, store, tools=tools)
        commission = case.commission()
        commission["selection"].update(
            goal="Retain the explicitly selected existing AlphaFold metadata and a separately selected advertised coordinate File.",
            purpose="Return the acquired metadata Source, selected coordinate Source and its File reference.",
            initial_report_json="{}", schema_json=json.dumps(obj({"records": {"type": "array",
                "items": {"type": "string", "format": "reference"}, "x-source": "committed_record_refs"}})))
        selected = case.selection(tools=[host.PREDICTION_TOOL, host.FILE_TOOL])
        for information in selected["child_tool_info"]:
            information["resources"] = "api"
        commission["selection"]["assignment"]["selection"] = selected
        provider = ScriptedProvider([commission, action(host.PREDICTION_TOOL, arguments),
            ExpectedMetadataChoicePending("expected test interruption before the explicit AlphaFold File choice")])
        workflow = _workflow(store, tools, provider, case.directory, "alphafold-staged-live", case.descriptors)
        root = workflow.build("annotation", "root", "Retain selected AlphaFold Source and File evidence.", case.scope)
        with pytest.raises(ExpectedMetadataChoicePending, match="before the explicit AlphaFold File choice"):
            asyncio.run(root.run_async(workflow.context))
        parent, child = _episodes(store.db)
        assert all(row["state"] == "active" and row["completion"] is None and row["archive"] is None
            for row in (parent, child))
        operations = [dict(row) for row in store.db.execute("SELECT * FROM tool_operations")]
        assert len(operations) == 1 and operations[0]["name"] == host.PREDICTION_TOOL
        outcome = json.loads(operations[0]["result"])
        assert outcome["status"] == "completed"
        metadata = af.validate_alphafold_prediction_result(outcome["result"])
        assert metadata["requested"] == arguments and metadata["response"]["http_status"] == 200
        assert metadata["response"]["body_complete"] is True and metadata["parse_state"] != "decode_failed"
        source = store.get(metadata["source_ref"])
        raw = store.get_artifact(source["artifact_ref"])
        assert source["provider"] == af.SERVICE and source["accession"] == identifier and source["version"] is None
        assert source["artifact_ref"] == metadata["raw_artifact_ref"] == "artifact_" + hashlib.sha256(raw).hexdigest()
        assert metadata["native_json"] == json.loads(raw)
        pending = store.db.execute("SELECT * FROM runtime_model_calls WHERE episode_id=? AND call_index=1",
            (child["episode_id"],)).fetchone()
        assert pending is not None and pending["response"] is None
        assert json.loads(pending["request"])["context"]["last_local_outcome"]["result"]["source_ref"] == source["id"]
        assert len(provider.contexts) == 3 and len(calls) == 1
        counts = _counts(store.db)
        assert counts == {"runtime_episodes": 2, "runtime_actions": 2, "runtime_observations": 1,
            "runtime_model_calls": 3, "tool_operations": 1, "runtime_forms": 0, "runtime_report_attempts": 0}
        report = {"qualification": "live primary-service metadata GET; scripted scientific choices; active prefix only",
            "limits": "No File selection or download, coordinate parsing, parent delivery or completed-root claim.",
            "store_path": str(store.path), "run_path": str(case.directory.resolve()),
            "source_path": str(case.source.resolve()), "run_id": workflow.run_id,
            "episode_binding_descriptors": workflow.episode_bindings.as_record(),
            "controller_binding": workflow.controller_binding, "credit_binding": workflow.credit_binding,
            "child_credit_binding": workflow.child_credit_binding, "implementation_pins": _pins(),
            "parent": parent, "child": child, "pending_call": dict(pending),
            "metadata_operation": operations[0], "metadata_result": metadata,
            "http_requests": calls, "counts": counts}
    (tmp_path / PREFIX_REPORT).write_text(json.dumps(report, indent=2) + "\n")


def _clone_prefix(original_store, tmp_path):
    report = json.loads((original_store.parent / PREFIX_REPORT).read_bytes())
    assert Path(report["store_path"]) == original_store
    original_run, original_source = Path(report["run_path"]), Path(report["source_path"])
    assert original_run.parent == original_source.parent == original_store.parent
    assert not tmp_path.resolve().is_relative_to(original_store.parent)
    assert report["implementation_pins"] == _pins()
    wal = original_store / "state.sqlite3-wal"
    assert not wal.exists() or wal.stat().st_size == 0, "immutable backup requires the closed, checkpointed prefix"
    cloned_store, cloned_run, cloned_source = tmp_path / "store", tmp_path / "run", tmp_path / "source"
    shutil.copytree(original_store, cloned_store,
        ignore=shutil.ignore_patterns("state.sqlite3", "state.sqlite3-wal", "state.sqlite3-shm"))
    shutil.copytree(original_run, cloned_run)
    shutil.copytree(original_source, cloned_source)
    address = (original_store / "state.sqlite3").as_uri() + "?mode=ro&immutable=1"
    with sqlite3.connect(address, uri=True) as original, sqlite3.connect(cloned_store / "state.sqlite3") as copied:
        original.row_factory = sqlite3.Row
        before = _tables(original)
        parent, child = _episodes(original)
        assert parent == report["parent"] and child == report["child"]
        assert parent["run_id"] == report["run_id"]
        assert all(row["state"] == "active" for row in (parent, child))
        assert _counts(original) == report["counts"]
        operation = dict(original.execute("SELECT * FROM tool_operations").fetchone())
        assert operation == report["metadata_operation"] and operation["name"] == host.PREDICTION_TOOL
        assert json.loads(operation["result"])["result"] == report["metadata_result"]
        pending = original.execute("SELECT * FROM runtime_model_calls WHERE episode_id=? AND call_index=1",
            (child["episode_id"],)).fetchone()
        assert dict(pending) == report["pending_call"] and pending["response"] is None
        original.backup(copied)
    descriptors = report["episode_binding_descriptors"]
    scientific = next(value for value in descriptors if value["binding_id"] == "scientific_process")
    assert scientific == json.loads(child["request"])["message"]["scientific_process"]["mechanics_binding"]
    return report, cloned_store, cloned_run, before, parent, child


def _direct_closed_child(workflow, parent, child):
    parent_path, child_path = json.loads(parent["path"]), json.loads(child["path"])
    parent_request, child_request = json.loads(parent["request"]), json.loads(child["request"])
    commissions = list(workflow.store.db.execute("SELECT decision_index,action FROM runtime_actions WHERE run_id=? "
        "AND episode_id=? AND json_extract(action,'$.kind')='episode_child'", (workflow.run_id, parent["episode_id"])))
    assert len(commissions) == 1
    selected = json.loads(commissions[0]["action"])
    assert selected["kind"] == "episode_child" and selected["role"] == child_path[-1][0]
    assert child_path[-1][1] == "child_" + str(commissions[0]["decision_index"])
    assert selected["goal"] == child_request["goal"]["objective"]
    assert selected["scope"] == child_request["message"]["scope"]
    parent_goal = EpisodeGoal.from_record(parent_request["goal"])
    child_goal = EpisodeGoal.from_record(child_request["goal"])
    assert child_goal.parent_goal_id == parent_goal.goal_id
    records = EpisodeReturnRecords(workflow.store, workflow.run_id, failure_prefix="alphafold_live_replay_")
    binding = records.context(child["episode_id"])
    declaration = child_request["report_contract"]
    assert selected["purpose"] == declaration["decision"]
    assert json.loads(selected["schema_json"]) == declaration["measurements"]["schema"]
    contract = TypedReportContract(declaration["decision"], declaration["measurements"]["schema"],
        workflow.resolver(binding.scope, context=binding))
    assert contract.as_record() == declaration
    episode = workflow.build(child_path[-1][0], child_path[-1][1], selected["goal"], selected["scope"],
        parent=parent_goal, parent_path=tuple(map(tuple, parent_path)), contract=contract,
        initial=child_request["message"]["initial_report"],
        episode_assignment=child_request["message"]["episode_assignment"],
        scientific_process=child_request["message"]["scientific_process"],
        report_contract_declaration=child_request["message"].get("report_contract_declaration"))
    assert episode.source.request.as_record() == child_request
    context = Context.from_commission(tree=workflow.tree, run_id=workflow.run_id,
        parent_path=tuple(map(tuple, parent_path)), parent_goal_id=parent_goal.goal_id,
        child_goal_id=child_goal.goal_id, grain=child_path[-1][0], key=child_path[-1][1])
    result = asyncio.run(episode.run_async(context))
    return asyncio.run(episode.build_result(result)).as_record()


def _closed_replays(store, directory, descriptors, run_id, parent, child, final, entity_refs, monkeypatch):
    before, artifacts = _tables(store.db), _files(store.path / "artifacts")
    actual_get, actual_open = Store.get_artifact, Path.open
    entity_paths = {store.path / "artifacts" / reference[9:11] / reference[9:] for reference in entity_refs}
    blocked = []
    def guarded_get(current, reference):
        if reference in entity_refs:
            blocked.append(reference)
            raise AssertionError("closed replay reopened original entity bytes")
        return actual_get(current, reference)
    def guarded_open(path, *args, **kwargs):
        if path.absolute() in entity_paths:
            blocked.append(str(path))
            raise AssertionError("closed replay reopened an original entity path")
        return actual_open(path, *args, **kwargs)
    with monkeypatch.context() as guards:
        guards.setattr(PublicClients, "_http", _forbidden)
        guards.setattr(ToolRegistry, "execute_async", _forbidden)
        guards.setattr(ScriptedProvider, "complete", _forbidden)
        guards.setattr("gene_annotation_episode.native_lifecycle.prepare_job", _forbidden)
        guards.setattr(Store, "get_artifact", guarded_get)
        guards.setattr(Path, "open", guarded_open)
        provider = ScriptedProvider([])
        replay = _workflow(store, ToolRegistry(store, clients=PublicClients(timeout=TIMEOUT)), provider,
            directory, run_id, descriptors)
        root = _build_root(replay, parent)
        result = asyncio.run(root.run_async(replay.context))
        assert asyncio.run(root.build_result(result)).as_record() == final
        assert provider.contexts == []
        direct_provider = ScriptedProvider([])
        direct = _workflow(store, ToolRegistry(store, clients=PublicClients(timeout=TIMEOUT)), direct_provider,
            directory, run_id, descriptors)
        child_result = _direct_closed_child(direct, parent, child)
        stored_form = json.loads(store.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (run_id, child["episode_id"])).fetchone()[0])
        assert child_result == {"form": stored_form} and direct_provider.contexts == []
    assert blocked == [] and _tables(store.db) == before and _files(store.path / "artifacts") == artifacts
    return {"closed_root_equal": True, "direct_scientific_child_equal": True,
        "public_commission_context": True, "tables_and_artifact_bytes_unchanged": True,
        "entity_payload_reads": blocked}


def test_live_alphafold_explicit_advertised_file_resumes_copied_pending_prefix(tmp_path, monkeypatch):
    original_store = Path(_explicit("HMMER_NATIVE_ORACLE_ALPHAFOLD_PENDING_STORE")).resolve(strict=True)
    pointer = _explicit("HMMER_NATIVE_ORACLE_ALPHAFOLD_URL_POINTER")
    file_format = _explicit("HMMER_NATIVE_ORACLE_ALPHAFOLD_FILE_FORMAT")
    _outputs(tmp_path, monkeypatch)
    original_files = _files(original_store.parent)
    try:
        report, copied_store, copied_run, original_tables, parent, child = _clone_prefix(original_store, tmp_path)
        metadata = af.validate_alphafold_prediction_result(report["metadata_result"])
        arguments = af.validate_alphafold_file_arguments({"metadata_source_ref": metadata["source_ref"],
            "url_pointer": pointer, "file_format": file_format, "max_bytes": FILE_LIMIT})
        advertised_url = af.alphafold_advertised_file_url(metadata["native_json"], arguments=arguments)
        monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", _forbidden)
        client = PublicClients(timeout=TIMEOUT)
        calls = _observe_http(client, monkeypatch, expected_url=advertised_url, limit=FILE_LIMIT)
        provider = ScriptedProvider([action(host.FILE_TOOL, arguments)])
        with Store(copied_store) as store:
            assert _tables(store.db) == original_tables
            tools = ToolRegistry(store, clients=client)
            descriptors, run_id = report["episode_binding_descriptors"], report["run_id"]
            workflow = _workflow(store, tools, provider, copied_run, run_id, descriptors)
            assert workflow.controller_binding == report["controller_binding"]
            assert workflow.credit_binding == report["credit_binding"]
            assert workflow.child_credit_binding == report["child_credit_binding"]
            metadata_source = store.get(metadata["source_ref"])
            metadata_raw = store.get_artifact(metadata["raw_artifact_ref"])
            root = _build_root(workflow, parent)
            result = asyncio.run(root.run_async(workflow.context))
            final = asyncio.run(root.build_result(result)).as_record()
            assert len(provider.contexts) == 1 and len(calls) == 1
            assert provider.contexts[0]["goal"]["goal_id"] == json.loads(child["request"])["goal"]["goal_id"]
            assert dict(store.db.execute("SELECT * FROM tool_operations WHERE name=?",
                (host.PREDICTION_TOOL,)).fetchone()) == report["metadata_operation"]
            operation = store.db.execute("SELECT * FROM tool_operations WHERE name=?", (host.FILE_TOOL,)).fetchone()
            outcome = json.loads(operation["result"])
            assert outcome["status"] == "completed"
            downloaded = af.validate_alphafold_file_result(outcome["result"])
            assert downloaded["requested"] == arguments and downloaded["response"]["http_status"] == 200
            assert downloaded["response"]["body_complete"] is True
            assert downloaded["observed_identity"] == {"native_model_id": None, "state": "not_parsed"}
            source = store.get(downloaded["source_ref"])
            raw = store.get_artifact(downloaded["file"]["artifact_ref"])
            assert source["version"] is source["accession"] is None and source["uri"] == advertised_url
            assert source["parent_source_refs"] == [metadata["source_ref"]]
            assert len(source["auxiliary_artifact_refs"]) == 1
            assert downloaded["file"]["artifact_ref"] == source["artifact_ref"] == "artifact_" + hashlib.sha256(raw).hexdigest()
            assert downloaded["file"]["byte_length"] == len(raw)
            assert downloaded["association"] == {"version": "alphafold_advertised_file_association_v1",
                "metadata_source_ref": metadata["source_ref"], "metadata_artifact_ref": metadata["raw_artifact_ref"],
                "url_pointer": pointer, "advertised_url": advertised_url, "file_format": file_format}
            assert store.get(metadata["source_ref"]) == metadata_source
            assert store.get_artifact(metadata["raw_artifact_ref"]) == metadata_raw
            assert json.loads(metadata_raw) == metadata["native_json"]
            form = json.loads(store.db.execute("SELECT form FROM runtime_forms WHERE episode_id=?",
                (child["episode_id"],)).fetchone()[0])
            expected_refs = {metadata["source_ref"], source["id"], source["artifact_ref"]}
            assert set(form["records"]) == expected_refs
            attempt = store.db.execute("SELECT * FROM runtime_report_attempts").fetchone()
            assert attempt["failure"] is None and json.loads(attempt["form"]) == form
            assert expected_refs <= set(workflow.receipts.known(parent["episode_id"]))
            counts = _counts(store.db)
            assert counts == {"runtime_episodes": 2, "runtime_actions": 3, "runtime_observations": 3,
                "runtime_model_calls": 3, "tool_operations": 2, "runtime_forms": 1, "runtime_report_attempts": 1}
            yielded_parent, yielded_child = _episodes(store.db)
            assert all(row["state"] == "yielded" for row in (yielded_parent, yielded_child))
            entities = {metadata["raw_artifact_ref"], source["artifact_ref"]}
            entities.update(json.loads(row[0])["sequence_ref"] for row in store.db.execute("SELECT data FROM inputs"))
            entities.discard(None)
            replay = _closed_replays(store, copied_run, descriptors, run_id, yielded_parent, yielded_child,
                final, entities, monkeypatch)
            completion = {"qualification": "one live explicitly advertised File GET; copied original pending scientific episode",
                "limits": "Scripted choices; no new prediction service, model selection, coordinate parser, numerical grader or relocation claim.",
                "original_store_path": str(original_store), "copied_store_path": str(copied_store),
                "copied_run_path": str(copied_run), "run_id": run_id, "implementation_pins": _pins(),
                "metadata_result": metadata, "file_result": downloaded, "http_requests": calls,
                "counts": counts, "parent_form": form, "parent_received_refs": sorted(expected_refs),
                "replay": replay, "original_absolute_uris_and_producer_paths_preserved": True}
    finally:
        after = _files(original_store.parent)
        assert after == original_files, "follow-up changed the original pending prefix"
    completion["original_prefix_files_before"] = original_files
    completion["original_prefix_files_after"] = after
    completion["original_prefix_unchanged_by_this_followup"] = True
    (tmp_path / FILE_REPORT).write_text(json.dumps(completion, indent=2) + "\n")
