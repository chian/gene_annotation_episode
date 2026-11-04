"""Finite A108 assessment template, separate from investigation instructions."""

EXPERIMENT_TYPES = {
    "requirement_compatibility": {
        "question": "Do experimentally supported requirements fit the organism and the actual sampled biological contexts?",
        "considerations": (
            "organism, strain, clade, preparation and correspondence of the observed context",
            "compartment, access, environment and condition requirements with native unit bases",
            "supported and incompatible domains versus unexamined conditions",
            "joint requirements within a route and genuinely alternative routes",
            "paired physical contexts, repeated representations and shared measurements",
            "sample weights and frame versus organism capability and unexamined states",
            "detection limits, reported spread, logical domains and sampling uncertainty",
        ),
        "readers": ("read_context_inputs", "read_native_selection", "read_source_selection"),
        "calculator": "populate_context_compatibility",
        "combination": "Existing conjunction within routes, disjunction across routes/states, weighted coverage and unpaired Frechet bounds.",
    },
}
