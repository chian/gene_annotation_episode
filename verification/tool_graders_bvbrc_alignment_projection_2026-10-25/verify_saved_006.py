"""Retain complete saved projection operands and replay without scientific work."""
from contextlib import ExitStack
from copy import deepcopy
import builtins
import hashlib
import json
import math
from pathlib import Path
import socket
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from test_bvbrc_alignment_bundle_projection import (
    saved, values, selection, metric_fields, operands, basic_fixture,
    msa_native_fixture, meta_fixture, cross_family_fixture,
)
from gene_annotation_episode import bvbrc_alignment_bundle_contracts as c
from gene_annotation_episode import bvbrc_alignment_bundle_projection as projection

OUT = Path(__file__).resolve().parent
EXAMPLES = OUT / 'saved_examples_009'
EXAMPLES.mkdir(exist_ok=True)


def digest(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(data).hexdigest(), 'byte_count': len(data)}


source_paths = [ROOT / 'gene_annotation_episode/bvbrc_alignment_bundle_projection.py', ROOT / 'gene_annotation_episode/bvbrc_alignment_bundle_contracts.py', ROOT / 'tests/test_bvbrc_alignment_bundle_projection.py', ROOT / 'tests/test_bvbrc_alignment_bundle_resolution.py', Path(__file__)]
source_before = [digest(path) for path in source_paths]


def fields_for(args):
    aid, results, requests = values(args)
    fields = metric_fields(args)
    fields['requirements'] = {'kind': 'missing_requirements'}
    fields['qualifications'] = {'kind': 'qualifications', 'analysis_id': aid, 'slot_id': None, 'request_id': None}
    for request in requests:
        rid, kind = request['request_id'], request['kind']; value = results[rid]
        if value is None:
            continue
        key = 'collection:' + rid
        if kind == 'msa_entropy':
            fields[key] = selection('msa_sites', aid, rid, columns_0based=[r['column_0based'] for r in value['sites'][:3]])
        elif kind == 'msa_reference_differences':
            fields[key] = selection('reference_differences', aid, rid, row_indices=request['member_row_indices'], columns_0based=[0, 1])
        elif kind == 'function_composition':
            fields[key] = selection('function_composition', aid, rid, function_keys=[r['function_key'] for r in value['rows']])
        elif kind == 'tree':
            fields[key] = selection('tree_branches', aid, rid, node_indices=[r['node_index'] for r in value['branches']])
        elif kind in ('native_group_counts', 'biological_group_counts'):
            groups = value['group_population']['groups'] if kind.startswith('biological') else value['group_order']
            site = value['sites'][0] if value['sites'] else None
            fields[key] = selection('group_counts', aid, rid, columns_0based=[] if site is None else [site['column_0based']], group_ids=[g['group_id'] for g in groups], symbols=[] if site is None else site['symbols'])
        elif kind in ('native_statistics', 'biological_statistics'):
            tests = value['omnibus'][:1] + value['pairs'][:1]
            fields[key] = selection('statistical_tests', aid, rid, tests=[{k: r[k] for k in ('category_id', 'column_0based', 'kind', 'group_ids')} for r in tests])
        elif kind == 'multiplicity':
            fields[key] = selection('multiplicity', aid, rid, family_request_id=None, selection='all_family', tests=[])
        elif kind == 'xmfa_column_coordinates':
            fields[key] = selection('xmfa_coordinates', aid, rid, cells=request['cells'])
        elif kind == 'xmfa_source_positions':
            fields[key] = selection('xmfa_source_positions', aid, rid, queries=request['queries'])
        elif kind == 'xmfa_interval_coverage':
            fields[key] = selection('xmfa_coverage', aid, rid, member_numbers=request['selection']['member_numbers'], include_intervals=True, include_original_coverage=True)
        elif kind == 'xmfa_alignment_components':
            metrics = [{'metric': 'selected_column_count', 'block_index': b['block_index']} for b in value['blocks']]
            metrics += [{'metric': m, 'block_index': 0, 'member_a': 1, 'member_b': 3} for m in ('identical_canonical', 'substitutions', 'comparable_canonical', 'identity_fraction')]
            fields[key] = selection('xmfa_alignment_measurements', aid, rid, measurements=metrics)
    for selected in args['sheet_set']['selections']:
        reader = selected['reader']
        if reader is not None and reader['reader'] == 'msa_frequency':
            fields['native_score'] = {'kind': 'native_measurement', 'analysis_id': aid, 'table': {'analysis_id': aid, 'slot_id': selected['slot_id']}, 'row_index': 0, 'field': {'kind': 'score'}}
    return fields


cases = []
for name in ('dna', 'protein', 'reference', 'original_coverage', 'composition', 'trees', 'ragged_alignment', 'empty_population', 'xmfa', 'xmfa_missing_sources', 'source_distinct_original_occurrences'):
    cases.append(('msa_' + name, saved(name), 'Complete provider examples; synthetic bundle commissioning; retained native outputs where documented by provider.'))
for name in ('official_na', 'aa_two_groups', 'aa_three_groups', 'native_pair_tail_underflow', 'metadata_only_first_group', 'all_missing', 'twelve_groups'):
    cases.append(('metacats_' + name, saved(name, 'metacats'), 'Complete retained native provider example; synthetic bundle commissioning.'))
cases.append(('synthetic_alignment', operands(basic_fixture()), 'Synthetic FASTA and custody; actual parser/provider/adapter.'))
cases.append(('native_msa_adapter', operands(msa_native_fixture()), 'Retained native FASTA/frequency bytes; synthetic custody; actual adapter.'))
cases.append(('synthetic_cross_analysis', operands(cross_family_fixture()), 'Two synthetic analyses with repeated category ID and explicit family.'))

records = []
for name, args, evidence in cases:
    fields = fields_for(args)
    if name == 'synthetic_cross_analysis':
        fields['cross_family'] = {'kind': 'multiplicity', 'analysis_id': None, 'request_id': None, 'family_request_id': 'both', 'selection': 'all_family', 'tests': []}
    original = {**deepcopy(args), 'requested_form': c.requested_form_schema(fields, provider=args['provider'])}
    facts = projection.project_requested_facts(**original)
    path = EXAMPLES / (name + '.inputs.json')
    path.write_text(json.dumps(original, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n')
    answer = EXAMPLES / (name + '.facts.json')
    answer.write_text(json.dumps(facts, indent=2, allow_nan=False) + '\n')
    records.append({'name': name, 'evidence': evidence, 'inputs': digest(path), 'facts': digest(answer), 'selected_fields': len(fields)})

loaded = [(json.loads((ROOT / r['inputs']['path']).read_text()), json.loads((ROOT / r['facts']['path']).read_text())) for r in records]


def forbidden(*args, **kwargs):
    raise AssertionError('Saved projection attempted I/O, scientific calculation or native parsing')


blocked = []
with ExitStack() as guard:
    for owner, name in ((builtins, 'open'), (Path, 'open'), (Path, 'read_bytes'), (Path, 'read_text'), (Path, 'write_bytes'), (Path, 'write_text'), (socket, 'socket'), (socket, 'create_connection'), (subprocess, 'Popen'), (subprocess, 'run')):
        guard.enter_context(patch.object(owner, name, forbidden)); blocked.append(str(owner) + '.' + name)
    for name in ('log', 'log2', 'exp', 'sqrt', 'fsum'):
        guard.enter_context(patch.object(math, name, forbidden)); blocked.append('math.' + name)
    calculation_names = {'alignment_components', 'original_member_coverage', 'tree_components', 'function_composition', 'taxon_components', 'compare_unrooted_relationships', 'msa_native_entropy', 'msa_reference_differences', 'metacats_group_counts', 'metacats_statistics', 'metacats_effects', 'biological_group_counts', 'biological_group_statistics', 'biological_group_effects', 'expected_count_adequacy', 'adjust_p_values', 'xmfa_column_coordinates', 'xmfa_source_positions', 'xmfa_alignment_components', 'xmfa_interval_coverage'}
    for name, module in list(sys.modules.items()):
        if not name.startswith('gene_annotation_episode.') or module is None:
            continue
        for attribute, value in list(vars(module).items()):
            if callable(value) and (attribute in calculation_names or attribute.startswith(('parse_', 'calculate_'))):
                guard.enter_context(patch.object(module, attribute, forbidden)); blocked.append(name + '.' + attribute)
    for original, facts in loaded:
        assert projection.project_requested_facts(**original) == facts
        assert projection.validate_projected_facts(facts, **original) == facts

source_after = [digest(path) for path in source_paths]
assert source_before == source_after, 'Source changed during verification'
receipt = {'status': 'passed', 'examples': len(records), 'selected_fields': sum(r['selected_fields'] for r in records), 'native_jobs_executed': 0, 'scope': 'Exact saved-cell projection and validation, no scientific recalculation or episode/live custody claim.', 'records': records, 'blocked_entrypoints': blocked, 'source_hashes_before': source_before, 'source_hashes_after': source_after}
(OUT / 'SAVED_REPLAY_009.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k: receipt[k] for k in ('status', 'examples', 'selected_fields', 'native_jobs_executed')}))
