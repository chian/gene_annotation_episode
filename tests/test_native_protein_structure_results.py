"""Protein host tests over retained native fixtures and real bounded396 work.

The small structures are synthetic engineering fixtures. Isolated publication
tests do not prove original runtime custody. Tests using406's actual commission
fixture separately exercise that boundary, without a fake host.
"""
import asyncio
from copy import deepcopy
from importlib import import_module
import json
import math
from pathlib import Path
import threading
from types import SimpleNamespace

import pytest

from gene_annotation_episode import native_protein_structure_results as hm
from gene_annotation_episode import protein_structure_calculations as calculations
from gene_annotation_episode import protein_structure_sheet as sheets
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_protein_structure_acquisition import retained_protein_structure_file
from gene_annotation_episode.native_protein_structure_returns import (
    PROJECTION_SOURCE, SAVED_SOURCE, SEQUENCE_SOURCE, FAILURE_SOURCE,
)
from gene_annotation_episode.protein_structure_authority import ProteinStructureOperandError
from gene_annotation_episode.protein_structure_result_views import project_protein_structure_results
from gene_annotation_episode.state import Store
from test_protein_structure_record_publication import case as retained_case, file_for, retain

RUNTIME = import_module("verification.tool_graders_protein_structure_result_host_2026-10-27_407.fixture_helpers")

REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / "verification/tool_graders_protein_structure_result_worker_2026-10-27_393/fixtures"
POLICY = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296)


def forbidden(*args, **kwargs):
    raise AssertionError("unexpected acquisition, calculation, publication or producer read")


def projection(family="comparison_summary", *, identifier="requested", delivery="values"):
    defaults = {
        "comparison_summary": ({"kind": "comparison"}, ["evaluation_sse", "evaluation_rmsd", "evaluation_used_count"]),
        "transform": ({"kind": "transform"}, ["rotation", "translation"]),
        "extracted_sequence": ({"kind": "extracted_sequence", "residue_positions": {"kind": "all"}},
                               ["descriptor", "alignment_sequence", "sequence_length", "residue_map_row"]),
        "structure_inventory": ({"kind": "all_inventory_rows"}, ["model", "chain", "position", "native_metadata"]),
    }
    members, fields = deepcopy(defaults[family])
    return {"projection_id": identifier, "family": family, "members": members, "fields": fields,
            "window": None, "delivery_kind": delivery}


def selector(*projections, saved=None, parameters=None, return_saved=False, uses=()):
    return {"version": "protein_structure_result_selector_v1",
        "acquisition": "complete_bound_bundle" if saved is None else "retained_sheet_only",
        "saved_sheet": deepcopy(saved), "parameters": deepcopy(parameters), "projections": list(projections),
        "return_saved_sheet": return_saved, "sequence_allowed_uses": list(uses)}


def fixture_host(store, directory):
    return hm.NativeProteinStructureResults(SimpleNamespace(store=store, run_id="fixture-host-run",
        directory=directory, acquired_record_unit=3, handoff_unit=2))


def fixture_body(selected, bundle, capture=None):
    """Publication-only input, never passed off as an authenticated receipt."""
    intent = {"version": "protein_structure_result_intent_v1", "run_id": "fixture-host-run",
        "episode_id": "results", "path": [["root", "root"], ["results", "child_0"]], "scope": {},
        "assignment": {"version": "execution_results_assignment_v1", "handoff_ref": "source_" + "a" * 24,
                       "selector": selected}, "original_request_sha256": "b" * 64,
        "operation_key": "fixture-host-run:results:0", "tool_name": "execution.results.collect",
        "arguments": {}, "target": {}}
    return {"version": "protein_structure_result_body_v1", "intent": intent,
        "handoff_proof": {"fixture_only": "not a runtime custody proof"},
        "observation": None, "observation_origin": "not_observed", "original_custody": None,
        "capture": deepcopy(capture), "bundle": deepcopy(bundle), "worker": None,
        "qualified_files": hm._empty_files(), "calculation": None, "issues": [],
        "native_success": False, "capture_complete": bool(capture and capture["capture_complete"])}


def worker_original(store, directory, *, case=None, label="held_out", alter=None):
    if case is None:
        raw = (FIXTURES / (label + ".json")).read_bytes()
        native = json.loads(raw)
        if alter:
            alter(native)
            raw = canonical(native).encode()
        identity = retain(store, raw, native["version"])
        job = {"request": native["request"], "software": native["producer"]}
        bundle = {"requested_job": {"native_protein_structure": job}, "software": native["producer"]}
    else:
        identity = file_for(case, "native_result")
        native = json.loads(retained_protein_structure_file(store, identity).read_bytes())
        bundle = case["bundle"]
        job = bundle["requested_job"]["native_protein_structure"]
    plan = {"version": "protein_structure_result_worker_plan_v1", "mode": "original_native_result",
        "directory": str(directory), "expected_request": job["request"], "expected_software": job["software"],
        "native_result": {"file_identity": identity, "path": str(retained_protein_structure_file(store, identity))}}
    return hm._prepare_worker_in_thread(store.path, plan=plan, policy=POLICY), native, bundle


def worker_saved(store, directory, sheet_file, original_file, parameters):
    plan = {"version": "protein_structure_result_worker_plan_v1", "mode": "saved_sheet_recalculation",
        "directory": str(directory), "sheet": {"file_identity": sheet_file,
            "path": str(retained_protein_structure_file(store, sheet_file))},
        "original_components": {"file_identity": original_file,
            "path": str(retained_protein_structure_file(store, original_file))}, "parameters": parameters}
    return hm._prepare_worker_in_thread(store.path, plan=plan, policy=POLICY)


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path / "store") as value:
        yield value


def forbid_original_science(monkeypatch):
    monkeypatch.setattr(calculations, "calculate_protein_structure_components", forbidden)
    monkeypatch.setattr(calculations, "fit_ca_transform", forbidden)
    monkeypatch.setattr(sheets, "parse_native_protein_comparison", forbidden)
    import numpy as np
    monkeypatch.setattr(np.linalg, "svd", forbidden)


def publish_fixture(host, body, science, row):
    ref = hm.publish_protein_structure_source(host.store, bundle=row["bundle"], capture=row["capture"],
                                             worker_result=body["worker"]["result"])
    return host._publication(body, science, host.store.get(ref), collecting=True)


def test_constructor_and_dispatch_are_inert_and_lazy(tmp_path):
    class NoReads:
        def __getattr__(self, name):
            raise AssertionError(name)
    owner = SimpleNamespace(store=NoReads(), directory=tmp_path, run_id="inert")
    host = hm.NativeProteinStructureResults(owner)
    context = SimpleNamespace(role="results", assignment={"selector": selector()})
    assert host.applies(context)
    context.role = "launch"
    assert not host.applies(context)
    context.role, context.assignment = "results", {"selector": {"version": "different"}}
    assert not host.applies(context)
    assert [row["name"] for row in hm.operation_catalog()] == ["execution.results.status", "execution.results.collect"]


def test_original_heldout_and_saved_all_five_preserve_baseline(store, tmp_path, monkeypatch):
    host = fixture_host(store, tmp_path)
    selected = selector(projection(), return_saved=True)
    view, native, bundle = worker_original(store, tmp_path / "original")
    body = fixture_body(selected, bundle)
    body["worker"] = view
    forbid_original_science(monkeypatch)
    original = host._original_science(body)
    assert original["sheet"] == native["sheet"]
    assert original["components"] == native["sheet"]["native_baseline"]
    rows, = project_protein_structure_results(original, selection=selected["projections"])
    values = {row["field"]: row["value"]["value"] for row in rows["rows"][0]["values"]}
    assert values == pytest.approx({"evaluation_sse": 4, "evaluation_rmsd": 2, "evaluation_used_count": 1})
    files = body["qualified_files"]
    parameters = deepcopy(native["request"]["parameters"])
    parameters["evaluation_selection"] = {"kind": "all_mapped_pairs"}
    later = worker_saved(store, tmp_path / "later", files["sheet_file"], files["original_components_file"], parameters)
    changed_selector = {"saved_sheet": {"sheet_file": files["sheet_file"],
        "original_components_file": files["original_components_file"]}, "parameters": parameters}
    later_body = deepcopy(body)
    later_body.update(worker=later, qualified_files=hm._empty_files(), calculation=None)
    changed = host._saved_science(later_body, {"body": body}, changed_selector)
    assert changed["components"]["evaluation"]["evaluation_rmsd"]["value"] == pytest.approx(math.sqrt(4 / 5))
    assert changed["components"]["counts"]["evaluation_used_count"]["value"] == 5
    assert changed["sheet"] == original["sheet"]
    assert changed["sheet"]["native_baseline"] == original["components"]
    for name in ("sheet_file", "original_components_file", "native_file"):
        assert later_body["qualified_files"][name] == files[name]
    assert later_body["qualified_files"]["components_file"] != files["components_file"]
    (tmp_path / "numerical-example.json").write_text(canonical({"original": values,
        "later_rmsd_A": changed["components"]["evaluation"]["evaluation_rmsd"]["value"],
        "original_files": files, "later_files": later_body["qualified_files"]}))


@pytest.mark.parametrize("case_name,family", [("inspection", "structure_inventory"),
    ("extraction", "extracted_sequence"), ("comparison", "comparison_summary")])
def test_actual392_396_400_selected_publication(store, tmp_path, monkeypatch, case_name, family):
    row = retained_case(store, case_name)
    host = fixture_host(store, tmp_path)
    selected = selector(projection(family), return_saved=case_name == "comparison",
                        uses=("structure_correspondence", "sequence_align") if case_name == "extraction" else ())
    view, native, _ = worker_original(store, tmp_path / "worker", case=row)
    body = fixture_body(selected, row["bundle"], row["capture"])
    body["worker"] = view
    forbid_original_science(monkeypatch)
    publication = publish_fixture(host, body, host._original_science(body), row)
    assert publication["accounting"]["projection_ids"] == ["requested"]
    assert not publication["accounting"]["failed_projection_ids"]
    assert publication["facts"][PROJECTION_SOURCE][0]["delivery"]["kind"] == "values"
    if case_name == "extraction":
        descriptor, = publication["facts"][SEQUENCE_SOURCE]
        assert descriptor["allowed_uses"] == ["structure_correspondence", "sequence_align"]
        assert store.get_artifact(descriptor["sequence_file"]["artifact_ref"]) == b"AGST"
        assert store.get_artifact(descriptor["residue_map_file"]["artifact_ref"]) == canonical(native["sequence"]).encode()
        assert store.subject_length(descriptor["reference_ref"]) == 4
        assert publication["reference_records"] == [store.get(descriptor["reference_ref"])]
    if case_name == "comparison":
        descriptor, = publication["facts"][SAVED_SOURCE]
        assert descriptor["allowed_uses"] == ["recalculate", "select_projection", "use_transform"]
    before = deepcopy(publication)
    for name in ("publish_protein_structure_projection", "publish_structure_sequence_reference", "publish_protein_structure_source"):
        monkeypatch.setattr(hm, name, forbidden)
    host._verify_artifacts({"body": body, "publication": publication})
    assert publication == before


def test_per_selection_failure_keeps_independent_rows_and_artifact_selection(store, tmp_path):
    row = retained_case(store, "comparison")
    host = fixture_host(store, tmp_path)
    missing = {"projection_id": "missing-coordinate-population", "family": "structure_coordinates",
        "members": {"kind": "coordinate_set", "coordinate_set_id": "not-requested-by-original"},
        "fields": ["xyz"], "window": None, "delivery_kind": "values"}
    table_selection = projection("transform", identifier="matrix", delivery="artifact")
    body = fixture_body(selector(projection(), missing, table_selection), row["bundle"], row["capture"])
    body["worker"], _, _ = worker_original(store, tmp_path / "worker", case=row)
    science = host._original_science(body)
    publication = publish_fixture(host, body, science, row)
    assert publication["accounting"]["projection_ids"] == ["requested", "matrix"]
    assert publication["accounting"]["failed_projection_ids"] == ["missing-coordinate-population"]
    failure, = publication["facts"][FAILURE_SOURCE]
    assert failure["projection_id"] == "missing-coordinate-population"
    assert failure["issue"]["code"] == "selected_field_unavailable"
    table = publication["facts"][PROJECTION_SOURCE][1]
    expected, = project_protein_structure_results(science, selection=[table_selection])
    assert store.get_artifact(table["delivery"]["table_file"]["artifact_ref"]) == canonical({
        "version": "protein_structure_projection_table_v1", "rows": expected["rows"]}).encode()
    assert not publication["facts"][SAVED_SOURCE] and not publication["facts"][SEQUENCE_SOURCE]


@pytest.mark.parametrize("diagnostic", ["native_arithmetic", "saved_baseline"])
def test_008_diagnostic_outputs_never_qualify_scientific_files(store, tmp_path, diagnostic):
    host = fixture_host(store, tmp_path)
    if diagnostic == "native_arithmetic":
        def alter(native):
            native["sheet"]["native_baseline"]["evaluation"]["evaluation_rmsd"]["value"] = 19.0
        view, _, bundle = worker_original(store, tmp_path / "worker", alter=alter)
        body = fixture_body(selector(projection(), return_saved=True), bundle)
        body["worker"] = view
        science = host._original_science(body)
        assert view["result"]["native_result_file"] is not None
    else:
        native = json.loads((FIXTURES / "held_out.json").read_bytes())
        sheet = deepcopy(native["sheet"])
        sheet["native_baseline"] = None
        sheet_file = retain(store, canonical(sheet).encode(), "protein_structure_comparison_sheet_v1")
        components_file = retain(store, canonical(native["sheet"]["native_baseline"]).encode(), "protein_structure_components_v1")
        view = worker_saved(store, tmp_path / "worker", sheet_file, components_file, native["request"]["parameters"])
        body = fixture_body(selector(), {})
        body["worker"] = view
        science = host._saved_science(body, None, None)
        assert view["result"]["sheet_file"] is not None
    assert view["result"]["state"] == "invalid" and view["result"]["components_file"] is None
    assert science is None and all(value is None for value in body["qualified_files"].values())
    assert body["calculation"] is None


@pytest.mark.parametrize("label", ["zero_available", "mixed_partial", "extract_unavailable"])
def test_partial_and_unavailable_native_values_are_preserved(store, tmp_path, label):
    view, native, bundle = worker_original(store, tmp_path / "worker", label=label)
    host = fixture_host(store, tmp_path)
    body = fixture_body(selector(), bundle, {"files": [], "capture_complete": False})
    body["worker"] = view
    science = host._original_science(body)
    assert science is not None
    if label == "extract_unavailable":
        assert science["sequence"] == native["sequence"] and science["descriptor"] is None
    else:
        assert science["components"] == native["sheet"]["native_baseline"]


def test_explicit_byte_check_fails_without_writer_or_calculator(store, tmp_path, monkeypatch):
    row = retained_case(store, "comparison")
    host = fixture_host(store, tmp_path)
    body = fixture_body(selector(projection(), return_saved=True), row["bundle"], row["capture"])
    body["worker"], _, _ = worker_original(store, tmp_path / "worker", case=row)
    publication = publish_fixture(host, body, host._original_science(body), row)
    forbid_original_science(monkeypatch)
    for name in ("publish_protein_structure_projection", "publish_protein_structure_source", "publish_structure_sequence_reference"):
        monkeypatch.setattr(hm, name, forbidden)
    retained_protein_structure_file(store, body["qualified_files"]["components_file"]).unlink()
    with pytest.raises(ProteinStructureOperandError, match="retained_artifact_missing"):
        host._verify_artifacts({"body": body, "publication": publication})


def test_thread_adapter_uses_separate_store_and_drains_cancellation(store, tmp_path, monkeypatch):
    """Adapter unit test;406 independently exercises the actual OS action lock."""
    host = fixture_host(store, tmp_path)
    action = SimpleNamespace(worker_directory=tmp_path / "worker")
    active, entered, release = {id(action)}, threading.Event(), threading.Event()
    host.receipts = SimpleNamespace(require_action=lambda value: hm._require(id(value) in active))
    parent_thread, calls = threading.get_ident(), []
    def prepare(worker_store, *, plan, policy):
        assert worker_store is not store and worker_store.path == store.path
        assert threading.get_ident() != parent_thread
        worker_store.db.execute("SELECT count(*) FROM artifacts").fetchone()
        calls.append((plan, policy))
        entered.set()
        assert release.wait(10)
        return {"prepared": True}
    monkeypatch.setattr(hm, "prepare_protein_structure_worker", prepare)
    monkeypatch.setattr(hm, "validate_prepared_protein_structure_worker", lambda store, prepared, *, plan: prepared)
    async def selected():
        task = asyncio.create_task(host._prepare_worker(action=action, plan={"directory": str(action.worker_directory)}, policy=POLICY))
        while not entered.is_set():
            await asyncio.sleep(0.01)
        task.cancel()
        await asyncio.sleep(0.02)
        assert not task.done()
        task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(selected())
    assert len(calls) == 1
    with store.transaction():
        with pytest.raises(ProteinStructureOperandError):
            asyncio.run(host._prepare_worker(action=action, plan={"directory": str(action.worker_directory)}, policy=POLICY))
    active.clear()
    with pytest.raises(ProteinStructureOperandError):
        asyncio.run(host._prepare_worker(action=action, plan={"directory": str(action.worker_directory)}, policy=POLICY))


@pytest.mark.parametrize("kind,family,source", [("inspect", "structure_inventory", PROJECTION_SOURCE),
    ("extract_sequence", "extracted_sequence", SEQUENCE_SOURCE), ("compare", "comparison_summary", SAVED_SOURCE)])
def test_actual_runtime_pending_replay_completed_authority_and_byte_loss(store, tmp_path, monkeypatch, kind, family, source):
    """Real native launch and host, with real runtime rows; no outer Workflow."""
    f = RUNTIME.HostFixture(store, tmp_path / "runtime", kind=kind)
    selected = selector(projection(family), return_saved=kind == "compare",
                        uses=["sequence_align"] if kind == "extract_sequence" else [])
    asyncio.run(f.live())
    child = f.child(selector=selected, schema=RUNTIME.schema_for(source, FAILURE_SOURCE,
                                                               include_result_refs=kind == "inspect"))
    result = asyncio.run(f.collect(child, commit=False))
    receipt, host = result["result"], f.host
    custody = receipt["publication"]["custody"]
    assert receipt["publication"]["delivery_complete"]
    assert not any(host.own_fact_groups(child, verify_artifacts=False).values())
    assert host.completion(child) is None
    assert host.credit_view(child, None)["credit"] == 0
    with pytest.raises(ProteinStructureOperandError):
        host.read_result_authority(custody, scope=f.scope)
    key = receipt["body"]["intent"]["operation_key"]
    with monkeypatch.context() as guard:
        guard.setattr(hm, "capture_local_protein_structure_bundle", forbidden)
        guard.setattr(host, "_prepare_worker", forbidden)
        guard.setattr(hm, "publish_protein_structure_source", forbidden)
        guard.setattr(hm, "publish_protein_structure_projection", forbidden)
        assert asyncio.run(host.execute(child, f.target, "execution.results.collect", {}, key)) == result
    f.commit(child, result)
    f.episode_receipts.receive(child.episode_id, result["record_refs"], kind="own_action", source_index=0)
    view = host.read_result_authority(custody, scope=f.scope)
    facts, completion, credit = host.facts(child, verify_artifacts=False), host.completion(child), host.credit_view(child, None)
    assert facts["execution_completed"] and facts["execution_result_origin"] == hm.ORIGIN
    assert credit["credit"] == 3 and credit["new_acquired_record_count"] == 1
    assert completion["validation_keys"] == ["original_protein_result_commission", "complete_sealed_bundle_acquisition",
                                             "requested_protein_projection_or_explicit_unavailability"]
    assert len(completion) == 8
    assert host.own_fact_groups(child, verify_artifacts=True) == receipt["publication"]["facts"]
    form = f.returned(child)
    if kind == "extract_sequence":
        descriptor = view["facts"][SEQUENCE_SOURCE][0]
        assert descriptor["allowed_uses"] == ["sequence_align"]
        assert f.returns.authenticate_received_sequence(f.root, descriptor, required_use="sequence_align") == view
        with pytest.raises(ProteinStructureOperandError, match="sequence_not_received"):
            f.returns.authenticate_received_sequence(f.root, descriptor, required_use="structure_correspondence")
        references = f.returns.record_admission(f.root, form, child.request["report_contract"]["measurements"]["schema"],
            f"{f.run_id}:{f.root.episode_id}:1:typed_form")
        expected = [descriptor["reference_ref"], *(descriptor[name]["artifact_ref"] for name in
            ("sequence_file", "residue_map_file", "structure_file")), *(descriptor["custody"][name] for name in
            ("handoff_ref", "source_ref", "bundle_artifact_ref"))]
        assert references == expected and len(references) == 7
        assert all(f.returns.resolve_received(f.root, ref, None) is True
                   for ref in references if ref != descriptor["custody"]["handoff_ref"])
        # The existing practical handoff resolver owns the seventh operand.
        assert f.returns.resolve_received(f.root, descriptor["custody"]["handoff_ref"], None) is None
        assert f.returns.resolve_received(f.root, view["native_file"]["artifact_ref"], "artifact") is False
    if kind == "compare":
        descriptor = view["facts"][SAVED_SOURCE][0]
        assert f.returns.authenticate_received_saved_sheet(f.root, descriptor, required_use="recalculate") == view
    if kind == "inspect":
        status = f.child(index=2, selector=selected, schema=RUNTIME.schema_for(PROJECTION_SOURCE))
        status_result = asyncio.run(f.collect(status, name="execution.results.status"))["result"]
        assert status_result["body"]["capture"] is None and status_result["body"]["worker"] is None
        assert not any(host.own_fact_groups(status, verify_artifacts=False).values())
        assert host.completion(status) is None and host.credit_view(status, None)["credit"] == 0
        later = f.child(index=3, selector=selector(projection(family, identifier="later")),
                        schema=RUNTIME.schema_for(PROJECTION_SOURCE))
        second = asyncio.run(f.collect(later))["result"]
        assert second["publication"]["source_record"] == receipt["publication"]["source_record"]
        assert second["publication"]["custody"] != custody
        assert host.read_result_authority(second["publication"]["custody"], scope=f.scope)["selector"]["projections"][0]["projection_id"] == "later"
        assert host.read_result_authority(custody, scope=f.scope) == view
        assert host.credit_view(later, None)["credit"] == 0
    # Public history is the copied, committed metadata after loss of every
    # scientific and lifecycle artifact body, including original handoff bytes.
    for path in (store.path / "artifacts").glob("*/*"):
        if path.is_file():
            path.unlink()
    with monkeypatch.context() as guard:
        guard.setattr(store, "get_artifact", forbidden)
        guard.setattr(hm, "_prepare_worker_in_thread", forbidden)
        guard.setattr(hm, "validate_prepared_protein_structure_worker", forbidden)
        guard.setattr(hm, "capture_local_protein_structure_bundle", forbidden)
        guard.setattr(hm, "publish_protein_structure_projection", forbidden)
        assert host.read_result_authority(custody, scope=f.scope) == view
        assert host.facts(child, verify_artifacts=False) == facts
        assert host.completion(child) == completion
        assert host.credit_view(child, None) == credit
        assert all(host.owns_reference(ref) for ref in receipt["publication"]["family_artifact_refs"])
        assert asyncio.run(host.execute(child, f.target, "execution.results.collect", {}, key)) == result
        if kind == "extract_sequence":
            assert f.returns.authenticate_received_sequence(f.root, descriptor, required_use="sequence_align") == view
        if kind == "compare":
            assert f.returns.authenticate_received_saved_sheet(f.root, descriptor, required_use="recalculate") == view
    with pytest.raises(ProteinStructureOperandError, match="retained_artifact_missing"):
        host.own_fact_groups(child, verify_artifacts=True)


@pytest.mark.parametrize("damage", ["missing", "changed"])
def test_actual_capture_failure_never_grants_science(store, tmp_path, damage):
    f = RUNTIME.HostFixture(store, tmp_path / "runtime", kind="compare")
    asyncio.run(f.live())
    path = f.attempt_root / "protein-structure-attempt/result.json"
    if damage == "missing":
        path.unlink()
    else:
        path.write_bytes(b"changed original producer file")
    child = f.child(selector=selector(projection(), return_saved=True), schema=RUNTIME.schema_for(SAVED_SOURCE, FAILURE_SOURCE))
    result = asyncio.run(f.collect(child))
    receipt = result["result"]
    assert not receipt["publication"]["delivery_complete"]
    assert not any(receipt["body"]["qualified_files"].values())
    assert receipt["publication"]["facts"][SAVED_SOURCE] == []
    assert receipt["publication"]["facts"][PROJECTION_SOURCE] == []
    assert receipt["publication"]["accounting"]["failed_projection_ids"] == ["requested"]
    assert receipt["publication"]["facts"][FAILURE_SOURCE]
    assert f.host.completion(child) is None


def test_actual_saved_action_uses_original_pair_and_later_custody(store, tmp_path, monkeypatch):
    f = RUNTIME.HostFixture(store, tmp_path / "runtime", kind="compare")
    asyncio.run(f.live())
    original = f.child(selector=selector(projection(), return_saved=True), schema=RUNTIME.schema_for(SAVED_SOURCE))
    result = asyncio.run(f.collect(original))
    descriptor = result["result"]["publication"]["facts"][SAVED_SOURCE][0]
    f.returned(original)
    parameters = deepcopy(f.requested["native_protein_structure"]["request"]["parameters"])
    parameters["distance_threshold_A"] = 2.0
    missing = {"projection_id": "missing-coordinate-population", "family": "structure_coordinates",
        "members": {"kind": "coordinate_set", "coordinate_set_id": "not-requested-by-original"},
        "fields": ["xyz"], "window": None, "delivery_kind": "values"}
    child = f.child(index=2, selector=selector(projection(), missing,
                    projection("transform", identifier="matrix", delivery="artifact"),
                    saved=descriptor, parameters=parameters, return_saved=True),
                    schema=RUNTIME.schema_for(PROJECTION_SOURCE, SAVED_SOURCE, FAILURE_SOURCE))
    with monkeypatch.context() as guard:
        guard.setattr(hm, "capture_local_protein_structure_bundle", forbidden)
        guard.setattr(f.owner.job_progress_provider.targets, "observe_target", forbidden)
        saved = asyncio.run(f.collect(child))["result"]
    assert saved["publication"]["delivery_complete"]
    assert saved["publication"]["facts"][SAVED_SOURCE] == [descriptor]
    assert saved["publication"]["custody"] != descriptor["custody"]
    assert saved["body"]["original_custody"] == descriptor["custody"]
    assert saved["publication"]["source_record"] == result["result"]["publication"]["source_record"]
    assert saved["body"]["qualified_files"]["sheet_file"] == descriptor["sheet_file"]
    assert saved["body"]["qualified_files"]["original_components_file"] == descriptor["original_components_file"]
    assert saved["body"]["qualified_files"]["components_file"] != descriptor["original_components_file"]
    assert saved["publication"]["accounting"]["projection_ids"] == ["requested", "matrix"]
    assert saved["publication"]["accounting"]["failed_projection_ids"] == ["missing-coordinate-population"]
    assert f.host.own_fact_groups(child, verify_artifacts=True) == saved["publication"]["facts"]
    assert f.host.credit_view(child, None)["credit"] == 0
    assert f.host.completion(child)["validation_keys"][1] == "retained_original_sheet_custody"
    retained_protein_structure_file(store, descriptor["sheet_file"]).unlink()
    lost = f.child(index=3, selector=selector(projection(), saved=descriptor, parameters=parameters, return_saved=True),
                   schema=RUNTIME.schema_for(SAVED_SOURCE, FAILURE_SOURCE))
    failed = asyncio.run(f.collect(lost))["result"]
    assert not failed["publication"]["delivery_complete"]
    assert not any(failed["body"]["qualified_files"].values())
    assert failed["publication"]["source_record"] == result["result"]["publication"]["source_record"]
    assert any(row["issue"]["code"] == "retained_artifact_missing" for row in failed["publication"]["facts"][FAILURE_SOURCE])
    assert f.host.completion(child) is not None and f.host.completion(lost) is None


def test_actual_same_action_cancellation_drains_under_receipt_lock(store, tmp_path, monkeypatch):
    """Two explicit callers reuse one actual396 reservation after cancellation."""
    from gene_annotation_episode import native_lifecycle
    f = RUNTIME.HostFixture(store, tmp_path / "runtime", kind="inspect")
    asyncio.run(f.live())
    child = f.child(selector=selector(projection("structure_inventory")), schema=RUNTIME.schema_for(PROJECTION_SOURCE))
    key = f.select(child)
    entered, release = threading.Event(), threading.Event()
    original = hm._prepare_worker_in_thread
    calls, reservations = [], []
    prepare_job = native_lifecycle.prepare_job
    def reserve(*args, **kwargs):
        handle = prepare_job(*args, **kwargs)
        reservations.append(str(handle.path))
        return handle
    def blocked(*args, **kwargs):
        calls.append(kwargs["plan"]["directory"])
        if len(calls) == 1:
            entered.set()
            release.wait()
        return original(*args, **kwargs)
    monkeypatch.setattr(hm, "_prepare_worker_in_thread", blocked)
    monkeypatch.setattr(native_lifecycle, "prepare_job", reserve)
    async def concurrent():
        first = asyncio.create_task(f.host.execute(child, f.target, "execution.results.collect", {}, key))
        while not entered.is_set():
            await asyncio.sleep(0.01)
        second = asyncio.create_task(f.host.execute(child, f.target, "execution.results.collect", {}, key))
        await asyncio.sleep(0.02)
        assert not second.done()
        first.cancel()
        await asyncio.sleep(0.02)
        assert not first.done() and not second.done()
        first.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await first
        return await second
    try:
        result = asyncio.run(concurrent())
    finally:
        release.set()
    assert len(calls) == 2 and calls[0] == calls[1]
    assert len(reservations) == 1
    assert result["result"]["publication"]["delivery_complete"]
    f.commit(child, result)
    f.episode_receipts.receive(child.episode_id, result["record_refs"], kind="own_action", source_index=0)
    assert f.host.credit_view(child, None)["new_acquired_record_count"] == 1
    assert len(f.host.receipts.completed_receipts(child)) == 1


def test_actual_source_publication_interruption_reuses_capture_and_worker(store, tmp_path, monkeypatch):
    from gene_annotation_episode import native_lifecycle
    from gene_annotation_episode import native_protein_structure_acquisition
    f = RUNTIME.HostFixture(store, tmp_path / "runtime", kind="inspect")
    asyncio.run(f.live())
    child = f.child(selector=selector(projection("structure_inventory")), schema=RUNTIME.schema_for(PROJECTION_SOURCE))
    key = f.select(child)
    publish, sources = hm.publish_protein_structure_source, []
    def interrupted(*args, **kwargs):
        sources.append(publish(*args, **kwargs))
        raise RuntimeError("injected interruption after ordinary source write")
    with monkeypatch.context() as guard:
        guard.setattr(hm, "publish_protein_structure_source", interrupted)
        with pytest.raises(RuntimeError, match="injected interruption"):
            asyncio.run(f.host.execute(child, f.target, "execution.results.collect", {}, key))
    assert not any(f.host.own_fact_groups(child, verify_artifacts=False).values())
    with monkeypatch.context() as guard:
        guard.setattr(native_protein_structure_acquisition, "_producer_file", forbidden)
        for name in ("prepare_job", "start_prepared", "resume_start", "wait_job"):
            guard.setattr(native_lifecycle, name, forbidden)
        result = asyncio.run(f.host.execute(child, f.target, "execution.results.collect", {}, key))
    assert result["record_refs"] == sources
    f.commit(child, result)
    f.episode_receipts.receive(child.episode_id, sources, kind="own_action", source_index=0)
    assert f.host.credit_view(child, None)["new_acquired_record_count"] == 1
    assert f.host.completion(child) is not None

