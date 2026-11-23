"""Private A110 source and sequence identity tools."""
from __future__ import annotations
import asyncio
from contextlib import ExitStack
from contextvars import ContextVar
from dataclasses import replace
from datetime import datetime, timezone
from importlib.metadata import version
import inspect
import json
import hashlib
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import ParseError
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.biochemical_feasibility_evidence.acquisition import AcquisitionError, PublicClients, SourceSnapshot, article_details, parse_genbank
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.api_error_feedback import api_error_feedback, api_error_response
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.domain import REF, REFS, RECORD_SCHEMAS, ContractError, canonical, identity, obj, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.calculations.chemistry import accession as chemical_accession, rhea_response, rhea_row, chebi_response, chemical_row
from gene_annotation_episode.episodic_workflow.episode_support.calculations.sequence_operations.biochemical_feasibility_evidence.sequence_ops import inspect_sequence, translate, translation_codes
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.biochemical_feasibility_evidence.local_jobs import LocalJobPolicy, run_cancellable_native
from gene_annotation_episode.local_resources import LocalResources
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_operations.sequence_mapping import VERSION as MAPPING_VERSION, extract_path, translation_mapping
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_operations.sequence_views import VERSION as VIEW_VERSION, view_sequence
from gene_annotation_episode.episodic_workflow.episode_support.readers.documents.biochemical_feasibility_evidence.material_parsing import FORMATS
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence import library_targets as libraries
from gene_annotation_episode import materials_packing as packing
from gene_annotation_episode.materials import source_window
from gene_annotation_episode.episodic_workflow.episode_support.readers.biochemical_feasibility_evidence.source_locations import locate as locate_source, locate_schema, received_source as received_location_source
from gene_annotation_episode.episodic_workflow.episode_support.tools.documents.biochemical_feasibility_evidence.document_tools import DocumentOutput, archive_extract, archive_inventory, pdf_native, resource as document_resource
from gene_annotation_episode.episodic_workflow.episode_support.tools.documents.biochemical_feasibility_evidence.spreadsheet_tools import xlsx_native, VERSION as XLSX_VERSION
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.biochemical_feasibility_evidence.literature_assets import PmcFiles, advertised_asset, metadata_assets, parse_listing, version as pmc_version, BUCKET
from gene_annotation_episode.episodic_workflow.episode_support.findings.biochemical_feasibility_evidence.image_evidence import prepare_image, visual_input, resolve_image_input as resolve_selected_image
from gene_annotation_episode.uniprot_native import parse_uniprot_native

def number(value: float, unit_ref: str | None=None) -> dict:
    return {'type': 'number', 'value': value, 'unit_ref': unit_ref}

def enum(value: str) -> dict:
    return {'type': 'enum', 'value': value}

def ref(value: str) -> dict:
    return {'type': 'reference', 'ref': value}

def measurements(**values: dict) -> list[dict]:
    return [{'name': key, 'value': value} for key, value in values.items()]
INTEGER = {'type': 'integer', 'minimum': 0}
POSITIVE = {'type': 'integer', 'minimum': 1}
TEXT = {'type': 'string', 'minLength': 1}

def uniprot_page_metadata(parsed):
    """Existing page-result keys projected from the already parsed page."""
    page = parsed["page"]
    return {"next_cursor": page["next_cursor"], "total_results": page["total_results"]["value"],
            "release": page["release"]["value"], "release_date": page["release_date"]["value"],
            "pagination_metadata_available": page["pagination_metadata_available"]}


def parse_uniprot_snapshot(snapshot, *, request):
    """Validate actual response custody before applying the pure native reader.

    The native parser receives a caller-supplied request. It cannot establish
    that the transport actually used that request; this adapter checks that
    separate relationship, without guessing missing request operands/status.
    """
    if snapshot is None or snapshot.service != "uniprot":
        raise ValueError("uniprot_response_required")
    if not isinstance(snapshot.request, dict):
        raise ValueError("uniprot_response_request_required")
    expected = {key: value for key, value in request.items() if key != "operation"}
    for key in ("accession", "query", "size", "cursor"):
        if key in expected and key not in snapshot.request:
            raise ValueError("uniprot_response_request_missing_" + key)
        if key in snapshot.request and (key not in expected or
                type(snapshot.request[key]) is not type(expected[key]) or
                snapshot.request[key] != expected[key]):
            raise ValueError("uniprot_response_request_conflict_" + key)
    if (set(snapshot.request) - (set(expected) | {"format"}) or
            snapshot.request.get("format", "json") != "json"):
        raise ValueError("uniprot_response_request_invalid")
    transport = snapshot.transport
    if not isinstance(transport, dict):
        raise ValueError("uniprot_response_transport_invalid")
    response = transport.get("response")
    if response is not None and not isinstance(response, dict):
        raise ValueError("uniprot_response_transport_invalid")
    response = response or {}
    for status in (transport.get("status"), response.get("status")):
        if status is not None and (type(status) is not int or not 200 <= status < 300):
            raise ValueError("uniprot_http_response_not_successful")
    if response.get("request_method") not in (None, "GET"):
        raise ValueError("uniprot_response_request_method_conflict")
    headers = response.get("headers", transport.get("headers"))
    if headers is not None and not isinstance(headers, dict):
        raise ValueError("uniprot_response_headers_invalid")
    return parse_uniprot_native(snapshot.content, request=request, response_headers=headers)


class ToolRegistry:

    def __init__(self, store: Any, *, clients: PublicClients | None=None, pdfinfo_executable: str | Path | None=None, pdftotext_executable: str | Path | None=None, pdftoppm_executable: str | Path | None=None, knowledge_library_directory: str | Path | None=None, job_limits: dict | None=None, native_statistics=None, local_resources: dict | None=None):
        self.store = store
        self.knowledge_library_directory = None if knowledge_library_directory is None else Path(knowledge_library_directory).expanduser().resolve()
        self.local_job_policy = LocalJobPolicy.from_config(job_limits)
        self.local_resources = LocalResources.configured(local_resources)
        if native_statistics is not None:
            from gene_annotation_episode.episodic_workflow.episode_support.jobs.biochemical_feasibility_evidence.ordinary_execution import OrdinaryExecutionStatistics
            if type(native_statistics) is not OrdinaryExecutionStatistics:
                raise TypeError('typed_ordinary_execution_statistics_required')
        self.native_statistics = native_statistics
        self.clients = clients or PublicClients()
        self._publications = ContextVar('annotation_tool_publications', default=None)
        self._publication_batch = ContextVar('annotation_native_publication_batch', default=None)
        self._mapping_directories = ContextVar('annotation_mapping_directories', default=None)
        self._native_execution_refs = ContextVar('annotation_native_execution_refs', default=None)
        self._grading_failures = ContextVar('annotation_tool_grading_failures', default=None)
        self._permitted_record_refs = ContextVar('annotation_tool_permitted_record_refs', default=None)
        self._current_invocation = ContextVar('annotation_tool_current_invocation', default=None)
        self.pdf_executables = {name: document_resource(path)['executable'] for name, path in (('pdfinfo', pdfinfo_executable), ('pdftotext', pdftotext_executable), ('pdftoppm', pdftoppm_executable))}

    def resource_binding(self) -> dict:
        return {'local_jobs': self.local_job_policy.to_dict(), 'local_resources': self.local_resources.as_record(), **({'knowledge_library_directory': str(self.knowledge_library_directory)} if self.knowledge_library_directory is not None else {}), **({'ordinary_execution_statistics': self.native_statistics.as_record()} if self.native_statistics is not None else {}), 'pdf_tools': {name: document_resource(path) for name, path in self.pdf_executables.items()}}

    def as_record(self):
        return {'a110_source_tools': {'version': 'a110_source_tool_registry', 'resources': self.resource_binding()}}

    @property
    def _written(self) -> list[str]:
        publications = self._publications.get()
        if publications is None:
            raise ContractError('publication_outside_tool_operation')
        return publications

    def catalog(self, scope: dict | None=None) -> dict[str, dict]:
        from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.biochemical_feasibility_evidence.literature_sequence_discovery import identity_schema, references_schema
        from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_operations.biochemical_feasibility_evidence.source_sequences import scan_schema
        from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_and_context_sources.biochemical_feasibility_evidence.ncbi_entrez_tools import ncbi_entrez_tool_contract
        from gene_annotation_episode.episodic_workflow.episode_support.acquisition.chemical_source_acquisition import PROVIDER_ARGUMENTS_SCHEMAS
        definitions = {'state.query': ('Read an exact page of typed scientific records, current revisions, or records referring to actual references. Follow the returned next_query for the same selection and order. Exact refs is a separate mode and cannot be combined with page selectors.', obj({'kind': {'enum': list(RECORD_SCHEMAS) + ['subject']}, 'offset': INTEGER, 'limit': POSITIVE, 'refs': {**REFS, 'description': 'Exact reference mode: supply refs alone, including an empty array for no records. Omit kind, offset, limit, current_only and references in this mode.'}, 'current_only': {'type': 'boolean'}, 'references': {'type': 'array', 'items': REF, 'minItems': 1, 'description': "Select records that refer to any supplied ID through reference fields or provenance anchors. This does not match a record's own ID; to read known records themselves, supply refs alone instead."}}, required=[])), 'source.read': ('Read a bounded UTF-8 byte window from an actual source. Choose original for retained source bytes, including XML tables/headings omitted by a paragraph projection; text selects that projection when available. Explicit stdout/stderr select retained native stream bytes when present, without falling back to another representation. Returned artifact/offsets support exact anchors.', obj({'source_ref': REF, 'offset': INTEGER, 'limit': POSITIVE, 'representation': {'enum': ['text', 'original', 'stdout', 'stderr']}}, ['source_ref'])), 'source.locate': ('Locate an exact supplied literal quote in an explicitly received original or text source representation. Return UTF-8 byte witnesses, unchanged neighboring context and bounded match continuation. Multiple occurrences remain separate. No normalization, scientific interpretation, measurement parsing or evidence credit is performed; no literal match means only no match in the examined bytes.', locate_schema()), 'image.view': ('Inspect one explicitly selected frame of a registered scientific image. The next reasoning call receives its actual pixels and exact source/frame metadata. Stored axes are preserved; no contrast adjustment, resizing, interpretation or annotation is performed. An optional RGB conversion is explicit and recorded; original bytes remain intact.', obj({'source_ref': REF, 'frame': INTEGER, 'colour_conversion': {'enum': ['preserve', 'rgb']}}, ['source_ref'])), 'public.pmc.versions': ('List one actual public PMC cloud version page. No version is chosen as latest/preferred; source versions can differ in manuscript status and can change in place.', obj({'pmcid': {'type': 'string', 'pattern': '^PMC[0-9]+$'}, 'continuation_token': TEXT}, ['pmcid'])), 'public.pmc.files': ("Read the selected advertised version's actual file inventory and its listed JSON metadata. Returns reusable listed-object/advertised-asset IDs; optional metadata failure preserves listed files. Choose a version ID, not a URL or guessed filename.", obj({'version_ref': REF, 'continuation_token': TEXT}, ['version_ref'])), 'public.pmc.asset': ('Acquire exactly one selected advertised/listed PMC asset ID. Preserve actual HTTP bytes, original advertisement and checksums; source content is evidence, not target annotation.', obj({'asset_ref': REF})), 'source.archive.members': ('Inventory one page of an actual ZIP/TAR source. Member IDs preserve ordinal identity, including duplicate names; no members are extracted or selected for you.', obj({'source_ref': REF, 'offset': INTEGER, 'limit': POSITIVE}, ['source_ref'])), 'source.archive.extract': ("Extract exactly one inventoried regular member to a source artifact; never follow a member's host path or link. Original archive and member identity remain attached.", obj({'member_ref': REF})), 'source.xlsx.sheets': ('Read the actual sheet names, relationship keys and package parts of a retained XLSX source. No sheet or biological interpretation is selected for you.', obj({'source_ref': REF})), 'source.xlsx.rows': ('Read a selected page of actual XLSX rows, optionally matching literal cell values. Select sheet_key from source.xlsx.sheets; row offsets count matching rows, while returned row numbers/cell addresses retain native identity. Header row is caller-selected or null. Original numeric/date lexical values, styles, formulas and caches remain distinct; no formula is recalculated or biology inferred.', obj({'source_ref': REF, 'sheet_key': TEXT, 'offset': INTEGER, 'limit': INTEGER, 'header_row': {'type': ['integer', 'null'], 'minimum': 1}, 'where': {**obj({'column': {'type': ['string', 'null'], 'pattern': '^[A-Z]+$'}, 'match': {'enum': ['equals', 'contains']}, 'value': TEXT, 'case_sensitive': {'type': 'boolean'}}), 'type': ['object', 'null']}})), 'source.pdf.info': ('Read native PDF information and physical page count for a selected actual source; no biological interpretation.', obj({'source_ref': REF})), 'source.pdf.text': ('Extract a selected physical PDF page or contiguous page range as a reusable UTF-8 text derivative. page is the first page; optional last_page is inclusive and defaults to page. Use source.pdf.info for the physical page count, then source.locate on the extracted text to find a section without guessing pages. Native page breaks and the selected range are retained. Byte offsets refer to this text derivative, not the PDF. No OCR or interpretation is performed.', obj({'source_ref': REF, 'page': POSITIVE, 'last_page': POSITIVE, 'layout': {'enum': ['reading_order', 'layout', 'raw']}}, ['source_ref', 'page'])), 'source.pdf.page': ('Render one explicitly selected physical PDF page as a reusable PNG source. Rendering does not by itself supply image input to a model or interpret a figure.', obj({'source_ref': REF, 'page': POSITIVE, 'dpi': {'type': 'number', 'exclusiveMinimum': 0}}, ['source_ref', 'page'])), 'material.parse': ('Parse a registered supplied asset under a chosen wrapper interpretation. Preserve valid independent members and exact original custody; evidence never enlarges annotation targets.', obj({'material_ref': REF, 'format': {'enum': FORMATS}}, ['material_ref'])), 'material.annotations': ('Page native supplied GenBank record metadata or feature assertions from one exact parse. These are source assertions, not current scientific annotations or accepted gene models. Bounded previews point to exact normalized JSONL byte windows for source.read; original GenBank bytes and their coordinate frame remain separate.', obj({'parse_ref': REF, 'record_ordinal': INTEGER, 'kind': {'enum': ['record', 'feature']}, 'offset': INTEGER, 'limit': POSITIVE}, ['parse_ref'])), 'material.from_source': ('Make an existing registered source reusable as evidence material, retaining its exact origin and bytes. This registers a wrapper and does not parse, classify or add annotation targets.', obj({'source_ref': REF, 'format': {'enum': FORMATS}}, ['source_ref'])), 'material.read': ('Read an exact bounded byte window of registered caller material as base64, including binary or unrecognized assets.', obj({'material_ref': REF, 'offset': INTEGER, 'limit': POSITIVE}, ['material_ref'])), 'material.members': ('Read a bounded page of an immutable parsed evidence collection in original record order; no read is made a credit target.', obj({'collection_ref': REF, 'offset': INTEGER, 'limit': POSITIVE}, ['collection_ref'])), 'material.errors': ('Read exact source-record/offset parser feedback; unparsed material remains available for another interpretation.', obj({'parse_ref': REF, 'offset': INTEGER, 'limit': POSITIVE}, ['parse_ref'])), 'material.member': ('Read a bounded sequence/quality window of one indexed source member and expose its reusable source-bound reference; infer no molecule, function or organism.', obj({'member_ref': REF, 'offset': INTEGER, 'limit': POSITIVE}, ['member_ref'])), 'material.header': ("Read an exact bounded UTF-8 byte window of a registered member's parser-returned title. Preserve its source and parser provenance; it is not the original file header bytes. Follow next_query for exact continuation.", obj({'member_ref': REF, 'offset': INTEGER, 'limit': POSITIVE}, ['member_ref'])), 'library.members': ('Page actual original reads of a fixed caller library in original member order. Returns stable lazy read_subject IDs and read-local metadata, not genes, organisms, joined coordinates or extra targets.', obj({'library_ref': REF, 'selection_ref': REF, 'offset': INTEGER, 'limit': POSITIVE}, ['library_ref'])), 'library.select': ('Freeze an explicitly chosen original-member subset for an investigation scope. Ordinal ranges select library inventory rows, never genomic intervals. No biology, pair identity or annotation is inferred.', obj({'library_ref': REF, 'member_refs': {'type': 'array', 'minItems': 1, 'items': REF}, 'ordinal_ranges': {'type': 'array', 'minItems': 1, 'items': obj({'start': INTEGER, 'end': POSITIVE})}}, ['library_ref'])), 'library.read': ("Read one actual original read's sequence and native quality window without turning the whole library into a sequence. Quality encoding and caller molecule declarations remain unchanged.", obj({'subject_ref': REF, 'offset': INTEGER, 'limit': POSITIVE}, ['subject_ref'])), 'sequence.inspect': ('Measure sequence composition and compatible alphabets; do not classify its biology.', obj({'subject_ref': REF})), 'sequence.view': ('Extract a reusable sequence view under the explicitly selected processing model; preserve original identity and coordinates. This does not classify the input and is not a prerequisite for direct searches.', obj({'subject_ref': REF, 'molecule': {'enum': ['dna', 'rna', 'protein']}, 'segments': {'type': 'array', 'minItems': 1, 'items': obj({'start': INTEGER, 'end': POSITIVE})}, 'orientation': {'enum': ['as_is', 'reverse_complement']}}, ['subject_ref', 'molecule'])), 'translation.codes': ('Read the installed NCBI translation tables; no code is selected for the input.', obj({})), 'sequence.translate': ('Derive one translation under an explicitly chosen code, interval and orientation; preserve the input.', obj({'subject_ref': REF, 'code': POSITIVE, 'strand': {'enum': ['+', '-']}, 'frame': {'enum': [0, 1, 2]}, 'start': INTEGER, 'end': POSITIVE, 'cds': {'type': 'boolean'}}, ['subject_ref', 'code'])), 'public.uniprot.search': ('Acquire one public reference page. Source annotations are not target annotations.', obj({'query': TEXT, 'size': {'type': 'integer', 'minimum': 1, 'maximum': 500}, 'cursor': TEXT}, ['query'])), 'public.uniprot.record': ('Acquire and pin an actual reference protein, its annotation, source features and evidence provenance.', obj({'accession': TEXT})), 'public.ncbi.search': ('Search one page of a named NCBI collection for selected references, taxa or sample context.', obj({'database': {'enum': ['protein', 'nuccore', 'assembly', 'taxonomy', 'biosample', 'bioproject', 'pubmed']}, 'term': TEXT, 'size': POSITIVE, 'offset': INTEGER}, ['database', 'term'])), 'public.ncbi.sequence': ('Acquire an external GenBank/GenPept sequence and its original feature context; optional nucleotide interval uses zero-based half-open coordinates.', obj({'accession': TEXT, 'database': {'enum': ['protein', 'nuccore']}, 'start': INTEGER, 'end': POSITIVE}, ['accession', 'database'])), 'public.taxonomy': ("Retrieve a taxon's source lineage record; it does not assign that taxon to the target.", obj({'taxon_id': POSITIVE})), 'public.literature.search': ('Acquire one literature search page. Read the actual source before extracting biological evidence.', obj({'query': TEXT, 'size': POSITIVE, 'cursor': TEXT}, ['query'])), 'public.literature.read': ("Acquire an actual open article, an ordered paragraph projection and separate cited-publication metadata. Bibliography identifiers and paragraph links support further source discovery; they do not identify the acquired article or establish a cited experiment's result. Read the retained original XML with source.read representation=original for tables, headings and other omitted elements.", obj({'pmcid': TEXT})), 'public.kegg.reaction': ('Acquire one literal KEGG reaction entry within the supplied byte limit. Retain the original flat-file text, ordered field and continuation lines, equation and native cross-references. Reaction direction in an organism, flux bounds and gene mappings are not inferred.', json.loads(canonical(PROVIDER_ARGUMENTS_SCHEMAS['public.kegg.reaction']))), 'public.reactome.record': ('Acquire one exact Reactome stable-ID ContentService record within the supplied byte limit. Retain all native species, compartments, inputs, outputs, components, references and inference flags when present. Do not traverse references or substitute a species search; absent fields remain absent.', json.loads(canonical(PROVIDER_ARGUMENTS_SCHEMAS['public.reactome.record']))), 'public.rhea.search': ('Search one explicitly limited Rhea JSON response. Returned left/right equation sides and native direction are database reaction facts, not substrates/products in the target organism. JSON search currently returns undefined-direction master records; no exhaustive absence or directional-variant resolution is claimed.', obj({'query': {'type': 'string'}, 'limit': POSITIVE}, ['query'])), 'public.rhea.reaction': ('Look up a selected Rhea accession through its JSON search interface. Preserve returned identity and direction; a directional accession may yield no search match. No automatic ID/direction substitution. Read native_record_ref with state.query for complete structured details.', obj({'accession': TEXT})), 'public.chebi.search': ("Search one selected ChEBI text-result page using the service's term parameter. Search summaries retain their source scope and scores/stars are never annotation acceptance rules. Follow next_query for later pages.", obj({'term': {'type': 'string'}, 'size': POSITIVE, 'page': POSITIVE}, ['term'])), 'public.chebi.compound': ("Retrieve a selected ChEBI compound's source chemistry, structure strings and ontology relations. These are chemical/source identities, not an enzyme assay, target substrate assignment or physiological role. Complete structured detail is available through native_record_ref using state.query.", obj({'accession': TEXT}))}
        result = {name: {'description': description, 'input_schema': schema} for name, (description, schema) in definitions.items()}
        from gene_annotation_episode.episodic_workflow.episode_support.acquisition.biochemical_feasibility_evidence.experimental_database_acquisition import catalog as experimental_database_catalog
        from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.experimental_database_records import READER as EXPERIMENT_RECORDS, reader_schema
        result.update(experimental_database_catalog())
        result[EXPERIMENT_RECORDS] = {'description': 'Inspect one page of a received experimental database response. Return native assay records, source measurement selectors and literal record links. Optional contains and contains_all filter retained rows by one or several literal terms, including their native headers and section labels. Record and whole-page link continuations are separate. These records locate the chemical or reaction source evidence; metadata and deposited scores retain their native meanings.', 'input_schema': reader_schema()}
        result['public.literature.sequence_identity'] = {'description': 'Find publication leads from a supplied protein sequence: retrieve one UniProtKB checksum-search page and verify each complete residue string. Return all equal records on the page, names, organisms, citation counts and explicit continuation. The optional reviewed filter selects database curation status. These are source identities and discovery metadata; experimental evidence requires reading the actual publications.', 'input_schema': identity_schema()}
        result['source.sequence.references'] = {'description': 'Read a page of publication identifiers, titles and reported citation scopes from a received sequence-identity response. Reverify full sequence equality for the selected record. Citation metadata supplies leads; it does not establish experimental results.', 'input_schema': references_schema()}
        result['source.sequence.scan'] = {'description': 'Recognize candidate protein sequence blocks in received source text/XML/HTML, preserving original UTF-8 positions. Normalize case, whitespace, numbering and soft hyphens; report exact containment, extra residues and literal differences. For numbered GenBank/GenPept blocks, include the ORIGIN marker and contiguous residue rows in the selected window. Hard hyphens remain explicit, with conditional correspondence, until their byte offsets are selected as formatting_hyphen_offsets after inspecting the layout. A document boundary may require an overlapping window. No biological gaps, tags or substitutions are silently removed.', 'input_schema': scan_schema()}
        for name, native in (('source.pdf.info', 'pdfinfo'), ('source.pdf.text', 'pdftotext'), ('source.pdf.page', 'pdftoppm')):
            result[name]['configuration'] = {**document_resource(self.pdf_executables[native]), 'job_limits': self.local_job_policy.to_dict()}
        for name in ('source.xlsx.sheets', 'source.xlsx.rows'):
            result[name]['configuration'] = {'adapter_version': XLSX_VERSION, 'job_limits': self.local_job_policy.to_dict(), 'execution': 'isolated_store_free_worker'}
            if self.native_statistics is not None:
                result[name]['configuration']['timing_statistics'] = self.native_statistics.as_record()
        if self.native_statistics is not None:
            result['execution.estimate'] = {'description': 'Obtain recorded duration expectations before a proposed workbook selection. Uses the same operands, actual settings and caller resource as execution. Creates no native job or scientific evidence; missing history stays unknown. This is an optional information tool, not a scheduling or continuation decision.', 'input_schema': {'anyOf': [obj({'tool': {'const': name}, 'arguments': result[name]['input_schema']}) for name in ('source.xlsx.sheets', 'source.xlsx.rows')]}}
        result['public.ncbi.entrez'] = ncbi_entrez_tool_contract()
        result['public.pubchem.compound'] = {'description': 'Acquire one selected PubChem compound record with its native chemical identity and retained source fields.', 'input_schema': PROVIDER_ARGUMENTS_SCHEMAS['public.pubchem.compound']}
        return result

    def _check_target(self, reference: str, scope: dict | None, *, footprint: list[dict] | None=None) -> dict:
        row = self.store.get(reference)
        footprint = self.store.coverage(reference) if footprint is None else footprint
        normalized = self.store.validate_scope(scope)
        allowed = set(normalized['subject_refs'])
        if not footprint or any((item['target_ref'] not in allowed for item in footprint)):
            raise ContractError('subject_outside_assigned_scope')
        if not self.store.scope_covers(footprint, normalized):
            raise ContractError('requested_measurement_outside_assigned_segments_or_members' if any(('member_ref' in span for span in footprint)) else 'requested_measurement_outside_assigned_segments')
        return row

    def _sequence(self, reference: str, *, molecule_model: str | None=None) -> str:
        row = self.store.get(reference)
        if row.get('record_type') == 'read_subject':
            member = self.store.get(row['member_ref'])
            return packing.component_window(self.store, member, 'sequence', 0, row['length']).decode('ascii')
        if libraries.is_library(row):
            raise ContractError('library_is_not_a_sequence_operand')
        if row.get('sequence_ref'):
            return self.store.get_artifact(row['sequence_ref']).decode('ascii')
        if row.get('record_type') == 'feature':
            parent = self._sequence(row['subject_ref'], molecule_model=molecule_model)
            sequence = ''.join((parent[item['start']:item['end']] for item in row['segments']))
            if row['strand'] == '-':
                known_model = self.store.subject_molecule(row['subject_ref'])
                model = known_model if known_model != 'unspecified' else molecule_model
                try:
                    return view_sequence(sequence, molecule=model, orientation='reverse_complement')['sequence']
                except ValueError as error:
                    raise ContractError(str(error)) from error
            return sequence
        raise ContractError('referenced_record_has_no_sequence')

    def _check_sequence_operand(self, reference: str, scope: dict | None, *, footprint: list[dict] | None=None) -> dict:
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

    def _source(self, provider: str, body: Any, *, snapshot: SourceSnapshot | None=None, text: str | None=None, accession: str | None=None, software_version: str | None=None, parent_source_refs: list[str] | None=None, stdout_ref: str | None=None, stderr_ref: str | None=None, auxiliary_artifact_refs: list[str] | None=None, operand_refs: list[str] | None=None, query_selection_ref: str | None=None, publication_identifiers: list[dict] | None=None, tool_grading: dict | None=None) -> dict:
        artifact = self.store.artifact(snapshot.content if snapshot else canonical(body), snapshot.media_type if snapshot else 'application/json')
        if tool_grading is not None:
            from gene_annotation_episode.episodic_workflow.episode_support.grading.biochemical_feasibility_evidence.tool_grading_artifacts import retain_tool_grading
            retained = retain_tool_grading(self.store, provider=provider, native_artifact_ref=artifact, grading=tool_grading)
            auxiliary_artifact_refs = list(dict.fromkeys([*(auxiliary_artifact_refs or ()), retained]))
        request = None
        if snapshot:
            request = self.store.artifact(canonical({'request': snapshot.request, 'transport': snapshot.transport}), 'application/json')
            if software_version is None and provider not in {'alphafold', 'emdb', 'rcsb_pdb', 'string', 'kegg', 'reactome', 'quickgo', 'pubchem', 'hpa', 'ucsc', 'ensembl', 'eva', 'gnomad', 'public.ncbi.entrez', 'public.ncbi.geo', 'public.ncbi.sra.file', 'public.jaspar', 'public.encode', 'public.screen'}:
                if snapshot.service == 'uniprot':
                    transport = snapshot.transport if isinstance(snapshot.transport, dict) else {}
                    response = transport.get('response')
                    headers = response.get('headers', transport.get('headers')) if isinstance(response, dict) else transport.get('headers')
                    candidate = headers.get('x-uniprot-release') if isinstance(headers, dict) else None
                    try:
                        validate_schema(candidate, RECORD_SCHEMAS['source']['properties']['version'])
                    except ContractError:
                        candidate = None
                    software_version = candidate
                elif snapshot.service not in {'rcsb_pdb', 'alphafold', 'emdb', 'string', 'kegg', 'reactome', 'quickgo', 'pubchem', 'hpa', 'ucsc', 'ensembl', 'eva', 'gnomad'}:
                    details = snapshot.transport.get('job_details') or {}
                    database = details.get('database')
                    software_version = (database.get('version') if isinstance(database, dict) else None) or snapshot.transport.get('response', {}).get('headers', {}).get('x-uniprot-release')
        return self._put('source', {'provider': provider, 'accession': accession, 'uri': snapshot.url if snapshot else None, 'artifact_ref': artifact, 'text_ref': self.store.artifact(text, 'text/plain') if text is not None else None, 'request_ref': request, 'version': software_version, 'retrieved_at': snapshot.retrieved_at if snapshot else datetime.now(timezone.utc).isoformat(), **({'parent_source_refs': parent_source_refs} if parent_source_refs is not None else {}), **({'stdout_ref': stdout_ref} if stdout_ref is not None else {}), **({'stderr_ref': stderr_ref} if stderr_ref is not None else {}), **({'auxiliary_artifact_refs': auxiliary_artifact_refs} if auxiliary_artifact_refs is not None else {}), **({'operand_refs': operand_refs} if operand_refs is not None else {}), **({'query_selection_ref': query_selection_ref} if query_selection_ref is not None else {}), **({'publication_identifiers': publication_identifiers} if publication_identifiers else {})}, origin='external' if snapshot else 'tool')

    def _observation(self, kind: str, subjects: list[str], source: dict, values: list[dict], *, references: list[str] | None=None, dependencies: list[str] | None=None, operand_intervals: list[dict] | None=None) -> dict:
        return self._put('observation', {'kind': kind, 'subject_refs': subjects, 'source_subject_refs': references or [], 'source_ref': source['id'], 'measurements': values, 'dependencies': dependencies or [], 'anchor': None, 'operand_intervals': operand_intervals}, origin='tool')

    def _put(self, kind: str, record: dict, **kwargs: Any) -> dict:
        result = self.store.put(kind, record, **kwargs)
        self._written.append(result['id'])
        return result

    def _grade_supplied_result(self, grader, *args, **kwargs):
        """Preserve native evidence when a grading input contract rejects it."""
        try:
            return grader(*args, **kwargs)
        except ValueError as error:
            failure = {'code': str(error), 'category': 'grading_input'}
            failures = self._grading_failures.get()
            if failures is not None:
                failures.append(failure)
            return {'sheet': None, 'scores': None, 'failure': failure}

    @staticmethod
    def _grading_values(scores, names):
        return measurements(**{name: number(scores[name]) for name in names if type(scores.get(name)) in (int, float)})

    def _composition_grading(self, subject, sequence):
        from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_operations.sequence_composition_grader import grade_sequence_composition
        member_ref = subject.get('member_ref') if subject['record_type'] == 'read_subject' else subject.get('source_record', {}).get('member_ref') if subject['record_type'] == 'input' else None
        quality, encoding = (None, None)
        if member_ref:
            member = self.store.get(member_ref)
            encoding = member.get('quality_encoding')
            if packing.component_info(self.store, member, 'quality') is not None:
                quality = b''.join(packing.component_chunks(self.store, member, 'quality')).decode('ascii')
        return self._grade_supplied_result(grade_sequence_composition, sequence, molecule=self.store.subject_molecule(subject['id']), quality=quality, quality_encoding=encoding)

    @classmethod
    def _composition_values(cls, grading):
        return cls._grading_values(grading.get('scores') or {}, ('unambiguous_nucleotide_count', 'ambiguous_symbol_count', 'ambiguity_fraction', 'gc_count', 'gc_denominator', 'quality_observation_count', 'mean_phred', 'mean_error_probability', 'expected_error_count'))

    def _begin_publication_batch(self, *, failures: bool=False) -> dict:
        """Declare generated publication metadata, never a scientific verdict.

        Mutable counters belong to this selected operation. Keeping the same
        declaration until _save also preserves truthful partial-publication
        counts when a later native row fails.
        """
        batch = {'representation': 'native_publications', 'published_rows_total': 0, 'failure_rows_total': 0 if failures else None, 'observation_query': None}
        self._publication_batch.set(batch)
        return batch

    @staticmethod
    def _batch_observations(batch: dict, source_ref: str) -> None:
        batch['observation_query'] = {'kind': 'observation', 'references': [source_ref], 'offset': 0}

    def execute(self, name: str, args: dict, *, scope: dict | None=None, operation_key: str | None=None, permitted_record_refs=None) -> dict:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.execute_async(name, args, scope=scope, operation_key=operation_key, permitted_record_refs=permitted_record_refs))
        raise ContractError('use_execute_async_in_running_event_loop')

    def _check_source_bytes(self, name, arguments):
        """Apply the finite Source/File receipt policies before byte tools."""
        if name in {'material.parse', 'material.read'}:
            material = self.store.require(arguments['material_ref'], {'material'})
            source = self.store.require(material['source_ref'], {'source'})
            artifact_ref = source['artifact_ref']
        elif name in {'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.archive.members', 'source.xlsx.sheets', 'source.xlsx.rows', 'source.pdf.info', 'source.pdf.text', 'source.pdf.page', 'image.view'}:
            source = self.store.require(arguments['source_ref'], {'source'})
            if name in {'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references'}:
                from gene_annotation_episode.materials import source_window_selection
                representation = 'original' if name == 'source.sequence.references' else arguments.get('representation', 'text')
                artifact_ref, _, _ = source_window_selection(source, representation)
            else:
                artifact_ref = source['artifact_ref']
        else:
            return
        permitted = self._permitted_record_refs.get()
        if permitted is not None and source['id'] not in permitted:
            raise ContractError('source_bytes_not_received')

    async def execute_async(self, name: str, args: dict, *, scope: dict | None=None, operation_key: str | None=None, permitted_record_refs=None) -> dict:
        if permitted_record_refs is None and name in {'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.experimental.records'}:
            invocation = self._current_invocation.get()
            if invocation is not None and operation_key is not None and (invocation[2:] == (name, args, operation_key)) and (invocation[0].scope == scope):
                permitted_record_refs = tuple(invocation[0].received_record_refs)
        if permitted_record_refs is not None and (not isinstance(permitted_record_refs, (list, tuple)) or any((not isinstance(ref, str) or not ref for ref in permitted_record_refs))):
            raise ContractError('explicit_permitted_record_refs_required')
        if name == 'source.locate':
            try:
                canonical(args)
            except (TypeError, ValueError):
                return {'status': 'invalid', 'operation_ref': None, 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': 'source_location_arguments_not_json'}}
        token = self._publications.set([])
        batch_token = self._publication_batch.set(None)
        directories = self._mapping_directories.set(ExitStack())
        native_receipts = self._native_execution_refs.set([])
        grading_failures = self._grading_failures.set([])
        permitted = self._permitted_record_refs.set(None if permitted_record_refs is None else tuple(permitted_record_refs))
        try:
            return await self._execute_operation_async(name, args, scope=scope, operation_key=operation_key)
        finally:
            self._mapping_directories.get().close()
            self._mapping_directories.reset(directories)
            self._native_execution_refs.reset(native_receipts)
            self._grading_failures.reset(grading_failures)
            self._permitted_record_refs.reset(permitted)
            self._publications.reset(token)
            self._publication_batch.reset(batch_token)

    async def _execute_operation_async(self, name: str, args: dict, *, scope: dict | None=None, operation_key: str | None=None) -> dict:
        operation_key = operation_key or identity('manual_operation', {'name': name, 'args': args, 'time': datetime.now(timezone.utc).isoformat()})
        from gene_annotation_episode.episodic_workflow.episode_support.acquisition.chemical_source_acquisition import OPERATIONS as CHEMICAL_SOURCE_OPERATIONS, PROVIDER_FAILURE_CODES, validate_provider_receipt
        ordinary_data_getters = {'public.ncbi.entrez', *CHEMICAL_SOURCE_OPERATIONS}
        getter_failure_codes = {name: PROVIDER_FAILURE_CODES for name in CHEMICAL_SOURCE_OPERATIONS}
        getter_validators = {name: validate_provider_receipt for name in CHEMICAL_SOURCE_OPERATIONS}
        getter_source_providers = {name: name.split('.')[1] for name in CHEMICAL_SOURCE_OPERATIONS}
        operation_ref = identity('operation', {'key': operation_key, 'name': name, 'arguments': args})
        result = {'status': 'invalid', 'operation_ref': operation_ref, 'record_refs': [], 'result': None, 'feedback': None}
        try:
            catalog = self.catalog(scope)
            if name not in catalog:
                raise ContractError('unknown_tool')
            validate_schema(args, catalog[name]['input_schema'])
            self.store.validate_scope(scope)
            self._check_source_bytes(name, args)
            snapshot = self._estimate_native(args, scope) if name == 'execution.estimate' else await self._document_async(name, args) if name.startswith(('source.archive.', 'source.pdf.', 'source.xlsx.')) else await self._acquire_async(name, args, scope, operation_key) if name.startswith('public.') else None
            with self.store.transaction():
                try:
                    result['result'], result['record_refs'] = self._perform(name, args, scope, snapshot)
                    result['status'] = 'completed'
                    if name in ordinary_data_getters and (not result['result']['acquired']):
                        result.update(status='partial', feedback={'category': 'acquisition', 'code': result['result']['failure_code'], 'source_ref': result['result']['source_ref']})
                        if name == 'public.ncbi.entrez' and result['result']['failure_code'] == 'ncbi_entrez_native_error_response' and (result['result']['source_ref'] is not None):
                            result['feedback']['response'] = api_error_response(snapshot)
                            result['feedback']['detail'] = {'explanation': 'The complete returned NCBI error response is included in feedback.response. For searches, inspect errorlist and querytranslation even when hits are present before choosing any revised request.', 'read_with': 'source.read', 'read_query': {'source_ref': result['result']['source_ref'], 'representation': 'original', 'offset': 0}}
                    if name == 'image.view':
                        result['visual_inputs'] = [visual_input(self.store, result['result']['view_ref'])]
                    if name == 'material.parse':
                        attempt = result['result']['parse_attempt']
                        result['status'] = attempt['status']
                        if attempt['status'] != 'completed':
                            result['feedback'] = {'category': 'representation', 'code': attempt['code'], 'parse_ref': attempt['id']}
                    if name == 'source.xlsx.rows' and result['result']['status'] != 'completed':
                        result.update(status=result['result']['status'], feedback={'category': 'representation', 'code': 'xlsx_rows_partially_decoded', 'source_ref': result['result']['source_ref'], 'cell_error_count': result['result']['cell_error_count'], 'row_error_count': result['result']['row_error_count'], 'parse_failures': result['result']['parse_failures']})
                    if name in {'public.uniprot.record', 'public.uniprot.search'} and result['result'].get('projection_errors'):
                        result.update(status='partial', feedback={'category': 'representation', 'code': 'uniprot_rows_partially_projected', 'source_ref': result['result']['source_ref'], 'rows': result['result']['projection_errors']})
                    if name in {'public.rhea.search', 'public.rhea.reaction', 'public.chebi.search', 'public.chebi.compound'} and result['result'].get('projection_errors'):
                        result.update(status='partial', feedback={'category': 'representation', 'code': 'chemistry_rows_partially_projected', 'source_ref': result['result']['source_ref'], 'rows': result['result']['projection_errors']})
                    if name in {'public.uniprot.record', 'public.uniprot.search'} and result['result'].get('projection_errors'):
                        result.update(status='partial', feedback={'category': 'representation', 'code': 'uniprot_rows_partially_projected', 'source_ref': result['result']['source_ref'], 'rows': result['result']['projection_errors']})
                    if isinstance(snapshot, PmcFiles) and snapshot.error:
                        result.update(status='partial', feedback={**api_error_feedback(snapshot.error), 'category': 'provider', 'code': snapshot.error.code, 'diagnostic_ref': self._acquisition_diagnostic(snapshot.error)})
                    if name in {'public.pmc.files', 'public.pmc.asset'} and result['result'].get('representation_feedback'):
                        feedback = result['result']['representation_feedback']
                        if isinstance(snapshot, PmcFiles) and snapshot.error:
                            feedback = {**feedback, 'acquisition_error': result['feedback']}
                        result.update(status='partial', feedback=feedback)
                except Exception as error:
                    if not self._written:
                        raise
                    if name in ordinary_data_getters:
                        sources = [reference for reference in dict.fromkeys(self._written) if self.store.get(reference).get('record_type') == 'source' and self.store.get(reference).get('provider') == getter_source_providers.get(name, name)]
                        failure_code = str(error) if isinstance(error, ContractError) else 'data_acquisition_publication_incomplete'
                        if name in getter_failure_codes and failure_code not in getter_failure_codes[name]:
                            failure_code = 'data_acquisition_publication_incomplete'
                        result.update(status='partial', record_refs=sources, changed_record_refs=sources, result={'acquired': False, 'source_ref': sources[0] if sources else None, 'data_ref': None, 'failure_code': failure_code}, feedback={'category': 'acquisition', 'code': failure_code, 'diagnostic_ref': self.store.artifact(f'{type(error).__name__}: {error}', 'text/plain')})
                        if name in getter_validators:
                            result['result'] = getter_validators[name](result['result'])
                    else:
                        result.update(status='partial', record_refs=list(dict.fromkeys(self._written)), result={'retained_record_refs': list(dict.fromkeys(self._written))}, feedback={'category': 'partial_execution', 'code': str(error) if isinstance(error, ContractError) else 'adapter_partial_result', 'diagnostic_ref': self.store.artifact(f'{type(error).__name__}: {error}', 'text/plain')})
                    if isinstance(error, ContractError) and error.detail:
                        result['feedback']['detail'] = error.detail
                    result['feedback'].update(api_error_feedback(error))
                self._save(operation_key, name, args, scope, result)
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
                diagnostic = self.store.artifact(canonical({'representation': 'local_exception', 'details': error.diagnostic}), 'application/json')
            result.update(status='unavailable' if error.code.endswith(('not_configured', 'not_installed', 'missing')) else 'failed', feedback={**api_error_feedback(error), 'category': 'execution' if error.code.startswith('local_job_') or error.phase in {'native_execution', 'local_execution', 'local_preflight', 'local_admission'} else 'provider', 'code': error.code, 'retry_after': error.retry_after, 'job_ref': error.job_ref, 'diagnostic_ref': diagnostic, **({'phase': error.phase} if error.phase is not None else {}), **operational})
        except (ContractError, ValueError, KeyError) as error:
            result['feedback'] = {**api_error_feedback(error), 'category': 'arguments_or_reference', 'code': str(error) if isinstance(error, ContractError) else 'invalid_tool_input'}
            if isinstance(error, ContractError) and error.detail:
                result['feedback']['detail'] = error.detail
        except Exception as error:
            diagnostic = self.store.artifact(f'{type(error).__name__}: {error}', 'text/plain')
            result.update(status='failed', feedback={**api_error_feedback(error), 'category': 'execution', 'code': 'adapter_execution_failed', 'diagnostic_ref': diagnostic})
        if name in ordinary_data_getters and result['result'] is None:
            failure_code = (result.get('feedback') or {}).get('code', 'data_acquisition_failed')
            if name in getter_failure_codes and failure_code not in getter_failure_codes[name]:
                failure_code = 'invalid_tool_input' if result['status'] == 'invalid' else 'data_acquisition_failed'
            result['result'] = {'acquired': False, 'source_ref': None, 'data_ref': None, 'failure_code': failure_code}
            if name in getter_validators:
                result['result'] = getter_validators[name](result['result'])
        with self.store.transaction():
            self._save(operation_key, name, args, scope, result)
        return result

    def _save(self, key: str, name: str, args: dict, scope: dict | None, result: dict) -> None:
        failures = self._grading_failures.get()
        if failures:
            if result['status'] == 'completed':
                result['status'] = 'partial'
            if result.get('feedback') is None:
                result['feedback'] = {'category': 'grading_input', 'code': 'tool_grading_input_rejected', 'failures': list(failures)}
            else:
                result['feedback']['grading_failures'] = list(failures)
        receipts = self._native_execution_refs.get()
        if receipts:
            result['native_execution_refs'] = list(dict.fromkeys(receipts))
            result['record_refs'] = list(dict.fromkeys([*result['record_refs'], *receipts]))
        batch = self._publication_batch.get()
        if batch is not None:
            result['published_batch'] = dict(batch)

    def _estimate_native(self, args, scope):
        from gene_annotation_episode.episodic_workflow.episode_support.jobs.biochemical_feasibility_evidence.execution_expectations import capture_execution_scopes
        _, path, operation, selected = self._spreadsheet_arguments(args['tool'], args['arguments'])
        execution_class = self.native_statistics.spreadsheet_class(path, operation, selected, self.local_job_policy)
        recovery = self.native_statistics.recover_pending_statistics()
        return {'tool': args['tool'], 'arguments': args['arguments'], 'execution_expectations': {**capture_execution_scopes(self.native_statistics.history_path, [execution_class]), 'statistics_recovery': recovery}}

    def _record_native_execution(self, metadata, *, operation, operands):
        """Retain actual timing independently of scientific publication success."""
        from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.execution_recording import NativeMeasurement
        from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.biochemical_feasibility_evidence.native_timing_information import record_native_measurement
        measured = (metadata.get('statistics_export') or {}).get('measurement')
        if measured is None:
            return
        measurement = NativeMeasurement.from_record(measured)
        reference = record_native_measurement(self.store, measurement, operation=operation, operands=operands)
        self._native_execution_refs.get().append(reference)
        metadata['native_execution_ref'] = reference

    @staticmethod
    async def _native_thread_async(function, *args, **kwargs):
        """Cancellation waits for the native adapter to reap its process tree."""
        return await run_cancellable_native(function, *args, **kwargs)

    def resolve_image_input(self, selected: dict) -> dict:
        return resolve_selected_image(self.store, self._mapping_directories.get().enter_context(self.store.scratch("image")), selected)

    def _artifact_file(self, ref):
        """A file holding the bytes of the held artifact ``ref``, in a scratch directory of the running unit
        (removed when the tool call ends), for a native program or a reader that needs a path."""
        return self._mapping_directories.get().enter_context(self.store.scratch('input')).copy_artifact(ref, 'input')

    def _spreadsheet_arguments(self, name, args):
        source = self.store.require(args['source_ref'], {'source'})
        path = self._artifact_file(source['artifact_ref'])
        return (source, path, name.rsplit('.', 1)[1], {key: value for key, value in args.items() if key != 'source_ref'})

    async def _document_async(self, name: str, args: dict) -> DocumentOutput:
        if self.store.in_transaction():
            raise ContractError('native_document_work_requires_no_active_store_transaction')
        if name.startswith('source.xlsx.'):
            source, path, operation, arguments = self._spreadsheet_arguments(name, args)
            member = None
        elif name == 'source.archive.extract':
            member = self.store.require(args['member_ref'], {'archive_member'})
            source = self.store.require(member['source_ref'], {'source'})
            path = self._artifact_file(source['artifact_ref'])
        else:
            member = None
            source = self.store.require(args['source_ref'], {'source'})
            path = self._artifact_file(source['artifact_ref'])
        if name == 'source.archive.members':
            output = await asyncio.to_thread(archive_inventory, path, offset=args.get('offset', 0), limit=args.get('limit', 50))
        elif name == 'source.archive.extract':
            output = await asyncio.to_thread(archive_extract, path, member)
        elif name.startswith('source.xlsx.'):
            operands = [{'role': 'input_source', 'subject_ref': source['id']}]
            try:
                output = await self._native_thread_async(xlsx_native, path, operation=operation, arguments=arguments, job_limits=self.local_job_policy.to_dict(), **{'statistics': self.native_statistics.for_spreadsheet(path, operation, arguments, self.local_job_policy)} if self.native_statistics is not None else {})
            except AcquisitionError as error:
                metadata = error.operational or {}
                self._record_native_execution(metadata.get('native', metadata), operation='xlsx_' + operation, operands=operands)
                raise
            self._record_native_execution((output.metadata.get('local_jobs') or {}).get('work', {}), operation='xlsx_' + operation, operands=operands)
        else:
            operation = name.rsplit('.', 1)[1]
            if operation == 'text' and args.get('last_page', args['page']) < args['page']:
                raise ContractError('pdf_page_range_reversed')
            output = await self._native_thread_async(pdf_native, path, operation=operation, executables=dict(self.pdf_executables), job_limits=self.local_job_policy.to_dict(), first_page=args.get('page'), last_page=args.get('last_page', args.get('page')), page=args.get('page'), layout=args.get('layout', 'reading_order'), dpi=args.get('dpi', 150))
        output = replace(output, metadata={**output.metadata, 'parent_source_ref': source['id'], 'input_artifact_ref': source['artifact_ref']})
        if output.metadata.get('returncode', 0) != 0:
            details = {**output.metadata, 'stdout_ref': self.store.artifact(output.stdout, 'text/plain'), 'stderr_ref': self.store.artifact(output.stderr, 'text/plain')}
            if output.content:
                details['partial_output_ref'] = self.store.artifact(output.content, output.media_type)
            raise AcquisitionError('pdf_native_error', phase='native_execution', operational={'native_returncode': output.metadata['returncode'], 'native_stderr_tail': output.stderr[-4000:].decode('utf-8', errors='replace'), 'diagnostic_ref': self.store.artifact(canonical(details), 'application/json')})
        return output

    def _source_bytes(self, provider: str, content: bytes, media_type: str, metadata: dict) -> dict:
        artifact = self.store.artifact(content, media_type)
        return self._put('source', {'provider': provider, 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact if media_type.startswith('text/') else None, 'request_ref': self.store.artifact(canonical(metadata), 'application/json'), 'version': metadata.get('software_version') or metadata.get('adapter_version'), 'parent_source_refs': [metadata['parent_source_ref']], 'stdout_ref': metadata['stdout_ref'], 'stderr_ref': metadata['stderr_ref'], 'retrieved_at': metadata.get('finished_at') or datetime.now(timezone.utc).isoformat()}, origin='tool')

    def _publish_document(self, name: str, args: dict, output: DocumentOutput) -> tuple[dict, list[str]]:
        metadata = {**output.metadata, 'stdout_ref': self.store.artifact(output.stdout, 'text/plain'), 'stderr_ref': self.store.artifact(output.stderr, 'text/plain')}
        if name.startswith('source.xlsx.'):
            source = self._source_bytes(name.removeprefix('source.'), output.content, 'application/json', metadata)
            return ({**json.loads(output.content), 'source_ref': source['id'], 'xlsx_source_ref': args['source_ref'], 'artifact_ref': source['artifact_ref'], 'provenance': metadata, 'biological_interpretation': 'not_performed'}, [source['id']])
        if name == 'source.archive.members':
            source = self._source('archive.inventory', metadata, parent_source_refs=[args['source_ref']], stdout_ref=metadata['stdout_ref'], stderr_ref=metadata['stderr_ref'])
            refs, members = ([source['id']], [])
            for entry in metadata['members']:
                member = self._put('archive_member', {'source_ref': args['source_ref'], 'archive_format': metadata['archive_format'], **entry}, origin='tool')
                refs.append(member['id'])
                members.append(member)
            next_query = {**args, 'offset': metadata['next_offset'], 'limit': metadata['limit']} if metadata['next_offset'] is not None else None
            return ({'source_ref': source['id'], 'archive_source_ref': args['source_ref'], 'members': members, **{key: metadata[key] for key in ('offset', 'limit', 'total', 'next_offset')}, 'next_query': next_query}, refs)
        if name == 'source.pdf.info':
            source = self._source_bytes('poppler.pdfinfo', output.content, 'text/plain', metadata)
            return ({'source_ref': source['id'], 'pdf_source_ref': args['source_ref'], 'page_count': metadata.get('page_count'), 'native_information': output.content.decode('utf-8'), 'provenance': metadata}, [source['id']])
        media_type = output.media_type
        if name == 'source.archive.extract':
            if output.content.startswith(b'%PDF-'):
                media_type = 'application/pdf'
            elif output.content.startswith(b'\x89PNG\r\n\x1a\n'):
                media_type = 'image/png'
            elif output.content.startswith(b'\xff\xd8\xff'):
                media_type = 'image/jpeg'
        if output.content is None:
            raise ContractError('native_document_output_missing')
        source = self._source_bytes('archive.member' if name == 'source.archive.extract' else 'poppler.pdftotext' if name == 'source.pdf.text' else 'poppler.pdftoppm', output.content, media_type, metadata)
        material = self.store.register_material(source_ref=source['id'], format='opaque', use='evidence')
        self._written.append(material['id'])
        transformation = 'archive_member' if name == 'source.archive.extract' else 'pdf_text' if name == 'source.pdf.text' else 'pdf_page'
        page = args.get('page')
        page_range = {}
        if transformation == 'pdf_text':
            page_range = {'first_page': page, 'last_page': args.get('last_page', page)}
            if page_range['first_page'] != page_range['last_page']:
                page = None
        derivative = self._put('source_derivative', {'source_ref': source['id'], 'parent_source_ref': metadata['parent_source_ref'], 'transformation': transformation, 'selection_ref': args.get('member_ref'), 'page': page, 'layout': args.get('layout', 'reading_order') if transformation == 'pdf_text' else None, 'dpi': args.get('dpi', 150) if transformation == 'pdf_page' else None, 'coordinate_system': 'original_member_bytes' if transformation == 'archive_member' else 'normalized_utf8_bytes' if transformation == 'pdf_text' else 'one_based_physical_pdf_page'}, origin='tool')
        return ({'source_ref': source['id'], 'material_ref': material['id'], 'derivation_ref': derivative['id'], 'artifact_ref': source['artifact_ref'], 'media_type': media_type, 'image_source_ref': source['id'] if media_type.startswith('image/') else None, 'page': page, **page_range, 'coordinate_system': derivative['coordinate_system'], 'provenance': metadata, 'biological_interpretation': 'not_performed'}, [source['id'], material['id'], derivative['id']])

    def _acquisition_diagnostic(self, error: AcquisitionError) -> str:
        snapshot = error.snapshot
        details = {'code': error.code, 'phase': error.phase, 'details': error.diagnostic}
        if snapshot:
            details.update(content_ref=self.store.artifact(snapshot.content, snapshot.media_type), url=snapshot.url, request=snapshot.request, transport=snapshot.transport)
        return self.store.artifact(canonical(details), 'application/json')

    async def _acquire_async(self, name: str, args: dict, scope: dict | None, operation_key: str) -> SourceSnapshot | None:
        function, arguments = self._acquisition_request(name, args, scope)
        return await self._acquire_response_async(name, function, arguments)

    async def _acquire_response_async(self, name, function, arguments):
        from gene_annotation_episode.episodic_workflow.episode_support.acquisition.chemical_source_acquisition import OPERATIONS as CHEMICAL_SOURCE_OPERATIONS
        try:
            return await asyncio.to_thread(function, **arguments)
        except AcquisitionError as error:
            if (name == 'public.ncbi.entrez' or name in CHEMICAL_SOURCE_OPERATIONS) and isinstance(error.snapshot, SourceSnapshot) and isinstance(error.snapshot.transport, dict) and (type(error.snapshot.transport.get('status')) is int):
                return error.snapshot
            raise

    def _acquisition_request(self, name: str, args: dict, scope: dict | None) -> tuple[Any, dict]:
        from gene_annotation_episode.episodic_workflow.episode_support.acquisition.biochemical_feasibility_evidence.experimental_database_acquisition import OPERATIONS as EXPERIMENT_DATABASE_TOOLS, request as experimental_database_request
        from gene_annotation_episode.episodic_workflow.episode_support.acquisition.chemical_source_acquisition import OPERATIONS as CHEMICAL_SOURCE_OPERATIONS
        if name in CHEMICAL_SOURCE_OPERATIONS:
            return (self.clients.chemical_source_request, {'operation': name, 'arguments': args})
        if name in EXPERIMENT_DATABASE_TOOLS:
            return (experimental_database_request, {'client': self.clients, 'operation': name, 'arguments': args})
        if name == 'public.literature.sequence_identity':
            from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.biochemical_feasibility_evidence.literature_sequence_discovery import identity_request
            return identity_request(self, args, scope)
        if name == 'public.ncbi.entrez':
            from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_and_context_sources.biochemical_feasibility_evidence.ncbi_entrez_tools import request_ncbi_entrez
            return (request_ncbi_entrez, {'client': self.clients, 'arguments': args})
        if name == 'public.rhea.search':
            return (self.clients.rhea_search, args)
        if name == 'public.rhea.reaction':
            return (self.clients.rhea_reaction, args)
        if name == 'public.chebi.search':
            return (self.clients.chebi_search, args)
        if name == 'public.chebi.compound':
            return (self.clients.chebi_compound, args)
        if name == 'public.uniprot.search':
            return (self.clients.uniprot_search, args)
        if name == 'public.pmc.versions':
            return (self.clients.pmc_versions, args)
        if name == 'public.pmc.files':
            selected = self.store.require(args['version_ref'], {'pmc_version'})
            return (self.clients.pmc_files, {'prefix': selected['prefix'], **({'continuation_token': args['continuation_token']} if 'continuation_token' in args else {})})
        if name == 'public.pmc.asset':
            asset = self.store.require(args['asset_ref'], {'pmc_asset', 'pmc_object'})
            selected = self.store.require(asset['version_ref'], {'pmc_version'})
            uri = asset.get('original_uri') or 's3://' + BUCKET + '/' + asset['object_key']
            return (self.clients.pmc_asset, {'original_uri': uri, 'prefix': selected['prefix']})
        if name == 'public.uniprot.record':
            return (self.clients.uniprot_record, args)
        if name == 'public.ncbi.search':
            return (self.clients.ncbi_search, args)
        if name == 'public.ncbi.sequence':
            return (self.clients.ncbi_sequence, args)
        if name == 'public.taxonomy':
            return (self.clients.taxonomy, args)
        if name == 'public.literature.search':
            return (self.clients.literature_search, args)
        if name == 'public.literature.read':
            return (self.clients.literature_read, args)
        raise ContractError('unimplemented_public_acquisition')

    def _perform(self, name: str, args: dict, scope: dict | None, snapshot: Any) -> tuple[dict, list[str]]:
        from gene_annotation_episode.episodic_workflow.episode_support.acquisition.biochemical_feasibility_evidence.experimental_database_acquisition import OPERATIONS as EXPERIMENT_DATABASE_TOOLS, publish as publish_experimental_database
        from gene_annotation_episode.episodic_workflow.episode_support.acquisition.chemical_source_acquisition import OPERATIONS as CHEMICAL_SOURCE_OPERATIONS, publish_molecular_provider_request
        if name in CHEMICAL_SOURCE_OPERATIONS:
            return publish_molecular_provider_request(self, name, args, snapshot)
        if name in EXPERIMENT_DATABASE_TOOLS:
            return publish_experimental_database(self, name, args, snapshot)
        if name == 'source.experimental.records':
            from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.experimental_database_records import read_records
            return read_records(self, args, scope, self._permitted_record_refs.get())
        if name == 'public.literature.sequence_identity':
            from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.biochemical_feasibility_evidence.literature_sequence_discovery import publish_identity
            return publish_identity(self, args, scope, snapshot)
        if name == 'source.sequence.references':
            from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.biochemical_feasibility_evidence.literature_sequence_discovery import references
            return references(self, args, scope, self._permitted_record_refs.get())
        if name == 'source.sequence.scan':
            from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_operations.biochemical_feasibility_evidence.source_sequences import scan
            return scan(self, args, scope, self._permitted_record_refs.get())
        if name == 'public.ncbi.entrez':
            from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_and_context_sources.biochemical_feasibility_evidence.ncbi_entrez_tools import publish_ncbi_entrez_request
            return publish_ncbi_entrez_request(self, args, snapshot)
        if name == 'execution.estimate':
            return (snapshot, [])
        if isinstance(snapshot, DocumentOutput):
            return self._publish_document(name, args, snapshot)
        if isinstance(snapshot, PmcFiles):
            return self._publish_pmc_files(args, snapshot)
        if name == 'public.pmc.versions':
            return self._publish_pmc_versions(args, snapshot)
        if name == 'public.pmc.asset':
            return self._publish_pmc_asset(args, snapshot)
        if name == 'material.from_source':
            material = self.store.register_material(source_ref=args['source_ref'], format=args.get('format', 'auto'), use='evidence')
            self._written.append(material['id'])
            return ({'material_ref': material['id'], 'source_ref': material['source_ref'], 'parse_with': {'material_ref': material['id']}, 'target_binding_changed': False}, [material['id']])
        if name == 'material.parse':
            attempt = self.store.parse_material(**args)
            refs = [attempt['source_ref'], attempt['id']]
            if attempt.get('native_source_ref') is not None:
                refs.append(attempt['native_source_ref'])
            if attempt['collection_ref'] is not None:
                refs.append(attempt['collection_ref'])
            self._written.extend(refs)
            return ({'parse_attempt': attempt}, refs)
        if name == 'library.members':
            return (libraries.member_page(self.store, scope=scope, **args), [])
        if name == 'library.select':
            selected = libraries.select(self.store, scope=scope, **args)
            self._written.append(selected['id'])
            return ({'selection': selected, 'scope': {'subject_refs': [selected['library_ref']], 'read_selection_refs': [selected['id']]}}, [selected['id']])
        if name == 'library.read':
            subject = self.store.require(args['subject_ref'], {'read_subject'})
            offset, limit = (args.get('offset', 0), args.get('limit', 12000))
            if type(offset) is not int or not 0 <= offset <= subject['length'] or type(limit) is not int or (limit < 1):
                raise ContractError('invalid_member_window')
            end = min(offset + limit, subject['length'])
            if offset < end:
                footprint = self.store.map_segments(subject['id'], [{'start': offset, 'end': end}])
                self._check_sequence_operand(subject['id'], scope, footprint=footprint)
            elif not self.store.scope_dimension_segments(scope, subject['id']):
                raise ContractError('subject_outside_assigned_scope')
            body = self.store.material_member(subject['member_ref'], offset=offset, limit=limit)
            return ({'subject_ref': subject['id'], 'library_ref': subject['library_ref'], **body}, [])
        if name == 'material.annotations':
            return (self.store.material_annotations(**args), [])
        if name == 'material.read':
            return (self.store.material_read(**args), [])
        if name == 'material.members':
            return (self.store.material_members(**args), [])
        if name == 'material.errors':
            return (self.store.material_errors(**args), [])
        if name == 'material.member':
            body = self.store.material_member(**args)
            reference = self.store.material_reference(args['member_ref'])
            refs = [reference['id'], *reference['context_refs']]
            self._written.extend(refs)
            return ({**body, 'reference_ref': reference['id']}, refs)
        if name == 'material.header':
            return (self.store.material_header(**args), [])
        if snapshot is not None:
            return self._import(name, args, snapshot)
        if name == 'state.query':

            def received(row):
                if row.get('record_type') != 'native_execution':
                    return row
                from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.biochemical_feasibility_evidence.native_timing_information import read_measurement
                return {**row, 'measurement': read_measurement(self.store, row['id']).as_record()}
            if 'refs' in args:
                conflicting_fields = sorted(set(args) - {'refs'})
                if conflicting_fields:
                    raise ContractError('exact_refs_cannot_be_combined_with_page_selectors', detail={'selection_mode': 'exact_references', 'conflicting_fields': conflicting_fields, 'allowed_fields': ['refs']})
                rows = [self.store.get(item) for item in args['refs']]
                for row in rows:
                    if row['record_type'] in {'input', 'feature', 'product', 'read_subject'}:
                        if not self.store.in_scope(row['id'], scope):
                            raise ContractError('subject_outside_assigned_scope')
                return ({'records': [received(row) for row in rows], 'count': len(rows), 'next_offset': None}, [])
            kind, offset, limit = (args.get('kind', 'hypothesis'), args.get('offset', 0), args.get('limit', 100))
            page = self.store.query_records(kind, scope=scope, offset=offset, limit=limit, current_only=args.get('current_only', False), references=args.get('references'))
            page['records'] = [received(row) for row in page['records']]
            return (page, [])
        if name == 'source.read':
            return (source_window(self.store, **args), [])
        if name == 'source.locate':
            return (locate_source(self.store, **args, permitted_inputs=self._permitted_record_refs.get(), scope=scope), [])
        if name == 'image.view':
            body = prepare_image(self.store, **args)
            source = self._put('source', {'provider': 'image.view', 'accession': None, 'uri': None, 'artifact_ref': body['image_artifact_ref'], 'text_ref': None, 'parent_source_refs': [body['input_source_ref']], 'request_ref': self.store.artifact(canonical(body), 'application/json'), 'version': body['software_version'], 'retrieved_at': datetime.now(timezone.utc).isoformat()}, origin='tool')
            view = self._put('image_view', {'source_ref': source['id'], **body}, origin='tool')
            return ({'view_ref': view['id'], 'view': view}, [source['id'], view['id']])
        if name == 'translation.codes':
            return ({'codes': translation_codes(), 'biopython_version': version('biopython')}, [])
        if name == 'sequence.inspect':
            subject = self._check_sequence_operand(args['subject_ref'], scope)
            sequence = self._sequence(subject['id'])
            grading = self._composition_grading(subject, sequence)
            scores = grading.get('scores') or {}
            body = {**inspect_sequence(sequence), 'molecule': self.store.subject_molecule(subject['id']), 'gc_fraction': scores.get('gc_fraction'), 'gc_denominator': scores.get('gc_denominator')}
            source = self._source('sequence.inspect', body, software_version=version('biopython'), tool_grading=grading)
            values = measurements(length=number(body['length']))
            if body['gc_fraction'] is not None:
                values += measurements(gc_fraction=number(body['gc_fraction']))
            values += self._composition_values(grading)
            observation = self._observation('sequence_composition', [subject['id']], source, values)
            return ({**body, 'observation_ref': observation['id']}, [source['id'], observation['id']])
        if name in {'sequence.translate', 'sequence.view'}:
            return self._derive(name, args, scope)
        raise ContractError('unimplemented_tool')

    def _publish_pmc_versions(self, args: dict, snapshot: SourceSnapshot) -> tuple[dict, list[str]]:
        source = self._source(snapshot.service, None, snapshot=snapshot, accession=args['pmcid'])
        refs, versions = ([source['id']], [])
        page = parse_listing(snapshot.content)
        if page['prefix'] != args['pmcid'] + '.':
            raise ContractError('pmc_version_listing_scope_mismatch')
        for prefix in page['version_prefixes']:
            selected = self._put('pmc_version', {'source_ref': source['id'], **pmc_version(prefix, pmcid=args['pmcid'])}, origin='external')
            refs.append(selected['id'])
            versions.append(selected)
        return ({'source_ref': source['id'], 'versions': versions, 'next_continuation_token': page['next_continuation_token'], 'listing_complete': not page['truncated'], 'version_preference': 'not_assigned', 'next_query': {'pmcid': args['pmcid'], 'continuation_token': page['next_continuation_token']} if page['next_continuation_token'] else None}, refs)

    def _publish_pmc_files(self, args: dict, snapshots: PmcFiles) -> tuple[dict, list[str]]:
        selected = self.store.require(args['version_ref'], {'pmc_version'})
        listing = self._source(snapshots.listing.service, None, snapshot=snapshots.listing, parent_source_refs=[selected['source_ref']])
        refs, objects, assets = ([listing['id']], [], [])
        page = parse_listing(snapshots.listing.content)
        if page['prefix'] != selected['prefix']:
            raise ContractError('pmc_file_listing_scope_mismatch')
        for item in page['objects']:
            record = self._put('pmc_object', {'source_ref': listing['id'], 'version_ref': selected['id'], 'object_key': item['key'], **{key: item[key] for key in ('size', 'etag', 'last_modified')}}, origin='external')
            refs.append(record['id'])
            objects.append(record)
        metadata = None
        if snapshots.metadata is not None:
            metadata = self._source(snapshots.metadata.service, None, snapshot=snapshots.metadata, parent_source_refs=[listing['id']])
            refs.append(metadata['id'])
        catalog = self._put('pmc_catalog', {'source_ref': listing['id'], 'version_ref': selected['id'], 'metadata_source_ref': metadata['id'] if metadata else None, 'listing_complete': not page['truncated'], 'next_continuation_token': page['next_continuation_token']}, origin='tool')
        refs.append(catalog['id'])
        body = {'source_ref': listing['id'], 'catalog_ref': catalog['id'], 'version_ref': selected['id'], 'objects': objects, 'assets': assets, 'metadata_source_ref': metadata['id'] if metadata else None, 'listing_complete': not page['truncated'], 'next_continuation_token': page['next_continuation_token'], 'next_query': {'version_ref': selected['id'], 'continuation_token': page['next_continuation_token']} if page['next_continuation_token'] else None}
        if metadata is None:
            return (body, refs)
        try:
            native = json.loads(snapshots.metadata.content)
            advertisements = metadata_assets(native, selected)
            errors = []
            for kind, field, uri in advertisements:
                try:
                    actual = advertised_asset(uri, prefix=selected['prefix'])
                    record = self._put('pmc_asset', {'source_ref': metadata['id'], 'catalog_ref': catalog['id'], 'version_ref': selected['id'], 'asset_kind': kind, 'metadata_field': field, **actual}, origin='external')
                    refs.append(record['id'])
                    assets.append(record)
                except ContractError as error:
                    errors.append({'metadata_field': field, 'code': str(error)})
            body['article_metadata'] = native
            if errors:
                body['representation_feedback'] = {'category': 'representation', 'code': 'pmc_partial_asset_advertisements', 'fields': errors}
        except (ValueError, UnicodeError) as error:
            body['representation_feedback'] = {'category': 'representation', 'code': str(error) if isinstance(error, ContractError) else 'pmc_metadata_invalid_json'}
        return (body, refs)

    def _publish_pmc_asset(self, args: dict, snapshot: SourceSnapshot) -> tuple[dict, list[str]]:
        advertisement = self.store.require(args['asset_ref'], {'pmc_asset', 'pmc_object'})
        snapshot = replace(snapshot, request={**snapshot.request, 'selected_asset_ref': advertisement['id'], 'selected_version_ref': advertisement['version_ref']})
        source = self._source(snapshot.service, None, snapshot=snapshot, parent_source_refs=[advertisement['source_ref']])
        material = self.store.register_material(source_ref=source['id'], format='opaque', use='evidence')
        self._written.append(material['id'])
        md5 = hashlib.md5(snapshot.content).hexdigest()
        advertised_md5 = advertisement.get('advertised_md5')
        body = {'source_ref': source['id'], 'material_ref': material['id'], 'asset_ref': advertisement['id'], 'artifact_ref': source['artifact_ref'], 'actual_sha256': snapshot.sha256, 'actual_md5': md5, 'advertised_md5': advertised_md5, 'advertised_md5_matches': md5 == advertised_md5 if advertised_md5 else None, 'original_advertisement': advertisement, 'target_binding_changed': False}
        if advertised_md5 is not None and md5 != advertised_md5:
            body['representation_feedback'] = {'category': 'provenance', 'code': 'advertised_checksum_differs_from_actual_bytes', 'actual_source_retained': True, 'source_ref': source['id']}
        return (body, [source['id'], material['id']])

    def _derive(self, name: str, args: dict, scope: dict | None, native=None) -> tuple[dict, list[str]]:
        batch = self._begin_publication_batch()
        grading = None
        subject = self.store.get(args['subject_ref'])
        model = args['molecule'] if name == 'sequence.view' else 'dna'
        sequence = self._sequence(subject['id'], molecule_model=model)
        parent_mapping = self.store.sequence_mapping(subject['id'])
        if name == 'sequence.view':
            selected = args.get('segments', [{'start': 0, 'end': len(sequence)}])
            footprint = self.store.map_segments(subject['id'], selected)
            self._check_sequence_operand(subject['id'], scope, footprint=footprint)
            try:
                body = view_sequence(sequence, **{key: value for key, value in args.items() if key != 'subject_ref'})
            except ValueError as error:
                raise ContractError(str(error)) from error
            from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_operations.sequence_extraction_grader import grade_extraction
            request = inspect.signature(view_sequence).bind(sequence, **{key: value for key, value in args.items() if key != 'subject_ref'})
            request.apply_defaults()
            selected_request = {key: value for key, value in request.arguments.items() if key != 'sequence'}
            if selected_request['segments'] is None:
                selected_request['segments'] = [{'start': 0, 'end': len(sequence)}]
            grading = self._grade_supplied_result(grade_extraction, body, input_sequence=sequence, subject_ref=subject['id'], parent_mapping=parent_mapping, request=selected_request)
            selected = body['input_segments']
            candidates = [{'segments': selected, 'strand': '-' if body['orientation'] == 'reverse_complement' else '+', 'sequence': body['sequence']}]
            software_version = VIEW_VERSION
        else:
            start, end = (args.get('start', 0), args.get('end', len(sequence)))
            if not 0 <= start < end <= len(sequence):
                raise ContractError('requested_interval_outside_subject')
            footprint = self.store.map_segments(subject['id'], [{'start': start, 'end': end}])
            self._check_sequence_operand(subject['id'], scope, footprint=footprint)
            if parent_mapping['units_per_symbol'] != 1:
                raise ContractError('translation_requires_nucleotide_symbol_mapping')
            if name == 'sequence.translate':
                body = translate(sequence, **{key: value for key, value in args.items() if key != 'subject_ref'})
                from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_operations.sequence_translation_grader import grade_translation
                request = inspect.signature(translate).bind(sequence, **{key: value for key, value in args.items() if key != 'subject_ref'})
                request.apply_defaults()
                selected_request = {key: value for key, value in request.arguments.items() if key != 'sequence'}
                if selected_request['end'] is None:
                    selected_request['end'] = len(sequence)
                grading = self._grade_supplied_result(grade_translation, body, input_sequence=sequence, subject_ref=subject['id'], parent_mapping=parent_mapping, request=selected_request, genetic_code=body['genetic_code_snapshot'])
                candidates = [{'start': body['translated_interval'][0], 'end': body['translated_interval'][1], 'strand': body['strand'], 'protein_sequence': body['sequence']}]
            body['omitted_terminal_stop'] = bool(name == 'sequence.translate' and body['cds'])
            software_version = version('biopython')
        body['mapping_version'] = MAPPING_VERSION
        body['subject_ref'] = subject['id']
        source = self._source(name, body, software_version=software_version, tool_grading=grading)
        self._batch_observations(batch, source['id'])
        condition = self._put('context', {'context_type': 'processing', 'name': 'sequence_view_model' if name == 'sequence.view' else 'translation_model', 'source_ref': source['id'], 'attributes': measurements(molecule_model=enum(model)) if name == 'sequence.view' else measurements(genetic_code=number(args['code'])), 'related_refs': [subject['id']]}, origin='tool')
        refs, results = ([source['id'], condition['id']], [])
        for candidate_index, candidate in enumerate(candidates):
            segments = candidate['segments'] if name == 'sequence.view' else [{'start': candidate['start'], 'end': candidate['end']}]
            output = candidate['sequence'] if name == 'sequence.view' else candidate['protein_sequence']
            try:
                if name == 'sequence.view':
                    scale = parent_mapping['units_per_symbol']
                    mapping = {'version': MAPPING_VERSION, 'units_per_symbol': scale, 'symbol_length': len(output), 'path': extract_path(parent_mapping['path'], [{'start': row['start'] * scale, 'end': row['end'] * scale} for row in segments], strand=candidate['strand'])}
                else:
                    mapping = translation_mapping(parent_mapping['path'], start=candidate['start'], end=candidate['end'], strand=candidate['strand'], protein_length=len(output), omitted_terminal_stop=body['omitted_terminal_stop'])
            except ValueError as error:
                raise ContractError(str(error)) from error
            feature = self._put('feature', {'subject_ref': subject['id'], 'kind': 'sequence_region', 'segments': segments, 'strand': candidate['strand'], 'context_refs': [condition['id']]}, origin='tool', scope=scope)
            product = self._put('product', {'parent_refs': [feature['id']], 'molecule': args['molecule'] if name == 'sequence.view' else 'protein', 'sequence_ref': self.store.artifact(output, 'text/plain'), 'derivation': 'extraction' if name == 'sequence.view' else 'translation', 'context_refs': [condition['id']], 'footprint': self.store.footprint_from_mapping(mapping), 'mapping': mapping, 'mapping_source_ref': source['id']}, origin='tool', scope=scope)
            if name == 'sequence.view':
                summary = (grading.get('scores') or {}).get('summary', {})
                values = measurements(molecule_model=enum(model))
                values += self._grading_values({'length': summary.get('output_symbol_count')}, ('length',))
            else:
                values = measurements(genetic_code=number(args['code']), start=number(candidate['start']), end=number(candidate['end']))
            if name == 'sequence.translate':
                values += self._grading_values((grading.get('scores') or {}).get('summary', {}), ('input_length_nt', 'selected_length_nt', 'frame_skipped_nt', 'translated_length_nt', 'trailing_untranslated_bases', 'translated_codon_count', 'output_symbol_count', 'amino_acid_symbol_count', 'internal_stop_count', 'terminal_stop_symbol_count', 'omitted_terminal_stop_codon_count', 'ambiguous_codon_count', 'ambiguous_output_symbol_count', 'mapped_output_symbol_count', 'compatible_codon_count', 'incompatible_codon_count', 'unknown_codon_count', 'selected_input_fraction', 'selected_input_fraction_denominator_nt'))
            elif name == 'sequence.view':
                values += self._grading_values((grading.get('scores') or {}).get('summary', {}), ('input_symbol_count', 'output_symbol_count', 'requested_segment_count', 'selected_symbol_occurrence_count', 'distinct_selected_input_symbol_count', 'repeated_selected_input_symbol_count', 'selected_input_fraction', 'selected_input_fraction_denominator_symbols', 'expected_output_symbol_count', 'output_length_difference', 'compared_symbol_count', 'matching_symbol_count', 'mismatching_symbol_count', 'unmapped_output_symbol_count', 'source_segment_count'))
            observation = self._observation('coordinate_mapping', [feature['id'], product['id']], source, values, dependencies=[subject['id'], condition['id']])
            refs += [feature['id'], product['id'], observation['id']]
            results.append({'feature_ref': feature['id'], 'product_ref': product['id'], 'observation_ref': observation['id']})
            batch['published_rows_total'] += 1
        return ({'count': len(results), 'records': results[:12], 'preview_limit': 12, 'more_records_available_through_state_query': len(results) > 12, 'source_ref': source['id'], 'limitations': body.get('limitations', [])}, refs)

    def _import(self, name: str, args: dict, snapshot: SourceSnapshot) -> tuple[dict, list[str]]:
        text = None
        article = None
        if name == 'public.literature.read':
            try:
                article = article_details(snapshot.content)
                paragraphs = article['sections']
            except ParseError as error:
                self._source(snapshot.service, None, snapshot=snapshot, accession=args.get('pmcid'))
                raise ContractError('literature_xml_parse_failed') from error
            text = '\n\n'.join((item['text'] for item in paragraphs))
        source = self._source(snapshot.service, None, snapshot=snapshot, text=text, accession=args.get('accession', args.get('pmcid', args.get('rid'))), publication_identifiers=article['publication_identifiers'] if article is not None else None)
        refs = [source['id']]
        if name in {'public.uniprot.record', 'public.uniprot.search'}:
            return self._import_uniprot(name, args, snapshot, source)
        if name in {'public.rhea.search', 'public.rhea.reaction', 'public.chebi.search', 'public.chebi.compound'}:
            return self._import_chemistry(name, args, snapshot, source)
        if name == 'public.ncbi.sequence':
            records = []
            for sequence in parse_genbank(snapshot.content):
                molecule = 'protein' if args['database'] == 'protein' else 'rna' if 'RNA' in sequence['annotations'].get('molecule_type', '') else 'dna'
                record = self._put('reference', {'reference_type': molecule, 'source_ref': source['id'], 'accession': sequence['accession'], 'label': sequence['description'], 'sequence_ref': self.store.artifact(sequence['sequence'], 'text/plain') if sequence['sequence_available'] else None, 'molecule': molecule, 'length': sequence['length'], 'term_refs': [], 'context_refs': []}, origin='external')
                refs.append(record['id'])
                records.append(record)
            return ({'source_ref': source['id'], 'records': records, 'count': len(records), 'original_feature_context_in_source': True}, refs)
        if name == 'public.literature.read':
            metadata_issues = list(article['metadata_issues'])
            reported = [item['value'] for item in article['publication_identifiers'] if item['namespace'] == 'pmcid']
            if reported and args['pmcid'] not in reported:
                metadata_issues.append({'code': 'requested_publication_identifier_mismatch', 'namespace': 'pmcid', 'requested_value': args['pmcid']})
            return ({'source_ref': source['id'], 'text_ref': source['text_ref'], 'paragraph_count': len(paragraphs), 'publication_identifiers': article['publication_identifiers'], 'metadata_issues': metadata_issues, 'cited_publications': article['cited_publications'], 'citation_meaning': 'Bibliography discovery metadata from the retained article. Read the cited source to assess its actual reported evidence and scope.', 'text_bytes': len(text.encode()), 'text_representation': 'ordered_paragraph_projection', 'omitted_elements_available_in_original': True, 'original_read_query': {'source_ref': source['id'], 'representation': 'original'}, 'read_with': 'source.read'}, refs)
        try:
            native = json.loads(snapshot.content)
        except ValueError:
            native = None
        return ({'source_ref': source['id'], 'provider_result': native, 'raw_artifact_ref': source['artifact_ref']}, refs)

    def _import_uniprot(self, name, args, snapshot, source):
        """Project one retained page while preserving original native row identity."""
        from gene_annotation_episode.uniprot_native import uniprot_source_records
        from gene_annotation_episode.uniprot_publication import bind_uniprot_publication
        operation = name.rsplit('.', 1)[1]
        request = {'operation': operation, **args, **({'size': args.get('size', 10)} if operation == 'search' else {})}
        result = {'source_ref': source['id'], 'records': [], 'count': 0, 'source_detail_available_through_source_read': True}
        refs = [source['id']]
        try:
            parsed = parse_uniprot_snapshot(snapshot, request=request)
        except ValueError as error:
            result['projection_errors'] = [{'code': str(error), 'record_ordinal': None, 'pointer': '', 'field': 'request', 'effect': 'page_unusable'}]
            return (result, refs)
        errors = [dict(issue) for issue in parsed['issues'] if issue['effect'] != 'qualification']
        release = parsed['page']['release']
        if release['state'] == 'present' and source['version'] != release['value']:
            result['projection_qualifications'] = [{'code': 'uniprot_projection_source_version_omitted', 'record_ordinal': None, 'pointer': release['pointer'], 'field': 'projection_source', 'effect': 'qualification'}]
        by_ordinal = {}

        def projection_failure(native, pointer, code, effect='field_partial'):
            errors.append({'code': code, 'record_ordinal': native['identity']['record_ordinal'], 'pointer': pointer, 'primary_accession': native['identity']['primary_accession'], 'field': 'source_fields', 'effect': effect})

        def projected_label(value, fallback, native, pointer):
            try:
                validate_schema(value, RECORD_SCHEMAS['reference']['properties']['label'])
            except ContractError:
                projection_failure(native, pointer, 'uniprot_projection_label_unrepresentable')
                return fallback
            return value

        def projected_term(namespace, accession, label, kind, native, pointer):
            payload = {'namespace': namespace, 'accession': accession, 'label': label, 'term_type': kind, 'source_ref': source['id'], 'anchor': None}
            try:
                validate_schema(payload, RECORD_SCHEMAS['term'])
            except ContractError:
                projection_failure(native, pointer, 'uniprot_projection_term_unrepresentable')
                return None
            term = self._put('term', payload, origin='external')
            refs.append(term['id'])
            return term['id']
        for native, protein in zip(parsed['records'], uniprot_source_records(parsed, snapshot.content), strict=True):
            anchor = native['identity']
            if protein['accession'] != anchor['primary_accession']:
                raise ContractError('uniprot_projection_record_identity_conflict')
            try:
                validate_schema(protein['accession'], RECORD_SCHEMAS['reference']['properties']['accession'])
            except ContractError:
                projection_failure(native, anchor['record_pointer'] + '/primaryAccession', 'uniprot_projection_reference_unrepresentable', 'record_unpublishable')
                continue
            terms = []
            if protein['taxon_id'] is not None:
                taxon_id = str(protein['taxon_id'])
                label = projected_label(protein['organism'] or taxon_id, taxon_id, native, native['taxon']['scientific_name']['pointer'])
                terms.append(projected_term('ncbi_taxonomy', taxon_id, label, 'taxon', native, native['taxon']['taxon_id']['pointer']))
            source_fields = native['source_fields']
            if source_fields['source_name']:
                terms.append(projected_term('uniprot_source_name', protein['accession'], source_fields['source_name'], 'molecular_role', native, source_fields['source_name_pointer']))
            for ec, pointer in zip(source_fields['source_ec_numbers'], source_fields['source_ec_number_pointers'], strict=True):
                terms.append(projected_term('EC', ec, 'EC ' + ec, 'molecular_role', native, pointer))
            sequence = native['sequence']
            sequence_ref = None
            if sequence['value']['state'] == 'present':
                sequence_bytes = sequence['value']['value'].encode('ascii')
                sequence_ref = self.store.artifact(sequence_bytes, 'text/plain')
                if self.store.get_artifact(sequence_ref) != sequence_bytes:
                    raise ContractError('uniprot_sequence_artifact_content_conflict')
            label = projected_label(source_fields['source_name'] or protein['accession'], protein['accession'], native, source_fields['source_name_pointer'])
            record = self._put('reference', {'reference_type': 'protein', 'source_ref': source['id'], 'accession': protein['accession'], 'label': label, 'sequence_ref': sequence_ref, 'molecule': 'protein', 'length': sequence['observed_length_aa'], 'term_refs': list(dict.fromkeys((term for term in terms if term is not None))), 'context_refs': []}, origin='external')
            by_ordinal[anchor['record_ordinal']] = record
            refs.append(record['id'])
            result['records'].append(record)
        if self.store.get_artifact(source['artifact_ref']) != snapshot.content:
            raise ContractError('uniprot_native_artifact_content_conflict')
        for native in parsed['records']:
            anchor = native['identity']
            if anchor['record_ordinal'] not in by_ordinal and (not any((error.get('code') == 'uniprot_projection_reference_unrepresentable' and error.get('effect') == 'record_unpublishable' and (error.get('record_ordinal') == anchor['record_ordinal']) and (error.get('pointer') == anchor['record_pointer'] + '/primaryAccession') and (error.get('primary_accession') == anchor['primary_accession']) for error in errors))):
                raise ContractError('uniprot_publication_omission_not_reported')
        result.update(count=len(by_ordinal), projection_errors=errors, uniprot_publication=bind_uniprot_publication(parsed, source_ref=source['id'], native_artifact_ref=source['artifact_ref'], references_by_ordinal=by_ordinal))
        if operation == 'search':
            result.update(uniprot_page_metadata(parsed))
        return (result, list(dict.fromkeys(refs)))

    def _chemistry_reference(self, kind: str, accession: str, source: dict, *, native_record_ref: str | None=None) -> dict:
        record = {'reference_type': kind, 'source_ref': source['id'], 'accession': accession, 'label': accession, 'sequence_ref': None, 'molecule': None, 'length': None, 'term_refs': [], 'context_refs': []}
        if native_record_ref is not None:
            record['native_record_ref'] = native_record_ref
        return self._put('reference', record, origin='external')

    def _import_chemistry(self, name: str, args: dict, snapshot: SourceSnapshot, source: dict) -> tuple[dict, list[str]]:
        is_rhea = name.startswith('public.rhea.')
        search = name.endswith('search')
        body = rhea_response(snapshot.content) if is_rhea else chebi_response(snapshot.content, search=search)
        rows = body['results'] if is_rhea or search else [body]
        references, errors, refs = ([], [], [source['id']])
        for index, native in enumerate(rows):
            before = len(self._written)
            try:
                if is_rhea:
                    details = rhea_row(native)
                    participants = []
                    for participant in details['participants']:
                        chemical = self._chemistry_reference('chemical', participant['source_accession'], source)
                        participants.append({**participant, 'chemical_ref': chemical['id']})
                    details['participants'] = participants
                    details = self._put('reaction_record', {**details, 'source_ref': source['id']}, origin='external')
                    reference = self._chemistry_reference('reaction', details['accession'], source, native_record_ref=details['id'])
                    preview = {'source_equation_preview': details['source_equation'][:240], 'equation_preview_complete': len(details['source_equation']) <= 240, 'source_direction': details['source_direction'], 'participant_count': len(participants)}
                else:
                    details = self._put('chemical_record', {**chemical_row(native, search=search), 'source_ref': source['id']}, origin='external')
                    reference = self._chemistry_reference('chemical', details['accession'], source, native_record_ref=details['id'])
                    preview = {'source_name_preview': details['source_name'][:160], 'name_preview_complete': len(details['source_name']) <= 160, 'representation': details['representation'], 'formula': details['formula'], 'charge': details['charge'], 'ontology_relation_count': len(details['ontology_relations'])}
                references.append({'reference_ref': reference['id'], 'native_record_ref': details['id'], 'accession': details['accession'], **preview})
            except (ContractError, ValueError, KeyError, TypeError) as error:
                errors.append({'row_index': index, 'code': str(error) if isinstance(error, ContractError) else 'missing_native_field' if isinstance(error, KeyError) else 'invalid_native_row', **({'missing_field': str(error.args[0])} if isinstance(error, KeyError) else {}), **({'detail': error.detail} if isinstance(error, ContractError) and error.detail else {})})
            refs.extend(self._written[before:])
        result = {'source_ref': source['id'], 'records': references[:6], 'preview_limit': 6, 'projected_record_count': len(references), 'provider_returned_row_count': len(rows), 'more_records_available_through_state_query': len(references) > 6, 'details_query': {'kind': 'reaction_record' if is_rhea else 'chemical_record', 'references': [source['id']], 'limit': 6}, 'complete_source_read_query': {'source_ref': source['id'], 'representation': 'original'}, 'projection_errors': errors, 'target_annotation': 'not_performed', 'thermodynamics_or_physiological_flux': 'not_inferred'}
        if is_rhea:
            result.update(native_count=body.get('count'), result_scope='provider_limited_json_search_not_exhaustive_absence', direction_scope='json_search_master_records_directional_variants_not_resolved')
        elif search:
            page = args.get('page', 1)
            pages = body.get('number_pages')
            result.update(native_total=body.get('total'), native_page_count=pages, page=page, next_query={'term': args['term'], 'size': args.get('size', 10), 'page': page + 1} if type(pages) is int and page < pages else None)
        if not search:
            database = 'RHEA' if is_rhea else 'CHEBI'
            requested = chemical_accession(args['accession'], database)
            result.update(requested_accession=requested, returned_accessions=[row['accession'] for row in references], exact_accession_match=any((row['accession'] == requested for row in references)), lookup_outcome='returned_source_records' if references else 'source_records_not_projected' if rows else 'no_search_match')
        return (result, list(dict.fromkeys(refs)))
