"""Continuation: the forecast yield controller (``ForecastYieldController``) over the taxon credit. The credit
(``credit.py``) is a sum that grows with every admitted candidate taxon and every differential and has no fixed maximum, but
every action the head offers has a ceiling (``credit.ceiling``: the most the credit can rise if that action is the next
unit). The forecast of an offered action is therefore a formula, not the model's estimate: the share of its ceiling such
actions realized before (this episode's units and the estimate ledger's history of the kind
``organism_identification:<action type>``) times the ceiling. The episode stops when no offered action's forecast exceeds
its expected seconds times the exchange rate (``yield_control``, section ``ForecastYieldController``; the design is
``docs/plan/designs/forecast_yield_controller.md``).

The parameters are this episode's own (``FORECAST``). ``exchange_rate`` is credit per second. The sheets are weighted so
that a strong result of any tool counts about 1. The tools differ in time by more than tenfold: a Kraken 2 classification
takes seconds to half a minute, a VITAP assignment a few minutes, a geNomad run several minutes (about 500 seconds measured
on 2026-11-24). At 0.0005 credit per second a geNomad run costs about 0.25 and a VITAP assignment about 0.08, so each is
taken while it is forecast to earn a good part of a strong result (a first run of a kind is forecast at half its ceiling,
0.5 or more) and refused once runs of its kind have earned little. A Kraken 2 classification costs about 0.01. The first
value, 0.002 (the Kraken 2 only head of the first three runs), would have priced geNomad at 1.0, more than a first run of
it can be forecast to earn, so the one tool that places a distant virus would never have been asked. To be tuned from this
episode's own real runs.

``ledger_prior_rows`` 1: the ledger learns softly. The share of no history, one half, counts as one row in the ledger's
mean share of each tool, so the first real rows move it part of the way and a tool is not judged by one piece. In run 07
(2026-11-24) the ledger held one Kraken 2 row under the present credit definition, the distant virus of run 05 on which
Kraken 2 rightly found nothing: the share was 0, the forecast 0, and Kraken 2 could not be chosen for a stretch of
Escherichia coli that it names in 33 seconds; the head spent 13 minutes on the two slow tools and returned "cellular
organisms". With one prior row that single 0 gives a share of 0.25. The owner, 2026-11-25: "change the yield estimator to
not skip Kraken2. that's a behavior tuning"; "the ledger ought to have some soft learning".

The definition each action's learned shares are on (``forecast_definitions``: per action type, the digest of the credit
definition record and that action's own ceiling name, ``credit.CEILINGS``) is handed to the controller. The assignment is
not read here."""
from gene_annotation_episode.episodic_workflow.episode_support.configuration.yield_declarations import (
    forecast_definitions, open_yield_controller)

from .credit import CEILINGS, TaxonDifferentialCredit

FORECAST = {'exchange_rate': 0.0005, 'forget_old_rows': True, 'job_kinds': {}, 'ledger_prior_rows': 1.0}


def yield_controller(initial_credit, settings, parent_input):
    return open_yield_controller('forecast', epoch='organism_identification', initial_credit=initial_credit,
                                 parameters=FORECAST,
                                 definition=forecast_definitions(TaxonDifferentialCredit().as_record(), CEILINGS))
