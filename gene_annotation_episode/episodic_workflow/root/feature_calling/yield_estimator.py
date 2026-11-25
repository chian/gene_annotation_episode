"""Continuation: the forecast yield controller (``ForecastYieldController``) over the feature credit. The credit
(``credit.py``) grows with every slot admitted, every claim found while no slot includes it and every differential, and
has no fixed maximum. The one action the head offers, a database search, has no finite ceiling (``credit.ceiling``), so
its forecast is not a share of a ceiling: it is the typical gain of such searches (this episode's units and the estimate
ledger's history of the kind ``feature_calling:bvbrc_blast``). The episode stops when no offered action's forecast
exceeds its expected seconds times the exchange rate, and not while a search is left running (``task.resume_action``).

The parameters are this episode's own (``FORECAST``), starting values of 2026-11-25 with no run behind them, to be tuned
from this episode's own real runs. ``exchange_rate`` is credit per second. A firm claim at a new place earns about 1
(``blast_claims``: the value of a place is run / (run + 1), the family's weight 1). A search at the service has taken from
a few minutes to a quarter of an hour, so at 0.0005 credit per second a search costs about 0.1 to 0.45: it is taken while
such searches are forecast to earn a good part of one new firm claim and refused once they have earned little.
``ledger_prior_rows`` 1 is set as in the organism identification head, but the controller uses it only for an action
with a finite ceiling, so it does nothing here: with no history, one finished search that earns nothing gives a forecast
of 0 and the episode stops after it. Whether that is wanted is to be seen in the first real runs.

The definition each action's learned gains are on (``forecast_definitions``: per action type, the digest of the credit
definition record and that action's own ceiling name, ``credit.CEILINGS``) is handed to the controller. The assignment is
not read here."""
from gene_annotation_episode.episodic_workflow.episode_support.configuration.yield_declarations import (
    forecast_definitions, open_yield_controller)

from .credit import CEILINGS, FeatureDifferentialCredit

FORECAST = {'exchange_rate': 0.0005, 'forget_old_rows': True, 'job_kinds': {}, 'ledger_prior_rows': 1.0}


def yield_controller(initial_credit, settings, parent_input):
    return open_yield_controller('forecast', epoch='feature_calling', initial_credit=initial_credit,
                                 parameters=FORECAST,
                                 definition=forecast_definitions(FeatureDifferentialCredit().as_record(), CEILINGS))
