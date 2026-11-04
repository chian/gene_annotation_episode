"""Original field, task, native-token and immediate-child admission semantics."""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode import bvbrc_proteome_fact_contracts as facts
from gene_annotation_episode.bvbrc_proteome_returns import ProteomeReturnError
from gene_annotation_episode.communication import form_with_facts, plain, validate_form
from gene_annotation_episode.execution_contracts import canonical
from test_bvbrc_proteome_returns import (
    ASSOCIATIONS, FACT_SOURCES, MEASUREMENTS, POPULATIONS, REQUIREMENTS, STATUS,
    MEAN, example, fact_form, project, run, selected_fields,
)


def test_generated_failure_scope_remains_field_local_and_keeps_original_request_ids():
    fields = selected_fields()
    fields['absent/row'] = {'kind': 'association', 'association_key': 'comp_genome_2/row/999'}
    fields['absent/track'] = {'kind': 'measurement', 'target': 'track_count', 'track_key': 'comp_genome_999',
                            'metric': 'reference_input_record_count'}
    fields['absent_status'] = {'kind': 'request_status', 'field': 'absent/row'}
    args = example(fields)
    projected = project(args)
    saved = args[0]['publication']['adapter_result']['facts']
    reqs = {row['requirement_ref']: row for row in projected[REQUIREMENTS][0]['value']['requirements']}
    generated = {}
    for name in ('denominator', 'ratio', 'absent/row', 'absent/track'):
        refs = [ref for ref in saved[name]['requirement_refs'] if reqs[ref]['code'].startswith('proteome_requested_')]
        assert len(refs) == 1
        generated[name] = refs[0]
        assert reqs[refs[0]]['scope']['track_key'] == (None if name == 'absent/track' else 'comp_genome_2')
        assert reqs[refs[0]]['scope']['association_key'] is None
        assert refs[0] not in saved['mean']['requirement_refs']
    assert len(set(generated.values())) == 4
    for name, ref in generated.items():
        assert all(ref not in saved[other]['requirement_refs'] for other in generated if other != name)
    assert saved['absent_status']['field'] == 'absent/row'
    assert saved['absent_status']['requirement_refs'] == saved['absent/row']['requirement_refs']
    emitted = {facts.decode_reference(row['field'])[2] for rows in projected.values() for row in rows}
    assert emitted == {'/facts/' + name.replace('~', '~0').replace('/', '~1') for name in fields}
    altered = deepcopy(args)
    altered[0]['publication']['adapter_result']['facts']['mean']['requirement_refs'].append(generated['absent/row'])
    with pytest.raises(ProteomeReturnError, match='saved_projection_invalid'):
        project(altered)


@pytest.mark.parametrize('target,value', [
    ('number', .9), ('cell_state', 'missing_input'), ('null_value', None), ('field', '/facts/unrequested'),
    ('category', 'arbitrary category'), ('category', 'uni (->)'), ('track_key', 'comp_genome_3'),
    ('association_key', 'comp_genome_2/row/1'), ('subject_identifier', 'other_subject'),
    ('reference_identifier', 'other_reference'), ('population_membership', 'comp_genome_2/row/77'),
    ('status_field', 'unrequested'), ('source', None), ('duplicate', None),
])
def test_matching_forged_frozen_facts_and_attempt_still_fail_original_semantics(run, target, value):
    args = run.example()
    child = run.child(run.saved.root, 'results', args[0])
    run.publications.add(child, args)
    form, schema, key, _ = run.admit(run.saved.root, child)
    altered = deepcopy(form)
    if target == 'number': altered['f0'][0]['value']['cell']['value'] = value
    elif target == 'cell_state': altered['f0'][0]['value']['cell']['state'] = value
    elif target == 'null_value': altered['f0'][0]['value']['cell']['value'] = value
    elif target == 'field': altered['f0'][0]['field'] = facts.encode_reference('field', args[1]['analysis_id'], value)
    elif target == 'category': altered['f3'][0]['value']['native_category'] = value
    elif target in {'track_key', 'association_key', 'subject_identifier', 'reference_identifier'}:
        altered['f3'][0]['value'][target] = value
    elif target == 'population_membership': altered['f2'][0]['value']['association_keys'][0] = value
    elif target == 'status_field': altered['f7'][0]['value']['field'] = value
    elif target == 'source': altered['f0'][0]['source_ref'] = run.saved.source()['source_ref']
    elif target == 'duplicate': altered['f0'].append(deepcopy(altered['f0'][0]))
    saved = {source: altered[f'f{i}'] for i, source in enumerate(FACT_SOURCES)}
    run.store.db.execute('UPDATE runtime_forms SET form=?,facts=? WHERE episode_id=?',
        (canonical(altered), canonical(saved), child.episode_id))
    run.store.db.execute('UPDATE runtime_report_attempts SET form=? WHERE child_episode_id=?',
        (canonical(altered), child.episode_id))
    with pytest.raises(ValueError):
        run.host.record_admission(run.saved.root, altered, schema, key)


@pytest.mark.parametrize('source,field,value', [
    (ASSOCIATIONS, 'native_category', 'not_native'),
    (ASSOCIATIONS, 'native_category', 'uni (->)'),
    (ASSOCIATIONS, 'subject_identifier', 'made_up_subject'),
    (ASSOCIATIONS, 'track_key', 'comp_genome_333'),
    (ASSOCIATIONS, 'association_key', 'comp_genome_2/row/333'),
    (MEASUREMENTS, 'cell', {'state': 'missing_input', 'value': .4375, 'reason_codes': [], 'source_field_refs': []}),
])
def test_narrower_caller_schema_cannot_authorize_forged_native_or_numeric_value(run, source, field, value):
    fields = {'association': {'kind': 'association', 'association_key': 'comp_genome_2/row/0'}} if source == ASSOCIATIONS else {'mean': MEAN}
    args = run.example(fields)
    schema = fact_form(source)
    if field != 'cell':
        node = schema['properties']['f0']['items']['properties']['value']['properties'][field]
        # Narrow the nullable native category carrier to a string; communication
        # code enums cannot contain the saved native literals' punctuation.
        # Other callers constrain the carrier to the forged token itself.
        # Original semantic domains and exact saved values govern both cases.
        if field == 'native_category':
            node['type'] = 'string'
        else:
            node['enum'] = [value]
    child = run.child(run.saved.root, 'results', args[0], schema=schema)
    run.publications.add(child, args)
    values = run.host.facts(child, schema)
    form = form_with_facts({}, schema, values)
    form['f0'][0]['value'][field] = value
    assert validate_form(form, schema, lambda *_: True) == form
    with pytest.raises(ValueError):
        run.host.validate_received_report(child, form, schema)


def test_narrowed_object_cannot_drop_required_fact_fields(run):
    args = run.example({'mean': MEAN})
    schema = fact_form(MEASUREMENTS)
    value_schema = schema['properties']['f0']['items']['properties']['value']
    value_schema['properties'].pop('cell')
    value_schema['required'].remove('cell')
    child = run.child(run.saved.root, 'results', args[0], schema=schema)
    run.publications.add(child, args)
    form = form_with_facts({}, schema, run.host.facts(child, schema))
    del form['f0'][0]['value']['cell']
    assert validate_form(form, schema, lambda *_: True) == form
    with pytest.raises(ProteomeReturnError, match='returned_facts_invalid'):
        run.host.validate_received_report(child, form, schema)


def test_native_tokens_and_saved_pointers_resolve_only_in_their_declared_namespace(run):
    args = run.example({'association': {'kind': 'association', 'association_key': 'comp_genome_2/row/0'}})
    child = run.child(run.saved.root, 'results', args[0], sources=(ASSOCIATIONS,))
    run.publications.add(child, args)
    form, schema, _, _ = run.admit(run.saved.root, child)
    row = form['f0'][0]
    assert run.host.resolve_own(child, row['field'], 'bvbrc_proteome_field') is True
    assert run.host.resolve_received(run.saved.root, row['value']['reference_join_ref'], 'bvbrc_proteome_join') is True
    assert run.host.resolve_received(run.saved.root, 'comp_genome_2', 'bvbrc_proteome_track') is True
    assert run.host.resolve_received(run.saved.root, 's1', 'bvbrc_proteome_native_identifier') is True
    assert run.host.resolve_received(run.saved.root, 'bi (<->)', 'bvbrc_proteome_native_category') is True
    assert run.host.resolve_received(run.saved.root, 'uni (->)', 'bvbrc_proteome_native_category') is False
    assert run.host.resolve_received(run.saved.root, 'r1', 'bvbrc_proteome_track') is False
    assert run.host.resolve_received(run.saved.root, 'bi (<->)', 'source') is None
    fake = facts.encode_reference('join', args[1]['analysis_id'], '/sheet/not_saved')
    assert run.host.resolve_received(run.saved.root, fake, 'bvbrc_proteome_join') is False


@pytest.mark.parametrize('target', ['scope', 'purpose', 'schema', 'action', 'frozen_form', 'frozen_facts'])
def test_actual_original_commission_and_frozen_child_form_cannot_be_substituted(run, target):
    args = run.example({'mean': MEAN})
    parent = run.saved.root
    child = run.child(parent, 'results', args[0], sources=(MEASUREMENTS,))
    run.publications.add(child, args)
    form, schema, key, _ = run.admit(parent, child)
    row = run.saved.journal.row('runtime_actions', parent.episode_id, 0)
    action = json.loads(row['action'])
    if target == 'scope': action['scope'] = {}
    elif target == 'purpose': action['purpose'] = 'different_requested_work'
    elif target == 'schema': action['schema_json'] = canonical(fact_form(ASSOCIATIONS))
    elif target == 'action':
        run.store.db.execute('DELETE FROM runtime_actions WHERE episode_id=?', (parent.episode_id,))
        run.store.db.execute('DELETE FROM runtime_model_calls WHERE episode_id=?', (parent.episode_id,))
    elif target == 'frozen_form':
        run.store.db.execute('UPDATE runtime_forms SET form=? WHERE episode_id=?', (canonical({}), child.episode_id))
    elif target == 'frozen_facts':
        run.store.db.execute('UPDATE runtime_forms SET facts=? WHERE episode_id=?', (canonical({MEASUREMENTS: []}), child.episode_id))
    if target in {'scope', 'purpose', 'schema'}:
        run.store.db.execute('UPDATE runtime_actions SET action=? WHERE episode_id=? AND decision_index=0',
            (canonical(action), parent.episode_id))
    with pytest.raises(ValueError):
        run.host.record_admission(parent, form, schema, key)


def test_immediate_child_identity_cannot_be_replaced_by_sibling(run):
    args = run.example({'mean': MEAN})
    first = run.child(run.saved.root, 'results', args[0], sources=(MEASUREMENTS,))
    second = run.child(run.saved.root, 'results', args[0], index=1, sources=(MEASUREMENTS,))
    run.publications.add(first, args)
    run.publications.add(second, args)
    run.admit(run.saved.root, first)
    run.candidate(second)
    run.store.db.execute('UPDATE runtime_report_attempts SET child_episode_id=? WHERE decision_index=0', (second.episode_id,))
    with pytest.raises(ValueError):
        run.host.received_facts(run.saved.root, fact_form(MEASUREMENTS))


def test_distinct_original_publications_remain_distinct(run):
    args = run.example({'mean': MEAN})
    refs = []
    for index in range(2):
        child = run.child(run.saved.root, 'results', args[0], index=index, sources=(MEASUREMENTS,))
        refs.append(run.publications.add(child, args)['source_ref'])
        run.admit(run.saved.root, child)
    rows = run.host.received_facts(run.saved.root, fact_form(MEASUREMENTS))[MEASUREMENTS]
    assert len(set(refs)) == 2
    assert [row['source_ref'] for row in rows] == refs
    assert [row['value']['cell']['value'] for row in rows] == [.4375, .4375]


def test_report_owner_and_admission_operation_are_explicit(run):
    args = run.example({'mean': MEAN})
    child = run.child(run.saved.root, 'results', args[0], sources=(MEASUREMENTS,))
    other = run.child(run.saved.root, 'monitor', args[0], index=1, sources=(MEASUREMENTS,))
    run.publications.add(child, args)
    form, schema, key, _ = run.admit(run.saved.root, child)
    with pytest.raises(ProteomeReturnError, match='unsupported_return_owner'):
        run.host.validate_received_report(other, {'f0': []}, schema)
    with pytest.raises(ValueError):
        run.host.record_admission(other, form, schema, key)
    with pytest.raises(ValueError):
        run.host.record_admission(run.saved.root, form, schema, 'not_an_admission_operation')
