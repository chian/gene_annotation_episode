"""Continuation: the forecast yield controller (``ForecastYieldController``) over the taxon credit. The credit
(``credit.py``) is a sum that grows with every admitted candidate taxon and every differential and has no fixed maximum, but
every action the head offers has a ceiling (``credit.ceiling``: the most the credit can rise if that action is the next
unit). The forecast of an offered action is therefore a formula, not the model's estimate: the share of its ceiling such
actions realized before (this episode's units and the estimate ledger's history of the kind
``organism_identification:<action type>``) times the ceiling. The episode stops when no offered action's forecast exceeds
its expected seconds times the exchange rate (``yield_control``, section ``ForecastYieldController``; the design is
``docs/plan/designs/forecast_yield_controller.md``).

The parameters are this episode's own (``FORECAST``). ``exchange_rate`` is credit per second. A first classification of a
sequence that has a relative in the index earns about 1 (the sheets are weighted so) and takes seconds to half a minute; one
that finds nothing earns 0. The rate 0.002 lets a classification of a kind that has earned be taken (a forecast of 0.1
over 30 seconds is 0.0033 per second) and stops a kind that keeps earning nothing. It is a first value from the direct
checks of 2026-11-24, to be tuned from this episode's own real runs.

The definition each action's learned shares are on (``forecast_definitions``: per action type, the digest of the credit
definition record and that action's own ceiling name, ``credit.CEILINGS``) is handed to the controller. The assignment is
not read here."""
from gene_annotation_episode.episodic_workflow.episode_support.configuration.yield_declarations import (
    forecast_definitions, open_yield_controller)

from .credit import CEILINGS, TaxonDifferentialCredit

FORECAST = {'exchange_rate': 0.002, 'forget_old_rows': True, 'job_kinds': {}}


def yield_controller(initial_credit, settings, parent_input):
    return open_yield_controller('forecast', epoch='organism_identification', initial_credit=initial_credit,
                                 parameters=FORECAST,
                                 definition=forecast_definitions(TaxonDifferentialCredit().as_record(), CEILINGS))
