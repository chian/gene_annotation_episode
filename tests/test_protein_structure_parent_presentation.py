"""Current parent rendering of a real retained protein typed return.

The original parent stopped after its child returned. This test reconstructs
its in-memory post-return state and enters the current DecisionSource builder;
it does not claim a historical callback, replay the Workflow or acquire data.
"""
import asyncio
from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
from types import SimpleNamespace

import pytest

from method_loop import Episode, EpisodeCompletion, EpisodeGoal, EpisodeRequest
from method_loop.archive import ArchivedRecord
from method_loop.communication import ReportContract
from method_loop.episode import EpisodeUpdate, EpisodeView
from method_loop.identities import EpisodeRef

from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import (
    apply_state_frame, instructional_model_context, state_frame,
)
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.protein_structure_action_records import (
    VIEW_SOURCE, frozen_protein_structure_action_facts,
)
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import DecisionSource, Record, Workflow
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

import test_protein_structure_saved_workflow as retained


_PROOF_ENV = 'HMMER_NATIVE_ORACLE_PROTEIN_PARENT_PRESENTATION_PROOF'
_PIN_ENV = _PROOF_ENV + '_SHA256'


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path.resolve()), sha256=_sha(raw), size_bytes=len(raw))


def _inventory(directory):
    root = Path(directory)
    return {str(path.relative_to(root)): dict(mode=path.lstat().st_mode,
        **({'target': os.readlink(path)} if path.is_symlink() else
           {'sha256': _sha(path.read_bytes()), 'size_bytes': path.stat().st_size}
           if path.is_file() else {}))
        for path in [root, *sorted(root.rglob('*'))]}


def _tables(connection):
    result = {}
    for row in connection.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name"):
        name, schema = row
        quoted = '"' + name.replace('"', '""') + '"'
        info = [list(entry) for entry in connection.execute('PRAGMA table_info(' + quoted + ')')]
        columns = [entry[1] for entry in info]
        result[name] = dict(columns=columns, column_info=info, schema=schema,
            rows=[list(entry) for entry in connection.execute('SELECT * FROM ' + quoted)])
    return result


def _encoded_rows(rows):
    return Counter(canonical(row) for row in rows)


def _old_rows_unchanged(before, after):
    """Permit only actual empty tables and all-NULL nullable column migrations."""
    migrations = {}
    for name, old in before.items():
        current = after[name]
        indices = [current['columns'].index(column) for column in old['columns']]
        assert _encoded_rows(old['rows']) == _encoded_rows(
            [[row[index] for index in indices] for row in current['rows']])
        extra = [index for index, column in enumerate(current['columns']) if column not in old['columns']]
        assert all(row[index] is None for row in current['rows'] for index in extra)
        assert all(current['column_info'][index][3] == 0 for index in extra)
        if extra:
            migrations[name] = dict(nullable_columns=[current['columns'][index] for index in extra])
    for name in after.keys() - before.keys():
        assert after[name]['rows'] == []
        migrations[name] = dict(new_empty_table=True)
    return migrations


def _forbidden(*_args, **_kwargs):
    raise AssertionError('parent presentation attempted scientific work, publication, replay or dispatch')


def _guard_work(monkeypatch):
    for method in ('build', 'selected', 'execute', 'dispatch_commission'):
        monkeypatch.setattr(Workflow, method, _forbidden)
    for method in ('run', 'run_async'):
        monkeypatch.setattr(Episode, method, _forbidden)
    for method in ('execute', 'execute_async'):
        monkeypatch.setattr(ToolRegistry, method, _forbidden)
    for method in ('artifact', 'put', 'commit_reasoning'):
        monkeypatch.setattr(Store, method, _forbidden)
    for method in ('execute', 'apply_response', 'finish', 'call'):
        monkeypatch.setattr(DecisionSource, method, _forbidden)
    monkeypatch.setattr(_SessionConnection, 'complete', _forbidden)
    for method in ('prepare_job', 'start_prepared', 'resume_start', 'wait_job', 'collect', 'status'):
        monkeypatch.setattr(retained.native_lifecycle, method, _forbidden)
    for target in (
        'gene_annotation_episode.protein_structure_tools.run_cancellable_native',
        'gene_annotation_episode.protein_structure_tools.resolve_protein_structure_operands',
        'gene_annotation_episode.protein_structure_calculations.fit_ca_transform',
        'gene_annotation_episode.protein_structure_calculations.calculate_protein_structure_components',
        'gene_annotation_episode.protein_structure_formats.parse_pdb_structure',
        'gene_annotation_episode.protein_structure_formats.parse_mmcif_structure',
        'gene_annotation_episode.protein_structure_result_views.project_protein_structure_results',
        'gene_annotation_episode.protein_structure_action_records.project_protein_structure_action_views',
        'gene_annotation_episode.acquisition.PublicClients._http',
        'socket.create_connection',
    ):
        monkeypatch.setattr(target, _forbidden)


def _request(record):
    assert record['report_contract'] is None
    result = EpisodeRequest(EpisodeGoal.from_record(record['goal']), Record(deepcopy(record['message'])), None)
    assert plain(result.as_record()) == record
    return result


def _view(flow, parent, archive, form, science):
    assert archive['episode_id'] == parent.episode_id and archive['run_id'] == parent.run_id
    assert archive['path'] == [list(item) for item in parent.path]
    assert archive['request'] == plain(parent.request)
    assert archive['ended_by'] == 'yield_stop' and archive['units_consumed'] == 1
    unit, = archive['units']
    recorded = unit['episode_update']
    assert unit['child_result'] == dict(form=form)
    assert recorded['record_id'] == science.episode_id and recorded['report'] == form
    assert recorded['goal'] == plain(science.request)['goal']
    assert recorded['report_contract'] == plain(science.request)['report_contract']
    assert recorded['delivery_failures'] == []
    # ArchivedRecord.load authenticated this complete child as part of the
    # parent expansion. Join its real identity/request and method completion
    # fields before constructing the validated completion value directly.
    child = unit['child']
    assert child['episode_id'] == science.episode_id and child['run_id'] == science.run_id
    assert child['episode_ref'] == EpisodeRef(science.run_id, science.path).as_record()
    assert child['path'] == [list(item) for item in science.path]
    assert child['scope_level'] == science.role and child['scope_key'] == science.path[-1][1]
    assert child['request'] == plain(science.request) and child['goal'] == recorded['goal']
    completion_fields = {'ended_by', 'end_reason', 'units_consumed'}
    assert set(recorded['completion']) == completion_fields
    assert recorded['completion'] == {key: child[key] for key in completion_fields}
    assert child['units_consumed'] == len(child['units'])
    assert recorded['controller_input'] == unit['controller_input']
    completion = EpisodeCompletion(**recorded['completion'])
    assert completion.as_record() == recorded['completion']
    contract = ReportContract.from_record(recorded['report_contract'])
    report = contract.admit(form, audit_identifiers=(science.episode_id, recorded['goal']['goal_id']))
    update = EpisodeUpdate(record_id=recorded['record_id'],
        goal=EpisodeGoal.from_record(recorded['goal']),
        completion=completion,
        controller_input=Record(deepcopy(recorded['controller_input'])), report=report,
        delivery_failures=(), _audit_identifiers=(science.episode_id, recorded['goal']['goal_id']))
    assert plain(update.as_record()) == recorded
    return EpisodeView(grain=flow.grains['annotation'], key=parent.path[-1][1], path=parent.path,
        units_consumed=archive['units_consumed'], updates=(update,),
        controller_state=deepcopy(archive['controller_state']),
        episode_ref=EpisodeRef(parent.run_id, parent.path), request=_request(plain(parent.request)))


def _assert_literal_values(context, wire, form):
    assert context['child_reports'] == [form]
    steering = wire.split('\nSTEERING\n', 1)[1]
    by_id = {view['selection']['projection_id']: (index, view)
        for index, view in enumerate(form['views'])}
    assert len(form['views']) == 6
    index, summary = by_id['saved-summary']
    values = {cell['field']: cell for cell in summary['outcome']['rows'][0]['values']}
    expected = {'mapped_pair_count': 2, 'evaluation_used_count': 2, 'above_threshold_count': 1,
        'above_threshold_fraction': .5, 'evaluation_sse': 1., 'evaluation_rmsd': .7071067811865476}
    for field, wanted in expected.items():
        cell = values[field]
        assert cell['value']['value'] == wanted and cell['value']['state'] == 'present'
    assert values['above_threshold_fraction']['population']['numerator'] == 1
    assert values['above_threshold_fraction']['population']['denominator'] == 2
    assert values['evaluation_sse']['value']['unit'] == 'angstrom_squared'
    assert values['evaluation_rmsd']['value']['unit'] == 'angstrom'
    assert values['fit_used_count']['value'] == dict(value=None, state='not_applicable',
        reason='mode_not_applicable', unit='pair', origin='derived')
    # Match every exact retained leaf in the real child-report section, rather
    # than finding the same numbers in a schema or generic instruction prose.
    for row_index, row in enumerate(summary['outcome']['rows']):
        for cell_index, cell in enumerate(row['values']):
            prefix = f'| [0].views[{index}].outcome.rows[{row_index}].values[{cell_index}]'
            assert prefix + '.field | ' + cell['field'] + ' |' in steering
            for key, value in cell['value'].items():
                literal = 'null' if value is None else str(value)
                assert prefix + '.value.' + key + ' | ' + literal + ' |' in steering
            for key in ('numerator', 'denominator'):
                assert prefix + '.population.' + key + ' | ' + (
                    'null' if cell['population'][key] is None else str(cell['population'][key])) + ' |' in steering
    site_index, sites = by_id['saved-distances']
    assert [row['values'][0]['value']['value'] for row in sites['outcome']['rows']] == [0., 1.]
    for row_index, row in enumerate(sites['outcome']['rows']):
        for cell_index, cell in enumerate(row['values']):
            prefix = f'| [0].views[{site_index}].outcome.rows[{row_index}].values[{cell_index}]'
            assert prefix + '.field | ' + cell['field'] + ' |' in steering
            for key, value in cell['value'].items():
                assert prefix + '.value.' + key + ' | ' + ('null' if value is None else str(value)) + ' |' in steering
    unavailable_index, unavailable = by_id['unrequested_coordinates']
    assert unavailable['outcome']['version'] == 'protein_structure_action_unavailable_v1'
    for issue_index, issue in enumerate(unavailable['outcome']['issues']):
        for key, value in issue.items():
            if value is None or isinstance(value, (str, int, float)):
                assert f'| [0].views[{unavailable_index}].outcome.issues[{issue_index}].{key} | ' + (
                    'null' if value is None else str(value)) + ' |' in steering
    # The delivered artifact-table descriptor stays a descriptor; it is not
    # promoted to site measurements or an implicit File grant.
    table_index, table = by_id['distances']
    assert table['outcome']['version'] == 'protein_structure_action_artifact_view_v1'
    assert 'rows' not in table['outcome']
    assert 'artifact_descriptor_not_numerical_delivery' in table['outcome']['qualifications']
    for key, value in table['outcome']['delivery']['table_file'].items():
        assert f'| [0].views[{table_index}].outcome.delivery.table_file.{key} | ' + str(value) + ' |' in steering


@pytest.mark.skipif(not os.environ.get(_PROOF_ENV), reason='opt-in authentic retained protein parent presentation')
def test_retained_protein_parent_full_current_builder_and_session(tmp_path, monkeypatch):
    proof_path = Path(os.environ[_PROOF_ENV]).resolve(strict=True)
    proof_pin = _pin(proof_path)
    assert proof_pin['sha256'] == os.environ[_PIN_ENV]
    recovery = json.loads(proof_path.read_text())
    assert recovery['version'] == 'protein_structure_saved_closed_verification_v1'
    assert recovery['passed'] and recovery['phase'] == 'verified'
    assert recovery['actual_parent_and_closed_child_archive_return_equal']
    original_path = Path(recovery['original_prefix']['path']).resolve(strict=True)
    assert _pin(original_path) == recovery['original_prefix']
    original = json.loads(original_path.read_text())
    assert original['question'] == retained.QUESTION and original['passed'] is False
    source_database = Path(recovery['owned_database']['path']).resolve(strict=True)
    assert _pin(source_database) == recovery['owned_database']
    assert not any(Path(str(source_database) + suffix).exists() for suffix in ('-wal', '-shm'))
    config = original['configuration']
    original_store, original_run = Path(original['owned_store_directory']), Path(config['directory'])
    originals = {str(path): _inventory(path) for path in
        (Path(original['original_store']), original_store, original_run)}
    raw_refs = original['raw_input_refs']
    assert len(raw_refs) == 3
    for directory in (Path(original['original_store']), original_store):
        assert all(not (directory / 'artifacts' / reference[9:11] / reference[9:]).exists()
            for reference in raw_refs)
    # Only the already consolidated, authenticated425 database is copied. The
    # original418 WAL family is never opened or used for SQLite recovery.
    historical = tmp_path / 'historical.sqlite3'
    shutil.copyfile(source_database, historical)
    assert _pin(historical)['sha256'] == recovery['owned_database']['sha256']
    connection = sqlite3.connect(historical.as_uri() + '?mode=ro&immutable=1', uri=True)
    state = tmp_path / 'current-state'
    state.mkdir()
    destination = sqlite3.connect(state / 'state.sqlite3')
    try:
        before = _tables(connection)
        connection.backup(destination)
        assert _tables(destination) == before
    finally:
        destination.close()
        connection.close()
    for name in ('artifacts', 'cache'):
        if (original_store / name).exists():
            shutil.copytree(original_store / name, state / name, symlinks=True)
    run = tmp_path / 'current-read-side'
    shutil.copytree(original_run, run, symlinks=True)
    for reference in raw_refs:
        assert not (state / 'artifacts' / reference[9:11] / reference[9:]).exists()
    _guard_work(monkeypatch)
    attempts = []
    retained._guard_raw_files(monkeypatch,
        [Path(original['original_store']), original_store, state], raw_refs, attempts)
    store = Store(state)
    result = dict(version='protein_parent_current_full_builder_presentation_v1', passed=False,
        original_proof=proof_pin, original_database=recovery['owned_database'],
        historical_parent_postresult_callback_claimed=False, original_Workflow_replay=False,
        in_memory_state_reconstructed_from_authentic_archive=True,
        new_native=0, new_calculations=0, new_tool_actions=0, new_model_calls=0,
        new_provider_calls=0, new_publications=0)
    try:
        records = EpisodeReturnRecords(store, original['run_id'], failure_prefix='protein_parent_presentation_')
        rows = list(store.db.execute('SELECT * FROM runtime_episodes WHERE run_id=? ORDER BY json_array_length(path)',
            (original['run_id'],)))
        assert len(rows) == 2
        parent, science = (records.context(row['episode_id']) for row in rows)
        assert parent.role == 'annotation' and science.role == 'scientific_process'
        attempt, = list(store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=?', (parent.run_id,)))
        form = json.loads(store.db.execute('SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?',
            (science.run_id, science.episode_id)).fetchone()[0])
        assert attempt['parent_episode_id'] == parent.episode_id and attempt['child_episode_id'] == science.episode_id
        assert attempt['failure'] is None and json.loads(attempt['form']) == form == recovery['verified']['form']
        assert json.loads(attempt['contract']) == plain(science.request)['report_contract']
        archive = recovery['restored_fields']['archive']
        descriptor = json.loads(rows[0]['archive'])
        assert Path(descriptor['file']).name == descriptor['file']
        assert _pin(original_run / 'archive' / descriptor['file'])['sha256'] == descriptor['sha256']
        # Authenticate the physical parent/index and recursively authenticate
        # each referenced child before comparing the complete expanded value.
        assert ArchivedRecord(original_run / 'archive' / descriptor['file'],
            descriptor['sha256'], descriptor['index_sha256']).load() == archive
        library = ScientificProcessLibrary(run / 'scientific-process-library')
        tool_library = ScientificToolLibrary(run / 'scientific-tool-library')
        old_binding = config['scientific_binding']
        current_binding = ScientificProcessEpisodes(None, library=library, tool_library=tool_library,
            child_roles=old_binding['configuration']['child_roles']).as_record()
        assert current_binding['configuration'] == old_binding['configuration']
        factory = ExecutionServiceFactory.from_record(config['factory'])
        assert factory.as_record() == config['factory']
        provider = SimpleNamespace(complete=_forbidden, release=_forbidden)
        flow, _tools, _factory = retained._workflow(store, run, parent.run_id,
            plain(factory.resources), plain(factory.protein_structure_environments),
            current_binding, provider, factory=factory)
        assert flow.execution_binding is None
        assert flow.services.protein_structure_action_received_facts(parent, fact_source=VIEW_SOURCE) == form['views']
        assert frozen_protein_structure_action_facts(store, parent.run_id, science,
            fact_source=VIEW_SOURCE) == form['views']
        constructor = _old_rows_unchanged(before, _tables(store.db))
        initialized = _tables(store.db)
        initialized_files = _inventory(run)
        artifact_files = _inventory(state / 'artifacts')
        known = set(flow.receipts.known(parent.episode_id))
        old_known = {row['record_ref'] for row in recovery['restored_fields']['receipts']
            if row['episode_id'] == parent.episode_id}
        assert known == old_known
        initial_files = {row['record_ref'] for row in recovery['restored_fields']['receipts']
            if row['episode_id'] == parent.episode_id and row['receipt_kind'] == 'initial'
            and row['record_ref'].startswith('artifact_')}
        assert initial_files and initial_files <= known and set(raw_refs).isdisjoint(known)
        for view in form['views']:
            assert view['source_ref'] in known
            source = store.get(view['source_ref'])
            assert set([source['artifact_ref'], source['request_ref'], *source['auxiliary_artifact_refs']]).isdisjoint(known)
        view = _view(flow, parent, archive, form, science)
        source = DecisionSource(flow, parent.path, view.request, plain(parent.scope))
        assert source.episode_id == parent.episode_id and plain(source.request.as_record()) == plain(parent.request)
        calls = list(store.db.execute('SELECT * FROM runtime_model_calls WHERE run_id=? AND episode_id=? ORDER BY call_index',
            (parent.run_id, parent.episode_id)))
        actions = list(store.db.execute('SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index',
            (parent.run_id, parent.episode_id)))
        assert len(calls) == len(actions) == archive['units_consumed'] == 1
        assert calls[0]['response'] is not None and actions[0]['result'] is not None
        assert actions[0]['credit'] == archive['units'][0]['controller_input']['credit']
        assert json.loads(actions[0]['action'])['role'] == science.role
        assert json.loads(actions[0]['result'])['status'] == 'completed'
        # These are transient source fields, reconstructed at the actual next
        # cursor after the one authenticated answered/completed parent action.
        source.calls = calls[-1]['call_index'] + 1
        source.last_outcome_index = actions[-1]['decision_index']
        source.last_outcome = json.loads(actions[-1]['result'])
        assert source.calls == 1 and source.last_outcome_index == 0
        role = dict(model='presentation-engineering-control', reasoning_effort='low')
        session = _SessionConnection({'connection': {'command': ['unselected-model-command']},
            'FAST': role, 'REASONING': role, 'routing': {}}, tmp_path / 'parent-session', tmp_path)
        captured = []

        class ParentContextCaptured(Exception):
            pass

        async def capture(actual, context, schema):
            assert actual is source and actual.calls == 1
            assert context['goal'] == plain(parent.request)['goal']
            assert context['scope'] == plain(parent.scope) and context['child_reports'] == [form]
            assert context['last_local_outcome'] == source.last_outcome
            instructions = actual.instructions(context)
            current = instructional_model_context(context)
            frame = state_frame(current)
            assert apply_state_frame(None, frame) == current
            wire, sent_instructions = session._presentation(parent.episode_id, 'REASONING', instructions, frame)
            assert wire.startswith('TASK\n') and '\nSTEERING\n' in wire
            assert retained.QUESTION in wire and instructions in wire and sent_instructions == instructions
            assert '/home/chia/' not in wire and 'ordinary-tool-binding.json' not in wire
            _assert_literal_values(current, wire, form)
            continuation = state_frame(current, current)
            again, _ = session._presentation(parent.episode_id, 'REASONING', instructions, continuation)
            assert again == wire
            captured.append(dict(context=context, model_context=current, schema=plain(schema),
                instructions=instructions, frame=frame, continuation=continuation, wire=wire,
                wire_sha256=_sha(wire.encode()), wire_size_bytes=len(wire.encode())))
            raise ParentContextCaptured('current full parent builder stopped before provider or journal dispatch')

        monkeypatch.setattr(DecisionSource, 'call', capture)
        monkeypatch.setattr(flow.journal, 'save', _forbidden)
        store.db.execute('PRAGMA query_only=ON')
        with pytest.raises(ParentContextCaptured, match='before provider or journal dispatch'):
            asyncio.run(source.next(view))
        assert len(captured) == 1 and attempts == []
        assert session.process is None and session.call_index == session.request_index == 0
        assert _tables(store.db) == initialized
        assert _inventory(run) == initialized_files and _inventory(state / 'artifacts') == artifact_files
        assert set(flow.receipts.known(parent.episode_id)) == known
        assert records.context(parent.episode_id).as_record() == parent.as_record()
        result.update(passed=True, full_current_parent_builder_verified=True,
            actual_parent_episode_id=parent.episode_id, actual_child_episode_id=science.episode_id,
            next_call_index=source.calls, original_parent_calls=len(calls), constructor_migrations=constructor,
            original_request_sha256=_sha(canonical(plain(parent.request)).encode()),
            actual_form_sha256=_sha(canonical(form).encode()), selected_view_count=len(form['views']),
            old_known=sorted(known), legitimate_initial_files=sorted(initial_files),
            original_rows_unchanged=True, owned_artifacts_and_workflow_files_unchanged=True,
            original_input_bodies_absent=True, original_input_body_attempts=attempts,
            original_binding=old_binding, readside_binding=current_binding, presentation=captured[0])
    except BaseException as error:
        result['failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        store.close()
        assert _pin(source_database) == recovery['owned_database'] and _pin(proof_path) == proof_pin
        assert _pin(original_path) == recovery['original_prefix']
        assert {path: _inventory(path) for path in originals} == originals
        result['original_files_and_modes_unchanged'] = True
        result['owned_database'] = _pin(state / 'state.sqlite3')
        (tmp_path / 'PROTEIN_PARENT_CURRENT_PRESENTATION.json').write_text(
            json.dumps(result, indent=2, allow_nan=False) + '\n')
