"""Construct the parent-private Homology implementations."""

def legacy_parent_types():
    from gene_annotation_episode.episodic_workflow.root.a103.episode import LegacyAnnotationEpisode
    from .legacy_improvement.episode import LegacyImprovementEpisode
    return {'annotation': LegacyAnnotationEpisode, 'improvement': LegacyImprovementEpisode}


def homology_binding_types():
    from gene_annotation_episode.episodic_workflow.root.a103.homology_job_submission.episode import HomologyEpisode as AnnotationSubmission
    from gene_annotation_episode.episodic_workflow.root.a103.homology_job_monitoring.episode import HomologyEpisode as AnnotationMonitoring
    from gene_annotation_episode.episodic_workflow.root.a103.homology_result_acquisition.episode import HomologyEpisode as AnnotationAcquisition
    from .legacy_improvement.homology_job_submission.episode import HomologyEpisode as ImprovementSubmission
    from .legacy_improvement.homology_job_monitoring.episode import HomologyEpisode as ImprovementMonitoring
    from .legacy_improvement.homology_result_acquisition.episode import HomologyEpisode as ImprovementAcquisition
    return {
        'legacy_annotation': {'job_launch': AnnotationSubmission, 'job_monitor': AnnotationMonitoring, 'job_results': AnnotationAcquisition},
        'legacy_improvement': {'job_launch': ImprovementSubmission, 'job_monitor': ImprovementMonitoring, 'job_results': ImprovementAcquisition},
    }


def create_homology_bindings(jobs, *, parser_policy, credit_projector, credit_binding,
                             monitoring_projector, monitoring_binding, statistics=None):
    """Share only the caller's original registry/statistics constructor operands."""
    return {parent: {role: cls(jobs, parser_policy=parser_policy,
                credit_projector=credit_projector, credit_binding=credit_binding,
                monitoring_projector=monitoring_projector, monitoring_binding=monitoring_binding,
                statistics=statistics) for role, cls in children.items()}
            for parent, children in homology_binding_types().items()}


def bound_homology_family(supplied):
    """Retain the supplied real object and construct its actual private counterparts."""
    types = homology_binding_types()
    matches = [(parent, role) for parent, children in types.items()
               for role, cls in children.items() if type(supplied) is cls]
    if len(matches) != 1:
        raise TypeError('typed_homology_episode_binding_required')
    parent, role = matches[0]
    if supplied.roles != (role,) or supplied.commissioning_parent != parent:
        raise ValueError('homology_parent_role_binding_mismatch')
    family = create_homology_bindings(supplied.jobs, parser_policy=supplied.parser_policy,
        credit_projector=supplied._job_credit_calculator,
        credit_binding=supplied._role_credit_bindings['job_launch'],
        monitoring_projector=supplied.monitoring_projector,
        monitoring_binding=supplied._role_credit_bindings['job_monitor'],
        statistics=supplied.statistics)
    if supplied.native_event_provider is not None:
        family = {name: {key: binding.with_native_events(supplied.native_event_provider)
                        for key, binding in children.items()}
                  for name, children in family.items()}
    family[parent][role] = supplied
    for children in family.values():
        for binding in children.values():
            if (binding.jobs is not supplied.jobs or binding.statistics is not supplied.statistics
                    or binding.native_event_provider is not supplied.native_event_provider):
                raise ValueError('homology_family_requires_original_mutable_custody')
    return family


def homology_binding_record(supplied, *, family=None):
    """Record both real parents and their active private child implementations."""
    if supplied is None:
        return None
    if family is None:
        family = bound_homology_family(supplied)
    parents = legacy_parent_types()
    return {'version': 'parent_private_homology_bindings_v1',
            'active_roles': list(supplied.roles),
            'parents': {parent.binding_path: {'parent': parent.as_record(),
                'children': {role: family[parent.binding_path][role].as_record()
                             for role in supplied.roles}}
                for parent in parents.values()}}
