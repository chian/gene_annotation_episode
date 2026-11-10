"""Compose the existing axis registries for a shared annotation parent."""
from pathlib import Path

from .a102_tools import A102ToolRegistry
from .a104_tools import A104ToolRegistry
from .a107_tools import A107ToolRegistry
from .a110_tools import A110ToolRegistry


class AllEvidenceToolRegistry(A107ToolRegistry, A102ToolRegistry,
                              A104ToolRegistry, A110ToolRegistry):
    COMPONENT_NATIVE_AXES = ('A107', 'A110')

    def __init__(self, store, *args, **kwargs):
        work = Path(store.path) / 'runs' / 'axis-tools'
        self._ncbi_blast_job_resource = False
        super().__init__(store, *args,
            a107_work_directory=work / 'a107',
            a102_work_directory=work / 'a102',
            a104_work_directory=work / 'a104', **kwargs)

    def configure_blast_execution(self, resources):
        self._ncbi_blast_job_resource = any(
            value.get('kind') == 'api' and value.get('service') == 'ncbi_blast'
            for value in resources.values())

    def catalog(self, scope=None):
        catalog = super().catalog(scope=scope)
        if self._ncbi_blast_job_resource:
            # The combined investigation uses the durable Launch/Monitor/Results
            # contract for NCBI jobs; the ordinary all-in-one call would hold
            # its scientific parent open through every provider poll.
            catalog.pop('public.blast.search', None)
            catalog.pop('public.blast.collect', None)
        return catalog
