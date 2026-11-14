"""A110 chemical accounting and conditional reaction/resource feasibility."""
from .component_axis_workflow import ComponentAxisServiceFactory, ComponentAxisSubtree, create_workflow
from .component_axis_reports import (
    report_schema as _schema, initial_report as _initial, resolve_report as _resolve)


class A110Subtree(ComponentAxisSubtree):
    AXIS = 'A110'


class A110ServiceFactory(ComponentAxisServiceFactory):
    AXIS = 'A110'

    def __call__(self, *args, tool_registry=None, **kwargs):
        factory = self.execution_service_factory
        if factory is not None:
            from .execution_service_setup import ExecutionServiceFactory
            if not isinstance(factory, ExecutionServiceFactory):
                raise TypeError('a110_explicit_execution_service_factory_required')
            if factory.hpc_commissions is not None:
                tool_registry.configure_component_native_hpc(factory.resources)
        return super().__call__(*args, tool_registry=tool_registry, **kwargs)


def report_schema():
    return _schema('A110')


def initial_report():
    return _initial('A110')


def resolve_report(store, report, *, context, services):
    return _resolve(store, report, context=context, services=services, axis='A110')


def create_a110_workflow(store, tools, provider, directory, run_id, controller_factory,
                         *, initial_known_record_refs, **options):
    return create_workflow(store, tools, provider, directory, run_id, controller_factory,
        initial_known_record_refs=initial_known_record_refs, **options)
