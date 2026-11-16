"""Ordinary-tool methods: tool_registry."""
from __future__ import annotations
from contextvars import ContextVar
import json
from pathlib import Path
from typing import Any
from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.local_resources import LocalResources
from gene_annotation_episode.episodic_workflow.root.library.provider_jobs import RemoteSearches
from gene_annotation_episode.episodic_workflow.root.library import read_mapping as mapper
from gene_annotation_episode.document_tools import resource as document_resource
from .library.rna_evidence import local_configuration
from .direct_tool_catalog import DirectToolCatalog
from .direct_tool_execution import DirectToolExecution
from .tool_blast_results import ToolBlastResults
from .tool_chemistry_results import ToolChemistryResults
from .tool_documents import ToolDocuments
from .tool_hmmer_results import ToolHmmerResults
from .tool_invocation_authority import ToolInvocationAuthority
from .tool_literature_assets import ToolLiteratureAssets
from .tool_native_sequence import ToolNativeSequence
from .tool_provider_acquisition import ToolProviderAcquisition
from .tool_read_mapping import ToolReadMapping
from .tool_reference_imports import ToolReferenceImports
from .tool_resource_configuration import ToolResourceConfiguration
from .tool_result_grading import ToolResultGrading
from .tool_rfam_results import ToolRfamResults
from .tool_rna_search import ToolRnaSearch
from .tool_scientific_operations import ToolScientificOperations
from .tool_sequence_operands import ToolSequenceOperands
from .tool_source_publication import ToolSourcePublication

class ToolRegistry(
    DirectToolCatalog,
    DirectToolExecution,
    ToolBlastResults,
    ToolChemistryResults,
    ToolDocuments,
    ToolHmmerResults,
    ToolInvocationAuthority,
    ToolLiteratureAssets,
    ToolNativeSequence,
    ToolProviderAcquisition,
    ToolReadMapping,
    ToolReferenceImports,
    ToolResourceConfiguration,
    ToolResultGrading,
    ToolRfamResults,
    ToolRnaSearch,
    ToolScientificOperations,
    ToolSequenceOperands,
    ToolSourcePublication,
):
    def __init__(self, store: Any, *, clients: PublicClients | None = None,
                 provider_poll_interval_seconds: float = 5,
                 cmsearch_executable: str | Path | None = None, cmsearch_cpu: int | None = None,
                 minimap2_executable: str | Path | None = None, minimap2_cpu: int | None = None,
                 minimap2_cache_dir: str | Path | None = None,
                 pdfinfo_executable: str | Path | None = None,
                 pdftotext_executable: str | Path | None = None,
                 pdftoppm_executable: str | Path | None = None,
                 knowledge_library_directory: str | Path | None = None,
                 job_limits: dict | None = None, native_statistics=None,
                 local_resources: dict | None = None,
                 run_directory: str | Path | None = None):
        if clients is None and run_directory is None:
            raise ValueError('public_client_run_directory_required')
        self.store = store
        self.knowledge_library_directory = (None if knowledge_library_directory is None else
                                            Path(knowledge_library_directory).expanduser().resolve())
        self.local_job_policy = LocalJobPolicy.from_config(job_limits)
        self.local_resources = LocalResources.configured(local_resources)
        if native_statistics is not None:
            from gene_annotation_episode.ordinary_execution import OrdinaryExecutionStatistics
            if type(native_statistics) is not OrdinaryExecutionStatistics:
                raise TypeError('typed_ordinary_execution_statistics_required')
        self.native_statistics = native_statistics
        self.clients = (clients if clients is not None else PublicClients(
            work_dir=Path(run_directory).expanduser().resolve()/'public-client-work'))
        store.db.execute("""CREATE TABLE IF NOT EXISTS tool_operations (
            operation_key TEXT PRIMARY KEY, id TEXT NOT NULL, name TEXT NOT NULL,
            arguments TEXT NOT NULL, scope TEXT NOT NULL, result TEXT NOT NULL)""")
        store.db.commit()
        self.remote_searches = RemoteSearches(store, self.clients, poll_interval_seconds=provider_poll_interval_seconds)
        self._publications = ContextVar("annotation_tool_publications", default=None)
        self._publication_batch = ContextVar("annotation_native_publication_batch", default=None)
        self._mapping_directories = ContextVar("annotation_mapping_directories", default=None)
        self._native_execution_refs = ContextVar('annotation_native_execution_refs', default=None)
        self._grading_failures = ContextVar('annotation_tool_grading_failures', default=None)
        self._permitted_record_refs = ContextVar('annotation_tool_permitted_record_refs', default=None)
        self._current_invocation = ContextVar('annotation_tool_current_invocation', default=None)
        self._protein_structure_configuration = None
        self._flux_balance_configuration = None
        self.ordinary_flux_balance_backend = None
        self._molecular_sequence_configuration = None
        self._molecular_sequence_saved_modes = None
        self.ordinary_molecular_sequence_backend = None
        self._homer_configuration = None
        self._tf_binding_configuration = None
        self._protease_kinetics_configuration = None
        self._protein_conservation_configuration = None
        self._protein_phylogeny_configuration = None
        self._somatic_variant_configuration = None
        self._esm_gene_embedding_configuration = None
        self._molecular_sequence_results_by_run = {}
        self._macs2_peak_capture_readers_by_run = {}
        self._execution_owners_by_run = {}
        self._protein_structure_input_authority = ContextVar(
            'annotation_tool_protein_structure_input_authority', default=None)
        self.cmsearch_configuration = local_configuration(executable=cmsearch_executable, cpu=cmsearch_cpu,
            job_limits=self.local_job_policy.to_dict())
        self.minimap2_configuration = mapper.local_configuration(executable=minimap2_executable,
            cpu=minimap2_cpu, cache_dir=(store.path/"cache"/"minimap2"
                if minimap2_cache_dir is None else minimap2_cache_dir), job_limits=self.local_job_policy.to_dict())
        self.pdf_executables = {name: document_resource(path)["executable"] for name, path in
            (("pdfinfo", pdfinfo_executable), ("pdftotext", pdftotext_executable), ("pdftoppm", pdftoppm_executable))}

    def resource_binding(self) -> dict:
        """Current caller-selected resources; individual measurements own provenance."""
        return {"local_jobs": self.local_job_policy.to_dict(),
                "local_resources": self.local_resources.as_record(),
                **({'flux_balance_tools': json.loads(canonical(self._flux_balance_configuration))}
                   if self._flux_balance_configuration is not None else {}),
                **({'protein_structure_tools': json.loads(canonical(self._protein_structure_configuration))}
                   if self._protein_structure_configuration is not None else {}),
                **({'native_molecular_sequence_tools': json.loads(canonical(self._molecular_sequence_configuration))}
                   if self._molecular_sequence_configuration is not None else {}),
                **({'molecular_sequence_saved_modes': True}
                   if self._molecular_sequence_saved_modes is True else {}),
                **({'homer_tools': json.loads(canonical(self._homer_configuration))}
                   if self._homer_configuration is not None else {}),
                **({'knowledge_library_directory': str(self.knowledge_library_directory)}
                   if self.knowledge_library_directory is not None else {}),
                **({'ordinary_execution_statistics': self.native_statistics.as_record()}
                   if self.native_statistics is not None else {}),
                "cmsearch": local_configuration(executable=self.cmsearch_configuration["executable"],
                                               cpu=self.cmsearch_configuration["cpu"], job_limits=self.local_job_policy.to_dict()),
                "pdf_tools": {name: document_resource(path) for name, path in self.pdf_executables.items()},
                "minimap2": mapper.local_configuration(**{key: self.minimap2_configuration[key]
                    for key in ("executable", "cpu", "cache_dir")}, job_limits=self.local_job_policy.to_dict())}

