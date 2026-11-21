"""Continuation: the accumulation controller (``AccumulationYieldController``) of the differential credit. The credit
(``credit.py``) is a sum that grows with every admitted candidate annotation and every differential and has no fixed
maximum, so its controller is the one for credit without a declared limit. The controller is opened through the library's
``checked_yield_declaration`` (the declaration for the task key ``A101:<context.a101_task.name>``, or
``A101:a101_native_sequence_correspondence`` when the commission names none, as ``read_from_parent`` reads it, must
name exactly this credit definition, ``A101DifferentialCredit().as_record()``, and the kind ``accumulation``) and
``open_yield_controller``, which takes the declaration's cutoff as the cost of one more unit and its parameters.

The cutoff is in the credit's own units: an admitted candidate earns up to 1 and a differential earns the size of a gap
between the moves of two scores. The run's declaration chooses 0.1: the episode continues while it expects a unit
to earn more than 0.1, the move the owner's example calls small (``S_B only moves +0.1``): a unit expected to differentiate
candidates by no more than that is not worth another decision. It reads what ``read_from_parent`` produced (the task
key), never the assignment; the declarations are this episode's settings (``settings['yield_bindings']``)."""
from gene_annotation_episode.episodic_workflow.episode_support.configuration.yield_declarations import (
    checked_yield_declaration, open_yield_controller)

from .credit import A101DifferentialCredit


def yield_controller(initial_credit, settings, parent_input):
    projector = A101DifferentialCredit()
    declaration = checked_yield_declaration(settings['yield_bindings'], parent_input['yield_task'],
                                            credit_definition=projector.as_record(),
                                            yield_method=projector.yield_method, code_prefix='scientific')
    return open_yield_controller(declaration['kind'], epoch='sequence_homology_evidence', initial_credit=initial_credit,
                                 cutoff=declaration['cutoff'], parameters=declaration['parameters'])
