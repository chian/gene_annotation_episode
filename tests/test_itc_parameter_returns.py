"""Retained-only ITC parameter returns through the existing episode protocol.

The original268 scientific Files and publications are inputs. These engineering
decisions make no worker, optimizer, calculator or publication call. Original
Source-only replay and the isolated receipt control have explicitly separate
scopes from the new requested rich-form Workflow.
"""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from gene_annotation_episode.communication import ReportBoundaryError, plain
from gene_annotation_episode.domain import canonical, obj
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.molecular_measurement_tools import (
    ITC_TOOL, ITC_PARAMETER_SOURCE, frozen_itc_parameter_facts,
    itc_parameter_fact_sources, merge_itc_parameter_facts, own_itc_parameter_facts,
    project_itc_parameter_return, received_itc_parameter_facts,
    requested_itc_parameter_fields,
    validate_frozen_itc_parameter_return, validate_itc_parameter_return,
)
from gene_annotation_episode.runtime import TypedReportContract, Workflow
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_itc_binding_tool import QUESTION, _RenderedScript, _archives, _libraries, _tables
from test_runtime import FixtureController


RETAINED = Path(__file__).resolve().parents[1] / (
    "verification/tool_graders_hmmer_map_verification_2026-10-28_529/"
    "check268_itc_ordinary_tool_delivery/temporary/pytest/test_registered_itc_fit_same_e0")
ORIGINAL = "source_4f6a6927cc1b155c54974cb7"
SAVED = "source_7275c03cef6e89f75c3d2605"


def _forbidden(*args, **kwargs):
    raise AssertionError("retained parameter delivery attempted new scientific work")


def _guards(monkeypatch):
    from gene_annotation_episode import itc_binding_fit, itc_binding_measurements, native_lifecycle
    from gene_annotation_episode import molecular_measurement_tools, tool_grading_artifacts
    monkeypatch.setattr(itc_binding_fit, "fit_itc_binding_measurements", _forbidden)
    monkeypatch.setattr(itc_binding_measurements, "calculate_itc_binding_components", _forbidden)
    monkeypatch.setattr(itc_binding_measurements, "predict_itc_binding_heats", _forbidden)
    monkeypatch.setattr(molecular_measurement_tools, "run_itc_tool_request", _forbidden)
    monkeypatch.setattr(molecular_measurement_tools, "run_owned_molecular_worker", _forbidden)
    monkeypatch.setattr(tool_grading_artifacts, "retain_tool_grading", _forbidden)
    for name in ("prepare_job", "resume_start", "collect", "wait_job"):
        monkeypatch.setattr(native_lifecycle, name, _forbidden)
    monkeypatch.setattr(ToolRegistry, "_sequence_worker_async", _forbidden)


def _clone(tmp_path):
    assert RETAINED.is_dir(), "the authentic268 retained input must be explicitly selected"
    directory = tmp_path / "retained268"
    shutil.copytree(RETAINED / "store", directory / "store")
    shutil.copytree(RETAINED / "run", directory / "run")
    # Frozen selected inputs stay untouched. Only this new owned copy is a
    # writable Store/workspace for the ordinary protocol and forgery controls.
    for path in (directory, *directory.rglob("*")):
        path.chmod(0o755 if path.is_dir() else 0o644)
    return directory


def _all_table_rows(store):
    """Compare stored row values and SQLite scalar types, including settings."""
    names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: [tuple((type(value).__name__, value) for value in row) for row in
        store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')] for name in names}


def _native(store, source):
    return json.loads(store.get_artifact(store.get(source)["artifact_ref"]))


def _expected(store):
    return [project_itc_parameter_return(_native(store, ref), source_ref=ref) for ref in (ORIGINAL, SAVED)]


def _descriptor(directory):
    return ScientificProcessEpisodes(None,
        library=ScientificProcessLibrary(directory / "scientific-process-library"),
        tool_library=ScientificToolLibrary(directory / "scientific-tool-library"),
        child_roles=["scientific_process"]).as_record()


def _original_workflow(store, directory, provider):
    first = store.get(ORIGINAL)
    control = json.loads(store.get_artifact(first["request_ref"]))
    supplied = control["request"]["received_input"]
    tools = ToolRegistry(store, job_limits=dict(memory_bytes=20 * 1024**3,
        scratch_bytes=4 * 1024**3, wall_seconds=None))
    workflow = Workflow(store, tools, provider, directory, "ordinary-itc-fixture",
        lambda path, initial: FixtureController(str(path), initial, 1 if len(path) == 1 else 3),
        lambda store, scope, **kwargs: 0, project_child_credit=lambda store, scope, **kwargs: 0,
        episode_binding_descriptors=[_descriptor(directory)], episode_record_receipts=True,
        initial_known_record_refs=[supplied["witness"]["reference"], supplied["file"]["artifact_ref"]])
    original_context = EpisodeReturnRecords(store, workflow.run_id, failure_prefix="test_").context(
        control["request"]["invocation"]["episode_id"])
    return workflow, original_context


def test_original_partial_and_saved_parameter_cells_and_old_source_only_replay(tmp_path, monkeypatch):
    directory = _clone(tmp_path)
    _guards(monkeypatch)
    with Store(directory / "store") as store:
        original_files = _archives(directory / "store/artifacts")
        before, run_files = _all_table_rows(store), _archives(directory / "run")
        workflow, context = _original_workflow(store, directory / "run", _RenderedScript([]))
        assert _all_table_rows(store) == before
        assert _archives(directory / "run") == run_files
        assert _archives(directory / "store/artifacts") == original_files
        expected = _expected(store)
        values = own_itc_parameter_facts(workflow.tools, context,
            read_received=workflow.services.read_received_molecular_input)
        assert canonical(values) == canonical(expected)
        assert [v["parameter_source"] for v in values] == ["fit_observation", "selected_parameters"]
        assert values[0]["kd"]["value"] == 2.999999999999987e-6
        assert values[1]["kd"]["value"] == 6e-6
        for reference, value in zip((ORIGINAL, SAVED), values):
            native = _native(store, reference)
            for name, unit in dict(kd="mol_per_litre", n="sites_per_macromolecule", delta_h="joule_per_mole").items():
                assert canonical(value[name]) == canonical({**native["components"]["parameter_values"][name], "unit": unit})
            assert canonical(value["fit_qualification_codes"]) == canonical(native["sheet"]["fit_observation"]["qualifications"])
            assert canonical(value["prediction_qualification_codes"]) == canonical(native["components"]["full_prediction"]["qualifications"])
        assert all(v["fit_call_count"] == 1 and v["fit_call_state"] == "returned" for v in values)
        assert all(v["fit_diagnostics_scope"] == "retained_original_fit_vector_and_residual_population" for v in values)
        assert all(v["identifiability"] == v["statistical_covariance_validity"] == "not_assessed" for v in values)
        assert frozen_itc_parameter_facts(store, workflow.run_id, context) is None
        # Three original actions include a repeated saved-source literal read;
        # the partial original publication is retained alongside the saved one.
        assert [json.loads(r[0])["status"] for r in store.db.execute(
            "SELECT result FROM runtime_actions WHERE episode_id=? ORDER BY decision_index", (context.episode_id,))] == [
                "partial", "completed", "completed"]
        assert _all_table_rows(store) == before
        assert _archives(directory / "store/artifacts") == original_files
        root = workflow.build("annotation", "root", QUESTION, plain(context.scope))
        record = asyncio.run(root.run_async(workflow.context))
        asyncio.run(root.build_result(record))
        assert _all_table_rows(store) == before
        assert _archives(directory / "run") == run_files
        assert _archives(directory / "store/artifacts") == original_files
        assert workflow.provider.contexts == []


def test_retained_parameter_form_received_and_onward_in_actual_workflow(tmp_path, monkeypatch):
    directory = _clone(tmp_path)
    _guards(monkeypatch)
    with Store(directory / "store") as store:
        files_before = _archives(directory / "store/artifacts")
        expected = _expected(store)
        source_records = [store.get(ref) for ref in (ORIGINAL, SAVED)]
        scope = json.loads(store.db.execute("SELECT request FROM runtime_episodes WHERE run_id=? "
            "AND json_array_length(path)=1", ("ordinary-itc-fixture",)).fetchone()[0])["message"]["scope"]
        tools = ToolRegistry(store)
        run = tmp_path / "rich-run"; run.mkdir()
        descriptor, selected = _libraries(run, tools, tool_names=(ITC_TOOL, "state.query"))
        parameters = itc_parameter_fact_sources()[ITC_PARAMETER_SOURCE]["report_schema"]
        form = obj(dict(parameters=parameters))
        def commission(goal, chosen):
            return dict(selection=dict(kind="episode_child", role="scientific_process", goal=goal,
                scope=scope, purpose="Return the retained Kd, effective n and enthalpy cells with their original qualifications.",
                schema_json=json.dumps(form), initial_report_json="{}", assignment=dict(selection=chosen,
                    evidence_refs=[ORIGINAL, SAVED], constraints={}, context=dict(question=goal))), report_update={})
        def read(source):
            return dict(selection=dict(kind="tool", tool=ITC_TOOL, arguments=dict(mode="read_stored",
                result_ref=source, injection_ordinals=[31, 0], fields=["predicted_heat", "residual"])), report_update={})
        received, inspected = [], []
        def onward(context):
            parent = workflow.binding_context(root.source)
            actual = workflow.services.itc_parameter_received_facts(parent)
            assert canonical(actual) == canonical(expected)
            attempts = store.db.execute("SELECT contract,form FROM runtime_report_attempts WHERE run_id=? "
                "AND parent_episode_id=? AND failure IS NULL", (workflow.run_id, parent.episode_id)).fetchall()
            assert len(attempts) == 1
            assert canonical(json.loads(attempts[0]["form"])["parameters"]) == canonical(expected)
            received.append(deepcopy(actual))
            next_selection = deepcopy(selected)
            next_selection["child_tool_info"] = [dict(name="state.query", resources="local")]
            return commission("What retained ITC parameter values and qualifications were explicitly received for this supplied history?",
                next_selection)
        def inspect(context):
            row = store.db.execute("SELECT episode_id FROM runtime_episodes WHERE run_id=? "
                "AND json_extract(path,'$[1][1]')='child_1'", (workflow.run_id,)).fetchone()
            current = EpisodeReturnRecords(store, workflow.run_id, failure_prefix="test_").context(row[0])
            actual = workflow.services.itc_parameter_received_facts(current)
            assert canonical(actual) == canonical(expected)
            assert workflow.services.itc_parameter_own_facts(current) == []
            inspected.append(deepcopy(actual))
            return dict(selection=dict(kind="tool", tool="state.query", arguments=dict(refs=[ORIGINAL, SAVED])), report_update={})
        provider = _RenderedScript([commission(QUESTION, selected), read(ORIGINAL), read(SAVED), read(SAVED), onward, inspect])
        initial = [reference for source in source_records for reference in
            (source["id"], source["artifact_ref"], *source["auxiliary_artifact_refs"])]
        workflow = Workflow(store, tools, provider, run, "retained-itc-parameter-forms",
            lambda path, initial: FixtureController(str(path), initial,
                2 if len(path) == 1 else 3 if path[-1][1] == "child_0" else 1),
            lambda store, scope, **kwargs: 0, project_child_credit=lambda store, scope, **kwargs: 0,
            episode_binding_descriptors=[descriptor], episode_record_receipts=True, initial_known_record_refs=initial)
        root_contract = TypedReportContract("Return the retained ITC parameter cells actually received in this investigation.",
            form, lambda reference, namespace: workflow.resolver(scope, source=root.source)(reference, namespace),
            semantic_validator=lambda value: workflow.validate_report(value, scope, grain="annotation", schema=form, source=root.source))
        root = workflow.build("annotation", "root", QUESTION, scope, contract=root_contract)
        record = asyncio.run(root.run_async(workflow.context))
        asyncio.run(root.build_result(record))
        assert len(provider.contexts) == 6 and received == inspected == [expected]
        parent_context = workflow.binding_context(root.source)
        parent_frozen = workflow.services.itc_parameter_frozen_facts(parent_context)
        assert canonical(parent_frozen) == canonical(expected)
        parent_form = json.loads(store.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (workflow.run_id, root.source.episode_id)).fetchone()[0])
        assert canonical(parent_form["parameters"]) == canonical(expected)
        forged_parent = deepcopy(parent_form); forged_parent["parameters"][0]["kd"]["value"] = 1e-3
        with pytest.raises(ReportBoundaryError, match="ITC parameter"):
            workflow.episode_bindings.validate_received_report(parent_context, forged_parent, form)
        rows = list(store.db.execute("SELECT child_episode_id,form,contract FROM runtime_report_attempts "
            "WHERE run_id=? AND failure IS NULL ORDER BY decision_index", (workflow.run_id,)))
        assert len(rows) == 2
        for row in rows:
            returned = json.loads(row["form"])
            assert canonical(returned["parameters"]) == canonical(expected)
            current = EpisodeReturnRecords(store, workflow.run_id, failure_prefix="test_").context(row["child_episode_id"])
            frozen = workflow.services.itc_parameter_frozen_facts(current)
            assert canonical(frozen) == canonical(expected)
            validate_frozen_itc_parameter_return(returned, json.loads(row["contract"])["measurements"]["schema"], frozen)
            forged = deepcopy(returned); forged["parameters"][0]["kd"]["value"] = 1e-3
            with pytest.raises(ReportBoundaryError, match="ITC parameter"):
                workflow.scientific_process_binding.validate_report(current, forged,
                    json.loads(row["contract"])["measurements"]["schema"])
        onward_context = EpisodeReturnRecords(store, workflow.run_id, failure_prefix="test_").context(rows[1]["child_episode_id"])
        manifest = store.db.execute("SELECT received_report_prefix FROM runtime_receipt_inheritance "
            "WHERE run_id=? AND episode_id=?", (workflow.run_id, onward_context.episode_id)).fetchone()[0]
        prefix = json.loads(manifest)
        assert [item["decision_index"] for item in prefix["attempts"]] == [0]
        altered_prefix = deepcopy(prefix); altered_prefix["attempts"][0]["form_sha256"] = "0" * 64
        try:
            store.db.execute("UPDATE runtime_receipt_inheritance SET received_report_prefix=? WHERE run_id=? AND episode_id=?",
                (canonical(altered_prefix), workflow.run_id, onward_context.episode_id))
            with pytest.raises(ValueError, match="received_prefix_conflict"):
                received_itc_parameter_facts(store, workflow.run_id, onward_context)
        finally:
            store.db.execute("UPDATE runtime_receipt_inheritance SET received_report_prefix=? WHERE run_id=? AND episode_id=?",
                (manifest, workflow.run_id, onward_context.episode_id))
        late_form = rows[1]["form"]
        corrupted = json.loads(late_form); corrupted["parameters"][0]["kd"]["value"] = 1e-3
        try:
            store.db.execute("UPDATE runtime_report_attempts SET form=? WHERE run_id=? AND parent_episode_id=? AND decision_index=1",
                (canonical(corrupted), workflow.run_id, root.source.episode_id))
            # This later parent return is outside this child's actual frozen
            # received prefix. It cannot become another inherited fact.
            assert canonical(received_itc_parameter_facts(store, workflow.run_id, onward_context)) == canonical(expected)
            with pytest.raises(ValueError, match="frozen_return_conflict"):
                workflow.services.itc_parameter_received_facts(workflow.binding_context(root.source))
        finally:
            store.db.execute("UPDATE runtime_report_attempts SET form=? WHERE run_id=? AND parent_episode_id=? AND decision_index=1",
                (late_form, workflow.run_id, root.source.episode_id))
        # These Files were explicit initial operands, not grants added by a
        # rich form. Only Source refs occur in the returned public groups.
        for source in source_records:
            for reference in (source["artifact_ref"], *source["auxiliary_artifact_refs"]):
                assert store.db.execute("SELECT receipt_kind FROM runtime_record_receipts WHERE run_id=? "
                    "AND episode_id=? AND record_ref=?", (workflow.run_id, root.source.episode_id, reference)).fetchone()[0] == "initial"
            assert source["request_ref"] not in set(workflow.receipts.known(root.source.episode_id))
        assert _archives(directory / "store/artifacts") == files_before
        # An isolated real receiver and the actual restricted Source receipt
        # demonstrate grant shape; this is not another rich-form Workflow.
        isolated = Workflow(store, ToolRegistry(store), _RenderedScript([]), tmp_path / "isolated", "source-only-itc-receiver",
            lambda path, initial: FixtureController(str(path), initial, 1), lambda store, scope: 0,
            episode_record_receipts=True, initial_known_record_refs=[])
        receiver = isolated.build("annotation", "root", "Which retained ITC sources were explicitly supplied?", scope)
        baseline = set(isolated.receipts.known(receiver.source.episode_id))
        baseline_rows = [dict(row) for row in store.db.execute("SELECT * FROM runtime_record_receipts WHERE run_id=? "
            "AND episode_id=? ORDER BY receipt_index", (isolated.run_id, receiver.source.episode_id))]
        for source in source_records:
            assert not baseline.intersection((source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"]))
        isolated.receipts.receive(receiver.source.episode_id, [v["source_ref"] for v in expected], kind="decision_input", source_index=0)
        assert set(isolated.receipts.known(receiver.source.episode_id)) == baseline | {ORIGINAL, SAVED}
        after_rows = [dict(row) for row in store.db.execute("SELECT * FROM runtime_record_receipts WHERE run_id=? "
            "AND episode_id=? ORDER BY receipt_index", (isolated.run_id, receiver.source.episode_id))]
        assert [row for row in after_rows if row["record_ref"] in baseline] == baseline_rows
        added = [row for row in after_rows if row["record_ref"] not in baseline]
        assert len(added) == 2
        assert {(row["record_ref"], row["receipt_kind"], row["source_index"]) for row in added} == {
            (ORIGINAL, "decision_input", 0), (SAVED, "decision_input", 0)}
        current = isolated.binding_context(receiver.source)
        for source in source_records:
            assert isolated.resolver(scope, context=current)(source["id"], "source") is True
            for reference in (source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"]):
                assert isolated.resolver(scope, context=current)(reference, "artifact") is False
        before, archive = _tables(store), _archives(run / "archive")
        monkeypatch.setattr(provider, "complete", _forbidden)
        replay = workflow.build("annotation", "root", QUESTION, scope, contract=root_contract)
        replay_record = asyncio.run(replay.run_async(workflow.context)); asyncio.run(replay.build_result(replay_record))
        assert _tables(store) == before and _archives(run / "archive") == archive
        assert _archives(directory / "store/artifacts") == files_before


@pytest.mark.parametrize("corruption", ["operation_name", "operation_arguments", "runtime_result", "source_receipt", "file_denied"])
def test_retained_parameter_own_authority_rejects_forged_links(tmp_path, monkeypatch, corruption):
    directory = _clone(tmp_path)
    _guards(monkeypatch)
    with Store(directory / "store") as store:
        workflow, context = _original_workflow(store, directory / "run", _RenderedScript([]))
        key = f"{context.run_id}:{context.episode_id}:0"
        if corruption == "operation_name":
            store.db.execute("UPDATE tool_operations SET name='state.query' WHERE operation_key=?", (key,))
        elif corruption == "operation_arguments":
            store.db.execute("UPDATE tool_operations SET arguments='{}' WHERE operation_key=?", (key,))
        elif corruption == "runtime_result":
            row = store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? "
                "AND decision_index=0", (context.run_id, context.episode_id)).fetchone()
            value = json.loads(row[0]); value["record_refs"] = [ORIGINAL]
            store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
                (canonical(value), context.run_id, context.episode_id))
        elif corruption == "source_receipt":
            store.db.execute("DELETE FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref=?",
                (context.run_id, context.episode_id, ORIGINAL))
        else:
            owner = workflow.services._molecular_reference_access
            native = store.get(ORIGINAL)["artifact_ref"]
            monkeypatch.setattr(workflow.services, "_molecular_reference_access", lambda current, ref, namespace:
                False if ref == native and namespace == "artifact" else owner(current, ref, namespace))
        with pytest.raises(ValueError):
            own_itc_parameter_facts(workflow.tools, context, read_received=workflow.services.read_received_molecular_input)


@pytest.mark.parametrize("mutation", ["boolean_value", "float_count", "boolean_count", "unit", "unknown_reason", "warning_text", "missing_scope"])
def test_parameter_return_closed_shape_and_duplicate_conflict(tmp_path, mutation):
    directory = _clone(tmp_path)
    with Store(directory / "store") as store:
        original = _expected(store)[0]
    value = deepcopy(original)
    if mutation == "boolean_value": value["kd"]["value"] = True
    elif mutation == "float_count": value["fit_call_count"] = 1.0
    elif mutation == "boolean_count": value["fit_call_count"] = True
    elif mutation == "unit": value["kd"]["unit"] = "joule"
    elif mutation == "unknown_reason": value["kd"] = dict(state="unavailable", value=None, unit="mol_per_litre", reason="guessed")
    elif mutation == "warning_text": value["warning_locations"] = [dict(location_code="fit_warning", ordinal=0, message="arbitrary")]
    else: del value["fit_diagnostics_scope"]
    with pytest.raises(ValueError): validate_itc_parameter_return(value)
    assert canonical(merge_itc_parameter_facts([original], [original])) == canonical([original])
    conflict = deepcopy(original); conflict["kd"]["value"] = 1e-3
    with pytest.raises(ValueError, match="source_conflict"):
        merge_itc_parameter_facts([original], [conflict])


def test_parameter_projection_without_observation_keeps_unknown_call_count(tmp_path):
    """A shape/projection fixture, not an authenticated native publication."""
    directory = _clone(tmp_path)
    with Store(directory / "store") as store:
        stored = _native(store, SAVED)
    stored["sheet"]["fit_observation"] = None
    stored["components"]["sheet"] = deepcopy(stored["sheet"])
    stored["request"]["sheet"] = deepcopy(stored["sheet"])
    stored["components"]["fit_diagnostics"] = None
    value = project_itc_parameter_return(stored, source_ref=SAVED)
    assert value["parameter_source"] == "selected_parameters" and value["kd"]["value"] == 6e-6
    assert value["fit_call_state"] is value["fit_call_count"] is None
    assert value["weighting"] is value["independent_error_assumption"] is value["absolute_sigma"] is None
    assert value["fit_qualification_codes"] is value["fit_diagnostics_scope"] is None
    assert value["warning_locations"] == [] and value["failure_location"] is None


def test_unrequested_parameter_source_does_not_enter_new_schema_or_source_readers(monkeypatch):
    from gene_annotation_episode import communication, molecular_measurement_tools as ordinary
    monkeypatch.setattr(communication, "validate_closed_schema", _forbidden)
    monkeypatch.setattr(ordinary, "itc_parameter_fact_sources", _forbidden)
    for name in ("own_itc_parameter_facts", "frozen_itc_parameter_facts", "received_itc_parameter_facts"):
        monkeypatch.setattr(ordinary, name, _forbidden)
    assert requested_itc_parameter_fields(obj(dict(sources={"type": "array", "items": {"type": "string"},
        "x-source": "changed_record_refs"}))) == []
