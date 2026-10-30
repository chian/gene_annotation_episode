"""Bounded source arithmetic; not an installed literature grader.

Only reported numbers from PMC12051542 are used. Experimental meanings are
declared in PROPOSAL.md, not inferred by the literal checks below.
"""
from pathlib import Path
from fractions import Fraction
import hashlib
import json

HERE = Path(__file__).resolve().parent
raw = (HERE / "primary_read.txt").read_bytes()
text = raw.decode()


def operand(fragment, value, unit, meaning, *, qualification="reported_point"):
    assert text.count(fragment) == 1, (fragment, text.count(fragment))
    start = raw.index(fragment.encode())
    return dict(value=value, unit=unit, meaning=meaning,
                qualification=qualification, origin="reported",
                source="primary_read.txt", start_utf8=start,
                end_utf8=start + len(fragment.encode()), fragment=fragment)


inputs = {
    "stock_total": operand("7 mg/ml per Bradford analysis", 7, "mg/ml", "total protein estimate"),
    "stock_hfp": operand("approximate concentration of 5 mg/ml HFP", 5, "mg/ml", "visual SDS-PAGE target estimate", qualification="source_qualified_approximate"),
    "arm_hfp": operand("8.4 μM HFP", 8.4, "uM", "one-pot nominal HFP concentration"),
    "arm_imp": operand("8.8 μM IMP", 8.8, "uM", "one-pot nominal IMP concentration"),
    "ru5p_percent": operand("39.7% ketose (ribulose)", 39.7, "percent", "reported equilibrium sugar-phosphate partition"),
    "r5p_percent": operand("60.3% aldose (ribose)", 60.3, "percent", "reported equilibrium sugar-phosphate partition"),
    "cleanup_time": operand(">18 h as opposed to <10 min", 18, "hour", "post-cleanup equilibrium completion-time lower bound", qualification="gt"),
    "precleanup_time": operand("less than 10 min (Fig. S5)", 10, "minute", "pre-cleanup equilibrium completion-time upper bound", qualification="lt"),
}

f = Fraction
derived = {
    "stock_target_over_total_estimate": {"value": float(f(5, 7)), "exact": "5/7", "approximate": True,
        "meaning": "mass-estimate relationship, not active fraction or contaminant activity"},
    "conditional_mass_denominator_factor": {"value": 1.4, "exact": "7/5", "approximate": True,
        "meaning": "multiply a same-stock total-mass-normalized rate only if that rate and denominator are established; not applied"},
    "nominal_hfp_minus_imp_uM": {"value": -.4, "exact": "8.4-8.8", "meaning": "between-arm amount difference"},
    "nominal_hfp_over_imp": {"value": float(f(84, 88)), "exact": "21/22", "meaning": "between-arm amount ratio, not an amount-response calibration"},
    "reported_r5p_partition": {"value": .603, "exact": "60.3/(39.7+60.3)", "meaning": "composition among reported sugar-phosphate species, not HFP attribution or total product recovery"},
    "reported_ru5p_partition": {"value": .397, "exact": "39.7/(39.7+60.3)", "meaning": "same reported composition denominator"},
    "equilibration_time_ratio": {"threshold": 108, "relation": "gt", "exact": "18*60/10",
        "meaning": "time after cleanup / time before cleanup; not initial-rate ratio"},
    "reciprocal_completion_metric_ratio": {"threshold": float(f(1, 108)), "relation": "lt", "exact": "10/(18*60)",
        "meaning": "reciprocal elapsed completion metric after/before cleanup; not retained HFP activity fraction"},
}

# A source conflict is preserved rather than silently repairing molar units.
assert "0.67 mM final concentration" in text
assert "0.67 M ribose 5-phosphate or 0.67 M ribulose 5-phosphate" in text

result = dict(
    status="bounded_primary_source_arithmetic_only",
    source_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC12051542/",
    source_text_sha256=hashlib.sha256(raw).hexdigest(), inputs=inputs, derived=derived,
    observed_panel={"isomerization_positive_samples": 4, "selected_samples": 5,
                    "probability_or_weight": None},
    activity_sheet={"values": {k: None for k in ("q", "g", "k", "E", "u", "v")},
        "covariance": None, "variance_status": "unknown", "observation_model": "none",
        "distinct_residual_variance": None, "corrected_activity": None,
        "source_presence_index": None,
        "reason": "same-preparation net molecular rate, contaminant contribution, recovery, condition-response controls and joint uncertainty not quantified"},
    limitations=["completion times are not initial rates", "cleanup changes construct, purification and heat exposure together",
        "target recovery after cleanup unreported", "5/7 stock differs from extensively purified NMR stock",
        "mM_vs_M_source_conflict_not_resolved", "no source-calibrated annotation reliability score"],
    annotation_credit=None, installed_grader=False, episode_integration_executed=False)
(HERE / "CALCULATED_CELLS.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
print(json.dumps(derived, indent=2))
