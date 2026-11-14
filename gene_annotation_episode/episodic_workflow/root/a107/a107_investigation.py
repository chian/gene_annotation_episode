"""A107 partner requirements, genomic presence and matched expression."""
from .component_axis_workflow import ComponentAxisServiceFactory, ComponentAxisSubtree, create_workflow
from .component_axis_reports import (
    report_schema as _schema, initial_report as _initial, resolve_report as _resolve)


class A107Subtree(ComponentAxisSubtree):
    AXIS = 'A107'


class A107ServiceFactory(ComponentAxisServiceFactory):
    AXIS = 'A107'

    def __call__(self, *args, tool_registry=None, **kwargs):
        factory = self.execution_service_factory
        if factory is not None:
            from .execution_service_setup import ExecutionServiceFactory
            if not isinstance(factory, ExecutionServiceFactory):
                raise TypeError('a107_explicit_execution_service_factory_required')
            if factory.hpc_commissions is not None:
                tool_registry.configure_a107_genomic_hpc(factory.resources)
                tool_registry.configure_component_native_hpc(factory.resources)
        return super().__call__(*args, tool_registry=tool_registry, **kwargs)


def report_schema():
    return _schema('A107')


def initial_report():
    return _initial('A107')


def resolve_report(store, report, *, context, services):
    return _resolve(store, report, context=context, services=services, axis='A107')


def create_a107_workflow(store, tools, provider, directory, run_id, controller_factory,
                         *, initial_known_record_refs, **options):
    return create_workflow(store, tools, provider, directory, run_id, controller_factory,
        initial_known_record_refs=initial_known_record_refs, **options)
