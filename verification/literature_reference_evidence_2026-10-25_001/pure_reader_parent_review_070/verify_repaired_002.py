"""Root independent corrected public replay plus immutable package checks."""
from pathlib import Path
import hashlib
import json
import sys
from copy import deepcopy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
packages = {}
for directory, manifest in [('a105_visual_signal_reader_070', 'MANIFEST_017.json'),
                            ('a105_visual_signal_reader_repair_074', 'MANIFEST_007.json')]:
    base = HERE.parent / directory
    data = json.loads((base / manifest).read_bytes())
    for row in data['files']:
        assert sha(base / row['path']) == row['sha256'], row['path']
    packages[directory] = {'manifest_sha256': sha(base / manifest), 'payloads_checked': len(data['files'])}

from gene_annotation_episode.literature_ratio_source_inputs import (
    read_relative_signal_source_inputs, validate_relative_signal_source_extraction)
from gene_annotation_episode.literature_ratio_source_calculations import populate_relative_signal_v2
from gene_annotation_episode.literature_ratio_source_validation import validate_relative_signal_saved

source, subject, genotype = ['source_' + str(n) * 24 for n in (1, 2, 3)]
data = {source: b'<article><body><sec id="s1"><p>SyntheticProtein 60% (V) of WT levels.</p></sec></body></article>',
        subject: b'SyntheticProtein', genotype: b'ConstructedStrain'}
def witness(ref):
    return {'kind': 'text', 'source_ref': ref, 'representation': 'original',
            'start': 0, 'end': len(data[ref]), 'quote': data[ref].decode()}
fields = ('subject', 'variant', 'reference', 'organism', 'genotype', 'construct_variant',
    'construct_reference', 'preparation_variant', 'preparation_reference', 'experiment',
    'condition', 'endpoint', 'normalization', 'signal_kind', 'reference_role', 'arrangement', 'signal_use')
unknown = {'status': 'unknown', 'value': None, 'witnesses': []}
comparison = {name: deepcopy(unknown) for name in fields}
for field, ref in [('subject', subject), ('genotype', genotype)]:
    comparison[field] = {'status': 'known', 'value': data[ref].decode(), 'witnesses': [witness(ref)]}
selected = {'version': 'relative_signal_source_selection_v2', 'source_ref': source,
    'comparison': comparison, 'representations': [{'representation_id': 'constructed_prose', 'kind': 'jats_percent',
        'selection': {'source_ref': source, 'section_id': 's1', 'paragraph_index': 0,
            'expected_subject': 'SyntheticProtein', 'variant': 'V', 'reference_literal': 'WT levels'},
        'comparison_relation': {'value': 'supported', 'witnesses': [witness(subject)]},
        'physical_measurement': deepcopy(unknown), 'reference_measurement': deepcopy(unknown)}]}
calls = []
def read_source(ref, representation):
    assert representation == 'original'
    calls.append(ref)
    return {'artifact_ref': 'artifact_' + hashlib.sha256(data[ref]).hexdigest(), 'content': data[ref]}
def forbidden(*a, **kw):
    raise AssertionError('unexpected acquisition during saved validation')
extraction = read_relative_signal_source_inputs(selected, read_source=read_source,
    read_view=forbidden, evidence_origin='synthetic_fixture')
loaded = json.loads(json.dumps(extraction, sort_keys=True))
assert validate_relative_signal_source_extraction(loaded) == extraction
sheet = populate_relative_signal_v2(loaded)
assert sheet['cells']['reported_ratio']['value'] == .6
ref = 'source_' + '9' * 24
outcome = {'status': 'completed', 'operation_ref': 'operation_root_constructed',
    'record_refs': [ref], 'changed_record_refs': [ref], 'feedback': None,
    'result': {'sheet_ref': ref, 'cells': deepcopy(sheet['cells']),
        **{k: sheet[k] for k in ('selected_roster_resolved', 'point_candidate_set_complete', 'known_source_conflict')}}}
import gene_annotation_episode.literature_ratio_source_inputs as inputs
import gene_annotation_episode.literature_ratio_source_calculations as calculations
inputs.read_relative_signal_source_inputs = forbidden
inputs._available_call = forbidden
inputs._view_bytes = forbidden
inputs._jats_expression = forbidden
inputs._jats_matches = forbidden
calculations.populate_relative_signal_v2 = forbidden
calculations._component_facts = forbidden
validate_relative_signal_saved(json.loads(json.dumps(selected, sort_keys=True)), loaded, sheet, outcome)
assert calls == sorted(data)
receipt = {'scope': 'Constructed pure API verification only; no paper/native/model execution',
    'packages': packages, 'corrected_original_counterexample_passed': True,
    'canonical_json_preserved_extraction': True, 'saved_validation_with_acquisition_and_population_forbidden': True,
    'actual_source_callbacks': calls, 'ratio': .6,
    'accepted': 'Pure printed-signal reader/calculator/saved validator, original017 plus repair074 only',
    'remaining': 'Native repository root review, genuine episode/C1/C4/parent/model integration and broader scientific coverage'}
with (HERE / 'REPAIRED_ROOT_RECEIPT_002.json').open('x') as f:
    json.dump(receipt, f, indent=2); f.write('\n')
print(json.dumps(receipt))
