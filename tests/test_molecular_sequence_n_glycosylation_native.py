"""Explicit genuine ordinary N scan, saved values and retained-only recovery.

Scripted choices exercise the real current Workflow; they are not biological
grading. The original scanner and existing sheet/calculator remain the owners
of the literal candidate-motif measurements.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import sys

import pytest

from gene_annotation_episode import glycosylation_measurements as glyco
from gene_annotation_episode import molecular_sequence_native as native
from gene_annotation_episode import molecular_sequence_ordinary as ordinary
from gene_annotation_episode import molecular_sequence_result_contracts as contracts
from gene_annotation_episode import molecular_sequence_tools as host
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.evidence_axis_instructions import instruction_view
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.molecular_sequence_execution_contracts import SOFTWARE_VERSION
from gene_annotation_episode.native_file_capture import retained_native_file
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import DecisionSource, ReturnedActionUnit, Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from tests.test_homer_motif_saved_workflow import _archive, _archive_value, _encode
from tests.test_molecular_sequence_tools_native import _pin, _write, _tables
from tests.test_runtime import FixtureController


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = "research/slotted_process_library/publications/2026-10-24-001"
REFERENCE_SITE = "reference/episode_tools/.venv/lib/python3.12/site-packages"
ORIGINAL_MODULE = REFERENCE_SITE + "/biomni/tool/glycoengineering.py"
MODULE_SHA256 = "ed3726d318f239e98183a359f18bcd341f4159ef2e400322c6141f77dcd2aff2"
CALLABLE_SHA256 = "d574294b1088dfb22b6f4242cc0c94b17de4999e86330e07620a83a0b4754c61"
PYTHON_SHA256 = "e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f"
TOOL = "find_n_glycosylation_motifs"
FACT = "n_glycosylation_motif_outcomes"
PROFILE = contracts.ordinary_molecular_sequence_profile(TOOL)
QUESTION = ("For the supplied NNST protein fragment with overlap enabled, which literal "
    "N-X-S/T candidate motifs, original positions, processed/source intervals and qualified "
    "native/printed populations are supported? Do the original retained and saved-sheet "
    "recalculated results agree under the same input and parameters, without a second scan? "
    "Preserve both Source-owned groups and distinguish original/processed symbol counts, "
    "native total and printed/usable rows. A candidate sequon does not establish experimentally "
    "measured glycosylation, occupancy, confidence or a transferred protein function; those "
    "properties remain unmeasured for this fragment.")
JOURNALS = ("runtime_episodes", "runtime_actions", "runtime_observations",
    "runtime_model_calls", "runtime_forms", "runtime_report_attempts")


def _forbidden(*args, **kwargs):
    raise AssertionError("No new native, calculation, input, model or acquisition work is permitted here")


def _credit(*args, **kwargs):
    return 0


def _controller(path, initial):
    return FixtureController(str(path), initial, 4 if path[-1][0] == "scientific_process" else 1)


def _rows():
    summary = ["original_symbol_count", "processed_symbol_count", "native_reported_sequence_length",
        "native_reported_total_count", "retained_printed_row_count", "usable_checked_row_count",
        "native_report_complete", "scan_exhaustiveness_verified"]
    sites = ["motif", "position_1based", "processed_interval", "source_intervals", "literal_sequon"]
    return [dict(row_id={"kind": "summary"}, fields=summary),
        *[dict(row_id={"kind": "glycosylation_site", "row_ordinal": i}, fields=deepcopy(sites)) for i in (0, 1)]]


def _form():
    return obj(dict(measurements=contracts.ordinary_molecular_sequence_fact_sources(TOOL)[FACT]["report_schema"]))


def _files(directory):
    directory = Path(directory)
    return {str(path.relative_to(directory)): dict(sha256=_pin(path)["sha256"],
        size_bytes=path.stat().st_size, mode=stat.S_IMODE(path.stat().st_mode))
        for path in sorted(directory.rglob("*")) if path.is_file() and not path.is_symlink()}


def _sqlite_pins(directory):
    directory = Path(directory)
    return [dict(name=name, **{key: value for key, value in _pin(directory / name).items() if key != "path"})
        for name in ("state.sqlite3", "state.sqlite3-wal", "state.sqlite3-shm") if (directory / name).is_file()]


def _history(store, run_id):
    history = {name: [dict(row) for row in store.db.execute(
        "SELECT * FROM " + name + " WHERE run_id=? ORDER BY rowid", (run_id,))] for name in JOURNALS}
    history["tool_operations"] = [dict(row) for row in store.db.execute(
        "SELECT * FROM tool_operations WHERE substr(operation_key,1,?)=? ORDER BY rowid",
        (len(run_id) + 1, run_id + ":"))]
    return history


def _checkpoint(store, proof, path):
    proof["history"] = _history(store, proof["run_id"])
    proof["counts"] = {key: len(rows) for key, rows in proof["history"].items()}
    proof["sqlite_pins"] = _sqlite_pins(store.path)
    proof["sqlite_pins_sha256"] = digest(proof["sqlite_pins"])
    _write(path, proof)


def _selected_closure(directory):
    attempt = Path(os.environ["HMMER529_ATTEMPT"]).resolve(strict=True)
    assert ROOT == attempt / "source_snapshot"
    request = json.loads((attempt / "selected_request.json").read_text())
    assert request["support_files"] == [ORIGINAL_MODULE]
    assert request["support_trees"] == [PUBLICATION]
    assert request["default_hmmer_fixtures"] is False
    assert request["native_executables"] == request["existing_native_executables"] == request["native_libraries"] == []
    assert request["policy"] == ordinary.POLICY and request["swap_bytes"] == 0
    assert request["selected_python_source_pin"]["sha256"] == PYTHON_SHA256
    python = _pin(attempt / "runtime/bin/python")
    assert python["sha256"] == PYTHON_SHA256 and Path(sys.executable).resolve(strict=True) == Path(python["path"])
    assert Path(sys.prefix).resolve(strict=True) == attempt / "runtime"
    module = _pin(ROOT / ORIGINAL_MODULE)
    assert module["sha256"] == MODULE_SHA256 and module["size_bytes"] == 6110
    files = {}
    for kind in ("source", "dependency", "stdlib", "binary"):
        for pin in json.loads((attempt / (kind + "_pins_before.json")).read_text()):
            assert _pin(pin["path"]) == pin and pin["path"] not in files
            files[pin["path"]] = pin
    manifest = directory / "selected-software-files.json"
    _write(manifest, [files[key] for key in sorted(files)])
    manifest_pin = _pin(manifest)
    roots = [str(ROOT), str(attempt / "dependencies"), str(ROOT / REFERENCE_SITE)]
    software = dict(version=SOFTWARE_VERSION, python=python,
        python_home=str(attempt / "runtime"), python_version=sys.version, import_roots=roots,
        software_files_file=manifest_pin, software_files_ref="artifact_" + manifest_pin["sha256"])
    deployment = dict(version=PROFILE["deployment_version"], runtime=dict(executable=python,
        home=software["python_home"]), module=module, import_roots=roots,
        software_files_file=manifest_pin, software_files_ref=software["software_files_ref"])
    return deployment, software, dict(selected_request_file=_pin(attempt / "selected_request.json"),
        module=module, python=python, manifest_file=manifest_pin,
        qualification="New explicitly selected current closure; original glyco source/callable pins retained. No historical227 scan rerun.")


def _configuration(directory, deployment, software):
    workspace = directory / "native-workspace"
    workspace.mkdir()
    resources = {"selected-n": dict(kind="local", workspace=str(workspace), policy=deepcopy(ordinary.POLICY),
        native_molecular_sequence=[dict(version=host.BINDING_VERSION, operation=TOOL,
            deployment=deployment, software=software)])}
    environments = [dict(operation=TOOL, resource_id="selected-n", binding_ordinal_0based=0,
        environment=deepcopy(ordinary.ENVIRONMENT_SELECTION))]
    return resources, environments


def _assemble(store, directory, proof, provider):
    factory = ExecutionServiceFactory.from_record(proof["factory"])
    registry = ToolRegistry(store, job_limits=deepcopy(ordinary.POLICY))
    application = factory(store, run_id=proof["run_id"], directory=directory, tool_registry=registry)
    workflow = Workflow(store, registry, provider, directory, proof["run_id"], _controller, _credit,
        project_child_credit=_credit, episode_record_receipts=True,
        initial_known_record_refs=proof["initial_known_record_refs"],
        episode_binding_descriptors=[proof["scientific_binding"], *application.episode_binding_descriptors],
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
    return workflow, registry


class _Choices:
    def __init__(self, store, library, proof, output, active):
        self.store, self.library, self.proof, self.output, self.active = store, library, proof, output, active
        self.turns, self.states = {}, {}
        self.connection = object.__new__(_SessionConnection)
        self.connection.scientific_prompt_states = {}

    async def complete(self, episode_id, role, instructions, context, schema):
        context = plain(context)
        row = self.store.db.execute("SELECT path FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (self.proof["run_id"], episode_id)).fetchone()
        grain = json.loads(row["path"])[-1][0]
        turn = self.turns.get(episode_id, 0) + 1
        self.turns[episode_id] = turn
        assert role == "REASONING" and not context.get("feedback"), context.get("feedback")
        assert context["goal"]["objective"] == QUESTION
        assert context["goal"]["task_context"]["root_objective"] == QUESTION
        wire, wire_instructions = self.connection._presentation(episode_id, role, instructions,
            state_frame(context, self.states.get(episode_id)))
        self.states[episode_id] = deepcopy(context)
        call = dict(episode_id=episode_id, grain=grain, turn=turn, context=deepcopy(context),
            instructions=plain(instructions), schema=deepcopy(schema), wire=wire,
            wire_instructions=plain(wire_instructions), wire_sha256=hashlib.sha256(wire.encode()).hexdigest(),
            wire_size_bytes=len(wire.encode()))
        self.proof["calls"].append(call)
        if grain == "annotation":
            assert turn == 1
            selected = dict(kind="episode_child", role="scientific_process", goal=QUESTION,
                scope=deepcopy(self.proof["scope"]), purpose=QUESTION, schema_json=json.dumps(_form()),
                initial_report_json="{}", assignment=dict(selection=dict(version="scientific_process_selection_v3",
                    evidence_axis=self.library.reference("A101"), thought_pattern=self.library.reference("P02"),
                    child_tool_info=[dict(name=TOOL, resources="local")]), evidence_refs=[], constraints={},
                    context=dict(n_motif_request=deepcopy(self.proof["arguments"]))))
        else:
            assert grain == "scientific_process" and 1 <= turn <= 4
            self.active["turn"] = turn
            assert context["requested_form"] == _form()
            process = context["scientific_process"]
            assert process["evidence_axis"] == instruction_view(self.library.resolve(self.library.reference("A101")))
            assert process["assignment"]["context"]["n_motif_request"] == self.proof["arguments"]
            entry, = [item for item in context["tools"] if item["name"] == TOOL]
            assert entry["resources"] == "local"
            assert wire.startswith("TASK\n") and "\n\nSTEERING\n" in wire
            assert QUESTION in wire and self.proof["selected_tool_contract"]["instructions"] in wire
            assert self.proof["selected_tool_contract"]["description"] in wire
            assert str(Path(self.proof["case_directory"])) not in wire
            previous = [json.loads(item["result"]) for item in self.store.db.execute(
                "SELECT result FROM tool_operations WHERE substr(operation_key,1,?)=? ORDER BY rowid",
                (len(self.proof["run_id"]) + 1, self.proof["run_id"] + ":"))]
            if turn == 1:
                arguments = deepcopy(self.proof["arguments"])
            elif turn == 2:
                assert len(previous) == 1
                arguments = dict(mode="read_stored", result_ref=previous[0]["result"]["source_ref"], rows=_rows())
            elif turn == 3:
                assert len(previous) == 2 and previous[1]["result"] == previous[0]["result"]
                assert previous[1]["changed_record_refs"] == []
                self.proof["literal_original_read_verified"] = True
                # Only this case's private workspace and original operand body
                # are removed. Shared selected software/runtime/source stay intact.
                workspace = Path(self.proof["factory"]["resources"]["selected-n"]["workspace"])
                assert workspace.parent == Path(self.proof["case_directory"])
                self.proof["removed_native_workspace_files"] = _files(workspace)
                retained = workspace.parent / "retained-native-workspace"
                assert not retained.exists()
                workspace.rename(retained)
                assert _files(retained) == self.proof["removed_native_workspace_files"]
                self.proof["retained_native_workspace"] = str(retained)
                workspace.mkdir()
                assert list(workspace.iterdir()) == []
                body = retained_native_file(self.store, self.proof["input_file"])
                assert _pin(body)["sha256"] == self.proof["input_file"]["sha256"]
                body.unlink()
                self.proof["owned_original_operand_body_removed"] = True
                arguments = dict(mode="calculate_saved", result_ref=previous[0]["result"]["source_ref"], rows=_rows())
            else:
                assert len(previous) == 3 and previous[2]["result"]["source_ref"] != previous[0]["result"]["source_ref"]
                arguments = dict(mode="read_stored", result_ref=previous[2]["result"]["source_ref"], rows=_rows())
            if turn > 1:
                shown = contracts.validate_ordinary_molecular_sequence_return(context["last_local_outcome"]["result"], operation=TOOL)
                assert shown == previous[-1]["result"]
            selected = dict(kind="tool", tool=TOOL, arguments=arguments)
        answer = _encode(dict(selection=selected, report_update={}), schema)
        call["response"] = deepcopy(answer)
        self.proof["phase"] = "decision_selected"
        _checkpoint(self.store, self.proof, self.output)
        return answer

    async def release(self, episode_id):
        pass


def _document(store, file):
    metadata = store.get(file["artifact_ref"])
    assert metadata["sha256"] == file["sha256"] and metadata["size"] == file["size_bytes"]
    return json.loads(store.get_artifact(file["artifact_ref"]))


def _cell(public, field, ordinal=None):
    return next(row for row in public["values"]["rows"] if row["field"] == field
        and (ordinal is None or row["row_id"].get("row_ordinal") == ordinal))


def _verify(store, workflow, registry, proof):
    history = _history(store, proof["run_id"])
    episodes = sorted(history["runtime_episodes"], key=lambda row: len(json.loads(row["path"])))
    assert len(episodes) == 2 and all(row["state"] == "yielded" and row["archive"] and row["completion"] for row in episodes)
    assert all(len(history[name]) == 5 for name in ("runtime_actions", "runtime_observations", "runtime_model_calls"))
    operations = history["tool_operations"]
    assert len(operations) == 4 and all(row["name"] == TOOL for row in operations)
    arguments = [json.loads(row["arguments"]) for row in operations]
    assert arguments == [proof["arguments"],
        dict(mode="read_stored", result_ref=json.loads(operations[0]["result"])["result"]["source_ref"], rows=_rows()),
        dict(mode="calculate_saved", result_ref=json.loads(operations[0]["result"])["result"]["source_ref"], rows=_rows()),
        dict(mode="read_stored", result_ref=json.loads(operations[2]["result"])["result"]["source_ref"], rows=_rows())]
    outcomes = [json.loads(row["result"]) for row in operations]
    assert all(row["status"] == "completed" for row in outcomes)
    values = [contracts.validate_ordinary_molecular_sequence_return(row["result"], operation=TOOL) for row in outcomes]
    assert values[0] == values[1] and values[2] == values[3]
    assert values[0]["source_ref"] != values[2]["source_ref"]
    assert values[0]["values"]["source_sheet_ref"] == values[2]["values"]["source_sheet_ref"]
    for index, (outcome, public) in enumerate(zip(outcomes, values)):
        assert outcome["record_refs"] == [public["source_ref"]]
        assert outcome["changed_record_refs"] == ([] if index in (1, 3) else [public["source_ref"]])
        assert public["failures"] == []
        for field, expected in dict(original_symbol_count=4, processed_symbol_count=4,
                native_reported_sequence_length=4, native_reported_total_count=2,
                retained_printed_row_count=2, usable_checked_row_count=2,
                native_report_complete=True, scan_exhaustiveness_verified=False).items():
            cell = _cell(public, field)
            assert cell["value_state"] == "stored_value" and type(cell["value"]) is type(expected) and cell["value"] == expected
        for ordinal, motif, position, interval in ((0, "NNS", 1, [0, 3]), (1, "NST", 2, [1, 4])):
            for field, expected in dict(motif=motif, position_1based=position,
                    processed_interval=interval, literal_sequon=True).items():
                assert _cell(public, field, ordinal)["value"] == expected
        assert public["values"]["context"]["parameters"]["supplied_allow_overlap"]["value"] is True
    records = EpisodeReturnRecords(store, proof["run_id"], failure_prefix="n_native_proof_")
    parent, science = [records.context(row["episode_id"]) for row in episodes]
    for context in (parent, science):
        records.authenticate(context)
    expected = dict(measurements=[values[0], values[2]])
    frozen, = history["runtime_forms"]
    report, = history["runtime_report_attempts"]
    assert frozen["episode_id"] == science.episode_id and json.loads(frozen["form"]) == expected
    assert json.loads(frozen["facts"])[FACT] == expected["measurements"]
    assert report["failure"] is None and json.loads(report["form"]) == expected
    assert report["parent_episode_id"] == parent.episode_id and report["child_episode_id"] == science.episode_id
    assert workflow.services.molecular_own_facts(science, fact_source=FACT) == expected["measurements"]
    assert workflow.services.molecular_frozen_facts(science, fact_source=FACT) == expected["measurements"]
    assert workflow.services.molecular_received_facts(parent, fact_source=FACT) == expected["measurements"]
    archives = [_archive(row, workflow.directory) for row in episodes]
    assert [row["units_consumed"] for row in archives] == [1, 4]
    assert all(row["ended_by"] == "yield_stop" for row in archives)
    assert archives[0]["units"][0]["child_result"] == dict(form=expected)
    owner = registry.molecular_sequence_results_for(proof["run_id"])
    publications = [owner.read_ordinary_molecular_sequence_publication(science, value["source_ref"],
        operation=TOOL, read_received=workflow.services.read_received_molecular_input) for value in expected["measurements"]]
    control = publications[0]["control"]
    original = control["original"]
    execution = _document(store, original["execution_file"])
    driver_request = _document(store, original["driver_request_file"])
    bundle = _document(store, original["bundle_file"])
    declaration = _document(store, original["declaration_file"])
    assert execution["terminal"] is execution["quiescent"] is True and execution["returncode"] == 0
    assert execution["failure"] is None and execution["metadata"]["policy"] == ordinary.POLICY
    assert execution["plan"]["identity"]["operation_key"] == operations[0]["operation_key"]
    assert execution["plan"]["selection"]["operation"] == TOOL
    assert bundle["invocation"]["invocation_count"] == bundle["invocation"]["launch_attempt_count"] == 1
    assert bundle["invocation"]["process_exit_observed"] is True
    assert declaration["native_call_state"] == "returned" and declaration["native_failure"] is declaration["driver_failure"] is None
    operand = _document(store, control["request"]["input_binding_file"])["frozen_operand"]
    assert operand["sequence"] == proof["stored_sequence"] == "NNST"
    assert operand["input_file"] == proof["input_file"]
    assert driver_request["selection"]["version"] == PROFILE["native_request_version"]
    assert driver_request["selection"]["arguments"] == dict(sequence="NNST", allow_overlap=True)
    assert driver_request["scientific_context"] == dict(input_ref=proof["subject_ref"], input_mapping=operand["parent_mapping"])
    source_files = control["source_files"]
    capture, sheet, components = [_document(store, source_files[role]["file"]) for role in ("capture", "sheet", "components")]
    assert capture["native_call_state"] == "returned" and capture["failure"] is None
    assert capture["execution_receipt"]["module_load"]["source_file"]["sha256"] == MODULE_SHA256
    assert capture["execution_receipt"]["observed_callable"]["sha256"] == CALLABLE_SHA256
    assert capture["execution_receipt"]["libraries"] == []
    assert capture["native_record"]["result"] == sheet["inputs"]["native_log"]
    assert sheet["inputs"]["sequence"] == "NNST" and sheet["inputs"]["parameters"] == dict(allow_overlap=True)
    assert components["status"] == sheet["status"] == "complete" and len(components["rows"]) == 2
    saved = publications[1]["control"]
    assert saved["source_files"]["sheet"]["file"] == source_files["sheet"]["file"]
    assert saved["calculation"]["native_call_state"] == "not_requested"
    assert saved["calculation"]["state"] == "returned" and saved["calculation"]["call_count"] == 1
    for context in (parent, science):
        known = set(workflow.receipts.known(context.episode_id))
        assert {proof["subject_ref"], proof["input_file"]["artifact_ref"], values[0]["source_ref"], values[2]["source_ref"]} <= known
        resolver = workflow.resolver(plain(context.scope), context=context)
        assert resolver(proof["input_file"]["artifact_ref"], "artifact") is True
        for publication in publications:
            source = publication["source"]
            private = {source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"]}
            assert proof["input_file"]["artifact_ref"] not in private and private.isdisjoint(known)
            for reference in private:
                denied, path = workflow.services.read_received_molecular_input(context, reference, "artifact", file_format="json")
                assert denied["failure"] is not None and path is None
        assert set(workflow.receipts.known(context.episode_id)) == known
    calls = history["runtime_model_calls"]
    assert len(proof["calls"]) == len(calls) == 5
    for row, recorded in zip(calls, proof["calls"]):
        request = json.loads(row["request"])
        assert row["episode_id"] == recorded["episode_id"] and request["context"] == recorded["context"]
        assert json.loads(row["response"]) == recorded["response"]
        assert hashlib.sha256(recorded["wire"].encode()).hexdigest() == recorded["wire_sha256"]
    return dict(returned=expected, episode_ids=[parent.episode_id, science.episode_id], archives=archives,
        outcomes=outcomes, original_native_handle=execution["handle"], original_invocation_count=1,
        saved_calculation_count=1, source_files=source_files)


class _NoNewDecisions:
    async def complete(self, *args, **kwargs):
        _forbidden()

    async def release(self, episode_id):
        pass


def _closed_replay(store, directory, proof, monkeypatch):
    before_tables, before_files = _tables(store), _files(directory)
    before_artifacts = _files(store.path / "artifacts")
    before_history = _history(store, proof["run_id"])
    episodes = sorted(before_history["runtime_episodes"], key=lambda row: len(json.loads(row["path"])))
    parent_archive, child_archive = [_archive(row, directory) for row in episodes]
    expected_request = json.loads(episodes[1]["request"])
    expected_form = json.loads(before_history["runtime_forms"][0]["form"])
    cached_calls = []
    with monkeypatch.context() as guarded:
        for module, names in ((ordinary, ("prepare_ordinary_molecular_sequence_attempt", "run_ordinary_molecular_sequence_attempt")),
                (native, ("execute_molecular_sequence_request",)),
                (native_lifecycle, ("prepare_job", "start_prepared", "resume_start", "status", "wait_job", "collect", "cancel"))):
            for name in names:
                if hasattr(module, name):
                    guarded.setattr(module, name, _forbidden)
        guarded.setattr(glyco, "calculate_glycosylation_components", _forbidden)
        guarded.setattr(ToolRegistry, "_prepare_molecular_sequence_operand", _forbidden)
        guarded.setattr("socket.create_connection", _forbidden)
        workflow, registry = _assemble(store, directory, proof, _NoNewDecisions())
        guarded.setattr(registry.clients, "_http", _forbidden)
        call = DecisionSource.call
        async def cached_call(source, context, schema):
            assert source.path[-1][0] == "annotation"
            row = source.workflow.journal.row("runtime_model_calls", source.episode_id, source.calls)
            assert row is not None and row["response"] is not None
            answer = await call(source, context, schema)
            cached_calls.append(dict(episode_id=source.episode_id, decision_index=answer[1]))
            return answer
        guarded.setattr(DecisionSource, "call", cached_call)
        selected = workflow._closed_child_commission
        returned = []
        def closed(*args, **kwargs):
            unit = selected(*args, **kwargs)
            assert isinstance(unit, ReturnedActionUnit)
            returned.append(dict(request=plain(unit.request.as_record()), child=_archive_value(unit.record)))
            assert plain(unit.request.as_record()) == expected_request
            assert _archive_value(unit.record) == child_archive
            assert plain(unit.result.as_record()) == dict(form=expected_form)
            return unit
        guarded.setattr(workflow, "_closed_child_commission", closed)
        root = workflow.build("annotation", "root", QUESTION, proof["scope"])
        completed = asyncio.run(root.run_async(workflow.context))
        final = _archive_value(asyncio.run(root.build_result(completed)))
        assert final == dict(credit=0, pending_handles=[])
        assert len(returned) == 1
        assert _archive_value(completed) == parent_archive
        assert cached_calls == [dict(episode_id=episodes[0]["episode_id"], decision_index=0)]
    assert _tables(store) == before_tables and _history(store, proof["run_id"]) == before_history
    assert _files(directory) == before_files and _files(store.path / "artifacts") == before_artifacts
    return dict(cached_parent_calls=cached_calls, new_model_calls=0, new_actions=0, new_native=0,
        new_calculations=0, all_tables_unchanged=True, files_and_modes_unchanged=True, final=final)


def test_genuine_n_glycosylation_native_saved_and_typed_parent(tmp_path, monkeypatch):
    if os.environ.get("HMMER_NATIVE_ORACLE_ORDINARY_N_GLYCOSYLATION") != "1":
        pytest.skip("requires explicit bounded ordinary N native selection")
    tag = os.environ.get("HMMER_NATIVE_ORACLE_ORDINARY_N_GLYCOSYLATION_ATTEMPT_ID")
    assert tag and Path(tag).name == tag and tag not in (".", "..")
    case = tmp_path / ("n-glycosylation-" + tag)
    case.mkdir()
    output = case / "N_GLYCOSYLATION_WORKFLOW.json"
    proof = dict(version="ordinary_n_glycosylation_workflow_v1", run_id="ordinary-n-" + tag,
        case_directory=str(case), store_directory=str(case / "store"), workflow_directory=str(case / "run"),
        question=QUESTION, calls=[], native_attempts=[], saved_calculator_calls=[], phase="prepared",
        literal_original_read_verified=False, owned_original_operand_body_removed=False,
        typed_delivery_verified=False, native_custody_verified=False, closed_replay_verified=False,
        passed=False, qualification="Scripted finite choices; genuine original N callable and existing calculator, no measured glycosylation claim.")
    _write(output, proof)
    active = dict(turn=0)
    try:
        deployment, software, proof["closure"] = _selected_closure(case)
        resources, environments = _configuration(case, deployment, software)
        factory = ExecutionServiceFactory(resources, {}, 2, .25, .5,
            molecular_sequence_environments=environments, molecular_sequence_saved_modes=True)
        proof["factory"] = factory.as_record()
        with Store(case / "store") as store:
            subject, = store.create_problem(raw_sequence="NNST", molecule="protein")["subject_refs"]
            subject_record = store.get(subject)
            file = store.get(subject_record["sequence_ref"])
            raw = store.get_artifact(file["id"])
            assert raw == b"NNST"
            proof.update(subject_ref=subject, scope=store.validate_scope(), stored_sequence=raw.decode("ascii"),
                input_api="Store.create_problem retains the observed stored File; no lowercase-retention assumption",
                input_file=dict(artifact_ref=file["id"], sha256=file["sha256"], size_bytes=file["size"], format="ascii_sequence"),
                initial_known_record_refs=[subject, file["id"]], arguments=dict(subject_ref=subject, allow_overlap=True, rows=_rows()))
            configured = ToolRegistry(store, job_limits=deepcopy(ordinary.POLICY))
            factory.configure_tool_registry(configured)
            proof["selected_tool_contract"] = configured.catalog()[TOOL]
            assert proof["selected_tool_contract"]["invocation_route"] == dict(kind="direct")
            proof["scientific_binding"] = prepare_scientific_binding(run_directory=case / "run",
                source_directory=ROOT / PUBLICATION, tool_catalog=configured.catalog(), child_roles=["scientific_process"])
            library = ScientificProcessLibrary(case / "run/scientific-process-library")
            provider = _Choices(store, library, proof, output, active)
            workflow, registry = _assemble(store, case / "run", proof, provider)
            prepare, observe = ordinary.prepare_ordinary_molecular_sequence_attempt, host._observe_original
            def prepare_once(**kwargs):
                assert active["turn"] == 1 and not proof["native_attempts"]
                prepared = prepare(**kwargs)
                proof["native_attempts"].append(dict(prepared=deepcopy(prepared), returned=None))
                _checkpoint(store, proof, output)
                return prepared
            async def observe_once(prepared):
                assert active["turn"] == 1 and len(proof["native_attempts"]) == 1
                result = await observe(prepared)
                proof["native_attempts"][0]["returned"] = deepcopy(result)
                _checkpoint(store, proof, output)
                return result
            calculate = glyco.calculate_glycosylation_components
            def saved_once(sheet):
                assert active["turn"] == 3 and not proof["saved_calculator_calls"]
                proof["saved_calculator_calls"].append(dict(sheet_sha256=digest(sheet), phase="entered"))
                _checkpoint(store, proof, output)
                result = calculate(sheet)
                proof["saved_calculator_calls"][0].update(phase="returned", components_sha256=digest(result))
                _checkpoint(store, proof, output)
                return result
            with monkeypatch.context() as measured:
                measured.setattr(ordinary, "prepare_ordinary_molecular_sequence_attempt", prepare_once)
                measured.setattr(host, "_observe_original", observe_once)
                measured.setattr(glyco, "calculate_glycosylation_components", saved_once)
                measured.setattr(registry.clients, "_http", _forbidden)
                root = workflow.build("annotation", "root", QUESTION, proof["scope"])
                try:
                    _checkpoint(store, proof, output)
                    completed = asyncio.run(root.run_async(workflow.context))
                    proof.update(phase="workflow_returned", archive=_archive_value(completed))
                    _checkpoint(store, proof, output)
                    proof["delivery"] = _verify(store, workflow, registry, proof)
                    proof.update(typed_delivery_verified=True, native_custody_verified=True)
                    assert len(proof["native_attempts"]) == len(proof["saved_calculator_calls"]) == 1
                    assert proof["saved_calculator_calls"][0]["phase"] == "returned"
                    proof["final_result"] = _archive_value(asyncio.run(root.build_result(completed)))
                    assert proof["final_result"] == dict(credit=0, pending_handles=[])
                    _checkpoint(store, proof, output)
                finally:
                    _checkpoint(store, proof, output)
            proof["replay"] = _closed_replay(store, case / "run", proof, monkeypatch)
            proof.update(phase="verified", closed_replay_verified=True, passed=True)
            _checkpoint(store, proof, output)
    except BaseException as error:
        proof["failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        if (case / "store/state.sqlite3").is_file():
            proof["sqlite_pins"] = _sqlite_pins(case / "store")
            proof["sqlite_pins_sha256"] = digest(proof["sqlite_pins"])
        _write(output, proof)


def test_retained_completed_n_glycosylation_finishes_without_scan_or_calculation(tmp_path, monkeypatch):
    reference = os.environ.get("HMMER_NATIVE_ORACLE_N_GLYCOSYLATION_RETAINED_PROOF")
    if not reference:
        pytest.skip("requires the explicit retained genuine N proof")
    output = Path(reference).resolve(strict=True)
    assert _pin(output)["sha256"] == os.environ["HMMER_NATIVE_ORACLE_N_GLYCOSYLATION_PROOF_SHA256"]
    proof = json.loads(output.read_text())
    assert proof["version"] == "ordinary_n_glycosylation_workflow_v1" and proof["question"] == QUESTION
    original = output.parent
    assert original == Path(proof["case_directory"]) and Path(proof["store_directory"]) == original / "store"
    pins = _sqlite_pins(original / "store")
    assert pins == proof["sqlite_pins"] and digest(pins) == os.environ["HMMER_NATIVE_ORACLE_N_GLYCOSYLATION_SQLITE_PINS_SHA256"]
    assert len(proof["calls"]) == 5 and len(proof["native_attempts"]) == len(proof["saved_calculator_calls"]) == 1
    before = _files(original)
    owned = tmp_path / "owned-retained-n"
    shutil.copytree(original, owned, ignore=shutil.ignore_patterns("state.sqlite3", "state.sqlite3-wal", "state.sqlite3-shm"))
    staging = tmp_path / "owned-sqlite-recovery"
    staging.mkdir()
    for pin in pins:
        shutil.copy2(original / "store" / pin["name"], staging / pin["name"])
        assert _pin(staging / pin["name"])["sha256"] == pin["sha256"]
    # Any WAL recovery is standard SQLite on owned copies only. Never open
    # the original physical family, manufacture rows, or declare it closed.
    with sqlite3.connect(staging / "state.sqlite3") as source:
        with sqlite3.connect(owned / "store/state.sqlite3") as target:
            source.backup(target)
    result = dict(version="ordinary_n_glycosylation_retained_finish_v1", original_proof=_pin(output),
        original_sqlite_pins=pins, passed=False, new_native=0, new_calculations=0, new_model_calls=0)
    finish = tmp_path / "N_GLYCOSYLATION_RETAINED_FINISH.json"
    _write(finish, result)
    try:
        with Store(owned / "store") as store:
            with monkeypatch.context() as guarded:
                guarded.setattr(glyco, "calculate_glycosylation_components", _forbidden)
                guarded.setattr(ordinary, "prepare_ordinary_molecular_sequence_attempt", _forbidden)
                guarded.setattr(ordinary, "run_ordinary_molecular_sequence_attempt", _forbidden)
                guarded.setattr(native, "execute_molecular_sequence_request", _forbidden)
                guarded.setattr("socket.create_connection", _forbidden)
                workflow, registry = _assemble(store, owned / "run", proof, _NoNewDecisions())
                guarded.setattr(registry.clients, "_http", _forbidden)
                before_tables = _tables(store)
                result["delivery"] = _verify(store, workflow, registry, proof)
                assert _tables(store) == before_tables
                result["replay"] = _closed_replay(store, owned / "run", proof, guarded)
                result["passed"] = True
    except BaseException as error:
        result["failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        result["original_files_and_modes_unchanged"] = _files(original) == before
        result["owned_sqlite_pins"] = _sqlite_pins(owned / "store")
        _write(finish, result)
    assert result["original_files_and_modes_unchanged"]
