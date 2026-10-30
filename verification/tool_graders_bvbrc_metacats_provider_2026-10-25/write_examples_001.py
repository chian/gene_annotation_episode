"""Save complete provider examples from retained native bytes; run no analysis."""
from contextlib import ExitStack
from copy import deepcopy
import builtins
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'tests'))
from test_bvbrc_metacats_provider import retained_sheet, CASES, NATIVE, by_id, native_family_request
from gene_annotation_episode.bvbrc_metacats_grader import calculate_metacats
from gene_annotation_episode.bvbrc_metacats_provider_contracts import validate_metacats_sheet, validate_metacats_components, STAT_KINDS
from gene_annotation_episode import bvbrc_metacats_formats as formats
from gene_annotation_episode import bvbrc_metacats_input_formats as input_formats
from gene_annotation_episode import bvbrc_metacats_calculators as native
from gene_annotation_episode import bvbrc_metacats_biological_calculators as biological
from gene_annotation_episode import bvbrc_metacats_adequacy as adequacy
from gene_annotation_episode import phylogeny_calculators as shared
from gene_annotation_episode import bvbrc_metacats_grader as grader

HERE = Path(__file__).resolve().parent
TARGET = HERE / 'EXAMPLES_001'
OWNED = [ROOT / 'gene_annotation_episode' / ('bvbrc_metacats_' + suffix + '.py') for suffix in ('provider_contracts', 'inputs', 'grader')]
DEPENDENCIES = [ROOT / 'gene_annotation_episode' / name for name in (
    'bvbrc_alignment_provider_contracts.py','bvbrc_alignment_associations.py','bvbrc_metacats_association_contracts.py','bvbrc_metacats_associations.py',
    'bvbrc_metacats_formats.py','bvbrc_metacats_format_contracts.py','bvbrc_metacats_input_formats.py','bvbrc_alignment_values.py',
    'bvbrc_metacats_calculators.py','bvbrc_metacats_calculation_contracts.py','bvbrc_metacats_biological_calculators.py','bvbrc_metacats_biological_contracts.py','bvbrc_metacats_adequacy.py',
    'bvbrc_contingency_math.py','phylogeny_calculators.py','phylogeny_calculation_contracts.py','phylogeny_format_contracts.py','bvbrc_appservice_contracts.py')]


def fingerprint(path):
    raw = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(raw).hexdigest(), 'byte_count': len(raw)}


def save(path, value):
    data = (json.dumps(value, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n').encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)
    return fingerprint(path)


def forbidden(*args, **kwargs):
    raise AssertionError('provider_verification_forbidden_IO_native_parser_or_calculator')


def no_io(stack):
    for module, names in ((builtins, ('open',)), (io, ('open',)), (os, ('open',)),
                          (Path, ('open','read_text','read_bytes','write_text','write_bytes')),
                          (socket, ('socket','create_connection','getaddrinfo')),
                          (subprocess, ('Popen','run','call','check_call','check_output')),
                          (formats, formats.__all__), (input_formats, input_formats.__all__)):
        for name in names:
            stack.enter_context(patch.object(module, name, forbidden))


def no_calculators(stack):
    for module, names in ((native, ('metacats_group_counts','metacats_statistics','metacats_effects','adjust_p_values','chi_square_tail')),
                          (biological, biological.__all__), (shared, shared.__all__),
                          (adequacy, ('expected_count_adequacy',)), (grader, ('calculate_metacats',))):
        for name in names:
            stack.enter_context(patch.object(module, name, forbidden))


def main():
    TARGET.mkdir(exist_ok=False)
    before = [fingerprint(path) for path in OWNED + DEPENDENCIES]
    rows = []
    for case in CASES:
        sheet, parameters, receipt = retained_sheet(case)
        category = sheet['analysis']['category_ids'][0]
        parameters['requests'].append(native_family_request(sheet, kind='pairwise', eligibility=['native:' + category + ':statistics']))
        answer = calculate_metacats(sheet, parameters)
        saved = json.dumps({'sheet': sheet, 'parameters': parameters, 'components': answer}, allow_nan=False)
        restored = json.loads(saved)
        changed = deepcopy(parameters)
        for request in changed['requests']:
            if request['kind'] in STAT_KINDS:
                request['epsilon'] = .01
        with ExitStack() as stack:
            no_io(stack)
            replay = calculate_metacats(restored['sheet'], restored['parameters'])
            assert replay == restored['components']
            epsilon = calculate_metacats(restored['sheet'], changed)
            assert restored['sheet'] == sheet
            with ExitStack() as validators:
                no_calculators(validators)
                assert validate_metacats_sheet(restored['sheet']) == sheet
                assert validate_metacats_components(restored['components'], sheet=restored['sheet']) == answer
                assert validate_metacats_components(epsilon, sheet=restored['sheet']) == epsilon
        row = {'case': case, 'input_kind': receipt['input_kind'],
            'provider_envelope': 'synthetic deterministic verification envelope around previously retained local native execution',
            'sheet': save(TARGET / (case + '-sheet.json'), sheet),
            'components': save(TARGET / (case + '-components.json'), answer),
            'changed_epsilon_components': save(TARGET / (case + '-epsilon001-components.json'), epsilon),
            'no_io_exact_replay': True, 'no_calculator_saved_validation': True,
            'native_numbers_unchanged': True, 'native_programs_executed': 0,
            'native_observation_count': len(sheet['native_observations']), 'original_native_receipt': str((NATIVE / case / 'RECEIPT.json').relative_to(ROOT)),
            'retained_native_files': []}
        for relative in ['RECEIPT.json', *receipt['files']]:
            source = NATIVE / case / relative
            target = HERE / 'retained_native' / case / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            raw = source.read_bytes()
            with target.open('xb') as stream:
                stream.write(raw)
            assert target.read_bytes() == raw
            row['retained_native_files'].append({'original': fingerprint(source), 'copy': fingerprint(target)})
        for basis in ('native', 'biological'):
            result = by_id(answer, basis + ':' + category + ':statistics')['value']
            row[basis + '_eligible_omnibus_count'] = len(result['omnibus'])
            row[basis + '_selected_pair_count'] = len(result['pairs'])
        rows.append(row)
        print(json.dumps({'case': case, 'native_observations': row['native_observation_count'], 'saved_replay': True}), flush=True)
    after = [fingerprint(path) for path in OWNED + DEPENDENCIES]
    assert before == after
    save(HERE / 'EXAMPLE_MANIFEST_001.json', {'scope': 'Pure MetaCATS provider, no new native/service/HPC/episode execution',
        'cases': rows, 'sources_before': before, 'sources_after': after,
        'original_native_evidence_unchanged': True, 'shared_or_historical_files_edited': False})


if __name__ == '__main__':
    main()
