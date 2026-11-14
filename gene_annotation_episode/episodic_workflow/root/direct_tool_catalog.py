"""Original substantive ordinary-tool methods: direct_tool_catalog."""
from __future__ import annotations
import json
from pathlib import Path
from gene_annotation_episode.domain import REF
from gene_annotation_episode.domain import REFS
from gene_annotation_episode.domain import RECORD_SCHEMAS
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episodic_workflow.root.library import blast_search as blast
from gene_annotation_episode.material_parsing import FORMATS
from gene_annotation_episode.episodic_workflow.root.library import read_mapping as mapper
from gene_annotation_episode.source_locations import locate_schema
from gene_annotation_episode.document_tools import resource as document_resource
from gene_annotation_episode.spreadsheet_tools import VERSION as XLSX_VERSION
from .library.rna_evidence import search_settings
from .tool_values import INTEGER
from .tool_values import POSITIVE
from .tool_values import TEXT

class DirectToolCatalog:
    def catalog(self, scope: dict | None = None) -> dict[str, dict]:
        from gene_annotation_episode.literature_sequence_discovery import identity_schema, references_schema
        from gene_annotation_episode.source_sequences import scan_schema
        from gene_annotation_episode.episodic_workflow.root.library.itc_tools import ITC_TOOL, itc_tool_contract
        from gene_annotation_episode.episodic_workflow.root.library.liftover_tools import LIFTOVER_TOOL, liftover_tool_contract
        from gene_annotation_episode.episodic_workflow.root.library.circular_dichroism_tools import circular_dichroism_tool_contract
        from gene_annotation_episode.episodic_workflow.root.library.circular_dichroism_contracts import CD_TOOL
        from gene_annotation_episode.episodic_workflow.root.library.arsenic_speciation_tools import TOOL as ARSENIC_SPECIATION_TOOL, arsenic_speciation_tool_contract
        from gene_annotation_episode.episodic_workflow.root.library.reference_edit_outcome_tools import TOOL as REFERENCE_EDIT_TOOL, reference_edit_outcome_tool_contract
        from gene_annotation_episode.episodic_workflow.root.library.protein_disorder_tools import TOOL as PROTEIN_DISORDER_TOOL, protein_disorder_tool_contract
        from gene_annotation_episode.episodic_workflow.root.library.vcf_result_tools import TOOL as VCF_RESULT_TOOL, vcf_result_tool_contract
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_tools import macs2_peak_tool_contract
        from gene_annotation_episode.rcsb_acquisition import RCSB_ENTRY_ARGUMENTS_SCHEMA, RCSB_FILE_ARGUMENTS_SCHEMA
        from gene_annotation_episode.emdb_acquisition import EMDB_ENTRY_ARGUMENTS_SCHEMA
        from gene_annotation_episode.alphafold_acquisition import ALPHAFOLD_PREDICTION_ARGUMENTS_SCHEMA, ALPHAFOLD_FILE_ARGUMENTS_SCHEMA
        from gene_annotation_episode.molecular_provider_acquisition import PROVIDER_ARGUMENTS_SCHEMAS
        from gene_annotation_episode.variant_provider_acquisition import provider_argument_schema as variant_provider_argument_schema
        from gene_annotation_episode.ucsc_acquisition import ARGUMENTS_SCHEMA as UCSC_ARGUMENTS_SCHEMA
        from gene_annotation_episode.ensembl_acquisition import ARGUMENTS_SCHEMA as ENSEMBL_ARGUMENTS_SCHEMA
        from gene_annotation_episode.ncbi_entrez_tools import ncbi_entrez_tool_contract
        from gene_annotation_episode.ncbi_sra_acquisition import sra_file_argument_schema
        from gene_annotation_episode.geo_tools import geo_tool_contract
        from gene_annotation_episode.jaspar_tools import jaspar_tool_contract
        from .library.encode_tools import encode_tool_contract
        from gene_annotation_episode.screen_tools import screen_tool_contract
        from gene_annotation_episode.episodic_workflow.root.library.restriction_mapping_tool_info import TOOL as RESTRICTION_TOOL, restriction_tool_contract
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
            "result.blast.hsp": ("Read a selected alignment-column window of one explicitly received BLAST HSP. Return native symbols, residue/nucleotide intervals, frames and directions, paired/substituted/gap counts and identity/coverage with explicit denominators. Retain the complete numerical sheet; whole-HSP scores retain their original meaning. Host-bound received inputs and original source custody are required. This reads retained results without executing a search or acquiring a reference sequence.",
                obj({"observation_ref": REF, "column_offset": INTEGER,
                     "column_limit": {"type": "integer", "minimum": 1, "maximum": 4096}})),
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
            "sequence.sites": ("Compare selected zero-based reference positions or a half-open window in one retained pairwise alignment or minimap2 placement. Preserve requested order and duplicates while counting each reference position once; distinguish substitutions, query gaps, reference skips, insertions and unavailable correspondence. Return identity/coverage components with explicit denominators, original coordinates and available read quality. Complete rows and the numerical sheet are retained behind the bounded preview. This does not execute another alignment or call variants.",
                obj({"alignment_ref": REF, "positions": {"type": "array", "items": INTEGER, "minItems": 1},
                    "window": obj({"start": INTEGER, "end": POSITIVE})}, ["alignment_ref"])),
            "reference.neighborhood": ("Inspect actual acquired GenBank features around one explicitly selected reference locus or coordinate. Preserve source labels, partial boundaries and unavailable context; infer no orthology or target function. Left/right follow the reference axis.",
                obj({"reference_ref": REF, "selector": obj({"locus_tag": TEXT, "protein_id": TEXT,
                    "coordinate": INTEGER, "coordinate_frame": {"enum": ["record", "original"]}, "feature_kind": TEXT}, []),
                    "left_bp": INTEGER, "right_bp": INTEGER}, ["reference_ref", "selector", "left_bp", "right_bp"])),
            "public.uniprot.search": ("Acquire one public reference page. Source annotations are not target annotations.",
                obj({"query": TEXT, "size": {"type": "integer", "minimum": 1, "maximum": 500}, "cursor": TEXT}, ["query"])),
            "public.uniprot.record": ("Acquire and pin an actual reference protein, its annotation, source features and evidence provenance.", obj({"accession": TEXT})),
            "public.rcsb.entry": ("Acquire one explicitly selected RCSB entry metadata response and return only the selected structural fields. Preserve native missing, null and zero values. Requested and returned entry identifiers remain separate; this call acquires no coordinate file and makes no annotation assertion.",
                json.loads(canonical(RCSB_ENTRY_ARGUMENTS_SCHEMA))),
            "public.rcsb.file": ("Acquire one explicitly selected RCSB coordinate response as a reusable Source and File. The chosen PDB or PDBx/mmCIF processing format is a declaration; use the structure reader to inspect the actual bytes. Native entry identity remains unparsed. Metadata lookup, redirects, format substitution and extra downloads are not performed.",
                json.loads(canonical(RCSB_FILE_ARGUMENTS_SCHEMA))),
            "public.emdb.entry": ("Acquire one explicitly selected EMDB entry metadata response within the supplied byte limit. Preserve the complete native JSON, identities, associations, units, missing values and response qualifications. This operation retrieves metadata; it does not acquire a density map or calculate a structural result.",
                json.loads(canonical(EMDB_ENTRY_ARGUMENTS_SCHEMA))),
            "public.alphafold.prediction": ("Acquire the existing AlphaFold prediction metadata for one literal supplied identifier within the selected byte limit. Preserve every native model record, field, advertised URL and response qualification. Native model identifiers, versions and quality values retain their source meanings; no model or file is selected by this operation.",
                json.loads(canonical(ALPHAFOLD_PREDICTION_ARGUMENTS_SCHEMA))),
            "public.alphafold.file": ("Acquire exactly the coordinate file advertised at the supplied JSON pointer in an explicitly received AlphaFold metadata Source. Select the PDB or PDBx/mmCIF processing format and byte limit. Retain the original advertisement, metadata source, downloaded Source and File identity. Native model identity remains unparsed; no model, version, filename, redirect or format substitution is chosen for you.",
                json.loads(canonical(ALPHAFOLD_FILE_ARGUMENTS_SCHEMA))),
            "public.string.network": ("Acquire one STRING 12.5 functional-network response for the supplied disambiguated STRING IDs, explicit taxon and score threshold. Add no network nodes or identifier-mapping request. Retain native endpoint identities, channel scores and response qualifications within the supplied byte limit; no returned edge is a gene-function annotation, and no returned edge does not establish biological absence.",
                json.loads(canonical(PROVIDER_ARGUMENTS_SCHEMAS['public.string.network']))),
            "public.kegg.reaction": ("Acquire one literal KEGG reaction entry within the supplied byte limit. Retain the original flat-file text, ordered field and continuation lines, equation and native cross-references. Reaction direction in an organism, flux bounds and gene mappings are not inferred.",
                json.loads(canonical(PROVIDER_ARGUMENTS_SCHEMAS['public.kegg.reaction']))),
            "public.reactome.record": ("Acquire one exact Reactome stable-ID ContentService record within the supplied byte limit. Retain all native species, compartments, inputs, outputs, components, references and inference flags when present. Do not traverse references or substitute a species search; absent fields remain absent.",
                json.loads(canonical(PROVIDER_ARGUMENTS_SCHEMAS['public.reactome.record']))),
            "public.quickgo.term": ("Acquire metadata for one literal GO term from QuickGO within the supplied byte limit. Retain the native envelope, term identity, definition, synonyms, relationships and obsolescence information when present. Requested and returned identities remain separate; no replacement term or gene-product annotation query is selected.",
                json.loads(canonical(PROVIDER_ARGUMENTS_SCHEMAS['public.quickgo.term']))),
            "public.ucsc.request": ("Acquire one explicitly selected UCSC assembly, hub, track, schema or DNA-interval response within the supplied byte limit. Preserve native fields, repeated members, exact numeric tokens and separate request, capture and item-limit meanings. Sequence intervals use zero-based half-open coordinates; returned DNA retains its actual orientation and masking case. Extra requests, whole-population coverage and gene-function assignments are not inferred.",
                json.loads(canonical(UCSC_ARGUMENTS_SCHEMA))),
            "public.ensembl.request": ("Acquire one explicitly selected Ensembl 116 BioMart registry, dataset inventory, dataset configuration or gene-homology response. Select literal source and target datasets, supplied gene IDs, advertised attributes and byte limit. Preserve native XML, ordered TSV rows, duplicate mappings, blank targets, native homology types and one-based inclusive gene coordinates. Dependent requests require received discovery Sources; each request is a separate selected action. Native completion, captured bytes and matching-population coverage remain distinct.",
                json.loads(canonical(ENSEMBL_ARGUMENTS_SCHEMA))),
            "public.eva.request": ("Acquire one explicitly selected EVA variant or region response within the supplied byte limit. Return controlled acquisition status and data references, or a finite failure reason. Native alleles, sample/study associations, coordinates and pagination remain in the retained data for later analysis.",
                variant_provider_argument_schema("public.eva.request")),
            "public.gnomad.request": ("Acquire one explicitly selected gnomAD variant, gene-search or gene response with the supplied reference, dataset where applicable, fields and byte limit. Return controlled acquisition status and data references, or a finite failure reason. Retain native counts, frequencies, missing values and population associations for later analysis; select no search match or additional request.",
                variant_provider_argument_schema("public.gnomad.request")),
            "public.ncbi.sra.file": ("Acquire exactly one explicitly selected SRA or FASTQ file advertised in a received experiment-package XML File, within the supplied byte limit. Select its exact native package, run, file and URL occurrence. Return only acquired, source_ref, data_ref and failure_code. The file is retained for later analysis; archive decoding is a separate operation.",
                sra_file_argument_schema()),
            "public.ncbi.search": ("Search one page of a named NCBI collection for selected references, taxa or sample context.",
                obj({"database": {"enum": ["protein", "nuccore", "assembly", "taxonomy", "biosample", "bioproject", "pubmed"]},
                     "term": TEXT, "size": POSITIVE, "offset": INTEGER}, ["database", "term"])),
            "public.ncbi.sequence": ("Acquire an external GenBank/GenPept sequence and its original feature context; optional nucleotide interval uses zero-based half-open coordinates.",
                obj({"accession": TEXT, "database": {"enum": ["protein", "nuccore"]}, "start": INTEGER, "end": POSITIVE}, ["accession", "database"])),
            "public.taxonomy": ("Retrieve a taxon's source lineage record; it does not assign that taxon to the target.", obj({"taxon_id": POSITIVE})),
            "public.literature.search": ("Acquire one literature search page. Read the actual source before extracting biological evidence.",
                obj({"query": TEXT, "size": POSITIVE, "cursor": TEXT}, ["query"])),
            "public.literature.read": ("Acquire an actual open article, an ordered paragraph projection and separate cited-publication metadata. Bibliography identifiers and paragraph links support further source discovery; they do not identify the acquired article or establish a cited experiment's result. Read the retained original XML with source.read representation=original for tables, headings and other omitted elements.", obj({"pmcid": TEXT})),
            "public.rhea.search": ("Search one explicitly limited Rhea JSON response. Returned left/right equation sides and native direction are database reaction facts, not substrates/products in the target organism. JSON search currently returns undefined-direction master records; no exhaustive absence or directional-variant resolution is claimed.",
                obj({"query": {"type": "string"}, "limit": POSITIVE}, ["query"])),
            "public.rhea.reaction": ("Look up a selected Rhea accession through its JSON search interface. Preserve returned identity and direction; a directional accession may yield no search match. No automatic ID/direction substitution. Read native_record_ref with state.query for complete structured details.", obj({"accession": TEXT})),
            "public.chebi.search": ("Search one selected ChEBI text-result page using the service's term parameter. Search summaries retain their source scope and scores/stars are never annotation acceptance rules. Follow next_query for later pages.",
                obj({"term": {"type": "string"}, "size": POSITIVE, "page": POSITIVE}, ["term"])),
            "public.chebi.compound": ("Retrieve a selected ChEBI compound's source chemistry, structure strings and ontology relations. These are chemical/source identities, not an enzyme assay, target substrate assignment or physiological role. Complete structured detail is available through native_record_ref using state.query.", obj({"accession": TEXT})),
            "public.search.jobs": ("Read a page of current remote job ownership/handles, without loading raw HTTP histories.",
                obj({"limit": POSITIVE, "offset": INTEGER, "active_only": {"type": "boolean"}}, [])),
            "public.blast.search": ("Search one actual registered operand with the selected BLAST program/database. Durable submission, same-job protocol wait and native results are one ordinary action. All reported HSPs are evidence; no function or taxon is assigned.",
                obj({"subject_ref": REF, "program": {"enum": list(blast.PROGRAM_UNITS)},
                     "database": TEXT, "hitlist_size": POSITIVE}, ["subject_ref", "program", "database"])),
            "public.blast.collect": ("Resume an existing durable BLAST job without resubmission or changing its subject, program or requested database. Requires that job's original operand to belong to the assigned measurement scope.", obj({"job_ref": REF})),
        }
        result = {name: {"description": description, "input_schema": schema}
                  for name, (description, schema) in definitions.items()}
        from gene_annotation_episode.experimental_database_acquisition import catalog as experimental_database_catalog
        from gene_annotation_episode.experimental_database_records import READER as EXPERIMENT_RECORDS, reader_schema
        result.update(experimental_database_catalog())
        result[EXPERIMENT_RECORDS] = {
            'description': 'Inspect one page of a received experimental database response. Return native assay records, source measurement selectors and literal record links. Optional contains and contains_all filter retained rows by one or several literal terms, including their native headers and section labels. Record and whole-page link continuations are separate. Database measurements require the same assay interpretation and A105 grader as literature measurements; metadata and deposited scores retain their native meanings.',
            'input_schema': reader_schema()}
        result['public.literature.sequence_identity'] = {
            'description': 'Find publication leads from a supplied protein sequence: retrieve one UniProtKB checksum-search page and verify each complete residue string. Return all equal records on the page, names, organisms, citation counts and explicit continuation. The optional reviewed filter selects database curation status. These are source identities and discovery metadata; experimental evidence requires reading the actual publications.',
            'input_schema': identity_schema()}
        result['source.sequence.references'] = {
            'description': 'Read a page of publication identifiers, titles and reported citation scopes from a received sequence-identity response. Reverify full sequence equality for the selected record. Citation metadata supplies leads; it does not establish experimental results.',
            'input_schema': references_schema()}
        result['source.sequence.scan'] = {
            'description': 'Recognize candidate protein sequence blocks in received source text/XML/HTML, preserving original UTF-8 positions. Normalize case, whitespace, numbering and soft hyphens; report exact containment, extra residues and literal differences. For numbered GenBank/GenPept blocks, include the ORIGIN marker and contiguous residue rows in the selected window. Hard hyphens remain explicit, with conditional correspondence, until their byte offsets are selected as formatting_hyphen_offsets after inspecting the layout. A document boundary may require an overlapping window. No biological gaps, tags or substitutions are silently removed.',
            'input_schema': scan_schema()}
        result["public.pubchem.compound"] = {
            "description": "Acquire the PubChem compound JSON for one explicitly selected CID within the supplied byte limit. Return controlled confirmation that the requested data was acquired, with its data reference or failure code.",
            "input_schema": PROVIDER_ARGUMENTS_SCHEMAS["public.pubchem.compound"]}
        result["public.hpa.gene"] = {
            "description": "Acquire the Human Protein Atlas gene JSON for one explicitly selected Ensembl gene identifier within the supplied byte limit. Return controlled confirmation that the requested data was acquired, with its data reference or failure code.",
            "input_schema": PROVIDER_ARGUMENTS_SCHEMAS["public.hpa.gene"]}
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
        result[ITC_TOOL] = {**itc_tool_contract(), "configuration": {
            "job_limits": self.local_job_policy.to_dict(),
            "execution": "isolated_store_free_worker", "algorithm_substitution": False}}
        result[LIFTOVER_TOOL] = {**liftover_tool_contract(), "configuration": {
            "job_limits": self.local_job_policy.to_dict(), "software": "pyliftover",
            "execution": "isolated_store_free_worker", "algorithm_substitution": False,
            "chain_acquisition": False}}
        result[CD_TOOL] = {**circular_dichroism_tool_contract(), "configuration": {
            "job_limits": self.local_job_policy.to_dict(),
            "execution": "isolated_store_free_worker", "algorithm_substitution": False}}
        result[ARSENIC_SPECIATION_TOOL] = {**arsenic_speciation_tool_contract(), "configuration": {
            "job_limits": self.local_job_policy.to_dict(),
            "execution": "isolated_store_free_worker", "algorithm_substitution": False}}
        result[REFERENCE_EDIT_TOOL] = reference_edit_outcome_tool_contract()
        result[RESTRICTION_TOOL] = {**restriction_tool_contract(), "configuration": {
            "job_limits": self.local_job_policy.to_dict(),
            "execution": "isolated_store_free_worker", "algorithm_substitution": False}}
        result[PROTEIN_DISORDER_TOOL] = {**protein_disorder_tool_contract(), "configuration": {
            "job_limits": self.local_job_policy.to_dict(),
            "execution": "isolated_store_free_worker", "algorithm_substitution": False}}
        result[VCF_RESULT_TOOL] = vcf_result_tool_contract()
        result['result.macs2.peaks'] = macs2_peak_tool_contract()
        result["public.ncbi.entrez"] = ncbi_entrez_tool_contract()
        result["public.ncbi.geo"] = geo_tool_contract()
        result["public.jaspar"] = jaspar_tool_contract()
        result["public.encode"] = encode_tool_contract()
        result["public.screen"] = screen_tool_contract()
        if self._homer_configuration is not None:
            from gene_annotation_episode.episodic_workflow.root.library.homer_motif_tools import homer_tool_contract
            entry = homer_tool_contract(self._homer_configuration)
            if entry is not None:
                result['find_enriched_motifs_with_homer'] = entry
        if self._tf_binding_configuration is not None:
            from gene_annotation_episode.episodic_workflow.root.library.tf_binding_tools import tf_binding_tool_arguments_schema
            schema = tf_binding_tool_arguments_schema(self._tf_binding_configuration)
            if schema is not None:
                result['identify_transcription_factor_binding_sites'] = dict(
                    resources='local', invocation_route=dict(kind='direct'),
                    description='Scan supplied DNA against a supplied motif matrix and return candidate-site scores and coordinates.',
                    input_schema=schema,
                    instructions=('Use the supplied DNA and motif-matrix records with explicit record/strand selection, '
                        'background, pseudocounts and raw log2-odds threshold. Retain native window scores for saved-data '
                        'recalculation. Preserve nonfinite and unscorable values, original record identities and '
                        'zero-based half-open forward-sequence coordinates. Return controlled candidate-site scores '
                        'and coordinates with input associations. Candidate sites do not establish measured binding or regulation.'),
                    configuration=dict(job_limits=self.local_job_policy.to_dict(),
                        saved_modes=self._tf_binding_configuration['saved_modes'],
                        execution='isolated_store_free_worker', algorithm_substitution=False))
        if self._protease_kinetics_configuration is not None:
            from gene_annotation_episode.episodic_workflow.root.library.protease_kinetics_tools import protease_kinetics_tool_contract
            entry = protease_kinetics_tool_contract(self._protease_kinetics_configuration)
            if entry is not None:
                result['analyze_protease_kinetics'] = entry
        if self._protein_conservation_configuration is not None:
            from .library.protein_conservation_tools import protein_conservation_tool_contract
            entry = protein_conservation_tool_contract(self._protein_conservation_configuration)
            if entry is not None:
                if 'analyze_protein_conservation' in result:
                    raise ContractError('protein_conservation_operation_owner_conflict')
                result['analyze_protein_conservation'] = entry
        if self._protein_phylogeny_configuration is not None:
            from .library.protein_phylogeny_tools import protein_phylogeny_tool_contract
            entry = protein_phylogeny_tool_contract(self._protein_phylogeny_configuration)
            if entry is not None:
                if 'analyze_protein_phylogeny' in result:
                    raise ContractError('protein_phylogeny_operation_owner_conflict')
                result['analyze_protein_phylogeny'] = entry
        if self._somatic_variant_configuration is not None:
            from gene_annotation_episode.episodic_workflow.root.library.somatic_variant_tools import somatic_variant_tool_contract
            entry = somatic_variant_tool_contract(self._somatic_variant_configuration)
            if entry is not None:
                if 'detect_and_annotate_somatic_mutations' in result:
                    raise ContractError('somatic_variant_operation_owner_conflict')
                result['detect_and_annotate_somatic_mutations'] = entry
        if self._esm_gene_embedding_configuration is not None:
            from gene_annotation_episode.episodic_workflow.root.library.esm_gene_embedding_tools import esm_gene_embedding_tool_contract
            entry = esm_gene_embedding_tool_contract(self._esm_gene_embedding_configuration)
            if entry is not None:
                if 'generate_gene_embeddings_with_ESM_models' in result:
                    raise ContractError('esm_gene_embedding_operation_owner_conflict')
                result['generate_gene_embeddings_with_ESM_models'] = entry
        if self._protein_structure_configuration is not None:
            from .library.protein_structure_tools import protein_structure_tool_catalog
            for name, entry in protein_structure_tool_catalog(self._protein_structure_configuration).items():
                if name in result:
                    raise ContractError('protein_structure_operation_owner_conflict')
                result[name] = entry
        if self._flux_balance_configuration is not None:
            from .library.flux_balance_tools import flux_balance_tool_catalog
            for name, entry in flux_balance_tool_catalog(self._flux_balance_configuration).items():
                if name in result:
                    raise ContractError('flux_balance_operation_owner_conflict')
                result[name] = entry
        if self._molecular_sequence_configuration is not None or self._molecular_sequence_saved_modes is True:
            from .library.molecular_sequence_tools import molecular_sequence_tool_catalog
            for name, entry in molecular_sequence_tool_catalog(self._molecular_sequence_configuration,
                    saved_modes=self._molecular_sequence_saved_modes is True).items():
                if name in result:
                    raise ContractError('molecular_sequence_operation_owner_conflict')
                result[name] = entry
        return result

