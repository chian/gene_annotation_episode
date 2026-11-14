"""Actual runtime settings, after the separately installed CORE57 boundary.

No runtime_runs/settings are synthesized here. The existing registered helper
executes _run_bound_workflow and intercepts its first root build after durable
registration. Its literal private factories and operational projectors remain
unchanged. This module cannot run before that genuine helper is installed.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from unittest.mock import patch

from .api_cases import HOMES, Responses, error_record, module, rows
from . import registered_saved_bindings as registered


def file_map(root):
    root = Path(root)
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob('*')) if path.is_file()}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def capture(output):
    output = Path(output).resolve()
    assert not output.exists(); output.mkdir(parents=True)
    records = []
    for index, home in enumerate(HOMES):
        live, archive = output / 'live' / str(index), output / 'archives' / str(index)
        live.mkdir(parents=True)
        with module('state').Store(live / 'store') as store:
            store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
            client = Responses()
            workflow, registration = registered.registered_workflow(store, live / 'workflow', home, client)
            assert client.calls == []
            actual = dict(workflow.journal.row('runtime_runs'))
            assert actual == registration['actual_runtime_run']
            settings = json.loads(actual['settings'])
            assert settings == registration['actual_settings']
            assert settings['episode_job_progress_provider'] == workflow.episode_job_progress_provider_binding
            saved = {'home': home, 'run_id': workflow.run_id, 'registration': registration,
                'runtime_run': actual, 'settings': settings, 'logical_rows': rows(store),
                'live': str(live), 'root_build_intercepted': True,
                'annotation_execution_or_full_iterator_claimed': False}
        write(live / 'capture.json', saved)
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(live, archive)
        assert file_map(live) == file_map(archive)
        records.append({'home': home, 'live': str(live), 'archive': str(archive),
            'files': file_map(archive)})
        write(output / 'registration_index.json', records)
    return {'version': 'a104_native_progress_actual_registration_capture_v1',
        'records': records, 'index_sha256': hashlib.sha256((output / 'registration_index.json').read_bytes()).hexdigest(),
        'registered_helper_sha256': hashlib.sha256(Path(registered.__file__).read_bytes()).hexdigest()}


def authenticate(captured, custody):
    captured = Path(captured).resolve()
    assert custody['version'] == 'a104_native_progress_actual_registration_capture_v1'
    raw = (captured / 'registration_index.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == custody['index_sha256']
    records = json.loads(raw)
    assert records == custody['records'] and [row['home'] for row in records] == list(HOMES)
    assert hashlib.sha256(Path(registered.__file__).read_bytes()).hexdigest() == custody['registered_helper_sha256']
    for index, row in enumerate(records):
        assert Path(row['live']) == captured / 'live' / str(index)
        assert Path(row['archive']) == captured / 'archives' / str(index)
        assert file_map(row['archive']) == row['files']
        saved = json.loads((Path(row['archive']) / 'capture.json').read_bytes())
        assert saved['home'] == row['home'] and saved['live'] == row['live']
        assert saved['settings'] == json.loads(saved['runtime_run']['settings'])
    return records


def selected_resume_comparisons(workflow):
    # These are the actual runtime comparisons, in its original guard order.
    selected_bindings = workflow.episode_bindings.as_record()
    selected_role_bindings = {role: {'definition': module('runtime')._plain(definition),
        'projector': module('runtime')._binding_name(workflow.role_credit_projectors[role], 'caller_injected')}
        for role, definition in workflow.role_credit_definitions.items()}
    return [
        ('episode_bindings', selected_bindings, [], 'resumption_requires_original_episode_bindings'),
        ('episode_role_credit_bindings', selected_role_bindings, {}, 'resumption_requires_original_episode_role_credit_bindings'),
        ('episode_job_progress_provider', workflow.episode_job_progress_provider_binding, None,
            'resumption_requires_original_episode_job_progress_provider'),
    ]


def reopen(captured, output, *, custody, expected_changed):
    assert type(expected_changed) is bool
    records = authenticate(captured, custody)
    output = Path(output).resolve(); assert not output.exists(); output.mkdir(parents=True)
    observations = []
    for row in records:
        live, archive = Path(row['live']), Path(row['archive'])
        assert file_map(live) == row['files']  # Exact original saved directory, no path rewrite.
        saved = json.loads((archive / 'capture.json').read_bytes())
        with module('state').Store(live / 'store') as store:
            before = rows(store)
            assert before == saved['logical_rows']
            client = Responses()
            runtime = module('runtime')
            original_assemble = runtime.assemble_workflow
            assembled = []
            def observe_assembly(*args, **kwargs):
                workflow = original_assemble(*args, **kwargs)
                assembled.append(workflow)
                return workflow
            try:
                with patch.object(runtime, 'assemble_workflow', observe_assembly):
                    workflow, registration = registered.registered_workflow(store, live / 'workflow',
                        row['home'], client, resume=True)
            except Exception as error:
                assert runtime.assemble_workflow is original_assemble and len(assembled) == 1
                comparisons = selected_resume_comparisons(assembled[0])
                different = [code for key, actual, default, code in comparisons
                    if actual != saved['settings'].get(key, default)]
                assert expected_changed and type(error) is module('runtime').WorkflowError
                assert different and str(error) == different[0]
                result = {'raised': error_record(error)}
            else:
                assert runtime.assemble_workflow is original_assemble and assembled == [workflow]
                comparisons = selected_resume_comparisons(workflow)
                different = [code for key, actual, default, code in comparisons
                    if actual != saved['settings'].get(key, default)]
                assert not different
                assert not expected_changed
                assert registration == saved['registration'] and workflow.run_id == saved['run_id']
                result = {'returned_registration': registration}
            assert client.calls == [] and rows(store) == before
            # The recorded settings remain the original contract, even when
            # resume rejects a supplied current provider. No alias is written.
            actual = module('episode_journal').Journal(store, saved['run_id']).row('runtime_runs')
            assert dict(actual) == saved['runtime_run']
        assert file_map(archive) == row['files']
        observations.append({'home': row['home'], 'boundary': result,
            'selected_resume_comparisons': [{'setting': key, 'actual': deepcopy(actual),
                'saved': deepcopy(saved['settings'].get(key, default)), 'guard': code}
                for key, actual, default, code in comparisons],
            'first_original_guard': different[0] if different else None,
            'original_settings': deepcopy(saved['settings']), 'all_rows_unchanged': True,
            'historical_archive_unchanged': True, 'full_iterator_restoration_claimed': False})
        write(output / 'registration_reopen.json', observations)
    assert authenticate(captured, custody) == records
    return observations
