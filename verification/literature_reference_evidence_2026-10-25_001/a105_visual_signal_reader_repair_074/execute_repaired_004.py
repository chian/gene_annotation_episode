"""Actual repaired public API execution on root counterexample + richer fixtures."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path.cwd().resolve()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from test_literature_ratio_source_inputs import multi_dependency_fixture
from gene_annotation_episode.literature_ratio_source_inputs import (
    read_relative_signal_source_inputs, validate_relative_signal_source_extraction)
from gene_annotation_episode.literature_ratio_source_calculations import populate_relative_signal_v2
from gene_annotation_episode.literature_ratio_source_validation import validate_relative_signal_saved

HERE = ROOT / 'verification/literature_reference_evidence_2026-10-25_001/a105_visual_signal_reader_repair_074'


def root_counterexample():
    source, subject, genotype = ['source_' + str(n) * 24 for n in (1, 2, 3)]
    data = {source: b'<article><body><sec id="s1"><p>SyntheticProtein 60% (V) of WT levels.</p></sec></body></article>',
        subject: b'SyntheticProtein', genotype: b'ConstructedStrain'}
    def witness(reference):
        return {'kind': 'text', 'source_ref': reference, 'representation': 'original',
            'start': 0, 'end': len(data[reference]), 'quote': data[reference].decode()}
    names = ('subject', 'variant', 'reference', 'organism', 'genotype', 'construct_variant',
        'construct_reference', 'preparation_variant', 'preparation_reference', 'experiment',
        'condition', 'endpoint', 'normalization', 'signal_kind', 'reference_role', 'arrangement', 'signal_use')
    comparison = {name: {'status': 'unknown', 'value': None, 'witnesses': []} for name in names}
    for field, reference in (('subject', subject), ('genotype', genotype)):
        comparison[field] = {'status': 'known', 'value': data[reference].decode(), 'witnesses': [witness(reference)]}
    selected = {'version': 'relative_signal_source_selection_v2', 'source_ref': source,
        'comparison': comparison, 'representations': [{'representation_id': 'constructed_prose', 'kind': 'jats_percent',
            'selection': {'source_ref': source, 'section_id': 's1', 'paragraph_index': 0,
                'expected_subject': 'SyntheticProtein', 'variant': 'V', 'reference_literal': 'WT levels'},
            'comparison_relation': {'value': 'supported', 'witnesses': [witness(subject)]},
            'physical_measurement': {'status': 'unknown', 'value': None, 'witnesses': []},
            'reference_measurement': {'status': 'unknown', 'value': None, 'witnesses': []}}]}
    calls = []
    def read_source(reference, representation):
        assert representation == 'original'
        calls.append(('source', reference, representation))
        raw = data[reference]
        return {'artifact_ref': 'artifact_' + hashlib.sha256(raw).hexdigest(), 'content': raw}
    def forbidden_view(*a):
        raise AssertionError('no image requested')
    return selected, read_source, forbidden_view, calls


outputs = []
for name, fixture in (('exact_original_root_counterexample', root_counterexample()),
                      ('multi_source_multi_view_aliases', multi_dependency_fixture()[:4])):
    selected, read_source, read_view, calls = fixture
    extraction = read_relative_signal_source_inputs(selected, read_source=read_source,
        read_view=read_view, evidence_origin='synthetic_fixture')
    sheet = populate_relative_signal_v2(extraction)
    assert sheet['cells']['reported_ratio']['value'] == .6
    ref = 'source_' + 'a' * 24
    outcome = {'status': 'completed', 'operation_ref': 'operation_' + 'a' * 24,
        'record_refs': [ref], 'changed_record_refs': [ref], 'feedback': None,
        'result': {'sheet_ref': ref, 'cells': deepcopy(sheet['cells']),
            **{key: sheet[key] for key in ('selected_roster_resolved', 'point_candidate_set_complete', 'known_source_conflict')}}}
    saved = json.loads(json.dumps({'selection': selected, 'extraction': extraction,
        'sheet': sheet, 'outcome': outcome}, sort_keys=True))
    prior_calls = list(calls)
    validate_relative_signal_source_extraction(saved['extraction'])
    validate_relative_signal_saved(saved['selection'], saved['extraction'], saved['sheet'], saved['outcome'])
    assert calls == prior_calls
    outputs.append({'case': name, 'scope': 'constructed engineering source/view callbacks, not native custody or science',
        'actual_callbacks': calls, 'callbacks_during_saved_checks': len(calls) - len(prior_calls),
        'canonical_json_saved_validation_passed': True, 'records': saved})
(HERE / 'ACTUAL_REPAIRED_OUTPUTS_004.json').write_text(json.dumps(outputs, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
print(json.dumps({'actual_cases': len(outputs), 'canonical_saved_checks': 'passed', 'source_callbacks_during_saved_checks': 0,
    'source_rosters': [[(s['source_ref'], s['representation']) for s in r['records']['extraction']['sources']] for r in outputs],
    'view_rosters': [[v['view_ref'] for v in r['records']['extraction']['views']] for r in outputs]}))
