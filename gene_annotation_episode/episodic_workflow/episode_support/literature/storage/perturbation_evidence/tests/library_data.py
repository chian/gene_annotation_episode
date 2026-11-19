"""Constructed summary data of the perturbation storage scenarios: statistical premise qualification and
covariance meanings. Synthetic operands; they make no scientific claim."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.perturbation_evidence.tests.test_literature_perturbation_summary import (
    source_data, covariance)

FIELDS = ('summary_kind', 'summary_scale', 'spread_kind', 'spread_scale',
          'count_n', 'count_unit', 'count_independence')
REQUIRED = ['W_summary_value', 'perturbation_difference', 'symmetric_effect',
    'restoration_difference', 'restoration_fraction_raw', 'amount_comparability',
    'effect_isolation', 'reference_restoration_index']
SUPPORT = b'Constructed covariance design; covariance 0.000000000000000000, unrelated arm value 987654321.'


def basis(**overrides):
    return {**dict.fromkeys(FIELDS, 'source_reported'), **overrides}


def data_with_basis():
    data = source_data()
    for role, entry in data['measurements'].items():
        entry['interpretation_basis'] = basis(summary_scale='conditional_assumption')
    return data


def data_for(kind='mean_covariance', basis_name='source_reported', *, qualify=True, all_pairs=False):
    data = source_data(); data['exposure_unit'] = 'unreported'
    for role in ('W', 'K', 'R'):
        entry = data['measurements'][role]
        entry['count'].update(n=5, unit_kind='culture')
        entry['uncertainty'].update(kind='sem', value=1)
        entry['interpretation_basis'] = dict.fromkeys(FIELDS, 'source_supported_inference')
    if kind == 'paired_units':
        for role, values in [('W', [8, 13, 13, 13, 13]), ('K', [3, 0, 2, 4, 6])]:
            entry = data['measurements'][role]; entry['value'] = None
            entry['uncertainty'].update(kind='unreported', value=None)
            entry['raw_units'] = [{'unit_id': 'unit' + str(i), 'values': [value]}
                                  for i, value in enumerate(values)]
    pairs = (('W', 'K'), ('W', 'R'), ('K', 'R')) if all_pairs else (('W', 'K'),)
    data['covariances'] = []
    for first, second in pairs:
        item = covariance(first, second, kind, 0 if kind == 'mean_covariance' else None)
        if qualify:
            item['interpretation_basis'] = basis_name
        data['covariances'].append(item)
    return data
