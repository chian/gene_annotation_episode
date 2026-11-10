"""Autonomous A107 or A110 investigation from caller material and a question.

Launch through one_workflow.sh with the caller's explicit execution authorization.
This runner supplies no evaluator expectations, forced scientific decisions,
answer-bearing follow-ups or stopping budget. The original controller decides
continuation; the existing HPC owner decides execution and recovery.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
import faulthandler
import json
import os
from pathlib import Path
import signal
import sys
import uuid

def path_from(base, value):
    path = Path(value).expanduser()
    return (base/path).resolve() if not path.is_absolute() else path.resolve()


@contextmanager
def controller_diagnostics(directory):
    """Manual, read-only stack observation inside the existing workflow."""
    with (directory/'controller-stacks.log').open('a') as output:
        faulthandler.register(signal.SIGUSR1, file=output, all_threads=True)
        try:
            yield
        finally:
            faulthandler.unregister(signal.SIGUSR1)


async def run(args):
    entry_point = Path(__file__).resolve()
    repository = entry_point.parents[1]
    implementation_root = args.implementation_root.resolve() if args.implementation_root else None
    if implementation_root is not None:
        if (not implementation_root.is_relative_to(repository/'runs')
                or not (implementation_root/'SOURCE_MANIFEST.sha256').is_file()
                or not (implementation_root/'gene_annotation_episode').is_dir()
                or not (implementation_root/'method_loop').is_dir()):
            raise ValueError('implementation_snapshot_and_manifest_required_under_runs')
        sys.path.insert(0, str(implementation_root))
    from gene_annotation_episode.a107_investigation import A107ServiceFactory, create_a107_workflow
    from gene_annotation_episode.a110_investigation import A110ServiceFactory, create_a110_workflow
    from gene_annotation_episode.acquisition import PublicClients
    from gene_annotation_episode.component_axis_reports import (
        cell_views, repository as component_repository, received_reports, mark_native_execution)
    from gene_annotation_episode.component_axis_native_hpc import received_components, execution_findings
    from gene_annotation_episode.component_axis_workflow import TASKS, INSTRUCTIONS
    from gene_annotation_episode.decision_context import PROTOCOL
    from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
    from gene_annotation_episode.hpc_monitoring import MonitorCheckpoint
    from gene_annotation_episode.hpc_scheduler import register_resume
    from gene_annotation_episode.materials import artifact_file, source_for_artifact
    from gene_annotation_episode.a107_tools import A107ToolRegistry
    from gene_annotation_episode.a110_tools import A110ToolRegistry
    from gene_annotation_episode.providers import load_config
    from gene_annotation_episode.public_configuration import configured_tools
    from gene_annotation_episode.runtime import controller_from_settings, _plain
    from gene_annotation_episode.serial_model_resources import SerialModelConnection
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.workflow_budget import active_budget
    owner = active_budget()
    directory = args.run_directory.resolve()
    if not directory.is_relative_to(repository/'runs'):
        raise ValueError('partner_chemical_output_requires_repository_runs_directory')
    # Resumption uses another launcher invocation in this same window; output
    # custody stays with the original scientific run and its frozen records.
    if not Path(owner['run_directory']).resolve().is_relative_to(repository/'runs'):
        raise ValueError('partner_chemical_original_workflow_resource_owner_required')
    if not args.resume and directory != Path(owner['run_directory']).resolve():
        raise ValueError('fresh_run_must_use_its_actual_launcher_output_directory')
    configuration_path = directory/'configuration.json'
    if args.resume:
        if args.configuration is not None:
            raise ValueError('resume_uses_original_saved_configuration')
        configuration = json.loads(configuration_path.read_text())
    else:
        if args.configuration is None or configuration_path.exists():
            raise ValueError('fresh_explicit_configuration_required')
        source = args.configuration.resolve()
        configuration = json.loads(source.read_text())
        allowed = {'axis', 'question', 'input_path', 'molecule', 'source_directory',
            'evidence_paths', 'target_genomic_paths', 'execution', 'a107_detection_bindings',
            'a110_flux_balance_bindings', 'model_config'}
        if set(configuration)-allowed or not {'axis', 'question', 'input_path', 'molecule', 'source_directory'} <= set(configuration):
            raise ValueError('partner_chemical_configuration_fields_invalid')
        for key in ('input_path', 'source_directory', 'model_config'):
            if configuration.get(key) is not None:
                configuration[key] = str(path_from(source.parent, configuration[key]))
        configuration['evidence_paths'] = [str(path_from(source.parent, path))
            for path in configuration.get('evidence_paths', [])]
        configuration['target_genomic_paths'] = [str(path_from(source.parent, path))
            for path in configuration.get('target_genomic_paths', [])]
        if configuration.get('execution') is not None:
            # A frozen import root must not silently relocate shared usage
            # history. Save the explicit existing interface for new runs;
            # resume keeps its original configuration and receipt history.
            configuration['execution'].setdefault('shared_execution_memory', {'path':
                str(path_from(repository, os.environ.get('GENE_EPISODE_EXECUTION_MEMORY',
                    str(repository/'runs'/'shared-execution'/'memory.sqlite3'))))})
        directory.mkdir(parents=True, exist_ok=True)
        configuration_path.write_text(json.dumps(configuration, indent=2)+'\n')
    axis = configuration['axis']
    if axis not in TASKS or not isinstance(configuration['question'], str) or not configuration['question'].strip():
        raise ValueError('partner_chemical_axis_and_question_required')
    for leaf in ('tmp', 'cache', 'native', 'provider'):
        (directory/leaf).mkdir(parents=True, exist_ok=True)
    os.environ.update(PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(directory/'tmp'),
        XDG_CACHE_HOME=str(directory/'cache'))
    os.chdir(directory)
    models = load_config(configuration.get('model_config'))
    retrieval = {'version': 'scientific_tool_retrieval_v1', 'mode': 'semantic_fast_v1',
        'model': {key: models['FAST'][key] for key in ('model', 'reasoning_effort')}}
    # Use the repository's original controller settings, not new experiment
    # limits. load_config contains only the model table.
    import tomllib
    from gene_annotation_episode.providers import default_config_path
    settings = tomllib.loads(default_config_path().read_text())
    execution = (ExecutionServiceFactory(**configuration['execution'])
        if configuration.get('execution') is not None else None)
    factory_class, create = (A107ServiceFactory, create_a107_workflow) if axis == 'A107' else (
        A110ServiceFactory, create_a110_workflow)
    pending = None
    with controller_diagnostics(directory), Store(directory/'state') as store:
        prepared_path = directory/'prepared.json'
        if args.resume:
            prepared = json.loads(prepared_path.read_text())
            if prepared['owner_window_id'] != owner['window_id']:
                raise ValueError('resume_requires_this_workflows_original_codex_window')
            if prepared.get('implementation_root') != (str(implementation_root) if implementation_root else None):
                raise ValueError('resume_requires_original_implementation_snapshot')
        else:
            store.create_problem(configuration['input_path'], molecule=configuration['molecule'])
            known = [row['id'] for row in store.targets()]
            for row in store.targets():
                known.extend([row['source_ref'], store.get(row['source_ref'])['artifact_ref']])
            target_ids = [row['id'] for row in store.targets()]
            genomic_paths = set(configuration.get('target_genomic_paths', []))
            if genomic_paths and len(target_ids) != 1:
                raise ValueError('target_genomic_paths_requires_one_target; use_explicit_per_target_registry_associations_for_multiple_targets')
            genomic_sources = []
            for file_path in dict.fromkeys([*configuration['evidence_paths'], *genomic_paths]):
                artifact = artifact_file(store, file_path)
                source = source_for_artifact(store, artifact, uri=Path(file_path).as_uri(), request={
                    'provided_path': file_path,
                    'caller_associated_target_genomic_subjects': target_ids if file_path in genomic_paths else []})
                known.extend([source['id'], artifact])
                if source['request_ref'] is not None:
                    known.append(source['request_ref'])
                if file_path in genomic_paths:
                    genomic_sources.append(source['id'])
            prepared = {'run_id': axis.lower()+'-'+uuid.uuid4().hex, 'scope': store.validate_scope(None),
                'owner_window_id': owner['window_id'],
                'implementation_root': str(implementation_root) if implementation_root else None,
                'target_genomic_sources': {target: list(genomic_sources) for target in target_ids},
                'public_client': configured_tools({'public': {
                    'provider_access_dir': str(directory/'provider-access')}})['public'],
                'known_record_refs': list(dict.fromkeys(known)), 'evaluator_expectations_loaded': False,
                'scripted_model_decisions': False}
            prepared_path.write_text(json.dumps(prepared, indent=2)+'\n')
        if not args.resume:
            # The factory already uses these exact settings. Retain and expose
            # them so the ordinary own-action yield table can fit its categories
            # instead of treating this configured controller as opaque.
            prepared['controller_binding'] = {
                'kind': 'configured_existing_yield',
                'definition': dict(settings['controller'])}
            prepared_path.write_text(json.dumps(prepared, indent=2)+'\n')
        controller_binding = prepared.get('controller_binding')
        controller_settings = (settings if controller_binding is None else {
            'controller': controller_binding['definition']})
        public = prepared['public_client']
        clients = PublicClients(ncbi_email=public['ncbi_email'], access_dir=Path(public['provider_access_dir']))
        # This runner commissions one evidence axis. Advertise that axis's
        # executable tools; the combined parent registry also contains tools
        # whose authenticated handlers require the other scientific axis.
        registry, registry_options = (A107ToolRegistry, {
            'a107_work_directory': directory/'native',
            'target_genomic_sources': prepared.get('target_genomic_sources', {}),
            'a107_detection_bindings': configuration.get('a107_detection_bindings', ()),
        }) if axis == 'A107' else (A110ToolRegistry, {
            'a110_flux_balance_bindings': configuration.get('a110_flux_balance_bindings', ()),
        })
        tools = registry(store, clients=clients, **registry_options,
            job_limits={'memory_bytes': min(512*1024**2, owner['environment_bounds']['memory_bytes']),
                'scratch_bytes': 1024**3})
        factory = factory_class(configuration['source_directory'], retrieval,
            execution_service_factory=execution)
        # The caller requests an axis subtree. Its scientific owner composes
        # literature providers and recursive decisions; root-level dispatch
        # must not skip that owner while claiming to exercise the subtree.
        child_roles = ('scientific_process',)
        if execution is not None and execution.hpc_commissions is not None:
            child_roles += ('hpc',)
        async with SerialModelConnection(models, directory/'provider'/uuid.uuid4().hex, directory) as provider:
            workflow = create(store, tools, provider, directory/'workflow', prepared['run_id'],
                controller_from_settings(controller_settings),
                controller_binding=controller_binding,
                initial_known_record_refs=prepared['known_record_refs'],
                episode_service_factory=factory, episode_service_binding=factory.as_record(),
                episode_service_inputs='actual_tool_registry_v1', decision_protocol=PROTOCOL,
                annotation_child_roles=child_roles)
            if args.resume:
                # Reconstruct the original commission, including older runs
                # whose prepared record predates root_goal. New presentation
                # code must never silently rewrite a live/historical objective.
                original = store.db.execute("SELECT json_extract(request,'$.goal.objective') "
                    "FROM runtime_episodes WHERE run_id=? AND json(path)=json(?)",
                    (prepared['run_id'], json.dumps([['annotation', 'root']]))).fetchone()
                retained = None if original is None else original[0]
                goal = prepared.get('root_goal', retained)
                if (not isinstance(goal, str) or not goal.strip()
                        or retained is not None and goal != retained):
                    raise ValueError('resume_requires_original_retained_root_goal')
            else:
                goal = (configuration['question']+'\n\n'+INSTRUCTIONS[axis]
                    +'\n\nInvestigate '+axis+' through independent scientific descendants as useful. '
                    'Choose sources, tasks and operations from actual available capabilities and '
                    'received outcomes. For work requiring primitive tools, use process.tools '
                    'to obtain their actual contracts and resource labels, and include the needed '
                    'operations in the fixed child_tool_info. An empty primitive toolset leaves '
                    'common reasoning, communication and permitted child investigations; it does '
                    'not grant the axis calculations or ordinary source readers. Tasks: '
                    +json.dumps(TASKS[axis])+'. Return the applicable '
                    'exact typed scientific components and interpret actual received findings at '
                    'the parent, preserving original sources, dependence and scope. Use the declared '
                    'saved-fact return types available through episode.return_contract. The receiver '
                    'automatically projects its scientific scoring sheets from admitted results; '
                    'no synthesis or finalize action is required to make those values count. '
                    'Choose any additional interpretation fields separately. Do not substitute controller progress for '
                    'scientific values. No biological answer is supplied by this commission.')
                prepared['root_goal'] = goal
                prepared['root_goal_presentation'] = 'component_axis_scientific_task_v2'
                prepared_path.write_text(json.dumps(prepared, indent=2)+'\n')
            root = workflow.build('annotation', 'root', goal, prepared['scope'])
            try:
                record = await root.run_async(workflow.context)
                result = await root.build_result(record)
                context = workflow.binding_context(root.source)
                from gene_annotation_episode.episode_source_failure import child_completion_status
                completion = child_completion_status(store, prepared['run_id'], context.episode_id,
                    {'ended_by': record.ended_by, 'end_reason': getattr(record, 'end_reason', None)},
                    delivery='root_return')
                (directory/'parent-completion.json').write_text(json.dumps(
                    completion, indent=2)+'\n')
                findings = received_reports(store, context=context, services=workflow.services)
                from gene_annotation_episode.component_axis_reports import current_scoring_sheets
                scoring = current_scoring_sheets(store, context=context, services=workflow.services)
                # Custom typed returns can deliver a saved-cell view without
                # selecting the canonical axis report. Read only the actual
                # receiver's copied, validated rows; a sheet reference alone
                # does not grant its undelivered cells.
                experimental = {schema['x-source']: component_repository(
                    workflow.services, axis, field).received_cells(context)
                    for field, schema in cell_views(axis).items()}
                if axis == 'A110':
                    from gene_annotation_episode.literature_reaction_native_storage import NAMESPACE
                    experimental[NAMESPACE] = workflow.services.literature_reaction_repository(
                        ).native_observations_projection().received_rows(context)
                # Custom child field names can deliver authenticated native
                # publications without selecting the canonical axis report.
                # Export only this root's actual receipts, keeping that path
                # distinct from canonical reports and from proof of model use.
                native = received_components(store, context.received_record_refs,
                    context.scope, axis=axis, compact=False)
                native_execution = mark_native_execution(execution_findings(
                    store, context.received_record_refs, context.scope, axis=axis), native)
                (directory/'parent-result.json').write_text(json.dumps(_plain(result), indent=2)+'\n')
                (directory/'received-components.json').write_text(json.dumps(findings, indent=2)+'\n')
                (directory/'current-scoring-sheets.json').write_text(json.dumps(scoring, indent=2)+'\n')
                (directory/'received-experimental-components.json').write_text(json.dumps({
                    'version': 'actual_parent_experimental_components_v1', 'axis': axis,
                    'run_id': prepared['run_id'], 'receiving_episode_id': context.episode_id,
                    'receiving_scope': _plain(context.scope),
                    'received_saved_facts_by_namespace': experimental,
                    'parent_use_status': 'inspect_actual_trace; receipt_alone_is_not_proof_of_use',
                }, indent=2)+'\n')
                (directory/'received-native-components.json').write_text(json.dumps({
                    'version': 'actual_parent_native_components_v1', 'axis': axis,
                    'run_id': prepared['run_id'], 'receiving_episode_id': context.episode_id,
                    'receiving_scope': _plain(context.scope), 'native_component_results': native,
                    'native_execution_findings': native_execution,
                    'parent_use_status': 'inspect_actual_trace; receipt_alone_is_not_proof_of_use',
                }, indent=2)+'\n')
                print(json.dumps({'event': ('partner_chemical_parent_failed'
                    if completion['failure'] is not None else 'partner_chemical_parent_returned'),
                    'axis': axis, 'completion': completion,
                    'run_id': prepared['run_id'],
                    'received_axes': sorted(set(findings) | {row['axis'] for row in native}
                        | ({axis} if any(experimental.values()) else set())),
                    'received_native_publications': len(native),
                    'parent_use_status': 'inspect_actual_trace; receipt_alone_is_not_proof_of_use',
                    'evaluator_expectations_loaded': False, 'scripted_model_decisions': False}), flush=True)
                if completion['failure'] is not None:
                    raise RuntimeError('partner_chemical_root_source_failed; inspect parent-completion.json')
            except MonitorCheckpoint as waiting:
                pending = waiting.schedule
    if pending is not None:
        command = [sys.executable, '-B', str(entry_point),
            '--run-directory', str(directory), '--resume']
        if implementation_root is not None:
            command.extend(['--implementation-root', str(implementation_root)])
        spec = register_resume(directory, repository, command, pending)
        print(json.dumps({key: spec[key] for key in ('event', 'resume_at', 'timer', 'controller_run_directory')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-directory', type=Path, required=True)
    parser.add_argument('--configuration', type=Path)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--implementation-root', type=Path)
    asyncio.run(run(parser.parse_args()))
