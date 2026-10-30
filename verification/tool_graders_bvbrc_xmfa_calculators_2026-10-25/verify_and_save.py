"""Retain complete calculator operands/results and prove exact saved replay.

This local verification harness performs file I/O before/after the pure replay.
It does not run an aligner, service, model, resource job or episode. Invocation
and original-map evidence in synthetic/source fixtures retain that identity.
"""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

import gene_annotation_episode.providers as providers
from gene_annotation_episode import xmfa_formats, xmfa_sources, phylogeny_formats
from gene_annotation_episode.xmfa_calculators import xmfa_alignment_components, xmfa_interval_coverage
from gene_annotation_episode.xmfa_coordinates import xmfa_column_coordinates, xmfa_source_positions
from gene_annotation_episode.xmfa_calculation_contracts import (
    validate_xmfa_coordinates, validate_xmfa_inverse_coordinates, validate_xmfa_selection,
    validate_xmfa_alignment_components, validate_xmfa_coverage_components)
from test_xmfa_sources import BASE, native_document, supplied, bind
from test_xmfa_coordinates import all_cells, toy, concat_case, original
from test_xmfa_calculators import selection


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Reproduction writes only this script's explicit example outputs. Initial
    # failure receipts and the original source snapshot are never rewritten.
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    return {'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def run(saved):
    document, bindings, chosen = saved['document'], saved['bindings'], saved['selection']
    return {
        'coordinates': xmfa_column_coordinates(document, cells=tuple(saved['cells']), bindings=bindings),
        'inverse': xmfa_source_positions(document, queries=tuple(saved['queries']), bindings=bindings),
        'alignment': xmfa_alignment_components(document, selection=chosen,
            selected_pairs=tuple(tuple(pair) for pair in saved['selected_pairs']), case_policy=saved['case_policy']),
        'coverage': {basis: xmfa_interval_coverage(document, selection=chosen, bindings=bindings, basis=basis)
                     for basis in ('represented', 'multi_member_block', 'cooccupied_column')},
        'changed_case_alignment': xmfa_alignment_components(document, selection=chosen,
            selected_pairs=tuple(tuple(pair) for pair in saved['selected_pairs']),
            case_policy='preserve' if saved['case_policy'] == 'uppercase' else 'uppercase')}


def cases():
    result = []
    for name, mode in (('combined.xmfa', 'single_file_entries'), ('separate.xmfa', 'multiple_files_concatenated')):
        document = native_document(name)
        result.append((name, 'retained_native_with_explicit_fixture_invocation', document,
                       bind(document, supplied(mode)), None))
    for name in ('simple.xmfa', 'simple_short.xmfa'):
        result.append((name, 'retained_native_unbound_source', native_document(name), None, None))
    source_examples = ROOT / 'verification/tool_graders_bvbrc_xmfa_sources_2026-10-25/saved_examples'
    for name in ('unknown_invocation', 'source_mismatch', 'entry_content_swap', 'distinct_original_occurrences',
                 'conflicting_original_maps', 'missing_map_evidence', 'missing_source_bytes', 'partial_input_population'):
        operand = json.loads((source_examples / (name + '-inputs.json')).read_text())
        binding = json.loads((source_examples / (name + '-answer.json')).read_text())
        result.append((name, 'synthetic_supplied_operand_counterexample_on_retained_native_xmfa', operand['document'], binding, None))
    doc, binding = concat_case()
    result.append(('concatenation_and_original_occurrences', 'deliberately_synthetic', doc, binding, None))
    doc, binding = concat_case([original('left.fa', 'row:0', 0, 2)])
    result.append(('partial_original_map', 'deliberately_synthetic', doc, binding, None))
    doc, binding = toy(b'#FormatVersion Mauve1\n#Sequence1File x.fa\n>1:1-4 +\nACGT\n=\n'
        b'>1:2-5 +\nCGTA\n=\n>1:3-4 +\nGT\n=\n', [('x.fa', b'>x\nACGTAA\n')])
    result.append(('triple_overlap', 'deliberately_synthetic', doc, binding, None))
    doc, binding = toy(b'#FormatVersion Mauve1\n#Sequence1File a.fa\n#Sequence2File b.fa\n'
        b'>1:1-3 +\nACG\n>2:1-2 +\nAC\n=\n', [('a.fa', b'>a\nACG\n'), ('b.fa', b'>b\nAC\n')])
    chosen = selection(doc, [1, 2], [{'block_index': 0, 'columns_0based': [0, 1]}])
    result.append(('ragged_dependency_subset', 'deliberately_synthetic', doc, binding, chosen))
    doc, binding = toy(b'#FormatVersion Mauve1\n#Sequence1File x.fa\n>1:1-2 +\nAC\n=\n'
                       b'>1:3-4 +\nGT\n', [('x.fa', b'>x\nACGT\n')])
    result.append(('truncated_with_valid_partial_coordinates', 'deliberately_synthetic', doc, binding, None))
    doc, binding = toy(b'#FormatVersion Mauve1\n>1:1-3 +\naRN-\n>2:1-3 +\nATN-\n=\n')
    result.append(('case_policy_and_empty_canonical_population', 'deliberately_synthetic', doc, binding, None))
    doc, binding = toy(b'#FormatVersion Mauve1\n#Sequence1File x.fa\n', [('x.fa', b'>x\nAC\n')])
    result.append(('header_only_unknown_completion', 'deliberately_synthetic', doc, binding, selection(doc, [1])))
    return result


def forbidden(*args, **kwargs):
    raise AssertionError('Pure saved XMFA replay attempted acquisition, native parsing, I/O, native execution, or a model call')


def main():
    paths = [ROOT / p for p in (
        'gene_annotation_episode/xmfa_calculation_contracts.py', 'gene_annotation_episode/xmfa_coordinates.py',
        'gene_annotation_episode/xmfa_calculators.py', 'gene_annotation_episode/xmfa_sources.py',
        'gene_annotation_episode/xmfa_source_contracts.py', 'gene_annotation_episode/xmfa_formats.py',
        'gene_annotation_episode/xmfa_format_contracts.py', 'gene_annotation_episode/bvbrc_alignment_values.py',
        'gene_annotation_episode/phylogeny_calculation_contracts.py', 'gene_annotation_episode/phylogeny_format_contracts.py',
        'tests/test_xmfa_coordinates.py', 'tests/test_xmfa_calculators.py', 'tests/test_xmfa_sources.py')]
    paths += sorted(path for path in BASE.iterdir() if path.is_file())
    before = {str(path.relative_to(ROOT)): digest(path) for path in paths}
    targets = [(obj, name) for obj, names in (
        (__import__('builtins'), ('open',)), (os, ('open', 'system')),
        (Path, ('open', 'read_text', 'read_bytes')), (socket, ('socket', 'create_connection')),
        (subprocess, ('Popen', 'run')), (xmfa_formats, ('parse_mauve_xmfa',)),
        (xmfa_sources, ('bind_xmfa_sources',)), (phylogeny_formats, ('parse_aligned_fasta',)),
        (providers.ModelConnection, ('complete',)), (providers._SessionConnection, ('complete',)),
        (importlib, ('import_module',))) for name in names]
    summary = []
    for name, provenance, document, binding, chosen in cases():
        chosen = selection(document) if chosen is None else chosen
        queries = []
        for number in chosen['member_numbers']:
            member = next((m for m in (binding or {}).get('members', []) if m['member_number'] == number), None)
            if member and member['source_length'] is not None:
                positions = range(member['source_length'])
            else:
                # A query has no implied source-length assertion. Full retained
                # rows and all their cells are still included in these examples.
                positions = sorted({0} | {row['interval_0based_half_open'][1] - 1
                    for block in document['blocks'] for row in block['records']
                    if row['coordinate_state'] == 'present' and row['member_number']['value'] == number})
            queries.extend({'member_number': number, 'position_0based': p} for p in positions)
        members = chosen['member_numbers']
        pairs = [[1, 3]] if 1 in members and 3 in members else [members[:2]] if len(members) >= 2 else []
        operands = {'document': document, 'bindings': binding, 'selection': chosen,
                    'cells': list(all_cells(document)), 'queries': queries,
                    'selected_pairs': pairs, 'case_policy': 'uppercase'}
        answers = run(operands)
        operand_path, answer_path = OUT / 'filled_examples' / (name + '.operands.json'), OUT / 'filled_examples' / (name + '.results.json')
        records = [write(operand_path, operands), write(answer_path, answers)]
        saved, expected = json.loads(operand_path.read_text()), json.loads(answer_path.read_text())
        pristine = deepcopy(saved)
        with ExitStack() as stack:
            for obj, method in targets:
                stack.enter_context(patch.object(obj, method, forbidden))
            actual = run(saved)
            assert actual == expected
            assert saved == pristine
            assert validate_xmfa_selection(saved['selection']) == saved['selection']
            assert validate_xmfa_coordinates(actual['coordinates']) == actual['coordinates']
            assert validate_xmfa_inverse_coordinates(actual['inverse']) == actual['inverse']
            for key in ('alignment', 'changed_case_alignment'):
                assert validate_xmfa_alignment_components(actual[key]) == actual[key]
            for value in actual['coverage'].values():
                assert validate_xmfa_coverage_components(value) == value
        assert all(digest(ROOT / row['path']) == row['sha256'] for row in records)
        summary.append({'case': name, 'provenance': provenance, 'artifacts': records,
            'exact_replay': True, 'operands_unchanged': True,
            'literal_cells': len(answers['coordinates']['cells']), 'inverse_queries': len(queries),
            'selected_columns': sum(len(b['columns_0based']) for b in chosen['block_columns']),
            'coverage': {basis: [{'member_number': m['member_number'],
                'source_length': m['source_length']['value'], 'known_union_bases': m['known_union_bases']['value'],
                'placement_bases': m['placement_bases']['value'], 'multiply_represented_bases': m['multiply_represented_bases']['value'],
                'excess_placement_bases': m['excess_placement_bases']['value'],
                'fraction': m['selected_coverage_fraction']['value'], 'fraction_state': m['selected_coverage_fraction']['state']}
                for m in answer['members']] for basis, answer in answers['coverage'].items()}})
        print(json.dumps({'case': name, 'saved_bytes': sum(r['bytes'] for r in records), 'exact_saved_replay': True}), flush=True)
    after = {str(path.relative_to(ROOT)): digest(path) for path in paths}
    assert before == after
    record = {'scope': 'Pure calculator verification; no live aligner, BV-BRC service, resource job, model, or episode communication.',
        'cases': summary, 'source_before': before, 'source_after': after, 'source_unchanged': True,
        'blocked_entrypoints': [obj.__name__ + '.' + name for obj, name in targets],
        'new_native_or_service_or_model_or_episode_executions': 0}
    write(OUT / 'SAVED_RECALCULATION.json', record)
    print(json.dumps({'case_count': len(summary), 'source_unchanged': True,
                      'total_saved_bytes': sum(r['bytes'] for case in summary for r in case['artifacts'])}))


if __name__ == '__main__':
    main()
