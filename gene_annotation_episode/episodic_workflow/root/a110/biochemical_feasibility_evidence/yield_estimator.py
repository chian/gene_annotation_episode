"""Continuation: an accumulation controller (the old ``BiochemicalFeasibilityEvidenceYield.yield_controller`` opened
the accumulation estimator of the declaration configured for the continuation task and raised
``scientific_yield_method_unavailable`` for the other two kinds; README 7b: ``numerical.YieldController`` becomes
``AccumulationYieldController``, cost = the old cutoff). The scientific credit accumulates without a declared limit.

The declarations are the old ``yield_bindings`` (``{task: {kind, cutoff, parameters{uncertainty_alpha},
credit_definition}}``), now ``settings['yield_bindings']``. The task is ``parent_input['continuation_task']``
(``A110:<a110_task name>`` or ``A110:received_scientific_finding_progress``, the old ``continuation_task``), read
from what ``read_from_parent`` produced. The declaration is checked against exactly this credit definition (the
projector's record) and the accumulation kind; the old configuration check of the declaration's shape is kept. The
cost must be above zero or the controller never stops (it is the controller's own check). Nothing else decides
continuation: the old absent-bindings route (``return None``, the old recorded controller) is not carried."""
from gene_annotation_episode.episodic_workflow.episode_support.configuration.yield_declarations import (
    checked_yield_declaration)
from gene_annotation_episode.episodic_workflow.episode_support.findings.biochemical_feasibility_evidence.investigation_progress import (
    FindingProgressPolicy, ScientificFindingProgress)
from yield_control import AccumulationYieldController, ADAPTIVE_CONTROL

_KINDS = ('accumulation', 'bounded_quality', 'completion')


def _declaration_shape(task, declaration):
    """The old ``ScientificConfiguration.__init__`` check of one task's declaration."""
    if (not isinstance(declaration, dict) or set(declaration) != {'kind', 'cutoff', 'parameters', 'credit_definition'}
            or declaration['kind'] not in _KINDS or not isinstance(declaration['parameters'], dict)
            or set(declaration['parameters']) != {'uncertainty_alpha'}
            or not isinstance(declaration['credit_definition'], dict) or not declaration['credit_definition']):
        raise ValueError('scientific_yield_task_binding_invalid:' + str(task))


def yield_controller(initial_credit, settings, parent_input):
    task = parent_input['continuation_task']
    projector = ScientificFindingProgress(FindingProgressPolicy(parent_input['finding_unit']))
    declaration = checked_yield_declaration(settings['yield_bindings'], task, credit_definition=projector.as_record(),
                                            yield_method=projector.yield_method, code_prefix='scientific')
    _declaration_shape(task, declaration)
    return AccumulationYieldController('biochemical_feasibility_evidence', initial_credit, ADAPTIVE_CONTROL,
                                       items=None)
