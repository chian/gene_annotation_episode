"""Configured VDB operation information, using controlled files and no native run."""
from copy import deepcopy
from itertools import product

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.native_blast_utility_contracts import (
    VDB_MODES, requested_job_from_native_blast_utility, validate_native_blast_utility_job,
)
from gene_annotation_episode.native_blast_utility_tool_info import (
    native_blast_utility_binding_accepts_job, native_blast_utility_tool_contracts,
    validate_native_blast_utility_bindings,
)
from test_blast_vdb_native_context_668 import controlled_job


SELECTIONS = ('entry', 'entry_batch', 'all_native_sequences', 'all_references',
              'info', 'paths', 'paths_all')
CASES = [(selection, source, filtered)
         for selection, source in product(SELECTIONS, ('db', 'dbs_file'))
         for filtered in ((False, True) if selection in {
             'entry', 'entry_batch', 'all_native_sequences'} else (False,))]


def variant(selection, source='db', filtered=False):
    return {'database_source': source, 'database_input_kind': 'path',
        'selection_kind': ('entries' if selection in {'entry', 'entry_batch'} else
            selection if selection in {'all_native_sequences', 'all_references'} else None),
        'entry_source': selection if selection in {'entry', 'entry_batch'} else None,
        'include_filtered_reads': filtered}


def job(tmp_path, selection, source='db', filtered=False):
    result = controlled_job(tmp_path, selection, source, metadata=False)
    result['operation']['parameters']['include_filtered_reads'] = filtered
    return validate_native_blast_utility_job(result)


def binding(selected_job, selected_variant):
    return {'program': 'blast_vdb_cmd', 'mode': selected_job['operation']['mode'],
        'software': deepcopy(selected_job['software']), 'molecules': ['dna'],
        'variants': [deepcopy(selected_variant)]}


@pytest.mark.parametrize('selection,source,filtered', CASES)
def test_configured_variant_matches_exact_requested_job_schema_and_runtime(
        tmp_path, selection, source, filtered):
    selected = variant(selection, source, filtered)
    row = binding(job(tmp_path, selection, source, filtered), selected)
    descriptor, = native_blast_utility_tool_contracts([row], resource_kind='local', resource_id='selected')
    validator = Draft202012Validator(descriptor['input_schema'])
    for alternative, other_source, other_filtered in CASES:
        other = job(tmp_path, alternative, other_source, other_filtered)
        expected = (other['operation']['mode'] == row['mode']
                    and variant(alternative, other_source, other_filtered) == selected)
        assert native_blast_utility_binding_accepts_job(row, other) is expected
        assert validator.is_valid(requested_job_from_native_blast_utility(other)) is expected
    assert descriptor['name'] == 'native.blast_vdb_cmd.' + row['mode']
    assert descriptor['resources'] == 'local'
    assert descriptor['invocation_route']['routes'] == [
        {'entry_role': 'launch', 'resource_id': 'selected', 'resource_role': 'launch_local'}]
    assert descriptor['input_schema']['properties']['native_blast_utility']['properties']['version'] == {
        'const': 'native_blast_utility_job_v3'}
    assert descriptor['description'] and descriptor['instructions']


@pytest.mark.parametrize('change', ['missing_variants', 'empty_variants', 'duplicate_variants',
    'extra_field', 'protein', 'unknown_molecule', 'alias', 'accession', 'all_with_entry_source',
    'entries_without_source', 'reference_filtered', 'nonboolean_filter', 'bad_database_source'])
def test_invalid_or_unestablished_variant_is_not_a_configured_capability(tmp_path, change):
    row = binding(job(tmp_path, 'entry'), variant('entry'))
    chosen = row['variants'][0]
    if change == 'missing_variants': row.pop('variants')
    elif change == 'empty_variants': row['variants'] = []
    elif change == 'duplicate_variants': row['variants'].append(deepcopy(chosen))
    elif change == 'extra_field': chosen['automatically_resolve'] = True
    elif change == 'protein': row['molecules'] = ['protein']
    elif change == 'unknown_molecule': row['molecules'] = ['unknown']
    elif change in {'alias', 'accession'}: chosen['database_input_kind'] = change
    elif change == 'all_with_entry_source': chosen['selection_kind'] = 'all_native_sequences'
    elif change == 'entries_without_source': chosen['entry_source'] = None
    elif change == 'reference_filtered':
        chosen.update(selection_kind='all_references', entry_source=None, include_filtered_reads=True)
    elif change == 'nonboolean_filter': chosen['include_filtered_reads'] = 1
    elif change == 'bad_database_source': chosen['database_source'] = 'automatic'
    with pytest.raises(ValueError): validate_native_blast_utility_bindings([row])


@pytest.mark.parametrize('selection', ['info', 'paths', 'paths_all'])
@pytest.mark.parametrize('field,value', [('selection_kind', 'entries'), ('entry_source', 'entry'),
                                        ('include_filtered_reads', True)])
def test_inspection_binding_does_not_advertise_extraction_arguments(tmp_path, selection, field, value):
    row = binding(job(tmp_path, selection), variant(selection))
    row['variants'][0][field] = value
    with pytest.raises(ValueError): validate_native_blast_utility_bindings([row])


@pytest.mark.parametrize('kind', ['alias', 'accession'])
def test_valid_core_token_does_not_imply_configured_offline_resolution(tmp_path, kind):
    selected = job(tmp_path, 'entry')
    row = binding(selected, variant('entry'))
    other = deepcopy(selected)
    token = 'controlled-alias' if kind == 'alias' else 'SRR0000000'
    other['operation']['parameters']['database_selection']['inputs'][0].update(kind=kind, value=token)
    other['vdb_context_request']['source_inputs'][0]['selected_input'] = {'kind': kind, 'value': token}
    validate_native_blast_utility_job(other)
    assert native_blast_utility_binding_accepts_job(row, other) is False
    descriptor, = native_blast_utility_tool_contracts([row], resource_kind='local', resource_id='selected')
    assert not Draft202012Validator(descriptor['input_schema']).is_valid(
        requested_job_from_native_blast_utility(other))


def test_multiple_selected_variants_share_one_actual_operation_name(tmp_path):
    rows = []
    for _, mode in VDB_MODES:
        selection = 'entry' if mode == 'extract_sequences' else mode
        row = binding(job(tmp_path, selection), variant(selection))
        row['variants'] = [variant(s, source, filtered) for s, source, filtered in CASES
            if ('extract_sequences' if s not in {'info', 'paths', 'paths_all'} else s) == mode]
        rows.append(row)
    assert sum(len(r['variants']) for r in rows) == 20
    descriptors = native_blast_utility_tool_contracts(rows, resource_kind='local', resource_id='selected')
    assert [d['name'] for d in descriptors] == ['native.' + '.'.join(pair) for pair in VDB_MODES]
    assert len(descriptors) == 4
    assert validate_native_blast_utility_bindings(rows) == rows
    assert native_blast_utility_tool_contracts([], resource_kind='local', resource_id='selected') == []


@pytest.mark.parametrize('resource', ['hpc', 'api'])
def test_local_descriptors_do_not_claim_an_unimplemented_resource(tmp_path, resource):
    row = binding(job(tmp_path, 'entry'), variant('entry'))
    with pytest.raises(ValueError, match='configured_local_resource_required'):
        native_blast_utility_tool_contracts([row], resource_kind=resource, resource_id='unbound')


def test_binding_validation_is_detached_and_does_not_read_or_execute(tmp_path, monkeypatch):
    selected = job(tmp_path, 'entry')
    row = binding(selected, variant('entry'))
    from pathlib import Path
    import subprocess
    def forbidden(*args, **kwargs):
        raise AssertionError('pure tool information attempted file access or execution')
    monkeypatch.setattr(Path, 'open', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    original = deepcopy(row)
    validated = validate_native_blast_utility_bindings([row])
    descriptor, = native_blast_utility_tool_contracts(validated, resource_kind='local', resource_id='selected')
    assert native_blast_utility_binding_accepts_job(row, selected)
    validated[0]['molecules'].append('protein')
    descriptor['input_schema'].clear()
    assert row == original
