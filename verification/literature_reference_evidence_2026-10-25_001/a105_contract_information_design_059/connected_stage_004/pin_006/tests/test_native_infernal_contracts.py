"""Selected job identity and native argv/format relationships, without execution."""
from copy import deepcopy
import builtins
from pathlib import Path
import socket
import subprocess

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.native_infernal_contracts import (
    compile_native_infernal_job, operand_contract, output_contract,
    native_infernal_digest, requested_job_from_infernal, validate_native_infernal_job,
    validate_native_infernal_requested_job,
)
from gene_annotation_episode.native_infernal_tool_info import (
    native_infernal_tool_contracts, native_infernal_tool_information,
)


def job_for(program, *, table_format=None):
    required, _ = operand_contract(program)
    operands = []
    for role, fmt in required.items():
        path = '/source/models.cm' if role == 'models' else '/source/sequences.fa'
        if role.startswith('models_'):
            path = '/source/models.cm.' + role.removeprefix('models_')
        operands.append({'role': role, 'path': path, 'format': fmt,
            'sha256': '1' * 64, 'size_bytes': 10, 'artifact_ref': None})
    outputs, _ = output_contract(program)
    return {'version': 'native_infernal_job_v1', 'program': program,
        'software': {'executable': '/software/' + program, 'sha256': '2' * 64,
            'engine_version': '1.1.5'}, 'environment': {}, 'operands': operands,
        'operand_bindings': [], 'options': ['--cpu', '0'],
        'outputs': [{'role': role, 'format': fmt, 'relative_path': 'out/' + role}
            for role, fmt in outputs.items()],
        'table_format': table_format if table_format is not None else (
            None if program == 'cmalign' else 3), 'metadata': {}, 'grading_parameters': {}}


@pytest.mark.parametrize('program,table_format', [
    ('cmsearch', 1), ('cmsearch', 3), ('cmscan', 1), ('cmscan', 2),
    ('cmscan', 3), ('cmalign', None)])
def test_compilation_preserves_selected_operands_and_original_request(program, table_format):
    job = job_for(program, table_format=table_format)
    original = deepcopy(job)
    staged = {row['role']: row['path'].replace('/source/', '/attempt/inputs/')
              for row in job['operands']}
    compiled = compile_native_infernal_job(job, input_paths=staged, output_directory='/attempt')
    assert compiled['argv'][0:3] == ['/software/' + program, '--cpu', '0']
    assert compiled['argv'][-2:] == ['/attempt/inputs/models.cm', '/attempt/inputs/sequences.fa']
    assert compiled['outputs'] == job['outputs']
    if program == 'cmalign':
        assert '--fmt' not in compiled['argv']
        assert compiled['argv'][compiled['argv'].index('--sfile') + 1] == '/attempt/out/scores'
    else:
        assert compiled['argv'][compiled['argv'].index('--fmt') + 1] == str(table_format)
        assert compiled['argv'][compiled['argv'].index('--tblout') + 1] == '/attempt/out/tblout'
        assert ('--tformat' if program == 'cmsearch' else '--qformat') in compiled['argv']
    requested = requested_job_from_infernal(job)
    assert validate_native_infernal_requested_job(requested) == requested
    requested['argv'][-1] = '/substituted/sequence.fa'
    with pytest.raises(ValueError, match='compiler_mismatch'):
        validate_native_infernal_requested_job(requested)
    assert job == original


def test_contract_functions_do_not_read_files_or_run_work(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('a pure selected-job contract performed I/O')
    for target, name in [(builtins, 'open'), (Path, 'open'), (Path, 'read_bytes'),
                         (subprocess, 'Popen'), (socket, 'socket')]:
        monkeypatch.setattr(target, name, forbidden)
    job = job_for('cmscan')
    request = requested_job_from_infernal(job)
    assert validate_native_infernal_requested_job(request) == request
    binding = {'program': job['program'], 'software': job['software']}
    entries = native_infernal_tool_information([binding], resource_kind='local', resource_id='machine')
    assert set(entries[0]) == {'name', 'description', 'resources', 'instructions'}


@pytest.mark.parametrize('path', ['../escaped', '/absolute', 'out/../escaped',
    'out//file', 'inputs/new', 'bundle.json', '.bundle.json.writing',
    '.native-infernal-owner.json', 'out\nfile'])
def test_outputs_cannot_overwrite_inputs_or_escape_attempt(path):
    job = job_for('cmsearch')
    job['outputs'][0]['relative_path'] = path
    with pytest.raises(ValueError, match='path'):
        validate_native_infernal_job(job)


def test_pressed_companions_require_the_same_original_and_staged_prefix():
    job = job_for('cmscan')
    job['operands'][-1]['path'] = '/other/index.i1p'
    with pytest.raises(ValueError, match='pressed_input_association'):
        validate_native_infernal_job(job)
    job = job_for('cmscan')
    paths = {row['role']: row['path'] for row in job['operands']}
    paths['models_i1m'] = '/different/model.i1m'
    with pytest.raises(ValueError, match='staged_pressed_association'):
        compile_native_infernal_job(job, input_paths=paths)


def test_global_and_interleaved_alignment_respect_native_output_constraints():
    job = job_for('cmalign')
    job['options'] += ['-g', '--ileaved']
    argv = compile_native_infernal_job(job)['argv']
    assert '-g' in argv and '--ileaved' in argv
    assert '--outformat' not in argv
    job['outputs'].append({'role': 'local_ends', 'format': 'cmalign_elfile', 'relative_path': 'out/el'})
    with pytest.raises(ValueError, match='global_alignment_has_no_EL_output'):
        compile_native_infernal_job(job)


def test_cmscan_overlap_information_has_explicit_clan_file_and_format():
    job = job_for('cmscan', table_format=2)
    job['options'].append('--oclan')
    with pytest.raises(ValueError, match='clan_input_required'):
        compile_native_infernal_job(job)
    job['operands'].append({'role': 'clanin', 'path': '/source/clans.txt', 'format': 'text',
        'sha256': '3' * 64, 'size_bytes': 4, 'artifact_ref': None})
    argv = compile_native_infernal_job(job)['argv']
    assert argv[argv.index('--clanin') + 1] == '/source/clans.txt'
    job['table_format'] = 3
    with pytest.raises(ValueError, match='require_format2'):
        compile_native_infernal_job(job)


@pytest.mark.parametrize('options', [
    ['--cpu', '-1'], ['--cpu', '1.5'], ['--cpu'], ['--cpu', '0', '--cpu', '1'],
    ['--tblout', '/elsewhere'], ['--smxsize', '.1'], ['--incE', 'nan']])
def test_invalid_option_operands_are_not_repaired_or_coerced(options):
    job = job_for('cmsearch')
    job['options'] = options
    with pytest.raises(ValueError, match='native_infernal_'):
        compile_native_infernal_job(job)


@pytest.mark.parametrize('value', [[], {}, True, 0, 'invented'])
def test_grading_parameters_require_the_declared_population_value(value):
    job = job_for('cmsearch')
    job['grading_parameters'] = {'hit_scope': value}
    with pytest.raises(ValueError, match='grading_parameters_invalid'):
        validate_native_infernal_job(job)


def test_tool_information_is_bound_to_the_actual_software_and_resource():
    job = job_for('cmalign')
    binding = {'program': 'cmalign', 'software': job['software']}
    contract, = native_infernal_tool_contracts([binding], resource_kind='local', resource_id='machine')
    request = requested_job_from_infernal(job)
    validator = Draft202012Validator(contract['input_schema'])
    assert validator.is_valid(request)
    request['native_infernal']['software']['sha256'] = '4' * 64
    assert not validator.is_valid(request)
    assert contract['invocation_route'] == {'kind': 'commission', 'routes': [
        {'entry_role': 'launch', 'resource_id': 'machine', 'resource_role': 'launch_local'}]}
    with pytest.raises(ValueError, match='resource_binding_unfinished'):
        native_infernal_tool_contracts([binding], resource_kind='hpc', resource_id='unbound')


def test_original_job_digest_preserves_list_order_and_rejects_nonfinite_data():
    assert native_infernal_digest({'a': 1, 'b': [2, 3]}) == native_infernal_digest({'b': [2, 3], 'a': 1})
    assert native_infernal_digest({'a': [2, 3]}) != native_infernal_digest({'a': [3, 2]})
    with pytest.raises(ValueError, match='finite_json'):
        native_infernal_digest({'measurement': float('nan')})


def test_original_record_ordinal_is_not_coerced_from_float():
    job = job_for('cmsearch')
    job['operand_bindings'] = [{'operand_role': 'sequences', 'record_ordinal': 1.0,
        'native_name': 'sequence', 'native_accession': None, 'subject_ref': None, 'reference_ref': None}]
    with pytest.raises(ValueError, match='input_record_binding_conflict'):
        validate_native_infernal_job(job)
