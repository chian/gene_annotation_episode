"""A108 observation-use identity and current context aggregation rules."""
from gene_annotation_episode.episodic_workflow.root.a108.domain import canonical
SCORING_PROVIDER = 'literature.a108.aggregation'
GRADING_PROVIDER = 'literature.a108.context_grading'
AXIS = 'A108'

def family_use(provider, arguments, saved, dependency_families, measurement_keys, replace_refs):
    if provider == GRADING_PROVIDER:
        use = {name: arguments[name] for name in ('assertion_ref', 'target_context_ref', 'grader_type')}
        use['observations'] = sorted({(row['original_observation_key'], row['context_claim_ref']) for cell in saved['sheet']['cells'].values() for row in cell['relations']})
        return use
    if provider == SCORING_PROVIDER:
        return {name: arguments[name] for name in ('assertion_ref', 'target_context_ref')}
    return None

def revised_arguments(arguments, replacements, replace_refs):
    updated = replace_refs(arguments, replacements)
    updated['contributions'] = list({canonical(item): item for item in updated['contributions']}.values())
    return updated

def main_binding():
    return (GRADING_PROVIDER, 'gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_aggregation_storage', 'LiteratureA108AggregationRepository', 'requested_a108_aggregation_components')

def main_plans(heads, contributions, main, assertion, target, main_context, read_grade):
    available = [row for row in contributions if read_grade(row, main_context)]
    return [{'assertion_ref': assertion, 'target_context_ref': target, 'contributions': [{'sheet_ref': row['sheet_ref'], 'component': 'evidence_amount'} for row in available]}]

def includes_grade(arguments, sheet_ref):
    return True
