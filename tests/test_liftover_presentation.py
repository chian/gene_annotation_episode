"""Current presentation of authentic309/311 liftover values, without conversion.

No historical dispatched instructions or wires were retained. The instruction
and Session checks below are explicitly current read-side reconstructions over
unchanged saved contexts; they do not dispatch, replay or complete an episode.
"""
import builtins
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode import liftover_contracts as core
from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import instructional_model_context, state_frame
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.runtime import DecisionSource, Workflow
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_prompt import (
    _cell, _rows, _values, has_molecular_receiver_context, text_instructions,
)
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_interval_results_presentation import (
    _assert_original_rows, _canonical, _inventory, _session, _sha,
    _source_for_original_context, _tables, _walk,
)


_GATE = "HMMER_NATIVE_ORACLE_LIFTOVER_PRESENTATION_CASES_JSON"
_PINS = {
    "native": dict(inventory="b154dabdbe774b801a7f999f8462d1dc6f6087259397fccd86ba63bdc9c74c2c",
        database="d5133e9d491c5209638d89bd40e1f46dbd2dd3652976fd0f199d267fbd191036",
        database_bytes=1978368, store="store", run="run", run_id="ordinary-liftover-fixture",
        episode_id="episode_edbdf8274cc42c2e867f1c824eb09431acd0bfbaedc5a275f909faabd868c13b"),
    "rich": dict(inventory="20feca09aeb4c91acbe7f4e5566f0fa14ba3e416a749820b8a3002451fd09efb",
        database="a9f3f9052796e00941dc485fb208d4adf02e4783b8c69b5dd21a588a935afd67",
        database_bytes=3182592, store="retained-liftover/store", run="rich-run",
        run_id="retained-liftover-rich-forms",
        episode_id="episode_db14958b3e2b2e095f848cd190db24dae5805f7ce5c0d8e116dad78e8ff718d2"),
}
_SUMMARY_SHA = "1d43730a90279d3b2e0d5cc266131e9f9300e7bd1803af0ee9b667e921b1d57a"
_TOOL_INFO_SHA = "d42531e73ae48a14dda1e1f388e1f782ef71eb4a6762ba0b904013ead82f928e"
_RICH_REQUEST_SHA = "d14228e7aa7a2beed852471274d2867dfff04c0f1434e7a816efa6ef8d0db788"
_POINT = dict(chromosome="literal.source", position_0based=0, strand="-")
_PLACEMENT = dict(ordinal=0, state="valid", target_chromosome="literal.target",
    target_position_0based=19, target_strand="+", native_chain_score=9, qualification_codes=[])


def _forbidden(*args, **kwargs):
    raise AssertionError("liftover presentation attempted execution, calculation, private bytes or publication")


def _guards(monkeypatch):
    from gene_annotation_episode import liftover_measurements, liftover_tools
    from gene_annotation_episode import molecular_measurement_tools, native_lifecycle, tool_grading_artifacts
    from gene_annotation_episode.acquisition import PublicClients
    from gene_annotation_episode.providers import _SessionConnection
    for name in ("calculate_liftover_components", "populate_liftover_sheet", "_components", "_population"):
        monkeypatch.setattr(core, name, _forbidden)
    monkeypatch.setattr(liftover_measurements, "run_liftover_tool_request", _forbidden)
    for name in ("prepare_liftover_work", "publish_liftover_work"):
        monkeypatch.setattr(liftover_tools, name, _forbidden)
    for name in ("run_owned_molecular_worker", "retain_molecular_publication", "read_retained_molecular_publication"):
        monkeypatch.setattr(molecular_measurement_tools, name, _forbidden)
    monkeypatch.setattr(tool_grading_artifacts, "retain_tool_grading", _forbidden)
    for name in ("prepare_job", "resume_start", "status", "collect", "wait_job"):
        monkeypatch.setattr(native_lifecycle, name, _forbidden)
    for name in ("put", "artifact", "commit_reasoning", "get_artifact"):
        monkeypatch.setattr(Store, name, _forbidden)
    for name in ("execute_async", "_sequence_worker_async"):
        monkeypatch.setattr(ToolRegistry, name, _forbidden)
    for name in ("build", "selected"):
        monkeypatch.setattr(Workflow, name, _forbidden)
    for name in ("call", "next"):
        monkeypatch.setattr(DecisionSource, name, _forbidden)
    monkeypatch.setattr(PublicClients, "_http", _forbidden)
    monkeypatch.setattr(_SessionConnection, "complete", _forbidden)
    original_import = builtins.__import__

    def no_converter(name, *args, **kwargs):
        assert name != "pyliftover" and not name.startswith("pyliftover."), "presentation imported converter"
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_converter)


def _request(connection, case, episode_id, call_index):
    row = connection.execute("SELECT request FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index=?",
        (case["pin"]["run_id"], episode_id, call_index)).fetchone()
    assert row is not None
    request = json.loads(row[0])
    assert "instructions" not in request  # No historical wire/instruction claim.
    return request


def _application(case, directory, initial_refs):
    """A second owned current application; never rebuild an old commission."""
    connection, pin = case["connection"], case["pin"]
    row = connection.execute("SELECT request FROM runtime_episodes WHERE run_id=? AND json_array_length(path)=2 "
        "AND json_extract(path,'$[1][1]')='child_0'", (pin["run_id"],)).fetchone()
    assert row is not None
    recorded = json.loads(row[0])["message"]["scientific_process"]["mechanics_binding"]
    application = directory / "current-read-side"
    application.mkdir()
    state = application / "state"
    shutil.copytree(case["historical"] / pin["store"], state, symlinks=True)
    run = application / "run"
    shutil.copytree(case["historical"] / pin["run"], run, symlinks=True)
    library = ScientificProcessLibrary(run / "scientific-process-library")
    tools_library = ScientificToolLibrary(run / "scientific-tool-library")
    configuration = recorded["configuration"]
    assert library.as_record() == configuration["library"]
    assert tools_library.as_record() == configuration["tool_library"]
    current = ScientificProcessEpisodes(None, library=library, tool_library=tools_library,
        child_roles=configuration["child_roles"], tool_retrieval=configuration.get("tool_retrieval"),
        contract_information_profile=configuration.get("contract_information_profile")).as_record()
    assert current["configuration"] == configuration
    # This explicitly authorized writable constructor touches only the second
    # copy. Historical inspection remains read-only/immutable; no db/path swaps.
    store = Store(state)
    try:
        flow = Workflow(store, ToolRegistry(store), SimpleNamespace(complete=_forbidden, release=_forbidden),
            run, pin["run_id"], controller_factory=_forbidden, project_credit=_forbidden,
            project_child_credit=_forbidden, episode_binding_descriptors=[current],
            episode_record_receipts=True, initial_known_record_refs=initial_refs)
        _assert_original_rows(store.db, case["tables"])
        return dict(store=store, flow=flow, recorded_binding=recorded, current_read_side_binding=current)
    except BaseException:
        store.close()
        raise


@pytest.fixture(scope="module")
def retained_liftover(tmp_path_factory):
    selected = os.environ.get(_GATE)
    if not selected:
        pytest.skip("explicit authentic309/311 liftover presentation inputs are required")
    selections = json.loads(selected)
    assert type(selections) is dict and set(selections) == set(_PINS)
    directory = tmp_path_factory.mktemp("liftover-presentation")
    cases, guard = {}, pytest.MonkeyPatch()
    try:
        # Copy both cases BEFORE opening either SQLite database. The selected
        # originals are only inventoried/hashed; they are never SQLite inputs.
        for name, pin in _PINS.items():
            item = selections[name]
            assert type(item) is dict and set(item) == {"directory", "inventory_sha256"}
            assert item["inventory_sha256"] == pin["inventory"]
            original = Path(item["directory"]).resolve(strict=True)
            inventory = _inventory(original)
            assert _sha(_canonical(inventory).encode()) == pin["inventory"]
            database = original / pin["store"] / "state.sqlite3"
            assert database.stat().st_size == pin["database_bytes"]
            assert _sha(database.read_bytes()) == pin["database"]
            wal = database.with_name(database.name + "-wal")
            assert not wal.exists() or wal.stat().st_size == 0, "a nonempty WAL requires a separately authenticated unified input"
            shm = database.with_name(database.name + "-shm")
            if shm.exists():
                # SHM alone contains no uncheckpointed database content. Keep
                # its exact inventory-bound bytes/mode in both case copies.
                selected_shm = inventory[str(shm.relative_to(original))]
                assert selected_shm["kind"] == "file" and not shm.is_symlink()
                assert selected_shm["size_bytes"] == shm.stat().st_size
                assert selected_shm["sha256"] == _sha(shm.read_bytes())
            historical = directory / name / "historical"
            shutil.copytree(original, historical, symlinks=True)
            assert _inventory(historical) == inventory
            cases[name] = dict(name=name, pin=pin, original=original, original_inventory=inventory,
                historical=historical, evidence=[])
        for case in cases.values():
            database = case["historical"] / case["pin"]["store"] / "state.sqlite3"
            connection = sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)
            case.update(connection=connection, tables=_tables(connection))
        summary_path = cases["native"]["historical"] / "LIFTOVER_TOOL.json"
        raw = summary_path.read_bytes()
        assert len(raw) == 69999 and _sha(raw) == _SUMMARY_SHA
        summary = json.loads(raw)
        assert summary["version"] == "liftover_tool_verification_v1"
        assert summary["native_worker_count"] == 3 and summary["native_conversion_count"] == 2
        assert summary["saved_public_calculator_count"] == 1 and summary["closed_replay_unchanged"] is True
        for case in cases.values():
            case["summary"] = summary
        _guards(guard)
        native_files = [row["stored"]["request"]["chain"]["file"]["artifact_ref"]
            for row in (*summary["originals"], summary["failure"])]
        native_refs = [summary["originals"][0]["stored"]["request"]["chain"]["source_ref"], *native_files]
        for name, case in cases.items():
            refs = native_refs if name == "native" else summary["source_refs"]
            case["application"] = _application(case, directory / name, refs)
        yield cases
        proofs = []
        for case in cases.values():
            application = case["application"]
            tables = _assert_original_rows(application["store"].db, case["tables"])
            assert _tables(case["connection"]) == case["tables"]
            assert _inventory(case["historical"]) == case["original_inventory"]
            assert _inventory(case["original"]) == case["original_inventory"]
            proofs.append(dict(case=case["name"], inventory_sha256=case["pin"]["inventory"],
                recorded_binding=application["recorded_binding"], current_read_side_binding=application["current_read_side_binding"],
                tables=tables, presentations=case["evidence"]))
        (directory / "LIFTOVER_PRESENTATION.json").write_text(json.dumps(dict(
            version="liftover_presentation_verification_v1", cases=proofs,
            current_rendering_only=True, historical_dispatched_instructions_available=False,
            historical_wire_claimed=False, new_decisions=0, new_actions=0, model_calls=0,
            native_calls=0, conversions=0, calculations=0, publications=0,
            original_rows_files_modes_and_grants_unchanged=True), indent=2, allow_nan=False) + "\n")
    finally:
        for case in cases.values():
            if "application" in case:
                case["application"]["store"].close()
            if "connection" in case:
                case["connection"].close()
        guard.undo()


def _render(case, episode_id, call_index, directory):
    request = _request(case["connection"], case, episode_id, call_index)
    context = deepcopy(request["context"])
    original = deepcopy(context)
    application = case["application"]
    flow, store = application["flow"], application["store"]
    records = EpisodeReturnRecords(store, flow.run_id, failure_prefix="liftover_presentation_")
    owner = records.context(episode_id)
    assert plain(owner.request)["goal"]["objective"] == context["goal"]["objective"]
    assert plain(owner.scope) == context["scope"]
    source = _source_for_original_context(flow, owner)
    original_request = plain(source.request.as_record())
    instructions = source.instructions(context)
    assert instructions
    session = _session(directory)
    model_state = instructional_model_context(context)
    text, presented = session._presentation(episode_id, "REASONING", instructions, state_frame(model_state))
    repeated, repeated_instructions = session._presentation(episode_id, "REASONING", instructions,
        state_frame(model_state, model_state))
    assert text == repeated and presented == repeated_instructions
    assert text.startswith("TASK\n") and "\n\nSTEERING\n" in text
    assert presented == text_instructions(instructions) and presented in text
    assert context["goal"]["objective"] in text
    assert context == original and request["context"] == original
    assert plain(source.request.as_record()) == original_request
    case["evidence"].append(dict(episode_id=episode_id, call_index=call_index,
        current_instructions_sha256=_sha(instructions.encode()), current_wire_sha256=_sha(text.encode()),
        original_context_sha256=_sha(_canonical(original).encode()), continuation_identical=True,
        meaning="Current real instruction composition and Session frames over authentic retained context; not historical wire"))
    return context, text, owner


def _literal_rows(value, text, prefix=""):
    for path, scalar in _rows(value, prefix):
        assert "| " + _cell(path) + " | " + _cell(scalar) + " |" in text


@pytest.mark.parametrize("call_index", [1, 2, 3, 5], ids=["plain", "gzip", "malformed", "saved-empty"])
def test_current_scientific_task_and_steering_keep_exact_retained_liftover_values(retained_liftover, tmp_path, call_index):
    case = retained_liftover["native"]
    context, text, _ = _render(case, case["pin"]["episode_id"], call_index, tmp_path / "session")
    assert context["goal"]["objective"] == case["summary"]["question"]
    process = context["scientific_process"]
    information, = process["child_tool_info"]
    assert set(information) == {"name", "resources", "description", "instructions"}
    assert _sha(_canonical(information).encode()) == _TOOL_INFO_SHA
    for name in ("name", "description", "instructions"):
        assert information[name] in text
    assert "Selected tool: " + information["name"] + " (" + information["resources"] + ")" in text
    _literal_rows(process["assignment"]["constraints"], text)
    _literal_rows(process["assignment"]["context"], text)
    outcome = context["last_local_outcome"]
    projection = outcome["result"]
    _literal_rows(projection, text, "result")
    assert projection["version"] == core.RETURN_VERSION and _canonical(projection["point"]) == _canonical(_POINT)
    assert all(item == dict(state="unavailable", label=None, reason="not_provided")
        for item in projection["assembly_context"].values())
    population = projection["population"]
    assert population["mapping_count_scope"] == "full_native_return"
    if call_index == 3:
        assert outcome["status"] == "partial"
        assert population["conversion_call_state"] == "not_started" and population["conversion_call_count"] == 0
        assert population["mapping_count"] is population["native_row_count"] is None
        assert projection["rows"] == []
        assert projection["failure"] == dict(stage="chain_parse", code="chain_parse_failed", location_code="native_failure", occurrence=0)
    else:
        assert population["conversion_call_state"] == "returned" and population["conversion_call_count"] == 1
        assert population["point_state"] == "unique" and population["mapping_count"] == 1
        assert _canonical(projection["rows"]) == _canonical([] if call_index == 5 else [_PLACEMENT])
        assert projection["selected_mapping_ordinals"] == ([] if call_index == 5 else [0])
        assert projection["failure"] is None
    # The exact native name is retained. The integer chain score is not
    # relabelled a probability, mapping confidence or assembly assertion.
    assert "native_chain_score" in text or call_index in (3, 5)


def test_plain_and_gzip_keep_same_science_and_distinct_complete_file_operands(retained_liftover):
    case = retained_liftover["native"]
    projections = [item["projection"] for item in case["summary"]["originals"]]
    left, right = projections
    assert left["source_ref"] != right["source_ref"]
    for key in ("point", "assembly_context", "population", "parsing_state", "selected_mapping_ordinals", "rows", "issues", "failure"):
        assert _canonical(left[key]) == _canonical(right[key])
    files = [item["chain"]["file"] for item in projections]
    assert files[0] != files[1] and [item["format"] for item in files] == ["ucsc_chain", "ucsc_chain_gzip"]
    for item in files:
        assert set(item) == {"artifact_ref", "sha256", "size_bytes", "format"}
        assert item["artifact_ref"] == "artifact_" + item["sha256"] and type(item["size_bytes"]) is int
    contexts = [_request(case["connection"], case, case["pin"]["episode_id"], index)["context"] for index in (1, 2)]
    for context, expected in zip(contexts, projections):
        assert _canonical(context["last_local_outcome"]["result"]) == _canonical(expected)
        text = _values(context["last_local_outcome"]["result"])
        _literal_rows(expected, text)


def test_current_parent_receiver_preserves_frozen_groups_and_opaque_file_provenance(retained_liftover, tmp_path):
    case = retained_liftover["rich"]
    raw = _request(case["connection"], case, case["pin"]["episode_id"], 1)
    assert _sha(_canonical(raw).encode()) == _RICH_REQUEST_SHA
    context, text, owner = _render(case, case["pin"]["episode_id"], 1, tmp_path / "parent-session")
    assert has_molecular_receiver_context(context)
    expected = [item["projection"] for item in case["summary"]["originals"]]
    groups = [item for item in _walk(context["child_reports"])
        if type(item) is dict and item.get("version") == core.RETURN_VERSION]
    assert _canonical(groups) == _canonical(expected)
    assert _values(context["child_reports"]) in text
    _literal_rows(context["child_reports"], text)
    row = case["connection"].execute("SELECT form,facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
        (case["pin"]["run_id"], owner.episode_id)).fetchone()
    assert _canonical(json.loads(row[0])["mappings"]) == _canonical(expected)
    assert _canonical(json.loads(row[1])[core.FACT_SOURCE]) == _canonical(expected)
    received = {row[0] for row in case["connection"].execute("SELECT record_ref FROM runtime_record_receipts WHERE run_id=? AND episode_id=?",
        (case["pin"]["run_id"], owner.episode_id))}
    resolver = case["application"]["flow"].resolver(plain(owner.scope), context=owner)
    for item, original in zip(groups, case["summary"]["originals"]):
        source = original["source"]
        assert item["source_ref"] in received and resolver(item["source_ref"], "source") is True
        private = {source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"]}
        input_file = item["chain"]["file"]["artifact_ref"]
        assert not (private | {input_file}).intersection(received)
        assert all(resolver(reference, "artifact") is False for reference in private)
        assert set(item["chain"]["file"]) == {"artifact_ref", "sha256", "size_bytes", "format"}


def test_onward_frozen_return_does_not_invent_a_missing_historical_model_view(retained_liftover):
    case = retained_liftover["rich"]
    row = case["connection"].execute("SELECT episode_id FROM runtime_episodes WHERE run_id=? AND json_extract(path,'$[1][1]')='child_1'",
        (case["pin"]["run_id"],)).fetchone()
    assert row is not None
    request = _request(case["connection"], case, row[0], 0)
    context = request["context"]
    assert context["child_reports"] == [] and context["current_report_update"] == {}
    assert not any(type(item) is dict and item.get("version") == core.RETURN_VERSION for item in _walk(context))
    expected = [item["projection"] for item in case["summary"]["originals"]]
    forms = list(case["connection"].execute("SELECT form,facts FROM runtime_forms WHERE run_id=?", (case["pin"]["run_id"],)))
    assert len(forms) == 3
    for form, facts in forms:
        assert _canonical(json.loads(form)["mappings"]) == _canonical(expected)
        assert _canonical(json.loads(facts)[core.FACT_SOURCE]) == _canonical(expected)
    case["evidence"].append(dict(onward_episode_id=row[0], original_onward_model_mapping_dto_visible=False,
        exact_onward_frozen_return_present=True, missing_historical_model_view_not_synthesized=True))
