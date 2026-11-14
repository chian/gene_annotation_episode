"""Four-field RNA tool information and separate child commissioning contracts."""
from copy import deepcopy

from .native_rna_structure_contracts import (NATIVE_RNA_STRUCTURE_REQUESTED_JOB_SCHEMA,
    validate_rna_structure_bindings)

_DESCRIPTIONS = {
    "mfe_prediction": "Predict one RNA minimum-free-energy secondary structure using explicitly selected ViennaRNA settings.",
    "supplied_features": "Retain exact supplied RNA secondary-structure topology and optionally evaluate that structure with ViennaRNA.",
}
_INSTRUCTIONS = {
    "mfe_prediction": (
        "Predict the secondary structure of the exact supplied RNA sequence. Supply one UTF-8 RNA prediction input JSON "
        "with its original record key, optional readable sequence label, sequence, explicit exact or uppercase_ascii "
        "normalization, and optional physical subject binding. Prediction requires nonempty ACGU after the selected case "
        "operation. Do not trim, replace T by U, guess bases, resolve a public name, or resize the sequence. Supply the "
        "selected ViennaRNA model and parameter-set operand when applicable. The selected primitive is "
        "RNA.fold_compound(sequence, md).mfe(); retain its exact returned structure and MFE in kcal/mol. "
        "An MFE structure is a prediction, and its energy is not an experimental measurement or annotation probability. "),
    "supplied_features": (
        "Analyze the exact supplied dot-bracket structure. Supply one UTF-8 RNA feature input JSON with the original "
        "record key, optional labels/sequence, exact or uppercase_ascii normalization, structure, supplied origin and "
        "provenance, optional physical subject binding, and energy_mode. Nested .()[]{} is supported; crossing pairs "
        "are explicitly unsupported. No repair or partial pairing subset is inferred for invalid topology. Pair "
        "endpoints are zero-based nucleotide indices; unpaired intervals are half open. Retain every position, "
        "immediate nesting relationship, maximal stem and exposed hairpin, bulge, internal, multibranch and exterior "
        "region. Optional sequence permits RNA IUPAC; ambiguous pairs remain distinct and excluded from an explicitly "
        "unambiguous-pair denominator. An absent sequence is different from empty or length-mismatched sequence. "
        "energy_mode=none needs no ViennaRNA import and no model. energy_mode=viennarna_evaluate requires unambiguous "
        "ACGU, an explicit model and RNA.fold_compound(sequence, md).eval_structure(structure). This evaluates the "
        "supplied structure and does not search for or report an MFE. Nested alternative bracket tokens are converted "
        "only for energy evaluation with every pair/index retained. Preserve valid supplied topology when energy fails. "
        "Do not use the former pair-weight energy heuristic or assign a biological zipper label. "),
}
_COMMON = (
    "Bind the selected Python executable and worker bytes plus known ViennaRNA distribution/module/extension "
    "identities; null identity fields mean unknown deployment. Select temperature, dangles, noLP, noGU, noGUclosure, "
    "special_hp, logML, min_loop_size, max_bp_span and Turner2004 or an exact supplied parameter file explicitly. "
    "This single-sequence model excludes circular folding, G-quadruplexes, cofolding and hard/soft constraints. "
    "Neither selected algorithm produces ensemble probabilities or uncertainty. Unknown uncertainty remains absent. "
    "Supply explicit descriptive calculation parameters separately from the native model. Native model or input "
    "changes require new selected execution; changing saved descriptive calculations does not. "
    "Declare exact input digests/sizes, native-result, complete stdout/stderr, and for energy modes model and "
    "effective-parameter outputs. Use the original compiled argv as an argument list, never shell text. Commission "
    "through launch and its configured local-compute child with 20 GiB RAM, 4 GiB scratch and no wall-time cap. "
    "Preparation reserves the original job; the child selects practical.job.start to execute it once. Resource "
    "changes, retries and subsequent investigation remain episode choices. Monitoring reads the original attempt; "
    "results acquisition captures its sealed bundle and uses separate deterministic native-output parsers and calculators. "
    "Request the numerical components and exact associations needed by the receiving episode. Native success, "
    "complete artifact capture and delivery of qualified requested values are distinct facts. This information "
    "grants no direct scientific execution operation to the root or receiving scientific episode."
)


def rna_structure_tool_contracts(bindings: list[dict], *, resource_kind: str, resource_id: str) -> list[dict]:
    if resource_kind != "local":
        raise ValueError("rna_native_result_incompatible")
    if type(resource_id) is not str or not resource_id or "\0" in resource_id:
        raise ValueError("rna_original_attempt_mismatch")
    rows = []
    for binding in validate_rna_structure_bindings(bindings):
        schema = deepcopy(NATIVE_RNA_STRUCTURE_REQUESTED_JOB_SCHEMA)
        native = schema["properties"]["native_rna_structure"]["properties"]
        for name in ("operation", "mode", "software"):
            native[name] = {"const": deepcopy(binding[name])}
        rows.append({"name": binding["operation"], "description": _DESCRIPTIONS[binding["mode"]],
            "resources": "local", "instructions": _INSTRUCTIONS[binding["mode"]] + _COMMON,
            "input_schema": schema, "invocation_route": {"kind": "commission", "routes": [
                {"entry_role": "launch", "resource_id": resource_id, "resource_role": "launch_local"}]}})
    return rows


def rna_structure_tool_information(bindings: list[dict], *, resource_kind: str, resource_id: str) -> list[dict]:
    return [{key: row[key] for key in ("name", "description", "resources", "instructions")}
        for row in rna_structure_tool_contracts(bindings, resource_kind=resource_kind, resource_id=resource_id)]
