"""Recalculate the retained host sheet with explicit thresholds and no acquisition."""
from pathlib import Path
import hashlib
import importlib
import json
import socket
import sys

OUT = Path(__file__).resolve().parent
CANDIDATE = OUT / 'candidate'
sys.path.insert(0, str(CANDIDATE))
from gene_annotation_episode.bvbrc_proteome_calculators import calculate_native_components
from gene_annotation_episode.bvbrc_proteome_bundle_contracts import canonical

example = OUT / 'numerical_example_final_002'
sheet_bytes = (example / 'SHEET.json').read_bytes()
saved = json.loads(sheet_bytes)
original = json.loads((example / 'COMPONENTS.json').read_text())
parameters = {**saved['parameters']['calculation_parameters'], 'minimum_identity_fraction': .9}

def forbidden(*args, **kwargs):
    raise AssertionError('saved recalculation attempted acquisition or native construction')

for name, functions in {
    'bvbrc_proteome_native': ['parse_genome_comparison'],
    'bvbrc_proteome_inputs': ['index_original_inputs', 'read_protein_fasta', 'read_feature_metadata', 'read_genome_metadata', 'read_feature_sequences'],
    'bvbrc_proteome_joins': ['build_native_joins'],
    'bvbrc_proteome_sheet': ['build_native_sheet'],
    'bvbrc_proteome_bundle_resolution': ['consume_bundle', 'parse_genome_comparison', 'index_original_inputs',
        'read_protein_fasta', 'read_feature_metadata', 'read_genome_metadata', 'read_feature_sequences', 'build_native_joins', 'build_native_sheet'],
}.items():
    module = importlib.import_module('gene_annotation_episode.' + name)
    for function in functions:
        setattr(module, function, forbidden)
socket.create_connection = forbidden
revised = calculate_native_components(saved['native_sheet_result']['value'], parameters=parameters)
assert original['value']['tracks'][0]['selection_counts']['pass']['value'] == 1
assert revised['value']['tracks'][0]['selection_counts']['pass']['value'] == 0
assert original['value']['sheet_sha256'] == revised['value']['sheet_sha256']
assert (example / 'SHEET.json').read_bytes() == sheet_bytes
(example / 'RECALCULATED_COMPONENTS.json').write_text(json.dumps(revised, indent=2) + '\n')
print(json.dumps({'python': sys.executable, 'calculator_module': sys.modules[calculate_native_components.__module__].__file__,
    'original_selected': 1, 'recalculated_selected': 0, 'parameters': parameters,
    'original_sheet_sha256': hashlib.sha256(sheet_bytes).hexdigest(),
    'numerical_sheet_sha256': original['value']['sheet_sha256'], 'native_acquisitions': 0}))
