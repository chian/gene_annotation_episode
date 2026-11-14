"""Actual A110 readers over original360 Store/actions/typed closed reports.

The declared current test factory is NOT recovered old global authority. Its
ordinary backend is an explicit test-only read dependency using current tools;
no old resource policy, software path or factory descriptor is rebound.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import sqlite3
from types import SimpleNamespace
from unittest.mock import patch
import traceback

from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources, commission

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a110.'
PIN = '7a3e9d961da978a8bc382539dcf21f6e224f26d4ac786d571fd4d60edfae18ae'
PARENTS = ('', 'scientific_process', 'hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution',
    'scientific_process/hpc_work_planning', 'scientific_process/hpc_work_planning/hpc_allocation_execution')


def module(name): return importlib.import_module(PREFIX + name.replace('/', '.'))
def plain(value): return module('communication').plain(value)
def sha(raw): return hashlib.sha256(raw).hexdigest()
def forbidden(*args, **kwargs): raise AssertionError('saved_fba_reader_attempted_new_execution')


def observe(function):
    try: return {'status': 'returned', 'value': plain(function())}
    except Exception as error:
        return {'status': 'raised', 'type': type(error).__module__ + '.' + type(error).__qualname__,
            'message': str(error), 'traceback': traceback.format_exc()}


def comparable(value): return {key: item for key, item in value.items() if key != 'traceback'}


def open_saved(directory):
    # The separately retained actual constructor observation authenticates
    # this supported Store path on an exact copy of the original database.
    return module('state').Store(directory)


def build_registry(store, run_id, directory, *, partial, connected):
    services = SimpleNamespace(annotation_task_required=lambda: False)
    tools = module('tools').ToolRegistry(store)
    # This actual backend read port consumes only original Store custody. It
    # has no configured native resource. Its saved-record methods do not call
    # _selection, execute, native preparation, solving or result calculation.
    tools.ordinary_flux_balance_backend = module('flux_balance_tools').OrdinaryFluxBalanceTools(tools)
    assert tools._flux_balance_configuration is None
    factory = module('execution_service_setup').ExecutionServiceFactory(resources(), {}, 3., 2., 1.,
        log_window_bytes=1024, log_roles=('stdout', 'stderr'))
    factory.configure_tool_registry(tools)
    assert tools._flux_balance_configuration is None
    definition = plain(factory.as_record())
    library = SimpleNamespace(as_record=lambda: {}, headers=lambda: [])
    science = module('scientific_process/episode').ScientificProcessEpisode(services,
        library=library, tool_library=library,
        child_roles=('scientific_process', 'hpc', 'launch', 'results', 'monitor', 'literature'))
    bindings = [science]
    for home in ('hpc_work_planning', 'scientific_process/hpc_work_planning'):
        for suffix in ('', '/hpc_allocation_execution', '/hpc_resource_prediction'):
            bindings.append(module(home + suffix + '/episode').HPCEpisode(services,
                store=store, run_id=run_id, directory=directory, resources=resources(),
                commissions={'commission': commission()}))
    own = None
    for parent in PARENTS[2:] if partial else PARENTS:
        prefix = parent + '/' if parent else ''
        for suffix in ('execution_job_submission', 'execution_job_submission/local_job_execution',
                'execution_job_submission/hpc_job_execution', 'execution_result_acquisition'):
            home = prefix + suffix
            binding = module(home + '/episode').ExecutionEpisode(services, store=store,
                run_id=run_id, directory=directory, tool_registry=tools,
                **{key: definition[key] for key in ('resources', 'initial_information',
                    'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles')})
            bindings.append(binding)
            if home == 'hpc_work_planning/execution_result_acquisition': own = binding
        bindings.append(module(prefix + 'execution_progress_assessment/episode').MonitorEpisode(services))
    assert own is not None and len(bindings) == (27 if partial else 37)
    registry = module('episode_bindings').EpisodeBindingRegistry(bindings)
    catalog = None
    if connected:
        configuration = module('library/received_execution_information/received_configuration').ReceivedExecutionConfiguration.original_global_factory(
            factory, authority_id='explicit-current-fba-reader-test-factory')
        catalog = configuration.construct(store=store, run_id=run_id, directory=directory,
            tool_registry=tools, services=services)
        registry.configure_received_execution_information(catalog,
            module('annotation_received_execution_information').received_execution_information)
    return registry, own, catalog, tools, factory


def run_case(fixture, destination, *, partial, connected):
    provenance = json.loads((fixture / 'provenance.json').read_text())
    assert provenance['database_sha256'] == PIN and provenance['historical_run_returncode'] == 1
    assert sha((fixture / 'store/state.sqlite3').read_bytes()) == PIN
    shutil.copytree(fixture / 'store', destination / 'store')
    store = open_saved(destination / 'store')
    try:
        raw_settings = [dict(row) for row in store.db.execute('SELECT * FROM runtime_runs')]
        episodes = list(store.db.execute('SELECT * FROM runtime_episodes ORDER BY json_array_length(path)'))
        assert len(episodes) == 2 and all(row['state'] == 'yielded' for row in episodes)
        run_id, = {row['run_id'] for row in episodes}
        records = module('episode_return_records').EpisodeReturnRecords(store, run_id, failure_prefix='genuine_fba_probe_')
        parent, science = [records.context(row['episode_id']) for row in episodes]
        attempt, = list(store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=?', (run_id,)))
        assert attempt['parent_episode_id'] == parent.episode_id and attempt['child_episode_id'] == science.episode_id
        assert attempt['failure'] is None
        returned = json.loads(attempt['form'])
        schema = json.loads(attempt['contract'])['measurements']['schema']
        frozen, = list(store.db.execute('SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?', (run_id, science.episode_id)))
        assert returned == json.loads(frozen['form'])
        before_construct = list(store.db.iterdump())
        registry, owner, catalog, tools, factory = build_registry(store, run_id, destination / 'workflow',
            partial=partial, connected=connected)
        callbacks = module('tests/general_received_registry_probe').originals()
        original = lambda name, *args: callbacks[name](owner, *args)
        boundary_rows = []
        def boundary(label, name, args, actual):
            expected = observe(lambda: original(name, *args))
            observed = observe(actual)
            row = {'label': label, 'callback': name, 'original': expected, 'registry': observed}
            if connected:
                reader = catalog.configured('@annotation')
                row['dedicated_reader'] = observe(lambda: getattr(reader, name)(*args))
                row['matches_original'] = comparable(row['dedicated_reader']) == comparable(expected) == comparable(observed)
            boundary_rows.append(row)
            (destination / 'boundary-observations.json').write_text(json.dumps(boundary_rows, indent=2) + '\n')
            return expected
        after_construct = list(store.db.iterdump())
        for context in (parent, science):
            boundary(context.role + ':sources', 'received_report_sources', (context.role,),
                lambda context=context: registry.received_report_sources(context.role, path=context.path))
            facts = boundary(context.role + ':facts', 'received_report_facts', (context,),
                lambda context=context: registry.received_report_facts(context))
            if context is science:
                assert facts['status'] == 'returned' and facts['value']['flux_balance_measurements']
                assert facts['value']['flux_balance_edited_models'] == returned['edited_models']
                assert facts['value']['flux_balance_saved_sheets'] == returned['saved_sheets']
            boundary(context.role + ':closure', 'received_report_closure_facts', (context,),
                lambda context=context: registry._received_report_mapping('received_report_closure_facts', context))
        # Parent public context has its own empty report; read the child's actual
        # returned FBA schema explicitly without changing that parent request.
        received = owner.native_flux_balance_returns.received_facts(parent, schema)
        for field in ('measurements', 'model_views', 'saved_sheets', 'edited_models', 'failures'):
            assert received['flux_balance_' + field] == returned[field]
        for context in (parent, science):
            validated = boundary(context.role + ':original_form_validation', 'validate_received_report',
                (context, returned, schema),
                lambda context=context: registry.validate_received_report(context, returned, schema))
            assert validated['status'] == 'returned'
        files = returned['saved_sheets'] + returned['edited_models']
        assert files
        for context in (parent, science):
            for file in files:
                expected = boundary(context.role + ':received_file:' + file['artifact_ref'], 'resolve_received_reference',
                    (context, file['artifact_ref'], 'artifact'),
                    lambda context=context, file=file: registry.resolve_received_reference(context, file['artifact_ref'], 'artifact'))
                assert expected == {'status': 'returned', 'value': True}
                module('native_file_capture').retained_native_file(store, file)
        operation_key = f'{run_id}:{parent.episode_id}:{attempt["decision_index"]}:typed_form'
        snapshot = list(store.db.iterdump())
        references = boundary('original_same_key_admission', 'received_form_references',
            (parent, returned, schema, operation_key),
            lambda: registry.received_form_references(parent, returned, schema, operation_key))
        assert references['status'] == 'returned'
        assert {file['artifact_ref'] for file in files} <= set(references['value'])
        boundary('original_same_key_replay', 'received_form_references', (parent, returned, schema, operation_key),
            lambda: registry.received_form_references(parent, returned, schema, operation_key))
        assert list(store.db.iterdump()) == snapshot
        changed = deepcopy(returned)
        changed['measurements'] = []
        invalid = boundary('changed_original_form', 'received_form_references', (parent, changed, schema, operation_key),
            lambda: registry.received_form_references(parent, changed, schema, operation_key))
        assert invalid['status'] == 'raised' and 'admitted_form_conflict' in invalid['message']
        assert list(store.db.iterdump()) == snapshot
        for source in store.db.execute("SELECT data FROM records WHERE record_type='source' AND json_extract(data,'$.provider')='perform_flux_balance_analysis'"):
            value = json.loads(source['data'])
            for reference in (value['request_ref'], value['artifact_ref']):
                for context in (parent, science):
                    expected = boundary(context.role + ':private_or_unreceived:' + reference, 'resolve_received_reference',
                        (context, reference, 'artifact'),
                        lambda context=context, reference=reference: registry.resolve_received_reference(context, reference, 'artifact'))
                    assert expected['status'] == 'returned' and expected['value'] is not True
        assert [dict(row) for row in store.db.execute('SELECT * FROM runtime_runs')] == raw_settings
        assert list(store.db.iterdump()) == after_construct
        return {'phase': 'connected' if connected else 'baseline', 'partial': partial,
            'constructor_bypass': False,
            'actual_store_constructor': PREFIX + 'state.Store',
            'actual_store_source_sha256': sha(Path(module('state').__file__).read_bytes()),
            'actual_connection_pragmas': {name: store.db.execute('PRAGMA ' + name).fetchone()[0]
                for name in ('foreign_keys', 'journal_mode', 'synchronous')},
            'bindings': len(registry._bindings), 'original_settings': raw_settings,
            'declared_test_factory': plain(factory.as_record()),
            'historical_factory_reconstruction': False, 'original_failure_returncode': 1,
            'test_only_dependency': 'actual OrdinaryFluxBalanceTools read port, native configuration absent',
            'tool_configuration': tools._flux_balance_configuration,
            'current_native_policy_was_not_derived_from_old_receipt': True,
            'constructor_database_unchanged': before_construct == after_construct,
            'rows_unchanged_after_reader_boundaries': True, 'original_operation_key': operation_key,
            'complete_child_returned_values': returned, 'actual_parent_received_values': received,
            'boundaries': boundary_rows,
            'connected_matches': None if not connected else all(row['matches_original'] for row in boundary_rows),
            'full_saved_workflow_reopen': 'separate_unexecuted_boundary'}
    finally: store.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--phase', choices=('baseline', 'connected'), required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    fixture = Path(__file__).parent / 'fixtures/genuine_fba360'
    results = []
    with ExitStack() as stack:
        for name in ('prepare_job', 'start_prepared', 'resume_start', 'wait_job', 'collect', 'status'):
            stack.enter_context(patch(PREFIX + 'native_lifecycle.' + name, forbidden))
        for name in ('run_selected_flux_balance_native', 'run_selected_flux_balance_result_worker', 'capture_flux_balance_native_files'):
            stack.enter_context(patch(PREFIX + 'flux_balance_tools.' + name, forbidden))
        stack.enter_context(patch('subprocess.Popen', forbidden))
        stack.enter_context(patch('socket.create_connection', forbidden))
        stack.enter_context(patch(PREFIX + 'acquisition.PublicClients._http', forbidden))
        for partial in (False, True):
            outcome = observe(lambda partial=partial: run_case(fixture,
                args.output / ('partial' if partial else 'full'), partial=partial, connected=args.phase == 'connected'))
            results.append({'partial': partial, 'outcome': outcome})
            (args.output / 'fba_receiving_probe.json').write_text(json.dumps(results, indent=2) + '\n')
    failed = any(row['outcome']['status'] != 'returned' or (
        args.phase == 'connected' and row['outcome']['value']['connected_matches'] is not True) for row in results)
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__': main()
