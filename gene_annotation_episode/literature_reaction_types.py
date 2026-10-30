"""A110 reusable questions and their existing numerical calculation families."""

EXPERIMENT_TYPES = {
    "reaction_prediction": {
        "question": "Do measured chemical ratios distinguish the proposed reaction from named alternatives?",
        "considerations": (
            "identified chemical species, products and isotopologues in the numerator and denominator",
            "formed, consumed or supplied amounts versus instrument signal",
            "reaction or atom-source predictions on the actual measured scale",
            "calibration, recovery, isotope enrichment and nuisance corrections already applied",
            "matched compartment, time window, molecular preparation and normalization",
            "replicate units, shared measurements, uncertainty and detection limits",
            "absolute prediction errors as well as relative alternative comparisons",
        ),
        "readers": ("read_reaction_inputs", "read_native_reaction_selection"),
        "calculator": "populate_reaction_constraints",
        "components": ("ratio_mean", "claim_nominal_squared_error", "claim_mean_squared_error",
                       "reaction_comparison", "reaction_comparison_lower", "reaction_comparison_upper"),
        "combination": "Existing squared-error contrast and minimum across fixed named alternatives.",
    },
    "resource_requirement": {
        "question": "Do measured usable resources meet the proposed reaction's demand in the stated biological scope?",
        "considerations": (
            "resource identity and measured accessible supply versus nominal reagent inventory",
            "consumption coefficients and output or demand basis",
            "same compartment and period, compatible amount/concentration/rate units",
            "carrier regeneration, competition and completeness of necessary resources",
            "censored supply, unknown constraints and physical domains versus sampling uncertainty",
        ),
        "readers": ("read_reaction_inputs", "read_native_reaction_selection"),
        "calculator": "populate_reaction_constraints",
        "components": ("resource_capacity", "resource_capacity_lower", "resource_capacity_upper",
                       "resource_coverage", "resource_coverage_lower", "resource_coverage_upper",
                       "resource_comparison", "resource_comparison_lower", "resource_comparison_upper"),
        "combination": "Existing limiting-resource minimum, capacity/demand coverage and signed coverage comparison.",
    },
}
