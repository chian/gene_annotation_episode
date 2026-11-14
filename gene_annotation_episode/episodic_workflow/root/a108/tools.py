"""Private A108 source acquisition, document access and source publication."""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from importlib.metadata import version
import inspect
import json
import hashlib
import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import ParseError

from .acquisition import AcquisitionError, PublicClients, SourceSnapshot, article_details, parse_genbank
from .api_error_feedback import api_error_feedback, api_error_response
from .domain import REF, REFS, RECORD_SCHEMAS, ContractError, canonical, identity, obj, validate_schema
from .local_jobs import LocalJobPolicy, run_local_job_async, run_cancellable_native
from .local_resources import LocalResources
from .sequence_views import VERSION as VIEW_VERSION, view_sequence
from . import library_targets as libraries
from . import materials_packing as packing
from .source_bytes import artifact_file, artifact_path, source_window
from .source_locations import locate as locate_source, locate_schema, received_source as received_location_source
from .document_tools import (DocumentOutput, archive_extract, archive_inventory,
                             pdf_native, resource as document_resource)
from .spreadsheet_tools import xlsx_native, VERSION as XLSX_VERSION
from .literature_assets import (PmcFiles, advertised_asset, metadata_assets,
                                parse_listing, version as pmc_version, BASE_URL, BUCKET)
from .image_evidence import (prepare_image, visual_input,
                             resolve_image_input as resolve_selected_image)
def number(value: float, unit_ref: str | None = None) -> dict:
    return {"type": "number", "value": value, "unit_ref": unit_ref}


def enum(value: str) -> dict:
    return {"type": "enum", "value": value}


def ref(value: str) -> dict:
    return {"type": "reference", "ref": value}


def measurements(**values: dict) -> list[dict]:
    return [{"name": key, "value": value} for key, value in values.items()]


INTEGER = {"type": "integer", "minimum": 0}
POSITIVE = {"type": "integer", "minimum": 1}
TEXT = {"type": "string", "minLength": 1}


class ToolRegistry:
    def workflow_services(self, workflow):
        from .episode_services import WorkflowServices
        return WorkflowServices(workflow)

    def __init__(self, store: Any, *, clients: PublicClients | None = None,
                 pdfinfo_executable: str | Path | None = None,
                 pdftotext_executable: str | Path | None = None,
                 pdftoppm_executable: str | Path | None = None,
                 knowledge_library_directory: str | Path | None = None,
                 job_limits: dict | None = None, native_statistics=None,
                 local_resources: dict | None = None):
        self.store = store
        self.knowledge_library_directory = (None if knowledge_library_directory is None else
                                            Path(knowledge_library_directory).expanduser().resolve())
        self.local_job_policy = LocalJobPolicy.from_config(job_limits)
        self.local_resources = LocalResources.configured(local_resources)
        if native_statistics is not None:
            from .ordinary_execution import OrdinaryExecutionStatistics
            if type(native_statistics) is not OrdinaryExecutionStatistics:
                raise TypeError('typed_ordinary_execution_statistics_required')
        self.native_statistics = native_statistics
        self.clients = clients or PublicClients()
        store.db.execute("""CREATE TABLE IF NOT EXISTS tool_operations (
            operation_key TEXT PRIMARY KEY, id TEXT NOT NULL, name TEXT NOT NULL,
            arguments TEXT NOT NULL, scope TEXT NOT NULL, result TEXT NOT NULL)""")
        store.db.commit()
        self._publications = ContextVar("annotation_tool_publications", default=None)
        self._publication_batch = ContextVar("annotation_native_publication_batch", default=None)
        self._mapping_directories = ContextVar("annotation_mapping_directories", default=None)
        self._native_execution_refs = ContextVar('annotation_native_execution_refs', default=None)
        self._grading_failures = ContextVar('annotation_tool_grading_failures', default=None)
        self._permitted_record_refs = ContextVar('annotation_tool_permitted_record_refs', default=None)
        self._current_invocation = ContextVar('annotation_tool_current_invocation', default=None)
        self.pdf_executables = {name: document_resource(path)["executable"] for name, path in
            (("pdfinfo", pdfinfo_executable), ("pdftotext", pdftotext_executable), ("pdftoppm", pdftoppm_executable))}




    def resource_binding(self) -> dict:
        return {"local_jobs": self.local_job_policy.to_dict(),
            "local_resources": self.local_resources.as_record(),
            **({'knowledge_library_directory': str(self.knowledge_library_directory)}
                if self.knowledge_library_directory is not None else {}),
            **({'ordinary_execution_statistics': self.native_statistics.as_record()}
                if self.native_statistics is not None else {}),
            "pdf_tools": {name: document_resource(path) for name, path in self.pdf_executables.items()}}

    @property
    def _written(self) -> list[str]:
        publications = self._publications.get()
        if publications is None:
            raise ContractError("publication_outside_tool_operation")
        return publications


    @contextmanager
    def current_invocation(self, context, *, tool_name, arguments, operation_key):
        """Host-only current action port; each participating tool authenticates it."""
        token = self._current_invocation.set((context, tool_name, arguments, operation_key))
        try:
            yield
        finally:
            self._current_invocation.reset(token)


    def catalog(self, scope: dict | None = None) -> dict[str, dict]:
        from .literature_sequence_discovery import identity_schema, references_schema
        from .source_sequences import scan_schema
        from .ncbi_entrez_tools import ncbi_entrez_tool_contract
        definitions = {
            "state.query": ("Read an exact page of typed scientific records, current revisions, or records referring to actual references. Follow the returned next_query for the same selection and order. Exact refs is a separate mode and cannot be combined with page selectors.", obj({
                "kind": {"enum": list(RECORD_SCHEMAS) + ["subject"]}, "offset": INTEGER,
                "limit": POSITIVE, "refs": {**REFS,
                    "description": "Exact reference mode: supply refs alone, including an empty array for no records. Omit kind, offset, limit, current_only and references in this mode."},
                "current_only": {"type": "boolean"},
                "references": {"type": "array", "items": REF, "minItems": 1,
                    "description": "Select records that refer to any supplied ID through reference fields or provenance anchors. This does not match a record's own ID; to read known records themselves, supply refs alone instead."}}, required=[])),
            "source.read": ("Read a bounded UTF-8 byte window from an actual source. Choose original for retained source bytes, including XML tables/headings omitted by a paragraph projection; text selects that projection when available. Explicit stdout/stderr select retained native stream bytes when present, without falling back to another representation. Returned artifact/offsets support exact anchors.",
                obj({"source_ref": REF, "offset": INTEGER, "limit": POSITIVE,
                     "representation": {"enum": ["text", "original", "stdout", "stderr"]}}, ["source_ref"])),
            "source.locate": ("Locate an exact supplied literal quote in an explicitly received original or text source representation. Return UTF-8 byte witnesses, unchanged neighboring context and bounded match continuation. Multiple occurrences remain separate. No normalization, scientific interpretation, measurement parsing or evidence credit is performed; no literal match means only no match in the examined bytes.", locate_schema()),
            "image.view": ("Inspect one explicitly selected frame of a registered scientific image. The next reasoning call receives its actual pixels and exact source/frame metadata. Stored axes are preserved; no contrast adjustment, resizing, interpretation or annotation is performed. An optional RGB conversion is explicit and recorded; original bytes remain intact.",
                obj({"source_ref": REF, "frame": INTEGER,
                     "colour_conversion": {"enum": ["preserve", "rgb"]}}, ["source_ref"])),
            "public.pmc.versions": ("List one actual public PMC cloud version page. No version is chosen as latest/preferred; source versions can differ in manuscript status and can change in place.",
                obj({"pmcid": {"type": "string", "pattern": "^PMC[0-9]+$"}, "continuation_token": TEXT}, ["pmcid"])),
            "public.pmc.files": ("Read the selected advertised version's actual file inventory and its listed JSON metadata. Returns reusable listed-object/advertised-asset IDs; optional metadata failure preserves listed files. Choose a version ID, not a URL or guessed filename.",
                obj({"version_ref": REF, "continuation_token": TEXT}, ["version_ref"])),
            "public.pmc.asset": ("Acquire exactly one selected advertised/listed PMC asset ID. Preserve actual HTTP bytes, original advertisement and checksums; source content is evidence, not target annotation.", obj({"asset_ref": REF})),
            "source.archive.members": ("Inventory one page of an actual ZIP/TAR source. Member IDs preserve ordinal identity, including duplicate names; no members are extracted or selected for you.",
                obj({"source_ref": REF, "offset": INTEGER, "limit": POSITIVE}, ["source_ref"])),
            "source.archive.extract": ("Extract exactly one inventoried regular member to a source artifact; never follow a member's host path or link. Original archive and member identity remain attached.", obj({"member_ref": REF})),
            "source.xlsx.sheets": ("Read the actual sheet names, relationship keys and package parts of a retained XLSX source. No sheet or biological interpretation is selected for you.", obj({"source_ref": REF})),
            "source.xlsx.rows": ("Read a selected page of actual XLSX rows, optionally matching literal cell values. Select sheet_key from source.xlsx.sheets; row offsets count matching rows, while returned row numbers/cell addresses retain native identity. Header row is caller-selected or null. Original numeric/date lexical values, styles, formulas and caches remain distinct; no formula is recalculated or biology inferred.",
                obj({"source_ref": REF, "sheet_key": TEXT, "offset": INTEGER, "limit": INTEGER,
                    "header_row": {"type": ["integer", "null"], "minimum": 1},
                    "where": {**obj({"column": {"type": ["string", "null"], "pattern": "^[A-Z]+$"},
                        "match": {"enum": ["equals", "contains"]}, "value": TEXT,
                        "case_sensitive": {"type": "boolean"}}), "type": ["object", "null"]}})),
            "source.pdf.info": ("Read native PDF information and physical page count for a selected actual source; no biological interpretation.", obj({"source_ref": REF})),
            "source.pdf.text": ("Extract a selected physical PDF page or contiguous page range as a reusable UTF-8 text derivative. page is the first page; optional last_page is inclusive and defaults to page. Use source.pdf.info for the physical page count, then source.locate on the extracted text to find a section without guessing pages. Native page breaks and the selected range are retained. Byte offsets refer to this text derivative, not the PDF. No OCR or interpretation is performed.",
                obj({"source_ref": REF, "page": POSITIVE, "last_page": POSITIVE,
                    "layout": {"enum": ["reading_order", "layout", "raw"]}}, ["source_ref", "page"])),
            "source.pdf.page": ("Render one explicitly selected physical PDF page as a reusable PNG source. Rendering does not by itself supply image input to a model or interpret a figure.",
                obj({"source_ref": REF, "page": POSITIVE, "dpi": {"type": "number", "exclusiveMinimum": 0}}, ["source_ref", "page"])),
            "public.uniprot.search": ("Acquire one public reference page. Source annotations are not target annotations.",
                obj({"query": TEXT, "size": {"type": "integer", "minimum": 1, "maximum": 500}, "cursor": TEXT}, ["query"])),
            "public.uniprot.record": ("Acquire and pin an actual reference protein, its annotation, source features and evidence provenance.", obj({"accession": TEXT})),
            "public.ncbi.search": ("Search one page of a named NCBI collection for selected references, taxa or sample context.",
                obj({"database": {"enum": ["protein", "nuccore", "assembly", "taxonomy", "biosample", "bioproject", "pubmed"]},
                     "term": TEXT, "size": POSITIVE, "offset": INTEGER}, ["database", "term"])),
            "public.ncbi.sequence": ("Acquire an external GenBank/GenPept sequence and its original feature context; optional nucleotide interval uses zero-based half-open coordinates.",
                obj({"accession": TEXT, "database": {"enum": ["protein", "nuccore"]}, "start": INTEGER, "end": POSITIVE}, ["accession", "database"])),
            "public.taxonomy": ("Retrieve a taxon's source lineage record; it does not assign that taxon to the target.", obj({"taxon_id": POSITIVE})),
            "public.literature.search": ("Acquire one literature search page. Read the actual source before extracting biological evidence.",
                obj({"query": TEXT, "size": POSITIVE, "cursor": TEXT}, ["query"])),
            "public.literature.read": ("Acquire an actual open article, an ordered paragraph projection and separate cited-publication metadata. Bibliography identifiers and paragraph links support further source discovery; they do not identify the acquired article or establish a cited experiment's result. Read the retained original XML with source.read representation=original for tables, headings and other omitted elements.", obj({"pmcid": TEXT})),
        }
        result = {name: {"description": description, "input_schema": schema}
                  for name, (description, schema) in definitions.items()}
        result['public.literature.sequence_identity'] = {
            'description': 'Find publication leads from a supplied protein sequence: retrieve one UniProtKB checksum-search page and verify each complete residue string. Return all equal records on the page, names, organisms, citation counts and explicit continuation. The optional reviewed filter selects database curation status. These are source identities and discovery metadata; experimental evidence requires reading the actual publications.',
            'input_schema': identity_schema()}
        result['source.sequence.references'] = {
            'description': 'Read a page of publication identifiers, titles and reported citation scopes from a received sequence-identity response. Reverify full sequence equality for the selected record. Citation metadata supplies leads; it does not establish experimental results.',
            'input_schema': references_schema()}
        result['source.sequence.scan'] = {
            'description': 'Recognize candidate protein sequence blocks in received source text/XML/HTML, preserving original UTF-8 positions. Normalize case, whitespace, numbering and soft hyphens; report exact containment, extra residues and literal differences. For numbered GenBank/GenPept blocks, include the ORIGIN marker and contiguous residue rows in the selected window. Hard hyphens remain explicit, with conditional correspondence, until their byte offsets are selected as formatting_hyphen_offsets after inspecting the layout. A document boundary may require an overlapping window. No biological gaps, tags or substitutions are silently removed.',
            'input_schema': scan_schema()}
        # Inform the owning Episode about actual configuration; the catalog
        # neither selects another tool nor introduces scientific permission.
        for name, native in (("source.pdf.info", "pdfinfo"), ("source.pdf.text", "pdftotext"), ("source.pdf.page", "pdftoppm")):
            result[name]["configuration"] = {**document_resource(self.pdf_executables[native]), "job_limits": self.local_job_policy.to_dict()}
        for name in ("source.xlsx.sheets", "source.xlsx.rows"):
            result[name]["configuration"] = {"adapter_version": XLSX_VERSION,
                "job_limits": self.local_job_policy.to_dict(), "execution": "isolated_store_free_worker"}
            if self.native_statistics is not None:
                result[name]['configuration']['timing_statistics'] = self.native_statistics.as_record()
        if self.native_statistics is not None:
            result['execution.estimate'] = {'description':
                'Obtain recorded duration expectations before a proposed workbook selection. Uses the same operands, actual settings and caller resource as execution. Creates no native job or scientific evidence; missing history stays unknown. This is an optional information tool, not a scheduling or continuation decision.',
                'input_schema': {'anyOf': [obj({'tool': {'const': name},
                    'arguments': result[name]['input_schema']})
                    for name in ('source.xlsx.sheets', 'source.xlsx.rows')]}}
        result["public.ncbi.entrez"] = ncbi_entrez_tool_contract()
        return result



    def _check_target(self, reference: str, scope: dict | None, *, footprint: list[dict] | None = None) -> dict:
        row = self.store.get(reference)
        footprint = self.store.coverage(reference) if footprint is None else footprint
        normalized = self.store.validate_scope(scope)
        allowed = set(normalized["subject_refs"])
        if not footprint or any(item["target_ref"] not in allowed for item in footprint):
            raise ContractError("subject_outside_assigned_scope")
        if not self.store.scope_covers(footprint, normalized):
            raise ContractError("requested_measurement_outside_assigned_segments_or_members"
                if any("member_ref" in span for span in footprint)
                else "requested_measurement_outside_assigned_segments")
        return row


    def _sequence(self, reference: str, *, molecule_model: str | None = None) -> str:
        row = self.store.get(reference)
        if row.get("record_type") == "read_subject":
            member = self.store.get(row["member_ref"])
            return packing.component_window(self.store, member, "sequence", 0, row["length"]).decode("ascii")
        if libraries.is_library(row):
            raise ContractError("library_is_not_a_sequence_operand")
        if row.get("sequence_ref"):
            return self.store.get_artifact(row["sequence_ref"]).decode("ascii")
        if row.get("record_type") == "feature":
            parent = self._sequence(row["subject_ref"], molecule_model=molecule_model)
            sequence = "".join(parent[item["start"]:item["end"]] for item in row["segments"])
            if row["strand"] == "-":
                known_model = self.store.subject_molecule(row["subject_ref"])
                model = known_model if known_model != "unspecified" else molecule_model
                try:
                    return view_sequence(sequence, molecule=model, orientation="reverse_complement")["sequence"]
                except ValueError as error:
                    raise ContractError(str(error)) from error
            return sequence
        raise ContractError("referenced_record_has_no_sequence")


    def _check_sequence_operand(self, reference: str, scope: dict | None,
                                *, footprint: list[dict] | None = None) -> dict:
        """Resolve scientific sequence material without turning it into a target.

        Original-input work retains its assigned account_context bounds. Registered
        external evidence and its derivatives have no input credit footprint;
        their absence of one is not a prohibition on investigating the source.
        """
        row = self.store.get(reference)
        if row["record_type"] not in {"input", "feature", "product", "reference", "read_subject"}:
            raise ContractError("sequence_operand_required")
        self.store.subject_length(reference)
        self.store.validate_scope(scope)
        if self.store.roots(reference):
            return self._check_target(reference, scope, footprint=footprint)
        return row


    def _source(self, provider: str, body: Any, *, snapshot: SourceSnapshot | None = None,
                text: str | None = None, accession: str | None = None, software_version: str | None = None,
                parent_source_refs: list[str] | None = None,
                stdout_ref: str | None = None, stderr_ref: str | None = None,
                auxiliary_artifact_refs: list[str] | None = None,
                operand_refs: list[str] | None = None, query_selection_ref: str | None = None,
                publication_identifiers: list[dict] | None = None) -> dict:
        artifact = self.store.artifact(snapshot.content if snapshot else canonical(body),
                                       snapshot.media_type if snapshot else "application/json")
        request = None
        if snapshot:
            request = self.store.artifact(canonical({"request": snapshot.request, "transport": snapshot.transport}), "application/json")
            if software_version is None and provider != 'public.ncbi.entrez':
                if snapshot.service == "uniprot":
                    # Source custody precedes projection, including an absent or
                    # malformed transport envelope. Its complete original value
                    # remains in request_ref; the old version label is optional.
                    transport = snapshot.transport if isinstance(snapshot.transport, dict) else {}
                    response = transport.get("response")
                    headers = (response.get("headers", transport.get("headers"))
                               if isinstance(response, dict) else transport.get("headers"))
                    candidate = headers.get("x-uniprot-release") if isinstance(headers, dict) else None
                    try:
                        validate_schema(candidate, RECORD_SCHEMAS["source"]["properties"]["version"])
                    except ContractError:
                        candidate = None
                    software_version = candidate
                elif snapshot.service not in {"rcsb_pdb", "alphafold", "emdb", "string", "kegg", "reactome", "quickgo", "pubchem", "hpa", "ucsc", "ensembl", "eva", "gnomad"}:
                    details = snapshot.transport.get("job_details") or {}
                    database = details.get("database")
                    software_version = (database.get("version") if isinstance(database, dict) else None) or snapshot.transport.get("response", {}).get("headers", {}).get("x-uniprot-release")
        return self._put("source", {
            "provider": provider, "accession": accession, "uri": snapshot.url if snapshot else None,
            "artifact_ref": artifact, "text_ref": self.store.artifact(text, "text/plain") if text is not None else None,
            "request_ref": request, "version": software_version,
            "retrieved_at": snapshot.retrieved_at if snapshot else datetime.now(timezone.utc).isoformat(),
            **({"parent_source_refs": parent_source_refs} if parent_source_refs is not None else {}),
            **({"stdout_ref": stdout_ref} if stdout_ref is not None else {}),
            **({"stderr_ref": stderr_ref} if stderr_ref is not None else {}),
            **({"auxiliary_artifact_refs": auxiliary_artifact_refs} if auxiliary_artifact_refs is not None else {}),
            **({"operand_refs": operand_refs} if operand_refs is not None else {}),
            **({"query_selection_ref": query_selection_ref} if query_selection_ref is not None else {}),
            **({'publication_identifiers': publication_identifiers} if publication_identifiers else {}),
        }, origin="external" if snapshot else "tool")


    def _observation(self, kind: str, subjects: list[str], source: dict, values: list[dict],
                     *, references: list[str] | None = None, dependencies: list[str] | None = None,
                     operand_intervals: list[dict] | None = None) -> dict:
        return self._put("observation", {"kind": kind, "subject_refs": subjects,
            "source_subject_refs": references or [], "source_ref": source["id"], "measurements": values,
            "dependencies": dependencies or [], "anchor": None,
            "operand_intervals": operand_intervals}, origin="tool")


    def _put(self, kind: str, record: dict, **kwargs: Any) -> dict:
        result = self.store.put(kind, record, **kwargs)
        self._written.append(result["id"])
        return result


    def _begin_publication_batch(self, *, failures: bool = False) -> dict:
        """Declare generated publication metadata, never a scientific verdict.

        Mutable counters belong to this selected operation. Keeping the same
        declaration until _save also preserves truthful partial-publication
        counts when a later native row fails.
        """
        batch = {"representation": "native_publications_v1", "published_rows_total": 0,
                 "failure_rows_total": 0 if failures else None, "observation_query": None}
        self._publication_batch.set(batch)
        return batch


    @staticmethod
    def _batch_observations(batch: dict, source_ref: str) -> None:
        batch["observation_query"] = {"kind": "observation", "references": [source_ref], "offset": 0}


    def execute(self, name: str, args: dict, *, scope: dict | None = None,
                operation_key: str | None = None, permitted_record_refs=None) -> dict:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.execute_async(name, args, scope=scope, operation_key=operation_key,
                                                  permitted_record_refs=permitted_record_refs))
        raise ContractError("use_execute_async_in_running_event_loop")


    def _check_source_bytes(self, name, arguments):
        """Apply the finite Source/File receipt policies before byte tools."""
        if name in {'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.archive.members',
                'source.xlsx.sheets', 'source.xlsx.rows', 'source.pdf.info',
                'source.pdf.text', 'source.pdf.page', 'image.view'}:
            source = self.store._require(arguments['source_ref'], {'source'})
            if name in {'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references'}:
                from .source_bytes import source_window_selection
                representation = 'original' if name == 'source.sequence.references' else arguments.get('representation', 'text')
                artifact_ref, _, _ = source_window_selection(source, representation)
            else:
                artifact_ref = source['artifact_ref']
        else:
            return
        permitted = self._permitted_record_refs.get()
        if permitted is not None and source['id'] not in permitted:
            raise ContractError('source_bytes_not_received')



    async def execute_async(self, name: str, args: dict, *, scope: dict | None = None,
                            operation_key: str | None = None, permitted_record_refs=None) -> dict:
        # Bind source readers to this exact host action's receipts. Scientific
        # dispatch and ordinary annotation dispatch use the same readers; an
        # omitted dispatch keyword must not discard their received-input port.
        # Keep an explicitly selected subset, and never infer access for an
        # unbound/manual call or for a different nested operation.
        if permitted_record_refs is None and name in {
                'source.locate', 'source.sequence.scan',
                'source.sequence.references'}:
            invocation = self._current_invocation.get()
            if (invocation is not None and operation_key is not None
                    and invocation[1:] == (name, args, operation_key)
                    and invocation[0].scope == scope):
                permitted_record_refs = tuple(invocation[0].received_record_refs)
        if (permitted_record_refs is not None and (not isinstance(permitted_record_refs, (list, tuple))
                or any(not isinstance(ref, str) or not ref for ref in permitted_record_refs))):
            raise ContractError('explicit_permitted_record_refs_required')
        if name == 'source.locate':
            try:
                canonical(args)
            except (TypeError, ValueError):
                # Non-JSON operands cannot have a canonical durable identity.
                return {'status': 'invalid', 'operation_ref': None, 'record_refs': [],
                    'changed_record_refs': [], 'result': None, 'feedback': {
                        'category': 'arguments_or_reference', 'code': 'source_location_arguments_not_json'}}
        token = self._publications.set([])
        batch_token = self._publication_batch.set(None)
        directories = self._mapping_directories.set([])
        native_receipts = self._native_execution_refs.set([])
        grading_failures = self._grading_failures.set([])
        permitted = self._permitted_record_refs.set(
            None if permitted_record_refs is None else tuple(permitted_record_refs))
        try:
            return await self._execute_operation_async(name, args, scope=scope, operation_key=operation_key)
        finally:
            import shutil
            for directory in self._mapping_directories.get():
                shutil.rmtree(directory)
            self._mapping_directories.reset(directories)
            self._native_execution_refs.reset(native_receipts)
            self._grading_failures.reset(grading_failures)
            self._permitted_record_refs.reset(permitted)
            self._publications.reset(token)
            self._publication_batch.reset(batch_token)


    async def _execute_operation_async(self, name: str, args: dict, *, scope: dict | None = None,
                                       operation_key: str | None = None) -> dict:
        operation_key = operation_key or identity("manual_operation", {"name": name, "args": args,
                                                "time": datetime.now(timezone.utc).isoformat()})
        ordinary_data_getters = {"public.ncbi.entrez"}
        getter_failure_codes, getter_validators, getter_source_providers = {}, {}, {}
        saved = self.store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (operation_key,)).fetchone()
        if saved:
            if saved["name"] != name or saved["arguments"] != canonical(args) or saved["scope"] != canonical(scope):
                raise ContractError("operation_key_reused_for_different_work")
            try:
                if json.loads(saved['result']).get('status') in {'completed', 'partial'}:
                    self._check_source_bytes(name, args)
                    if name in {'public.literature.sequence_identity', 'source.sequence.scan', 'source.sequence.references'}:
                        from .literature_sequence_discovery import protein_operand
                        protein_operand(self, args['subject_ref'], scope)
                    if name in {'source.sequence.scan', 'source.sequence.references'}:
                        received_location_source(self.store, args['source_ref'],
                            args.get('representation', 'original'),
                            permitted_inputs=self._permitted_record_refs.get(), scope=scope)
            except ContractError as error:
                return {'status': 'invalid', 'operation_ref': saved['id'], 'record_refs': [],
                    'changed_record_refs': [], 'result': None,
                    'feedback': {'category': 'arguments_or_reference', 'code': str(error)}}
            if name == 'source.locate' and json.loads(saved['result'])['status'] == 'completed':
                try:
                    artifact = received_location_source(self.store, args['source_ref'], args['representation'],
                        permitted_inputs=self._permitted_record_refs.get(), scope=scope)
                    original = json.loads(saved['result'])
                    if (original['result']['artifact_ref'] != artifact['id']
                            or original['result']['total_bytes'] != artifact['size']):
                        raise ContractError('source_location_artifact_identity_conflict')
                except ContractError as error:
                    return {'status': 'invalid', 'operation_ref': saved['id'], 'record_refs': [],
                        'changed_record_refs': [], 'result': None,
                        'feedback': {'category': 'arguments_or_reference', 'code': str(error)}}
            return json.loads(saved["result"])
        operation_ref = identity("operation", {"key": operation_key, "name": name, "arguments": args})
        result = {"status": "invalid", "operation_ref": operation_ref, "record_refs": [], "result": None, "feedback": None}
        try:
            catalog = self.catalog(scope)
            if name not in catalog:
                raise ContractError("unknown_tool")
            validate_schema(args, catalog[name]["input_schema"])
            self.store.validate_scope(scope)
            self._check_source_bytes(name, args)
            # Network acquisition happens before scientific publication. No
            # SQLite write transaction is held while waiting on a provider.
            snapshot = (self._estimate_native(args, scope) if name == 'execution.estimate' else
                await self._document_async(name, args) if name.startswith(("source.archive.", "source.pdf.", "source.xlsx.")) else
                await self._acquire_async(name, args, scope, operation_key) if name.startswith("public.") else None)
            with self.store.transaction():
                try:
                    result["result"], result["record_refs"] = self._perform(name, args, scope, snapshot)
                    result["status"] = "completed"
                    if name in ordinary_data_getters and not result["result"]["acquired"]:
                        result.update(status="partial", feedback={"category": "acquisition",
                            "code": result["result"]["failure_code"],
                            "source_ref": result["result"]["source_ref"]})
                        if (name == "public.ncbi.entrez"
                                and result["result"]["failure_code"] == "ncbi_entrez_native_error_response"
                                and result["result"]["source_ref"] is not None):
                            result["feedback"]["response"] = api_error_response(snapshot)
                            result["feedback"]["detail"] = {
                                "explanation": "The complete returned NCBI error response is included in feedback.response. "
                                    "For searches, inspect errorlist and querytranslation even when hits are present "
                                    "before choosing any revised request.",
                                "read_with": "source.read",
                                "read_query": {"source_ref": result["result"]["source_ref"],
                                    "representation": "original", "offset": 0}}
                    if name == "image.view":
                        # Only this host adapter can select a visual input. Never
                        # read attachment instructions from nested provider/model
                        # content, historical child work or a query response.
                        result["visual_inputs"] = [visual_input(self.store, result["result"]["view_ref"])]
                    if name == "source.xlsx.rows" and result["result"]["status"] != "completed":
                        result.update(status=result["result"]["status"],
                            feedback={"category": "representation", "code": "xlsx_rows_partially_decoded",
                                "source_ref": result["result"]["source_ref"],
                                "cell_error_count": result["result"]["cell_error_count"],
                                "row_error_count": result["result"]["row_error_count"],
                                "parse_failures": result["result"]["parse_failures"]})
                    if name in {"public.uniprot.record", "public.uniprot.search"} and result["result"].get("projection_errors"):
                        result.update(status="partial", feedback={"category": "representation",
                            "code": "uniprot_rows_partially_projected",
                            "source_ref": result["result"]["source_ref"],
                            "rows": result["result"]["projection_errors"]})
                    if isinstance(snapshot, PmcFiles) and snapshot.error:
                        result.update(status="partial", feedback={**api_error_feedback(snapshot.error),
                            "category": "provider", "code": snapshot.error.code,
                            "diagnostic_ref": self._acquisition_diagnostic(snapshot.error)})
                    if name in {"public.pmc.files", "public.pmc.asset"} and result["result"].get("representation_feedback"):
                        feedback = result["result"]["representation_feedback"]
                        if isinstance(snapshot, PmcFiles) and snapshot.error:
                            feedback = {**feedback, "acquisition_error": result["feedback"]}
                        result.update(status="partial", feedback=feedback)
                except Exception as error:
                    # Keep completed independent publications. A failed parser
                    # or later row does not erase an acquired source or an
                    # earlier valid candidate. Report the exact retained rows.
                    if not self._written:
                        raise
                    if name in ordinary_data_getters:
                        sources = [reference for reference in dict.fromkeys(self._written)
                            if self.store.get(reference).get("record_type") == "source"
                            and self.store.get(reference).get("provider") == getter_source_providers.get(name, name)]
                        failure_code = (str(error) if isinstance(error, ContractError)
                            else "data_acquisition_publication_incomplete")
                        if name in getter_failure_codes and failure_code not in getter_failure_codes[name]:
                            failure_code = 'data_acquisition_publication_incomplete'
                        result.update(status="partial", record_refs=sources, changed_record_refs=sources,
                            result={"acquired": False, "source_ref": sources[0] if sources else None,
                                "data_ref": None, "failure_code": failure_code}, feedback={
                                "category": "acquisition", "code": failure_code,
                                "diagnostic_ref": self.store.artifact(f"{type(error).__name__}: {error}", "text/plain")})
                        if name in getter_validators:
                            result["result"] = getter_validators[name](result["result"])
                    else:
                        result.update(status="partial", record_refs=list(dict.fromkeys(self._written)),
                            result={"retained_record_refs": list(dict.fromkeys(self._written))},
                            feedback={"category": "partial_execution", "code": str(error) if isinstance(error, ContractError) else "adapter_partial_result",
                                      "diagnostic_ref": self.store.artifact(f"{type(error).__name__}: {error}", "text/plain")})
                    if isinstance(error, ContractError) and error.detail:
                        result["feedback"]["detail"] = error.detail
                    result["feedback"].update(api_error_feedback(error))
                self._save(operation_key, name, args, scope, result)
            return result
        except AcquisitionError as error:
            operational = error.operational or {}
            diagnostic = (operational.get("cause") or {}).get("diagnostic_ref")
            if diagnostic is None and error.snapshot is not None:
                from dataclasses import asdict
                metadata = asdict(error.snapshot)
                metadata.pop("content")
                metadata["content_ref"] = self.store.artifact(error.snapshot.content, error.snapshot.media_type)
                diagnostic = self.store.artifact(canonical(metadata), "application/json")
            elif diagnostic is None and error.diagnostic is not None:
                diagnostic = self.store.artifact(canonical({"representation": "local_exception",
                    "details": error.diagnostic}), "application/json")
            result.update(status="unavailable" if error.code.endswith(("not_configured", "not_installed", "missing")) else "failed",
                          feedback={**api_error_feedback(error),
                              "category": "execution" if error.code.startswith("local_job_") or error.phase in {
                              'native_execution', 'local_execution', 'local_preflight', 'local_admission'} else "provider", "code": error.code, "retry_after": error.retry_after,
                                    "job_ref": error.job_ref, "diagnostic_ref": diagnostic,
                                    **({"phase": error.phase} if error.phase is not None else {}),
                                    **operational})
        except (ContractError, ValueError, KeyError) as error:
            result["feedback"] = {**api_error_feedback(error), "category": "arguments_or_reference",
                "code": str(error) if isinstance(error, ContractError) else "invalid_tool_input"}
            if isinstance(error, ContractError) and error.detail:
                result["feedback"]["detail"] = error.detail
        except Exception as error:
            diagnostic = self.store.artifact(f"{type(error).__name__}: {error}", "text/plain")
            result.update(status="failed", feedback={**api_error_feedback(error),
                "category": "execution", "code": "adapter_execution_failed",
                                                    "diagnostic_ref": diagnostic})
        # Failed attempts are durable audit, not acquired scientific units.
        # An operation key identifies this attempt; later attempts need a new key.
        if name in ordinary_data_getters and result["result"] is None:
            failure_code = (result.get("feedback") or {}).get("code", "data_acquisition_failed")
            if name in getter_failure_codes and failure_code not in getter_failure_codes[name]:
                failure_code = 'invalid_tool_input' if result['status'] == 'invalid' else 'data_acquisition_failed'
            result["result"] = {"acquired": False, "source_ref": None, "data_ref": None,
                "failure_code": failure_code}
            if name in getter_validators:
                result["result"] = getter_validators[name](result["result"])
        with self.store.transaction():
            self._save(operation_key, name, args, scope, result)
        return result




    def _save(self, key: str, name: str, args: dict, scope: dict | None, result: dict) -> None:
        failures = self._grading_failures.get()
        if failures:
            if result['status'] == 'completed':
                result['status'] = 'partial'
            if result.get('feedback') is None:
                result['feedback'] = {'category': 'grading_input',
                    'code': 'tool_grading_input_rejected', 'failures': list(failures)}
            else:
                # Preserve an execution/provider/representation failure already
                # reported for the same selected action.
                result['feedback']['grading_failures'] = list(failures)
        receipts = self._native_execution_refs.get()
        if receipts:
            result['native_execution_refs'] = list(dict.fromkeys(receipts))
            result['record_refs'] = list(dict.fromkeys([*result['record_refs'], *receipts]))
        batch = self._publication_batch.get()
        if batch is not None:
            result["published_batch"] = dict(batch)
        self.store.db.execute("INSERT INTO tool_operations VALUES(?,?,?,?,?,?)",
            (key, result["operation_ref"], name, canonical(args), canonical(scope), canonical(result)))


    def _estimate_native(self, args, scope):
        from .execution_expectations import capture_execution_scopes
        _, path, operation, selected = self._spreadsheet_arguments(args['tool'], args['arguments'])
        execution_class = self.native_statistics.spreadsheet_class(path, operation, selected, self.local_job_policy)
        recovery = self.native_statistics.recover_pending_statistics()
        return {'tool': args['tool'], 'arguments': args['arguments'],
            'execution_expectations': {**capture_execution_scopes(self.native_statistics.history_path, [execution_class]),
                                       'statistics_recovery': recovery}}


    def _record_native_execution(self, metadata, *, operation, operands):
        """Retain actual timing independently of scientific publication success."""
        from .execution_recording import NativeMeasurement
        from .native_timing_information import record_native_measurement
        measured = (metadata.get('statistics_export') or {}).get('measurement')
        if measured is None:
            return
        measurement = NativeMeasurement.from_record(measured)
        reference = record_native_measurement(self.store, measurement, operation=operation, operands=operands)
        # Do not append this to _written: a timing receipt does not turn a
        # failed scientific publisher into partially successful science.
        self._native_execution_refs.get().append(reference)
        metadata['native_execution_ref'] = reference


    @staticmethod
    async def _native_thread_async(function, *args, **kwargs):
        """Cancellation waits for the native adapter to reap its process tree."""
        return await run_cancellable_native(function, *args, **kwargs)


    def resolve_image_input(self, selected: dict) -> dict:
        return resolve_selected_image(self.store, selected)


    def _spreadsheet_arguments(self, name, args):
        source = self.store._require(args['source_ref'], {'source'})
        path = artifact_path(self.store, source['artifact_ref'])
        return source, path, name.rsplit('.', 1)[1], {key: value for key, value in args.items() if key != 'source_ref'}


    async def _document_async(self, name: str, args: dict) -> DocumentOutput:
        if self.store.db.in_transaction:
            raise ContractError("native_document_work_requires_no_active_store_transaction")
        if name.startswith('source.xlsx.'):
            source, path, operation, arguments = self._spreadsheet_arguments(name, args)
            member = None
        elif name == "source.archive.extract":
            member = self.store._require(args["member_ref"], {"archive_member"})
            source = self.store._require(member["source_ref"], {"source"})
            path = artifact_path(self.store, source['artifact_ref'])
        else:
            member = None
            source = self.store._require(args["source_ref"], {"source"})
            path = artifact_path(self.store, source['artifact_ref'])
        if name == "source.archive.members":
            output = await asyncio.to_thread(archive_inventory, path, offset=args.get("offset", 0), limit=args.get("limit", 50))
        elif name == "source.archive.extract":
            output = await asyncio.to_thread(archive_extract, path, member)
        elif name.startswith("source.xlsx."):
            operands = [{'role': 'input_source', 'subject_ref': source['id']}]
            try:
                output = await self._native_thread_async(xlsx_native, path, operation=operation,
                    arguments=arguments, job_limits=self.local_job_policy.to_dict(),
                    **({'statistics': self.native_statistics.for_spreadsheet(path, operation, arguments, self.local_job_policy)}
                       if self.native_statistics is not None else {}))
            except AcquisitionError as error:
                metadata = error.operational or {}
                self._record_native_execution(metadata.get('native', metadata),
                    operation='xlsx_'+operation, operands=operands)
                raise
            self._record_native_execution((output.metadata.get('local_jobs') or {}).get('work', {}),
                operation='xlsx_'+operation, operands=operands)
        else:
            operation = name.rsplit(".", 1)[1]
            if operation == "text" and args.get("last_page", args["page"]) < args["page"]:
                raise ContractError("pdf_page_range_reversed")
            output = await self._native_thread_async(pdf_native, path, operation=operation, executables=dict(self.pdf_executables),
                job_limits=self.local_job_policy.to_dict(),
                first_page=args.get("page"), last_page=args.get("last_page", args.get("page")), page=args.get("page"),
                layout=args.get("layout", "reading_order"), dpi=args.get("dpi", 150))
        output = replace(output, metadata={**output.metadata, "parent_source_ref": source["id"],
            "input_artifact_ref": source["artifact_ref"]})
        if output.metadata.get("returncode", 0) != 0:
            details = {**output.metadata,
                "stdout_ref": self.store.artifact(output.stdout, "text/plain"),
                "stderr_ref": self.store.artifact(output.stderr, "text/plain")}
            if output.content:
                details["partial_output_ref"] = self.store.artifact(output.content, output.media_type)
            raise AcquisitionError("pdf_native_error", phase="native_execution", operational={
                "native_returncode": output.metadata["returncode"],
                "native_stderr_tail": output.stderr[-4000:].decode("utf-8", errors="replace"),
                "diagnostic_ref": self.store.artifact(canonical(details), "application/json")})
        return output


    def _source_bytes(self, provider: str, content: bytes, media_type: str, metadata: dict) -> dict:
        artifact = self.store.artifact(content, media_type)
        return self._put("source", {"provider": provider, "accession": None, "uri": None,
            "artifact_ref": artifact, "text_ref": artifact if media_type.startswith("text/") else None,
            "request_ref": self.store.artifact(canonical(metadata), "application/json"),
            "version": metadata.get("software_version") or metadata.get("adapter_version"),
            "parent_source_refs": [metadata["parent_source_ref"]],
            "stdout_ref": metadata["stdout_ref"], "stderr_ref": metadata["stderr_ref"],
            "retrieved_at": metadata.get("finished_at") or datetime.now(timezone.utc).isoformat()}, origin="tool")


    def _publish_document(self, name: str, args: dict, output: DocumentOutput) -> tuple[dict, list[str]]:
        metadata = {**output.metadata,
            "stdout_ref": self.store.artifact(output.stdout, "text/plain"),
            "stderr_ref": self.store.artifact(output.stderr, "text/plain")}
        if name.startswith("source.xlsx."):
            source = self._source_bytes(name.removeprefix('source.'), output.content,
                'application/json', metadata)
            return {**json.loads(output.content), 'source_ref': source['id'],
                'xlsx_source_ref': args['source_ref'], 'artifact_ref': source['artifact_ref'],
                'provenance': metadata, 'biological_interpretation': 'not_performed'}, [source['id']]
        if name == "source.archive.members":
            source = self._source("archive.inventory", metadata, parent_source_refs=[args["source_ref"]],
                stdout_ref=metadata["stdout_ref"], stderr_ref=metadata["stderr_ref"])
            refs, members = [source["id"]], []
            for entry in metadata["members"]:
                member = self._put("archive_member", {"source_ref": args["source_ref"],
                    "archive_format": metadata["archive_format"], **entry}, origin="tool")
                refs.append(member["id"])
                members.append(member)
            next_query = ({**args, "offset": metadata["next_offset"], "limit": metadata["limit"]}
                          if metadata["next_offset"] is not None else None)
            return {"source_ref": source["id"], "archive_source_ref": args["source_ref"],
                "members": members, **{key: metadata[key] for key in ("offset", "limit", "total", "next_offset")},
                "next_query": next_query}, refs
        if name == "source.pdf.info":
            source = self._source_bytes("poppler.pdfinfo", output.content, "text/plain", metadata)
            return {"source_ref": source["id"], "pdf_source_ref": args["source_ref"],
                "page_count": metadata.get("page_count"), "native_information": output.content.decode("utf-8"),
                "provenance": metadata}, [source["id"]]
        media_type = output.media_type
        if name == "source.archive.extract":
            if output.content.startswith(b"%PDF-"):
                media_type = "application/pdf"
            elif output.content.startswith(b"\x89PNG\r\n\x1a\n"):
                media_type = "image/png"
            elif output.content.startswith(b"\xff\xd8\xff"):
                media_type = "image/jpeg"
        if output.content is None:
            raise ContractError("native_document_output_missing")
        source = self._source_bytes("archive.member" if name == "source.archive.extract" else
            "poppler.pdftotext" if name == "source.pdf.text" else "poppler.pdftoppm",
            output.content, media_type, metadata)
        material = self.store.register_material(source_ref=source["id"], format="opaque", use="evidence")
        self._written.append(material["id"])
        transformation = "archive_member" if name == "source.archive.extract" else "pdf_text" if name == "source.pdf.text" else "pdf_page"
        page = args.get("page")
        page_range = {}
        if transformation == "pdf_text":
            page_range = {"first_page": page, "last_page": args.get("last_page", page)}
            if page_range["first_page"] != page_range["last_page"]:
                # The source's retained native selection identifies the range.
                # Do not label a multi-page derivative as one physical page.
                page = None
        derivative = self._put("source_derivative", {"source_ref": source["id"],
            "parent_source_ref": metadata["parent_source_ref"], "transformation": transformation,
            "selection_ref": args.get("member_ref"), "page": page,
            "layout": args.get("layout", "reading_order") if transformation == "pdf_text" else None,
            "dpi": args.get("dpi", 150) if transformation == "pdf_page" else None,
            "coordinate_system": "original_member_bytes" if transformation == "archive_member" else
                "normalized_utf8_bytes" if transformation == "pdf_text" else "one_based_physical_pdf_page"}, origin="tool")
        return {"source_ref": source["id"], "material_ref": material["id"], "derivation_ref": derivative["id"],
            "artifact_ref": source["artifact_ref"], "media_type": media_type,
            "image_source_ref": source["id"] if media_type.startswith("image/") else None,
            "page": page, **page_range, "coordinate_system": derivative["coordinate_system"],
            "provenance": metadata, "biological_interpretation": "not_performed"}, [source["id"], material["id"], derivative["id"]]


    def _acquisition_diagnostic(self, error: AcquisitionError) -> str:
        snapshot = error.snapshot
        details = {"code": error.code, "phase": error.phase, "details": error.diagnostic}
        if snapshot:
            details.update(content_ref=self.store.artifact(snapshot.content, snapshot.media_type),
                url=snapshot.url, request=snapshot.request, transport=snapshot.transport)
        return self.store.artifact(canonical(details), "application/json")


    async def _acquire_async(self, name: str, args: dict, scope: dict | None,
                             operation_key: str) -> SourceSnapshot | None:
        function, arguments = self._acquisition_request(name, args, scope)
        return await self._acquire_response_async(name, function, arguments)




    async def _acquire_response_async(self, name, function, arguments):
        try:
            return await asyncio.to_thread(function, **arguments)
        except AcquisitionError as error:
            if (name == "public.ncbi.entrez" and isinstance(error.snapshot, SourceSnapshot)
                    and isinstance(error.snapshot.transport, dict)
                    and type(error.snapshot.transport.get("status")) is int):
                return error.snapshot
            raise


    def _acquisition_request(self, name: str, args: dict, scope: dict | None) -> tuple[Any, dict]:
        if name == 'public.literature.sequence_identity':
            from .literature_sequence_discovery import identity_request
            return identity_request(self, args, scope)
        if name == "public.ncbi.entrez":
            from .ncbi_entrez_tools import request_ncbi_entrez
            return request_ncbi_entrez, {"client": self.clients, "arguments": args}
        if name == "public.uniprot.search":
            return self.clients.uniprot_search, args
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




    def _perform(self, name: str, args: dict, scope: dict | None, snapshot: Any) -> tuple[dict, list[str]]:
        if name == 'public.literature.sequence_identity':
            from .literature_sequence_discovery import publish_identity
            return publish_identity(self, args, scope, snapshot)
        if name == 'source.sequence.references':
            from .literature_sequence_discovery import references
            return references(self, args, scope, self._permitted_record_refs.get())
        if name == 'source.sequence.scan':
            from .source_sequences import scan
            return scan(self, args, scope, self._permitted_record_refs.get())
        if name == "public.ncbi.entrez":
            from .ncbi_entrez_tools import publish_ncbi_entrez_request
            return publish_ncbi_entrez_request(self, args, snapshot)
        if name == 'execution.estimate':
            return snapshot, []
        if isinstance(snapshot, DocumentOutput):
            return self._publish_document(name, args, snapshot)
        if isinstance(snapshot, PmcFiles):
            return self._publish_pmc_files(args, snapshot)
        if name == "public.pmc.versions":
            return self._publish_pmc_versions(args, snapshot)
        if name == "public.pmc.asset":
            return self._publish_pmc_asset(args, snapshot)
        if snapshot is not None:
            return self._import(name, args, snapshot)
        if name == "state.query":
            def received(row):
                if row.get('record_type') != 'native_execution':
                    return row
                from .native_timing_information import read_measurement
                return {**row, 'measurement': read_measurement(self.store, row['id']).as_record()}
            if "refs" in args:
                conflicting_fields = sorted(set(args) - {"refs"})
                if conflicting_fields:
                    raise ContractError("exact_refs_cannot_be_combined_with_page_selectors",
                        detail={"selection_mode": "exact_references",
                                "conflicting_fields": conflicting_fields,
                                "allowed_fields": ["refs"]})
                rows = [self.store.get(item) for item in args["refs"]]
                # Exact target membership remains enforced for local records;
                # external evidence/source records are reusable resources.
                for row in rows:
                    if row["record_type"] in {"input", "feature", "product", "read_subject"}:
                        if not self.store._in_scope(row["id"], self.store.validate_scope(scope)):
                            raise ContractError("subject_outside_assigned_scope")
                return {"records": [received(row) for row in rows], "count": len(rows), "next_offset": None}, []
            kind, offset, limit = args.get("kind", "hypothesis"), args.get("offset", 0), args.get("limit", 100)
            page = self.store.query_records(kind, scope=scope, offset=offset, limit=limit,
                current_only=args.get("current_only", False), references=args.get("references"))
            page['records'] = [received(row) for row in page['records']]
            return page, []
        if name == "source.read":
            return source_window(self.store, **args), []
        if name == 'source.locate':
            return locate_source(self.store, **args,
                permitted_inputs=self._permitted_record_refs.get(), scope=scope), []
        if name == "image.view":
            body = prepare_image(self.store, **args)
            source = self._put("source", {"provider": "image.view", "accession": None, "uri": None,
                "artifact_ref": body["image_artifact_ref"], "text_ref": None,
                "parent_source_refs": [body["input_source_ref"]],
                "request_ref": self.store.artifact(canonical(body), "application/json"),
                "version": body["software_version"],
                "retrieved_at": datetime.now(timezone.utc).isoformat()}, origin="tool")
            view = self._put("image_view", {"source_ref": source["id"], **body}, origin="tool")
            return {"view_ref": view["id"], "view": view}, [source["id"], view["id"]]
        raise ContractError("unimplemented_tool")




    def _publish_pmc_versions(self, args: dict, snapshot: SourceSnapshot) -> tuple[dict, list[str]]:
        source = self._source(snapshot.service, None, snapshot=snapshot, accession=args["pmcid"])
        refs, versions = [source["id"]], []
        page = parse_listing(snapshot.content)
        if page["prefix"] != args["pmcid"] + ".":
            raise ContractError("pmc_version_listing_scope_mismatch")
        for prefix in page["version_prefixes"]:
            selected = self._put("pmc_version", {"source_ref": source["id"],
                **pmc_version(prefix, pmcid=args["pmcid"])}, origin="external")
            refs.append(selected["id"])
            versions.append(selected)
        return {"source_ref": source["id"], "versions": versions,
            "next_continuation_token": page["next_continuation_token"], "listing_complete": not page["truncated"],
            "version_preference": "not_assigned",
            "next_query": {"pmcid": args["pmcid"], "continuation_token": page["next_continuation_token"]}
                if page["next_continuation_token"] else None}, refs


    def _publish_pmc_files(self, args: dict, snapshots: PmcFiles) -> tuple[dict, list[str]]:
        selected = self.store._require(args["version_ref"], {"pmc_version"})
        listing = self._source(snapshots.listing.service, None, snapshot=snapshots.listing,
                               parent_source_refs=[selected["source_ref"]])
        refs, objects, assets = [listing["id"]], [], []
        page = parse_listing(snapshots.listing.content)
        if page["prefix"] != selected["prefix"]:
            raise ContractError("pmc_file_listing_scope_mismatch")
        for item in page["objects"]:
            record = self._put("pmc_object", {"source_ref": listing["id"], "version_ref": selected["id"],
                "object_key": item["key"], **{key: item[key] for key in ("size", "etag", "last_modified")}}, origin="external")
            refs.append(record["id"])
            objects.append(record)
        metadata = None
        if snapshots.metadata is not None:
            metadata = self._source(snapshots.metadata.service, None, snapshot=snapshots.metadata,
                                    parent_source_refs=[listing["id"]])
            refs.append(metadata["id"])
        catalog = self._put("pmc_catalog", {"source_ref": listing["id"], "version_ref": selected["id"],
            "metadata_source_ref": metadata["id"] if metadata else None,
            "listing_complete": not page["truncated"], "next_continuation_token": page["next_continuation_token"]}, origin="tool")
        refs.append(catalog["id"])
        body = {"source_ref": listing["id"], "catalog_ref": catalog["id"], "version_ref": selected["id"],
            "objects": objects, "assets": assets, "metadata_source_ref": metadata["id"] if metadata else None,
            "listing_complete": not page["truncated"], "next_continuation_token": page["next_continuation_token"],
            "next_query": {"version_ref": selected["id"], "continuation_token": page["next_continuation_token"]}
                if page["next_continuation_token"] else None}
        if metadata is None:
            return body, refs
        try:
            native = json.loads(snapshots.metadata.content)
            advertisements = metadata_assets(native, selected)
            errors = []
            for kind, field, uri in advertisements:
                try:
                    actual = advertised_asset(uri, prefix=selected["prefix"])
                    record = self._put("pmc_asset", {"source_ref": metadata["id"], "catalog_ref": catalog["id"],
                        "version_ref": selected["id"], "asset_kind": kind, "metadata_field": field, **actual}, origin="external")
                    refs.append(record["id"])
                    assets.append(record)
                except ContractError as error:
                    errors.append({"metadata_field": field, "code": str(error)})
            body["article_metadata"] = native
            if errors:
                body["representation_feedback"] = {"category": "representation", "code": "pmc_partial_asset_advertisements", "fields": errors}
        except (ValueError, UnicodeError) as error:
            body["representation_feedback"] = {"category": "representation", "code": str(error) if isinstance(error, ContractError) else "pmc_metadata_invalid_json"}
        return body, refs


    def _publish_pmc_asset(self, args: dict, snapshot: SourceSnapshot) -> tuple[dict, list[str]]:
        advertisement = self.store._require(args["asset_ref"], {"pmc_asset", "pmc_object"})
        snapshot = replace(snapshot, request={**snapshot.request,
            "selected_asset_ref": advertisement["id"], "selected_version_ref": advertisement["version_ref"]})
        source = self._source(snapshot.service, None, snapshot=snapshot,
                              parent_source_refs=[advertisement["source_ref"]])
        # Keep the actual HTTP Content-Type (generic public binary types are
        # honest); selected archive/PDF adapters inspect the actual bytes.
        material = self.store.register_material(source_ref=source["id"], format="opaque", use="evidence")
        self._written.append(material["id"])
        md5 = hashlib.md5(snapshot.content).hexdigest()
        advertised_md5 = advertisement.get("advertised_md5")
        body = {"source_ref": source["id"], "material_ref": material["id"], "asset_ref": advertisement["id"],
            "artifact_ref": source["artifact_ref"], "actual_sha256": snapshot.sha256, "actual_md5": md5,
            "advertised_md5": advertised_md5, "advertised_md5_matches": md5 == advertised_md5 if advertised_md5 else None,
            "original_advertisement": advertisement, "target_binding_changed": False}
        if advertised_md5 is not None and md5 != advertised_md5:
            body["representation_feedback"] = {"category": "provenance", "code": "advertised_checksum_differs_from_actual_bytes",
                "actual_source_retained": True, "source_ref": source["id"]}
        return body, [source["id"], material["id"]]


    def _import(self, name: str, args: dict, snapshot: SourceSnapshot) -> tuple[dict, list[str]]:
        text = None
        article = None
        if name == "public.literature.read":
            try:
                article = article_details(snapshot.content)
                paragraphs = article['sections']
            except ParseError as error:
                # A failed text projection must not discard acquired bytes.
                self._source(snapshot.service, None, snapshot=snapshot,
                             accession=args.get("pmcid"))
                raise ContractError("literature_xml_parse_failed") from error
            text = "\n\n".join(item["text"] for item in paragraphs)
        source = self._source(snapshot.service, None, snapshot=snapshot, text=text,
            accession=args.get("accession", args.get("pmcid", args.get("rid"))),
            publication_identifiers=article['publication_identifiers'] if article is not None else None)
        refs = [source["id"]]
        if name in {"public.uniprot.record", "public.uniprot.search"}:
            return self._import_uniprot(name, args, snapshot, source)
        if name == "public.ncbi.sequence":
            records = []
            for sequence in parse_genbank(snapshot.content):
                molecule = "protein" if args["database"] == "protein" else "rna" if "RNA" in sequence["annotations"].get("molecule_type", "") else "dna"
                record = self._put("reference", {"reference_type": molecule, "source_ref": source["id"],
                    "accession": sequence["accession"], "label": sequence["description"],
                    "sequence_ref": self.store.artifact(sequence["sequence"], "text/plain") if sequence["sequence_available"] else None,
                    "molecule": molecule, "length": sequence["length"], "term_refs": [], "context_refs": []}, origin="external")
                refs.append(record["id"])
                records.append(record)
            return {"source_ref": source["id"], "records": records, "count": len(records),
                    "original_feature_context_in_source": True}, refs
        if name == "public.literature.read":
            metadata_issues = list(article['metadata_issues'])
            reported = [item['value'] for item in article['publication_identifiers'] if item['namespace'] == 'pmcid']
            if reported and args['pmcid'] not in reported:
                metadata_issues.append({'code': 'requested_publication_identifier_mismatch',
                    'namespace': 'pmcid', 'requested_value': args['pmcid']})
            return {"source_ref": source["id"], "text_ref": source["text_ref"], "paragraph_count": len(paragraphs),
                    'publication_identifiers': article['publication_identifiers'],
                    'metadata_issues': metadata_issues,
                    'cited_publications': article['cited_publications'],
                    'citation_meaning': 'Bibliography discovery metadata from the retained article. Read the cited source to assess its actual reported evidence and scope.',
                    "text_bytes": len(text.encode()), "text_representation": "ordered_paragraph_projection",
                    "omitted_elements_available_in_original": True,
                    "original_read_query": {"source_ref": source["id"], "representation": "original"},
                    "read_with": "source.read"}, refs
        # Search/status outputs retain provider structure and source provenance;
        # no target assertion is manufactured by these acquisitions.
        try:
            native = json.loads(snapshot.content)
        except ValueError:
            native = None
        return {"source_ref": source["id"], "provider_result": native,
                "raw_artifact_ref": source["artifact_ref"]}, refs




    def _import_uniprot(self, name, args, snapshot, source):
        """Project one retained page while preserving original native row identity."""
        from .api_uniprot import parse_uniprot_snapshot, uniprot_page_metadata
        from .uniprot_native import legacy_uniprot_records
        from .uniprot_publication import bind_uniprot_publication

        operation = name.rsplit(".", 1)[1]
        request = {"operation": operation, **args,
                   **({"size": args.get("size", 10)} if operation == "search" else {})}
        result = {"source_ref": source["id"], "records": [], "count": 0,
                  "source_detail_available_through_source_read": True}
        refs = [source["id"]]
        try:
            parsed = parse_uniprot_snapshot(snapshot, request=request)
        except ValueError as error:
            # The source is already retained. A mismatched or unknown native
            # request cannot establish a bound result from otherwise valid JSON.
            result["projection_errors"] = [{"code": str(error), "record_ordinal": None,
                "pointer": "", "field": "request", "effect": "page_unusable"}]
            return result, refs
        errors = [dict(issue) for issue in parsed["issues"]
                  if issue["effect"] != "qualification"]
        release = parsed["page"]["release"]
        if release["state"] == "present" and source["version"] != release["value"]:
            result["projection_qualifications"] = [{"code": "uniprot_legacy_source_version_omitted",
                "record_ordinal": None, "pointer": release["pointer"],
                "field": "legacy_source", "effect": "qualification"}]
        by_ordinal = {}

        def projection_failure(native, pointer, code, effect="field_partial"):
            errors.append({"code": code, "record_ordinal": native["identity"]["record_ordinal"],
                "pointer": pointer, "primary_accession": native["identity"]["primary_accession"],
                "field": "legacy_publication", "effect": effect})

        def legacy_label(value, fallback, native, pointer):
            try:
                validate_schema(value, RECORD_SCHEMAS["reference"]["properties"]["label"])
            except ContractError:
                # Native text stays complete and valid in the publication. The
                # old label column has a narrower representation contract.
                projection_failure(native, pointer, "uniprot_legacy_label_unrepresentable")
                return fallback
            return value

        def legacy_term(namespace, accession, label, kind, native, pointer):
            payload = {"namespace": namespace, "accession": accession, "label": label,
                       "term_type": kind, "source_ref": source["id"], "anchor": None}
            try:
                validate_schema(payload, RECORD_SCHEMAS["term"])
            except ContractError:
                projection_failure(native, pointer, "uniprot_legacy_term_unrepresentable")
                return None
            term = self._put("term", payload, origin="external")
            refs.append(term["id"])
            return term["id"]

        for native, protein in zip(parsed["records"],
                                   legacy_uniprot_records(parsed, snapshot.content), strict=True):
            anchor = native["identity"]
            if protein["accession"] != anchor["primary_accession"]:
                raise ContractError("uniprot_legacy_record_identity_conflict")
            try:
                validate_schema(protein["accession"], RECORD_SCHEMAS["reference"]["properties"]["accession"])
            except ContractError:
                projection_failure(native, anchor["record_pointer"] + "/primaryAccession",
                                   "uniprot_legacy_reference_unrepresentable", "record_unpublishable")
                continue
            terms = []
            if protein["taxon_id"] is not None:
                taxon_id = str(protein["taxon_id"])
                label = legacy_label(protein["organism"] or taxon_id, taxon_id, native,
                                     native["taxon"]["scientific_name"]["pointer"])
                terms.append(legacy_term("ncbi_taxonomy", taxon_id, label, "taxon", native,
                                         native["taxon"]["taxon_id"]["pointer"]))
            legacy = native["legacy_publication"]
            if legacy["source_name"]:
                terms.append(legacy_term("uniprot_source_name", protein["accession"],
                    legacy["source_name"], "molecular_role", native, legacy["source_name_pointer"]))
            for ec, pointer in zip(legacy["source_ec_numbers"], legacy["source_ec_number_pointers"], strict=True):
                terms.append(legacy_term("EC", ec, "EC " + ec, "molecular_role", native, pointer))
            sequence = native["sequence"]
            sequence_ref = None
            if sequence["value"]["state"] == "present":
                sequence_bytes = sequence["value"]["value"].encode("ascii")
                sequence_ref = self.store.artifact(sequence_bytes, "text/plain")
                if self.store.get_artifact(sequence_ref) != sequence_bytes:
                    raise ContractError("uniprot_sequence_artifact_content_conflict")
            label = legacy_label(legacy["source_name"] or protein["accession"], protein["accession"],
                                 native, legacy["source_name_pointer"])
            record = self._put("reference", {"reference_type": "protein", "source_ref": source["id"],
                "accession": protein["accession"], "label": label, "sequence_ref": sequence_ref,
                "molecule": "protein", "length": sequence["observed_length_aa"],
                "term_refs": list(dict.fromkeys(term for term in terms if term is not None)),
                "context_refs": []}, origin="external")
            by_ordinal[anchor["record_ordinal"]] = record
            refs.append(record["id"])
            result["records"].append(record)
        if self.store.get_artifact(source["artifact_ref"]) != snapshot.content:
            raise ContractError("uniprot_native_artifact_content_conflict")
        for native in parsed["records"]:
            anchor = native["identity"]
            if anchor["record_ordinal"] not in by_ordinal and not any(
                    error.get("code") == "uniprot_legacy_reference_unrepresentable" and
                    error.get("effect") == "record_unpublishable" and
                    error.get("record_ordinal") == anchor["record_ordinal"] and
                    error.get("pointer") == anchor["record_pointer"] + "/primaryAccession" and
                    error.get("primary_accession") == anchor["primary_accession"] for error in errors):
                raise ContractError("uniprot_publication_omission_not_reported")
        result.update(count=len(by_ordinal), projection_errors=errors,
            uniprot_publication=bind_uniprot_publication(parsed, source_ref=source["id"],
                native_artifact_ref=source["artifact_ref"], references_by_ordinal=by_ordinal))
        if operation == "search":
            result.update(uniprot_page_metadata(parsed))
        return result, list(dict.fromkeys(refs))

    def retained_molecular_reference_access(self, context, reference, namespace, *, initial_record_refs=()):
        """Actual finite publication owner; this port grants no new receipt."""
        from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.enrichr_reference_privacy import enrichr_reference_restriction
        from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.molecular_reference_privacy import molecular_reference_restriction
        restriction = enrichr_reference_restriction(self.store, context, reference, namespace, initial_record_refs=initial_record_refs)
        if restriction is not None:
            return restriction
        return molecular_reference_restriction(self.store, context, reference, namespace)

