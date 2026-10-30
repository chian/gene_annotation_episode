"""Reproduce full D numerical sheets using retained local fixtures only.

Native documents derive from retained upstream Mauve examples. All C task,
source custody, alias and interval/original-map witnesses are synthetic tests.
No scientific program, service, model, install, workflow or HPC call is made.
"""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from test_bvbrc_genome_alignment_sheet import fixture_data, fixture_sheet, all_requests, plan
from test_bvbrc_genome_alignment_calculators import (
    IO_AND_PARSERS, SCIENCE, forbidden, values, internal_seven_data, original_map_data)
from gene_annotation_episode.bvbrc_genome_alignment_calculators import (
    calculate_genome_alignment_components, recalculate_genome_alignment_sheet)
from gene_annotation_episode.bvbrc_genome_alignment_sheet import (
    build_genome_alignment_sheet, validate_genome_alignment_sheet)


def write(name, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    (OUT / name).write_bytes(raw)
    return {'path': name, 'sha256': hashlib.sha256(raw).hexdigest(), 'byte_count': len(raw)}


sheet = fixture_sheet()
requested = all_requests()
requested[1]['selection']['minimum_selected_multiplicity'] = 3
requested[2]['selection']['minimum_selected_multiplicity'] = 3
requested[4]['basis'] = 'cooccupied_column'
before = deepcopy(sheet)
with ExitStack() as stack:
    for target in IO_AND_PARSERS:
        stack.enter_context(patch(target, forbidden))
    recalculated = recalculate_genome_alignment_sheet(sheet, calculation_plan=plan(requested))
    assert sheet == before
with ExitStack() as stack:
    for target in IO_AND_PARSERS + SCIENCE:
        stack.enter_context(patch(target, forbidden))
    assert validate_genome_alignment_sheet(sheet) == sheet
    assert validate_genome_alignment_sheet(recalculated) == recalculated

missing_data = fixture_data(with_inputs=False, with_associations=False, include_missing=True)
missing_requests = all_requests()
missing_requests[2]['xmfa_document_slot_id'] = 'missing'
missing = build_genome_alignment_sheet(data=missing_data, components=calculate_genome_alignment_components(
    missing_data, calculation_plan=plan(missing_requests)))
seven_data = internal_seven_data()
seven = build_genome_alignment_sheet(data=seven_data, components=calculate_genome_alignment_components(
    seven_data, calculation_plan=plan([all_requests()[2]])))
map_data = original_map_data()
mapped = build_genome_alignment_sheet(data=map_data, components=calculate_genome_alignment_components(
    map_data, calculation_plan=plan(all_requests()[4:])))

artifacts = [write(name, value) for name, value in (
    ('NATIVE_EXAMPLE_SYNTHETIC_C_SHEET.json', sheet),
    ('RECALCULATED_K3_COOCCUPIED_SHEET.json', recalculated),
    ('MISSING_INPUTS_SECONDARY_SHEET.json', missing),
    ('SYNTHETIC_INTERNAL7_EXPORTED0_SHEET.json', seven),
    ('SYNTHETIC_ORIGINAL_MAP_SHEET.json', mapped))]
native = values(sheet['components']); changed = values(recalculated['components'])
summary = {
    'provenance': {
        'native_bytes': 'Retained upstream Mauve v4/backbone/BBCols/XMFA examples; existing receipts remain unchanged.',
        'C_bindings': 'Synthetic original task, input/source custody, member aliases, interval and original-coordinate witnesses; not authenticated BV-BRC output.',
        'internal7_case': 'Intentionally altered native sidecar tokens and a synthetic explicit 7-to-0 interval witness.',
        'execution': 'Pure local Python parsing/validation/calculation tests only; no native program/service/model/HPC/episode execution.'},
    'checks': {'no_io_or_parser_recalculation': 'passed', 'no_science_or_source_comparison_replay': 'passed',
        'prior_sheet_unchanged': 'passed'},
    'numbers': {
        'v4_coverage': [[r['known_union_bases']['value'], r['denominator_bases']['value'], r['coverage_fraction']['value']] for r in native['anchors']['coverage']],
        'backbone_k2': [r['known_union_bases']['value'] for r in native['backbone']['coverage']],
        'backbone_k3': [r['known_union_bases']['value'] for r in changed['backbone']['coverage']],
        'bbcols_k2': {k: native['columns']['intervals'][0][k]['value'] for k in ('union_columns', 'column_placements', 'bound_block_width', 'selected_block_fraction')},
        'bbcols_k3': {k: changed['columns']['intervals'][0][k]['value'] for k in ('union_columns', 'bound_block_width', 'selected_block_fraction')},
        'xmfa_pair1_2': {k: native['pairs']['blocks'][0]['pairs'][0][k]['value'] for k in ('identical_canonical', 'substitutions', 'comparable_canonical', 'identity_fraction')},
        'xmfa_cooccupied': [[r['known_union_bases']['value'], r['source_length']['value'], r['selected_coverage_fraction']['value']] for r in changed['coverage']['members']],
        'original_coordinate': values(mapped['components'])['cell']['cells'][0]['original_coordinates'][0]},
    'artifacts': artifacts,
    'remaining': ['D is not the E provider facade, F return custody, host registration, selected child path or production integration.',
        'Synthetic positive C fixtures do not establish authentic staged source/census/interval witnesses for a service run.',
        'No live service, native scientific executable, model or HPC run was performed.']}
write('VERIFICATION_NUMBERS.json', summary)
print(json.dumps({'checks': summary['checks'], 'numbers': summary['numbers'], 'artifacts': artifacts}, indent=2))

owned = [ROOT / 'gene_annotation_episode' / (name + '.py') for name in (
    'bvbrc_genome_alignment_calculation_contracts', 'bvbrc_genome_alignment_sheet', 'bvbrc_genome_alignment_calculators')]
owned += [ROOT / 'tests' / ('test_' + p.name) for p in owned]
dependencies = ['mauve_v4_calculation_contracts.py', 'mauve_v4_calculators.py', 'mauve_v4_format_contracts.py',
    'mauve_v4_formats.py', 'mauve_backbone_contracts.py', 'mauve_backbone_calculators.py', 'mauve_backbone_formats.py',
    'xmfa_calculation_contracts.py', 'xmfa_calculators.py', 'xmfa_coordinates.py', 'xmfa_format_contracts.py',
    'xmfa_formats.py', 'xmfa_source_contracts.py', 'xmfa_sources.py', 'bvbrc_genome_alignment_input_contracts.py',
    'bvbrc_alignment_values.py', 'phylogeny_calculation_contracts.py', 'phylogeny_format_contracts.py',
    'bvbrc_appservice_contracts.py', 'bvbrc_appservice_schemas.json']
write('SOURCE_HASHES_FINAL.json', {'created_utc': datetime.now(timezone.utc).isoformat(),
    'files': [{'path': str(p.relative_to(ROOT)),
        'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'byte_count': p.stat().st_size}
        for p in owned + [ROOT / 'gene_annotation_episode' / name for name in dependencies]]})
