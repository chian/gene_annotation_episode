"""Ordinary-tool methods: tool_provider_acquisition."""
from __future__ import annotations
import asyncio
from typing import Any
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.episodic_workflow.root.library import blast_search as blast
from gene_annotation_episode.literature_assets import BUCKET

class ToolProviderAcquisition:
    def _acquisition_diagnostic(self, error: AcquisitionError) -> str:
        snapshot = error.snapshot
        details = {"code": error.code, "phase": error.phase, "details": error.diagnostic}
        if snapshot:
            details.update(content_ref=self.store.artifact(snapshot.content, snapshot.media_type),
                url=snapshot.url, request=snapshot.request, transport=snapshot.transport)
        return self.store.artifact(canonical(details), "application/json")

    async def _alphafold_file_async(self, args, *, authority):
        from .library.alphafold_acquisition_host import prepare_alphafold_file
        selection = prepare_alphafold_file(self, args, authority=authority)
        snapshot = await self._acquire_response_async('public.alphafold.file',
            self.clients.alphafold_structure_file,
            {'arguments': args, 'association': selection['association']})
        return {'snapshot': snapshot, 'selection': selection}

    async def _sra_file_async(self, args, *, authority, operation_key):
        from gene_annotation_episode.ncbi_sra_acquisition import TOOL, sra_file_request_spec
        from gene_annotation_episode.ncbi_sra_acquisition_host import prepare_sra_file
        prepared = prepare_sra_file(self, args, authority=authority, operation_key=operation_key)
        specification = sra_file_request_spec(args, selection=prepared['selection'])
        snapshot = await self._acquire_response_async(TOOL, self.clients._http,
            specification)
        return {'snapshot': snapshot, 'prepared': prepared}

    async def _ensembl_request_async(self, args, *, authority):
        from gene_annotation_episode.ensembl_acquisition_host import prepare_ensembl_request
        try:
            prepared = prepare_ensembl_request(self, args, authority=authority)
        except ValueError as error:
            if isinstance(error, ContractError):
                raise
            raise ContractError(str(error)) from error
        snapshot = await self._acquire_response_async('public.ensembl.request',
            self.clients.ensembl_request, {'arguments': args})
        return {'snapshot': snapshot, 'prepared': prepared}

    async def _encode_request_async(self, args, *, authority):
        from .library.encode_tools import prepare_encode_request
        selection = prepare_encode_request(self, args, authority=authority)
        function, arguments = self._acquisition_request('public.encode', args, None)
        snapshot = await self._acquire_response_async('public.encode', function,
            {**arguments, 'selection': selection})
        return {'snapshot': snapshot, 'selection': selection}

    async def _acquire_async(self, name: str, args: dict, scope: dict | None,
                             operation_key: str) -> SourceSnapshot | None:
        if name == "public.blast.search":
            row = self._check_sequence_operand(args["subject_ref"], scope)
            model = "protein" if blast.PROGRAM_UNITS[args["program"]][0] == "aa" else "dna"
            sequence = self._sequence(row["id"], molecule_model=model)
            return await self.remote_searches.search(operation_key, subject_ref=row["id"],
                query_fasta=f">{row['id']}\n{sequence}", algorithm=args["program"], database=args["database"],
                parameters={"hitlist_size": args.get("hitlist_size", 50)}, provider="blast")
        if name == "public.blast.collect":
            job = self.remote_searches.describe(args["job_ref"])
            if job["request"].get("provider", "hmmer") != "blast":
                raise ContractError("provider_job_does_not_belong_to_blast")
            self._check_sequence_operand(job["request"]["subject_ref"], scope)
            return await self.remote_searches.collect(args["job_ref"])
        if name == "public.search.jobs":
            return None
        if name in {"public.rfam.search", "public.rfam.collect"}:
            raise ContractError("rfam_requires_api_execution_episode")
        function, arguments = self._acquisition_request(name, args, scope)
        return await self._acquire_response_async(name, function, arguments)

    async def _acquire_response_async(self, name, function, arguments):
        from gene_annotation_episode.molecular_provider_acquisition import OPERATIONS as MOLECULAR_PROVIDER_OPERATIONS
        from gene_annotation_episode.variant_provider_acquisition import OPERATIONS as VARIANT_PROVIDER_OPERATIONS
        try:
            return await asyncio.to_thread(function, **arguments)
        except AcquisitionError as error:
            # Retain the actual selected response even when its HTTP status or
            # captured body is partial. A transport failure without a response
            # remains the existing acquisition diagnostic path.
            if ((name in {"public.rcsb.entry", "public.rcsb.file", "public.emdb.entry", "public.alphafold.prediction", "public.alphafold.file", "public.ucsc.request", "public.ensembl.request", "public.ncbi.entrez", "public.ncbi.geo", "public.ncbi.sra.file", "public.jaspar", "public.screen"}
                    or name in MOLECULAR_PROVIDER_OPERATIONS or name in VARIANT_PROVIDER_OPERATIONS)
                    and isinstance(error.snapshot, SourceSnapshot)
                    and isinstance(error.snapshot.transport, dict)
                    and type(error.snapshot.transport.get("status")) is int):
                return error.snapshot
            raise

    def _acquisition_request(self, name: str, args: dict, scope: dict | None) -> tuple[Any, dict]:
        from gene_annotation_episode.experimental_database_acquisition import OPERATIONS as EXPERIMENT_DATABASE_TOOLS, request as experimental_database_request
        if name in EXPERIMENT_DATABASE_TOOLS:
            return experimental_database_request, {'client': self.clients, 'operation': name, 'arguments': args}
        if name == 'public.literature.sequence_identity':
            from gene_annotation_episode.literature_sequence_discovery import identity_request
            return identity_request(self, args, scope)
        from gene_annotation_episode.molecular_provider_acquisition import OPERATIONS as MOLECULAR_PROVIDER_OPERATIONS
        from gene_annotation_episode.variant_provider_acquisition import OPERATIONS as VARIANT_PROVIDER_OPERATIONS, provider_request_spec as variant_provider_request_spec
        if name in VARIANT_PROVIDER_OPERATIONS:
            return self.clients._http, variant_provider_request_spec(name, args)
        if name == "public.ncbi.entrez":
            from gene_annotation_episode.ncbi_entrez_tools import request_ncbi_entrez
            return request_ncbi_entrez, {"client": self.clients, "arguments": args}
        if name == "public.ncbi.geo":
            from gene_annotation_episode.geo_tools import request_geo
            return request_geo, {"client": self.clients, "arguments": args}
        if name == "public.jaspar":
            from gene_annotation_episode.jaspar_tools import request_jaspar
            return request_jaspar, {"client": self.clients, "arguments": args}
        if name == "public.screen":
            from gene_annotation_episode.screen_tools import request_screen
            return request_screen, {"client": self.clients, "arguments": args}
        if name == "public.encode":
            from .library.encode_tools import request_encode
            return request_encode, {"client": self.clients, "arguments": args}
        if name == "public.ucsc.request":
            return self.clients.ucsc_request, {"arguments": args}
        if name == "public.ensembl.request":
            return self.clients.ensembl_request, {"arguments": args}
        if name in MOLECULAR_PROVIDER_OPERATIONS:
            return self.clients.molecular_provider_request, {'operation': name, 'arguments': args}
        if name == "public.rcsb.entry":
            return self.clients.rcsb_entry, args
        if name == "public.rcsb.file":
            return self.clients.rcsb_structure_file, args
        if name == "public.emdb.entry":
            return self.clients.emdb_entry, args
        if name == "public.alphafold.prediction":
            return self.clients.alphafold_prediction, args
        if name == "public.uniprot.search":
            return self.clients.uniprot_search, args
        if name == "public.rhea.search":
            return self.clients.rhea_search, args
        if name == "public.rhea.reaction":
            return self.clients.rhea_reaction, args
        if name == "public.chebi.search":
            return self.clients.chebi_search, args
        if name == "public.chebi.compound":
            return self.clients.chebi_compound, args
        if name == "public.rfam.model":
            return self.clients.rfam_model, args
        if name == "public.pmc.versions":
            return self.clients.pmc_versions, args
        if name == "public.pmc.files":
            selected = self.store._require(args["version_ref"], {"pmc_version"})
            return self.clients.pmc_files, {"prefix": selected["prefix"],
                **({"continuation_token": args["continuation_token"]} if "continuation_token" in args else {})}
        if name == "public.pmc.asset":
            asset = self.store._require(args["asset_ref"], {"pmc_asset", "pmc_object"})
            selected = self.store._require(asset["version_ref"], {"pmc_version"})
            uri = asset.get("original_uri") or "s3://" + BUCKET + "/" + asset["object_key"]
            return self.clients.pmc_asset, {"original_uri": uri, "prefix": selected["prefix"]}
        if name == "public.uniprot.record":
            return self.clients.uniprot_record, args
        if name == "public.ncbi.search":
            return self.clients.ncbi_search, args
        if name == "public.ncbi.sequence":
            return self.clients.ncbi_sequence, args
        if name == "public.taxonomy":
            return self.clients.taxonomy, args
        if name == "public.literature.search":
            return self.clients.literature_search, args
        if name == "public.literature.read":
            return self.clients.literature_read, args
        raise ContractError("unimplemented_public_acquisition")

