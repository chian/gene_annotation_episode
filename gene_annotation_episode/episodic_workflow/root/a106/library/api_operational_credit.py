"""Exact detached operational identity-set calculation; no episode or reader dispatch."""
import math
from ..api_service_execution import VERSION

def operational_credit_from_identities(handoffs, old_handoffs, results, old_results, handoff_unit, acquired_record_unit):
    new_handoffs, new_results = (len(handoffs - old_handoffs), len(results - old_results))
    value = handoff_unit * new_handoffs + acquired_record_unit * new_results
    if not math.isfinite(value):
        raise ValueError('finite_operational_credit_required')
    return {'credit': value, 'operational_credit': value, 'new_handoff_count': new_handoffs, 'new_acquired_record_count': new_results, 'operational_credit_binding': {'version': VERSION, 'handoff_unit': handoff_unit, 'acquired_record_unit': acquired_record_unit, 'scientific_credit': False, 'monitoring_credit': False}}
