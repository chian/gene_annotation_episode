"""One caller-configuration path for ordinary tools, CLI or case harness."""
from copy import deepcopy
from pathlib import Path

from .acquisition import PublicClients
from .tools import ToolRegistry
from .ordinary_execution import OrdinaryExecutionStatistics


def build_tools(store, configuration=None):
    configuration = configuration or {}
    public, local = configuration.get('public', {}), configuration.get('local_tools', {})
    clients = PublicClients(ncbi_email=public.get('ncbi_email'),
        skill_root=Path(public['skill_root']) if public.get('skill_root') else None,
        timeout=public.get('transport_timeout_seconds', 90),
        access_dir=(Path(public['provider_access_dir']).expanduser() if 'provider_access_dir' in public
                    else Path.home()/'.cache'/'gene_annotation_episode'/'provider_access'))
    statistics = (OrdinaryExecutionStatistics(configuration['history'], configuration['resource_id'],
        local.get('native_receipts_dir', store.path/'native-execution-receipts'))
        if 'history' in configuration or 'resource_id' in configuration else None)
    tools = ToolRegistry(store, clients=clients, job_limits=configuration.get('local_jobs'),
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
