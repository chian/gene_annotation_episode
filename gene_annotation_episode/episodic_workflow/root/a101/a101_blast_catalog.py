"""A101 BLAST job catalog selection for the combined registry."""


class A101BlastCatalogMixin:
    def __init__(self, *args, **kwargs):
        self._ncbi_blast_job_resource = False
        super().__init__(*args, **kwargs)

    def configure_blast_execution(self, resources):
        self._ncbi_blast_job_resource = any(
            value.get('kind') == 'api' and value.get('service') == 'ncbi_blast'
            for value in resources.values())

    def catalog(self, scope=None):
        catalog = super().catalog(scope=scope)
        if self._ncbi_blast_job_resource:
            # A101 can hand a durable NCBI job to a separate monitor.
            catalog.pop('public.blast.search', None)
            catalog.pop('public.blast.collect', None)
        return catalog
