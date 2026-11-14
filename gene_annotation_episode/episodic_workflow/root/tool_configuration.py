"""One caller-configuration path for ordinary tools, CLI or case harness."""
from copy import deepcopy
from pathlib import Path

from gene_annotation_episode.acquisition import PublicClients
from .tool_registry import ToolRegistry
from gene_annotation_episode.ordinary_execution import OrdinaryExecutionStatistics
from gene_annotation_episode.public_configuration import configured_tools


def _construct_tools(store, configuration, *, run_directory, registry_class):
    if not isinstance(registry_class, type) or not issubclass(registry_class, ToolRegistry):
        raise TypeError('tool_registry_class_required')
    configuration = configured_tools(configuration)
    public, local = configuration.get('public', {}), configuration.get('local_tools', {})
    clients = PublicClients(ncbi_email=public.get('ncbi_email'),
        skill_root=Path(public['skill_root']) if public.get('skill_root') else None,
        work_dir=Path(run_directory).expanduser().resolve()/'public-client-work',
        access_dir=(Path(public['provider_access_dir']).expanduser() if 'provider_access_dir' in public
                    else None))
    statistics = (OrdinaryExecutionStatistics(configuration['history'], configuration['resource_id'],
        local.get('native_receipts_dir', store.path/'native-execution-receipts'))
        if 'history' in configuration or 'resource_id' in configuration else None)
    tools = registry_class(store, clients=clients, job_limits=configuration.get('local_jobs'),
        local_resources=configuration.get('local_resources'),
        knowledge_library_directory=configuration.get('knowledge_library_directory'),
        native_statistics=statistics,
        provider_poll_interval_seconds=public.get('poll_interval_seconds', 5),
        **{name: local[name] for name in ('cmsearch_executable', 'cmsearch_cpu',
            'minimap2_executable', 'minimap2_cpu', 'minimap2_cache_dir',
            'pdfinfo_executable', 'pdftotext_executable', 'pdftoppm_executable') if name in local})
    # Reconstruction receives the actual caller operands, independently of
    # later mutation of the input mapping. Custom registries have no inferred
    # configuration merely because they expose similar resource records.
    tools.reconstruction_configuration = deepcopy(configuration)
    return tools


def build_tools(store, configuration=None, *, run_directory, registry_class=ToolRegistry):
    """Construct fresh tools with an explicit caller-selected run directory."""
    if not isinstance(registry_class, type) or not issubclass(registry_class, ToolRegistry):
        raise TypeError('tool_registry_class_required')
    selected = configured_tools(configuration)
    if 'transport_timeout_seconds' in selected.get('public', {}):
        raise ValueError('transport_timeout_configuration_not_supported')
    return _construct_tools(store, selected, run_directory=run_directory,
        registry_class=registry_class)


def reopen_tools(store, run_directory, configuration, *, registry_class=ToolRegistry):
    """Reopen exact authenticated saved configuration; old elapsed data stay inert."""
    from gene_annotation_episode.domain import canonical
    from .saved_run_records import _settings, _failure
    run_directory = Path(run_directory).expanduser().resolve()
    _, settings = _settings(store, run_directory)
    saved = settings.get('tool_configuration', {})
    if canonical(configuration) != canonical(saved):
        raise _failure('identity_conflict', 'tool_configuration')
    public = saved.get('public', {})
    if 'transport_timeout_seconds' in public:
        value = public['transport_timeout_seconds']
        if type(value) is not int or value <= 0:
            raise ValueError('invalid_transport_timeout')
    tools = _construct_tools(store, saved, run_directory=run_directory,
        registry_class=registry_class)
    # Preserve saved caller metadata exactly. The original configured_tools
    # contact-selection route above remains an effective constructor operand;
    # it does not rewrite the authenticated run record or this saved mapping.
    tools.reconstruction_configuration = deepcopy(saved)
    return tools
