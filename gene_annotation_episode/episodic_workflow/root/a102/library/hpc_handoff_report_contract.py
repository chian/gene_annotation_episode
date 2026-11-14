"""A102's original HPC launch handoff-return policy and nominal selection.

The eight configured private consumers are declared below. Custom classes and
changed static selections retain Workflow.selected's literal original fallback.
No instance path, binding, specialist or provider is read by the selector.
"""
from __future__ import annotations
import sys
from types import ModuleType

def validate_return_contract(source, role, schema):
    hpc_launch = role == 'launch' and source.path[-1][0] in {'hpc', 'hpc_execution'} or (role == 'launch_hpc' and _original_any()((part[0] == 'hpc' for part in source.path)))
    if hpc_launch and (not _original_any()((node.get('x-source') == 'execution_handoff_refs' for node in schema.get('properties', {}).values()))):
        raise _original_error()('hpc_launch_requires_original_handoff_fact_in_return_form')
    return hpc_launch

CONSUMERS = {'gene_annotation_episode.episodic_workflow.root.a102.hpc_work_planning.task': 'HPCWorkTask', 'gene_annotation_episode.episodic_workflow.root.a102.hpc_work_planning.execution_job_submission.task': 'LaunchTask', 'gene_annotation_episode.episodic_workflow.root.a102.hpc_work_planning.hpc_allocation_execution.task': 'HPCWorkTask', 'gene_annotation_episode.episodic_workflow.root.a102.hpc_work_planning.hpc_allocation_execution.execution_job_submission.task': 'LaunchTask', 'gene_annotation_episode.episodic_workflow.root.a102.scientific_process.hpc_work_planning.task': 'HPCWorkTask', 'gene_annotation_episode.episodic_workflow.root.a102.scientific_process.hpc_work_planning.execution_job_submission.task': 'LaunchTask', 'gene_annotation_episode.episodic_workflow.root.a102.scientific_process.hpc_work_planning.hpc_allocation_execution.task': 'HPCWorkTask', 'gene_annotation_episode.episodic_workflow.root.a102.scientific_process.hpc_work_planning.hpc_allocation_execution.execution_job_submission.task': 'LaunchTask'}


def selected_validator(source):
    cls = type(source)
    if type(cls) is not type:
        return None
    namespace = type.__getattribute__(cls, '__dict__')
    module_name = namespace.get('__module__')
    if type(module_name) is not str:
        return None
    class_name = CONSUMERS.get(module_name)
    if class_name is None or type(sys.modules) is not dict:
        return None
    module = sys.modules.get(module_name)
    if type(module) is not ModuleType:
        return None
    if ModuleType.__getattribute__(module, '__dict__').get(class_name) is not cls:
        return None
    declared = namespace.get('hpc_handoff_report_validator')
    if type(declared) is not staticmethod or declared.__func__ is not validate_return_contract:
        return None
    return validate_return_contract


# Define both functions before importing the original native Name getters.
# Direct cold entry can meet a task module importing the declared validator.
# Each captured getter keeps the actual runtime globals and cached builtins;
# calls occur only at the original Name-load positions in the policy above.
from ..runtime import _hpc_guard_any as _original_any, _hpc_guard_error as _original_error
