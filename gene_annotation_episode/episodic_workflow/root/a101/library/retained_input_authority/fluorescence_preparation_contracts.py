"""Closed data ports for explicitly selected fluorescence preparation.

The common fluorescence sheet remains the only numerical scoring authority.
These validators check identities and lineage, never rerun a native operation.
"""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority import fluorescence_event_contracts as core
SCALE_METHOD = 'fcs_scale_flowio_1_4_0'
COMPENSATE_METHOD = 'spill_compensate_flowutils_1_2_2'
METHODS = {SCALE_METHOD, COMPENSATE_METHOD}
POLICY = 'strict_present_fcs_metadata_v1'
_CODE = 'invalid_parameters'

def _need(condition):
    core._need(condition, _CODE)

def _keys(value, names):
    core._keys(value, names, _CODE)

def _list(value):
    core._list(value, _CODE)

def _output_channels(value):
    _list(value)
    for channel in value:
        _keys(channel, 'key ordinal native_name label unit analyte')
        core._channel(dict(channel, measurement_origin='observed'), binding=True)
    core._unique([channel['key'] for channel in value], _CODE)
    _need([channel['ordinal'] for channel in value] == list(range(len(value))))
    _need(bool(value))

def _request(value):
    _keys(value, 'key input output recipe_file recipe')
    core._key(value['key'], _CODE)
    _keys(value['input'], 'kind index')
    core._enum(value['input']['kind'], {'event_input', 'preparation'}, _CODE)
    core._integer(value['input']['index'], _CODE)
    output = value['output']
    _keys(output, 'key source_key sample_key channels comparison_basis')
    for name in ('key', 'source_key', 'sample_key'):
        core._key(output[name], _CODE)
    _output_channels(output['channels'])
    core._basis(output['comparison_basis'], _CODE, nullable=True)
    core._file(value['recipe_file'], _CODE)
    recipe = value['recipe']
    _keys(recipe, 'version method parameters')
    _need(recipe['version'] == 'fluorescence_preparation_recipe_v1')
    core._enum(recipe['method'], METHODS, _CODE)
    params = recipe['parameters']
    if recipe['method'] == SCALE_METHOD:
        _keys(params, 'metadata_policy')
        _need(params['metadata_policy'] == POLICY)
    else:
        _keys(params, 'matrix_file dataset_position keyword input_domain_basis axes')
        core._file(params['matrix_file'], _CODE)
        core._integer(params['dataset_position'], _CODE)
        core._enum(params['keyword'], {'spill', 'spillover'}, _CODE)
        core._basis(params['input_domain_basis'], _CODE)
        _list(params['axes'])
        _need(bool(params['axes']))
        for axis in params['axes']:
            _keys(axis, 'native_label input_channel_key input_ordinal')
            core._key(axis['native_label'], _CODE)
            core._key(axis['input_channel_key'], _CODE)
            core._integer(axis['input_ordinal'], _CODE)
        for name in ('native_label', 'input_channel_key', 'input_ordinal'):
            core._unique([axis[name] for axis in params['axes']], _CODE)
    return value

def validate_preparation_request(value: dict, *, input_domains: list[dict]) -> dict:
    """Resolve index in the ordered list for the request's selected input kind.

    The producer supplies DomainIdentity records {key, source_key, sample_key}
    projected from original domains or earlier requested outputs. It validates
    that category/topology; this port never invents a future executed Domain.
    """
    _request(value)
    _list(input_domains)
    for domain in input_domains:
        _keys(domain, 'key source_key sample_key')
        for name in domain:
            core._key(domain[name], _CODE)
    core._unique([domain['key'] for domain in input_domains], _CODE)
    index = value['input']['index']
    _need(index < len(input_domains))
    parent = input_domains[index]
    output = value['output']
    _need(output['sample_key'] == parent['sample_key'])
    _need(output['key'] not in {domain['key'] for domain in input_domains})
    _need(output['source_key'] not in {domain['source_key'] for domain in input_domains})
    return deepcopy(value)
