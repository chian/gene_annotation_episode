"""Opt-in current disorder API action, supplied-data return and closed replay.

This submits one selected POST at most. A transport failure stays a failure;
controlled supplied-data values never authenticate scientific service execution.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

from method_loop.episode import EpisodeView
import pytest

from gene_annotation_episode import native_lifecycle
from gene_annotation_episode import protein_disorder_measurements as core
from gene_annotation_episode import protein_disorder_result_contracts as contracts
from gene_annotation_episode import protein_disorder_tools as adapter
from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.communication import plain, validate_form
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.domain import canonical, obj
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import DecisionSource, Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_homer_motif_saved_workflow import _archive, _archive_value, _encode
from test_protein_disorder_result_contracts import request, selection
from test_vcf_result_workflow import _tables, _zero


PUBLICATION = Path(__file__).resolve().parents[1] / "research/slotted_process_library/publications/2026-10-24-001"
SEQUENCE = "MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG"
QUESTION = ("For the explicitly supplied 76-character protein string at threshold 0.5, return retained "
    "disorder response values and their original input, parsed-row, finite-score and coverage qualifications. "
    "Compare a saved calculation of that same supplied Sheet with literal retained readings; preserve "
    "unavailable responses and distinguish predictor outputs from evidence of service execution.")
POLICY = dict(memory_bytes=20 * 1024 ** 3, scratch_bytes=4 * 1024 ** 3)
GATE = "HMMER_NATIVE_ORACLE_DISORDER_EPISODE"


class OriginalDisorderPrefixObserved(RuntimeError):
    """Stop a failed original action prefix before another scripted choice."""


def _forbidden(*args, **kwargs):
    raise AssertionError("retained disorder verification attempted new work")


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, allow_nan=False) + "\n")


def _checkpoint(store, proof, output):
    proof["tables"] = _tables(store)
    proof["counts"] = {name: len(rows) for name, rows in proof["tables"].items()
        if name.startswith("runtime_") or name == "tool_operations"}
    _write(output, proof)


def _form():
    return obj(dict(outcomes=contracts.ordinary_disorder_fact_sources()[contracts.FACT_SOURCE]["report_schema"]))


def _selected_rows():
    return selection(request("summary", ["source_parsed_row_count", "descriptive_mean_score",
        "descriptive_mean_denominator_rows", "thresholded_row_count", "parsed_row_denominator",
        "disordered_percentage", "unique_input_coverage", "region_count"]),
        request("residue", ["score_token", "score_kind", "score_value", "source_intervals"], row_ordinal=0),
        request("region", ["start_1based", "end_1based", "length_residues"], region_ordinal=0))


def _controller(path, initial):
    horizon = 1 if path[-1][0] == "annotation" else 4
    def estimate(history, parameters, contexts):
        return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= horizon else 1),
            parameters, dict(engineering_fixture="four_explicit_disorder_actions"))
    return YieldController(str(path), initial, 0, estimate_with_context=estimate)


def _assemble(store, directory, proof, provider):
    factory = ExecutionServiceFactory.from_record(proof["factory"])
    clients = PublicClients(ncbi_email=None, timeout=proof["transport_timeout_seconds"])
    registry = ToolRegistry(store, clients=clients, job_limits=deepcopy(POLICY))
    application = factory(store, run_id=proof["run_id"], directory=directory, tool_registry=registry)
    assert registry.catalog()[contracts.TOOL] == proof["selected_tool_contract"]
    workflow = Workflow(store, registry, provider, directory, proof["run_id"], _controller, _zero,
        project_child_credit=_zero, episode_binding_descriptors=[proof["scientific_binding"], *application.episode_binding_descriptors],
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider,
        episode_record_receipts=True, initial_known_record_refs=[])
    return workflow, registry


def _operations(store):
    return [dict(row) for row in store.db.execute("SELECT * FROM tool_operations WHERE name=? ORDER BY rowid", (contracts.TOOL,))]


class _Choices:
    def __init__(self, store, library, proof, output):
        self.store, self.library, self.proof, self.output = store, library, proof, output
        self.connection = object.__new__(_SessionConnection)
        self.connection.scientific_prompt_states = {}
        self.cleanup = []

    async def complete(self, episode_id, role, instructions, context, schema):
        context = plain(context)
        grain = json.loads(self.store.db.execute("SELECT path FROM runtime_episodes WHERE episode_id=?", (episode_id,)).fetchone()[0])[-1][0]
        turn = self.store.db.execute("SELECT count(*)+1 FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND response IS NOT NULL",
            (self.proof["run_id"], episode_id)).fetchone()[0]
        previous = [json.loads(row["result"]) for row in _operations(self.store)]
        if context.get("feedback") or any(item["result"] is None for item in previous):
            self.proof.update(phase="original_action_prefix_observed", feedback=deepcopy(context.get("feedback")),
                whole_episode_completed=False, complete_transport_and_76_parsed_rows_observed=False)
            _checkpoint(self.store, self.proof, self.output)
            raise OriginalDisorderPrefixObserved("original disorder action cannot continue without another submission")
        wire, wire_instructions = self.connection._presentation(episode_id, role, instructions, context)
        self.proof["calls"].append(dict(episode_id=episode_id, grain=grain, turn=turn, context=deepcopy(context),
            wire=wire, wire_instructions=plain(wire_instructions)))
        assert role == "REASONING" and context["goal"]["objective"] == QUESTION
        if grain == "annotation":
            assert turn == 1
            chosen = dict(kind="episode_child", role="scientific_process", goal=QUESTION, scope=deepcopy(self.proof["scope"]),
                purpose="Return the literal controlled disorder groups and their distinct population qualifications.",
                schema_json=json.dumps(_form()), initial_report_json="{}", assignment=dict(
                    selection=dict(version="scientific_process_selection_v3", evidence_axis=self.library.reference("A101"),
                        thought_pattern=self.library.reference("P01"),
                        child_tool_info=[dict(name=contracts.TOOL, resources=self.proof["selected_tool_contract"]["resources"])]),
                    evidence_refs=[], constraints={}, context=dict(protein_sequence=SEQUENCE, threshold=.5)))
        else:
            assert grain == "scientific_process" and 1 <= turn <= 4
            assert wire.startswith("TASK\n") and "\n\nSTEERING\n" in wire and QUESTION in wire
            assert context["requested_form"] == _form()
            assert "Selected tool: " + contracts.TOOL + " (api)" in wire
            if turn == 1:
                arguments = dict(mode="predict", protein_sequence=SEQUENCE, threshold=.5, max_bytes=1048576, selection=selection())
            elif turn == 2:
                arguments = dict(mode="read_stored", result_ref=previous[0]["result"]["source_ref"], selection=selection())
            elif turn == 3:
                assert previous[1]["result"] == previous[0]["result"]
                arguments = dict(mode="calculate_saved", result_ref=previous[0]["result"]["source_ref"], selection=selection())
            else:
                arguments = dict(mode="read_stored", result_ref=previous[2]["result"]["source_ref"], selection=_selected_rows())
            if previous:
                assert context["last_local_outcome"]["result"] == previous[-1]["result"]
                assert "parsed_row_denominator" in wire and "scientific_service_execution_verified" in wire
                assert previous[-1]["result"]["source_ref"] in wire
            chosen = dict(kind="tool", tool=contracts.TOOL, arguments=arguments)
        answer = _encode(dict(selection=chosen, report_update={}), schema)
        self.proof["calls"][-1]["response"] = deepcopy(answer)
        _checkpoint(self.store, self.proof, self.output)
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


def _closed_receiver(store, directory, proof, groups, monkeypatch):
    before = _tables(store)
    episodes = list(store.db.execute("SELECT * FROM runtime_episodes ORDER BY json_array_length(path)"))
    parent_archive, child_archive = [_archive(dict(row), directory) for row in episodes]
    provider = _NoDecisions()
    public_packets = {store.get(group["source_ref"])["artifact_ref"] for group in groups}
    actual_get, receiver = Store.get_artifact, {}
    with monkeypatch.context() as guarded:
        for module, names in ((native_lifecycle, ("prepare_job", "start_prepared", "resume_start", "wait_job", "status", "collect", "cancel", "release")),
                (core, ("build_disorder_sheet", "calculate_disorder_components")),
                (adapter, ("run_disorder_tool_request", "_perform_post", "_dispatch"))):
            for name in names:
                guarded.setattr(module, name, _forbidden)
        guarded.setattr(ToolRegistry, "execute_async", _forbidden)
        guarded.setattr(ToolRegistry, "_sequence_worker_async", _forbidden)
        guarded.setattr(PublicClients, "_http", _forbidden)
        guarded.setattr(Store, "get_artifact", _forbidden)
        workflow, registry = _assemble(store, directory, proof, provider)
        root = workflow.build("annotation", "root", QUESTION, proof["scope"])
        record = asyncio.run(root.run_async(workflow.context))
        assert _archive_value(record) == parent_archive
        assert _archive_value(asyncio.run(root.build_result(record))) == dict(credit=0, pending_handles=[])
        # Build the actual existing child commission through its original action.
        commission = workflow.journal.row("runtime_actions", root.source.episode_id, 0)
        closed = workflow.selected(root.source, json.loads(commission["action"]), 0)
        assert _archive_value(closed.record) == child_archive
        assert plain(closed.result.as_record()) == dict(form=dict(outcomes=groups))
        scope = workflow.context.enter(root.grain, root.key)
        try:
            view = EpisodeView(grain=root.grain, key=root.key, path=scope, units_consumed=record.units_consumed,
                updates=tuple(workflow.context._child_updates.get(scope, ())), controller_state=record.controller_state,
                episode_ref=record.episode_ref, request=record.request)
            def public_only(current, reference):
                assert reference in public_packets
                return actual_get(current, reference)
            class ReceiverCaptured(BaseException):
                pass
            async def capture(source, context, schema):
                assert context["child_reports"] == [dict(outcomes=groups)]
                connection = object.__new__(_SessionConnection)
                connection.scientific_prompt_states = {}
                with guarded.context() as no_bytes:
                    no_bytes.setattr(Store, "get_artifact", _forbidden)
                    wire, instructions = connection._presentation(source.episode_id, "REASONING", source.instructions(context),
                        state_frame(plain(context)))
                assert "dimensionless_predictor_score" in wire and "scientific_service_execution_verified" in wire
                assert all(group["source_ref"] in wire for group in groups)
                receiver.update(context=plain(context), wire=wire, instructions=plain(instructions),
                    historical_post_return_decision_claimed=False, current_receiver_reconstruction=True)
                raise ReceiverCaptured()
            guarded.setattr(Store, "get_artifact", public_only)
            guarded.setattr(DecisionSource, "call", capture)
            count = root.source.calls
            with pytest.raises(ReceiverCaptured):
                asyncio.run(root.source.next(view))
            assert root.source.calls == count
        finally:
            workflow.context.leave(scope)
    assert _tables(store) == before
    return dict(all_rows_unchanged=True, new_provider_decisions=0, provider_cleanup_callbacks=provider.cleanup,
        new_tool_actions=0, new_workers=0, new_posts=0, new_calculations=0, receiver=receiver)


def test_genuine_current_disorder_post_saved_values_typed_return_and_closed_replay(tmp_path, monkeypatch):
    selected = os.environ.get(GATE)
    if selected is None:
        pytest.skip("requires an explicit JSON opt-in for one genuine IUPred2A POST")
    gate = json.loads(selected)
    assert type(gate) is dict and set(gate) == {"enabled", "timeout_seconds"} and gate["enabled"] is True
    assert type(gate["timeout_seconds"]) is int and gate["timeout_seconds"] > 0
    assert len(SEQUENCE) == 76
    proof = dict(passed=False, phase="preparing", run_id="current-ordinary-disorder", calls=[], workers=[], cache=[],
        transport_timeout_seconds=gate["timeout_seconds"], whole_episode_completed=False,
        actual_transport_success=False, complete_transport_and_76_parsed_rows_observed=False,
        scientific_service_execution_verified=False, live_attempt_repeated=False)
    output = tmp_path / "DISORDER_EPISODE.json"
    try:
        with Store(tmp_path / "store") as store:
            store.create_problem(raw_sequence=SEQUENCE, molecule="protein")
            directory = tmp_path / "run"
            workspace = tmp_path / "workspace"; workspace.mkdir()
            factory = ExecutionServiceFactory({"ordinary": dict(kind="local", workspace=str(workspace), policy=deepcopy(POLICY))}, {}, 2, .25, .5)
            catalog_registry = ToolRegistry(store, clients=PublicClients(ncbi_email=None, timeout=gate["timeout_seconds"]), job_limits=deepcopy(POLICY))
            factory.configure_tool_registry(catalog_registry)
            proof.update(factory=factory.as_record(), scope=store.validate_scope(),
                selected_tool_contract=deepcopy(catalog_registry.catalog()[contracts.TOOL]))
            proof["scientific_binding"] = prepare_scientific_binding(run_directory=directory, source_directory=PUBLICATION,
                tool_catalog=catalog_registry.catalog(), child_roles=["scientific_process"])
            provider = _Choices(store, ScientificProcessLibrary(directory / "scientific-process-library"), proof, output)
            flow, registry = _assemble(store, directory, proof, provider)
            native_files, actual_get = set(), Store.get_artifact
            def protected(current, reference):
                assert reference not in native_files
                return actual_get(current, reference)
            monkeypatch.setattr(Store, "get_artifact", protected)
            monkeypatch.setattr(core, "build_disorder_sheet", _forbidden)
            monkeypatch.setattr(core, "calculate_disorder_components", _forbidden)
            # Host HTTP is forbidden: only the independently selected worker may POST.
            monkeypatch.setattr(PublicClients, "_http", _forbidden)
            actual_worker = registry._sequence_worker_async
            async def worker(operation, arguments, *, directory, owned_directory):
                assert operation == adapter.WORKER_OPERATION and directory == owned_directory
                work = await actual_worker(operation, arguments, directory=directory, owned_directory=owned_directory)
                evidence = dict(request=deepcopy(arguments["request"]), metadata=deepcopy(work.metadata), files={})
                for name in ("execution-selection.json", "worker-request.json", "native-handle.json", "worker-result.json", "post-started.json", "transport-seal.json"):
                    path = directory / name
                    if path.is_file():
                        raw = path.read_bytes()
                        evidence["files"][name] = dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw), value=json.loads(raw))
                path = directory / "native-response.bin"
                if path.is_file():
                    raw = path.read_bytes()
                    evidence["files"][path.name] = dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
                proof["workers"].append(evidence)
                proof["phase"] = "original_worker_returned_before_publication_checks"
                _checkpoint(store, proof, output)
                # Seal evidence precedes these checks, so a verifier failure
                # cannot require another original POST. Block native capture
                # artifacts before the first stored read or saved calculation.
                if arguments["request"]["post"] is not None and "worker-result.json" in evidence["files"]:
                    transport = evidence["files"]["worker-result.json"]["value"]["transport"]
                    native_files.add("artifact_" + hashlib.sha256(canonical(transport).encode()).hexdigest())
                    if transport["response_hex"] is not None:
                        native_files.add("artifact_" + hashlib.sha256(bytes.fromhex(transport["response_hex"])).hexdigest())
                return work
            monkeypatch.setattr(registry, "_sequence_worker_async", worker)
            actual_execute = registry.execute_async
            async def execute(name, arguments, **kwargs):
                outcome = await actual_execute(name, arguments, **kwargs)
                if name == contracts.TOOL and arguments["mode"] == "read_stored" and not proof["cache"] and outcome["result"] is not None:
                    # Workflow.execute still owns the authentic current action
                    # invocation here. Reuse its actual ToolOp key; no new
                    # decision, action, receipt or authority is constructed.
                    before = _tables(store)
                    packet = store.get(outcome["result"]["source_ref"])["artifact_ref"]
                    reads = []
                    def public_only(current, reference):
                        assert reference == packet
                        reads.append(reference)
                        return actual_get(current, reference)
                    with monkeypatch.context() as cached_guard:
                        cached_guard.setattr(registry, "_sequence_worker_async", _forbidden)
                        cached_guard.setattr(adapter, "_perform_post", _forbidden)
                        cached_guard.setattr(adapter, "_dispatch", _forbidden)
                        cached_guard.setattr(adapter, "_retain_protein_disorder_publication", _forbidden)
                        cached_guard.setattr(Store, "get_artifact", public_only)
                        cached_guard.setattr(Store, "artifact", _forbidden)
                        cached_guard.setattr(Store, "put", _forbidden)
                        cached = await actual_execute(name, deepcopy(arguments), **kwargs)
                    assert cached == outcome and _tables(store) == before
                    proof["cache"].append(dict(operation_key=kwargs["operation_key"], same_original_invocation=True,
                        all_rows_unchanged=True, new_sources=0, new_workers=0, new_posts=0,
                        new_calculations=0, allowed_public_packet=packet, public_packet_reads=reads))
                    _checkpoint(store, proof, output)
                return outcome
            monkeypatch.setattr(registry, "execute_async", execute)
            root = flow.build("annotation", "root", QUESTION, proof["scope"])
            try:
                record = asyncio.run(root.run_async(flow.context))
            except OriginalDisorderPrefixObserved:
                proof["correct_original_prefix_preserved"] = True
                _checkpoint(store, proof, output)
                pytest.skip("original API action produced no usable public result; no retry or completion claim")
            proof.update(phase="workflow_returned_before_postchecks", whole_episode_completed=True)
            _checkpoint(store, proof, output)
            assert _archive_value(asyncio.run(root.build_result(record))) == dict(credit=0, pending_handles=[])
            outcomes = [json.loads(row["result"]) for row in _operations(store)]
            assert len(outcomes) == 4
            original, literal, derived, reread = outcomes
            assert original["result"] == literal["result"] and literal["changed_record_refs"] == []
            assert derived["result"]["source_ref"] != original["result"]["source_ref"]
            assert reread["result"]["source_ref"] == derived["result"]["source_ref"] and reread["changed_record_refs"] == []
            groups = [original["result"], derived["result"], reread["result"]]
            sources = [store.get(item["source_ref"]) for item in groups[:2]]
            assert all(source["provider"] == contracts.TOOL and source["origin"] == "tool"
                and source["version"] == contracts.SOURCE_VERSION for source in sources)
            controls = [json.loads(actual_get(store, source["request_ref"])) for source in sources]
            proof.update(groups=groups, sources=sources, controls=controls)
            _checkpoint(store, proof, output)
            for control in controls:
                for role in ("native_response", "transport"):
                    file = control["files"][role]["file"]
                    if file is not None:
                        native_files.add(file["artifact_ref"])
            original_result, saved_result = [control["worker"]["result"] for control in controls]
            for source, control, outcome in zip(sources, controls, (original, derived)):
                assert json.loads(actual_get(store, source["artifact_ref"])) == {
                    key: value for key, value in outcome["result"].items()
                    if key != "source_ref"}
                for role in ("sheet", "components"):
                    file = control["files"][role]["file"]
                    raw = actual_get(store, file["artifact_ref"])
                    assert file["sha256"] == hashlib.sha256(raw).hexdigest() and file["size_bytes"] == len(raw)
                    assert json.loads(raw) == control["worker"]["result"][role]
            assert original_result["sheet"] == saved_result["sheet"]
            assert original_result["components"] == saved_result["components"]
            assert [control["worker"]["result"]["calculation"] for control in controls] == [dict(state="completed", call_count=1)] * 2
            assert saved_result["transport"]["state"] == "not_requested" and controls[1]["intent"]["request"]["post"] is None
            assert sources[1]["parent_source_refs"] == [sources[0]["id"]]
            post_workers = [entry for entry in proof["workers"] if entry["request"]["post"] is not None]
            assert len(proof["workers"]) == 2 and len(post_workers) == 1
            post = controls[0]["intent"]["request"]["post"]
            assert post["form"] == dict(seq=SEQUENCE, iupred2="long", anchor2="no")
            assert post["url"] == contracts.ENDPOINT and post["max_bytes"] == 1048576 and post["timeout_seconds"] == gate["timeout_seconds"]
            transport = original_result["transport"]
            assert "post-started.json" in post_workers[0]["files"] and "transport-seal.json" in post_workers[0]["files"]
            assert transport == post_workers[0]["files"]["transport-seal.json"]["value"]
            assert original_result["sheet"]["inputs"]["native_csv"] is None
            assert original_result["sheet"]["inputs"]["native_log"] is None
            assert original_result["sheet"]["inputs"]["input_ref"] is None
            assert original_result["sheet"]["inputs"]["input_mapping"] is None
            assert original_result["sheet"]["inputs"]["protein_sequence"] == SEQUENCE
            assert original_result["sheet"]["inputs"]["threshold"] == .5
            assert original_result["sheet"]["inputs"]["native_response"] == transport["response_text"]
            assert original_result["sheet"]["inputs"]["native_outcome"] == adapter._native_outcome(transport)
            if transport["snapshot"] is not None:
                native_raw = bytes.fromhex(transport["response_hex"])
                file = controls[0]["files"]["native_response"]["file"]
                assert file["sha256"] == hashlib.sha256(native_raw).hexdigest() and file["size_bytes"] == len(native_raw)
                assert {key: post_workers[0]["files"]["native-response.bin"][key] for key in ("sha256", "size_bytes")} == {
                    key: file[key] for key in ("sha256", "size_bytes")}
            context = original["result"]["values"]["context"]
            assert context["summary"]["scientific_service_execution_verified"] is False
            proof["actual_transport_success"] = adapter._native_outcome(transport) == "completed"
            proof["complete_transport_and_76_parsed_rows_observed"] = proof["actual_transport_success"] and context["status"] == "complete" and context["summary"]["source_parsed_row_count"] == 76
            records = EpisodeReturnRecords(store, flow.run_id, failure_prefix="disorder_episode_")
            episodes = list(store.db.execute("SELECT episode_id FROM runtime_episodes ORDER BY json_array_length(path)"))
            assert len(episodes) == 2
            parent, science = [records.context(row[0]) for row in episodes]
            assert controls[0]["intent"]["source_admission"] is None
            admission = controls[1]["intent"]["source_admission"]
            assert admission == records.source_admission_before(science, sources[0]["id"], 2)
            assert admission["baseline"] is False and admission["receipt"]["receipt_kind"] == "own_action"
            assert admission["receipt"]["source_index"] == 0
            for source_ref, cutoff in ((sources[0]["id"], 0), (sources[1]["id"], 2)):
                with pytest.raises(ValueError, match="result_not_received"):
                    records.source_admission_before(science, source_ref, cutoff)
            assert len(proof["cache"]) == 1
            assert flow.services.molecular_own_facts(science, fact_source=contracts.FACT_SOURCE) == groups
            assert flow.services.molecular_frozen_facts(science, fact_source=contracts.FACT_SOURCE) == groups
            assert flow.services.molecular_received_facts(parent, fact_source=contracts.FACT_SOURCE) == groups
            frozen = store.db.execute("SELECT facts,form FROM runtime_forms").fetchone()
            assert json.loads(frozen["facts"])[contracts.FACT_SOURCE] == groups and json.loads(frozen["form"]) == dict(outcomes=groups)
            attempt = store.db.execute("SELECT failure,form FROM runtime_report_attempts").fetchone()
            assert attempt["failure"] is None and json.loads(attempt["form"]) == dict(outcomes=groups)
            private = {ref for source in sources for ref in (source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"])}
            for current in (parent, science):
                known = set(flow.receipts.known(current.episode_id))
                assert {item["source_ref"] for item in groups} <= known and private.isdisjoint(known)
                assert all(registry.retained_molecular_reference_access(current, ref, "artifact") is False for ref in private)
            resolved = []
            validate_form(dict(outcomes=groups), _form(), lambda ref, ns: resolved.append((ref, ns)) or ns == "source" and ref in {item["source_ref"] for item in groups})
            assert set(resolved) == {(item["source_ref"], "source") for item in groups}
            proof["phase"] = "typed_delivery_verified_before_closed_replay"
            _checkpoint(store, proof, output)
            proof["closed_replay"] = _closed_receiver(store, directory, proof, groups, monkeypatch)
            proof.update(passed=True, phase="verified", selected_post_workers=1, saved_calculator_workers=1,
                host_calculator_calls=0, source_only_typed_delivery=True, provider_cleanup_callbacks=provider.cleanup)
    finally:
        _write(output, proof)
