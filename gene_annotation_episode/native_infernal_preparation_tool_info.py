"""Real preparation operations, with explicit configured program/mode resources."""
from copy import deepcopy

from .infernal_preparation_schema import PROGRAM_MODES
from .native_infernal_contracts import finite_json_copy
from .native_infernal_preparation_contracts import _path, _sha, _text, operand_contract, output_contract
from .native_infernal_preparation_job_schema import preparation_requested_job_schema


_DESCRIPTIONS = {
    "cmbuild": {"build": "Build RNA covariance models from a supplied alignment.",
        "refine": "Refine a supplied RNA alignment while building covariance models."},
    "cmcalibrate": {"calibrate": "Fit native search calibration parameters for supplied covariance models.",
        "forecast": "Predict the runtime of covariance-model calibration using Infernal's native forecast.",
        "memory_estimate": "Report Infernal's native calibration-memory estimates.",
        "split_commands": "Write native commands for explicitly requested calibration partitions.",
        "partition_scores": "Generate calibration scores for one explicitly selected partition.",
        "merge_scores": "Fit calibration parameters from explicitly supplied partition-score files."},
    "cmconvert": {"ascii": "Convert supplied covariance models to current Infernal text format.",
        "binary": "Convert supplied covariance models to native binary format.",
        "legacy_ascii": "Convert supplied covariance models to legacy Infernal text format.",
        "maximum_likelihood_hmm": "Extract maximum-likelihood HMMs from supplied covariance models.",
        "filter_hmm": "Extract the filter HMMs stored in supplied covariance models."},
    "cmemit": {"sample_unaligned": "Generate unaligned sequence samples from supplied RNA models.",
        "sample_aligned": "Generate aligned sequence samples from supplied RNA models.",
        "consensus": "Generate consensus sequences from supplied RNA models."},
    "cmfetch": {"single_key": "Retrieve a covariance model matching one supplied key.",
        "key_file": "Retrieve covariance models for keys in a supplied file.",
        "index": "Create an SSI lookup index beside an owned copy of supplied covariance models."},
    "cmpress": {"press": "Create the four native database files needed by cmscan."},
    "cmstat": {"summary": "Report model sizes, training populations and native model statistics.",
        "scores_at_evalue": "Calculate native score thresholds for a selected database E-value.",
        "scores_at_pvalue": "Calculate native score thresholds for a selected tail probability.",
        "evalues_at_score": "Calculate native E-values for a supplied score threshold.",
        "evalues_at_ga": "Report native E-values at model gathering cutoffs.",
        "evalues_at_nc": "Report native E-values at model noise cutoffs.",
        "evalues_at_tc": "Report native E-values at model trusted cutoffs."},
}
_DETAILS = {
    "cmbuild": "Keep original, processed and refined alignments distinct. Retain sequence membership, "
        "columns, RF/structure annotations, effective sequence counts and refinement scores.",
    "cmcalibrate": "Calibration writes only an owned model copy. Preserve all fitted parameters, "
        "native score arrays, tail populations and units. Forecasts are predictions; memory output "
        "is a memory estimate. Split mode writes commands and does not execute them. Partition "
        "mode executes only the requested partition; merge consumes the explicitly supplied parts.",
    "cmconvert": "Preserve original and converted bytes. Binary signatures establish format only; "
        "undecoded fields remain unknown. Text/HMM conversion does not establish state-table equivalence.",
    "cmemit": "Keep generated samples distinct from biological observations. Preserve selected mode, "
        "seed, model correspondence, actual sequences/alignments, truncation and available native traces. "
        "Calculate composition and gap fractions only with their actual denominators.",
    "cmfetch": "Preserve key order, aliases and repeated requests. Check requested versus retrieved "
        "models independently of exit status: native success can still omit a missing key. "
        "An index is usable only with its exact original model bytes.",
    "cmpress": "Retain the complete i1m/i1i/i1f/i1p quartet and its original model association. "
        "Successful pressing does not establish that the models were calibrated. A later search "
        "is separate selected work.",
    "cmstat": "Retain the native row and the model header separately. Preserve native discrepancies, "
        "including cutoff output that disagrees with a stored header. Keep search-space size, "
        "calibration parameters and requested probability/score thresholds explicit.",
}


def validate_native_infernal_preparation_bindings(value):
    rows = finite_json_copy(value)
    if type(rows) is not list:
        raise ValueError("native_infernal_preparation_explicit_binding_rows_required")
    seen = set()
    for row in rows:
        if type(row) is not dict or set(row) != {"program", "mode", "software"}:
            raise ValueError("native_infernal_preparation_invalid_binding")
        program, mode = row["program"], row["mode"]
        if (type(program) is not str or program not in PROGRAM_MODES or type(mode) is not str
                or mode not in PROGRAM_MODES[program] or (program, mode) in seen):
            raise ValueError("native_infernal_preparation_invalid_or_duplicate_bound_mode")
        software = row["software"]
        if type(software) is not dict or set(software) != {"executable", "sha256", "engine_version"}:
            raise ValueError("native_infernal_preparation_invalid_bound_software")
        _path(software["executable"], absolute=True)
        _sha(software["sha256"])
        _text(software["engine_version"], "engine_version", nullable=True)
        seen.add((program, mode))
    return rows


def native_infernal_preparation_tool_contracts(bindings, *, resource_kind, resource_id):
    if resource_kind != "local":
        raise ValueError("native_infernal_preparation_resource_binding_unfinished:" + str(resource_kind))
    _text(resource_id, "resource_id")
    entries = []
    for binding in validate_native_infernal_preparation_bindings(bindings):
        program, mode = binding["program"], binding["mode"]
        inputs, optional_inputs = operand_contract(program, mode)
        outputs, optional_outputs = output_contract(program, mode)
        instructions = (_DESCRIPTIONS[program][mode] + " Supply " + ", ".join(inputs) + ". "
            + ("Optional inputs: " + ", ".join(optional_inputs) + ". " if optional_inputs else "")
            + "Retain " + ", ".join(outputs) + ". "
            + ("Optional outputs: " + ", ".join(optional_outputs) + ". " if optional_outputs else "")
            + _DETAILS[program] + " Use the exact selected files, formats, native options and "
            "explicit environment. Commission this job through launch and its configured local "
            "child; that child selects practical.job.start. The existing native lifecycle retains "
            "the original attempt and caller resource allocation. Monitoring observes this attempt's "
            "native status and requested logs; it does not select retries or new jobs. Retain full "
            "outputs for the separate deterministic parsers, numerical sheets and calculators. "
            "Request only the typed quantities or artifacts needed for the receiving assignment. "
            "Preparation measurements do not create gene-function confidence. These instructions "
            "provide no direct native execution operation to a scientific parent.")
        schema = preparation_requested_job_schema(program, mode)
        schema["properties"]["native_infernal_preparation"]["properties"]["software"] = {
            "const": deepcopy(binding["software"])}
        entries.append({"name": "native." + program + "." + mode,
            "description": _DESCRIPTIONS[program][mode], "resources": resource_kind,
            "instructions": instructions, "input_schema": schema,
            "invocation_route": {"kind": "commission", "routes": [{"entry_role": "launch",
                "resource_id": resource_id, "resource_role": "launch_local"}]}})
    return entries


def native_infernal_preparation_tool_information(bindings, *, resource_kind, resource_id):
    return [{key: entry[key] for key in ("name", "description", "resources", "instructions")}
        for entry in native_infernal_preparation_tool_contracts(bindings,
            resource_kind=resource_kind, resource_id=resource_id)]
