"""Continuation: the forecast yield controller (``ForecastYieldController``) over the annotation credit (the owner,
2026-11-23: "this does seem to suggest we do need the forecast yield controller ... make that switch"). The root
chooses among steps of very different cost, and each kind of step is forecast on its own: the gain steps of that kind
realized before (this episode's units and the estimate ledger's history of the kind ``root:<action type>``) against
the seconds they took. A commission of an axis head has no ceiling (``credit.ceiling``: ``UNBOUNDED``), so its forecast
is the typical gain of that kind; with no unit of the kind anywhere it is unknown, and an unknown forecast is neither
refused nor lets the episode stop. The episode stops when no offered step's forecast exceeds its expected seconds times
the exchange rate and no work is owed (``task.resume_action``). Nothing else ends this episode.

``ROOT_FORECAST`` is the root's own tuning (the owner, 2026-11-22: the stop settings are "tuned parameters based on
what behavior you want"). ``exchange_rate`` is the price of a second in annotation credit: 0.000002. Tuned from the
first root run that returned (``root_a101_a105_05``, 2026-11-23). All claim checks are one kind of step and share one
forecast, and one check moves it all the way. In that run the first claim checked (popZ binds parB) found one weak
result: 0.0173 annotation credit in 4849 s, 0.0000036 per second. At the first value of the rate (0.00003, half the
rate of the one good check measured before: binds ChpT in the A105 head run 20, about 0.47 in 2 h 13 min) that priced
out the two claims still unchecked, binds ChpT among them, and its ledger row alone would have refused the first check
of every later run. What a claim check is for is to find whether experiments bear on the annotation, and one claim says
little about the next, so the rate sits just below what a check that found something weak earned: a check that finds
anything keeps the checks going, and the forecast after a check that finds nothing (half of the ledger's mean) falls
under the threshold and ends them. A commission of the sequence-homology head earns far above it (0.9 in about 6
minutes). To be tuned again as root runs accumulate.
``forget_old_rows``: ledger rows are weighted by age, as for the other forecast episodes. ``job_kinds``: none; a
step's cost is its measured unit seconds.

The definition the learned gains are on (``forecast_definitions``: the digest of the credit definition record and
each action's ceiling name, ``credit.CEILINGS``) is handed to the controller: the ledger's history of an action is
only the rows recorded under that action's definition.

The annotation task sets no target and no maximum, so the controller takes nothing from ``parent_input`` (what
``messages/read_from_parent.py`` produced). The assignment is not read here."""
from gene_annotation_episode.episodic_workflow.episode_support.configuration.yield_declarations import (
    forecast_definitions, open_yield_controller)

from .credit import CEILINGS, CREDIT_DEFINITION

ROOT_FORECAST = {'exchange_rate': 0.000002, 'forget_old_rows': True, 'job_kinds': {}}


def yield_controller(initial_credit, settings, parent_input):
    return open_yield_controller('forecast', epoch='root', initial_credit=initial_credit, parameters=ROOT_FORECAST,
                                 definition=forecast_definitions(CREDIT_DEFINITION, CEILINGS))
