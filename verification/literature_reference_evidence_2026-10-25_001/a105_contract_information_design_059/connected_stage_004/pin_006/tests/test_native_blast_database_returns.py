"""Synthetic original-action, typed-return and scientific-consumer authority."""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical
from test_native_blast_database_episode_binding import SyntheticHost, schema_for, selector
from test_native_blast_database_results import query_selection


def test_actual_received_form_is_required_and_saved_row_cannot_be_rewritten(tmp_path, monkeypatch):
    h = SyntheticHost(tmp_path, monkeypatch)
    try:
        child = h.results()
        body = h.select(child, 0, 'execution.results.collect')['result']
        row = body['publication']['rows_by_family']['hsp'][0]
        assert h.family.resolve_received_reference(h.root, row['record_key'], 'native_blast_database_row') is False
        h.receipts.receive(h.root.episode_id, [row['source_ref']], kind='initial')
        assert h.family.resolve_received_reference(h.root, row['record_key'], 'native_blast_database_row') is False
        form, schema = h.returned(child)
        assert h.family.resolve_received_reference(h.root, row['record_key'], 'native_blast_database_row') is True
        altered = deepcopy(form)
        field = next(k for k, v in schema['properties'].items() if v['x-source'] == 'execution_blast_database_hsp_rows')
        altered[field][0]['measurements'][0]['value'] = 21
        with pytest.raises(ValueError, match='facts_conflict'):
            h.family.validate_received_report(child, altered, schema)
        sibling = h.child(h.root, 'scientific_process', {}, schema_for('execution_blast_database_hsp_rows'), index=2)
        h.receipts.receive(sibling.episode_id, [row['source_ref']], kind='initial')
        assert h.family.resolve_received_reference(sibling, row['record_key'], 'native_blast_database_row') is False
        assert h.family.resolve_received_reference(sibling, row['source_ref'], 'execution_result') is False
        # Replacing only a saved form cannot manufacture an original result.
        h.store.db.execute('UPDATE runtime_forms SET form=? WHERE run_id=? AND episode_id=?',
            (canonical(altered), h.run_id, child.episode_id))
        with pytest.raises(ValueError, match='frozen_form_conflict'):
            h.family.native_blast_database_returns.received_facts(h.root, schema)
    finally:
        h.store.close()


def test_unchanged_scientific_forwarding_uses_immediate_child_forms(tmp_path, monkeypatch):
    h = SyntheticHost(tmp_path, monkeypatch)
    try:
        original_parent = h.root
        schema = schema_for('execution_blast_database_hsp_rows', 'execution_blast_database_acquisition',
            'execution_blast_database_failures')
        process = h.child(original_parent, 'scientific_process', {}, schema, index=1)
        h.root = process
        child = h.results(selector('hsp'), index=0)
        body = h.select(child, 0, 'execution.results.collect')['result']
        original, _ = h.returned(child)
        received = h.family.native_blast_database_returns.received_facts(process, schema)
        forwarded, _ = h.deliver(process, original_parent, received)
        assert forwarded == original
        assert h.family.native_blast_database_returns.received_facts(original_parent, schema) == received
        assert h.family.resolve_received_reference(original_parent,
            body['publication']['rows_by_family']['hsp'][0]['record_key'], 'native_blast_database_row') is True
    finally:
        h.store.close()


def test_every_native_consumer_qualifies_frozen_measurements_and_missing_reference(tmp_path, monkeypatch):
    from gene_annotation_episode.native_blast_database_result_publication import validate_native_blast_database_observation
    from gene_annotation_episode.evidence_geometry import _observation_extent, _observation_extents
    from gene_annotation_episode.evidence_axis_contracts import native_metric_facts
    from gene_annotation_episode.blast_result_views import _original_hsp
    from gene_annotation_episode.alignment_site_native import source_descriptor, blast_grading
    from gene_annotation_episode.infernal_result_presentation import infernal_receiver_context
    from gene_annotation_episode.domain import REASONING_SCHEMA
    from test_evidence_axis_contracts import axis_entry
    h = SyntheticHost(tmp_path, monkeypatch)
    try:
        child = h.results(query_selection(h))
        body = h.select(child, 0, 'execution.results.collect')['result']
        row = body['publication']['rows_by_family']['hsp'][0]
        observed, source = h.store.get(row['observation_ref']), h.store.get(row['source_ref'])
        entry = axis_entry(); entry['native_measurements'][0]['binding']['measurement_name'] = 'native_score_bits'
        facts = native_metric_facts(entry, h.store, observation_refs=[observed['id']], received_record_refs=[observed['id']])
        assert facts['native_facts'][0]['native_value']['value'] == 20
        assert _observation_extents(h.store, observed)[0][0] == {h.scope['subject_refs'][0]: [(0, 4)]}
        readers = [lambda: _original_hsp(h.store, observed['id'], [observed['id']], h.scope),
            lambda: source_descriptor(h.store, source, observed),
            lambda: blast_grading(h.store, observed, source, None, None, 0, 4, grade_result=lambda *_: None)]
        for reader in readers:
            with pytest.raises(ValueError, match='biological_reference_unavailable'):
                reader()
        assert 'native_blast_database' not in REASONING_SCHEMA['properties']['observations']['items']['properties']
        context = dict(working_state=dict(observations=[observed]), child_returns=[{'explicit': row}])
        projected = infernal_receiver_context(context)
        assert projected['working_state']['observations'] == [] and projected['child_returns'] == context['child_returns']
        original_get = h.store.get
        changed = deepcopy(observed); changed['measurements'][0]['value']['value'] += 1
        monkeypatch.setattr(h.store, 'get', lambda ref: changed if ref == observed['id'] else original_get(ref))
        observed = changed
        checks = [lambda: validate_native_blast_database_observation(h.store, changed),
            lambda: _observation_extent(h.store, changed), lambda: _observation_extents(h.store, changed),
            lambda: native_metric_facts(entry, h.store, observation_refs=[changed['id']], received_record_refs=[changed['id']]), *readers]
        for check in checks:
            with pytest.raises(ValueError, match='frozen_observation_conflict'):
                check()
    finally:
        h.store.close()


def test_successful_original_collect_immediately_has_exact_zero_future_expectation(tmp_path, monkeypatch):
    from gene_annotation_episode.numerical import YieldParameters
    from test_practical_yield import completion_context
    h = SyntheticHost(tmp_path, monkeypatch)
    try:
        child = h.results()
        body = h.select(child, 0, 'execution.results.collect')['result']
        proof = h.family.completion_for_action(child, body['operation_key'])
        context = completion_context(run_id=h.run_id, episode_id=child.episode_id, unit_index=0, action_index=0)
        runtime_fields = {k: context['practical_completion'][k] for k in ('unit_ref', 'action_index')}
        context['practical_completion'] = {**proof, **runtime_fields}
        before = deepcopy(context)
        estimate = h.family.practical_estimator(child)((2.0,), YieldParameters(), (context,))
        assert estimate.expected_next_gain.lower == estimate.expected_next_gain.upper == 0
        assert context == before
        assert h.store.db.execute('SELECT COUNT(*) FROM runtime_actions WHERE run_id=? AND episode_id=?',
            (h.run_id, child.episode_id)).fetchone()[0] == 1
    finally:
        h.store.close()


def test_frozen_observation_requires_original_commission_handoff_and_record(tmp_path, monkeypatch):
    from gene_annotation_episode.native_blast_database_result_publication import (
        validate_native_blast_database_observation, validate_native_blast_database_publication)
    h = SyntheticHost(tmp_path, monkeypatch)
    try:
        child = h.results(query_selection(h))
        body = h.select(child, 0, 'execution.results.collect')['result']
        observation = h.store.get(body['publication']['rows_by_family']['hsp'][0]['observation_ref'])
        for episode_id, index in [(h.root.episode_id, 1), (h.hpc.episode_id, 0)]:
            saved = h.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',
                (h.run_id, episode_id, index)).fetchone()['action']
            altered = json.loads(saved)
            if episode_id == h.root.episode_id:
                altered['purpose'] = 'different parent commission'
            else:
                altered['arguments']['queue'] = 'different queue'
            h.store.db.execute('UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=?',
                (json.dumps(altered), h.run_id, episode_id, index))
            with pytest.raises(ValueError):
                validate_native_blast_database_observation(h.store, observation)
            h.store.db.execute('UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=?',
                (saved, h.run_id, episode_id, index))
            assert validate_native_blast_database_observation(h.store, observation)['family'] == 'hsp'
        h.store.db.execute('DELETE FROM records WHERE id=?', (observation['id'],))
        with pytest.raises(ValueError):
            validate_native_blast_database_publication(h.store, context=child, publication=body['publication'])
        assert h.store.query_records('observation')['total'] == 0
    finally:
        h.store.close()


def test_repeated_projection_receipts_retain_distinct_original_cells(tmp_path, monkeypatch):
    from gene_annotation_episode.communication import form_with_facts, validate_form
    h = SyntheticHost(tmp_path, monkeypatch)
    try:
        selection = selector('hsp')
        first = h.results(selection)
        h.select(first, 0, 'execution.results.collect')
        first_form, schema = h.returned(first)
        selection['projections'][0]['metrics'] = ['native_raw_score']
        second = h.results(selection, index=2)
        h.select(second, 0, 'execution.results.collect')
        second_form, _ = h.returned(second)
        received = h.family.native_blast_database_returns.received_facts(h.root, schema)
        rows = received['execution_blast_database_hsp_rows']
        assert len(rows) == 2 and rows[0]['record_key'] == rows[1]['record_key']
        assert rows[0]['calculation_id'] == rows[1]['calculation_id']
        with pytest.raises(ValueError) as failure:
            validate_form(form_with_facts({}, schema, received), schema, lambda *_: True)
        (tmp_path / 'projection-return-conflict.json').write_text(canonical(dict(
            original_forms=[first_form, second_form], schema=schema, received=received, failure=str(failure.value))))
    finally:
        h.store.close()
