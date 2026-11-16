"""Retained-native numerical replay and detached sheet/component validation."""
from copy import deepcopy

import pytest

from test_bvbrc_metacats_provider import requests, simple_sheet
from gene_annotation_episode.episodic_workflow.root.library import bvbrc_metacats_provider_contracts as c
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_metacats_grader import calculate_metacats


@pytest.mark.parametrize('mutation', ['request_kind', 'population', 'raw_identity', 'test_identity', 'parameters', 'subset', 'family_basis', 'p_value', 'dependency'])
def test_saved_component_request_population_and_identity_forgeries_rejected(mutation):
    sheet = simple_sheet(); parameters = requests(sheet, native=False); components = calculate_metacats(sheet, parameters)
    bad = deepcopy(components)
    if mutation == 'request_kind': bad['results'][0]['kind'] = 'native_group_counts'
    if mutation == 'population': bad['results'][0]['value']['population_id'] = 'foreign'
    if mutation == 'raw_identity': bad['results'][0]['value']['sites'][1]['table_id'] = 'biological_group_counts:fake'
    if mutation == 'test_identity': bad['results'][1]['value']['omnibus'][0]['test_id'] = 'biological_group_test:fake'
    if mutation == 'parameters': bad['parameters']['requests'][1]['epsilon'] = .1
    if mutation == 'subset': bad['results'][1]['value']['omnibus'] = []
    if mutation == 'family_basis': bad['results'][-1]['value']['family']['p_value_basis'] = 'native_unadjusted'
    if mutation == 'p_value': bad['results'][-1]['value']['results'][0]['input_p']['value'] = .123
    if mutation == 'dependency': bad['parameters']['requests'][1]['counts_request_id'] = bad['parameters']['requests'][2]['request_id']
    with pytest.raises(ValueError, match='bvbrc_metacats_provider_'):
        c.validate_metacats_components(bad, sheet=sheet)


