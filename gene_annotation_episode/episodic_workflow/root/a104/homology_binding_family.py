"""Explicit original Homology resource family; each task belongs to its private role.

The family serializes the original full v4 resource record. It is not an Episode,
task, continuation controller, native operation implementation or C7 binding.
The caller supplies actual resources and calculators; saved names load nothing.
"""
from .library.homology_family_resources import HomologyFamilyResources
from .library.homology_family_record import original_family_record

ROLES = ('job_launch', 'job_monitor', 'job_results')


class HomologyBindingFamily(HomologyFamilyResources):
    roles = ROLES

    def __init__(self, jobs, *, parser_policy, credit_projector, credit_binding,
                 monitoring_projector, monitoring_binding, statistics=None):
        # One original admission and three original JSON binding copies. Each
        # private attachment below uses that explicit already-admitted owner.
        super().__init__(jobs, parser_policy=parser_policy, credit_projector=credit_projector,
            credit_binding=credit_binding, monitoring_projector=monitoring_projector,
            monitoring_binding=monitoring_binding, statistics=statistics)
        self._attach_private_owners()

    def _attach_private_owners(self):
        from .homology_job_submission.episode import HomologyEpisode as Submission
        from .homology_job_monitoring.episode import HomologyEpisode as Monitoring
        from .homology_result_acquisition.episode import HomologyEpisode as Acquisition
        operands = {'parser_policy': self.parser_policy, 'credit_projector': self._job_credit_calculator,
            'credit_binding': self._role_credit_bindings['job_launch'],
            'monitoring_projector': self.monitoring_projector,
            'monitoring_binding': self._role_credit_bindings['job_monitor'],
            'statistics': self.statistics, '_family_resources': self}
        self._private_bindings = {
            'job_launch': Submission(self.jobs, **operands),
            'job_monitor': Monitoring(self.jobs, **operands),
            'job_results': Acquisition(self.jobs, **operands),
        }

    def for_role(self, role):
        return self._private_bindings[role]

    def as_record(self):
        return original_family_record(self)

    def with_native_events(self, provider):
        # The original typed provider and resource-id admission runs exactly
        # once. Its host-local shallow state copy stays separate from the
        # caller's family; all three actual private owners share the new view.
        view = super().with_native_events(provider)
        view._attach_private_owners()
        return view

    def describe(self):
        return {role: {'report_facts': self.fact_sources(role), 'responsibility': self.instructions(role)}
                for role in ROLES}

    def fact_sources(self, role):
        if role not in ROLES:
            return {}
        return self._private_bindings[role].fact_sources(role)

    def credit_kind(self, role):
        if role not in ROLES:
            raise ValueError('unknown_job_episode_role')
        return self._private_bindings[role].credit_kind(role)

    def assign(self, store, role, selection, scope, *, operation_key):
        if role not in ROLES:
            raise ValueError('unknown_job_episode_role')
        return self._private_bindings[role].assign(store, role, selection, scope, operation_key=operation_key)

    def commission_schemas(self, scientific_child):
        from copy import deepcopy
        from .homology_job_submission.from_parent import append_commission_schemas as launch
        from .homology_job_monitoring.from_parent import append_commission_schemas as monitor
        from .homology_result_acquisition.from_parent import append_commission_schemas as results
        common = {key: deepcopy(value) for key, value in scientific_child['properties'].items()
                  if key != 'kind'}
        values = []
        # The original common deepcopy happens once. Each actual private
        # producer owns its complete specialized original loop body and appends
        # to the same original list with the same original common operands.
        launch(self, common, values)
        monitor(self, common, values)
        results(self, common, values)
        return values


def selected_homology_binding(binding, role):
    """Literal family opt-in; every existing singleton/custom object is unchanged."""
    return binding.for_role(role) if type(binding) is HomologyBindingFamily else binding
