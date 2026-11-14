"""Original prepared-metadata validators; no API resource/client/transport."""
from copy import deepcopy
import math

import pytest

# Direct owner import preserves the actual missing-module baseline.
import gene_annotation_episode.episodic_workflow.root.enrichr_publication_metadata as metadata
from gene_annotation_episode.enrichr_contracts import validate_enrichr_request


def request(profile='standard_enrichr_v1', supplied=False):
    return {'version': 'enrichr_request_v1', 'protocol_profile': profile,
        'library': 'literal engineering library', 'genes': ['TP53', 'tp53', 'TP53'],
        'identifier_policy': 'literal_no_mapping', 'species_context': None,
        'description': 'Original engineering metadata — no provider result',
        'background': {'policy': 'supplied' if supplied else 'service_native',
            'genes': ['TP53', 'OTHER'] if supplied else None},
        'native_statistic_profile': 'uninterpreted'}


def configuration(profile='standard_enrichr_v1'):
    # Original recorded per-request metadata; never enforced or submitted here.
    return {'kind': 'api', 'service': 'enrichr', 'protocol_profile': profile,
        'base_url': 'https://engineering.invalid/literal-base',
        'timeout': 1.25, 'response_byte_limit': 4096}


def prepared(profile='standard_enrichr_v1', *, supplied=False, query=True):
    return {'version': 'enrichr_prepared_protocol_v1',
        'operation': 'api.enrichr.query' if query else 'api.enrichr.result',
        'request': request(profile, supplied), 'configuration': configuration(profile) if query else None,
        'mutates_remote': query, 'cache_original': not query}




@pytest.mark.parametrize('profile,supplied', [
    ('standard_enrichr_v1', False), ('speedrichr_v1', False), ('speedrichr_v1', True)])
def test_query_metadata_preserves_literals_and_detaches_nested_inputs(profile, supplied):
    value = prepared(profile, supplied=supplied)
    original = deepcopy(value)
    result = metadata._prepared(value, query_only=True)
    assert result == original and value == original
    assert result is not value and result['request'] is not value['request']
    assert result['request']['genes'] == ['TP53', 'tp53', 'TP53']
    assert result['configuration']['base_url'] == 'https://engineering.invalid/literal-base'
    assert result['configuration']['timeout'] == 1.25
    value['request']['genes'].append('later change')
    value['configuration']['response_byte_limit'] = 1
    assert result == original
    result['request']['background']['policy'] = 'changed detached copy'
    assert value['request']['background']['policy'] == original['request']['background']['policy']


def test_result_metadata_has_no_configuration_and_query_only_rejects_it():
    value = prepared(query=False)
    assert metadata._prepared(value) == value
    assert metadata._prepared(value)['configuration'] is None
    with pytest.raises(ValueError, match='enrichr_prepared_invalid'):
        metadata._prepared(value, query_only=True)
    with pytest.raises(ValueError, match='enrichr_prepared_invalid'):
        metadata._prepared({**value, 'configuration': configuration()})


@pytest.mark.parametrize('change', [
    {'version': 'other'}, {'operation': 'unselected'}, {'extra': True},
    {'mutates_remote': 1}, {'cache_original': 0}, {'mutates_remote': False}, {'cache_original': True},
])
def test_prepared_shape_and_exact_boolean_semantics(change):
    with pytest.raises(ValueError, match='enrichr_prepared_invalid'):
        metadata._prepared({**prepared(), **change})


def test_request_profile_conflict_and_supplied_background_policy_remain_rejected():
    value = prepared()
    value['configuration']['protocol_profile'] = 'speedrichr_v1'
    with pytest.raises(ValueError, match='enrichr_configuration_profile_conflict'):
        metadata._prepared(value)
    with pytest.raises(ValueError, match='enrichr_background_protocol_conflict'):
        metadata._prepared(prepared(supplied=True))
    value = prepared()
    del value['request']['identifier_policy']
    with pytest.raises(ValueError):
        metadata._prepared(value)


@pytest.mark.parametrize('url', ['', ' https://engineering.invalid', 'https://engineering.invalid/',
    'ftp://engineering.invalid', 'https://user:password@engineering.invalid',
    'https://engineering.invalid?query=1', 'https://engineering.invalid#fragment',
    'https://engineering.invalid:invalid', 'https://engineering.invalid/\npath'])
def test_configuration_rejects_original_invalid_endpoint_shapes(url):
    with pytest.raises(ValueError, match='enrichr_configuration_invalid'):
        metadata.validate_enrichr_configuration({**configuration(), 'base_url': url})


@pytest.mark.parametrize('change', [
    {'kind': 'local'}, {'service': 'other'}, {'protocol_profile': 'other'}, {'extra': None},
    {'timeout': True}, {'timeout': 0}, {'timeout': -1}, {'timeout': math.inf}, {'timeout': math.nan},
    {'response_byte_limit': True}, {'response_byte_limit': 0}, {'response_byte_limit': 1.5},
])
def test_configuration_preserves_original_finite_type_and_field_checks(change):
    with pytest.raises(ValueError):
        metadata.validate_enrichr_configuration({**configuration(), **change})


def test_configuration_required_fields_are_not_defaulted():
    for key in configuration():
        value = configuration()
        del value[key]
        with pytest.raises(ValueError, match='enrichr_configuration_invalid'):
            metadata.validate_enrichr_configuration(value)


def test_canonical_finite_json_preserves_unicode_and_original_overflow_behavior():
    assert metadata._canonical({'b': [1, None], 'a': 'α'}) == '{"a":"α","b":[1,null]}'.encode('utf-8')
    for invalid in (float('nan'), float('inf'), {'unsupported': {1, 2}}):
        with pytest.raises(ValueError, match='enrichr_finite_json_required'):
            metadata._canonical(invalid)
    cyclic = []
    cyclic.append(cyclic)
    with pytest.raises(ValueError, match='enrichr_finite_json_required'):
        metadata._canonical(cyclic)
    assert metadata._positive(10 ** 10000) is False
    assert metadata._positive(True) is False
