"""Continuation: the forecast yield controller (``ForecastYieldController``) over the feature credit. The credit
(``credit.py``) grows with every slot admitted, every claim found (waiting or sitting in a slot) and every differential,
and has no fixed maximum, but every action the head offers has a finite ceiling (``credit.ceiling``: what its program
can state at most on a stretch of that length). The forecast of an offered action is a formula, not the model's estimate:
the share of its ceiling such actions realized, times the ceiling. The episode stops when no offered action's forecast
exceeds its expected seconds times the exchange rate, and not while a search is left running (``task.resume_action``).

The parameters are this episode's own (``FORECAST``), starting values of 2026-11-25 with no run behind them, to be tuned
from this episode's own real runs. ``exchange_rate`` is credit per second. A firm claim at a new place earns about 1
(``blast_claims``: the value of a place is run / (run + 1), the family's weight 1). A search at the service has taken from
a few minutes to a quarter of an hour, so at 0.0005 credit per second a search costs about 0.1 to 0.45: it is taken while
such searches are forecast to earn a good part of one new firm claim and refused once they have earned little.
The ledger and the run (the owner, 2026-11-25, after the first real run, in which one search that found nothing made
the forecast of every other search 0 and ended the episode with seven databases untried: "the ledger forecaster needs to
be better really"; "Yes, that is much better if you can cluster by situation"; "history is thin means you don't know a
lot. it means you don't rely on the ledger ... you learn as you go along ... like this is how things used to work before
the ledger. that's what they need to asymptote back to if there is no information"). Each search states its situation
(``credit.situations``: letters of the searched sequence, database, program). ``situation_discount`` 0.5: a past search
counts for the forecast of another in full when it is the same search, half for another program on the same database, a
quarter for another database, an eighth for a sequence of other letters. ``ledger_strength_rows`` 2: the ledger's mean
gets the share W / (W + 2) of a forecast, W the summed weight of its like rows, and the rest goes to the estimate of this
run alone, which is the earlier controllers' own estimator over this run's searches; so the ledger and the run weigh the
same once the ledger holds two searches' worth of like history, and with little like history the episode learns as it
goes. Both are starting values with no run behind them.

The definition each action's learned gains are on (``forecast_definitions``: per action type, the digest of the credit
definition record and that action's own ceiling name, ``credit.CEILINGS``) is handed to the controller. The assignment is
not read here."""
from gene_annotation_episode.episodic_workflow.episode_support.configuration.yield_declarations import (
    forecast_definitions, open_yield_controller)
from yield_control import expected_seconds_from_history

from .credit import CEILINGS, FeatureDifferentialCredit

FORECAST = {'parameters': {'ledger_strength_rows': 2.0, 'situation_discount': 0.5},
            'cost': {'exchange_rate': 0.0005, 'job_kinds': {}}, 'forget_old_rows': True}


def yield_controller(initial_credit, settings, parent_input):
    return open_yield_controller('forecast', epoch='feature_calling', initial_credit=initial_credit,
                                 parameters=FORECAST['parameters'], cost=FORECAST['cost'],
                                 cost_estimator=expected_seconds_from_history,
                                 forget_old_rows=FORECAST['forget_old_rows'],
                                 definition=forecast_definitions(FeatureDifferentialCredit().as_record(), CEILINGS))
