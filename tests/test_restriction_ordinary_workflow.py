"""Opt-in current EcoRI/native then saved-reader Workflow and literal replay.

Decisions and continuation inputs are scripted engineering choices. Native
observations, jobs, Sources, receipts and typed returns use their actual owners.
The commercial selection is not executed by this test.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import stat

import pytest
from method_loop.episode import EpisodeView

from fluorescence_flowio_test_support import require_bounded_runtime
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode import restriction_mapping_native as native
from gene_annotation_episode import restriction_mapping_readers as readers
from gene_annotation_episode import restriction_mapping_registry as adapter
from gene_annotation_episode import restriction_mapping_worker as worker
from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.restriction_mapping_action_records import RestrictionMappingActionRecords
from gene_annotation_episode.restriction_mapping_jobs import RestrictionMappingJobs
from gene_annotation_episode.restriction_mapping_publication import read_published_restriction_result
from gene_annotation_episode.restriction_mapping_returns import restriction_mapping_fact_sources
from gene_annotation_episode.restriction_mapping_tool_info import TOOL
from gene_annotation_episode.runtime import DecisionSource, Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_homer_motif_saved_workflow import _archive, _archive_value, _encode
from test_vcf_result_workflow import _tables, _zero


GATE = "HMMER_NATIVE_ORACLE_RESTRICTION_EPISODE"
PUBLICATION = Path(__file__).resolve().parents[1] / "research/slotted_process_library/publications/2026-10-24-001"
SEQUENCE = "AAAAGAATTCTTTT"
QUESTION = ("For the explicitly supplied 14-nucleotide DNA, use EcoRI with linear topology and return "
    "its retained native positions, recognition spans, Watson/Crick boundaries and qualified enzyme populations. "
    "Compare the saved-reader result with the original selected search without repeating that search. "
    "Keep conditional sequence predictions distinct from measured digestion or gene-function confidence.")
FACT = "restriction_mapping_results"
POLICY = dict(memory_bytes=20 * 1024 ** 3, scratch_bytes=4 * 1024 ** 3, wall_seconds=None)


def _forbidden(*args, **kwargs):
    raise AssertionError("restriction replay or host attempted new scientific work")


def _checkpoint(store, output, proof):
    proof["tables"] = _tables(store)
    proof["counts"] = {name: len(rows) for name, rows in proof["tables"].items()
        if name.startswith("runtime_") or name in {"tool_operations", "restriction_mapping_operations"}}
    temporary = output.with_suffix(".pending.json")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(proof, stream, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, output)


def _files(directory):
    return {str(path.relative_to(directory)): dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        size_bytes=path.stat().st_size, mode=stat.S_IMODE(path.stat().st_mode))
        for path in sorted(directory.rglob("*")) if path.is_file()}


def _form():
    fields = restriction_mapping_fact_sources()[FACT]["report_schema"]
    fields["items"]["properties"]["selection_policy"] = dict(type="string", const="all_own_completed_results")
    return dict(type="object", properties=dict(restriction_evidence=fields),
        required=["restriction_evidence"], additionalProperties=False)


def _controller(path, initial):
    horizon = 1 if path[-1][0] == "annotation" else 2

    def estimate(history, parameters, contexts):
        return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= horizon else 1),
            parameters, dict(engineering_fixture="one_selected_EcoRI_action_and_one_saved_reader"))

    return YieldController(str(path), initial, 0, estimate_with_context=estimate)


def _assemble(store, directory, proof, provider):
    factory = ExecutionServiceFactory.from_record(proof["factory"])
    registry = ToolRegistry(store, clients=PublicClients(ncbi_email=None), job_limits=deepcopy(POLICY))
    application = factory(store, run_id=proof["run_id"], directory=directory, tool_registry=registry)
    assert registry.catalog()[TOOL] == proof["selected_tool_contract"]
    flow = Workflow(store, registry, provider, directory, proof["run_id"], _controller, _zero,
        project_child_credit=_zero,
        episode_binding_descriptors=[proof["scientific_binding"], *application.episode_binding_descriptors],
        role_credit_bindings=application.role_credit_bindings,
        job_progress_provider=application.job_progress_provider,
        episode_record_receipts=True, initial_known_record_refs=[])
    return flow, registry


class _Choices:
    def __init__(self, store, library, proof, output):
        self.store, self.library, self.proof, self.output = store, library, proof, output
        self.connection = object.__new__(_SessionConnection)
        self.connection.scientific_prompt_states = {}
        self.cleanup = []

    async def complete(self, episode_id, role, instructions, context, schema):
        context = plain(context)
        grain = json.loads(self.store.db.execute("SELECT path FROM runtime_episodes WHERE episode_id=?",
            (episode_id,)).fetchone()[0])[-1][0]
        turn = self.store.db.execute("SELECT count(*)+1 FROM runtime_model_calls WHERE run_id=? "
            "AND episode_id=? AND response IS NOT NULL", (self.proof["run_id"], episode_id)).fetchone()[0]
        wire, shown_instructions = self.connection._presentation(episode_id, role, instructions, context)
        self.proof["calls"].append(dict(episode_id=episode_id, grain=grain, turn=turn,
            context=deepcopy(context), wire=wire, wire_instructions=plain(shown_instructions)))
        _checkpoint(self.store, self.output, self.proof)
        assert role == "REASONING" and context["goal"]["objective"] == QUESTION
        assert not context.get("feedback"), "preserve the original failed prefix before another selection"
        if grain == "annotation":
            assert turn == 1
            chosen = dict(kind="episode_child", role="scientific_process", goal=QUESTION,
                scope=deepcopy(self.proof["scope"]),
                purpose="Return the original selected restriction values and their saved-reader comparison.",
                schema_json=json.dumps(_form()), initial_report_json="{}", assignment=dict(selection=dict(
                    version="scientific_process_selection_v3", evidence_axis=self.library.reference("A101"),
                    thought_pattern=self.library.reference("P01"), child_tool_info=[dict(name=TOOL, resources="local")]),
                    evidence_refs=[self.proof["subject_ref"]], constraints={}, context=dict(
                        sequence_ref=self.proof["subject_ref"], selected_enzyme="EcoRI", topology="linear")))
        else:
            assert grain == "scientific_process" and turn in (1, 2)
            assert wire.startswith("TASK\n") and "\n\nSTEERING\n" in wire and QUESTION in wire
            assert context["requested_form"] == _form()
            assert "Selected tool: " + TOOL + " (local)" in wire
            info, = context["scientific_process"]["child_tool_info"]
            assert set(info) == {"name", "description", "resources", "instructions"}
            assert info["name"] == TOOL and info["resources"] == "local"
            assert info["description"] == self.proof["selected_tool_contract"]["description"]
            assert self.proof["selected_tool_contract"]["instructions"] in info["instructions"]
            if turn == 1:
                self.proof["actual_selected_tool_info"] = deepcopy(info)
                arguments = dict(mode="native", sequence_ref=self.proof["subject_ref"],
                    enzyme_selection=dict(kind="explicit", names=["EcoRI"]), topology="linear")
            else:
                assert info == self.proof["actual_selected_tool_info"]
                previous = context["last_local_outcome"]
                assert previous["status"] == "completed" and previous["result"]["work_mode"] == "native"
                assert previous["result"]["population"] == dict(selected_enzyme_count=1,
                    attempted_enzyme_count=1, returned_enzyme_count=1,
                    complete_empty_enzyme_count=0, recognition_match_count=1)
                assert previous["result"]["source_ref"] in wire
                arguments = dict(mode="saved", result_source_ref=previous["result"]["source_ref"])
            chosen = dict(kind="tool", tool=TOOL, arguments=arguments)
        answer = _encode(dict(selection=chosen, report_update={}), schema)
        self.proof["calls"][-1]["response"] = deepcopy(answer)
        _checkpoint(self.store, self.output, self.proof)
        return answer

    async def release(self, episode_id):
        self.cleanup.append(episode_id)


class _NoDecisions:
    def __init__(self):
        self.cleanup = []

    async def complete(self, *args, **kwargs):
        _forbidden()

    async def release(self, episode_id):
        self.cleanup.append(episode_id)


def _closed_replay(store, directory, proof, groups, monkeypatch):
    before = _tables(store)
    artifacts, run_files = _files(store.path / "artifacts"), _files(directory)
    episodes = list(store.db.execute("SELECT * FROM runtime_episodes ORDER BY json_array_length(path)"))
    parent_archive, science_archive = [_archive(dict(row), directory) for row in episodes]
    provider, receiver = _NoDecisions(), {}
    with monkeypatch.context() as guarded:
        for module, names in ((native_lifecycle, ("prepare_job", "start_prepared", "resume_start", "wait_job",
                "status", "collect", "cancel", "release")),
                (adapter, ("prepare_restriction_work", "publish_restriction_work", "retire_restriction_work")),
                (RestrictionMappingJobs, ("reserve", "run_async"))):
            for name in names:
                guarded.setattr(module, name, _forbidden)
        guarded.setattr(ToolRegistry, "execute_async", _forbidden)
        guarded.setattr(PublicClients, "_http", _forbidden)
        guarded.setattr(Store, "get_artifact", _forbidden)
        flow, _ = _assemble(store, directory, proof, provider)
        root = flow.build("annotation", "root", QUESTION, proof["scope"])
        record = asyncio.run(root.run_async(flow.context))
        assert _archive_value(record) == parent_archive
        assert _archive_value(asyncio.run(root.build_result(record))) == dict(credit=0, pending_handles=[])
        commission = flow.journal.row("runtime_actions", root.source.episode_id, 0)
        closed = flow.selected(root.source, json.loads(commission["action"]), 0)
        assert _archive_value(closed.record) == science_archive
        assert plain(closed.result.as_record()) == dict(form=dict(restriction_evidence=groups))
        parent_context = flow.binding_context(root.source)
        resolve = flow.resolver(plain(parent_context.scope), context=parent_context)
        assert resolve("EcoRI", "restriction_enzyme") is True
        assert resolve("ecori", "restriction_enzyme") is False
        assert resolve("BamHI", "restriction_enzyme") is False
        scope = flow.context.enter(root.grain, root.key)
        try:
            view = EpisodeView(grain=root.grain, key=root.key, path=scope, units_consumed=record.units_consumed,
                updates=tuple(flow.context._child_updates.get(scope, ())), controller_state=record.controller_state,
                episode_ref=record.episode_ref, request=record.request)

            class ReceiverCaptured(BaseException):
                pass

            async def capture(source, context, schema):
                assert context["child_reports"] == [dict(restriction_evidence=groups)]
                connection = object.__new__(_SessionConnection)
                connection.scientific_prompt_states = {}
                wire, instructions = connection._presentation(source.episode_id, "REASONING",
                    source.instructions(context), state_frame(plain(context)))
                for field in ("native_search_positions_1based", "watson_boundary_0based",
                        "crick_boundary_0based", "recognition_match_count", "complete_empty_enzyme_count"):
                    assert field in wire
                assert "EcoRI" in wire and all(group["source_ref"] in wire for group in groups)
                receiver.update(context=plain(context), wire=wire, instructions=plain(instructions),
                    current_receiver_reconstruction=True, historical_post_return_decision_claimed=False)
                raise ReceiverCaptured()

            guarded.setattr(DecisionSource, "call", capture)
            calls = root.source.calls
            with pytest.raises(ReceiverCaptured):
                asyncio.run(root.source.next(view))
            assert root.source.calls == calls
        finally:
            flow.context.leave(scope)
    assert _tables(store) == before
    assert _files(store.path / "artifacts") == artifacts and _files(directory) == run_files
    return dict(all_rows_unchanged=True, artifact_and_run_file_bytes_modes_unchanged=True,
        new_provider_decisions=0, new_tool_actions=0, new_workers=0, new_native_searches=0,
        new_reader_calculations=0, receiver=receiver, cleanup=provider.cleanup)


def test_genuine_current_ecori_saved_typed_parent_cache_and_closed_replay(tmp_path, monkeypatch):
    selected = os.environ.get(GATE)
    if selected is None:
        pytest.skip("requires explicit JSON opt-in for one current public EcoRI native action")
    gate = json.loads(selected)
    assert type(gate) is dict and set(gate) == {"enabled"} and gate["enabled"] is True
    require_bounded_runtime()
    output = tmp_path / "RESTRICTION_ORDINARY_WORKFLOW.json"
    proof = dict(version="restriction_current_ordinary_workflow_observation_v1", passed=False,
        phase="preparing", run_id="current-ordinary-restriction", calls=[], workers=[], cache=[],
        whole_episode_completed=False, commercial_public_invocation_verified=False,
        historical718_or719_test_suites_repeated=False, external_model_calls=0,
        host_enzyme_searches=0, host_mapping_reader_calls=0)
    with Store(tmp_path / "store") as store:
        try:
            store.create_problem(raw_sequence=SEQUENCE, molecule="dna")
            directory, workspace = tmp_path / "run", tmp_path / "workspace"
            workspace.mkdir()
            factory = ExecutionServiceFactory(dict(ordinary=dict(kind="local", workspace=str(workspace),
                policy=deepcopy(POLICY))), {}, 2, .25, .5)
            catalog = ToolRegistry(store, clients=PublicClients(ncbi_email=None), job_limits=deepcopy(POLICY))
            factory.configure_tool_registry(catalog)
            proof.update(factory=factory.as_record(), scope=store.validate_scope(), subject_ref=store.targets()[0]["id"],
                selected_tool_contract=deepcopy(catalog.catalog()[TOOL]))
            proof["scientific_binding"] = prepare_scientific_binding(run_directory=directory,
                source_directory=PUBLICATION, tool_catalog=catalog.catalog(), child_roles=["scientific_process"])
            provider = _Choices(store, ScientificProcessLibrary(directory / "scientific-process-library"), proof, output)
            flow, registry = _assemble(store, directory, proof, provider)
            monkeypatch.setattr(PublicClients, "_http", _forbidden)
            monkeypatch.setattr(native, "run_restriction_mapping", _forbidden)
            monkeypatch.setattr(readers, "read_restriction_mapping", _forbidden)
            monkeypatch.setattr(worker, "read_restriction_mapping", _forbidden)
            monkeypatch.setattr(worker, "run_restriction_worker", _forbidden)
            actual_run = RestrictionMappingJobs.run_async

            async def observed_run(owner, operation_key):
                result = await actual_run(owner, operation_key)
                state = owner.publication_state(operation_key)
                reservation = state["reservation"]
                captured = dict(operation_key=operation_key, reservation=deepcopy(reservation),
                    execution_proof=deepcopy(state["execution_proof"]),
                    execution_proof_artifact_ref=state["execution_proof_artifact_ref"], files={})
                proof["workers"].append(captured)
                proof["phase"] = "original_worker_closed_before_publication_checks"
                _checkpoint(store, output, proof)
                handle = owner.store.get_artifact(state["execution_proof"]["handle_artifact_ref"])
                captured["native_handle"] = json.loads(handle)
                captured["native_handle_pin"] = dict(sha256=hashlib.sha256(handle).hexdigest(), size_bytes=len(handle))
                for name in ("native.json", "catalog.json", "mapping.json", "manifest.json"):
                    path = Path(reservation["output_directory"]) / name
                    if path.is_file():
                        raw = path.read_bytes()
                        captured["files"][name] = dict(sha256=hashlib.sha256(raw).hexdigest(),
                            size_bytes=len(raw), value=json.loads(raw))
                _checkpoint(store, output, proof)
                return result

            monkeypatch.setattr(RestrictionMappingJobs, "run_async", observed_run)
            actual_execute = registry.execute_async

            async def execute(name, arguments, **kwargs):
                outcome = await actual_execute(name, arguments, **kwargs)
                if name == TOOL and outcome["status"] in {"completed", "partial"}:
                    proof["phase"] = "original_operation_published_before_cache_checks"
                    _checkpoint(store, output, proof)
                    before, artifacts = _tables(store), _files(store.path / "artifacts")
                    with monkeypatch.context() as guarded:
                        for module, names in ((RestrictionMappingJobs, ("reserve", "run_async")),
                                (adapter, ("_software", "publish_restriction_result")),
                                (native_lifecycle, ("prepare_job", "start_prepared", "resume_start", "wait_job", "status"))):
                            for port in names:
                                guarded.setattr(module, port, _forbidden)
                        guarded.setattr(registry, "_sequence", _forbidden)
                        guarded.setattr(registry, "_save", _forbidden)
                        guarded.setattr(Store, "artifact", _forbidden)
                        guarded.setattr(Store, "put", _forbidden)
                        cached = await actual_execute(name, deepcopy(arguments), **kwargs)
                    assert cached == outcome and _tables(store) == before
                    assert _files(store.path / "artifacts") == artifacts
                    proof["cache"].append(dict(operation_key=kwargs["operation_key"], mode=arguments["mode"],
                        same_original_invocation=True, all_rows_and_artifacts_unchanged=True,
                        authenticated_retained_body_reads_allowed=True, new_workers=0,
                        new_native_searches=0, new_reader_calculations=0, new_publications=0))
                    _checkpoint(store, output, proof)
                return outcome

            monkeypatch.setattr(registry, "execute_async", execute)
            root = flow.build("annotation", "root", QUESTION, proof["scope"])
            _checkpoint(store, output, proof)
            record = asyncio.run(root.run_async(flow.context))
            proof.update(phase="workflow_returned_before_postchecks", whole_episode_completed=True)
            _checkpoint(store, output, proof)
            assert _archive_value(asyncio.run(root.build_result(record))) == dict(credit=0, pending_handles=[])
            operations = list(store.db.execute("SELECT * FROM tool_operations WHERE name=? ORDER BY rowid", (TOOL,)))
            assert len(operations) == 2 and [json.loads(row["arguments"])["mode"] for row in operations] == ["native", "saved"]
            publications = [read_published_restriction_result(store, json.loads(row["result"])["result"]["source_ref"],
                scope=proof["scope"]) for row in operations]
            original, saved = publications
            assert saved["native"] == original["native"] and saved["mapping"] == original["mapping"]
            assert saved["body"]["input_source_ref"] == original["body"]["input_source_ref"]
            assert saved["body"]["prior_result_source_ref"] == original["source"]["id"]
            for role in ("native", "catalog", "mapping"):
                assert saved["body"]["files"][role] == original["body"]["files"][role]
            mapping = original["mapping"]
            assert mapping["population"] == dict(selected_enzyme_count=1, attempted_enzyme_count=1,
                returned_enzyme_count=1, complete_empty_enzyme_count=0, recognition_match_count=1)
            row, = mapping["enzyme_rows"]
            assert row["name"] == "EcoRI" and row["native_search_positions_1based"] == [6]
            assert row["returned_position_count"] == row["recognition_match_count"] == 1
            assert row["position_meaning"] == "first_base_after_cut_1based"
            position, = row["positions"]
            assert position["watson_boundary_0based"] == 5 and position["crick_boundary_0based"] == 9
            assert position["recognition_association"] == "not_recorded" and position["recognition_event_ordinal"] is None
            event, = row["recognition_events"]
            assert event["native_start_1based"] == 5 and event["unwrapped_span_0based"] == [4, 10]
            assert len(proof["workers"]) == 2 and [w["reservation"]["work_mode"] for w in proof["workers"]] == ["native", "saved"]
            for captured in proof["workers"]:
                execution = captured["execution_proof"]
                reservation = captured["reservation"]
                handle = captured["native_handle"]
                assert execution["returncode"] == 0 and execution["original_view"]["terminal"] is True
                assert execution["original_view"]["quiescent"] is True
                assert execution["original_view"]["metadata"]["policy"] == POLICY
                assert handle["command"] == [reservation["software"]["python"]["path"], "-B", "-m",
                    "gene_annotation_episode.restriction_mapping_worker", reservation["request_file"]["path"],
                    reservation["output_directory"]]
                assert handle["cwd"] == reservation["directory"]
                assert handle["metadata"]["policy"] == POLICY
                assert captured["files"]["manifest.json"]["value"]["mode"] == captured["reservation"]["work_mode"]
            assert len({captured["native_handle"]["unit"] for captured in proof["workers"]}) == 2
            proof.update(publications=publications, phase="actual_native_and_saved_values_verified")
            _checkpoint(store, output, proof)
            contexts = EpisodeReturnRecords(store, flow.run_id, failure_prefix="restriction_episode_")
            episodes = list(store.db.execute("SELECT episode_id FROM runtime_episodes ORDER BY json_array_length(path)"))
            assert len(episodes) == 2
            parent, science = [contexts.context(row[0]) for row in episodes]
            admission = contexts.source_admission_before(science, original["source"]["id"], 1)
            assert admission["receipt"]["receipt_kind"] == "own_action" and admission["receipt"]["source_index"] == 0
            with pytest.raises(ValueError, match="result_not_received"):
                contexts.source_admission_before(science, original["source"]["id"], 0)
            selected = dict(policy="all_own_completed_results", sequence_ref=None)
            action_records = RestrictionMappingActionRecords(store, flow.run_id)
            own = action_records.own_action_results(science, selection=selected, after_decision_index=None, limit=64)
            assert len(own["records"]) == 2 and own["next_after_decision_index"] is None
            receipt_index = admission["receipt"]["receipt_index"]
            assert action_records.own_enzyme_reference(science, "EcoRI", before_decision_index=0,
                through_receipt_index=receipt_index) is False
            assert action_records.own_enzyme_reference(science, "EcoRI", before_decision_index=1,
                through_receipt_index=receipt_index) is True
            frozen = store.db.execute("SELECT facts,form FROM runtime_forms WHERE episode_id=?", (science.episode_id,)).fetchone()
            groups = json.loads(frozen["facts"])[FACT]
            assert len(groups) == 2 and [group["work_mode"] for group in groups] == ["native", "saved"]
            assert json.loads(frozen["form"]) == dict(restriction_evidence=groups)
            assert _archive_value(record)["units"][0]["child_result"]["form"] == dict(restriction_evidence=groups)
            attempt = store.db.execute("SELECT failure,form FROM runtime_report_attempts WHERE parent_episode_id=?",
                (parent.episode_id,)).fetchone()
            assert attempt["failure"] is None and json.loads(attempt["form"]) == dict(restriction_evidence=groups)
            private = {file["artifact_ref"] for item in publications for file in item["body"]["files"].values() if file is not None}
            private.update(ref for item in publications for ref in (item["source"]["artifact_ref"],
                item["body"]["reservation_artifact_ref"], item["body"]["execution_proof_artifact_ref"]))
            private.add(original["input_source"]["artifact_ref"])
            private.update(captured["execution_proof"][field] for captured in proof["workers"]
                for field in ("handle_artifact_ref", "control_request_artifact_ref", "status_artifact_ref",
                    "native_receipt_artifact_ref") if captured["execution_proof"][field] is not None)
            for context in (parent, science):
                known = set(flow.receipts.known(context.episode_id))
                assert {group["source_ref"] for group in groups} <= known and private.isdisjoint(known)
            assert len(proof["cache"]) == 2 and len(proof["calls"]) == 3
            proof.update(groups=groups, saved_source_admission=admission, phase="typed_parent_verified_before_closed_replay")
            _checkpoint(store, output, proof)
            proof["closed_replay"] = _closed_replay(store, directory, proof, groups, monkeypatch)
            proof.update(passed=True, phase="verified", selected_native_workers=1, selected_saved_reader_workers=1,
                typed_parent_return_verified=True, provider_cleanup=provider.cleanup)
        except BaseException as error:
            proof["verification_failure"] = dict(exception_type=type(error).__name__, message=str(error))
            raise
        finally:
            _checkpoint(store, output, proof)


RETAINED570_GATE = "HMMER_NATIVE_ORACLE_RESTRICTION_RETAINED570_JSON"
RETAINED570_INVENTORY = "e2bbbfa4fbcaad9d7e3800c7a6654705f90b8528610d6956bf8dc7710ddec40c"
RETAINED570_PROOF = "5b1eda42fe51abeef276d7e2346801b27d7b617dfd4974d051b51cb865789528"
RETAINED570_DB = "65cb45a86f99ceb978033a9f5717f0428931d0530f6efd4a72b52f4cd1f3ee61"
RETAINED570_EVIDENCE = {
    "receipt.json": ("c9622a2282fdbe2921d30bce18cbbfd1fdc0a3545f3089f83185efa823a9477b", 1652),
    "junit.xml": ("a48a056226286d0640589c1d84f5edf1e479f4a9a6bcd1809c61db68b46c8fea", 831),
    "execution_audit.json": ("db7732f183ccd7dd634d27bb0f3ad0221ab88d75883c8417aee35b429f19b20b", 156),
    "selected_tests.json": ("2d21dce3220b4d201461afbad8d2bc3fe03b3e8e78fbe794cddcfa735728580c", 117),
    "selected_test_environment.json": ("d5c001194681c6861c40e4a4f062dbc0ba15344aef14badf64893c504f25caf4", 70),
    "source_snapshot/tests/test_restriction_ordinary_workflow.py": (
        "5103fd771fd8782a730dda203cdeca38ec15ce6934e535a3da8de6716ffbf19e", 27966),
}


def _retained570_inventory(directory):
    """Authenticate this selected regular-file case, including original modes."""
    result = {}
    for path in sorted(directory.rglob("*")):
        assert not path.is_symlink()
        name, mode = str(path.relative_to(directory)), stat.S_IMODE(path.lstat().st_mode)
        if path.is_file():
            raw = path.read_bytes()
            result[name] = dict(kind="file", mode=mode, sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        else:
            assert path.is_dir()
            result[name] = dict(kind="directory", mode=mode)
    return result


def _retained570_inventory_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _retained570_sqlite(database):
    """Read only a new owned copy; callers never pass the original database."""
    import sqlite3

    assert not Path(str(database) + "-wal").exists() and not Path(str(database) + "-shm").exists()
    connection = sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        names = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {name: sorted((tuple(row) for row in connection.execute(
            'SELECT * FROM "' + name.replace('"', '""') + '"')), key=repr) for name in names}
    finally:
        connection.close()


def _retained570_input(selected, tmp_path):
    """Pin the actual failed verifier, then copy its closed Store and libraries."""
    import shutil
    import xml.etree.ElementTree as ET

    attempt = require_bounded_runtime()
    gate = json.loads(selected)
    assert type(gate) is dict and set(gate) == {"directory", "original_directory", "inventory_sha256"}
    assert gate["inventory_sha256"] == RETAINED570_INVENTORY
    original = Path(gate["original_directory"]).resolve(strict=True)
    supplied = Path(gate["directory"]).resolve(strict=True)
    assert supplied.is_relative_to(attempt / "source_snapshot") and supplied != original
    before = _retained570_inventory(original)
    assert _retained570_inventory_sha(before) == RETAINED570_INVENTORY
    assert len(before) == 171 and sum(row["kind"] == "file" for row in before.values()) == 134
    assert before["store/state.sqlite3"] == dict(kind="file", mode=0o644, sha256=RETAINED570_DB, size_bytes=11616256)
    assert "store/state.sqlite3-wal" not in before and "store/state.sqlite3-shm" not in before
    frozen = deepcopy(before)
    for row in frozen.values():
        row["mode"] = 0o555 if row["kind"] == "directory" or row["mode"] & 0o111 else 0o444
    assert _retained570_inventory(supplied) == frozen
    snapshot_run = supplied.parents[1]
    for name, (digest, size) in RETAINED570_EVIDENCE.items():
        for root in (snapshot_run, original.parents[1]):
            raw = (root / name).read_bytes()
            assert len(raw) == size and hashlib.sha256(raw).hexdigest() == digest
    receipt = json.loads((snapshot_run / "receipt.json").read_bytes())
    assert receipt["returncode"] == 1 and receipt["terminal"] is True and receipt["quiescent"] is True
    assert all(receipt[name] for name in ("source_unchanged", "dependency_unchanged", "stdlib_unchanged",
        "binary_unchanged", "selected_stdlib_source_unchanged"))
    failure = ET.fromstring((snapshot_run / "junit.xml").read_bytes()).find("testsuite")
    assert failure.attrib["tests"] == failure.attrib["failures"] == "1"
    assert failure.attrib["errors"] == failure.attrib["skipped"] == "0"
    assert failure.find("testcase/failure").attrib["message"] == "AttributeError: 'EpisodeRecord' object has no attribute 'units'"
    raw = (supplied / "RESTRICTION_ORDINARY_WORKFLOW.json").read_bytes()
    assert len(raw) == 18467948 and hashlib.sha256(raw).hexdigest() == RETAINED570_PROOF
    proof = json.loads(raw)
    assert proof["passed"] is False and proof["whole_episode_completed"] is True
    assert proof["phase"] == "actual_native_and_saved_values_verified"
    assert proof["verification_failure"] == dict(exception_type="AttributeError",
        message="'EpisodeRecord' object has no attribute 'units'")
    assert [item["mode"] for item in proof["cache"]] == ["native", "saved"]
    assert all(item["same_original_invocation"] and item["all_rows_and_artifacts_unchanged"]
        and all(item[name] == 0 for name in ("new_workers", "new_native_searches", "new_reader_calculations",
            "new_publications")) for item in proof["cache"])
    assert [item["reservation"]["work_mode"] for item in proof["workers"]] == ["native", "saved"]
    assert all(Path(item["reservation"]["directory"]).parents[2] == original for item in proof["workers"])
    assert proof["factory"]["resources"]["ordinary"]["workspace"] == str(original / "workspace")
    owned = tmp_path / "retained570"
    owned.mkdir()
    for name in ("store", "run"):
        shutil.copytree(supplied / name, owned / name, copy_function=shutil.copy2)
    # Only new owned copies regain the recorded modes. The source snapshot and
    # original runtime remain untouched, including every serialized old path.
    for name, row in sorted(before.items(), key=lambda item: len(Path(item[0]).parts)):
        if Path(name).parts[0] in {"store", "run"}:
            (owned / name).chmod(row["mode"])
    expected = {name: row for name, row in before.items() if Path(name).parts[0] in {"store", "run"}}
    assert _retained570_inventory(owned) == expected
    expected_tables = {name: [tuple(row) for row in rows] for name, rows in proof["tables"].items()}
    assert _retained570_sqlite(owned / "store/state.sqlite3") == expected_tables
    assert _retained570_inventory(original) == before and _retained570_inventory(supplied) == frozen
    return proof, owned, original, before, supplied, frozen


def test_retained570_typed_parent_and_current_closed_replay_without_new_work(tmp_path, monkeypatch):
    selected = os.environ.get(RETAINED570_GATE)
    if selected is None:
        pytest.skip("requires the exact closed570 Store/run and failed verifier proof")
    import builtins
    import sqlite3
    from dataclasses import replace
    from urllib.parse import unquote
    from gene_annotation_episode import restriction_mapping_publication as publication
    from gene_annotation_episode.restriction_mapping_references import RestrictionMappingReferences
    from gene_annotation_episode.restriction_mapping_returns import validate_frozen_restriction_return

    original_proof, owned, original, before, supplied, frozen_input = _retained570_input(selected, tmp_path)
    output = tmp_path / "RESTRICTION_RETAINED570_POSTCHECK.json"
    result = dict(version="restriction_retained570_postcheck_v1", passed=False,
        original_proof_sha256=RETAINED570_PROOF, original_case_inventory_sha256=RETAINED570_INVENTORY,
        original_failure_preserved=True, original570_caches_authenticated=deepcopy(original_proof["cache"]),
        cache_reinvoked=False, new_workers=0, new_native_searches=0, new_reader_calculations=0,
        new_publications=0, new_model_decisions=0, original_application_accesses=[])
    expected = {name: [tuple(row) for row in rows] for name, rows in original_proof["tables"].items()}
    owned_before = _retained570_inventory(owned)
    old_run = original.parents[1]
    real_open, real_path_open, real_os_open, real_connect = builtins.open, Path.open, os.open, sqlite3.connect

    def protect_original(path, port):
        if isinstance(path, (str, bytes, os.PathLike)):
            text = os.fsdecode(path)
            if text.startswith("file:"):
                text = unquote(text[5:].split("?", 1)[0])
            if Path(text).absolute().is_relative_to(old_run):
                result["original_application_accesses"].append(dict(port=port, path=text))
                raise AssertionError("retained application attempted original570 body/database access or mutation")

    def open_file(path, *args, **kwargs):
        protect_original(path, "builtins.open")
        return real_open(path, *args, **kwargs)

    def open_path(path, *args, **kwargs):
        protect_original(path, "Path.open")
        return real_path_open(path, *args, **kwargs)

    def open_descriptor(path, *args, **kwargs):
        protect_original(path, "os.open")
        return real_os_open(path, *args, **kwargs)

    def connect(database, *args, **kwargs):
        protect_original(database, "sqlite3.connect")
        return real_connect(database, *args, **kwargs)

    def mutation_guard(name, function, count):
        def mutation(*args, **kwargs):
            for path in args[:count]:
                protect_original(path, "os." + name)
            return function(*args, **kwargs)
        return mutation

    try:
        with monkeypatch.context() as guarded:
            guarded.setattr(builtins, "open", open_file)
            guarded.setattr(Path, "open", open_path)
            guarded.setattr(os, "open", open_descriptor)
            guarded.setattr(sqlite3, "connect", connect)
            for name, count in (("mkdir", 1), ("unlink", 1), ("remove", 1), ("rmdir", 1),
                    ("chmod", 1), ("rename", 2), ("replace", 2), ("link", 2), ("symlink", 2)):
                guarded.setattr(os, name, mutation_guard(name, getattr(os, name), count))
            for module, names in ((native, ("run_restriction_mapping",)),
                    (readers, ("read_restriction_mapping",)),
                    (worker, ("run_restriction_worker", "read_restriction_mapping")),
                    (adapter, ("prepare_restriction_work", "publish_restriction_work", "replay_restriction_work", "_software")),
                    (publication, ("read_published_restriction_result", "read_restriction_input", "publish_restriction_result",
                        "retain_restriction_input")),
                    (RestrictionMappingJobs, ("reserve", "run_async", "publication_state")),
                    (native_lifecycle, ("prepare_job", "start_prepared", "resume_start", "wait_job", "status", "collect",
                        "cancel", "release"))):
                for name in names:
                    guarded.setattr(module, name, _forbidden)
            guarded.setattr(PublicClients, "_http", _forbidden)
            guarded.setattr(ToolRegistry, "execute_async", _forbidden)
            guarded.setattr(Store, "get_artifact", _forbidden)
            guarded.setattr(Store, "artifact", _forbidden)
            guarded.setattr(Store, "put", _forbidden)
            guarded.setattr(RestrictionMappingActionRecords, "own_enzyme_reference", _forbidden)
            with Store(owned / "store") as store:
                assert _tables(store) == expected
                episodes = list(store.db.execute("SELECT * FROM runtime_episodes ORDER BY json_array_length(path)"))
                assert len(episodes) == 2 and all(row["state"] == "yielded" for row in episodes)
                parent_record, science_record = [_archive(dict(row), owned / "run") for row in episodes]
                parent_id, science_id = [row["episode_id"] for row in episodes]
                frozen = store.db.execute("SELECT facts,form FROM runtime_forms WHERE episode_id=?", (science_id,)).fetchone()
                facts, form = json.loads(frozen["facts"]), json.loads(frozen["form"])
                groups = facts[FACT]
                assert form == dict(restriction_evidence=groups)
                assert parent_record["units"][0]["child_result"]["form"] == form
                validate_frozen_restriction_return(form, _form(), facts)
                attempt = store.db.execute("SELECT failure,form FROM runtime_report_attempts WHERE parent_episode_id=?",
                    (parent_id,)).fetchone()
                assert attempt["failure"] is None and json.loads(attempt["form"]) == form
                assert science_record["request"]["report_contract"]["measurements"]["schema"] == _form()
                references = RestrictionMappingReferences(store, original_proof["run_id"])
                child_context, parent_context = references.context(science_id), references.context(parent_id)
                assert references.frozen_reference(child_context, "EcoRI", "restriction_enzyme") is True
                absent = ["ecori", "BamHI", "", None, False, 0, {}, []]
                assert all(references.frozen_reference(child_context, name, "restriction_enzyme") is False
                    for name in absent)
                assert all(references.frozen_reference(child_context, "EcoRI", namespace) is None
                    for namespace in (None, "source", "restriction_enzyme_catalog"))
                assert references.frozen_reference(parent_context, "EcoRI", "restriction_enzyme") is False
                changed_scope = plain(child_context.scope)
                changed_scope["subject_refs"] = []
                assert changed_scope != plain(child_context.scope)
                with pytest.raises(ValueError, match="restriction_mapping_reference_context_conflict"):
                    references.frozen_reference(replace(child_context, scope=changed_scope), "EcoRI", "restriction_enzyme")
                assert _tables(store) == expected
                result["frozen_name_controls"] = dict(exact_EcoRI=True, absent_names=absent,
                    other_namespaces_unhandled=True, parent_role_denied=True, changed_scope_rejected=True,
                    live_catalog_fallback_forbidden=True, all_rows_and_receipts_unchanged=True)
                assert [group["work_mode"] for group in groups] == ["native", "saved"]
                assert len(original_proof["calls"]) == 3
                assert [call["grain"] for call in original_proof["calls"]] == ["annotation", "scientific_process", "scientific_process"]
                assert all(call["context"]["goal"]["objective"] == QUESTION for call in original_proof["calls"])
                publications = original_proof["publications"]
                assert [group["source_ref"] for group in groups] == [item["source"]["id"] for item in publications]
                assert publications[0]["native"] == publications[1]["native"]
                assert publications[0]["mapping"] == publications[1]["mapping"]
                private = {file["artifact_ref"] for item in publications for file in item["body"]["files"].values() if file is not None}
                private.update(ref for item in publications for ref in (item["source"]["artifact_ref"],
                    item["body"]["reservation_artifact_ref"], item["body"]["execution_proof_artifact_ref"]))
                private.add(publications[0]["input_source"]["artifact_ref"])
                private.update(item["execution_proof"][name] for item in original_proof["workers"]
                    for name in ("handle_artifact_ref", "control_request_artifact_ref", "status_artifact_ref",
                        "native_receipt_artifact_ref") if item["execution_proof"][name] is not None)
                for episode_id in (parent_id, science_id):
                    known = {row[0] for row in store.db.execute("SELECT record_ref FROM runtime_record_receipts WHERE episode_id=?",
                        (episode_id,))}
                    assert {group["source_ref"] for group in groups} <= known and private.isdisjoint(known)
                result.update(groups=groups, original_factory=original_proof["factory"],
                    original_scientific_binding=original_proof["scientific_binding"], phase="frozen_parent_and_private_receipts_verified")
                _checkpoint(store, output, result)
                result["closed_replay"] = _closed_replay(store, owned / "run", original_proof, groups, monkeypatch)
                assert QUESTION in result["closed_replay"]["receiver"]["wire"]
                assert _tables(store) == expected
                result.update(phase="closed_replay_verified", all_original_rows_preserved_on_copy=True,
                    typed_parent_form_verified=True, private_receipts_verified=True)
                _checkpoint(store, output, result)
            assert _retained570_inventory(owned) == owned_before
            result.update(passed=True, phase="verified", owned_store_and_run_inventory_unchanged_after_close=True)
    except BaseException as error:
        result["verification_failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        assert _retained570_inventory(original) == before
        assert _retained570_inventory(supplied) == frozen_input
        result["original_and_snapshot_inventories_unchanged"] = True
        output.write_text(json.dumps(result, allow_nan=False) + "\n")
