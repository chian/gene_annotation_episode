"""Tiny synthetic native-format fixtures, never receipts of biological data.

Stable helper ports for owners B/C/D. All parser/scientific calls using these
helpers must run inside the caller's bounded local_jobs verification worker.
"""
from copy import deepcopy
import hashlib
from gene_annotation_episode.protein_structure_contracts import canonical

DEFAULT_XYZ = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
COMPONENTS = dict(zip("ARNDCQEGHILKMFPSTWYVBZXUOJ", "ALA ARG ASN ASP CYS GLN GLU GLY HIS ILE LEU LYS MET PHE PRO SER THR TRP TYR VAL ASX GLX UNK SEC PYL XLE".split()))

def identity(data: bytes, format: str) -> dict:
    sha = hashlib.sha256(data).hexdigest()
    return {"artifact_ref": "artifact_" + sha, "sha256": sha, "byte_length": len(data), "format": format}

def atom_line(*, serial=1, component="ALA", chain="A", number=10, insertion=" ",
              atom=" CA ", alt=" ", xyz=(0.0, 0.0, 0.0), occupancy="1.00", b="20.00",
              element="C", record="ATOM") -> str:
    return (f"{record:<6}{serial:5d} {atom:4s}{alt}{component:>3s} {chain}{number:4d}{insertion}   "
            + "".join(f"{x:8.3f}" if isinstance(x, (float, int)) else f"{x:>8s}" for x in xyz)
            + f"{occupancy:>6s}{b:>6s}          {element:>2s}  \n")

def pdb_bytes(sequence="AGST", *, coordinates=None, chain="A", numbers=None, insertions=None,
              occupancy="1.00", b="20.00") -> bytes:
    coords = DEFAULT_XYZ if coordinates is None else coordinates
    numbers = ([10, 10, 11, 15] if len(sequence) == 4 and chain == "A" else list(range(101, 101 + len(sequence)))) if numbers is None else numbers
    insertions = ([" ", "A", " ", " "] if len(sequence) == 4 and chain == "A" else [" "] * len(sequence)) if insertions is None else insertions
    if any(len(value) != len(sequence) for value in (coords, numbers, insertions)):
        raise ValueError("Synthetic fixture sequence and coordinate/number/insertion lengths must agree")
    return ("HEADER    SYNTHETIC CONTRACT FIXTURE\n" + "".join(atom_line(serial=i + 1, component=COMPONENTS[s], chain=chain, number=n, insertion=ins, xyz=xyz, occupancy=occupancy, b=b)
        for i, (s, n, ins, xyz) in enumerate(zip(sequence, numbers, insertions, coords))) + "END\n").encode("ascii")

def selection(parsed: dict, *, role="fixed", model_ordinal=0, chain_index=0,
              sequence_basis="observed_polymer", zero_occupancy_policy="exclude") -> dict:
    # Explicit fixture indices, never a production default selector.
    model = parsed["models"][model_ordinal]
    chain = parsed["chains"][chain_index]
    block = model["block_ordinal_0based"]
    return {"structure_role": role, "file_identity": deepcopy(parsed["file_identity"]),
        "data_block": None if block is None else {"ordinal_0based": block, "name": parsed["cif_blocks"][block]["name"]},
        "model_key": deepcopy(model["model_key"]), "chain_key": deepcopy(chain["chain_key"]),
        "sequence_basis": sequence_basis, "residue_variant_choices": [],
        "symbol_policy": {"unknown": "reject", "explicit_component_overrides": []},
        "ca_selection": {"policy": "unambiguous_only", "choices": []},
        "zero_occupancy_policy": zero_occupancy_policy, "bfactor_semantics": "unspecified", "semantics_evidence": None}

def fixture_pdb(sequence="AGST", *, role="fixed", **kwargs) -> tuple[bytes, dict, dict, dict]:
    from gene_annotation_episode.protein_structure_formats import parse_pdb_structure
    from gene_annotation_episode.protein_structure_sequences import extract_structure_sequence
    from gene_annotation_episode.protein_structure_metadata import extract_native_structure_metadata
    data = pdb_bytes(sequence, **kwargs)
    parsed = parse_pdb_structure(data, file_identity=identity(data, "pdb_3x_text"))
    seq = extract_structure_sequence(parsed, selection=selection(parsed, role=role))
    metadata = extract_native_structure_metadata(parsed, selected_sequence=seq, supplied_metadata=[])
    return data, parsed, seq, metadata

def explicit_map(fixed: dict, moving: dict, pairs=None) -> tuple[dict, dict, dict]:
    from gene_annotation_episode.protein_structure_correspondence import validate_explicit_residue_map
    pairs = list(zip(range(len(fixed["residues"])), range(len(moving["residues"])))) if pairs is None else pairs
    document = {"version": "protein_residue_map_v1", "declared_order": "collinear", "fixed_selection": deepcopy(fixed["selection"]),
        "moving_selection": deepcopy(moving["selection"]), "rows": [{"fixed_position_key": deepcopy(fixed["residues"][i]["position_key"]),
        "moving_position_key": deepcopy(moving["residues"][j]["position_key"])} for i, j in pairs]}
    file = identity(canonical(document).encode(), "protein_residue_map_v1")
    return document, file, validate_explicit_residue_map(document, map_file=file, fixed=fixed, moving=moving)

def numerical_parameters():
    return {"svd_relative_tolerance": 1e-12, "svd_absolute_tolerance_A2": 1e-12,
        "geometry_absolute_tolerance_A": 1e-12, "rotation_orthogonality_tolerance": 1e-10,
        "rotation_determinant_tolerance": 1e-10, "sse_roundoff_absolute_tolerance_A2": 1e-10,
        "sse_roundoff_relative_tolerance": 1e-12}

def fit_parameters():
    return {"version": "protein_structure_calculation_parameters_v1", "mode": "fit_then_evaluate_ca",
        "fit_selection": {"kind": "all_mapped_pairs"}, "evaluation_selection": {"kind": "all_mapped_pairs"},
        "missing_coordinate_policy": "require_all", "declared_transform": None, "distance_threshold_A": None,
        "numerical": numerical_parameters(), "coordinate_sets": []}

def fixture_cif(*, role="fixed", sequence_basis="mmcif_declared_polymer", extra="", data=None):
    from pathlib import Path
    from gene_annotation_episode.protein_structure_formats import parse_mmcif_structure
    from gene_annotation_episode.protein_structure_sequences import extract_structure_sequence
    from gene_annotation_episode.protein_structure_metadata import extract_native_structure_metadata
    data = (Path(__file__).parent / "fixtures/declared_gaps.cif").read_bytes() if data is None else data
    data += extra.encode("utf-8")
    parsed = parse_mmcif_structure(data, file_identity=identity(data, "pdbx_mmcif_text"), data_block=None)
    seq = extract_structure_sequence(parsed, selection=selection(parsed, role=role, sequence_basis=sequence_basis))
    return data, parsed, seq, extract_native_structure_metadata(parsed, selected_sequence=seq, supplied_metadata=[])

def synthetic_custody():
    value = {"run_id": "synthetic-run", "result_episode_id": "synthetic-episode", "result_operation_key": "synthetic-action",
        "result_receipt_key": "", "handoff_ref": "source_" + "1" * 24, "source_ref": "source_" + "2" * 24,
        "bundle_artifact_ref": "artifact_" + "3" * 64, "original_request_sha256": "4" * 64}
    payload = {"run_id": value["run_id"], "episode_id": value["result_episode_id"], "operation_key": value["result_operation_key"]}
    value["result_receipt_key"] = "protein_structure_result_receipt:" + hashlib.sha256(canonical(payload).encode()).hexdigest()
    return value

def sequence_descriptor(seq, *, reference_digit="a"):
    return {"version": "structure_sequence_descriptor_v1", "custody": synthetic_custody(), "reference_ref": "reference_" + reference_digit * 24,
        "sequence_file": identity(seq["alignment_sequence"].encode("ascii"), "ascii_protein_sequence_v1"),
        "residue_map_file": identity(canonical(seq).encode(), "protein_structure_sequence_v1"), "structure_file": deepcopy(seq["selection"]["file_identity"]),
        "selection": deepcopy(seq["selection"]), "sequence_length": seq["sequence_length"], "allowed_uses": ["sequence_align", "structure_correspondence"]}

def retained_alignment(fixed, moving, *, orientation="fixed_is_query", mode="global"):
    from gene_annotation_episode.sequence_ops import align_pair
    from gene_annotation_episode.biopython_pairwise_grader import build_biopython_pairwise_sheet
    from gene_annotation_episode.protein_structure_correspondence import correspondence_from_pairwise_sheet
    fd, md = sequence_descriptor(fixed, reference_digit="a"), sequence_descriptor(moving, reference_digit="b")
    query, reference = (fixed, moving) if orientation == "fixed_is_query" else (moving, fixed)
    native = align_pair(query["alignment_sequence"], reference["alignment_sequence"], molecule="protein", mode=mode)
    sheet = build_biopython_pairwise_sheet(native, molecule="protein")
    descriptor = {"version": "structure_alignment_descriptor_v1", "observation_ref": "observation_" + "c" * 24,
        "source_ref": "source_" + "d" * 24, "original_operation_key": "synthetic-alignment",
        "query_reference_ref": fd["reference_ref"] if orientation == "fixed_is_query" else md["reference_ref"],
        "reference_reference_ref": md["reference_ref"] if orientation == "fixed_is_query" else fd["reference_ref"],
        "native_file": identity(canonical(native).encode(), "biopython_pairwise_json"),
        "grading_file": identity(canonical(sheet).encode(), "tool_grading_artifact_v1"),
        "molecule": "protein", "mode": mode, "traceback_selection": "explicit_retained",
        "producer_traceback_selection": "first_native_optimal_returned", "optimal_alternative_count": None}
    kwargs = {"native": native, "alignment": descriptor, "fixed": fixed, "moving": moving,
        "fixed_descriptor": fd, "moving_descriptor": md, "orientation": orientation}
    return sheet, kwargs, correspondence_from_pairwise_sheet(sheet, **kwargs)
