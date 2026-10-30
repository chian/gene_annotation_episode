"""Reproduce F examples from retained bytes and explicitly synthetic custody.

Run from the repository root with .venv/bin/python. No service/native job is
invoked. D/E calculations construct the examples before saved-only F reads.
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]

from test_bvbrc_genome_alignment_returns import (
    example, facade_example, project, fact_form, FACT_SOURCES,
)
from test_bvbrc_genome_alignment_associations import V4_NATIVE, NATIVE_DIR
from test_bvbrc_genome_alignment_returns_original import mapped_example

OUT = Path(__file__).resolve().parent


def snapshot(args):
    body, sheet, components = args
    saved = body['publication']['adapter_result']
    return {'status': saved['status'], 'facts': project(args),
        'saved_content_bindings': {k: saved[k] for k in ('sheet_content', 'components_content')},
        'original_parameters': body['publication_inputs']['adapter']['parameters'],
        'original_requested_schema': body['publication_inputs']['selector']['requested_schema'],
        'sheet_present': sheet is not None, 'components_present': components is not None}


def wrong_task(args):
    args['bundle']['original_task'].update(required_application_id='MSA', native_application_id='MSA')
    args['retained_records'] = ()


native_files = [V4_NATIVE, *(NATIVE_DIR / name for name in (
    'separate.xmfa', 'separate.xmfa.backbone', 'separate.xmfa.bbcols'))]
value = {
    'qualification': 'Retained native output bytes; synthetic task/input/association witnesses and publication envelopes. No live BV-BRC job, authenticated production publication chain, or complete selected-episode integration is claimed.',
    'generation': 'Actual D calculators and E facade/projection build saved values; F projects those values without acquisition or invoking scientific APIs. Strict no-arithmetic replay remains blocked by shared D/native validators until their separate correction.',
    'retained_native_inputs': [{'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'byte_count': path.stat().st_size} for path in native_files],
    'closed_return_schema': fact_form(*FACT_SOURCES),
    'all_twelve_families': snapshot(example()),
    'explicitly_synthetic_original_member_map': snapshot(mapped_example()[0]),
    'four_actual_e_facade_results': {fmt: snapshot(facade_example(fmt)) for fmt in (
        'mauve_v4', 'mauve_backbone', 'mauve_bbcols', 'mauve1_xmfa')},
    'missing_bytes': snapshot(facade_example(change=lambda args: args['artifact_bytes'].clear())),
    'invalid_wrong_application': snapshot(facade_example(change=wrong_task)),
}
(OUT / 'FILLED_EXAMPLES_001.json').write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
print(json.dumps({'output': str((OUT / 'FILLED_EXAMPLES_001.json').relative_to(ROOT)),
    'retained_numbers': {'xmfa_identity': 40 / 48, 'v4_coverage': 690 / 693, 'measured_gap_count': 0,
        'bbcols_union_columns': 52, 'xmfa_reverse_position_1based': 50, 'xmfa_reverse_position_0based': 49,
        'synthetic_original_position_0based': 59, 'synthetic_original_coverage': 50 / 100}}, indent=2))
