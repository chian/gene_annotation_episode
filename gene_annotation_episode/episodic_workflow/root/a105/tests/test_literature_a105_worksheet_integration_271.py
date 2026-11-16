"""Selected worksheet integration, using explicit controlled episode choices.

The numerical source selectors reuse the already root-converted AP case. These
tests introduce no new paper interpretation or actual-model science. Ordinary
episode choices, saved facts and original report contracts remain authoritative.
"""
from copy import deepcopy
import json
import sqlite3
from types import SimpleNamespace
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_storage import LiteratureRateRepository







@pytest.mark.parametrize('variant', ['literal', 'alias', 'duplicate_same_type', 'changed_type', 'unknown', 'ambiguous', 'nested', 'external', 'alias_sibling', 'purpose'])
def test_repair_authenticates_aliases_against_only_original_frozen_types(variant):
    """Exercise the selected-choice authentication, without a current factory."""
    database = sqlite3.connect(':memory:')
    database.row_factory = sqlite3.Row
    store = SimpleNamespace(db=database)
    repository = LiteratureRateRepository(store, 'run271')
    source = 'literature_rate_cells'
    field_type = {'type': 'array', 'x-source': source, 'items': {'type': 'number'}}
    schema = {'type': 'object', 'properties': {'rates': deepcopy(field_type)}, 'required': ['rates'], 'additionalProperties': False}
    original = {'decision': 'Original numerical return.', 'measurements': {'schema': deepcopy(schema)}}
    original['measurements']['schema']['properties']['context'] = {'type': 'string'}
    original['measurements']['schema']['required'].append('context')
    selected_schema = deepcopy(schema)
    if variant != 'literal':
        selected_schema['properties']['rates'] = {'$ref': 'episode-fact:' + source}
    if variant == 'duplicate_same_type':
        original['measurements']['schema']['properties']['duplicate'] = deepcopy(field_type)
    elif variant == 'changed_type':
        selected_schema['additionalProperties'] = True
    elif variant == 'unknown':
        selected_schema['properties']['rates']['$ref'] = 'episode-fact:not_in_original'
    elif variant == 'ambiguous':
        original['measurements']['schema']['properties']['duplicate'] = {**field_type, 'maxItems': 1}
    elif variant == 'nested':
        selected_schema['properties']['rates'] = {'type': 'array', 'items': {'$ref': 'episode-fact:' + source}}
    elif variant == 'external':
        selected_schema['properties']['rates']['$ref'] = 'https://example.invalid/type'
    elif variant == 'alias_sibling':
        selected_schema['properties']['rates']['maxItems'] = 1
    repaired = {'decision': 'Numerical facts only.', 'measurements': {'schema': schema}}
    choice = {'kind': 'redeliver_report', 'delivery_ref': 'delivery271', 'purpose': repaired['decision'], 'schema_json': json.dumps(selected_schema)}
    if variant == 'purpose':
        choice['purpose'] = 'Different request.'
    database.execute('CREATE TABLE runtime_episodes(run_id,episode_id,request)')
    database.execute('CREATE TABLE runtime_report_attempts(run_id,parent_episode_id,decision_index,form,contract,failure,child_episode_id,delivery_ref)')
    database.execute('CREATE TABLE runtime_actions(run_id,episode_id,decision_index,action)')
    database.execute('INSERT INTO runtime_episodes VALUES(?,?,?)', ('run271', 'child271', json.dumps({'report_contract': original})))
    database.execute('INSERT INTO runtime_report_attempts VALUES(?,?,?,?,?,?,?,?)', ('run271', 'parent271', 1, None, json.dumps(original), 'unsupported link', 'child271', 'delivery271'))
    database.execute('INSERT INTO runtime_report_attempts VALUES(?,?,?,?,?,?,?,?)', ('run271', 'parent271', 2, json.dumps({'rates': [1.25]}), json.dumps(repaired), None, 'child271', 'delivery271'))
    database.execute('INSERT INTO runtime_actions VALUES(?,?,?,?)', ('run271', 'parent271', 2, json.dumps(choice)))
    context = SimpleNamespace(episode_id='parent271')
    try:
        if variant in ('literal', 'alias', 'duplicate_same_type'):
            assert repository._runtime_delivery_cells(context, 'run271:parent271:2:typed_form') == [1.25]
        else:
            with pytest.raises(ContractError, match='literature_delivery_binding_mismatch'):
                repository._runtime_delivery_cells(context, 'run271:parent271:2:typed_form')
    finally:
        database.close()

