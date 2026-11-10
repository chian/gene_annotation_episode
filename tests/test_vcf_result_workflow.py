"""Supplied native VCF through ordinary tools and genuine episode returns.

Scripted decisions use the actual provider renderer and controlled wire schema.
This verifies retained-result handling; no variant caller or model RPC runs.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

from jsonschema import Draft202012Validator
from method_loop.episode import ClosedChildUnit
import pytest

from gene_annotation_episode import native_lifecycle
from gene_annotation_episode import vcf_result_measurements as core
from gene_annotation_episode import vcf_result_tools as host
from gene_annotation_episode.communication import plain, validate_form
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate
from gene_annotation_episode.native_file_capture import retained_native_file
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.scientific_process_prompt import _selected_molecular_text, _selected_molecular_view
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = ROOT / "research/slotted_process_library/publications/2026-10-24-001"
NATIVE = Path(__file__).parent / "fixtures/vcf_results/expected.testExposureOfSmithWatermanParameters.M2.gatk4.vcf"
QUESTION = ("For the supplied Mutect2 VCF, what native record, ALT-token and sample-cell populations "
    "and selected reported GT, AD, FAD and AF values are retained? Return the controlled VCF result groups.")
POLICY = dict(memory_bytes=20 * 1024 ** 3, scratch_bytes=4 * 1024 ** 3)
SOURCE = "vcf_result_outcomes"


def _selection(**changes):
    return dict(dict(version="vcf_result_selection_v1", record_ordinals=None, sample_ordinals=None,
        info_keys=None, format_keys=None, offset=0, limit=2), **changes)


def _schema():
    return obj(dict(outcomes=host.vcf_result_fact_sources()[SOURCE]["report_schema"]))


def _zero(*args, **kwargs):
    return 0


def _controller(path, initial):
    horizon = 1 if path[-1][0] == "annotation" else 3
    def estimate(history, parameters, contexts):
        return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= horizon else 1),
            parameters, dict(engineering_fixture="three_explicit_result_operations"))
    return YieldController(str(path), initial, 0, estimate_with_context=estimate)


def _single_saved_result_controller(path, initial):
    """Stable fixture callable used for both execution and reconstruction."""
    def estimate(history, parameters, contexts):
        return YieldEstimate(len(history), NumericBand.exact(0 if history else 1),
            parameters, dict(engineering_fixture="one_explicit_saved_result_read"))
    return YieldController(str(path), initial, 0, estimate_with_context=estimate)


def _tables(store):
    names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: sorted((tuple(row) for row in store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')),
        key=repr) for name in names}


def _forbidden(*args, **kwargs):
    raise AssertionError("supplied VCF result path attempted forbidden native, parser or input work")


def _closed_child(workflow, root, parent, science):
    commission = workflow.journal.row("runtime_actions", parent.episode_id, 0)
    closed = workflow.selected(root.source, json.loads(commission["action"]), 0)
    assert isinstance(closed, ClosedChildUnit)
    assert closed.record.episode_id == science.episode_id and closed.record.path == science.path
    assert plain(closed.request.as_record()) == plain(science.request)
    assert closed.record.archived_record is not None
    return plain(closed.result.as_record())


class VcfProvider:
    def __init__(self, store, library, scope, input_ref, *, result_refs=None, saved_selection=None,
                 question=QUESTION, native_file=NATIVE, analyze_selection=None, derived_selection=None,
                 allow_partial=False):
        self.store, self.library, self.scope, self.input_ref = store, library, scope, input_ref
        self.result_refs = result_refs
        self.saved_selection = saved_selection
        self.question, self.native_file = question, native_file
        self.allow_partial = allow_partial
        self.statuses = ('completed', 'partial') if allow_partial else ('completed',)
        self.analyze_selection = _selection() if analyze_selection is None else deepcopy(analyze_selection)
        self.derived_selection = (dict(_selection(), record_ordinals=[1, 0], sample_ordinals=[0],
            info_keys=["DP", "TLOD"], format_keys=["GT", "AD", "FAD", "AF"], offset=1, limit=1)
            if derived_selection is None else deepcopy(derived_selection))
        self.contexts, self.wire = [], []
        self.connection = object.__new__(_SessionConnection)
        self.connection.scientific_prompt_states = {}

    def outcomes(self):
        return [json.loads(row[0]) for row in self.store.db.execute(
            "SELECT result FROM tool_operations WHERE name=? ORDER BY rowid", (host.TOOL,))]

    async def complete(self, episode_id, role, instructions, context, output_schema):
        index = len(self.contexts)
        self.contexts.append(deepcopy(context))
        rendered, wire_instructions = self.connection._presentation(episode_id, role, instructions, context)
        self.wire.append(dict(rendered=rendered, instructions=wire_instructions))
        assert rendered.startswith("TASK\n") and "STEERING" in rendered and self.question in rendered
        assert context["goal"]["objective"] == self.question
        assert context["feedback"] is None or self.allow_partial
        assert index < (4 if self.result_refs is None else 3 if self.saved_selection is not None else 1 + len(self.result_refs))
        if index == 0:
            selection = dict(kind="episode_child", role="scientific_process", goal=self.question,
                scope=deepcopy(self.scope), purpose="Return the recorded VCF result groups.",
                schema_json=json.dumps(_schema()), initial_report_json="{}",
                assignment=dict(selection=dict(version="scientific_process_selection_v3",
                    evidence_axis=self.library.reference("A101"), thought_pattern=self.library.reference("P01"),
                    child_tool_info=[dict(name=host.TOOL, resources="local")]),
                    evidence_refs=[self.input_ref] if self.result_refs is None else list(self.result_refs),
                    constraints=dict(no_external_acquisition=True),
                    context=dict(supplied_native_result=True)))
        else:
            assert context["requested_form"] == _schema()
            assert "Selected tool: " + host.TOOL + " (local)" in rendered
            if self.saved_selection is not None and index == 1:
                arguments = dict(mode="calculate_saved", result_ref=self.result_refs[0],
                    selection=deepcopy(self.saved_selection))
            elif self.saved_selection is not None:
                derived = self.outcomes()[-1]
                assert derived["status"] in self.statuses, derived
                arguments = dict(mode="read_stored", result_ref=derived["result"]["source_ref"])
            elif self.result_refs is not None:
                arguments = dict(mode="read_stored", result_ref=self.result_refs[index - 1])
            elif index == 1:
                arguments = dict(mode="analyze", namespace="artifact", reference=self.input_ref,
                    max_bytes=self.native_file.stat().st_size, capture_state="complete",
                    original_size_bytes=self.native_file.stat().st_size, selection=deepcopy(self.analyze_selection))
            elif index == 2:
                original, = self.outcomes()
                assert original["status"] in self.statuses, original
                arguments = dict(mode="calculate_saved", result_ref=original["result"]["source_ref"],
                    selection=deepcopy(self.derived_selection))
            else:
                original, derived = self.outcomes()
                assert derived["status"] in self.statuses, derived
                arguments = dict(mode="read_stored", result_ref=derived["result"]["source_ref"])
            Draft202012Validator(host.vcf_result_tool_contract()["input_schema"]).validate(arguments)
            selection = dict(kind="tool", tool=host.TOOL, arguments=arguments)
        response = dict(selection=selection, report_update={})
        branches = [branch for branch in output_schema["properties"]["selection"]["anyOf"]
            if all(selection[key] in branch["properties"].get(key, {}).get("enum", [])
                for key in ("kind", "role", "tool") if key in selection)]
        assert len(branches) == 1
        fields = branches[0]["properties"]
        for key in ("assignment", "arguments"):
            if key in selection and fields[key].get("type") == "string":
                selection[key] = json.dumps(selection[key], allow_nan=False)
        if selection["kind"] == "episode_child":
            for key in fields["scope"]["required"]:
                if key not in selection["scope"]:
                    assert {"type": "null"} in fields["scope"]["properties"][key]["anyOf"]
                    selection["scope"][key] = None
        Draft202012Validator(output_schema).validate(response)
        return response

    async def release(self, episode_id):
        pass


def _saved_workflow(store, directory, run_id, scope, references, factory, *, scientific=None):
    tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
    factory.configure_tool_registry(tools)
    if scientific is None:
        scientific = prepare_scientific_binding(run_directory=directory, source_directory=PUBLICATION,
            tool_catalog=tools.catalog(), child_roles=["scientific_process"])
    library = ScientificProcessLibrary(directory / "scientific-process-library")
    provider = VcfProvider(store, library, scope, None, result_refs=references)
    application = factory(store, run_id=run_id, directory=directory, tool_registry=tools)
    workflow = Workflow(store, tools, provider, directory, run_id, _single_saved_result_controller, _zero,
        project_child_credit=_zero, episode_binding_descriptors=[deepcopy(scientific), *application.episode_binding_descriptors],
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider,
        episode_record_receipts=True, initial_known_record_refs=references)
    return tools, workflow, provider, scientific


def test_supplied_native_vcf_saved_modes_typed_parent_return_and_closed_replay(tmp_path, monkeypatch):
    audit_path = tmp_path / "vcf_workflow_audit.json"
    proof = dict(question=QUESTION, native_input_sha256=hashlib.sha256(NATIVE.read_bytes()).hexdigest(), passed=False,
        calculator_calls=[], parser_calls=[], forbidden_input_attempts=[])
    try:
        with Store(tmp_path / "store") as store:
            subject_file = tmp_path / "subject.fa"
            subject_file.write_text(">supplied_scope\nACGTACGT\n")
            subject, = store.create_problem(subject_file, molecule="dna")["subject_refs"]
            scope = store.validate_scope(dict(subject_refs=[subject]))
            supplied = store.register_material(input_path=NATIVE, name="supplied_native_vcf", use="evidence")
            supplied_source = store.get(supplied["source_ref"])
            input_ref = supplied_source["artifact_ref"]
            workspace = tmp_path / "workspace"
            workspace.mkdir()
            factory = ExecutionServiceFactory({"ordinary": dict(kind="local", workspace=str(workspace),
                policy=deepcopy(POLICY))}, {}, 2, .25, .5)
            tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
            factory.configure_tool_registry(tools)
            scientific = prepare_scientific_binding(run_directory=tmp_path / "run", source_directory=PUBLICATION,
                tool_catalog=tools.catalog(), child_roles=["scientific_process"])
            library = ScientificProcessLibrary(tmp_path / "run/scientific-process-library")
            provider = VcfProvider(store, library, scope, input_ref)
            run_id = "supplied-native-vcf-workflow"
            application = factory(store, run_id=run_id, directory=tmp_path / "run", tool_registry=tools)
            workflow = Workflow(store, tools, provider, tmp_path / "run", run_id, _controller, _zero,
                project_child_credit=_zero, episode_binding_descriptors=[scientific, *application.episode_binding_descriptors],
                role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider,
                episode_record_receipts=True, initial_known_record_refs=[input_ref])
            proof.update(run_id=run_id, store_directory=str(store.path), workflow_directory=str(workflow.directory),
                factory=factory.as_record(), scientific_binding=scientific, scope=scope, input_ref=input_ref,
                supplied_material_ref=supplied["id"], supplied_source_ref=supplied_source["id"])
            root = workflow.build("annotation", "root", QUESTION, scope)
            actual_calculate, actual_parse = core.calculate_vcf_components, core.parse_vcf_sheet
            actual_get = Store.get_artifact
            actual_verified = retained_native_file.__globals__["_verified_artifact_path"]
            def calculate(sheet, selection):
                proof["calculator_calls"].append(deepcopy(selection))
                return actual_calculate(sheet, selection)
            def parse(record):
                proof["parser_calls"].append(record["input_id"])
                return actual_parse(record)
            def get(current, reference, *args, **kwargs):
                # The first parse may read supplied bytes. Saved operations and
                # every later fact/projection boundary must use retained data.
                if reference == input_ref and proof["parser_calls"]:
                    proof["forbidden_input_attempts"].append(reference)
                    raise AssertionError("saved operation reopened the original VCF File")
                return actual_get(current, reference, *args, **kwargs)
            def verified(current, reference, *args, **kwargs):
                if reference == input_ref and proof["parser_calls"]:
                    proof["forbidden_input_attempts"].append(reference)
                    raise AssertionError("saved operation reopened the original VCF File path")
                return actual_verified(current, reference, *args, **kwargs)
            with monkeypatch.context() as patch:
                patch.setattr(core, "calculate_vcf_components", calculate)
                patch.setattr(core, "parse_vcf_sheet", parse)
                patch.setattr(Store, "get_artifact", get)
                patch.setattr("gene_annotation_episode.materials._verified_artifact_path", verified)
                patch.setattr("gene_annotation_episode.native_file_capture._verified_artifact_path", verified)
                patch.setattr("gene_annotation_episode.acquisition.PublicClients._http", _forbidden)
                patch.setattr("socket.create_connection", _forbidden)
                for name in ("prepare_job", "start_prepared", "resume_start", "wait_job", "collect", "status", "cancel", "release"):
                    patch.setattr(native_lifecycle, name, _forbidden)
                completed = asyncio.run(root.run_async(workflow.context))
            assert plain(asyncio.run(root.build_result(completed)).as_record()) == dict(credit=0, pending_handles=[])
            original, derived, read = provider.outcomes()
            assert all(value["status"] == "completed" for value in (original, derived, read))
            assert original["result"]["source_ref"] != derived["result"]["source_ref"]
            assert derived["result"] == read["result"] and read["changed_record_refs"] == []
            assert len(proof["parser_calls"]) == 1 and len(proof["calculator_calls"]) == 2
            assert proof["forbidden_input_attempts"] == []
            records = EpisodeReturnRecords(store, run_id, failure_prefix="vcf_workflow_")
            episodes = list(store.db.execute("SELECT episode_id FROM runtime_episodes WHERE run_id=? ORDER BY json_array_length(path)", (run_id,)))
            assert len(episodes) == 2
            parent, science = [records.context(row[0]) for row in episodes]
            group = [original["result"], derived["result"]]
            assert all(item["value"]["input"]["source_ref"] is None for item in group)
            full_population = group[0]["value"]["population"]
            selected_population = group[1]["value"]["population"]
            assert [full_population[key] for key in ("total_original_record_slots", "retained_record_slots",
                "selected_record_slots", "returned_record_slots")] == [295, 295, 295, 2]
            assert [selected_population[key] for key in ("total_original_record_slots", "retained_record_slots",
                "selected_record_slots", "returned_record_slots")] == [295, 295, 2, 1]
            assert selected_population["returned_record_fraction"] == dict(value=.5, numerator=1, denominator=2,
                unit="fraction", missing_reason=None)
            assert [record["record_ordinal_0based"] for record in group[1]["value"]["records"]] == [0]
            assert all(record["filter"]["state"] == "not_applied" for item in group for record in item["value"]["records"])
            with monkeypatch.context() as patch:
                patch.setattr(core, "calculate_vcf_components", _forbidden)
                patch.setattr(core, "parse_vcf_sheet", _forbidden)
                assert workflow.services.molecular_own_facts(science, fact_source=SOURCE) == group
                assert workflow.services.molecular_frozen_facts(science, fact_source=SOURCE) == group
                assert workflow.services.molecular_received_facts(parent, fact_source=SOURCE) == group
                with patch.context() as display:
                    display.setattr(Store, "get_artifact", _forbidden)
                    view, packets = _selected_molecular_view(dict(outcomes=group))
                    assert len(packets) == 2 and view == dict(outcomes=["Selected molecular result 1", "Selected molecular result 2"])
                    texts = [_selected_molecular_text(packet, number) for number, packet in enumerate(packets, 1)]
                    assert "| selected_record_slots | 295 |" in texts[0]
                    assert "| selected_record_slots | 2 |" in texts[1]
                    assert "| returned_record_slots | 1 |" in texts[1]
                    assert "Native token" in texts[0] and "not_applied" in texts[0]
                    assert not any(item["value"]["input"]["retained_file"]["sha256"] in text for item, text in zip(group, texts))
            forms = list(store.db.execute("SELECT facts,form FROM runtime_forms WHERE run_id=?", (run_id,)))
            assert len(forms) == 1 and json.loads(forms[0][0])[SOURCE] == group
            assert json.loads(forms[0][1]) == dict(outcomes=group)
            attempts = list(store.db.execute("SELECT failure,form FROM runtime_report_attempts WHERE run_id=?", (run_id,)))
            assert len(attempts) == 1 and attempts[0][0] is None and json.loads(attempts[0][1]) == dict(outcomes=group)
            source_records = [store.get(item["source_ref"]) for item in group]
            assert source_records[1]["parent_source_refs"] == [source_records[0]["id"]]
            private = {ref for source in source_records for ref in
                (source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"])}
            for current in (parent, science):
                known = set(workflow.receipts.known(current.episode_id))
                assert {item["source_ref"] for item in group} <= known and private.isdisjoint(known)
            resolved = []
            def resolve(reference, namespace):
                resolved.append((reference, namespace))
                return namespace == "source" and reference in {item["source_ref"] for item in group}
            assert validate_form(dict(outcomes=group), _schema(), resolve) == dict(outcomes=group)
            assert set(resolved) == {(item["source_ref"], "source") for item in group}
            before = _tables(store)
            with monkeypatch.context() as patch:
                patch.setattr(core, "parse_vcf_sheet", _forbidden)
                patch.setattr(core, "calculate_vcf_components", _forbidden)
                patch.setattr(ToolRegistry, "execute_async", _forbidden)
                patch.setattr(provider, "complete", _forbidden)
                patch.setattr(Store, "get_artifact", _forbidden)
                closed_root = workflow.build("annotation", "root", QUESTION, scope)
                again = asyncio.run(closed_root.run_async(workflow.context))
                assert plain(asyncio.run(closed_root.build_result(again)).as_record()) == dict(credit=0, pending_handles=[])
                assert _closed_child(workflow, closed_root, parent, science) == dict(form=dict(outcomes=group))
            assert _tables(store) == before
            proof.update(passed=True, returned=group, source_records=source_records,
                runtime_counts={name: store.db.execute("SELECT count(*) FROM " + name + " WHERE run_id=?", (run_id,)).fetchone()[0]
                    for name in ("runtime_episodes", "runtime_actions", "runtime_observations", "runtime_model_calls", "runtime_forms", "runtime_report_attempts")},
                provider_calls=len(provider.contexts), private_file_grants=[], frozen_replay_unchanged=True)
    except BaseException as error:
        proof["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        audit_path.write_text(json.dumps(proof, indent=2, allow_nan=False) + "\n")




def test_current_vcf_saved_result_handoff_grants_only_returned_Sources(tmp_path, monkeypatch):
    """Use current normal commissions over authentic already calculated results.

    Earlier closed receipt projections remain historical facts. This new
    handoff makes one new saved selection at the native AD/FAD conflict record,
    then reads that result literally. It must create its own ordinary Source
    receipts without reparsing, repeating an old selection or changing old rows.
    """
    supplied = os.environ.get("HMMER_NATIVE_ORACLE_VCF_RETAINED_PROOF")
    expected_sha = os.environ.get("HMMER_NATIVE_ORACLE_VCF_RETAINED_SHA256")
    if not supplied or not expected_sha:
        pytest.skip("requires the explicit retained VCF Workflow proof and digest")
    prefix_path = Path(supplied).resolve(strict=True)
    assert hashlib.sha256(prefix_path.read_bytes()).hexdigest() == expected_sha
    prefix = json.loads(prefix_path.read_text())
    assert prefix["failure"] == dict(type="KeyError", message="'vcf_result_outcomes'")
    assert len(prefix["parser_calls"]) == 1 and len(prefix["calculator_calls"]) == 2
    audit = dict(original_proof=str(prefix_path), original_proof_sha256=expected_sha,
        store_directory=prefix["store_directory"], original_run_id=prefix["run_id"], passed=False)
    path = tmp_path / "vcf_current_handoff_audit.json"
    try:
        with Store(prefix["store_directory"]) as store:
            old_run = prefix["run_id"]
            tables = ("runtime_episodes", "runtime_actions", "runtime_observations", "runtime_model_calls",
                "runtime_forms", "runtime_report_attempts", "runtime_record_receipts")
            old_rows = {name: [dict(row) for row in store.db.execute("SELECT * FROM " + name + " WHERE run_id=? ORDER BY rowid", (old_run,))]
                for name in tables}
            assert len(old_rows["runtime_episodes"]) == 2
            assert all(row["state"] == "yielded" for row in old_rows["runtime_episodes"])
            old_form, = old_rows["runtime_forms"]
            old_group = json.loads(old_form["form"])["outcomes"]
            assert len(old_group) == 2
            references = [old_group[0]["source_ref"]]
            old_sources = [store.get(item["source_ref"]) for item in old_group]
            private = {ref for source in old_sources for ref in (source["request_ref"], *source["auxiliary_artifact_refs"])}
            primary_files = {source["artifact_ref"] for source in old_sources}
            old_operations = [dict(row) for row in store.db.execute("SELECT * FROM tool_operations ORDER BY rowid")]
            assert len(old_operations) == 3
            run_id, scope = "vcf-current-saved-result-handoff", prefix["scope"]
            workspace = tmp_path / "workspace"
            workspace.mkdir()
            factory = ExecutionServiceFactory({"ordinary": dict(kind="local", workspace=str(workspace),
                policy=deepcopy(POLICY))}, {}, 2, .25, .5)
            tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
            factory.configure_tool_registry(tools)
            directory = tmp_path / "run"
            scientific = prepare_scientific_binding(run_directory=directory, source_directory=PUBLICATION,
                tool_catalog=tools.catalog(), child_roles=["scientific_process"])
            library = ScientificProcessLibrary(directory / "scientific-process-library")
            selected = _selection(record_ordinals=[279], sample_ordinals=[0],
                info_keys=["DP", "POPAF", "TLOD"], format_keys=["GT", "PGT", "PID", "AD", "FAD", "AF", "DP"], limit=1)
            assert all(item["value"]["selection"] != selected for item in old_group)
            provider = VcfProvider(store, library, scope, None, result_refs=references, saved_selection=selected)
            application = factory(store, run_id=run_id, directory=directory, tool_registry=tools)
            def controller(episode_path, initial):
                horizon = 1 if episode_path[-1][0] == "annotation" else 2
                def estimate(history, parameters, contexts):
                    return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= horizon else 1),
                        parameters, dict(engineering_fixture="new_saved_conflict_record_then_literal_read"))
                return YieldController(str(episode_path), initial, 0, estimate_with_context=estimate)
            workflow = Workflow(store, tools, provider, directory, run_id, controller, _zero,
                project_child_credit=_zero, episode_binding_descriptors=[scientific, *application.episode_binding_descriptors],
                role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider,
                episode_record_receipts=True, initial_known_record_refs=references)
            audit.update(run_id=run_id, workflow_directory=str(directory), scientific_binding=scientific,
                factory=factory.as_record(), scope=scope, initial_known_record_refs=references,
                new_selection=selected)
            actual_get = Store.get_artifact
            actual_verified = retained_native_file.__globals__["_verified_artifact_path"]
            actual_calculate, actual_execute = core.calculate_vcf_components, host.execute_vcf_result
            phase, attempts, calculator_calls, artifact_reads = [None], [], [], []
            old_components_and_grading = {reference for source in old_sources for reference in source["auxiliary_artifact_refs"][1:]}
            def calculate(sheet, selection):
                assert selection == selected and calculator_calls == []
                calculator_calls.append(deepcopy(selection))
                return actual_calculate(sheet, selection)
            def execute(registry, arguments, **kwargs):
                phase[0] = arguments["mode"]
                try:
                    result = actual_execute(registry, arguments, **kwargs)
                    if result["status"] in ("completed", "partial"):
                        source = registry.store.get(result["result"]["source_ref"])
                        private.update((source["request_ref"], *source["auxiliary_artifact_refs"]))
                        primary_files.add(source["artifact_ref"])
                    return result
                finally:
                    phase[0] = None
            def check(reference):
                artifact_reads.append(dict(mode=phase[0], reference=reference))
                if (reference == prefix["input_ref"] or reference in old_components_and_grading
                        or phase[0] != "calculate_saved" and reference in private):
                    attempts.append(reference)
                    raise AssertionError("saved handoff opened original input or private scientific data")
            def get(current, reference, *args, **kwargs):
                check(reference)
                return actual_get(current, reference, *args, **kwargs)
            def verified(current, reference, *args, **kwargs):
                check(reference)
                return actual_verified(current, reference, *args, **kwargs)
            with monkeypatch.context() as patch:
                patch.setattr(core, "parse_vcf_sheet", _forbidden)
                patch.setattr(core, "calculate_vcf_components", calculate)
                patch.setattr(host, "execute_vcf_result", execute)
                patch.setattr(Store, "get_artifact", get)
                patch.setattr("gene_annotation_episode.materials._verified_artifact_path", verified)
                patch.setattr("gene_annotation_episode.native_file_capture._verified_artifact_path", verified)
                patch.setattr("gene_annotation_episode.acquisition.PublicClients._http", _forbidden)
                patch.setattr("socket.create_connection", _forbidden)
                for name in ("prepare_job", "start_prepared", "resume_start", "wait_job", "collect", "status", "cancel", "release"):
                    patch.setattr(native_lifecycle, name, _forbidden)
                root = workflow.build("annotation", "root", QUESTION, scope)
                completed = asyncio.run(root.run_async(workflow.context))
                assert plain(asyncio.run(root.build_result(completed)).as_record()) == dict(credit=0, pending_handles=[])
                records = EpisodeReturnRecords(store, run_id, failure_prefix="vcf_current_")
                episodes = list(store.db.execute("SELECT episode_id FROM runtime_episodes WHERE run_id=? ORDER BY json_array_length(path)", (run_id,)))
                assert len(episodes) == 2
                parent, science = [records.context(row[0]) for row in episodes]
                rows = list(store.db.execute("SELECT operation.result FROM tool_operations operation JOIN runtime_actions action "
                    "ON operation.operation_key=action.run_id||':'||action.episode_id||':'||action.decision_index WHERE action.run_id=? ORDER BY action.decision_index", (run_id,)))
                assert len(rows) == 2
                group = [json.loads(rows[0][0])["result"]]
                assert json.loads(rows[1][0])["result"] == group[0]
                assert group[0]["source_ref"] not in references
                assert group[0]["value"]["selection"] == selected
                record, = group[0]["value"]["records"]
                assert record["record_ordinal_0based"] == 279 and record["pos_1based"] == 10099029
                native_fields = {field["key"]: field for field in record["samples"][0]["fields"]}
                assert {key: [v["token"]["raw_token"] for v in native_fields[key]["values"]]
                    for key in ("AD", "FAD", "AF")} == dict(AD=["19", "10"], FAD=["25", "10"], AF=["0.296"])
                assert workflow.services.molecular_own_facts(science, fact_source=SOURCE) == group
                assert workflow.services.molecular_frozen_facts(science, fact_source=SOURCE) == group
                assert workflow.services.molecular_received_facts(parent, fact_source=SOURCE) == group
                resolved = []
                def resolve(reference, namespace):
                    resolved.append((reference, namespace))
                    return reference == group[0]["source_ref"] and namespace == "source"
                assert validate_form(dict(outcomes=group), _schema(), resolve) == dict(outcomes=group)
                assert set(resolved) == {(group[0]["source_ref"], "source")}
                view, packets = _selected_molecular_view(dict(outcomes=group))
                assert view == dict(outcomes=["Selected molecular result 1"])
                texts = [_selected_molecular_text(packet, number) for number, packet in enumerate(packets, 1)]
                assert "| retained_record_slots | 295 |" in texts[0]
                assert "| selected_record_slots | 1 |" in texts[0] and "| returned_record_slots | 1 |" in texts[0]
                assert not any(item["value"]["input"]["retained_file"]["sha256"] in text for item, text in zip(group, texts))
                assert _closed_child(workflow, root, parent, science) == dict(form=dict(outcomes=group))
                closed_tables = _tables(store)
                with patch.context() as replay:
                    replay.setattr(core, "calculate_vcf_components", _forbidden)
                    replay.setattr(ToolRegistry, "execute_async", _forbidden)
                    replay.setattr(provider, "complete", _forbidden)
                    closed_root = workflow.build("annotation", "root", QUESTION, scope)
                    again = asyncio.run(closed_root.run_async(workflow.context))
                    assert plain(asyncio.run(closed_root.build_result(again)).as_record()) == dict(credit=0, pending_handles=[])
                    assert _closed_child(workflow, closed_root, parent, science) == dict(form=dict(outcomes=group))
                assert _tables(store) == closed_tables
            assert attempts == [] and calculator_calls == [selected] and len(provider.contexts) == len(provider.wire) == 3
            returned_refs = [group[0]["source_ref"]]
            for current in (parent, science):
                known = set(workflow.receipts.known(current.episode_id))
                assert set(references + returned_refs) <= known
                assert not ({prefix["input_ref"], *private, *primary_files} & known)
            attempt, = list(store.db.execute("SELECT failure,form FROM runtime_report_attempts WHERE run_id=?", (run_id,)))
            assert attempt["failure"] is None and json.loads(attempt["form"]) == dict(outcomes=group)
            parent_action = json.loads(store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=0",
                (run_id, parent.episode_id)).fetchone()[0])
            assert parent_action["record_refs"] == returned_refs
            receipt = store.db.execute("SELECT receipt_kind,source_index FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref=?",
                (run_id, parent.episode_id, returned_refs[0])).fetchone()
            assert tuple(receipt) == ("child_form", 0)
            assert old_rows == {name: [dict(row) for row in store.db.execute("SELECT * FROM " + name + " WHERE run_id=? ORDER BY rowid", (old_run,))]
                for name in tables}
            assert old_sources == [store.get(source["id"]) for source in old_sources]
            assert old_operations == [dict(row) for row in store.db.execute("SELECT * FROM tool_operations ORDER BY rowid LIMIT 3")]
            new_operations = [dict(row) for row in store.db.execute("SELECT operation.* FROM tool_operations operation JOIN runtime_actions action "
                "ON operation.operation_key=action.run_id||':'||action.episode_id||':'||action.decision_index WHERE action.run_id=? ORDER BY action.decision_index", (run_id,))]
            assert len(new_operations) == 2 and [json.loads(row["arguments"])["mode"] for row in new_operations] == ["calculate_saved", "read_stored"]
            assert [json.loads(row["result"])["result"] for row in new_operations] == group * 2
            assert [json.loads(row["result"])["changed_record_refs"] for row in new_operations] == [returned_refs, []]
            audit.update(passed=True, returned=group, source_records=[store.get(reference) for reference in returned_refs],
                original_sources=old_sources, old_run_rows_unchanged=True,
                original_sources_and_operations_unchanged=True, new_parser_calls=0, new_calculator_calls=1,
                new_selection=selected, artifact_reads=artifact_reads,
                new_native_calls=0, new_http_calls=0, new_model_rpc_calls=0, scripted_provider_calls=len(provider.contexts),
                new_saved_calculation_operations=1, new_saved_read_operations=1,
                result_Source_receipts=returned_refs, new_result_File_grants=[],
                forbidden_reads=attempts, closed_replay_unchanged=True,
                runtime_counts={name: store.db.execute("SELECT count(*) FROM " + name + " WHERE run_id=?", (run_id,)).fetchone()[0]
                    for name in tables if name != "runtime_record_receipts"})
    except BaseException as error:
        audit["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        path.write_text(json.dumps(audit, indent=2, allow_nan=False) + "\n")


def test_saved_vcf_delivery_and_reconstruction_use_same_controller_owner(tmp_path, monkeypatch):
    """Verify a fresh typed handoff and closed replay over a genuine saved result."""
    supplied = os.environ.get("HMMER_NATIVE_ORACLE_VCF_CLOSED_PROOF")
    expected_sha = os.environ.get("HMMER_NATIVE_ORACLE_VCF_CLOSED_SHA256")
    if not supplied or not expected_sha:
        pytest.skip("requires the explicit retained VCF handoff proof and digest")
    prefix_path = Path(supplied).resolve(strict=True)
    assert hashlib.sha256(prefix_path.read_bytes()).hexdigest() == expected_sha
    prefix = json.loads(prefix_path.read_text())
    audit = dict(original_proof=str(prefix_path), original_proof_sha256=expected_sha,
        store_directory=prefix["store_directory"], passed=False)
    path = tmp_path / "vcf_stable_delivery_audit.json"
    try:
        with Store(prefix["store_directory"]) as store:
            old_run = prefix["run_id"]
            old_contexts = EpisodeReturnRecords(store, old_run, failure_prefix="vcf_saved_input_")
            old_science = store.db.execute("SELECT episode_id FROM runtime_episodes WHERE run_id=? AND json_array_length(path)=2", (old_run,)).fetchone()[0]
            old_context = old_contexts.context(old_science)
            frozen = json.loads(store.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?", (old_run, old_science)).fetchone()[0])
            group = frozen["outcomes"]
            assert len(group) == 1 and group[0]["value"]["records"][0]["record_ordinal_0based"] == 279
            references = [group[0]["source_ref"]]
            source = store.get(references[0])
            private = {source["request_ref"], *source["auxiliary_artifact_refs"]}
            native_file = group[0]["value"]["input"]["retained_file"]["artifact_ref"]
            scope, run_id = plain(old_context.scope), "vcf-stable-saved-result-handoff"
            old_tables = _tables(store)
            workspace = tmp_path / "workspace"
            workspace.mkdir()
            factory = ExecutionServiceFactory({"ordinary": dict(kind="local", workspace=str(workspace),
                policy=deepcopy(POLICY))}, {}, 2, .25, .5)
            directory = tmp_path / "run"
            tools, workflow, provider, scientific = _saved_workflow(store, directory, run_id, scope, references, factory)
            audit.update(run_id=run_id, workflow_directory=str(directory), factory=factory.as_record(),
                scientific_binding=scientific, scope=scope, initial_known_record_refs=references)
            actual_get = Store.get_artifact
            actual_verified = retained_native_file.__globals__["_verified_artifact_path"]
            forbidden_reads = []
            def check(reference):
                if reference == native_file or reference in private:
                    forbidden_reads.append(reference)
                    raise AssertionError("literal saved read reopened original input or private scientific data")
            def get(current, reference, *args, **kwargs):
                check(reference)
                return actual_get(current, reference, *args, **kwargs)
            def verified(current, reference, *args, **kwargs):
                check(reference)
                return actual_verified(current, reference, *args, **kwargs)
            with monkeypatch.context() as patch:
                patch.setattr(core, "parse_vcf_sheet", _forbidden)
                patch.setattr(core, "calculate_vcf_components", _forbidden)
                patch.setattr(Store, "get_artifact", get)
                patch.setattr("gene_annotation_episode.materials._verified_artifact_path", verified)
                patch.setattr("gene_annotation_episode.native_file_capture._verified_artifact_path", verified)
                patch.setattr("gene_annotation_episode.acquisition.PublicClients._http", _forbidden)
                patch.setattr("socket.create_connection", _forbidden)
                for name in ("prepare_job", "start_prepared", "resume_start", "wait_job", "collect", "status", "cancel", "release"):
                    patch.setattr(native_lifecycle, name, _forbidden)
                root = workflow.build("annotation", "root", QUESTION, scope)
                completed = asyncio.run(root.run_async(workflow.context))
                assert plain(asyncio.run(root.build_result(completed)).as_record()) == dict(credit=0, pending_handles=[])
                records = EpisodeReturnRecords(store, run_id, failure_prefix="vcf_stable_")
                episodes = list(store.db.execute("SELECT episode_id FROM runtime_episodes WHERE run_id=? ORDER BY json_array_length(path)", (run_id,)))
                assert len(episodes) == 2
                parent, science = [records.context(row[0]) for row in episodes]
                assert workflow.services.molecular_own_facts(science, fact_source=SOURCE) == group
                assert workflow.services.molecular_frozen_facts(science, fact_source=SOURCE) == group
                assert workflow.services.molecular_received_facts(parent, fact_source=SOURCE) == group
                assert _closed_child(workflow, root, parent, science) == dict(form=frozen)
                completed_tables = _tables(store)
                with patch.context() as replay:
                    replay.setattr(ToolRegistry, "execute_async", _forbidden)
                    replay.setattr(provider, "complete", _forbidden)
                    replay.setattr(Store, "get_artifact", _forbidden)
                    replay.setattr("gene_annotation_episode.materials._verified_artifact_path", _forbidden)
                    replay.setattr("gene_annotation_episode.native_file_capture._verified_artifact_path", _forbidden)
                    _, reopened, other_provider, other_scientific = _saved_workflow(store, directory, run_id, scope,
                        references, ExecutionServiceFactory.from_record(factory.as_record()), scientific=scientific)
                    replay.setattr(other_provider, "complete", _forbidden)
                    assert other_scientific == scientific
                    closed_root = reopened.build("annotation", "root", QUESTION, scope)
                    closed = asyncio.run(closed_root.run_async(reopened.context))
                    assert plain(asyncio.run(closed_root.build_result(closed)).as_record()) == dict(credit=0, pending_handles=[])
                    assert _closed_child(reopened, closed_root, parent, science) == dict(form=frozen)
                    assert reopened.services.molecular_received_facts(parent, fact_source=SOURCE) == group
                    assert other_provider.contexts == other_provider.wire == []
                assert _tables(store) == completed_tables
            assert forbidden_reads == [] and len(provider.contexts) == len(provider.wire) == 2
            parent_action = json.loads(store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=0",
                (run_id, parent.episode_id)).fetchone()[0])
            assert parent_action["record_refs"] == references
            for current in (parent, science):
                known = set(workflow.receipts.known(current.episode_id))
                assert references[0] in known
                assert not ({native_file, source["artifact_ref"], *private, *source["parent_source_refs"]} & known)
            operation, = list(store.db.execute("SELECT operation.* FROM tool_operations operation JOIN runtime_actions action "
                "ON operation.operation_key=action.run_id||':'||action.episode_id||':'||action.decision_index WHERE action.run_id=?", (run_id,)))
            assert json.loads(operation["arguments"]) == dict(mode="read_stored", result_ref=references[0])
            outcome = json.loads(operation["result"])
            assert outcome["status"] == "completed" and outcome["result"] == group[0] and outcome["changed_record_refs"] == []
            attempt, = list(store.db.execute("SELECT failure,form FROM runtime_report_attempts WHERE run_id=?", (run_id,)))
            assert attempt["failure"] is None and json.loads(attempt["form"]) == frozen
            # Every pre-existing row remains byte-for-byte the same tuple.
            after = _tables(store)
            assert all(name == "sqlite_sequence" or all(row in after[name] for row in rows)
                for name, rows in old_tables.items())
            audit.update(passed=True, returned=group, source_records=[source], new_parser_calls=0,
                new_calculator_calls=0, new_native_calls=0, new_http_calls=0, new_model_rpc_calls=0,
                scripted_provider_calls=2, new_saved_read_operations=1, original_rows_unchanged=True,
                closed_reconstruction_rows_unchanged=True, exact_saved_factory_binding_and_controller=True,
                forbidden_reads=forbidden_reads, result_Source_projection=references, new_result_File_grants=[],
                runtime_counts={name: store.db.execute("SELECT count(*) FROM " + name + " WHERE run_id=?", (run_id,)).fetchone()[0]
                    for name in ("runtime_episodes", "runtime_actions", "runtime_observations", "runtime_model_calls", "runtime_forms", "runtime_report_attempts")})
    except BaseException as error:
        audit["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        path.write_text(json.dumps(audit, indent=2, allow_nan=False) + "\n")


