"""Current saved-result readers over explicitly selected completed257 evidence.

This composes a current read-side owner over literal old metadata and uses the
existing closed-request protocol. It does not reopen the original configured
binding, dispatch a new SCI commission, reproduce historical model wire or
repeat native/calculation work. Input directories are caller-selected opt-in
data; reusable code lives with tests.
"""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import sqlite3

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import instructional_model_context, state_frame
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import DecisionSource
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

from test_interval_pending_results import _commission, _fixture
from test_interval_results_presentation import (
    _assert_original_rows, _canonical, _inventory, _session, _sha,
    _source_for_original_context, _tables,
)
from test_homer_motif_saved_workflow import _archive


CASES = ("chromatin_weighted", "chromatin_insulation")
_SCIENCE = "episode_8731ed67018aca6f912b1cacfd1bf840c15d91cfb74f5a0c3b9a83b002de63ec"
_NATIVE = "episode_52b0b49482faa4a6b62d15d2b671c700b2fd258611690737d1ef8cdf43b1cff0"
_SAVED = "episode_068be6ca5addcca4414f00890e588e5331cfa46df7a36a49399ff52ef6d1ce31"
_CONTROL_NAMES = ("receipt.json", "intent.json", "handoff.json", "observation.json",
    "native-snapshot.json", "capture.json", "worker-plan.json", "worker-capture.json",
    "worker-execution.json", "sheet-evidence.json", "source-action.json", "writer-closure.json")


def _forbidden(*args, **kwargs):
    raise AssertionError("saved chromatin read-side check attempted new work or File bytes")


@pytest.fixture(params=CASES)
def saved_case(request, tmp_path):
    supplied = os.environ.get("HMMER_NATIVE_ORACLE_CHROMATIN_SAVED_PRESENTATION_CASES_JSON")
    if not supplied:
        pytest.skip("requires explicitly selected completed257 chromatin cases and inventory pins")
    cases = json.loads(supplied)
    assert set(cases) == set(CASES)
    selected = cases[request.param]
    assert set(selected) == {"directory", "inventory_sha256"}
    original = Path(selected["directory"]).resolve(strict=True)
    inventory = _inventory(original)
    assert _sha(_canonical(inventory).encode()) == selected["inventory_sha256"]
    database = original / "state/state.sqlite3"
    assert not database.is_symlink() and database.is_file()
    assert not database.with_name(database.name + "-wal").exists()
    assert not database.with_name(database.name + "-shm").exists()
    historical = tmp_path / "historical-metadata"
    (historical / "state").mkdir(parents=True)
    shutil.copy2(database, historical / "state/state.sqlite3")
    assert _sha(database.read_bytes()) == _sha((historical / "state/state.sqlite3").read_bytes())
    # No original database is opened, and neither owned copy contains science
    # bodies. Actual File identities and records remain in the copied database.
    connection = sqlite3.connect((historical / "state/state.sqlite3").resolve().as_uri()
        + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    before = _tables(connection)
    captures = {"decision-7.json": json.loads((original / "decision-7.json").read_bytes())}
    configuration = json.loads((original / "fixture-configuration.json").read_bytes())
    try:
        yield dict(name=request.param, original=original, inventory=inventory, historical=historical,
            source=connection, tables=before, captures=captures, configuration=configuration)
        assert _tables(connection) == before and connection.total_changes == 0
    finally:
        connection.close()
        assert _inventory(original) == inventory
        assert _sha((historical / "state/state.sqlite3").read_bytes()) == inventory["state/state.sqlite3"]["sha256"]


def _copy_application_metadata(case, directory, run_id):
    """Copy the exact controls read by the completed owner, without its runtimes."""
    state, run = directory / "state", directory / "run"
    state.mkdir(parents=True)
    shutil.copy2(case["historical"] / "state/state.sqlite3", state / "state.sqlite3")
    run.mkdir()
    original_run = case["original"] / "run"
    for name in ("scientific-process-library", "scientific-tool-library", "archive"):
        shutil.copytree(original_run / name, run / name, symlinks=True)
    for name in ("tool-knowledge", "launch-instructions"):
        (run / name).mkdir()
        shutil.copy2(original_run / name / "index.json", run / name / "index.json")
    for episode_id in (_NATIVE, _SAVED):
        relative = Path("execution-results") / digest([run_id, episode_id])
        destination = run / relative
        destination.mkdir(parents=True)
        shutil.copy2(original_run / relative / "assignment.json", destination / "assignment.json")
        key = run_id + ":" + episode_id + ":0"
        action = Path("native-chromatin-interaction-actions") / digest(key)
        (destination / action).mkdir(parents=True)
        for name in _CONTROL_NAMES:
            source = original_run / relative / action / name
            if source.exists():
                assert source.is_file() and not source.is_symlink()
                shutil.copy2(source, destination / action / name)
    assert not (state / "artifacts").exists()
    return state, run


def _work_guards(monkeypatch, case, state):
    for target in (
        "gene_annotation_episode.native_chromatin_interaction_results.capture_chromatin_native_files",
        "gene_annotation_episode.native_chromatin_interaction_results.prepare_chromatin_result_worker",
        "gene_annotation_episode.native_chromatin_interaction_results.retained_native_file",
        "gene_annotation_episode.native_chromatin_interaction_driver.run_chromatin_interaction_driver",
        "gene_annotation_episode.chromatin_interaction_result_worker.run_chromatin_result_worker",
        "gene_annotation_episode.chromatin_interaction_calculations.calculate_chromatin_components",
        "gene_annotation_episode.chromatin_interaction_calculations.calculate_contact_enrichment",
        "gene_annotation_episode.chromatin_interaction_calculations.calculate_insulation_components",
        "gene_annotation_episode.chromatin_interaction_inputs.build_chromatin_sheet",
        "gene_annotation_episode.chromatin_interaction_tables.open_chromatin_contact_tables",
        "gene_annotation_episode.chromatin_interaction_tables.read_chromatin_sheet_tables",
        "gene_annotation_episode.chromatin_cooler_inputs.read_cooler_contacts",
        "gene_annotation_episode.chromatin_hic_inputs.read_hic_contacts",
        "gene_annotation_episode.acquisition.PublicClients._http",
        "socket.create_connection", "socket.socket.connect", "socket.socket.connect_ex",
    ):
        monkeypatch.setattr(target, _forbidden)
    for name in ("prepare_job", "start_prepared", "resume_start", "status", "wait_job", "collect", "cancel", "release"):
        monkeypatch.setattr("gene_annotation_episode.native_lifecycle." + name, _forbidden)
    for name in ("get_artifact", "put", "artifact", "commit_reasoning"):
        monkeypatch.setattr(Store, name, _forbidden)
    monkeypatch.setattr(ToolRegistry, "execute_async", _forbidden)
    monkeypatch.setattr(_SessionConnection, "complete", _forbidden)
    import builtins
    resource = case["configuration"]["factory"]["resources"]["here"]
    software = resource["native_chromatin_interactions"][0]["software"]
    protected = (case["original"], Path(resource["workspace"]), state / "artifacts",
        Path(software["module_root"]), Path(software["python_executable"]).parent.parent,
        *(Path(row["package_root"]) for row in software["dependencies"]),
        *(Path(row["path"]) for row in (software.get("native_runtime") or {}).get("files", ())))
    attempts = []
    def body_guard(function, *, descriptor=False):
        def call(path, *args, **kwargs):
            if isinstance(path, (str, os.PathLike)):
                candidate = Path(path)
                if descriptor and not candidate.is_absolute() and kwargs.get("dir_fd") is not None:
                    candidate = Path(os.readlink("/proc/self/fd/" + str(kwargs["dir_fd"]))) / candidate
                candidate = candidate.absolute()
                flags = args[0] if descriptor and args else kwargs.get("flags", 0)
                if not descriptor or not flags & os.O_DIRECTORY:
                    if any(candidate == root or root in candidate.parents for root in protected):
                        attempts.append(str(candidate))
                        _forbidden()
            return function(path, *args, **kwargs)
        return call
    monkeypatch.setattr(builtins, "open", body_guard(builtins.open))
    monkeypatch.setattr(Path, "open", body_guard(Path.open))
    monkeypatch.setattr(os, "open", body_guard(os.open, descriptor=True))
    return attempts


def _negative_controls(store, receipts, receipt):
    """Explicit adversarial mutations use only this owned copy and roll back."""
    rejected = []
    for name in ("producer_path", "artifact_path", "selection_order", "operation_identity"):
        changed = deepcopy(receipt)
        if name == "producer_path":
            changed["worker_plan"]["directory"] += "-changed"
        elif name == "artifact_path":
            changed["worker_plan"]["sheet_bundle"]["sheet"]["path"] += "-changed"
        elif name == "selection_order":
            files = changed["intent"]["assignment"]["selector"]["saved_sheet_bundle"]["tables"]
            files[:2] = reversed(files[:2])
        else:
            changed["intent"]["operation_key"] += "1"
        with pytest.raises(ValueError):
            receipts.validate_worker(changed)
        rejected.append(name)
    invocation = receipt["intent"]
    for name in ("uncompleted_action_keeps_current_roots", "current_artifact_size_conflict"):
        store.db.execute("SAVEPOINT chromatin_negative_control")
        try:
            if name == "uncompleted_action_keeps_current_roots":
                store.db.execute("UPDATE runtime_actions SET result=NULL WHERE run_id=? AND episode_id=? AND decision_index=0",
                    (invocation["run_id"], invocation["episode_id"]))
            else:
                artifact = receipt["worker_plan"]["sheet_bundle"]["sheet"]["file"]["artifact_ref"]
                store.db.execute("UPDATE artifacts SET size=size+1 WHERE id=?", (artifact,))
            with pytest.raises(ValueError):
                receipts.validate_worker(deepcopy(receipt))
            rejected.append(name)
        finally:
            store.db.execute("ROLLBACK TO chromatin_negative_control")
            store.db.execute("RELEASE chromatin_negative_control")
    return rejected


def _receiver(flow, root, record, expected, session, monkeypatch):
    """Use the actual completed return; stop before any new dispatch/journaling."""
    from method_loop.episode import EpisodeView
    receiver = {}
    scope = flow.context.enter(root.grain, root.key)
    try:
        assert scope == root.source.path == record.path
        view = EpisodeView(grain=root.grain, key=root.key, path=scope, units_consumed=record.units_consumed,
            updates=tuple(flow.context._child_updates.get(scope, ())), controller_state=record.controller_state,
            episode_ref=record.episode_ref, request=record.request)
        assert [plain(report.as_record()) for report in view.child_reports] == [expected]
        class Captured(BaseException): pass
        async def capture(source, context, schema):
            assert source is root.source and context["child_reports"] == [expected]
            instructions = source.instructions(context)
            model = instructional_model_context(context)
            wire, actual = session._presentation(source.episode_id, "REASONING", instructions, state_frame(model))
            repeated, repeated_instructions = session._presentation(source.episode_id, "REASONING", instructions,
                state_frame(model, model))
            assert repeated == wire and actual == repeated_instructions == instructions
            assert wire.startswith("TASK") and "STEERING" in wire and context["goal"]["objective"] in wire
            receiver.update(context_sha256=_sha(_canonical(context).encode()), wire=wire,
                wire_sha256=_sha(wire.encode()), actual_child_form_sha256=_sha(_canonical(expected).encode()),
                full_current_receiver_builder_verified=True, historical_postreturn_model_call_claimed=False)
            raise Captured()
        with monkeypatch.context() as guarded:
            guarded.setattr(DecisionSource, "call", capture)
            calls = root.source.calls
            with pytest.raises(Captured):
                asyncio.run(root.source.next(view))
            assert root.source.calls == calls
    finally:
        flow.context.leave(scope)
    return receiver


def test_completed_saved_results_current_builder_and_actual_receiver_without_science(saved_case, tmp_path, monkeypatch):
    case = saved_case
    capture = case["captures"]["decision-7.json"]
    run_id = capture["context"]["execution_target"]["run_id"]
    native = _commission(case["source"], run_id, _NATIVE, "results")
    saved = _commission(case["source"], run_id, _SAVED, "results")
    science = _commission(case["source"], run_id, _SCIENCE, "scientific_process")
    assert capture["episode_id"] == _SAVED and saved["selected"]["assignment"] == capture["context"]["execution_assignment"]
    assert saved["parent_episode_id"] == native["parent_episode_id"] == _SCIENCE
    assert science["request"]["goal"]["objective"] == case["configuration"]["goal"]
    assert "instructions" not in capture and capture["context"]["last_local_outcome"] is None
    directory = tmp_path / "current-saved-read-side"
    state, run = _copy_application_metadata(case, directory, run_id)
    fixture = _fixture(case, monkeypatch)
    assert run_id == fixture.RUN_ID
    configuration = deepcopy(case["configuration"])
    original_binding = deepcopy(configuration["scientific_binding"])
    library = ScientificProcessLibrary(run / "scientific-process-library")
    tools = ScientificToolLibrary(run / "scientific-tool-library")
    assert library.as_record() == original_binding["configuration"]["library"]
    assert tools.as_record() == original_binding["configuration"]["tool_library"]
    current_binding = ScientificProcessEpisodes(None, library=library, tool_library=tools,
        child_roles=original_binding["configuration"]["child_roles"]).as_record()
    assert current_binding["configuration"] == original_binding["configuration"]
    configuration["scientific_binding"] = current_binding
    proof = dict(version="chromatin_saved_current_read_side_verification_v1", case=case["name"], passed=False,
        new_native_calls=0, new_calculations=0, new_workers=0, new_sources=0, new_provider_decisions=0,
        new_model_call_rows=0, new_actions=0, new_observations=0,
        new_saved_commission_verified=False, historical_wire_or_postcollect_callback_claimed=False,
        original_configured_binding_reopen_verified=False,
        original_binding=original_binding, actual_current_read_side_binding=current_binding,
        original_inventory_sha256=_sha(_canonical(case["inventory"]).encode()),
        integrity_inventory_reads_performed=True, scientific_File_bodies_copied=False)
    class NoDecisions:
        def __init__(self): self.cleanup = []
        async def complete(self, *args, **kwargs): _forbidden()
        async def release(self, episode_id): self.cleanup.append(episode_id)
    provider = NoDecisions()
    store = None
    try:
        with monkeypatch.context() as guarded:
            attempted_reads = _work_guards(guarded, case, state)
            store = Store(state)
            flow, _ = fixture.assemble(store, directory, provider, configuration)
            constructor = _assert_original_rows(store.db, case["tables"])
            before = _tables(store.db)
            files = _inventory(run)
            records = EpisodeReturnRecords(store, run_id, failure_prefix="chromatin_saved_current_")
            scientific_context = records.context(_SCIENCE)
            flow.scientific_process_binding.validate_context(scientific_context)
            with pytest.raises(ContractError, match="scientific_execution_identity_mismatch"):
                flow.scientific_process_binding.validate_execution_context(scientific_context)
            assert _tables(store.db) == before
            context = records.context(_SAVED)
            source = _source_for_original_context(flow, context)
            binding = flow.specialist(source)
            context = flow.binding_context(source)
            assert plain(context.request) == saved["request"]
            host, returns = binding.native_chromatin_interaction_results, binding.native_chromatin_interaction_returns
            origins = returns.authenticate_received_saved_bundle(context, plain(context.assignment)["selector"]["saved_sheet_bundle"])
            assert origins == (dict(episode_id=_NATIVE, operation_key=run_id + ":" + _NATIVE + ":0"),)
            receipt, = host.receipts.completed_receipts(context)
            assert receipt["intent"]["assignment"] == saved["selected"]["assignment"]
            assert receipt["worker_plan"]["directory"] != str(host.receipts.action_directory(_SAVED,
                run_id + ":" + _SAVED + ":0") / "worker")
            built = binding.decision_context(context, None)
            assert built["execution_assignment"] == plain(context.assignment)
            assert built["execution_target"] == capture["context"]["execution_target"]
            task = built["selected_execution_task"]
            full_info = science["request"]["message"]["episode_assignment"]["selection"]["child_tool_info"]
            assert task["scientific_question"] == science["selected"]["goal"]
            assert task["selected_tool_info"] == full_info and task["selector"] == plain(context.assignment)["selector"]
            assert built["execution_target_description"]["observation_basis"] == "received_saved_sheet_and_original_receipts"
            assert built["execution_progress"]["execution_completed"] is True
            frozen = json.loads(store.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?",
                (run_id, _SAVED)).fetchone()[0])
            assert built["execution_progress"][fixture.PROJECTION_SOURCE] == frozen["chromatin"]
            assert built["execution_progress"][fixture.SAVED_SOURCE] == frozen["saved"]
            assert frozen["saved"] == [task["selector"]["saved_sheet_bundle"]]
            bundle = frozen["saved"][0]
            if case["name"] == "chromatin_weighted":
                assert len(bundle["tables"]) == 8 and bundle["tables"][:4] == bundle["tables"][4:]
                assert task["selector"]["parameters"]["contact"]["fold_threshold"] == 0.5
                assert native["selected"]["assignment"]["selector"]["parameters"]["contact"]["fold_threshold"] == 2
                first, second = frozen["chromatin"][0]["rows"]
                assert first["fields"]["fold_enrichment"]["numerator"] == 6
                assert first["fields"]["fold_enrichment"]["denominator"] == 7
                assert first["fields"]["above_fold_threshold"]["value"] is True
                assert second["fields"]["fold_enrichment"]["value"] is None
                assert second["fields"]["fold_enrichment"]["reason"] == "zero_denominator"
            else:
                assert len(bundle["tables"]) == 3 and task["selector"]["projection"]["kind"] == "domains"
                row, = frozen["chromatin"][0]["rows"]
                assert [row["fields"][key]["value"] for key in task["selector"]["projection"]["fields"]] == [20, 40, 20, 0.02]
                assert row["fields"]["domain_size_kb"]["denominator"] == 1000
            # The base is an authentic precollect capture. Only the entire
            # current binding builder's fields replace it for this labelled view.
            current = {**deepcopy(capture["context"]), **built}
            instructions = source.instructions(current)
            model = instructional_model_context(current)
            session = _session(tmp_path / "saved-results-session")
            wire, actual = session._presentation(_SAVED, "REASONING", instructions, state_frame(model))
            repeated, _ = session._presentation(_SAVED, "REASONING", instructions, state_frame(model, model))
            assert wire == repeated and actual == instructions and wire.startswith("TASK") and "STEERING" in wire
            assert task["scientific_question"] in wire
            for info in full_info:
                assert info["name"] in wire and info["description"] in wire and info["instructions"] in wire
            for file in (bundle["sheet"], *bundle["tables"]):
                assert all(str(file[key]) in wire for key in ("artifact_ref", "sha256", "size_bytes", "format"))
            assert str(case["original"]) not in wire
            negative = _negative_controls(store, host.receipts, receipt)
            assert _tables(store.db) == before
            # The existing closed-request protocol under this current read-side
            # composition supplies the actual form; it does not reopen the
            # recorded binding for new dispatch or rewrite its requests/grants.
            root, record, archive = asyncio.run(fixture.run_root(flow, configuration))
            root_row = store.db.execute("SELECT * FROM runtime_episodes WHERE run_id=? AND episode_id=?",
                (run_id, record.episode_id)).fetchone()
            assert archive == _archive(root_row, run)
            returned = archive["units"][0]["child_result"]["form"]
            assert set(returned) == {"chromatin"} and frozen["chromatin"][0] in returned["chromatin"]
            root_context = records.context(record.episode_id)
            for file in (bundle["sheet"], *bundle["tables"]):
                assert file["artifact_ref"] not in set(flow.receipts.known(root_context.episode_id))
                assert returns.resolve_received(root_context, file["artifact_ref"], "artifact") is False
            with pytest.raises(ValueError, match="saved_bundle_not_received"):
                returns.authenticate_received_saved_bundle(root_context, bundle)
            receiver = _receiver(flow, root, record, returned, _session(tmp_path / "receiving-session"), guarded)
            assert _tables(store.db) == before and _inventory(run) == files and attempted_reads == []
            assert list((state / "artifacts").iterdir()) == []
            proof.update(passed=True, original_rows_unchanged=True, constructor=constructor,
                original_SCI_new_dispatch_denied=True, current_read_side_closed_record_restoration_verified=True,
                full_current_saved_binding_builder_verified=True, saved_task_wire=wire,
                saved_task_wire_sha256=_sha(wire.encode()), saved_context_sha256=_sha(_canonical(current).encode()),
                original_precollect_context_sha256=_sha(_canonical(capture["context"]).encode()),
                exact_saved_assignment=saved["selected"]["assignment"], full_original_tool_info=full_info,
                authenticated_origins=list(origins), actual_frozen_saved_form=frozen,
                actual_parent_received_form=returned, receiver=receiver,
                engineering_owned_copy_negative_controls=negative, unchanged_run_inventory_sha256=_sha(_canonical(files).encode()),
                unchanged_logical_tables_sha256=_sha(_canonical(before).encode()),
                provider_cleanup_callbacks=provider.cleanup, application_body_open_attempts=attempted_reads)
    except BaseException as error:
        proof["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        if store is not None:
            store.close()
        proof["original_inventory_unchanged"] = _inventory(case["original"]) == case["inventory"]
        (tmp_path / "CHROMATIN_SAVED_CURRENT_READ_SIDE.json").write_text(json.dumps(proof, indent=2, allow_nan=False) + "\n")
        assert proof["original_inventory_unchanged"]
