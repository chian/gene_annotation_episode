"""Same-axis HPC launch handoff report policy, selected by private parents."""
import sys as _sys
from types import ModuleType as _ModuleType

def validate_hpc_launch_report_contract(source, role, schema):
    hpc_launch = role == 'launch' and source.path[-1][0] in {'hpc', 'hpc_execution'} or (role == 'launch_hpc' and _get_any()((part[0] == 'hpc' for part in source.path)))
    if hpc_launch and (not _get_any()((node.get('x-source') == 'execution_handoff_refs' for node in schema.get('properties', {}).values()))):
        raise _get_error()('hpc_launch_requires_original_handoff_fact_in_return_form')
    return hpc_launch

_ORIGINAL_VALIDATOR = validate_hpc_launch_report_contract
_CONSUMERS = {'gene_annotation_episode.episodic_workflow.root.a107.hpc_work_planning.task': 'HPCWorkTask', 'gene_annotation_episode.episodic_workflow.root.a107.hpc_work_planning.execution_job_submission.task': 'LaunchTask', 'gene_annotation_episode.episodic_workflow.root.a107.hpc_work_planning.hpc_allocation_execution.task': 'HPCWorkTask', 'gene_annotation_episode.episodic_workflow.root.a107.hpc_work_planning.hpc_allocation_execution.execution_job_submission.task': 'LaunchTask', 'gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.hpc_work_planning.task': 'HPCWorkTask', 'gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.hpc_work_planning.execution_job_submission.task': 'LaunchTask', 'gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.hpc_work_planning.hpc_allocation_execution.task': 'HPCWorkTask', 'gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.hpc_work_planning.hpc_allocation_execution.execution_job_submission.task': 'LaunchTask'}

def selected_hpc_launch_report_validator(source):
    """Inspect cached nominal identity only; original late operands stay unread."""
    source_type = type(source)
    if type(source_type) is not type:
        return None
    namespace = source_type.__dict__
    module_name = namespace.get('__module__')
    if type(module_name) is not str:
        return None
    class_name = _CONSUMERS.get(module_name)
    if class_name is None or type(_sys.modules) is not dict:
        return None
    module = _sys.modules.get(module_name)
    if type(module) is not _ModuleType or module.__dict__.get(class_name) is not source_type:
        return None
    declared = namespace.get('_validate_hpc_launch_report_contract')
    if type(declared) is not staticmethod or declared.__func__ is not _ORIGINAL_VALIDATOR:
        return None
    return _ORIGINAL_VALIDATOR

# Pure native Name getters exist before ordinary runtime imports.
from gene_annotation_episode.episodic_workflow.root.a107.runtime import (
    _hpc_report_any as _get_any,
    _hpc_report_contract_error as _get_error,
)
