"""A111 experimental feature assessment using the established source geometry sheet."""

EXPERIMENT_TYPES = {
    "structural_feature_geometry": {
        "question": "What does an experimentally determined model establish about the selected function-relevant molecular features?",
        "considerations": (
            "actual assayed molecule, construct, partners, experimental method and conditions",
            "exact deposited model, revision, atom assignment, alternate locations and insertion codes",
            "fixed required feature panel and distinct supporting/incompatible geometrical predictions",
            "local model/data agreement and matching validation entry/revision",
            "unmodeled endpoints, coordinate uncertainty and unknown local validation",
            "one fitted dataset versus independent experiments and population occupancy",
            "limits of selected-state geometry for mechanistic and causal claims",
        ),
        "reader": "read_structure_inputs",
        "calculator": "populate_source_geometry",
        "components": ("local_fit_index", "geometry_support_fraction", "geometry_opposition_fraction",
                       "source_geometry_positive", "source_geometry_opposing", "source_geometry_signed"),
        "combination": "Existing weakest local-fit index times the supporting/opposing geometry fractions, retaining the shared factor.",
    },
}
