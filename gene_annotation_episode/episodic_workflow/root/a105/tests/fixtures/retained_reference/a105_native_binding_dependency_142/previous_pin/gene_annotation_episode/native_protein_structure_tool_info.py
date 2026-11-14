"""Actual four-field information, separate from exact commission schemas."""
from .native_protein_structure_contracts import (
    NativeProteinBinding, ProteinResourceToolContract, ProteinToolInformation,
    protein_structure_execution_schema, validate_protein_structure_bindings,
)

_NAMES = {"inspect": "inspect_protein_structure", "extract_sequence": "extract_protein_structure_sequence",
          "compare": "compare_protein_structures"}
_DESCRIPTIONS = {
    "inspect": "Inspect explicit PDB 3.x or PDBx/mmCIF bytes for requested model, chain, residue, CA-candidate and native metadata inventories.",
    "extract_sequence": "Extract a selected structure's protein sequence and exact sequence-to-residue map, retaining missing coordinates and native uncertainty.",
    "compare": "Compare explicitly corresponding protein CA coordinates using a proper unweighted rigid fit or a supplied moving-to-fixed transform, with separately selected evaluation sites.",
}
_INSTRUCTIONS = {
    "inspect": ("Supply operation=inspect, structure_file and inventory: select all or explicitly named mmCIF blocks and the requested models, chains, sequence_bases, residue_variants, ca_candidates or native_metadata categories. "
        "The operation preserves complete parsed native tables and returns the requested inventory. It does not choose a model, chain or conformer for a later operation. "
        "The native result format is protein_structure_inventory_native_v1. Inspection is a supporting transformation without annotation-confidence scoring. "),
    "extract_sequence": ("Supply operation=extract_sequence, selection with structure_role=single, exact file/block/model/chain, observed_polymer or mmcif_declared_polymer basis, symbol overrides, CA choices, zero-occupancy policy and B-column semantics. "
        "Supply every explicitly selected metadata declaration file. No first model, highest-occupancy conformer or integer-residue-number match is inferred. "
        "Output protein_structure_sequence_native_v1 retains original raw records, sequence map and native metadata. Available sequences additionally produce uppercase ASCII sequence.txt without header or trailing newline; residue-map.json retains the complete protein_structure_sequence_v1 map. "
        "Missing CA does not erase a sequence position; unresolved symbols prevent publishing an alignment operand. Sequence extraction is a supporting transformation without function-confidence scoring. "),
    "compare": ("Supply operation=compare with fixed_selection and moving_selection, one model and chain on each side, explicit correspondence, calculation parameters and selected metadata files. "
        "Correspondence is an injective collinear explicit residue map or an explicitly selected retained Biopython protein local/global alignment with full native traceback, original grading artifact and both authenticated extraction sequence/map descriptors. "
        "The existing scientific-child sequence.align uses BLOSUM62, gap open -10 and gap extension -0.5; obtain that result separately when needed. This comparison performs no alignment, chain search, outlier removal or conformer search. "
        "In fit_then_evaluate_ca, declare fit_selection separately from evaluation_selection; only selected fit CA pairs determine the unweighted proper rigid transform. In evaluate_declared_transform_ca, provide the exact proper rotation and translation and no fit selection. "
        "The convention is row-vector y@R+t, moving to fixed, in angstroms. Native protein_structure_native_v1 retains the complete numerical sheet and baseline: original coordinates, exact correspondence, CA availability, denominators, fit diagnostics, transform and requested site measurements. "
        "Declare require_all or use_available for missing coordinates, numerical tolerances, optional descriptive distance threshold and explicit coordinate-output sets. Degenerate fits retain a computable minimum but do not invent a unique transform. "
        "B factors, native pLDDT, PAE and reported uncertainties retain their actual semantics and units; they are not fit weights or annotation probabilities. Saved-sheet recalculation uses a separate deterministic calculator with explicit new parameters and preserves the original baseline. "),
}
_COMMON = ("Declare the selected Software interpreter, version, dependency versions and implementation hashes, exact input artifacts, SHA-256/byte lengths and absolute authorized staging paths. "
    "The closed requested_job contains the compiled worker argv, explicit environment and native_protein_structure job. Output paths are fixed: result.json, stdout.log, stderr.log, with the extraction outputs described above. "
    "Commission launch and its configured launch_local child with 20 GiB RAM, 4 GiB scratch, zero swap and no wall-time budget. Preparation only reserves the attempt; the owning child selects practical.job.start. "
    "Status reads the original durable identity and available logs; a retry requires a separately selected failed-attempt retry. The sealed bundle retains the original plan, worker input, complete declared files and structured failures. "
    "Native execution success, complete capture and delivery of the parent's requested typed results remain separate. Resource choice and further investigation belong to the episode. This entry provides no API or HPC deployment and grants no direct execution operation to the root.")


def protein_structure_tool_contracts(bindings: list[NativeProteinBinding], *, resource_kind: str,
                                      resource_id: str) -> list[ProteinResourceToolContract]:
    if resource_kind != "local" or type(resource_id) is not str or not resource_id or "\0" in resource_id:
        raise ValueError("original_commission_mismatch")
    bindings = validate_protein_structure_bindings(bindings)
    result = []
    for operation in _NAMES:
        selected = [row for row in bindings if row["operation"] == operation]
        if not selected:
            continue
        result.append({"name": _NAMES[operation], "description": _DESCRIPTIONS[operation], "resources": "local",
            "instructions": _INSTRUCTIONS[operation] + _COMMON,
            "input_schema": protein_structure_execution_schema("RequestedProteinJob", bindings=selected),
            "invocation_route": {"kind": "commission", "routes": [{"entry_role": "launch", "resource_id": resource_id, "resource_role": "launch_local"}]}})
    return result


def protein_structure_tool_information(bindings: list[NativeProteinBinding], *, resource_kind: str,
                                        resource_id: str) -> list[ProteinToolInformation]:
    return [{key: row[key] for key in ("name", "description", "resources", "instructions")}
            for row in protein_structure_tool_contracts(bindings, resource_kind=resource_kind, resource_id=resource_id)]
