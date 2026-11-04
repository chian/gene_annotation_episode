"""Synthetic association/hand arithmetic and retained-native provider evidence."""
from copy import deepcopy
from contextlib import ExitStack
import builtins
import hashlib
import inspect
import io
import json
from pathlib import Path
import socket
import subprocess
from unittest.mock import patch

import pytest

from gene_annotation_episode import phylogeny_formats as formats
from gene_annotation_episode import phylogeny_raxml_inputs as raxml
from gene_annotation_episode import bvbrc_codon_tree_native as codon_native
from gene_annotation_episode import bvbrc_phylogeny_common_inputs as inputs
from gene_annotation_episode import bvbrc_phylogeny_common_contracts as contracts
from gene_annotation_episode import bvbrc_phylogeny_common_grader as grader

ROOT = Path('/home/chia/repos/gene_annotation_episode')
NATIVE = ROOT / 'verification/tool_graders_bvbrc_phylogeny_boundaries_2026-10-24'
EVIDENCE = ROOT / 'verification/tool_graders_bvbrc_phylogeny_implementation_2026-10-24/provider-common-verification'


def artifact(data, name):
    return {'raw_artifact_ref': name, 'source_ref': name + '/source', 'sha256': hashlib.sha256(data).hexdigest()}


def evidence(value, name='synthetic/fact'):
    data = json.dumps(value, sort_keys=True).encode()
    return {'content': {'source_ref': name + '/source', 'artifact_field': 'artifact_ref', 'artifact_ref': name,
            'sha256': hashlib.sha256(data).hexdigest(), 'byte_count': len(data)}, 'pointer': ''}


def read(data, name, reader, **options):
    ref = artifact(data, name)
    functions = {'newick': formats.parse_newick, 'aligned_fasta': formats.parse_aligned_fasta,
                 'relaxed_phylip': formats.parse_relaxed_phylip, 'phyloxml': formats.parse_phyloxml,
                 'raxml_partitions': formats.parse_raxml_partitions, 'raxml_run_log': raxml.parse_raxml_run_log,
                 'codon_membership': codon_native.parse_codon_membership,
                 'codon_family_statistics': codon_native.parse_codon_family_statistics}
    return {'read_id': name + '/read', 'artifact': ref, 'reader': {'reader': reader, **options},
            'result': functions[reader](data, artifact=ref, **options)}


def populations():
    return {k: [] for k in contracts.POPULATION_KEYS}


def run():
    return {'original_task_id': None, 'source_revision': None, 'settings': [], 'commands': [], 'engines': [], 'conflicts': [], 'completeness': 'unknown'}


def joins(provider='gene_tree'):
    result = {key: [] for key in ('input_rows', 'tip_rows', 'feature_genomes', 'functions', 'function_equivalences', 'taxa', 'display_tips', 'transformations', 'residues', 'organismal_tips')}
    if provider == 'codon_tree':
        result['family_blocks'] = []
    return result


def fixture(*, matrix=b'>q\nA-CX\n>q\nATCX\n>c\nATGX\n>d\nAT-X\n', tree=b'((q:-1,q:0)0:2,(c:3,d:4)50:5);', provider='gene_tree'):
    reads = []
    if matrix is not None:
        reads.append(read(matrix, 'synthetic/alignment', 'aligned_fasta', id_rule='first_whitespace_token', encoding='ascii'))
    if tree is not None:
        reads.append(read(tree, 'synthetic/tree', 'newick', dialect='newick', allow_multiple=False))
    store = {'alignments': [], 'tree_documents': [], 'partitions': [], 'phyloxml': [], 'source_records': [], 'native_tables': []}
    for item in reads:
        if item['result']['value'] is not None:
            store['alignments' if item['reader']['reader'] == 'aligned_fasta' else 'tree_documents'].append(item['result']['value'])
    aid = store['alignments'][0]['alignment_id'] if store['alignments'] else None
    tid = store['tree_documents'][0]['trees'][0]['tree_id'] if store['tree_documents'] and store['tree_documents'][0]['trees'] else None
    analysis = {'analysis_id': 'primary', 'mode': 'gene_tree' if provider == 'gene_tree' else 'core_genome_codon_protein', 'raw_tree_id': tid, 'phyloxml_tree_id': None, 'native_engine_observation_ids': [], 'output_role_evidence': []}
    if provider == 'gene_tree':
        analysis.update(locus_ids=['locus'], aligned_document_id=aid)
    else:
        analysis.update(final_alignment_id=aid, partition_document_id=None, supported_tree_id=None, rooted_derivative_tree_id=None, display_tree_id=None, membership_document_id=None, family_stats_document_id=None, genome_counts_document_id=None, analysis_stats_document_id=None, bootstrap_tree_document_id=None, per_family_final_alignment_ids=[], explicit_family_matrix_id=None)
    docs = {'parsed': {'store': store, 'analyses': [analysis]}, 'raxml_runs': [], 'reads': reads}
    if provider == 'codon_tree':
        docs.update(membership=[], family_statistics=[], genome_counts=[], analysis_statistics=[])
    assembly = {'version': 'bvbrc_phylogeny_assembly_v1', 'analysis_id': 'primary', 'caller_populations': populations(), 'locus_bindings': [], 'genome_request_sets': [], 'family_matrices': [], 'historical_frequencies': [], 'model_associations': []}
    observed = run()
    if matrix is not None:
        observed['settings'] = [{'name': 'alphabet', 'value': 'protein', 'origin': 'observed', 'evidence': [evidence('protein')], 'location': None}]
    return {'provider': provider, 'documents': docs, 'inputs': (), 'observed_run': observed, 'joins': joins(provider), 'assembly': assembly,
            'parameters': {'source_dialect': 'retained_bvbrc_gene_tree', 'raw_tree_required_for_branch_facts': False} if provider == 'gene_tree' else {'source_dialect': 'retained_codon_trees', 'membership_dialect': 'pgfams_legacy', 'family_stats_dialect': None}}


def extracted(args):
    result = inputs.extract_common_fields(**args)
    assert result['value'] is not None, result
    common = result['value']; provider = args['provider']
    header = {'schema_version': 'bvbrc_gene_tree_sheet_v1', 'tool': 'C-L194-GeneTree', 'mode': 'gene_tree', 'loci': []} if provider == 'gene_tree' else {'schema_version': 'bvbrc_codon_tree_sheet_v1', 'tool': 'C-L193-CodonTree', 'mode': 'core_genome_codon_protein', 'genomes': [], 'families': [], 'models': []}
    return result, {**header, **common}


def parameters(sheet):
    result = {k: [] for k in contracts.COMMON_PARAMETER_KEYS}
    if sheet['populations']['alignments']:
        result['alignment_requests'] = [{'population_id': sheet['populations']['alignments'][0]['population_id'], 'alphabet': 'protein', 'case_policy': 'uppercase', 'pairs': [[0, 1]]}]
    if sheet['populations']['leaves']:
        result['tree_requests'] = [{'population_id': sheet['populations']['leaves'][0]['population_id'], 'branch_unit': 'native_unknown', 'pairs': []}]
    return result


def add_members(args):
    alignment = args['documents']['parsed']['store']['alignments'][0]
    bindings, subjects = [], []
    for i, row in enumerate(alignment['rows']):
        bid = f'file-{i}'; mid = 'q' if i < 2 else row['member_label']; sequence = row['sequence'].replace('-', '')
        binding = {'binding_id': bid, 'parameter_pointer': f'/sequences/{i}', 'kind': 'inline_parameter', 'content': None, 'workspace_path': None, 'inline_value': sequence, 'link_evidence': None,
                   'members': [{'member_id': mid, 'member_pointer': '', 'length': len(sequence), 'molecule': 'protein', 'sequence_sha256': hashlib.sha256(sequence.encode()).hexdigest(), 'evidence': None}]}
        bindings.append(binding)
        subject = {'kind': 'input_member', 'id': inputs.input_member_subject_id(bid, mid), 'source_record_id': f'anchor/{i}'}; subjects.append(subject)
        args['documents']['parsed']['store']['source_records'].append({'source_record_id': f'anchor/{i}', 'subject': subject, 'artifact': None, 'evidence': [], 'pointer': '', 'source_database': None, 'source_version': None})
        args['joins']['input_rows'].append({'alignment_id': alignment['alignment_id'], 'row_index': i, 'input_binding_id': bid, 'member_id': mid, 'locus_id': 'locus', 'transformation_id': None, 'evidence': []})
    args['inputs'] = tuple(bindings)
    return subjects


def guard_io():
    stack = ExitStack()
    def fail(*a, **k):
        raise AssertionError('I/O is disabled during extraction/calculation')
    for target in ('builtins.open', 'io.open', 'pathlib.Path.open', 'socket.socket', 'socket.create_connection', 'subprocess.run', 'subprocess.Popen'):
        stack.enter_context(patch(target, fail))
    return stack


def test_exact_public_signatures_and_keys():
    assert list(inspect.signature(inputs.extract_common_fields).parameters) == ['provider', 'documents', 'inputs', 'observed_run', 'joins', 'assembly', 'parameters']
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in inspect.signature(inputs.extract_common_fields).parameters.values())
    assert list(inspect.signature(contracts.validate_shared_fields).parameters) == ['sheet', 'provider']
    assert list(inspect.signature(inputs.input_member_subject_id).parameters) == ['input_binding_id', 'member_id']
    assert list(inspect.signature(grader.calculate_common_components).parameters) == ['sheet', 'provider', 'parameters']
    args = fixture(); result, sheet = extracted(args)
    assert set(result) == {'status', 'value', 'diagnostics'}
    assert set(result['value']) == contracts.COMMON_KEYS
    assert set(grader.calculate_common_components(sheet, provider='gene_tree', parameters=parameters(sheet))) == contracts.COMMON_COMPONENT_KEYS


@pytest.mark.parametrize('binding,member,expected', [('A', 'q', 'member/A/q'), ('B', 'q', 'member/B/q'), ('a/b%', 'é q', 'member/a%2Fb%25/%C3%A9%20q'), ('a~_.-', 'x/y', 'member/a~_.-/x%2Fy')])
def test_member_identity(binding, member, expected):
    assert inputs.input_member_subject_id(binding, member) == expected


def test_hand_arithmetic_negative_branch_and_native_zero_support():
    _, sheet = extracted(fixture()); result = grader.calculate_common_components(sheet, provider='gene_tree', parameters=parameters(sheet))
    alignment = result['alignments'][0]; tree = result['trees'][0]
    assert alignment['cell_count']['value'] == 16
    assert alignment['gap_cells']['value'] == 2 and alignment['gap_fraction']['value'] == 1 / 8
    assert alignment['canonical_cells']['value'] == 10 and alignment['ambiguity_cells']['value'] == 4
    assert alignment['sites'][2]['canonical_entropy_bits']['value'] == pytest.approx(0.9182958340544896)
    assert alignment['pairs'][0]['identity_fraction']['value'] == 1
    assert tree['branch_length_sum']['value'] == 13 and tree['branch_length_sum']['unit'] == 'native_unknown'
    assert any(o['field'] == 'branch_support_native' and o['value'] == 0 for o in sheet['native_measurements'])
    assert all(o['method'] == 'native_unknown' for o in sheet['support_observations'])
    assert any('support_method_unresolved' == r['reason_code'] for r in result['missing_requirements'])


def test_two_q_members_composition_and_distinct_taxon_denominators():
    args = fixture(); subjects = add_members(args)
    for i, function in enumerate(('A', 'A', 'B')):
        args['joins']['functions'].append({'assignment_id': f'function/{i}', 'subject': subjects[i], 'function_key': function, 'function_label': function, 'source_record_id': subjects[i]['source_record_id'], 'evidence': []})
        args['joins']['taxa'].append({'subject': subjects[i], 'taxon_id': ('X', 'X', 'Y')[i], 'rank': 'species', 'lineage': [], 'source_record_id': subjects[i]['source_record_id'], 'evidence': []})
    for kind, selected in (('composition', subjects), ('taxonomy', subjects[:3])):
        args['assembly']['caller_populations'][kind].append({'population_id': kind, 'unit': 'sequence_member', 'member_subjects': selected, 'assignment_completeness': 'unknown', 'membership_completeness': 'complete', 'evidence': []})
    _, sheet = extracted(args); p = parameters(sheet); p.update(composition_population_ids=['composition'], taxon_requests=[{'population_id': 'taxonomy', 'rank': 'species'}])
    result = grader.calculate_common_components(sheet, provider='gene_tree', parameters=p)
    composition, taxonomy = result['composition'][0], result['taxonomy'][0]
    assert composition['total_members']['value'] == 4
    assert composition['rows'][0]['fraction_all']['value'] == .5 and composition['rows'][0]['fraction_recorded']['value'] == 2 / 3
    assert taxonomy['known_members']['value'] == 3 and taxonomy['same_taxon_pair_fraction']['value'] == 1 / 3
    assert subjects[0]['id'] != subjects[1]['id']


@pytest.mark.parametrize('mutation,code', [
    (lambda a: a['documents']['parsed']['store']['source_records'][0]['subject'].update(id='member/file-1/q'), 'subject_anchor_conflict'),
    (lambda a: a['joins']['input_rows'][0].update(member_id='absent'), 'member_reference_unknown'),
    (lambda a: a['joins']['input_rows'][0].update(row_index=99), 'row_reference_unknown'),
    (lambda a: a['assembly'].update(analysis_id='wrong'), 'assembly_analysis_conflict'),
])
def test_wrong_associations_invalid(mutation, code):
    args = fixture(); add_members(args); mutation(args)
    result = inputs.extract_common_fields(**args)
    assert result['status'] == 'invalid' and result['value'] is None
    assert result['diagnostics'][0]['code'].endswith(code)


def test_full_assignment_registry_validated_before_population_filter():
    args = fixture(); subjects = add_members(args)
    args['joins']['functions'] = [{'assignment_id': 'bad', 'subject': subjects[-1], 'function_key': 'A', 'function_label': 'A', 'source_record_id': subjects[0]['source_record_id'], 'evidence': []}]
    result = inputs.extract_common_fields(**args)
    assert result['status'] == 'invalid' and result['diagnostics'][0]['code'].endswith('function_source_subject_conflict')


@pytest.mark.parametrize('matrix', [b'>a\nAAA\n>b\nAA\n', b'>a\nAAA\n>\n'])
def test_malformed_independent_matrix_retains_tree_and_original_errors(matrix):
    args = fixture(matrix=matrix); result, sheet = extracted(args)
    assert result['status'] == 'partial'
    first = args['documents']['reads'][0]['result']
    assert sheet['read_outcomes'][0]['status'] == first['status']
    assert sheet['read_outcomes'][0]['diagnostics'] == first['diagnostics']
    assert all(d['path'].startswith('/read_outcomes/') for d in sheet['qualifications'] if d['code'].startswith('phylogeny_'))
    p = parameters(sheet); p['alignment_requests'][0]['pairs'] = []
    result = grader.calculate_common_components(sheet, provider='gene_tree', parameters=p)
    assert result['trees'][0]['tip_count']['value'] == 4
    assert result['alignments'][0]['cell_count']['value'] is None


def test_missing_alignment_valid_tree_and_missing_coverage_members():
    _, tree_sheet = extracted(fixture(matrix=None))
    result = grader.calculate_common_components(tree_sheet, provider='gene_tree', parameters=parameters(tree_sheet))
    assert result['trees'][0]['tip_count']['value'] == 4
    assert any(r['reason_code'] == 'alignment_bytes_required' for r in result['missing_requirements'])
    _, sheet = extracted(fixture()); p = parameters(sheet); p['original_coverage_population_ids'] = [p['alignment_requests'][0]['population_id']]
    result = grader.calculate_common_components(sheet, provider='gene_tree', parameters=p)
    assert result['original_coverage'][0]['rows'] == []
    assert result['original_coverage'][0]['missing_requirements'][0]['reason_code'] == 'original_residue_map_required'


def test_original_coverage_requires_maps_and_retains_original_length():
    args = fixture(); add_members(args); _, sheet = extracted(args); p = parameters(sheet); p['original_coverage_population_ids'] = [p['alignment_requests'][0]['population_id']]
    result = grader.calculate_common_components(sheet, provider='gene_tree', parameters=p)
    assert [r['original_length']['value'] for r in result['original_coverage'][0]['rows']] == [3, 4, 4, 3]
    assert all(r['original_member_coverage']['value'] is None for r in result['original_coverage'][0]['rows'])
    alignment = args['documents']['parsed']['store']['alignments'][0]
    for join in args['joins']['input_rows']:
        offset = 0
        for col, symbol in enumerate(alignment['rows'][join['row_index']]['sequence']):
            args['joins']['residues'].append({'alignment_id': alignment['alignment_id'], 'row_index': join['row_index'], 'column_0based': col, 'staged_ungapped_position_0based': None if symbol == '-' else offset,
                'original_member': {'input_binding_id': join['input_binding_id'], 'member_id': join['member_id']}, 'original_interval_0based_half_open': None if symbol == '-' else [offset, offset + 1], 'strand': 'unknown', 'translation_table': None, 'transformation_id': None, 'evidence': []})
            offset += symbol != '-'
    _, sheet = extracted(args); result = grader.calculate_common_components(sheet, provider='gene_tree', parameters=p)
    assert all(r['original_member_coverage']['value'] == 1 for r in result['original_coverage'][0]['rows'])
    args['joins']['residues'][0]['original_interval_0based_half_open'] = [0, 3]
    assert inputs.extract_common_fields(**args)['status'] == 'invalid'


def test_reader_duplicate_equality_and_conflict():
    args = fixture(); args['documents']['reads'].append(deepcopy(args['documents']['reads'][0]))
    result, sheet = extracted(args)
    assert len(sheet['read_outcomes']) == 2
    args['documents']['reads'][-1]['result']['status'] = 'partial'
    result = inputs.extract_common_fields(**args)
    assert result['status'] == 'invalid' and result['diagnostics'][0]['code'].endswith('record_identity_conflict')


def test_invalid_reader_with_value_preserved():
    args = fixture(matrix=None, provider='codon_tree')
    native = read(b'PGFam\tgaps\tsum_squared_freq\tmean_squared_freq\tnum_pos\tnum_seqs\tworstSeqScoreused_in_tree\nPGF_a\t1\t2\n', 'synthetic/badstats', 'codon_family_statistics', dialect='current_missing_header_tab')
    assert native['result']['status'] == 'invalid' and native['result']['value'] is not None
    args['documents']['reads'].append(native); args['documents']['family_statistics'].append(native['result']['value']); args['documents']['parsed']['store']['native_tables'].append(native['result']['value']['table'])
    result, sheet = extracted(args)
    assert result['status'] == 'partial' and sheet['read_outcomes'][-1]['value_present']
    p = parameters(sheet)
    assert grader.calculate_common_components(sheet, provider='codon_tree', parameters=p)['trees'][0]['tip_count']['value'] == 4


def test_native_count_only_population_not_empty_membership():
    args = fixture(provider='codon_tree')
    native = read(b'PGFam\tgaps\tsum_squared_freq\tmean_squared_freq\tnum_pos\tnum_seqs\tworstSeqScoreused_in_tree\nPGF_a\t0\t2\t0.5\t4\t8\tna\tTrue\n', 'synthetic/stats', 'codon_family_statistics', dialect='current_missing_header_tab')
    assert native['result']['value'] is not None
    args['documents']['reads'].append(native); args['documents']['family_statistics'].append(native['result']['value']); args['documents']['parsed']['store']['native_tables'].append(native['result']['value']['table'])
    _, sheet = extracted(args)
    pop = sheet['populations']['native'][0]
    assert pop['observed_member_count'] == 8 and pop['observed_site_count'] == 4 and pop['members'] == [] and pop['membership_completeness'] == 'unknown'
    assert any(o['value'] == 0 and o['state'] == 'available' for o in sheet['native_measurements'])
    assert any(o['raw_token'] == 'na' and o['value'] is None for o in sheet['native_measurements'])


def test_generic_xml_and_root_zero_support_retained():
    args = fixture(matrix=None, tree=None)
    xml = read(b'<phyloxml><phylogeny><clade><confidence type="support">0</confidence><clade><name>A</name><branch_length>0</branch_length></clade><clade><name>B</name></clade></clade></phylogeny></phyloxml>', 'synthetic/xml', 'phyloxml')
    args['documents']['reads'] = [xml]; args['documents']['parsed']['store']['phyloxml'] = [xml['result']['value']]
    args['documents']['parsed']['analyses'][0]['phyloxml_tree_id'] = xml['result']['value']['trees'][0]['tree']['tree_id']
    _, sheet = extracted(args)
    support = [o for o in sheet['native_measurements'] if o['field'] == 'branch_support_native']
    assert len(support) == 1 and support[0]['value'] == 0 and support[0]['method'] == 'native_unknown'
    assert any(d['code'].endswith('xml_converter_zero_and_support_loss') for d in sheet['qualifications'])
    result = grader.calculate_common_components(sheet, provider='gene_tree', parameters=parameters(sheet))
    assert result['trees'][0]['tip_count']['value'] == 2 and result['trees'][0]['missing_branch_length_count']['value'] == 1


def test_reserved_population_namespace_rejected():
    args = fixture(); aid = args['documents']['parsed']['store']['alignments'][0]['alignment_id']
    args['assembly']['caller_populations']['alignments'] = [{'population_id': contracts._whole_id('primary', 'alignment', aid), 'alignment_id': aid, 'row_indices': [], 'columns_0based': [], 'completeness': 'complete', 'evidence': []}]
    assert inputs.extract_common_fields(**args)['diagnostics'][0]['code'].endswith('reserved_population_identity')


@pytest.mark.parametrize('mutate', [lambda s: s.update(extra=[]), lambda s: s.update(tool='C-L193-CodonTree'), lambda s: s.pop('assembly'), lambda s: s.update(loci={}), lambda s: s['populations']['leaves'][0]['node_indices'].pop(), lambda s: s['read_outcomes'].pop(), lambda s: s['read_outcomes'][0].update(extra=True)])
def test_saved_sheet_closed_validation(mutate):
    _, sheet = extracted(fixture()); mutate(sheet)
    with pytest.raises(ValueError):
        contracts.validate_shared_fields(sheet, provider='gene_tree')


def test_saved_fields_detached_and_no_mutation_with_io_disabled():
    args = fixture(); original = deepcopy(args)
    with guard_io():
        result, sheet = extracted(args); p = parameters(sheet)
        first = grader.calculate_common_components(sheet, provider='gene_tree', parameters=p)
        saved = json.loads(json.dumps({'sheet': sheet, 'parameters': p}, allow_nan=False))
        second = grader.calculate_common_components(saved['sheet'], provider='gene_tree', parameters=saved['parameters'])
        projection = contracts.validate_shared_fields(sheet, provider='gene_tree')
    assert first == second and args == original
    projection['documents']['analyses'][0]['analysis_id'] = 'changed'
    assert sheet['documents']['analyses'][0]['analysis_id'] == 'primary'


def test_unknown_requested_branch_unit_cannot_be_promoted():
    _, sheet = extracted(fixture()); p = parameters(sheet); p['tree_requests'][0]['branch_unit'] = 'expected_substitutions_per_model_site'
    result = grader.calculate_common_components(sheet, provider='gene_tree', parameters=p)
    assert result['trees'][0]['branch_length_sum']['value'] == 13
    assert result['trees'][0]['branch_length_sum']['unit'] == 'native_unknown'
    assert result['alignments'][0]['cell_count']['value'] == 16
    assert any(r['reason_code'] == 'branch_unit_unresolved' for r in result['missing_requirements'])


def test_requirement_registry_preserved_separately():
    _, sheet = extracted(fixture())
    sheet['missing_requirements'].append({'requirement_id': 'provider/locus', 'kind': 'scientific_metadata', 'role': 'locus_membership', 'source_refs': [], 'reason_code': 'gene_tree_locus_membership_unknown'})
    result = grader.calculate_common_components(sheet, provider='gene_tree', parameters=parameters(sheet))
    assert any(r['requirement_id'] == 'provider/locus' for r in result['missing_requirements'])


def test_retained_native_nine_row_alignment_and_tree():
    directory = NATIVE / 'official_example/test9_genome_dir'
    matrix_path = next(directory.glob('*.phy')); tree_path = next(directory.glob('RAxML_bestTree.*'))
    matrix = read(matrix_path.read_bytes(), 'retained/native_matrix', 'relaxed_phylip', layout='interleaved', continuation_ids='absent')
    tree = read(tree_path.read_bytes(), 'retained/native_tree', 'newick', dialect='newick', allow_multiple=False)
    args = fixture(matrix=None, tree=None, provider='codon_tree')
    args['documents']['reads'] = [matrix, tree]; args['documents']['parsed']['store']['alignments'] = [matrix['result']['value']]; args['documents']['parsed']['store']['tree_documents'] = [tree['result']['value']]
    analysis = args['documents']['parsed']['analyses'][0]; analysis['final_alignment_id'] = matrix['result']['value']['alignment_id']; analysis['raw_tree_id'] = tree['result']['value']['trees'][0]['tree_id']
    _, sheet = extracted(args); p = parameters(sheet); p['alignment_requests'][0]['alphabet'] = 'unknown'; p['alignment_requests'][0]['pairs'] = []
    with guard_io():
        result = grader.calculate_common_components(sheet, provider='codon_tree', parameters=p)
    assert result['alignments'][0]['member_count']['value'] == 9 and result['alignments'][0]['cell_count']['value'] == 137700
    assert result['alignments'][0]['gap_cells']['value'] == 17308 and result['alignments'][0]['gap_fraction']['value'] == 17308 / 137700
    assert result['trees'][0]['tip_count']['value'] == 9


@pytest.mark.parametrize('path', sorted((NATIVE / 'additional_sources/bvbrc_gene_tree/tests').glob('*.xml')))
def test_retained_native_xml(path):
    xml = read(path.read_bytes(), 'retained/' + path.name, 'phyloxml')
    args = fixture(matrix=None, tree=None); args['documents']['reads'] = [xml]; args['documents']['parsed']['store']['phyloxml'] = [xml['result']['value']]
    args['documents']['parsed']['analyses'][0]['phyloxml_tree_id'] = xml['result']['value']['trees'][0]['tree']['tree_id']
    _, sheet = extracted(args)
    with guard_io():
        result = grader.calculate_common_components(sheet, provider='gene_tree', parameters=parameters(sheet))
    assert result['trees'][0]['tip_count']['value'] == 17
    assert len(sheet['support_observations']) == 14
    assert {r['method'] for r in sheet['support_observations']} == {'native_unknown'}


@pytest.mark.parametrize('origin,with_evidence,conflicting', [('requested', True, False), ('observed', False, False), ('source_expected', True, False), ('observed', True, True)])
def test_unverified_and_conflicting_alphabet_preserves_literal_counts(origin, with_evidence, conflicting):
    args = fixture(); setting = args['observed_run']['settings'][0]
    setting['origin'] = origin; setting['evidence'] = [evidence('protein')] if with_evidence else []
    if conflicting:
        args['observed_run']['settings'].append({'name': 'alphabet', 'value': 'dna', 'origin': 'observed', 'evidence': [evidence('dna')], 'location': None})
    _, sheet = extracted(args); p = parameters(sheet); original = deepcopy(p)
    result = grader.calculate_common_components(sheet, provider='gene_tree', parameters=p)
    component = result['alignments'][0]
    assert component['gap_cells']['value'] == 2 and component['cell_count']['value'] == 16
    assert component['canonical_cells']['value'] is None and component['sites'][0]['symbol_counts'] == [{'symbol': 'A', 'count': 4}]
    assert any(row['reason_code'] == 'alphabet_required' for row in result['missing_requirements'])
    assert any(row['code'].endswith('observed_alphabet_conflict' if conflicting else 'requested_alphabet_unverified') for row in result['diagnostics'])
    assert p == original


def test_exact_mixed_partition_alphabet_populations():
    args = fixture(matrix=b'>a\nACLX\n>b\nATLX\n', provider='codon_tree'); args['observed_run']['settings'] = []
    partition = read(b'DNA, nucleotides = 1-2\nLGF, proteins = 3-4\n', 'synthetic/partitions', 'raxml_partitions', alignment_column_count=4)
    args['documents']['reads'].append(partition); args['documents']['parsed']['store']['partitions'] = [partition['result']['value']]
    analysis = args['documents']['parsed']['analyses'][0]; analysis['partition_document_id'] = partition['result']['value']['document_id']
    for pid, columns in [('dna', [0, 1]), ('protein', [2, 3]), ('mixed', [0, 1, 2, 3])]:
        args['assembly']['caller_populations']['alignments'].append({'population_id': pid, 'alignment_id': analysis['final_alignment_id'], 'row_indices': [0, 1], 'columns_0based': columns, 'completeness': 'complete', 'evidence': []})
    _, sheet = extracted(args); p = {k: [] for k in contracts.COMMON_PARAMETER_KEYS}
    p['alignment_requests'] = [{'population_id': pid, 'alphabet': alphabet, 'case_policy': 'literal', 'pairs': []} for pid, alphabet in [('dna', 'dna'), ('protein', 'protein'), ('mixed', 'dna')]]
    result = grader.calculate_common_components(sheet, provider='codon_tree', parameters=p)
    assert result['alignments'][0]['canonical_cells']['value'] == 4
    assert result['alignments'][1]['canonical_cells']['value'] == 2 and result['alignments'][1]['ambiguity_cells']['value'] == 2
    assert result['alignments'][2]['cell_count']['value'] == 8 and result['alignments'][2]['canonical_cells']['value'] is None


def transformation(args, *, before=None, after=None):
    alignment = args['documents']['parsed']['store']['alignments'][0]
    row = {'transformation_id': 'transform', 'kind': 'end_trim', 'input_members': [{'input_binding_id': 'file-0', 'member_id': 'q'}],
        'output_rows': [{'alignment_id': alignment['alignment_id'], 'row_index': 0}], 'before_header': None, 'after_label': None,
        'segment_id': None, 'locus_order': [], 'removed_alignment_columns_0based': None, 'before_sequence_sha256': before,
        'after_sequence_sha256': after, 'evidence': []}
    args['joins']['transformations'] = [row]; args['joins']['input_rows'][0]['transformation_id'] = 'transform'
    return row


def test_transform_exact_case_gapped_digests_and_null_multiple_operands():
    args = fixture(); add_members(args)
    row = transformation(args, before=args['inputs'][0]['members'][0]['sequence_sha256'], after=hashlib.sha256(b'A-CX').hexdigest())
    extracted(args)
    row['after_sequence_sha256'] = hashlib.sha256(b'ACX').hexdigest()
    assert inputs.extract_common_fields(**args)['diagnostics'][0]['code'].endswith('transformation_after_digest_conflict')
    row['after_sequence_sha256'] = hashlib.sha256(b'a-cx').hexdigest()
    assert inputs.extract_common_fields(**args)['status'] == 'invalid'
    row['after_sequence_sha256'] = None; row['input_members'].append({'input_binding_id': 'file-1', 'member_id': 'q'})
    assert inputs.extract_common_fields(**args)['diagnostics'][0]['code'].endswith('transformation_before_digest_ambiguous')
    row['before_sequence_sha256'] = None
    extracted(args)
    row['output_rows'].append({'alignment_id': row['output_rows'][0]['alignment_id'], 'row_index': 1}); row['after_sequence_sha256'] = hashlib.sha256(b'A-CX').hexdigest()
    assert inputs.extract_common_fields(**args)['diagnostics'][0]['code'].endswith('transformation_after_digest_ambiguous')
    row['after_sequence_sha256'] = None
    extracted(args)


def test_unknown_original_digest_cannot_be_replaced_by_assertion():
    args = fixture(); add_members(args); row = transformation(args, before='a' * 64)
    args['inputs'][0]['members'][0]['sequence_sha256'] = None
    assert inputs.extract_common_fields(**args)['diagnostics'][0]['code'].endswith('transformation_before_digest_conflict')
    row['before_sequence_sha256'] = None
    extracted(args)


def attach_log(args, *, mode='a', bad_version=False):
    body = ('This is RAxML version 8.2.9 released by source.\nRAxML was called as follows:\n\n'
        f'raxml -s input.fa -n run -f {mode} -m PROTGAMMALG -N 4 -T 2\n'
        'Alignment has 7 distinct alignment patterns\nFinal ML Optimization Likelihood: -3.25\n'
        + ('This is RAxML version 8.2.10 released by source.\n' if bad_version else '')
        + 'Overall execution time for full ML analysis: 1.0 secs\n').encode()
    log = read(body, 'synthetic/log', 'raxml_run_log', dialect='raxml_8')
    args['documents']['reads'].append(log); args['documents']['raxml_runs'].append(log['result']['value'])
    analysis = args['documents']['parsed']['analyses'][0]
    analysis['native_engine_observation_ids'] = [r['observation_id'] for r in log['result']['value']['observations']]
    analysis['output_role_evidence'] = [evidence({'analysis': 'primary', 'log': 'synthetic/log', 'tree': analysis['raw_tree_id']}, 'synthetic/analysis-map')]
    return log


def test_observed_log_merges_native_settings_and_preserves_requested_conflicts():
    args = fixture(); attach_log(args)
    args['observed_run']['settings'].append({'name': 'recipe', 'value': 'phyml', 'origin': 'requested', 'evidence': [], 'location': None})
    result, sheet = extracted(args)
    assert result['status'] == 'ok'
    assert any(r['name'] == 'recipe' and r['value'] == 'raxml' and r['origin'] == 'observed' for r in sheet['observed_run']['settings'])
    assert len(sheet['observed_run']['conflicts']) == 1
    assert {r['unit'] for r in sheet['native_measurements'] if r['field'] == 'branch_length'} == {'expected_substitutions_per_model_site'}
    assert {r['method'] for r in sheet['support_observations']} == {'rapid_bootstrap'}
    p = parameters(sheet); p['tree_requests'][0]['branch_unit'] = 'expected_substitutions_per_model_site'
    computed = grader.calculate_common_components(sheet, provider='gene_tree', parameters=p)
    support = [r['support_rescaled']['value'] for r in computed['trees'][0]['branches'] if r['native_support_observation_ids']]
    assert support == [0, .5]


def test_contradictory_native_engine_does_not_supply_method_or_unit():
    args = fixture(); log = attach_log(args, bad_version=True)
    assert log['result']['status'] == 'invalid' and log['result']['value'] is not None
    result, sheet = extracted(args)
    assert result['status'] == 'partial' and sheet['read_outcomes'][-1]['status'] == 'invalid'
    assert {r['unit'] for r in sheet['native_measurements'] if r['field'] == 'branch_length'} == {'native_unknown'}
    assert {r['method'] for r in sheet['support_observations']} == {'native_unknown'}
    assert any(r['value'] == -3.25 for r in sheet['native_measurements'])


def test_partial_forest_keeps_complete_tree_and_conditional_bootstrap_counts():
    args = fixture(tree=b'((A:1,B:1):1,(C:1,D:1):1);'); attach_log(args)
    forest = read(b'((A,B),(C,D));((A,B),(C,D));((A,C),(B,D));(A,B,C,D);BROKEN(', 'synthetic/forest', 'newick', dialect='newick', allow_multiple=True)
    assert forest['result']['status'] == 'partial'
    args['documents']['reads'].append(forest); args['documents']['parsed']['store']['tree_documents'].append(forest['result']['value'])
    reference = args['documents']['parsed']['store']['tree_documents'][0]['trees'][0]
    replicate_trees = forest['result']['value']['trees']; mappings = []
    reference_tips = {n['decoded_label']: n['node_index'] for n in reference['nodes'] if not n['child_indices']}
    for tree in replicate_trees:
        tips = {n['decoded_label']: n['node_index'] for n in tree['nodes'] if not n['child_indices']}
        mappings.append({'replicate_tree_id': tree['tree_id'], 'pairs': [{'reference_node_index': index, 'replicate_node_index': tips[label]} for label, index in reference_tips.items()]})
    args['assembly']['caller_populations']['bootstraps'] = [{'population_id': 'replicates', 'tree_ids': [t['tree_id'] for t in replicate_trees], 'expected_replicates': 5, 'completeness': 'partial', 'expected_count_evidence': [evidence(5)]}]
    result, sheet = extracted(args); assert result['status'] == 'partial'
    p = parameters(sheet); p['bootstrap_requests'] = [{'reference_tree_id': reference['tree_id'], 'replicate_population_id': 'replicates', 'tip_join': {'reference_tree_id': reference['tree_id'], 'mappings': mappings}, 'method': 'rapid_bootstrap'}]
    calculated = grader.calculate_common_components(sheet, provider='gene_tree', parameters=p)
    bootstrap = calculated['bootstrap'][0]
    assert bootstrap['supplied_replicates']['value'] == bootstrap['usable_replicates']['value'] == 4
    assert bootstrap['expected_replicates']['value'] == 5
    assert bootstrap['rows'][0]['frequency']['value'] == .5 and bootstrap['rows'][0]['frequency']['method'] == 'conditional_rapid_bootstrap_frequency'
    assert all(pop['completeness'] == 'complete' for pop in sheet['populations']['leaves'])
    p['bootstrap_requests'][0]['tip_join']['mappings'][0]['pairs'][0]['reference_node_index'] = 999
    with pytest.raises(ValueError):
        grader.calculate_common_components(sheet, provider='gene_tree', parameters=p)


def test_explicit_comparison_uses_supplied_join_and_saves_restricted_splits():
    args = fixture(tree=b'(((A,E),B),(C,D));'); subjects = add_members(args)
    organism = read(b'((A,C),(B,D));', 'synthetic/organism', 'newick', dialect='newick', allow_multiple=False)
    args['documents']['reads'].append(organism); args['documents']['parsed']['store']['tree_documents'].append(organism['result']['value'])
    left = args['documents']['parsed']['store']['tree_documents'][0]['trees'][0]; right = organism['result']['value']['trees'][0]
    left_tips = {n['decoded_label']: n['node_index'] for n in left['nodes'] if not n['child_indices']}; right_tips = {n['decoded_label']: n['node_index'] for n in right['nodes'] if not n['child_indices']}
    args['joins']['organismal_tips'] = [{'gene_tree_id': left['tree_id'], 'gene_node_index': left_tips[label], 'organismal_tree_id': right['tree_id'], 'organismal_node_index': right_tips[label], 'subject': subjects[i], 'evidence': []} for i, label in enumerate('ABCD')]
    _, sheet = extracted(args); p = parameters(sheet)
    p['comparisons'] = [{'comparison_id': 'restricted-four', 'gene_tree_id': left['tree_id'], 'organismal_tree_id': right['tree_id'], 'tip_pairs': deepcopy(args['joins']['organismal_tips'])}]
    result = grader.calculate_common_components(sheet, provider='gene_tree', parameters=p); comp = result['comparisons'][0]
    assert comp['matched_tips']['value'] == 4 and comp['rf']['value'] == 2 and comp['rf_fraction']['value'] == 1
    assert len(comp['omitted_gene_tips']) == 1 and comp['restricted_gene_splits'][0]['split_id'].startswith('restricted-four/gene/split/')
    p['comparisons'][0]['tip_pairs'].pop()
    with pytest.raises(ValueError, match='comparison_join_not_supplied'):
        grader.calculate_common_components(sheet, provider='gene_tree', parameters=p)


def test_duplicate_headers_do_not_create_dependence_and_explicit_source_does():
    args = fixture(); add_members(args); _, sheet = extracted(args)
    assert not sheet['dependence_groups']
    ev = evidence({'sequence': 'same-original'}, 'synthetic/original')
    # Unknown lengths/digests preserve the explicit same-original relationship;
    # final transformed row equality is a separate dependence kind.
    for member in [args['inputs'][0]['members'][0], args['inputs'][1]['members'][0]]:
        member.update(evidence=ev, length=None, sequence_sha256=None)
    _, sheet = extracted(args)
    groups = [g for g in sheet['dependence_groups'] if g['kind'] == 'shared_original_member']
    assert len(groups) == 1 and len(groups[0]['subject_ids']) == 2
    groups[0]['subject_ids'][1] = 'synthetic/alignment#alignment/row/3'
    with pytest.raises(ValueError, match='shared_original_dependence_conflict'):
        contracts.validate_shared_fields(sheet, provider='gene_tree')


def test_imports_resolve_only_to_owned_staging_modules():
    staging = Path(__file__).resolve().parents[1] / 'gene_annotation_episode'
    assert all(Path(module.__file__).resolve().parent == staging for module in (inputs, contracts, grader))


def test_missing_bootstrap_method_preserves_multiple_independent_requests():
    args = fixture(); tid = args['documents']['parsed']['analyses'][0]['raw_tree_id']
    args['assembly']['caller_populations']['bootstraps'] = [{'population_id': 'unknown-method-replicates', 'tree_ids': [], 'expected_replicates': None, 'completeness': 'unknown', 'expected_count_evidence': []}]
    _, sheet = extracted(args); p = parameters(sheet); p['tree_requests'][0]['branch_unit'] = 'expected_substitutions_per_model_site'
    p['bootstrap_requests'] = [{'reference_tree_id': tid, 'replicate_population_id': 'unknown-method-replicates', 'tip_join': {'reference_tree_id': tid, 'mappings': []}, 'method': 'rapid_bootstrap'}]
    result = grader.calculate_common_components(sheet, provider='gene_tree', parameters=p)
    assert result['alignments'][0]['cell_count']['value'] == 16 and result['trees'][0]['tip_count']['value'] == 4
    assert result['bootstrap'] == [] and len(sheet['support_observations']) == 2
    assert {r['reason_code'] for r in result['missing_requirements']} >= {'branch_unit_unresolved', 'bootstrap_method_unresolved'}
    p['bootstrap_requests'][0]['tip_join']['reference_tree_id'] = 'wrong-reference'
    with pytest.raises(ValueError, match='bootstrap_reference_conflict'):
        grader.calculate_common_components(sheet, provider='gene_tree', parameters=p)


def test_conflicting_bootstrap_method_is_explicit_without_losing_alignment():
    args = fixture(); attach_log(args); tid = args['documents']['parsed']['analyses'][0]['raw_tree_id']
    args['assembly']['caller_populations']['bootstraps'] = [{'population_id': 'replicates', 'tree_ids': [], 'expected_replicates': 0, 'completeness': 'complete', 'expected_count_evidence': [evidence(0)]}]
    _, sheet = extracted(args); p = parameters(sheet)
    p['bootstrap_requests'] = [{'reference_tree_id': tid, 'replicate_population_id': 'replicates', 'tip_join': {'reference_tree_id': tid, 'mappings': []}, 'method': 'rell_bootstrap'}]
    result = grader.calculate_common_components(sheet, provider='gene_tree', parameters=p)
    assert result['bootstrap'] == [] and result['alignments'][0]['cell_count']['value'] == 16
    assert any(d['code'].endswith('bootstrap_method_conflict') and d['severity'] == 'error' for d in result['diagnostics'])


def test_saved_native_value_and_method_tampering_rejected():
    _, sheet = extracted(fixture())
    support = sheet['support_observations'][0]; obs = next(o for o in sheet['native_measurements'] if o['observation_id'] == support['native_observation_id'])
    obs['value'] = 9
    with pytest.raises(ValueError, match='support_token_value_conflict'):
        contracts.validate_shared_fields(sheet, provider='gene_tree')
    obs['value'] = 0; obs['method'] = support['method'] = 'rapid_bootstrap'
    with pytest.raises(ValueError, match='support_method_provenance_unverified'):
        contracts.validate_shared_fields(sheet, provider='gene_tree')


def test_nucleotide_original_coverage_requires_explicit_strand_and_translation():
    args = fixture(matrix=b'>q\nM\n', tree=None); add_members(args)
    member = args['inputs'][0]['members'][0]; member.update(molecule='dna', length=3, sequence_sha256=hashlib.sha256(b'ATG').hexdigest())
    aid = args['documents']['parsed']['store']['alignments'][0]['alignment_id']
    tr = transformation(args); tr['kind'] = 'codon_gap_projection'
    args['joins']['residues'] = [{'alignment_id': aid, 'row_index': 0, 'column_0based': 0, 'staged_ungapped_position_0based': 0, 'original_member': {'input_binding_id': 'file-0', 'member_id': 'q'}, 'original_interval_0based_half_open': [0, 3], 'strand': 'unknown', 'translation_table': None, 'transformation_id': 'transform', 'evidence': []}]
    _, sheet = extracted(args); p = {k: [] for k in contracts.COMMON_PARAMETER_KEYS}; p['original_coverage_population_ids'] = [sheet['populations']['alignments'][0]['population_id']]
    result = grader.calculate_common_components(sheet, provider='gene_tree', parameters=p)
    assert result['original_coverage'][0]['rows'][0]['original_member_coverage']['value'] is None
    assert sheet['joins']['residues'][0]['original_interval_0based_half_open'] == [0, 3]
    args['joins']['residues'][0].update(strand='+', translation_table=11)
    _, sheet = extracted(args); result = grader.calculate_common_components(sheet, provider='gene_tree', parameters=p)
    assert result['original_coverage'][0]['rows'][0]['original_covered_positions']['value'] == 3
    assert result['original_coverage'][0]['rows'][0]['original_member_coverage']['value'] == 1
    args['joins']['residues'][0]['translation_table'] = 999
    assert inputs.extract_common_fields(**args)['diagnostics'][0]['code'].endswith('translation_table_invalid')


def test_shared_container_evidence_requires_exact_original_member_pointer():
    args = fixture(); add_members(args); ev = evidence({'members': ['ACX', 'ATCX']}, 'synthetic/container')
    first, second = args['inputs'][0]['members'][0], args['inputs'][1]['members'][0]
    first.update(evidence=ev, member_pointer='/members/0'); second.update(evidence=ev, member_pointer='/members/1')
    _, sheet = extracted(args)
    assert not any(g['kind'] == 'shared_original_member' for g in sheet['dependence_groups'])
    second['member_pointer'] = '/members/0'
    assert inputs.extract_common_fields(**args)['diagnostics'][0]['code'].endswith('shared_original_member_facts_conflict')
    second.update(length=first['length'], sequence_sha256=first['sequence_sha256'])
    _, sheet = extracted(args)
    assert len([g for g in sheet['dependence_groups'] if g['kind'] == 'shared_original_member']) == 1
    sheet['inputs'][1]['members'][0]['member_pointer'] = '/members/1'
    with pytest.raises(ValueError, match='shared_original_dependence_conflict'):
        contracts.validate_shared_fields(sheet, provider='gene_tree')
