"""A104 original-allocation handoff return policy, selected by private tasks.

The eight declared HPC/Allocation and descendant Launch task owners opt in.
Custom or rebound task objects retain Workflow.selected's literal fallback.
"""
import sys
from types import ModuleType
from ..child_message_owners import _state, _static
from .live_runtime_functions import bind_functions as _bind_functions

HPC_HANDOFF_RETURN_POLICY = object()
PRIVATE_TASKS = {'gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.task': 'HPCWorkTask', 'gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.hpc_allocation_execution.task': 'HPCWorkTask', 'gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.execution_job_submission.task': 'LaunchTask', 'gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.hpc_allocation_execution.execution_job_submission.task': 'LaunchTask', 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.task': 'HPCWorkTask', 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.hpc_allocation_execution.task': 'HPCWorkTask', 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.execution_job_submission.task': 'LaunchTask', 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.hpc_allocation_execution.execution_job_submission.task': 'LaunchTask'}


def validate_hpc_handoff_return_form(source, role, schema):
    hpc_launch = role == 'launch' and source.path[-1][0] in {'hpc', 'hpc_execution'} or (role == 'launch_hpc' and any((part[0] == 'hpc' for part in source.path)))
    if hpc_launch and (not any((node.get('x-source') == 'execution_handoff_refs' for node in schema.get('properties', {}).values()))):
        raise ContractError('hpc_launch_requires_original_handoff_fact_in_return_form')


def private_handoff_validator(source):
    """Select an explicit private opt-in without reading policy operands."""
    cls = type(source)
    if type(cls) is not type:
        return None
    module_name = type.__getattribute__(cls, '__dict__').get('__module__')
    if type(module_name) is not str or module_name not in PRIVATE_TASKS:
        return None
    module = sys.modules.get(module_name)
    if type(module) is not ModuleType:
        return None
    namespace = vars(module)
    if namespace.get('_hpc_handoff_original_task') is not cls:
        return None
    if namespace.get(PRIVATE_TASKS[module_name]) is not cls:
        return None
    state = _state(source)
    if state is None or 'child_return_form_policy' in state:
        return None
    if _static(cls, 'child_return_form_policy') is not HPC_HANDOFF_RETURN_POLICY:
        return None
    return validate_hpc_handoff_return_form


def _bind_original_runtime(namespace):
    definitions = {'validate_hpc_handoff_return_form': globals()['validate_hpc_handoff_return_form']}
    globals().update(_bind_functions(namespace, definitions,
        runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime',
        qualified_names={'validate_hpc_handoff_return_form': 'validate_hpc_handoff_return_form'},
        defining_module='gene_annotation_episode.episodic_workflow.root.a104.library.hpc_handoff_return_form'))
