"""A107 partner literature population descriptors for the shared literature loop."""

def population_catalog_entries():
    from gene_annotation_episode.episodic_workflow.root.a107.library.literature_partner_sheet_records import partner_population_schema
    from gene_annotation_episode.episodic_workflow.root.a107.library.literature_partner_operand_information import partner_source_population_schema_with_information
    return ({'name': 'literature.partner.populate', 'description': 'Populate source experimental partner-removal and addback components from received retained measurements and exact source witnesses. Preserve directed molecule/partner roles, nitrogen and other nonpartner conditions, normalization identity, physical measurement identity and reported spread meanings. Incompatible or incomplete comparisons keep native values and explicit unknown components. Censor domains are not confidence intervals; chemical bypass and partner swaps do not establish universal partner necessity, genomic presence, target transfer or annotation credit.', 'input_schema': partner_population_schema(include_assessment=True)}, {'name': 'literature.partner.source.populate', 'description': 'Populate the same experimental partner components directly from selected literal source spans. Select complete rate/limit tokens, native units, spread meanings and source-bound entity/physical-measurement identities; do not supply scientific numbers or a prepared numeric JSON dataset. For source-defined activity units such as U/mg, select the endpoint-specific definition, quantity, molecular entity and time basis; no universal U conversion is assumed. Deterministic readers preserve original tokens, convert supported rate units and retain unknown normalization, conditions or observation identity. A repeated representation is not a new measurement. No sampling uncertainty, universal necessity, target correspondence or annotation credit is inferred.', 'input_schema': partner_source_population_schema_with_information()})

def population_family_specs():
    """Tuples matching literature_task_selection._Family constructor fields."""
    from gene_annotation_episode.episodic_workflow.root.a107.library.partner_source_instruction_text import PARTNER_TASK
    return (('literature_partner_cells', PARTNER_TASK, 'literature_partner_storage', 'LiteraturePartnerRepository', 'requested_partner_components', 'literature.partner.populate'),)

def scope_sources():
    return {'reference_experimental_partner_components': 'literature_partner_cells'}

def population_routes(services):
    from gene_annotation_episode.episodic_workflow.root.a107.literature_partner_storage import LiteraturePartnerRepository
    from gene_annotation_episode.episodic_workflow.root.a107.library.literature_partner_sheet_records import COMPONENTS, PROVIDER
    return (('literature_partner_cells', 'requested_partner_components', PROVIDER, COMPONENTS, lambda: LiteraturePartnerRepository(services.workflow.store, services.workflow.run_id)),)

def fact_sources():
    from gene_annotation_episode.episodic_workflow.root.a107.library.literature_partner_sheet_records import partner_cells_schema
    return {'literature_partner_cells': {'type': 'array', 'meaning': 'Saved experimental partner-removal and addback components with actual molecule/partner identities, nonpartner-condition comparisons, normalization, physical observation identity and reported spread meanings. Native rates survive unavailable controlled comparisons. Bounds condition on supplied censor domains and exact reported means; they are not sampling confidence. Directed condition-specific dependence does not establish universal necessity, genomic presence, coexpression, target correspondence or annotation credit.', 'report_schema': partner_cells_schema()}}

def assignment_schema_fields():
    from gene_annotation_episode.episodic_workflow.root.a107.library.literature_partner_calculations import COMPONENTS
    return {'requested_partner_components': {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(COMPONENTS)}}}

def inspection_operations():
    return frozenset({'literature.partner.populate', 'literature.partner.source.populate'})
