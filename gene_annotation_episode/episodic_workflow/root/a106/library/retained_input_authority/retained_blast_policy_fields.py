"""Validate inert BLAST receipt policy fields, never execution settings.

The enclosing plan validator owns the closed policy key set, job version, exact
VDB allocation record, request digest and all path/compiler checks. This
function cannot construct, configure, admit or launch a native job.
"""


def validate_retained_blast_policy_fields(policy):
    for name in ('memory_bytes', 'scratch_bytes'):
        value = policy[name]
        if type(value) is not int or value <= 0:
            raise ValueError(f'invalid_local_job_{name}')
