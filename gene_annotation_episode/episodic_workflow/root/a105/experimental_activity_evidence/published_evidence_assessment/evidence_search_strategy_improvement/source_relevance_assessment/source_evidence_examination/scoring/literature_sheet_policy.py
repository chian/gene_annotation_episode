"""A105 scientific identity and automatic assay aggregation rules."""
from __future__ import annotations
import json
SCORING_PROVIDER = 'literature.a105.aggregation'
GRADING_PROVIDER = 'literature.a105.assay_grading'
AXIS = 'A105'

def family_use(provider, arguments, saved, dependency_families, measurement_keys, replace_refs):
    if provider == GRADING_PROVIDER:
        effect = saved['sheet']['cells']['measured_effect']
        use = {name: arguments.get(name) for name in ('experiment_ref', 'assertion_ref', 'assay_type', 'quantity_kind')}
        use['effect_identity'] = measurement_keys(effect) or replace_refs(arguments['quantities']['effect'], dependency_families)
        return use
    if provider == SCORING_PROVIDER:
        return {name: arguments[name] for name in ('assertion_ref', 'comparison_ref')}
    return None

def main_binding():
    return (GRADING_PROVIDER, 'gene_annotation_episode.episodic_workflow.root.a105.experimental_activity_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_a105_aggregation_storage', 'LiteratureA105AggregationRepository', 'requested_a105_aggregation_components')

def main_plans(heads, contributions, main, assertion, target, main_context, read_grade):
    prior = [row for row in heads if row['provider'] == main.provider and json.loads(row['arguments'])['assertion_ref'] == assertion and (json.loads(row['receipt'])['custody'] == 'owned')]
    plans = [json.loads(row['arguments']) for row in prior if row['current_status'] == 'current'] if prior else [{'assertion_ref': assertion, 'comparison_ref': None, 'experiments': []}]
    for arguments in plans:
        known = {entry['experiment_ref'] for entry in arguments['experiments']}
        for row in contributions:
            experiment = json.loads(row['arguments']).get('experiment_ref')
            if experiment is None or experiment in known:
                continue
            arguments['experiments'].append({'experiment_ref': experiment, 'metrics': {name: None for name in main.components}})
            known.add(experiment)
    return plans

def includes_grade(arguments, sheet_ref):
    return True
