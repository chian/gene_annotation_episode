"""Opt-in MUSCLE alignment and retained returns through their actual owner.

The choices and supplied comparison are engineering inputs. Native bytes,
ordinary action custody, the existing neutral calculator, typed delivery and
closed reconstruction remain real. Retained checks preserve earlier producers
and histories and never repeat the native alignment.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

from method_loop import EpisodeView
import pytest

from gene_annotation_episode import muscle_alignment_driver as native
from gene_annotation_episode import native_atac_differential_driver as native_storage
from gene_annotation_episode import native_flux_balance_storage as storage
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode import phylogeny_calculators as science
from gene_annotation_episode import phylogeny_formats as formats
from gene_annotation_episode import protein_conservation_result_contracts as contracts
from gene_annotation_episode import protein_conservation_result_worker as result_worker
from gene_annotation_episode import protein_conservation_tools as host
from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.evidence_axis_instructions import instruction_view
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import DecisionSource, ReturnedActionUnit
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from tests.test_homer_motif_saved_workflow import _archive, _archive_value, _encode
from tests.test_tf_binding_tools import (
    POLICY, PUBLICATION, ROOT, _assemble, _history, _inventory, _pin,
    _sqlite_pins, _tables, _write,
)


TOOL, FACT = contracts.TOOL, contracts.FACT_SOURCE
PARAMETERS = dict(threads=1, randseed=1, perturb=0, perm="none", consiters=2, refineiters=100)
RAW_FASTA = (b">first full header\r\nacD.-eFGH\r\n"
    b">second descriptive label\r\nAcDeYGH\r\n"
    b">fourth full header\r\nacdEFgH\r\n"
    b">third\r\nACDEFGH\r\n")
MALFORMED_NATIVE_INPUT = (b">dup full header\r\nacD.-eFGH\r\n"
    b">second descriptive label\r\nAcDeYGH\r\n"
    b">dup full header\r\nacdEFgH\r\n"
    b">third\r\nACDEFGH\r\n")
QUESTION = (
    "For the supplied protein FASTA comparison, which aligned symbols and literal-site "
    "conservation values are observed for the complete retained output matrix and for "
    "the declared output-row subset [2, 0] and columns [2, 0, 1]? Preserve the raw input "
    "identity, full-header occurrence associations, native execution/capture/parser "
    "qualifications, and the selected member/site denominators independently of returned "
    "view windows. Include the requested distinct and empty retained views. This supplied "
    "comparison establishes no genomic context, biological function probability, "
    "phylogeny or experimental validation."
)


def _forbidden(*args, **kwargs):
    raise AssertionError("conservation retained phase attempted new native/parser/calculator/tool/body/network work")


def _selection(rows=None, sites=None):
    return dict(version=contracts.SELECTION_VERSION,
        native_rows=dict(row_indices=deepcopy(rows), offset=0, limit=100),
        sites=dict(columns_0based=deepcopy(sites), offset=0, limit=100))


def _form():
    return obj(dict(conservation=contracts.conservation_fact_sources()[FACT]["report_schema"]))


def _checkpoint(store, proof, output):
    history = _history(store, proof["run_id"])
    proof["journal_checkpoint"] = {name: dict(count=len(rows), sha256=digest(rows))
        for name, rows in history.items()}
    proof["table_checkpoint_sha256"] = digest(_tables(store))
    _write(output, proof)


def _integrity_inventory(directory, active):
    previous = active.get("integrity_read", False)
    active["integrity_read"] = True
    try:
        return _inventory(directory)
    finally:
        active["integrity_read"] = previous


def _document(store, file):
    raw = store.get_artifact(file["artifact_ref"])
    assert len(raw) == file["size_bytes"] and hashlib.sha256(raw).hexdigest() == file["sha256"]
    return json.loads(raw)


def _source_control(store, reference):
    source = store.get(reference)
    assert source["record_type"] == "source" and source["provider"] == TOOL
    assert source["version"] == contracts.SOURCE_VERSION
    control = json.loads(store.get_artifact(source["request_ref"]))
    assert control["version"] == "ordinary_protein_conservation_publication_v1"
    return source, control


class UnexpectedConservationFeedback(RuntimeError):
    pass


class _Choices:
    def __init__(self, store, library, proof, output, active):
        self.store, self.library, self.proof, self.output, self.active = store, library, proof, output, active
        self.connection = object.__new__(_SessionConnection)
        self.connection.scientific_prompt_states = {}
        self.states, self.cleanup, self.workflow = {}, [], None

    async def complete(self, episode_id, role, instructions, context, schema):
        context = plain(context)
        if context.get("feedback") and not self.proof.get("partial_native_output"):
            self.proof["unexpected_feedback"] = deepcopy(context["feedback"])
            _checkpoint(self.store, self.proof, self.output)
            raise UnexpectedConservationFeedback(json.dumps(context["feedback"], sort_keys=True))
        episode = self.store.db.execute("SELECT path FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (self.proof["run_id"], episode_id)).fetchone()
        pending, = self.store.db.execute("SELECT call_index FROM runtime_model_calls WHERE run_id=? "
            "AND episode_id=? AND purpose='decision' AND response IS NULL ORDER BY call_index",
            (self.proof["run_id"], episode_id)).fetchall()
        grain, turn = json.loads(episode["path"])[-1][0], pending["call_index"] + 1
        assert role == "REASONING" and context["goal"]["objective"] == QUESTION
        wire, shown = self.connection._presentation(episode_id, role, instructions,
            state_frame(context, self.states.get(episode_id)))
        self.states[episode_id] = deepcopy(context)
        call = dict(episode_id=episode_id, grain=grain, turn=turn,
            context_sha256=digest(context), instructions=plain(instructions), schema_sha256=digest(schema),
            wire=wire, wire_instructions=plain(shown), wire_sha256=hashlib.sha256(wire.encode()).hexdigest())
        self.proof["calls"].append(call)
        if grain == "annotation":
            assert turn == 1
            selected = dict(kind="episode_child", role="scientific_process", goal=QUESTION,
                scope=deepcopy(self.proof["scope"]), purpose=QUESTION, schema_json=json.dumps(_form()),
                initial_report_json="{}", assignment=dict(selection=dict(version="scientific_process_selection_v3",
                    evidence_axis=self.library.reference("A101"), thought_pattern=self.library.reference("P01"),
                    child_tool_info=[dict(name=TOOL, resources="local")]),
                    evidence_refs=[], constraints={},
                    context=dict(conservation_request=deepcopy(self.proof["arguments"])) ))
        else:
            assert grain == "scientific_process" and 1 <= turn <= 4
            assert context["requested_form"] == _form()
            process = context["scientific_process"]
            assert process["evidence_axis"] == instruction_view(self.library.resolve(self.library.reference("A101")))
            thought = self.library.resolve(self.library.reference("P01"))
            assert process["thought_pattern"] == {name: deepcopy(thought[name]) for name in
                ("id", "name", "description", "use_when", "live_alternatives", "decision_guidance",
                    "outcome_contingencies", "boundary") if name in thought}
            assert process["assignment"]["context"]["conservation_request"] == self.proof["arguments"]
            entry, = [item for item in context["tools"] if item["name"] == TOOL]
            assert entry["resources"] == "local"
            assert wire.startswith("TASK\n") and "\n\nSTEERING\n" in wire and QUESTION in wire
            assert self.proof["selected_tool_contract"]["instructions"] in wire
            assert self.proof["case_directory"] not in wire
            assert self.proof["selected_software"]["path"] not in wire
            previous = [json.loads(row["result"]) for row in self.store.db.execute(
                "SELECT result FROM tool_operations WHERE substr(operation_key,1,?)=? ORDER BY rowid",
                (len(self.proof["run_id"]) + 1, self.proof["run_id"] + ":"))]
            if turn == 1:
                assert previous == []
                records = EpisodeReturnRecords(self.store, self.proof["run_id"], failure_prefix="conservation_test_")
                current = records.context(episode_id)
                changes = self.store.db.total_changes
                with pytest.MonkeyPatch.context() as metadata_only:
                    metadata_only.setattr(Store, "get_artifact", _forbidden)
                    item = self.workflow.services.read_received_molecular_file_metadata(current,
                        self.proof["input_file"]["artifact_ref"], "artifact", file_format="fasta")
                    assert item["file"] == self.proof["input_file"] and item["byte_verification"] == "unavailable"
                    with pytest.raises(ValueError, match="molecular_sequence_input_reference_not_received"):
                        self.workflow.services.read_received_molecular_file_metadata(current,
                            self.proof["unreceived_file_ref"], "artifact", file_format="fasta")
                assert self.store.db.total_changes == changes
                self.proof["unreceived_operand_denied_before_body_reads"] = True
                arguments = (dict(mode="read_stored", result_ref=self.proof["retained_source_ref"],
                    selection=_selection()) if "retained_source_ref" in self.proof
                    else deepcopy(self.proof["arguments"]))
            else:
                assert len(previous) == turn - 1
                public = contracts.validate_conservation_return(context["last_local_outcome"]["result"])
                assert public == previous[-1]["result"]
                assert public["source_ref"] in wire and "literal" in wire.lower()
                assert all(reference not in wire for reference in self.proof["private_refs"])
                if self.proof.get("partial_native_output"):
                    assert public["context"]["native_execution"]["parser_status"] == "partial"
                    assert public["context"]["population_resolution"]["state"] == "unresolved"
                    assert public["context"]["population"] is None
                    arguments = dict(mode="read_stored", result_ref=public["source_ref"],
                        selection=_selection(([1], [3, 1], [])[turn - 2], []))
                elif turn == 2:
                    assert public["context"]["native_execution"]["state"] == "completed"
                    assert public["context"]["native_execution"]["parser_status"] == "ok"
                    assert public["context"]["population_resolution"]["state"] == "resolved"
                    arguments = dict(mode="calculate_saved", result_ref=public["source_ref"],
                        population_request=dict(kind="explicit_output_indices", label="declared-output-subset",
                            row_indices=[2, 0], columns_0based=[2, 0, 1], completeness="complete"),
                        selection=_selection([2, 0], [2, 0]))
                elif turn == 3:
                    arguments = dict(mode="read_stored", result_ref=public["source_ref"], selection=_selection([3, 1], [1]))
                else:
                    assert public["selection"] == _selection([3, 1], [1])
                    arguments = dict(mode="read_stored", result_ref=previous[0]["result"]["source_ref"],
                        selection=_selection([], []))
            self.active["turn"] = turn
            selected = dict(kind="tool", tool=TOOL, arguments=arguments)
        response = _encode(dict(selection=selected, report_update={}), schema)
        call["response"] = deepcopy(response)
        self.proof["phase"] = "decision_selected"
        _checkpoint(self.store, self.proof, self.output)
        return response

    async def release(self, episode_id):
        self.cleanup.append(episode_id)


def _literal_values(public, alignment, population, components):
    """Select retained records literally; do not count symbols or divide values."""
    public = contracts.validate_conservation_return(public)
    selection, context = public["selection"], public["context"]
    selected_rows = selection["native_rows"]["row_indices"]
    if selected_rows is None:
        selected_rows = list(range(len(alignment["rows"])))
    selected_sites = selection["sites"]["columns_0based"]
    if selected_sites is None:
        selected_sites = population["columns_0based"]
    page = lambda values, window: values[window["offset"]:window["offset"] + window["limit"]]
    rows = page(selected_rows, selection["native_rows"])
    columns = page(selected_sites, selection["sites"])
    by_column = {row["column_0based"]: row for row in components["sites"]}
    assert public["native_rows"] == [alignment["rows"][index] for index in rows]
    assert public["sites"] == [by_column[index] for index in columns]
    assert context["alignment"] == {key: value for key, value in alignment.items() if key != "rows"}
    assert context["population"] == population
    for field in ("convention", "ordered_source_row_indices", "member_count", "site_count", "threshold", "display"):
        assert context[field] == components[field]
    assert context["components_version"] == components["version"]
    for name, retained, selected, returned in (("native_rows", len(alignment["rows"]), selected_rows, rows),
            ("sites", len(components["sites"]), selected_sites, columns)):
        assert public["accounting"][name] == dict(retained_record_count=retained,
            selected_record_count=len(selected), returned_record_count=len(returned),
            omitted_record_count=len(selected) - len(returned))


def _full_header_associations(context, alignment):
    original = context["input"]
    assert original["capture"]["state"] == "complete" and original["records_state"] == "available"
    assert [row["header"] for row in original["records"]] == [
        "first full header", "second descriptive label", "fourth full header", "third"]
    by_header, output_counts = {}, {}
    for record in original["records"]:
        by_header.setdefault(record["header"], []).append(record["record_ordinal"])
    for row in alignment["rows"]:
        output_counts[row["raw_header"]] = output_counts.get(row["raw_header"], 0) + 1
    seen = set()
    by_output_index = {row["row_index"]: row for row in alignment["rows"]}
    assert [row["output_row_index"] for row in context["row_associations"]["rows"]] == list(by_output_index)
    for association in context["row_associations"]["rows"]:
        row = by_output_index[association["output_row_index"]]
        candidates = by_header.get(row["raw_header"], [])
        assert association["output_row_index"] == row["row_index"]
        assert association["input_record_ordinals"] == candidates
        assert association["state"] == ("unmatched_output_label" if not candidates else
            "ambiguous_label_match" if len(candidates) > 1 or output_counts[row["raw_header"]] > 1 else "unique_label_match")
        seen.update(candidates)
    assert context["row_associations"]["unmatched_input_record_ordinals"] == [
        row["record_ordinal"] for row in original["records"] if row["record_ordinal"] not in seen]
    return dict(full_header_only=True, output_rows=len(alignment["rows"]),
        actual_associations=context["row_associations"], input_order_or_member_label_zip_used=False)


def _worker_files(store, worker, output, *, operation):
    assert set(worker) == {"request", "selection", "handle", "observation", "native_request", "native_request_raw", "result_sha256"}
    selected, handle, observed = worker["selection"], worker["handle"], worker["observation"]
    assert observed["terminal"] is observed["quiescent"] is True
    assert observed["metadata"]["native_returncode"] == 0
    assert selected["request"] == dict(operation=operation, arguments=dict(request=worker["request"]))
    assert selected["command"] == handle["command"]
    assert selected["cwd"] == handle["cwd"]
    directory = Path(selected["cwd"])
    module = {"protein_conservation_native": "muscle_alignment_driver",
        "protein_conservation_result": "protein_conservation_result_worker"}[operation]
    assert selected["command"] == [selected["python"]["path"], "-m", "gene_annotation_episode." + module,
        str(directory / "worker-request.json"), str(directory / "worker-result.json")]
    assert selected["policy"] == observed["metadata"]["policy"] == POLICY
    assert hashlib.sha256(worker["native_request_raw"].encode()).hexdigest() == handle["request_sha256"]
    assert json.loads(worker["native_request_raw"]) == worker["native_request"]
    assert worker["result_sha256"] == digest(output)
    return dict(command=selected["command"], cwd=selected["cwd"], handle=handle,
        observation=observed, selected_request_sha256=digest(selected["request"]),
        implementation_file_count=len(selected["implementation_files"]), output_sha256=digest(output))


def _custody_and_values(store, workflow, proof, values):
    publications = [_source_control(store, value["source_ref"]) for value in values[:2]]
    (original_source, original), (saved_source, saved) = publications
    assert original_source["id"] != saved_source["id"]
    assert saved_source["parent_source_refs"] == [original_source["id"]]
    capture_ref = original["capture_source"]["source_ref"]
    capture = store.get(capture_ref)
    assert original_source["parent_source_refs"] == [capture_ref]
    assert original["capture_source"]["record_sha256"] == digest(capture)
    assert saved["capture_source"] == original["capture_source"]
    assert saved["original_source"] == dict(source_ref=original_source["id"], record_sha256=digest(original_source))
    assert original["original_source"] is None
    capture_control = json.loads(store.get_artifact(capture["request_ref"]))
    assert capture_control["version"] == "ordinary_protein_conservation_native_capture_control_v1"
    assert capture["parent_source_refs"] == []
    assert capture_control["invocation"] == original["invocation"]
    operations = _history(store, proof["run_id"])["tool_operations"]
    assert original["invocation"]["operation_key"] == proof.get(
        "retained_native_operation_key", operations[0]["operation_key"])
    assert saved["invocation"]["operation_key"] == operations[1]["operation_key"]
    native_capture = json.loads(store.get_artifact(capture_control["manifest_ref"]))
    assert native_capture["version"] == "ordinary_protein_conservation_native_capture_v1"
    original_calls = proof.get("original_worker_calls", proof["worker_calls"])
    native_calls = [row for row in original_calls if row["operation"] == "protein_conservation_native"]
    assert len(native_calls) == 1
    manifest = native_calls[0]["result"]
    assert native_capture["original_manifest"] == manifest
    assert native_capture["invocation"] == original["invocation"]
    assert manifest["request"] == capture_control["native_request"]
    native_worker_audit = _worker_files(store, capture_control["native_worker"], manifest,
        operation="protein_conservation_native")
    assert manifest["request"]["software"] == proof["selected_software"]
    assert manifest["request"]["parameters"] == proof["selected_parameters"]
    assert manifest["returncode"] == 0
    assert manifest["argv"] == native.muscle_alignment_native_argv(manifest["request"])
    assert manifest["issues"] == []
    native_directory = Path(native_calls[0]["output_path"]).parent
    outputs = {row["relative_path"]: row for row in native_capture["outputs"]}
    native_files = {}
    for declaration in manifest["files"]:
        path = native_directory / declaration["relative_path"]
        pin = _pin(path)
        assert {key: pin[key] for key in ("sha256", "size_bytes")} == {
            key: declaration[key] for key in ("sha256", "size_bytes")}
        retained = outputs[declaration["relative_path"]]
        assert retained["declared"] == declaration and retained["file"] is not None
        file = retained["file"]
        raw = store.get_artifact(file["artifact_ref"])
        assert len(raw) == file["size_bytes"] == declaration["size_bytes"]
        assert hashlib.sha256(raw).hexdigest() == file["sha256"] == declaration["sha256"]
        assert raw == path.read_bytes()
        native_files[declaration["role"]] = file
    assert store.get_artifact(native_files["input"]["artifact_ref"]) == RAW_FASTA
    assert native_files["input"]["artifact_ref"] == proof["input_file"]["artifact_ref"]
    assert capture["artifact_ref"] == native_files["alignment"]["artifact_ref"]
    assert native_files["alignment"]["format"] == "aligned_fasta"
    assert _pin(proof["selected_software"]["path"]) == proof["selected_software"]
    assert original["input_artifact_refs"] == saved["input_artifact_refs"] == [proof["input_file"]["artifact_ref"]]
    assert capture_control["input_artifact_refs"] == [proof["input_file"]["artifact_ref"]]
    assert original["alignment_file"] == saved["alignment_file"]
    alignment = _document(store, original["alignment_file"])
    assert alignment["artifact"] == dict(raw_artifact_ref=capture["artifact_ref"],
        source_ref=capture_ref, sha256=native_files["alignment"]["sha256"])
    assert len(alignment["rows"]) == 4 and alignment["observed_column_count"] >= 3
    evidence = dict(content=dict(source_ref=capture_ref, artifact_field="artifact_ref",
        artifact_ref=capture["artifact_ref"], sha256=native_files["alignment"]["sha256"],
        byte_count=native_files["alignment"]["size_bytes"]), pointer="")
    contexts, populations, components, worker_audits = [], [], [], []
    result_calls = [row for row in proof["worker_calls"] if row["operation"] == "protein_conservation_result"]
    if "original_worker_calls" in proof:
        first_parse, = [row for row in original_calls if row["operation"] == "protein_conservation_result"
            and row["request"]["mode"] == "parse"]
        result_calls = [first_parse, *result_calls]
    assert [row["request"]["mode"] for row in result_calls] == ["parse", "calculate_saved"]
    for index, (_source, control) in enumerate(publications):
        context = _document(store, control["context_file"])
        population = _document(store, control["population_file"])
        calculated = _document(store, control["components_file"])
        packet = _document(store, control["value_file"])
        assert _source["artifact_ref"] == control["value_file"]["artifact_ref"]
        assert contracts.project_conservation_return(packet, source_ref=_source["id"]) == values[index]
        assert population["evidence"] == [evidence]
        assert context["input"]["file"] == proof["input_file"] and context["input"]["source_ref"] is None
        assert context["native_execution"]["state"] == "completed"
        assert context["native_execution"]["returncode"] == 0
        assert context["native_execution"]["parser_status"] == "ok"
        assert context["native_execution"]["output_capture"]["retained_size_bytes"] == native_files["alignment"]["size_bytes"]
        assert context["native_execution"]["alphabet"]["state"] in ("unknown", "reported")
        worker = control["worker"]
        assert worker["request"] == result_calls[index]["request"]
        result = result_calls[index]["result"]
        worker_audits.append(_worker_files(store, worker, result, operation="protein_conservation_result"))
        for role in ("context", "population", "components", "value"):
            declaration, file = result[role], control[role + "_file"]
            assert file["sha256"] == declaration["sha256"] and file["size_bytes"] == declaration["size_bytes"]
            assert file["format"] == declaration["format"]
        if index == 0:
            request = worker["request"]
            assert request["mode"] == "parse" and request["saved"] is None
            assert request["alignment_file"]["source_ref"] == capture_ref
            assert request["alignment_file"]["file"] == native_files["alignment"]
            assert request["input"]["file"] == proof["input_file"]
            assert request["input"]["source_ref"] is None
            declaration = result["alignment"]
            assert original["alignment_file"] == dict(artifact_ref="artifact_" + declaration["sha256"],
                sha256=declaration["sha256"], size_bytes=declaration["size_bytes"], format=declaration["format"])
        else:
            request = worker["request"]
            assert request["mode"] == "calculate_saved"
            assert request["input"] is request["alignment_file"] is request["native_execution"] is None
            assert request["saved"]["alignment"]["file"] == original["alignment_file"]
            assert request["saved"]["context"]["file"] == original["context_file"]
            assert result["alignment"] is None
        contexts.append(context)
        populations.append(population)
        components.append(calculated)
    assert contexts[0] == contexts[1]
    assert populations[0]["row_indices"] == [0, 1, 2, 3]
    assert populations[1]["row_indices"] == [2, 0] and populations[1]["columns_0based"] == [2, 0, 1]
    assert components[0]["member_count"]["value"] == 4 and components[1]["member_count"]["value"] == 2
    assert components[1]["site_count"]["value"] == 3
    for public, index in zip(values, (0, 1, 1, 0)):
        _literal_values(public, alignment, populations[index], components[index])
    assert values[3]["native_rows"] == values[3]["sites"] == []
    assert values[3]["context"] == values[0]["context"]
    assert values[2]["context"] == values[1]["context"]
    private = {capture_ref, capture["artifact_ref"], capture["request_ref"], *capture["auxiliary_artifact_refs"]}
    for source, control in publications:
        private.update((source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"]))
        assert proof["input_file"]["artifact_ref"] not in source["auxiliary_artifact_refs"]
    private.discard(proof["input_file"]["artifact_ref"])
    assert proof["input_file"]["artifact_ref"] not in capture["auxiliary_artifact_refs"]
    return dict(native_files=native_files, capture_source_ref=capture_ref,
        capture_control_sha256=digest(capture_control), original_manifest=manifest,
        native_worker_audit=native_worker_audit, worker_audits=worker_audits, private_refs=sorted(private),
        original_alignment_file=original["alignment_file"], population_files=[control["population_file"] for _, control in publications],
        component_files=[control["components_file"] for _, control in publications],
        full_header_associations=_full_header_associations(values[0]["context"], alignment),
        literal_component_copies_verified=True, verifier_parser_calls=0, verifier_calculator_calls=0,
        native_alignment_attempts=1, new_native_alignment_attempts=0 if "retained_source_ref" in proof else 1,
        parsed_result_worker_modes=["parse", "calculate_saved"],
        runtime_parser_calculator_counters_not_supplied=True)


def _partial_custody_and_values(store, proof, values):
    """Authenticate the actual current partial and copy its retained values."""
    source, control = _source_control(store, values[0]["source_ref"])
    operations = _history(store, proof["run_id"])["tool_operations"]
    assert control["invocation"]["operation_key"] == operations[0]["operation_key"]
    assert control["original_source"] is None
    assert control["population_file"] is control["components_file"] is None
    capture_ref = control["capture_source"]["source_ref"]
    capture = store.get(capture_ref)
    assert source["parent_source_refs"] == [capture_ref]
    assert control["capture_source"]["record_sha256"] == digest(capture)
    capture_control = json.loads(store.get_artifact(capture["request_ref"]))
    body = json.loads(store.get_artifact(capture_control["manifest_ref"]))
    native_call, = [row for row in proof["worker_calls"]
        if row["operation"] == "protein_conservation_native"]
    parsed_call, = [row for row in proof["worker_calls"]
        if row["operation"] == "protein_conservation_result"]
    manifest = native.validate_muscle_alignment_native_manifest(body["original_manifest"])
    assert manifest == native_call["result"] and manifest["returncode"] == 0
    assert manifest["request"]["software"] == proof["selected_software"]
    assert manifest["request"]["parameters"] == proof["selected_parameters"]
    native_files = {}
    for row in body["outputs"]:
        file, declaration = row["file"], row["declared"]
        assert file is not None and row["qualification"] is None
        raw = store.get_artifact(file["artifact_ref"])
        assert hashlib.sha256(raw).hexdigest() == file["sha256"] == declaration["sha256"]
        assert len(raw) == file["size_bytes"] == declaration["size_bytes"]
        native_files[declaration["role"]] = file
    assert store.get_artifact(native_files["input"]["artifact_ref"]) == MALFORMED_NATIVE_INPUT
    assert b">dup full header\r dupelabel1\n" in store.get_artifact(native_files["alignment"]["artifact_ref"])
    assert capture["artifact_ref"] == native_files["alignment"]["artifact_ref"]
    assert control["input_artifact_refs"] == capture_control["input_artifact_refs"] == [proof["input_file"]["artifact_ref"]]
    assert body["invocation"] == capture_control["invocation"] == control["invocation"]
    native_audit = _worker_files(store, capture_control["native_worker"], manifest,
        operation="protein_conservation_native")
    parser_audit = _worker_files(store, control["worker"], parsed_call["result"],
        operation="protein_conservation_result")
    assert control["worker"]["request"] == parsed_call["request"]
    alignment = _document(store, control["alignment_file"])
    assert alignment["artifact"] == dict(raw_artifact_ref=capture["artifact_ref"],
        source_ref=capture_ref, sha256=native_files["alignment"]["sha256"])
    packet = _document(store, control["value_file"])
    context = packet["context"]
    assert values[0] == dict(packet, source_ref=source["id"])
    assert alignment["observed_row_count"] == len(alignment["rows"]) == 4
    assert alignment["observed_column_count"] is None and alignment["completeness"] == "partial"
    assert alignment["rows"][1]["sequence"] == "dupelabel1ACDEFGH"
    assert context["native_execution"]["state"] == "completed"
    assert context["native_execution"]["returncode"] == 0
    assert context["native_execution"]["parser_status"] == "partial"
    assert context["population_resolution"] == dict(state="unresolved",
        reason_codes=["output_column_dimension_unresolved"])
    assert all(context[field] is None for field in
        ("population", "components_version", "ordered_source_row_indices", "member_count", "site_count"))
    assert {issue["code"] for issue in context["issues"]} == {
        "phylogeny_alignment_whitespace_ignored", "phylogeny_alignment_symbol_invalid",
        "phylogeny_alignment_lengths_unequal"}
    assert [row["input_record_ordinals"] for row in context["row_associations"]["rows"][:2]] == [[0, 2], [0, 2]]
    assert all(row["state"] == "ambiguous_label_match" for row in context["row_associations"]["rows"][:2])
    for value in values:
        assert value["context"] == context and value["source_ref"] == source["id"]
        assert value["sites"] == []
        indices = value["selection"]["native_rows"]["row_indices"]
        indices = list(range(4)) if indices is None else indices
        assert value["native_rows"] == [alignment["rows"][i] for i in indices]
        assert value["accounting"]["native_rows"] == dict(retained_record_count=4,
            selected_record_count=len(indices), returned_record_count=len(indices), omitted_record_count=0)
        explicit_empty = value["selection"]["sites"]["columns_0based"] == []
        assert value["accounting"]["sites"] == dict(retained_record_count=None,
            selected_record_count=0 if explicit_empty else None, returned_record_count=0,
            omitted_record_count=0 if explicit_empty else None)
    assert values[-1]["native_rows"] == []
    return dict(capture_source_ref=capture_ref, private_refs=proof["private_refs"],
        native_worker_audit=native_audit, original_parser_worker_audit=parser_audit,
        original_alignment_file=control["alignment_file"], native_files=native_files,
        new_native_alignment_attempts=1, parser_workers=1, calculation_workers=0,
        native_partial_and_ambiguous_header_associations_preserved=True,
        unknown_population_and_denominators_preserved=True, literal_rows_and_view_counts_verified=True)


def _delivery(store, workflow, registry, proof):
    history = _history(store, proof["run_id"])
    episodes = sorted(history["runtime_episodes"], key=lambda row: len(json.loads(row["path"])))
    assert len(episodes) == 2 and all(row["state"] == "yielded" and row["archive"] for row in episodes)
    assert all(len(history[name]) == 5 for name in ("runtime_actions", "runtime_observations", "runtime_model_calls"))
    operations = history["tool_operations"]
    assert len(operations) == 4 and all(row["name"] == TOOL for row in operations)
    arguments = [json.loads(row["arguments"]) for row in operations]
    retained = "retained_source_ref" in proof
    partial = proof.get("partial_native_output", False)
    assert [row["mode"] for row in arguments] == (["run_native", "read_stored", "read_stored", "read_stored"] if partial else
        ["read_stored" if retained else "run_native", "calculate_saved", "read_stored", "read_stored"])
    assert arguments[0] == (dict(mode="read_stored", result_ref=proof["retained_source_ref"],
        selection=_selection()) if retained else proof["arguments"])
    outcomes = [json.loads(row["result"]) for row in operations]
    assert all(row["status"] == ("partial" if partial else "completed") for row in outcomes)
    values = [contracts.validate_conservation_return(row["result"]) for row in outcomes]
    if partial:
        assert len({row["source_ref"] for row in values}) == 1
    else:
        assert values[0]["source_ref"] == values[3]["source_ref"] != values[1]["source_ref"] == values[2]["source_ref"]
    assert len({(row["source_ref"], canonical(row["selection"])) for row in values}) == 4
    for index, outcome in enumerate(outcomes):
        assert outcome["record_refs"] == [values[index]["source_ref"]]
        assert outcome["changed_record_refs"] == ([values[index]["source_ref"]]
            if index == 0 and not retained or index == 1 and not partial else [])
    records = EpisodeReturnRecords(store, proof["run_id"], failure_prefix="conservation_episode_")
    parent, child = [records.context(row["episode_id"]) for row in episodes]
    expected = dict(conservation=values)
    frozen, = history["runtime_forms"]
    attempt, = history["runtime_report_attempts"]
    assert frozen["episode_id"] == child.episode_id and json.loads(frozen["form"]) == expected
    assert json.loads(frozen["facts"])[FACT] == values
    assert attempt["failure"] is None and json.loads(attempt["form"]) == expected
    assert attempt["parent_episode_id"] == parent.episode_id and attempt["child_episode_id"] == child.episode_id
    assert workflow.services.molecular_own_facts(child, fact_source=FACT) == values
    assert workflow.services.molecular_frozen_facts(child, fact_source=FACT) == values
    assert workflow.services.molecular_received_facts(parent, fact_source=FACT) == values
    archives = [_archive(row, workflow.directory) for row in episodes]
    assert [row["units_consumed"] for row in archives] == [1, 4]
    assert archives[0]["units"][0]["child_result"] == dict(form=expected)
    custody = (_partial_custody_and_values(store, proof, values) if partial else
        _custody_and_values(store, workflow, proof, values))
    private = set(custody["private_refs"])
    admission_checks = []
    for context in (parent, child):
        known = set(workflow.receipts.known(context.episode_id))
        assert {proof["input_file"]["artifact_ref"], *(row["source_ref"] for row in values)} <= known
        assert private.isdisjoint(known)
        resolver = workflow.resolver(plain(context.scope), context=context)
        assert all(resolver(ref, "source" if ref == custody["capture_source_ref"] else "artifact") is False for ref in private)
        before = _tables(store)
        with pytest.MonkeyPatch.context() as guard:
            guard.setattr(Store, "get_artifact", _forbidden)
            admitted = workflow.services.read_received_molecular_file_metadata(context,
                proof["input_file"]["artifact_ref"], "artifact", file_format="fasta")
            assert admitted["file"] == proof["input_file"] and admitted["byte_verification"] == "unavailable"
            for public in values[:1 if partial else 2]:
                received = workflow.services.read_received_molecular_input(context, public["source_ref"], "source", source_metadata_only=True)
                assert received["failure"] is None and received["input"]["witness"]["reference"] == public["source_ref"]
            denied = workflow.services.read_received_molecular_input(context, custody["capture_source_ref"], "source", source_metadata_only=True)
            assert denied["failure"] is not None and denied["input"] is None
            for ref in sorted(private - {custody["capture_source_ref"]}):
                with pytest.raises(ValueError):
                    workflow.services.read_received_molecular_file_metadata(context, ref, "artifact", file_format="binary")
        assert _tables(store) == before and set(workflow.receipts.known(context.episode_id)) == known
        for public in values[:1 if partial else 2]:
            assert host.read_retained_protein_conservation_publication(registry, context,
                workflow.services.read_received_molecular_input, public["source_ref"]) == public
        admission_checks.append(dict(episode_id=context.episode_id, original_file_admitted=True,
            public_source_metadata_admitted=True, private_source_and_files_denied=True, new_receipts=0))
    assert records._received_before(child.episode_id, proof["input_file"]["artifact_ref"], 0)
    assert records._received_before(child.episode_id, values[0]["source_ref"], 0) is retained
    assert records._received_before(child.episode_id, values[0]["source_ref"], 1)
    assert records._received_before(child.episode_id, values[1]["source_ref"], 1) is partial
    assert records._received_before(child.episode_id, values[1]["source_ref"], 2)
    return dict(returned=expected, outcomes=outcomes, custody=custody,
        admission_checks=admission_checks, original_action_cutoffs_verified=True,
        own_frozen_received_equal=True, source_and_selection_group_count=4,
        top_source_only_grants=True, original_input_grant_preserved=True)


class _NoDecisions:
    def __init__(self):
        self.cleanup = []

    async def complete(self, *args, **kwargs):
        _forbidden()

    async def release(self, episode_id):
        self.cleanup.append(episode_id)


def _closed_receiver(store, directory, proof, monkeypatch):
    before_tables, before_files = _tables(store), _inventory(directory)
    before_artifacts = _inventory(store.path / "artifacts")
    before_cache = _inventory(store.path / "cache")
    episodes = sorted(_history(store, proof["run_id"])["runtime_episodes"], key=lambda row: len(json.loads(row["path"])))
    parent_archive, child_archive = [_archive(row, directory) for row in episodes]
    expected = proof["delivery"]["returned"]
    public_files = {store.get(row["source_ref"])["artifact_ref"] for row in expected["conservation"]}
    actual_get, provider, receiver = Store.get_artifact, _NoDecisions(), {}
    with monkeypatch.context() as guard:
        for module, names in ((native, ("run_muscle_alignment_native",)),
                (formats, ("parse_aligned_fasta",)), (science, ("literal_site_conservation",)),
                (result_worker, ("run_protein_conservation_result", "parse_aligned_fasta", "literal_site_conservation")),
                (native_lifecycle, ("prepare_job", "start_prepared", "resume_start", "status", "wait_job", "collect", "cancel", "release"))):
            for name in names:
                guard.setattr(module, name, _forbidden)
        guard.setattr(ToolRegistry, "execute_async", _forbidden)
        guard.setattr(ToolRegistry, "_sequence_worker_async", _forbidden)
        guard.setattr(PublicClients, "_http", _forbidden)
        guard.setattr(Store, "get_artifact", _forbidden)
        workflow, _registry = _assemble(store, directory, proof, provider)
        root = workflow.build("annotation", "root", QUESTION, proof["scope"])
        record = asyncio.run(root.run_async(workflow.context))
        assert _archive_value(record) == parent_archive
        assert _archive_value(asyncio.run(root.build_result(record))) == dict(credit=0, pending_handles=[])
        original = workflow.journal.row("runtime_actions", root.source.episode_id, 0)
        returned = workflow.selected(root.source, json.loads(original["action"]), 0)
        assert isinstance(returned, ReturnedActionUnit)
        assert _archive_value(returned.record) == child_archive and plain(returned.result.as_record()) == dict(form=expected)
        scope = workflow.context.enter(root.grain, root.key)
        try:
            view = EpisodeView(grain=root.grain, key=root.key, path=scope, units_consumed=record.units_consumed,
                updates=tuple(workflow.context._child_updates.get(scope, ())), controller_state=record.controller_state,
                episode_ref=record.episode_ref, request=record.request)
            assert _archive_value(view.controller_state) == parent_archive["controller_state"]
            def public_only(current, reference):
                assert reference in public_files
                return actual_get(current, reference)
            class ReceiverCaptured(BaseException):
                pass
            async def capture(source, context, schema):
                assert plain(context["child_reports"]) == [expected]
                connection = object.__new__(_SessionConnection)
                connection.scientific_prompt_states = {}
                with guard.context() as no_bytes:
                    no_bytes.setattr(Store, "get_artifact", _forbidden)
                    wire, instructions = connection._presentation(source.episode_id, "REASONING", source.instructions(context),
                        state_frame(plain(context)))
                assert all(row["source_ref"] in wire for row in expected["conservation"])
                assert "literal" in wire.lower() and "denominator" in wire.lower()
                assert all(ref not in wire for ref in proof["delivery"]["custody"]["private_refs"])
                assert proof["case_directory"] not in wire
                assert proof["selected_software"]["path"] not in wire
                receiver.update(context_sha256=digest(plain(context)), wire=wire, instructions=plain(instructions),
                    current_receiver_reconstruction=True, historical_post_return_decision_claimed=False,
                    empty_view_context=deepcopy(expected["conservation"][-1]["context"]))
                raise ReceiverCaptured()
            guard.setattr(Store, "get_artifact", public_only)
            guard.setattr(DecisionSource, "call", capture)
            calls = root.source.calls
            with pytest.raises(ReceiverCaptured):
                asyncio.run(root.source.next(view))
            assert root.source.calls == calls
        finally:
            workflow.context.leave(scope)
    assert _tables(store) == before_tables and _inventory(directory) == before_files
    assert _inventory(store.path / "artifacts") == before_artifacts
    assert _inventory(store.path / "cache") == before_cache
    return dict(all_rows_unchanged=True, files_and_modes_unchanged=True, new_provider_decisions=0,
        provider_cleanup_callbacks=provider.cleanup, new_tool_actions=0, new_native_attempts=0,
        new_parser_calls=0, new_calculations=0, closed_replay_verified=True,
        no_Store_get_artifact_calls_during_closed_replay=True,
        receiver_fact_reads_only_public_packets=True, integrity_inventory_reads_performed=True, receiver=receiver)




def _exercise_conservation_workflow(tmp_path, monkeypatch, *, retained=False, partial=False):
    assert not (partial and retained)
    gate = os.environ.get("HMMER_NATIVE_ORACLE_MUSCLE_CONSERVATION_PARTIAL_NATIVE_JSON" if partial else
        "HMMER_NATIVE_ORACLE_MUSCLE_CONSERVATION_RETAINED_JSON" if retained else
        "HMMER_NATIVE_ORACLE_MUSCLE_CONSERVATION_JSON")
    if gate is None:
        pytest.skip("requires one explicitly selected current physical MUSCLE pin and native profile")
    selected = json.loads(gate)
    original = None
    if retained:
        assert type(selected) is dict and set(selected) == {"attempt_id", "proof"}
        supplied = selected["proof"]
        assert type(supplied) is dict and set(supplied) == {"path", "sha256", "size_bytes"}
        assert _pin(supplied["path"]) == supplied
        original = json.loads(Path(supplied["path"]).read_bytes())
        assert original["native_alignment_attempts"] == 1 and len(original["worker_calls"]) == 3
        assert original["phase"] == "workflow_returned" and original["failure"]["exception_type"] == "AssertionError"
        original_proof_pin = deepcopy(supplied)
        selected = dict(attempt_id=selected["attempt_id"], software=original["selected_software"],
            parameters=original["selected_parameters"])
    assert type(selected) is dict and set(selected) == {"attempt_id", "software", "parameters"}
    attempt = selected["attempt_id"]
    assert type(attempt) is str and attempt and Path(attempt).name == attempt and attempt not in (".", "..")
    software = native.validate_muscle_alignment_software(selected["software"])
    parameters = native.validate_muscle_alignment_parameters(selected["parameters"])
    assert parameters == PARAMETERS
    if not retained:
        assert _pin(software["path"]) == software
    case = tmp_path / ("muscle-conservation-" + attempt)
    case.mkdir()
    output = case / "PROTEIN_CONSERVATION_WORKFLOW.json"
    proof = dict(version="ordinary_protein_conservation_workflow_v1", run_id="ordinary-conservation-" + attempt,
        case_directory=str(case), store_directory=str(case / "store"), workflow_directory=str(case / "run"),
        question=QUESTION, selected_software=software, selected_parameters=parameters, calls=[], worker_calls=[],
        cache_checks=[], private_refs=[], protected_body_refs=[], protected_body_paths=[], phase="prepared", passed=False,
        scripted_model_decisions=True, external_model_calls=0, native_alignment_attempts=None,
        qualification="One new selected MUSCLE alignment; observed output populations and literal conservation only, no prior producer restoration or biological validation.")
    _write(output, proof)
    if retained:
        proof.update(version="ordinary_protein_conservation_retained_workflow_v1",
            store_directory=original["store_directory"], original_proof=original_proof_pin,
            original_run_id=original["run_id"], original_worker_calls=deepcopy(original["worker_calls"]),
            native_alignment_attempts=0, private_refs=deepcopy(original["private_refs"]),
            protected_body_refs=deepcopy(original["protected_body_refs"]),
            protected_body_paths=deepcopy(original["protected_body_paths"]),
            qualification="New actual receiver over an unchanged genuine earlier native Source; one saved calculation, no native repeat, old receipts/history preserved.")
    if partial:
        proof.update(partial_native_output=True,
            qualification="New genuine malformed-input MUSCLE attempt under current ownership and receipts; capture/parser/unknown-population states remain distinct from native process success, with no saved calculation.")
    active = dict(turn=0, cache=False, integrity_read=False)
    try:
        raw_input = MALFORMED_NATIVE_INPUT if partial else RAW_FASTA
        workspace = case / "native-workspace"
        workspace.mkdir()
        resources = {"selected-conservation": dict(kind="local", workspace=str(workspace), policy=deepcopy(POLICY))}
        environment = dict(version="protein_conservation_execution_selection_v1",
            environment_realization="operation_scoped_tmp_and_cache_v1", software=software, parameters=parameters)
        factory = ExecutionServiceFactory(resources, {}, 2, .25, .5,
            protein_conservation_environments=[dict(operation=TOOL, resource_id="selected-conservation", environment=environment)],
            protein_conservation_saved_modes=True)
        if retained:
            factory = ExecutionServiceFactory.from_record(original["factory"])
        assert ExecutionServiceFactory.from_record(factory.as_record()).as_record() == factory.as_record()
        proof["factory"] = factory.as_record()
        with Store(Path(proof["store_directory"])) as store:
            if retained:
                previous_history = _history(store, original["run_id"])
                original_operations = previous_history["tool_operations"]
                assert len(original_operations) == 4
                original_outcome = json.loads(original_operations[0]["result"])
                assert original_outcome["status"] == ("partial" if partial else "completed")
                subject, reference, unreceived = (original["subject_ref"], original["input_file"]["artifact_ref"],
                    original["unreceived_file_ref"])
                proof.update(retained_source_ref=original_outcome["result"]["source_ref"],
                    retained_native_operation_key=original_operations[0]["operation_key"])
            else:
                subject, = store.create_problem(raw_sequence="ACDEFGH", molecule="protein")["subject_refs"]
                reference = store.artifact(raw_input, "text/x-fasta")
                unreceived = store.artifact(b">not received\nACDEFGH\n", "text/x-fasta")
            record = store.get(reference)
            proof.update(subject_ref=subject, scope=store.validate_scope(), unreceived_file_ref=unreceived,
                input_file=dict(artifact_ref=reference, sha256=record["sha256"], size_bytes=record["size"], format="fasta"),
                initial_known_record_refs=[subject, reference], raw_input_sha256=hashlib.sha256(raw_input).hexdigest(),
                arguments=dict(mode="run_native", input=dict(namespace="artifact", reference=reference, format="fasta"),
                    population_request=dict(kind="all_output_rows_and_columns", label="complete-retained-output", completeness="complete"),
                    selection=_selection()))
            if retained:
                assert proof["input_file"] == original["input_file"]
                proof["initial_known_record_refs"].append(proof["retained_source_ref"])
                proof["raw_input_sha256"] = original["input_file"]["sha256"]
            configured = ToolRegistry(store, job_limits=deepcopy(POLICY))
            factory.configure_tool_registry(configured)
            proof["selected_tool_contract"] = configured.catalog()[TOOL]
            assert proof["selected_tool_contract"]["invocation_route"] == dict(kind="direct")
            assert proof["selected_tool_contract"]["resources"] == "local"
            proof["scientific_binding"] = prepare_scientific_binding(run_directory=case / "run",
                source_directory=ROOT / PUBLICATION, tool_catalog=configured.catalog(), child_roles=["scientific_process"])
            library = ScientificProcessLibrary(case / "run/scientific-process-library")
            provider = _Choices(store, library, proof, output, active)
            workflow, registry = _assemble(store, case / "run", proof, provider)
            provider.workflow = workflow
            actual_worker, actual_execute = registry._sequence_worker_async, registry.execute_async
            actual_get, actual_open = Store.get_artifact, Path.open
            actual_regular, actual_native_regular = storage.regular, native_storage._regular
            def protected_path(path):
                if (retained or active["turn"] >= 2 or active["cache"]) and not active["integrity_read"]:
                    assert str(Path(path).absolute()) not in proof["protected_body_paths"]
            def checked_open(path, *args, **kwargs):
                protected_path(path)
                return actual_open(path, *args, **kwargs)
            def checked_regular(path):
                protected_path(path)
                return actual_regular(path)
            def checked_native_regular(path):
                protected_path(path)
                return actual_native_regular(path)
            def checked_get(current, ref):
                if retained or active["turn"] >= 2 or active["cache"]:
                    assert ref not in proof["protected_body_refs"]
                return actual_get(current, ref)
            async def measured_worker(operation, arguments, **kwargs):
                assert not active["cache"] and active["turn"] in (1, 2)
                request = arguments["request"]
                if retained:
                    assert active["turn"] == 2 and operation == "protein_conservation_result"
                    assert request["mode"] == "calculate_saved" and not proof["worker_calls"]
                expected = [(1, "protein_conservation_native", None), (1, "protein_conservation_result", "parse"),
                    (2, "protein_conservation_result", "calculate_saved")]
                index = len(proof["worker_calls"])
                assert retained or index < 3 and (active["turn"], operation, request.get("mode")) == expected[index]
                if active["turn"] == 2:
                    assert request["input"] is request["alignment_file"] is request["native_execution"] is None
                call = dict(turn=active["turn"], operation=operation, request=deepcopy(request),
                    directory=str(kwargs["directory"]), returned=False)
                proof["worker_calls"].append(call)
                _checkpoint(store, proof, output)
                work = await actual_worker(operation, arguments, **kwargs)
                call.update(returned=True, output_path=str(work.output_path), output_pin=None,
                    result=None, metadata=deepcopy(work.metadata))
                proof["phase"] = "worker_returned_before_verifier_decode"
                _checkpoint(store, proof, output)
                if Path(work.output_path).is_file():
                    raw = Path(work.output_path).read_bytes()
                    call["output_pin"] = _pin(work.output_path)
                    call["result"] = json.loads(raw)
                if operation == "protein_conservation_native":
                    manifest = call["result"]
                    proof["protected_body_paths"] = [software["path"], request["input"]["path"]]
                    if manifest is not None and manifest.get("version") == native.MANIFEST_VERSION:
                        native.validate_muscle_alignment_native_manifest(manifest)
                        proof["native_alignment_attempts"] = 1
                        proof["protected_body_paths"].extend(str(Path(work.output_path).parent / row["relative_path"])
                            for row in manifest["files"])
                    proof["phase"] = "original_native_worker_returned"
                else:
                    proof["phase"] = "result_worker_returned"
                _checkpoint(store, proof, output)
                return work
            async def execute_and_check_cache(name, arguments, **kwargs):
                outcome = await actual_execute(name, arguments, **kwargs)
                if name != TOOL:
                    return outcome
                proof["latest_tool_outcome"] = deepcopy(outcome)
                proof["phase"] = "ordinary_action_returned"
                _checkpoint(store, proof, output)
                if outcome["status"] != ("partial" if partial else "completed"):
                    raise UnexpectedConservationFeedback("First actual outcome retained; positive alignment branch unverified: "
                        + json.dumps(outcome.get("feedback"), sort_keys=True))
                if partial:
                    assert outcome["feedback"] == dict(category="representation",
                        code="protein_conservation_selected_result_partial", source_ref=outcome["result"]["source_ref"])
                if arguments["mode"] in ("run_native", "calculate_saved"):
                    source, control = _source_control(store, outcome["result"]["source_ref"])
                    capture = store.get(control["capture_source"]["source_ref"])
                    private = {capture["id"], capture["artifact_ref"], capture["request_ref"], *capture["auxiliary_artifact_refs"],
                        source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"]}
                    private.discard(reference)
                    proof["private_refs"] = sorted(set(proof["private_refs"]) | private)
                    proof["protected_body_refs"] = list(dict.fromkeys([
                        *(proof["protected_body_refs"] if retained else []), reference, capture["artifact_ref"],
                        *[file["artifact_ref"] for file in proof.get("native_output_files", [])]]))
                    if arguments["mode"] == "run_native":
                        cap_control = json.loads(actual_get(store, capture["request_ref"]))
                        capture_manifest = json.loads(actual_get(store, cap_control["manifest_ref"]))
                        proof["native_output_files"] = [row["file"] for row in capture_manifest["outputs"] if row["file"] is not None]
                        proof["protected_body_refs"] = list(dict.fromkeys([reference,
                            *(file["artifact_ref"] for file in proof["native_output_files"])]))
                    proof["protected_body_paths"] = list(dict.fromkeys([
                        *proof["protected_body_paths"], *(str(store.path / "artifacts" / ref[9:11] / ref[9:])
                            for ref in proof["protected_body_refs"])]))
                    before_tables = _tables(store)
                    before_files = _integrity_inventory(case / "run", active)
                    before_artifacts = _integrity_inventory(store.path / "artifacts", active)
                    before_cache = _integrity_inventory(store.path / "cache", active)
                    public_packet_reads = []
                    def cached_public_packet(current, ref):
                        assert ref == source["artifact_ref"]
                        public_packet_reads.append(ref)
                        return actual_get(current, ref)
                    active["cache"] = True
                    try:
                        with monkeypatch.context() as cached:
                            cached.setattr(registry, "_sequence_worker_async", _forbidden)
                            cached.setattr(Store, "get_artifact", cached_public_packet)
                            answer = await actual_execute(name, arguments, **kwargs)
                    finally:
                        active["cache"] = False
                    assert answer == outcome and _tables(store) == before_tables
                    assert _integrity_inventory(case / "run", active) == before_files
                    assert _integrity_inventory(store.path / "artifacts", active) == before_artifacts
                    assert _integrity_inventory(store.path / "cache", active) == before_cache
                    assert public_packet_reads == [source["artifact_ref"]]
                    proof["cache_checks"].append(dict(operation_key=kwargs["operation_key"], same_outcome=True,
                        all_rows_and_retained_files_unchanged=True, new_native_or_result_workers=0,
                        new_parser_or_calculator_calls=0, Store_get_artifact_calls=1,
                        authenticated_public_packet_reads=1, original_or_private_body_reads=0,
                        integrity_inventory_reads_performed=True))
                    _checkpoint(store, proof, output)
                return outcome
            with monkeypatch.context() as guard:
                guard.setattr(registry, "_sequence_worker_async", measured_worker)
                guard.setattr(registry, "execute_async", execute_and_check_cache)
                guard.setattr(Store, "get_artifact", checked_get)
                guard.setattr(Path, "open", checked_open)
                guard.setattr(storage, "regular", checked_regular)
                guard.setattr(native_storage, "_regular", checked_native_regular)
                guard.setattr(formats, "parse_aligned_fasta", _forbidden)
                guard.setattr(science, "literal_site_conservation", _forbidden)
                guard.setattr(result_worker, "parse_aligned_fasta", _forbidden)
                guard.setattr(result_worker, "literal_site_conservation", _forbidden)
                guard.setattr(PublicClients, "_http", _forbidden)
                root = workflow.build("annotation", "root", QUESTION, proof["scope"])
                try:
                    _checkpoint(store, proof, output)
                    completed = asyncio.run(root.run_async(workflow.context))
                    proof.update(phase="workflow_returned", archive=_archive_value(completed),
                        provider_cleanup_callbacks=provider.cleanup)
                finally:
                    _checkpoint(store, proof, output)
            active["turn"] = 0
            proof["delivery"] = _delivery(store, workflow, registry, proof)
            assert len(proof["worker_calls"]) == (2 if partial else 1 if retained else 3)
            assert all(row["returned"] for row in proof["worker_calls"])
            assert proof["native_alignment_attempts"] == (0 if retained else 1)
            assert len(proof["cache_checks"]) == (1 if partial or retained else 2)
            if retained:
                assert _history(store, original["run_id"]) == previous_history
                assert _pin(original_proof_pin["path"]) == original_proof_pin
                proof.update(original_run_history_unchanged=True, original_proof_unchanged=True)
            assert proof["unreceived_operand_denied_before_body_reads"] is True
            proof["final_result"] = _archive_value(asyncio.run(root.build_result(completed)))
            assert proof["final_result"] == dict(credit=0, pending_handles=[])
            _checkpoint(store, proof, output)
            proof["replay"] = _closed_receiver(store, case / "run", proof, monkeypatch)
            proof.update(phase="verified", passed=True, current_typed_delivery_verified=True,
                literal_components_verified=not partial, literal_partial_value_verified=partial,
                closed_replay_verified=True,
                native_execution_success_distinct_from_capture_parse_population_and_scientific_validity=True)
            _checkpoint(store, proof, output)
    except BaseException as error:
        proof["failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        if (Path(proof["store_directory"]) / "state.sqlite3").is_file():
            proof["sqlite_pins"] = _sqlite_pins(Path(proof["store_directory"]))
            proof["sqlite_pins_sha256"] = digest(proof["sqlite_pins"])
        _write(output, proof)


def test_genuine_current_muscle_alignment_conservation_saved_views_typed_parent_and_closed_replay(tmp_path, monkeypatch):
    _exercise_conservation_workflow(tmp_path, monkeypatch)


def test_retained_genuine_conservation_new_receipts_saved_views_typed_parent_and_closed_replay(tmp_path, monkeypatch):
    _exercise_conservation_workflow(tmp_path, monkeypatch, retained=True)


def test_genuine_current_muscle_malformed_output_partial_typed_parent_and_closed_replay(tmp_path, monkeypatch):
    _exercise_conservation_workflow(tmp_path, monkeypatch, partial=True)
