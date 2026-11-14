"""Typed registry for the three predefined A101 Homology task owners.

This registry supplies the original optional runtime job interface. Scientific
operations, contracts, progress and task execution remain in their private homes.
"""
from types import MappingProxyType

from .homology_job_submission.episode import HomologyEpisode as Submission
from .homology_job_monitoring.episode import HomologyEpisode as Monitoring
from .homology_result_acquisition.episode import HomologyEpisode as Acquisition

_PRIVATE_TYPES = {'job_launch': Submission, 'job_monitor': Monitoring, 'job_results': Acquisition}


class HomologyBindingFamily:
    roles = ('job_launch', 'job_monitor', 'job_results')

    def __init__(self, bindings):
        if (not isinstance(bindings, dict) or set(bindings) != set(self.roles)
                or any(type(bindings[role]) is not kind for role, kind in _PRIVATE_TYPES.items())):
            raise TypeError('explicit_complete_private_homology_family_required')
        launch = bindings['job_launch']
        for binding in bindings.values():
            if (binding.jobs.config != launch.jobs.config
                    or binding.jobs.directory != launch.jobs.directory
                    or binding.parser_policy.to_dict() != launch.parser_policy.to_dict()):
                raise ValueError('homology_roles_require_original_shared_job_registry')
            if binding.native_event_provider is not launch.native_event_provider:
                raise ValueError('homology_family_native_event_provider_conflict')
            if binding.statistics is not launch.statistics:
                raise ValueError('homology_family_statistics_binding_conflict')
        self.bindings = MappingProxyType(dict(bindings))
        self.jobs = launch.jobs
        self.parser_policy = launch.parser_policy
        self.statistics = launch.statistics
        self.native_event_provider = launch.native_event_provider

    def for_role(self, role):
        try:
            return self.bindings[role]
        except KeyError as error:
            raise ValueError('unknown_job_episode_role') from error

    def for_source(self, source):
        return self.for_role(source.path[-1][0])

    def as_record(self):
        return {'binding_id': 'homology_private_role_family',
                'version': 'homology_private_role_family_v1',
                'bindings': {role: self.for_role(role).as_record() for role in self.roles}}

    def describe(self):
        return {role: self.for_role(role).describe()[role] for role in self.roles}

    def commission_schemas(self, scientific_child):
        return [schema for role in self.roles
                for schema in self.for_role(role).commission_schemas(scientific_child)]

    def instructions(self, role):
        return self.for_role(role).instructions(role)

    def assign(self, store, role, selection, scope, *, operation_key):
        return self.for_role(role).assign(store, role, selection, scope, operation_key=operation_key)

    def assignment(self, source):
        return self.for_source(source).assignment(source)

    def catalog(self, source):
        return self.for_source(source).catalog(source)

    async def execute(self, source, name, args, *, operation_key):
        return await self.for_source(source).execute(source, name, args, operation_key=operation_key)

    def facts(self, source, *, credit_view=None):
        return self.for_source(source).facts(source, credit_view=credit_view)

    def credit_view(self, source):
        return self.for_source(source).credit_view(source)

    def working_state(self, source):
        return self.for_source(source).working_state(source)

    def initial_credit(self, store, role, assignment, episode_id, run_id):
        return self.for_role(role).initial_credit(store, role, assignment, episode_id, run_id)

    def credit_kind(self, role):
        return self.for_role(role).credit_kind(role)

    def binding_for(self, role):
        return self.for_role(role).binding_for(role)

    def has_information_channel(self, role):
        return self.for_role(role).has_information_channel(role)

    def fact_sources(self, role):
        return {} if role not in self.roles else self.for_role(role).fact_sources(role)

    def validate_report(self, value, assignment, *, role, store=None, schema=None):
        return self.for_role(role).validate_report(value, assignment, role=role, store=store, schema=schema)

    def latest_sample(self, source, *, include_inherited=False):
        return self.for_source(source).latest_sample(source, include_inherited=include_inherited)

    def latest_checked_status(self, source):
        return self.for_source(source).latest_checked_status(source)

    def received_timing_records(self, store, value, schema, scope):
        return self.for_role('job_monitor').received_timing_records(store, value, schema, scope)

    def resolve(self, store, scope, value, namespace, *, assignment=None):
        return self.for_role('job_results').resolve(store, scope, value, namespace, assignment=assignment)

    def recover_statistics(self):
        return self.for_role('job_launch').recover_statistics()

    def recover_native_events(self):
        return self.for_role('job_launch').recover_native_events()

    def with_native_events(self, provider):
        return type(self)({role: binding.with_native_events(provider) for role, binding in self.bindings.items()})

    def prospective_execution_options(self, store, scope):
        return self.for_role('job_launch').prospective_execution_options(store, scope)

    def prospective_execution_classes(self, store, scope):
        return self.for_role('job_launch').prospective_execution_classes(store, scope)


def normalize_homology_family(value):
    """Keep explicit private callers and unrelated legacy implementations intact."""
    if type(value) is HomologyBindingFamily:
        return value
    if isinstance(value, dict):
        return HomologyBindingFamily(value)
    if type(value) not in _PRIVATE_TYPES.values():
        return value
    from .homology_service_setup import create_homology_bindings
    bindings = create_homology_bindings(value.jobs, parser_policy=value.parser_policy,
        credit_projector=value._job_credit_calculator,
        credit_binding=value._role_credit_bindings['job_launch'],
        monitoring_projector=value.monitoring_projector,
        monitoring_binding=value._role_credit_bindings['job_monitor'], statistics=value.statistics)
    if value.native_event_provider is not None:
        bindings = {role: binding.with_native_events(value.native_event_provider)
                    for role, binding in bindings.items()}
    bindings[value.roles[0]] = value
    return HomologyBindingFamily(bindings)
