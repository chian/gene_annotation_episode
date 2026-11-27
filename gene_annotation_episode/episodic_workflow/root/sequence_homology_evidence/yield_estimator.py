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
kind ``forecast``) and ``open_yield_controller``, which takes the declaration's ``parameters`` (the estimator's
settings), ``cost`` (``exchange_rate``, ``job_kinds``) and ``forget_old_rows`` (the values and their reasons are in
the design note). It reads
what ``read_from_parent`` produced (the task key), never the assignment; the declarations are this episode's settings
(``settings['yield_bindings']``).

The definition each action's learned shares are on (``forecast_definitions``: per action type, the digest of the credit
definition record and that action's own ceiling name, ``credit.CEILINGS``) is handed to the controller, and
the estimate ledger's shares of an action are only the rows recorded under that action's definition; its measured
seconds are every row of the action, whatever the definition. Changing one action's ceiling therefore discards only that
action's shares.

The expected seconds of an alignment and of a MetaCATS report are this head's own cost estimator
(``expected_seconds``, given to the controller): what the job is expected to run for at the size the step's situation
states (``credit.situations``), from the past jobs the ledger's load gives for the action. The load holds those jobs
when the declaration's ``cost`` names their ledger kinds in ``job_kinds``: ``bvbrc_msa`` -> ``bvbrc_msa:`` and
``bvbrc_metacats`` -> ``bvbrc_metacats:``."""
from gene_annotation_episode.episodic_workflow.episode_support.configuration.yield_declarations import (
    checked_yield_declaration, forecast_definitions, open_yield_controller)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import (
    bvbrc_metacats_search, bvbrc_msa_alignment)
from yield_control import deciding_seconds, expected_seconds_from_history, situation_size

from .credit import CEILINGS, A101DifferentialCredit


def yield_controller(initial_credit, settings, parent_input):
    projector = A101DifferentialCredit()
    declaration = checked_yield_declaration(settings['yield_bindings'], parent_input['yield_task'],
                                            credit_definition=projector.as_record(),
                                            yield_method=projector.yield_method, code_prefix='scientific')
    return open_yield_controller(declaration['kind'], epoch='sequence_homology_evidence', initial_credit=initial_credit,
                                 parameters=declaration['parameters'], cost=declaration['cost'],
                                 cost_estimator=expected_seconds,
                                 forget_old_rows=declaration['forget_old_rows'],
                                 definition=forecast_definitions(projector.as_record(), CEILINGS))


def expected_seconds(action_type, situation, ledger_seconds, jobs, timings, cost):
    """This head's cost estimator (the contract: ``yield_control``, above ``expected_seconds_from_history``). For an
    alignment (``bvbrc_msa``) and a MetaCATS report (``bvbrc_metacats``) whose situation states the size of the job:
    what that tool's duration curve, fitted on the past jobs ``jobs``, gives for that size (its
    ``expected_job_seconds``), plus the deciding as the plain cost estimator adds it. For every other action, and when
    the situation states no size or the jobs make no curve: the plain cost estimator."""
    tools = {'bvbrc_msa': bvbrc_msa_alignment, 'bvbrc_metacats': bvbrc_metacats_search}
    size = situation_size(situation)
    if action_type in tools and size:
        seconds = tools[action_type].expected_job_seconds(jobs, size)
        if seconds is not None:
            decision = deciding_seconds(ledger_seconds, timings)
            return seconds + (0.0 if decision is None else decision), 'ledger_job_duration_curve_plus_decision'
    return expected_seconds_from_history(action_type, situation, ledger_seconds, jobs, timings, cost)
