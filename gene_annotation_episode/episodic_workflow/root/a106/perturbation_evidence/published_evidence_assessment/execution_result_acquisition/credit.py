"""Credit: the operational credit of the result acquisition. New unique handoff identities earn the handoff unit
and new unique result identities earn the acquired-record unit, each counted against the identities the episode
started with: the handoff identity of the original handoff, and no result (old ``_api_operational_credit`` -> ``operational_credit_from_identities(handoffs, old_handoffs,
results, old_results, handoff_unit, acquired_record_unit)``; the initial references of this episode are the
original handoff, so the handoff earns nothing and acquired results earn). The identities and the two units come
from the tools' outcomes through the summary: credit has no services and no settings, and the identities are the
service's (old ``api.read_target(...)`` and ``api.result_identity(...)``).

Credit is not bounded here. The old closed-credit snapshot (``_closed_credit_*``), the completion projectors
(``_appservice_completion``, ``_appservice_publication_completion``, ``completion_for_action``,
``verify_completion``, ``_proof_for_action``, ``_closed_completion_verdict``) and ``credit_kind`` are machinery of
the old runner or of the practical-completion estimator and are not carried."""


def credit(summary, records):
    units = summary['credit_units']
    if units is None:
        return 0.0
    new_handoffs = set(summary['handoff_identities']) - set(summary['initial_handoff_identities'])
    new_results = set(summary['result_identities'])
    return units['handoff_unit'] * len(new_handoffs) + units['acquired_record_unit'] * len(new_results)
