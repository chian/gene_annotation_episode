"""A106 intervention identity and dependent-sheet revision rules."""


SCORING_PROVIDER = 'literature.a106.subscore'
GRADING_PROVIDER = 'literature.a106.intervention_grading'
AXIS = 'A106'


def family_use(provider, arguments, saved, dependency_families, measurement_keys, replace_refs):
    if provider == GRADING_PROVIDER:
        assessment = arguments['experiment_assessment']
        return {name: assessment[name] for name in ('experiment_ref', 'assessment_key')}
    if provider == SCORING_PROVIDER:
        from gene_annotation_episode.episodic_workflow.root.a106.library.literature_a106_subscore_storage import QUESTION_FIELDS
        return {name: arguments[name] for name in QUESTION_FIELDS}
    return None


def dependent_revision(provider, arguments, replacements):
    """An intervention assessment is never silently rejudged."""
    if provider == GRADING_PROVIDER:
        return 'skip', None
    if provider == SCORING_PROVIDER:
        changed = [replacements.get(item['sheet_ref'], item['sheet_ref'])
            for item in arguments['experiments'] if item['sheet_ref'] is not None]
        if any(replacements.get(item['sheet_ref'], item['sheet_ref']) != item['sheet_ref']
                for item in arguments['experiments']):
            return 'unavailable', {
                'reason': 'a106_current_assessments_require_automatic_judgment',
                'input_versions': changed}
        return 'skip', None
    return 'refresh', None


def includes_grade(arguments, sheet_ref):
    return sheet_ref in {item['sheet_ref'] for item in arguments['experiments']}
