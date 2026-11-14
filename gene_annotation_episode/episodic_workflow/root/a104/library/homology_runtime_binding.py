"""Complete original Homology declarations before binding live runtime globals.

This is import assembly only. It does not wrap or call scientific functions.
The original private function objects are replaced by their code bound to the
authentic runtime dictionary before a completed entry import returns.
"""
from importlib import import_module
import sys

_RUNTIME = 'gene_annotation_episode.episodic_workflow.root.a104.runtime'
_ENTRIES = ('gene_annotation_episode.episodic_workflow.root.a104.homology_job_monitoring.action_admission', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_monitoring.action_execution', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_monitoring.decision_context', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_monitoring.decision_contracts', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_monitoring.decision_exchange', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_monitoring.decision_inputs', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_monitoring.episode', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_monitoring.task', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_monitoring.task_action', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_monitoring.task_decision', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_monitoring.task_report_delivery', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_monitoring.task_state', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_monitoring.yield', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.action_admission', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.action_execution', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.decision_context', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.decision_contracts', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.decision_exchange', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.decision_inputs', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.episode', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.task', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.task_action', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.task_decision', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.task_report_delivery', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.task_state', 'gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.yield', 'gene_annotation_episode.episodic_workflow.root.a104.homology_result_acquisition.action_admission', 'gene_annotation_episode.episodic_workflow.root.a104.homology_result_acquisition.action_execution', 'gene_annotation_episode.episodic_workflow.root.a104.homology_result_acquisition.decision_context', 'gene_annotation_episode.episodic_workflow.root.a104.homology_result_acquisition.decision_contracts', 'gene_annotation_episode.episodic_workflow.root.a104.homology_result_acquisition.decision_exchange', 'gene_annotation_episode.episodic_workflow.root.a104.homology_result_acquisition.decision_inputs', 'gene_annotation_episode.episodic_workflow.root.a104.homology_result_acquisition.episode', 'gene_annotation_episode.episodic_workflow.root.a104.homology_result_acquisition.task', 'gene_annotation_episode.episodic_workflow.root.a104.homology_result_acquisition.task_action', 'gene_annotation_episode.episodic_workflow.root.a104.homology_result_acquisition.task_decision', 'gene_annotation_episode.episodic_workflow.root.a104.homology_result_acquisition.task_report_delivery', 'gene_annotation_episode.episodic_workflow.root.a104.homology_result_acquisition.task_state', 'gene_annotation_episode.episodic_workflow.root.a104.homology_result_acquisition.yield')
_READY = {}
_PENDING = {}
_RUNTIME_NAMESPACE = None


def bind_pending_runtime(namespace):
    global _RUNTIME_NAMESPACE
    runtime = sys.modules.get(_RUNTIME)
    if runtime is None or type(namespace) is not dict or namespace is not vars(runtime):
        raise TypeError('authentic_homology_runtime_namespace_required')
    _RUNTIME_NAMESPACE = namespace
    for name, (module, binder) in tuple(_PENDING.items()):
        if sys.modules.get(name) is not module or _READY.get(name) is not module:
            raise RuntimeError('homology_owner_module_identity_changed')
        binder(namespace)
        del _PENDING[name]


def complete_owner(module_name, binder=None):
    if module_name not in _ENTRIES:
        raise ValueError('undeclared_homology_import_owner')
    module = sys.modules[module_name]
    _READY[module_name] = module
    runtime = sys.modules.get(_RUNTIME)
    if runtime is not None and _RUNTIME_NAMESPACE is vars(runtime):
        if binder is not None:
            binder(_RUNTIME_NAMESPACE)
        return
    if binder is not None:
        if module_name in _PENDING:
            raise RuntimeError('duplicate_pending_homology_owner')
        _PENDING[module_name] = (module, binder)
    for name in _ENTRIES:
        entry = sys.modules.get(name)
        if entry is None or _READY.get(name) is entry:
            continue
        spec = vars(entry).get('__spec__')
        if spec is not None and vars(spec).get('_initializing', False):
            return
    if runtime is None:
        runtime = import_module(_RUNTIME)
        if _RUNTIME_NAMESPACE is not vars(runtime):
            raise RuntimeError('homology_runtime_binding_hook_not_completed')
    # An already executing runtime reaches its explicit binding hook before
    # the original Homology aliases. No provider value is read here.
