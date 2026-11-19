"""Continuation: the old estimator chose the controller of the head's credit task from the explicit yield
declaration for the task key ``A101:<context.a101_task.name>`` (or ``A101:<projector kind>``): the declaration
must name exactly this credit definition (``A101SequenceCredit().as_record()``) and this estimator kind
(``bounded_quality``), and the bounded-quality controller takes the declaration's cutoff as its cost, the
projector's ``native_score_maximum`` (1.0) as its maximum and the declared uncertainty parameters (README 7b,
``numerical.BoundedYieldController`` row). It reads what ``read_from_parent`` produced (the task key), never the
assignment; the declarations are this episode's settings (``settings['yield_bindings']``). The old
construction-time check of every configured declaration (``validate_yield_bindings``) is not carried; the check of
the declaration this commission uses is."""
from yield_control import BoundedQualityYieldController

from gene_annotation_episode.episodic_workflow.episode_support.configuration.yield_declarations import (
    checked_yield_declaration)

from .credit import A101SequenceCredit


def yield_controller(initial_credit, settings, parent_input):
    projector = A101SequenceCredit()
    declaration = checked_yield_declaration(settings['yield_bindings'], parent_input['yield_task'],
                                            credit_definition=projector.as_record(),
                                            yield_method=projector.yield_method, code_prefix='scientific')
    return BoundedQualityYieldController('sequence_homology_evidence', initial_credit, declaration['cutoff'],
                                         projector.native_score_maximum, declaration['parameters'])
