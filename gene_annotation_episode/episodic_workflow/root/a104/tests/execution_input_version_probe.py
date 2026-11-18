"""Observe actual A104 input validators with empty and ordinary nonempty inputs.

This diagnostic constructs the actual thirty existing execution owners and one
real Store. It never runs a task, native command, model or remote operation.
Returned errors are retained as errors, not counted as passing assertions.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

from gene_annotation_episode.workflow_budget import active_budget
from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.episode_bindings import BindingContext
from gene_annotation_episode.episodic_workflow.root.a104.method_loop.identities import EpisodeRef
from gene_annotation_episode.episodic_workflow.root.a104.state import Store


PARENTS = ('', 'evolutionary_history_evidence', 'hpc_work_planning',
    'hpc_work_planning/hpc_allocation_execution', 'evolutionary_history_evidence/hpc_work_planning',
    'evolutionary_history_evidence/hpc_work_planning/hpc_allocation_execution')
CHILDREN = ('execution_job_submission', 'execution_job_submission/api_job_execution',
    'execution_job_submission/local_job_execution', 'execution_job_submission/hpc_job_execution',
    'execution_result_acquisition')
ROLES = {'evolutionary_history_evidence': 'evolutionary_history_evidence', 'hpc_work_planning': 'hpc',
    'hpc_allocation_execution': 'hpc_execution', 'execution_job_submission': 'launch',
    'api_job_execution': 'launch_api', 'local_job_execution': 'launch_local',
    'hpc_job_execution': 'launch_hpc', 'execution_result_acquisition': 'results'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    owner = active_budget()
    output = args.directory.resolve()
    assert output.is_relative_to(Path(owner['run_directory']).resolve())
    output.mkdir(parents=True, exist_ok=True)
    report = {'scope': 'Actual owners/Store/validator; supplied context without an executed action.',
        'workflow_owner': owner,
        'diagnostic_complete': False, 'cases': [], 'native_commands': 0, 'provider_requests': 0}

    def save():
        target = output / 'probe.json'
        temporary = output / 'probe.json.new'
        temporary.write_text(json.dumps(report, indent=2) + '\n')
        temporary.replace(target)

    def observe(callback):
        try:
            return {'status': 'returned', 'value': plain(callback())}
        except Exception as error:
            return {'status': 'raised', 'type': type(error).__module__ + '.' + type(error).__qualname__,
                    'message': str(error)}

    save()
    with Store(output / 'store') as store:
        problem = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        scope = {'subject_refs': problem['subject_refs']}
        reference, = scope['subject_refs']
        record = store.get(reference)
        artifact = record.get('sequence_ref', record.get('artifact_ref'))
        assert artifact is not None
        versions = [{'reference': reference, 'version': None,
                     'content_sha256': hashlib.sha256(store.get_artifact(artifact)).hexdigest()}]
        report['ordinary_input_versions'] = versions
        services = SimpleNamespace(annotation_task_required=lambda: False)
        for parent in PARENTS:
            for child in CHILDREN:
                home = '/'.join(part for part in (parent, child) if part)
                module = importlib.import_module('gene_annotation_episode.episodic_workflow.root.a104.'
                    + home.replace('/', '.') + '.episode')
                binding = module.ExecutionEpisode(services, store=store, run_id='a104-input-version-probe',
                    directory=output / 'workflow', resources=resources(), initial_information={},
                    tool_registry=None, handoff_unit=1., acquired_record_unit=1.,
                    log_window_bytes=1024, log_roles=('stdout', 'stderr'))
                path = tuple((ROLES[part], 'original-' + part) for part in home.split('/'))
                if not home.startswith('evolutionary_history_evidence/'):
                    path = (('annotation', 'root'),) + path
                role = path[-1][0]
                assert binding.binding_path == home and binding.roles == (role,)
                context = BindingContext(binding.run_id, EpisodeRef(binding.run_id, path).episode_id,
                    role, path, scope, {}, {})
                row = {'home': home, 'role': role,
                    'empty': observe(lambda: binding._versions([], scope, context=context)),
                    'ordinary_nonempty': observe(lambda: binding._versions(versions, scope, context=context)),
                    'reference_callbacks': {name: callable(getattr(binding, name, None)) for name in (
                        '_atac_reference_access', '_chromatin_reference_access', '_protein_reference_access')}}
                report['cases'].append(row)
                save()
    assert len(report['cases']) == 30
    report['diagnostic_complete'] = True
    save()
    print(json.dumps({'owners': 30, 'diagnostic_complete': True,
        'empty_returned': sum(row['empty']['status'] == 'returned' for row in report['cases']),
        'nonempty_returned': sum(row['ordinary_nonempty']['status'] == 'returned' for row in report['cases']),
        'test_pass_count': None}))


if __name__ == '__main__':
    main()
