"""A105's own tool registry: source acquisition, document access and source publication over the run's store.

Each A105 binding gets its own ``A105ToolRegistry`` over the run's one shared
``gene_annotation_episode.state.Store`` (BINDING_CONTRACT C4). It offers only the
tools whose implementation exists in this axis folder:

- store and source reads: ``state.query``, ``source.read``, ``source.locate``;
- received-response readers: ``source.sequence.references``, ``source.experimental.records``;
- documents: ``source.archive.members``, ``source.archive.extract``, ``source.pdf.info``,
  ``source.pdf.text``, ``source.pdf.page``;
- public acquisition: ``public.pmc.versions``, ``public.pmc.files``, ``public.pmc.asset``,
  ``public.ncbi.search``, ``public.ncbi.sequence``, ``public.taxonomy``, ``public.literature.search``,
  ``public.literature.read``, ``public.literature.sequence_identity`` and every experimental-database
  operation of ``experimental_database_acquisition``.
"""
from __future__ import annotations

import asyncio
from contextlib import ExitStack
from contextvars import ContextVar
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import ParseError

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence import library_targets as libraries
from gene_annotation_episode import materials_packing as packing
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.experimental_activity_evidence.acquisition import PublicClients, SourceSnapshot, article_details, parse_genbank
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.api_error_feedback import api_error_feedback
from gene_annotation_episode.episodic_workflow.episode_support.tools.documents.experimental_activity_evidence.document_tools import DocumentOutput, archive_extract, archive_inventory, pdf_native, resource as document_resource
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import REF, REFS, RECORD_SCHEMAS, canonical, identity, obj, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.experimental_activity_evidence.experimental_database_acquisition import (OPERATIONS as EXPERIMENT_DATABASE_TOOLS,
                                                catalog as experimental_database_catalog,
                                                publish as publish_experimental_database,
                                                request as experimental_database_request)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.experimental_database_records import READER as EXPERIMENT_RECORDS, read_records, reader_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_assets import (BUCKET, PmcFiles, advertised_asset, metadata_assets, parse_listing,
                                        version as pmc_version)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_sequence_discovery import (identity_request, identity_schema, protein_operand,
                                                    publish_identity, references as sequence_references,
                                                    references_schema)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.experimental_activity_evidence.local_jobs import LocalJobPolicy, run_cancellable_native
from gene_annotation_episode.episodic_workflow.episode_support.readers.experimental_activity_evidence.source_bytes import source_window, source_window_selection
from gene_annotation_episode.episodic_workflow.episode_support.readers.experimental_activity_evidence.source_locations import locate as locate_source, locate_schema, received_source as received_location_source

INTEGER = {'type': 'integer', 'minimum': 0}
POSITIVE = {'type': 'integer', 'minimum': 1}
TEXT = {'type': 'string', 'minLength': 1}

_DEFINITIONS = {
    'state.query': ('Read an exact page of typed scientific records, current revisions, or records referring to actual references. Follow the returned next_query for the same selection and order. Exact refs is a separate mode and cannot be combined with page selectors.', obj({'kind': {'enum': list(RECORD_SCHEMAS) + ['subject']}, 'offset': INTEGER, 'limit': POSITIVE, 'refs': {**REFS, 'description': 'Exact reference mode: supply refs alone, including an empty array for no records. Omit kind, offset, limit, current_only and references in this mode.'}, 'current_only': {'type': 'boolean'}, 'references': {'type': 'array', 'items': REF, 'minItems': 1, 'description': "Select records that refer to any supplied ID through reference fields or provenance anchors. This does not match a record's own ID; to read known records themselves, supply refs alone instead."}}, required=[])),
    'source.read': ('Read a bounded UTF-8 byte window from an actual source. Choose original for retained source bytes, including XML tables/headings omitted by a paragraph projection; text selects that projection when available. Explicit stdout/stderr select retained native stream bytes when present, without falling back to another representation. Returned artifact/offsets support exact anchors.', obj({'source_ref': REF, 'offset': INTEGER, 'limit': POSITIVE, 'representation': {'enum': ['text', 'original', 'stdout', 'stderr']}}, ['source_ref'])),
    'source.locate': ('Locate an exact supplied literal quote in an explicitly received original or text source representation. Return UTF-8 byte witnesses, unchanged neighboring context and bounded match continuation. Multiple occurrences remain separate. No normalization, scientific interpretation, measurement parsing or evidence credit is performed; no literal match means only no match in the examined bytes.', locate_schema()),
    'public.pmc.versions': ('List one actual public PMC cloud version page. No version is chosen as latest/preferred; source versions can differ in manuscript status and can change in place.', obj({'pmcid': {'type': 'string', 'pattern': '^PMC[0-9]+$'}, 'continuation_token': TEXT}, ['pmcid'])),
    'public.pmc.files': ("Read the selected advertised version's actual file inventory and its listed JSON metadata. Returns reusable listed-object/advertised-asset IDs; optional metadata failure preserves listed files. Choose a version ID, not a URL or guessed filename.", obj({'version_ref': REF, 'continuation_token': TEXT}, ['version_ref'])),
    'public.pmc.asset': ('Acquire exactly one selected advertised/listed PMC asset ID. Preserve actual HTTP bytes, original advertisement and checksums; source content is evidence, not target annotation.', obj({'asset_ref': REF})),
    'source.archive.members': ('Inventory one page of an actual ZIP/TAR source. Member IDs preserve ordinal identity, including duplicate names; no members are extracted or selected for you.', obj({'source_ref': REF, 'offset': INTEGER, 'limit': POSITIVE}, ['source_ref'])),
    'source.archive.extract': ("Extract exactly one inventoried regular member to a source artifact; never follow a member's host path or link. Original archive and member identity remain attached.", obj({'member_ref': REF})),
    'source.pdf.info': ('Read native PDF information and physical page count for a selected actual source; no biological interpretation.', obj({'source_ref': REF})),
    'source.pdf.text': ('Extract a selected physical PDF page or contiguous page range as a reusable UTF-8 text derivative. page is the first page; optional last_page is inclusive and defaults to page. Use source.pdf.info for the physical page count, then source.locate on the extracted text to find a section without guessing pages. Native page breaks and the selected range are retained. Byte offsets refer to this text derivative, not the PDF. No OCR or interpretation is performed.', obj({'source_ref': REF, 'page': POSITIVE, 'last_page': POSITIVE, 'layout': {'enum': ['reading_order', 'layout', 'raw']}}, ['source_ref', 'page'])),
    'source.pdf.page': ('Render one explicitly selected physical PDF page as a reusable PNG source. Rendering does not by itself supply image input to a model or interpret a figure.', obj({'source_ref': REF, 'page': POSITIVE, 'dpi': {'type': 'number', 'exclusiveMinimum': 0}}, ['source_ref', 'page'])),
    'public.ncbi.search': ('Search one page of a named NCBI collection for selected references, taxa or sample context.', obj({'database': {'enum': ['protein', 'nuccore', 'assembly', 'taxonomy', 'biosample', 'bioproject', 'pubmed']}, 'term': TEXT, 'size': POSITIVE, 'offset': INTEGER}, ['database', 'term'])),
    'public.ncbi.sequence': ('Acquire an external GenBank/GenPept sequence and its original feature context; optional nucleotide interval uses zero-based half-open coordinates.', obj({'accession': TEXT, 'database': {'enum': ['protein', 'nuccore']}, 'start': INTEGER, 'end': POSITIVE}, ['accession', 'database'])),
    'public.taxonomy': ("Retrieve a taxon's source lineage record; it does not assign that taxon to the target.", obj({'taxon_id': POSITIVE})),
    'public.literature.search': ('Acquire one literature search page. Read the actual source before extracting biological evidence.', obj({'query': TEXT, 'size': POSITIVE, 'cursor': TEXT}, ['query'])),
    'public.literature.read': ("Acquire an actual open article, an ordered paragraph projection and separate cited-publication metadata. Bibliography identifiers and paragraph links support further source discovery; they do not identify the acquired article or establish a cited experiment's result. Read the retained original XML with source.read representation=original for tables, headings and other omitted elements.", obj({'pmcid': TEXT})),
}
_EXPERIMENT_RECORDS_DESCRIPTION = 'Inspect one page of a received experimental database response. Return native assay records, source measurement selectors and literal record links. Optional contains and contains_all filter retained rows by one or several literal terms, including their native headers and section labels. Record and whole-page link continuations are separate. These records locate the assayed molecule and its original measured-activity evidence; metadata and deposited scores retain their native meanings.'
_SEQUENCE_IDENTITY_DESCRIPTION = 'Find publication leads from a supplied protein sequence: retrieve one UniProtKB checksum-search page and verify each complete residue string. Return all equal records on the page, names, organisms, citation counts and explicit continuation. The optional reviewed filter selects database curation status. These are source identities and discovery metadata; experimental evidence requires reading the actual publications.'
_SEQUENCE_REFERENCES_DESCRIPTION = 'Read a page of publication identifiers, titles and reported citation scopes from a received sequence-identity response. Reverify full sequence equality for the selected record. Citation metadata supplies leads; it does not establish experimental results.'
_PDF_TOOLS = (('source.pdf.info', 'pdfinfo'), ('source.pdf.text', 'pdftotext'), ('source.pdf.page', 'pdftoppm'))
_SOURCE_BYTE_READERS = frozenset({'source.read', 'source.locate', 'source.sequence.references', 'source.archive.members',
                                  'source.pdf.info', 'source.pdf.text', 'source.pdf.page'})
_WINDOW_READERS = frozenset({'source.read', 'source.locate', 'source.sequence.references'})


class A105ToolRegistry:
    """One A105 binding's tools over the run's shared store.

    ``pdfinfo_executable``, ``pdftotext_executable`` and ``pdftoppm_executable`` are the
    installed Poppler programs (``None`` declares one not installed: its tool then
    returns ``unavailable``); ``job_limits`` are the local native job settings.
    """

    def __init__(self, store: Any, *, pdfinfo_executable: str | Path | None, pdftotext_executable: str | Path | None,
                 pdftoppm_executable: str | Path | None, job_limits: dict):
        self.store = store
        self.local_job_policy = LocalJobPolicy.from_config(job_limits)
        self.clients = PublicClients()
        self.pdf_executables = {name: document_resource(path)['executable'] for name, path in (
            ('pdfinfo', pdfinfo_executable), ('pdftotext', pdftotext_executable), ('pdftoppm', pdftoppm_executable))}
        self._publications = ContextVar('a105_tool_publications', default=None)
        self._permitted_record_refs = ContextVar('a105_tool_permitted_record_refs', default=None)
        self._mapping_directories = ContextVar('a105_unit_scratch_directories', default=None)

    @property
    def _written(self) -> list[str]:
        publications = self._publications.get()
        if publications is None:
            raise ContractError('publication_outside_tool_operation')
        return publications

    # -- catalog ----------------------------------------------------------------------------------------------------
    def catalog(self, scope: dict | None = None) -> dict[str, dict]:
        result = {name: {'description': description, 'input_schema': schema}
                  for name, (description, schema) in _DEFINITIONS.items()}
        result.update(experimental_database_catalog())
        result[EXPERIMENT_RECORDS] = {'description': _EXPERIMENT_RECORDS_DESCRIPTION, 'input_schema': reader_schema()}
        result['public.literature.sequence_identity'] = {'description': _SEQUENCE_IDENTITY_DESCRIPTION,
                                                         'input_schema': identity_schema()}
        result['source.sequence.references'] = {'description': _SEQUENCE_REFERENCES_DESCRIPTION,
                                                'input_schema': references_schema()}
        for name, native in _PDF_TOOLS:
            result[name]['configuration'] = {**document_resource(self.pdf_executables[native]),
                                             'job_limits': self.local_job_policy.to_dict()}
        return result

    # -- operands ---------------------------------------------------------------------------------------------------
    def _check_target(self, reference: str, scope: dict | None, *, footprint: list[dict] | None = None) -> dict:
        row = self.store.get(reference)
        footprint = self.store.coverage(reference) if footprint is None else footprint
        normalized = self.store.validate_scope(scope)
        allowed = set(normalized['subject_refs'])
        if not footprint or any(item['target_ref'] not in allowed for item in footprint):
            raise ContractError('subject_outside_assigned_scope')
        if not self.store.scope_covers(footprint, normalized):
            raise ContractError('requested_measurement_outside_assigned_segments_or_members'
                                if any('member_ref' in span for span in footprint)
                                else 'requested_measurement_outside_assigned_segments')
        return row

    def _sequence(self, reference: str) -> str:
        row = self.store.get(reference)
        if row.get('record_type') == 'read_subject':
            member = self.store.get(row['member_ref'])
            return packing.component_window(self.store, member, 'sequence', 0, row['length']).decode('ascii')
        if libraries.is_library(row):
            raise ContractError('library_is_not_a_sequence_operand')
        if row.get('sequence_ref'):
            return self.store.get_artifact(row['sequence_ref']).decode('ascii')
        if row.get('record_type') == 'feature':
            if row['strand'] == '-':
                raise ContractError('a105_reverse_complement_feature_view_not_implemented')
            parent = self._sequence(row['subject_ref'])
            return ''.join(parent[item['start']:item['end']] for item in row['segments'])
        raise ContractError('referenced_record_has_no_sequence')

    def _check_sequence_operand(self, reference: str, scope: dict | None, *, footprint: list[dict] | None = None) -> dict:
        """Resolve scientific sequence material without turning it into a target.

        Original-input work retains its assigned ownership bounds. Registered
        external evidence and its derivatives have no input credit footprint;
        their absence of one is not a prohibition on investigating the source.
        """
        row = self.store.get(reference)
        if row['record_type'] not in {'input', 'feature', 'product', 'reference', 'read_subject'}:
            raise ContractError('sequence_operand_required')
        self.store.subject_length(reference)
        self.store.validate_scope(scope)
        if self.store.roots(reference):
            return self._check_target(reference, scope, footprint=footprint)
        return row

    def _check_source_bytes(self, name, arguments):
        """Only received sources may be read when the caller names its received records."""
        if name not in _SOURCE_BYTE_READERS:
            return
        source = self.store.require(arguments['source_ref'], {'source'})
        if name in _WINDOW_READERS:
            representation = 'original' if name == 'source.sequence.references' else arguments.get('representation', 'text')
            source_window_selection(source, representation)
        permitted = self._permitted_record_refs.get()
        if permitted is not None and source['id'] not in permitted:
            raise ContractError('source_bytes_not_received')

    # -- publication ------------------------------------------------------------------------------------------------
    def _put(self, kind: str, record: dict, **kwargs: Any) -> dict:
        result = self.store.put(kind, record, **kwargs)
        self._written.append(result['id'])
        return result

    def _source(self, provider: str, body: Any, *, snapshot: SourceSnapshot | None = None, text: str | None = None,
                accession: str | None = None, software_version: str | None = None,
                parent_source_refs: list[str] | None = None, stdout_ref: str | None = None,
                stderr_ref: str | None = None, operand_refs: list[str] | None = None,
                publication_identifiers: list[dict] | None = None) -> dict:
        artifact = self.store.artifact(snapshot.content if snapshot else canonical(body),
                                       snapshot.media_type if snapshot else 'application/json')
        request = None
        if snapshot:
            request = self.store.artifact(canonical({'request': snapshot.request, 'transport': snapshot.transport}),
                                          'application/json')
            if software_version is None:
                if snapshot.service == 'uniprot':
                    transport = snapshot.transport if isinstance(snapshot.transport, dict) else {}
                    response = transport.get('response')
                    headers = response.get('headers', transport.get('headers')) if isinstance(response, dict) \
                        else transport.get('headers')
                    candidate = headers.get('x-uniprot-release') if isinstance(headers, dict) else None
                    try:
                        validate_schema(candidate, RECORD_SCHEMAS['source']['properties']['version'])
                    except ContractError:
                        candidate = None
                    software_version = candidate
                else:
                    details = snapshot.transport.get('job_details') or {}
                    database = details.get('database')
                    software_version = (database.get('version') if isinstance(database, dict) else None) or \
                        snapshot.transport.get('response', {}).get('headers', {}).get('x-uniprot-release')
        return self._put('source', {
            'provider': provider, 'accession': accession, 'uri': snapshot.url if snapshot else None,
            'artifact_ref': artifact, 'text_ref': self.store.artifact(text, 'text/plain') if text is not None else None,
            'request_ref': request, 'version': software_version,
            'retrieved_at': snapshot.retrieved_at if snapshot else datetime.now(timezone.utc).isoformat(),
            **({'parent_source_refs': parent_source_refs} if parent_source_refs is not None else {}),
            **({'stdout_ref': stdout_ref} if stdout_ref is not None else {}),
            **({'stderr_ref': stderr_ref} if stderr_ref is not None else {}),
            **({'operand_refs': operand_refs} if operand_refs is not None else {}),
            **({'publication_identifiers': publication_identifiers} if publication_identifiers else {})},
            origin='external' if snapshot else 'tool')

    def _source_bytes(self, provider: str, content: bytes, media_type: str, metadata: dict) -> dict:
        artifact = self.store.artifact(content, media_type)
        return self._put('source', {
            'provider': provider, 'accession': None, 'uri': None, 'artifact_ref': artifact,
            'text_ref': artifact if media_type.startswith('text/') else None,
            'request_ref': self.store.artifact(canonical(metadata), 'application/json'),
            'version': metadata.get('software_version') or metadata.get('adapter_version'),
            'parent_source_refs': [metadata['parent_source_ref']], 'stdout_ref': metadata['stdout_ref'],
            'stderr_ref': metadata['stderr_ref'],
            'retrieved_at': metadata.get('finished_at') or datetime.now(timezone.utc).isoformat()}, origin='tool')

    def _acquisition_diagnostic(self, error: AcquisitionError) -> str:
        snapshot = error.snapshot
        details = {'code': error.code, 'phase': error.phase, 'details': error.diagnostic}
        if snapshot:
            details.update(content_ref=self.store.artifact(snapshot.content, snapshot.media_type), url=snapshot.url,
                           request=snapshot.request, transport=snapshot.transport)
        return self.store.artifact(canonical(details), 'application/json')

    # -- execution --------------------------------------------------------------------------------------------------
    async def execute_async(self, name: str, args: dict, *, scope: dict | None = None,
                            operation_key: str | None = None, permitted_record_refs=None) -> dict:
        if permitted_record_refs is not None and (
                not isinstance(permitted_record_refs, (list, tuple))
                or any(not isinstance(ref, str) or not ref for ref in permitted_record_refs)):
            raise ContractError('explicit_permitted_record_refs_required')
        if name == 'source.locate':
            try:
                canonical(args)
            except (TypeError, ValueError):
                return {'status': 'invalid', 'operation_ref': None, 'record_refs': [], 'changed_record_refs': [],
                        'result': None,
                        'feedback': {'category': 'arguments_or_reference', 'code': 'source_location_arguments_not_json'}}
        token = self._publications.set([])
        directories = self._mapping_directories.set(ExitStack())
        permitted = self._permitted_record_refs.set(
            None if permitted_record_refs is None else tuple(permitted_record_refs))
        try:
            return await self._execute_operation_async(name, args, scope=scope, operation_key=operation_key)
        finally:
            self._mapping_directories.get().close()
            self._mapping_directories.reset(directories)
            self._permitted_record_refs.reset(permitted)
            self._publications.reset(token)

    async def _execute_operation_async(self, name: str, args: dict, *, scope: dict | None = None,
                                       operation_key: str | None = None) -> dict:
        operation_key = operation_key or identity('manual_operation', {
            'name': name, 'args': args, 'time': datetime.now(timezone.utc).isoformat()})
        operation_ref = identity('operation', {'key': operation_key, 'name': name, 'arguments': args})
        result = {'status': 'invalid', 'operation_ref': operation_ref, 'record_refs': [], 'result': None, 'feedback': None}
        try:
            catalog = self.catalog(scope)
            if name not in catalog:
                raise ContractError('unknown_tool')
            validate_schema(args, catalog[name]['input_schema'])
            self.store.validate_scope(scope)
            self._check_source_bytes(name, args)
            if name.startswith(('source.archive.', 'source.pdf.')):
                snapshot = await self._document_async(name, args)
            elif name.startswith('public.'):
                function, arguments = self._acquisition_request(name, args, scope)
                snapshot = await asyncio.to_thread(function, **arguments)
            else:
                snapshot = None
            with self.store.transaction():
                try:
                    result['result'], result['record_refs'] = self._perform(name, args, scope, snapshot)
                    result['status'] = 'completed'
                    if isinstance(snapshot, PmcFiles) and snapshot.error:
                        result.update(status='partial', feedback={
                            **api_error_feedback(snapshot.error), 'category': 'provider', 'code': snapshot.error.code,
                            'diagnostic_ref': self._acquisition_diagnostic(snapshot.error)})
                    if name in {'public.pmc.files', 'public.pmc.asset'} and result['result'].get('representation_feedback'):
                        feedback = result['result']['representation_feedback']
                        if isinstance(snapshot, PmcFiles) and snapshot.error:
                            feedback = {**feedback, 'acquisition_error': result['feedback']}
                        result.update(status='partial', feedback=feedback)
                except Exception as error:
                    if not self._written:
                        raise
                    written = list(dict.fromkeys(self._written))
                    result.update(status='partial', record_refs=written, result={'retained_record_refs': written},
                                  feedback={'category': 'partial_execution',
                                            'code': str(error) if isinstance(error, ContractError) else 'adapter_partial_result',
                                            'diagnostic_ref': self.store.artifact(f'{type(error).__name__}: {error}', 'text/plain')})
                    if isinstance(error, ContractError) and error.detail:
                        result['feedback']['detail'] = error.detail
                    result['feedback'].update(api_error_feedback(error))
            return result
        except AcquisitionError as error:
            operational = error.operational or {}
            diagnostic = (operational.get('cause') or {}).get('diagnostic_ref')
            if diagnostic is None and error.snapshot is not None:
                from dataclasses import asdict
                metadata = asdict(error.snapshot)
                metadata.pop('content')
                metadata['content_ref'] = self.store.artifact(error.snapshot.content, error.snapshot.media_type)
                diagnostic = self.store.artifact(canonical(metadata), 'application/json')
            elif diagnostic is None and error.diagnostic is not None:
                diagnostic = self.store.artifact(canonical({'representation': 'local_exception', 'details': error.diagnostic}),
                                                 'application/json')
            result.update(
                status='unavailable' if error.code.endswith(('not_configured', 'not_installed', 'missing')) else 'failed',
                feedback={**api_error_feedback(error),
                          'category': 'execution' if error.code.startswith('local_job_') or error.phase in {
                              'native_execution', 'local_execution', 'local_preflight', 'local_admission'} else 'provider',
                          'code': error.code, 'retry_after': error.retry_after, 'job_ref': error.job_ref,
                          'diagnostic_ref': diagnostic, **({'phase': error.phase} if error.phase is not None else {}),
                          **operational})
        except (ContractError, ValueError, KeyError) as error:
            result['feedback'] = {**api_error_feedback(error), 'category': 'arguments_or_reference',
                                  'code': str(error) if isinstance(error, ContractError) else 'invalid_tool_input'}
            if isinstance(error, ContractError) and error.detail:
                result['feedback']['detail'] = error.detail
        except Exception as error:
            diagnostic = self.store.artifact(f'{type(error).__name__}: {error}', 'text/plain')
            result.update(status='failed', feedback={**api_error_feedback(error), 'category': 'execution',
                                                     'code': 'adapter_execution_failed', 'diagnostic_ref': diagnostic})
        return result

    def _artifact_file(self, ref):
        """A file holding the bytes of the held artifact ``ref``, in a scratch directory of the running unit
        (removed when the tool call ends), for a native program or a reader that needs a path."""
        return self._mapping_directories.get().enter_context(self.store.scratch('input')).copy_artifact(ref, 'input')

    # -- native documents -------------------------------------------------------------------------------------------
    async def _document_async(self, name: str, args: dict) -> DocumentOutput:
        if self.store.in_transaction():
            raise ContractError('native_document_work_requires_no_active_store_transaction')
        if name == 'source.archive.extract':
            member = self.store.require(args['member_ref'], {'archive_member'})
            source = self.store.require(member['source_ref'], {'source'})
        else:
            member = None
            source = self.store.require(args['source_ref'], {'source'})
        path = self._artifact_file(source['artifact_ref'])
        if name == 'source.archive.members':
            output = await asyncio.to_thread(archive_inventory, path, offset=args.get('offset', 0),
                                             limit=args.get('limit', 50))
        elif name == 'source.archive.extract':
            output = await asyncio.to_thread(archive_extract, path, member)
        else:
            operation = name.rsplit('.', 1)[1]
            if operation == 'text' and args.get('last_page', args['page']) < args['page']:
                raise ContractError('pdf_page_range_reversed')
            output = await run_cancellable_native(
                pdf_native, path, operation=operation, executables=dict(self.pdf_executables),
                job_limits=self.local_job_policy.to_dict(), first_page=args.get('page'),
                last_page=args.get('last_page', args.get('page')), page=args.get('page'),
                layout=args.get('layout', 'reading_order'), dpi=args.get('dpi', 150))
        output = replace(output, metadata={**output.metadata, 'parent_source_ref': source['id'],
                                           'input_artifact_ref': source['artifact_ref']})
        if output.metadata.get('returncode', 0) != 0:
            details = {**output.metadata, 'stdout_ref': self.store.artifact(output.stdout, 'text/plain'),
                       'stderr_ref': self.store.artifact(output.stderr, 'text/plain')}
            if output.content:
                details['partial_output_ref'] = self.store.artifact(output.content, output.media_type)
            raise AcquisitionError('pdf_native_error', phase='native_execution', operational={
                'native_returncode': output.metadata['returncode'],
                'native_stderr_tail': output.stderr[-4000:].decode('utf-8', errors='replace'),
                'diagnostic_ref': self.store.artifact(canonical(details), 'application/json')})
        return output

    def _publish_document(self, name: str, args: dict, output: DocumentOutput) -> tuple[dict, list[str]]:
        metadata = {**output.metadata, 'stdout_ref': self.store.artifact(output.stdout, 'text/plain'),
                    'stderr_ref': self.store.artifact(output.stderr, 'text/plain')}
        if name == 'source.archive.members':
            source = self._source('archive.inventory', metadata, parent_source_refs=[args['source_ref']],
                                  stdout_ref=metadata['stdout_ref'], stderr_ref=metadata['stderr_ref'])
            refs, members = [source['id']], []
            for entry in metadata['members']:
                member = self._put('archive_member', {'source_ref': args['source_ref'],
                                                      'archive_format': metadata['archive_format'], **entry}, origin='tool')
                refs.append(member['id'])
                members.append(member)
            next_query = {**args, 'offset': metadata['next_offset'], 'limit': metadata['limit']} \
                if metadata['next_offset'] is not None else None
            return ({'source_ref': source['id'], 'archive_source_ref': args['source_ref'], 'members': members,
                     **{key: metadata[key] for key in ('offset', 'limit', 'total', 'next_offset')},
                     'next_query': next_query}, refs)
        if name == 'source.pdf.info':
            source = self._source_bytes('poppler.pdfinfo', output.content, 'text/plain', metadata)
            return ({'source_ref': source['id'], 'pdf_source_ref': args['source_ref'],
                     'page_count': metadata.get('page_count'), 'native_information': output.content.decode('utf-8'),
                     'provenance': metadata}, [source['id']])
        if output.content is None:
            raise ContractError('native_document_output_missing')
        media_type = output.media_type
        if name == 'source.archive.extract':
            if output.content.startswith(b'%PDF-'):
                media_type = 'application/pdf'
            elif output.content.startswith(b'\x89PNG\r\n\x1a\n'):
                media_type = 'image/png'
            elif output.content.startswith(b'\xff\xd8\xff'):
                media_type = 'image/jpeg'
        provider = 'archive.member' if name == 'source.archive.extract' else \
            'poppler.pdftotext' if name == 'source.pdf.text' else 'poppler.pdftoppm'
        source = self._source_bytes(provider, output.content, media_type, metadata)
        material = self.store.register_material(source_ref=source['id'], format='opaque', use='evidence')
        self._written.append(material['id'])
        transformation = 'archive_member' if name == 'source.archive.extract' else \
            'pdf_text' if name == 'source.pdf.text' else 'pdf_page'
        page = args.get('page')
        page_range = {}
        if transformation == 'pdf_text':
            page_range = {'first_page': page, 'last_page': args.get('last_page', page)}
            if page_range['first_page'] != page_range['last_page']:
                page = None
        derivative = self._put('source_derivative', {
            'source_ref': source['id'], 'parent_source_ref': metadata['parent_source_ref'],
            'transformation': transformation, 'selection_ref': args.get('member_ref'), 'page': page,
            'layout': args.get('layout', 'reading_order') if transformation == 'pdf_text' else None,
            'dpi': args.get('dpi', 150) if transformation == 'pdf_page' else None,
            'coordinate_system': 'original_member_bytes' if transformation == 'archive_member'
            else 'normalized_utf8_bytes' if transformation == 'pdf_text' else 'one_based_physical_pdf_page'},
            origin='tool')
        return ({'source_ref': source['id'], 'material_ref': material['id'], 'derivation_ref': derivative['id'],
                 'artifact_ref': source['artifact_ref'], 'media_type': media_type,
                 'image_source_ref': source['id'] if media_type.startswith('image/') else None, 'page': page,
                 **page_range, 'coordinate_system': derivative['coordinate_system'], 'provenance': metadata,
                 'biological_interpretation': 'not_performed'}, [source['id'], material['id'], derivative['id']])

    # -- public acquisition -----------------------------------------------------------------------------------------
    def _acquisition_request(self, name: str, args: dict, scope: dict | None) -> tuple[Any, dict]:
        if name in EXPERIMENT_DATABASE_TOOLS:
            return experimental_database_request, {'client': self.clients, 'operation': name, 'arguments': args}
        if name == 'public.literature.sequence_identity':
            return identity_request(self, args, scope)
        if name == 'public.pmc.versions':
            return self.clients.pmc_versions, args
        if name == 'public.pmc.files':
            selected = self.store.require(args['version_ref'], {'pmc_version'})
            return self.clients.pmc_files, {'prefix': selected['prefix'], **(
                {'continuation_token': args['continuation_token']} if 'continuation_token' in args else {})}
        if name == 'public.pmc.asset':
            asset = self.store.require(args['asset_ref'], {'pmc_asset', 'pmc_object'})
            selected = self.store.require(asset['version_ref'], {'pmc_version'})
            uri = asset.get('original_uri') or 's3://' + BUCKET + '/' + asset['object_key']
            return self.clients.pmc_asset, {'original_uri': uri, 'prefix': selected['prefix']}
        if name == 'public.ncbi.search':
            return self.clients.ncbi_search, args
        if name == 'public.ncbi.sequence':
            return self.clients.ncbi_sequence, args
        if name == 'public.taxonomy':
            return self.clients.taxonomy, args
        if name == 'public.literature.search':
            return self.clients.literature_search, args
        if name == 'public.literature.read':
            return self.clients.literature_read, args
        raise ContractError('a105_public_acquisition_not_implemented:' + name)

    def _perform(self, name: str, args: dict, scope: dict | None, snapshot: Any) -> tuple[dict, list[str]]:
        if name in EXPERIMENT_DATABASE_TOOLS:
            return publish_experimental_database(self, name, args, snapshot)
        if name == EXPERIMENT_RECORDS:
            return read_records(self, args, scope, self._permitted_record_refs.get())
        if name == 'public.literature.sequence_identity':
            return publish_identity(self, args, scope, snapshot)
        if name == 'source.sequence.references':
            return sequence_references(self, args, scope, self._permitted_record_refs.get())
        if isinstance(snapshot, DocumentOutput):
            return self._publish_document(name, args, snapshot)
        if isinstance(snapshot, PmcFiles):
            return self._publish_pmc_files(args, snapshot)
        if name == 'public.pmc.versions':
            return self._publish_pmc_versions(args, snapshot)
        if name == 'public.pmc.asset':
            return self._publish_pmc_asset(args, snapshot)
        if snapshot is not None:
            return self._import(name, args, snapshot)
        if name == 'state.query':
            return self._query(args, scope), []
        if name == 'source.read':
            return source_window(self.store, **args), []
        if name == 'source.locate':
            return locate_source(self.store, **args, permitted_inputs=self._permitted_record_refs.get(), scope=scope), []
        raise ContractError('a105_tool_not_implemented:' + name)

    def _query(self, args: dict, scope: dict | None) -> dict:
        def received(row):
            if row.get('record_type') == 'native_execution':
                raise ContractError('a105_native_execution_measurement_reader_not_implemented')
            return row
        if 'refs' in args:
            conflicting_fields = sorted(set(args) - {'refs'})
            if conflicting_fields:
                raise ContractError('exact_refs_cannot_be_combined_with_page_selectors', detail={
                    'selection_mode': 'exact_references', 'conflicting_fields': conflicting_fields,
                    'allowed_fields': ['refs']})
            rows = [self.store.get(item) for item in args['refs']]
            for row in rows:
                if row['record_type'] in {'input', 'feature', 'product', 'read_subject'} and \
                        not self.store.in_scope(row['id'], scope):
                    raise ContractError('subject_outside_assigned_scope')
            return {'records': [received(row) for row in rows], 'count': len(rows), 'next_offset': None}
        page = self.store.query_records(args.get('kind', 'hypothesis'), scope=scope, offset=args.get('offset', 0),
                                        limit=args.get('limit', 100), current_only=args.get('current_only', False),
                                        references=args.get('references'))
        page['records'] = [received(row) for row in page['records']]
        return page

    def _publish_pmc_versions(self, args: dict, snapshot: SourceSnapshot) -> tuple[dict, list[str]]:
        source = self._source(snapshot.service, None, snapshot=snapshot, accession=args['pmcid'])
        refs, versions = [source['id']], []
        page = parse_listing(snapshot.content)
        if page['prefix'] != args['pmcid'] + '.':
            raise ContractError('pmc_version_listing_scope_mismatch')
        for prefix in page['version_prefixes']:
            selected = self._put('pmc_version', {'source_ref': source['id'], **pmc_version(prefix, pmcid=args['pmcid'])},
                                 origin='external')
            refs.append(selected['id'])
            versions.append(selected)
        return ({'source_ref': source['id'], 'versions': versions,
                 'next_continuation_token': page['next_continuation_token'], 'listing_complete': not page['truncated'],
                 'version_preference': 'not_assigned',
                 'next_query': {'pmcid': args['pmcid'], 'continuation_token': page['next_continuation_token']}
                 if page['next_continuation_token'] else None}, refs)

    def _publish_pmc_files(self, args: dict, snapshots: PmcFiles) -> tuple[dict, list[str]]:
        selected = self.store.require(args['version_ref'], {'pmc_version'})
        listing = self._source(snapshots.listing.service, None, snapshot=snapshots.listing,
                               parent_source_refs=[selected['source_ref']])
        refs, objects, assets = [listing['id']], [], []
        page = parse_listing(snapshots.listing.content)
        if page['prefix'] != selected['prefix']:
            raise ContractError('pmc_file_listing_scope_mismatch')
        for item in page['objects']:
            record = self._put('pmc_object', {'source_ref': listing['id'], 'version_ref': selected['id'],
                                              'object_key': item['key'],
                                              **{key: item[key] for key in ('size', 'etag', 'last_modified')}},
                               origin='external')
            refs.append(record['id'])
            objects.append(record)
        metadata = None
        if snapshots.metadata is not None:
            metadata = self._source(snapshots.metadata.service, None, snapshot=snapshots.metadata,
                                    parent_source_refs=[listing['id']])
            refs.append(metadata['id'])
        catalog = self._put('pmc_catalog', {'source_ref': listing['id'], 'version_ref': selected['id'],
                                            'metadata_source_ref': metadata['id'] if metadata else None,
                                            'listing_complete': not page['truncated'],
                                            'next_continuation_token': page['next_continuation_token']}, origin='tool')
        refs.append(catalog['id'])
        body = {'source_ref': listing['id'], 'catalog_ref': catalog['id'], 'version_ref': selected['id'],
                'objects': objects, 'assets': assets, 'metadata_source_ref': metadata['id'] if metadata else None,
                'listing_complete': not page['truncated'], 'next_continuation_token': page['next_continuation_token'],
                'next_query': {'version_ref': selected['id'], 'continuation_token': page['next_continuation_token']}
                if page['next_continuation_token'] else None}
        if metadata is None:
            return body, refs
        try:
            native = json.loads(snapshots.metadata.content)
            errors = []
            for kind, field, uri in metadata_assets(native, selected):
                try:
                    actual = advertised_asset(uri, prefix=selected['prefix'])
                    record = self._put('pmc_asset', {'source_ref': metadata['id'], 'catalog_ref': catalog['id'],
                                                     'version_ref': selected['id'], 'asset_kind': kind,
                                                     'metadata_field': field, **actual}, origin='external')
                    refs.append(record['id'])
                    assets.append(record)
                except ContractError as error:
                    errors.append({'metadata_field': field, 'code': str(error)})
            body['article_metadata'] = native
            if errors:
                body['representation_feedback'] = {'category': 'representation',
                                                   'code': 'pmc_partial_asset_advertisements', 'fields': errors}
        except (ValueError, UnicodeError) as error:
            body['representation_feedback'] = {'category': 'representation', 'code': str(error)
                                               if isinstance(error, ContractError) else 'pmc_metadata_invalid_json'}
        return body, refs

    def _publish_pmc_asset(self, args: dict, snapshot: SourceSnapshot) -> tuple[dict, list[str]]:
        advertisement = self.store.require(args['asset_ref'], {'pmc_asset', 'pmc_object'})
        snapshot = replace(snapshot, request={**snapshot.request, 'selected_asset_ref': advertisement['id'],
                                              'selected_version_ref': advertisement['version_ref']})
        source = self._source(snapshot.service, None, snapshot=snapshot, parent_source_refs=[advertisement['source_ref']])
        material = self.store.register_material(source_ref=source['id'], format='opaque', use='evidence')
        self._written.append(material['id'])
        md5 = hashlib.md5(snapshot.content).hexdigest()
        advertised_md5 = advertisement.get('advertised_md5')
        body = {'source_ref': source['id'], 'material_ref': material['id'], 'asset_ref': advertisement['id'],
                'artifact_ref': source['artifact_ref'], 'actual_sha256': snapshot.sha256, 'actual_md5': md5,
                'advertised_md5': advertised_md5,
                'advertised_md5_matches': md5 == advertised_md5 if advertised_md5 else None,
                'original_advertisement': advertisement, 'target_binding_changed': False}
        if advertised_md5 is not None and md5 != advertised_md5:
            body['representation_feedback'] = {'category': 'provenance',
                                               'code': 'advertised_checksum_differs_from_actual_bytes',
                                               'actual_source_retained': True, 'source_ref': source['id']}
        return body, [source['id'], material['id']]

    def _import(self, name: str, args: dict, snapshot: SourceSnapshot) -> tuple[dict, list[str]]:
        text = article = None
        if name == 'public.literature.read':
            try:
                article = article_details(snapshot.content)
                paragraphs = article['sections']
            except ParseError as error:
                self._source(snapshot.service, None, snapshot=snapshot, accession=args.get('pmcid'))
                raise ContractError('literature_xml_parse_failed') from error
            text = '\n\n'.join(item['text'] for item in paragraphs)
        source = self._source(snapshot.service, None, snapshot=snapshot, text=text,
                              accession=args.get('accession', args.get('pmcid')),
                              publication_identifiers=article['publication_identifiers'] if article is not None else None)
        refs = [source['id']]
        if name == 'public.ncbi.sequence':
            records = []
            for sequence in parse_genbank(snapshot.content):
                molecule = 'protein' if args['database'] == 'protein' else \
                    'rna' if 'RNA' in sequence['annotations'].get('molecule_type', '') else 'dna'
                record = self._put('reference', {
                    'reference_type': molecule, 'source_ref': source['id'], 'accession': sequence['accession'],
                    'label': sequence['description'],
                    'sequence_ref': self.store.artifact(sequence['sequence'], 'text/plain')
                    if sequence['sequence_available'] else None,
                    'molecule': molecule, 'length': sequence['length'], 'term_refs': [], 'context_refs': []},
                    origin='external')
                refs.append(record['id'])
                records.append(record)
            return ({'source_ref': source['id'], 'records': records, 'count': len(records),
                     'original_feature_context_in_source': True}, refs)
        if name == 'public.literature.read':
            metadata_issues = list(article['metadata_issues'])
            reported = [item['value'] for item in article['publication_identifiers'] if item['namespace'] == 'pmcid']
            if reported and args['pmcid'] not in reported:
                metadata_issues.append({'code': 'requested_publication_identifier_mismatch', 'namespace': 'pmcid',
                                        'requested_value': args['pmcid']})
            return ({'source_ref': source['id'], 'text_ref': source['text_ref'], 'paragraph_count': len(paragraphs),
                     'publication_identifiers': article['publication_identifiers'], 'metadata_issues': metadata_issues,
                     'cited_publications': article['cited_publications'],
                     'citation_meaning': 'Bibliography discovery metadata from the retained article. Read the cited source to assess its actual reported evidence and scope.',
                     'text_bytes': len(text.encode()), 'text_representation': 'ordered_paragraph_projection',
                     'omitted_elements_available_in_original': True,
                     'original_read_query': {'source_ref': source['id'], 'representation': 'original'},
                     'read_with': 'source.read'}, refs)
        try:
            native = json.loads(snapshot.content)
        except ValueError:
            native = None
        return {'source_ref': source['id'], 'provider_result': native, 'raw_artifact_ref': source['artifact_ref']}, refs


__all__ = ['A105ToolRegistry']
