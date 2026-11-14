"""Explicit actual-resource reconstruction for the original v4 Homology family.

This function opens no file, constructs no active policy from saved JSON and
loads no executable named by a descriptor. The caller reopens and supplies the
original typed registry, policy, calculators and optional statistics explicitly.
"""
from .homology_binding_family import HomologyBindingFamily


def restore_homology_family(descriptor, jobs, *, parser_policy, credit_projector,
                            credit_binding, monitoring_projector, monitoring_binding,
                            statistics=None):
    from .runtime import WorkflowError
    if (not isinstance(descriptor, dict) or descriptor.get('version') != 'homology_episode_bindings_v4'
            or 'binding_id' in descriptor):
        raise WorkflowError('resumption requires the original job episode resources and scoring binding')
    family = HomologyBindingFamily(jobs, parser_policy=parser_policy,
        credit_projector=credit_projector, credit_binding=credit_binding,
        monitoring_projector=monitoring_projector, monitoring_binding=monitoring_binding,
        statistics=statistics)
    if family.as_record() != descriptor:
        raise WorkflowError('resumption requires the original job episode resources and scoring binding')
    return family
