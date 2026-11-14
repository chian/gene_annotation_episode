"""Validate inert historical BLAST receipt fields, never execution settings.

The enclosing original plan validator owns the closed policy key sets, job
version, exact VDB allocation record, request digest and all path/compiler
checks. This function replaces only historical LocalJobPolicy construction.
It cannot construct, configure, admit or launch a native job.

Both archived and tracked original LocalJobPolicy.__post_init__ require exact
positive integer memory/scratch values. The archived source additionally checks
an optional wall_seconds data field; it is not forwarded to current policy.
"""
import math


def validate_retained_blast_policy_fields(policy):
    for name in ('memory_bytes', 'scratch_bytes'):
        value = policy[name]
        if type(value) is not int or value <= 0:
            raise ValueError(f'invalid_local_job_{name}')
    if 'wall_seconds' in policy:
        value = policy['wall_seconds']
        if value is not None and (type(value) not in (int, float) or
                not math.isfinite(value) or value <= 0):
            raise ValueError('invalid_local_job_wall_seconds')
