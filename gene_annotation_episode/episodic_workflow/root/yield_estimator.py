"""Continuation: the forecast yield controller (``ForecastYieldController``) over the root's credit (``credit.py``:
feature calling's credit as the base, multiplied by the factor of the axis credits; the owner, 2026-11-23: "this does
seem to suggest we do need the forecast yield controller ... make that switch"). The root chooses among steps of very
different cost, and each kind of step is forecast on its own: the gain steps of that kind realized before (this
episode's units and the estimate ledger's history of the kind ``root:<action type>``) against the seconds they took. A
commission of feature calling has no ceiling (``credit.ceiling``: ``UNBOUNDED``), nor has a commission of an axis head
once feature calling is credited, so their forecast is the typical gain of that kind; with no unit of the kind anywhere
it is unknown, and an unknown forecast is neither refused nor lets the episode stop. While feature calling has no
credit the ceiling of an axis head is 0, so its forecast is 0 and it is refused: the credit cannot rise by it. The
episode stops when no offered step's forecast exceeds its expected seconds times the exchange rate and no work is owed
(``task.resume_action``). Nothing else ends this episode.

``ROOT_FORECAST`` is the root's own tuning (the owner, 2026-11-22: the stop settings are "tuned parameters based on
what behavior you want"). ``exchange_rate`` is the price of a second in the root's credit: 0.0000005. Tuned from the
root runs of 2026-11-23, when the credit was the axes' hypervolume alone (it is now that factor times feature calling's
base, so the same axis progress is worth the base times as much; with the base near 1 the tuning carries over, and it
is to be tuned again from root runs with feature calling). All claim checks are one kind of step and share one forecast: the mean of what the ledger's
checks earned and of what this run's checks earned. The same claim (popZ binds parB) was checked in three runs and
found 0.0173 (run 05), 0.228 on its sheet (run 06, stopped for another reason before it returned) and 0 (run 08): one
check of one claim is a noisy sample and says little about the next claim. At 0.00003 (the first value, from one good
check measured before) the one weak check of run 05 priced out the two claims still unchecked; at 0.000002 the empty
check of run 08 ended the checks with three claims unchecked, binds chpT among them (0.249 in the A105 head run 20),
and the root returned a family of unknown function as its best annotation. A claim check is how the root learns
whether experiments bear on an annotation, and it takes about two hours whatever it finds, so the rate is set so that
an empty check does not end the checks: with the ledger's mean at 0.0087 the forecast after any number of empty
checks in a run is half of it, 0.0043, against a threshold of about 0.003 for a check of 100 minutes. The checks then
end when the claims are used up, or when the ledger's mean itself has fallen (many runs of empty checks). A commission
of the sequence-homology head earns far above it. To be tuned again as root runs accumulate.
``forget_old_rows``: ledger rows are weighted by age, as for the other forecast episodes. ``job_kinds``: none, for every
action the root offers, feature calling among them (it leaves no job running: its searches end inside its own turn); a
step's cost is its measured unit seconds.

The definition the learned gains are on (``forecast_definitions``: the digest of the credit definition record and
each action's ceiling name, ``credit.CEILINGS``, which names every action the root offers, ``feature_calling`` among
them) is handed to the controller: the ledger's history of an action is only the rows recorded under that action's
definition. The credit definition changed on 2026-11-25 (feature calling's credit became the base), so the ledger's
rows of every action recorded before are on another definition and the learned shares start afresh.

The annotation task sets no target and no maximum, so the controller takes nothing from ``parent_input`` (what
``messages/read_from_parent.py`` produced). The assignment is not read here."""
from gene_annotation_episode.episodic_workflow.episode_support.configuration.yield_declarations import (
    forecast_definitions, open_yield_controller)

from .credit import CEILINGS, CREDIT_DEFINITION

ROOT_FORECAST = {'exchange_rate': 0.0000005, 'forget_old_rows': True, 'job_kinds': {}}


def yield_controller(initial_credit, settings, parent_input):
    return open_yield_controller('forecast', epoch='root', initial_credit=initial_credit, parameters=ROOT_FORECAST,
                                 definition=forecast_definitions(CREDIT_DEFINITION, CEILINGS))
