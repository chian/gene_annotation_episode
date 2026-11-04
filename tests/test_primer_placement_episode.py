"""Opt-in current ordinary placement, saved values and typed receiving boundary.

One new selected callable execution uses caller-supplied engineering operands.
The old234 attempt is neither restored nor relabelled. This test introduces no
placement scan, mismatch formula, PCR, design or confidence interpretation.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

from method_loop import EpisodeView
import pytest

from gene_annotation_episode import molecular_sequence_driver as driver
from gene_annotation_episode import molecular_sequence_native as native
from gene_annotation_episode import molecular_sequence_ordinary as ordinary
from gene_annotation_episode import molecular_sequence_result_contracts as shared
from gene_annotation_episode import molecular_sequence_tools as host
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode import primer_placement_measurements as science
from gene_annotation_episode import primer_placement_result_contracts as contracts
from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.evidence_axis_instructions import instruction_view
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.molecular_sequence_results import MolecularSequenceResults
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import DecisionSource, ReturnedActionUnit
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from tests.test_homer_motif_saved_workflow import _archive, _archive_value, _encode
from tests.test_molecular_sequence_n_glycosylation_native import (
    _assemble, _checkpoint, _document, _files, _history, _sqlite_pins,
)
from tests.test_molecular_sequence_tools_native import (
    PUBLICATION, ROOT, _selected_closure, _tables, _write,
)


TOOL, FACT = contracts.TOOL, contracts.FACT_SOURCE
PROFILE = contracts.profile()
CALLABLE_SHA256 = "22db874a1776118c633103253ae0366f1e2d09df47b6bf41b031f423ff25d82e"
QUESTION = (
    "For the explicitly supplied target and ordered primer occurrences, what literal "
    "complete ungapped placements and checked mismatch positions are supported by the "
    "selected source's at-most-one-mismatch rule? Preserve repeated primer occurrences, "
    "orientations, original operand identities/mappings, native/checked populations and "
    "full-primer mismatch denominators. Compare retained original and saved-Sheet values "
    "under the same operands, including a new ordered stored view. Return the requested "
    "Source-owned fields and qualifications; this establishes no PCR performance, primer "
    "design, calibrated confidence or transferred biological function."
)
SUPPLIED = (("target", "AAAACCCCAAAATTTT"), ("primer-a", "AAAA"), ("primer-b", "TTTT"))


def _forbidden(*args, **kwargs):
    raise AssertionError("placement retained phase attempted new scientific/native/input/network work")


def _rows():
    return [dict(row_id=dict(kind="summary"), fields=list(shared.PLACEMENT_SUMMARY)),
        dict(row_id=dict(kind="placement_group", group_ordinal=0),
            fields=["primer_length_symbols", "candidate_windows_per_orientation", "candidate_oriented_windows", "reported_hit_count",
                "native_group", "primer_occurrence_ordinal", "native_group_ordinal", "native_sequence_matches_occurrence"]),
        dict(row_id=dict(kind="placement_hit", group_ordinal=0, native_hit_ordinal=0),
            fields=["target_interval", "strand", "mismatch_count", "mismatch_fraction.value", "native_hit",
                "oriented_source_primer", "target_window", "target_mapping", "primer_mapping"]),
        dict(row_id=dict(kind="placement_mismatch", group_ordinal=0, native_hit_ordinal=0, native_mismatch_ordinal=0),
            fields=["oriented_primer_position", "original_primer_position", "target_position", "symbols_match_full_operands",
                "native_triple", "target_source_intervals", "primer_source_intervals"])]


def _new_rows():
    return [dict(row_id=dict(kind="placement_hit", group_ordinal=ordinal, native_hit_ordinal=0),
            fields=["target_interval", "strand", "mismatch_fraction.denominator", "mismatch_fraction.value",
                "native_hit", "target_mapping", "primer_mapping"])
            for ordinal in (2, 0)] + [dict(row_id=dict(kind="summary"),
                fields=["requested_primer_occurrence_count", "mismatch_count_sum", "mismatch_count_denominator_hits"])]


def _form():
    return obj(dict(placements=contracts.fact_sources()[FACT]["report_schema"]))


def _configuration(case, deployment, software):
    workspace = case / "native-workspace"
    workspace.mkdir()
    resources = {"selected-placement": dict(kind="local", workspace=str(workspace), policy=deepcopy(ordinary.POLICY),
        native_molecular_sequence=[dict(version=host.BINDING_VERSION, operation=TOOL,
            deployment=deployment, software=software)])}
    environments = [dict(operation=TOOL, resource_id="selected-placement", binding_ordinal_0based=0,
        environment=deepcopy(ordinary.ENVIRONMENT_SELECTION))]
    return resources, environments


class UnexpectedPlacementFeedback(RuntimeError):
    pass


class _Choices:
    def __init__(self, store, library, proof, output, active):
        self.store, self.library, self.proof, self.output, self.active = store, library, proof, output, active
        self.turns, self.states, self.cleanup = {}, {}, []
        self.connection = object.__new__(_SessionConnection)
        self.connection.scientific_prompt_states = {}

    async def complete(self, episode_id, role, instructions, context, schema):
        context = plain(context)
        if context.get("feedback"):
            raise UnexpectedPlacementFeedback(json.dumps(context["feedback"], sort_keys=True))
        row = self.store.db.execute("SELECT path FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (self.proof["run_id"], episode_id)).fetchone()
        grain = json.loads(row["path"])[-1][0]
        turn = self.turns.get(episode_id, 0) + 1
        self.turns[episode_id] = turn
        assert role == "REASONING" and context["goal"]["objective"] == QUESTION
        wire, shown_instructions = self.connection._presentation(episode_id, role, instructions,
            state_frame(context, self.states.get(episode_id)))
        self.states[episode_id] = deepcopy(context)
        call = dict(episode_id=episode_id, grain=grain, turn=turn, context=deepcopy(context),
            instructions=plain(instructions), schema=deepcopy(schema), wire=wire,
            wire_instructions=plain(shown_instructions), wire_sha256=hashlib.sha256(wire.encode()).hexdigest())
        self.proof["calls"].append(call)
        if grain == "annotation":
            assert turn == 1
            selected = dict(kind="episode_child", role="scientific_process", goal=QUESTION,
                scope=deepcopy(self.proof["scope"]), purpose=QUESTION, schema_json=json.dumps(_form()),
                initial_report_json="{}", assignment=dict(selection=dict(version="scientific_process_selection_v3",
                    evidence_axis=self.library.reference("A101"), thought_pattern=self.library.reference("P02"),
                    child_tool_info=[dict(name=TOOL, resources="local")]),
                    evidence_refs=deepcopy(self.proof["initial_known_record_refs"]), constraints={},
                    context=dict(placement_request=deepcopy(self.proof["arguments"]))))
        else:
            assert grain == "scientific_process" and 1 <= turn <= 4
            assert context["requested_form"] == _form()
            process = context["scientific_process"]
            assert process["evidence_axis"] == instruction_view(self.library.resolve(self.library.reference("A101")))
            assert process["assignment"]["context"]["placement_request"] == self.proof["arguments"]
            entry, = [item for item in context["tools"] if item["name"] == TOOL]
            assert entry["resources"] == "local"
            assert wire.startswith("TASK\n") and "\n\nSTEERING\n" in wire and QUESTION in wire
            for field in ("description", "instructions"):
                assert self.proof["selected_tool_contract"][field] in wire
            assert str(Path(self.proof["case_directory"])) not in wire
            previous = [json.loads(item["result"]) for item in self.store.db.execute(
                "SELECT result FROM tool_operations WHERE substr(operation_key,1,?)=? ORDER BY rowid",
                (len(self.proof["run_id"]) + 1, self.proof["run_id"] + ":"))]
            if turn == 1:
                arguments = deepcopy(self.proof["arguments"])
            else:
                assert len(previous) == turn - 1
                shown = contracts.validate_return(context["last_local_outcome"]["result"])
                assert shown == previous[-1]["result"]
                assert "Retained primer-placement operands and populations" in wire
                assert "source_assumptions" in wire and shown["source_ref"] in wire
                for field in ("native_group", "native_hit", "native_triple", "target_source_intervals"):
                    if turn == 2:
                        assert field in wire
                assert all(file["sha256"] not in wire.replace(file["artifact_ref"], "")
                    for file in self.proof["input_files"].values())
                if turn == 2:
                    source = self.store.get(shown["source_ref"])
                    control = json.loads(self.store.get_artifact(source["request_ref"]))
                    capture_file = control["source_files"]["capture"]["file"]
                    self.proof["native_body_refs"] = [*self.proof["operand_file_refs"], capture_file["artifact_ref"]]
                    self.proof["original_public"] = deepcopy(shown)
                    _checkpoint(self.store, self.proof, self.output)
                    arguments = dict(mode="read_stored", result_ref=shown["source_ref"], rows=_rows())
                elif turn == 3:
                    assert previous[0]["result"] == previous[1]["result"]
                    assert previous[1]["changed_record_refs"] == []
                    self.proof["literal_original_read_verified"] = True
                    arguments = dict(mode="calculate_saved", result_ref=previous[0]["result"]["source_ref"], rows=[])
                else:
                    assert shown["selection"]["rows"] == [] and shown["values"]["rows"] == []
                    assert shown["context"]["population"] == previous[0]["result"]["context"]["population"]
                    assert "primer input form" in wire and "ordered list" in wire
                    arguments = dict(mode="read_stored", result_ref=shown["source_ref"], rows=_new_rows())
            self.active["turn"] = turn
            selected = dict(kind="tool", tool=TOOL, arguments=arguments)
        answer = _encode(dict(selection=selected, report_update={}), schema)
        call["response"] = deepcopy(answer)
        self.proof["phase"] = "decision_selected"
        _checkpoint(self.store, self.proof, self.output)
        return answer

    async def release(self, episode_id):
        self.cleanup.append(episode_id)


def _selected_cells_equal_components(public, components):
    profile = shared._public_profile(public["values"])
    for cell in public["values"]["rows"]:
        path, _type, unit, population, denominator_paths = shared.field_table(TOOL, cell["row_id"], profile=profile)[cell["field"]]
        literal = shared.pointer(components, path)
        assert cell["value_state"] == ("stored_null" if literal is None else "stored_value")
        assert digest(cell["value"]) == digest(literal)
        assert cell["source_pointer"] == path and cell["unit"] == unit and cell["population_id"] == population
        assert [item["source_pointer"] for item in cell["denominators"]] == list(denominator_paths)
        for item in cell["denominators"]:
            assert item["value_state"] == "stored_value" and item["value"] == shared.pointer(components, item["source_pointer"])


def _verify(store, workflow, registry, proof):
    history = _history(store, proof["run_id"])
    episodes = sorted(history["runtime_episodes"], key=lambda row: len(json.loads(row["path"])))
    assert len(episodes) == 2 and all(row["state"] == "yielded" and row["archive"] for row in episodes)
    assert all(len(history[name]) == 5 for name in ("runtime_actions", "runtime_observations", "runtime_model_calls"))
    operations = history["tool_operations"]
    assert len(operations) == 4 and all(row["name"] == TOOL for row in operations)
    outcomes = [json.loads(row["result"]) for row in operations]
    assert all(row["status"] == "completed" for row in outcomes)
    values = [contracts.validate_return(row["result"]) for row in outcomes]
    assert values[0] == values[1] and values[0]["source_ref"] != values[2]["source_ref"] == values[3]["source_ref"]
    assert values[2]["selection"]["rows"] == [] and values[2]["values"]["rows"] == []
    assert values[3]["selection"]["rows"] == _new_rows()
    for index, (outcome, public) in enumerate(zip(outcomes, values)):
        assert outcome["record_refs"] == [public["source_ref"]]
        assert outcome["changed_record_refs"] == ([] if index in (1, 3) else [public["source_ref"]])
        assert public["failures"] == []
        assert public["context"]["input"] == values[0]["context"]["input"]
        assert public["context"]["original_operand_files"] == values[0]["context"]["original_operand_files"]
    records = EpisodeReturnRecords(store, proof["run_id"], failure_prefix="placement_native_proof_")
    parent, science_context = [records.context(row["episode_id"]) for row in episodes]
    for context in (parent, science_context):
        records.authenticate(context)
    expected = dict(placements=[values[0], values[2], values[3]])
    frozen, = history["runtime_forms"]
    attempt, = history["runtime_report_attempts"]
    assert frozen["episode_id"] == science_context.episode_id and json.loads(frozen["form"]) == expected
    assert json.loads(frozen["facts"])[FACT] == expected["placements"]
    assert attempt["failure"] is None and json.loads(attempt["form"]) == expected
    assert attempt["parent_episode_id"] == parent.episode_id and attempt["child_episode_id"] == science_context.episode_id
    assert workflow.services.molecular_own_facts(science_context, fact_source=FACT) == expected["placements"]
    assert workflow.services.molecular_frozen_facts(science_context, fact_source=FACT) == expected["placements"]
    assert workflow.services.molecular_received_facts(parent, fact_source=FACT) == expected["placements"]
    archives = [_archive(row, workflow.directory) for row in episodes]
    assert [row["units_consumed"] for row in archives] == [1, 4]
    assert archives[0]["units"][0]["child_result"] == dict(form=expected)
    owner = registry.molecular_sequence_results_for(proof["run_id"])
    publications = [owner.read_ordinary_molecular_sequence_publication(science_context, value["source_ref"],
        operation=TOOL, read_received=workflow.services.read_received_molecular_input) for value in (values[0], values[2])]
    original, saved = [item["control"] for item in publications]
    execution = _document(store, original["original"]["execution_file"])
    request = _document(store, original["original"]["driver_request_file"])
    bundle = _document(store, original["original"]["bundle_file"])
    declaration = _document(store, original["original"]["declaration_file"])
    operand = _document(store, original["request"]["input_binding_file"])["frozen_operand"]
    assert execution["terminal"] is execution["quiescent"] is True and execution["returncode"] == 0
    assert execution["failure"] is None and execution["metadata"]["policy"] == ordinary.POLICY
    assert execution["plan"]["identity"]["operation_key"] == operations[0]["operation_key"]
    assert bundle["invocation"]["invocation_count"] == bundle["invocation"]["launch_attempt_count"] == 1
    assert bundle["invocation"]["process_exit_observed"] is True
    assert declaration["native_call_state"] == "returned" and declaration["native_failure"] is declaration["driver_failure"] is None
    arguments = proof["arguments"]
    assert request["selection"]["arguments"] == contracts.native_arguments(arguments, operand)
    assert request["scientific_context"] == contracts.scientific_context(arguments, operand)
    assert [item["subject"]["id"] for item in operand["primers"]] == arguments["primer_refs"]
    assert operand["primers"][0] == operand["primers"][2]
    assert operand["target"]["sequence"] == proof["stored_operands"][arguments["target_ref"]]
    assert [item["sequence"] for item in operand["primers"]] == [proof["stored_operands"][ref] for ref in arguments["primer_refs"]]
    files = original["source_files"]
    capture, sheet, components = [_document(store, files[role]["file"]) for role in ("capture", "sheet", "components")]
    assert capture["native_call_state"] == "returned" and capture["failure"] is None
    receipt = capture["execution_receipt"]
    assert receipt["module_load"]["source_file"] == proof["closure"]["module"]
    assert receipt["observed_callable"]["sha256"] == CALLABLE_SHA256
    assert [item["module_name"] for item in receipt["libraries"]] == ["pandas", "requests", "Bio", "bs4", "soupsieve", "typing_extensions"]
    assert sheet["inputs"]["native_record"] == capture["native_record"]
    assert sheet["inputs"]["target_sequence"] == proof["stored_operands"][arguments["target_ref"]]
    assert sheet["inputs"]["primers"] == [proof["stored_operands"][ref] for ref in arguments["primer_refs"]]
    assert sheet["inputs"]["primer_refs"] == arguments["primer_refs"]
    assert components["summary"]["requested_primer_occurrence_count"] == 3
    assert [group["primer_occurrence_ordinal"] for group in components["groups"]] == [0, 1, 2]
    assert components["groups"][0]["native_group"] == components["groups"][2]["native_group"]
    assert values[0]["context"]["population"] == components["summary"]
    assert values[0]["context"]["definitions"] == components["definitions"]
    _selected_cells_equal_components(values[0], components)
    selected_native = {(cell["row_id"]["kind"], cell["field"]): cell["value"]
        for cell in values[0]["values"]["rows"]}
    native_group = capture["native_record"]["result"]["sequences"][0]
    assert digest(selected_native[("placement_group", "native_group")]) == digest(native_group)
    assert digest(selected_native[("placement_hit", "native_hit")]) == digest(native_group["alignments"][0])
    assert digest(selected_native[("placement_mismatch", "native_triple")]) == digest(native_group["alignments"][0]["mismatches"][0])
    saved_components = _document(store, saved["source_files"]["components"]["file"])
    assert saved_components == components
    assert saved["source_files"]["sheet"]["file"] == files["sheet"]["file"]
    assert saved["calculation"]["native_call_state"] == "not_requested"
    assert saved["calculation"]["state"] == "returned" and saved["calculation"]["call_count"] == 1
    _selected_cells_equal_components(values[3], saved_components)
    fields_per_hit = len(_new_rows()[0]["fields"])
    assert [cell["row_id"]["group_ordinal"] for cell in values[3]["values"]["rows"][:2 * fields_per_hit]] == [2] * fields_per_hit + [0] * fields_per_hit
    with pytest.raises(ValueError, match="placement_native_proof_result_not_received"):
        records.source_admission_before(science_context, values[0]["source_ref"], 0)
    assert records.source_admission_before(science_context, values[0]["source_ref"], 1)["baseline"] is False
    with pytest.raises(ValueError, match="placement_native_proof_result_not_received"):
        records.source_admission_before(science_context, values[2]["source_ref"], 2)
    assert records.source_admission_before(science_context, values[2]["source_ref"], 3)["baseline"] is False
    private = set()
    for publication in publications:
        source = publication["source"]
        private.update([source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"]])
    assert private.isdisjoint(proof["operand_file_refs"])
    for context in (parent, science_context):
        known = set(workflow.receipts.known(context.episode_id))
        assert set(proof["initial_known_record_refs"]) <= known
        assert {values[0]["source_ref"], values[2]["source_ref"]} <= known and private.isdisjoint(known)
        resolver = workflow.resolver(plain(context.scope), context=context)
        for ref in proof["operand_file_refs"]:
            assert resolver(ref, "artifact") is True
        for ref in private:
            assert resolver(ref, "artifact") is False
        assert set(workflow.receipts.known(context.episode_id)) == known
    return dict(returned=expected, private_refs=sorted(private), publications=[item["source"] for item in publications],
        original_invocation_count=1, original_components_retained=True, saved_calculation_count=1,
        selected_native_literals_and_checked_mappings_inspectable=True)


class _NoDecisions:
    def __init__(self):
        self.cleanup = []

    async def complete(self, *args, **kwargs):
        _forbidden()

    async def release(self, episode_id):
        self.cleanup.append(episode_id)


def _closed_receiver(store, directory, proof, groups, monkeypatch):
    before_tables, before_files = _tables(store), _files(directory)
    before_artifacts = _files(store.path / "artifacts")
    episodes = sorted(_history(store, proof["run_id"])["runtime_episodes"], key=lambda row: len(json.loads(row["path"])))
    parent_archive, child_archive = [_archive(row, directory) for row in episodes]
    provider = _NoDecisions()
    packets = {store.get(group["source_ref"])["artifact_ref"] for group in groups}
    actual_get, receiver = Store.get_artifact, {}
    with monkeypatch.context() as guarded:
        for module, names in ((ordinary, ("prepare_ordinary_molecular_sequence_attempt", "run_ordinary_molecular_sequence_attempt")),
                (native, ("execute_molecular_sequence_request",)),
                (science, ("build_primer_placement_sheet", "calculate_primer_placement_components")),
                (driver, ("build_primer_placement_sheet", "calculate_primer_placement_components", "execute_molecular_sequence_request")),
                (native_lifecycle, ("prepare_job", "start_prepared", "resume_start", "status", "wait_job", "collect", "cancel", "release"))):
            for name in names:
                guarded.setattr(module, name, _forbidden)
        guarded.setattr(ToolRegistry, "execute_async", _forbidden)
        guarded.setattr(ToolRegistry, "_prepare_molecular_sequence_operand", _forbidden)
        guarded.setattr(PublicClients, "_http", _forbidden)
        guarded.setattr(Store, "get_artifact", _forbidden)
        workflow, _registry = _assemble(store, directory, proof, provider)
        root = workflow.build("annotation", "root", QUESTION, proof["scope"])
        completed = asyncio.run(root.run_async(workflow.context))
        assert _archive_value(completed) == parent_archive
        assert _archive_value(asyncio.run(root.build_result(completed))) == dict(credit=0, pending_handles=[])
        commission = workflow.journal.row("runtime_actions", root.source.episode_id, 0)
        closed = workflow.selected(root.source, json.loads(commission["action"]), 0)
        assert isinstance(closed, ReturnedActionUnit) and _archive_value(closed.record) == child_archive
        assert plain(closed.result.as_record()) == dict(form=dict(placements=groups))
        scope = workflow.context.enter(root.grain, root.key)
        try:
            view = EpisodeView(grain=root.grain, key=root.key, path=scope, units_consumed=completed.units_consumed,
                updates=tuple(workflow.context._child_updates.get(scope, ())), controller_state=completed.controller_state,
                episode_ref=completed.episode_ref, request=completed.request)
            def public_only(current, reference):
                assert reference in packets
                return actual_get(current, reference)
            class ReceiverCaptured(BaseException):
                pass
            async def capture(source, context, schema):
                assert plain(context["child_reports"]) == [dict(placements=groups)]
                connection = object.__new__(_SessionConnection)
                connection.scientific_prompt_states = {}
                with guarded.context() as no_bytes:
                    no_bytes.setattr(Store, "get_artifact", _forbidden)
                    wire, instructions = connection._presentation(source.episode_id, "REASONING", source.instructions(context),
                        state_frame(plain(context)))
                assert "Retained primer-placement operands and populations" in wire
                assert "mismatch_fraction.value" in wire and "source_assumptions" in wire
                assert all(group["source_ref"] in wire for group in groups)
                assert all(ref not in wire for ref in proof["delivery"]["private_refs"])
                assert str(directory.parent) not in wire
                receiver.update(context=plain(context), wire=wire, instructions=plain(instructions),
                    current_receiver_reconstruction=True, historical_post_return_decision_claimed=False)
                raise ReceiverCaptured()
            guarded.setattr(Store, "get_artifact", public_only)
            guarded.setattr(DecisionSource, "call", capture)
            calls = root.source.calls
            with pytest.raises(ReceiverCaptured):
                asyncio.run(root.source.next(view))
            assert root.source.calls == calls
        finally:
            workflow.context.leave(scope)
    assert _tables(store) == before_tables and _files(directory) == before_files
    assert _files(store.path / "artifacts") == before_artifacts
    return dict(all_rows_unchanged=True, files_and_modes_unchanged=True, new_provider_decisions=0,
        provider_cleanup_callbacks=provider.cleanup, new_tool_actions=0, new_native_attempts=0,
        new_calculations=0, closed_replay_verified=True, receiver=receiver)


def test_genuine_current_primer_placement_native_saved_typed_parent_and_closed_replay(tmp_path, monkeypatch):
    if os.environ.get("HMMER_NATIVE_ORACLE_PRIMER_PLACEMENT") != "1":
        pytest.skip("requires explicit bounded current primer-placement native selection")
    tag = os.environ.get("HMMER_NATIVE_ORACLE_PRIMER_PLACEMENT_ATTEMPT_ID")
    assert tag and Path(tag).name == tag and tag not in (".", "..")
    case = tmp_path / ("primer-placement-" + tag)
    case.mkdir()
    output = case / "PRIMER_PLACEMENT_WORKFLOW.json"
    proof = dict(version="ordinary_primer_placement_workflow_v1", run_id="ordinary-placement-" + tag,
        case_directory=str(case), store_directory=str(case / "store"), workflow_directory=str(case / "run"),
        question=QUESTION, supplied_operands=dict(SUPPLIED), calls=[], native_attempts=[], saved_calculator_calls=[],
        native_body_refs=[], cache_checks=[], phase="prepared", literal_original_read_verified=False,
        native_custody_verified=False, typed_delivery_verified=False, closed_replay_verified=False, passed=False,
        scripted_model_decisions=True, external_model_calls=0,
        qualification="New explicit engineering operands and selected current deployment; no old234 producer/custody restoration.")
    _write(output, proof)
    active = dict(turn=0, cache=False)
    try:
        deployment, software, proof["closure"] = _selected_closure(case)
        proof["closure"]["qualification"] = "New selected current source/runtime/import manifest; no historical234 path or producer restoration."
        assert deployment["version"] == PROFILE["deployment_version"]
        resources, environments = _configuration(case, deployment, software)
        factory = ExecutionServiceFactory(resources, {}, 2, .25, .5,
            molecular_sequence_environments=environments, molecular_sequence_saved_modes=True)
        assert ExecutionServiceFactory.from_record(factory.as_record()).as_record() == factory.as_record()
        proof["factory"] = factory.as_record()
        manifest = case / "supplied-operands.json"
        _write(manifest, dict(schema_version=1, entries=[dict(name=name, sequence=sequence, molecule="dna") for name, sequence in SUPPLIED]))
        with Store(case / "store") as store:
            problem = store.create_problem(manifest_path=manifest)
            assert problem["intake_status"] == "completed"
            by_name = {store.get(ref)["name"]: ref for ref in problem["subject_refs"]}
            assert set(by_name) == {name for name, _sequence in SUPPLIED}
            stored, input_files = {}, {}
            for name, supplied in SUPPLIED:
                ref = by_name[name]
                record = store.get(ref)
                file = store.get(record["sequence_ref"])
                raw = store.get_artifact(file["id"])
                assert raw == supplied.encode("ascii")
                stored[ref] = raw.decode("ascii")
                input_files[ref] = dict(artifact_ref=file["id"], sha256=file["sha256"], size_bytes=file["size"], format="ascii_sequence")
            proof.update(scope=store.validate_scope(), stored_operands=stored, input_files=input_files,
                operand_file_refs=list(dict.fromkeys(file["artifact_ref"] for file in input_files.values())),
                initial_known_record_refs=[*problem["subject_refs"], *dict.fromkeys(file["artifact_ref"] for file in input_files.values())],
                arguments=dict(mode="run_native", target_ref=by_name["target"],
                    primer_refs=[by_name["primer-b"], by_name["primer-a"], by_name["primer-b"]], rows=_rows()))
            configured = ToolRegistry(store, job_limits=deepcopy(ordinary.POLICY))
            factory.configure_tool_registry(configured)
            proof["selected_tool_contract"] = configured.catalog()[TOOL]
            proof["scientific_binding"] = prepare_scientific_binding(run_directory=case / "run",
                source_directory=ROOT / PUBLICATION, tool_catalog=configured.catalog(), child_roles=["scientific_process"])
            library = ScientificProcessLibrary(case / "run/scientific-process-library")
            provider = _Choices(store, library, proof, output, active)
            workflow, registry = _assemble(store, case / "run", proof, provider)
            prepare, observe = ordinary.prepare_ordinary_molecular_sequence_attempt, host._observe_original
            calculate, execute, get_artifact = science.calculate_primer_placement_components, registry.execute_async, Store.get_artifact
            retained_value, path_open = MolecularSequenceResults._ordinary_value, Path.open
            freeze_operand = registry._prepare_molecular_sequence_operand
            def prepare_once(**kwargs):
                assert active["turn"] == 1 and not proof["native_attempts"]
                prepared = prepare(**kwargs)
                proof["native_attempts"].append(dict(prepared=deepcopy(prepared), returned=None))
                _checkpoint(store, proof, output)
                return prepared
            async def observe_once(prepared):
                result = await observe(prepared)
                proof["native_attempts"][0]["returned"] = deepcopy(result)
                proof["phase"] = "original_native_attempt_returned"
                _checkpoint(store, proof, output)
                return result
            def saved_once(sheet):
                assert active["turn"] == 3 and not proof["saved_calculator_calls"]
                proof["saved_calculator_calls"].append(dict(sheet_sha256=digest(sheet), phase="entered"))
                _checkpoint(store, proof, output)
                result = calculate(sheet)
                proof["saved_calculator_calls"][0].update(phase="returned", components_sha256=digest(result))
                _checkpoint(store, proof, output)
                return result
            def retained_get(current, reference):
                if active["turn"] > 1 or active["cache"]:
                    assert reference not in proof["native_body_refs"]
                return get_artifact(current, reference)
            def checked_value(owner, file):
                if active["turn"] > 1 or active["cache"]:
                    assert file["artifact_ref"] not in proof["native_body_refs"]
                return retained_value(owner, file)
            def checked_open(path, *args, **kwargs):
                if active["turn"] > 1 or active["cache"]:
                    current = path.absolute()
                    protected = {Path(pin["path"]) for pin in (proof["closure"]["module"], proof["closure"]["python"], proof["closure"]["manifest_file"])}
                    protected.update(store.path / "artifacts" / ref[9:11] / ref[9:] for ref in proof["native_body_refs"])
                    assert current not in protected and not current.is_relative_to(case / "native-workspace")
                return path_open(path, *args, **kwargs)
            def checked_freeze(*args, **kwargs):
                assert active["turn"] == 1 and not active["cache"]
                return freeze_operand(*args, **kwargs)
            async def execute_with_same_key_cache(name, arguments, **kwargs):
                outcome = await execute(name, arguments, **kwargs)
                if name == TOOL and arguments.get("mode") == "run_native":
                    proof["native_tool_outcome"] = deepcopy(outcome)
                    _checkpoint(store, proof, output)
                    if outcome["status"] != "completed":
                        raise UnexpectedPlacementFeedback("Original native outcome preserved; positive branch unverified: "
                            + json.dumps(outcome.get("feedback"), sort_keys=True))
                    source = store.get(outcome["result"]["source_ref"])
                    control = json.loads(get_artifact(store, source["request_ref"]))
                    proof["native_body_refs"] = [*proof["operand_file_refs"], control["source_files"]["capture"]["file"]["artifact_ref"]]
                    before = _tables(store)
                    active["cache"] = True
                    try:
                        cached = await execute(name, arguments, **kwargs)
                    finally:
                        active["cache"] = False
                    assert cached == outcome and _tables(store) == before
                    proof["cache_checks"].append(dict(operation_key=kwargs["operation_key"],
                        same_tool_operation=True, all_rows_unchanged=True, new_native_attempts=0))
                    _checkpoint(store, proof, output)
                return outcome
            with monkeypatch.context() as measured:
                measured.setattr(ordinary, "prepare_ordinary_molecular_sequence_attempt", prepare_once)
                measured.setattr(host, "_observe_original", observe_once)
                measured.setattr(science, "calculate_primer_placement_components", saved_once)
                measured.setattr(registry, "execute_async", execute_with_same_key_cache)
                measured.setattr(registry, "_prepare_molecular_sequence_operand", checked_freeze)
                measured.setattr(Store, "get_artifact", retained_get)
                measured.setattr(MolecularSequenceResults, "_ordinary_value", checked_value)
                measured.setattr(Path, "open", checked_open)
                measured.setattr(PublicClients, "_http", _forbidden)
                root = workflow.build("annotation", "root", QUESTION, proof["scope"])
                try:
                    _checkpoint(store, proof, output)
                    completed = asyncio.run(root.run_async(workflow.context))
                    proof.update(phase="workflow_returned", archive=_archive_value(completed),
                        provider_cleanup_callbacks=provider.cleanup)
                    _checkpoint(store, proof, output)
                finally:
                    _checkpoint(store, proof, output)
            proof["delivery"] = _verify(store, workflow, registry, proof)
            proof.update(native_custody_verified=True, typed_delivery_verified=True)
            assert len(proof["native_attempts"]) == len(proof["saved_calculator_calls"]) == len(proof["cache_checks"]) == 1
            assert proof["saved_calculator_calls"][0]["phase"] == "returned"
            proof["final_result"] = _archive_value(asyncio.run(root.build_result(completed)))
            assert proof["final_result"] == dict(credit=0, pending_handles=[])
            _checkpoint(store, proof, output)
            proof["replay"] = _closed_receiver(store, case / "run", proof, proof["delivery"]["returned"]["placements"], monkeypatch)
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
