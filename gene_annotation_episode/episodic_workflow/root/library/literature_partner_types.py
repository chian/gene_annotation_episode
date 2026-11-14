"""Experimental A107 partner requirement assessment; genomic searches are separate."""

EXPERIMENT_TYPES = {
    "partner_requirement": {
        "question": "Which experimentally identified partner is required for the measured outcome under the tested conditions?",
        "considerations": (
            "actual subject, partner identity, direction of the molecular relationship and assayed construct",
            "partner-present, omitted and independently observed addback arms",
            "matched nonpartner factors, endpoint and normalization",
            "required partner versus bypass reagent or indirect stimulation",
            "physical measurement identity and shared reference controls",
            "native rates, source-defined units, detection limits and reported uncertainty",
            "condition-specific dependence versus physiological presence or computational coexpression",
        ),
        "readers": ("read_partner_inputs", "read_partner_native_inputs"),
        "calculator": "populate_partner_components",
        "components": ("reference_rate", "omitted_rate", "addback_rate", "partner_loss",
                       "partner_loss_fraction", "addback_gain", "addback_fraction", "restored_reference_fraction"),
        "combination": "Existing matched omission/addback differences and fractions with shared physical measurements and conditional censor domains.",
    },
}
