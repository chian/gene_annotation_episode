"""Continuation: the forecast controller (``ForecastYieldController``) over the differential credit. The credit (``credit.py``)
is a sum that grows with every admitted candidate annotation and every differential and has no fixed maximum, but every
action the head offers has a ceiling (``credit.ceiling``: the most the credit can rise if that action is the next unit). The
forecast of an offered action is therefore a formula, not the model's estimate: the share of its ceiling such actions realized
before (this episode's units and the estimate ledger's history of the kind ``structural_homology_evidence:<action type>``)
times the ceiling. The episode stops when no offered action's forecast exceeds its expected seconds times the exchange rate
and no parked job is owed its continuation (``yield_control``, section ``ForecastYieldController``; the design is
``docs/plan/designs/forecast_yield_controller.md``).

The controller is opened through the library's ``checked_yield_declaration`` (the declaration for the task key
``A102:a102_structural_correspondence`` as ``read_from_parent`` reads it must name exactly this credit definition,
``A102DifferentialCredit().as_record()``, and the kind ``forecast``) and ``open_yield_controller``, which takes the
declaration's parameters: ``exchange_rate``, ``forget_old_rows`` and ``job_kinds``. The run's continuation declares
``exchange_rate`` 0.006, ``forget_old_rows`` true and ``job_kinds`` ``{}``. PROVISIONAL: 0.006 is A101's value (the owner on a
first figure: "you have to start somewhere that's fine"); it is A101's rate for A101's credit scale and is to be re-derived from
A102's own resolved forecast rows after the first real runs (``docs/plan/designs/a102_head.md``). It reads what
``read_from_parent`` produced (the task key), never the assignment; the declarations are this episode's settings
(``settings['yield_bindings']``).

The definition each action's learned shares are on (``forecast_definitions``: per action type, the digest of the credit
definition record and that action's own ceiling version, ``credit.CEILING_VERSIONS``) is handed to the controller."""
from gene_annotation_episode.episodic_workflow.episode_support.configuration.yield_declarations import (
    checked_yield_declaration, forecast_definitions, open_yield_controller)

from .credit import CEILING_VERSIONS, A102DifferentialCredit


def yield_controller(initial_credit, settings, parent_input):
    projector = A102DifferentialCredit()
    declaration = checked_yield_declaration(settings['yield_bindings'], parent_input['yield_task'],
                                            credit_definition=projector.as_record(),
                                            yield_method=projector.yield_method, code_prefix='scientific')
    return open_yield_controller(declaration['kind'], epoch='structural_homology_evidence', initial_credit=initial_credit,
                                 parameters=declaration['parameters'],
                                 definition=forecast_definitions(projector.as_record(), CEILING_VERSIONS))
