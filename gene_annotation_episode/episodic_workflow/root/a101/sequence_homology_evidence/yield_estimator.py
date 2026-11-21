"""Continuation: the forecast controller (``ForecastYieldController``) over the differential credit. The credit
(``credit.py``) is a sum that grows with every admitted candidate annotation and every differential and has no fixed
maximum, but every action the head offers has a ceiling (``credit.ceiling``: the most the credit can rise if that action is
the next unit, or ``UNBOUNDED`` for the one action whose gain has none). The forecast of an offered action is therefore
a formula, not the model's estimate: the share of its ceiling such actions realized before (this episode's units and the
estimate ledger's history of the kind ``a101/sequence_homology_evidence:<action type>``) times the ceiling, or, for
``UNBOUNDED``, the typical gain of that kind. The episode stops when no offered action's forecast exceeds its expected
seconds times the exchange rate (``yield_control``, section ``ForecastYieldController``; the design is
``docs/plan/designs/forecast_yield_controller.md``).

The controller is opened through the library's ``checked_yield_declaration`` (the declaration for the task key
``A101:<context.a101_task.name>``, or ``A101:a101_native_sequence_correspondence`` when the commission names none, as
``read_from_parent`` reads it, must name exactly this credit definition, ``A101DifferentialCredit().as_record()``, and the
kind ``forecast``) and ``open_yield_controller``, which takes the declaration's parameters: ``exchange_rate``,
``forget_old_rows`` and ``job_kinds`` (the values and their reasons are in the design note). It reads
what ``read_from_parent`` produced (the task key), never the assignment; the declarations are this episode's settings
(``settings['yield_bindings']``).

The definition each action's learned shares are on (``forecast_definitions``: per action type, the digest of the credit
definition record and that action's own ceiling version, ``credit.CEILING_VERSIONS``) is handed to the controller, and
the estimate ledger's shares of an action are only the rows recorded under that action's definition; its measured
seconds are every row of the action, whatever the definition. Changing one action's ceiling therefore discards only that
action's shares."""
from gene_annotation_episode.episodic_workflow.episode_support.configuration.yield_declarations import (
    checked_yield_declaration, forecast_definitions, open_yield_controller)

from .credit import CEILING_VERSIONS, A101DifferentialCredit


def yield_controller(initial_credit, settings, parent_input):
    projector = A101DifferentialCredit()
    declaration = checked_yield_declaration(settings['yield_bindings'], parent_input['yield_task'],
                                            credit_definition=projector.as_record(),
                                            yield_method=projector.yield_method, code_prefix='scientific')
    return open_yield_controller(declaration['kind'], epoch='sequence_homology_evidence', initial_credit=initial_credit,
                                 parameters=declaration['parameters'],
                                 definition=forecast_definitions(projector.as_record(), CEILING_VERSIONS))
