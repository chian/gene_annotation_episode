"""Reproduce E examples using real upstream native bytes and synthetic custody.

This verification script writes artifacts; the production pure facade does not.
Run from the repository root with .venv/bin/python and no external service.
"""
from base64 import b64encode
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from gene_annotation_episode import bvbrc_genome_alignment_bundle_adapter as facade
from gene_annotation_episode import bvbrc_genome_alignment_bundle_projection as projection
from test_bvbrc_genome_alignment_bundle_resolution import arguments, measurement, member, scientific_artifact, replace_native
from test_bvbrc_genome_alignment_bundle_projection import saved_arguments, synthetic_original_sheet, CELL
from test_bvbrc_genome_alignment_sheet import plan, slot

OUT = Path(__file__).parent


def write(name, value):
    (OUT / name).write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')


def call_record(args):
    serialized = {k: deepcopy(v) for k, v in args.items() if k != 'artifact_bytes'}
    serialized['artifact_bytes_base64'] = {key: {'byte_count': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
        'base64': b64encode(raw).decode('ascii')} for key, raw in args['artifact_bytes'].items()}
    return {'provenance': 'Native file bytes are retained upstream examples. OriginalTask, receipt envelopes, Workspace objects, manifest and custody are synthetic test data; this is not host/live execution evidence.',
        'arguments': serialized, 'result': facade.consume_bundle(**args)}


def main():
    examples = {}
    for fmt in ('mauve_v4', 'mauve1_xmfa', 'mauve_backbone', 'mauve_bbcols'):
        examples[fmt] = call_record(arguments(fmt))
    args = arguments(); first = deepcopy(args['parameters']['calculation_plan']['requests'][0])
    args['parameters']['document_slots'].append(dict(slot('absent', 'mauve_v4'), source_ref='absent:source'))
    args['parameters']['calculation_plan'] = plan([dict(deepcopy(first), request_id='missing-first', document_slot_id='absent'),
                                                 dict(deepcopy(first), request_id='retained-second')])
    args['requested_form'] = facade.requested_form_schema({'first': measurement('missing-first'), 'second': measurement('retained-second')})
    examples['missing_first_request'] = call_record(args)
    write('FILLED_PUBLIC_FACADE_EXAMPLES_001.json', examples)

    sheet, original = synthetic_original_sheet()
    fields = {
        'v4_member': measurement('anchors', 'v4_member', 'alignment_columns', interval_index=0, segment_index=0, member=member()),
        'v4_pair': measurement('anchors', 'v4_pair', 'identity_fraction', interval_index=0, segment_index=0, pair={'member_a': member(), 'member_b': member(1)}),
        'v4_coverage': measurement(field='coverage_fraction'),
        'backbone_row': measurement('backbone', 'backbone_row', 'selected_member_count', row_index=0),
        'backbone_span': measurement('backbone', 'backbone_span', 'span_bases', row_index=0, member=member(0, 'mauve_sidecar_member_0based')),
        'backbone_coverage': measurement('backbone', 'backbone_coverage', 'known_union_bases', member=member(0, 'mauve_sidecar_member_0based')),
        'bbcols_row': measurement('columns', 'bbcols_row', 'column_count', row_index=0),
        'bbcols_interval': measurement('columns', 'bbcols_interval', 'union_columns', native_interval_index_0based=0),
        'xmfa_block': measurement('pairs', 'xmfa_block', 'selected_column_count', block_index=0),
        'xmfa_site': measurement('pairs', 'xmfa_site', 'canonical_count', block_index=0, column_0based=0),
        'xmfa_symbol': measurement('pairs', 'xmfa_symbol', 'count', block_index=0, column_0based=0, symbol='T'),
        'xmfa_pair': measurement('pairs', 'xmfa_pair', 'identity_fraction', block_index=0, member_a=1, member_b=2),
        'xmfa_coverage': measurement('coverage', 'xmfa_coverage', 'source_length', member_number=1),
        'xmfa_original_coverage': measurement('coverage', 'xmfa_original_coverage', 'coverage_fraction', member_number=1, original_member=original),
        'native_coordinate': {'kind': 'xmfa_native_coordinate', 'request_id': 'cell', 'cell': CELL},
        'source_coordinate': {'kind': 'xmfa_source_coordinate', 'request_id': 'cell', 'cell': CELL},
        'original_coordinate': {'kind': 'xmfa_original_coordinates', 'request_id': 'cell', 'cell': CELL},
        'inverse_coordinate': {'kind': 'xmfa_inverse_coordinates', 'request_id': 'inverse', 'query': {'member_number': 1, 'position_0based': 49}},
        'requirements': {'kind': 'missing_requirements', 'scope': 'all', 'request_id': None},
        'qualifications': {'kind': 'qualifications', 'scope': 'all', 'request_id': None},
    }
    saved = saved_arguments(sheet, fields)
    write('FILLED_SAVED_NUMERICAL_CATALOG_001.json', {'provenance': 'Actual upstream native and source bytes; synthetic C source, feature-map and association witnesses exercise stored numerical dependency paths only. Current C producers cannot authenticate these same-run source witnesses. Strict no-arithmetic replay is blocked by existing D/native validators, recorded separately.',
        'arguments': saved, 'projection': projection.project_genome_alignment_facts(**saved)})

    corrected = {}
    for edge in ('unsupported_native_version', 'unrepresentable_native_symbol'):
        fields = {'independent': measurement('pairs', 'xmfa_block', 'selected_column_count', block_index=0),
                  'selected': {'kind': 'xmfa_native_coordinate', 'request_id': 'cell', 'cell': CELL}}
        args = arguments('mauve1_xmfa', fields)
        replace_native(args, (OUT / 'edge_cases' / (edge + '.xmfa')).read_bytes())
        corrected[edge] = call_record(args)
    write('EDGE_CASE_RESULTS_AFTER_012.json', corrected)
    print('Saved full public-facade, fourteen-family catalog, and accepted012 edge examples.')


if __name__ == '__main__':
    main()
