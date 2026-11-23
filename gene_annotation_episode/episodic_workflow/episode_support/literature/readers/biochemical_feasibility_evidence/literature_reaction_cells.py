"""The controlled features of a saved A110 reaction sheet (``literature_reaction_cells`` /
``literature_reaction_semantic_cells``), read by code from the sheet's cell rows and its saved extraction, each with
its validator.

What a feature is: the evidence type (``prediction_contrast``, E4 of ``INVESTIGATION_FINDING_FEATURES_a110.md``
table 1: a sheet compares a reaction claim's prediction, or a resource demand, with measured operands), the sheet's
reference and view, the value, status and unavailable reason of each of the fifteen cells (a cell without a value
has no value feature: nothing is defaulted), the input kinds the sheet keeps apart (R6: ratio mode, kind and unit,
budget basis and unit, the uncertainty kind), the panel sizes (independent units, named alternatives, resources,
native observations), whether the resource list was declared complete, the operand source kind and whether an
experiment assessment was saved with the sheet. No model-written text: the assessment's question, conclusion and
limitations and every witness quotation stay in the sheet, inside the Episode that saved it.

A grading sheet's own criteria and status are the result (owner, R19): nothing here re-judges or re-thresholds a
saved cell, and the cells of different sheets are listed side by side, never combined.
"""
import json
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.biochemical_feasibility_evidence.literature_reaction_calculations import (
    BUDGET_BASES, BUDGET_UNITS, COMPONENTS, RATIO_KINDS, RATIO_MODES, RATIO_UNITS, REASONS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.biochemical_feasibility_evidence.reaction_population_contracts import (
    MEANINGS_RECORD_VERSION, SOURCE_KINDS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.biochemical_feasibility_evidence.literature_reaction_storage import (
    CELLS, LiteratureReactionRepository)

EVIDENCE_TYPE = 'prediction_contrast'
STATUSES = ('populated', 'unavailable')
REASON_CHOICES = (*REASONS, 'none')
VIEWS = ('numerical', 'semantic')
UNCERTAINTIES = ('reported_sample_sd', 'descriptive_sample_sd', 'unreported')

# name -> (validator, meaning); validators: ('number',), ('count',), ('choice', options), ('boolean',), ('refs',);
# a validator with ``optional`` may be absent (a cell without a value, an unreported count)
FEATURES = {
    'evidence_type': (('choice', (EVIDENCE_TYPE,)), 'The A110 evidence type of a reaction sheet: prediction_contrast'),
    'sheet_refs': (('refs',), 'The saved sheet (one reference)'),
    'sheet_view': (('choice', VIEWS), 'numerical: literature_reaction_cells; semantic: the same cells '
                   'with source-bound meanings'),
    **{name: (('number', 'optional'), 'The value of the ' + name + ' cell, absent when the cell is unavailable')
       for name in COMPONENTS},
    **{name + '_status': (('choice', STATUSES), 'Whether the ' + name + ' cell is populated or unavailable')
       for name in COMPONENTS},
    **{name + '_unavailable_reason': (('choice', REASON_CHOICES),
                                      'The fixed reason the ' + name + ' cell is unavailable, or none')
       for name in COMPONENTS},
    'ratio_mode': (('choice', (*RATIO_MODES, 'none')), 'Independent units or a source summary; none without a ratio'),
    'ratio_kind': (('choice', (*RATIO_KINDS, 'none')), 'What the ratio relates; none without a ratio'),
    'ratio_unit': (('choice', (*RATIO_UNITS, 'none')), 'Moles or instrument signal; none without a ratio'),
    'ratio_uncertainty': (('choice', UNCERTAINTIES), 'How the ratio uncertainty is known'),
    'independent_n': (('count', 'optional'), 'Independent units of the ratio, absent when unreported'),
    'alternative_count': (('count',), 'Named alternative predictions compared with the claim'),
    'budget_basis': (('choice', (*BUDGET_BASES, 'none')), 'Supplied reagent or usable capacity; none without a budget'),
    'budget_unit': (('choice', (*BUDGET_UNITS, 'none')), 'Amount, concentration or rate; none without a budget'),
    'resource_count': (('count',), 'Resources in the budget'),
    'resources_complete': (('boolean', 'optional'), 'Whether the resource list was declared complete, absent without '
                           'a budget'),
    'native_observation_count': (('count',), 'Native source operands saved with the sheet'),
    'operand_source_kind': (('choice', SOURCE_KINDS), 'The kind of source the operands were read from'),
    'experiment_assessed': (('boolean',), 'Whether an experiment assessment was saved with the sheet'),
}


def validate_features(features):
    """Each feature against its validator. A violation raises ``ValueError``."""
    required = {name for name, (rule, _) in FEATURES.items() if 'optional' not in rule}
    if not required <= set(features) <= set(FEATURES):
        raise ValueError('reaction_finding_features_mismatch')
    for name, value in features.items():
        rule = FEATURES[name][0]
        if rule[0] == 'number':
            valid = type(value) in (int, float) and math.isfinite(value)
        elif rule[0] == 'count':
            valid = type(value) is int and value >= 0
        elif rule[0] == 'choice':
            valid = value in rule[1]
        elif rule[0] == 'boolean':
            valid = type(value) is bool
        else:
            valid = type(value) is list and len(value) == 1 and type(value[0]) is str
        if not valid:
            raise ValueError('reaction_finding_feature_invalid:' + name)
    return features


def _choice(value):
    return 'none' if value is None else value


def sheet_features(reader, sheet_ref):
    """The features of one sheet this Episode saved, read from its cell rows and its saved extraction."""
    cells = {row['component']: row['cell'] for row in reader.table(CELLS).select({'sheet_ref': sheet_ref})}
    saved = json.loads(reader.get_artifact(reader.get(sheet_ref)['artifact_ref']))
    inputs = saved['extraction']['calculation_inputs']
    ratio, budget = inputs['ratio'], inputs['budget']
    any_cell = cells[COMPONENTS[0]]
    features = {'evidence_type': EVIDENCE_TYPE, 'sheet_refs': [sheet_ref],
                'sheet_view': 'semantic' if saved['version'] == MEANINGS_RECORD_VERSION else 'numerical'}
    for name in COMPONENTS:
        cell = cells[name]
        if cell['value'] is not None:
            features[name] = cell['value']
        features[name + '_status'] = cell['status']
        features[name + '_unavailable_reason'] = _choice(cell['unavailable_reason'])
    features.update({
        'ratio_mode': _choice(any_cell['ratio_mode']), 'ratio_kind': _choice(any_cell['ratio_kind']),
        'ratio_unit': _choice(any_cell['ratio_unit']), 'ratio_uncertainty': any_cell['ratio_uncertainty'],
        'alternative_count': 0 if ratio is None else len(ratio['alternatives']),
        'budget_basis': _choice(any_cell['budget_basis']), 'budget_unit': _choice(any_cell['budget_unit']),
        'resource_count': 0 if budget is None else len(budget['resources']),
        'native_observation_count': len(saved.get('native_observations', ())),
        'operand_source_kind': any_cell['operand_source_kind'],
        'experiment_assessed': 'experiment_assessment' in saved,
    })
    if any_cell['independent_n'] is not None:
        features['independent_n'] = any_cell['independent_n']
    if any_cell['resources_complete'] is not None:
        features['resources_complete'] = any_cell['resources_complete']
    return validate_features(features)


def current_sheet_features(reader):
    """The features of each current sheet this Episode saved, in the order the sheets were first saved."""
    return [sheet_features(reader, ref) for ref in LiteratureReactionRepository(reader).current_sheet_refs()]


def merged_sheet_features(own, returned):
    """This Episode's own sheets and the sheets its children returned, one entry per sheet (first seen kept):
    sheets are listed side by side, never combined."""
    result = {}
    for features in (*own, *returned):
        result.setdefault(features['sheet_refs'][0], features)
    return list(result.values())
