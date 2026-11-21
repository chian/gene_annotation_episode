"""Continuation: an accumulation controller (the old ``BiochemicalFeasibilityEvidenceYield.yield_controller`` opened
the accumulation estimator of the declaration configured for the continuation task and raised
``scientific_yield_method_unavailable`` for the other two kinds; README 7b: ``numerical.YieldController`` becomes
``AccumulationYieldController``, nano-graphrag's ``EstimatorController`` port, here with ``ADAPTIVE_CONTROL`` and
``items=None``). The scientific credit accumulates without a declared limit. The controller takes no cost: after W = 8
units attempted and m = 4 observed it fits nano-graphrag's yield model; a unit is flat when the upper bound of the
expected next marginal (hypervolume) credit is at or below gamma (``ADAPTIVE_CONTROL``: after every unit gamma =
max(one-result resolution, 0.1 x median of the recent productive credits)); it stops after 4 flat units in a row. With
``items=None`` there is no input list, so no item count stops it.

The declarations are the old ``yield_bindings`` (``{task: {kind, cutoff, parameters{uncertainty_alpha},
credit_definition}}``), now ``settings['yield_bindings']``. The task is ``parent_input['continuation_task']``
(``A110:<a110_task name>`` or ``A110:received_scientific_finding_progress``, the old ``continuation_task``), read
from what ``read_from_parent`` produced. The declaration is checked against exactly this credit definition (the
projector's record) and the accumulation kind; the old configuration check of the declaration's shape is kept. The
declaration's ``cutoff`` (the old cost) is checked for shape only and is not passed to the controller. Nothing else
decides continuation: the old absent-bindings route (``return None``, the old recorded controller) is not carried."""
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
