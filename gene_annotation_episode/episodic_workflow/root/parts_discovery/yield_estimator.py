"""Continuation: the forecast controller (``ForecastYieldController``) over the part credit. The credit (``credit.py``) has no fixed
maximum, but every action the head offers has a ceiling (``credit.ceiling``: the most the credit can rise if that action is the next
unit; a gene finding and an RNA scan are ``UNBOUNDED``, with the reason beside them). The forecast of an offered action is a
formula, not the model's estimate: the share of its ceiling such actions realized before, or for an ``UNBOUNDED`` action their
typical gain, from this episode's units and the estimate ledger's history of the kind ``parts_discovery:<action type>``. The episode
stops when no offered action's forecast exceeds its expected seconds times the exchange rate (``yield_control``, section
``ForecastYieldController``; the design is ``docs/plan/designs/forecast_yield_controller.md``).

The controller is opened through the library's ``checked_yield_declaration`` (the declaration for the task key
``parts_discovery:parts_reading`` as ``read_from_parent`` reads it must name exactly this credit definition,
``PartsDiscoveryCredit(part_units).as_record()``, and the kind ``forecast``) and ``open_yield_controller``, which takes the
declaration's ``parameters`` (the estimator's settings), ``cost`` (``exchange_rate``, ``job_kinds``) and ``forget_old_rows``, and this
episode's cost estimator (the plain one, ``expected_seconds_from_history``). The exchange rate is in credit per second and
the credit's scale is the commissioner's ``part_units``: it is a setting of the run and is set with them. The declarations are this
episode's settings (``settings['yield_bindings']``); the controller reads what ``read_from_parent`` produced (the task key and the
part units), never the assignment.

The definition each action's learned shares are on (``forecast_definitions``: per action type, the digest of the credit definition
record and that action's own ceiling name, ``credit.CEILINGS``) is handed to the controller."""
from gene_annotation_episode.episodic_workflow.episode_support.configuration.yield_declarations import (
    checked_yield_declaration, forecast_definitions, open_yield_controller)

from yield_control import expected_seconds_from_history

from .credit import CEILINGS, PartsDiscoveryCredit


def yield_controller(initial_credit, settings, parent_input):
    projector = PartsDiscoveryCredit(parent_input['part_units'])
    declaration = checked_yield_declaration(settings['yield_bindings'], parent_input['yield_task'],
                                            credit_definition=projector.as_record(),
                                            yield_method=projector.yield_method, code_prefix='parts_discovery')
    return open_yield_controller(declaration['kind'], epoch='parts_discovery', initial_credit=initial_credit,
                                 parameters=declaration['parameters'], cost=declaration['cost'],
                                 cost_estimator=expected_seconds_from_history,
                                 forget_old_rows=declaration['forget_old_rows'],
                                 definition=forecast_definitions(projector.as_record(), CEILINGS))
