"""Diagnostic baseline for root execution; never starts a native/provider operation."""
from __future__ import annotations

import asyncio
from dataclasses import replace
import importlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import (
    commission, recorded_queue, resources,
)


PREFIX = 'gene_annotation_episode.episodic_workflow.root.a104.'
ROOT = Path(__file__).resolve().parents[4]
RUN = Path(sys.argv[1]).resolve()
assert RUN.is_relative_to(ROOT / 'runs')
RUN.mkdir(parents=True, exist_ok=True)


def module(name):
    return importlib.import_module(PREFIX + name.replace('/', '.'))


def observe(callback):
    try:
        value = callback()
    except Exception as error:
        return {'status': 'raised', 'type': type(error).__name__, 'message': str(error)}
    return {'status': 'returned', 'value': module('communication').plain(value)}


def main():
    Bindings = module('episode_bindings')
    EpisodeRef = module('method_loop.identities').EpisodeRef
    c, r = commission(), resources()
    axis = PREFIX.rstrip('.').rsplit('.', 1)[1]
    run_id = axis+'-launch-registry-source-baseline'
    directory = RUN / 'workflow'
    services = SimpleNamespace(annotation_task_required=lambda: False)
    report = {'purpose': 'actual full '+axis.upper()+' HPC registry diagnostic baseline',
        'native_or_model_operations': 0, 'contexts': [], 'parent_contexts': []}
    with module('state').Store(RUN / 'store') as store:
        # Actual scientific Store scope validation requires a recorded problem,
        # even though this diagnostic never runs an assay or native operation.
        problem = store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        scope = {'subject_refs': problem['subject_refs']}
        common_hpc = dict(store=store, run_id=run_id, directory=directory,
            resources=r, commissions={'commission': c})
        common_execution = dict(store=store, run_id=run_id, directory=directory,
            resources=r, initial_information={}, tool_registry=None,
            handoff_unit=1., acquired_record_unit=1., log_window_bytes=1024,
            log_roles=('stdout', 'stderr'))
        library = SimpleNamespace(as_record=lambda: {}, headers=lambda: [])
        science = module('scientific_process.episode').ScientificProcessEpisode(
            services, library=library, tool_library=library,
            child_roles=('scientific_process', 'hpc'))
        all_bindings = [science]
        roots = {}
        branches = {}
        for parent_home in ('hpc_work_planning', 'scientific_process/hpc_work_planning'):
            parent = module(parent_home + '/episode').HPCEpisode(services, **common_hpc)
            allocation_home = parent_home + '/hpc_allocation_execution'
            allocation = module(allocation_home + '/episode').HPCEpisode(services, **common_hpc)
            prediction = module(parent_home + '/hpc_resource_prediction/episode').HPCEpisode(
                services, **common_hpc)
            roots[parent_home] = parent
            all_bindings.extend((parent, allocation, prediction))
            for home, binding in ((parent_home, parent), (allocation_home, allocation)):
                execution = module(home + '/episode').create_execution_bindings(
                    services, **common_execution)
                launch_home = home + '/execution_job_submission'
                expected_execution = [launch_home]
                if axis != 'a110':
                    expected_execution.append(launch_home + '/api_job_execution')
                expected_execution.extend((launch_home + '/local_job_execution',
                    launch_home + '/hpc_job_execution', home + '/execution_result_acquisition'))
                assert [item.binding_path for item in execution] == expected_execution
                monitor = module(home + '/execution_progress_assessment/episode').MonitorEpisode(
                    services)
                all_bindings.extend((*execution, monitor))
                branches[home] = (binding, execution[0])
        registry = Bindings.EpisodeBindingRegistry(all_bindings)
        report['registered_bindings'] = [binding.binding_path for binding in all_bindings]
        assert len(all_bindings) == {'a102': 31, 'a103': 31, 'a104': 31,
            'a107': 31, 'a110': 27}[axis]

        def initial_context_receipt(context):
            rows = []
            for selected in registry._context_bindings(context):
                callback = getattr(selected, 'initial_decision_context', None)
                if callback is not None:
                    rows.append({'binding_path': selected.binding_path,
                        **observe(lambda: callback(context))})
            return {'role': context.role, 'path': [list(part) for part in context.path],
                'callbacks': rows, 'registry': observe(lambda: registry.initial_decision_context(context))}

        for parent_home, parent in roots.items():
            path = ((('scientific_process', 'science'), ('hpc', 'parent'))
                if parent_home.startswith('scientific_process/')
                else (('annotation', 'root'), ('hpc', 'parent')))
            owner = Bindings.BindingContext(run_id, EpisodeRef(run_id, path).episode_id,
                'hpc', path, scope, {'commission_id': 'commission'}, {})
            parent.initialize(owner)
            for home in (parent_home, parent_home + '/hpc_allocation_execution'):
                binding, launch = branches[home]
                context = owner
                if binding is not parent:
                    allocation_path = path + (('hpc_execution', 'allocation'),)
                    context = replace(owner, role='hpc_execution', path=allocation_path,
                        episode_id=EpisodeRef(run_id, allocation_path).episode_id,
                        assignment={'commission_id': 'commission',
                                    'owner_episode_id': owner.episode_id})
                    binding.initialize(context)
                report['parent_contexts'].append({'binding_path': binding.binding_path,
                    **initial_context_receipt(context)})
                ledger = binding.state(context)
                queue_ref = ledger.put('queue', {'snapshot': recorded_queue(module('hpc_queue'))})
                outcome = asyncio.run(binding.execute(context, 'hpc.plan',
                    {'candidate_id': c['candidates'][0]['id'], 'model_ref': 'reference_model',
                     'queue_ref': queue_ref}, 'baseline-plan:' + home))
                assert outcome['status'] == 'completed', outcome
                plan = ledger.read(outcome['result']['plan_ref'])
                launch_path = context.path + (('launch', 'original-launch'),)
                launched = replace(context, role='launch', path=launch_path,
                    episode_id=EpisodeRef(run_id, launch_path).episode_id,
                    assignment=plan['launch_assignment'])
                assert registry.for_path(launched.path) is launch
                row = {'binding_path': launch.binding_path, 'callbacks': []}
                selected = registry._context_bindings(launched)
                seen = {}
                for item in selected:
                    callback = getattr(item, 'initial_decision_context', None)
                    if callback is None:
                        continue
                    result = observe(lambda: callback(launched))
                    info = {'binding_path': item.binding_path, **result}
                    if result['status'] == 'returned':
                        keys = sorted(result['value'])
                        info['keys'] = keys
                        info['duplicate_fields'] = {key: seen[key] for key in keys if key in seen}
                        for key in keys:
                            seen.setdefault(key, item.binding_path)
                    row['callbacks'].append(info)
                row['registry_initial_decision_context'] = observe(
                    lambda: registry.initial_decision_context(launched))
                row['registry_received_report_sources'] = observe(
                    lambda: registry.received_report_sources(launched.role, path=launched.path))
                row['registry_received_report_facts'] = observe(
                    lambda: registry.received_report_facts(launched))
                row['launch_permitted_common_actions'] = observe(
                    lambda: launch.permitted_common_actions(launched))
                row['launch_incoming_advertised_schema'] = observe(
                    lambda: launch.child_assignment_schema(context, 'launch'))
                native_path = launch_path + (('launch_hpc', 'original-native-child'),)
                native = replace(launched, role='launch_hpc', path=native_path,
                    episode_id=EpisodeRef(run_id, native_path).episode_id,
                    assignment=plan['practical_assignment'])
                row['native_binding_path'] = registry.for_path(native.path).binding_path
                row['native_registry_initial_decision_context'] = observe(
                    lambda: registry.initial_decision_context(native))
                row['native_context_callbacks'] = initial_context_receipt(native)['callbacks']
                row['native_incoming_advertised_schema'] = observe(
                    lambda: registry.for_path(native.path).child_assignment_schema(launched, 'launch_hpc'))
                row['native_registry_received_report_sources'] = observe(
                    lambda: registry.received_report_sources(native.role, path=native.path))
                row['native_registry_received_report_facts'] = observe(
                    lambda: registry.received_report_facts(native))
                row['launch_prepare_assignment'] = observe(lambda: launch.prepare_assignment(
                    context, 'launch', plan['launch_assignment'], context.scope,
                    'baseline-launch:' + home))
                # Exercise the real child's incoming parent/request validator
                # independently even if the earlier Launch admission is broken.
                # Both results are retained; this is not an accepted workflow.
                row['native_prepare_assignment'] = observe(
                    lambda: registry.for_path(native.path).prepare_assignment(
                        launched, 'launch_hpc', plan['practical_assignment'],
                        launched.scope, 'baseline-native:' + home))
                row['bound_masking_selector'] = (observe(lambda: launch._masking_selector({}))
                    if axis in ('a103', 'a104', 'a107') else
                    {'status': 'not_applicable', 'reason': 'This axis has no masking selector.'})
                row['launch_reservations'] = ledger.records('launch_commission')
                report['contexts'].append(row)
        (RUN / 'launch_registry_probe.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({'registered_bindings': len(all_bindings), 'contexts': [
            {'binding_path': row['binding_path'],
             'registry': row['registry_initial_decision_context'],
             'native_registry': row['native_registry_initial_decision_context'],
             'admission': row['launch_prepare_assignment'],
             'masking': row['bound_masking_selector']} for row in report['contexts']]}, indent=2))


if __name__ == '__main__':
    main()
