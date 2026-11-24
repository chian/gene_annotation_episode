"""Continuation. The old ``yield_estimator.py``: the continuation task is ``A103:<context.a103_task.name>`` or
``A103:<projector kind>``; the private yield declaration of the episode's configuration for that task fixes the kind,
the cutoff, the parameters and the exact credit definition, which must equal the projector record, and the kind must be
the projector's own ``yield_method``. ``A103ContextCredit`` declares ``yield_method = 'bounded_quality'`` with
``native_score_maximum`` (README 7b: ``BoundedYieldController`` -> ``BoundedQualityYieldController``, its maximum the
projector's declared maximum). The declarations are this episode's settings (``settings['yield_bindings']``, keyed by
task); the task name comes from the parent input (``read_from_parent`` read ``context.a103_task.name``). The old code
returned no controller when no declaration was configured; a controller is required now, so a missing declaration
raises (``scientific_yield_bindings_not_configured``). The check and the opening are the library's
``checked_yield_declaration`` and ``open_yield_controller``, called with this episode's own pieces."""
from gene_annotation_episode.episodic_workflow.episode_support.configuration.yield_declarations import (
    checked_yield_declaration, open_yield_controller)
from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.credit import (
    A103ContextCredit)

AXIS = 'A103'


def yield_controller(initial_credit, settings, parent_input):
    projector = A103ContextCredit()
    record = projector.as_record()
    task = AXIS + ':' + (parent_input['a103_task_name'] or record['kind'])
    declaration = checked_yield_declaration(settings.get('yield_bindings'), task, credit_definition=record,
                                            yield_method=projector.yield_method, code_prefix='scientific')
    return open_yield_controller(declaration['kind'], epoch='gene_context_evidence', initial_credit=initial_credit,
                                 cutoff=declaration['cutoff'], parameters=declaration['parameters'],
                                 maximum_credit=projector.native_score_maximum)
