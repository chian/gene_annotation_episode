"""Execute only explicit ready CDS plans through the existing native view."""
from .coding_sequence_support import _validated_plan
from .sequence_views import view_sequence


def run_coding_sequence_plan(plan):
    plan=_validated_plan(plan)
    results=[]
    for row in plan['rows']:
        result={'selection_ordinal':row['selection_ordinal'],'native_result':None,'failure_code':None}
        results.append(result)
        if row['status']!='ready':
            result['failure_code']='plan_unavailable'
            continue
        try:
            result['native_result']=view_sequence(row['input_sequence'],**row['effective_request'])
        except (ValueError,TypeError):
            result['failure_code']='native_extraction_failed'
    return results


__all__=['run_coding_sequence_plan']
