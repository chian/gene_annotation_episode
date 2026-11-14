"""Synthetic byte fixtures and actual local software pins for bounded tests."""
from copy import deepcopy
import hashlib
from pathlib import Path
import platform
import sys
from importlib import import_module

import Bio
import numpy

_a = import_module("verification.tool_graders_protein_structure_inputs_2026-10-27_386.fixture_helpers")
fixture_pdb, explicit_map, fit_parameters, identity = (_a.fixture_pdb, _a.explicit_map, _a.fit_parameters, _a.identity)
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.native_protein_structure_contracts import (
    DRIVER_MODULE, WORKER_MODULE, POLICY, output_files, required_input_files,
    requested_job_from_protein_structure,
)

REPO = Path(__file__).resolve().parents[2]
MODULES = ["native_protein_structure_contracts", "native_protein_structure_local", "native_protein_structure_driver",
    "native_protein_structure_worker", "native_protein_structure_tool_info", "protein_structure_contracts",
    "protein_structure_formats", "protein_structure_sequences", "protein_structure_correspondence",
    "protein_structure_metadata", "protein_structure_sheet", "protein_structure_calculations",
    "biopython_pairwise_grader", "alignment_correspondence"]


def software():
    return {"python_executable": sys.executable, "python_sha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
        "python_version": platform.python_version(), "driver_module": DRIVER_MODULE, "worker_module": WORKER_MODULE,
        "implementation_files": [{"module": "gene_annotation_episode." + name,
            "sha256": hashlib.sha256((REPO / "gene_annotation_episode" / (name + ".py")).read_bytes()).hexdigest()} for name in MODULES],
        "numpy_version": numpy.__version__, "biopython_version": Bio.__version__,
        "implementation": "gene_annotation_episode_corrected_protein_structure_v1", "algorithm": "unweighted_proper_rigid_ca_svd_v1"}


def requests(kind="compare", *, fixed_kwargs=None, moving_kwargs=None):
    data, parsed, seq, _ = fixture_pdb(role="single" if kind != "compare" else "fixed", **(fixed_kwargs or {}))
    if kind == "inspect":
        request = {"version": "protein_structure_inspect_request_v1", "operation": "inspect", "structure_file": parsed["file_identity"],
            "inventory": {"blocks": {"kind": "all"}, "include": ["models", "chains", "sequence_bases", "residue_variants", "ca_candidates", "native_metadata"]}}
        operands = [("single_structure", data, parsed["file_identity"])]
    elif kind == "extract_sequence":
        request = {"version": "protein_structure_extract_request_v1", "operation": kind,
            "selection": seq["selection"], "supplied_metadata_files": []}
        operands = [("single_structure", data, parsed["file_identity"])]
    else:
        moving_data, moving_parsed, moving_seq, _ = fixture_pdb(role="moving", chain="B", **(moving_kwargs or {}))
        document, map_file, _ = explicit_map(seq, moving_seq)
        request = {"version": "protein_structure_compare_request_v1", "operation": "compare", "fixed_selection": seq["selection"],
            "moving_selection": moving_seq["selection"], "correspondence": {"kind": "explicit_map", "map_file": map_file},
            "parameters": fit_parameters(), "supplied_metadata_files": []}
        operands = [("fixed_structure", data, parsed["file_identity"]), ("moving_structure", moving_data, moving_parsed["file_identity"]),
            ("explicit_map", canonical(document).encode(), map_file)]
    return request, [{"input_id": "input_" + str(i), "role": role, "file_identity": deepcopy(file), "data": raw}
        for i, (role, raw, file) in enumerate(operands)]


def job(tmp_path, *, request=None, inputs=None, kind="compare", **kwargs):
    if request is None:
        request, inputs = requests(kind, **kwargs)
    source = tmp_path / "operands"
    source.mkdir(parents=True, exist_ok=True)
    rows = []
    for row in inputs:
        path = source / row["input_id"]
        path.write_bytes(row["data"])
        rows.append({k: deepcopy(row[k]) for k in ("input_id", "role", "file_identity")} |
            {"path": str(path), "staged_relative_path": "inputs/" + row["input_id"]})
    return {"version": "native_protein_structure_job_v1", "program": "protein_structure_python", "request": request,
        "software": software(), "inputs": rows, "outputs": output_files(request["operation"]), "environment": {"PYTHONPATH": str(REPO)}}


def retained_request(*, orientation="fixed_is_query", mixed_format=False):
    """Run real Biopython on synthetic extracted sequences, retain its full grade.

    Custody references below are deliberately synthetic. C verifies supplied
    byte/selection relationships; D must authenticate received parent custody.
    """
    from gene_annotation_episode.sequence_ops import align_pair
    from gene_annotation_episode.biopython_pairwise_grader import grade_biopython_pairwise
    from gene_annotation_episode.protein_structure_sequences import rebind_structure_sequence
    fixed_raw, _, fixed, _ = fixture_pdb(role="single")
    moving_raw, _, moving, _ = (_a.fixture_cif(role="single") if mixed_format else fixture_pdb(role="single", chain="B"))
    fd, md = _a.sequence_descriptor(fixed, reference_digit="a"), _a.sequence_descriptor(moving, reference_digit="b")
    query, reference = (fixed, moving) if orientation == "fixed_is_query" else (moving, fixed)
    native = align_pair(query["alignment_sequence"], reference["alignment_sequence"], molecule="protein", mode="global")
    native_bytes = canonical(native).encode()
    native_file = identity(native_bytes, "biopython_pairwise_json")
    grade = {"schema": "tool_grading_artifact_v1", "provider": "biopython.alignment",
        "native_artifact_ref": native_file["artifact_ref"], "grading": grade_biopython_pairwise(native, molecule="protein")}
    grade_bytes = canonical(grade).encode()
    alignment = {"version": "structure_alignment_descriptor_v1", "observation_ref": "observation_" + "c" * 24,
        "source_ref": "source_" + "d" * 24, "original_operation_key": "synthetic-native-alignment",
        "query_reference_ref": fd["reference_ref"] if orientation == "fixed_is_query" else md["reference_ref"],
        "reference_reference_ref": md["reference_ref"] if orientation == "fixed_is_query" else fd["reference_ref"],
        "native_file": native_file, "grading_file": identity(grade_bytes, "tool_grading_artifact_v1"),
        "molecule": "protein", "mode": "global", "traceback_selection": "explicit_retained",
        "producer_traceback_selection": "first_native_optimal_returned", "optimal_alternative_count": None}
    request = {"version": "protein_structure_compare_request_v1", "operation": "compare",
        "fixed_selection": rebind_structure_sequence(fixed, structure_role="fixed")["selection"],
        "moving_selection": rebind_structure_sequence(moving, structure_role="moving")["selection"],
        "correspondence": {"kind": "retained_alignment", "alignment": alignment,
            "fixed_sequence_descriptor": fd, "moving_sequence_descriptor": md, "orientation": orientation},
        "parameters": fit_parameters(), "supplied_metadata_files": []}
    data = {"fixed_structure": fixed_raw, "moving_structure": moving_raw, "alignment_native": native_bytes,
        "alignment_grading": grade_bytes, "fixed_sequence": fixed["alignment_sequence"].encode("ascii"),
        "fixed_residue_map": canonical(fixed).encode(), "moving_sequence": moving["alignment_sequence"].encode("ascii"),
        "moving_residue_map": canonical(moving).encode()}
    return request, [{"input_id": "input_" + str(i), "role": role, "file_identity": file, "data": data[role]}
        for i, (role, file) in enumerate(required_input_files(request))]


def plan(tmp_path, selected_job):
    from gene_annotation_episode.native_protein_structure_driver import _immutable
    root = tmp_path / ".episode-operations" / digest({"run": "synthetic-run", "episode": "synthetic-episode"}) / digest("selected-start")
    root.mkdir(parents=True)
    request = requested_job_from_protein_structure(selected_job)
    result = {"version": "native_protein_structure_run_plan_v1", "identity": {"run_id": "synthetic-run", "episode_id": "synthetic-episode",
        "resource_id": "local", "execution_id": str(root / "native.json"), "attempt_id": digest("selected-start"), "operation_key": "selected-start",
        "requested_job_sha256": digest(request)}, "requested_job": request,
        "attempt_directory": str(root / "protein-structure-attempt"), "policy": deepcopy(POLICY)}
    _immutable(root / "protein-structure-plan.json", result)
    return result
