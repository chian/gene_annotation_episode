"""Retained public native reports and offline saved-observation recalculation."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from unittest.mock import patch
import urllib.request

EVIDENCE = Path(__file__).resolve().parent
CANDIDATE = EVIDENCE.parent / 'candidate'
sys.path.insert(0, str(CANDIDATE))

from gene_annotation_episode import bvbrc_proteome_directional as reader
from gene_annotation_episode.bvbrc_proteome_directional_sheet import build_directional_sheet
from gene_annotation_episode.bvbrc_proteome_directional_calculators import calculate_directional_components
from gene_annotation_episode.bvbrc_proteome_directional_numerical_contracts import (
    canonical_sheet_sha256, validate_directional_numerical,
)

FILES = {
    '2011': ('biopython_text_2011L_blastp_002.txt', 'c122ef42cd2d2da7ae5318045aa88a73c84713572a2c14d15c562117f3eec62d'),
    '2202': ('biopython_text_2202L_blastp_001.txt', 'c0f5e5d3541500aef1ac93957fe35fbd4481f5788314e3e12ed1ea5f9d16510a'),
    '2221': ('biopython_text_2221L_blastp_001.txt', 'e8bcff01bf827d936c36f00e4bbb73f2b5b1dd99b4d37af4cb9a6b0de44e25f8'),
}
PARAMETERS = {'version': 'bvbrc_proteome_directional_parameters_v1',
    'formula_version': 'displayed_blastp_correspondence_v1',
    'amino_acid_alphabet': 'standard20', 'ratio_decimal_places': 18, 'rounding': 'half_even'}
REPLAY_PARAMETERS = {**PARAMETERS, 'amino_acid_alphabet': 'standard20_plus_uo', 'ratio_decimal_places': 7}


def digest(path):
    data = path.read_bytes()
    return {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def write(name, value):
    path = EVIDENCE / name
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')
    return {'path': name, **digest(path)}


def package_hashes():
    return {str(p.relative_to(CANDIDATE)): digest(p)
            for p in sorted((CANDIDATE / 'gene_annotation_episode').glob('*'))
            if p.suffix in ('.py', '.json')}


def population(calculated):
    report = calculated['reports'][0]
    return {name: report[name]['value'] for name in (
        'displayed_query_count', 'displayed_description_count', 'displayed_subject_count',
        'displayed_hsp_count', 'displayed_block_count')}


def main():
    started = datetime.now(timezone.utc).isoformat()
    before = package_hashes()
    rows = []
    saved = []
    for label, (filename, expected_sha) in FILES.items():
        path = CANDIDATE / 'tests' / 'fixtures' / 'bvbrc_proteome_directional' / filename
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == expected_sha
        source = {'content': {'source_ref': 'retained-public-fixture:' + filename,
            'artifact_field': 'stdout_ref', 'artifact_ref': 'retained-public-fixture:' + filename,
            'sha256': expected_sha, 'byte_count': len(data)},
            'body_complete': True, 'object_complete': 'yes'}
        native = reader.parse_genome_comparison_directional_report(data, source=source,
            declared_format='ncbi_blastall_blastp_pairwise_text_v1', report_key=filename)
        observed_result = build_directional_sheet([native])
        assert observed_result['state'] == 'available'
        observed = observed_result['sheet']
        result = calculate_directional_components(observed, parameters=PARAMETERS)
        assert result['components'] is not None
        scoring = {'version': 'bvbrc_proteome_directional_scoring_sheet_v1',
                   'observed': observed, 'calculated': result['components']}
        validate_directional_numerical('DirectionalComponentsResult', result, sheet=observed)
        validate_directional_numerical('DirectionalScoringSheet', scoring)
        artifact = write('native_' + label + '_scoring_sheet_001.json', scoring)
        row = {'native_file': str(path.relative_to(CANDIDATE)), 'native': digest(path),
               'reader_state': native['state'], 'sheet_state': observed_result['state'],
               'calculation_state': result['state'], 'population': population(scoring['calculated']),
               'sheet_sha256': canonical_sheet_sha256(observed), 'artifact': artifact,
               'diagnostic_codes': sorted({i['code'] for i in result['diagnostics']})}
        rows.append(row)
        saved.append(json.loads((EVIDENCE / artifact['path']).read_text(encoding='utf-8')))

    blocked_calls = []
    def forbidden(*args, **kwargs):
        blocked_calls.append('forbidden acquisition/parsing/I/O called')
        raise AssertionError(blocked_calls[-1])

    targets = [(reader, 'parse_genome_comparison_directional_report'),
        ('builtins', 'open'), (io, 'open'), (Path, 'open'),
        (socket, 'socket'), (socket, 'create_connection'),
        (urllib.request, 'urlopen'), (subprocess, 'Popen'), (subprocess, 'run'),
        (subprocess, 'call'), (subprocess, 'check_call'), (subprocess, 'check_output'),
        (os, 'system'), (os, 'popen')]
    for name in ('execl', 'execle', 'execlp', 'execlpe', 'execv', 'execve', 'execvp', 'execvpe',
                 'spawnl', 'spawnle', 'spawnlp', 'spawnlpe', 'spawnv', 'spawnve', 'spawnvp', 'spawnvpe'):
        if hasattr(os, name): targets.append((os, name))
    replayed = []
    with ExitStack() as stack:
        for obj, name in targets:
            if isinstance(obj, str): stack.enter_context(patch(obj + '.' + name, forbidden))
            else: stack.enter_context(patch.object(obj, name, forbidden))
        for scoring in saved:
            original = deepcopy(scoring)
            observed = scoring['observed']
            validate_directional_numerical('DirectionalSheet', observed)
            replay = calculate_directional_components(observed, parameters=REPLAY_PARAMETERS)
            assert replay['components'] is not None
            validate_directional_numerical('DirectionalComponentsResult', replay, sheet=observed)
            publication = {'version': 'bvbrc_proteome_directional_scoring_sheet_v1',
                           'observed': observed, 'calculated': replay['components']}
            validate_directional_numerical('DirectionalScoringSheet', publication)
            assert scoring == original
            assert replay['components']['sheet_sha256'] == scoring['calculated']['sheet_sha256']
            for previous_report, new_report in zip(scoring['calculated']['reports'], replay['components']['reports']):
                for previous_query, new_query in zip(previous_report['queries'], new_report['queries']):
                    for previous_subject, new_subject in zip(previous_query['subjects'], new_query['subjects']):
                        assert previous_subject['correspondence'] == new_subject['correspondence']
            replayed.append((publication, replay['state']))

    assert blocked_calls == []
    for row, (publication, state), label in zip(rows, replayed, FILES):
        row['saved_observation_replay'] = write('native_' + label + '_replay_scoring_sheet_001.json', publication)
        row['replay_state'] = state

    after = package_hashes()
    assert before == after
    receipt = {'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Retained original Biopython BLAST text fixtures, not BV-BRC service job outputs',
        'fixture_source_metadata': 'Local fixture labels and declared completeness only; no authenticated host custody or execution witness',
        'parameters': PARAMETERS, 'changed_replay_parameters': REPLAY_PARAMETERS,
        'complete_scoring_sheets': rows,
        'saved_observation_replay': {'native_parsing_forbidden': True, 'file_open_forbidden': True,
            'network_and_process_entry_points_forbidden': True, 'forbidden_call_count': len(blocked_calls),
            'original_publications_unchanged': True, 'geometry_graphs_unchanged': True},
        'source_modules_unchanged': before == after, 'module_hashes': before,
        'harness': digest(Path(__file__))}
    write('native_artifacts_receipt_001.json', receipt)
    print(json.dumps({'complete_scoring_sheet_count': len(rows),
        'complete_replay_scoring_sheet_count': len(replayed), 'forbidden_call_count': len(blocked_calls),
        'source_modules_unchanged': before == after, 'populations': [r['population'] for r in rows]}, indent=2))


if __name__ == '__main__':
    main()
