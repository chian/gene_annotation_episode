"""Original tracking filtering preserves scientific names, operands and qualification."""
from copy import deepcopy
from importlib import import_module

import pytest

AXIS = __package__.rsplit('.tests', 1)[0]
OWNERS = [AXIS + '.library.literature_experimental_prompt',
    AXIS + '.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.prompts.literature_experimental_prompt']


@pytest.mark.parametrize('owner', OWNERS)
def test_original_filter_omits_tracking_and_keeps_scientific_values(owner):
    safe = import_module(owner)._safe
    value = {'measurement_keys': {'rate': 'HOST_MEASUREMENT_HASH'},
        'private_trace': 'PRIVATE_ONLY', 'original_sha256': 'PRIVATE_DIGEST',
        'claim': 'native_rate_label is the literal source label',
        'subject': 'amount_sensitive enzyme', 'quantity': 0.16, 'unit': 'µmol/min',
        'qualification': 'Productive coupling remains unquantified.',
        'observations': ({'accession': 'native_rate_generated', 'value': 0.10,
            'uncertainty': None, 'status': 'partial', 'subject': 'transport_curve_A'},)}
    original = deepcopy(value)
    assert safe(value) == {'claim': value['claim'], 'subject': value['subject'],
        'quantity': 0.16, 'unit': 'µmol/min', 'qualification': value['qualification'],
        'observations': [{'value': 0.10, 'uncertainty': None, 'status': 'partial', 'subject': 'transport_curve_A'}]}
    assert value == original


@pytest.mark.parametrize('owner', OWNERS)
def test_original_filter_distinguishes_generated_accessions_from_source_identity(owner):
    safe = import_module(owner)._safe
    values = [{'accession': prefix + 'internal', 'source_subject': prefix + 'reported_name'}
        for prefix in ('transport_curve_', 'transport_quantity_', 'native_rate_', 'amount_')]
    values.extend([{'accession': 'P12345', 'uncertainty': 'unreported'},
        {'accession': 42, 'qualification': 'unresolved target correspondence'}])
    original = deepcopy(values)
    actual = safe(values)
    assert actual[:4] == [{'source_subject': row['source_subject']} for row in values[:4]]
    assert actual[4:] == values[4:]
    assert values == original
