"""Recurring instructions for the original, single-input RNA results path.

The selected job and return form are supplied by the host. These functions do
not open artifacts, populate a scientific sheet or choose an episode action.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from .communication import plain
from .rna_structure_contracts import OPERATIONS
from .rna_structure_result_views import validate_rna_structure_result_selector
from .scientific_process_prompt import (
    _pick, _scalar, _section, _table, _values, render_episode_steering,
    text_instructions,
)


_MEANINGS = {
    "n_nt": "Number of nucleotides in the valid retained topology.",
    "pair_count": "Number of retained base pairs.",
    "paired_nt": "Number of paired nucleotide positions; two per retained pair.",
    "unpaired_nt": "Number of unpaired nucleotide positions in the retained topology.",
    "paired_fraction": "Paired nucleotide positions divided by topology length; preserve both counts.",
    "unpaired_fraction": "Unpaired nucleotide positions divided by topology length; preserve both counts.",
    "mean_pair_span_nt": "Sum of endpoint differences j-i divided by pair count; not enclosed unpaired bases.",
    "stem_count": "Number of maximal contiguous nested stems.",
    "longest_stem_pairs": "Largest retained stem pair count; the existing empty maximum convention is zero.",
    "mean_stem_pairs": "Sum of stem pair counts divided by stem count; a zero denominator is unavailable.",
    "stack_count": "Adjacent nested pair steps; a stem of L pairs contains L-1 steps.",
    "long_stem_count": "Number of stems meeting the explicitly selected minimum pair count.",
    "long_stem_fraction": "Stems meeting the selected minimum pair count divided by all stems.",
    "hairpin_count": "Number of closed hairpin regions, excluding the exterior region.",
    "bulge_count": "Number of closed bulge regions, excluding the exterior region.",
    "internal_loop_count": "Number of closed internal-loop regions, excluding the exterior region.",
    "multibranch_count": "Number of closed multibranch regions, excluding the exterior region.",
    "loop_mean_unpaired_nt": "Exposed unpaired nucleotides summed over closed regions, divided by closed-region count.",
    "loop_max_unpaired_nt": "Largest exposed unpaired count over closed regions; unavailable when no closed region exists.",
    "external_unpaired_nt": "Exposed unpaired nucleotide count in the exterior region.",
    "unambiguous_pair_count": "Pairs with two unambiguous A/C/G/U symbols.",
    "ambiguous_pair_count": "Pairs containing an ambiguous sequence symbol; excluded from the unambiguous denominator.",
    "accepted_pair_count": "Unambiguous pairs in the explicitly selected ordered-pair set.",
    "accepted_pair_fraction": "Pairs in the selected ordered-pair set divided by unambiguous pairs.",
    "mfe_kcal_mol": "Unchanged retained native minimum free energy in kcal/mol; a prediction.",
    "evaluated_energy_kcal_mol": "Unchanged retained native energy evaluation of the supplied structure, in kcal/mol.",
    "mfe_per_nt": "Retained native minimum free energy divided by valid topology length, in kcal/mol/nt.",
    "evaluated_energy_per_nt": "Retained evaluated structure energy divided by valid topology length, in kcal/mol/nt.",
    "pair_span_nt": "Endpoint difference j-i, in nucleotides; not a count of enclosed unpaired bases.",
    "stem_length_pairs": "Pair count in this maximal contiguous nested stem.",
    "loop_unpaired_nt": "Exposed unpaired nucleotide count in this selected region.",
    "branch_count": "Immediate closing-pair branches of this region; retain its selected boundaries.",
    "five_prime_unpaired_nt": "Unpaired nucleotide count on the defined five-prime side of this region.",
    "three_prime_unpaired_nt": "Unpaired nucleotide count on the defined three-prime side of this region.",
}
_MEANINGS.update({"pair_count_" + left + right:
    "Count of the ordered pair " + left + right +
    " from the lower to the higher nucleotide index; ambiguous pairs excluded."
    for left in "ACGU" for right in "ACGU"})

_OPERATIONS = (
    "Choose each next action using the actual preceding outcomes. Both available operations take an empty "
    "argument object. execution.results.status checks the assigned original attempt or received saved input. "
    "execution.results.collect retains or reads the assigned data, uses the deterministic parsers and calculators, "
    "and supplies the requested recorded fields. A status check and collection are distinct choices; there is "
    "no prescribed order. Keep the assigned input, resource, selector and parent constraints fixed."
)
_QUALIFICATIONS = (
    "Preserve exact native values, units, available numerators and denominators, and the specific state and reason "
    "for each unavailable field. Measured zero, missing input, not requested, failed, truncated and incompatible "
    "are different outcomes. Preserve useful partial topology when optional energy is unavailable. Distinguish "
    "native execution success, complete artifact capture and delivery of the requested information. An unbound "
    "structure has no established association with the annotation target; that alone does not invalidate its topology. "
    "Recorded fields are supplied automatically from actual records. Fill only any separately declared constrained "
    "interpretation fields. Return only the parent's requested fields and their required qualifications."
)
_COMPLETION = (
    "The configured yield estimator and controller govern continuation. Validated delivery of the original "
    "practical assignment sets future expected credit to exact zero immediately while preserving the final "
    "actual gain and earlier observations. A completed status action alone does not establish delivery. There "
    "is no extra zero-gain turn, model-composed completion or scientific acceptance threshold. Internal parsing, "
    "calculation and report construction do not create additional completed actions."
)


def _text(value):
    return _values(value) if isinstance(value, (Mapping, list, tuple)) else _scalar(value)


def _selected_parameters(parameters, metrics):
    """Show only supplied settings that affect the requested numerical fields."""
    selected = {}
    if set(metrics) & {"long_stem_count", "long_stem_fraction"}:
        selected["long_stem_min_pairs"] = parameters["topology"]["long_stem_min_pairs"]
    if set(metrics) & {"loop_mean_unpaired_nt", "loop_max_unpaired_nt"}:
        selected["include_exterior_in_loop_size_statistics"] = parameters["topology"][
            "include_exterior_in_loop_size_statistics"]
    if set(metrics) & {"accepted_pair_count", "accepted_pair_fraction"}:
        selected["accepted_ordered_pair_types"] = parameters["pair_composition"]["accepted_ordered_pair_types"]
        selected["pair_composition_denominator"] = parameters["pair_composition"]["denominator"]
    if set(metrics) & {"mfe_per_nt", "evaluated_energy_per_nt"}:
        selected["energy_normalization"] = parameters["energy"]["normalization"]
    return selected


def rna_structure_results_instructions(assignment: Mapping, *, job: Mapping) -> str:
    """Build the full original-results assignment from already supplied records."""
    assignment, job = plain(assignment), plain(job)
    if assignment.get("version") != "execution_results_assignment_v1":
        raise ValueError("rna_structure_results_context_required")
    mode = job.get("mode")
    if mode not in OPERATIONS or job.get("operation") != OPERATIONS[mode]:
        raise ValueError("rna_input_identity_mismatch")
    selector = validate_rna_structure_result_selector(assignment["selector"], mode=mode)
    saved = selector["acquisition"] == "retained_sheet_only"
    projection = selector["projection"]
    metrics, family = projection["metrics"], projection["family"]
    parameters = selector["parameters"] if saved else job["grading_parameters"]
    opening = ("Read the received saved RNA result for " if saved else
        "Retrieve the requested RNA prediction results for " if mode == "mfe_prediction" else
        "Retrieve the requested measurements from the supplied RNA structure for ")
    parts = [opening + _scalar(job["record_key"]) + "."]
    if saved:
        parts.append("Calculate the selected descriptive measurements under the fixed saved-result parameters. "
            "Use the exact received saved input. Original observations and capture facts remain facts about that "
            "earlier attempt. This action does not run a new prediction or energy evaluation, contact the producer, "
            "reacquire inputs or earn fresh acquisition credit. Preserve the original saved sheet and native baseline.")
    else:
        parts.append("Use the original selected execution handoff. Collection retains its sealed output bundle, "
            "parses the native record, populates the saved numerical sheet and calculates the requested descriptive "
            "components. Native scientific execution belongs to the already assigned attempt. Preserve actual "
            "partial outputs and specific acquisition, parsing or calculation failures.")
    if mode == "mfe_prediction":
        parts.append("This operation predicts a minimum-free-energy secondary structure for the supplied sequence. "
            "Its native energy is a prediction under the selected model, not an experimental stability measurement "
            "or probability of a gene function.")
    else:
        parts.append("This operation analyzes a supplied secondary structure. Preserve its supplied origin. "
            "Optional native energy evaluation scores that fixed structure; it does not search for a minimum-free-energy "
            "structure. Valid topology remains usable when optional evaluation is absent or fails.")
    _section(parts, "Selected result rows", _values({"family": family, **projection["rows"]}))
    if metrics:
        _section(parts, "Requested numerical fields", _table(("Field", "Meaning"),
            ((name, _MEANINGS[name]) for name in metrics)))
    else:
        parts.append("Return the selected recorded failure rows with their original stage, code and affected field, "
            "position or artifact role. A failure row has no numerical score.")
    if family in {"pair", "stem", "region"}:
        parts.append("Nucleotide indices are zero based; unpaired intervals are half open [start, end). "
            "Retain the selected pair endpoints, complete selected stem pair membership, or selected region's "
            "closing pair and immediate branches as applicable. The chosen rows do not imply receipt of the whole structure.")
    selected_parameters = _selected_parameters(parameters, metrics)
    if selected_parameters:
        _section(parts, "Parameters affecting the requested measurements", _values(selected_parameters))
    if any(name in {"mfe_kcal_mol", "evaluated_energy_kcal_mol", "mfe_per_nt", "evaluated_energy_per_nt"}
            for name in metrics):
        parts.append("Keep native minimum free energy and evaluated supplied-structure energy distinct. "
            "The native operation produces no ensemble uncertainty estimate. Unknown uncertainty stays unknown. "
            "Normalization changes a descriptive result; it does not change the original native energy.")
        if job.get("model") is not None:
            _section(parts, "Originally selected native model settings", _values({
                key: value for key, value in job["model"].items() if key != "schema"}))
            parts.append("These are the original requested model settings. Actual effective settings and their "
                "validation come from the retained native records; requested settings alone do not prove compatibility.")
    parts.extend(["", _OPERATIONS, "", _QUALIFICATIONS, "",
        "Use the assigned local allocation: 20 GiB RAM and 4 GiB scratch, with no wall-time budget. "
        "Keep any selected software and resource instructions in force.", "", _COMPLETION])
    return "\n\n".join(part for part in parts if part)


def render_rna_structure_results_prompt(state: Mapping, instructions: str, *, lookup_results: Sequence = ()) -> str:
    """Full recurring TASK, with concise supplied facts from shared STEERING."""
    from .rna_structure_presentation import is_rna_structure_results_context
    from .rna_structure_comparison_prompt import render_rna_comparison_requested_return
    if not is_rna_structure_results_context(state):
        raise ValueError("rna_structure_results_context_required")
    target = state["execution_target"]
    job = target["assignment"]["requested_job"]["native_rna_structure"]
    assigned = rna_structure_results_instructions(state["execution_assignment"], job=job)
    parts = ["TASK", "", text_instructions(instructions)]
    if assigned not in instructions:
        _section(parts, "Assigned RNA results", assigned)
    goal = state.get("goal")
    if goal is not None:
        if isinstance(goal, Mapping):
            _section(parts, "Parent's assigned question", _text(_pick(goal, ("objective", "task_context"))))
            contract = goal.get("result_contract")
            if contract is not None and contract != state.get("requested_form"):
                if isinstance(contract, Mapping) and "properties" in contract:
                    _section(parts, "Assigned result contract", render_rna_comparison_requested_return(
                        {"requested_form": contract, "available_report_facts": state.get("available_report_facts", {})}))
                else:
                    _section(parts, "Assigned result contract", _text(contract))
        else:
            _section(parts, "Parent's assigned question", _text(goal))
    if state.get("scope") is not None:
        _section(parts, "Fixed scope", _text(state["scope"]))
    for section in (state.get("selected_launch_instructions") or {}).get("sections", ()):
        _section(parts, "Selected software or resource instructions", section["text"])
    parts.extend(["", render_rna_comparison_requested_return(state), "",
        render_episode_steering(state, lookup_results=lookup_results)])
    return "\n".join(parts)


__all__ = ["rna_structure_results_instructions", "render_rna_structure_results_prompt"]
