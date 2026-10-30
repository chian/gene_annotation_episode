# Additive reader clarification and selected storage contract

REACTION_INTERFACES001 uses sources.literal as shorthand. Existing _Sources
provides witness(): reader wraps {value:witness.quote,witness:witness}. Exact
reader output remains version,arguments,sources,literals,interpretations,
observations,calculation_inputs; sources is list(_Sources.references).

Fresh storage owner exclusive files literature_reaction_storage.py under
gene_annotation_episode and tests/test_literature_reaction_storage.py.
Expose LiteratureReactionRepository, reaction_population_schema,
reaction_cells_schema, COMPONENTS, PROVIDER. Reuse LiteratureRateRepository
receive/admission behavior; operation tables literature_reaction_operations
and literature_reaction_received, provider literature.experimental.reaction,
recordversion literature_reaction_record_v1. Populate calls new source reader
then pure calculator; frozen selected operation/request/scope/payload survive
reopen without source-byte reading or recomputation. Source receipt/scope/page
lineage, immutable selected authority, transactionality, same-run/request checks
follow literature_structure_storage. Read existing complete consumers first.

Eight scientific BINDINGS:
assayed_subject_ref:molecule/reference; construct_ref:construct/reference;
experiment_ref:experiment/reference; numerator_ref:numerator/term;
denominator_ref:denominator/term; endpoint_ref:endpoint/term;
condition_ref:condition/context; resource_context_ref:resource_context/context.
Keep actual source byte anchors in generated records. Canonical directinputs
are root source, dataset when present, literals in fixed LITERAL_FIELDS order,
interpretation_witnesses in declared order, deduplicated. Compare sets against
reader.sources because JSONcanonicalization can reorder literal dict keys.
All directinputs must be received, in scope and assigned page lineage; parent
source provenance in scope. Replay validates permissions but reads only saved
payload/request artifacts (no original byte parsing/calculation).

Typed requested row = source sheet/evidence/data refs, eight BINDINGS,
component and cellshape without formula but with fixed formula_code,
ratio_mode(nullable enum),ratio_kind(nullable enum),ratio_unit(nullable enum),
claim_prediction(nullable number),alternative_predictions(array nullable numbers),
budget_basis(nullable enum),budget_unit(nullable enum),resources_complete(nullable
boolean),demand(nullable number),operand_source_kind(enum),
evaluation_scope='reported_reference_reaction_constraints',
bound_kind='logical_model_domain_not_confidence_interval',
measurement_corrections='not_applied',
target_correspondence='not_evaluated'.
Meaning of model comparisons is the ordered fixed numeric prediction panel on
the named numerator/denominator scale; original model keys remain in immutable
sheet. No unrestricted prose field, invented independence or target weight.
No fullsheet inserted into prompts. Schema uses declared constrained types;
constants from calculator populate allowed reasons/conditions/origin/units.
Actual allowed return rows must exactly match saved selected subset, checked
through both JSON schema and repository validation. Parent forwarding only
admitted subset, not child's entire private sheet. No controller observations
or model calls in storage. No modifications to existing files by storage owner.
