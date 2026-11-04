"""Actual admitted function rows, frozen cell subsets and saved-handle authority."""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.communication import form_with_facts, validate_form
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.materials import artifact_path
from gene_annotation_episode.native_blast_database_result_publication import saved_function_input_descriptor
from gene_annotation_episode.native_blast_database_result_views import SAVED_INPUT_SOURCE
from test_native_blast_database_episode_binding import schema_for
from test_native_blast_vdb_function_integration import connected_fixture, capture, selection, results_child
from test_native_blast_vdb_function_recalculation import forbid_acquisition


def failure_triple(body):
    assert not body['complete'] and body['capture'] is body['observation'] is body['publication'] is None
    assert body['record_refs'] == [] and len(body['failures']) == 1
    return tuple(body['failures'][0][k] for k in ('stage','code','detail_code'))


AUTHORITY = ('authority','native_blast_database_return_unauthorized','scope_or_receipt_conflict')


def test_artifact_and_source_possession_without_requested_descriptor_is_not_authority(tmp_path, monkeypatch):
    h, selected = connected_fixture(tmp_path, monkeypatch)
    try:
        original, body = capture(h, selected, descriptors=False)
        assert body['complete']
        h.returned(original)
        descriptor = saved_function_input_descriptor(h.store, body)
        returns = h.family.native_blast_database_returns
        with pytest.raises(ValueError, match='unauthorized'):
            returns.resolve_saved_function_input(h.root, descriptor)
        with pytest.raises(ValueError, match='selected_input_not_received'):
            results_child(h, selection(saved=descriptor, temperature=2), index=2)
        # Possession of every real matching hash/source is still insufficient.
        refs = returns._references({SAVED_INPUT_SOURCE:[descriptor]})
        h.receipts.receive(h.root.episode_id, refs, kind='initial')
        before = deepcopy(h.calls)
        forbid_acquisition(h, monkeypatch)
        child, failed = capture(h, selection(saved=descriptor, temperature=2), index=2)
        assert failure_triple(failed) == AUTHORITY
        assert h.calls == before
        h.returned(child)
    finally:
        h.store.close()


def test_exact_descriptor_rejects_generation_receipt_scope_and_cycle_substitutions(tmp_path, monkeypatch):
    h, selected = connected_fixture(tmp_path, monkeypatch)
    try:
        original, body = capture(h, selected)
        h.returned(original)
        descriptor = h.family.native_blast_database_results.facts(original)[SAVED_INPUT_SOURCE][0]
        before = deepcopy(h.calls)
        forbid_acquisition(h, monkeypatch)
        mutations = [('generation', lambda d: d.update(original_calculation_id='0'*64)),
            ('interpretation',lambda d:d.update(input_interpretation_id='0'*64)),
            ('receipt_hash',lambda d:d['original_result_receipt'].update(receipt_sha256='0'*64)),
            ('other_run',lambda d:d['original_result_receipt'].update(run_id='different-run')),
            ('other_episode',lambda d:d['original_result_receipt'].update(episode_id=h.hpc.episode_id)),
            ('missing_operation',lambda d:d['original_result_receipt'].update(operation_key=body['operation_key'][:-1]+'99'))]
        failures = []
        for index,(name, mutate) in enumerate(mutations, 2):
            wrong = deepcopy(descriptor); mutate(wrong)
            child, failed = capture(h, selection(saved=wrong, temperature=2), index=index)
            assert failure_triple(failed) == AUTHORITY, name
            assert h.family.completion_for_action(child, failed['operation_key']) is None
            failures.append(dict(case=name,receipt=failed))
        owner = h.family.native_blast_database_results
        address = descriptor['original_result_receipt']
        repeated = tuple(address[k] for k in ('run_id','episode_id','operation_key'))
        with pytest.raises(ValueError, match='unauthorized'):
            owner._read_saved_function_input(descriptor, h.scope, _seen=(repeated,))
        foreign = h.store.create_problem(raw_sequence='TTTTTTTT', molecule='dna')['subject_refs']
        with pytest.raises(ValueError):
            owner.read_saved_function_input(descriptor, {'subject_refs':foreign})
        # A self-addressed request cannot become an original receipt authority.
        self_descriptor = deepcopy(descriptor)
        child = results_child(h, selection(saved=self_descriptor, temperature=2), index=20)
        self_descriptor['original_result_receipt'].update(episode_id=child.episode_id,
            operation_key=f'{h.run_id}:{child.episode_id}:0')
        with pytest.raises(ValueError, match='unauthorized'):
            owner.read_saved_function_input(self_descriptor, h.scope)
        assert h.calls == before
        (tmp_path/'authority-failures.json').write_text(canonical(failures))
    finally:
        h.store.close()


@pytest.mark.parametrize('change', ['sealed_bytes','missing_original_receipt'])
def test_changed_or_missing_originals_fail_without_fallback_acquisition(tmp_path, monkeypatch, change):
    h, selected = connected_fixture(tmp_path, monkeypatch)
    try:
        first, original = capture(h, selected); h.returned(first)
        descriptor = h.family.native_blast_database_results.facts(first)[SAVED_INPUT_SOURCE][0]
        child = results_child(h, selection(saved=descriptor, temperature=2), index=2)
        before = deepcopy(h.calls)
        forbid_acquisition(h, monkeypatch)
        owner = h.family.native_blast_database_results
        path = artifact_path(h.store, descriptor['sheets_artifact_ref']) if change == 'sealed_bytes' else None
        if change == 'missing_original_receipt':
            from gene_annotation_episode.execution_contracts import digest
            path = owner._directory(first) / digest(original['operation_key']) / 'receipt.json'
        raw = path.read_bytes()
        if change == 'sealed_bytes': path.write_bytes(raw + b'changed')
        else: path.unlink()
        try:
            failed = h.select(child, 0, 'execution.results.collect')['result']
            expected = ('worker','native_blast_database_frozen_artifact_changed','frozen_value_changed') if change == 'sealed_bytes' else AUTHORITY
            assert failure_triple(failed) == expected
            assert h.calls == before
        finally:
            path.write_bytes(raw)
        h.returned(child)
        assert owner.read_saved_function_input(descriptor, h.scope) == original
        (tmp_path/'rejected-original.json').write_text(canonical(failed))
    finally:
        h.store.close()


def test_actual_parent_unions_only_received_cells_and_forwards_saved_generation(tmp_path, monkeypatch):
    h, selected = connected_fixture(tmp_path, monkeypatch)
    try:
        outer = h.root
        source = 'execution_blast_database_vdb_function_rows'
        schema = schema_for(source, SAVED_INPUT_SOURCE)
        process = h.child(outer, 'scientific_process', {}, schema, index=1)
        h.root = process
        selected['projections'] = [p for p in selected['projections'] if p['family']=='vdb_function']
        selected['projections'][0]['metrics'] = ['prior']
        first, original = capture(h, selected, index=0)
        first_form, _ = h.returned(first)
        other = deepcopy(selected); other['projections'][0]['metrics'] = ['conditional_function_weight','representation_adjusted_function_weight']
        second, another = capture(h, other, index=1)
        h.returned(second)
        assert original['preparation']['calculation_id'] == another['preparation']['calculation_id']
        received = h.family.native_blast_database_returns.received_facts(process,schema)
        assert len(received[source]) == 2
        assert all({c['name'] for c in r['measurements']} == {'prior','conditional_function_weight','representation_adjusted_function_weight'} for r in received[source])
        for field in ('value','component_pointer','source_ref','calculation_id'):
            forged = form_with_facts({},schema,received)
            row = forged['field_0'][0]
            if field=='value': row['measurements'][0]['value'] += .25
            elif field=='component_pointer': row['measurements'][0][field]='/vdb_function/0/components/strata/999'
            elif field=='calculation_id': row[field]='f'*64
            else: row[field]=h.handoff
            with pytest.raises(ValueError): h.family.validate_received_report(process,forged,schema)
        forwarded, _ = h.deliver(process,outer,received)
        validate_form(forwarded,schema,lambda ref,ns:h.family.resolve_received_reference(outer,ref,ns))
        assert h.family.native_blast_database_returns.received_facts(outer,schema)==received
        before = deepcopy(h.calls)
        forbid_acquisition(h,monkeypatch)
        descriptor = received[SAVED_INPUT_SOURCE][0]
        h.root = outer
        third, recalculated = capture(h,selection(saved=descriptor,temperature=2,families=('vdb_function',)),index=2)
        assert recalculated['complete'], recalculated['failures']
        h.returned(third)
        all_received = h.family.native_blast_database_returns.received_facts(outer,schema)
        assert len(all_received[source]) == 4 and len({r['calculation_id'] for r in all_received[source]}) == 2
        assert h.calls==before and h.store.query_records('observation')['total']==0
        assert h.family.native_blast_database_returns.received_facts(process,schema)==received
        assert json.loads(h.store.db.execute('SELECT form FROM runtime_forms WHERE episode_id=?',(first.episode_id,)).fetchone()[0]) == first_form
        (tmp_path/'parent-return-union.json').write_text(canonical(dict(received=received,forwarded=forwarded,after_recalculation=all_received)))
    finally:
        h.store.close()
