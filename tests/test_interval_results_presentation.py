"""Current interval presentation over explicitly pinned historical evidence.

These are presentation reconstructions, not historical model-wire bytes or new
scientific executions. The original histories and their qualifications remain
literal. Native work, calculations, acquisition and model dispatch are forbidden.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
from types import SimpleNamespace

import pytest

from gene_annotation_episode.decision_context import instructional_model_context, state_frame
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.runtime import DecisionSource, Workflow
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.scientific_process_prompt import (
    _execution_presentation_values, has_molecular_receiver_context,
    render_episode_steering,
)


CASES = ("overlap_complete", "overlap_invalid_c", "overlap_missing_stdout",
    "chromatin_weighted", "chromatin_insulation")


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _inventory(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        name = str(path.relative_to(directory))
        mode = stat.S_IMODE(path.lstat().st_mode)
        if path.is_symlink():
            result[name] = dict(kind="symlink", mode=mode, target=os.readlink(path))
        elif path.is_file():
            raw = path.read_bytes()
            result[name] = dict(kind="file", mode=mode, sha256=_sha(raw), size_bytes=len(raw))
        elif path.is_dir():
            result[name] = dict(kind="directory", mode=mode)
    return result


def _walk(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _domain(name):
    if name.startswith("overlap_"):
        from gene_annotation_episode.genomic_overlap_presentation import (
            genomic_overlap_scientific_job_view, select_genomic_overlap_execution_values,
            select_genomic_overlap_presentation, render_genomic_overlap_projections,
        )
        return dict(version="genomic_overlap_projection_v1", kind="native_genomic_overlap",
            job=genomic_overlap_scientific_job_view, values=select_genomic_overlap_execution_values,
            select=select_genomic_overlap_presentation, render=render_genomic_overlap_projections)
    from gene_annotation_episode.chromatin_interaction_presentation import (
        chromatin_scientific_job_view, select_chromatin_execution_values,
        select_chromatin_presentation, render_chromatin_projections,
    )
    return dict(version="chromatin_interaction_projection_v1", kind="native_chromatin_interactions",
        job=chromatin_scientific_job_view, values=select_chromatin_execution_values,
        select=select_chromatin_presentation, render=render_chromatin_projections)


@pytest.fixture(scope="module", params=CASES)
def retained(request):
    supplied = os.environ.get("HMMER_NATIVE_ORACLE_INTERVAL_PRESENTATION_CASES_JSON")
    if not supplied:
        pytest.skip("requires explicitly selected historical interval evidence and inventory pins")
    cases = json.loads(supplied)
    assert set(cases) == set(CASES)
    selected = cases[request.param]
    assert set(selected) == {"directory", "inventory_sha256"}
    directory = Path(selected["directory"]).resolve(strict=True)
    before = _inventory(directory)
    assert _sha(_canonical(before).encode()) == selected["inventory_sha256"]
    database = directory / "state" / "state.sqlite3"
    assert database.is_file() and not database.is_symlink()
    assert not database.with_name("state.sqlite3-wal").exists()
    assert not database.with_name("state.sqlite3-shm").exists()
    captures = {}
    for path in sorted(directory.glob("decision-*.json")):
        value = json.loads(path.read_bytes())
        assert set(value) in ({"episode_id", "role", "context"},
            {"episode_id", "role", "instructions", "context"})
        captures[path.name] = value
    assert captures
    yield dict(name=request.param, directory=directory, captures=captures,
        configuration=json.loads((directory / "fixture-configuration.json").read_bytes()),
        original_inventory=before, domain=_domain(request.param))
    assert _inventory(directory) == before


def _session(directory):
    # This real object is used only at its pure presentation port. No native
    # conversation is started and no completed model call is manufactured.
    role = dict(model="presentation-engineering-control", reasoning_effort="low")
    return _SessionConnection({"connection": {"command": ["unselected-model-command"]},
        "FAST": role, "REASONING": role, "routing": {}}, directory, directory.parent)


def _projections(case):
    version = case["domain"]["version"]
    result = []
    for capture in case["captures"].values():
        for value in _walk(capture["context"]):
            if isinstance(value, dict) and value.get("version") == version:
                if value not in result:
                    result.append(value)
    assert result
    return result


def _forbidden(*args, **kwargs):
    raise AssertionError("presentation selected native, calculation, File acquisition or model work")


def _guard_work(monkeypatch):
    for name in ("prepare_job", "start_prepared", "resume_start", "wait_job", "status",
            "collect", "cancel", "release"):
        monkeypatch.setattr("gene_annotation_episode.native_lifecycle." + name, _forbidden)
    monkeypatch.setattr("gene_annotation_episode.acquisition.PublicClients._http", _forbidden)
    monkeypatch.setattr("socket.create_connection", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.genomic_overlap_calculations.calculate_genomic_overlap_components", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.chromatin_interaction_calculations.calculate_chromatin_components", _forbidden)
    monkeypatch.setattr(_SessionConnection, "complete", _forbidden)


def _tables(connection):
    result = {}
    for name, sql in connection.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name"):
        columns = [row[1] for row in connection.execute('PRAGMA table_info("' + name.replace('"', '""') + '")')]
        rows = [list(row) for row in connection.execute('SELECT * FROM "' + name.replace('"', '""') + '"')]
        result[name] = dict(sql=sql, columns=columns, rows=sorted(rows, key=_canonical))
    return result


def _assert_original_rows(connection, before):
    current = _tables(connection)
    for name, original in before.items():
        assert name in current and set(original["columns"]) <= set(current[name]["columns"])
        columns = ','.join('"' + column.replace('"', '""') + '"' for column in original["columns"])
        rows = [list(row) for row in connection.execute('SELECT ' + columns + ' FROM "' + name.replace('"', '""') + '"')]
        assert sorted(rows, key=_canonical) == original["rows"]
        added = set(current[name]["columns"]) - set(original["columns"])
        if not added:
            assert current[name]["sql"] == original["sql"]
        for column in added:
            assert all(row[0] is None for row in connection.execute(
                'SELECT "' + column.replace('"', '""') + '" FROM "' + name.replace('"', '""') + '"'))
    for name in set(current) - set(before):
        assert current[name]["rows"] == []
    return {name: dict(columns=value["columns"], row_count=len(value["rows"]),
        rows_sha256=_sha(_canonical(value["rows"]).encode()),
        schema_sha256=_sha(value["sql"].encode()),
        new_empty_table=name not in before,
        added_nullable_columns=sorted(set(value["columns"]) - set(before[name]["columns"]))
            if name in before else []) for name, value in current.items()}


def _read_side_application(case, directory):
    """Compose current readers, retaining every original request verbatim.

    This does not restore the old scientific implementation binding. The new
    read-side application uses today's descriptor over the exact old libraries;
    no old commission is built, selected, run, relabelled or granted anything.
    """
    historical = directory / "historical"
    shutil.copytree(case["directory"], historical, symlinks=True)
    assert _inventory(historical) == case["original_inventory"]
    database = historical / "state" / "state.sqlite3"
    source = sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)
    current_state = directory / "current-state"
    current_state.mkdir()
    destination = sqlite3.connect(current_state / "state.sqlite3")
    try:
        before = _tables(source)
        source.backup(destination)
        assert _tables(destination) == before
        assert source.total_changes == destination.total_changes == 0
    finally:
        destination.close()
        source.close()
    for name in ("artifacts", "cache"):
        if (historical / "state" / name).exists():
            shutil.copytree(historical / "state" / name, current_state / name, symlinks=True)
    application_directory = directory / "current-read-side"
    shutil.copytree(historical / "run", application_directory, symlinks=True)
    configuration = case["configuration"]
    retained_binding = deepcopy(configuration["scientific_binding"])
    library = ScientificProcessLibrary(application_directory / "scientific-process-library")
    tools_library = ScientificToolLibrary(application_directory / "scientific-tool-library")
    assert library.as_record() == retained_binding["configuration"]["library"]
    assert tools_library.as_record() == retained_binding["configuration"]["tool_library"]
    current_binding = ScientificProcessEpisodes(None, library=library, tool_library=tools_library,
        child_roles=retained_binding["configuration"]["child_roles"]).as_record()
    assert current_binding["configuration"] == retained_binding["configuration"]
    store = Store(current_state)
    try:
        episode_id = next(iter(case["captures"].values()))["episode_id"]
        row = store.db.execute("SELECT run_id FROM runtime_episodes WHERE episode_id=?", (episode_id,)).fetchone()
        assert row is not None
        run_id = row[0]
        factory = ExecutionServiceFactory.from_record(configuration["factory"])
        assert factory.as_record() == configuration["factory"]
        if case["name"].startswith("overlap_"):
            from gene_annotation_episode.native_genomic_overlap_contracts import POLICY
        else:
            from gene_annotation_episode.native_chromatin_interaction_contracts import POLICY
        tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
        services = factory(store, run_id=run_id, directory=application_directory, tool_registry=tools)
        provider = SimpleNamespace(complete=_forbidden, release=_forbidden)
        flow = Workflow(store, tools, provider, application_directory, run_id,
            controller_factory=_forbidden, project_credit=_forbidden,
            annotation_child_roles=("scientific_process",), episode_record_receipts=True,
            initial_known_record_refs=configuration["initial_refs"],
            episode_binding_descriptors=(current_binding, *services.episode_binding_descriptors),
            role_credit_bindings=services.role_credit_bindings,
            job_progress_provider=services.job_progress_provider)
        _assert_original_rows(store.db, before)
        return dict(store=store, flow=flow, before=before, historical=historical,
            retained_binding=retained_binding, current_binding=current_binding)
    except BaseException:
        store.close()
        raise


def _source_for_original_context(flow, context):
    request = flow.returned_request({"run_id": context.run_id, "child": {
        "request": plain(context.request), "scope": plain(context.scope),
        "role": context.role, "path": context.path, "episode_id": context.episode_id}})
    assert plain(request.as_record()) == plain(context.request)
    source = DecisionSource(flow, context.path, request, context.scope)
    assert source.episode_id == context.episode_id
    return source


def _retained_receipt_outcomes(case, directory):
    """Join durable controls to original actions on a copied immutable DB.

    The resulting channel is an engineering reconstruction after acquisition.
    A sole original pre-collect model context never supplied these later bytes.
    No original database is opened and no receipt owner is re-executed.
    """
    from gene_annotation_episode.execution_contracts import digest
    if case["name"].startswith("overlap_"):
        from gene_annotation_episode.genomic_overlap_result_receipts import (
            GenomicOverlapResultIntent as Intent, GenomicOverlapResultReceipt as Receipt,
        )
        action_kind = "native-genomic-overlap-actions"
        version = "native_genomic_overlap_acquired_result_v1"
        intent_version = "genomic_overlap_result_intent_v1"
    else:
        from gene_annotation_episode.chromatin_interaction_result_receipts import (
            ChromatinInteractionResultIntent as Intent, ChromatinInteractionResultReceipt as Receipt,
        )
        action_kind = "native-chromatin-interaction-actions"
        version = "native_chromatin_interaction_acquired_result_v1"
        intent_version = "chromatin_interaction_result_intent_v1"
    assert _inventory(case["directory"]) == case["original_inventory"]
    directory.mkdir()
    database = directory / "state.sqlite3"
    shutil.copy2(case["directory"] / "state" / "state.sqlite3", database)
    expected = case["original_inventory"]["state/state.sqlite3"]
    assert _sha(database.read_bytes()) == expected["sha256"]
    connection = sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    result, evidence = [], []
    try:
        for name, pin in sorted(case["original_inventory"].items()):
            parts = Path(name).parts
            if (len(parts) != 6 or parts[:2] != ("run", "execution-results")
                    or parts[3] != action_kind or parts[5] != "receipt.json"):
                continue
            assert pin["kind"] == "file" and pin["mode"] == 0o444
            path = case["directory"] / name
            raw = path.read_bytes()
            assert len(raw) == pin["size_bytes"] and _sha(raw) == pin["sha256"]
            receipt = json.loads(raw)
            assert set(receipt) == set(Receipt.__annotations__) and receipt["version"] == version
            intent = receipt["intent"]
            assert set(intent) == set(Intent.__annotations__) and intent["version"] == intent_version
            assert parts[2] == digest([intent["run_id"], intent["episode_id"]])
            assert parts[4] == digest(intent["operation_key"])
            prefix = intent["run_id"] + ":" + intent["episode_id"] + ":"
            assert intent["operation_key"].startswith(prefix)
            index = int(intent["operation_key"][len(prefix):])
            assert intent["operation_key"] == prefix + str(index)
            row = connection.execute("SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
                (intent["run_id"], intent["episode_id"], index)).fetchone()
            assert row is not None and row["result"] is not None
            action, outcome = json.loads(row["action"]), json.loads(row["result"])
            assert action == {"kind": "tool", "tool": intent["tool_name"], "arguments": intent["arguments"]}
            assert intent["tool_name"] in {"execution.results.collect", "execution.results.status"}
            assert intent["arguments"] == {} and outcome["status"] in {"completed", "partial"}
            assert _canonical(outcome["result"]) == _canonical(receipt)
            episode = connection.execute("SELECT path,request FROM runtime_episodes WHERE run_id=? AND episode_id=?",
                (intent["run_id"], intent["episode_id"])).fetchone()
            assert episode is not None and json.loads(episode["path"]) == intent["path"]
            request = json.loads(episode["request"])
            assert request["message"]["episode_assignment"] == intent["assignment"]
            assert request["message"]["scope"] == intent["scope"]
            assert digest(request) == intent["original_request_sha256"]
            result.append(dict(receipt=receipt, outcome=outcome))
            evidence.append(dict(relative_path=name, sha256=pin["sha256"], size_bytes=pin["size_bytes"],
                operation_key=intent["operation_key"], tool_name=intent["tool_name"],
                original_action_and_full_outcome_joined=True))
        assert result
        assert connection.total_changes == 0
    finally:
        connection.close()
    assert _sha(database.read_bytes()) == expected["sha256"]
    (directory / "AUTHENTIC_RECEIPT_ENGINEERING_INPUTS.json").write_text(json.dumps(dict(
        version="interval_durable_receipt_presentation_inputs_v1", case=case["name"],
        original_database_sha256=expected["sha256"], receipts=evidence,
        channel_meaning="Engineered post-acquisition channel from authentic durable actions, not a captured model context",
        historical_postcollect_model_context_claimed=False), indent=2, allow_nan=False) + "\n")
    return result


def test_retained_projection_channels_deduplicate_without_mutating_or_reading(retained, monkeypatch):
    projections = _projections(retained)
    projection = projections[0]
    state = {"child_reports": [{"selected": [deepcopy(projection)]}],
        "last_local_outcome": {"result": deepcopy(projection)},
        "current_report_update": {"selected": [deepcopy(projection)]},
        "working_state": {"literal_input": deepcopy(projection)},
        "tools": [{"instructions": _canonical(projection)}],
        "requested_form": {"description": _canonical(projection)}}
    lookups = [{"result": deepcopy(projection)}]
    before, original_lookups = deepcopy(state), deepcopy(lookups)
    _guard_work(monkeypatch)
    monkeypatch.setattr("gene_annotation_episode.state.Store.get_artifact", _forbidden)
    selected = retained["domain"]["select"](state, lookup_results=lookups)
    assert selected["projections"] == [projection]
    assert state == before and lookups == original_lookups
    for field in ("working_state", "tools", "requested_form"):
        assert selected["context"][field] == state[field]
    rendered = render_episode_steering(state, lookup_results=lookups)
    label = "Selected genomic overlap result 1" if retained["name"].startswith("overlap_") else "Selected chromatin projection 1"
    # One scientific expansion; references to that expansion may occur in each
    # actual outcome/report/lookup slot.
    assert rendered.count(retained["domain"]["render"]([projection])) == 1
    assert label in rendered
    assert state == before and lookups == original_lookups


def test_genuine_retained_measurements_keep_units_operands_and_missingness(retained, monkeypatch):
    projection = _projections(retained)[0]
    _guard_work(monkeypatch)
    text = retained["domain"]["render"]([projection])
    if retained["name"].startswith("overlap_"):
        rows = {row["comparison_key"]: row for row in projection["pair_rows"]}
        measured = rows["AB"]["measurements"]
        assert measured["unfiltered.native_pair_count"] == 2
        assert measured["unfiltered.pairwise_overlap_bp_sum"] == 8
        assert measured["unfiltered.intersection_union_bp"] == 5
        assert measured["unfiltered.jaccard_bp"] == dict(value=0.3333333333333333,
            numerator=5, denominator=15, missing_reason=None)
        assert "| AB | unfiltered | pairwise_overlap_bp_sum | 8 | bp |" in text
        assert "| AB | unfiltered | intersection_union_bp | 5 | bp |" in text
        assert "| AB | unfiltered | jaccard_bp | 0.3333333333333333 | fraction | 5 | 15 |" in text
        if retained["name"] != "overlap_complete":
            assert projection["result_extent"] == "partial"
            assert rows["AC"]["result_extent"] == "unavailable"
            assert rows["AC"]["measurements"]["unfiltered.native_pair_count"] is None
            reason = "incomplete_input" if retained["name"] == "overlap_invalid_c" else "unavailable_native_result"
            assert rows["AC"]["measurements"]["unfiltered.jaccard_bp"]["missing_reason"] == reason
            assert reason in text and "unavailable" in text and "null" in text
            assert "| AC | unfiltered | native_pair_count | null | occurrence pairs | null | null | null | unavailable |" in text
            assert "not supplied" not in text
            assert rows["BC"]["result_extent"] == ("unavailable" if retained["name"] == "overlap_invalid_c" else "complete")
    elif retained["name"] == "chromatin_weighted":
        first, zero = projection["rows"]
        assert first["fields"]["normalized_contact"]["value"] == 6.0
        assert first["fields"]["expected_contact"]["value"] == 7.0
        ratio = first["fields"]["fold_enrichment"]
        assert (ratio["value"], ratio["numerator"], ratio["denominator"]) == (0.8571428571428571, 6.0, 7.0)
        assert zero["fields"]["raw_contact"]["value"] == 0
        assert zero["fields"]["fold_enrichment"]["value"] is None
        assert zero["fields"]["fold_enrichment"]["reason"] == "zero_denominator"
        assert "| 2 | p1 | raw_contact | 0 |" in text
        assert "| 2 | p1 | fold_enrichment | null |" in text
        for literal in ("precomputed_weighted", "multiplicative", "zero_denominator",
                "not_measured", "0.8571428571428571", "6.0", "7.0"):
            assert literal in text
    else:
        assert projection["parameters"]["insulation"]["threshold_comparison"] == "strict_lt"
        assert projection["parameters"]["insulation"]["z_threshold"] == -1
        assert [row["fields"]["cross_contact_sum"]["value"] for row in projection["rows"]] == [5, 1, 5, 1, 5]
        assert [row["fields"]["is_boundary"]["value"] for row in projection["rows"]] == [False, True, False, True, False]
        assert projection["rows"][1]["fields"]["insulation_z"]["value"] == -1.224744871391589
        for literal in ("strict_lt", "heuristic_prediction", "unknown", "ineligible_edge", "-1.224744871391589"):
            assert literal in text


def test_unknown_and_invalid_projection_stay_literal(retained, monkeypatch):
    projection = deepcopy(_projections(retained)[0])
    projection["unexpected_presentation_field"] = "literal qualification remains"
    state = {"child_reports": [{"selected": [projection]}]}
    _guard_work(monkeypatch)
    selected = retained["domain"]["select"](state)
    assert selected["context"] == state and selected["projections"] == []
    assert not has_molecular_receiver_context(state)
    assert "literal qualification remains" in render_episode_steering(state)
    assert retained["domain"]["values"]({"arbitrary": projection}) is None


def test_unrelated_versioned_records_and_nested_input_slots_stay_opaque(retained, monkeypatch):
    projection = deepcopy(_projections(retained)[0])
    unrelated = {"version": "unrelated_caller_record_v1", "nested": projection}
    inputs = {key: deepcopy(projection) for key in
        ("instructions", "schema", "input_schema", "output_schema", "result_selector_schema",
            "schema_json", "requested_form", "tools", "inputs", "request", "assignment")}
    state = {"last_local_outcome": {"result": unrelated},
        "child_reports": [inputs], "current_report_update": {"input": projection}}
    lookups = [{"result": unrelated}, inputs]
    before = deepcopy(state)
    _guard_work(monkeypatch)
    selected = retained["domain"]["select"](state, lookup_results=lookups)
    assert selected["context"] == state == before
    assert selected["lookup_results"] == lookups and selected["projections"] == []
    assert not has_molecular_receiver_context(state)


def test_selected_receipt_view_remains_recognized_before_generic_masking(retained, tmp_path, monkeypatch):
    _guard_work(monkeypatch)
    observed = []
    for authentic in _retained_receipt_outcomes(retained, tmp_path / "durable-receipts"):
        selected = retained["domain"]["select"]({"last_local_outcome": authentic["outcome"]})
        for value in _walk(selected["context"].get("last_local_outcome")):
            if isinstance(value, dict) and value.get("version") in {
                    "genomic_overlap_result_receipt_view_v1", "chromatin_result_receipt_view_v1"}:
                assert retained["domain"]["values"](value) == value
                assert _execution_presentation_values(value) == value
                observed.append(value)
    assert observed


def test_unrequested_private_receipt_siblings_cannot_change_public_presentation(retained, tmp_path, monkeypatch):
    _guard_work(monkeypatch)
    monkeypatch.setattr(Store, "get_artifact", _forbidden)
    for authentic in _retained_receipt_outcomes(retained, tmp_path / "durable-receipts"):
        before = retained["domain"]["select"]({"last_local_outcome": authentic["outcome"]})
        changed = deepcopy(authentic["receipt"])
        marker = "unrequested-private-control-must-not-be-rendered"
        changed["projection"] = {"invalid_unrequested_sibling": marker}
        changed["host_failures"] = [{"invalid_unrequested_sibling": marker}]
        changed["intent"]["target"] = {"invalid_unrequested_sibling": marker}
        outcome = deepcopy(authentic["outcome"])
        outcome["result"] = changed
        state = {"last_local_outcome": outcome}
        after = retained["domain"]["select"](state)
        assert before["context"] != {"last_local_outcome": authentic["outcome"]}
        assert after["context"] == before["context"]
        assert after["projections"] == before["projections"]
        assert marker not in render_episode_steering(state)


def test_saved_callable_file_identities_survive_early_execution_projection(retained, monkeypatch):
    _guard_work(monkeypatch)
    selectors = [capture["context"]["execution_assignment"]["selector"]
        for capture in retained["captures"].values()
        if capture["context"].get("execution_assignment", {}).get("selector", {}).get("mode") == "saved_sheet_recalculation"]
    if not selectors:
        assert retained["name"] in {"overlap_invalid_c", "overlap_missing_stdout"}
        return
    for selector in selectors:
        original = deepcopy(selector)
        projected = _execution_presentation_values(selector)
        files = [value for value in _walk(selector) if isinstance(value, dict)
            and set(value) == {"artifact_ref", "format", "sha256", "size_bytes"}]
        assert files
        for file in files:
            assert file in list(_walk(projected))
        assert selector == original


def test_current_receiver_route_uses_only_real_return_channels(retained, tmp_path, monkeypatch):
    projection = deepcopy(_projections(retained)[0])
    # This explicitly labelled current receiving reconstruction carries an
    # original retained projection; it does not invent a historical callback.
    capture = deepcopy(next(iter(retained["captures"].values())))
    state = {"goal": deepcopy(capture["context"]["goal"]),
        "scope": deepcopy(capture["context"]["scope"]),
        "child_reports": [{"selected": [projection]}]}
    session = _session(tmp_path / "receiver")
    _guard_work(monkeypatch)
    assert has_molecular_receiver_context(state)
    text, _ = session._presentation("current-receiver-reconstruction", "REASONING", "",
        state_frame(instructional_model_context(state)))
    assert text.startswith("TASK") and "STEERING" in text
    assert retained["domain"]["render"]([projection]) in text
    unrelated = {"goal": state["goal"], "working_state": {"caller_input": projection}}
    assert not has_molecular_receiver_context(unrelated)
    other, instructions = session._presentation("unrelated", "REASONING", "literal instructions", unrelated)
    assert json.loads(other) == unrelated and instructions == "literal instructions"


def test_authentic_scientific_frames_preserve_literal_steering_and_recorded_guidance(retained, tmp_path, monkeypatch):
    captures = [(name, value) for name, value in retained["captures"].items()
        if "scientific_process" in value["context"]]
    assert captures
    if retained["name"].startswith("chromatin_"):
        assert [name for name, _ in captures] == ["decision-1.json", "decision-4.json", "decision-6.json"]
    session = _session(tmp_path / "retained-scientific-presentation")
    _guard_work(monkeypatch)
    previous = None
    evidence = []
    for name, capture in captures:
        state = deepcopy(capture["context"])
        original = deepcopy(state)
        selected = retained["domain"]["select"](state)
        steering = render_episode_steering(state)
        if selected["projections"]:
            assert retained["domain"]["render"](selected["projections"]) in steering
        process = state["scientific_process"]
        assert process["child_tool_info"]
        if "instructions" in capture:
            # G1 captures retain their actual dispatched instruction bytes.
            # This renders those bytes now; it does not assert that the old
            # provider used today's presentation implementation.
            model_state = instructional_model_context(state)
            text, _ = session._presentation(capture["episode_id"], "REASONING",
                capture["instructions"], state_frame(model_state, previous))
            assert state["goal"]["objective"] in text and capture["instructions"] in text
            for information in process["child_tool_info"]:
                assert information["name"] in text
                assert information["description"] in text and information["instructions"] in text
            assert text.startswith("TASK") and "STEERING" in text
            previous = model_state
            mode = "current_presentation_with_recorded_G1_instructions"
        else:
            assert retained["name"].startswith("chromatin_")
            mode = "current_literal_STEERING_only_original_instructions_not_recorded"
        assert state == original and capture["context"] == original
        evidence.append(dict(capture=name, mode=mode,
            current_steering_sha256=_sha(steering.encode()),
            original_context_sha256=_sha(_canonical(original).encode()),
            projection_count=len(selected["projections"])))
    (tmp_path / "INTERVAL_SCIENTIFIC_PRESENTATION.json").write_text(json.dumps(dict(
        version="interval_scientific_presentation_reconstruction_v1", case=retained["name"],
        presentations=evidence, historical_wire_bytes_claimed=False,
        chromatin_current_SCI_instruction_compatibility_claimed=False), indent=2, allow_nan=False) + "\n")


def test_original_results_task_helper_and_current_presentation_preserve_guidance(retained, tmp_path, monkeypatch):
    from gene_annotation_episode.execution_contracts import validate_target
    _guard_work(monkeypatch)
    application = _read_side_application(retained, tmp_path)
    store, flow = application["store"], application["flow"]
    session = _session(tmp_path / "current-results-presentation")
    evidence = []
    try:
        for name in ("put", "artifact", "commit_reasoning"):
            monkeypatch.setattr(Store, name, _forbidden)
        monkeypatch.setattr(ToolRegistry, "execute_async", _forbidden)
        monkeypatch.setattr(Workflow, "build", _forbidden)
        monkeypatch.setattr(Workflow, "selected", _forbidden)
        monkeypatch.setattr(DecisionSource, "call", _forbidden)
        monkeypatch.setattr(DecisionSource, "next", _forbidden)
        records = EpisodeReturnRecords(store, flow.run_id,
            failure_prefix="interval_presentation_original_")
        for name, capture in retained["captures"].items():
            if "execution_assignment" not in capture["context"] or "selector" not in capture["context"]["execution_assignment"]:
                continue
            context = records.context(capture["episode_id"])
            assert context.role == "results"
            original_request = plain(context.request)
            assert plain(context.assignment) == capture["context"]["execution_assignment"]
            recorded_contexts = [json.loads(row[0])["context"] for row in store.db.execute(
                "SELECT request FROM runtime_model_calls WHERE run_id=? AND episode_id=? ORDER BY call_index",
                (flow.run_id, context.episode_id))]
            assert _canonical(capture["context"]) in {_canonical(value) for value in recorded_contexts}
            original_context = deepcopy(capture["context"])
            assert "selected_execution_task" not in original_context
            source = _source_for_original_context(flow, context)
            binding = flow.specialist(source)
            # Full current decision_context cannot authenticate relocated old
            # worker/Artifact paths. Exercise only the changed helper over the
            # exact historical target, never stub or relax those readers.
            supplied = binding._with_selected_execution_task(context, deepcopy(original_context))
            parent = flow.services.scientific_parent_task(context)
            assert parent is not None and parent["selected_tool_info"]
            task = supplied["selected_execution_task"]
            assert task["scientific_question"] == parent["scientific_question"]
            assert task["selected_tool_info"] == parent["selected_tool_info"]
            assert len(task["requests"]) == 1
            target = validate_target(original_context["execution_target"])
            job = target["assignment"]["requested_job"][retained["domain"]["kind"]]
            assert task["requests"][0]["job"] == retained["domain"]["job"](job)
            state = supplied
            for field, value in original_context.items():
                assert state[field] == value
            instructions = source.instructions(state)
            before_state = deepcopy(state)
            model_state = instructional_model_context(state)
            first = state_frame(model_state)
            text, model_instructions = session._presentation(context.episode_id, "REASONING", instructions, first)
            assert text.startswith("TASK") and "STEERING" in text
            assert task["scientific_question"] in text
            for information in task["selected_tool_info"]:
                assert information["name"] in text
                assert information["description"] in text and information["instructions"] in text
            assert instructions in text and model_instructions == instructions
            # A real continuation frame repeats the same supplied TASK. The
            # newly selected interval views remain literal, with no work call.
            second = state_frame(model_state, model_state)
            again, _ = session._presentation(context.episode_id, "REASONING", instructions, second)
            assert again == text and state == before_state
            assert plain(context.request) == original_request
            assert capture["context"] == original_context
            evidence.append(dict(capture=name, episode_id=context.episode_id,
                selector=plain(context.assignment)["selector"],
                scientific_question=task["scientific_question"],
                selected_tool_info=task["selected_tool_info"],
                original_context_sha256=_sha(_canonical(original_context).encode()),
                current_context_sha256=_sha(_canonical(state).encode()),
                current_wire_sha256=_sha(text.encode()),
                current_instructions_sha256=_sha(instructions.encode())))
        assert evidence
        tables = _assert_original_rows(store.db, application["before"])
        assert _inventory(application["historical"]) == retained["original_inventory"]
        (tmp_path / "INTERVAL_RESULTS_TASK_HELPER_RECONSTRUCTION.json").write_text(json.dumps(dict(
            version="interval_results_task_helper_presentation_reconstruction_v1",
            case=retained["name"], passed=True,
            meaning="Current production task helper and presentation over authentic captured targets; not full decision-context building, historical wire or composition compatibility",
            task_helper_verified=True, full_current_builder_verified=False,
            full_builder_limitation="Original481 five full-builder checks rejected relocated worker directories; worker directory and retained Artifact paths remain bound to literal original owner/Store roots",
            original481_full_builder_failures_preserved=True,
            current_callable_catalog_rebuilt=False, captured_callable_catalog_preserved=True,
            original_binding=application["retained_binding"],
            current_read_side_binding=application["current_binding"],
            original_inventory_sha256=_sha(_canonical(retained["original_inventory"]).encode()),
            original_rows_unchanged=True, current_tables=tables, presentations=evidence,
            native_calls=0, calculator_calls=0, model_calls=0, new_decisions=0,
            new_actions=0, publications=0), indent=2, allow_nan=False) + "\n")
    finally:
        store.close()
