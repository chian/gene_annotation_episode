"""MinHash custody and typed-admission checks using real selected episode work.

Only the HTTP boundary and episode choices are synthetic. Each Store below is
fresh; all mutations exercise this test's receipts and are restored afterward.
No live BV-BRC access, credentials, runtime replacement or invented request is
used. This complements the selected-process path tests.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
import asyncio
import json

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.practical_execution_records import canonical as record_json
from gene_annotation_episode.runtime import TypedReportContract
from gene_annotation_episode.state import Store

from bvbrc_minhash_episode_fixture import (
    MinhashRun, SyntheticHTTP, child, fact_form, request,
)


def runtime_records(run):
    result = {}
    for name, in run.store.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'runtime_%'"):
        columns = {row[1] for row in run.store.db.execute('PRAGMA table_info(' + name + ')')}
        if 'run_id' in columns:
            result[name] = sorted(canonical(row) for row in run.rows(name))
    return result


def episode_contexts(run):
    return {json.loads(row['path'])[-1][0]: run.context(row['episode_id'])
            for row in run.rows('runtime_episodes')}


@contextmanager
def changed_record(store, sql, operands):
    store.db.execute('SAVEPOINT minhash_boundary_record')
    try:
        store.db.execute(sql, operands)
        yield
    finally:
        store.db.execute('ROLLBACK TO minhash_boundary_record')
        store.db.execute('RELEASE minhash_boundary_record')


@contextmanager
def changed_json(path, change):
    original = path.read_bytes()
    value = json.loads(original)
    change(value)
    path.write_text(record_json(value) + '\n')
    try:
        yield
    finally:
        path.write_bytes(original)


@pytest.fixture(scope='module')
def completed_run(tmp_path_factory):
    directory = tmp_path_factory.mktemp('minhash-return-boundaries')
    with pytest.MonkeyPatch.context() as monkeypatch, Store(directory / 'state') as store:
        http = SyntheticHTTP(monkeypatch, request())
        run = MinhashRun(store, directory / 'run')
        run.run()
        assert len(http.calls) == 1
        yield run, http


def test_own_and_received_boundary_rejects_wrong_context_and_fabricated_source(completed_run):
    run, http = completed_run
    contexts = episode_contexts(run)
    reference, = run.received_form['references']
    host = run.api.minhash
    history = runtime_records(run)
    assert host.read_own(reference, context=contexts['results'])['source_ref'] == reference
    for role in ('annotation', 'scientific_process', 'launch', 'launch_api'):
        with pytest.raises(ValueError, match='results_owner_required'):
            host.read_own(reference, context=contexts[role])
    for fake in (
            replace(contexts['results'], run_id='unrelated-run'),
            replace(contexts['results'], episode_id=contexts['annotation'].episode_id),
            replace(contexts['results'], assignment={'selector': {}})):
        with pytest.raises(ValueError, match='context_conflict'):
            host.read_own(reference, context=fake)

    source = run.store.get(reference)
    forged = {key: value for key, value in source.items()
              if key not in {'id', 'record_type', 'origin'}}
    forged['uri'] = 'https://unselected.synthetic.invalid/response'
    with changed_record(run.store, 'SELECT 1', ()):
        fabricated = run.store.put('source', forged, origin='external')['id']
        assert fabricated != reference
        with pytest.raises(ValueError, match='not_an_api_acquired_result'):
            host.read_own(fabricated, context=contexts['results'])
        for role in ('annotation', 'scientific_process', 'launch'):
            assert host.resolve_received(contexts[role], fabricated, 'execution_result') is False
        bad = deepcopy(run.received_form)
        bad['matches'][0]['source_ref'] = fabricated
        with pytest.raises(ValueError):
            run.workflow.validate_report(bad, run.scope, grain='results',
                schema=run.result_form, context=contexts['results'])

    # Root actually received only counts. A valid opaque reference has no
    # authority to expand the root's received fact families or genome IDs.
    assert host.resolve_received(contexts['annotation'], reference, 'execution_result')
    assert host.received_facts(contexts['annotation'], fact_form('bvbrc_minhash_matches')) == {
        'bvbrc_minhash_matches': []}
    assert not host.resolve_received(contexts['annotation'], '83333.1', 'bvbrc_minhash_genome')
    assert host.received_context(contexts['launch']) == []
    assert runtime_records(run) == history
    assert len(http.calls) == 1


def test_record_admission_requires_original_form_schema_receiver_and_operation(completed_run):
    run, http = completed_run
    contexts = episode_contexts(run)
    context = contexts['scientific_process']
    key = f'{run.run_id}:{context.episode_id}:1:typed_form'
    attempt = run.store.db.execute('SELECT form,contract FROM runtime_report_attempts '
        'WHERE run_id=? AND parent_episode_id=? AND decision_index=1',
        (run.run_id, context.episode_id)).fetchone()
    form = json.loads(attempt['form'])
    schema = json.loads(attempt['contract'])['measurements']['schema']
    history = runtime_records(run)
    reference, = run.received_form['references']
    for _ in range(2):
        assert run.api.minhash.record_admission(context, form, schema, key) == [reference]
    for value in (999, True):
        forged = deepcopy(form)
        forged['counts'][0]['returned_row_count'] = value
        with pytest.raises(ValueError, match='admitted_form_conflict'):
            run.api.minhash.record_admission(context, forged, schema, key)
    changed = deepcopy(schema)
    changed['properties']['counts']['items']['properties']['returned_row_count']['maximum'] = 999
    with pytest.raises(ValueError, match='admitted_form_conflict'):
        run.api.minhash.record_admission(context, form, changed, key)
    for invalid in (key.replace(':1:typed_form', ':01:typed_form'),
                    key.removesuffix(':typed_form'), key + ':extra',
                    key.replace(run.run_id, 'unrelated-run', 1)):
        with pytest.raises(ValueError, match='admission_operation_required'):
            run.api.minhash.record_admission(context, form, schema, invalid)
    with pytest.raises(ValueError, match='admission_operation_required'):
        run.api.minhash.record_admission(contexts['annotation'], form, schema, key)
    with pytest.raises(ValueError, match='successful_return_required'):
        run.api.minhash.record_admission(context, form, schema,
            f'{run.run_id}:{context.episode_id}:999:typed_form')
    assert runtime_records(run) == history
    assert len(http.calls) == 1


def test_selected_action_and_original_acquisition_links_reject_corruption(completed_run):
    run, http = completed_run
    context = episode_contexts(run)['results']
    reference, = run.received_form['references']
    (directory, outcome), = run.api._own_outcomes(context)
    history = runtime_records(run)
    action = json.loads(run.workflow.journal.row('runtime_actions', context.episode_id, 0)['action'])
    action['tool'] = 'api.bvbrc.minhash.genome'
    with changed_record(run.store,
            'UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=0',
            (canonical(action), run.run_id, context.episode_id)):
        with pytest.raises(ValueError, match='api_selected_action_conflict'):
            run.api.minhash.read_own(reference, context=context)
    with changed_record(run.store,
            'UPDATE runtime_actions SET result=NULL WHERE run_id=? AND episode_id=? AND decision_index=0',
            (run.run_id, context.episode_id)):
        with pytest.raises(ValueError, match='completed_acquisition_required'):
            run.api.minhash.read_own(reference, context=context)
    for path, change, code in (
            (directory / 'acquisition.json', lambda data: data.update(snapshot_sha256='0' * 64),
             'api_result_acquisition_receipt_conflict'),
            (directory / 'intent.json', lambda data: data['prepared']['request'].update(query='999.1'),
             'original_selection_conflict'),
            (directory / 'intent.json', lambda data: data['prepared']['rpc_request']['params'].__setitem__(0, '999.1'),
             'original_selection_conflict'),
            (directory / 'snapshot.json', lambda data: data.update(retrieved_at='2099-01-01T00:00:00Z'),
             'source_request_conflict')):
        with changed_json(path, change):
            with pytest.raises(ValueError, match=code):
                run.api.minhash.read_own(reference, context=context)
    assert run.api.minhash.read_own(reference, context=context)['source_ref'] == reference
    assert runtime_records(run) == history
    assert len(http.calls) == 1


@pytest.mark.parametrize('artifact_kind', ['raw', 'request', 'rpc', 'grading'])
def test_saved_artifact_bytes_are_digest_checked(completed_run, artifact_kind):
    run, http = completed_run
    context = episode_contexts(run)['results']
    reference, = run.received_form['references']
    source = run.store.get(reference)
    retained = json.loads(run.store.get_artifact(source['request_ref']))
    artifacts = {'raw': source['artifact_ref'], 'request': source['request_ref'],
        'rpc': retained['rpc_request_artifact_ref'], 'grading': source['auxiliary_artifact_refs'][0]}
    digest = artifacts[artifact_kind].removeprefix('artifact_')
    path = run.store.path / 'artifacts' / digest[:2] / digest
    original, history = path.read_bytes(), runtime_records(run)
    try:
        path.write_bytes(original + b' ')
        with pytest.raises(ValueError, match='artifact_digest_mismatch'):
            run.api.minhash.read_own(reference, context=context)
    finally:
        path.write_bytes(original)
    assert run.api.minhash.read_own(reference, context=context)['source_ref'] == reference
    assert runtime_records(run) == history
    assert len(http.calls) == 1


def test_reopen_and_original_action_replay_preserve_saved_grades_and_histories(completed_run, monkeypatch):
    run, http = completed_run
    contexts = episode_contexts(run)
    reference, = run.received_form['references']
    grading = run.api.minhash.read_own(reference, context=contexts['results'])['grading']
    received = run.api.minhash.received_context(contexts['scientific_process'])
    history, archive = runtime_records(run), deepcopy(run.archive)
    outcomes = {role: next(run.api._own_outcomes(contexts[role]))[1]
                for role in ('launch_api', 'results')}

    def forbidden(*args, **kwargs):
        raise AssertionError('Saved return replay attempted invocation or regrading')

    for module in ('api_bvbrc_minhash', 'bvbrc_minhash_grader'):
        for function in ('parse_minhash_result', 'calculate_minhash_components'):
            monkeypatch.setattr('gene_annotation_episode.' + module + '.' + function, forbidden)
    monkeypatch.setattr('gene_annotation_episode.api_bvbrc_minhash.BVBRCMinhashService.invoke', forbidden)
    with Store(run.store.path) as reopened:
        replay = MinhashRun(reopened, run.directory, scope=run.scope)

        async def no_model(*args, **kwargs):
            raise AssertionError('Saved return replay attempted another model decision')

        replay.complete = no_model
        assert replay.run() == archive
        assert replay.api.minhash.read_own(reference, context=replay.context(contexts['results'].episode_id))['grading'] == grading
        assert replay.api.minhash.received_context(replay.context(contexts['scientific_process'].episode_id)) == received
        for role, operation in (('launch_api', 'api.bvbrc.minhash.genome'),
                                ('results', 'api.bvbrc.minhash.result')):
            context = replay.context(contexts[role].episode_id)
            assert asyncio.run(replay.api.execute(context, operation, {},
                f'{run.run_id}:{context.episode_id}:0')) == outcomes[role]
        assert runtime_records(replay) == history
    assert runtime_records(run) == history
    assert len(http.calls) == 1


def test_saved_typed_admission_is_visible_before_receipt_projection_without_new_action(tmp_path, monkeypatch):
    http = SyntheticHTTP(monkeypatch, request())
    with Store(tmp_path / 'state') as store:
        run = MinhashRun(store, tmp_path / 'run')
        stages = []
        original_admit = TypedReportContract.admit
        original_save = run.workflow.save_attempt
        original_receive = run.workflow.receive_form

        def relevant(schema):
            return any(node.get('x-source') == 'bvbrc_minhash_matches'
                       for node in schema.get('properties', {}).values())

        def scientific_context(child_id):
            context = run.context(child_id)
            return run.api.minhash.context(next(row['episode_id'] for row in run.rows('runtime_episodes')
                if json.loads(row['path']) == plain(context.path[:-1])))

        def checked_admit(contract, value, *, audit_identifiers):
            if not relevant(contract.schema):
                return original_admit(contract, value, audit_identifiers=audit_identifiers)
            context = scientific_context(audit_identifiers[0])
            saved = store.db.execute('SELECT form FROM runtime_report_attempts '
                'WHERE run_id=? AND parent_episode_id=? AND child_episode_id=? '
                'AND form IS NOT NULL AND failure IS NULL',
                (run.run_id, context.episode_id, audit_identifiers[0])).fetchone()
            if saved is not None:
                # The shared method loop validates the already admitted form
                # once more when constructing its EpisodeUpdate. It creates
                # neither another delivery attempt nor another own action.
                history = runtime_records(run)
                received = run.api.minhash.received_context(context)
                admitted = original_admit(contract, value, audit_identifiers=audit_identifiers)
                assert run.api.minhash.received_context(context) == received
                assert runtime_records(run) == history
                stages.append('later_boundary_revalidation')
                return admitted
            assert run.api.minhash.received_context(context) == []
            stages.append('before_typed_admit')
            admitted = original_admit(contract, value, audit_identifiers=audit_identifiers)
            assert run.api.minhash.received_context(context) == []
            stages.append('after_typed_admit_before_save')
            return admitted

        def checked_save(parent_id, index, delivery_ref, child_id, contract, *, form=None, failure=None):
            result = original_save(parent_id, index, delivery_ref, child_id, contract,
                form=form, failure=failure)
            if form is not None and relevant(contract.schema):
                context = run.context(parent_id)
                materialized = run.api.minhash.received_context(context)
                assert {row['fact_source'] for row in materialized} == {
                    'bvbrc_minhash_matches', 'bvbrc_minhash_counts'}
                action = run.workflow.journal.row('runtime_actions', parent_id, index)
                assert action['result'] is None and action['credit'] is None
                references = {row['source_ref'] for entry in materialized for row in entry['facts']}
                assert not references.intersection(run.workflow.receipts.known(parent_id))
                stages.append('saved_admission_before_receipts_and_credit')
            return result

        def checked_receive(source, admitted, schema, index, *, redelivery=False):
            result = original_receive(source, admitted, schema, index, redelivery=redelivery)
            if relevant(schema):
                references = {row['source_ref'] for row in admitted['matches']}
                assert references <= set(run.workflow.receipts.known(source.episode_id))
                stages.append('receipt_projection')
            return result

        monkeypatch.setattr(TypedReportContract, 'admit', checked_admit)
        monkeypatch.setattr(run.workflow, 'save_attempt', checked_save)
        monkeypatch.setattr(run.workflow, 'receive_form', checked_receive)
        run.run()
        assert stages[:4] == ['before_typed_admit', 'after_typed_admit_before_save',
            'saved_admission_before_receipts_and_credit', 'receipt_projection']
        assert stages.count('before_typed_admit') == 1
        assert stages.count('saved_admission_before_receipts_and_credit') == 1
        assert stages.count('later_boundary_revalidation') == 1
        for role, count in (('annotation', 2), ('scientific_process', 3),
                            ('launch', 1), ('launch_api', 1), ('results', 1)):
            context = episode_contexts(run)[role]
            assert len(run.rows('runtime_actions', context.episode_id)) == count
            assert len(run.rows('runtime_observations', context.episode_id)) == count
        assert len(http.calls) == 1


class RepeatedResultsRun(MinhashRun):
    """Select a second original results child instead of the final fixture wait."""

    async def complete(self, episode_id, role, instructions, current, schema):
        if 'scientific_process' in current and self.calls.get(episode_id, 0) == 2:
            self.calls[episode_id] = 3
            self.contexts.append((episode_id, deepcopy(current)))
            self.scientific_after_result = deepcopy(current)
            self.received_form = deepcopy(current['child_reports'][-1])
            return child('results', {'version': 'execution_results_assignment_v1',
                'handoff_ref': self.handoff, 'selector': {}}, self.scope, self.result_form)
        return await super().complete(episode_id, role, instructions, current, schema)


def test_two_selected_result_owners_can_read_same_retained_source(tmp_path, monkeypatch):
    http = SyntheticHTTP(monkeypatch, request())
    with Store(tmp_path / 'state') as store:
        run = RepeatedResultsRun(store, tmp_path / 'run')
        run.run()
        children = [run.context(row['episode_id']) for row in run.rows('runtime_episodes')
                    if json.loads(row['path'])[-1][0] == 'results']
        assert len(children) == 2
        reference, = run.received_form['references']
        history = runtime_records(run)
        grades = [run.api.minhash.read_own(reference, context=context)['grading'] for context in children]
        assert grades[0] == grades[1]
        science = episode_contexts(run)['scientific_process']
        received = run.api.minhash.received_context(science)
        assert next(row['facts'] for row in received if row['fact_source'] == 'bvbrc_minhash_counts') == [
            {'source_ref': reference, 'returned_row_count': 2,
             'parse_status': 'ok', 'population_size': None, 'truncated': None}]
        assert len(next(row['facts'] for row in received if row['fact_source'] == 'bvbrc_minhash_matches')) == 2
        assert len(run.rows('runtime_actions', science.episode_id)) == 3
        assert len(run.rows('runtime_observations', science.episode_id)) == 3
        for context in children:
            assert len(run.rows('runtime_actions', context.episode_id)) == 1
            assert len(run.rows('runtime_observations', context.episode_id)) == 1
        repeated = next(context for context in children if context.path[-1][1] == 'child_2')
        assert run.rows('runtime_actions', repeated.episode_id)[0]['credit'] == 0
        assert runtime_records(run) == history
        assert len(http.calls) == 1
