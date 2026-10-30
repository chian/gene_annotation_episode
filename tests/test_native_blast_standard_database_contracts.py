"""Synthetic standard database contract examples; no native search executes."""
from copy import deepcopy
import builtins
import os
from pathlib import Path
import socket
import subprocess

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import native_blast_standard_database_contracts as c
from gene_annotation_episode.native_blast_database_metadata import (
    metadata_schema_registry, validate_native_blast_database_metadata_payload)


def identity(path):
    return {'path': path, 'sha256': 'a' * 64, 'size_bytes': 12, 'artifact_ref': None}


def database(kind='blast_protein_sequence'):
    source = {'source_ref': 'synthetic_source', 'pointer': '/preparation'}
    ident = {'namespace': 'synthetic', 'value': 'target', 'version': None, 'release': None,
        'scope': None, 'preparation_type': 'sequence_database', 'source': source}
    paths = ['/selected/db/target']
    prefix = 'p' if kind == 'blast_protein_sequence' else 'n'
    manifest = {'version': 'native_blast_standard_prepared_database_manifest_v1', 'database_key': 'target',
        'kind': kind, 'identity': ident, 'native_paths': paths,
        'files': [{'path': paths[0] + '.' + prefix + suffix, 'sha256': 'b' * 64, 'size_bytes': 23}
                  for suffix in ['hr', 'in', 'sq']],
        'preparation': {'method': 'publisher_package', 'preparation_type': 'sequence_database',
            'software': {'name': 'synthetic preparation', 'version': None, 'executable_sha256': None},
            'argv': None, 'source': source, 'input_manifest': None, 'receipt': identity('/selected/receipt')},
        'metadata_manifests': [], 'access': {'mode': 'prepared_local', 'offline_configuration': None},
        'inventory_complete': True}
    return {'database_key': 'target', 'role': 'target', 'kind': kind, 'identity': ident,
        'native_paths': paths, 'manifest_file': identity('/selected/manifest'), 'manifest': manifest}


def job_for(program='blastp', query='sequence', fmt='json15'):
    return {'version': 'native_blast_standard_database_job_v1', 'program': program, 'mode': 'database',
        'software': {'executable': '/selected/bin/' + program, 'sha256': 'c' * 64, 'engine_version': '2.17.0+'},
        'environment': {'EXPLICIT': 'selected'}, 'inputs': [{'input_key': 'query', 'role': 'query_' + query,
            'format': 'fasta' if query == 'sequence' else 'scoremat_asn_text', **identity('/selected/query')}],
        'query': {'kind': query, 'input_key': 'query'},
        'databases': [database('blast_protein_sequence' if program in {'blastp', 'blastx'} else 'blast_nucleotide_sequence')],
        'options': [], 'outputs': [
            {'output_key': role, 'role': role, 'path_kind': 'file', 'relative_path': role + '.txt', 'format': 'text',
             'fields': [], 'delimiter': None, 'required': True} for role in ['stdout', 'stderr']
        ] + [{'output_key': 'report', 'role': 'primary_report', 'path_kind': 'file', 'relative_path': 'report',
              'format': fmt, 'fields': [] if fmt == 'json15' else ['qseqid', 'sseqid', 'bitscore'],
              'delimiter': None, 'required': True}],
        'metadata_inputs': [], 'grading_parameters': {'sequence_database_model': None}}


def compiled(job, **kw):
    return c.compile_standard_blast_database_argv(job,
        input_paths=kw.get('input_paths', {r['input_key']: r['path'] for r in job['inputs']}),
        database_paths=kw.get('database_paths', {r['database_key']: r['native_paths'] for r in job['databases']}),
        output_directory=kw.get('output_directory', '.'))


def forbid_io(monkeypatch):
    def fail(*a, **kw):
        pytest.fail('pure port attempted filesystem/process/network access')
    for obj, name in [(builtins, 'open'), (Path, 'open'), (Path, 'resolve'), (os, 'stat'),
                      (os, 'listdir'), (subprocess, 'run'), (subprocess, 'Popen'),
                      (socket, 'socket'), (socket, 'getaddrinfo')]:
        monkeypatch.setattr(obj, name, fail)


@pytest.mark.parametrize('program,query', [(p, q) for p in c.PROGRAMS for q in
    (['sequence', 'pssm'] if p == 'tblastn' else ['sequence'])])
@pytest.mark.parametrize('fmt', ['json15', 'tabular6', 'tabular7'])
def test_exact_selected_argv_all_programs_and_formats_pure(monkeypatch, program, query, fmt):
    job = job_for(program, query, fmt)
    job['options'] = ['-evalue', '0.0100', '-num_threads', '2', '-soft_masking', 'false']
    original = deepcopy(job)
    forbid_io(monkeypatch)
    assert c.validate_standard_blast_database_job(job) == job
    flag = '-in_pssm' if query == 'pssm' else '-query'
    outfmt = '15' if fmt == 'json15' else ('6' if fmt == 'tabular6' else '7') + ' qseqid sseqid bitscore'
    assert compiled(job) == [job['software']['executable'], *job['options'], flag, '/selected/query',
        '-db', '/selected/db/target', '-outfmt', outfmt, '-out', 'report']
    request = c.requested_job_from_standard_blast_database(job)
    assert c.validate_standard_blast_database_requested_job(request) == request
    Draft202012Validator(c.NATIVE_BLAST_STANDARD_DATABASE_REQUESTED_JOB_SCHEMA).validate(request)
    request['native_blast_standard_database']['query']['input_key'] = 'changed'
    assert job == original


@pytest.mark.parametrize('program,units', [('blastn', ('nt', 'nt', 'nt')), ('blastp', ('aa', 'aa', 'aa')),
    ('blastx', ('nt', 'aa', 'aa')), ('tblastn', ('aa', 'nt', 'aa')), ('tblastx', ('nt', 'nt', 'aa'))])
def test_public_program_geometry_matches_actual_alias_context(monkeypatch, program, units):
    forbid_io(monkeypatch)
    spec = c.standard_blast_database_program_spec(program)
    Draft202012Validator(c.STANDARD_BLAST_DATABASE_PROGRAM_SPEC_SCHEMA).validate(spec)
    assert tuple(spec[k] for k in ['query_coordinate_unit', 'reference_coordinate_unit', 'alignment_coordinate_unit']) == units
    assert spec['program_contexts']['sequence']['geometry_program'] == program
    assert spec['native_program_aliases']['sequence'] == [program]
    if program == 'tblastn':
        assert spec['native_program_aliases']['pssm'] == ['psitblastn']
    spec['admitted_options'].clear()
    assert c.standard_blast_database_program_spec(program)['admitted_options']


@pytest.mark.parametrize('program,options', [
    ('blastn', ['-task', 'dc-megablast', '-template_type', 'coding', '-template_length', '18', '-dust', '20 64 1', '-strand', 'minus']),
    ('blastp', ['-task', 'blastp-fast', '-seg', '12 2.2 2.5', '-matrix', 'BLOSUM62', '-comp_based_stats', '3']),
    ('blastx', ['-query_gencode', '33', '-mt_mode', '2', '-num_threads', '2', '-sum_stats', 'true']),
    ('tblastn', ['-db_gencode', '11', '-max_intron_length', '0', '-word_size', '2', '-use_sw_tback']),
    ('tblastx', ['-strand', 'both', '-query_gencode', '11', '-db_gencode', '33', '-num_threads', '4']),
])
def test_mode_specific_options_preserve_tokens_and_order(program, options):
    job = job_for(program); job['options'] = options
    assert compiled(job)[1:1 + len(options)] == options
    selected = c.validate_standard_blast_database_options(program, options, query_kind='sequence')
    assert selected[options[0]] == options[1]
    if '-use_sw_tback' in options:
        assert selected['-use_sw_tback'] is None


@pytest.mark.parametrize('program,options,query,code', [
    ('tblastn', ['-query_loc', '1-2'], 'pssm', 'invalid_option_operand'),
    *[('tblastx', [flag] + ([] if flag in {'-ungapped', '-use_sw_tback'} else ['1']), 'sequence', 'unsupported_option')
      for flag in ['-task', '-gapopen', '-gapextend', '-ungapped', '-mt_mode', '-comp_based_stats', '-use_sw_tback']],
    ('blastp', ['-mt_mode', '1'], 'sequence', 'required_option'),
    ('blastn', ['-template_length', '16'], 'sequence', 'required_option'),
    ('blastp', ['-culling_limit', '1', '-best_hit_overhang', '.1'], 'sequence', 'conflicting_options'),
    ('blastp', ['-culling_limit', '0', '-best_hit_score_edge', '.1'], 'sequence', 'conflicting_options'),
    ('blastp', ['-evalue', 'inf'], 'sequence', 'invalid_option_operand'),
    ('blastp', ['-num_threads', '0'], 'sequence', 'invalid_option_operand'),
    ('blastn', ['-word_size', '3'], 'sequence', 'invalid_option_operand'),
    ('blastp', ['-word_size', '1'], 'sequence', 'invalid_option_operand'),
    ('blastp', ['-dbsize', str(2**63)], 'sequence', 'invalid_option_operand'),
    ('blastp', ['-searchsp', '-1'], 'sequence', 'invalid_option_operand'),
    ('blastx', ['-query_gencode', '8'], 'sequence', 'invalid_option_operand'),
    ('tblastn', ['-db_gencode', '32'], 'sequence', 'invalid_option_operand'),
    ('blastp', ['-matrix', '/untracked/matrix'], 'sequence', 'invalid_option_operand'),
    ('blastp', ['-evalue', '1', '-evalue', '2'], 'sequence', 'duplicate_option'),
    ('blastp', ['-evalue'], 'sequence', 'option_operand_required'),
])
def test_closed_option_rejections(program, options, query, code):
    with pytest.raises(ValueError, match=code):
        c.validate_standard_blast_database_options(program, options, query_kind=query)


@pytest.mark.parametrize('flag', ['-query', '-in_pssm', '-db', '-out', '-outfmt', '-remote', '-subject', '-subject_loc',
    '-entrez_query', '-import_search_strategy', '-export_search_strategy', '-gilist', '-negative_gilist', '-seqidlist',
    '-negative_seqidlist', '-taxids', '-negative_taxids', '-taxidlist', '-negative_taxidlist', '-ipglist', '-negative_ipglist',
    '-db_soft_mask', '-db_hard_mask', '-filtering_db', '-window_masker_db', '-window_masker_taxid', '-use_index', '-index_name',
    '-html', '-num_descriptions', '-num_alignments', '-line_length', '-sorthits', '-sorthsps', '-in_msa', '-num_iterations'])
def test_no_raw_path_resource_rendering_or_iteration_escape(flag):
    with pytest.raises(ValueError, match='(compiler_owned|forbidden|unsupported)_option'):
        c.validate_standard_blast_database_options('blastp', [flag, '/untracked'], query_kind='sequence')


@pytest.mark.parametrize('delimiter', [None, '\t', '@', ',', '|'])
def test_explicit_selected_table_layout_no_injection(delimiter):
    job = job_for('blastn', fmt='tabular7')
    job['outputs'][2].update(delimiter=delimiter, fields=['sseqid', 'qseqid', 'qcovus'])
    result = compiled(job)
    assert result[result.index('-outfmt') + 1] == '7' + ('' if delimiter in {None, '\t'} else ' delim=' + delimiter) + ' sseqid qseqid qcovus'
    assert 'qseq' not in result[result.index('-outfmt') + 1].split()


@pytest.mark.parametrize('change', [lambda j: j['outputs'][2].update(delimiter=' '),
    lambda j: j['outputs'][2].update(delimiter='é'), lambda j: j['outputs'][2].update(delimiter='\n'),
    lambda j: j['outputs'][2].update(fields=['qseqid', 'sseqid', 'std']),
    lambda j: j['outputs'][2].update(fields=['qseqid', 'bitscore']),
    lambda j: j['outputs'][2].update(fields=['qseqid', 'sseqid', 'qcovus'])])
def test_invalid_table_contracts_fail(change):
    job = job_for(fmt='tabular6'); change(job)
    with pytest.raises(ValueError): c.validate_standard_blast_database_job(job)


@pytest.mark.parametrize('program', c.PROGRAMS)
def test_wrong_target_kind_fails(program):
    job = job_for(program)
    job['databases'] = [database('blast_nucleotide_sequence' if program in {'blastp', 'blastx'} else 'blast_protein_sequence')]
    with pytest.raises(ValueError, match='program_database_role_conflict'): c.validate_standard_blast_database_job(job)


def test_metadata_registry_is_exact_and_public_validator_accepts_real_standard_job(monkeypatch):
    job = job_for()
    payload = {'schema': 'native_blast_database_sequence_metadata_v1', 'documents': [], 'searches': []}
    descriptor = {'input_key': 'meta', 'consumer': 'sequence_database', 'schema_id': payload['schema'],
        'artifact_ref': 'artifact_meta', 'sha256': 'd' * 64, 'size_bytes': 12, 'origin': 'original_job_input'}
    job['inputs'].append({'input_key': 'meta', 'role': 'metadata', 'format': 'json', **identity('/selected/meta')})
    job['metadata_inputs'] = [{k: descriptor[k] for k in ['input_key', 'consumer', 'schema_id']}]
    catalog = {'descriptor': descriptor, 'documents': [], 'primary_reports': [],
        'bundle_source_ref': 'source_bundle', 'bundle_artifact_ref': 'artifact_bundle'}
    old = metadata_schema_registry()
    forbid_io(monkeypatch)
    assert c.standard_blast_database_metadata_registry() == [r for r in old if r['consumer'] in {'query_identity', 'sequence_database'}]
    assert c.validate_standard_blast_database_job(job) == job
    result = validate_native_blast_database_metadata_payload(payload, descriptor=descriptor, document_catalog=catalog, job=job)
    assert result['status'] == 'valid' and result['normalized']['searches'] == []
    assert job['version'] == 'native_blast_standard_database_job_v1'


@pytest.mark.parametrize('change', [lambda j: j.update(mode='pairwise'), lambda j: j.update(extra='undeclared'),
    lambda j: j['query'].update(kind='msa'), lambda j: j['query'].update(msa_master_record_ordinal=0),
    lambda j: j['inputs'][0].update(size_bytes=True), lambda j: j['inputs'][0].update(path='/a/../b'),
    lambda j: j['outputs'][2].update(relative_path='../escape'), lambda j: j['outputs'][2].update(relative_path='stdout.txt/child'),
    lambda j: j['outputs'][2].update(required=False), lambda j: j['databases'][0]['manifest'].update(inventory_complete=False),
    lambda j: j['databases'][0]['manifest'].update(database_key='other'),
    lambda j: j['grading_parameters'].update(sequence_database_model={'temperature_bits': True}),
    lambda j: j['grading_parameters'].update(sequence_database_model={'temperature_bits': float('nan')}),
    lambda j: j['grading_parameters'].update(sequence_database_model={'temperature_bits': 0}),
    lambda j: j['grading_parameters'].update(sequence_database_model={'temperature_bits': 10**1000}),
    lambda j: j['grading_parameters'].update(sequence_database_model={'function_priors': {}}),
    lambda j: j['grading_parameters'].update(sequence_database_model={'function_priors': {'f': 0}}),
    lambda j: j['grading_parameters'].update(sequence_database_model={'function_priors': {'f': True}}),
    lambda j: j['grading_parameters'].update(sequence_database_model={'function_priors': {'f': -1}}),
    lambda j: j['grading_parameters'].update(sequence_database_model={'invented_weight': 1})])
def test_closed_relationship_and_model_type_rejections(change):
    job = job_for(); change(job)
    with pytest.raises(ValueError): c.validate_standard_blast_database_job(job)


@pytest.mark.parametrize('key', sorted(c.RESERVED_ENVIRONMENT))
def test_producer_environment_is_not_overridden(key):
    job = job_for(); job['environment'][key] = '/elsewhere'
    with pytest.raises(ValueError, match='producer_owned_environment'): c.validate_standard_blast_database_job(job)


def test_multiple_selected_prefixes_preserve_one_explicit_population():
    job = job_for(); db = job['databases'][0]
    db['native_paths'].append('/selected/db/other')
    db['manifest']['files'].extend([{**r, 'path': r['path'].replace('/target.', '/other.')} for r in list(db['manifest']['files'])])
    assert compiled(job)[4] == '/selected/db/target /selected/db/other'
    with pytest.raises(ValueError, match='selected_database_paths_mismatch'):
        compiled(job, database_paths={'target': ['/unselected/db']})


def test_non_json_and_cyclic_values_rejected():
    cyclic = []; cyclic.append(cyclic)
    for bad in [cyclic, {1: 'nonstring'}, (1, 2), float('inf')]:
        job = job_for(); job['grading_parameters']['sequence_database_model'] = bad
        with pytest.raises(ValueError, match='finite_json_required'): c.validate_standard_blast_database_job(job)


@pytest.mark.parametrize('query_kind', [None, [], {}, True, 'msa'])
def test_direct_options_port_invalid_query_kind_has_stable_failure(query_kind):
    with pytest.raises(ValueError, match='native_blast_standard_database_program_query_kind_conflict'):
        c.validate_standard_blast_database_options('tblastn', [], query_kind=query_kind)
