"""Keep numerical/source-binding references strict with science disabled."""
from copy import deepcopy
import json
from pathlib import Path
import resource
import sys

OWN = Path(__file__).resolve().parent
CANDIDATE = OWN / 'repair_candidate'
OUT = OWN / 'component_scope_001'
OUT.mkdir(exist_ok=False)
sys.dont_write_bytecode = True
sys.path[:0] = [str(CANDIDATE), str(CANDIDATE / 'tests')]
resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))
import pytest
from test_bvbrc_genome_alignment_sheet import fixture_sheet
from test_genome_alignment_saved_structure import scientific_barrier
from gene_annotation_episode.bvbrc_genome_alignment_sheet import validate_genome_alignment_sheet


def paths(value, path=()):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == 'requirement_ids':
                yield path + (key,)
            yield from paths(child, path + (key,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from paths(child, path + (index,))


sheet = fixture_sheet()
original = deepcopy(sheet)
native_path = ('components', 'outcomes', 0, 'measurement', 'value', 'coverage', 0,
    'known_union_bases', 'requirement_ids')
source_path = next(path for path in paths(sheet)
    if path[:2] == ('components', 'source_bindings'))
results = []
with pytest.MonkeyPatch.context() as patch:
    blocked = scientific_barrier(patch)
    assert validate_genome_alignment_sheet(sheet) == original
    for path in (native_path, source_path):
        for unknown in ('unknown-scientific-cause', 'native'):
            changed = deepcopy(sheet)
            target = changed
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = [unknown]
            before = deepcopy(changed)
            try:
                validate_genome_alignment_sheet(changed)
            except ValueError as error:
                results.append({'path': '/' + '/'.join(map(str, path)),
                    'injected_ids': [unknown], 'rejection': str(error)})
            else:
                raise AssertionError(('Unknown scientific reference was accepted', path, unknown))
            assert changed == before
    assert sheet == original
    assert validate_genome_alignment_sheet(sheet) == original
with (OUT / 'receipt.json').open('x') as handle:
    json.dump({'positive_original_sheet_preserved': True, 'negative_results': results,
        'scientific_aliases_blocked': list(blocked), 'acquisition_and_processes_forbidden': True,
        'native_provenance': 'retained native documents; explicitly synthetic C witnesses',
        'wall_time_limit': None}, handle, indent=2, sort_keys=True)
    handle.write('\n')
(OUT / 'receipt.json').chmod(0o444)
print(json.dumps(results, sort_keys=True))
