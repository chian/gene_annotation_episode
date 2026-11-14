"""Populate retained protein comparison inputs, independently of calculations.

All input bytes have already been parsed and authenticated by their owners. This
module joins supplied records only. It neither runs alignment nor fits a
transform; a native baseline is validated and preserved, never replaced.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import TYPE_CHECKING

from .execution_contracts import canonical, digest
from .protein_structure_contracts import (
    ParsedStructure, StructureSequence, Correspondence, CorrespondenceInput,
    StructureMetadata, CalculationParameters, ProteinStructureComponents,
    ProteinStructureSheet, CoordinatePair, VectorCell, same,
    validate_parsed_structure, validate_structure_sequence,
    validate_correspondence, validate_correspondence_input,
    validate_structure_metadata, validate_calculation_parameters,
    validate_protein_structure_sheet, validate_protein_structure_components,
)
from .protein_structure_sequences import extract_structure_sequence, rebind_structure_sequence
from .protein_structure_metadata import extract_native_structure_metadata
from .protein_structure_correspondence import (
    validate_explicit_residue_map, correspondence_from_pairwise_sheet,
)

if TYPE_CHECKING:
    from .native_protein_structure_contracts import ComparisonNative, CompareRequest


def _unique_records(values):
    result = []
    for value in values:
        if not any(same(value, old) for old in result):
            result.append(deepcopy(value))
    return result


def _coordinate_cell(ca, atom) -> VectorCell:
    if ca["state"] == "available":
        if atom is None or any(n["state"] != "present" for n in atom["xyz_A"]):
            raise ValueError("invalid_coordinate_identity")
        return {"value": [n["value"] for n in atom["xyz_A"]], "state": "present",
                "reason": None, "unit": "angstrom", "origin": "observed"}
    return {"value": None, "state": "invalid" if ca["state"] == "invalid" else "unavailable",
            "reason": ca["primary_reason"], "unit": "angstrom", "origin": "observed"}


def _join_pairs(structures, sequences, correspondence, metadata) -> list[CoordinatePair]:
    atoms = {s: {a["identity"]["atom_row_key"]: a for a in structures[s]["atoms"]}
             for s in ("fixed", "moving")}
    uncertainty = {}
    for side in ("fixed", "moving"):
        uncertainty[side] = {}
        for row in metadata[side]["atom_uncertainty"]:
            key = row["atom_row_key"]
            if key in uncertainty[side] or key not in atoms[side]:
                raise ValueError("metadata_join_conflict")
            if not same(row["residue_identity"], atoms[side][key]["identity"]["residue"]):
                raise ValueError("metadata_join_conflict")
            uncertainty[side][key] = row["row_key"]
    result = []
    for row in correspondence["rows"]:
        if row["fixed_position_0based"] is None or row["moving_position_0based"] is None:
            continue
        pair = {"correspondence_id": row["correspondence_id"]}
        for side in ("fixed", "moving"):
            position = row[side + "_position_0based"]
            if position >= len(sequences[side]["residues"]):
                raise ValueError("map_endpoint_missing")
            residue = sequences[side]["residues"][position]
            ca = residue["ca"]
            key = ca["selected_atom_row_key"]
            atom = atoms[side].get(key)
            if key is not None and atom is None:
                raise ValueError("invalid_coordinate_identity")
            if atom is not None and not same(atom["identity"]["residue"], residue["selected_residue_identity"]):
                raise ValueError("invalid_coordinate_identity")
            pair.update({side + "_position_0based": position,
                side + "_atom_row_key": key, side + "_xyz_A": _coordinate_cell(ca, atom),
                side + "_ca_state": deepcopy(ca),
                side + "_uncertainty_row_key": uncertainty[side].get(key)})
        result.append(pair)
    return result


def _validate_input_relationships(sheet: ProteinStructureSheet) -> None:
    """Check saved selections against complete supplied native tables/maps.

    Re-extraction validates native input relationships; it does not execute an
    alignment or numerical fit, and never substitutes a rebuilt record.
    """
    sequences = sheet["sequences"]
    for side in ("fixed", "moving"):
        parsed, seq, metadata = (sheet["structures"][side], sequences[side],
                                 sheet["native_uncertainty"][side])
        if not same(extract_structure_sequence(parsed, selection=seq["selection"]), seq):
            raise ValueError("sequence_artifact_mismatch")
        rebuilt_metadata = extract_native_structure_metadata(parsed,
            selected_sequence=seq, supplied_metadata=metadata["supplied_metadata"])
        if not same(rebuilt_metadata, metadata):
            raise ValueError("metadata_join_conflict")
    source, corr = sheet["input_identities"]["correspondence"], sheet["correspondence"]
    if source["kind"] != corr["origin"]:
        raise ValueError("alignment_operand_mismatch")
    if source["kind"] == "retained_alignment":
        # Even an invalid traceback does not relax the original extraction
        # association. This checks supplied maps; Store authority stays in D.
        for side in ("fixed", "moving"):
            descriptor = source[side + "_sequence_descriptor"]
            original = rebind_structure_sequence(sequences[side],
                structure_role=descriptor["selection"]["structure_role"])
            if ("structure_correspondence" not in descriptor["allowed_uses"]
                    or not same(original["selection"], descriptor["selection"])
                    or not original["sequence_available"]
                    or original["sequence_length"] != descriptor["sequence_length"]):
                raise ValueError("sequence_artifact_mismatch")
            for data, file in ((original["alignment_sequence"].encode("ascii"), descriptor["sequence_file"]),
                               (canonical(original).encode("utf-8"), descriptor["residue_map_file"])):
                if len(data) != file["byte_length"] or hashlib.sha256(data).hexdigest() != file["sha256"]:
                    raise ValueError("sequence_artifact_mismatch")
    if source["kind"] == "explicit_map":
        if not same(source["map_file"], corr["map_file"]):
            raise ValueError("input_digest_mismatch")
        rebuilt = validate_explicit_residue_map(corr["explicit_map"], map_file=source["map_file"],
            fixed=sequences["fixed"], moving=sequences["moving"])
        if not same(rebuilt, corr):
            raise ValueError("conflicting_identity")
    elif corr["alignment_native"] is not None:
        snapshot = corr["alignment_native"]
        if not same(snapshot["descriptor"], source["alignment"]):
            raise ValueError("alignment_operand_mismatch")
        rebuilt = correspondence_from_pairwise_sheet(snapshot["pairwise_sheet"],
            native=snapshot["native_result"], alignment=source["alignment"],
            fixed=sequences["fixed"], moving=sequences["moving"],
            fixed_descriptor=source["fixed_sequence_descriptor"],
            moving_descriptor=source["moving_sequence_descriptor"], orientation=source["orientation"])
        if not same(rebuilt, corr):
            raise ValueError("conflicting_identity")
    elif corr["population_available"] or not any(i["code"] == "invalid_traceback" for i in corr["issues"]):
        raise ValueError("invalid_traceback")
    pairs = _join_pairs(sheet["structures"], sequences, corr, sheet["native_uncertainty"])
    if not same(pairs, sheet["coordinate_pairs"]):
        raise ValueError("invalid_coordinate_identity")
    expected_files = _unique_records([item["file_identity"]
        for side in ("fixed", "moving")
        for item in sheet["native_uncertainty"][side]["supplied_metadata"]])
    if not same(expected_files, sheet["input_identities"]["metadata_artifacts"]):
        raise ValueError("metadata_join_conflict")
    expected_issues = _unique_records([i for side in ("fixed", "moving")
        for i in sheet["structures"][side]["issues"] + sequences[side]["issues"]
        + sheet["native_uncertainty"][side]["issues"]])
    expected_quals = _unique_records([q for side in ("fixed", "moving")
        for q in sequences[side]["qualifications"] + sheet["native_uncertainty"][side]["qualifications"]]
        + corr["qualifications"] + ["uncertainty_not_used_as_weight", "original_coordinates_preserved"])
    if (not same(expected_issues, sheet["parse_issues"])
            or not same(corr["issues"], sheet["correspondence_issues"])
            or not same(expected_quals, sheet["source_qualifications"])):
        raise ValueError("conflicting_identity")
    declared = sheet["native_request"]["declared_transform"]
    if declared is not None:
        for side in ("fixed", "moving"):
            if not same(declared[side + "_selection"], sequences[side]["selection"]):
                raise ValueError("invalid_transform")


def build_protein_structure_sheet(*, fixed: ParsedStructure, moving: ParsedStructure,
    fixed_sequence: StructureSequence, moving_sequence: StructureSequence,
    correspondence: Correspondence, correspondence_input: CorrespondenceInput,
    fixed_metadata: StructureMetadata, moving_metadata: StructureMetadata,
    native_request: CalculationParameters,
    native_baseline: ProteinStructureComponents | None) -> ProteinStructureSheet:
    structures = {"fixed": validate_parsed_structure(fixed), "moving": validate_parsed_structure(moving)}
    sequences = {"fixed": validate_structure_sequence(fixed_sequence),
                 "moving": validate_structure_sequence(moving_sequence)}
    metadata = {"fixed": validate_structure_metadata(fixed_metadata),
                "moving": validate_structure_metadata(moving_metadata)}
    corr, source = validate_correspondence(correspondence), validate_correspondence_input(correspondence_input)
    parameters = validate_calculation_parameters(native_request)
    baseline = None if native_baseline is None else validate_protein_structure_components(native_baseline)
    sheet = {"version": "protein_structure_comparison_sheet_v1", "operation": "compare_protein_structures",
        "scientific_mode": parameters["mode"],
        "input_identities": {"fixed": deepcopy(structures["fixed"]["file_identity"]),
            "moving": deepcopy(structures["moving"]["file_identity"]), "correspondence": source,
            "metadata_artifacts": _unique_records([x["file_identity"] for s in ("fixed", "moving")
                                                    for x in metadata[s]["supplied_metadata"]])},
        "structures": structures, "sequences": sequences, "correspondence": corr,
        "coordinate_pairs": _join_pairs(structures, sequences, corr, metadata),
        "native_request": parameters, "native_baseline": baseline, "native_uncertainty": metadata,
        "parse_issues": _unique_records([i for s in ("fixed", "moving") for i in
            structures[s]["issues"] + sequences[s]["issues"] + metadata[s]["issues"]]),
        "correspondence_issues": deepcopy(corr["issues"]),
        "source_qualifications": _unique_records([q for s in ("fixed", "moving") for q in
            sequences[s]["qualifications"] + metadata[s]["qualifications"]] + corr["qualifications"]
            + ["uncertainty_not_used_as_weight", "original_coordinates_preserved"])}
    result = validate_protein_structure_sheet(sheet)
    if baseline is not None:
        from .protein_structure_calculations import _validate_recorded_components
        _validate_recorded_components(result, baseline, original=True)
    else:
        _validate_input_relationships(result)
    return result


def parse_native_protein_comparison(native: ComparisonNative, *,
                                   expected_request: CompareRequest) -> ProteinStructureSheet | None:
    # Local imports keep C's worker -> B -> C contract dependency acyclic.
    from .native_protein_structure_contracts import (
        validate_protein_structure_request, validate_native_protein_structure_result,
    )
    request = validate_protein_structure_request(expected_request)
    result = validate_native_protein_structure_result(native)
    if request["operation"] != "compare" or result["version"] != "protein_structure_native_v1":
        raise ValueError("unsupported_format")
    if not same(request, result["request"]):
        raise ValueError("original_commission_mismatch")
    if result["sheet"] is None:
        if result["state"] == "complete" or not result["issues"]:
            raise ValueError("native_result_missing")
        return None
    sheet = validate_protein_structure_sheet(result["sheet"])
    for side in ("fixed", "moving"):
        if not same(sheet["sequences"][side]["selection"], request[side + "_selection"]):
            raise ValueError("original_commission_mismatch")
    if (not same(sheet["native_request"], request["parameters"])
            or not same(sheet["input_identities"]["correspondence"], request["correspondence"])
            or not same(sheet["input_identities"]["metadata_artifacts"], request["supplied_metadata_files"])):
        raise ValueError("original_commission_mismatch")
    baseline = sheet["native_baseline"]
    if baseline is None:
        raise ValueError("native_result_missing")
    from .protein_structure_calculations import _validate_recorded_components
    _validate_recorded_components(sheet, baseline, original=True)
    if result["state"] != baseline["state"]:
        raise ValueError("conflicting_identity")
    return deepcopy(sheet)


def _numerical_digest(sheet: ProteinStructureSheet) -> str:
    """The original baseline is deliberately outside numerical input identity."""
    return digest({key: value for key, value in sheet.items() if key != "native_baseline"})


__all__ = ["build_protein_structure_sheet", "parse_native_protein_comparison"]
