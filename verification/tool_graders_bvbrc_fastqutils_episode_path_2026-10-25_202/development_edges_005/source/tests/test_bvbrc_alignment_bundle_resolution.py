"""Whole pure bundles with real retained native bytes and synthetic custody.

These fixtures do not claim a live AppService task or episode communication.
"""
from copy import deepcopy
import hashlib
import json
import math
import itertools
import re
from pathlib import Path

import pytest
import scipy
from jsonschema import Draft202012Validator

from gene_annotation_episode import bvbrc_alignment_bundle_contracts as c
from gene_annotation_episode import bvbrc_alignment_bundle_resolution as r

ROOT = Path(__file__).resolve().parents[1]
MSA_NATIVE = ROOT / 'verification/tool_graders_bvbrc_msa_metacats_boundaries_2026-10-25/native_examples'
META_NATIVE = ROOT / 'verification/tool_graders_bvbrc_metacats_native_execution_2026-10-25/cases'
BACKEND = {'name': 'scipy_chi2_integer_df_logtail_v1', 'version': scipy.__version__}


def slot(aid, sid):
    return {'analysis_id': aid, 'slot_id': sid}


class Fixture:
    def __init__(self, provider='msa', aid='analysis'):
        self.provider = provider; self.raw = {}; self.values = []
        app = 'MSA' if provider == 'msa' else 'MetaCATS'
        self.bundle = {'version': 'bvbrc_appservice_artifact_bundle_v1',
            'original_task': {'resource_id': 'synthetic-custody-api', 'task_id': 'synthetic-custody-task',
                'required_application_id': app, 'native_application_id': app, 'submitted_parameters': {},
                'submitted_start_parameters': {}, 'scheduler_returned_parameters': None, 'effective_parameters': None,
                'submission_receipt_ref': 'synthetic:submission', 'submission_operation_key': 'synthetic:operation:0',
                'submission_source_ref': 'synthetic:source'},
            'artifacts': [], 'input_bindings': [], 'query_bindings': [], 'supplied_scientific_metadata': [],
            'supplied_contents': [], 'acquisition_receipt_refs': [], 'requested_selector_sha256': '0' * 64,
            'status': 'ok', 'missing_requirements': [], 'diagnostics': []}
        self.parameters = {'version': c.VERSION, 'artifact_selection': [], 'analyses': [], 'multiplicity_families': []}
        self.add_plan(aid)

    def add_plan(self, aid):
        if self.provider == 'msa':
            analysis = {'analysis_id': aid, 'mode': 'ordinary_new_alignment', 'alignment_id': None,
                'frequency_table_id': None, 'consensus_alignment_id': None, 'tree_id': None,
                'full_xmfa_slot_id': None, 'xmfa_document_id': None, 'segment_ids': [], 'reference': None,
                'output_role_evidence': []}
        else:
            analysis = {'analysis_id': aid, 'mode': 'files', 'alignment_id': None, 'metadata_document_id': None,
                'category_ids': ['category'], 'adjusted_matrix_ids': [], 'chisq_table_ids': [], 'pair_table_ids': [],
                'raw_r_table_ids': [], 'output_role_evidence': []}
        plan = {'analysis': analysis, 'population_plans': [], 'scientific_inputs': [],
            'read_parameters': {'source_dialect': 'retained_bvbrc_' + self.provider},
            'calculation_parameters': {'version': 'bvbrc_' + self.provider + '_components_v1', 'requests': []}}
        self.parameters['analyses'].append(plan)
        return plan

    def plan(self, aid='analysis'):
        return next(p for p in self.parameters['analyses'] if p['analysis']['analysis_id'] == aid)

    def artifact(self, data, sid, reader, semantic='alignment', aid='analysis', role=None):
        name = aid + '/' + sid; ref = 'synthetic:artifact/' + name
        receipt = 'synthetic:acquisition/' + name
        artifact = {'role': role or name, 'source_ref': 'synthetic:source/' + name, 'raw_artifact_ref': ref,
            'sha256': hashlib.sha256(data).hexdigest(), 'byte_count': len(data),
            'workspace_object': {'path': '/synthetic/' + name, 'uuid': 'synthetic-object:' + name, 'type': 'file', 'metadata_receipt_ref': None},
            'task_association': {'kind': 'task_result_manifest', 'evidence_ref': 'synthetic:manifest', 'pointer': '',
                'task_id': self.bundle['original_task']['task_id'], 'output_path': '/synthetic/' + name,
                'output_uuid': 'synthetic-object:' + name, 'byte_version_status': 'current_bytes_observed', 'version_evidence': []},
            'transfer': {'receipt_ref': receipt, 'body_complete': True, 'requested_range': None, 'observed_range': None,
                'total_size': len(data), 'object_complete': 'yes'},
            'declared_format': {'format': reader['reader'] if reader else 'opaque', 'version': None,
                'mode': None, 'producer_source_ref': None, 'transformation_evidence': []}}
        self.raw[ref] = data; self.bundle['artifacts'].append(artifact)
        self.bundle['acquisition_receipt_refs'].append(receipt)
        self.parameters['artifact_selection'].append({'analysis_id': aid, 'slot_id': sid, 'semantic_role': semantic,
            'source': {'kind': 'acquired_role', 'bundle_role': artifact['role']}, 'reader': deepcopy(reader)})
        return artifact

    def scientific(self, role, value, aid='analysis'):
        data = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
        name = aid + '/supplied/' + role
        content = {'source_ref': 'synthetic:source/' + name, 'artifact_field': 'artifact_ref',
            'artifact_ref': 'synthetic:artifact/' + name, 'sha256': hashlib.sha256(data).hexdigest(), 'byte_count': len(data)}
        evidence = {'content': content, 'pointer': ''}
        self.bundle['supplied_scientific_metadata'].append(evidence)
        self.values.append({'evidence': evidence, 'value': deepcopy(value)})
        self.plan(aid)['scientific_inputs'].append({'role': role, 'evidence': evidence})
        return evidence

    def register_nested_evidence(self, value):
        if type(value) is dict:
            if set(value) == {'content', 'pointer'}:
                if value not in self.bundle['supplied_scientific_metadata']:
                    self.bundle['supplied_scientific_metadata'].append(deepcopy(value))
            else:
                for item in value.values(): self.register_nested_evidence(item)
        elif type(value) in (list, tuple):
            for item in value: self.register_nested_evidence(item)

    def original(self, data, sid, reader, semantic='original_sequences', aid='analysis'):
        artifact = self.artifact(data, sid, reader, semantic, aid)
        content = r._content(artifact); binding_id = aid + ':original:' + sid
        self.bundle['artifacts'].remove(artifact)
        self.bundle['supplied_contents'].append(content)
        self.bundle['original_task']['submitted_parameters'].setdefault('input', {})[binding_id] = '/synthetic/' + sid
        self.bundle['input_bindings'].append({'binding_id': binding_id, 'parameter_pointer': '/input/' + binding_id,
            'kind': 'retained_bytes', 'content': content, 'workspace_path': '/synthetic/' + sid,
            'inline_value': None, 'link_evidence': None, 'members': []})
        self.parameters['artifact_selection'][-1]['source'] = {'kind': 'original_input', 'input_binding_id': binding_id, 'content': content}
        return binding_id, artifact

    def resolve(self):
        return r.resolve_bundle(self.bundle, artifact_bytes=self.raw, supplied_values=self.values,
            parameters=self.parameters, provider=self.provider)

    def compose(self):
        resolved = self.resolve()
        compiler = r._Resolver(self.bundle, self.raw, self.values, self.parameters, self.provider)
        compiler.slots = {(v['analysis_id'], v['slot_id']): v for v in resolved['selections']}
        for row in resolved['analyses']:
            compiler.documents[row['analysis_id']] = row['documents']
        return [r._assemble(compiler, row) for row in resolved['analyses']], resolved, compiler

    def consume(self, fields):
        return r.consume_bundle(self.bundle, artifact_bytes=self.raw, supplied_values=self.values,
            requested_form=c.requested_form_schema(fields, provider=self.provider), parameters=self.parameters, provider=self.provider)


FASTA = {'reader': 'aligned_fasta', 'id_rule': 'first_whitespace_token', 'encoding': 'ascii'}
META_FASTA = {**FASTA, 'reader': 'metacats_input_fasta'}


def basic_fixture(provider='msa', data=b'>a\nAC\n>b\nAT\n', aid='analysis'):
    f = Fixture(provider, aid); f.artifact(data, 'alignment', FASTA if provider == 'msa' else META_FASTA, aid=aid)
    p = f.plan(aid); p['analysis']['alignment_id'] = slot(aid, 'alignment')
    p['population_plans'] = [{'kind': 'whole_alignment', 'population_id': 'whole', 'alignment': slot(aid, 'alignment')}]
    p['calculation_parameters']['requests'] = [{'kind': 'alignment', 'request_id': 'alignment', 'population_id': 'whole', 'alphabet': 'dna', 'case_policy': 'uppercase', 'pairs': [[0, 1]]}]
    return f


def msa_native_fixture(alphabet='dna'):
    f = basic_fixture(data=(MSA_NATIVE / alphabet / 'output.afa').read_bytes())
    f.artifact((MSA_NATIVE / alphabet / 'foma.table').read_bytes(), 'frequency',
        {'reader': 'msa_frequency', 'alphabet': alphabet, 'layout': 'current_without_reference', 'encoding': 'ascii'}, 'msa_frequency')
    f.artifact((MSA_NATIVE / alphabet / 'cons.fasta').read_bytes(), 'consensus', FASTA, 'consensus')
    p = f.plan(); p['analysis'].update(frequency_table_id=slot('analysis', 'frequency'), consensus_alignment_id=slot('analysis', 'consensus'))
    p['calculation_parameters']['requests'][0]['alphabet'] = alphabet
    p['calculation_parameters']['requests'].append({'kind': 'msa_entropy', 'request_id': 'entropy', 'population_id': 'whole',
        'alphabet': alphabet, 'case_policy': 'uppercase', 'terminal_gap': '-', 'observed_table_id': slot('analysis', 'frequency'),
        'native_rounding': 'binary64_fixed_2_ties_to_even'})
    return f


def meta_fixture(data=b'>a\nAC\n>b\nAT\n', metadata=b'id\tgroup\na\tB\nb\tC\n', aid='analysis'):
    f = basic_fixture('metacats', data, aid)
    f.artifact(metadata, 'metadata', {'reader': 'metacats_metadata', 'delimiter': 'tab', 'header': 'present', 'encoding': 'ascii'}, 'metadata', aid)
    p = f.plan(aid); p['analysis']['metadata_document_id'] = slot(aid, 'metadata')
    context = r._empty_metacats(aid)
    context['metadata_joins'] = [{'metadata': slot(aid, 'metadata'), 'id_column_index_0based': 0, 'alignment': slot(aid, 'alignment'),
        'alignment_identity': 'member_label', 'case_policy': 'preserve', 'duplicate_policy': 'retain_unresolved', 'evidence': []}]
    context['categories'] = [{'category_id': 'category', 'metadata': slot(aid, 'metadata'), 'metadata_column_index_0based': 1,
        'raw_heading_token': 'group', 'native_category_ordinal_1based': 1, 'native_output_stem': 'category', 'input_mode': 'files',
        'group_identity_rule': 'exact_category_value', 'evidence': []}]
    context['biological_group_populations'] = [{'kind': 'observed_metadata_groups', 'group_population_id': 'groups', 'category_id': 'category',
        'order': 'first_metadata_occurrence', 'include_metadata_only': True, 'evidence': []}]
    f.scientific('metacats_context', context, aid)
    groups = ['metacats_group:category/B', 'metacats_group:category/C']
    p['calculation_parameters']['requests'] += [
        {'kind': 'biological_group_counts', 'request_id': 'counts', 'population_id': 'whole', 'category_id': 'category',
            'group_population_id': 'groups', 'case_policy': 'preserve', 'terminal_gap_policy': 'exclude_terminal_dash', 'original_hash_policy': 'exclude_hash'},
        {'kind': 'biological_statistics', 'request_id': 'stats', 'counts_request_id': 'counts', 'alphabet': 'aa', 'epsilon': .001,
            'nucleotide_padding': 'ACGT_at_variable_sites', 'omnibus_continuity': 'r_default_2x2_min_delta', 'pair_df_policy': 'standard_pair',
            'selected_pairs': [groups], 'distribution_backend': BACKEND},
        {'kind': 'biological_effects', 'request_id': 'effects', 'counts_request_id': 'counts', 'selected_pairs': [groups], 'zero_margin_policy': 'drop_for_raw_effect_only'},
        {'kind': 'expected_adequacy', 'request_id': 'adequacy', 'statistics_request_id': 'stats', 'statistics_kind': 'biological'}]
    return f


def meta_native_fixture(case='aa_two_groups'):
    directory = META_NATIVE / case
    receipt = json.loads((directory / 'RECEIPT.json').read_text())
    old = ROOT / 'verification/tool_graders_bvbrc_msa_metacats_implementation_2026-10-25'
    saved = json.loads((old / ('EXAMPLES_002' if case == 'twelve_groups' else 'EXAMPLES_001') / (case + '-inputs.json')).read_text())
    category = saved['counts_arguments']['category_id']; columns = saved['counts_arguments']['group_order']
    f = Fixture('metacats'); plan = f.plan(); plan['analysis']['category_ids'] = [category]
    original_id, _ = f.original((directory / 'original.fasta').read_bytes(), 'alignment', META_FASTA)
    f.artifact((directory / 'metadata.tsv').read_bytes(), 'metadata',
        {'reader': 'metacats_metadata', 'delimiter': 'tab', 'header': 'present', 'encoding': 'ascii'}, 'metadata')
    plan['analysis'].update(alignment_id=slot('analysis', 'alignment'), metadata_document_id=slot('analysis', 'metadata'))
    matrix_name = next(p for p in receipt['files'] if p.startswith('output/') and '/retained_raw/' not in p and p.endswith('.txt'))
    f.artifact((directory / matrix_name).read_bytes(), 'matrix', {'reader': 'metacats_adjusted_matrix', 'category_id': category, 'encoding': 'ascii'}, 'adjusted_matrix')
    plan['analysis']['adjusted_matrix_ids'] = [slot('analysis', 'matrix')]
    for suffix, sid, field, semantic, reader in (
        ('-chisqTable.tsv', 'chisq', 'chisq_table_ids', 'chisq_export', {'reader': 'metacats_chisq', 'layout': 'current_filtered_tsv'}),
        ('-mcTable.tsv', 'pairs', 'pair_table_ids', 'pair_export', {'reader': 'metacats_pair', 'layout': 'current_filtered_tsv'}),
        ('-chisqTable.txt', 'raw_omnibus', 'raw_r_table_ids', 'raw_r_omnibus', {'reader': 'metacats_raw_r', 'layout': 'r_write_table_single_result_string', 'kind': 'omnibus'}),
        ('-mcTable.txt', 'raw_pairs', 'raw_r_table_ids', 'raw_r_pairwise', {'reader': 'metacats_raw_r', 'layout': 'r_write_table_single_result_string', 'kind': 'pairwise'})):
        name = next(p for p in receipt['files'] if p.endswith(suffix))
        data = (directory / name).read_bytes()
        assert len(data) == receipt['files'][name]['bytes'] and hashlib.sha256(data).hexdigest() == receipt['files'][name]['sha256']
        f.artifact(data, sid, {**reader, 'category_id': category, 'encoding': 'ascii'}, semantic)
        plan['analysis'][field].append(slot('analysis', sid))
    common = r._empty_common('analysis')
    common['input_sequences'] = [{'kind': 'parsed_document', 'input_binding_id': original_id, 'document': slot('analysis', 'alignment'),
        'member_id_rule': 'first_whitespace_token', 'molecule': 'dna' if receipt['alphabet'] == 'na' else 'protein', 'host_member_joins': [], 'evidence': []}]
    common['automatic_row_joins'] = [{'alignment': slot('analysis', 'alignment'), 'input_binding_ids': [original_id], 'method': 'exact_unique_header',
        'case_policy': 'literal', 'gap_policy': 'literal', 'transformation_ids': [], 'evidence': []}]
    f.scientific('common_associations', common)
    context = r._empty_metacats('analysis')
    context['metadata_joins'] = [{'metadata': slot('analysis', 'metadata'), 'id_column_index_0based': 0, 'alignment': slot('analysis', 'alignment'),
        'alignment_identity': 'member_label', 'case_policy': 'preserve', 'duplicate_policy': 'retain_unresolved', 'evidence': []}]
    context['categories'] = [{'category_id': category, 'metadata': slot('analysis', 'metadata'), 'metadata_column_index_0based': 1,
        'raw_heading_token': (directory / 'metadata.tsv').read_text().splitlines()[0].split('\t')[1], 'native_category_ordinal_1based': 1,
        'native_output_stem': category, 'input_mode': 'files', 'group_identity_rule': 'exact_category_value', 'evidence': []}]
    context['biological_group_populations'] = [{'kind': 'observed_metadata_groups', 'group_population_id': 'groups', 'category_id': category,
        'order': 'first_metadata_occurrence', 'include_metadata_only': True, 'evidence': []}]
    from gene_annotation_episode.bvbrc_metacats_association_contracts import group_id
    context['native_group_maps'] = [{'category_id': category, 'entries': [{'raw_group_value': col['group_id'],
        'native_group_ordinal': col['native_group_ordinal'], 'group_id': group_id(category, col['group_id']), 'evidence': col['evidence']} for col in columns],
        'completeness': 'complete', 'evidence': columns[0]['evidence']}]
    context['r_columns'] = [{'category_id': category, 'adjusted_matrix': slot('analysis', 'matrix'), 'interpreter_version': 'R 4.3.3',
        'columns': [{k: deepcopy(col[k]) for k in ('r_column_index_0based', 'r_group_token', 'native_group_ordinal', 'evidence')}
            | {'group_id': group_id(category, col['group_id'])} for col in columns], 'completeness': 'complete', 'evidence': columns[0]['evidence']}]
    header = f.raw['synthetic:artifact/analysis/chisq'].decode().splitlines()[0].split('\t')[5:]
    context['exported_group_joins'] = [{'category_id': category, 'table_id': slot('analysis', 'chisq'), 'heading_index_0based': i,
        'raw_heading_token': header[i], 'group_id': group_id(category, col['group_id']), 'r_column_index_0based': i,
        'state': 'resolved' if header[i] == col['group_id'] else 'wrong_native_label', 'evidence': col['evidence']} for i,col in enumerate(columns)]
    f.register_nested_evidence(context); f.scientific('metacats_context', context)
    plan['population_plans'] = [{'kind': 'whole_alignment', 'population_id': 'whole', 'alignment': slot('analysis', 'alignment')}]
    groups = [group_id(category, col['group_id']) for col in columns]; pairs = [list(p) for p in itertools.combinations(groups, 2)]
    for basis in ('native', 'biological'):
        counts = {'kind': basis + '_group_counts', 'request_id': basis + ':counts', 'population_id': 'whole', 'category_id': category, 'case_policy': 'preserve'}
        counts.update({'terminal_mask': 'native_terminal_dash_to_hash', 'native_input_hash_policy': 'exclude_hash'} if basis == 'native' else
            {'group_population_id': 'groups', 'terminal_gap_policy': 'exclude_terminal_dash', 'original_hash_policy': 'exclude_hash'})
        stats = {'kind': basis + '_statistics', 'request_id': basis + ':stats', 'counts_request_id': basis + ':counts', 'alphabet': receipt['alphabet'], 'epsilon': .001,
            'nucleotide_padding': 'ACGT_at_variable_sites', 'omnibus_continuity': 'r_default_2x2_min_delta', 'pair_df_policy': 'native_source' if basis == 'native' else 'standard_pair',
            'selected_pairs': pairs, 'distribution_backend': BACKEND}
        if basis == 'native': stats['pair_zero_policy'] = 'retain_math_and_native_zero_to_one'
        plan['calculation_parameters']['requests'] += [counts, stats]
    return f


def xmfa_native_fixture(with_sources=True):
    native = ROOT / 'verification/tool_graders_bvbrc_msa_xmfa_boundaries_2026-10-25/native_examples'
    saved = json.loads((ROOT / 'verification/tool_graders_bvbrc_xmfa_sources_2026-10-25/saved_examples/combined_native-inputs.json').read_text())
    f = Fixture(); p = f.plan(); p['analysis'].update(mode='mauve_blocks', full_xmfa_slot_id='full', xmfa_document_id=slot('analysis', 'full'))
    f.artifact((native / 'combined.xmfa').read_bytes(), 'full', {'reader': 'mauve_xmfa_v1', 'dialect': 'mauve1', 'alphabet': 'dna', 'encoding': 'ascii'}, 'full_xmfa')
    selection = {'population_id': 'xmfa-all', 'document_id': slot('analysis', 'full'), 'member_numbers': [1,2,3],
        'block_columns': [{'block_index': b['block_index'], 'columns_0based': list(range(b['alignment_column_count']))} for b in saved['document']['blocks']],
        'completeness': 'complete', 'evidence': []}
    requests = [{'kind': 'xmfa_alignment_components', 'request_id': 'metrics', 'document_id': slot('analysis', 'full'), 'selection': selection, 'selected_pairs': [[1,3]], 'case_policy': 'uppercase'}]
    for basis in ('represented', 'multi_member_block', 'cooccupied_column'):
        requests.append({'kind': 'xmfa_interval_coverage', 'request_id': basis, 'document_id': slot('analysis', 'full'), 'selection': selection, 'use_source_bindings': True, 'basis': basis})
    requests += [{'kind': 'xmfa_column_coordinates', 'request_id': 'coordinates', 'document_id': slot('analysis', 'full'),
        'cells': [{'block_index': 0, 'record_index': 0, 'column_0based': i} for i in (0,28,48)], 'use_source_bindings': True},
        {'kind': 'xmfa_source_positions', 'request_id': 'inverse', 'document_id': slot('analysis', 'full'),
        'queries': [{'member_number': 1, 'position_0based': 48}], 'use_source_bindings': True}]
    p['calculation_parameters']['requests'] = requests
    if with_sources:
        inputs = saved['inputs']
        for file in inputs['files']:
            art = f.artifact((native / file['file_id']).read_bytes(), 'source:' + file['file_id'], None, 'xmfa_staged_source')
            file['artifact'] = {k: art[k] for k in ('raw_artifact_ref','source_ref','sha256')}
            for record in file['records']: record['source_location']['artifact'] = deepcopy(file['artifact'])
        sources = {'version': 'bvbrc_msa_xmfa_sources_v1', 'analysis_id': 'analysis', 'items': [{'document': slot('analysis', 'full'), 'inputs': inputs,
            'source_readers': [{'file_id': file['file_id'], 'reader': 'fasta_records_for_xmfa_v1', 'id_rule': 'first_whitespace_token', 'encoding': 'ascii'} for file in inputs['files']],
            'source_comparison': saved['source_comparison'], 'evidence': []}]}
        f.register_nested_evidence(sources); f.scientific('xmfa_sources', sources)
    return f


@pytest.mark.parametrize('provider', ['msa', 'metacats'])
def test_real_closed_parameter_schema_and_full_validation(provider):
    f = basic_fixture(provider); schema = c.parameters_schema(provider=provider)
    Draft202012Validator.check_schema(schema)
    assert c.validate_parameters(f.parameters, provider=provider) == f.parameters
    f.parameters['analyses'][0]['calculation_parameters']['requests'][0]['unknown'] = 1
    with pytest.raises(ValueError):
        c.validate_parameters(f.parameters, provider=provider)


@pytest.mark.parametrize('alphabet', ['dna', 'protein'])
def test_retained_native_msa_provider_composition(alphabet):
    f = msa_native_fixture(alphabet); result, resolved, _ = f.compose()
    sheet, components, _ = result[0]
    assert sheet is not None and components is not None
    assert len(resolved['selections']) == 3
    assert sheet['consensus_associations'][0]['state'] == 'resolved'
    entropy = components['results'][1]['value']
    if alphabet == 'dna':
        assert entropy['sites'][1]['literal_entropy_bits']['value'] == pytest.approx(.9182958340544896)
        assert entropy['sites'][1]['native_score_recalculated']['value'] == 92
        assert entropy['sites'][2]['native_score_recalculated']['value'] == 81
    else:
        assert entropy['sites'][3]['literal_entropy_bits']['value'] == 1
        assert entropy['sites'][3]['native_score_recalculated']['value'] == 100


def test_metacats_biology_does_not_require_native_r_columns():
    result, _, _ = meta_fixture().compose(); sheet, components, _ = result[0]
    assert sheet['native_group_columns'] == []
    counts = next(r['value'] for r in components['results'] if r['request_id'] == 'counts')
    assert counts['sites'][1]['observed_counts'] == [[1, 0], [0, 1]]
    stats = next(r['value'] for r in components['results'] if r['request_id'] == 'stats')
    assert stats['pairs'][0]['df']['value'] == 1
    # Four augmented cells differ from expected .501 by .5; df=1 has
    # survival function erfc(sqrt(chi_square/2)).
    assert stats['pairs'][0]['mathematical_p']['value'] == pytest.approx(math.erfc(math.sqrt((4 * .5 ** 2 / .501) / 2)))


@pytest.mark.parametrize('change,state,code', [
    ('missing', 'missing', 'alignment_slot_missing'), ('hash', 'invalid', 'alignment_slot_sha256_conflict'),
    ('length', 'invalid', 'alignment_slot_sha256_conflict'), ('incomplete', 'incomplete', 'alignment_slot_incomplete'),
    ('format', 'invalid', 'alignment_declared_format_conflict'), ('ambiguous', 'ambiguous', 'alignment_slot_ambiguous')])
def test_slot_failure_preserves_exact_original_plan(change, state, code):
    f = basic_fixture(); original = deepcopy(f.parameters)
    a = f.bundle['artifacts'][0]
    if change == 'missing': f.bundle['artifacts'] = []
    elif change == 'hash': f.raw[a['raw_artifact_ref']] = b'>other\nAC\n'
    elif change == 'length': a['byte_count'] += 1; a['transfer']['total_size'] += 1
    elif change == 'incomplete': a['transfer'].update(body_complete=False, object_complete='no')
    elif change == 'format': a['declared_format']['format'] = 'newick'
    else:
        b = deepcopy(a); b['workspace_object']['uuid'] = 'other'; b['task_association']['output_uuid'] = 'other'
        f.bundle['artifacts'].append(b)
    if change == 'missing': f.raw = {}
    resolved = f.resolve()
    assert resolved['selections'][0]['state'] == state
    assert code in [v['reason_code'] for v in resolved['requirements']]
    assert resolved['analyses'][0]['analysis']['alignment_id'] is None
    assert resolved['parameters'] == original


def test_repeated_equivalent_representations_retain_every_receipt():
    f = basic_fixture(); a = deepcopy(f.bundle['artifacts'][0]); a['transfer']['receipt_ref'] += '/second'
    f.bundle['artifacts'].append(a); f.bundle['acquisition_receipt_refs'].append(a['transfer']['receipt_ref'])
    resolved = f.resolve(); selected = resolved['selections'][0]
    assert selected['state'] == 'resolved' and len(selected['acquisition_receipt_refs']) == 2
    assert any(d['code'] == 'duplicate_artifact_representation' for d in selected['diagnostics'])


def test_same_native_bytes_different_categories_remain_distinct():
    f = Fixture('metacats'); p = f.plan(); p['analysis']['category_ids'] = ['first', 'second']
    data = b'Position\tChi-square_value\tP-value\tDegrees_of_freedom\tFewer_5\tA\tB\n1\t2\t0.1\t1\tN\tA=2\tC=2\n'
    a = f.artifact(data, 'first', {'reader': 'metacats_chisq', 'layout': 'current_filtered_tsv', 'category_id': 'first', 'encoding': 'ascii'}, 'chisq_export')
    f.parameters['artifact_selection'].append({'analysis_id': 'analysis', 'slot_id': 'second', 'semantic_role': 'chisq_export',
        'source': {'kind': 'acquired_role', 'bundle_role': a['role']}, 'reader': {'reader': 'metacats_chisq', 'layout': 'current_filtered_tsv', 'category_id': 'second', 'encoding': 'ascii'}})
    p['analysis']['chisq_table_ids'] = [slot('analysis', 'first'), slot('analysis', 'second')]
    resolved = f.resolve()
    assert [s['state'] for s in resolved['selections']] == ['resolved', 'resolved']
    assert len({d['value']['table_id'] for d in resolved['analyses'][0]['documents']}) == 2


def test_native_reader_is_not_inferred_from_extension():
    f = basic_fixture(); f.bundle['artifacts'][0]['workspace_object']['path'] = '/synthetic/a.tree'
    f.bundle['artifacts'][0]['task_association']['output_path'] = '/synthetic/a.tree'
    resolved = f.resolve()
    assert resolved['analyses'][0]['documents'][0]['kind'] == 'alignment'


def test_no_generic_slot_substitution():
    f = basic_fixture(); common = r._empty_common('analysis')
    common['source_records'] = [{'source_record_id': slot('analysis', 'alignment'), 'kind': 'parent_declaration',
        'evidence': {'content': {'source_ref': 'missing', 'artifact_ref': 'missing', 'artifact_field': 'artifact_ref', 'sha256': '0' * 64, 'byte_count': 0}, 'pointer': ''}}]
    f.scientific('common_associations', common)
    resolved = f.resolve()
    assert resolved['analyses'][0]['status'] == 'invalid'
    assert resolved['analyses'][0]['scientific_values'] == []


def test_missing_direct_request_reference_is_quarantined_without_fake_id():
    f = basic_fixture(); f.plan()['calculation_parameters']['requests'].append({'kind': 'ungapped_map', 'request_id': 'map', 'alignment_id': slot('analysis', 'alignment'), 'row_indices': [0]})
    f.bundle['artifacts'] = []; f.raw = {}
    values, resolved, compiler = f.compose(); sheet, components, _ = values[0]
    assert sheet is not None
    assert components['parameters']['requests'] == [f.plan()['calculation_parameters']['requests'][0]]
    assert components['results'][0]['value'] is None
    assert any(n['role'] == 'map' and n['reason_code'] == 'alignment_calculation_dependency_unavailable' for n in compiler.requirements['analysis'])


@pytest.mark.parametrize('defect', ['unknown', 'pointer', 'value'])
def test_original_auto_request_custody_before_pure_association(defect):
    f = Fixture('metacats'); f.plan()['analysis']['mode'] = 'auto'
    original = [{'id': 'feature-a', 'grp': 'A'}]
    f.bundle['original_task']['submitted_parameters']['auto_groups'] = original
    f.bundle['input_bindings'] = [{'binding_id': 'auto', 'parameter_pointer': '/auto_groups', 'kind': 'inline_parameter',
        'content': None, 'workspace_path': None, 'inline_value': original, 'link_evidence': None, 'members': []}]
    context = r._empty_metacats('analysis')
    context['auto_group_entries'] = [{'input_binding_id': 'auto', 'entry_index_0based': 0, 'original_parameter_pointer': '/auto_groups/0',
        'feature_id': 'feature-a', 'raw_group_value': 'A', 'member_keys': [], 'evidence': []}]
    if defect == 'unknown': context['auto_group_entries'][0]['input_binding_id'] = 'unknown'
    if defect == 'pointer': context['auto_group_entries'][0]['original_parameter_pointer'] = '/auto_groups/00'
    if defect == 'value': context['auto_group_entries'][0]['raw_group_value'] = 'B'
    f.scientific('metacats_context', context)
    resolved = f.resolve()
    assert resolved['analyses'][0]['status'] == 'invalid'
    assert resolved['analyses'][0]['scientific_values'] == []


def test_known_auto_request_with_zero_fetched_members_is_retained():
    f = Fixture('metacats'); f.plan()['analysis']['mode'] = 'auto'
    original = [{'id': 'feature-a', 'grp': 'A'}]
    f.bundle['original_task']['submitted_parameters']['auto_groups'] = original
    f.bundle['input_bindings'] = [{'binding_id': 'auto', 'parameter_pointer': '/auto_groups', 'kind': 'inline_parameter',
        'content': None, 'workspace_path': None, 'inline_value': original, 'link_evidence': None, 'members': []}]
    context = r._empty_metacats('analysis')
    context['auto_group_entries'] = [{'input_binding_id': 'auto', 'entry_index_0based': 0, 'original_parameter_pointer': '/auto_groups/0',
        'feature_id': 'feature-a', 'raw_group_value': 'A', 'member_keys': [], 'evidence': []}]
    f.scientific('metacats_context', context)
    result, _, _ = f.compose(); sheet = result[0][0]
    assert sheet is not None
    assert sheet['auto_group_entries'] == context['auto_group_entries']
    assert sheet['associations']['original_members'] == []


def test_saved_reference_encoding_roundtrip_and_reject_noncanonical():
    value = c.encode_reference('member', 'analysis/α', 'input/β%1')
    assert c.decode_reference(value) == ('member', 'analysis/α', 'input/β%1')
    with pytest.raises(ValueError): c.decode_reference(value.replace('%2F', '%2f'))


def test_requested_form_is_exact_and_empty_selectors_stay_empty():
    fields = {'empty': {'kind': 'msa_sites', 'analysis_id': 'analysis', 'request_id': 'entropy', 'columns_0based': []}}
    schema = c.requested_form_schema(fields, provider='msa'); assert c.validate_requested_form(schema, provider='msa') == schema
    assert schema['properties']['empty']['x-alignment-fact']['columns_0based'] == []
    schema['properties']['empty']['description'] = 'unauthorized schema relaxation'
    with pytest.raises(ValueError): c.validate_requested_form(schema, provider='msa')


@pytest.mark.parametrize('case', ['aa_two_groups', 'aa_three_groups', 'metadata_only_first_group', 'all_missing', 'twelve_groups', 'native_pair_tail_underflow'])
def test_retained_metacats_native_bytes_and_originals(case):
    f = meta_native_fixture(case); values, _, _ = f.compose(); sheet, components, _ = values[0]
    assert sheet is not None and components is not None
    assert all(row['value'] is not None for row in components['results'])
    assert len(sheet['documents']) == 7
    original = next(d['value'] for d in sheet['documents'] if d['kind'] == 'alignment')
    raw = (META_NATIVE / case / 'original.fasta').read_text()
    assert ''.join(row['sequence'] for row in original['rows']) == ''.join(line for line in raw.splitlines() if not line.startswith('>'))
    assert all(row['state'] == 'resolved' for row in sheet['associations']['row_members'])
    if case == 'metadata_only_first_group':
        assert [row['group_id'] for row in sheet['native_group_columns']] == ['metacats_group:comparison/B', 'metacats_group:comparison/C']
        assert len(sheet['biological_group_populations'][0]['groups']) == 3
    if case == 'native_pair_tail_underflow':
        stats = components['results'][1]['value']; pair = stats['pairs'][0]
        assert pair['mathematical_p']['value'] is None and pair['numerical_state'] == 'underflow' and pair['log_p']['value'] < -1000
        assert pair['native_zero_rule_p']['value'] == 1


@pytest.mark.parametrize('with_sources', [True, False])
def test_full_xmfa_native_bytes_metrics_coordinates_and_coverage(with_sources):
    f = xmfa_native_fixture(with_sources); result, resolved, _ = f.compose(); sheet, components, _ = result[0]
    assert sheet is not None and components is not None
    values = [row['value'] for row in components['results']]
    assert all(v is not None for v in values)
    assert len(values[0]['blocks']) == 6
    pair = values[0]['blocks'][0]['pairs'][0]
    assert (pair['identical_canonical']['value'], pair['substitutions']['value'], pair['comparable_canonical']['value']) == (39,7,46)
    for row, expected in zip(values[1:4], ([50,41,49], [48,0,47], [46,0,46])):
        assert [m['known_union_bases']['value'] for m in row['members']] == expected
        assert [m['source_length']['value'] for m in row['members']] == ([50,41,49] if with_sources else [None,None,None])
    assert [cell['native_position_0based'] for cell in values[4]['cells']] == [48,None,1]
    assert resolved['analyses'][0]['status'] != 'invalid'


def test_xmfa_sequence_claim_cannot_substitute_for_actual_bytes():
    f = xmfa_native_fixture()
    sources = next(row['value'] for row in f.values if 'items' in row['value'])
    sources['items'][0]['inputs']['files'][0]['records'][0]['sequence'] = 'A' * 50
    values, _, _ = f.compose(); sheet, components, _ = values[0]
    assert sheet['xmfa_bindings'][0]['verification']['status'] != 'ok'
    coverage = components['results'][1]['value']
    assert [row['source_length']['value'] for row in coverage['members']] == [None,None,None]
    assert coverage['members'][0]['known_union_bases']['value'] == 50


@pytest.mark.parametrize('defect', ['value', 'pointer', 'hash', 'duplicate_key'])
def test_supplied_json_evidence_uses_actual_selected_bytes(defect):
    f = basic_fixture(); common = r._empty_common('analysis'); evidence = f.scientific('common_associations', common)
    content = evidence['content']; payload = json.dumps(common, sort_keys=True, separators=(',', ':')).encode()
    if defect == 'value': f.values[0]['value']['analysis_id'] = 'forged'
    elif defect == 'pointer': evidence['pointer'] = '/unknown'
    elif defect == 'hash': payload += b' '
    else:
        payload = b'{"analysis_id":"other",' + payload[1:]
        content.update(sha256=hashlib.sha256(payload).hexdigest(), byte_count=len(payload))
    f.bundle['supplied_contents'].append(content); f.raw[content['artifact_ref']] = payload
    with pytest.raises(ValueError): f.resolve()


def test_original_source_binding_must_match_parameter_and_selected_content():
    f = Fixture(); bid, artifact = f.original(b'>a\nAC\n', 'original', FASTA)
    assert f.resolve()['selections'][0]['state'] == 'resolved'
    f.bundle['original_task']['submitted_parameters']['input'][bid] = '/different'
    with pytest.raises(ValueError, match='original_input_conflict'): f.resolve()


def test_missing_one_analysis_keeps_independent_sheet_and_calculation():
    f = basic_fixture(aid='first'); other = basic_fixture(aid='second')
    f.parameters['analyses'] += other.parameters['analyses']; f.parameters['artifact_selection'] += other.parameters['artifact_selection']
    results, resolved, _ = f.compose()
    assert results[0][1]['results'][0]['value']['member_count']['value'] == 2
    assert results[1][0] is not None and results[1][1]['results'][0]['value'] is None
    assert resolved['analyses'][1]['analysis']['alignment_id'] is None


def cross_family_fixture():
    f = meta_fixture(aid='first'); other = meta_fixture(aid='second')
    f.parameters['analyses'] += other.parameters['analyses']; f.parameters['artifact_selection'] += other.parameters['artifact_selection']
    for key in ('artifacts','supplied_contents','supplied_scientific_metadata','acquisition_receipt_refs'):
        f.bundle[key] += other.bundle[key]
    f.raw.update(other.raw); f.values += other.values
    family = {'family_request_id': 'both', 'family': {'family_id': 'pair-family', 'analysis_ids': ['first','second'],
        'category_ids': ['category'], 'test_kind': 'pairwise', 'eligibility': 'variable_site_positive_df', 'population_state': 'complete',
        'total_test_count': None, 'assumption': None, 'p_value_basis': 'biological_mathematical_recalculation', 'evidence': [], 'selection': 'all_eligible', 'tests': []},
        'p_values': {'kind': 'statistical_results', 'requests': [{'analysis_id': aid, 'request_id': 'stats'} for aid in ('first','second')], 'field': 'mathematical_p'},
        'method': 'holm', 'alpha': .05, 'dependence_assumption': 'none_required_between_tests'}
    f.parameters['multiplicity_families'] = [family]
    return f


def composed_family(f):
    values, resolved, _ = f.compose()
    sheets = {'analyses': [{'analysis_id': row['analysis_id'], 'sheet': value[0]} for row,value in zip(resolved['analyses'],values)], 'selections': resolved['selections']}
    components = {'analyses': [{'analysis_id': row['analysis_id'], 'components': value[1]} for row,value in zip(resolved['analyses'],values)]}
    return r._cross_family(f.parameters['multiplicity_families'][0], sheet_set=sheets, component_set=components, parameters=f.parameters, provider=f.provider), sheets, components


def test_cross_analysis_same_category_keeps_both_tests_and_full_denominator():
    f = cross_family_fixture(); result, _, _ = composed_family(f)
    assert result['value']['total_test_count'] == 2
    rows = result['value']['results']; assert len({r['test_id'] for r in rows}) == 2
    expected = 2 * math.erfc(math.sqrt((4 * .5 ** 2 / .501) / 2))
    assert [row['adjusted_p']['value'] for row in rows] == pytest.approx([expected, expected])


def test_explicit_cross_analysis_test_order_is_original_order():
    f = cross_family_fixture(); family = f.parameters['multiplicity_families'][0]['family']; family['selection'] = 'explicit_tests'
    test = {'category_id': 'category', 'column_0based': 1, 'kind': 'pairwise', 'group_ids': ['metacats_group:category/B','metacats_group:category/C']}
    family['tests'] = [{'analysis_id': aid, 'test': test} for aid in ('second','first')]
    result, _, components = composed_family(f)
    ids = [row['components']['results'][2]['value']['pairs'][0]['test_id'] for row in reversed(components['analyses'])]
    assert result['value']['family']['test_ids'] == ids


def test_cross_analysis_explicit_empty_family_is_measured_zero():
    f = cross_family_fixture(); f.parameters['multiplicity_families'][0]['family']['selection'] = 'explicit_tests'
    result, _, _ = composed_family(f)
    assert result['value']['total_test_count'] == 0 and result['value']['results'] == []


def test_filtered_native_rows_never_become_whole_family_denominator():
    f = meta_native_fixture('official_na')
    family = {'family_request_id': 'native-whole', 'family': {'family_id': 'whole', 'analysis_ids': ['analysis'], 'category_ids': ['GROUP'],
        'test_kind': 'omnibus', 'eligibility': 'variable_site_positive_df', 'population_state': 'complete', 'total_test_count': None, 'assumption': None,
        'p_value_basis': 'native_unadjusted', 'evidence': [], 'selection': 'all_eligible', 'tests': []},
        'p_values': {'kind': 'native_tables', 'tables': [slot('analysis','raw_omnibus')], 'eligibility_statistics_requests': [{'analysis_id': 'analysis', 'request_id': 'native:stats'}]},
        'method': 'holm', 'alpha': .05, 'dependence_assumption': 'none_required_between_tests'}
    f.parameters['multiplicity_families'] = [family]
    raw_result, sheets, _ = composed_family(f)
    assert raw_result['value']['total_test_count'] == 312
    filtered = next(d['value'] for d in sheets['analyses'][0]['sheet']['documents'] if d['kind'] == 'metacats_chisq')
    assert len(filtered['rows']) == 143
    family['p_values']['tables'] = [slot('analysis','chisq')]
    result, _, _ = composed_family(f)
    assert result['status'] == 'partial' and result['value'] is None
    assert any(n['reason_code'] == 'metacats_test_family_incomplete' for n in result['requirements'])


COUNT_FIELD = {'n': {'kind': 'measurement', 'analysis_id': 'analysis', 'request_id': 'alignment', 'metric': 'member_count', 'selector': {}}}


def optional_missing_fixture():
    f = basic_fixture(); plan = f.add_plan('unfinished')
    plan['analysis']['alignment_id'] = slot('unfinished','missing')
    f.parameters['artifact_selection'].append({'analysis_id': 'unfinished', 'slot_id': 'missing', 'semantic_role': 'alignment',
        'source': {'kind': 'acquired_role', 'bundle_role': 'not_acquired'}, 'reader': FASTA})
    return f


def test_requested_only_success_retains_independent_missing_analysis():
    result = optional_missing_fixture().consume(COUNT_FIELD)
    assert result['status'] == 'ok' and result['facts']['n']['value'] == 2
    assert result['missing_requirements']
    assert result['sheet']['analyses'][1]['sheet']['analysis']['alignment_id'] is None
    assert result['sheet']['analyses'][1]['status'] == 'partial'


@pytest.mark.parametrize('mode,expected', [('missing','partial'), ('wrong_hash','invalid'), ('failed','failed')])
def test_missing_requested_scalar_has_no_invented_method(mode,expected):
    f = basic_fixture()
    if mode == 'wrong_hash': f.raw[f.bundle['artifacts'][0]['raw_artifact_ref']] += b'X'
    else: f.bundle['artifacts'] = []; f.raw = {}
    if mode == 'failed': f.bundle['status'] = 'failed'
    result = f.consume(COUNT_FIELD)
    assert result['status'] == expected
    assert result['facts']['n']['value'] is None and result['facts']['n']['method_ref'] is None
    assert result['facts']['n']['state'] == 'missing' and result['facts']['n']['requirement_refs']


def test_exact_empty_selector_is_distinct_from_unavailable_collection():
    fields = {'sites': {'kind': 'msa_sites', 'analysis_id': 'analysis', 'request_id': 'entropy', 'columns_0based': []}}
    f = msa_native_fixture(); available = f.consume(fields)
    assert available['facts']['sites'] == [] and available['status'] == 'ok'
    f.bundle['artifacts'] = []; f.raw = {}; missing = f.consume(fields)
    assert missing['facts']['sites'] is None and missing['status'] == 'partial'


def test_native_measurement_keeps_observed_value_and_unrecorded_method():
    f = msa_native_fixture(); fields = {'score': {'kind': 'native_measurement', 'analysis_id': 'analysis', 'table': slot('analysis','frequency'), 'row_index': 1, 'field': {'kind':'score'}}}
    result = f.consume(fields)
    assert result['status'] == 'ok'
    assert result['facts']['score']['value'] == 92 and result['facts']['score']['origin'] == 'native_observation'
    assert result['facts']['score']['method_ref'] is None


def test_four_xmfa_projections_and_missing_source_status():
    fields = {'cell': {'kind':'xmfa_coordinates', 'analysis_id':'analysis', 'request_id':'coordinates', 'cells':[{'block_index':0,'record_index':0,'column_0based':0}]},
        'metric': {'kind':'xmfa_alignment_measurements', 'analysis_id':'analysis', 'request_id':'metrics', 'measurements':[{'metric':'identical_canonical','block_index':0,'member_a':1,'member_b':3}]},
        'coverage': {'kind':'xmfa_coverage', 'analysis_id':'analysis', 'request_id':'represented', 'member_numbers':[1,2,3], 'include_intervals':True, 'include_original_coverage':False},
        'inverse': {'kind':'xmfa_source_positions', 'analysis_id':'analysis', 'request_id':'inverse', 'queries':[{'member_number':1,'position_0based':48}]}}
    result = xmfa_native_fixture().consume(fields); facts = result['facts']
    assert result['status'] == 'ok'
    assert facts['cell'][0]['source_coordinate']['position_0based'] == 48
    assert facts['metric'][0]['measurement']['value'] == 39
    assert facts['metric'][0]['selection'] == {'metric':'identical_canonical','block_index':0,'column_0based':None,'symbol':None,'member_a':1,'member_b':3}
    assert [r['source_length'] for r in facts['coverage']] == [50,41,49]
    assert facts['inverse'][0]['state'] == 'unique'
    missing = xmfa_native_fixture(False).consume(fields)
    assert missing['status'] == 'partial' and missing['facts']['metric'][0]['measurement']['value'] == 39
    assert missing['facts']['cell'][0]['native_position_0based'] == 48 and missing['facts']['cell'][0]['source_coordinate'] is None


def test_bundle_consumption_has_no_file_network_process_or_repeated_parse(monkeypatch):
    from test_bvbrc_alignment_associations import forbid_io
    f = basic_fixture()
    repeated = deepcopy(f.parameters['artifact_selection'][0]); repeated['slot_id'] = 'same-again'
    f.parameters['artifact_selection'].append(repeated)
    calls = []; original = r._parse
    def observed(*args):
        calls.append(args[2]); return original(*args)
    monkeypatch.setattr(r, '_parse', observed); forbid_io(monkeypatch)
    result = f.consume(COUNT_FIELD)
    assert result['facts']['n']['value'] == 2 and len(calls) == 1
    assert len(result['sheet']['analyses'][0]['sheet']['read_outcomes']) == 2


def test_changed_saved_parameters_do_not_modify_native_values_or_reparse(monkeypatch):
    from test_bvbrc_alignment_associations import forbid_io
    from gene_annotation_episode.bvbrc_metacats_grader import calculate_metacats
    f = meta_native_fixture(); values, _, _ = f.compose(); sheet, original, _ = values[0]
    before = deepcopy(sheet); changed = deepcopy(original['parameters'])
    for request in changed['requests']:
        if request['kind'].endswith('_statistics'): request['epsilon'] = .01
    def forbidden(*args, **kwargs): raise AssertionError('saved recalculation parsed or verified new data')
    monkeypatch.setattr(r, '_parse', forbidden)
    monkeypatch.setattr(r, 'verify_xmfa_source_inputs', forbidden)
    forbid_io(monkeypatch)
    recomputed = calculate_metacats(sheet, changed)
    assert sheet == before
    assert recomputed['parameters'] != original['parameters']
    assert recomputed['results'][1]['value']['pairs'][0]['chi_square']['value'] != original['results'][1]['value']['pairs'][0]['chi_square']['value']


def test_saved_projection_replay_has_no_parsers_calculators_or_io(monkeypatch):
    from test_bvbrc_alignment_associations import forbid_io
    from gene_annotation_episode.bvbrc_alignment_bundle_projection import project_requested_facts, validate_projected_facts
    f = basic_fixture(); result = f.consume(COUNT_FIELD)
    arguments = {'sheet_set': result['sheet'], 'component_set': result['components'], 'missing_requirements': tuple(result['missing_requirements']),
        'diagnostics': tuple(result['diagnostics']), 'requested_form': c.requested_form_schema(COUNT_FIELD, provider='msa'), 'parameters': f.parameters, 'provider':'msa'}
    def forbidden(*args, **kwargs): raise AssertionError('saved projection invoked scientific computation')
    for field in ('_parse','calculate_msa','calculate_metacats','extract_msa_sheet','extract_metacats_sheet','verify_xmfa_source_inputs'):
        monkeypatch.setattr(r, field, forbidden)
    forbid_io(monkeypatch)
    assert project_requested_facts(**arguments) == result['facts']
    assert validate_projected_facts(result['facts'], **arguments) == result['facts']


def test_facades_keep_exact_original_eight_fields_and_digest():
    from gene_annotation_episode import bvbrc_msa_bundle_adapter as msa, bvbrc_metacats_bundle_adapter as meta
    for provider, adapter in [('msa',msa),('metacats',meta)]:
        f = basic_fixture(provider); form = adapter.requested_form_schema(COUNT_FIELD)
        result = adapter.consume_bundle(f.bundle, artifact_bytes=f.raw, supplied_values=f.values, requested_form=form, parameters=f.parameters)
        assert set(result) == {'adapter_id','adapter_version','status','sheet','components','facts','missing_requirements','diagnostics'}
        assert result['adapter_id'] == 'bvbrc_' + provider and result['adapter_version'] == '1'
        assert result['facts']['n']['value'] == 2
    assert msa.implementation_sha256() == meta.implementation_sha256()
    assert len(msa.implementation_sha256()) == 64


def test_supplied_original_hash_and_case_are_not_reconstructed_from_native_masks():
    f = meta_fixture(data=b'>a\n#Ac\n>b\n-AT\n')
    artifact = f.bundle['artifacts'][0]; content = r._content(artifact)
    f.bundle['supplied_contents'].append(content); f.bundle['artifacts'].remove(artifact)
    f.bundle['original_task']['submitted_parameters']['alignment_file'] = '/synthetic/original'
    f.bundle['input_bindings'].append({'binding_id':'original','parameter_pointer':'/alignment_file','kind':'retained_bytes',
        'content':content,'workspace_path':'/synthetic/original','inline_value':None,'link_evidence':None,'members':[]})
    f.parameters['artifact_selection'][0]['source'] = {'kind':'original_input','input_binding_id':'original','content':content}
    common = r._empty_common('analysis')
    common['input_sequences'] = [{'kind':'parsed_document','input_binding_id':'original','document':slot('analysis','alignment'),
        'member_id_rule':'first_whitespace_token','molecule':'protein','host_member_joins':[],'evidence':[]}]
    common['automatic_row_joins'] = [{'alignment':slot('analysis','alignment'),'input_binding_ids':['original'],'method':'exact_unique_header',
        'case_policy':'literal','gap_policy':'literal','transformation_ids':[],'evidence':[]}]
    f.scientific('common_associations', common)
    values, _, _ = f.compose(); sheet, components, _ = values[0]
    alignment = next(d['value'] for d in sheet['documents'] if d['kind']=='alignment')
    assert [row['sequence'] for row in alignment['rows']] == ['#Ac','-AT']
    site = components['results'][1]['value']['sites'][0]
    assert site['excluded_original_hash_rows_by_group'] == [[0],[]]
    assert site['excluded_terminal_rows_by_group'] == [[],[1]]
    assert components['results'][1]['value']['sites'][2]['symbols'] == ['T','c']


def test_adapter_digest_covers_consumed_contract_bytes(monkeypatch):
    from gene_annotation_episode import bvbrc_msa_bundle_adapter as adapter
    original = Path.read_bytes; digest = adapter.implementation_sha256()
    def changed(path):
        raw = original(path)
        return raw + b'\n# explicit synthetic digest check\n' if path.name == 'bvbrc_alignment_bundle_contracts.py' else raw
    monkeypatch.setattr(Path, 'read_bytes', changed)
    assert adapter.implementation_sha256() != digest


def test_nested_evidence_and_original_task_conflicts_have_specific_requirements():
    f = basic_fixture(); common = r._empty_common('analysis')
    common['source_records'] = [{'source_record_id':'unbound','kind':'parent_declaration','evidence':{
        'content':{'source_ref':'source','artifact_ref':'artifact','artifact_field':'artifact_ref','sha256':'0'*64,'byte_count':0},'pointer':''}}]
    f.scientific('common_associations', common)
    assert any(row['reason_code']=='alignment_supplied_evidence_unbound' for row in f.resolve()['requirements'])


def test_registered_native_diagnostic_is_preserved_in_requested_qualification():
    f = basic_fixture(); f.artifact(b'wrong native header\n', 'frequency', {'reader':'msa_frequency','alphabet':'dna','layout':'current_without_reference','encoding':'ascii'}, 'msa_frequency')
    f.plan()['analysis']['frequency_table_id'] = slot('analysis','frequency')
    fields = {**COUNT_FIELD, 'qualifications':{'kind':'qualifications','analysis_id':'analysis','slot_id':'frequency','request_id':None}}
    result = f.consume(fields)
    assert result['status'] == 'ok' and result['facts']['n']['value'] == 2
    assert 'bvbrc_msa_native_header_conflict' in [row['code'] for row in result['facts']['qualifications']]
    assert 'alignment_unregistered_qualification' not in [row['code'] for row in result['facts']['qualifications']]
    assert all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,127}',code) for code in c.DIAGNOSTIC_CODES)
    assert not any(code.startswith(('phylogeny_phylip_', 'phylogeny_phyloxml_', 'codon_', 'paml_')) for code in c.DIAGNOSTIC_CODES)
