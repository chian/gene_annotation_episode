"""Map an explicitly retained alignment or full-identity map onto protein sites.

No alignment is run here. Descriptor authentication belongs to the receiving
host; this module checks supplied identities, exact maps and native tracebacks.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
from typing import Literal

from .protein_structure_contracts import (
    BiopythonPairwiseSheetV1, BiopythonPairwiseNative, AlignmentDescriptor,
    StructureSequence, StructureSequenceDescriptor, ExplicitMapDocument, FileIdentity,
    Correspondence, canonical, issue, same, validate_structure_sequence,
    validate_structure_sequence_descriptor, validate_alignment_descriptor,
    validate_alignment_snapshot, validate_explicit_residue_map_document,
    validate_file_identity, validate_correspondence,
)
from .protein_structure_sequences import rebind_structure_sequence


def _base(fixed, moving, origin):
    if fixed["selection"]["structure_role"] != "fixed" or moving["selection"]["structure_role"] != "moving":
        raise ValueError("conflicting_identity")
    return {"version": "protein_structure_correspondence_v1", "state": "complete", "population_available": True,
        "origin": origin, "alignment_native": None, "explicit_map": None, "map_file": None,
        "fixed_sequence_selection": deepcopy(fixed["selection"]), "moving_sequence_selection": deepcopy(moving["selection"]),
        "rows": [], "unmapped_fixed": [], "unmapped_moving": [], "issues": [], "qualifications": []}


def _row(identifier, ordinal, fixed, moving, fixed_index, moving_index):
    result = {"correspondence_id": identifier, "origin_ordinal_0based": ordinal}
    for side, sequence, position in (("fixed", fixed, fixed_index), ("moving", moving, moving_index)):
        row = sequence["residues"][position] if position is not None else None
        result.update({side + "_position_0based": position,
            side + "_symbol": row["alignment_symbol"] if row else None,
            side + "_position_key": deepcopy(row["position_key"]) if row else None,
            side + "_residue": deepcopy(row["selected_residue_identity"]) if row else None,
            side + "_declared_residue": deepcopy(row["no_coordinate_identity"]) if row else None,
            side + "_ca": deepcopy(row["ca"]) if row else None})
    a, b = result["fixed_symbol"], result["moving_symbol"]
    result["relationship"] = "fixed_gap" if a is None else "moving_gap" if b is None else "identical" if a == b else "substituted"
    return result


def _unmapped(result, fixed, moving, reason):
    for side, sequence in (("fixed", fixed), ("moving", moving)):
        other = "moving" if side == "fixed" else "fixed"
        by_position = {r[side + "_position_0based"]: r for r in result["rows"] if r[side + "_position_0based"] is not None}
        for residue in sequence["residues"]:
            index = residue["sequence_position_0based"]
            row = by_position.get(index)
            if row is None or row[other + "_position_0based"] is None:
                result["unmapped_" + side].append({"sequence_position_0based": index, "position_key": deepcopy(residue["position_key"]),
                    "correspondence_id": row["correspondence_id"] if row else None,
                    "reason": "gap_in_other_sequence" if row else reason})


def _descriptor(sequence, descriptor, role):
    desc = validate_structure_sequence_descriptor(descriptor)
    if "structure_correspondence" not in desc["allowed_uses"]:
        raise ValueError("sequence_not_received")
    # The ONLY admitted role substitution is an explicit detached rebind.
    original = rebind_structure_sequence(sequence, structure_role=desc["selection"]["structure_role"])
    if not same(original["selection"], desc["selection"]) or sequence["selection"]["structure_role"] != role:
        raise ValueError("alignment_operand_mismatch")
    if not original["sequence_available"] or original["sequence_length"] != desc["sequence_length"]:
        raise ValueError("sequence_artifact_mismatch")
    raw_sequence = original["alignment_sequence"].encode("ascii")
    raw_map = canonical(original).encode("utf-8")
    for data, identity in ((raw_sequence, desc["sequence_file"]), (raw_map, desc["residue_map_file"])):
        if hashlib.sha256(data).hexdigest() != identity["sha256"] or len(data) != identity["byte_length"]:
            raise ValueError("sequence_artifact_mismatch")
    return desc


def correspondence_from_pairwise_sheet(pairwise_sheet: BiopythonPairwiseSheetV1, *,
    native: BiopythonPairwiseNative, alignment: AlignmentDescriptor,
    fixed: StructureSequence, moving: StructureSequence,
    fixed_descriptor: StructureSequenceDescriptor, moving_descriptor: StructureSequenceDescriptor,
    orientation: Literal["fixed_is_query", "fixed_is_reference"]) -> Correspondence:
    fixed, moving = validate_structure_sequence(fixed), validate_structure_sequence(moving)
    alignment = validate_alignment_descriptor(alignment)
    fd, md = _descriptor(fixed, fixed_descriptor, "fixed"), _descriptor(moving, moving_descriptor, "moving")
    if type(orientation) is not str or orientation not in ("fixed_is_query", "fixed_is_reference"):
        raise ValueError("invalid_schema")
    query, reference = (fd, md) if orientation == "fixed_is_query" else (md, fd)
    if alignment["query_reference_ref"] != query["reference_ref"] or alignment["reference_reference_ref"] != reference["reference_ref"]:
        raise ValueError("alignment_operand_mismatch")
    result = _base(fixed, moving, "retained_alignment")
    result["qualifications"].append("alternative_correspondences_not_enumerated")
    try:
        snapshot = validate_alignment_snapshot({"descriptor": alignment, "native_result": native, "pairwise_sheet": pairwise_sheet})
    except ValueError as error:
        if str(error) == "alignment_operand_mismatch":
            raise
        # Invalid native bytes/sheets remain retained inputs at the host. They
        # cannot be put into the healthy AlignmentSnapshot union as a fake zero.
        result.update(state="invalid", population_available=False,
            issues=[issue("invalid_traceback", stage="correspondence", field="traceback")])
        return validate_correspondence(result)
    if native["query_length"] != query["sequence_length"] or native["reference_length"] != reference["sequence_length"]:
        raise ValueError("alignment_operand_mismatch")
    result["alignment_native"] = snapshot
    if not native["aligned"]:
        _unmapped(result, fixed, moving, "no_alignment")
        return validate_correspondence(result)
    for column in pairwise_sheet["residue_correspondence"]:
        fi, mi = ((column["query_position"], column["reference_position"]) if orientation == "fixed_is_query" else (column["reference_position"], column["query_position"]))
        fs, ms = ((column["query_symbol"], column["reference_symbol"]) if orientation == "fixed_is_query" else (column["reference_symbol"], column["query_symbol"]))
        for sequence, position, symbol in ((fixed, fi, fs), (moving, mi, ms)):
            if position is not None and (position >= len(sequence["residues"]) or sequence["alignment_sequence"][position] != symbol):
                raise ValueError("alignment_symbol_mismatch")
        result["rows"].append(_row("column_" + str(column["column"]), column["column"], fixed, moving, fi, mi))
    _unmapped(result, fixed, moving, "outside_alignment")
    return validate_correspondence(result)


def validate_explicit_residue_map(map_value: ExplicitMapDocument, *, map_file: FileIdentity,
    fixed: StructureSequence, moving: StructureSequence) -> Correspondence:
    fixed, moving = validate_structure_sequence(fixed), validate_structure_sequence(moving)
    document, file = validate_explicit_residue_map_document(map_value), validate_file_identity(map_file)
    if file["format"] != "protein_residue_map_v1":
        raise ValueError("unsupported_format")
    for side, sequence in (("fixed", fixed), ("moving", moving)):
        if not same(document[side + "_selection"], sequence["selection"]):
            raise ValueError("alignment_operand_mismatch")
    result = _base(fixed, moving, "explicit_map")
    result.update(explicit_map=document, map_file=file)
    result["qualifications"].append("declared_correspondence_not_homology_proof")
    if not fixed["sequence_available"] or not moving["sequence_available"]:
        result.update(state="unavailable", population_available=False,
            issues=[issue("polymer_mapping_unavailable", stage="correspondence", field="residue_map")])
        return validate_correspondence(result)
    lookups = [{canonical(r["position_key"]): r["sequence_position_0based"] for r in seq["residues"]} for seq in (fixed, moving)]
    previous = (-1, -1)
    seen_fixed, seen_moving = set(), set()
    for index, row in enumerate(document["rows"]):
        fk, mk = canonical(row["fixed_position_key"]), canonical(row["moving_position_key"])
        if fk not in lookups[0] or mk not in lookups[1]:
            raise ValueError("map_endpoint_missing")
        fi, mi = lookups[0][fk], lookups[1][mk]
        if fi in seen_fixed or mi in seen_moving:
            raise ValueError("map_not_injective")
        if fi <= previous[0] or mi <= previous[1]:
            raise ValueError("map_not_collinear")
        previous = fi, mi
        seen_fixed.add(fi); seen_moving.add(mi)
        result["rows"].append(_row("map_" + str(index), index, fixed, moving, fi, mi))
    _unmapped(result, fixed, moving, "explicit_map_unmapped")
    return validate_correspondence(result)

__all__ = ["correspondence_from_pairwise_sheet", "validate_explicit_residue_map"]
