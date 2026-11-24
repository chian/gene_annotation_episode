"""Credit: operational credit for the job's handoff and its acquired results.

Carried from the old ``credit.py`` (``credit_kind`` 'operational'; ``project_credit`` -> ``api_execution.credit_view``)
and ``api_service.py`` ``APIJobService.credit_view`` / ``HMMERJobService.credit_view``:

    credit = handoff_unit * (new distinct (resource_id, execution_id) handoffs not among the initial refs)
           + acquired_record_unit * (new distinct result identities not among the initial refs)

The old credit read the handoff targets and result identities back from the Store. Here the tool that wrote each
handoff returned its identity in its outcome, and ``internal_summary`` lists them (with the two units, which the
commission fixes); this function counts them. It is never bounded, clamped or rescaled. ``scientific_credit`` and
``monitoring_credit`` stay False: the binding is ``operational_credit_binding`` of ``internal_summary``.
The old closed-credit freeze (``closed_credit.py``) is the system's: the Episode's credit is what its controller last
saw."""
import math


def credit(summary, records):
    initial_handoffs = {tuple(identity) for identity in summary['initial_handoff_identities']}
    initial_results = {tuple(identity) for identity in summary['initial_result_identities']}
    handoffs = {tuple(identity) for identity in summary['handoff_identities']}
    results = {tuple(identity) for identity in summary['result_identities']}
    value = (summary['handoff_unit'] * len(handoffs - initial_handoffs)
             + summary['acquired_record_unit'] * len(results - initial_results))
    if not math.isfinite(value):
        raise ValueError('finite_operational_credit_required')
    return value
