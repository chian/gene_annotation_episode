"""Original public raw API credit invocation; private episodes bind their own callback."""
from ..communication import plain
from ..domain import ContractError
from .api_operational_credit import operational_credit_from_identities

def standalone_api_credit(api, context, receiver_selection):
    facts = api.facts(context, {})
    selection = plain(receiver_selection)
    known, initial = (set(selection['known_record_refs']), set(selection['initial_known_record_refs']))
    if not initial <= known:
        raise ValueError('api_initial_references_must_be_known')
    old_handoffs, old_results = (set(), set())
    for reference in initial:
        try:
            target = api.read_target(reference, context.scope)
            old_handoffs.add((target['resource_id'], target['execution_id']))
        except (ValueError, ContractError, KeyError, OSError):
            pass
        try:
            old_results.add(api.result_identity(reference, context.scope))
        except (ValueError, ContractError, KeyError, OSError):
            pass
    handoffs = set()
    for reference in set(facts['execution_handoff_refs']) & known:
        target = api.read_target(reference, context.scope)
        handoffs.add((target['resource_id'], target['execution_id']))
    results = {api.result_identity(ref, context.scope) for ref in set(facts['execution_result_refs']) & known}
    return operational_credit_from_identities(handoffs, old_handoffs, results, old_results, api.handoff_unit, api.acquired_record_unit)
