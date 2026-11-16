"""Constructor options shared by the saved-binding tests."""
from .api_cases import resources


def constructor_options(store, directory, run_id, tools):
    return dict(store=store, directory=directory, run_id=run_id, resources=resources(),
        initial_information={}, tool_registry=tools, handoff_unit=3., acquired_record_unit=2.,
        log_window_bytes=1024, log_roles=('stdout', 'stderr'), require_private_yield=True,
        task_yield_profiles={'launch_api:api_uniprot_handoff': {'cutoff': .5, 'parameters': {}},
            'launch:api_uniprot_handoff': {'cutoff': .5, 'parameters': {}},
            'results:api_uniprot': {'cutoff': .5, 'parameters': {}}})
