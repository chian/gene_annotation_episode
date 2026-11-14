"""Text for the fixed retained-RNA comparison and its parent-requested return.

This is presentation of supplied assignment/state only. Authority, numerical
calculation, delivery, credit and continuation retain their existing owners.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy

from .communication import plain
from .rna_structure_comparison_contracts import validate_rna_comparison_selector
from .rna_structure_comparison_presentation import is_rna_comparison_results_context
from .rna_structure_comparison_views import PROJECTION_SOURCE
from .scientific_process_prompt import (
    _pick, _scalar, _schema, _section, _table, _values,
    render_episode_steering, text_instructions,
)


_FIXED_WORK = (
    "Use only the independently selected retained RNA inputs named in this assignment. "
    "Keep the parent's baseline, membership, correspondence, site selections, model comparison "
    "and requested outputs fixed. The routing handoff does not choose the scientific baseline. "
    "This calculation uses retained data; it acquires no new native observation and generates no variants."
)
_OPERATIONS = (
    "Choose the next available operation using the recorded outcomes. execution.results.status "
    "checks the selected retained inputs and existing comparison records. execution.results.collect "
    "calculates the fixed comparison and prepares exactly the requested return. Both operations "
    "take an empty argument object. The calculation uses the bound local limits of 20 GiB memory "
    "and 4 GiB scratch, with no wall-time budget. Choose between the available operations as the "
    "evidence warrants; no operation order is prescribed."
)
_LIMITS = (
    "Preserve native measurements, model assumptions, units, coordinates, valid partial results "
    "and specific failure qualifications. Measured zero, unavailable, not tested, failed and "
    "incompatible are distinct. The scientific parent interprets the returned comparison; model "
    "energy or pairing change alone does not establish experimental stability, biological importance or function."
)
_COMPLETION = (
    "A completed status action does not complete the requested comparison delivery. The configured "
    "controller owns continuation. Validated completion of the original requested delivery sets "
    "future expected credit to exact zero through the existing practical endpoint, preserving the "
    "final actual gain and prior observations. Select the next action and constrained interpretations "
    "through the supplied typed response contract; recorded facts are populated automatically."
)
_NAMES = {
    "native_mfe": "native minimum-free-energy prediction",
    "native_evaluation": "native evaluated structure energy",
    "original_sequence": "original sequence (complete, preserving original case)",
    "analysis_sequence": "analysis sequence (complete, preserving the selected normalization)",
    "dot_bracket": "dot-bracket structure (complete original string)",
    "pairs": "base-pair endpoint list",
    "baseline_rank_start": "baseline rank start (first occupied exact rank)",
    "baseline_rank_end": "baseline rank end (last occupied exact rank)",
    "baseline_tie_count": "baseline tie count (including the baseline)",
    "lowest_energy_tie_count": "lowest-energy tie count",
    "baseline_energy_above_minimum": "baseline selected energy above the population minimum",
    "energy_delta": "signed energy difference (variant minus baseline)",
    "energy_absolute_delta": "absolute energy difference",
    "baseline_tolerance": "parent-selected absolute tolerance",
    "rank_start": "first occupied exact member rank",
    "rank_end": "last occupied exact member rank",
    "delta": "signed energy difference from the baseline",
}


def _name(value):
    return _NAMES.get(value, str(value).replace("_", " "))


def _names(values):
    return "; ".join(_name(value) for value in values) or "none selected"


def _labels(values):
    return "; ".join(values) or "none selected"


def _energy(request):
    if request is None:
        return "No energy comparison requested."
    normalization = ("no per-nucleotide normalization; kcal/mol" if request["normalization"] == "none"
        else "per-nucleotide normalization using each input's own sequence length; kcal/mol/nt")
    tolerance = request["baseline_absolute_tolerance"]
    return (_name(request["quantity"]) + "; " + normalization +
        "; ViennaRNA 2.7 retained linear model compatibility profile; " +
        ("no absolute tolerance classification requested" if tolerance is None else
            "absolute baseline tolerance " + str(tolerance) + " in the selected energy unit") + ".")


def _correspondence(request):
    if request is None:
        return "None supplied; equal integer indices do not establish correspondence."
    kind = request["kind"]
    if kind == "identical_sequence":
        return "Explicit identical-sequence correspondence, validated against both retained sequences."
    if kind == "substitution_only":
        substitutions = request["substitutions"]
        detail = (f"index {substitutions[0]['index']}: {substitutions[0]['baseline_symbol']} to "
            f"{substitutions[0]['variant_symbol']}" if len(substitutions) == 1 else
            str(len(substitutions)) + " declared substitutions")
        return ("Complete supplied substitution manifest (" + detail +
            "); unchanged positions correspond in place only after validation of that manifest.")
    if kind == "supplied_complete_alignment":
        return (str(len(request["columns"])) + " supplied complete alignment columns; each side's "
            "sequence indices and alignment columns are separate coordinates; null on a side denotes its supplied gap.")
    return (str(len(request["matches"])) + " supplied partial one-to-one matches; unlisted positions "
        "remain unknown and do not assert gaps or unpaired bases.")


def _site(selection):
    positions, intervals, regions = (selection[name] for name in
        ("positions", "intervals", "unpaired_region_keys"))
    if len(positions) == 1 and not intervals and not regions:
        chosen = "one explicit position, index " + str(positions[0])
    elif len(intervals) == 1 and not positions and not regions:
        chosen = f"one half-open interval [{intervals[0][0]}, {intervals[0][1]})"
    else:
        chosen = (f"{len(positions)} explicit position selectors; {len(intervals)} half-open interval selectors; "
            f"{len(regions)} unpaired-region selectors")
    return (selection["coordinate_member_id"], chosen,
        "set union; overlaps count once; region selectors include their unpaired indices")


def _projection(selection):
    family = selection["family"]
    if family == "energy_comparison":
        outputs = list(selection["metrics"])
        if selection["include_order"]:
            outputs.append("exact_energy_ordering")
        if selection["include_tolerance_band"]:
            outputs.append("baseline_tolerance_classification")
        scope = "comparisons " + _labels(selection["comparison_ids"])
    elif family == "structures":
        scope, outputs = "members " + _labels(selection["member_ids"]), selection["fields"]
    elif family == "position_changes":
        scope = "comparison " + selection["comparison_id"] + "; selection " + selection["selection_id"]
        return (scope, "Position/base symbols, indices, both partners' states and indices, transition and change "
            "indicator for selected transitions: " + _names(selection["transitions"]))
    elif family == "pair_changes":
        return ("comparisons " + _labels(selection["comparison_ids"]),
            "Original pair endpoints and separate alignment-column endpoints for relations: " + _names(selection["relations"]))
    elif family == "comparison_counts":
        scope = "comparisons " + _labels(selection["comparison_ids"]) + "; site selections " + _labels(selection["selection_ids"])
        outputs = [*selection["metrics"], *(["pairing_change_state"] if selection["include_pairing_change_state"] else [])]
    elif family == "scan_energy":
        scope = "scan " + selection["scan_id"]
        outputs = [*selection["metrics"], *(["baseline_rank_class"] if selection["include_rank_class"] else [])]
    elif family == "scan_sites":
        scope = "scan " + selection["scan_id"] + "; site selections " + _labels(selection["selection_ids"])
        outputs = selection["metrics"]
    else:
        members = selection["members"]
        chosen = ("explicit members " + _labels(members["member_ids"]) if members["kind"] == "explicit"
            else "members matching any selected predicate: " + _names(members["predicates"]))
        scope = "scan " + selection["scan_id"] + "; " + chosen
        limit = "all matching selected members" if selection["limit"] is None else "at most " + str(selection["limit"]) + " matching selected members"
        return (scope, _names(selection["fields"]) + "; declared order; " + limit +
            "; matched, returned and omitted counts describe the selected window, not native truncation")
    return scope, _names(outputs)


def rna_comparison_results_instructions(assignment: Mapping) -> str:
    """Full recurring instructions selected from the fixed assignment, no reads."""
    if (not is_rna_comparison_results_context({"execution_assignment": assignment})
            or set(assignment) != {"version", "handoff_ref", "selector"}
            or not isinstance(assignment["handoff_ref"], str) or not assignment["handoff_ref"]):
        raise ValueError("rna_comparison_results_assignment_required")
    selector = validate_rna_comparison_selector(plain(assignment["selector"]))
    question = selector["question"]
    baseline, scan = question["baseline_member_id"], question["scan"]
    scope = ("finite scan " + scan["scan_id"] if scan is not None else "pairwise comparison with " +
        question["comparisons"][0]["variant_member_id"])
    parts = [f"Compare the retained RNA inputs against the explicit baseline {baseline} for the parent's {scope}. "
        "Calculate and return only the selected comparison outputs below.", "", _FIXED_WORK]
    members = question["membership"]
    if scan is not None:
        # Counts describe the supplied fixed assignment, not measured success.
        _section(parts, "Declared scan population (input states, not calculation outcomes)", _table(
            ("Declared input category", "Entries"), [
                ("All declared entries, including baseline and aliases", len(members)),
                ("Retained saved inputs", sum(m["kind"] == "saved_sheet" for m in members)),
                ("Received failures", sum(m["kind"] == "received_failure" for m in members)),
                ("Not supplied", sum(m.get("state") == "not_supplied" for m in members)),
                ("Not tested", sum(m.get("state") == "not_tested" for m in members)),
                ("Aliases, with no additional rank weight", sum(m["kind"] == "alias" for m in members)),
            ]))
        baseline_member = next(m for m in members if m["member_id"] == baseline)
        _section(parts, "Explicit baseline input", baseline + ": " +
            _name(baseline_member.get("state", baseline_member["kind"])) + ".")
        _section(parts, "Fixed scan comparisons", str(len(question["comparisons"])) +
            " baseline-to-canonical-variant comparisons; declared order. Count each canonical sequence "
            "variant once. Retain failures and absent entries in population qualifications. "
            "Aliases retain their declared relationships without additional population weight.")
        _section(parts, "Selected scan energy", _energy(scan["energy"]))
        if scan["energy"] is not None:
            parts.extend(["", "Rank the explicit baseline with comparable canonical variants under the selected model. "
                "Preserve exact ranks, ties and the selected population's exclusions. Rank and energy gap apply only "
                "to that declared comparable population; they do not establish a global optimum."])
        if scan["topology_selection_ids"]:
            _section(parts, "Selected scan sites", _labels(scan["topology_selection_ids"]) +
                "; identical baseline-coordinate selectors across the declared comparisons. Each site's "
                "decidable variant population is separate; missing correspondence or topology is not unchanged pairing.")
            selections = {s["selection_id"]: s for s in question["comparisons"][0]["site_selections"]}
            _section(parts, "Declared baseline site selectors", _table(
                ("Selection", "Coordinate member", "Declared selectors", "Combination meaning"),
                ((key, *_site(selections[key])) for key in scan["topology_selection_ids"])))
        correspondence_counts = {}
        for comparison in question["comparisons"]:
            kind = (comparison["correspondence"] or {}).get("kind", "not_supplied")
            correspondence_counts[kind] = correspondence_counts.get(kind, 0) + 1
        _section(parts, "Declared correspondence coverage", _table(("Supplied correspondence kind", "Comparisons"),
            ((_name(kind), count) for kind, count in correspondence_counts.items())))
    else:
        _section(parts, "Selected input members", _table(("Member", "Assigned input"),
            ((m["member_id"], "alias of " + m["canonical_member_id"] if m["kind"] == "alias" else
                _name(m.get("state", m["kind"]))) for m in members)))
        for comparison in question["comparisons"]:
            _section(parts, "Comparison " + comparison["comparison_id"],
                "Baseline " + baseline + "; variant " + comparison["variant_member_id"] + ".\n\n" +
                _correspondence(comparison["correspondence"]) + "\n\n" + _energy(comparison["energy"]) +
                "\n\nPair-change calculation: " + ("requested." if comparison["calculate_pair_changes"] else "not requested."))
            if comparison["site_selections"]:
                _section(parts, "Declared site selections", _table(
                    ("Selection", "Coordinate member", "Declared selectors", "Combination meaning"),
                    ((s["selection_id"], *_site(s)) for s in comparison["site_selections"])))

    projections = selector["projections"]
    _section(parts, "Exact requested comparison outputs", _table(("Parent selection", "Output family", "Selection scope", "Requested values"),
        ((s["projection_id"], _name(s["family"]), *_projection(s)) for s in projections)))
    families = {s["family"] for s in projections}
    if "structures" in families:
        parts.extend(["", "Return every explicitly selected structure field completely, preserving original case, "
            "structure origin and validity. Invalid original text stays invalid; it does not establish validated pairing."])
    if families & {"position_changes", "pair_changes", "comparison_counts", "scan_sites"}:
        parts.extend(["", "Sequence indices are zero based; intervals are half open. Alignment columns are a separate "
            "coordinate system. Use only the supplied validated correspondence. Unpaired, supplied gap, unmapped "
            "and unavailable topology remain distinct. Selected-site fractions use decidable selected shared sites; "
            "scan-site fractions use decidable variants at each selected baseline site. Pair relations use mapped "
            "alignment-column endpoints. Preserve requested coverage and unresolved endpoints; zero known changes "
            "over incomplete correspondence does not establish that every requested site or pair is unchanged."])
    if any(c["energy"] is not None for c in question["comparisons"]) or scan is not None and scan["energy"] is not None:
        parts.extend(["", "Use the selected retained native energy kind and its saved model-compatibility qualification. "
            "Native minimum-free-energy prediction and native evaluated structure energy have distinct meanings; "
            "neither substitutes for the other. Preserve ordering of stored values, not rounded display values. "
            "Exact ties remain separate from any explicitly selected tolerance band. The tolerance is not an "
            "uncertainty interval; unavailable comparison uncertainty remains unavailable."])
    if families & {"scan_energy", "scan_members"} and scan["energy"] is not None:
        parts.extend(["", "Keep the mandatory scan population qualifications: declared variants, aliases excluded, "
            "native energy available, comparable variants, received failures, not supplied, not tested, requested "
            "energy unavailable, incompatible model, unknown model and rank population. These states describe "
            "different populations; a failure does not prove energy evaluation."])
    parts.extend(["", "Return the selected fields with their required availability, coverage and model qualifications. "
        "Do not add unselected structures, positions, energies or member rows.", "", _OPERATIONS, "", _LIMITS, "", _COMPLETION])
    return "\n".join(parts)


def _text(value):
    return _values(value) if isinstance(value, (Mapping, list, tuple)) else _scalar(value)


def render_rna_comparison_requested_return(state: Mapping) -> str:
    """Explain the actual parent's form; recorded RNA rows need no model entry.

Only the top-level, exact comparison fact source receives compact treatment.
The authoritative schema and every interpretation constraint remain untouched.
Other fact sources retain their declared field/schema and source meanings.
"""
    parts = []
    purpose = state.get("requested_report_purpose")
    if purpose is not None:
        _section(parts, "Information requested by the parent", _text(purpose))
    form = state.get("requested_form")
    if form is None:
        _section(parts, "Parent return form", "Absent: no parent return form was supplied.")
    else:
        shown = deepcopy(plain(form))
        for name, node in shown.get("properties", {}).items():
            if node.get("x-source") == PROJECTION_SOURCE:
                # The complete eight-family source contract is host-validated.
                # It is not an interpretation form for the model to populate.
                shallow = _pick(node, ("type", "description", "x-source",
                    "minItems", "maxItems", "uniqueItems"))
                shallow["description"] = (node.get("description", "") +
                    ("; " if node.get("description") else "") +
                    "Automatically supplied requested RNA comparison facts and their required qualifications.")
                shown["properties"][name] = shallow
        _section(parts, "Parent return form", _schema(shown, "return"))
        sources = state.get("available_report_facts", {})
        requested = {node.get("x-source") for node in form.get("properties", {}).values()}
        meanings = [(name, sources[name].get("meaning", "")) for name in sources if name in requested]
        if meanings:
            _section(parts, "Meaning of requested recorded facts", _table(("Source", "Meaning"), meanings))
    lifecycle = state.get("report_lifecycle")
    if lifecycle is not None:
        _section(parts, "Return interpretation timing", _text(lifecycle))
    return "\n".join(parts).lstrip("\n")


def render_rna_comparison_results_prompt(state: Mapping, instructions: str, *, lookup_results: Sequence = ()) -> str:
    """Repeat the complete fixed TASK and reuse supplied-fact/own-yield steering."""
    if not is_rna_comparison_results_context(state):
        raise ValueError("rna_comparison_results_context_required")
    assigned = rna_comparison_results_instructions(state["execution_assignment"])
    parts = ["TASK", "", text_instructions(instructions)]
    if assigned not in instructions:
        _section(parts, "Assigned retained comparison", assigned)
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
    parts.extend(["", render_rna_comparison_requested_return(state), "", render_episode_steering(state,
        lookup_results=lookup_results)])
    return "\n".join(parts)


__all__ = ["rna_comparison_results_instructions", "render_rna_comparison_results_prompt",
    "render_rna_comparison_requested_return"]
