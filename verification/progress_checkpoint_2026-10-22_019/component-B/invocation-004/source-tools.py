"""One execution path for ordinary, explicitly selected annotation tools."""
from __future__ import annotations

import asyncio
from copy import deepcopy
from contextvars import ContextVar
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from importlib.metadata import version
import json
import hashlib
import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import ParseError

from .acquisition import AcquisitionError, PublicClients, RfamModelSnapshots, SourceSnapshot, article_details, parse_genbank, parse_hmmer, parse_uniprot, uniprot_pagination
from .domain import REF, REFS, RECORD_SCHEMAS, ContractError, canonical, identity, obj, validate_schema
from .sequence_ops import compare_sites, inspect_sequence, translate, translation_codes
from .local_jobs import LocalJobPolicy, run_local_job_async, run_cancellable_native
from .sequence_mapping import VERSION as MAPPING_VERSION, extract_path, mapping_footprint, translation_mapping
from .sequence_views import VERSION as VIEW_VERSION, view_sequence
from .provider_jobs import RemoteSearches
from . import blast_search as blast
from .rfam_discovery import VERSION as RFAM_DISCOVERY_VERSION, hit_row as rfam_hit_row
from .comparative_ops import genbank_neighborhood, VERSION as NEIGHBORHOOD_VERSION
from .material_parsing import FORMATS
from . import library_targets as libraries
from . import materials_packing as packing
from . import read_mapping as mapper
from .chemistry import (accession as chemical_accession, rhea_response, rhea_row,
                        chebi_response, chemical_row)
from .materials import artifact_file, artifact_path, source_window
from .document_tools import (DocumentOutput, archive_extract, archive_inventory,
                             pdf_native, resource as document_resource)
from .spreadsheet_tools import xlsx_native, VERSION as XLSX_VERSION
from .literature_assets import (PmcFiles, advertised_asset, metadata_assets,
                                parse_listing, version as pmc_version, BASE_URL, BUCKET)
from .rna_evidence import (NativeSearch, iter_fmt3, local_configuration, model_header,
                           run_cmsearch, search_settings)
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


@dataclass(frozen=True)
class SequenceWork:
    output_path: Path
    metadata: dict


class ToolRegistry:
    def __init__(self, store: Any, *, clients: PublicClients | None = None,
                 provider_poll_interval_seconds: float = 5,
                 cmsearch_executable: str | Path | None = None, cmsearch_cpu: int | None = None,
                 minimap2_executable: str | Path | None = None, minimap2_cpu: int | None = None,
                 minimap2_cache_dir: str | Path | None = None,
                 pdfinfo_executable: str | Path | None = None,
                 pdftotext_executable: str | Path | None = None,
                 pdftoppm_executable: str | Path | None = None,
                 knowledge_library_directory: str | Path | None = None,
                 job_limits: dict | None = None, native_statistics=None):
        self.store = store
        self.knowledge_library_directory = (None if knowledge_library_directory is None else
                                            Path(knowledge_library_directory).expanduser().resolve())
        self.local_job_policy = LocalJobPolicy.from_config(job_limits)
        if native_statistics is not None:
            from .ordinary_execution import OrdinaryExecutionStatistics
            if type(native_statistics) is not OrdinaryExecutionStatistics:
                raise TypeError('typed_ordinary_execution_statistics_required')
        self.native_statistics = native_statistics
        self.api_execution_planner = None
        self.api_direct_hmmer_timing = None
        self.clients = clients or PublicClients()
        store.db.execute("""CREATE TABLE IF NOT EXISTS tool_operations (
            operation_key TEXT PRIMARY KEY, id TEXT NOT NULL, name TEXT NOT NULL,
            arguments TEXT NOT NULL, scope TEXT NOT NULL, result TEXT NOT NULL)""")
        store.db.commit()
        self.remote_searches = RemoteSearches(store, self.clients, poll_interval_seconds=provider_poll_interval_seconds)
        self._publications = ContextVar("annotation_tool_publications", default=None)
        self._publication_batch = ContextVar("annotation_native_publication_batch", default=None)
        self._mapping_directories = ContextVar("annotation_mapping_directories", default=None)
        self._native_execution_refs = ContextVar('annotation_native_execution_refs', default=None)
        self._direct_hmmer_acquisitions = ContextVar('annotation_direct_hmmer_acquisitions', default=None)
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
                **({'knowledge_library_directory': str(self.knowledge_library_directory)}
                   if self.knowledge_library_directory is not None else {}),
                **({'ordinary_execution_statistics': self.native_statistics.as_record()}
                   if self.native_statistics is not None else {}),
                "cmsearch": local_configuration(executable=self.cmsearch_configuration["executable"],
                                               cpu=self.cmsearch_configuration["cpu"], job_limits=self.local_job_policy.to_dict()),
                "pdf_tools": {name: document_resource(path) for name, path in self.pdf_executables.items()},
                "minimap2": mapper.local_configuration(**{key: self.minimap2_configuration[key]
                    for key in ("executable", "cpu", "cache_dir")}, job_limits=self.local_job_policy.to_dict())}

    def bind_api_execution_planner(self, planner):
        """Attach the supplied typed run owner after exact identity checks."""
        from .api_execution_planning import ApiExecutionPlanner
        if type(planner) is not ApiExecutionPlanner:
            raise TypeError('typed_api_execution_planner_required')
        planner.validate_registry(self)
        previous = self.api_execution_planner
        if previous is not None and previous.as_record() != planner.as_record():
            raise ContractError('api_execution_planner_identity_conflict')
        self.api_execution_planner = planner
        return planner

    def bind_api_direct_hmmer_timing(self, binding):
        """Attach the supplied actual run owner after exact descriptor checks."""
        from .direct_hmmer_timing import DirectHmmerTiming
        if type(binding) is not DirectHmmerTiming:
            raise TypeError('typed_direct_hmmer_timing_binding_required')
        binding.validate_registry(self)
        previous = self.api_direct_hmmer_timing
        if previous is not None and previous.as_record() != binding.as_record():
            raise ContractError('api_direct_hmmer_timing_identity_conflict')
        self.api_direct_hmmer_timing = binding
        return binding

    @property
    def _written(self) -> list[str]:
        publications = self._publications.get()
        if publications is None:
            raise ContractError("publication_outside_tool_operation")
        return publications

    def catalog(self, scope: dict | None = None) -> dict[str, dict]:
        definitions = {
            "state.query": ("Read an exact page of typed scientific records, current revisions, or records referring to actual references. Follow the returned next_query for the same selection and order. Exact refs is a separate mode and cannot be combined with page selectors.", obj({
                "kind": {"enum": list(RECORD_SCHEMAS) + ["subject"]}, "offset": INTEGER,
                "limit": POSITIVE, "refs": {**REFS,
                    "description": "Exact reference mode: supply refs alone, including an empty array for no records. Omit kind, offset, limit, current_only and references in this mode."},
                "current_only": {"type": "boolean"},
                "references": {"type": "array", "items": REF, "minItems": 1}}, required=[])),
            "source.read": ("Read a bounded UTF-8 byte window from an actual source. Choose original for retained source bytes, including XML tables/headings omitted by a paragraph projection; text selects that projection when available. Explicit stdout/stderr select retained native stream bytes when present, without falling back to another representation. Returned artifact/offsets support exact anchors.",
                obj({"source_ref": REF, "offset": INTEGER, "limit": POSITIVE,
                     "representation": {"enum": ["text", "original", "stdout", "stderr"]}}, ["source_ref"])),
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
            "source.pdf.text": ("Extract one explicitly selected physical PDF page as a reusable UTF-8 text derivative. Its byte offsets are normalized-text coordinates, not original PDF byte offsets. No OCR or interpretation is performed.",
                obj({"source_ref": REF, "page": POSITIVE, "layout": {"enum": ["reading_order", "layout", "raw"]}}, ["source_ref", "page"])),
            "source.pdf.page": ("Render one explicitly selected physical PDF page as a reusable PNG source. Rendering does not by itself supply image input to a model or interpret a figure.",
                obj({"source_ref": REF, "page": POSITIVE, "dpi": {"type": "number", "exclusiveMinimum": 0}}, ["source_ref", "page"])),
            "material.parse": ("Parse a registered supplied asset under a chosen wrapper interpretation. Preserve valid independent members and exact original custody; evidence never enlarges annotation targets.",
                obj({"material_ref": REF, "format": {"enum": FORMATS}}, ["material_ref"])),
            "material.annotations": ("Page native supplied GenBank record metadata or feature assertions from one exact parse. These are source assertions, not current scientific annotations or accepted gene models. Bounded previews point to exact normalized JSONL byte windows for source.read; original GenBank bytes and their coordinate frame remain separate.",
                obj({"parse_ref": REF, "record_ordinal": INTEGER, "kind": {"enum": ["record", "feature"]},
                     "offset": INTEGER, "limit": POSITIVE}, ["parse_ref"])),
            "material.from_source": ("Make an existing registered source reusable as evidence material, retaining its exact origin and bytes. This registers a wrapper and does not parse, classify or add annotation targets.",
                obj({"source_ref": REF, "format": {"enum": FORMATS}}, ["source_ref"])),
            "material.read": ("Read an exact bounded byte window of registered caller material as base64, including binary or unrecognized assets.",
                obj({"material_ref": REF, "offset": INTEGER, "limit": POSITIVE}, ["material_ref"])),
            "material.members": ("Read a bounded page of an immutable parsed evidence collection in original record order; no read is made a credit target.",
                obj({"collection_ref": REF, "offset": INTEGER, "limit": POSITIVE}, ["collection_ref"])),
            "material.errors": ("Read exact source-record/offset parser feedback; unparsed material remains available for another interpretation.",
                obj({"parse_ref": REF, "offset": INTEGER, "limit": POSITIVE}, ["parse_ref"])),
            "material.member": ("Read a bounded sequence/quality window of one indexed source member and expose its reusable source-bound reference; infer no molecule, function or organism.",
                obj({"member_ref": REF, "offset": INTEGER, "limit": POSITIVE}, ["member_ref"])),
            "material.header": ("Read an exact bounded UTF-8 byte window of a registered member's parser-returned title. Preserve its source and parser provenance; it is not the original file header bytes. Follow next_query for exact continuation.",
                obj({"member_ref": REF, "offset": INTEGER, "limit": POSITIVE}, ["member_ref"])),
            "library.members": ("Page actual original reads of a fixed caller library in original member order. Returns stable lazy read_subject IDs and read-local metadata, not genes, organisms, joined coordinates or extra targets.",
                obj({"library_ref": REF, "selection_ref": REF, "offset": INTEGER, "limit": POSITIVE}, ["library_ref"])),
            "library.select": ("Freeze an explicitly chosen original-member subset for an investigation scope. Ordinal ranges select library inventory rows, never genomic intervals. No biology, pair identity or annotation is inferred.",
                obj({"library_ref": REF, "member_refs": {"type": "array", "minItems": 1, "items": REF},
                    "ordinal_ranges": {"type": "array", "minItems": 1, "items": obj({"start": INTEGER, "end": POSITIVE})}}, ["library_ref"])),
            "library.read": ("Read one actual original read's sequence and native quality window without turning the whole library into a sequence. Quality encoding and caller molecule declarations remain unchanged.",
                obj({"subject_ref": REF, "offset": INTEGER, "limit": POSITIVE}, ["subject_ref"])),
            "reads.inspect": ("Measure composition of exactly the selected original read subjects as one ordinary action. Each native result keeps its own original member; no average is promoted to a library-wide biological assertion. Full results are source-bound, with a bounded preview.",
                obj({"subject_refs": {"type": "array", "minItems": 1, "uniqueItems": True, "items": REF}})),
            "sequence.inspect": ("Measure sequence composition and compatible alphabets; do not classify its biology.", obj({"subject_ref": REF})),
            "public.rfam.model": ("Acquire one explicitly selected Rfam covariance model and its family metadata. The reusable family is not a biological sequence or target annotation.",
                obj({"accession": {"type": "string", "pattern": "^RF[0-9]{5}$"}})),
            "public.rfam.search": ("Discover RNA-family matches for one registered nucleotide operand through the public Rfam batch service, without requiring a known family accession. One durable submission/protocol wait/result is one ordinary action. All native hits remain source evidence; no function, taxon or annotation is assigned. Provider search defaults and database/model release are not exposed by this API.",
                obj({"subject_ref": REF})),
            "public.rfam.collect": ("Collect an existing Rfam discovery job after interruption or transport failure without another submission; committed results replay exactly. Job identity must belong to Rfam.", obj({"job_ref": REF})),
            "rna.cmsearch": ("Search a registered nucleotide operand with one explicitly selected acquired covariance model using native Infernal. Retain every reported row, including native '?' rows; no RNA or organism-wide absence annotation is assigned. Native query=model, target=sequence. Model consensus coordinates are not physical reference residues.",
                obj({"subject_ref": REF, "model_ref": REF, "parameters": obj({
                    "report_evalue": {"type": "number", "exclusiveMinimum": 0}, "report_bitscore": {"type": "number"},
                    "inclusion_evalue": {"type": "number", "exclusiveMinimum": 0}, "inclusion_bitscore": {"type": "number"},
                    "model_cutoff": {"enum": ["ga", "tc", "nc"]}, "search_space_mb": {"type": "number", "exclusiveMinimum": 0},
                    "alignment_mode": {"enum": ["local", "glocal"]}, "strand": {"enum": ["both", "top", "bottom"]},
                    "truncation": {"enum": ["default", "none", "any"]},
                    "acceleration": {"enum": ["default", "max", "nohmm", "mid", "rfam", "hmmonly"]},
                    "force_cm": {"type": "boolean"}, "cyk": {"type": "boolean"},
                    "matrix_mb": {"type": "number", "exclusiveMinimum": 0},
                    "sequence_matrix_mb": {"type": "number", "exclusiveMinimum": 0},
                    "alignment_output": {"type": "boolean"}}, [])}, ["subject_ref", "model_ref"])),
            "sequence.view": ("Extract a reusable sequence view under the explicitly selected processing model; preserve original identity and coordinates. This does not classify the input and is not a prerequisite for direct searches.",
                obj({"subject_ref": REF, "molecule": {"enum": ["dna", "rna", "protein"]},
                     "segments": {"type": "array", "minItems": 1, "items": obj({"start": INTEGER, "end": POSITIVE})},
                     "orientation": {"enum": ["as_is", "reverse_complement"]}}, ["subject_ref", "molecule"])),
            "translation.codes": ("Read the installed NCBI translation tables; no code is selected for the input.", obj({})),
            "sequence.translate": ("Derive one translation under an explicitly chosen code, interval and orientation; preserve the input.",
                obj({"subject_ref": REF, "code": POSITIVE, "strand": {"enum": ["+", "-"]},
                     "frame": {"enum": [0, 1, 2]}, "start": INTEGER, "end": POSITIVE,
                     "cds": {"type": "boolean"}}, ["subject_ref", "code"])),
            "genes.predict": ("Run one native Pyrodigal prediction under the chosen code hypothesis. Candidates remain proposals.",
                obj({"subject_ref": REF, "code": POSITIVE, "mode": {"enum": ["meta", "single"]},
                     "start": INTEGER, "end": POSITIVE}, ["subject_ref", "code", "mode"])),
            "reads.align": ("Compare exactly the selected original reads with one actual registered reference under the chosen native pairwise model as one ordinary action. Each read retains separate native alignment/source/operand intervals. Independent failures preserve successful rows. No organism, orthology or function is assigned.",
                obj({"subject_refs": {"type": "array", "minItems": 1, "uniqueItems": True, "items": REF},
                    "reference_ref": REF, "molecule": {"enum": ["dna", "rna", "protein"]},
                    "mode": {"enum": ["local", "global"]}})),
            "reads.map": ("Map exactly one chosen immutable original-read selection against explicitly selected actual reference sequences using native minimap2. A selected preset is a processing model, not input classification. Preserve every reported PAF placement and native ranking; no host result threshold, consensus, correction, organism or function assignment. Each placement has actual separate operands. No report means no placement under this recorded search, not biological absence.",
                obj({"query_selection_ref": REF,
                    "reference_refs": {"type": "array", "items": REF, "minItems": 1, "uniqueItems": True},
                    "preset": {"enum": mapper.PRESETS}, "parameters": obj({
                        **{name: mapper.parameter_schema(name) for name in mapper.PARAMETER_RANGES},
                        "secondary": {"type": "boolean"},
                        "homopolymer_compression": {"const": True,
                            "description": "Native -H enable-only override. Omit to retain the chosen preset; this interface does not promise a false override for a preset enabling HPC."}}, [])},
                    ["query_selection_ref", "reference_refs", "preset"])),
            "sequence.align": ("Align two registered actual sequences, including acquired evidence sequences. Preserve operand identities; no function or orthology is assigned.",
                obj({"query_ref": REF, "reference_ref": REF, "molecule": {"enum": ["dna", "rna", "protein"]},
                     "mode": {"enum": ["local", "global"]}}, ["query_ref", "reference_ref", "molecule", "mode"])),
            "sequence.sites": ("Inspect selected reference positions or a chosen half-open window in an existing native alignment. Distinguish substitutions, query gaps, insertions between reference bases and unexamined sites. Reverse-strand query coordinates and original FASTQ quality characters retain their own identity; numeric scores require a known declared encoding. This does not call a consensus or variants. Bounded preview; complete structured result remains in source.read.",
                obj({"alignment_ref": REF, "positions": {"type": "array", "items": INTEGER, "minItems": 1},
                    "window": obj({"start": INTEGER, "end": POSITIVE})}, ["alignment_ref"])),
            "reference.neighborhood": ("Inspect actual acquired GenBank features around one explicitly selected reference locus or coordinate. Preserve source labels, partial boundaries and unavailable context; infer no orthology or target function. Left/right follow the reference axis.",
                obj({"reference_ref": REF, "selector": obj({"locus_tag": TEXT, "protein_id": TEXT,
                    "coordinate": INTEGER, "coordinate_frame": {"enum": ["record", "original"]}, "feature_kind": TEXT}, []),
                    "left_bp": INTEGER, "right_bp": INTEGER}, ["reference_ref", "selector", "left_bp", "right_bp"])),
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
            "public.literature.read": ("Acquire an actual open article and an ordered paragraph projection for source-linked interpretation. Read the retained original XML with source.read representation=original for tables, headings and other omitted elements.", obj({"pmcid": TEXT})),
            "public.rhea.search": ("Search one explicitly limited Rhea JSON response. Returned left/right equation sides and native direction are database reaction facts, not substrates/products in the target organism. JSON search currently returns undefined-direction master records; no exhaustive absence or directional-variant resolution is claimed.",
                obj({"query": {"type": "string"}, "limit": POSITIVE}, ["query"])),
            "public.rhea.reaction": ("Look up a selected Rhea accession through its JSON search interface. Preserve returned identity and direction; a directional accession may yield no search match. No automatic ID/direction substitution. Read native_record_ref with state.query for complete structured details.", obj({"accession": TEXT})),
            "public.chebi.search": ("Search one selected ChEBI text-result page using the service's term parameter. Search summaries retain their source scope and scores/stars are never annotation acceptance rules. Follow next_query for later pages.",
                obj({"term": {"type": "string"}, "size": POSITIVE, "page": POSITIVE}, ["term"])),
            "public.chebi.compound": ("Retrieve a selected ChEBI compound's source chemistry, structure strings and ontology relations. These are chemical/source identities, not an enzyme assay, target substrate assignment or physiological role. Complete structured detail is available through native_record_ref using state.query.", obj({"accession": TEXT})),
            "public.hmmer.databases": ("Read the actual currently served sequence/profile databases and versions.", obj({})),
            "public.hmmer.search": ("Perform one selected protein similarity or profile search; durable submission, protocol waiting and the first result page form one ordinary action. No function or taxon is assigned.",
                obj({"subject_ref": REF, "algorithm": {"enum": ["phmmer", "hmmscan"]}, "database": TEXT,
                    "parameters": obj({**{key: {"type": "number"} for key in ["E", "domE", "incE", "incdomE", "T", "domT", "incT", "incdomT", "popen", "pextend"]},
                        "threshold": {"enum": ["evalue", "bitscore"]}, "mx": TEXT,
                        "include_taxonomy": {"type": "array", "items": POSITIVE}, "exclude_taxonomy": {"type": "array", "items": POSITIVE}}, []),
                    "page_size": POSITIVE}, ["subject_ref", "algorithm", "database"])),
            "public.hmmer.collect": ("Resume a known durable search after interruption or transport failure without another submission.", obj({"job_ref": REF})),
            "public.hmmer.page": ("Retrieve another exact page from a known search; original query, database and settings remain attached.",
                obj({"job_ref": REF, "page": POSITIVE, "page_size": POSITIVE}, ["job_ref", "page"])),
            "public.search.jobs": ("Read a page of current remote job ownership/handles, without loading raw HTTP histories.",
                obj({"limit": POSITIVE, "offset": INTEGER, "active_only": {"type": "boolean"}}, [])),
            "public.blast.search": ("Search one actual registered operand with the selected BLAST program/database. Durable submission, same-job protocol wait and native results are one ordinary action. All reported HSPs are evidence; no function or taxon is assigned.",
                obj({"subject_ref": REF, "program": {"enum": list(blast.PROGRAM_UNITS)},
                     "database": TEXT, "hitlist_size": POSITIVE}, ["subject_ref", "program", "database"])),
            "public.blast.collect": ("Resume an existing durable BLAST job without resubmission or changing its subject, program or requested database. Requires that job's original operand to belong to the assigned measurement scope.", obj({"job_ref": REF})),
        }
        result = {name: {"description": description, "input_schema": schema}
                  for name, (description, schema) in definitions.items()}
        # Inform the owning Episode about actual configuration; the catalog
        # neither selects another tool nor introduces scientific permission.
        result["public.blast.search"]["configuration"] = {
            "ncbi_contact_configured": bool(getattr(self.clients, "ncbi_email", None)),
            "provider_access_dir": str(Path(self.clients.access_dir).resolve()) if getattr(self.clients, "access_dir", None) is not None else None,
            "spacing_scope": "cooperating_clients_using_configured_directory"}
        result["rna.cmsearch"]["configuration"] = {**self.resource_binding()["cmsearch"],
            "native_default_settings": search_settings(), "job_limits": self.local_job_policy.to_dict(),
            "no_hit_scope": "submitted_operand_under_recorded_settings"}
        result["reads.map"]["configuration"] = {**self.resource_binding()["minimap2"],
            "job_limits": self.local_job_policy.to_dict(), "base_alignment": "PAF_cg_and_cs_long", "fragment_mode": "unpaired",
            "no_hit_scope": "chosen_read_selection_and_references_under_recorded_native_settings"}
        for name, native in (("source.pdf.info", "pdfinfo"), ("source.pdf.text", "pdftotext"), ("source.pdf.page", "pdftoppm")):
            result[name]["configuration"] = {**document_resource(self.pdf_executables[native]), "job_limits": self.local_job_policy.to_dict()}
        for name in ("source.xlsx.sheets", "source.xlsx.rows"):
            result[name]["configuration"] = {"adapter_version": XLSX_VERSION,
                "job_limits": self.local_job_policy.to_dict(), "execution": "isolated_store_free_worker"}
            if self.native_statistics is not None:
                result[name]['configuration']['timing_statistics'] = self.native_statistics.as_record()
        for name in ("sequence.align", "reads.align", "genes.predict"):
            result[name]["configuration"] = {"job_limits": self.local_job_policy.to_dict(),
                "execution": "isolated_store_free_worker", "algorithm_substitution": False}
            if name != 'genes.predict' and self.native_statistics is not None:
                result[name]['configuration']['timing_statistics'] = self.native_statistics.as_record()
        if self.native_statistics is not None:
            result['execution.estimate'] = {'description':
                'Obtain recorded duration expectations before a proposed native alignment or workbook selection. Uses the same operands, actual settings and caller resource as execution. Creates no native job or scientific evidence; missing history stays unknown. This is an optional information tool, not a scheduling or continuation decision.',
                'input_schema': {'anyOf': [obj({'tool': {'const': name},
                    'arguments': result[name]['input_schema']})
                    for name in ('sequence.align', 'source.xlsx.sheets', 'source.xlsx.rows')]}}
        if self.api_execution_planner is not None:
            planner = self.api_execution_planner
            branch = planner.input_schema(deepcopy(result['public.hmmer.search']['input_schema']))
            if 'execution.estimate' not in result:
                result['execution.estimate'] = {'description':
                    'Obtain an original reported-duration forecast for an explicitly proposed registered HMMER request and the bound API candidate before commissioning work. Supply tool, arguments, resource_selection, constraints and immutable_input_versions explicitly. Creates no order, submission, measurement or scientific evidence; unavailable statistics remain information and do not prevent work.',
                    'input_schema': {'anyOf': []}}
            else:
                result['execution.estimate']['description'] += (
                    ' Also accepts an explicitly proposed registered HMMER request and bound API candidate, with explicit constraints and immutable_input_versions. API forecasts retain original provider-reported-result units and create no order, submission or measurement; unavailable statistics do not prevent work.')
            result['execution.estimate']['input_schema']['anyOf'].append(branch)
            result['execution.estimate']['configuration'] = planner.as_record()
        if self.api_direct_hmmer_timing is not None:
            for name in ('public.hmmer.search', 'public.hmmer.collect'):
                result[name]['configuration'] = {
                    'ordinary_hmmer_timing': self.api_direct_hmmer_timing.as_record()}
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

        Original-input work retains its assigned ownership bounds. Registered
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
            if software_version is None:
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
                operation_key: str | None = None) -> dict:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.execute_async(name, args, scope=scope, operation_key=operation_key))
        raise ContractError("use_execute_async_in_running_event_loop")

    async def execute_async(self, name: str, args: dict, *, scope: dict | None = None,
                            operation_key: str | None = None) -> dict:
        token = self._publications.set([])
        batch_token = self._publication_batch.set(None)
        directories = self._mapping_directories.set([])
        native_receipts = self._native_execution_refs.set([])
        direct_acquisitions = self._direct_hmmer_acquisitions.set([])
        try:
            return await self._execute_operation_async(name, args, scope=scope, operation_key=operation_key)
        finally:
            import shutil
            for directory in self._mapping_directories.get():
                shutil.rmtree(directory)
            self._mapping_directories.reset(directories)
            self._native_execution_refs.reset(native_receipts)
            self._direct_hmmer_acquisitions.reset(direct_acquisitions)
            self._publications.reset(token)
            self._publication_batch.reset(batch_token)

    async def _execute_operation_async(self, name: str, args: dict, *, scope: dict | None = None,
                                       operation_key: str | None = None) -> dict:
        operation_key = operation_key or identity("manual_operation", {"name": name, "args": args,
                                                "time": datetime.now(timezone.utc).isoformat()})
        saved = self.store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (operation_key,)).fetchone()
        if saved:
            if saved["name"] != name or saved["arguments"] != canonical(args) or saved["scope"] != canonical(scope):
                raise ContractError("operation_key_reused_for_different_work")
            return json.loads(saved["result"])
        operation_ref = identity("operation", {"key": operation_key, "name": name, "arguments": args})
        result = {"status": "invalid", "operation_ref": operation_ref, "record_refs": [], "result": None, "feedback": None}
        try:
            catalog = self.catalog(scope)
            if name not in catalog:
                raise ContractError("unknown_tool")
            try:
                validate_schema(args, catalog[name]["input_schema"])
            except ContractError as error:
                # Explain the existing schema failure without a second
                # validation or a new successful-path assessment.
                feedback = (mapper.parameter_schema_failure(error.__cause__)
                    if name == "reads.map" and error.__cause__ is not None else None)
                if feedback is not None:
                    raise ContractError(feedback["code"], detail=feedback["detail"]) from error
                raise
            normalized_scope = self.store.validate_scope(scope)
            # Network acquisition happens before scientific publication. No
            # SQLite write transaction is held while waiting on a provider.
            snapshot = (self._estimate_execution(args, scope, api_scope=normalized_scope) if name == 'execution.estimate' else
                await self._prepare_sequence_work_async(name, args, scope) if name in {"sequence.align", "reads.align", "genes.predict"} else
                await self._document_async(name, args) if name.startswith(("source.archive.", "source.pdf.", "source.xlsx.")) else
                await self._native_cmsearch_async(args, scope) if name == "rna.cmsearch" else
                await self._native_mapping_async(args, scope) if name == "reads.map" else
                await self._acquire_async(name, args, scope, operation_key) if name.startswith("public.") else None)
            if self.api_direct_hmmer_timing is not None:
                from .direct_hmmer_timing import DirectHmmerAcquisition
                if type(snapshot) is DirectHmmerAcquisition:
                    self._direct_hmmer_acquisitions.get().append(snapshot)
                    if snapshot.failure is not None:
                        raise snapshot.failure
                    snapshot = snapshot.snapshot
            with self.store.transaction():
                try:
                    result["result"], result["record_refs"] = self._perform(name, args, scope, snapshot)
                    result["status"] = "completed"
                    if name == "image.view":
                        # Only this host adapter can select a visual input. Never
                        # read attachment instructions from nested provider/model
                        # content, historical child work or a query response.
                        result["visual_inputs"] = [visual_input(self.store, result["result"]["view_ref"])]
                    if name == "reads.align" and result["result"].get("errors"):
                        result.update(status="partial" if result["record_refs"] else
                            "failed" if any(row.get("category") == "execution" for row in result["result"]["errors"]) else "invalid",
                            feedback={"category": "partial_execution" if result["record_refs"] else
                                "execution" if any(row.get("category") == "execution" for row in result["result"]["errors"]) else "arguments_or_reference",
                                "code": "selected_read_alignments_incomplete",
                                "rows": result["result"]["errors"]})
                    if name == "reads.map" and result["result"].get("projection_error_count"):
                        result.update(status="partial", feedback={"category": "representation",
                            "code": "native_mapping_rows_partially_projected", "rows": result["result"]["projection_errors"],
                            "error_count": result["result"]["projection_error_count"],
                            "error_source_ref": result["result"]["error_source_ref"]})
                    if name == "reads.map" and result["result"].get("resource_failure"):
                        result.update(status="partial" if result["result"]["reported_placement_count"] else "failed",
                            feedback={"category": "execution", "code": "local_job_resource_limit",
                                "source_ref": result["result"]["source_ref"],
                                "phase": result["result"]["resource_failure"]["phase"],
                                **result["result"]["resource_failure"]["operational"]})
                    elif name == "reads.map" and result["result"]["native_returncode"] != 0:
                        result.update(status="partial" if result["result"]["reported_placement_count"] else "failed",
                            feedback={"category": "execution", "code": "native_mapping_error",
                                "native_phase": result["result"]["native_phase"],
                                "native_returncode": result["result"]["native_returncode"],
                                "source_ref": result["result"]["source_ref"]})
                    if name == "material.parse":
                        attempt = result["result"]["parse_attempt"]
                        result["status"] = attempt["status"]
                        if attempt["status"] != "completed":
                            result["feedback"] = {"category": "representation", "code": attempt["code"],
                                "parse_ref": attempt["id"]}
                    if name == "source.xlsx.rows" and result["result"]["status"] != "completed":
                        result.update(status=result["result"]["status"],
                            feedback={"category": "representation", "code": "xlsx_rows_partially_decoded",
                                "source_ref": result["result"]["source_ref"],
                                "cell_error_count": result["result"]["cell_error_count"],
                                "row_error_count": result["result"]["row_error_count"],
                                "parse_failures": result["result"]["parse_failures"]})
                    if name in {"public.rhea.search", "public.rhea.reaction", "public.chebi.search", "public.chebi.compound"} and result["result"].get("projection_errors"):
                        result.update(status="partial", feedback={"category": "representation",
                            "code": "chemistry_rows_partially_projected",
                            "source_ref": result["result"]["source_ref"],
                            "rows": result["result"]["projection_errors"]})
                    if name in {"public.rfam.search", "public.rfam.collect", "public.blast.search", "public.blast.collect"} and result["result"].get("projection_errors"):
                        result.update(status="partial", feedback={"category": "representation",
                            "code": "blast_rows_partially_projected" if name.startswith("public.blast.") else "rfam_rows_partially_projected", "source_ref": result["result"]["source_ref"],
                            "rows": result["result"]["projection_errors"]})
                    if isinstance(snapshot, RfamModelSnapshots) and snapshot.metadata_error:
                        error = snapshot.metadata_error
                        result.update(status="partial", feedback={"category": "provider",
                            "code": "rfam_metadata_acquisition_failed", "cause_code": error.code,
                            "diagnostic_ref": self._acquisition_diagnostic(error),
                            "retained_model_ref": result["result"]["model_ref"]})
                    if isinstance(snapshot, PmcFiles) and snapshot.error:
                        result.update(status="partial", feedback={"category": "provider", "code": snapshot.error.code,
                            "diagnostic_ref": self._acquisition_diagnostic(snapshot.error)})
                    if name in {"public.pmc.files", "public.pmc.asset"} and result["result"].get("representation_feedback"):
                        result.update(status="partial", feedback=result["result"]["representation_feedback"])
                except Exception as error:
                    # Keep completed independent publications. A failed parser
                    # or later row does not erase an acquired source or an
                    # earlier valid candidate. Report the exact retained rows.
                    if not self._written:
                        raise
                    result.update(status="partial", record_refs=list(dict.fromkeys(self._written)),
                        result={"retained_record_refs": list(dict.fromkeys(self._written))},
                        feedback={"category": "partial_execution", "code": str(error) if isinstance(error, ContractError) else "adapter_partial_result",
                                  "diagnostic_ref": self.store.artifact(f"{type(error).__name__}: {error}", "text/plain")})
                    if isinstance(error, ContractError) and error.detail:
                        result["feedback"]["detail"] = error.detail
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
                          feedback={"category": "execution" if error.code.startswith("local_job_") or error.phase in {
                              'native_execution', 'local_execution', 'local_preflight'} else "provider", "code": error.code, "retry_after": error.retry_after,
                                    "job_ref": error.job_ref, "diagnostic_ref": diagnostic,
                                    **({"phase": error.phase} if error.phase is not None else {}),
                                    **operational})
        except (ContractError, ValueError, KeyError) as error:
            result["feedback"] = {"category": "arguments_or_reference", "code": str(error) if isinstance(error, ContractError) else "invalid_tool_input"}
            if isinstance(error, ContractError) and error.detail:
                result["feedback"]["detail"] = error.detail
        except Exception as error:
            diagnostic = self.store.artifact(f"{type(error).__name__}: {error}", "text/plain")
            result.update(status="failed", feedback={"category": "execution", "code": "adapter_execution_failed",
                                                    "diagnostic_ref": diagnostic})
        # Failed attempts are durable audit, not acquired scientific units.
        # An operation key identifies this attempt; later attempts need a new key.
        with self.store.transaction():
            self._save(operation_key, name, args, scope, result)
        return result

    def _save(self, key: str, name: str, args: dict, scope: dict | None, result: dict) -> None:
        direct = self._direct_hmmer_acquisitions.get()
        if direct:
            acquired = direct[-1]
            result.update(api_timing_disposition=deepcopy(acquired.api_timing_disposition),
                api_timing_refs=list(acquired.api_timing_refs),
                provider_operation_refs=list(acquired.provider_operation_refs))
        receipts = self._native_execution_refs.get()
        if receipts:
            result['native_execution_refs'] = list(dict.fromkeys(receipts))
            result['record_refs'] = list(dict.fromkeys([*result['record_refs'], *receipts]))
        batch = self._publication_batch.get()
        if batch is not None:
            result["published_batch"] = dict(batch)
        self.store.db.execute("INSERT INTO tool_operations VALUES(?,?,?,?,?,?)",
            (key, result["operation_ref"], name, canonical(args), canonical(scope), canonical(result)))

    async def _sequence_worker_async(self, operation: str, arguments: dict, *, directory: Path) -> SequenceWork:
        """Native work has no Store handle and no in-process fallback.

        This method is the explicit native-worker seam for synthetic publisher
        tests; production always uses the common bounded local-job runner.
        """
        if self.store.db.in_transaction:
            raise ContractError("native_sequence_work_requires_no_active_store_transaction")
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix="sequence-",
                suffix=".request.json", dir=directory, delete=False) as handle:
            json.dump({"operation": operation, "arguments": arguments}, handle, allow_nan=False)
            request = Path(handle.name)
        output = request.with_suffix(".result.json")
        stdout, stderr = request.with_suffix(".stdout"), request.with_suffix(".stderr")
        environment = dict(os.environ)
        package_root = str(Path(__file__).resolve().parent.parent)
        environment["PYTHONPATH"] = package_root + os.pathsep + environment.get("PYTHONPATH", "")
        # cwd includes retained earlier sibling results, so the common scratch
        # monitor covers the entire staged selected operation, not just this row.
        completed = False
        try:
            job = await run_local_job_async([sys.executable, "-m", "gene_annotation_episode.sequence_worker",
                str(request), str(output)], cwd=directory, policy=self.local_job_policy,
                stdout_path=stdout, stderr_path=stderr, env=environment,
                **({'statistics': self.native_statistics.for_alignment(arguments, self.local_job_policy)}
                   if operation == 'align_pair' and self.native_statistics is not None else {}))
            if job.returncode == 2 and output.is_file():
                failure = json.loads(output.read_text(encoding="utf-8"))
                if failure.get("exception_type") == "ValueError":
                    raise ContractError(failure["code"], detail={'native_execution': job.metadata})
            if job.returncode != 0:
                worker_failure = {}
                if job.returncode == 3 and output.is_file():
                    failure = json.loads(output.read_text(encoding="utf-8"))
                    if failure.get("exception_type") == "MemoryError":
                        worker_failure = {"worker_failure": "native_memory_allocation_failed"}
                diagnostic = artifact_file(self.store, stderr, "text/plain") if stderr.exists() else None
                raise AcquisitionError("local_job_execution_failed", phase="local_execution", operational={
                    **job.metadata, **worker_failure, "diagnostic_ref": diagnostic,
                    "native_returncode": job.returncode, "worker_operation": operation})
            if not output.is_file():
                raise AcquisitionError("local_job_output_missing", phase="local_execution", operational={
                    **job.metadata, "worker_operation": operation})
            completed = True
            return SequenceWork(output, job.metadata)
        finally:
            # Keep only the staged successful native body until publication.
            request.unlink(missing_ok=True)
            stdout.unlink(missing_ok=True)
            stderr.unlink(missing_ok=True)
            if not completed:
                output.unlink(missing_ok=True)

    async def _prepare_sequence_work_async(self, name: str, args: dict, scope: dict | None):
        if self.store.db.in_transaction:
            raise ContractError("native_sequence_work_requires_no_active_store_transaction")
        directory = Path(tempfile.mkdtemp(prefix=".native-sequence-", dir=self.store.path))
        self._mapping_directories.get().append(directory)
        if name == "reads.align":
            prepared = []
            for index, reference in enumerate(args["subject_refs"]):
                selected = {"query_ref": reference,
                    **{key: args[key] for key in ("reference_ref", "molecule", "mode")}}
                try:
                    if self.store.get(reference)["record_type"] != "read_subject":
                        raise ContractError("original_read_subject_required")
                    native = await self._prepare_alignment_async(selected, scope, directory)
                    prepared.append({"arguments": selected, "native": native})
                except (ContractError, ValueError, AcquisitionError) as error:
                    operational = isinstance(error, AcquisitionError)
                    row = {"row_index": index, "subject_ref": reference,
                        "code": error.code if operational else str(error) if isinstance(error, ContractError) else "native_alignment_input_error"}
                    if operational:
                        row.update(category="execution", phase=error.phase, **(error.operational or {}))
                    elif isinstance(error, ContractError) and error.detail:
                        row["detail"] = error.detail
                    prepared.append({"error": row})
            return prepared
        if name == "sequence.align":
            return await self._prepare_alignment_async(args, scope, directory)
        subject = self.store.get(args["subject_ref"])
        sequence = self._sequence(subject["id"], molecule_model="dna")
        start, end = args.get("start", 0), args.get("end", len(sequence))
        if not 0 <= start < end <= len(sequence):
            raise ContractError("requested_interval_outside_subject")
        footprint = self.store.map_segments(subject["id"], [{"start": start, "end": end}])
        self._check_sequence_operand(subject["id"], scope, footprint=footprint)
        if self.store.sequence_mapping(subject["id"])["units_per_symbol"] != 1:
            raise ContractError("translation_requires_nucleotide_symbol_mapping")
        return await self._sequence_worker_async("predict_genes", {"sequence": sequence[start:end],
            "code": args["code"], "mode": args["mode"]}, directory=directory)

    def _alignment_arguments(self, args, scope):
        query = self._check_sequence_operand(args["query_ref"], scope)
        self.store.subject_length(args["reference_ref"])
        return query, {'query': self._sequence(query['id'], molecule_model=args['molecule']),
            'reference': self._sequence(args['reference_ref'], molecule_model=args['molecule']),
            'molecule': args['molecule'], 'mode': args['mode']}

    def _estimate_native(self, args, scope):
        from .execution_expectations import capture_execution_scopes
        if args['tool'] == 'sequence.align':
            _, native = self._alignment_arguments(args['arguments'], scope)
            execution_class = self.native_statistics.alignment_class(native, self.local_job_policy)
        else:
            _, path, operation, selected = self._spreadsheet_arguments(args['tool'], args['arguments'])
            execution_class = self.native_statistics.spreadsheet_class(path, operation, selected, self.local_job_policy)
        recovery = self.native_statistics.recover_pending_statistics()
        return {'tool': args['tool'], 'arguments': args['arguments'],
            'execution_expectations': {**capture_execution_scopes(self.native_statistics.history_path, [execution_class]),
                                       'statistics_recovery': recovery}}

    def _estimate_execution(self, args, scope, *, api_scope):
        if args['tool'] == 'public.hmmer.search':
            if self.api_execution_planner is None:
                raise ContractError('api_execution_planner_unavailable')
            try:
                return self.api_execution_planner.estimate(args, scope=api_scope)
            except ContractError:
                raise
            except ValueError as error:
                raise ContractError(str(error)) from error
        return self._estimate_native(args, scope)

    async def _prepare_alignment_async(self, args: dict, scope: dict | None, directory: Path):
        query, arguments = self._alignment_arguments(args, scope)
        operands = [{'role': 'query', 'subject_ref': query['id']},
                    {'role': 'reference', 'subject_ref': args['reference_ref']}]
        try:
            native = await self._sequence_worker_async('align_pair', arguments, directory=directory)
        except (AcquisitionError, ContractError) as error:
            metadata = error.operational if isinstance(error, AcquisitionError) else error.detail.get('native_execution')
            if metadata:
                self._record_native_execution(metadata, operation='align_pair', operands=operands)
            raise
        self._record_native_execution(native.metadata, operation='align_pair', operands=operands)
        return native

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

    def _publish_read_alignments(self, args, scope, prepared):
        batch = self._begin_publication_batch(failures=True)
        rows, errors, refs, completed = [], [], [], 0
        for index, item in enumerate(prepared):
            before = len(self._written)
            if "error" in item:
                errors.append(item["error"])
                batch["failure_rows_total"] = len(errors)
                continue
            try:
                result, published = self._align_one(item["arguments"], scope, item["native"])
                refs.extend(published)
                completed += 1
                batch["published_rows_total"] = completed
                if len(rows) < 12:
                    rows.append({"subject_ref": args["subject_refs"][index], **result})
            except (ContractError, ValueError) as error:
                refs.extend(self._written[before:])
                errors.append({"row_index": index, "subject_ref": args["subject_refs"][index],
                    "code": str(error) if isinstance(error, ContractError) else "native_alignment_input_error",
                    **({"detail": error.detail} if isinstance(error, ContractError) and error.detail else {})})
                batch["failure_rows_total"] = len(errors)
            finally:
                item["native"].output_path.unlink(missing_ok=True)
        return {"count": len(args["subject_refs"]), "completed_count": completed,
            "records": rows, "preview_limit": 12, "errors": errors,
            "more_records_available_through_state_query": completed > 12,
            "target_annotation": "not_performed"}, list(dict.fromkeys(refs))

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
            output = await self._native_thread_async(pdf_native, path, operation=operation, executables=dict(self.pdf_executables),
                job_limits=self.local_job_policy.to_dict(),
                first_page=args.get("page"), last_page=args.get("page"), page=args.get("page"),
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
        derivative = self._put("source_derivative", {"source_ref": source["id"],
            "parent_source_ref": metadata["parent_source_ref"], "transformation": transformation,
            "selection_ref": args.get("member_ref"), "page": args.get("page"),
            "layout": args.get("layout", "reading_order") if transformation == "pdf_text" else None,
            "dpi": args.get("dpi", 150) if transformation == "pdf_page" else None,
            "coordinate_system": "original_member_bytes" if transformation == "archive_member" else
                "normalized_utf8_bytes" if transformation == "pdf_text" else "one_based_physical_pdf_page"}, origin="tool")
        return {"source_ref": source["id"], "material_ref": material["id"], "derivation_ref": derivative["id"],
            "artifact_ref": source["artifact_ref"], "media_type": media_type,
            "image_source_ref": source["id"] if media_type.startswith("image/") else None,
            "page": args.get("page"), "coordinate_system": derivative["coordinate_system"],
            "provenance": metadata, "biological_interpretation": "not_performed"}, [source["id"], material["id"], derivative["id"]]

    def _acquisition_diagnostic(self, error: AcquisitionError) -> str:
        snapshot = error.snapshot
        details = {"code": error.code, "phase": error.phase, "details": error.diagnostic}
        if snapshot:
            details.update(content_ref=self.store.artifact(snapshot.content, snapshot.media_type),
                url=snapshot.url, request=snapshot.request, transport=snapshot.transport)
        return self.store.artifact(canonical(details), "application/json")

    async def _native_cmsearch_async(self, args: dict, scope: dict | None) -> NativeSearch:
        subject = self._check_sequence_operand(args["subject_ref"], scope)
        molecule = self.store.subject_molecule(subject["id"])
        if molecule == "protein":
            raise ContractError("cmsearch_requires_nucleotide_operand")
        model = self.store.get(args["model_ref"])
        if model["record_type"] != "reference" or model["reference_type"] != "family":
            raise ContractError("acquired_covariance_model_reference_required")
        source = self.store.get(model["source_ref"])
        if source["provider"] != "rfam_covariance_model":
            raise ContractError("acquired_covariance_model_source_required")
        # All Store reads are on the owning thread. Only immutable bytes and
        # settings cross to the worker; no write transaction spans native work.
        if self.store.db.in_transaction:
            raise ContractError("native_search_requires_no_active_store_transaction")
        orientation_model = molecule if molecule in {"dna", "rna"} else "rna"
        native = await self._native_thread_async(run_cmsearch,
            sequence=self._sequence(subject["id"], molecule_model=orientation_model),
            subject_ref=subject["id"], model=self.store.get_artifact(source["artifact_ref"]),
            model_ref=model["id"], configuration=dict(self.cmsearch_configuration), parameters=args.get("parameters"),
            job_limits=self.local_job_policy.to_dict())
        native = replace(native, metadata={**native.metadata, "operand_molecule_declaration": molecule,
            "orientation_processing_model": orientation_model,
            "orientation_model_is_input_classification": False})
        if native.metadata["returncode"] != 0:
            diagnostic = self._native_artifacts(native)
            raise AcquisitionError("cmsearch_native_error", phase="native_execution",
                operational={"diagnostic_ref": self.store.artifact(canonical(diagnostic), "application/json"),
                    "native_returncode": native.metadata["returncode"],
                    "native_stderr_tail": native.stderr[-4000:].decode("utf-8", errors="replace"),
                    "native_stdout_tail": native.stdout[-4000:].decode("utf-8", errors="replace")})
        return native

    def _native_artifacts(self, native: NativeSearch) -> dict:
        return {**native.metadata, **{key + "_ref": self.store.artifact(value,
            "text/x-fasta" if key == "input_fasta" else "text/plain") for key, value in
            (("stdout", native.stdout), ("stderr", native.stderr), ("table", native.table),
             ("input_fasta", native.input_fasta), ("native_help", native.help_output))}}

    async def _native_mapping_async(self, args, scope):
        import tempfile
        selection = self.store._require(args["query_selection_ref"], {"read_selection"})
        selected_scope = {"subject_refs": [selection["library_ref"]], "read_selection_refs": [selection["id"]]}
        self.store.validate_scope(selected_scope, parent_scope=scope)
        mapper.settings(args["preset"], args.get("parameters"))
        if self.store.db.in_transaction:
            raise ContractError("native_mapping_requires_no_active_store_transaction")
        directory = Path(tempfile.mkdtemp(prefix=".native-read-mapping-", dir=self.store.path))
        self._mapping_directories.get().append(directory)
        source_refs = set()
        import sqlite3
        with sqlite3.connect(directory/"operands.sqlite") as index:
            index.execute("CREATE TABLE operands(role TEXT,subject_ref TEXT,length INTEGER,PRIMARY KEY(role,subject_ref))")
            for role, filename, subjects in (
                ("query", "queries.fasta", (row[0] for row in self.store.db.execute(
                    "SELECT read_ref FROM library_selection_members WHERE selection_ref=? ORDER BY read_ref", (selection["id"],)))),
                ("reference", "references.fasta", iter(args["reference_refs"]))):
                with (directory/filename).open("w", encoding="ascii") as handle:
                    for reference in subjects:
                        row = self._check_sequence_operand(reference, scope) if role == "query" else self.store.get(reference)
                        if row["record_type"] not in {"input", "read_subject", "reference", "feature", "product"}:
                            raise ContractError("sequence_operand_required")
                        if self.store.subject_molecule(reference) == "protein":
                            raise ContractError("native_genomic_mapping_requires_nucleotide_operand",
                                detail={"role": role, "subject_ref": reference})
                        sequence = self._sequence(reference, molecule_model="dna")
                        if not sequence or not set(sequence.upper()) <= set("ACGTRYSWKMBDHVN"):
                            raise ContractError("native_mapping_requires_DNA_processing_alphabet",
                                detail={"role": role, "subject_ref": reference,
                                    "input_classification_changed": False})
                        handle.write(">" + reference + "\n" + sequence + "\n")
                        index.execute("INSERT INTO operands VALUES(?,?,?)", (role, reference, len(sequence)))
                        if row.get("source_ref"):
                            source_refs.add(row["source_ref"])
            count = index.execute("SELECT count(*) FROM operands WHERE role='query'").fetchone()[0]
        if count != selection["member_count"]:
            raise ContractError("selected_read_index_membership_mismatch")
        metadata = {"query_selection_ref": selection["id"], "library_ref": selection["library_ref"],
            "query_count": count, "selection_membership_sha256": selection["membership_sha256"],
            "reference_refs": args["reference_refs"], "source_refs": sorted(source_refs),
            "staged_header_meaning": "actual_stable_subject_ids_not_native_title_or_biological_identity",
            "query_fasta_sha256": mapper.file_digest(directory/"queries.fasta"),
            "reference_fasta_sha256": mapper.file_digest(directory/"references.fasta")}
        return await mapper.run_mapping(directory, configuration=dict(self.minimap2_configuration),
            preset=args["preset"], parameters=args.get("parameters"), input_metadata=metadata,
            job_limits=self.local_job_policy.to_dict())

    def _publish_mapping(self, args, native):
        batch = self._begin_publication_batch(failures=True)
        from .materials import artifact_file
        artifacts = {}
        for name in ("queries.fasta", "references.fasta", "mappings.paf", "mapping.stderr", "version.stdout",
                "version.stderr", "help.stdout", "help.stderr", "index.stdout", "index.stderr", "projection-errors.jsonl"):
            if native.path(name).is_file():
                artifacts[name] = artifact_file(self.store, native.path(name),
                    "text/x-fasta" if name.endswith(".fasta") else "text/plain")
        source = self._source("minimap2.mapping", {**native.metadata, "artifacts": artifacts},
            software_version=native.metadata["native_version"],
            parent_source_refs=native.metadata["input_metadata"]["source_refs"],
            stdout_ref=artifacts.get("mappings.paf", artifacts.get("index.stdout")),
            stderr_ref=artifacts.get("mapping.stderr", artifacts.get("index.stderr")),
            auxiliary_artifact_refs=list(dict.fromkeys(artifacts.values())),
            operand_refs=args["reference_refs"], query_selection_ref=args["query_selection_ref"])
        preview, refs, total = [], [source["id"]], 0
        self._batch_observations(batch, source["id"])
        if native.path("placements.jsonl").is_file():
            with native.path("placements.jsonl").open() as handle:
                for line in handle:
                    row = json.loads(line)
                    values = measurements(reference_ref=ref(row["reference_name"]),
                        identity_fraction=number(row["matching_bases"]/row["block_length"]),
                        query_coverage=number((row["query_interval"][1]-row["query_interval"][0])/row["query_length"]),
                        target_coverage=number((row["reference_interval"][1]-row["reference_interval"][0])/row["reference_length"]),
                        query_start=number(row["query_interval"][0]), query_end=number(row["query_interval"][1]))
                    score = next((item for item in row["tags"] if item["name"] == "AS" and item["type"] == "i"), None)
                    if score:
                        values += measurements(alignment_score=number(int(score["value"])))
                    observation = self._put("observation", {"kind": "alignment", "subject_refs": [row["query_name"]],
                        "source_subject_refs": [row["reference_name"]], "source_ref": source["id"],
                        "measurements": values, "dependencies": list(dict.fromkeys(
                            [row["query_name"], row["reference_name"], args["query_selection_ref"]])),
                        "anchor": None, "operand_intervals": [{"role": role, "subject_ref": subject, "start": interval[0],
                            "end": interval[1], "unit": self.store.subject_unit(subject), "model_unit": "nt"}
                            for role, subject, interval in (("query", row["query_name"], row["query_interval"]),
                                ("reference", row["reference_name"], row["reference_interval"]))],
                        "native_minimap2": {key: row[key] for key in ("line_number", "row_start", "row_end", "strand",
                            "mapping_quality", "native_alignment_type")}}, origin="tool")
                    total += 1
                    batch["published_rows_total"] = total
                    refs.append(observation["id"])
                    if len(preview) < 12:
                        preview.append({"observation_ref": observation["id"], **{key: value for key, value in row.items()
                            if key not in {"tags", "cigar", "cs"}}})
        errors, error_count = [], 0
        error_source_ref = None
        if native.path("projection-errors.jsonl").is_file():
            with native.path("projection-errors.jsonl").open() as handle:
                for line in handle:
                    error_count += 1
                    batch["failure_rows_total"] = error_count
                    if len(errors) < 12:
                        errors.append(json.loads(line))
            if error_count:
                error_source = self._put("source", {"provider": "minimap2.projection_errors", "accession": None, "uri": None,
                    "artifact_ref": artifacts["projection-errors.jsonl"], "text_ref": artifacts["projection-errors.jsonl"],
                    "request_ref": None, "version": mapper.VERSION, "retrieved_at": native.metadata["finished_at"],
                    "parent_source_refs": [source["id"]]}, origin="tool")
                error_source_ref = error_source["id"]
                refs.append(error_source_ref)
        # This is custody of the executed search and its exact selection, not
        # a placement/absence claim about a library or organism. It anchors
        # zero-result native source/operand closure using the existing zero-
        # credit source_content meaning and creates no additional own action.
        summary = None
        if not native.metadata.get("resource_failure"):
            summary = self._observation("source_content", [native.metadata["input_metadata"]["library_ref"]], source,
                measurements(count=number(total)), references=args["reference_refs"],
                dependencies=[args["query_selection_ref"], *args["reference_refs"]], operand_intervals=[])
            refs.append(summary["id"])
        return {"source_ref": source["id"], "query_selection_ref": args["query_selection_ref"],
            "query_count": native.metadata["input_metadata"]["query_count"], "reference_refs": args["reference_refs"],
            "reported_placement_count": total, "records": preview, "preview_limit": 12,
            "search_result_observation_ref": summary["id"] if summary else None,
            "native_result_type": "minimap2_placements_v1",
            "record_refs_are_preview": False,
            "all_observations_query": {"kind": "observation", "references": [source["id"]], "offset": 0, "limit": 12},
            "query_result_kinds": ["alignment", "source_content"],
            "projection_error_count": error_count, "projection_errors": errors, "error_source_ref": error_source_ref,
            **({"resource_failure": native.metadata["resource_failure"]} if native.metadata.get("resource_failure") else {}),
            "native_returncode": native.metadata["returncode"], "native_phase": native.metadata["phase"],
            "native_settings": native.metadata["settings"], "resource_binding": native.metadata["configuration"],
            "index": {key: native.metadata["index"][key] for key in ("cache_key", "reused", "index_sha256")}
                if "index" in native.metadata else None,
            "target_annotation": "not_performed", "result_meaning":
                "partial_native_reported_placements_from_resource_limited_search_not_biological_absence"
                    if native.metadata.get("resource_failure") else "native_reported_placements_under_recorded_search_not_biological_absence"}, refs

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
        if name == "public.rfam.search":
            row = self._check_sequence_operand(args["subject_ref"], scope)
            if self.store.subject_molecule(row["id"]) == "protein":
                raise ContractError("rfam_nucleotide_operand_required")
            sequence = self._sequence(row["id"], molecule_model="rna")
            return await self.remote_searches.search(operation_key, subject_ref=row["id"],
                query_fasta=f">{row['id']}\n{sequence}", algorithm="cmscan", database="Rfam", provider="rfam")
        if name == "public.rfam.collect":
            job = self.remote_searches.describe(args["job_ref"])
            if job["request"].get("provider", "hmmer") != "rfam":
                raise ContractError("provider_job_does_not_belong_to_rfam")
            self._check_sequence_operand(job["request"]["subject_ref"], scope)
            return await self.remote_searches.collect(args["job_ref"])
        if name == "public.hmmer.search":
            if self.api_direct_hmmer_timing is not None:
                return await self.api_direct_hmmer_timing.acquire(name, args,
                    scope=self.store.validate_scope(scope), operation_key=operation_key)
            from .communication import plain
            from .hmmer_request_preparation import prepare_hmmer_request
            def sequence_symbols(reference, *, scope):
                row = self._check_sequence_operand(reference, scope)
                return self._sequence(row['id'], molecule_model='protein')
            prepared = prepare_hmmer_request(args, sequence_symbols=sequence_symbols, scope=scope)
            snapshot = await self.remote_searches.search(operation_key, query_fasta=prepared.query_fasta,
                **plain(prepared.normalized_arguments))
            return replace(snapshot, request={**snapshot.request, "molecule_model": "protein",
                "molecule_assignment": "not_performed"})
        if name in {"public.hmmer.collect", "public.hmmer.page"}:
            job = self.remote_searches.describe(args["job_ref"])
            request = job["request"]
            if request.get("provider", "hmmer") != "hmmer":
                raise ContractError("provider_job_does_not_belong_to_hmmer")
            self._check_sequence_operand(request["subject_ref"], scope)
            if name == 'public.hmmer.collect' and self.api_direct_hmmer_timing is not None:
                from .direct_hmmer_timing import membership_error
                membership = self.api_direct_hmmer_timing.planner.ports.operations.classify_order(args['job_ref'])
                if membership['state'] == 'registered' and membership['code'] is None:
                    return await self.api_direct_hmmer_timing.acquire(name, args,
                        scope=self.store.validate_scope(scope), operation_key=operation_key)
                if membership['state'] != 'unregistered' or membership['code'] is not None:
                    membership_error(membership, job_ref=args['job_ref'])
            snapshot = (await self.remote_searches.collect(args["job_ref"]) if name.endswith("collect") else
                await self.remote_searches.page(args["job_ref"], page=args["page"], page_size=args.get("page_size")))
            return replace(snapshot, request={**snapshot.request, "molecule_model": "protein",
                "molecule_assignment": "not_performed"})
        function, arguments = self._acquisition_request(name, args, scope)
        return await asyncio.to_thread(function, **arguments)

    def _acquisition_request(self, name: str, args: dict, scope: dict | None) -> tuple[Any, dict]:
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
        if name == "public.hmmer.databases":
            return self.clients.hmmer_databases, args
        raise ContractError("unimplemented_public_acquisition")

    def _perform(self, name: str, args: dict, scope: dict | None, snapshot: Any) -> tuple[dict, list[str]]:
        if name == 'execution.estimate':
            return snapshot, []
        if name == "sequence.align":
            return self._align_one(args, scope, snapshot)
        if name == "reads.align":
            return self._publish_read_alignments(args, scope, snapshot)
        if name == "genes.predict":
            return self._derive(name, args, scope, snapshot)
        if isinstance(snapshot, mapper.NativeMapping):
            return self._publish_mapping(args, snapshot)
        if isinstance(snapshot, DocumentOutput):
            return self._publish_document(name, args, snapshot)
        if isinstance(snapshot, PmcFiles):
            return self._publish_pmc_files(args, snapshot)
        if name == "public.pmc.versions":
            return self._publish_pmc_versions(args, snapshot)
        if name == "public.pmc.asset":
            return self._publish_pmc_asset(args, snapshot)
        if name == "material.from_source":
            material = self.store.register_material(source_ref=args["source_ref"], format=args.get("format", "auto"), use="evidence")
            self._written.append(material["id"])
            return {"material_ref": material["id"], "source_ref": material["source_ref"],
                "parse_with": {"material_ref": material["id"]}, "target_binding_changed": False}, [material["id"]]
        if name == "material.parse":
            attempt = self.store.parse_material(**args)
            refs = [attempt["source_ref"], attempt["id"]]
            if attempt.get("native_source_ref") is not None:
                refs.append(attempt["native_source_ref"])
            if attempt["collection_ref"] is not None:
                refs.append(attempt["collection_ref"])
            self._written.extend(refs)
            return {"parse_attempt": attempt}, refs
        if name == "library.members":
            return libraries.member_page(self.store, scope=scope, **args), []
        if name == "library.select":
            selected = libraries.select(self.store, scope=scope, **args)
            self._written.append(selected["id"])
            return {"selection": selected, "scope": {"subject_refs": [selected["library_ref"]],
                "read_selection_refs": [selected["id"]]}}, [selected["id"]]
        if name == "library.read":
            subject = self.store._require(args["subject_ref"], {"read_subject"})
            offset, limit = args.get("offset", 0), args.get("limit", 12000)
            if type(offset) is not int or not 0 <= offset <= subject["length"] or type(limit) is not int or limit < 1:
                raise ContractError("invalid_member_window")
            end = min(offset + limit, subject["length"])
            if offset < end:
                footprint = self.store.map_segments(subject["id"], [{"start": offset, "end": end}])
                self._check_sequence_operand(subject["id"], scope, footprint=footprint)
            elif not self.store.scope_dimension_segments(scope, subject["id"]):
                # The normal EOF window contains no sequence positions. It is
                # readable only for an actually assigned original member.
                raise ContractError("subject_outside_assigned_scope")
            body = self.store.material_member(subject["member_ref"], offset=offset, limit=limit)
            return {"subject_ref": subject["id"], "library_ref": subject["library_ref"], **body}, []
        if name == "reads.inspect":
            return self._inspect_reads(args, scope)
        if name == "material.annotations":
            return self.store.material_annotations(**args), []
        if name == "material.read":
            return self.store.material_read(**args), []
        if name == "material.members":
            return self.store.material_members(**args), []
        if name == "material.errors":
            return self.store.material_errors(**args), []
        if name == "material.member":
            body = self.store.material_member(**args)
            reference = self.store.material_reference(args["member_ref"])
            refs = [reference["id"], *reference["context_refs"]]
            self._written.extend(refs)
            return {**body, "reference_ref": reference["id"]}, refs
        if name == "material.header":
            return self.store.material_header(**args), []
        if isinstance(snapshot, NativeSearch):
            return self._publish_cmsearch(args, snapshot)
        if isinstance(snapshot, RfamModelSnapshots):
            return self._import_rfam(args, snapshot)
        if name == "public.search.jobs":
            permitted = set(self.store.validate_scope(scope)["subject_refs"])
            limit, offset = args.get("limit", 100), args.get("offset", 0)
            page = self.remote_searches.jobs(limit=limit+1, offset=offset, active_only=args.get("active_only", True))
            jobs = [job for job in page[:limit]
                    if set(self.store.roots(job["request"]["subject_ref"])) <= permitted]
            return {"jobs": jobs, "offset": offset, "next_offset": offset+limit if len(page)>limit else None}, []
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
        if name == "translation.codes":
            return {"codes": translation_codes(), "biopython_version": version("biopython")}, []
        if name == "reference.neighborhood":
            reference = self.store.get(args["reference_ref"])
            if reference["record_type"] != "reference" or reference.get("molecule") not in {"dna", "rna"}:
                raise ContractError("acquired_nucleotide_reference_required")
            original = self.store.get(reference["source_ref"])
            request = json.loads(self.store.get_artifact(original["request_ref"]))["request"] if original["request_ref"] else None
            body = genbank_neighborhood(self.store.get_artifact(original["artifact_ref"]),
                accession=reference["accession"], selector=args["selector"], left_bp=args["left_bp"],
                right_bp=args["right_bp"], source_request=request)
            source = self._source("genbank.neighborhood", {"source_ref": original["id"],
                "reference_ref": reference["id"], **body}, software_version=NEIGHBORHOOD_VERSION)
            observation = self._observation("context", [reference["id"]], source,
                measurements(reference_ref=ref(reference["id"]), count=number(len(body["features"]))),
                references=[reference["id"]], dependencies=[original["id"], reference["id"]])
            return {**body, "source_ref": source["id"], "observation_ref": observation["id"]}, [source["id"], observation["id"]]
        if name == "sequence.inspect":
            subject = self._check_sequence_operand(args["subject_ref"], scope)
            body = inspect_sequence(self._sequence(subject["id"]))
            source = self._source("sequence.inspect", body, software_version=version("biopython"))
            values = measurements(length=number(body["length"]))
            if body["gc_fraction"] is not None:
                values += measurements(gc_fraction=number(body["gc_fraction"]))
            observation = self._observation("sequence_composition", [subject["id"]], source, values)
            return {**body, "observation_ref": observation["id"]}, [source["id"], observation["id"]]
        if name in {"sequence.translate", "genes.predict", "sequence.view"}:
            return self._derive(name, args, scope)
        if name == "sequence.sites":
            return self._alignment_sites(args, scope)
        raise ContractError("unimplemented_tool")

    def _align_one(self, args, scope, native: SequenceWork):
        query = self._check_sequence_operand(args["query_ref"], scope)
        # A comparison operand is reusable evidence even when it is an
        # original caller sequence outside this local annotation assignment.
        self.store.subject_length(args["reference_ref"])
        body = json.loads(native.output_path.read_text(encoding="utf-8"))
        # Physical timing is execution information. Keeping it out of the
        # measurement body preserves the identity of unchanged scientific
        # evidence across independent physical runs.
        source = self._source("biopython.alignment", body, software_version=version("biopython"))
        values = measurements(reference_ref=ref(args["reference_ref"]))
        if body["aligned"]:
            values += measurements(identity_fraction=number(body["identity_fraction"]),
                                   query_coverage=number(body["query_coverage"]), target_coverage=number(body["reference_coverage"]),
                                   query_start=number(body["query_interval"][0]), query_end=number(body["query_interval"][1]),
                                   alignment_score=number(body["native_score"]))
        intervals = ([{"role": role, "subject_ref": subject_ref, "start": interval[0], "end": interval[1],
            "unit": self.store.subject_unit(subject_ref), "model_unit": "aa" if args["molecule"] == "protein" else "nt"}
            for role, subject_ref, interval in (("query", query["id"], body["query_interval"]),
                ("reference", args["reference_ref"], body["reference_interval"]))] if body["aligned"] else None)
        observation = self._observation("alignment", [query["id"]], source, values,
            references=[args["reference_ref"]], dependencies=list(dict.fromkeys([query["id"], args["reference_ref"]])),
            operand_intervals=intervals)
        preview = {key: value for key, value in body.items() if key not in {"aligned_query", "aligned_reference", "coordinates"}}
        return {**preview, "local_job": native.metadata,
            "observation_ref": observation["id"], "source_ref": source["id"]}, [source["id"], observation["id"]]

    def _alignment_sites(self, args, scope):
        alignment = self.store.get(args["alignment_ref"])
        if alignment.get("record_type") != "observation" or alignment.get("kind") != "alignment":
            raise ContractError("alignment_observation_required")
        if ("positions" in args) == ("window" in args):
            raise ContractError("choose_reference_positions_or_window",
                detail={"conflicting_or_missing_fields": ["positions", "window"]})
        positions = args.get("positions")
        if positions is None:
            start, end = args["window"]["start"], args["window"]["end"]
            if not start < end:
                raise ContractError("invalid_reference_window")
            positions = list(range(start, end))
        source = self.store.get(alignment["source_ref"])
        for subject in alignment["subject_refs"]:
            # Reusing an alignment does not rerun a full-read measurement.
            # Actual newly read query positions are checked below. A scoped
            # member must still be visible; comparison references are reusable.
            if self.store.roots(subject) and not self.store._in_scope(subject, self.store.validate_scope(scope)):
                raise ContractError("subject_outside_assigned_scope")
        extra, quality, encoding = {}, None, "unspecified"
        if source["provider"] == "biopython.alignment":
            body = json.loads(self.store.get_artifact(source["artifact_ref"]))
            sites = compare_sites(body, positions)
        elif source["provider"] == "native.phmmer.alignment":
            body = json.loads(self.store.get_artifact(source["artifact_ref"]))
            sites = compare_sites({"aligned": True, "reference_length": body["reference_length"],
                "query_interval": body["query_interval_aa_zero_based_half_open"],
                "reference_interval": body["reference_interval_aa_zero_based_half_open"],
                "aligned_query": body["query_aligned"].upper().replace('.', '-'),
                "aligned_reference": body["reference_aligned"].upper().replace('.', '-')}, positions)
        elif source["provider"] == "minimap2.mapping" and alignment.get("native_minimap2") is not None:
            native = alignment["native_minimap2"]
            with artifact_path(self.store, source["stdout_ref"]).open("rb") as handle:
                handle.seek(native["row_start"])
                row = mapper.parse_paf_line(handle.read(native["row_end"]-native["row_start"]))
            query = self.store.get(alignment["subject_refs"][0])
            if query["record_type"] == "read_subject":
                member = self.store.get(query["member_ref"])
                if query["quality_present"]:
                    quality = packing.component_window(self.store, member, "quality", 0, query["length"]).decode("ascii")
                encoding = query["quality_encoding"]
            extra = mapper.compare_paf_sites(row, positions, query=self._sequence(query["id"], molecule_model="dna"),
                reference=self._sequence(alignment["source_subject_refs"][0], molecule_model="dna"),
                quality=quality, quality_encoding=encoding)
            sites = extra.pop("sites")
        else:
            raise ContractError("native_alignment_site_mapping_unavailable")
        intervals = []
        for site in sites:
            if site["relationship"] == "outside_alignment":
                continue
            for role, refs, position in (("query", alignment["subject_refs"], site["query_position"]),
                ("reference", alignment["source_subject_refs"], site["reference_position"])):
                if position is not None and len(refs) == 1:
                    inherited = next((row for row in alignment.get("operand_intervals", ())
                        if row["role"] == role and row["subject_ref"] == refs[0]), {})
                    intervals.append({"role": role, "subject_ref": refs[0], "start": position,
                        "end": position+1, "unit": self.store.subject_unit(refs[0]),
                        **({"model_unit": inherited["model_unit"]} if "model_unit" in inherited else {})})
        for insertion in extra.get("insertions", []):
            intervals.append({"role": "query", "subject_ref": alignment["subject_refs"][0],
                "start": insertion["query_interval"][0], "end": insertion["query_interval"][1],
                "unit": self.store.subject_unit(alignment["subject_refs"][0]), "model_unit": "nt"})
        intervals = list({canonical(row): row for row in intervals}.values())
        for subject in alignment["subject_refs"]:
            query_spans = [{"start": row["start"], "end": row["end"]} for row in intervals
                if row["role"] == "query" and row["subject_ref"] == subject]
            if query_spans:
                footprint = None
                if self.store.roots(subject):
                    try:
                        footprint = self.store.map_segments(subject, query_spans)
                    except ContractError as error:
                        if str(error) != "subregion_mapping_unavailable":
                            raise
                        # An actual aggregate/correction sequence is still
                        # inspectable. Unknown original submaps require owning
                        # its existing aggregate footprint; do not invent one.
                        footprint = self.store.coverage(subject)
                self._check_sequence_operand(subject, scope, footprint=footprint)
        measured = self._source("alignment.sites", {"alignment_ref": alignment["id"], "native_provider": source["provider"],
            "requested_positions": positions, "sites": sites, **extra}, parent_source_refs=[source["id"]],
            software_version="literal_alignment_sites_v2")
        observation = self._observation("comparison", alignment["subject_refs"], measured,
            measurements(count=number(len(sites))), references=alignment["source_subject_refs"],
            dependencies=[alignment["id"]], operand_intervals=intervals)
        preview = {"sites": sites[:12], **{key: value for key, value in extra.items() if key != "insertions"}}
        if "insertions" in extra:
            preview.update(insertions=extra["insertions"][:12], insertion_count=len(extra["insertions"]))
        return {**preview, "site_count": len(sites), "preview_limit": 12,
            "complete_result_source_ref": measured["id"], "observation_ref": observation["id"],
            "source_ref": measured["id"]}, [measured["id"], observation["id"]]

    def _inspect_reads(self, args, scope):
        batch = self._begin_publication_batch()
        # Select explicitly, validate ownership first, then stream native rows.
        # No private controller loop or scientific judgment is hidden here.
        from .materials import artifact_file
        import tempfile
        import os
        subjects = [self._check_sequence_operand(ref, scope) for ref in args["subject_refs"]]
        if any(row["record_type"] != "read_subject" for row in subjects):
            raise ContractError("original_read_subject_required")
        with tempfile.TemporaryDirectory(prefix=".read-inspection-", dir=self.store.path) as directory:
            path = Path(directory) / "native.jsonl"
            with path.open("w") as handle:
                for subject in subjects:
                    body = {"subject_ref": subject["id"], **inspect_sequence(self._sequence(subject["id"]))}
                    handle.write(canonical(body) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            artifact = artifact_file(self.store, path, "application/x-ndjson")
            source = self._put("source", {"provider": "reads.inspect", "accession": None,
                "uri": None, "artifact_ref": artifact, "text_ref": artifact,
                "request_ref": self.store.artifact(canonical(args), "application/json"),
                "version": version("biopython"), "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "parent_source_refs": sorted({row["source_ref"] for row in subjects})}, origin="tool")
            preview, refs = [], [source["id"]]
            self._batch_observations(batch, source["id"])
            with path.open() as handle:
                for line in handle:
                    body = json.loads(line)
                    values = measurements(length=number(body["length"]))
                    if body["gc_fraction"] is not None:
                        values += measurements(gc_fraction=number(body["gc_fraction"]))
                    observed = self._observation("sequence_composition", [body["subject_ref"]], source, values,
                        dependencies=[body["subject_ref"]])
                    refs.append(observed["id"])
                    batch["published_rows_total"] += 1
                    if len(preview) < 12:
                        preview.append({**body, "observation_ref": observed["id"]})
            return {"count": len(subjects), "records": preview, "preview_limit": 12,
                "source_ref": source["id"], "more_records_available_through_state_query": len(subjects)>12,
                "target_annotation": "not_performed"}, refs

    def _import_blast(self, snapshot: SourceSnapshot) -> tuple[dict, list[str]]:
        job = self.remote_searches._get(snapshot.transport["job_ref"])
        submission = self.remote_searches._load_snapshot(job["submission"])
        submitted = self._source(submission.service, None, snapshot=submission)
        parsed = blast.document(snapshot.content)
        blast.validate_identity(parsed, snapshot.request)
        parents, refs = [submitted["id"]], [submitted["id"]]
        if parsed["member"] is not None:
            archive = self._source("ncbi_blast_archive", None, snapshot=snapshot, parent_source_refs=parents)
            refs.append(archive["id"])
            parents.append(archive["id"])
            snapshot = replace(snapshot, content=parsed["json_bytes"], media_type="application/json",
                transport={**snapshot.transport, "representation": "exact_blast_zip_member_bytes",
                    "archive_member": parsed["member"]})
        snapshot = replace(snapshot, transport={**snapshot.transport, "source_version_meaning": "native_blast_program_version_not_database_release"})
        source = self._source("ncbi_blast", None, snapshot=snapshot, parent_source_refs=parents,
            software_version=parsed["report"].get("version"))
        subject_ref = snapshot.request["subject_ref"]
        program = snapshot.request["algorithm"]
        query_unit, reference_unit, model_unit = blast.PROGRAM_UNITS[program]
        processing = self._put("context", {"context_type": "processing", "name": "blast_search_model",
            "source_ref": source["id"], "attributes": measurements(molecule_model=enum(
                "protein" if query_unit == "aa" else "dna")), "related_refs": [subject_ref]}, origin="tool")
        refs += [source["id"], processing["id"]]
        records, errors, hit_count, hsp_count = [], [], 0, 0
        for hit_index, hit in enumerate(parsed["search"].get("hits", [])):
            try:
                if not isinstance(hit, dict):
                    raise ValueError("blast_hit_object_required")
                length = blast.integer(hit["len"], "hit_length", minimum=1)
                descriptions = hit.get("description") or []
                if not isinstance(descriptions, list):
                    errors.append({"hit_ordinal": hit_index, "hsp_ordinal": None, "code": "blast_hit_description_array_required"})
                    descriptions = []
                valid_descriptions = []
                for description_index, description in enumerate(descriptions):
                    if isinstance(description, dict):
                        valid_descriptions.append((description_index, description))
                    else:
                        errors.append({"hit_ordinal": hit_index, "hsp_ordinal": None,
                            "description_ordinal": description_index, "code": "blast_hit_description_object_required"})
                descriptions = valid_descriptions
                first = descriptions[0][1] if descriptions else {}
                import re
                accession = first.get("accession") or first.get("id")
                accession_basis = "native_accession" if first.get("accession") else "native_id"
                if (not isinstance(accession, str) or len(accession)>200
                        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/+%#?=;&@~-]*", accession) is None):
                    accession = identity("source_local_hit", {"source_ref": source["id"], "hit_ordinal": hit_index})
                    accession_basis = "source_local_hit"
                label = first.get("title") or accession
                if not isinstance(label, str):
                    errors.append({"hit_ordinal": hit_index, "hsp_ordinal": None, "code": "blast_hit_title_not_string"})
                    label = accession
                terms = []
                for description_index, description in descriptions:
                    if description.get("taxid") is not None:
                        try:
                            taxid = blast.integer(description["taxid"], "taxid", minimum=1)
                            taxon_label = description.get("sciname")
                            if not isinstance(taxon_label, str) or len(taxon_label)>512 or "\n" in taxon_label or "\r" in taxon_label:
                                taxon_label = str(taxid)
                            term = self._put("term", {"namespace": "ncbi_taxonomy", "accession": str(taxid),
                                "label": taxon_label, "term_type": "taxon",
                                "source_ref": source["id"], "anchor": None}, origin="external")
                            terms.append(term["id"])
                        except (ValueError, TypeError) as error:
                            errors.append({"hit_ordinal": hit_index, "hsp_ordinal": None,
                                "description_ordinal": description_index, "code": str(error)})
                reference = self._put("reference", {"reference_type": "protein" if reference_unit == "aa" else "sequence",
                    "source_ref": source["id"], "accession": accession,
                    "label": label if len(label)<=512 and "\n" not in label and "\r" not in label else accession,
                    "sequence_ref": None, "molecule": "protein" if reference_unit == "aa" else "unspecified",
                    "length": length, "term_refs": list(dict.fromkeys(terms)), "context_refs": []}, origin="external")
                refs += terms + [reference["id"]]
                hit_count += 1
                hsps = hit.get("hsps", [])
                if not isinstance(hsps, list):
                    raise ValueError("blast_hsp_array_required")
            except (ValueError, TypeError, KeyError) as error:
                errors.append({"hit_ordinal": hit_index, "hsp_ordinal": None, "code": str(error)})
                continue
            for hsp_index, native in enumerate(hsps):
                try:
                    row = blast.hsp_row(native, program=program, query_length=snapshot.request["query_length"],
                        reference_length=length, hit_ordinal=hit_index, hsp_ordinal=hsp_index)
                    qi, ri = row["query_interval"], row["reference_interval"]
                    observation = self._put("observation", {"kind": "comparison", "subject_refs": [subject_ref],
                        "source_subject_refs": [reference["id"]], "source_ref": source["id"], "anchor": None,
                        "measurements": measurements(reference_ref=ref(reference["id"]),
                            **{key:number(value) for key,value in row["measurements"].items()}),
                        "dependencies": [subject_ref, reference["id"], processing["id"]],
                        "operand_intervals": [{"role": "query", "subject_ref": subject_ref, "start": qi[0], "end": qi[1],
                            "unit": self.store.subject_unit(subject_ref), "model_unit": model_unit},
                            {"role": "reference", "subject_ref": reference["id"], "start": ri[0], "end": ri[1],
                             "unit": self.store.subject_unit(reference["id"]), "model_unit": model_unit}],
                        "native_blast": row["native_blast"]}, origin="tool")
                    refs.append(observation["id"])
                    hsp_count += 1
                    if len(records) < 12:
                        records.append({"reference_ref": reference["id"], "observation_ref": observation["id"],
                            "accession": accession, "accession_basis": accession_basis, **row})
                except (ValueError, TypeError, KeyError) as error:
                    errors.append({"hit_ordinal": hit_index, "hsp_ordinal": hsp_index, "code": str(error)})
        return {"source_ref": source["id"], "submission_source_ref": submitted["id"],
            "job_ref": snapshot.transport["job_ref"], "rid": snapshot.request["job_id"], "subject_ref": subject_ref,
            "records": records, "preview_limit": 12, "projected_hit_count": hit_count,
            "projected_hsp_count": hsp_count, "native_hit_count": len(parsed["search"]["hits"]) if "hits" in parsed["search"] else None,
            "native_hit_array_present": "hits" in parsed["search"],
            "reported_hit_array_empty": parsed["search"].get("hits") == [],
            "more_records_available_through_state_query": hsp_count > 12, "projection_errors": errors,
            "requested_database": snapshot.request["database"], "effective_search_target": parsed["report"].get("search_target"),
            "native_program_version": parsed["report"].get("version"), "database_release": None,
            "native_parameters": parsed["report"].get("params"), "native_statistics": parsed["search"].get("stat"),
            "native_message": parsed["search"].get("message"), "adapter_version": blast.VERSION,
            "no_hit_meaning": ("explicit_empty_native_hit_array_for_submitted_operand_under_recorded_provider_search"
                if parsed["search"].get("hits") == [] else None),
            "functional_or_lineage_assignment": "not_performed"}, list(dict.fromkeys(refs))

    def _import_rfam_discovery(self, snapshot: SourceSnapshot) -> tuple[dict, list[str]]:
        # Submission and result sources form a forward export lineage. Neither
        # the native label nor a new external family becomes an input target.
        job = self.remote_searches._get(snapshot.transport["job_ref"])
        submission = self.remote_searches._load_snapshot(job["submission"])
        submitted = self._source(submission.service, None, snapshot=submission)
        source = self._source(snapshot.service, None, snapshot=snapshot,
                              parent_source_refs=[submitted["id"]])
        body = json.loads(snapshot.content)
        subject_ref = snapshot.request["subject_ref"]
        length = len(self._sequence(subject_ref, molecule_model="rna"))
        processing = self._put("context", {"context_type": "processing", "name": "rfam_nucleotide_search_model",
            "source_ref": source["id"], "attributes": measurements(molecule_model=enum("rna")),
            "related_refs": [subject_ref]}, origin="tool")
        refs, records, errors = [submitted["id"], source["id"], processing["id"]], [], []
        native_rows = 0
        for family_key, hits in body["hits"].items():
            if not isinstance(hits, list):
                errors.append({"family_key": family_key, "native_index": None,
                               "code": "rfam_family_hit_array_required"})
                continue
            native_rows += len(hits)
            for index, native in enumerate(hits):
                try:
                    row = rfam_hit_row(native, family_key=family_key, sequence_length=length)
                except (ValueError, TypeError) as error:
                    errors.append({"family_key": family_key, "native_index": index, "code": str(error)})
                    continue
                label = row["source_family_label"]
                family = self._put("reference", {"reference_type": "family", "source_ref": source["id"],
                    "accession": row["accession"], "label": label if len(label)<=512 and "\n" not in label and "\r" not in label else row["accession"],
                    "sequence_ref": None, "molecule": None, "length": None,
                    "term_refs": [], "context_refs": []}, origin="external")
                start, end = row["sequence_interval"]
                observation = self._observation("profile_match", [subject_ref], source,
                    measurements(profile_ref=ref(family["id"]), reference_ref=ref(family["id"]),
                        bitscore=number(row["bitscore"]), evalue=number(row["evalue"]),
                        gc_fraction=number(row["gc_fraction"]), strand=enum(row["strand"]),
                        query_start=number(start), query_end=number(end), query_coverage=number((end-start)/length)),
                    references=[family["id"]], dependencies=[subject_ref, family["id"], processing["id"]],
                    operand_intervals=[{"role": "query", "subject_ref": subject_ref, "start": start, "end": end,
                        "unit": self.store.subject_unit(subject_ref), "model_unit": "nt"}])
                refs += [family["id"], observation["id"]]
                records.append({"family_ref": family["id"], "observation_ref": observation["id"],
                    "family_key": family_key, "native_index": index, **row,
                    "native_alignment": native.get("alignment")})
        if native_rows != body["numHits"]:
            errors.append({"family_key": None, "native_index": None, "code": "rfam_native_hit_count_mismatch"})
        return {"source_ref": source["id"], "submission_source_ref": submitted["id"],
            "job_ref": snapshot.transport["job_ref"], "job_id": snapshot.request["job_id"],
            "subject_ref": subject_ref, "status": "SUCCESS", "native_hit_count": body["numHits"],
            "projected_hit_count": len(records), "records": records[:12], "preview_limit": 12,
            "more_records_available_through_state_query": len(records)>12, "projection_errors": errors,
            "raw_artifact_ref": source["artifact_ref"], "adapter_version": RFAM_DISCOVERY_VERSION,
            "database_release": None, "model_release": None,
            "native_search_parameters": "provider_defaults_not_exposed",
            "native_times": {key: body.get(key) for key in ("opened", "started", "closed")},
            "time_meaning": "native_strings_preserved_no_clock_correction_or_duration_inference",
            "model_consensus_positions_are_not_physical_reference_residues": True,
            "searched_scope": {"subject_ref": subject_ref, "start": 0, "end": length,
                "unit": self.store.subject_unit(subject_ref)},
            "no_hit_meaning": "no_reported_match_in_submitted_operand_under_unexposed_provider_defaults",
            "functional_or_lineage_assignment": "not_performed"}, list(dict.fromkeys(refs))

    def _import_rfam(self, args: dict, snapshots: RfamModelSnapshots) -> tuple[dict, list[str]]:
        model = self._source("rfam_covariance_model", None, snapshot=snapshots.model,
                             accession=args["accession"])
        refs = [model["id"]]
        header = model_header(snapshots.model.content)
        if header["accession"] != args["accession"]:
            raise ContractError("rfam_model_accession_mismatch")
        family = self._put("reference", {"reference_type": "family", "source_ref": model["id"],
            "accession": args["accession"], "label": header["description"] or header["name"],
            "sequence_ref": None, "molecule": None, "length": None, "term_refs": [], "context_refs": []}, origin="external")
        refs.append(family["id"])
        metadata_ref, metadata = None, None
        if snapshots.metadata is not None:
            source = self._source("rfam_family_metadata", None, snapshot=snapshots.metadata, accession=args["accession"])
            metadata_ref = source["id"]
            refs.append(metadata_ref)
            try:
                metadata = json.loads(snapshots.metadata.content)
            except (ValueError, UnicodeDecodeError) as error:
                raise ContractError("rfam_metadata_invalid_json", detail={"model_ref": family["id"],
                    "metadata_source_ref": metadata_ref}) from error
        return {"model_ref": family["id"], "source_ref": model["id"], "metadata_source_ref": metadata_ref,
            "model_header": header, "family_metadata": metadata,
            "model_consensus_positions_are_not_physical_sequence_residues": True,
            "target_annotation": "not_performed"}, refs

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

    def _publish_cmsearch(self, args: dict, native: NativeSearch) -> tuple[dict, list[str]]:
        artifacts = self._native_artifacts(native)
        source = self._source("infernal.cmsearch", artifacts, text=native.stdout.decode("utf-8"),
                              software_version=native.metadata["native_version"])
        refs, records = [source["id"]], []
        for row in iter_fmt3(native.table):
            header = native.metadata["model_header"]
            if (row["native_target_name"] != args["subject_ref"] or
                row["target_length"] != native.metadata["target_length"] or
                row["native_query_name"] != header["name"] or
                row["native_query_accession"] != header["accession"] or
                row["model_length"] != header["consensus_length"]):
                raise ContractError("native_cmsearch_operand_identity_mismatch")
            values = measurements(profile_ref=ref(args["model_ref"]), bitscore=number(row["bitscore"]),
                evalue=number(row["evalue"]), query_start=number(row["target_interval"][0]),
                query_end=number(row["target_interval"][1]),
                query_coverage=number((row["target_interval"][1]-row["target_interval"][0])/row["target_length"]))
            observation = self._put("observation", {"kind": "profile_match", "subject_refs": [args["subject_ref"]],
                "source_subject_refs": [args["model_ref"]], "source_ref": source["id"],
                "measurements": values, "dependencies": [args["subject_ref"], args["model_ref"]], "anchor": None,
                "operand_intervals": [{"role": "query", "subject_ref": args["subject_ref"],
                    "start": row["target_interval"][0], "end": row["target_interval"][1],
                    "unit": self.store.subject_unit(args["subject_ref"]), "model_unit": "nt"}],
                "native_cmsearch": {**row, "native_query_model_ref": args["model_ref"],
                    "native_target_subject_ref": args["subject_ref"]}}, origin="tool")
            refs.append(observation["id"])
            records.append({"observation_ref": observation["id"], **row})
        return {"source_ref": source["id"], "model_ref": args["model_ref"], "subject_ref": args["subject_ref"],
            "reported_hit_count": len(records), "records": records[:12], "preview_limit": 12,
            "more_records_available_through_state_query": len(records)>12,
            "native_settings": native.metadata["settings"], "resource_binding": native.metadata["configuration"],
            "native_limitations": native.metadata["native_limitations"],
            "native_roles": native.metadata["native_roles"], "raw_artifacts": artifacts,
            "searched_scope": {"subject_ref": args["subject_ref"], "start": 0, "end": native.metadata["target_length"],
                "unit": self.store.subject_unit(args["subject_ref"])},
            "result_meaning": native.metadata["no_hit_meaning"], "target_annotation": "not_performed"}, refs

    def _derive(self, name: str, args: dict, scope: dict | None, native: SequenceWork | None = None) -> tuple[dict, list[str]]:
        batch = self._begin_publication_batch()
        subject = self.store.get(args["subject_ref"])
        model = args["molecule"] if name == "sequence.view" else "dna"
        sequence = self._sequence(subject["id"], molecule_model=model)
        parent_mapping = self.store.sequence_mapping(subject["id"])
        if name == "sequence.view":
            selected = args.get("segments", [{"start": 0, "end": len(sequence)}])
            footprint = self.store.map_segments(subject["id"], selected)
            self._check_sequence_operand(subject["id"], scope, footprint=footprint)
            try:
                body = view_sequence(sequence, **{key: value for key, value in args.items() if key != "subject_ref"})
            except ValueError as error:
                raise ContractError(str(error)) from error
            selected = body["input_segments"]
            candidates = [{"segments": selected, "strand": "-" if body["orientation"] == "reverse_complement" else "+",
                           "sequence": body["sequence"]}]
            software_version = VIEW_VERSION
        else:
            start, end = args.get("start", 0), args.get("end", len(sequence))
            if not 0 <= start < end <= len(sequence):
                raise ContractError("requested_interval_outside_subject")
            footprint = self.store.map_segments(subject["id"], [{"start": start, "end": end}])
            self._check_sequence_operand(subject["id"], scope, footprint=footprint)
            if parent_mapping["units_per_symbol"] != 1:
                raise ContractError("translation_requires_nucleotide_symbol_mapping")
            if name == "sequence.translate":
                body = translate(sequence, **{key: value for key, value in args.items() if key != "subject_ref"})
                candidates = [{"start": body["translated_interval"][0], "end": body["translated_interval"][1],
                    "strand": body["strand"], "protein_sequence": body["sequence"]}]
            else:
                if native is None:
                    raise ContractError("native_sequence_worker_result_required")
                body = json.loads(native.output_path.read_text(encoding="utf-8"))
                body["local_job"] = native.metadata
                for candidate in body["candidates"]:
                    candidate["start"] += start
                    candidate["end"] += start
                body["input_interval"] = [start, end]
                candidates = body["candidates"]
            body["omitted_terminal_stop"] = bool(name == "sequence.translate" and body["cds"])
            software_version = version("biopython" if name == "sequence.translate" else "pyrodigal")
        body["mapping_version"] = MAPPING_VERSION
        body["subject_ref"] = subject["id"]
        source = self._source(name, body, software_version=software_version)
        self._batch_observations(batch, source["id"])
        condition = self._put("context", {"context_type": "processing",
            "name": "sequence_view_model" if name == "sequence.view" else "translation_model",
            "source_ref": source["id"], "attributes": measurements(molecule_model=enum(model)) if name == "sequence.view"
                else measurements(genetic_code=number(args["code"])), "related_refs": [subject["id"]]}, origin="tool")
        refs, results = [source["id"], condition["id"]], []
        for candidate in candidates:
            segments = candidate["segments"] if name == "sequence.view" else [{"start": candidate["start"], "end": candidate["end"]}]
            output = candidate["sequence"] if name == "sequence.view" else candidate["protein_sequence"]
            try:
                if name == "sequence.view":
                    scale = parent_mapping["units_per_symbol"]
                    mapping = {"version": MAPPING_VERSION, "units_per_symbol": scale, "symbol_length": len(output),
                        "path": extract_path(parent_mapping["path"],
                            [{"start": row["start"] * scale, "end": row["end"] * scale} for row in segments],
                            strand=candidate["strand"])}
                else:
                    mapping = translation_mapping(parent_mapping["path"], start=candidate["start"], end=candidate["end"],
                        strand=candidate["strand"], protein_length=len(output), omitted_terminal_stop=body["omitted_terminal_stop"])
            except ValueError as error:
                raise ContractError(str(error)) from error
            feature = self._put("feature", {"subject_ref": subject["id"], "kind": "CDS" if name == "genes.predict" else "sequence_region",
                "segments": segments, "strand": candidate["strand"], "context_refs": [condition["id"]]}, origin="tool", scope=scope)
            product = self._put("product", {"parent_refs": [feature["id"]],
                "molecule": args["molecule"] if name == "sequence.view" else "protein",
                "sequence_ref": self.store.artifact(output, "text/plain"),
                "derivation": "extraction" if name == "sequence.view" else "translation", "context_refs": [condition["id"]],
                "footprint": self.store.footprint_from_mapping(mapping),
                "mapping": mapping, "mapping_source_ref": source["id"]}, origin="tool", scope=scope)
            values = measurements(length=number(len(output)), molecule_model=enum(model)) if name == "sequence.view" else measurements(
                genetic_code=number(args["code"]), start=number(candidate["start"]), end=number(candidate["end"]))
            if name == "genes.predict":
                values += measurements(native_confidence=number(candidate["native_confidence"]), model_score=number(candidate["native_score"]))
            observation = self._observation("gene_prediction" if name == "genes.predict" else "coordinate_mapping",
                [feature["id"], product["id"]], source, values, dependencies=[subject["id"], condition["id"]])
            refs += [feature["id"], product["id"], observation["id"]]
            results.append({"feature_ref": feature["id"], "product_ref": product["id"], "observation_ref": observation["id"]})
            batch["published_rows_total"] += 1
        return {"count": len(results), "records": results[:12], "preview_limit": 12,
                "more_records_available_through_state_query": len(results) > 12,
                "source_ref": source["id"], "limitations": body.get("limitations", [])}, refs

    def _import(self, name: str, args: dict, snapshot: SourceSnapshot) -> tuple[dict, list[str]]:
        if name in {"public.blast.search", "public.blast.collect"}:
            return self._import_blast(snapshot)
        if name in {"public.rfam.search", "public.rfam.collect"}:
            return self._import_rfam_discovery(snapshot)
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
        if name in {"public.rhea.search", "public.rhea.reaction", "public.chebi.search", "public.chebi.compound"}:
            return self._import_chemistry(name, args, snapshot, source)
        if name.startswith("public.uniprot."):
            records = []
            for protein in parse_uniprot(snapshot.content):
                terms = []
                if protein["taxon_id"] is not None:
                    term = self._put("term", {"namespace": "ncbi_taxonomy", "accession": str(protein["taxon_id"]),
                        "label": protein["organism"] or str(protein["taxon_id"]), "term_type": "taxon", "source_ref": source["id"], "anchor": None}, origin="external")
                    terms.append(term["id"])
                if protein["source_name"]:
                    term = self._put("term", {"namespace": "uniprot_source_name", "accession": protein["accession"],
                        "label": protein["source_name"], "term_type": "molecular_role", "source_ref": source["id"], "anchor": None}, origin="external")
                    terms.append(term["id"])
                for ec in protein["source_ec_numbers"]:
                    term = self._put("term", {"namespace": "EC", "accession": ec, "label": "EC " + ec,
                        "term_type": "molecular_role", "source_ref": source["id"], "anchor": None}, origin="external")
                    terms.append(term["id"])
                sequence = protein["sequence"]
                record = self._put("reference", {"reference_type": "protein", "source_ref": source["id"],
                    "accession": protein["accession"], "label": protein["source_name"] or protein["accession"],
                    "sequence_ref": self.store.artifact(sequence, "text/plain") if sequence else None,
                    "molecule": "protein", "length": len(sequence) if sequence else None, "term_refs": terms, "context_refs": []}, origin="external")
                refs += terms + [record["id"]]
                records.append(record)
            return {"source_ref": source["id"], "records": records, "count": len(records),
                    "source_detail_available_through_source_read": True,
                    **(uniprot_pagination(snapshot) if name.endswith("search") else {})}, refs
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
                    "text_bytes": len(text.encode()), "text_representation": "ordered_paragraph_projection",
                    "omitted_elements_available_in_original": True,
                    "original_read_query": {"source_ref": source["id"], "representation": "original"},
                    "read_with": "source.read"}, refs
        if name in {"public.hmmer.search", "public.hmmer.collect", "public.hmmer.page"}:
            body = parse_hmmer(snapshot.content, algorithm=snapshot.request["algorithm"])
            return self._import_hmmer_body(snapshot, source, body, refs)
        # Search/status outputs retain provider structure and source provenance;
        # no target assertion is manufactured by these acquisitions.
        try:
            native = json.loads(snapshot.content)
        except ValueError:
            native = None
        return {"source_ref": source["id"], "provider_result": native,
                "raw_artifact_ref": source["artifact_ref"]}, refs

    def publish_hmmer_snapshot(self, snapshot: SourceSnapshot, *, scope: dict) -> dict:
        """Publish retained API bytes with the ordinary HMMER importer, no HTTP.

        Each independent native hit is projected separately; a bad later hit
        retains earlier actual records and exact source-relative row locators.
        """
        token = self._publications.set([])
        batch_token = self._publication_batch.set(None)
        try:
            self.store.validate_scope(scope)
            self._check_sequence_operand(snapshot.request["subject_ref"], scope)
            with self.store.transaction():
                source = self._source(snapshot.service, None, snapshot=snapshot)
                native = json.loads(snapshot.content)
                if native.get("status") != "SUCCESS" or not isinstance(native.get("result", {}).get("hits"), list):
                    raise ContractError("provider_result_response_invalid")
                rows, failures = [], []
                for ordinal, hit in enumerate(native["result"]["hits"]):
                    before = len(self._written)
                    try:
                        selected = {**native, "result": {**native["result"], "hits": [hit]}}
                        body = parse_hmmer(json.dumps(selected).encode(), algorithm=snapshot.request["algorithm"])
                        result, _ = self._import_hmmer_body(snapshot, source, body, [source["id"]])
                        record = result["records"][0]
                        rows.append(dict(hit_ordinal=ordinal, domain_ordinal=None,
                                         record_ref=record["reference_ref"], record_type="reference"))
                        domains = hit.get("domains", [])
                        rows.extend(dict(hit_ordinal=ordinal, domain_ordinal=index if domains else None,
                                         record_ref=reference, record_type="observation")
                                    for index, reference in enumerate(record["domain_observation_refs"]))
                    except (ContractError, ValueError, KeyError, TypeError, IndexError) as error:
                        code = str(error) if isinstance(error, ContractError) else "invalid_native_hit"
                        failures.append(dict(hit_ordinal=ordinal, domain_ordinal=None, code=code))
                        # Actual records already committed by the ordinary helper
                        # remain useful even if a later domain could not publish.
                        reference = None
                        domain = 0
                        for record_ref in self._written[before:]:
                            record = self.store.get(record_ref)
                            if record["record_type"] == "reference":
                                reference = record_ref
                                rows.append(dict(hit_ordinal=ordinal, domain_ordinal=None,
                                                 record_ref=record_ref, record_type="reference"))
                            elif record["record_type"] == "observation" and reference is not None:
                                rows.append(dict(hit_ordinal=ordinal, domain_ordinal=domain if hit.get("domains") else None,
                                                 record_ref=record_ref, record_type="observation"))
                                domain += 1
                page_count = native.get("page_count")
                if page_count is not None and (type(page_count) is not int or page_count < 0):
                    failures.append(dict(hit_ordinal=None, domain_ordinal=None, code="invalid_native_page_count"))
                    page_count = None
                return dict(source_ref=source["id"], publication_rows=rows,
                            projection_failures=failures, page_count=page_count,
                            record_refs=list(dict.fromkeys(self._written)))
        finally:
            self._publications.reset(token)
            self._publication_batch.reset(batch_token)

    def _import_hmmer_body(self, snapshot, source, body, refs):
        subject_ref = snapshot.request["subject_ref"]
        query_model = self._put("context", {"context_type": "processing", "name": "protein_search_model",
            "source_ref": source["id"], "attributes": measurements(molecule_model=enum("protein")),
            "related_refs": [subject_ref]}, origin="tool")
        refs.append(query_model["id"])
        records = []
        for hit in body["hits"]:
            terms = []
            if hit["taxon_id"] is not None:
                taxon = self._put("term", {"namespace": "ncbi_taxonomy", "accession": str(hit["taxon_id"]),
                    "label": hit["source_organism"] or str(hit["taxon_id"]), "term_type": "taxon",
                    "source_ref": source["id"], "anchor": None}, origin="external")
                terms.append(taxon["id"])
            is_profile = snapshot.request["algorithm"] == "hmmscan"
            accession = hit["accession"] or identity("source_local_hit", {"source": source["id"], "index": hit["native_index"]})
            label = hit["source_label"] or accession
            reference = self._put("reference", {"reference_type": "family" if is_profile else "protein",
                "source_ref": source["id"], "accession": accession,
                "label": label if len(label) <= 512 and "\n" not in label else accession,
                "sequence_ref": None, "molecule": None if is_profile else "protein",
                "length": next((domain.get("reference_length") for domain in hit["domains"]
                                if domain.get("reference_length") is not None), None) if not is_profile else None,
                "term_refs": terms, "context_refs": []}, origin="external")
            refs += terms + [reference["id"]]
            observations = []
            for domain in hit["domains"] or [{}]:
                operand_intervals = None
                values = measurements(reference_ref=ref(reference["id"]))
                if is_profile:
                    values += measurements(profile_ref=ref(reference["id"]))
                for key, value in {"bitscore": domain.get("bitscore", hit["bitscore"]),
                                   "evalue": domain.get("independent_evalue", hit["evalue"]),
                                   "query_coverage": domain.get("query_coverage"),
                                   "target_coverage": domain.get("reference_coverage"),
                                   "identity_fraction": domain.get("identity_fraction")}.items():
                    if value is not None:
                        values += measurements(**{key: number(value)})
                if "query_interval" in domain:
                    if domain["query_length"] != len(self._sequence(subject_ref)):
                        raise ContractError("provider_query_length_differs_from_submitted_subject")
                    values += measurements(query_start=number(domain["query_interval"][0]),
                                           query_end=number(domain["query_interval"][1]))
                    operand_intervals = [{"role": "query", "subject_ref": subject_ref,
                        "start": domain["query_interval"][0], "end": domain["query_interval"][1],
                        "unit": self.store.subject_unit(subject_ref), "model_unit": "aa"}]
                observation = self._observation("profile_match" if is_profile else "comparison",
                    [subject_ref], source, values, references=[reference["id"]],
                    dependencies=[subject_ref, reference["id"], query_model["id"]], operand_intervals=operand_intervals)
                refs.append(observation["id"])
                observations.append(observation["id"])
            records.append({"reference_ref": reference["id"], "native_index": hit["native_index"],
                "accession": hit["accession"], "source_label": hit["source_label"],
                "taxon_id": hit["taxon_id"], "bitscore": hit["bitscore"], "evalue": hit["evalue"],
                "domain_observation_refs": observations})
        return {"source_ref": source["id"], "job_ref": snapshot.transport["job_ref"],
            "job_id": snapshot.request["job_id"], "status": body["status"], "records": records,
            "page": snapshot.request["page"], "page_count": body["page_count"],
            "next_page": snapshot.request["page"]+1 if body["page_count"] and snapshot.request["page"] < body["page_count"] else None,
            "database": (snapshot.transport.get("job_details") or {}).get("database"),
            "native_search_stats": body["stats"], "functional_or_lineage_assignment": "not_performed"}, refs

    def _chemistry_reference(self, kind: str, accession: str, source: dict,
                             *, native_record_ref: str | None = None) -> dict:
        record = {"reference_type": kind, "source_ref": source["id"], "accession": accession,
            "label": accession, "sequence_ref": None, "molecule": None, "length": None,
            "term_refs": [], "context_refs": []}
        if native_record_ref is not None:
            record["native_record_ref"] = native_record_ref
        return self._put("reference", record, origin="external")

    def _import_chemistry(self, name: str, args: dict, snapshot: SourceSnapshot,
                          source: dict) -> tuple[dict, list[str]]:
        is_rhea = name.startswith("public.rhea.")
        search = name.endswith("search")
        body = rhea_response(snapshot.content) if is_rhea else chebi_response(snapshot.content, search=search)
        rows = body["results"] if is_rhea or search else [body]
        references, errors, refs = [], [], [source["id"]]
        for index, native in enumerate(rows):
            before = len(self._written)
            try:
                if is_rhea:
                    details = rhea_row(native)
                    participants = []
                    for participant in details["participants"]:
                        # This is the actual Rhea participant identity, not a
                        # silently fetched ChEBI record or a substrate verdict.
                        chemical = self._chemistry_reference("chemical", participant["source_accession"], source)
                        participants.append({**participant, "chemical_ref": chemical["id"]})
                    details["participants"] = participants
                    details = self._put("reaction_record", {**details, "source_ref": source["id"]}, origin="external")
                    reference = self._chemistry_reference("reaction", details["accession"], source,
                                                          native_record_ref=details["id"])
                    preview = {"source_equation_preview": details["source_equation"][:240],
                        "equation_preview_complete": len(details["source_equation"]) <= 240,
                        "source_direction": details["source_direction"], "participant_count": len(participants)}
                else:
                    details = self._put("chemical_record", {**chemical_row(native, search=search),
                        "source_ref": source["id"]}, origin="external")
                    reference = self._chemistry_reference("chemical", details["accession"], source,
                                                          native_record_ref=details["id"])
                    preview = {"source_name_preview": details["source_name"][:160],
                        "name_preview_complete": len(details["source_name"]) <= 160,
                        "representation": details["representation"], "formula": details["formula"],
                        "charge": details["charge"], "ontology_relation_count": len(details["ontology_relations"])}
                references.append({"reference_ref": reference["id"], "native_record_ref": details["id"],
                                   "accession": details["accession"], **preview})
            except (ContractError, ValueError, KeyError, TypeError) as error:
                errors.append({"row_index": index, "code": str(error) if isinstance(error, ContractError)
                    else "missing_native_field" if isinstance(error, KeyError) else "invalid_native_row",
                    **({"missing_field": str(error.args[0])} if isinstance(error, KeyError) else {}),
                    **({"detail": error.detail} if isinstance(error, ContractError) and error.detail else {})})
            refs.extend(self._written[before:])
        result = {"source_ref": source["id"], "records": references[:6], "preview_limit": 6,
            "projected_record_count": len(references), "provider_returned_row_count": len(rows),
            "more_records_available_through_state_query": len(references) > 6,
            "details_query": {"kind": "reaction_record" if is_rhea else "chemical_record",
                              "references": [source["id"]], "limit": 6},
            "complete_source_read_query": {"source_ref": source["id"], "representation": "original"},
            "projection_errors": errors, "target_annotation": "not_performed",
            "thermodynamics_or_physiological_flux": "not_inferred"}
        if is_rhea:
            result.update(native_count=body.get("count"),
                result_scope="provider_limited_json_search_not_exhaustive_absence",
                direction_scope="json_search_master_records_directional_variants_not_resolved")
        elif search:
            page = args.get("page", 1)
            pages = body.get("number_pages")
            result.update(native_total=body.get("total"), native_page_count=pages, page=page,
                next_query={"term": args["term"], "size": args.get("size", 10), "page": page+1}
                    if type(pages) is int and page < pages else None)
        if not search:
            database = "RHEA" if is_rhea else "CHEBI"
            requested = chemical_accession(args["accession"], database)
            result.update(requested_accession=requested,
                returned_accessions=[row["accession"] for row in references],
                exact_accession_match=any(row["accession"] == requested for row in references),
                lookup_outcome=("returned_source_records" if references else
                                "source_records_not_projected" if rows else "no_search_match"))
        return result, list(dict.fromkeys(refs))
