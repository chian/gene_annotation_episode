"""Fresh isolated A104 task, call-entry-provider and prompt import orders.

CLI TREE SELECTION_JSON SELECTION_SHA FIRST_MODULE OUTPUT_JSON DEPENDENCY_ROOT...
Invoked only by the coordinator's serial isolated child runner.
"""
from __future__ import annotations
import hashlib
import importlib
import json
from pathlib import Path
import sys
import traceback

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a104'
FIRST_MODULES = ('execution_job_submission.api_job_execution.task', 'homology_job_monitoring.task', 'hpc_work_planning.execution_job_submission.task', 'execution_job_submission.task', 'published_evidence_assessment.task', 'execution_progress_assessment.task', 'execution_job_submission.hpc_job_execution.task', 'execution_job_submission.local_job_execution.task', 'hpc_work_planning.task', 'hpc_work_planning.hpc_resource_prediction.task', 'hpc_work_planning.execution_result_acquisition.task', 'execution_result_acquisition.task', 'scientific_process.task', 'homology_job_monitoring.yield', 'homology_job_submission.yield', 'homology_result_acquisition.yield', 'scientific_process.task_instructions', 'execution_job_submission.api_job_execution.task_instructions', 'homology_job_submission.task', 'homology_job_submission.episode', 'homology_job_monitoring.episode', 'homology_result_acquisition.task', 'homology_result_acquisition.episode', 'homology_job_monitoring.task_state', 'homology_job_monitoring.task_decision', 'homology_job_monitoring.task_action', 'homology_job_monitoring.decision_inputs', 'homology_job_monitoring.decision_context')
FIXTURE_SHA = '83130a45c6ecd1296b2443e0040b448e2b49a7336be52e786759acf47bacce87'
def sha(raw): return hashlib.sha256(raw).hexdigest()
def main():
    assert len(sys.argv) >= 6 and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
    tree = Path(sys.argv[1]).resolve(strict=True)
    selection_path, pin, first = Path(sys.argv[2]).resolve(strict=True), sys.argv[3], sys.argv[4]
    output = Path(sys.argv[5]).resolve()
    assert first in FIRST_MODULES and not output.exists() and output.parent.is_dir() and output.is_relative_to(tree.parent)
    raw = selection_path.read_bytes(); assert sha(raw) == pin
    selection = json.loads(raw); rows = {row['target']: row for row in selection['rows']}
    assert len(rows) == len(selection['rows'])
    for target in rows: assert not Path(target).is_absolute() and '..' not in Path(target).parts
    dependencies = [Path(value).resolve(strict=True) for value in sys.argv[6:]]
    assert all(path.is_dir() and path != tree for path in dependencies)
    sys.path[:0] = [str(tree), *map(str, dependencies)]
    record = {'version': 'a104_registered_provider_cold_v2', 'first_module': first,
        'source_selection': {'path': str(selection_path), 'sha256': pin}, 'tree': str(tree),
        'dependency_roots': list(map(str, dependencies)), 'application_workflow_executed': False, 'passed': False}
    status = 1
    try:
        importlib.import_module(PACKAGE + '.' + first)
        runtime = importlib.import_module(PACKAGE + '.runtime')
        fixture = tree / PACKAGE.replace('.', '/') / 'tests/fixtures/source_request_assembly/a104_registered_provider_preservation.json.txt'
        raw = fixture.read_bytes(); assert sha(raw) == FIXTURE_SHA
        packet = json.loads(raw); case = packet['cold'][first]
        task_module = importlib.import_module(case['task_module']); task = vars(task_module)[case['task_class']]
        assert task.__module__ == case['task_module'] and task.__name__ == case['task_class']
        checked = []
        for row in case['members']:
            module = importlib.import_module(row['module'])
            owner = module if row['owner'] is None else vars(module)[row['owner']]
            function = vars(owner)[row['member']]
            assert function.__globals__ is vars(importlib.import_module(row['namespace']))
            assert function.__module__ == row['module'] and function.__qualname__ == row['qualified_name']
            assert function.__code__.co_filename == module.__file__ and function.__closure__ is None
            checked.append(row['qualified_name'])
        assert checked
        homology_aliases = []
        for expected in packet['homology_lifecycle_aliases']:
            home = expected['home']
            episode = importlib.import_module(PACKAGE + '.' + home + '.episode')
            controller = importlib.import_module(PACKAGE + '.' + home + '.yield')
            context = importlib.import_module(PACKAGE + '.' + home + '.decision_context')
            declaration = vars(episode)['HomologyEpisode']
            assert vars(runtime)[expected['runtime_alias']] is declaration
            task_owner = importlib.import_module(PACKAGE + '.' + home + '.task')
            assert vars(declaration)['decision_source_type'] is vars(task_owner)[expected['task_class']]
            descriptor = vars(declaration)['controller_selection']
            assert type(descriptor) is staticmethod and descriptor.__func__ is vars(controller)['select_controller']
            assert descriptor.__func__.__globals__ is vars(runtime)
            for name in expected['public_provider_aliases']:
                assert vars(context)[name] is vars(runtime)[name]
            homology_aliases.append({'home': home, 'runtime_alias': expected['runtime_alias'],
                'task_class': expected['task_class'], 'controller_module': descriptor.__func__.__module__,
                'controller_qualname': descriptor.__func__.__qualname__, 'public_provider_aliases': expected['public_provider_aliases']})
        lifecycle = importlib.import_module(PACKAGE + '.library.homology_runtime_binding')
        assert vars(lifecycle)['_RUNTIME_NAMESPACE'] is vars(runtime) and vars(lifecycle)['_PENDING'] == {}
        assert set(vars(lifecycle)['_READY']) == set(vars(lifecycle)['_ENTRIES'])
        origins = {}
        for name, module in tuple(sys.modules.items()):
            if not (name in ('gene_annotation_episode', 'method_loop') or name.startswith(('gene_annotation_episode.', 'method_loop.'))): continue
            file = vars(module).get('__file__')
            if file is None:
                paths = vars(module).get('__path__'); assert paths is not None and all(Path(path).resolve().is_relative_to(tree) for path in paths), name
                continue
            path = Path(file).resolve(strict=True); assert path.is_relative_to(tree), (name, str(path))
            target = str(path.relative_to(tree)); assert target in rows, (name, target)
            row = rows[target]; digest = sha(path.read_bytes())
            assert row.get('descriptor_byte_operand_only') is not True, ('descriptor_bytes_imported', name, target)
            assert digest == row['source']['sha256'] and path.stat().st_mode & 0o7777 == row['mode'], (name, target)
            origins[name] = {'target': target, 'sha256': digest, 'path': str(path)}
        assert PACKAGE + '.' + first in origins and runtime.__name__ in origins and case['task_module'] in origins
        record.update(passed=True, bound_members_checked=checked, project_origins=origins,
            task_class={'module': task.__module__, 'qualname': task.__qualname__}, fixture_sha256=FIXTURE_SHA,
            homology_alias_identities=homology_aliases, complete_ready_entry_count=len(vars(lifecycle)['_READY']))
        status = 0
    except BaseException as error:
        record['error'] = {'type': type(error).__module__ + '.' + type(error).__qualname__, 'message': str(error), 'traceback': traceback.format_exc()}
    with output.open('x') as stream: json.dump(record, stream, indent=2); stream.write('\n')
    raise SystemExit(status)
if __name__ == '__main__': main()
