"""Constructed, non-paper covariance counterexample; no production changes.

Uses real selected binding, typed projection/admission and actual parent STEERING
renderer. It does not run a model or claim scientific source investigation.
"""
from pathlib import Path
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
import sys

BASE = Path(__file__).resolve().parent
PIN = BASE / 'pin_002_unit'
sys.path[:0] = [str(PIN), str(PIN / 'tests')]

from gene_annotation_episode.communication import form_with_facts
from gene_annotation_episode.domain import canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_experimental_prompt import _steering
from gene_annotation_episode.literature_perturbation_summary_storage import (
    LiteraturePerturbationSummaryProjection, perturbation_summary_cells_schema,
)
from gene_annotation_episode.state import Store
from test_literature_perturbation_summary import source_data, arguments
from test_literature_perturbation_summary_integration import source, binding_for

TEXT = b'Constructed matched endpoint: mean W12 K3 R11; five independent culture units per arm. Retained scenario is explicitly synthetic.'
FIELDS = ('summary_kind', 'summary_scale', 'spread_kind', 'spread_scale', 'count_n', 'count_unit', 'count_independence')


def data_for(kind):
    data = source_data(); data['exposure_unit'] = 'unreported'
    for role in ('W', 'K', 'R'):
        e = data['measurements'][role]
        e['count'].update(n=5, unit_kind='culture')
        e['uncertainty'].update(kind='sem', value=1)
        e['interpretation_basis'] = dict.fromkeys(FIELDS, 'source_supported_inference')
    cov_kind = kind
    if kind == 'paired_units':
        # Exact orthogonal centred vectors, n5: both sample variances5,
        # mean variances1 and cross-arm covariance0.
        for role, values in [('W', [8, 13, 13, 13, 13]), ('K', [3, 0, 2, 4, 6])]:
            e = data['measurements'][role]; e['value'] = None
            e['uncertainty'].update(kind='unreported', value=None)
            e['raw_units'] = [{'unit_id': 'unit' + str(i), 'values': [value]} for i, value in enumerate(values)]
    data['covariances'] = [{'first': 'W', 'second': 'K', 'kind': cov_kind,
        'value': 0 if kind == 'mean_covariance' else None,
        'variance_status': 'estimated', 'witnesses': []}]
    return data


def run_one(output, kind):
    output.mkdir()
    store = Store(output / 'state'); store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    try:
        root = source(store, TEXT)
        data = data_for(kind)
        retained = source(store, canonical(data), parents=[root['id']])
        args = arguments(); args.update(source_ref=root['id'], data_source_ref=retained['id'])
        start = TEXT.index(b'matched endpoint')
        witness = {'source_ref': root['id'], 'representation': 'original', 'start': start,
            'end': start + len(b'matched endpoint'), 'quote': 'matched endpoint'}
        args['interpretation_witnesses'] = [witness]
        args['literals']['molecule'] = witness
        names = ['perturbation_mean_variance']
        assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
            'source_refs': [root['id'], retained['id']], 'requested_perturbation_summary_components': names}
        context = BindingContext('covariance-counterexample', 'child', 'literature', (('literature', 'child'),),
            store.validate_scope(), assignment, {}, (root['id'], retained['id']))
        binding = binding_for(store, context)
        outcome = asyncio.run(binding.execute(context, 'literature.perturbation.populate', args, 'selected'))
        assert outcome['status'] == 'completed', outcome.get('feedback')
        sheet = outcome['result']['sheet_ref']
        context = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
        schema = obj({'measurement': perturbation_summary_cells_schema()})
        form = form_with_facts({}, schema, binding.facts(context, {'committed_record_refs': [sheet]}))
        binding.validate_report(context, form, schema)
        parent = replace(context, role='annotation', episode_id='parent', path=(('annotation', 'parent'),), assignment={})
        binding.received_form_references(parent, form, schema, 'counterexample-admission')
        projection = LiteraturePerturbationSummaryProjection(store, context.run_id)
        assert projection.received_cells(parent) == form['measurement']
        presented = _steering({'child_reports': [form]}, ())
        (output / 'PARENT_STEERING.txt').write_text(presented)
        (output / 'RETAINED_DATA.json').write_text(json.dumps(data, indent=2) + '\n')
        (output / 'TYPED_FORM.json').write_text(json.dumps(form, indent=2) + '\n')
        return form['measurement'][0], presented
    finally:
        store.close()


if __name__ == '__main__':
    output = BASE / 'covariance_custody_audit_001'; output.mkdir()
    rows, presentations = {}, {}
    for kind in ('mean_covariance', 'uncorrelated', 'paired_units', 'unknown'):
        rows[kind], presentations[kind] = run_one(output / kind, kind)
    custody = {'sheet_ref', 'data_source_ref'}
    normalized = {kind: {k: v for k, v in row.items() if k not in custody} for kind, row in rows.items()}
    assert normalized['mean_covariance'] == normalized['uncorrelated'] == normalized['paired_units']
    assert all(rows[kind]['value'] == 2 for kind in ('mean_covariance', 'uncorrelated', 'paired_units'))
    assert rows['unknown']['value'] is None
    assert rows['unknown']['unavailable_reason'] == 'cross_arm_covariance_unknown'
    assert presentations['mean_covariance'] == presentations['uncorrelated'] == presentations['paired_units']
    assert not any('covariance_kind' in row or 'covariance_basis' in row for row in rows.values())
    result = {'kind': 'constructed engineering counterexample; no paper/model/production change',
        'known_scenarios': ['source-supplied zero mean covariance', 'assumed uncorrelated', 'paired raw estimated zero covariance'],
        'derived_variance': 2.0, 'typed_scientific_fields_exactly_identical_except_custody': sorted(custody),
        'actual_parent_steering_exactly_identical': True,
        'unknown_covariance_is_visible_as_unavailable': True,
        'gap': 'Requested derived row and actual parent STEERING omit selected cross-arm covariance kind, basis and witnesses. Source recipe has kind; retained covariances have no reported/inferred/conditional basis field.',
        'no_new_metadata_or_scoring_change_implemented': True}
    (output / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
