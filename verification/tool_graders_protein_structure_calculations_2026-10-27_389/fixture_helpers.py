"""Synthetic coordinate cases; call scientific helpers only in bounded workers."""
from copy import deepcopy
from importlib import import_module
from gene_annotation_episode.protein_structure_sheet import build_protein_structure_sheet
from gene_annotation_episode.protein_structure_formats import parse_pdb_structure, parse_mmcif_structure
from gene_annotation_episode.protein_structure_sequences import extract_structure_sequence
from gene_annotation_episode.protein_structure_metadata import extract_native_structure_metadata

a = import_module("verification.tool_graders_protein_structure_inputs_2026-10-27_386.fixture_helpers")
TETRAHEDRON = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]


def from_pdb(data, role, *, select=None):
    parsed = parse_pdb_structure(data, file_identity=a.identity(data, "pdb_3x_text"))
    selection = a.selection(parsed, role=role)
    if select:
        selection = select(parsed, selection)
    sequence = extract_structure_sequence(parsed, selection=selection)
    metadata = extract_native_structure_metadata(parsed, selected_sequence=sequence, supplied_metadata=[])
    return data, parsed, sequence, metadata


def cif_case(coordinates, *, role="fixed", labels=None, missing=(), extra=""):
    symbols = "AGSTVDEK"[:len(coordinates)]
    labels = labels or list(range(1, len(coordinates) + 1))
    components = [a.COMPONENTS[s] for s in symbols]
    text = "data_synthetic\n_struct_asym.id X\n_struct_asym.entity_id 1\n_entity_poly.entity_id 1\n_entity_poly.type 'polypeptide(L)'\n"
    text += "loop_\n_entity_poly_seq.entity_id\n_entity_poly_seq.num\n_entity_poly_seq.mon_id\n"
    text += "".join(f"1 {label} {component}\n" for label, component in zip(labels, components))
    text += "loop_\n_pdbx_poly_seq_scheme.asym_id\n_pdbx_poly_seq_scheme.entity_id\n_pdbx_poly_seq_scheme.seq_id\n_pdbx_poly_seq_scheme.mon_id\n_pdbx_poly_seq_scheme.pdb_strand_id\n_pdbx_poly_seq_scheme.auth_seq_num\n_pdbx_poly_seq_scheme.pdb_ins_code\n"
    text += "".join(f"X 1 {label} {component} A {100 + i} .\n" for i, (label, component) in enumerate(zip(labels, components)))
    text += "loop_\n_atom_site.group_PDB\n_atom_site.id\n_atom_site.type_symbol\n_atom_site.label_atom_id\n_atom_site.label_alt_id\n_atom_site.label_comp_id\n_atom_site.label_asym_id\n_atom_site.label_entity_id\n_atom_site.label_seq_id\n_atom_site.auth_asym_id\n_atom_site.auth_seq_id\n_atom_site.auth_comp_id\n_atom_site.auth_atom_id\n_atom_site.pdbx_PDB_ins_code\n_atom_site.Cartn_x\n_atom_site.Cartn_y\n_atom_site.Cartn_z\n_atom_site.occupancy\n_atom_site.B_iso_or_equiv\n_atom_site.pdbx_PDB_model_num\n"
    for i, (label, component, xyz) in enumerate(zip(labels, components, coordinates)):
        if i not in missing:
            text += f"ATOM {i + 1} C CA . {component} X 1 {label} A {100 + i} {component} CA . {' '.join(str(x) for x in xyz)} 1 20 5\n"
    data = (text + extra).encode("utf-8")
    parsed = parse_mmcif_structure(data, file_identity=a.identity(data, "pdbx_mmcif_text"), data_block=None)
    sequence = extract_structure_sequence(parsed, selection=a.selection(parsed, role=role, sequence_basis="mmcif_declared_polymer"))
    metadata = extract_native_structure_metadata(parsed, selected_sequence=sequence, supplied_metadata=[])
    return data, parsed, sequence, metadata


def make_sheet(fixed=None, moving=None, *, parameters=None, pairs=None, retained=False, baseline=None,
               orientation="fixed_is_query", alignment_mode="global"):
    fixed = fixed or a.fixture_pdb()
    moving = moving or a.fixture_pdb(role="moving", chain="B")
    if retained:
        _, kwargs, corr = a.retained_alignment(fixed[2], moving[2], orientation=orientation, mode=alignment_mode)
        source = {"kind": "retained_alignment", "alignment": kwargs["alignment"],
            "fixed_sequence_descriptor": kwargs["fixed_descriptor"], "moving_sequence_descriptor": kwargs["moving_descriptor"],
            "orientation": kwargs["orientation"]}
    else:
        _, file, corr = a.explicit_map(fixed[2], moving[2], pairs=pairs)
        source = {"kind": "explicit_map", "map_file": file}
    return build_protein_structure_sheet(fixed=fixed[1], moving=moving[1], fixed_sequence=fixed[2], moving_sequence=moving[2],
        correspondence=corr, correspondence_input=source, fixed_metadata=fixed[3], moving_metadata=moving[3],
        native_request=parameters or a.fit_parameters(), native_baseline=baseline)


def declared_parameters(sheet, *, rotation=None, translation=None):
    parameters = a.fit_parameters()
    parameters.update(mode="evaluate_declared_transform_ca", fit_selection=None, declared_transform={
        "version": "protein_structure_transform_v1", "direction": "moving_to_fixed", "convention": "row_vector_y_R_plus_t",
        "rotation": rotation if rotation is not None else [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
        "translation_A": translation if translation is not None else [0, 0, 0],
        "fixed_selection": deepcopy(sheet["sequences"]["fixed"]["selection"]),
        "moving_selection": deepcopy(sheet["sequences"]["moving"]["selection"]), "origin": "supplied", "received_from": None})
    return parameters


def rebuild_sheet(sheet, **changes):
    arguments = {"fixed": sheet["structures"]["fixed"], "moving": sheet["structures"]["moving"],
        "fixed_sequence": sheet["sequences"]["fixed"], "moving_sequence": sheet["sequences"]["moving"],
        "correspondence": sheet["correspondence"], "correspondence_input": sheet["input_identities"]["correspondence"],
        "fixed_metadata": sheet["native_uncertainty"]["fixed"], "moving_metadata": sheet["native_uncertainty"]["moving"],
        "native_request": sheet["native_request"], "native_baseline": sheet["native_baseline"]}
    arguments.update(changes)
    return build_protein_structure_sheet(**arguments)


def synthetic_native(sheet):
    """Synthetic envelope only: these hashes assert no executed native attempt."""
    from gene_annotation_episode.native_protein_structure_contracts import DRIVER_MODULE, WORKER_MODULE
    from gene_annotation_episode.protein_structure_calculations import calculate_protein_structure_components
    result = deepcopy(sheet)
    result["native_baseline"] = calculate_protein_structure_components(result, parameters=result["native_request"])
    request = {"version": "protein_structure_compare_request_v1", "operation": "compare",
        "fixed_selection": deepcopy(result["sequences"]["fixed"]["selection"]),
        "moving_selection": deepcopy(result["sequences"]["moving"]["selection"]),
        "correspondence": deepcopy(result["input_identities"]["correspondence"]),
        "parameters": deepcopy(result["native_request"]), "supplied_metadata_files": deepcopy(result["input_identities"]["metadata_artifacts"])}
    return {"version": "protein_structure_native_v1", "request": request, "sheet": result,
        "state": result["native_baseline"]["state"], "issues": deepcopy(result["native_baseline"]["issues"]),
        "producer": {"python_executable": "/synthetic/not-executed/python", "python_sha256": "1" * 64,
            "python_version": "synthetic", "driver_module": DRIVER_MODULE, "worker_module": WORKER_MODULE,
            "implementation_files": [{"module": m, "sha256": "2" * 64} for m in (DRIVER_MODULE, WORKER_MODULE)],
            "numpy_version": "synthetic", "biopython_version": "synthetic",
            "implementation": "gene_annotation_episode_corrected_protein_structure_v1", "algorithm": "unweighted_proper_rigid_ca_svd_v1"}}


def with_semantics(fixture, semantics):
    data, parsed, sequence, _ = fixture
    selection = deepcopy(sequence["selection"])
    declaration = {"declaration_id": "synthetic_semantics", "scope": {
        "structure_file": selection["file_identity"], "data_block": selection["data_block"],
        "model_key": selection["model_key"], "chain_key": selection["chain_key"]},
        "bfactor_semantics": semantics, "producer_name": "Synthetic documented fixture", "producer_version": "1",
        "evidence_artifact_ref": parsed["file_identity"]["artifact_ref"], "evidence_span": None}
    document = {"version": "protein_structure_metadata_v1", "semantics_declarations": [declaration], "metric_unit_declarations": []}
    from gene_annotation_episode.execution_contracts import canonical
    file = a.identity(canonical(document).encode(), "protein_structure_metadata_v1")
    selection.update(bfactor_semantics=semantics, semantics_evidence={"file_identity": file, "declaration_id": "synthetic_semantics"})
    sequence = extract_structure_sequence(parsed, selection=selection)
    metadata = extract_native_structure_metadata(parsed, selected_sequence=sequence, supplied_metadata=[{"file_identity": file, "document": document}])
    return data, parsed, sequence, metadata
