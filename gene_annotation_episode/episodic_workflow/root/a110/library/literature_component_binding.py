"""A110 reaction literature population descriptors for the shared literature loop."""

def population_catalog_entries():
    from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reaction_inputs import reaction_population_schema
    from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_source_selection import reaction_source_population_schema
    return ({'name': 'literature.reaction.populate', 'description': 'Populate reported reference reaction-ratio residuals, named-prediction comparisons and simple resource-budget components from an explicitly retained received dataset or native source-selection recipe. Read exact report ratio points or author a:b expressions, summary uncertainty/counts and simple resource quantities with source units. Preserve unknown replication, missing alternatives, calibration basis and incomplete resource constraints. Product-pair ratios, instrument signals, supplied reagent budgets and usable capacity have distinct meanings. This route does not parse NMR spectra, establish measured oxygen coupling, apply missing corrections or calculate target transfer/annotation credit.', 'input_schema': reaction_population_schema(include_assessment=True)}, {'name': 'literature.reaction.source.populate', 'description': 'Populate the original experimental reaction components directly from exact received source spans, without a prepared measurement dataset. Select reported ratio points or author a:b expressions, actual uncertainty/count witnesses and source-unit resource quantities. Explicit predictions, coefficients and demand retain their interpreted basis. The host saves the source-selection recipe and invokes the existing native readers, numerical calculator, publication and exact selected-cell returns. Unknown sampling, calibration, alternatives and resource completeness remain unknown; no spectrum digitization, biological activity, target transfer or new score is inferred.', 'input_schema': reaction_source_population_schema()})

def population_family_specs():
    """Tuples matching literature_task_selection._Family constructor fields."""
    from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reaction_prompt import REACTION_TASK
    return (('literature_reaction_cells', REACTION_TASK, 'literature_reaction_storage', 'LiteratureReactionRepository', 'requested_reaction_components', 'literature.reaction.populate'),)

def scope_sources():
    return {'reported_reference_reaction_constraints': 'literature_reaction_cells'}

def source_aliases():
    return {'literature_reaction_semantic_cells': 'literature_reaction_cells', 'literature_reaction_native_observations': 'literature_reaction_cells'}

def request_aliases():
    return {'requested_reaction_native_positions': 'literature_reaction_cells'}

def population_routes(services):
    from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_population_contracts import COMPONENTS, PROVIDER
    from gene_annotation_episode.episodic_workflow.root.a110.literature_reaction_storage import LiteratureReactionRepository
    return (('literature_reaction_cells', 'requested_reaction_components', PROVIDER, COMPONENTS, lambda: LiteratureReactionRepository(services.workflow.store, services.workflow.run_id)), ('literature_reaction_semantic_cells', 'requested_reaction_components', PROVIDER, COMPONENTS, lambda: LiteratureReactionRepository(services.workflow.store, services.workflow.run_id).semantic_projection()))

def fact_sources():
    from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_report_contracts import reaction_cells_schema, reaction_semantic_cells_schema
    from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_native_observations import NAMESPACE, native_observations_schema
    return {'literature_reaction_cells': {'type': 'array', 'meaning': 'Saved reported reference reaction-ratio residuals, fixed named-prediction comparisons and simple resource budgets. Source summary uncertainty and incomplete resources remain explicit unknowns. Product-pair ratios and supplied reagent coverage do not establish consumption, native capacity or measured coupling. Logical domain bounds are not confidence intervals; no target correspondence or annotation credit is calculated.', 'report_schema': reaction_cells_schema()}, 'literature_reaction_semantic_cells': {'type': 'array', 'meaning': 'The same saved reference reaction/resource components with source-supported claim and alternative identities, named predictions and exact comparison membership. Resource meanings preserve supply basis, coefficient-to-demand linkage, period and compartment. Missing descriptions add no numerical gate. These are conditional source comparisons and fixed-consumption constraints, not extra assays, physiological sufficiency, target correspondence or annotation credit.', 'report_schema': reaction_semantic_cells_schema()}, NAMESPACE: {'type': 'array', 'meaning': 'Separately requested native reaction observations preserving exact reported points or ratio-expression operands, source unit conversion, measurement/calibration basis, actual uncertainty kind and count basis. Reported technical or unknown counts are not independent n. These are source operands, not extra scoring components or independent evidence.', 'report_schema': native_observations_schema()}}

def assignment_schema_fields():
    from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reaction_calculations import COMPONENTS
    from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_native_observations import positions_schema
    return {'requested_reaction_components': {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(COMPONENTS)}}, 'requested_reaction_native_positions': positions_schema()}

def inspection_operations():
    return frozenset({'literature.reaction.populate', 'literature.reaction.source.populate'})
