"""Small neutral-output probes, not an implementation of the proposed provider."""
from copy import deepcopy
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import urllib.request
from unittest.mock import patch

from gene_annotation_episode.mauve_v4_calculators import calculate_mauve_v4_segments
from gene_annotation_episode.mauve_v4_calculation_contracts import validate_mauve_v4_components
from gene_annotation_episode.mauve_backbone_calculators import calculate_mauve_backbone_components, calculate_mauve_bbcols_components
from gene_annotation_episode.mauve_backbone_contracts import validate_mauve_backbone_components, validate_mauve_bbcols_components
from gene_annotation_episode.xmfa_sources import bind_xmfa_sources
from gene_annotation_episode.xmfa_source_contracts import validate_xmfa_source_bindings
from gene_annotation_episode.xmfa_calculators import xmfa_alignment_components, xmfa_interval_coverage
from gene_annotation_episode.xmfa_coordinates import xmfa_column_coordinates, xmfa_source_positions
from gene_annotation_episode.xmfa_calculation_contracts import validate_xmfa_alignment_components, validate_xmfa_coverage_components, validate_xmfa_coordinates, validate_xmfa_inverse_coordinates
from gene_annotation_episode.bvbrc_genome_alignment_input_contracts import validate_genome_alignment_inputs, validate_genome_alignment_associations

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
def read(relative):
    return json.loads((ROOT / relative).read_text())

b = read('verification/tool_graders_mauve_sidecars_2026-10-25/FILLED_EXAMPLES_001.json')
xoperand = read('verification/tool_graders_bvbrc_xmfa_sources_2026-10-25/saved_examples/separate_native-inputs.json')
vdoc = read('verification/tool_graders_mauve_v4_2026-10-25/official_small.document.json')
vold = read('verification/tool_graders_mauve_v4_2026-10-25/official_small.components.json')
xd = xoperand['document']
# Third-party JSON-schema vocabularies are configuration-time lazy resources.
# Warm them before enforcing the no-I/O scientific/replay boundary.
validate_genome_alignment_inputs(b['synthetic_source_inputs'])
validate_genome_alignment_associations(b['synthetic_associations'])
selection = {'population_id': 'provider-boundary-explicit-all-native-columns', 'document_id': xd['document_id'],
    'member_numbers': [1, 2, 3], 'block_columns': [{'block_index': block['block_index'],
    'columns_0based': list(range(max(len(row['sequence']) for row in block['records'])))} for block in xd['blocks']],
    'completeness': 'complete', 'evidence': []}
def forbidden(*args, **kwargs):
    raise AssertionError('forbidden I/O/parser/calculator during probe phase')

with ExitStack() as stack:
    for target in ['builtins.open', 'pathlib.Path.read_text', 'pathlib.Path.read_bytes',
        'subprocess.Popen', 'socket.create_connection', 'urllib.request.urlopen',
        'gene_annotation_episode.mauve_v4_formats.parse_mauve_v4',
        'gene_annotation_episode.mauve_backbone_formats.parse_mauve_backbone',
        'gene_annotation_episode.mauve_backbone_formats.parse_mauve_bbcols',
        'gene_annotation_episode.xmfa_formats.parse_mauve_xmfa']:
        stack.enter_context(patch(target, forbidden))
    v4 = calculate_mauve_v4_segments(vdoc, selection=vold['selection'], inputs=None)
    assert v4 == vold
    backbone = {}
    bbcols = {}
    for k in [2, 3]:
        bs = deepcopy(b['backbone_k2']['selection']); bs['minimum_selected_multiplicity'] = k
        cs = deepcopy(b['bbcols_k2']['selection']); cs['minimum_selected_multiplicity'] = k
        backbone[str(k)] = calculate_mauve_backbone_components(b['backbone_document'], selection=bs, inputs=b['synthetic_source_inputs'])
        bbcols[str(k)] = calculate_mauve_bbcols_components(b['bbcols_document'], selection=cs,
            xmfa_document=b['xmfa_document'], associations=b['synthetic_associations'])
        assert backbone[str(k)] == b[f'backbone_k{k}']
        assert bbcols[str(k)] == b[f'bbcols_k{k}']
    native_bbcols = calculate_mauve_bbcols_components(b['bbcols_document'], selection=b['bbcols_k2']['selection'],
        xmfa_document=None, associations=None)
    bindings = bind_xmfa_sources(xd, inputs=xoperand['inputs'],
        source_comparison='case_insensitive_iupac_exact')
    alignment = xmfa_alignment_components(xd, selection=selection, selected_pairs=((1, 2), (1, 3), (2, 3)), case_policy='uppercase')
    coverage = {basis: xmfa_interval_coverage(xd, selection=selection, bindings=bindings, basis=basis)
        for basis in ['represented', 'multi_member_block', 'cooccupied_column']}
    coordinates = xmfa_column_coordinates(xd, cells=({'block_index': 0, 'record_index': 0, 'column_0based': 0},), bindings=bindings)
    inverse = xmfa_source_positions(xd, queries=({'member_number': 1, 'position_0based': 49},), bindings=bindings)

with ExitStack() as stack:
    for target in ['builtins.open', 'pathlib.Path.read_text', 'pathlib.Path.read_bytes',
        'gene_annotation_episode.mauve_v4_calculators.calculate_mauve_v4_segments',
        'gene_annotation_episode.mauve_backbone_calculators.calculate_mauve_backbone_components',
        'gene_annotation_episode.mauve_backbone_calculators.calculate_mauve_bbcols_components',
        'gene_annotation_episode.xmfa_sources.bind_xmfa_sources',
        'gene_annotation_episode.xmfa_sources.validate_xmfa_bindings_for_document',
        'gene_annotation_episode.xmfa_calculators.xmfa_alignment_components',
        'gene_annotation_episode.xmfa_calculators.xmfa_interval_coverage',
        'gene_annotation_episode.xmfa_coordinates.xmfa_column_coordinates',
        'gene_annotation_episode.xmfa_coordinates.xmfa_source_positions']:
        stack.enter_context(patch(target, forbidden))
    assert validate_mauve_v4_components(v4) == v4
    for value in backbone.values(): assert validate_mauve_backbone_components(value) == value
    for value in [*bbcols.values(), native_bbcols]: assert validate_mauve_bbcols_components(value) == value
    assert validate_xmfa_source_bindings(bindings) == bindings
    assert validate_xmfa_alignment_components(alignment) == alignment
    for value in coverage.values(): assert validate_xmfa_coverage_components(value) == value
    assert validate_xmfa_coordinates(coordinates) == coordinates
    assert validate_xmfa_inverse_coordinates(inverse) == inverse

report = {
    'scope': 'Existing neutral functions only; no proposed D/E/F production implementation tested',
    'provenance': {'native_documents': 'Retained real Mauve examples from A/B verification; see referenced receipts',
        'source_and_task_and_interval_bindings': 'Synthetic offline fixtures from B, NOT an authentic BV-BRC run',
        'live_service_or_job_or_episode_execution': False},
    'checks': {'saved_native_recalculation_without_io_or_parsers': 'passed',
        'saved_component_validation_without_scientific_calculators_or_source_comparison': 'passed',
        'exact_A_B_saved_reproduction': 'passed'},
    'v4': v4, 'backbone': backbone, 'bbcols': bbcols, 'bbcols_without_join': native_bbcols,
    'xmfa_bindings': bindings, 'xmfa_alignment': alignment, 'xmfa_coverage': coverage,
    'xmfa_coordinates': coordinates, 'xmfa_inverse': inverse}
payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n'
(OUT / 'OFFLINE_EXAMPLES_001.json').write_text(payload)
print(json.dumps({'checks': report['checks'], 'artifact': str(OUT / 'OFFLINE_EXAMPLES_001.json'),
    'sha256': hashlib.sha256(payload.encode()).hexdigest()}, indent=2))
