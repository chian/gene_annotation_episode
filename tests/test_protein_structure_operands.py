"""Exact scientific bytes with a narrow received-authority fixture.

Fixture setup performs real C extraction/comparison and real Biopython alignment
inside the enclosing local_jobs cgroup. ToolRegistry publishes the full native
alignment and grading artifacts and its original operation row. The injected
returns ports prove only this module's consumption of an authenticated read
view; they are NOT proof of real runtime commissions, frozen typed delivery or
complete episode integration. Those checks belong to returns397 and root.
"""
from copy import deepcopy
from importlib import import_module
import json
import math
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
from types import SimpleNamespace

import numpy as np
import pytest

from gene_annotation_episode import protein_structure_operands as operands
from gene_annotation_episode import protein_structure_calculations as calculations
from gene_annotation_episode import protein_structure_formats as formats
from gene_annotation_episode import sequence_ops
from gene_annotation_episode.domain import canonical as domain_canonical, identity
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.native_protein_structure_acquisition import (
    capture_local_protein_structure_bundle, decode_protein_structure_json,
)
from gene_annotation_episode.native_protein_structure_contracts import (
    output_files, requested_job_from_protein_structure, required_input_files,
)
from gene_annotation_episode.native_protein_structure_driver import run_protein_structure_driver
from gene_annotation_episode.native_protein_structure_local import (
    prepare_local_protein_structure, local_protein_structure_plan,
)
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.protein_structure_authority import ProteinStructureOperandError
from gene_annotation_episode.protein_structure_contracts import issue, same
from gene_annotation_episode.protein_structure_publication import protein_structure_source_payload
from gene_annotation_episode.protein_structure_result_views import project_protein_structure_results
from gene_annotation_episode.protein_structure_result_worker import run_protein_structure_result_worker
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry, SequenceWork

F = import_module("verification.tool_graders_protein_structure_execution_2026-10-27_390.fixture_helpers")
A = import_module("verification.tool_graders_protein_structure_inputs_2026-10-27_386.fixture_helpers")
GROUPS = ("execution_protein_structure_projections", "execution_protein_structure_saved_sheets",
    "execution_protein_structure_sequences", "execution_protein_structure_failures")
USES = ["sequence_align", "structure_correspondence"]
SAVED_USES = ["recalculate", "select_projection", "use_transform"]


def encoded(value):
    return canonical(value).encode("utf-8")


def retained(store, raw, format, media="application/json"):
    ref = store.artifact(raw, media)
    meta = store.get(ref)
    return {"artifact_ref": ref, "sha256": meta["sha256"], "byte_length": meta["size"], "format": format}


def ordinary_source(store, *, provider="fixture.input", version=None, artifact=None):
    return store.put("source", {"provider": provider, "accession": None, "uri": None,
        "artifact_ref": artifact or store.artifact(b"explicit fixture input", "text/plain"),
        "text_ref": None, "request_ref": None, "version": version, "retrieved_at": None}, origin="caller")


def custody(store, source, label):
    handoff = ordinary_source(store, provider="fixture.handoff." + label)
    value = {"run_id": "synthetic-run", "result_episode_id": "fixture-result-" + label,
        "result_operation_key": "synthetic-run:fixture-result-" + label + ":0",
        "result_receipt_key": "", "handoff_ref": handoff["id"], "source_ref": source["id"],
        "bundle_artifact_ref": source["artifact_ref"], "original_request_sha256": digest({"fixture_assignment": label})}
    value["result_receipt_key"] = "protein_structure_result_receipt:" + digest({
        "run_id": value["run_id"], "episode_id": value["result_episode_id"], "operation_key": value["result_operation_key"]})
    return value


def selector(*, descriptor=None, parameters=None, projections=(), uses=(), saved=False):
    return {"version": "protein_structure_result_selector_v1",
        "acquisition": "retained_sheet_only" if descriptor is not None else "complete_bound_bundle",
        "saved_sheet": deepcopy(descriptor), "parameters": deepcopy(parameters),
        "projections": list(deepcopy(projections)), "return_saved_sheet": saved,
        "sequence_allowed_uses": list(uses)}


def native_fixture(store, directory, label, *, request=None, inputs=None, sequence="AGST", chain="A"):
    directory.mkdir(parents=True)
    selected = F.job(directory, kind="extract_sequence", fixed_kwargs={"sequence": sequence, "chain": chain,
        "coordinates": [[float(i % 2), float((i // 2) % 2), float(i // 4)] for i in range(len(sequence))]}) if request is None else F.job(directory, request=request, inputs=inputs)
    assignment = {"resource_kind": "local", "resource_id": "local", "workspace": str(directory),
        "requested_job": requested_job_from_protein_structure(selected), "constraints": {"allocation": deepcopy(F.POLICY)}}
    state = SimpleNamespace(assignment=assignment, run_id="synthetic-run", episode_id="synthetic-episode")
    reservation = directory / ".episode-operations" / digest({"run": state.run_id, "episode": state.episode_id}) / digest("selected-start")
    handle = prepare_local_protein_structure(state, "selected-start", root=reservation, policy=LocalJobPolicy(**F.POLICY))
    plan = local_protein_structure_plan(assignment, str(handle.path))
    # Preparation records a real C reservation. The driver runs within this
    # outer bounded worker; this fixture makes no runtime completion claim.
    bundle = run_protein_structure_driver(plan)
    assert bundle["native_status"] == "complete", bundle["failures"]
    target = {"version": "execution_target_v1", "handle": "fixture-" + label,
        "run_id": plan["identity"]["run_id"], "origin_episode_id": plan["identity"]["episode_id"],
        "resource_id": "local", "resource_kind": "local", "execution_id": plan["identity"]["execution_id"],
        "request_sha256": plan["identity"]["requested_job_sha256"], "assignment": assignment, "scope": {}}
    capture = capture_local_protein_structure_bundle(store, target=target, directory=directory / "capture")
    assert capture["capture_complete"], capture
    native_file = next(row["observed"] for row in capture["files"] if row["declared"]["role"] == "native_result")
    native = json.loads(store.get_artifact(native_file["artifact_ref"]))
    worker_plan = {"version": "protein_structure_result_worker_plan_v1", "mode": "original_native_result",
        "directory": str(directory / "qualified"), "expected_request": native["request"],
        "expected_software": native["producer"], "native_result": {"file_identity": native_file,
            "path": str(store.path / "artifacts" / native_file["sha256"][:2] / native_file["sha256"])}}
    prepared = run_protein_structure_result_worker(worker_plan)
    for field in ("native_result_file", "sheet_file", "components_file"):
        row = prepared[field]
        if row is not None:
            assert retained(store, (directory / "qualified" / row["relative_path"]).read_bytes(),
                row["file_identity"]["format"]) == row["file_identity"]
    source = store.put("source", protein_structure_source_payload(bundle=bundle, capture=capture,
        worker_result=prepared), origin="tool")
    owner = custody(store, source, label)
    view = {"custody": owner, "selector": selector(), "request": native["request"], "software": native["producer"],
        "native_file": native_file, "sequence_file": None, "residue_map_file": None,
        "sheet_file": prepared["sheet_file"]["file_identity"] if prepared["sheet_file"] else None,
        "original_components_file": prepared["components_file"]["file_identity"] if prepared["components_file"] else None,
        "components_file": prepared["components_file"]["file_identity"] if prepared["components_file"] else None,
        "facts": {name: [] for name in GROUPS}}
    if native["request"]["operation"] == "extract_sequence":
        for role, key in (("sequence", "sequence_file"), ("residue_map", "residue_map_file")):
            view[key] = next(row["observed"] for row in capture["files"] if row["declared"]["role"] == role)
        seq = native["sequence"]
        reference = store.put("reference", {"reference_type": "protein", "source_ref": source["id"],
            "accession": "structure_sequence_" + digest(seq), "label": "Structure-derived protein sequence",
            "sequence_ref": view["sequence_file"]["artifact_ref"], "molecule": "protein", "length": seq["sequence_length"],
            "term_refs": [], "context_refs": [], "anchor": None}, origin="tool")
        descriptor = {"version": "structure_sequence_descriptor_v1", "custody": deepcopy(owner),
            "reference_ref": reference["id"], "sequence_file": view["sequence_file"], "residue_map_file": view["residue_map_file"],
            "structure_file": seq["selection"]["file_identity"], "selection": seq["selection"],
            "sequence_length": seq["sequence_length"], "allowed_uses": list(USES)}
        view["selector"] = selector(uses=USES)
        view["facts"][GROUPS[2]] = [deepcopy(descriptor)]
    else:
        descriptor = {"version": "protein_structure_saved_sheet_v1", "custody": deepcopy(owner),
            "sheet_file": view["sheet_file"], "original_components_file": view["original_components_file"],
            "operation": "compare_protein_structures", "original_mode": native["request"]["parameters"]["mode"],
            "allowed_uses": list(SAVED_USES)}
        view["selector"] = selector(saved=True)
        view["facts"][GROUPS[1]] = [deepcopy(descriptor)]
    return {"descriptor": descriptor, "view": view, "native": native, "bundle": bundle,
        "capture": capture, "target": target, "prepared": prepared}


def alignment_fixture(store, registry, directory, fixed, moving, *, mode, ordinal):
    args = {"query_ref": fixed["descriptor"]["reference_ref"], "reference_ref": moving["descriptor"]["reference_ref"],
        "molecule": "protein", "mode": mode}
    native = sequence_ops.align_pair(fixed["native"]["sequence"]["alignment_sequence"],
        moving["native"]["sequence"]["alignment_sequence"], molecule="protein", mode=mode)
    path = directory / ("original-alignment-" + str(ordinal) + ".json")
    path.write_bytes(encoded(native))
    # The actual selected ToolRegistry operation publishes these measured native
    # bytes. Only resource transport is replaced for this bounded module fixture.
    previous = registry._prepare_sequence_work_async
    async def prepared(*args, **kwargs):
        return SequenceWork(path, {"fixture": "398 actual align_pair inside enclosing local_jobs"})
    registry._prepare_sequence_work_async = prepared
    key = "synthetic-run:operand-reader:" + str(ordinal)
    try:
        outcome = registry.execute("sequence.align", args, operation_key=key)
    finally:
        registry._prepare_sequence_work_async = previous
    assert outcome["status"] == "completed", outcome
    body = outcome["result"]
    source = store.get(body["source_ref"])
    def file(ref, format):
        m = store.get(ref)
        return {"artifact_ref": ref, "sha256": m["sha256"], "byte_length": m["size"], "format": format}
    descriptor = {"version": "structure_alignment_descriptor_v1", "observation_ref": body["observation_ref"],
        "source_ref": source["id"], "original_operation_key": key, "query_reference_ref": args["query_ref"],
        "reference_reference_ref": args["reference_ref"], "native_file": file(source["artifact_ref"], "biopython_pairwise_json"),
        "grading_file": file(source["auxiliary_artifact_refs"][0], "tool_grading_artifact_v1"),
        "molecule": "protein", "mode": mode, "traceback_selection": "explicit_retained",
        "producer_traceback_selection": "first_native_optimal_returned", "optimal_alternative_count": None}
    return {"descriptor": descriptor, "outcome": outcome, "arguments": args}


def projection(store, view, sheet, components, *, fields=("rotation", "translation"), artifact=False, label="transform"):
    selection = {"projection_id": label, "family": "transform", "members": {"kind": "transform"},
        "fields": list(fields), "window": None, "delivery_kind": "artifact" if artifact else "values"}
    rows = project_protein_structure_results({"kind": "comparison", "sheet": sheet, "components": components}, selection=[selection])[0]
    result = {key: deepcopy(value) for key, value in rows.items() if key not in {"version", "calculation_id", "rows"}}
    result.update(version="protein_structure_projection_v1", custody=deepcopy(view["custody"]),
        calculation={"calculation_id": components["calculation_id"], "input_numerical_sha256": components["input_numerical_sha256"],
            "components_file": deepcopy(view["components_file"])})
    if artifact:
        file = retained(store, encoded({"version": "protein_structure_projection_table_v1", "rows": rows["rows"]}),
            "protein_structure_projection_table_v1")
        result["delivery"] = {"kind": "artifact", "table_file": file, "row_count": len(rows["rows"]), "allowed_use": "read_exact_selected_table"}
    else:
        result["delivery"] = {"kind": "values", "rows": rows["rows"]}
    view["facts"][GROUPS[0]].append(deepcopy(result))
    view["selector"]["projections"].append(deepcopy(selection))
    return result


@pytest.fixture(scope="module")
def original_assets(tmp_path_factory):
    root = tmp_path_factory.mktemp("398-original-native-fixtures")
    with Store(root / "store") as store:
        problem = store.create_problem(raw_sequence="AGST", molecule="protein", role="protein")
        registry = ToolRegistry(store)
        rows = {}
        for label, sequence, chain in (("fixed", "AGST", "A"), ("moving", "AGST", "B"),
                ("local", "WAGSTW", "C"), ("zero_q", "AAAA", "D"), ("zero_r", "WWWW", "E")):
            rows[label] = native_fixture(store, root / label, label, sequence=sequence, chain=chain)
        alignments = {}
        for i, (label, q, r, mode) in enumerate((("global", "fixed", "moving", "global"),
                ("reverse", "moving", "fixed", "global"), ("local", "local", "fixed", "local"),
                ("zero", "zero_q", "zero_r", "local"))):
            alignments[label] = alignment_fixture(store, registry, root, rows[q], rows[r], mode=mode, ordinal=i)
        coords = A.DEFAULT_XYZ + [[2.0, 2.0, 2.0]]
        moving = deepcopy(coords); moving[-1][0] += 2.0
        request, inputs = F.requests("compare", fixed_kwargs={"sequence": "AGSTA", "coordinates": coords},
            moving_kwargs={"sequence": "AGSTA", "coordinates": moving})
        request["parameters"]["fit_selection"] = {"kind": "explicit", "members": [
            {"kind": "correspondence_id", "correspondence_id": "map_" + str(i)} for i in range(4)]}
        request["parameters"]["evaluation_selection"] = {"kind": "explicit", "members": [
            {"kind": "correspondence_id", "correspondence_id": "map_4"}]}
        saved = native_fixture(store, root / "held-out", "held-out", request=request, inputs=inputs)
        sheet = saved["native"]["sheet"]
        baseline = sheet["native_baseline"]
        original_projection = projection(store, saved["view"], sheet, baseline)
        table_projection = projection(store, saved["view"], sheet, baseline, artifact=True, label="transform-table")
        later_parameters = deepcopy(sheet["native_request"])
        later_parameters["evaluation_selection"] = {"kind": "all_mapped_pairs"}
        later = calculations.calculate_protein_structure_components(sheet, parameters=later_parameters)
        later_view = deepcopy(saved["view"])
        later_view["custody"] = custody(store, store.get(saved["descriptor"]["custody"]["source_ref"]), "later-calculation")
        later_view["custody"]["handoff_ref"] = saved["descriptor"]["custody"]["handoff_ref"]
        later_view["components_file"] = retained(store, encoded(later), "protein_structure_components_v1")
        later_view["selector"] = selector(descriptor=saved["descriptor"], parameters=later_parameters)
        later_view["facts"] = {name: [] for name in GROUPS}
        later_projection = projection(store, later_view, sheet, later)
        data = {"rows": rows, "alignments": alignments, "saved": saved, "later_view": later_view,
            "later_components": later, "projections": [original_projection, table_projection, later_projection], "scope": problem}
        receipts = EpisodeReceipts(store, "synthetic-run")
        receipts.bind("operand-reader")
        refs = [r["id"] for kind in ("source", "reference", "observation") for r in store.list(kind)]
        refs += [row[0] for row in store.db.execute("SELECT id FROM artifacts")]
        receipts.receive("operand-reader", refs, kind="initial")
        (root / "fixture.json").write_bytes(encoded(data))
        (root / "filled_examples.json").write_bytes(encoded({
            "qualification": "fresh398 actual synthetic native engineering fixtures; narrow returns port is not episode proof",
            "fit_used": baseline["counts"]["fit_used_count"], "held_out_used": baseline["counts"]["evaluation_used_count"],
            "held_out_sse": baseline["evaluation"]["evaluation_sse"], "held_out_rmsd": baseline["evaluation"]["evaluation_rmsd"],
            "later_all_pairs_used": later["counts"]["evaluation_used_count"], "later_all_pairs_rmsd": later["evaluation"]["evaluation_rmsd"],
            "original_calculation_id": baseline["calculation_id"], "later_calculation_id": later["calculation_id"]}))
    return root


class ReceivedPortFixture:
    """Injected public ports only. No claim of original runtime/report proof."""
    def __init__(self, store, data, context):
        self.store, self.run_id, self.context = store, context.run_id, context
        self.sequences = [deepcopy(row["descriptor"]) for row in data["rows"].values()]
        self.saved = [deepcopy(data["saved"]["descriptor"])]
        views = [row["view"] for row in data["rows"].values()] + [data["saved"]["view"], data["later_view"]]
        self.views = {digest(row["custody"]): deepcopy(row) for row in views}
        self.alignments = [deepcopy(row["descriptor"]) for row in data["alignments"].values()]
        self.projections = deepcopy(data["projections"])
        self.owner = SimpleNamespace(native_protein_structure_results=self)
        self.denied_refs = set()
        self.calls = []

    def authenticate(self, context, *, allow_unsaved=False):
        assert context is self.context
        return context

    def received_sequence_descriptors(self, context, reference_ref):
        return deepcopy([v for v in self.sequences if v["reference_ref"] == reference_ref])

    def authenticate_received_sequence(self, context, descriptor, *, required_use):
        self.calls.append(("sequence", required_use))
        if not any(same(v, descriptor) for v in self.sequences) or required_use not in descriptor["allowed_uses"]:
            raise ProteinStructureOperandError(issue("sequence_not_received", stage="authority", field="descriptor"))
        return self.read_result_authority(descriptor["custody"], scope=context.scope)

    def authenticate_received_saved_sheet(self, context, descriptor, *, required_use):
        self.calls.append(("saved", required_use))
        if not any(same(v, descriptor) for v in self.saved) or required_use not in descriptor["allowed_uses"]:
            raise ProteinStructureOperandError(issue("saved_sheet_not_received", stage="authority", field="descriptor"))
        return self.read_result_authority(descriptor["custody"], scope=context.scope)

    def authenticate_received_alignment(self, context, alignment):
        if not any(same(v, alignment) for v in self.alignments):
            raise ProteinStructureOperandError(issue("alignment_not_received", stage="authority", field="alignment"))

    def received_transform_projections(self, context, transform):
        return deepcopy([row for row in self.projections if same(row["custody"], transform["received_from"]["calculation_custody"])])

    def read_result_authority(self, custody, *, scope):
        self.calls.append(("original", digest(custody)))
        return deepcopy(self.views[digest(custody)])

    def resolve_received(self, context, reference, namespace):
        return False if reference in self.denied_refs else None

    def retained_reference_access(self, context, reference, namespace):
        return False if reference in self.denied_refs else None


@pytest.fixture
def f(original_assets, tmp_path):
    shutil.copytree(original_assets / "store", tmp_path / "store")
    store = Store(tmp_path / "store")
    data = json.loads((original_assets / "fixture.json").read_bytes())
    context = SimpleNamespace(run_id="synthetic-run", episode_id="operand-reader", role="scientific",
        scope=data["scope"], assignment={})
    result = SimpleNamespace(store=store, data=data, context=context, root=tmp_path)
    result.returns = ReceivedPortFixture(store, data, context)
    yield result
    store.close()


def forbidden(*args, **kwargs):
    raise AssertionError("operand authentication attempted new execution, acquisition, fitting, calculation or publication")


def readonly(f, monkeypatch):
    monkeypatch.setattr(sequence_ops, "align_pair", forbidden)
    monkeypatch.setattr(calculations, "calculate_protein_structure_components", forbidden)
    monkeypatch.setattr(calculations, "fit_ca_transform", forbidden)
    monkeypatch.setattr(np.linalg, "svd", forbidden)
    monkeypatch.setattr(formats, "parse_pdb_structure", forbidden)
    monkeypatch.setattr(formats, "parse_mmcif_structure", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(f.store, "put", forbidden)
    monkeypatch.setattr(f.store, "artifact", forbidden)
    monkeypatch.setattr(f.store, "_validate_record", forbidden)
    monkeypatch.setattr(import_module("gene_annotation_episode.native_protein_structure_worker"), "execute_protein_structure_request", forbidden)
    monkeypatch.setattr(import_module("gene_annotation_episode.native_protein_structure_acquisition"), "capture_local_protein_structure_bundle", forbidden)
    monkeypatch.setattr(import_module("gene_annotation_episode.biopython_pairwise_grader"), "calculate_biopython_pairwise_scores", forbidden)
    # SELECT/READ/PRAGMA-only is checked by SQLite itself; any hidden receipt
    # helper creating tables or committing would violate this read-only guard.
    f.store.db.execute("PRAGMA query_only=ON")


def desc(f, label="fixed"):
    return f.data["rows"][label]["descriptor"]


def alignment(f, label="global"):
    return f.data["alignments"][label]["descriptor"]


def comparison(f, *, orientation="fixed_is_query", label="global"):
    request = deepcopy(f.data["saved"]["view"]["request"])
    request["parameters"] = A.fit_parameters()
    for side in ("fixed", "moving"):
        request[side + "_selection"] = deepcopy(desc(f, side)["selection"])
        request[side + "_selection"]["structure_role"] = side
    request["correspondence"] = {"kind": "retained_alignment", "alignment": deepcopy(alignment(f, label)),
        "fixed_sequence_descriptor": deepcopy(desc(f)), "moving_sequence_descriptor": deepcopy(desc(f, "moving")),
        "orientation": orientation}
    return request


def declared(f, *, later=False):
    view = f.data["later_view"] if later else f.data["saved"]["view"]
    components = f.data["later_components"] if later else f.data["saved"]["native"]["sheet"]["native_baseline"]
    request = f.data["saved"]["view"]["request"]
    return {"version": "protein_structure_transform_v1", "direction": "moving_to_fixed", "convention": "row_vector_y_R_plus_t",
        "rotation": deepcopy(components["transform"]["rotation"]["value"]),
        "translation_A": deepcopy(components["transform"]["translation"]["value"]),
        "fixed_selection": deepcopy(request["fixed_selection"]), "moving_selection": deepcopy(request["moving_selection"]),
        "origin": "received_fitted", "received_from": {"saved_sheet": deepcopy(f.data["saved"]["descriptor"]),
            "components_file": deepcopy(view["components_file"]), "calculation_id": components["calculation_id"],
            "calculation_custody": deepcopy(view["custody"])}}


def error(code, *, stage=None, field=None):
    class Check:
        def __enter__(self):
            self.manager = pytest.raises(ProteinStructureOperandError)
            self.caught = self.manager.__enter__()
            return self.caught
        def __exit__(self, *args):
            self.manager.__exit__(*args)
            e = self.caught.value
            assert str(e) == code
            assert e.detail == {"protein_structure_issue": e.issue}
            if stage is not None: assert e.issue["stage"] == stage
            if field is not None: assert e.issue["field"] == field
            assert all(e.issue[k] is None for k in ("position_key", "atom_row_key", "correspondence_id"))
            return True
    return Check()


def test_original_sequence_exact_readonly_and_detached(f, monkeypatch):
    before = deepcopy(desc(f))
    readonly(f, monkeypatch)
    result = operands.authenticate_structure_sequence_reference(f.store, f.context, before["reference_ref"], returns=f.returns)
    assert same(result, before) and result is not before
    assert f.store.get_artifact(result["sequence_file"]["artifact_ref"]) == b"AGST"
    assert ("sequence", "sequence_align") in f.returns.calls
    result["allowed_uses"].clear()
    assert desc(f)["allowed_uses"] == USES


@pytest.mark.parametrize("kind", ["absent", "wrong_use", "missing_binding"])
def test_sequence_receipt_and_use_required(f, monkeypatch, kind):
    if kind == "absent": f.returns.sequences.clear()
    if kind == "wrong_use": f.returns.sequences[0]["allowed_uses"] = ["structure_correspondence"]
    readonly(f, monkeypatch)
    expected = "original_commission_mismatch" if kind == "missing_binding" else "sequence_not_received"
    with error(expected):
        operands.authenticate_structure_sequence_reference(f.store, f.context, desc(f)["reference_ref"],
            returns=None if kind == "missing_binding" else f.returns)


def test_first_eligible_received_witness_is_not_a_union(f, monkeypatch):
    original = deepcopy(desc(f))
    first = deepcopy(original); first["allowed_uses"] = ["structure_correspondence"]
    second = deepcopy(original); second["allowed_uses"] = ["sequence_align"]
    f.returns.sequences[:1] = [first, second, original]
    readonly(f, monkeypatch)
    result = operands.authenticate_structure_sequence_reference(f.store, f.context, original["reference_ref"], returns=f.returns)
    assert result["allowed_uses"] == ["sequence_align"]


@pytest.mark.parametrize("field", ["structure_role", "chain_key", "model_key", "sequence_basis", "ca_selection", "symbol_policy", "semantics_evidence"])
def test_exact_original_selection_cannot_be_reinterpreted(f, monkeypatch, field):
    value = desc(f)
    original = f.returns.views[digest(value["custody"])]
    changed = deepcopy(original["request"])
    changed["selection"][field] = deepcopy(desc(f, "moving")["selection"][field])
    if field == "structure_role": changed["selection"][field] = "fixed"
    elif field == "model_key": changed["selection"][field]["ordinal_0based"] = 1
    elif field == "sequence_basis": changed["selection"][field] = "mmcif_declared_polymer"
    elif field == "ca_selection": changed["selection"][field]["policy"] = "explicit"
    elif field == "symbol_policy": changed["selection"][field]["unknown"] = "use_X"
    elif field == "semantics_evidence": changed["selection"]["bfactor_semantics"] = "physical_B"
    original["request"] = changed
    readonly(f, monkeypatch)
    with pytest.raises(ProteinStructureOperandError):
        operands.authenticate_structure_sequence_reference(f.store, f.context, value["reference_ref"], returns=f.returns)


@pytest.mark.parametrize("field", ["sequence_file", "residue_map_file", "structure_file", "native_file"])
@pytest.mark.parametrize("changed", [False, True])
def test_missing_retained_bytes_differ_from_digest_conflict(f, monkeypatch, field, changed):
    value = desc(f)
    file = value.get(field) or f.returns.views[digest(value["custody"])][field]
    path = f.store.path / "artifacts" / file["sha256"][:2] / file["sha256"]
    if changed: path.write_bytes(path.read_bytes() + b"changed")
    else: path.unlink()
    readonly(f, monkeypatch)
    with error("input_digest_mismatch" if changed else "retained_artifact_missing", stage="input", field="file_identity"):
        operands.authenticate_structure_sequence_reference(f.store, f.context, value["reference_ref"], returns=f.returns)


@pytest.mark.parametrize("field", ["sequence_file", "residue_map_file"])
def test_valid_different_artifact_never_substitutes_original_map_or_sequence(f, monkeypatch, field):
    value = desc(f)
    raw = f.store.get_artifact(value[field]["artifact_ref"])
    changed = raw.replace(b"AGST", b"AGSA") if field == "sequence_file" else raw + b"\n"
    replacement = retained(f.store, changed, value[field]["format"])
    value[field] = replacement
    f.returns.sequences[0] = deepcopy(value)
    f.returns.views[digest(value["custody"])][field] = deepcopy(replacement)
    readonly(f, monkeypatch)
    with error("sequence_artifact_mismatch", stage="sequence"):
        operands.authenticate_structure_sequence_reference(f.store, f.context, value["reference_ref"], returns=f.returns)


def derivative(store, reference, *, product=False, origin="reasoning"):
    feature = store.put("feature", {"subject_ref": reference, "kind": "sequence_region",
        "segments": [{"start": 0, "end": 3}], "strand": "+", "context_refs": []}, origin=origin)
    if not product: return feature["id"]
    return store.put("product", {"parent_refs": [feature["id"]], "molecule": "protein",
        "sequence_ref": store.artifact(b"AGS", "text/plain"), "derivation": "extraction", "context_refs": [],
        "footprint": []}, origin="tool")["id"]


@pytest.mark.parametrize("product", [False, True])
def test_immutable_reasoning_and_product_ancestry_protected(f, monkeypatch, product):
    wrapper = derivative(f.store, desc(f)["reference_ref"], product=product)
    readonly(f, monkeypatch)
    assert operands.is_protein_structure_sequence_operand(f.store, wrapper)
    with error("sequence_not_received", stage="authority", field="descriptor"):
        operands.authenticate_structure_sequence_reference(f.store, f.context, wrapper, returns=f.returns)


@pytest.mark.parametrize("cropped", [False, True])
def test_actual_sequence_view_constructor_cannot_bypass_exact_descriptor(f, monkeypatch, cropped):
    registry = ToolRegistry(f.store)
    args = {"subject_ref": desc(f)["reference_ref"], "molecule": "protein"}
    if cropped: args["segments"] = [{"start": 1, "end": 3}]
    result = registry.execute("sequence.view", args, operation_key="398-wrapper")
    assert result["status"] == "completed", result
    wrapper = result["result"]["records"][0]["product_ref"]
    readonly(f, monkeypatch)
    assert operands.is_protein_structure_sequence_operand(f.store, wrapper)
    with error("sequence_not_received"):
        operands.authenticate_structure_sequence_reference(f.store, f.context, wrapper, returns=f.returns)


def test_ordinary_equal_bytes_and_unrelated_provenance_are_not_protected(f, monkeypatch):
    source = ordinary_source(f.store, artifact=desc(f)["sequence_file"]["artifact_ref"])
    ref = f.store.put("reference", {"reference_type": "protein", "source_ref": source["id"],
        "accession": "structure_sequence_looks_protected", "label": "Structure-derived protein sequence",
        "sequence_ref": desc(f)["sequence_file"]["artifact_ref"], "molecule": "protein", "length": 4,
        "term_refs": [], "context_refs": [], "anchor": None}, origin="tool")
    wrapper = derivative(f.store, ref["id"], product=True)
    readonly(f, monkeypatch)
    assert not operands.is_protein_structure_sequence_operand(f.store, f.context.scope["subject_refs"][0])
    assert not operands.is_protein_structure_sequence_operand(f.store, ref["id"])
    assert not operands.is_protein_structure_sequence_operand(f.store, wrapper)


def test_iterative_dag_checks_every_parent_without_depth_limit(f, monkeypatch):
    # Deliberately insert valid immutable schema records directly: ordinary
    # Store construction recursively computes unrelated sequence footprints.
    def insert(kind, payload):
        key = identity(kind, {"origin": "reasoning", "record": payload})
        record = dict(payload, id=key, record_type=kind, origin="reasoning")
        f.store.db.execute("INSERT INTO records VALUES(?,?,?,?)", (key, kind, "reasoning", domain_canonical(record)))
        return key
    protected = desc(f)["reference_ref"]
    ordinary = f.context.scope["subject_refs"][0]
    leaf = insert("product", {"parent_refs": [ordinary, protected], "molecule": "protein", "sequence_ref": desc(f)["sequence_file"]["artifact_ref"],
        "derivation": "extraction", "context_refs": [], "footprint": []})
    for _ in range(1100):
        leaf = insert("feature", {"subject_ref": leaf, "kind": "sequence_region", "segments": [{"start": 0, "end": 3}],
            "strand": "+", "context_refs": []})
    shared = insert("product", {"parent_refs": [leaf, protected, leaf], "molecule": "protein", "sequence_ref": desc(f)["sequence_file"]["artifact_ref"],
        "derivation": "extraction", "context_refs": [], "footprint": []})
    readonly(f, monkeypatch)
    assert operands.is_protein_structure_sequence_operand(f.store, shared)


@pytest.mark.parametrize("fault", ["missing_source", "wrong_kind", "missing_parent", "malformed_link", "altered_identity", "cycle"])
def test_classifier_corruption_fails_closed(f, monkeypatch, fault):
    wrapper = derivative(f.store, desc(f)["reference_ref"], product=True)
    product = f.store.get(wrapper)
    feature = f.store.get(product["parent_refs"][0])
    if fault == "missing_source":
        f.store.db.execute("DELETE FROM records WHERE id=?", (desc(f)["custody"]["source_ref"],))
    else:
        payload = {k: v for k, v in feature.items() if k not in {"id", "record_type", "origin"}}
        if fault == "malformed_link": payload["subject_ref"] = []
        elif fault == "missing_parent": payload["subject_ref"] = "reference_" + "f" * 24
        elif fault == "wrong_kind": payload["subject_ref"] = desc(f)["custody"]["source_ref"]
        elif fault == "cycle": payload["subject_ref"] = wrapper
        else: payload["strand"] = "."
        # Preserve the intentionally corrupted record id: immutable contradiction
        # itself must reject before trying any generic ordinary fallback.
        record = dict(payload, id=feature["id"], record_type="feature", origin=feature["origin"])
        f.store.db.execute("UPDATE records SET data=? WHERE id=?", (domain_canonical(record), feature["id"]))
    readonly(f, monkeypatch)
    with error("invalid_schema" if fault == "malformed_link" else "conflicting_identity", stage="authority", field="descriptor"):
        operands.is_protein_structure_sequence_operand(f.store, wrapper)


@pytest.mark.parametrize("label, fixed_label, moving_label, orientation", [
    ("global", "fixed", "moving", "fixed_is_query"), ("reverse", "fixed", "moving", "fixed_is_reference"),
    ("local", "local", "fixed", "fixed_is_query"), ("zero", "zero_q", "zero_r", "fixed_is_query")])
def test_real_original_alignment_full_traceback_and_zero(f, monkeypatch, label, fixed_label, moving_label, orientation):
    readonly(f, monkeypatch)
    snapshot = operands.authenticate_selected_alignment(f.store, f.context, alignment(f, label),
        fixed=desc(f, fixed_label), moving=desc(f, moving_label), orientation=orientation, returns=f.returns)
    assert snapshot["native_result"]["mode"] == alignment(f, label)["mode"]
    if label == "zero":
        assert snapshot["native_result"]["aligned"] is False
        assert snapshot["pairwise_sheet"]["measured_column_counts"]["paired_positions"] == 0
    else:
        assert snapshot["pairwise_sheet"]["measured_column_counts"]["paired_positions"] == 4
    if label == "local": assert snapshot["pairwise_sheet"]["geometry"]["query_interval"] == [1, 5]


@pytest.mark.parametrize("change", ["wrong_mode", "reads_align", "wrong_operation_key", "missing_operation", "unreceived", "wrong_orientation", "wrong_grading"])
def test_alignment_original_binding_rejects_substitution(f, monkeypatch, change):
    value = alignment(f)
    if change == "wrong_mode":
        row = f.store.db.execute("SELECT arguments FROM tool_operations WHERE operation_key=?", (value["original_operation_key"],)).fetchone()
        args = json.loads(row[0]); args["mode"] = "local"
        f.store.db.execute("UPDATE tool_operations SET arguments=? WHERE operation_key=?", (domain_canonical(args), value["original_operation_key"]))
    elif change == "reads_align": f.store.db.execute("UPDATE tool_operations SET name='reads.align' WHERE operation_key=?", (value["original_operation_key"],))
    elif change == "missing_operation": f.store.db.execute("DELETE FROM tool_operations WHERE operation_key=?", (value["original_operation_key"],))
    elif change == "unreceived": f.returns.alignments.clear()
    elif change == "wrong_operation_key": value["original_operation_key"] += "-wrong"; f.returns.alignments[0] = deepcopy(value)
    elif change == "wrong_grading": value["grading_file"] = deepcopy(alignment(f, "local")["grading_file"]); f.returns.alignments[0] = deepcopy(value)
    readonly(f, monkeypatch)
    with error("alignment_not_received" if change == "unreceived" else "alignment_operand_mismatch"):
        operands.authenticate_selected_alignment(f.store, f.context, value, fixed=desc(f), moving=desc(f, "moving"),
            orientation="fixed_is_reference" if change == "wrong_orientation" else "fixed_is_query", returns=f.returns)


def test_alignment_corrupt_traceback_never_becomes_zero(f, monkeypatch):
    value = alignment(f)
    native = json.loads(f.store.get_artifact(value["native_file"]["artifact_ref"]))
    native["coordinates"] = [[0, 9], [0, 9]]
    replacement = retained(f.store, domain_canonical(native).encode(), "biopython_pairwise_json")
    source = f.store.get(value["source_ref"])
    payload = {k: v for k, v in source.items() if k not in {"id", "record_type", "origin"}}
    grade = json.loads(f.store.get_artifact(value["grading_file"]["artifact_ref"]))
    grade["native_artifact_ref"] = replacement["artifact_ref"]
    grade["grading"]["sheet"]["native_result"] = native
    grade_file = retained(f.store, domain_canonical(grade).encode(), "tool_grading_artifact_v1",
        "application/vnd.gene-annotation.tool-grading+json")
    payload.update(artifact_ref=replacement["artifact_ref"], auxiliary_artifact_refs=[grade_file["artifact_ref"]])
    new_source = f.store.put("source", payload, origin="tool")
    observation = f.store.get(value["observation_ref"])
    op = {k: v for k, v in observation.items() if k not in {"id", "record_type", "origin"}}
    op["source_ref"] = new_source["id"]
    new_observation = f.store.put("observation", op, origin="tool")
    value.update(source_ref=new_source["id"], observation_ref=new_observation["id"], native_file=replacement, grading_file=grade_file)
    row = f.store.db.execute("SELECT result FROM tool_operations WHERE operation_key=?", (value["original_operation_key"],)).fetchone()
    outcome = json.loads(row[0]); outcome["record_refs"] = [value["source_ref"], value["observation_ref"]]
    f.store.db.execute("UPDATE tool_operations SET result=? WHERE operation_key=?", (domain_canonical(outcome), value["original_operation_key"]))
    f.returns.alignments[0] = deepcopy(value)
    readonly(f, monkeypatch)
    with error("invalid_traceback", stage="correspondence", field="traceback"):
        operands.authenticate_selected_alignment(f.store, f.context, value, fixed=desc(f), moving=desc(f, "moving"),
            orientation="fixed_is_query", returns=f.returns)


def test_resolve_exact_retained_file_roles_without_staging(f, monkeypatch):
    request = comparison(f)
    readonly(f, monkeypatch)
    result = operands.resolve_comparison_operands(f.store, f.context, request, returns=f.returns)
    assert same(result["request"], request)
    assert [(x["role"], x["file_identity"]) for x in result["input_files"]] == required_input_files(request)
    assert all(row["path"].startswith(str(f.store.path / "artifacts")) for row in result["input_files"])
    assert [row["staged_relative_path"] for row in result["input_files"]] == ["inputs/input_" + str(i) for i in range(8)]
    assert set(result["selected_references"]) == set([file["artifact_ref"] for _, file in required_input_files(request)]
        + operands._sequence_refs(desc(f)) + operands._sequence_refs(desc(f, "moving"))
        + [alignment(f)["observation_ref"], alignment(f)["source_ref"]])


@pytest.mark.parametrize("changed", [False, True])
def test_selected_job_preserves_order_but_requires_exact_store_paths(f, monkeypatch, changed):
    request = comparison(f)
    resolved = operands.resolve_comparison_operands(f.store, f.context, request, returns=f.returns)
    files = list(reversed(resolved["input_files"]))
    for i, row in enumerate(files):
        row.update(input_id="input_" + str(i), staged_relative_path="inputs/input_" + str(i))
    job = {"version": "native_protein_structure_job_v1", "program": "protein_structure_python", "request": request,
        "software": f.data["saved"]["view"]["software"], "inputs": files, "outputs": output_files("compare"), "environment": {}}
    if changed: job["inputs"][0]["path"] = str(f.root / "identical-bytes-alias")
    assignment = {"requested_job": requested_job_from_protein_structure(job)}
    readonly(f, monkeypatch)
    if changed:
        with error("invalid_output_path"):
            operands.validate_protein_structure_job_inputs(f.store, f.context, assignment, returns=f.returns)
    else:
        assert operands.validate_protein_structure_job_inputs(f.store, f.context, assignment, returns=f.returns) == resolved["selected_references"]


def test_explicit_map_and_metadata_need_received_inputs(f, monkeypatch):
    request = deepcopy(f.data["saved"]["view"]["request"])
    hidden = request["correspondence"]["map_file"]["artifact_ref"]
    f.returns.denied_refs.add(hidden)
    readonly(f, monkeypatch)
    with error("original_commission_mismatch", field="receipt"):
        operands.resolve_comparison_operands(f.store, f.context, request, returns=f.returns)


def test_nonprotein_assignment_is_unchanged_without_binding(f):
    assert operands.validate_protein_structure_job_inputs(f.store, f.context, {"requested_job": {"argv": ["ordinary"]}}, returns=None) == []


def test_original_saved_sheet_baseline_and_handchecked_numbers(f, monkeypatch):
    readonly(f, monkeypatch)
    sheet = operands.validate_saved_structure_sheet_operand(f.store, f.context, f.data["saved"]["descriptor"], returns=f.returns)
    original = sheet["native_baseline"]
    assert original["counts"]["fit_used_count"]["value"] == 4
    assert original["counts"]["evaluation_used_count"]["value"] == 1
    assert original["evaluation"]["evaluation_sse"]["value"] == pytest.approx(4)
    assert original["evaluation"]["evaluation_rmsd"]["value"] == pytest.approx(2)


@pytest.mark.parametrize("fault", ["absent", "diagnostic", "missing_bytes", "bad_baseline", "wrong_original_mode"])
def test_saved_sheet_does_not_manufacture_original_baseline(f, monkeypatch, fault):
    descriptor = f.data["saved"]["descriptor"]
    if fault == "absent": f.returns.saved.clear()
    elif fault == "diagnostic": f.returns.views[digest(descriptor["custody"])]["original_components_file"] = None
    elif fault == "missing_bytes":
        file = descriptor["sheet_file"]; (f.store.path / "artifacts" / file["sha256"][:2] / file["sha256"]).unlink()
    elif fault == "wrong_original_mode":
        descriptor["original_mode"] = "evaluate_declared_transform_ca"; f.returns.saved[0] = deepcopy(descriptor)
    else:
        sheet = deepcopy(f.data["saved"]["native"]["sheet"]); sheet["native_baseline"] = None
        descriptor["sheet_file"] = retained(f.store, encoded(sheet), "protein_structure_comparison_sheet_v1")
        f.returns.saved[0] = deepcopy(descriptor)
        f.returns.views[digest(descriptor["custody"])]["sheet_file"] = deepcopy(descriptor["sheet_file"])
    readonly(f, monkeypatch)
    code = "saved_sheet_not_received" if fault == "absent" else "retained_artifact_missing" if fault == "missing_bytes" else "original_commission_mismatch"
    with error(code): operands.validate_saved_structure_sheet_operand(f.store, f.context, descriptor, returns=f.returns)


@pytest.mark.parametrize("kind", ["values", "artifact", "later"])
def test_exact_original_or_later_received_transform(f, monkeypatch, kind):
    transform = declared(f, later=kind == "later")
    chosen = {"values": 0, "artifact": 1, "later": 2}[kind]
    f.returns.projections = [f.data["projections"][chosen]]
    readonly(f, monkeypatch)
    result = operands.authenticate_received_structure_transform(f.store, f.context, transform, returns=f.returns)
    assert result["calculation_id"] == transform["received_from"]["calculation_id"]
    assert same(result["transform"]["rotation"]["value"], transform["rotation"])
    if kind == "later":
        assert result["evaluation"]["evaluation_rmsd"]["value"] == pytest.approx(math.sqrt(4 / 5))
        assert f.data["saved"]["native"]["sheet"]["native_baseline"]["counts"]["evaluation_used_count"]["value"] == 1


@pytest.mark.parametrize("fault", ["descriptor_only", "rotation_only", "wrong_calculation", "later_under_original", "wrong_rotation", "wrong_translation", "wrong_selection", "no_use", "table_changed"])
def test_transform_authority_and_exact_values_cannot_be_combined(f, monkeypatch, fault):
    transform = declared(f)
    if fault == "descriptor_only": f.returns.projections.clear()
    elif fault == "rotation_only":
        view = f.returns.views[digest(transform["received_from"]["calculation_custody"])]
        value = projection(f.store, view, f.data["saved"]["native"]["sheet"], f.data["saved"]["native"]["sheet"]["native_baseline"], fields=("rotation",), label="only-r")
        f.returns.projections = [value]
    elif fault == "wrong_calculation": transform["received_from"]["calculation_id"] += "different"
    elif fault == "later_under_original":
        later = declared(f, later=True)
        transform["received_from"]["components_file"] = later["received_from"]["components_file"]
        transform["received_from"]["calculation_id"] = later["received_from"]["calculation_id"]
    elif fault == "wrong_rotation": transform["rotation"][0][0] = -1.0
    elif fault == "wrong_translation": transform["translation_A"][0] += 1.0
    elif fault == "wrong_selection": transform["fixed_selection"]["zero_occupancy_policy"] = "include"
    elif fault == "no_use":
        transform["received_from"]["saved_sheet"]["allowed_uses"] = ["recalculate"]
        f.returns.saved[0] = deepcopy(transform["received_from"]["saved_sheet"])
    else:
        f.returns.projections = [f.data["projections"][1]]
        file = f.returns.projections[0]["delivery"]["table_file"]
        path = f.store.path / "artifacts" / file["sha256"][:2] / file["sha256"]
        path.write_bytes(path.read_bytes() + b"changed")
    readonly(f, monkeypatch)
    code = "saved_sheet_not_received" if fault == "no_use" else "input_digest_mismatch" if fault == "table_changed" else "invalid_transform"
    with error(code): operands.authenticate_received_structure_transform(f.store, f.context, transform, returns=f.returns)


def test_selected_saved_inputs_require_original_anchor_and_recalculate(f, monkeypatch):
    descriptor = f.data["saved"]["descriptor"]
    selected = selector(descriptor=descriptor, parameters=f.data["later_components"]["parameters"])
    readonly(f, monkeypatch)
    refs = operands.validate_protein_structure_selected_inputs(f.store, f.context, selected,
        handoff_ref=descriptor["custody"]["handoff_ref"], returns=f.returns)
    assert refs == operands._saved_refs(descriptor)
    assert ("saved", "recalculate") in f.returns.calls
    with error("original_commission_mismatch", field="request"):
        operands.validate_protein_structure_selected_inputs(f.store, f.context, selected,
            handoff_ref=desc(f)["custody"]["handoff_ref"], returns=f.returns)


def test_complete_collection_anchor_adds_no_hidden_input_grant(f, monkeypatch):
    handoff = desc(f)["custody"]["handoff_ref"]
    readonly(f, monkeypatch)
    assert operands.validate_protein_structure_selected_inputs(f.store, f.context, selector(),
        handoff_ref=handoff, returns=f.returns) == [handoff]


@pytest.mark.parametrize("which", ["reference", "source"])
def test_original_immutable_record_tampering_is_not_a_new_grant(f, monkeypatch, which):
    ref = desc(f)["reference_ref"] if which == "reference" else desc(f)["custody"]["source_ref"]
    record = f.store.get(ref)
    record["label" if which == "reference" else "accession"] = "changed_stored_payload"
    f.store.db.execute("UPDATE records SET data=? WHERE id=?", (domain_canonical(record), ref))
    readonly(f, monkeypatch)
    with error("conflicting_identity", stage="authority", field="descriptor"):
        operands.authenticate_structure_sequence_reference(f.store, f.context, desc(f)["reference_ref"], returns=f.returns)


@pytest.mark.parametrize("which", ["missing_parent", "wrong_kind", "malformed_product", "malformed_argument"])
def test_typed_ancestry_links_fail_before_any_sequence_read(f, monkeypatch, which):
    if which == "malformed_argument":
        ref = []
    else:
        # Fresh immutable records isolate link validation from identity failure.
        payload = {"parent_refs": ["reference_" + "f" * 24 if which == "missing_parent" else desc(f)["custody"]["source_ref"]],
            "molecule": "protein", "sequence_ref": desc(f)["sequence_file"]["artifact_ref"],
            "derivation": "extraction", "context_refs": [], "footprint": []}
        if which == "malformed_product": payload["parent_refs"] = None
        ref = identity("product", {"origin": "reasoning", "record": payload})
        record = dict(payload, id=ref, record_type="product", origin="reasoning")
        f.store.db.execute("INSERT INTO records VALUES(?,?,?,?)", (ref, "product", "reasoning", domain_canonical(record)))
    readonly(f, monkeypatch)
    with error("invalid_schema" if which.startswith("malformed") else "conflicting_identity", stage="authority", field="descriptor"):
        operands.is_protein_structure_sequence_operand(f.store, ref)


@pytest.mark.parametrize("kind", ["inspect", "extract_sequence"])
def test_single_structure_job_authorizes_only_original_explicit_files(f, monkeypatch, kind):
    request = deepcopy(f.data["rows"]["fixed"]["view"]["request"])
    if kind == "inspect":
        request = {"version": "protein_structure_inspect_request_v1", "operation": "inspect",
            "structure_file": request["selection"]["file_identity"],
            "inventory": {"blocks": {"kind": "all"}, "include": ["models", "chains"]}}
    files = []
    for i, (role, file) in enumerate(required_input_files(request)):
        files.append({"input_id": "input_" + str(i), "role": role, "file_identity": file,
            "path": str(f.store.path / "artifacts" / file["sha256"][:2] / file["sha256"]),
            "staged_relative_path": "inputs/input_" + str(i)})
    job = {"version": "native_protein_structure_job_v1", "program": "protein_structure_python", "request": request,
        "software": f.data["saved"]["view"]["software"], "inputs": files, "outputs": output_files(kind), "environment": {}}
    selected = requested_job_from_protein_structure(job)
    readonly(f, monkeypatch)
    assert operands.validate_protein_structure_job_inputs(f.store, f.context, {"requested_job": selected}, returns=f.returns) == [
        row["file_identity"]["artifact_ref"] for row in files]


@pytest.mark.parametrize("receipt", ["explicit", "envelope_only", "unknown"])
def test_supplied_metadata_requires_its_explicit_received_file(f, monkeypatch, receipt):
    request = deepcopy(f.data["saved"]["view"]["request"])
    file = retained(f.store, encoded({"version": "protein_structure_metadata_v1", "semantics_declarations": [],
        "metric_unit_declarations": []}), "protein_structure_metadata_v1")
    request["supplied_metadata_files"] = [file]
    if receipt != "unknown":
        EpisodeReceipts(f.store, f.context.run_id).receive(f.context.episode_id, [file["artifact_ref"]], kind="initial")
    if receipt == "envelope_only":
        # Models the protected-family public resolver denial despite an older
        # recursively expanded receipt row. The actual resolver is tested397.
        f.returns.denied_refs.add(file["artifact_ref"])
    readonly(f, monkeypatch)
    if receipt == "explicit":
        result = operands.resolve_comparison_operands(f.store, f.context, request, returns=f.returns)
        assert result["input_files"][-1]["role"] == "supplied_metadata"
        assert result["selected_references"] == [row["file_identity"]["artifact_ref"] for row in result["input_files"]]
    else:
        with error("original_commission_mismatch", field="receipt"):
            operands.resolve_comparison_operands(f.store, f.context, request, returns=f.returns)


def test_same_exact_structure_file_can_fill_two_selected_roles(f, monkeypatch):
    fixed = deepcopy(f.data["rows"]["fixed"]["native"]["sequence"])
    moving = deepcopy(fixed)
    fixed["selection"]["structure_role"], moving["selection"]["structure_role"] = "fixed", "moving"
    document, map_file, _ = A.explicit_map(fixed, moving)
    assert retained(f.store, encoded(document), map_file["format"]) == map_file
    EpisodeReceipts(f.store, f.context.run_id).receive(f.context.episode_id, [map_file["artifact_ref"]], kind="initial")
    request = {"version": "protein_structure_compare_request_v1", "operation": "compare",
        "fixed_selection": fixed["selection"], "moving_selection": moving["selection"],
        "correspondence": {"kind": "explicit_map", "map_file": map_file},
        "parameters": A.fit_parameters(), "supplied_metadata_files": []}
    readonly(f, monkeypatch)
    result = operands.resolve_comparison_operands(f.store, f.context, request, returns=f.returns)
    assert result["input_files"][0]["path"] == result["input_files"][1]["path"]
    assert result["input_files"][0]["input_id"] != result["input_files"][1]["input_id"]
    assert result["selected_references"] == [fixed["selection"]["file_identity"]["artifact_ref"], map_file["artifact_ref"]]


@pytest.mark.parametrize("role", ["scientific", "launch", "launch_local", "results"])
def test_assigned_inputs_cannot_use_later_own_receipt(f, monkeypatch, role):
    request = deepcopy(f.data["saved"]["view"]["request"])
    file = request["correspondence"]["map_file"]["artifact_ref"]
    f.store.db.execute("UPDATE runtime_record_receipts SET receipt_kind='own_action' WHERE record_ref=?", (file,))
    f.context.role = role
    readonly(f, monkeypatch)
    if role == "scientific":
        assert file in operands.resolve_comparison_operands(f.store, f.context, request, returns=f.returns)["selected_references"]
    else:
        with error("original_commission_mismatch", field="receipt"):
            operands.resolve_comparison_operands(f.store, f.context, request, returns=f.returns)


def test_transform_r_and_t_from_separate_projections_are_not_combined(f, monkeypatch):
    transform = declared(f)
    view = f.returns.views[digest(transform["received_from"]["calculation_custody"])]
    sheet = f.data["saved"]["native"]["sheet"]
    f.returns.projections = [projection(f.store, view, sheet, sheet["native_baseline"], fields=(field,), label=field)
        for field in ("rotation", "translation")]
    readonly(f, monkeypatch)
    with error("invalid_transform", field="rotation"):
        operands.authenticate_received_structure_transform(f.store, f.context, transform, returns=f.returns)


def test_results_selector_must_equal_its_original_assignment(f, monkeypatch):
    handoff = desc(f)["custody"]["handoff_ref"]
    selected = selector()
    f.context.role = "results"
    f.context.assignment = {"version": "execution_results_assignment_v1", "handoff_ref": handoff, "selector": deepcopy(selected)}
    readonly(f, monkeypatch)
    assert operands.validate_protein_structure_selected_inputs(f.store, f.context, selected, handoff_ref=handoff, returns=f.returns) == [handoff]
    selected["return_saved_sheet"] = True
    with error("original_commission_mismatch", field="request"):
        operands.validate_protein_structure_selected_inputs(f.store, f.context, selected, handoff_ref=handoff, returns=f.returns)
