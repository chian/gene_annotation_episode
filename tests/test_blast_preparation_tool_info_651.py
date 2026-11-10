"""Pure binding checks using explicitly synthetic operands; no native commands.

The reused 649 fixtures create controlled bytes only. These checks establish
configuration/schema/runtime parity, not native validity or a full Workflow.
"""
import ast
from copy import deepcopy
import hashlib
from itertools import product
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.native_blast_utility_contracts import (
    LEGACY_MODES, PREPARATION_MODES, NATIVE_BLAST_UTILITY_REQUESTED_JOB_SCHEMA,
    native_blast_utility_job_schema, requested_job_from_native_blast_utility,
    validate_native_blast_utility_job,
)
from gene_annotation_episode.native_blast_utility_tool_info import (
    native_blast_utility_binding_accepts_job, native_blast_utility_tool_contracts,
    validate_native_blast_utility_bindings,
)
from test_native_blast_preparation_649 import preparation_job, supplied, output, entry
from test_native_blast_utility_producer_628 import job_fixture


VARIANTS = {
    'convert_gi_list': [{}],
    'convert_seqid_list': [{'database_binding': value} for value in ('unbound', 'bound')],
    'inspect_seqid_list': [{}],
    'create_subset_alias': [{'restriction_kind': kind, 'input_format': fmt} for kind, fmt in (
        ('gi_list', 'text'), ('gi_list', 'gi_list_binary'), ('seqid_list', 'text'),
        ('seqid_list', 'seqid_list_binary'), ('taxid_list', 'text'), ('oid_masks', None))],
    'aggregate_databases': [{'classic_source': classic, 'vdb_source': vdb}
        for classic, vdb in product((None, 'inline', 'file'), repeat=2)
        if classic is not None or vdb is not None],
    'aggregate_volumes': [{}],
    'create_megablast_index': [{'input_format': fmt, 'old_style_index': old, 'legacy': legacy}
        for fmt, old, legacy in product(('fasta', 'blastdb'), (False, True), (False, True))
        if old or fmt == 'blastdb'],
    'show_filters': [{}],
    'create_profile_database': [{'profile_type': kind, 'input_format': fmt}
        for kind, fmt in product(('rps', 'delta', 'cobalt'), ('pssm_asn1_text', 'pssm_asn1_binary'))],
}
CASES = [(pair, variant) for pair in PREPARATION_MODES for variant in VARIANTS[pair[1]]]
PACKET = Path(__file__).resolve().parents[1] / 'verification/tool_graders_blast_preparation_tool_info_2026-10-28_651'


def software(program):
    return {'executable': '/configured/' + program, 'sha256': 'a' * 64, 'engine_version': 'fixture-only'}


def molecule(pair, variant):
    mode = pair[1]
    if mode in {'convert_gi_list', 'inspect_seqid_list'} or (
            mode == 'convert_seqid_list' and variant['database_binding'] == 'unbound'):
        return 'unknown'
    return 'protein' if mode == 'create_profile_database' else 'dna'


def binding(pair, variant):
    return {'program': pair[0], 'mode': pair[1], 'software': software(pair[0]),
            'molecules': [molecule(pair, variant)], 'variants': [deepcopy(variant)]}


def selected_job(tmp_path, pair, variant):
    mode = pair[1]
    job = preparation_job(tmp_path, mode,
        bound=variant.get('database_binding') == 'bound',
        old=variant.get('input_format') == 'fasta',
        profile_type=variant.get('profile_type', 'rps'),
        binary=variant.get('input_format') == 'pssm_asn1_binary')
    job['software'] = software(pair[0])
    p = job['operation']['parameters']
    if mode == 'create_subset_alias':
        kind, fmt = variant['restriction_kind'], variant['input_format']
        if kind == 'oid_masks':
            p['restriction'] = {'kind': kind, 'value': 1}
            job['inputs'] = []
        else:
            p['restriction'] = {'kind': kind, 'occurrence_id': 'ids', 'format': fmt}
            job['inputs'][0]['format'] = fmt
    elif mode == 'aggregate_databases':
        databases = job['databases']
        job['inputs'], job['databases'], job['materializations']['list_files'] = [], [], []
        for ordinal, name in enumerate(('classic', 'vdb')):
            source = variant[name + '_source']
            p[name + '_list'] = None
            if source is None:
                continue
            db = databases[ordinal]
            if name == 'vdb':
                manifest = db['manifest']
                manifest['version'] = 'native_blast_prepared_database_manifest_v1'
                manifest['kind'] = db['kind'] = 'vdb'
                manifest['identity']['preparation_type'] = 'unknown'
                manifest['preparation']['preparation_type'] = 'vdb'
                manifest['native_paths'] = db['native_paths'] = [str(Path(manifest['files'][0]['path']).parent)]
                # Declared synthetic custody, not an applied offline configuration.
                encoded = json.dumps(manifest, sort_keys=True).encode()
                db['manifest_file'].update(sha256=hashlib.sha256(encoded).hexdigest(), size_bytes=len(encoded))
            job['databases'].append(db)
            key = db['database_key']
            e = entry(0, key, key, line=1 if source == 'file' else None)
            p[name + '_list'] = {'source': source, 'entries': [e]}
            if source == 'file':
                input_key = name + '-list'
                job['inputs'].append(supplied(tmp_path, input_key, 'database_list', 'text', (key + '\n').encode()))
                p[name + '_list']['input_occurrence_id'] = input_key
                job['materializations']['list_files'].append({'input_key': input_key,
                    'relative_path': 'selected/' + input_key, 'grammar': 'blast_database_lines',
                    'entries': [{'ordinal': 0, 'line_number': 1, 'token_ordinal': 0, 'original_token': key,
                        'target': {'kind': 'database', 'database_key': key, 'native_path_index': 0}}]})
    elif mode == 'create_megablast_index':
        p['legacy'] = variant['legacy']
        if variant['old_style_index'] and variant['input_format'] == 'blastdb':
            p.update(old_style_index=True, output_prefix='result/old-db')
            job['materializations']['database_copies'] = []
            job['outputs'][2] = output('index', 'index_family', 'result/old-db',
                                      'blast_index_family', population='prefix_members')
    job['operation']['input_occurrence_ids'] = [r['input_key'] for r in job['inputs']]
    return validate_native_blast_utility_job(job)


@pytest.mark.parametrize('pair,variant', CASES)
def test_every_variant_has_exact_descriptor_and_acceptance_parity(tmp_path, pair, variant):
    selected = binding(pair, variant)
    descriptor = native_blast_utility_tool_contracts([selected], resource_kind='local', resource_id='chosen')[0]
    validator = Draft202012Validator(descriptor['input_schema'])
    for index, other_variant in enumerate(VARIANTS[pair[1]]):
        job = selected_job(tmp_path / str(index), pair, other_variant)
        request = requested_job_from_native_blast_utility(job)
        expected = other_variant == variant
        assert native_blast_utility_binding_accepts_job(selected, job) is expected
        assert validator.is_valid(request) is expected
    assert descriptor['name'] == 'native.' + '.'.join(pair)
    assert descriptor['resources'] == 'local'
    assert descriptor['invocation_route']['routes'] == [
        {'entry_role': 'launch', 'resource_id': 'chosen', 'resource_role': 'launch_local'}]


def test_mixed_legacy_and_preparation_rows_only_expose_selected_pairs():
    legacy = [{'program': p, 'mode': m, 'software': software(p), 'molecules': ['dna', 'protein']}
              for p, m in LEGACY_MODES]
    new = []
    for pair in PREPARATION_MODES:
        variants = VARIANTS[pair[1]]
        row = binding(pair, variants[0])
        row['variants'] = deepcopy(variants)
        row['molecules'] = list(dict.fromkeys(molecule(pair, v) for v in variants))
        new.append(row)
    rows = legacy + new
    assert sum(len(row['variants']) for row in new) == 32
    assert validate_native_blast_utility_bindings(rows) == rows
    descriptors = native_blast_utility_tool_contracts(rows, resource_kind='local', resource_id='selected-local')
    assert [d['name'] for d in descriptors] == ['native.' + r['program'] + '.' + r['mode'] for r in rows]
    assert len(descriptors) == 14
    assert native_blast_utility_tool_contracts([], resource_kind='local', resource_id='selected-local') == []
    assert len(native_blast_utility_tool_contracts(new[:1], resource_kind='local', resource_id='one')) == 1


@pytest.mark.parametrize('pair', LEGACY_MODES)
def test_legacy_descriptors_are_exactly_unchanged(tmp_path, pair):
    saved = json.loads((PACKET / 'LEGACY_INFORMATION_001.json').read_text())
    before = (PACKET / 'TOOL_INFO_BEFORE.py.txt').read_bytes()
    assert hashlib.sha256(before).hexdigest() == saved['source_sha256']
    # Literal source text only; no historical implementation executes.
    ast.parse(before)
    row = {'program': pair[0], 'mode': pair[1], 'software': software(pair[0]), 'molecules': ['dna', 'protein']}
    schema = deepcopy(NATIVE_BLAST_UTILITY_REQUESTED_JOB_SCHEMA)
    job_schema = native_blast_utility_job_schema(program=pair[0], mode=pair[1])
    job_schema['properties']['software'] = {'const': row['software']}
    job_schema['properties']['operation']['allOf'].append({'properties': {'molecule': {'enum': row['molecules']}}})
    schema['properties']['native_blast_utility'] = job_schema
    expected = {'name': 'native.' + '.'.join(pair), 'description': saved['_DESCRIPTIONS'][pair[1]],
        'resources': 'local', 'instructions': saved['_INSTRUCTIONS'][pair[1]] + saved['suffix'],
        'input_schema': schema, 'invocation_route': {'kind': 'commission', 'routes': [
            {'entry_role': 'launch', 'resource_id': 'legacy', 'resource_role': 'launch_local'}]}}
    assert native_blast_utility_tool_contracts([row], resource_kind='local', resource_id='legacy') == [expected]
    job = job_fixture(tmp_path, pair[1]); job['software'] = software(pair[0])
    assert native_blast_utility_binding_accepts_job(row, job)
    assert Draft202012Validator(expected['input_schema']).is_valid(requested_job_from_native_blast_utility(job))


@pytest.mark.parametrize('mode,bad', [
    ('convert_gi_list', {'unknown': True}),
    ('convert_seqid_list', {'database_binding': None}),
    ('create_subset_alias', {'restriction_kind': 'taxid_list', 'input_format': 'seqid_list_binary'}),
    ('create_subset_alias', {'restriction_kind': 'oid_masks', 'input_format': 'text'}),
    ('create_subset_alias', {'restriction_kind': 'gi_list', 'input_format': None}),
    ('aggregate_databases', {'classic_source': None, 'vdb_source': None}),
    ('aggregate_databases', {'classic_source': 'automatic', 'vdb_source': None}),
    ('create_megablast_index', {'input_format': 'fasta', 'old_style_index': False, 'legacy': True}),
    ('create_megablast_index', {'input_format': 'blastdb', 'old_style_index': 1, 'legacy': False}),
    ('create_megablast_index', {'input_format': 'blastdb', 'old_style_index': True, 'legacy': 0.0}),
    ('create_profile_database', {'profile_type': 'rps', 'input_format': 'text'}),
    ('create_profile_database', {'profile_type': 'automatic', 'input_format': 'pssm_asn1_text'}),
])
def test_invalid_variant_combinations_are_not_configured(mode, bad):
    pair = next(p for p in PREPARATION_MODES if p[1] == mode)
    row = binding(pair, VARIANTS[mode][0]); row['variants'] = [bad]
    with pytest.raises(ValueError): validate_native_blast_utility_bindings([row])


@pytest.mark.parametrize('change', ['missing', 'empty', 'duplicate', 'unknown_key', 'molecule_unknown',
                                  'molecule_duplicate', 'bad_pair', 'program_type', 'nan', 'infinity'])
def test_missing_unknown_and_duplicate_binding_values_fail(change):
    row = binding(('makembindex', 'show_filters'), {})
    if change == 'missing': row.pop('variants')
    elif change == 'empty': row['variants'] = []
    elif change == 'duplicate': row['variants'] = [{}, {}]
    elif change == 'unknown_key': row['resources'] = 'all'
    elif change == 'molecule_unknown': row['molecules'] = ['unknown']
    elif change == 'molecule_duplicate': row['molecules'] = ['dna', 'dna']
    elif change == 'bad_pair': row['program'] = 'blastdb_aliastool'
    elif change == 'program_type': row['program'] = []
    else: row['variants'] = [{'unselected': float('nan' if change == 'nan' else 'inf')}]
    with pytest.raises(ValueError): validate_native_blast_utility_bindings([row])


def test_duplicate_rows_and_new_fields_on_legacy_are_rejected():
    row = binding(('makembindex', 'show_filters'), {})
    with pytest.raises(ValueError): validate_native_blast_utility_bindings([row, deepcopy(row)])
    legacy = {'program': 'blastdbcmd', 'mode': 'info', 'software': software('blastdbcmd'), 'molecules': ['dna']}
    with pytest.raises(ValueError): validate_native_blast_utility_bindings([{**legacy, 'variants': [{}]}])
    with pytest.raises(ValueError): validate_native_blast_utility_bindings([{**legacy, 'molecules': ['unknown']}])
    with pytest.raises(ValueError): validate_native_blast_utility_bindings({'bindings': [row]})


@pytest.mark.parametrize('pair,variant', CASES)
def test_molecule_configuration_respects_each_shared_operation(pair, variant):
    row = binding(pair, variant)
    invalid = 'dna' if row['molecules'] == ['unknown'] else 'unknown'
    row['molecules'] = [invalid]
    with pytest.raises(ValueError): validate_native_blast_utility_bindings([row])
    if pair[0] in {'makembindex', 'makeprofiledb'}:
        row['molecules'] = ['protein' if pair[0] == 'makembindex' else 'dna']
        with pytest.raises(ValueError): validate_native_blast_utility_bindings([row])


def test_bound_unbound_molecules_and_selected_variants_remain_coupled(tmp_path):
    pair = ('blastdb_aliastool', 'convert_seqid_list')
    row = binding(pair, {'database_binding': 'unbound'})
    row['variants'].append({'database_binding': 'bound'})
    with pytest.raises(ValueError): validate_native_blast_utility_bindings([row])
    row['molecules'] = ['unknown', 'dna', 'protein']
    descriptor = native_blast_utility_tool_contracts([row], resource_kind='local', resource_id='list')[0]
    for i, variant in enumerate(row['variants']):
        job = selected_job(tmp_path / str(i), pair, variant)
        assert native_blast_utility_binding_accepts_job(row, job)
        assert Draft202012Validator(descriptor['input_schema']).is_valid(requested_job_from_native_blast_utility(job))


@pytest.mark.parametrize('changed', ['executable', 'sha256', 'engine_version', 'molecule', 'pair'])
def test_exact_software_molecule_and_pair_are_required(tmp_path, changed):
    pair = ('blastdb_aliastool', 'create_subset_alias'); variant = VARIANTS[pair[1]][0]
    job = selected_job(tmp_path, pair, variant); row = binding(pair, variant)
    if changed == 'molecule': row['molecules'] = ['protein']
    elif changed == 'pair': row = binding(('makembindex', 'show_filters'), {})
    else: row['software'][changed] = {'executable': '/other/aliastool', 'sha256': 'b' * 64,
                                     'engine_version': None}[changed]
    descriptor = native_blast_utility_tool_contracts([row], resource_kind='local', resource_id='exact')[0]
    assert not native_blast_utility_binding_accepts_job(row, job)
    assert not Draft202012Validator(descriptor['input_schema']).is_valid(requested_job_from_native_blast_utility(job))


@pytest.mark.parametrize('mode', ['convert_seqid_list', 'create_subset_alias', 'aggregate_databases',
                                 'aggregate_volumes', 'create_profile_database'])
def test_explicit_empty_v2_title_stays_in_descriptor_and_selected_request(tmp_path, mode):
    pair = next(p for p in PREPARATION_MODES if p[1] == mode); variant = VARIANTS[mode][0]
    job = selected_job(tmp_path, pair, variant); job['operation']['parameters']['title'] = ''
    row = binding(pair, variant)
    request = requested_job_from_native_blast_utility(job)
    assert '' in request['argv']
    assert native_blast_utility_binding_accepts_job(row, job)
    descriptor = native_blast_utility_tool_contracts([row], resource_kind='local', resource_id='empty-title')[0]
    assert Draft202012Validator(descriptor['input_schema']).is_valid(request)


def test_validators_are_pure_and_return_detached_values(tmp_path, monkeypatch):
    import builtins
    import socket
    import subprocess
    pair = ('blastdb_aliastool', 'aggregate_databases'); variant = VARIANTS[pair[1]][-1]
    job = selected_job(tmp_path, pair, variant); row = binding(pair, variant)
    before = deepcopy((row, job))
    def forbidden(*args, **kwargs): pytest.fail('binding performed IO or execution')
    for obj, key in ((builtins, 'open'), (Path, 'open'), (Path, 'resolve'),
                     (subprocess, 'run'), (subprocess, 'Popen'), (socket, 'socket')):
        monkeypatch.setattr(obj, key, forbidden)
    assert native_blast_utility_binding_accepts_job(row, job)
    descriptor = native_blast_utility_tool_contracts([row], resource_kind='local', resource_id='pure')[0]
    descriptor['input_schema']['properties']['native_blast_utility']['properties']['software']['const']['sha256'] = 'c' * 64
    detached = validate_native_blast_utility_bindings([row]); detached[0]['variants'][0]['classic_source'] = None
    assert (row, job) == before
    wrong = deepcopy(job); wrong['operation']['parameters']['classic_list']['entries'][0]['ordinal'] = True
    with pytest.raises(ValueError): native_blast_utility_binding_accepts_job(row, wrong)


@pytest.mark.parametrize('kind,resource_id', [('hpc', 'unconfigured'), ('api', 'unconfigured'), ('local', ''), ('local', None)])
def test_descriptors_do_not_invent_resource_bindings(kind, resource_id):
    row = binding(('makembindex', 'show_filters'), {})
    with pytest.raises(ValueError): native_blast_utility_tool_contracts([row], resource_kind=kind, resource_id=resource_id)


def test_actual_practical_admission_matches_descriptor_for_bound_and_unbound_variant(tmp_path):
    from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
    pair = ('makeprofiledb', 'create_profile_database')
    variant = {'profile_type': 'rps', 'input_format': 'pssm_asn1_text'}
    job = selected_job(tmp_path, pair, variant)
    request = requested_job_from_native_blast_utility(job)
    policy = {'memory_bytes': 20 * 1024 ** 3, 'scratch_bytes': 4 * 1024 ** 3}
    assignment = {'resource_kind': 'local', 'resource_id': 'configured-local',
        'workspace': str(tmp_path), 'requested_job': request, 'constraints': {'allocation': policy}}
    for selected, accepted in [(variant, True),
            ({'profile_type': 'rps', 'input_format': 'pssm_asn1_binary'}, False)]:
        row = binding(pair, selected)
        assert (row['program'], row['mode'], row['software'], row['molecules']) == (
            job['operation']['program'], job['operation']['mode'], job['software'], [job['operation']['molecule']])
        backend = LocalPracticalOperations({'kind': 'local', 'workspace': str(tmp_path),
            'policy': policy, 'native_blast_utility': [row]})
        descriptor = native_blast_utility_tool_contracts([row], resource_kind='local', resource_id='configured-local')[0]
        assert Draft202012Validator(descriptor['input_schema']).is_valid(request) is accepted
        if accepted:
            assert backend.validate_assignment(assignment) is None
        else:
            with pytest.raises(ValueError, match='native_blast_utility_program_mode_software_molecule_variant_not_bound'):
                backend.validate_assignment(assignment)
