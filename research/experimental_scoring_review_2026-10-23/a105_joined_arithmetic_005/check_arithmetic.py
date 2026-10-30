#!/usr/bin/env python3
"""Standalone synthetic arithmetic check; no production imports or source reading.

Run from the repository root with:
  .venv/bin/python research/experimental_scoring_review_2026-10-23/a105_joined_arithmetic_005/check_arithmetic.py

Only the explicitly supplied calculations are evaluated. Outputs are new research
artifacts beside this script; they are neither a reader nor an adopted scorer.
"""

from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction
import json
import math
from pathlib import Path


F = Fraction
AUTHORITY_READ = [
    "AGENTS.md",
    "GOAL.md",
    "docs/EPISODE_STRUCTURE.md",
    "docs/TIME_AWARE_ESTIMATION.md",
    "docs/TOOL_KNOWLEDGE.md",
    "docs/TASK_AND_STEERING.md",
    "docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md",
    "docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md",
    "research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md",
    "research/slotted_process_library/publications/2026-10-23-002/VERBATIM_RECOVERY_002.md",
    "docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md",
    "verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md",
    "research/experimental_scoring_review_2026-10-23/AGENTS.md",
    "research/experimental_scoring_review_2026-10-23/A105_REVIEW_ASSIGNMENTS_2026-10-23_001.md",
    "/home/chia/.codex/attachments/9a858f85-d1dc-4f59-b574-9988cc09dee2/pasted-text-1.txt",
]


def dec(value: Fraction | Decimal | int) -> Decimal:
    if isinstance(value, Fraction):
        return Decimal(value.numerator) / Decimal(value.denominator)
    return Decimal(value)


def number(value: Fraction | Decimal, units: str = "dimensionless") -> dict:
    """A numeric JSON cell plus exact rational or high-precision decimal form."""
    out = {"value": float(value), "decimal": str(dec(value)), "units": units}
    if isinstance(value, Fraction):
        out["exact_fraction"] = str(value)
    return out


def harmonic(values: list[Decimal], shift: Decimal) -> Decimal:
    return Decimal(len(values)) / sum(1 / (shift + v) for v in values) - shift


def arithmetic(values: list[Decimal]) -> Decimal:
    return sum(values) / Decimal(len(values))


def check_close(actual: float, expected: float) -> None:
    assert math.isclose(actual, expected, rel_tol=2e-14, abs_tol=2e-15), (actual, expected)


def evaluate() -> dict:
    with localcontext() as ctx:
        ctx.prec = 60
        sample, blank, contaminant = F("1.2"), F(".2"), F(".15")
        recovery, protein, response = F(1), F(1), F("1.25")
        a = (sample - blank - contaminant) / (recovery * protein * response)
        terms = list(map(F, [".0256", ".001156", ".00296225", ".0144", ".004624", ".0625"]))
        variance = sum(terms, F(0))
        S = a * a / (2 * variance)
        # tanh(S/2) = (exp(S)-1)/(exp(S)+1); no probability interpretation.
        B = (dec(S).exp() - 1) / (dec(S).exp() + 1)
        sequence = 2 * F(240) / (F(300) + F(320))
        structure = min(F(".9"), F(".85"))
        site, evolution = F(8, 10), F(85, 100)
        system_distance_squared = F(7) ** 2 / 100 + F(".5") ** 2 / 1
        system = (-dec(system_distance_squared) / 2).exp()
        components = {
            "sequence": dec(sequence), "structure": dec(structure),
            "site": dec(site), "evolution": dec(evolution), "system": system,
        }
        shift = Decimal(".1")
        values = list(components.values())
        known = [v for name, v in components.items() if name != "evolution"]
        results = {}
        for label, aggregate in [("arithmetic", arithmetic),
                                 ("shifted_harmonic", lambda v: harmonic(v, shift))]:
            full = aggregate(values)
            conditional = aggregate(known)
            lower, upper = aggregate(known + [Decimal(0)]), aggregate(known + [Decimal(1)])
            d = B * full
            d_lower, d_upper = B * lower, B * upper
            results[label] = {
                "full_five_family_R": number(full),
                "full_five_family_D": number(d),
                "full_five_family_c_unadopted": number(max(Decimal(0), d)),
                "missing_evolution_conditional_four_family_R": number(conditional),
                "missing_evolution_conditional_four_family_D": number(B * conditional),
                "missing_evolution_conditional_four_family_c_unadopted": number(max(Decimal(0), B * conditional)),
                "missing_evolution_full_five_family_R_bounds": [number(lower), number(upper)],
                "missing_evolution_full_five_family_D_bounds": [number(d_lower), number(d_upper)],
                "missing_evolution_full_five_family_c_bounds_unadopted": [number(max(Decimal(0), d_lower)), number(max(Decimal(0), d_upper))],
                "reversed_comparison_full_five_family_D": number(-d),
                "reversed_comparison_full_five_family_c_unadopted": number(Decimal(0)),
                "reversed_comparison_missing_evolution_D_bounds": [number(-d_upper), number(-d_lower)],
                "reversed_comparison_missing_evolution_c_bounds_unadopted": [number(Decimal(0)), number(Decimal(0))],
                "rejected_extra_0_85_times_0_8_D_for_check_only": number(d * Decimal(".85") * Decimal(".8")),
            }
            assert lower <= full <= upper
            assert lower <= conditional <= upper
            assert d == B * full  # No extra attribution/similarity multiplier.
            assert d != d * Decimal(".85") * Decimal(".8")
            # Swapping ordered comparison changes sign; the coordinate loses it.
            minus_B = ((-dec(S)).exp() - 1) / ((-dec(S)).exp() + 1)
            assert abs(minus_B + B) < Decimal("1e-58")
            assert abs(minus_B * full + d) < Decimal("1e-58")
            assert max(Decimal(0), minus_B * full) == 0

        assert a == F(17, 25) == F(".68")
        assert variance == F(".11124225")
        assert len(terms) == 6
        assert sequence == F(24, 31)
        assert structure == F(17, 20)
        assert system_distance_squared == F(37, 50)
        assert results["shifted_harmonic"]["full_five_family_R"]["value"] <= results["arithmetic"]["full_five_family_R"]["value"]

        # Independent binary-float evaluation of the whole numerical path.
        float_a = (1.2 - .2 - .15) / (1 * 1 * 1.25)
        float_v = math.fsum([.0256, .001156, .00296225, .0144, .004624, .0625])
        float_s = float_a ** 2 / (2 * float_v)
        float_b = math.tanh(float_s / 2)
        float_values = [480 / 620, min(.9, .85), 8 / 10, 85 / 100,
                        math.exp(-.5 * (7 ** 2 / 100 + .5 ** 2 / 1))]
        check_close(float_a, float(a))
        check_close(float_v, float(variance))
        check_close(float_s, float(S))
        check_close(float_b, float(B))
        for name, float_aggregate in [
            ("arithmetic", lambda v: math.fsum(v) / len(v)),
            ("shifted_harmonic", lambda v: len(v) / math.fsum(1 / (.1 + x) for x in v) - .1),
        ]:
            float_known = [value for i, value in enumerate(float_values) if i != 3]
            row = results[name]
            check_close(float_aggregate(float_values), row["full_five_family_R"]["value"])
            check_close(float_b * float_aggregate(float_values), row["full_five_family_D"]["value"])
            check_close(float_aggregate(float_known), row["missing_evolution_conditional_four_family_R"]["value"])
            for i, endpoint in enumerate([0., 1.]):
                rr = float_aggregate(float_known + [endpoint])
                check_close(rr, row["missing_evolution_full_five_family_R_bounds"][i]["value"])
                check_close(float_b * rr, row["missing_evolution_full_five_family_D_bounds"][i]["value"])

        # Rate/variance units scale together; unit conversion is not new evidence.
        seconds_a, seconds_v = a / 60, variance / 60 ** 2
        assert seconds_a ** 2 / (2 * seconds_v) == S
        # Every positive common rescaling preserves the dimensionless comparison.
        for scale in [F(1, 60), F(60), F(1000)]:
            assert (a * scale) ** 2 / (2 * variance * scale ** 2) == S
        # Exact rational identity, independent of Decimal transcendental arithmetic.
        for equal in [F(0), F(1, 5), F(1, 2), F(4, 5), F(1)]:
            for count in [4, 5]:
                assert F(count) / sum((1 / (F(1, 10) + equal) for _ in range(count)), F(0)) - F(1, 10) == equal

        # Same measurement identity in two representations remains one observation.
        assay = {"measurement_id": "synthetic_assay_1", "a": a, "V": variance}
        duplicate_representations = [assay, dict(assay)]
        unique = {}
        for record in duplicate_representations:
            identity = record["measurement_id"]
            if identity in unique:
                assert unique[identity] == record
            unique[identity] = record
        assert len(unique) == 1
        retained = unique["synthetic_assay_1"]
        assert retained["V"] == variance  # No artificial division by two.
        assert retained["a"] ** 2 / (2 * retained["V"]) == S

        return {
            "scope": "Entirely synthetic research arithmetic. No adopted formula, papers, readers, prompts, production edits or scientific runs.",
            "conditioning": {
                "comparison": "Explicitly hypothetical nonnegative activity model versus fixed zero activity, at the supplied positive corrected activity and supplied fixed variance.",
                "S": "a^2/(2V), evaluated only at this positive a; reversing ordered model comparison negates S.",
                "B": "tanh(S/2), a bounded signed transform; not a probability or calibrated evidence strength.",
                "uncertainty": "Six supplied additive variance terms on the corrected activity scale; covariance must already be accounted for or zero. Their experimental derivation is not supplied or validated here.",
                "negative_activity": "The positive-a squared expression must not be applied as positive evidence after observing a negative activity under a nonnegative-activity alternative.",
                "missing_evolution": "No five-family point estimate. Four-family point is conditional on measured families; five-family bounds use only the allowed missing-component range [0,1]. No midpoint, zero imputation or confidence coverage claim.",
                "weights": "Equal family weights and shifted-harmonic shape 0.1 are unadopted, uncalibrated arithmetic proposals.",
                "coordinate": "c=max(0,D) is an unadopted proposed nonnegative coordinate. Signed D is retained.",
            },
            "inputs": {
                "sample_rate": number(sample, "uM min^-1"),
                "blank_rate": number(blank, "uM min^-1"),
                "contaminant_rate": number(contaminant, "uM min^-1"),
                "recovery": number(recovery), "protein": number(protein, "uM"),
                "condition_response": number(response),
                "unit_convention": "uM rate/protein convention is declared only for this synthetic calculation; no source supplied physical concentration units.",
                "variance_contributions": [number(t, "min^-2") for t in terms],
                "sequence_pair_raw": 240, "sequence_self_raw": [300, 320],
                "structure_comparison_scores": [.9, .85],
                "site_numerator_denominator": [8, 10],
                "evolution_numerator_denominator": [85, 100],
                "system_difference_and_squared_scale": [[7, 100], [.5, 1]],
                "system_units": "Each squared difference must match its denominator's squared units; the specific dimensions and calibration are unspecified.",
                "harmonic_shift": number(F(1, 10)),
                "missing_evolution_input": None,
            },
            "derived": {
                "corrected_activity": number(a, "min^-1"),
                "V": number(variance, "min^-2"), "S": number(S), "B": number(B),
                "r_sequence": number(sequence), "r_structure": number(structure),
                "r_site": number(site), "r_evolution": number(evolution),
                "system_squared_standardized_distance": number(system_distance_squared),
                "r_system": number(system),
                "activity_per_second": number(seconds_a, "s^-1"),
                "variance_per_second_squared": number(seconds_v, "s^-2"),
            },
            "aggregates": results,
            "checks": {
                "exact_activity_and_variance": "passed",
                "independent_float_recalculation": "passed",
                "ordered_comparison_sign_reversal": "passed",
                "units_invariance": "passed",
                "all_equal_harmonic_identity_10_exact_cases": "passed",
                "missing_component_bounds_and_no_imputation": "passed",
                "duplicate_measurement_unique_count": len(unique),
                "duplicate_measurement_unchanged_variance_and_S": "passed",
                "each_original_variance_contribution_used_once": "passed",
                "no_extra_0_85_attribution_or_0_8_similarity_multiplier": "passed",
            },
            "provenance": {
                "instructions_fully_read": AUTHORITY_READ,
                "latest_human_instructions_reread_last": [AUTHORITY_READ[12], AUTHORITY_READ[-1]],
                "paper_reads": 0, "source_packets_read": 0,
                "arithmetic_inputs_source": "Parent's bounded assignment for a105_joined_arithmetic_005; all numbers synthetic.",
                "independence": "Checker written from supplied formulas without inspecting prior arithmetic implementations.",
            },
        }


def write_table(results: dict) -> str:
    d = results["derived"]
    rows = results["aggregates"]
    def fmt(cell: dict) -> str:
        return f"{cell['value']:.12f}"
    def bounds(cells: list[dict]) -> str:
        return "[" + ", ".join(fmt(c) for c in cells) + "]"
    lines = [
        "# A105 joined arithmetic — synthetic and unadopted",
        "",
        "This independently coded research check joins only the supplied numerical proposals. It adopts no scoring formula and completes no sheet. No paper, primary-source packet, reader, prompt, production file or scientific run was inspected or changed.",
        "",
        "| Cell | Exact expression | Value | Meaning / units |",
        "| --- | --- | ---: | --- |",
        f"| Corrected activity a | (1.2−0.2−0.15)/(1×1×1.25) = 17/25 | {fmt(d['corrected_activity'])} | min⁻¹ |",
        f"| V | 0.0256+0.001156+0.00296225+0.0144+0.004624+0.0625 = {d['V']['exact_fraction']} | {fmt(d['V'])} | min⁻²; each supplied variance contribution once |",
        f"| S | a²/(2V) = {d['S']['exact_fraction']} | {fmt(d['S'])} | dimensionless, specified comparison |",
        f"| B | tanh(S/2) | {fmt(d['B'])} | bounded signed transform, not probability |",
        f"| r_sequence | 2×240/(300+320) = 24/31 | {fmt(d['r_sequence'])} | normalized supplied sequence score |",
        f"| r_structure | min(0.9,0.85) = 17/20 | {fmt(d['r_structure'])} | supplied structure correspondence |",
        f"| r_site | 8/10 = 4/5 | {fmt(d['r_site'])} | supplied site correspondence fraction |",
        f"| r_evolution | 85/100 = 17/20 | {fmt(d['r_evolution'])} | supplied evolutionary correspondence fraction |",
        f"| r_system | exp[−½(7²/100+0.5²/1)] = exp(−37/100) | {fmt(d['r_system'])} | supplied system similarity transformation |",
        "",
        "All rate and protein units use a declared synthetic concentration convention: rates in µM/min and protein in µM. This makes a min⁻¹; no real experimental units are inferred. The six V terms are assumed already on the corrected-activity scale, with covariance accounted for upstream or zero. Their underlying experimental derivations are unavailable.",
        "",
        "The model comparison is explicitly hypothetical: nonnegative activity versus fixed zero, evaluated at this positive a and supplied fixed V. The positive-a expression S=a²/(2V) is not a general sign rule for a negative measurement. Swapping the ordered model comparison gives −S, −B and −D. B is neither a probability nor calibrated evidence strength.",
        "",
        "The following are competing **unadopted** combinations: R_A=Σr_j/5; R_H=5/Σ[1/(0.1+r_j)]−0.1; D=B×R. The harmonic shape 0.1 and equal family weights are not calibrated. The proposed c=max(0,D) is also unadopted; signed D remains present.",
        "",
        "| Available components / quantity | Arithmetic proposal | Shifted harmonic proposal |",
        "| --- | ---: | ---: |",
    ]
    display_rows = [
        ("All five: R", "full_five_family_R", False),
        ("All five: signed D", "full_five_family_D", False),
        ("All five: proposed c", "full_five_family_c_unadopted", False),
        ("Evolution missing: four-family conditional R", "missing_evolution_conditional_four_family_R", False),
        ("Evolution missing: four-family conditional D", "missing_evolution_conditional_four_family_D", False),
        ("Evolution missing: four-family conditional proposed c", "missing_evolution_conditional_four_family_c_unadopted", False),
        ("Evolution missing: full five-family R bounds", "missing_evolution_full_five_family_R_bounds", True),
        ("Evolution missing: full five-family D bounds", "missing_evolution_full_five_family_D_bounds", True),
        ("Evolution missing: full five-family proposed c bounds", "missing_evolution_full_five_family_c_bounds_unadopted", True),
        ("Comparison reversed: all-five signed D", "reversed_comparison_full_five_family_D", False),
        ("Comparison reversed: all-five proposed c", "reversed_comparison_full_five_family_c_unadopted", False),
        ("Comparison reversed, evolution missing: D bounds", "reversed_comparison_missing_evolution_D_bounds", True),
        ("Comparison reversed, evolution missing: proposed c bounds", "reversed_comparison_missing_evolution_c_bounds_unadopted", True),
    ]
    for label, key, is_bounds in display_rows:
        render = bounds if is_bounds else fmt
        lines.append(f"| {label} | {render(rows['arithmetic'][key])} | {render(rows['shifted_harmonic'][key])} |")
    lines += [
        "",
        "The missing-evolution conditional values use the four observed families: R_A,4=Σ_known r/4 and R_H,4=4/Σ_known[1/(0.1+r)]−0.1. They are not estimates of the complete five-family value. The full-five bounds substitute the allowed missing-component endpoints 0 and 1 only to calculate monotone bounds. No missing measurement is entered as zero, no midpoint is supplied, and these are not confidence intervals. For positive B, D and proposed c share these bounds; reversed D bounds are [−B R_upper,−B R_lower] and proposed c becomes [0,0].",
        "",
        "The contaminant subtraction addresses isolation of this preparation's activity; the response/recovery/protein corrections address the supplied measurement/comparability adjustments. Those adjusted quantities and their uncertainty enter a and V once. No additional 0.85 attribution multiplier or 0.8 similarity multiplier follows D. The numerical 0.85 structural component and 0.8 site component remain the separately requested correspondence inputs; they are not a second correction of the assay.",
        "",
        "The family fractions describe supplied correspondence measurements, not independent experiments. Their denominators and transforms are explicit; pair/self sequence scores must share a scoring convention, structural scores must be comparable, and site/evolution denominators require a defined eligible set in any real sheet. The system squared differences must have the same squared units as 100 and 1. No calibration, cross-family independence or real target relationship is established by this arithmetic fixture.",
        "",
        f"Checks passed: exact rational activity/variance; independent binary-float recalculation of the complete join; ordered-comparison sign reversal; units invariance (a={fmt(d['activity_per_second'])} s⁻¹, V={d['variance_per_second_squared']['decimal']} s⁻² leaves S unchanged); ten exact all-equal harmonic identities; missing-component bounds; same measurement in two representations retains one observation and unchanged V/S; six original variance terms used once; no extra correction multipliers. These checks validate arithmetic only.",
        "",
        "`joined_results.json` contains numerical cells, 60-digit calculation forms, exact fractions for rational values, formulas/conditioning, and the complete instruction-read provenance. Transcendental decimals are approximations to the exact expressions above; displayed values are rounded to 12 places. `check_arithmetic.py` uses only the Python standard library and no production modules. Run it with `.venv/bin/python research/experimental_scoring_review_2026-10-23/a105_joined_arithmetic_005/check_arithmetic.py`.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    payload = evaluate()
    output = Path(__file__).resolve().parent
    (output / "joined_results.json").write_text(json.dumps(payload, indent=2) + "\n")
    (output / "JOINED_NUMERICAL_TABLE.md").write_text(write_table(payload))
    print(json.dumps({"status": "all checks passed", "derived": payload["derived"],
                      "aggregates": payload["aggregates"], "checks": payload["checks"]}, indent=2))
