"""Literal profile views and one fresh pending Results call; never execute science.

The two historical physical families are copied before any SQLite connection.
Infernal6/8 are authentic SCI captures, not a surviving Infernal Store. Engineered
Infernal carriers below test presentation shape only and establish no custody.
"""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import sqlite3

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import instructional_model_context, state_frame
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.native_profile_presentation import (
    native_profile_scientific_job_view, select_native_profile_execution_values,
    select_native_profile_presentation, render_native_profile_results,
    has_native_profile_receiver_context,
)
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_interval_pending_results import _commission, _new_rows
from test_interval_results_presentation import (
    _assert_original_rows, _canonical, _inventory, _session, _sha, _tables, _source_for_original_context,
)
from test_native_hmmer_preparation_nested_workflow import provider_value


_GATE = "HMMER_NATIVE_ORACLE_PROFILE_PRESENTATION_CASES_JSON"
_PINS = {
    "hmmer_native": "49e44a2bfc1df4fdc6d8cc48745ccfd0f74b465fa755f4bb778bbadeef019a5b",
    "hmmer_preparation": "0fd9c4e041b976415dea704b7e218334a7098cc95624f3c620f58cb33bfe97d2",
}
_RECEIPTS = {
    "hmmer_native": ("156b1e4544f6c532ed68f3dc481c0628fd489b60202c8bebfb2f8ffc4a1962f5",
        "native-hmmer-actions/2a45fc78b2cbacf4e4afdbab0254cb1aaea4915ef943229bd86811b32315b27d",
        "267f4624b91b8674f1edc586afb904ed2bb285fa237749c4cfb0db6ad3327c35", 12958),
    "hmmer_preparation": ("b9068d63e692eaeac4ac87a04792634424601bbf6428ab0cc639325ec2886883",
        "native-hmmer-preparation-actions/9e03ef5533e69bd39faed1831b012b9334d9aafd0477ae627ea622747aecb31f",
        "9243e6fcc0928ec1556266d96a47681d5df4b9009e449e0ec39917376399060a", 17260),
}
_KINDS = ("native_hmmer", "native_infernal", "native_hmmer_preparation", "native_infernal_preparation")
_HANDOFF = "source_ecbbd55db164e6290f228fba"
_PORTABLE = {
    "scientific-decision-6.json": ("d3b8960802bd7988baea133989d40c3cbbc4ad429f35b8f1c8bb2a43e8cbbe45", 150420),
    "scientific-decision-8.json": ("eb7e5d97811180d2e8bc2eb27e561a2006267dd06ccac6e5efac054c8a7b365b", 154863),
}


def _forbidden(*args, **kwargs):
    raise AssertionError("profile presentation attempted native/scientific/worker/model/HTTP/publication work")


def _guards(patch):
    # Guard calls, not package imports: Session has unrelated SciPy imports.
    for name in ("prepare_job", "start_prepared", "resume_start", "wait_job", "status", "collect", "cancel", "release"):
        patch.setattr("gene_annotation_episode.native_lifecycle." + name, _forbidden)
    for family, owner in (("hmmer", "NativeHMMERResults"), ("infernal", "NativeInfernalResults"),
            ("hmmer_preparation", "NativeHmmerPreparationResults"),
            ("infernal_preparation", "NativeInfernalPreparationResults")):
        patch.setattr("gene_annotation_episode.native_" + family + "_results." + owner + ".execute", _forbidden)
        patch.setattr("gene_annotation_episode.native_" + family + "_result_worker.run", _forbidden)
    for target in (
        "gene_annotation_episode.hmmer_graders.grade_hmmer_native_artifacts",
        "gene_annotation_episode.native_hmmer_preparation_worker.grade_hmmer_preparation",
        "gene_annotation_episode.native_hmmer_preparation_worker.recalculate_hmmer_preparation",
        "gene_annotation_episode.native_infernal_preparation_worker.grade_infernal_preparation",
        "gene_annotation_episode.native_infernal_preparation_worker.recalculate_infernal_preparation",
        "gene_annotation_episode.cmalign_grader.calculate_cmalign_scores",
        "gene_annotation_episode.infernal_search_grader.calculate_infernal_search_scores",
        "gene_annotation_episode.hmmer_search_grader.calculate_hmmer_search_scores",
    ):
        patch.setattr(target, _forbidden)
    patch.setattr("gene_annotation_episode.acquisition.PublicClients._http", _forbidden)
    patch.setattr("socket.create_connection", _forbidden)
    patch.setattr("socket.socket.connect", _forbidden)
    patch.setattr("socket.socket.connect_ex", _forbidden)
    patch.setattr(_SessionConnection, "complete", _forbidden)
    patch.setattr(ToolRegistry, "execute_async", _forbidden)
    patch.setattr(ToolRegistry, "_sequence_worker_async", _forbidden)
    for name in ("put", "artifact", "commit_reasoning"):
        patch.setattr(Store, name, _forbidden)


def _json(path, sha, size):
    raw = path.read_bytes()
    assert (_sha(raw), len(raw)) == (sha, size)
    return json.loads(raw)


@pytest.fixture(scope="module")
def profile_cases(tmp_path_factory):
    supplied = os.environ.get(_GATE)
    if not supplied:
        pytest.skip("requires the explicitly pinned native HMMER and277 preparation cases")
    selected = json.loads(supplied)
    assert set(selected) == set(_PINS)
    directory = tmp_path_factory.mktemp("native-profile-input")
    cases = {}
    with pytest.MonkeyPatch.context() as patch:
        _guards(patch)
        # Both complete physical families precede the first SQLite open.
        for name, expected in _PINS.items():
            item = selected[name]
            assert set(item) == {"directory", "inventory_sha256"} and item["inventory_sha256"] == expected
            original = Path(item["directory"]).resolve(strict=True)
            inventory = _inventory(original)
            assert _sha(_canonical(inventory).encode()) == expected
            copied = directory / name
            shutil.copytree(original, copied, symlinks=True)
            assert _inventory(copied) == inventory
            database = copied / "state/state.sqlite3"
            wal = database.with_name(database.name + "-wal")
            assert not wal.exists() or wal.stat().st_size == 0, "nonempty WAL needs consolidated authority"
            cases[name] = dict(name=name, original=original, directory=copied, inventory=inventory)
        try:
            for name, case in cases.items():
                database = case["directory"] / "state/state.sqlite3"
                db = sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)
                db.row_factory = sqlite3.Row
                case.update(db=db, tables=_tables(db))
                stem, suffix, sha, size = _RECEIPTS[name]
                path = case["directory"] / "run/execution-results" / stem / suffix / "receipt.json"
                case["receipt"] = _json(path, sha, size)
                assert case["receipt"]["complete"] is True
                assignment = json.loads(db.execute("SELECT request FROM runtime_episodes WHERE run_id=? AND episode_id=?",
                    (case["receipt"]["run_id"], case["receipt"]["episode_id"])).fetchone()[0])["message"]["episode_assignment"]
                assert assignment == case["receipt"]["assignment"]
                context = json.loads(db.execute("SELECT request FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index=0",
                    (case["receipt"]["run_id"], case["receipt"]["episode_id"])).fetchone()[0])["context"]
                case["context"] = context
                kind = "native_hmmer" if name == "hmmer_native" else "native_hmmer_preparation"
                case["job"] = deepcopy(case["receipt"]["target"]["assignment"]["requested_job"][kind])
            portable = {}
            for name, (sha, size) in _PORTABLE.items():
                portable[name] = _json(Path(__file__).parent / "fixtures/native_infernal_episode" / name, sha, size)
            cases["portable"] = portable
            yield cases
            for name in _PINS:
                case = cases[name]
                assert _tables(case["db"]) == case["tables"] and case["db"].total_changes == 0
        finally:
            for name in _PINS:
                case = cases[name]
                if "db" in case:
                    case["db"].close()
                assert _inventory(case["directory"]) == case["inventory"]
                assert _inventory(case["original"]) == case["inventory"]


def _job(cases, kind):
    if kind in {"native_hmmer", "native_hmmer_preparation"}:
        return deepcopy(cases["hmmer_native" if kind == "native_hmmer" else "hmmer_preparation"]["job"])
    # Clearly engineered request metadata; no native work or receipt asserted.
    if kind == "native_infernal":
        job = deepcopy(cases["hmmer_native"]["job"])
        job.pop("mode")
        job.update(version="native_infernal_job_v1", program="cmsearch", table_format=1,
            options=["--cpu", "1"],
            operands=[dict(role=role, path="/engineered/unselected/" + role, format=fmt,
                artifact_ref=None, sha256="1" * 64, size_bytes=1)
                for role, fmt in (("models", "infernal_ascii"), ("sequences", "fasta"))],
            operand_bindings=[], outputs=[dict(role=role, format=fmt, relative_path="outputs/" + role)
                for role, fmt in (("stdout", "infernal_stdout"), ("stderr", "text"), ("tblout", "infernal_tblout"))])
    else:
        job = deepcopy(cases["hmmer_preparation"]["job"])
        job.pop("input_metadata")
        job.update(version="native_infernal_preparation_job_v1", program="cmemit", mode="consensus")
        job["operands"][0].update(format="infernal_cm_ascii", path="/engineered/unselected/models", artifact_ref=None)
        for row in job["outputs"]:
            if row["role"] in {"stdout", "stderr"}:
                row["format"] = "infernal_" + row["role"]
    job["software"] = dict(executable="/engineered/unselected/" + job["program"], sha256="2" * 64, engine_version="1.1.5")
    return job


def _carrier(cases, kind):
    if kind in {"native_hmmer", "native_hmmer_preparation"}:
        return deepcopy(cases["hmmer_native" if kind == "native_hmmer" else "hmmer_preparation"]["receipt"])
    # UI-only carriers; no inferred native/SQL/Source authority for Infernal.
    row = deepcopy(cases["portable"]["scientific-decision-6.json"]["context"]["child_reports"][1]["rows"][0])
    carrier = deepcopy(cases["hmmer_native" if kind == "native_infernal" else "hmmer_preparation"]["receipt"])
    carrier.update(version=kind + "_acquired_result_v1", complete=False,
        observation=dict(state="unknown", returncode=None))
    if kind == "native_infernal":
        carrier.update(source_ref=row["source_ref"], record_refs=[row["source_ref"], row["observation_ref"], *row["reference_refs"]], rows=[row])
        carrier["assignment"]["selector"] = dict(version="native_infernal_result_selector_v1",
            acquisition="complete_bound_bundle", projection=dict(family="search_hit", metrics=["bitscore"], rows=dict(offset=0, limit=1)))
    else:
        carrier.update(source_ref=None, record_refs=[], rows=[], artifacts=[], population=None)
        carrier["assignment"]["selector"] = dict(version="native_infernal_preparation_result_selector_v1",
            acquisition="complete_bound_bundle", projection=None,
            artifacts=[dict(direction="output", role="stdout", ordinal=0)])
    return carrier


@pytest.mark.parametrize("kind", _KINDS)
def test_four_finite_jobs_preserve_science_and_complete_input_identities(profile_cases, kind):
    job = _job(profile_cases, kind)
    before = deepcopy(job)
    view = native_profile_scientific_job_view(job)
    assert view["kind"] == kind and select_native_profile_execution_values(view) == view
    expected = {k: deepcopy(v) for k, v in job.items() if k not in {"version", "environment"}}
    expected["software"] = {"engine_version": job["software"]["engine_version"]}
    expected["operands"] = [{k: v for k, v in row.items() if k != "path"} for row in job["operands"]]
    expected["outputs"] = [{k: v for k, v in row.items() if k != "relative_path"} for row in job["outputs"]]
    assert view["job"] == expected and job == before
    for original, selected in zip(job["operands"], view["job"]["operands"]):
        assert all(selected[k] == original[k] for k in ("artifact_ref", "format", "sha256", "size_bytes"))


@pytest.mark.parametrize("kind", ("native_hmmer", "native_infernal"))
def test_unknown_caller_metadata_is_opaque_retained_data(profile_cases, kind):
    job = _job(profile_cases, kind)
    job["metadata"]["caller_association"] = dict(path="literal caller path", values=[None, 0, False],
        nested_receipt=_carrier(profile_cases, "native_hmmer"))
    view = native_profile_scientific_job_view(job)
    assert view["job"]["metadata"] == job["metadata"]
    state = {"last_local_outcome": {"metadata": view["job"]["metadata"]}}
    selected = select_native_profile_presentation(state)
    assert selected["context"] == state and selected["projections"] == []


@pytest.mark.parametrize("kind", _KINDS)
def test_public_receipts_reenter_deduplicate_and_ignore_unrequested_controls(profile_cases, kind):
    raw = _carrier(profile_cases, kind)
    before = deepcopy(raw)
    view = select_native_profile_execution_values(raw)
    assert view is not None and view["kind"] == kind
    assert select_native_profile_execution_values(view) == view
    for name in ("capture", "prepared", "target", "failures"):
        raw[name] = {"engineered_invalid_private_sibling": True}
    assert select_native_profile_execution_values(raw) == view
    selected = select_native_profile_presentation({"last_local_outcome": {"result": raw}, "child_reports": [raw]}, lookup_results=[raw])
    assert selected["projections"] == [view]
    assert selected["lookup_results"] == ["Selected profile result 1"]
    assert select_native_profile_presentation(selected["context"])["context"] == selected["context"]
    assert before != raw and view["rows"] == before["rows"]
    assert "Selected profile result 1" in render_native_profile_results([view])
    assert has_native_profile_receiver_context({"last_local_outcome": raw})
    literal_rows = {"child_reports": [{"rows": deepcopy(view["rows"])}]}
    assert not has_native_profile_receiver_context(literal_rows)
    assert select_native_profile_presentation(literal_rows)["context"] == literal_rows
    from gene_annotation_episode import hmmer_native_result_views, infernal_native_result_views
    from gene_annotation_episode import hmmer_preparation_result_views, infernal_preparation_result_views
    facts = {
        "native_hmmer": hmmer_native_result_views.native_hmmer_fact_sources,
        "native_infernal": infernal_native_result_views.native_infernal_fact_sources,
        "native_hmmer_preparation": hmmer_preparation_result_views.preparation_fact_sources,
        "native_infernal_preparation": infernal_preparation_result_views.preparation_fact_sources,
    }[kind]()
    name = next(iter(facts))
    capability = {"available_report_facts": {name: deepcopy(facts[name])}}
    assert has_native_profile_receiver_context(capability)
    capability["available_report_facts"][name]["meaning"] = "engineered changed declaration"
    assert not has_native_profile_receiver_context(capability)


def test_authentic_native_metrics_unknown_identity_and_preparation_populations(profile_cases):
    native = select_native_profile_execution_values(profile_cases["hmmer_native"]["receipt"])
    row, = native["rows"]
    assert row["measurements"] == [dict(name="paired_positions", value=20),
        dict(name="paired_model_coverage", value=1.0), dict(name="native_domain_score_bits", value=72.1),
        dict(name="native_independent_evalue", value=1.1e-24)]
    assert row["unavailable"] == [dict(name="sequence_identity_fraction", reason="missing_input")]
    prep = select_native_profile_execution_values(profile_cases["hmmer_preparation"]["receipt"])
    assert prep["population"]["total_records"] == prep["population"]["returned_records"] == 3
    assert prep["population"]["requested_artifact_count"] == 3 and len(prep["artifacts"]) == 4
    assert [x["role"] for x in prep["artifacts"]] == ["stdout", "stderr", "generated_sequences", "models"]
    assert prep["rows"][0]["quantities"][:3] == [dict(path="length", value=12, state="present", unit="residue_count"),
        dict(path="canonical_residue_count", value=12, state="present", unit="residue_count"),
        dict(path="ambiguous_residue_count", value=0, state="present", unit="residue_count")]
    text = render_native_profile_results([native, prep])
    assert "1.1e-24" in text and "missing_input" in text and "residues_per_captured_record" in text
    assert "retained scientific acquisition" in text


def test_repeated_requested_hmmer_checks_preserve_distinct_occurrences(profile_cases):
    raw = deepcopy(profile_cases["hmmer_preparation"]["receipt"])
    check = deepcopy(raw["rows"][1]["checks"][0])
    assert check["name"] == "sample_population_count" and len(check["occurrences"]) == 2
    check["occurrences"] = check["occurrences"][:1]
    raw["rows"][1]["checks"].insert(0, check)
    view = select_native_profile_execution_values(raw)
    assert view is not None and view["rows"][1]["checks"] == raw["rows"][1]["checks"]


def test_engineered_infernal_preparation_checks_keep_native_order(profile_cases):
    raw = _carrier(profile_cases, "native_infernal_preparation")
    source = profile_cases["hmmer_preparation"]["receipt"]["source_ref"]
    requested = ["cmemit_model_association", "cmemit_sequence_count_matches"]
    raw.update(source_ref=source, record_refs=[source], rows=[dict(record_key="engineered:calculation",
        kind="calculation", name=None, accession=None, source_ref=source, artifact_ref=None,
        quantities=[], checks=[dict(name=name, outcome="unknown", occurrences=[]) for name in reversed(requested)])],
        population=dict(source_ref=source, collection="calculations", total_records=1, returned_records=1,
            omitted_records=0, requested_artifact_count=0, returned_artifact_count=0,
            missing_record_keys=[], missing_artifacts=[]))
    raw["assignment"]["selector"]["projection"] = dict(collection="calculations", quantities=[],
        checks=requested, rows=dict(offset=0, limit=10))
    raw["assignment"]["selector"]["artifacts"] = []
    view = select_native_profile_execution_values(raw)
    assert view is not None and view["rows"] == raw["rows"]


@pytest.mark.parametrize("fault", ("omitted_check", "unrequested_check", "omitted_quantity", "population_count"))
def test_preparation_public_selection_relationships_reject_conflicts(profile_cases, fault):
    raw = deepcopy(profile_cases["hmmer_preparation"]["receipt"])
    if fault == "omitted_check":
        raw["rows"][0]["checks"].pop()
    elif fault == "unrequested_check":
        raw["rows"][0]["checks"].append(dict(name="artifact_binding", outcome="unknown", occurrences=[]))
    elif fault == "omitted_quantity":
        raw["rows"][0]["quantities"].pop()
    else:
        raw["population"]["returned_records"] = 2
    assert select_native_profile_execution_values(raw) is None


@pytest.mark.parametrize("slot", ("input_schema", "output_schema", "schema_json", "result_selector_schema", "instructions", "input", "arguments", "working_state"))
def test_opaque_slots_and_unknown_packets_do_not_extract_embedded_receipts(profile_cases, slot):
    raw = profile_cases["hmmer_native"]["receipt"]
    value = {"last_local_outcome": {slot: {"embedded": deepcopy(raw)}}}
    result = select_native_profile_presentation(value)
    assert result["context"] == value and result["projections"] == []
    unknown = {"last_local_outcome": {"version": "unrelated_result_v1", "result": deepcopy(raw)}}
    assert select_native_profile_presentation(unknown)["context"] == unknown


@pytest.mark.parametrize("fault", ("wrong_source", "duplicate_metric", "extra_metric", "selection_conflict", "wrong_returncode"))
def test_malformed_public_selection_stays_uninterpreted(profile_cases, fault):
    raw = deepcopy(profile_cases["hmmer_native"]["receipt"])
    if fault == "wrong_source":
        raw["rows"][0]["source_ref"] = "source_" + "f" * 24
    elif fault == "duplicate_metric":
        raw["rows"][0]["measurements"].append(deepcopy(raw["rows"][0]["measurements"][0]))
    elif fault == "extra_metric":
        raw["rows"][0]["measurements"].append(dict(name="model_length", value=20))
    elif fault == "selection_conflict":
        raw["assignment"]["selector"]["projection"]["metrics"] = ["paired_positions"]
    else:
        raw["observation"]["returncode"] = True
    assert select_native_profile_execution_values(raw) is None
    selected = select_native_profile_presentation({"last_local_outcome": raw})
    assert selected["context"]["last_local_outcome"] == raw and selected["projections"] == []


def test_portable_infernal_current_scientific_frames_keep_requested_rows_only(profile_cases, tmp_path):
    session = _session(tmp_path / "infernal-views")
    previous = None
    for name in _PORTABLE:
        saved = profile_cases["portable"][name]
        current = saved["context"]
        state = instructional_model_context(current)
        wire, instructions = session._presentation(saved["episode_id"], saved["role"], saved["instructions"], state_frame(state, previous))
        assert wire.startswith("TASK") and "STEERING" in wire and current["goal"]["objective"] in wire
        assert instructions == saved["instructions"] and instructions in wire
        assert all(info["instructions"] in wire for info in current["scientific_process"]["child_tool_info"])
        assert current["child_reports"][1]["rows"][0]["measurements"] == [dict(name="bitscore", value=71.4)]
        previous = state
    assert current["child_reports"][2]["rows"][0]["measurements"] == [dict(name="evalue", value=3.6e-22)]
    repeated, _ = session._presentation(saved["episode_id"], saved["role"], saved["instructions"], state_frame(previous, previous))
    assert repeated == wire


def test_new_current_preparation_toolinfo_does_not_rewrite_original277_library(profile_cases, tmp_path):
    from gene_annotation_episode.native_hmmer_preparation_tool_info import native_hmmer_preparation_tool_contracts
    job = profile_cases["hmmer_preparation"]["job"]
    bindings = [{key: deepcopy(job[key]) for key in ("program", "mode", "software")}]
    entries = native_hmmer_preparation_tool_contracts(bindings, resource_kind="local", resource_id="here")
    library = ScientificToolLibrary.freeze(tmp_path / "new-current-tool-library", catalog=[], tool_info=True,
        resource_catalogs={"local": entries})
    selection = [{"name": "native.hmmemit.consensus_simple", "resources": "local"}]
    current, = library.resolve_tool_info(selection)
    original = ScientificToolLibrary(profile_cases["hmmer_preparation"]["directory"] / "run/scientific-tool-library")
    old, = original.resolve_tool_info(selection)
    assert old["instructions"] != current["instructions"]
    assert "independent model-probability decoding remains unavailable" in old["instructions"]
    assert "Recognized HMMER3 binary revisions a-f" in current["instructions"]
    assert "HMMER2 probabilities retain their quantization" in current["instructions"]
    assert library.as_record() != original.as_record()


def _controller(path, initial):
    def estimate(raw, parameters, contexts):
        horizon = 1 if path[-1][0] == "annotation" else 3
        return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= horizon else 1), parameters,
            {"fixture": "caller_selected_profile_presentation_estimator_only"})
    scientific = path[-1][0] in {"annotation", "scientific_process"}
    return YieldController(str(path), initial, 0, YieldParameters(100, 50),
        estimate_with_context=estimate if scientific else None)


def _neutral(store, scope, **kwargs):
    return 0


class PendingProfileCaptured(RuntimeError):
    pass


class UnexpectedProfileFeedback(RuntimeError):
    pass


def test_fresh_current_preparation_results_stops_before_collection(profile_cases, tmp_path, monkeypatch):
    case = profile_cases["hmmer_preparation"]
    run_id = case["receipt"]["run_id"]
    db = case["db"]
    scientific = _commission(db, run_id, "episode_34b21389fd28a00644ee59be2da4f7a3a11974aa9fcdf2bf3c428874667b2501", "scientific_process")
    results = _commission(db, run_id, case["receipt"]["episode_id"], "results")
    assert results["selected"]["assignment"]["handoff_ref"] == _HANDOFF
    scope = scientific["selected"]["scope"]
    job = case["job"]
    old_binding = scientific["request"]["message"]["scientific_process"]["mechanics_binding"]
    directory = tmp_path / "current-pending"
    state = directory / "state"
    state.mkdir(parents=True)
    destination = sqlite3.connect(state / "state.sqlite3")
    try:
        db.backup(destination)
        assert _tables(destination) == case["tables"]
    finally:
        destination.close()
    shutil.copytree(case["directory"] / "state/artifacts", state / "artifacts")
    run = directory / "run"
    run.mkdir()
    for name in ("scientific-process-library", "scientific-tool-library", "tool-knowledge", "launch-instructions"):
        if (case["directory"] / "run" / name).exists():
            destination = directory / "original-scientific-tool-library" if name == "scientific-tool-library" else run / name
            shutil.copytree(case["directory"] / "run" / name, destination, symlinks=True)
    original_tool_library = ScientificToolLibrary(directory / "original-scientific-tool-library")
    process_library = ScientificProcessLibrary(run / "scientific-process-library")
    assert process_library.as_record() == old_binding["configuration"]["library"]
    assert original_tool_library.as_record() == old_binding["configuration"]["tool_library"]
    original_info = original_tool_library.resolve_tool_info(
        scientific["request"]["message"]["scientific_process"]["selection"]["child_tool_info"])
    original_science_call = json.loads(db.execute(
        "SELECT request FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index=0",
        (run_id, scientific["episode_id"])).fetchone()[0])["context"]
    assert original_info == original_science_call["scientific_process"]["child_tool_info"]
    target = case["receipt"]["target"]
    resources = {"here": dict(kind="local", workspace=target["assignment"]["workspace"],
        policy=target["assignment"]["constraints"]["allocation"],
        native_hmmer_preparation=[{key: deepcopy(job[key]) for key in ("program", "mode", "software")}])}
    factory = ExecutionServiceFactory(resources, {}, 3, 2, 1, log_window_bytes=128)
    session = _session(tmp_path / "pending-session")
    calls, pending = [], {}
    current_info, current_scientific = None, None

    class Choices:
        async def complete(self, episode_id, role, instructions, current, schema):
            calls.append(dict(episode_id=episode_id, role=role, instructions=instructions, context=deepcopy(current)))
            if current.get("feedback"):
                raise UnexpectedProfileFeedback("unexpected action-contract feedback: " + _canonical(plain(current["feedback"])))
            state = instructional_model_context(current)
            wire, actual = session._presentation(episode_id, role, instructions, state_frame(state))
            calls[-1]["wire"] = wire
            if current.get("execution_assignment", {}).get("version") == "execution_results_assignment_v1":
                assert len(calls) == 3 and current["execution_assignment"] == results["selected"]["assignment"]
                assert current["execution_target"] == target
                task = current["selected_execution_task"]
                assert task["scientific_question"] == scientific["selected"]["goal"]
                assert task["selected_tool_info"] == current_info
                assert task["requests"][0]["job"] == native_profile_scientific_job_view(job)
                assert task["selector"] == results["selected"]["assignment"]["selector"]
                assert current["requested_form"] == json.loads(results["selected"]["schema_json"])
                assert current["last_local_outcome"] is None and current["child_reports"] == []
                assert current["execution_progress"]["execution_completed"] is False
                assert wire.startswith("TASK") and "STEERING" in wire and actual == instructions
                assert all(info["instructions"] in wire for info in current_info)
                repeated, repeated_instructions = session._presentation(episode_id, role, instructions, state_frame(state, state))
                assert repeated == wire and repeated_instructions == actual
                pending.update(context=deepcopy(current), wire=wire, episode_id=episode_id)
                raise PendingProfileCaptured("before any result tool selection")
            chosen = results["selected"] if "scientific_process" in current else current_scientific
            if "scientific_process" in current:
                assert current["scientific_process"]["child_tool_info"] == current_info
            answer = provider_value({"selection": deepcopy(chosen), "report_update": {}}, plain(schema))
            Draft202012Validator(plain(schema)).validate(answer)
            return answer

        async def release(self, episode_id):
            pass

    store = Store(state)
    proof = dict(version="native_profile_pending_results_verification_v1", passed=False,
        old_replay_claimed=False, native_calls=0, calculator_calls=0, real_model_calls=0)
    initialized = None
    try:
        # Original model body remains forbidden; only sealed control JSON may open.
        original_get = store.get_artifact
        forbidden_inputs = {"artifact_" + row["sha256"] for row in job["operands"]}
        def controls_only(reference):
            assert reference not in forbidden_inputs, "pending builder read an original model body"
            return original_get(reference)
        monkeypatch.setattr(store, "get_artifact", controls_only)
        registry = ToolRegistry(store)
        application = factory(store, run_id=run_id, directory=run, tool_registry=registry)
        # A fresh commission selects current configured contracts. The copied
        # historical library and every historical request remain unchanged.
        current_library = ScientificToolLibrary.freeze(run / "scientific-tool-library",
            catalog=registry.catalog(), tool_info=True, resource_catalogs=application.resource_tool_catalogs)
        selectors = [{key: item[key] for key in ("name", "resources")} for item in original_info]
        current_info = current_library.resolve_tool_info(selectors)
        assert current_info != original_info
        assert current_library.as_record() != original_tool_library.as_record()
        descriptor = ScientificProcessEpisodes(None, library=process_library, tool_library=current_library,
            child_roles=old_binding["configuration"]["child_roles"]).as_record()
        expected_configuration = deepcopy(old_binding["configuration"])
        expected_configuration["tool_library"] = current_library.as_record()
        assert descriptor["configuration"] == expected_configuration
        current_scientific = deepcopy(scientific["selected"])
        current_scientific["assignment"]["selection"]["child_tool_info"] = selectors
        flow = Workflow(store, registry, Choices(), run, run_id, controller_factory=_controller,
            project_credit=_neutral, annotation_child_roles=("scientific_process",),
            episode_record_receipts=True, initial_known_record_refs=[_HANDOFF],
            episode_binding_descriptors=(descriptor, *application.episode_binding_descriptors),
            role_credit_bindings=application.role_credit_bindings,
            job_progress_provider=application.job_progress_provider)
        constructor = _assert_original_rows(store.db, case["tables"])
        initialized = _tables(store.db)
        initialized_files = _inventory(directory)
        root = flow.build("annotation", "current-profile-pending277",
            scientific["request"]["goal"]["task_context"]["root_objective"], scope)
        with pytest.raises(PendingProfileCaptured, match="before any result tool"):
            asyncio.run(root.run_async(flow.context))
        assert len(calls) == 3 and pending
        added = _new_rows(initialized, _tables(store.db))
        assert len(added["runtime_episodes"]) == 3 and len(added["runtime_actions"]) == 2
        assert len(added["runtime_model_calls"]) == 3
        for name in ("records", "artifacts", "tool_operations", "runtime_forms", "runtime_report_attempts", "runtime_observations"):
            assert added[name] == []
        for row in added["runtime_episodes"]:
            item = dict(zip(initialized["runtime_episodes"]["columns"], row))
            assert item["state"] == "active" and item["completion"] is item["archive"] is None
        model_rows = [dict(zip(initialized["runtime_model_calls"]["columns"], row)) for row in added["runtime_model_calls"]]
        assert sum(row["response"] is None for row in model_rows) == 1
        assert next(row for row in model_rows if row["response"] is None)["episode_id"] == pending["episode_id"]
        records = EpisodeReturnRecords(store, flow.run_id, failure_prefix="profile_pending_")
        context = records.context(pending["episode_id"])
        owner = flow.specialist(_source_for_original_context(flow, context))
        assert owner._target(context) == target
        assert _HANDOFF in set(flow.receipts.known(context.episode_id))
        current_files = _inventory(directory)
        for name, pin in initialized_files.items():
            if name not in {"state/state.sqlite3", "state/state.sqlite3-wal", "state/state.sqlite3-shm"}:
                assert current_files[name] == pin
        proof.update(passed=True, constructor=constructor, original_question=scientific["selected"]["goal"],
            actual_new_row_counts={name: len(rows) for name, rows in added.items()},
            initial_handoff=_HANDOFF, full_current_results_builder_verified=True,
            copied_controls_and_libraries_unchanged=True,
            original_model_artifact_access_forbidden=True,
            original_scientific_binding=old_binding, current_scientific_binding=descriptor,
            original_tool_info=original_info, current_tool_info=current_info,
            current_scientific_selection=current_scientific)
    except BaseException as error:
        proof["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        proof["calls"] = calls
        if initialized is not None:
            proof["actual_new_rows"] = _new_rows(initialized, _tables(store.db))
        store.close()
        (tmp_path / "PROFILE_CURRENT_PENDING_RESULTS.json").write_text(json.dumps(proof, indent=2, allow_nan=False) + "\n")


@pytest.fixture
def canonical_preparation277(tmp_path):
    """Required retained data lives with the tests; only an owned copy opens."""
    source = Path(__file__).parent / "fixtures/native_hmmer_preparation277"
    before = _inventory(source)
    manifest = _json(source / "manifest.json",
        "c03c40263c8289bb094e426c46e6ddc5b21100f7619208e8b71baa282884291e", 26410)
    assert manifest["schema"] == "native_hmmer_preparation277_retained_fixture_v1"
    assert manifest["original_case"]["inventory_sha256"] == _PINS["hmmer_preparation"]
    subset = manifest["preserved_subset"]
    assert _sha(_canonical(subset["inventory"]).encode()) == subset["inventory_sha256"] == (
        "8bfa589b51f0e8220bf926f36d1bde88a008e95f182f13fd820fe160ae6e5ce2")
    assert subset["file_count"] == 84 and subset["total_file_bytes"] == 3454307
    omitted = manifest["omitted_unused_manual_bodies"]
    assert omitted["file_count"] == len(omitted["original_case_relative_paths"]) == 29
    assert omitted["total_file_bytes"] == 82511 and omitted["consumed_by_new_prefix"] is False
    assert not any(name.endswith(".md") for name in before)
    attempt = os.environ.get("HMMER529_ATTEMPT")
    snapshot = None if attempt is None else Path(attempt).resolve(strict=True) / "source_snapshot"
    frozen = (snapshot is not None and Path(__file__).resolve() == snapshot / "tests/test_native_profile_presentation.py"
        and source.resolve() == snapshot / "tests/fixtures/native_hmmer_preparation277")
    expected_source = deepcopy(subset["inventory"])
    if frozen:
        for pin in expected_source.values():
            assert pin["kind"] in {"directory", "file"}
            pin["mode"] = 0o555 if pin["kind"] == "directory" or pin["mode"] & 0o111 else 0o444
    assert {name: pin for name, pin in before.items() if name != "manifest.json"} == expected_source
    assert before["manifest.json"] == dict(kind="file", mode=0o444 if frozen else 0o644,
        sha256="c03c40263c8289bb094e426c46e6ddc5b21100f7619208e8b71baa282884291e", size_bytes=26410)
    copied = tmp_path / "canonical277-input"
    shutil.copytree(source / "case", copied, symlinks=True)
    assert _inventory(copied) == {name.removeprefix("case/"): pin for name, pin in expected_source.items()
        if name.startswith("case/")}
    copied.chmod(subset["inventory"]["case"]["mode"])
    for name, pin in sorted(subset["inventory"].items(), key=lambda item: len(Path(item[0]).parts)):
        if name.startswith("case/"):
            (copied / name.removeprefix("case/")).chmod(pin["mode"])
    copied_before = _inventory(copied)
    assert copied_before == {name.removeprefix("case/"): pin for name, pin in subset["inventory"].items()
        if name.startswith("case/")}
    database = copied / "state/state.sqlite3"
    assert not database.with_name(database.name + "-wal").exists()
    assert not database.with_name(database.name + "-shm").exists()
    db = sqlite3.connect(database.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    db.row_factory = sqlite3.Row
    with pytest.MonkeyPatch.context() as guards:
        _guards(guards)
        try:
            receipt = _json(copied / manifest["receipt_relative_path"].removeprefix("case/"),
                _RECEIPTS["hmmer_preparation"][2], _RECEIPTS["hmmer_preparation"][3])
            assert receipt["complete"] is True
            stored = db.execute("SELECT request FROM runtime_episodes WHERE run_id=? AND episode_id=?",
                (receipt["run_id"], receipt["episode_id"])).fetchone()
            assert json.loads(stored[0])["message"]["episode_assignment"] == receipt["assignment"]
            job = receipt["target"]["assignment"]["requested_job"]["native_hmmer_preparation"]
            assert len(job["operands"]) == 1
            model = manifest["original_model"]
            assert all(job["operands"][0][key] == model[key] for key in
                ("artifact_ref", "format", "path", "sha256", "size_bytes"))
            raw = (source / "inputs/profile.hmm").read_bytes()
            assert _sha(raw) == model["sha256"] and len(raw) == model["size_bytes"] == 6670
            tables = _tables(db)
            yield dict(directory=copied, db=db, tables=tables, receipt=receipt, job=job, manifest=manifest)
            assert _tables(db) == tables and db.total_changes == 0
        finally:
            db.close()
            assert _inventory(copied) == copied_before
            assert _inventory(source) == before


def test_fresh_current_preparation_launch_and_local_stop_before_first_tool(canonical_preparation277, tmp_path, monkeypatch):
    """A new normal commissioning prefix, not replay or native completion."""
    import builtins
    from gene_annotation_episode.launch_instructions import LaunchInstructions
    from gene_annotation_episode.tool_knowledge import ToolKnowledge

    case = canonical_preparation277
    db, run_id, job = case["db"], case["receipt"]["run_id"], case["job"]
    scientific = _commission(db, run_id,
        "episode_34b21389fd28a00644ee59be2da4f7a3a11974aa9fcdf2bf3c428874667b2501", "scientific_process")
    launch = _commission(db, run_id,
        "episode_aa3d244022ce40bbdfadcfb663131216b05c9b5aa144cf76cb683aecf2b8fa23", "launch")
    local = _commission(db, run_id,
        "episode_b52e169fb498f755077d212346deb48a06d46e8bc539d5086f339c65430b0796", "launch_local")
    assert launch["parent_episode_id"] == scientific["episode_id"] and local["parent_episode_id"] == launch["episode_id"]
    original_assignment = local["selected"]["assignment"]
    assert launch["selected"]["assignment"]["requests"] == {"here": original_assignment}
    assert original_assignment == case["receipt"]["target"]["assignment"]
    assert original_assignment["requested_job"]["native_hmmer_preparation"] == job
    assert original_assignment["progress_requirements"] == [
        dict(key="handoff", credit=7, predicate=dict(kind="requested_job_handoff"))]
    assert "launch_instructions" not in original_assignment
    scope = scientific["selected"]["scope"]
    old_binding = scientific["request"]["message"]["scientific_process"]["mechanics_binding"]
    directory = tmp_path / "current-local-prefix"
    state = directory / "state"
    state.mkdir(parents=True)
    destination = sqlite3.connect(state / "state.sqlite3")
    try:
        db.backup(destination)
        assert _tables(destination) == case["tables"]
    finally:
        destination.close()
    shutil.copytree(case["directory"] / "state/artifacts", state / "artifacts")
    run = directory / "run"
    run.mkdir()
    for name in ("scientific-process-library", "scientific-tool-library", "tool-knowledge", "launch-instructions"):
        target = directory / "original-scientific-tool-library" if name == "scientific-tool-library" else run / name
        shutil.copytree(case["directory"] / "run" / name, target, symlinks=True)
    original_library = ScientificToolLibrary(directory / "original-scientific-tool-library")
    process_library = ScientificProcessLibrary(run / "scientific-process-library")
    assert original_library.as_record() == old_binding["configuration"]["tool_library"]
    assert process_library.as_record() == old_binding["configuration"]["library"]
    original_info = original_library.resolve_tool_info(
        scientific["request"]["message"]["scientific_process"]["selection"]["child_tool_info"])
    original_call = json.loads(db.execute("SELECT request FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index=0",
        (run_id, scientific["episode_id"])).fetchone()[0])["context"]
    assert original_info == original_call["scientific_process"]["child_tool_info"]
    factory = ExecutionServiceFactory({"here": dict(kind="local", workspace=original_assignment["workspace"],
        policy=deepcopy(original_assignment["constraints"]["allocation"]),
        native_hmmer_preparation=[{key: deepcopy(job[key]) for key in ("program", "mode", "software")}])},
        {}, 3, 2, 1, log_window_bytes=128)
    session = _session(tmp_path / "local-prefix-session")
    calls, pending, forbidden_body_reads, historical_metadata_checks = [], {}, [], []
    manual_body_accesses, empty_manual_materializations = [], []
    current_info, current_scientific = None, None

    class Choices:
        async def complete(self, episode_id, role, instructions, current, schema):
            calls.append(dict(episode_id=episode_id, role=role, instructions=instructions, context=deepcopy(current)))
            if current.get("feedback"):
                raise UnexpectedProfileFeedback("unexpected local commission feedback: " + _canonical(plain(current["feedback"])))
            frame_state = instructional_model_context(current)
            wire, actual = session._presentation(episode_id, role, instructions, state_frame(frame_state))
            calls[-1]["wire"] = wire
            assert wire.startswith("TASK") and "STEERING" in wire and actual == instructions
            assert current["goal"]["objective"] in wire
            repeated, repeated_instructions = session._presentation(episode_id, role, instructions, state_frame(frame_state, frame_state))
            assert repeated == wire and repeated_instructions == actual
            if "practical_assignment" in current or "execution_assignment" in current:
                is_local = "practical_assignment" in current
                selected = local if is_local else launch
                assert len(calls) == (4 if is_local else 3)
                assert current["practical_assignment" if is_local else "execution_assignment"] == selected["selected"]["assignment"]
                task = current["selected_execution_task"]
                assert task["scientific_question"] == scientific["selected"]["goal"]
                assert task["selected_tool_info"] == current_info and len(task["requests"]) == 1
                assert task["constraints"] == selected["selected"]["assignment"]["constraints"]
                assert task["selector"] is None
                request = task["requests"][0]
                assert request["resource_id"] == "here" and request["resource_kind"] == "local"
                assert request["job"] == native_profile_scientific_job_view(job)
                assert request["constraints"] == original_assignment["constraints"]
                assert current["requested_form"] == json.loads(selected["selected"]["schema_json"])
                assert current["last_local_outcome"] is None and current["child_reports"] == []
                assert all(info["name"] in wire and info["description"] in wire and info["instructions"] in wire
                    for info in current_info)
                assert scientific["selected"]["goal"] in wire
                assert current.get("selected_launch_instructions") is None
                if is_local:
                    assert current["practical_completion"] is None
                    pending.update(episode_id=episode_id, context=deepcopy(current), wire=wire)
                    raise PendingProfileCaptured("local resource before first tool selection")
                assert current["execution_progress"]["execution_completed"] is False
                chosen = local["selected"]
            elif "scientific_process" in current:
                assert len(calls) == 2 and current["scientific_process"]["child_tool_info"] == current_info
                chosen = launch["selected"]
            else:
                assert len(calls) == 1
                chosen = current_scientific
            answer = provider_value({"selection": deepcopy(chosen), "report_update": {}}, plain(schema))
            Draft202012Validator(plain(schema)).validate(answer)
            return answer

        async def release(self, episode_id):
            pass

    original_model = Path(case["manifest"]["original_model"]["path"])
    original_workspace = Path(original_assignment["workspace"])
    def guarded_body_path(function):
        def call(path, *args, **kwargs):
            if isinstance(path, (str, os.PathLike)):
                candidate = Path(path).absolute()
                if candidate == original_model or candidate.is_relative_to(original_workspace):
                    forbidden_body_reads.append(str(candidate))
                    raise AssertionError("before-tool prefix read historical model/workspace bytes")
            return function(path, *args, **kwargs)
        return call
    for owner, name in ((builtins, "open"), (Path, "open"), (os, "open")):
        monkeypatch.setattr(owner, name, guarded_body_path(getattr(owner, name)))
    def recorded_metadata_path(port, function):
        def call(path, *args, **kwargs):
            if isinstance(path, (str, os.PathLike)):
                candidate = Path(path).absolute()
                if candidate == original_model or candidate.is_relative_to(original_workspace):
                    historical_metadata_checks.append(dict(port=port, path=str(candidate)))
            return function(path, *args, **kwargs)
        return call
    for name in ("stat", "lstat"):
        monkeypatch.setattr(os, name, recorded_metadata_path("os." + name, getattr(os, name)))
    def forbidden_manual_body(port):
        def call(*args, **kwargs):
            manual_body_accesses.append(port)
            raise AssertionError("before-tool prefix consumed unselected manual bodies: " + port)
        return call
    for owner, name in ((ToolKnowledge, "read"), (LaunchInstructions, "read"), (LaunchInstructions, "select")):
        monkeypatch.setattr(owner, name, forbidden_manual_body(owner.__name__ + "." + name))
    original_materialize = LaunchInstructions.materialize
    def only_empty_materialization(library, selection):
        if selection is not None:
            manual_body_accesses.append("LaunchInstructions.materialize")
            raise AssertionError("before-tool prefix materialized unselected manual bodies")
        empty_manual_materializations.append(str(library.directory))
        return original_materialize(library, selection)
    monkeypatch.setattr(LaunchInstructions, "materialize", only_empty_materialization)
    store = Store(state)
    proof = dict(version="native_profile_pending_local_commission_verification_v1", passed=False,
        original_replay_claimed=False, native_execution_completed=False, native_calls=0, calculator_calls=0,
        real_model_calls=0, nonempty_selected_manual_sections_verified=False)
    initialized = None
    try:
        original_get = store.get_artifact
        forbidden_inputs = {"artifact_" + row["sha256"] for row in job["operands"]}
        def controls_only(reference):
            assert reference not in forbidden_inputs, "local prefix read original native input body"
            return original_get(reference)
        monkeypatch.setattr(store, "get_artifact", controls_only)
        registry = ToolRegistry(store)
        application = factory(store, run_id=run_id, directory=run, tool_registry=registry)
        current_library = ScientificToolLibrary.freeze(run / "scientific-tool-library",
            catalog=registry.catalog(), tool_info=True, resource_catalogs=application.resource_tool_catalogs)
        selectors = [{key: item[key] for key in ("name", "resources")} for item in original_info]
        current_info = current_library.resolve_tool_info(selectors)
        descriptor = ScientificProcessEpisodes(None, library=process_library, tool_library=current_library,
            child_roles=old_binding["configuration"]["child_roles"]).as_record()
        expected_configuration = deepcopy(old_binding["configuration"])
        expected_configuration["tool_library"] = current_library.as_record()
        assert descriptor["configuration"] == expected_configuration
        current_scientific = deepcopy(scientific["selected"])
        current_scientific["assignment"]["selection"]["child_tool_info"] = selectors
        references = scientific["selected"]["assignment"]["evidence_refs"]
        flow = Workflow(store, registry, Choices(), run, run_id, controller_factory=_controller,
            project_credit=_neutral, annotation_child_roles=("scientific_process",), episode_record_receipts=True,
            initial_known_record_refs=deepcopy(references),
            episode_binding_descriptors=(descriptor, *application.episode_binding_descriptors),
            role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
        constructor = _assert_original_rows(store.db, case["tables"])
        initialized, initialized_files = _tables(store.db), _inventory(directory)
        root = flow.build("annotation", "current-profile-local-prefix277",
            scientific["request"]["goal"]["task_context"]["root_objective"], scope)
        with pytest.raises(PendingProfileCaptured, match="local resource before first tool"):
            asyncio.run(root.run_async(flow.context))
        assert len(calls) == 4 and pending and forbidden_body_reads == [] and manual_body_accesses == []
        assert any(row == dict(port="os.lstat", path=str(original_workspace))
            for row in historical_metadata_checks)
        added = _new_rows(initialized, _tables(store.db))
        assert len(added["runtime_episodes"]) == 4 and len(added["runtime_actions"]) == 3
        assert len(added["runtime_model_calls"]) == 4
        for name in ("records", "artifacts", "tool_operations", "runtime_forms", "runtime_report_attempts", "runtime_observations"):
            assert added[name] == []
        roles = []
        for row in added["runtime_episodes"]:
            value = dict(zip(initialized["runtime_episodes"]["columns"], row))
            assert value["state"] == "active" and value["completion"] is value["archive"] is None
            roles.append(json.loads(value["path"])[-1][0])
        assert sorted(roles) == ["annotation", "launch", "launch_local", "scientific_process"]
        for row in added["runtime_actions"]:
            assert dict(zip(initialized["runtime_actions"]["columns"], row))["result"] is None
        model_rows = [dict(zip(initialized["runtime_model_calls"]["columns"], row)) for row in added["runtime_model_calls"]]
        assert sum(row["response"] is not None for row in model_rows) == 3
        assert [row["episode_id"] for row in model_rows if row["response"] is None] == [pending["episode_id"]]
        for captured in calls:
            row = store.db.execute("SELECT request FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index=0",
                (run_id, captured["episode_id"])).fetchone()
            assert json.loads(row[0])["context"] == captured["context"]
        current_files = _inventory(directory)
        for name, pin in initialized_files.items():
            if name not in {"state/state.sqlite3", "state/state.sqlite3-wal", "state/state.sqlite3-shm"}:
                assert current_files[name] == pin
        proof.update(passed=True, constructor=constructor, original_question=scientific["selected"]["goal"],
            actual_new_row_counts={name: len(rows) for name, rows in added.items()},
            full_current_launch_and_resource_builders_verified=True,
            selected_tool_resource_guidance_verified=True, original_input_refs=references,
            original_scientific_binding=old_binding, current_scientific_binding=descriptor,
            original_tool_info=original_info, current_tool_info=current_info,
            original_launch_commission=launch, original_local_commission=local,
            canonical_fixture_manifest_sha256="c03c40263c8289bb094e426c46e6ddc5b21100f7619208e8b71baa282884291e",
            omitted_unused_manual_bodies=case["manifest"]["omitted_unused_manual_bodies"],
            original_full_inventory_sha256=case["manifest"]["original_case"]["inventory_sha256"],
            preserved_subset_inventory_sha256=case["manifest"]["preserved_subset"]["inventory_sha256"])
    except BaseException as error:
        proof["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        proof["calls"], proof["forbidden_historical_body_reads"] = calls, forbidden_body_reads
        proof["historical_metadata_checks"] = historical_metadata_checks
        proof["manual_body_accesses"] = manual_body_accesses
        proof["empty_manual_materializations"] = empty_manual_materializations
        if initialized is not None:
            proof["actual_new_rows"] = _new_rows(initialized, _tables(store.db))
        store.close()
        (tmp_path / "PROFILE_CURRENT_PENDING_LOCAL_COMMISSION.json").write_text(json.dumps(proof, indent=2, allow_nan=False) + "\n")
