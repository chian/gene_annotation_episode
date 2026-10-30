"""Independent synthetic checks of previously observed unit/meaning failures."""
from pathlib import Path
import hashlib
import json
import math
import sys
import time
from copy import deepcopy
from fractions import Fraction

OUT = Path(__file__).resolve().parent
PIN = OUT / 'pin_002'
sys.dont_write_bytecode = True
sys.path[:0] = [str(PIN), str(PIN / 'tests')]
from gene_annotation_episode.literature_assay_inputs import _Sources
from gene_annotation_episode.literature_ion_discrimination_numbers import (
    read_ion_number, read_ion_unit, check_explicit_unit,
)
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
import test_literature_ion_discrimination_components_194 as fixture

results = []


def record(name, passed, detail):
    results.append({'name': name, 'passed': bool(passed), 'detail': detail})


def lexical(case):
    text, token = case['text'], case.get('token', '100')
    raw = text.encode()
    source_ref = 'source_' + 'abcd' * 6
    artifact = 'artifact_' + hashlib.sha256(raw).hexdigest()

    def source(ref, representation):
        assert ref == source_ref and representation == 'original'
        return {'artifact_ref': artifact, 'content': raw}

    def witness(token):
        i = text.index(token)
        return {'source_ref': source_ref, 'representation': 'original',
                'start': len(text[:i].encode()), 'end': len(text[:i + len(token)].encode()), 'quote': token}

    sources = _Sources(source)
    unit_token = case.get('unit_selection')
    try:
        number = read_ion_number({'witness': witness(token), 'number_start': 0,
                                  'number_end': len(token)}, sources=sources)
        unit = read_ion_unit(witness(unit_token), sources=sources) if unit_token else None
        check_explicit_unit(number, unit, sources=sources, dimensionless=unit_token is None)
        actual, error = 'accept', None
    except ExperimentalContractError as exc:
        actual, error = 'reject', exc.code
    record(text, actual == case['expected'], {'expected': case['expected'], 'actual': actual, 'error': error})


for name in ('UNIT_ROLE_PROBE_001.json', 'UNIT_ROLE_PROBE_002.json'):
    for case in json.loads((OUT / name).read_text())['cases']:
        lexical(case)

# Independent exact polynomial for the ratio variance; no production gradient.
args, rows, sources = fixture.setup()
matrix = [[.0081, .000675], [.000675, .000225]]
args, sources, _ = fixture.covariance(args, rows, sources, matrix)
_, sheet = fixture.calculate(args, rows, sources)
A, B = Fraction(9, 10), Fraction(15, 100)
var_a, cov_ab, var_b = Fraction(81, 10000), Fraction(675, 1000000), Fraction(225, 1000000)
expected_var = (B * B * var_a + A * A * var_b - 2 * A * B * cov_ab) / B**4
expected_log_var = var_a / A**2 + var_b / B**2 - 2 * cov_ab / (A * B)
cells = sheet['cells']
record('correlated_ratio_and_log_uncertainty',
       cells['activity_ratio']['value'] == 6
       and math.isclose(cells['activity_ratio_variance']['value'], float(expected_var))
       and math.isclose(cells['log_activity_ratio_variance']['value'], float(expected_log_var))
       and math.isclose(cells['activity_ratio_standard_uncertainty']['value'], .6)
       and math.isclose(cells['log_activity_ratio_standard_uncertainty']['value'], .1),
       {'R': cells['activity_ratio']['value'], 'variance_R': cells['activity_ratio_variance']['value'],
        'variance_log_R': cells['log_activity_ratio_variance']['value'],
        'exact_expected_variance_R': str(expected_var), 'exact_expected_variance_log_R': str(expected_log_var)})

for a, b, expected in [(0, .15, 0), (-.03, .15, -.2), (-.9, -.15, 6), (.9, 0, None)]:
    args, rows, sources = fixture.setup(a, b)
    _, sheet = fixture.calculate(args, rows, sources)
    cell = sheet['cells']['activity_ratio']
    ok = cell['value'] is None if expected is None else math.isclose(cell['value'], expected, abs_tol=1e-15)
    if a < 0 or b < 0:
        ok = ok and cell['scientific_applicability'] == 'estimator_comparison_only'
    record(f'signed_or_zero_{a}_{b}', ok and cell['physical_domain'] is None,
           {k: cell[k] for k in ('value', 'scientific_applicability', 'zero_denominator_case')})

text = ('Preferred quantity >30 per_s; alternative <3 ions/s. '
        'First interpretation: ion flux. Second interpretation: charge equivalents.')
for meaning in ('charge_equivalent_rate', 'signed_reporter_estimator', 'unknown', 'conflicting'):
    preferred = fixture.source_quantity(text, '30', 'per_s', meaning=meaning)
    preferred['derivation'] = {'value': 'unknown', 'witnesses': []}
    if meaning == 'conflicting':
        preferred['meaning']['witnesses'] = [fixture.w(text, 'First interpretation: ion flux.'),
                                            fixture.w(text, 'Second interpretation: charge equivalents.')]
    args = {**fixture.common(text), 'source_kind': 'primary_source', 'route': 'reported_threshold_pair',
            'thresholds': {'preferred': preferred,
                           'alternative': fixture.source_quantity(text, '3', 'ions/s', at=text.index('<3') + 1)}}
    _, sheet = fixture.calculate(args, [], {fixture.SOURCE: text.encode()})
    cell = sheet['cells']['preferred_activity']
    record('native_meaning_' + meaning,
           cell['quantity_kind'] == meaning and cell['origin'] == 'reported'
           and cell['derivation'] == 'unknown' and cell['threshold'] == 30
           and cell['physical_domain'] is None and sheet['cells']['nominal_threshold_ratio']['threshold'] is None,
           {k: cell[k] for k in ('quantity_kind', 'origin', 'derivation', 'threshold')})

args, rows, sources = fixture.setup(.9, .9)
rows[1]['dependencies'] = deepcopy(rows[0]['dependencies'])
_, sheet = fixture.calculate(args, rows, sources)
record('two_sheet_refs_same_whole_estimator',
       sheet['cells']['activity_ratio']['value'] is None
       and 'reused_activity_not_ion_discrimination' in sheet['cells']['activity_ratio']['unavailable_reasons'],
       sheet['cells']['activity_ratio']['unavailable_reasons'])
rows[1]['value'] = .15
_, sheet = fixture.calculate(args, rows, sources)
record('same_estimator_inconsistent_values',
       'shared_activity_estimator_inconsistent' in sheet['cells']['activity_ratio']['unavailable_reasons'],
       sheet['cells']['activity_ratio']['unavailable_reasons'])

args, rows, sources = fixture.setup()
rows[1]['dependencies'][3] = deepcopy(rows[0]['dependencies'][3])
_, sheet = fixture.calculate(args, rows, sources)
record('shared_amount_is_not_same_entire_activity', sheet['cells']['activity_ratio']['value'] == 6
       and sheet['cells']['activity_ratio_variance']['value'] is None,
       {'R': sheet['cells']['activity_ratio']['value'], 'variance': sheet['cells']['activity_ratio_variance']['value']})

args['source_kind'] = 'primary_source'
_, sheet = fixture.calculate(args, rows, sources)
record('synthetic_mean_remains_partial_for_primary_request',
       sheet['cells']['preferred_activity']['origin'] == 'synthetic'
       and sheet['cells']['preferred_activity']['value'] == .9
       and sheet['cells']['activity_ratio']['value'] is None,
       sheet['cells']['activity_ratio']['unavailable_reasons'])

imports = {n: str(Path(m.__file__).resolve()) for n, m in sys.modules.items()
           if getattr(m, '__file__', None) and (n.startswith('gene_annotation_episode') or n.startswith('test_'))}
outside = {n: p for n, p in imports.items() if not Path(p).is_relative_to(PIN)}
manifest = json.loads((OUT / 'PIN_002.json').read_text())
changed = [p for p, sha in manifest.items() if hashlib.sha256((PIN / p).read_bytes()).hexdigest() != sha]
output = {'time': time.time(), 'scope': 'Synthetic independent numerical and semantic review; no new paper packet.',
          'checks': results, 'passed': sum(r['passed'] for r in results), 'total': len(results),
          'imports_outside_pin': outside, 'changed_pinned_files': changed}
with (OUT / 'ROOT_PROBE_003.json').open('x') as stream:
    json.dump(output, stream, indent=2)
    stream.write('\n')
print(json.dumps({'passed': output['passed'], 'total': len(results), 'imports_outside_pin': outside,
                  'changed_pinned_files': changed}))
raise SystemExit(bool(outside or changed) or output['passed'] != len(results))
