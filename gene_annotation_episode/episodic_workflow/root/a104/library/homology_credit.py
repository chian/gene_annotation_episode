"""Original caller-injected Homology scalar calculation, without episode state.

Source-only candidate for own A104 library/homology_credit.py. The explicit
callers and role operands remain the original functions; no new score policy.
"""
from copy import deepcopy
import math


def project_homology_credit(job_credit_calculator, monitoring_projector, store,
                            role, assignment, episode_id, run_id):
    calculators = {
        'job_launch': (job_credit_calculator, 'job_launch'),
        'job_monitor': (monitoring_projector, 'job_monitor'),
        'job_results': (job_credit_calculator, 'job_results'),
    }
    if role not in calculators:
        raise ValueError('unknown_job_episode_role')
    calculator, selected_role = calculators[role]
    value = calculator(store, role=selected_role, assignment=deepcopy(assignment),
        episode_id=episode_id, run_id=run_id)
    value = float(value['credit'] if isinstance(value, dict) else value)
    if not math.isfinite(value):
        raise ValueError('finite_operational_credit_required')
    return value
