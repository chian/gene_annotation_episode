"""The explicit monitoring policy an HPC commission declares (``hpc_campaign.validate_commission``)."""
from __future__ import annotations

from copy import deepcopy
import math


DEFAULT_POLICY = {'min_interval_seconds': 60., 'max_interval_seconds': 1800.,
                  'monitor_cost': .001}


def validate_policy(policy):
    if set(policy) != set(DEFAULT_POLICY) or any(type(v) not in (int, float)
            or not math.isfinite(v) for v in policy.values()):
        raise ValueError('explicit_finite_monitor_policy_required')
    if not 0 < policy['min_interval_seconds'] <= policy['max_interval_seconds'] or policy['monitor_cost'] < 0:
        raise ValueError('invalid_monitor_interval_or_cost')
    return deepcopy(policy)
