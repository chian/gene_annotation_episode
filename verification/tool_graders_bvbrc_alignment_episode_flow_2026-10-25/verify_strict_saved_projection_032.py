"""Strict replay barriers on retained adapter examples; no new custody claim."""
import cProfile
import hashlib
import importlib
import json
import math
from pathlib import Path
import pstats
import socket
import subprocess
import sys

EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
import pytest
from test_bvbrc_alignment_episode_flow import block_saved_scientific_work
from gene_annotation_episode.bvbrc_alignment_bundle_projection import validate_projected_facts
from gene_annotation_episode.execution_contracts import digest

EXAMPLES = ROOT / 'verification/tool_graders_bvbrc_alignment_bundle_2026-10-25/EXAMPLES_010'
cases = []
hashes = {}
for path in sorted(EXAMPLES.glob('*.result.json')):
    operand = path.with_name(path.name.replace('.result.json', '.operands.json'))
    for item in (path, operand):
        hashes[str(item.relative_to(ROOT))] = hashlib.sha256(item.read_bytes()).hexdigest()
    cases.append((path.name.removesuffix('.result.json'), json.loads(path.read_text()), json.loads(operand.read_text())))

def forbidden(*args, **kwargs):
    raise AssertionError('Strict saved projection attempted scientific computation or acquisition')

with pytest.MonkeyPatch.context() as patch:
    patch.setattr(socket.socket, 'connect', forbidden)
    patch.setattr(subprocess, 'run', forbidden)
    patch.setattr(subprocess, 'Popen', forbidden)
    parser = importlib.import_module('gene_annotation_episode.phylogeny_formats')
    consumer = importlib.import_module('gene_annotation_episode.bvbrc_alignment_bundle_resolution')
    patch.setattr(consumer, '_test_retained_parser_alias', parser.parse_aligned_fasta, raising=False)
    patch.setattr(parser, 'parse_aligned_fasta', forbidden)
    blocked = block_saved_scientific_work(patch, forbidden)
    assert consumer._test_retained_parser_alias is forbidden
    xmfa = importlib.import_module('gene_annotation_episode.xmfa_calculation_contracts')
    # These controls prove the barriers reject actual reached helper families.
    for function, args in ((math.log2, (2,)), (xmfa.union_intervals, ([[0, 1]],)),
            (xmfa.interval_length, ([[0, 1]],)), (xmfa.multiplicity_bases, ([[0, 1]],)),
            (xmfa.complement_intervals, ([], 1)), (xmfa.validate_xmfa_alignment_components, ({},)),
            (xmfa.validate_xmfa_coverage_components, ({},))):
        with pytest.raises(AssertionError, match='Strict saved projection'):
            function(*args)
    profile = cProfile.Profile()
    results = []
    for name, saved, operands in cases:
        args = {'sheet_set': saved['sheet'], 'component_set': saved['components'],
            'missing_requirements': tuple(saved['missing_requirements']),
            'diagnostics': tuple(saved['diagnostics']), 'requested_form': operands['requested_form'],
            'parameters': operands['parameters'], 'provider': operands['provider']}
        actual = profile.runcall(validate_projected_facts, saved['facts'], **args)
        assert actual == saved['facts']
        results.append({'name': name, 'facts_sha256': digest(actual), 'facts': actual,
            'original_status': saved['status'], 'source_custody': 'original E example synthetic custody; pure projection only'})

calls = [{'path': str(Path(path).relative_to(ROOT)), 'line': line, 'function': function,
    'calls': values[1], 'cumulative_seconds': values[3]}
    for (path, line, function), values in pstats.Stats(profile).stats.items()
    if path.startswith(str(ROOT / 'gene_annotation_episode'))]
assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == value for path, value in hashes.items())
receipt = {'status': 'eight_strict_saved_projections_passed', 'workflow_started': False,
    'host_custody_exercised': False, 'new_calculation': False,
    'blocked_implementations_and_aliases': blocked, 'barrier_rejection_controls': 7, 'preexisting_parser_alias_replaced': True,
    'source_hashes': hashes, 'results': results, 'local_calls': calls,
    'test_source_sha256': hashlib.sha256((ROOT / 'tests/test_bvbrc_alignment_episode_flow.py').read_bytes()).hexdigest()}
(EVIDENCE / 'strict-saved-projection-032.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'status': receipt['status'], 'cases': len(results),
    'blocked_symbols': len(blocked), 'barrier_rejection_controls': 7, 'preexisting_parser_alias_replaced': True,
    'executed_package_modules': sorted({row['path'] for row in calls})}))
