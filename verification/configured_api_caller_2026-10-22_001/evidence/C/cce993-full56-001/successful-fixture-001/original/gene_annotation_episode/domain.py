"""Closed semantic records shared by scientific tools and reasoning commits."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
import hashlib
import json
import math
import re
from typing import Any

import jsonschema


class ContractError(ValueError):
    def __init__(self, code: str, *, detail: dict | None = None):
        self.detail = {} if detail is None else detail
        super().__init__(code)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def identity(kind: str, value: Any) -> str:
    return kind + "_" + hashlib.sha256(canonical(value).encode()).hexdigest()[:24]


def obj(properties: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": properties,
            "required": list(properties) if required is None else required, "additionalProperties": False}


REF = {"type": "string", "pattern": r"^(?:[a-z][a-z_]*_[a-f0-9]{24,64}|@[A-Za-z][A-Za-z0-9_]*)$",
       "description": "An existing persistent record ID. In a reasoning commit only, @name refers to an earlier successfully processed row declared with alias name in this same commit. Ordinary tool calls require existing persistent IDs."}
REFS = {"type": "array", "items": REF, "uniqueItems": True}
ALIAS = {"type": "string", "pattern": r"^[A-Za-z][A-Za-z0-9_]*$",
         "description": "Bare local definition name, for example role (not @role). Reference this successful row in the same commit as @role; use its returned persistent ID in later commits."}
NULL_REF = {"anyOf": [REF, {"type": "null"}]}
LABEL = {"type": "string", "minLength": 1, "maxLength": 512, "pattern": r"^[^\n\r]+$"}
IDENTIFIER = {"type": "string", "minLength": 1, "maxLength": 200, "pattern": r"^[A-Za-z0-9][A-Za-z0-9_.:/+%#?=;&@~-]*$"}
PUBLICATION_ID_PATTERNS = {'pmcid': r'^PMC[1-9][0-9]*$',
    'pmid': r'^[1-9][0-9]*$', 'doi': r'^10\.[0-9]{4,9}/[^\s]+$'}
PUBLICATION_IDENTIFIER = {'anyOf': [obj({'namespace': {'const': namespace},
    'value': {'type': 'string', 'pattern': pattern, 'maxLength': 512}})
    for namespace, pattern in PUBLICATION_ID_PATTERNS.items()]}
MOLECULES = ["dna", "rna", "protein", "unspecified"]
ROLES = ["unspecified", "read", "gene", "assembly", "transcript", "protein", "metagenomic_bin"]
PREDICATES = ["taxon", "molecule_type", "genetic_code", "biological_role", "functional_family", "catalyzes", "transports",
              "binds", "located_in", "participates_in", "requires", "uses", "produces", "sequence_integrity",
              "feature_structure", "sample_membership", "element_membership", "partner_dependence",
              "growth_capability", "regulates"]
ENUM_VALUES = ["unknown", "unresolved", "intact", "partial", "disrupted", "frameshift", "sequencing_error",
               "assembly_error", "gene_model_error", "recoding", "functional_split", "fusion", "contamination",
               "horizontal_transfer", "mobile_element", "mixture", "coding", "noncoding", "dna", "rna",
               "protein", "bacteria", "archaea", "eukaryota", "virus", "genomic", "transcript",
               "experimental_construct", "not_applicable", "present", "absent", "observed", "not_measured",
               "growth", "no_growth", "weak_growth", "positive", "negative", "ambiguous", "+", "-", ".",
               "CDS", "tRNA", "rRNA", "ncRNA", "regulatory_element", "repeat", "protein_domain", "protein_site"]
RELATION_ROLES = ["substrate", "product", "cofactor", "metal", "location", "partner", "member", "feature",
                  "source", "target", "condition", "taxon", "reactant", "donor", "acceptor", "carbon_source",
                  "energy_source", "electron_donor", "electron_acceptor", "nitrogen_source", "control", "sample"]
ATOM = {"anyOf": [
    obj({"type": {"const": "number"}, "value": {"type": "number"}, "unit_ref": NULL_REF,
        "bound": {"enum": ["less_than", "less_or_equal", "greater_than", "greater_or_equal"],
            "description": "An explicit source-reported bound (<, <=, > or >=) on value, in unit_ref. Preserve the threshold rather than replacing a censored value with zero or an exact measurement. Omission adds no precision claim. A bounded threshold is not an exact coordinate, coverage, extent or arithmetic operand."},
        "qualifier": {"const": "approximate", "description": "An explicit source approximation such as ~. Omission adds no precision claim and does not mean scientifically exact."},
        "uncertainty": {**obj({"representation": {"const": "plus_minus"},
            "magnitude": {"type": "number", "minimum": 0},
            "statistic": {"const": "unspecified"}}),
            "description": "A source-reported plus/minus magnitude in this number's enclosing unit. The statistic is unspecified: do not infer SD, SE, CI, a probability distribution or interval endpoints. Omit when no uncertainty is reported."}},
        required=["type", "value", "unit_ref"]),
    obj({"type": {"const": "enum"}, "value": {"enum": ENUM_VALUES}}),
    obj({"type": {"const": "term_ref"}, "ref": REF}),
    obj({"type": {"const": "reference"}, "ref": REF}),
    obj({"type": {"const": "relation"}, "roles": {"type": "array", "minItems": 1,
        "items": obj({"role": {"enum": RELATION_ROLES}, "ref": REF})}}),
]}
ATOM["description"] = "Typed biological/scientific values. Entity references can name actual subjects or biological entities; custody sources, artifacts and read_selection dataset handles are not biological values. Actual dataset selection handles can still be requested as typed parent-form references."
METRIC_NAMES = ["length", "gc_fraction", "ambiguous_fraction", "identity_fraction", "query_coverage",
    "target_coverage", "alignment_score", "bitscore", "evalue", "model_score", "count", "start", "end",
    "strand", "genetic_code", "feature_kind", "reference_ref", "profile_ref", "source_taxon", "annotation_ref",
    "missing_data", "boundary_state", "match_state", "activity", "growth_rate", "observed_growth", "temperature",
    "ph", "salinity", "time", "replicate", "control_ref", "relation_ref", "substrate_ref", "product_ref",
    "cofactor_ref", "location_ref", "sample_ref", "condition_ref", "biomass", "dna_concentration", "coverage",
    "quality_score", "reading_frame", "stop_count", "intron_count", "native_confidence", "assay_outcome",
    "extraction_batch", "environment_ref", "medium_ref", "oxygen_relationship", "source_reference", "query_start", "query_end", "molecule_model",
    "concentration", "dissociation_constant"]
MEASUREMENTS = {"type": "array", "items": obj({"name": {"enum": METRIC_NAMES}, "value": ATOM})}
ANCHOR = obj({"source_ref": REF, "artifact_ref": REF, "start": {"type": "integer", "minimum": 0},
              "end": {"type": "integer", "minimum": 1}, "quote": {"type": "string", "minLength": 1, "maxLength": 16000}})
ANCHOR['description'] = (
    'An exact half-open UTF-8 byte interval of this retained artifact. '
    'quote.encode("utf-8") must equal artifact_bytes[start:end], including punctuation. '
    'A source.read window already supplies start, end and text: use that complete '
    'text as quote with those unchanged offsets, or select a smaller read window. '
    'Character indices and a cropped quote do not determine new byte offsets.')
SEGMENTS = {"type": "array", "minItems": 1,
            "items": obj({"start": {"type": "integer", "minimum": 0}, "end": {"type": "integer", "minimum": 1}})}
FEATURE_KINDS = ["CDS", "gene", "tRNA", "rRNA", "ncRNA", "regulatory_element", "repeat", "mobile_element",
                 "protein_domain", "protein_site", "sequence_region"]
OBSERVATION_KINDS = ["sequence_composition", "gene_prediction", "alignment", "profile_match", "structure_match",
    "taxonomy_assignment", "source_annotation", "source_content", "assay_report", "biochemical_assay",
    "genetic_phenotype", "growth_assay", "context_measurement", "read_support", "coordinate_mapping",
    "reaction_context", "mechanism", "comparison", "context"]
VISUAL_ANCHOR = obj({"view_ref": REF, "image_artifact_ref": REF,
    "region": obj({"x": {"type": "integer", "minimum": 0},
        "y": {"type": "integer", "minimum": 0},
        "width": {"type": "integer", "minimum": 1},
        "height": {"type": "integer", "minimum": 1}})})
VISUAL_ANCHOR["description"] = "A reasoned reading of a registered native image view, not a literal text quotation or a performed assay. Region uses rendered PNG pixels from the top-left: half-open [x,x+width) by [y,y+height)."
FOOTPRINT = {"type": "array", "items": obj({"target_ref": REF, "member_ref": REF,
              "start": {"type": "integer", "minimum": 0},
              "end": {"type": "integer", "minimum": 1}, "unit": {"enum": ["nt", "aa", "symbol"]}},
              required=["target_ref", "start", "end", "unit"])}
FOOTPRINT["description"] = "Original scalar input intervals or disjoint original-read intervals. A library span additionally requires member_ref for its exact fixed original member. Library mass is never a linear sequence coordinate."
CONTEXT_MASK = obj({"subject_refs": {"type": "array", "items": REF},
    "read_selection_refs": {"type": "array", "items": REF},
    "segments": {**FOOTPRINT, "minItems": 1}}, required=["subject_refs"])
CONTEXT_MASK["description"] = "Fixed original material position set for a nonmolecular context interpretation. Frozen read selections of the same library union; segments restrict actual selected members. This is not a sequence mapping. {subject_refs: []} explicitly withdraws allocation; Episode scopes remain nonempty."
SEQUENCE_MAPPING = obj({"version": {"const": "oriented_source_subject_path_v2"},
    "units_per_symbol": {"enum": [1, 3]}, "symbol_length": {"type": "integer", "minimum": 1},
    "path": {"type": "array", "minItems": 1, "items": obj({"subject_ref": REF,
        "start": {"type": "integer", "minimum": 0}, "end": {"type": "integer", "minimum": 1},
        "unit": {"enum": ["nt", "aa", "symbol"]}, "strand": {"enum": ["+", "-"]}})}})
INTERPRETATION = obj({"hypothesis_ref": REF, "disposition": {"enum": ["supported", "weakened", "unresolved"]},
                      "assessment_refs": REFS})
COHERENT_SET = obj({"interpretations": {"type": "array", "items": INTERPRETATION, "minItems": 1}, "context_refs": REFS})

CMSEARCH_MATCH = obj({
    "native_query_model_ref": REF, "native_target_subject_ref": REF,
    "native_target_name": {"type": "string"}, "native_target_accession": {"type": ["string", "null"]},
    "native_query_name": {"type": "string"}, "native_query_accession": {"type": ["string", "null"]},
    "algorithm": {"enum": ["cm", "hmm"]},
    **{key: {"type": "integer", "minimum": 1} for key in
       ("model_from", "model_to", "target_from", "target_to", "pass", "model_length", "target_length")},
    "strand": {"enum": ["+", "-"]}, "truncation": {"enum": ["no", "5'", "3'", "5'&3'", "-"]},
    **{key: {"type": "number"} for key in ("gc_fraction", "bias_bits", "bitscore", "evalue")},
    "inclusion": {"enum": ["!", "?"]}, "description": {"type": "string"},
    "target_interval": {"type": "array", "items": {"type": "integer", "minimum": 0}, "minItems": 2, "maxItems": 2},
    "model_consensus_interval": {"type": "array", "items": {"type": "integer", "minimum": 0}, "minItems": 2, "maxItems": 2},
})

RECORD_SCHEMAS = {
    "source": obj({"provider": IDENTIFIER, "accession": {"anyOf": [IDENTIFIER, {"type": "null"}]},
        "uri": {"anyOf": [{"type": "string", "format": "uri"}, {"type": "null"}]}, "artifact_ref": REF,
        "text_ref": NULL_REF, "request_ref": NULL_REF, "version": {"anyOf": [LABEL, {"type": "null"}]},
        "retrieved_at": {"anyOf": [{"type": "string", "format": "date-time"}, {"type": "null"}]}}),
    "term": obj({"namespace": IDENTIFIER, "accession": IDENTIFIER, "label": LABEL,
        "term_type": {"enum": ["taxon", "chemical", "reaction", "pathway", "family", "domain",
            "homologous_superfamily", "molecular_role", "location", "unit", "other"],
            "description": "Preserve the source's classification category: a protein domain or homologous superfamily is distinct from a family and from a molecular activity. These categories do not establish target membership or function."},
        "source_ref": REF, "anchor": {"anyOf": [ANCHOR, {"type": "null"}]}}),
    "reference": obj({"reference_type": {"enum": ["sequence", "protein", "dna", "rna", "assay", "taxon", "reaction", "pathway", "family", "feature", "literature_result", "construct", "sample", "organism", "complex", "element", "chemical"]},
        "source_ref": REF, "accession": IDENTIFIER, "label": LABEL, "sequence_ref": NULL_REF,
        "molecule": {"enum": MOLECULES + [None]}, "length": {"anyOf": [{"type": "integer", "minimum": 0}, {"type": "null"}]},
        "term_refs": REFS, "context_refs": REFS, "anchor": {"anyOf": [ANCHOR, {"type": "null"}]}},
        required=["reference_type", "source_ref", "accession", "label", "sequence_ref", "molecule", "length", "term_refs", "context_refs"]),
    "context": obj({"context_type": {"enum": ["sample", "environment", "growth_condition", "assay_condition", "processing", "collection", "organism"]},
        "name": LABEL, "source_ref": REF, "attributes": MEASUREMENTS, "related_refs": REFS,
        "anchor": {"anyOf": [ANCHOR, {"type": "null"}]}},
        required=["context_type", "name", "source_ref", "attributes", "related_refs"]),
    "feature": obj({"subject_ref": REF, "kind": {"enum": FEATURE_KINDS}, "segments": SEGMENTS,
                    "strand": {"enum": ["+", "-", "."]}, "context_refs": REFS}),
    "product": obj({"parent_refs": {"type": "array", "items": REF, "minItems": 1}, "molecule": {"enum": MOLECULES},
        "sequence_ref": REF, "derivation": {"enum": ["translation", "splicing", "extraction", "reverse_complement", "correction_hypothesis"]},
        "context_refs": REFS, "footprint": FOOTPRINT,
        "mapping": {"anyOf": [SEQUENCE_MAPPING, {"type": "null"}]}, "mapping_source_ref": NULL_REF},
        required=["parent_refs", "molecule", "sequence_ref", "derivation", "context_refs", "footprint"]),
    "observation": obj({"subject_refs": {"type": "array", "items": REF, "minItems": 1},
        "source_subject_refs": REFS, "kind": {"enum": OBSERVATION_KINDS}, "source_ref": REF,
        "measurements": MEASUREMENTS, "dependencies": REFS,
        "native_blast": obj({"program": {"enum": ["blastn", "blastp", "blastx", "tblastn", "tblastx"]},
            **{key: {"enum": ["nt", "aa"]} for key in ["query_coordinate_unit", "hit_coordinate_unit", "alignment_unit"]},
            **{key: {"type": "integer", "minimum": 0} for key in ["report_ordinal", "hit_ordinal", "hsp_ordinal"]},
            **{key: {"type": "integer", "minimum": 1} for key in ["query_from", "query_to", "hit_from", "hit_to"]},
            **{key: {"enum": ["Plus", "Minus"]} for key in ["query_strand", "hit_strand"]},
            **{key: {"type": "integer"} for key in ["query_frame", "hit_frame"]}},
            required=["program", "report_ordinal", "hit_ordinal", "hsp_ordinal", "query_from", "query_to", "hit_from", "hit_to",
                "query_coordinate_unit", "hit_coordinate_unit", "alignment_unit"]),
        "native_cmsearch": {**CMSEARCH_MATCH, "description": "Deterministic native Infernal fmt3 row. Model consensus positions are not physical reference residue coordinates. Only native adapter publications may supply this field."},
        "native_minimap2": obj({"line_number": {"type": "integer", "minimum": 1},
            "row_start": {"type": "integer", "minimum": 0}, "row_end": {"type": "integer", "minimum": 1},
            "strand": {"enum": ["+", "-"]}, "mapping_quality": {"type": "integer", "minimum": 0, "maximum": 255},
            "native_alignment_type": {"type": ["string", "null"], "maxLength": 1}}),
        "anchor": {"anyOf": [ANCHOR, {"type": "null"}]},
        "visual_anchor": {"anyOf": [VISUAL_ANCHOR, {"type": "null"}],
            "description": "Optional exact displayed-image provenance. A model observation with this anchor has reasoning origin and null text anchor; source_ref must be the native view source. Omitted/null retains ordinary literal-text extraction."},
        "operand_intervals": {"anyOf": [{"type": "array",
            "items": obj({"role": {"enum": ["query", "reference"]}, "subject_ref": REF,
                "start": {"type": "integer", "minimum": 0}, "end": {"type": "integer", "minimum": 1},
                "unit": {"enum": ["nt", "aa", "symbol"]}, "model_unit": {"enum": ["nt", "aa", "symbol"]}},
                required=["role", "subject_ref", "start", "end", "unit"])}, {"type": "null"}]}},
        required=["subject_refs", "source_subject_refs", "kind", "source_ref", "measurements", "dependencies", "anchor"]),
    "hypothesis": obj({"subject_refs": {"type": "array", "items": REF, "minItems": 1},
        "predicate": {"enum": PREDICATES}, "value": ATOM, "context_refs": REFS}),
    "assessment": obj({"hypothesis_ref": REF, "observation_ref": REF,
        "relation": {"enum": ["strengthens", "weakens", "mixed", "does_not_discriminate"]},
        "applicability": {"enum": ["direct", "transfer", "contextual", "scope_limited", "incomparable"]},
        "extent_basis": {"enum": ["observed_extent", "inferred_extent", "context_allocation"],
            "description": "Observed extent projects only actual measured input/source extent; target_footprint can restrict it. Inferred extent is non-direct reasoned attribution to explicit target_footprint, independent of source coordinates; it does not create a target measurement. context_allocation preserves a nonmolecular interpretation and its actual source/applicability while allocating it to explicit original material positions; it creates no molecular measurement or sequence mapping."},
        "condition_refs": REFS, "assumption_refs": REFS,
        "context_account_scope": CONTEXT_MASK, "context_scope": {"anyOf": [CONTEXT_MASK, {"type": "null"}]},
        "target_footprint": {"description": "Explicit original-input intervals within hypothesis coverage and assigned scope. With observed_extent this only restricts measured extent. With inferred_extent this defines the reasoned attribution, never a measured residue map. Omission/null is allowed: an inferred assessment remains recorded but has no invented target extent or projected credit; completed commit notices identify the missing field.",
            "anyOf": [{**FOOTPRINT, "minItems": 1}, {"type": "null"}]}},
        required=["hypothesis_ref", "observation_ref", "relation", "applicability", "extent_basis", "condition_refs", "assumption_refs"]),
    "annotation": obj({"subject_ref": REF, "footprint_kind": {"enum": ["localized", "whole_input_context"]},
        "coherent_sets": {"type": "array", "items": COHERENT_SET}, "alternative_refs": REFS,
        "resolution": {"enum": ["selected", "alternatives_retained", "unresolved"]},
        "context_account_scope": CONTEXT_MASK, "context_scope": {"anyOf": [CONTEXT_MASK, {"type": "null"}]}},
        required=["subject_ref", "footprint_kind", "coherent_sets", "alternative_refs", "resolution"]),
}

# A scientific finding is recorded in the existing assessment revision, not in
# a second review/reporting process. It distinguishes the source assertion from
# its use for this target question. No unrestricted prose crosses this boundary.
SOURCE_CLAIM = obj({"subject_refs": {**REFS, "minItems": 1},
    "predicate": {"enum": PREDICATES}, "value": ATOM, "context_refs": REFS})
FINDING_QUALIFICATIONS = ["none", "measurement_does_not_establish_claim",
    "different_source_subject", "conditions_limit_transfer",
    "alternatives_not_discriminated", "prediction_not_measurement",
    "assumption_not_established", "confounding_unresolved"]
FINDING_WITHDRAWAL_REASONS = ["not_withdrawn", "source_misread", "wrong_subject",
    "wrong_condition", "wrong_unit", "unsupported_claim", "duplicate_information",
    "superseded_evidence"]
RECORD_SCHEMAS['assessment']['properties']['investigation_finding'] = {
    **obj({'source_claim': SOURCE_CLAIM,
        'qualification': obj({'kind': {'enum': FINDING_QUALIFICATIONS},
            'context_refs': REFS, 'assumption_refs': REFS}),
        'status': {'enum': ['retained', 'withdrawn']},
        'withdrawal_reason': {'enum': FINDING_WITHDRAWAL_REASONS},
        'same_source_claim_as_ref': NULL_REF,
        'replaces_refs': REFS}),
    'description': 'Optional typed scientific information in this assessment. source_claim names the actual observed/source-reported subject, proposition and conditions, not a transferred target measurement. The assessment hypothesis is the target issue. qualification states an explicit limitation; valid negative/nontransferable findings remain retained. Withdrawn means this finding is no longer relied upon, with a concrete reason. same_source_claim_as_ref can identify an earlier assessment of the same underlying source claim when names/representations differ; that is an explicit episode interpretation, not automatically proven equivalence. replaces_refs names exact earlier assessment findings corrected by this one. Quotes, IDs, account copies and scoring opinions are not new information.'}

# Host/tool provenance records are not model-authored scientific findings.
NATIVE_EXECUTION_OPERATIONS = {'align_pair': 'pairwise_sequence_alignment',
    'xlsx_sheets': 'spreadsheet_selection', 'xlsx_rows': 'spreadsheet_selection',
    'phmmer_search': 'protein_homology_search'}
RECORD_SCHEMAS.update({
    "native_execution": obj({"representation": {"const": "native_execution_receipt_v2"},
        'operation': {'enum': list(NATIVE_EXECUTION_OPERATIONS)},
        "measurement_artifact_ref": REF,
        "operands": {'type': 'array', 'uniqueItems': True, 'items': obj({
            'role': {'enum': ['query', 'reference', 'input_source']}, 'subject_ref': REF})}}),
    "image_view": obj({"representation": {"const": "selected_native_image_frame_v1"},
        "source_ref": REF, "input_source_ref": REF, "original_artifact_ref": REF,
        "image_artifact_ref": REF, "native_format": IDENTIFIER,
        "native_initial_mode": IDENTIFIER, "selected_mode": IDENTIFIER,
        "display_mode": IDENTIFIER,
        "frame": {"type": "integer", "minimum": 0},
        "frame_count": {"type": "integer", "minimum": 1},
        "width": {"type": "integer", "minimum": 1},
        "height": {"type": "integer", "minimum": 1},
        "colour_conversion": {"enum": ["preserve", "rgb"]},
        "software": {"const": "Pillow"}, "software_version": IDENTIFIER,
        "geometric_transform": {"const": "identity"},
        "contrast_transform": {"const": "identity"},
        "orientation": {"const": "stored_pixel_axis_no_exif_rotation"}}),
    "material": obj({"source_ref": REF, "name": LABEL,
        "use": {"enum": ["target", "evidence", "unassigned"]},
        "requested_format": {"type": "string"}, "molecule": {"enum": MOLECULES},
        "role": {"enum": ROLES}, "sample_ref": NULL_REF, "library_ref": NULL_REF,
        "context_source_refs": REFS, "quality_encoding": {"enum": ["unspecified", "phred33", "phred64", "solexa64"]}}),
    "material_link": obj({"source_ref": REF, "left_ref": REF, "right_ref": REF,
        "relation": {"enum": ["paired_with", "same_library", "control_for", "derived_from"]}}),
    "collection": obj({"material_ref": REF, "source_ref": REF, "parse_key": IDENTIFIER,
        "representation": {"enum": ["raw", "fasta", "fastq", "genbank"]}, "parser_version": IDENTIFIER,
        "member_count": {"type": "integer", "minimum": 0}, "sequence_symbols": {"type": "integer", "minimum": 0},
        "complete": {"type": "boolean"}, "molecule": {"enum": MOLECULES}, "role": {"enum": ROLES},
        "sample_ref": NULL_REF, "library_ref": NULL_REF, "context_source_refs": REFS,
        "quality_encoding": {"enum": ["unspecified", "phred33", "phred64", "solexa64"]}}),
    "parse_attempt": obj({"material_ref": REF, "source_ref": REF, "requested_format": {"type": "string"},
        "representation": {"type": "string"}, "compression": {"enum": ["none", "gzip"]},
        "parser_version": IDENTIFIER, "parse_key": IDENTIFIER,
        "status": {"enum": ["completed", "partial", "unavailable", "failed"]},
        "code": IDENTIFIER, "collection_ref": NULL_REF,
        "valid_records": {"type": "integer", "minimum": 0}, "error_count": {"type": "integer", "minimum": 0}}),
})
RECORD_SCHEMAS["source"]["properties"]["parent_source_refs"] = {
    **REFS, "description": "Optional host-recorded forward source lineage. Each reference names an actual immutable source; this does not assign a biological subject or target."}
RECORD_SCHEMAS['source']['properties']['publication_identifiers'] = {
    'type': 'array', 'items': PUBLICATION_IDENTIFIER, 'uniqueItems': True,
    'description': 'Primary article identifiers retained from actual publication metadata, not bibliography citations, source record IDs or scientific findings. Multiple IDs are source assertions, not automatic independent evidence or an equivalence judgment.'}
RECORD_SCHEMAS["parse_attempt"]["properties"]["native_source_ref"] = {
    **REF, "description": "Optional tool-owned native GenBank JSONL assertion projection. Coordinates in that source describe normalized projection bytes, distinct from original GenBank bytes and current scientific annotations."}
RECORD_SCHEMAS["collection"]["properties"]["storage_representation"] = {
    "const": "packed_member_components_v1", "description": "Host physical storage of exact read-member component bytes. This is not a biological sequence target or coordinate system."}
for _native_stream in ("stdout_ref", "stderr_ref"):
    RECORD_SCHEMAS["source"]["properties"][_native_stream] = {
        **REF, "description": "Optional host-recorded exact native output stream artifact. This is provenance, not a biological observation or model-authored text."}
RECORD_SCHEMAS["source"]["properties"]["auxiliary_artifact_refs"] = {
    **REFS, "description": "Optional host-retained native input, diagnostic and metadata artifacts. These preserve operational provenance, never biological subjects or additional targets."}
RECORD_SCHEMAS["source"]["properties"]["operand_refs"] = {
    **REFS, "description": "Optional host-retained actual sequence operand identities. This source lineage grants no target ownership or biological interpretation."}
RECORD_SCHEMAS["source"]["properties"]["query_selection_ref"] = {
    **REF, "description": "Optional exact immutable original-read search selection. A library container named in a search-result custody observation does not mean all its members were searched."}
RECORD_SCHEMAS["reference"]["properties"].update({"member_ref": REF})
RECORD_SCHEMAS["read_selection"] = obj({"library_ref": REF,
    "binding_version": {"const": "fixed_original_read_position_measure_v1"},
    "member_count": {"type": "integer", "minimum": 1},
    "position_mass": {"type": "integer", "minimum": 1},
    "membership_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"}})
RECORD_SCHEMAS["read_selection"]["description"] = "An immutable original-dataset selection handle, usable in explicit scope and typed parent forms; it is not a biological entity or an ATOM biological value."
RECORD_SCHEMAS["reference"]["properties"].update({
    "label_is_preview": {"type": "boolean", "description": "For an indexed native member, true identifies label as a bounded display prefix, never the complete source identifier. member_ref retains the exact native name/title."},
    "label_full_characters": {"type": "integer", "minimum": 0},
    "label_full_utf8_bytes": {"type": "integer", "minimum": 0},
})

# Public database projections are source facts, not model-authored findings or
# assertions that an input enzyme carries out a reaction. Full details are kept
# outside the automatic working-view categories and read by explicit state.query.
_SOURCE_TEXT = {"type": ["string", "null"]}
_SOURCE_MASS = {"type": ["string", "number", "null"]}
RECORD_SCHEMAS.update({
    "reaction_record": obj({"source_ref": REF, "accession": IDENTIFIER,
        "source_equation": {"type": "string"}, "source_arrow": {"enum": ["=", "=>", "<=", "<=>"]},
        "source_direction": {"enum": ["undefined", "left_to_right", "right_to_left", "bidirectional"]},
        "source_status": _SOURCE_TEXT, "source_balanced": {"type": ["boolean", "null"]},
        "source_transport": {"type": ["boolean", "null"]}, "source_comment": _SOURCE_TEXT,
        "participants": {"type": "array", "items": obj({
            "ordinal": {"type": "integer", "minimum": 0}, "side": {"enum": ["left", "right"]},
            "chemical_ref": REF, "source_accession": IDENTIFIER, "source_name": {"type": "string"},
            "coefficient_expression": {"type": "string"}, "source_coefficient_text": {"type": "string"},
            "coefficient_basis": {"enum": ["source_explicit", "implicit_unit_rhea_notation"]},
            "source_location": {"type": "string"}})}}),
    "chemical_record": obj({"source_ref": REF, "accession": IDENTIFIER,
        "source_name": {"type": "string"}, "source_definition": _SOURCE_TEXT,
        "representation": {"enum": ["search_summary", "compound_detail"]},
        "formula": _SOURCE_TEXT, "charge": {"type": ["integer", "null"]},
        "mass": _SOURCE_MASS, "monoisotopic_mass": _SOURCE_MASS,
        "smiles": _SOURCE_TEXT, "inchi": _SOURCE_TEXT, "inchikey": _SOURCE_TEXT,
        "wurcs": _SOURCE_TEXT, "is_r_group": {"type": ["boolean", "null"]},
        "source_structure_id": {"type": ["integer", "null"]},
        "secondary_accessions": {"type": "array", "items": IDENTIFIER},
        "ontology_relations": {"type": "array", "items": obj({
            "orientation": {"enum": ["incoming_relations", "outgoing_relations"]},
            "initial_accession": IDENTIFIER, "initial_name": {"type": "string"},
            "source_relation": {"type": "string"}, "final_accession": IDENTIFIER,
            "final_name": {"type": "string"}})},
        "source_modified_on": _SOURCE_TEXT, "source_stars": {"type": ["integer", "null"]},
        "source_is_released": {"type": ["boolean", "null"]}}),
})
RECORD_SCHEMAS["reference"]["properties"]["native_record_ref"] = REF

# Native custody/catalog identities are not model-authored scientific claims.
RECORD_SCHEMAS.update({
    "pmc_version": obj({"source_ref": REF, "pmcid": {"type": "string", "pattern": "^PMC[0-9]+$"},
        "version": {"type": "integer", "minimum": 1}, "prefix": {"type": "string", "pattern": r"^PMC[0-9]+\.[1-9][0-9]*/$"}}),
    "pmc_catalog": obj({"source_ref": REF, "version_ref": REF, "metadata_source_ref": NULL_REF,
        "listing_complete": {"type": "boolean"}, "next_continuation_token": {"type": ["string", "null"]}}),
    "pmc_object": obj({"source_ref": REF, "version_ref": REF, "object_key": {"type": "string"},
        "size": {"type": "integer", "minimum": 0}, "etag": {"type": ["string", "null"]},
        "last_modified": {"type": ["string", "null"]}}),
    "pmc_asset": obj({"source_ref": REF, "catalog_ref": REF, "version_ref": REF,
        "asset_kind": {"enum": ["xml", "text", "pdf", "media"]}, "metadata_field": {"type": "string"},
        "object_key": {"type": "string"}, "original_uri": {"type": "string", "format": "uri"},
        "https_uri": {"type": "string", "format": "uri"},
        "advertised_md5": {"type": ["string", "null"], "pattern": "^[a-f0-9]{32}$"}}),
    "archive_member": obj({"source_ref": REF, "archive_format": {"enum": ["zip", "tar"]},
        "ordinal": {"type": "integer", "minimum": 0}, "name": {"type": "string"},
        "size": {"type": "integer", "minimum": 0}, "compressed_size": {"type": ["integer", "null"], "minimum": 0},
        "crc32": {"type": ["integer", "null"], "minimum": 0}, "header_offset": {"type": "integer", "minimum": 0},
        "entry_type": {"enum": ["file", "directory", "symlink", "hardlink", "other"]}}),
    "source_derivative": obj({"source_ref": REF, "parent_source_ref": REF,
        "transformation": {"enum": ["archive_member", "pdf_text", "pdf_page"]},
        "selection_ref": NULL_REF, "page": {"type": ["integer", "null"], "minimum": 1},
        "layout": {"enum": ["reading_order", "layout", "raw", None]}, "dpi": {"type": ["number", "null"], "exclusiveMinimum": 0},
        "coordinate_system": {"enum": ["original_member_bytes", "normalized_utf8_bytes", "one_based_physical_pdf_page"]}}),
})

RECORD_SCHEMAS["observation"]["properties"]["native_blast"]["description"] = "Host-native BLAST report locator, original endpoints and coordinate/frame metadata; only the actual native adapter may publish this field."

# These meanings are already enforced by Store's reference checks. Descriptions
# remain visible when the provider removes unsupported regular expressions.
_REFERENCE_MEANINGS = {
    "context_refs": "Only actual context or hypothesis records, not protein/profile references, sources, located features or generic citations.",
    "condition_refs": "Actual context, hypothesis, observation or term records describing the conditions relevant to this assessment.",
    "assumption_refs": "Only hypothesis records representing examined assumptions; observation IDs are not assumptions.",
}


def _describe_reference_fields(schema):
    if isinstance(schema, dict):
        for name, field in schema.get("properties", {}).items():
            if name in _REFERENCE_MEANINGS:
                # Copy before decorating: REFS is shared by other field meanings.
                schema["properties"][name] = {**field, "description": _REFERENCE_MEANINGS[name]}
        for value in schema.values():
            _describe_reference_fields(value)
    elif isinstance(schema, list):
        for value in schema:
            _describe_reference_fields(value)


RECORD_SCHEMAS['interpretation_account'] = json.loads(canonical(RECORD_SCHEMAS['annotation']))
RECORD_SCHEMAS['interpretation_account']['description'] = (
    'A revisable episode-owned coherent interpretation of recorded evidence. '
    'It does not replace the parent annotation. Ownership and assigned scope '
    'are bound by the runtime, never supplied in this scientific record.')

for _schema in RECORD_SCHEMAS.values():
    _describe_reference_fields(_schema)


def aliased(schema: dict, *, revision: bool = False) -> dict:
    properties = {"alias": ALIAS, **schema["properties"]}
    required = ["alias", *schema["required"]]
    if revision:
        properties["expected_revision"] = {"type": "integer", "minimum": 0,
            "description": "The current revision being replaced, not the desired next revision. Use 0 for a new record key. Otherwise use that key's actual current revision; a revision conflict returns current_revision. The host increments the revision after a changed record is committed."}
        required.append("expected_revision")
    return obj(properties, required=required)


REASONING_SCHEMA = obj({
    "structural_proposals": {"type": "array", "items": aliased(RECORD_SCHEMAS["feature"])},
    "terms": {"type": "array", "items": aliased(obj({key:value for key,value in RECORD_SCHEMAS["term"]["properties"].items() if key not in {"namespace", "accession"}}))},
    "source_subjects": {"type": "array", "items": aliased(obj({"reference_type": {"enum": ["protein", "dna", "rna", "assay", "construct", "sample", "organism", "complex", "element", "feature", "chemical"]},
        "source_ref": REF, "label": LABEL, "anchor": ANCHOR}))},
    "contexts": {"type": "array", "description": "Source-anchored sample, environment, growth, assay or processing context. Preserve the actual reported subject and conditions; related_refs does not assign the context to the submitted target. Name must occur literally in the anchor.",
        "items": aliased(obj({**RECORD_SCHEMAS["context"]["properties"], "anchor": ANCHOR}))},
    "observations": {"type": "array", "items": aliased(RECORD_SCHEMAS["observation"])},
    "hypotheses": {"type": "array", "items": aliased(RECORD_SCHEMAS["hypothesis"])},
    "assessments": {"type": "array", "items": aliased(RECORD_SCHEMAS["assessment"], revision=True)},
    "annotation_updates": {"type": "array", "items": aliased(RECORD_SCHEMAS["annotation"], revision=True)},
    "interpretation_accounts": {"type": "array",
        "description": RECORD_SCHEMAS['interpretation_account']['description'],
        "items": aliased(RECORD_SCHEMAS['interpretation_account'], revision=True)},
}, required=["structural_proposals", "terms", "source_subjects", "observations", "hypotheses", "assessments", "annotation_updates"])

REASONING_SCHEMA["properties"]["terms"]["items"]["properties"]["label"] = {
    **LABEL, "description": "Literal label occurring in the anchored quote, e.g. DUF8182. Do not compose DUF8182 (Pfam PF26554) unless that complete text occurs in the quote. Extraction preserves a source assertion, not its biological truth."}
REASONING_SCHEMA["properties"]["source_subjects"]["items"]["properties"]["label"] = {
    **LABEL, "description": "Literal source-subject label occurring in the exact anchored quote; preserve the entity actually reported or assayed."}
REASONING_SCHEMA['properties']['interpretation_accounts']['items']['properties']['expected_revision']['description'] += (
    ' This account lineage belongs to the current episode and assigned scope. '
    'Use 0 for this episode\'s first account even when an inherited account from '
    'another episode has revision 6; use this episode\'s own current revision for later updates.')

# Native output is published by the adapter, never synthesized by the model.
REASONING_SCHEMA["properties"]["observations"]["items"]["properties"].pop("native_cmsearch", None)
REASONING_SCHEMA["properties"]["observations"]["items"]["properties"].pop("native_blast", None)
REASONING_SCHEMA["properties"]["observations"]["items"]["properties"].pop("native_minimap2", None)


@lru_cache(maxsize=64)
def _validator(serialized_schema: str):
    return jsonschema.Draft202012Validator(json.loads(serialized_schema), format_checker=jsonschema.FormatChecker())


def validate_schema(value: Any, schema: dict) -> None:
    try:
        _validator(canonical(schema)).validate(value)
        canonical(value)  # reject NaN/Infinity, including numbers nested in atoms.
    except jsonschema.ValidationError as exc:
        raise ContractError("representation_error", detail={"field_path": list(exc.absolute_path),
            "schema_keyword": exc.validator}) from exc
    except (ValueError, TypeError) as exc:
        raise ContractError("representation_error") from exc


@dataclass(frozen=True)
class SequenceRecord:
    name: str
    sequence: str
    description: str = ""
    occurrence: int = 0
    issues: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


def parse_sequences(data: str | bytes, *, format: str = "raw", molecule: str = "unspecified", name: str = "input") -> list[SequenceRecord]:
    if molecule not in MOLECULES or format not in {"auto", "fasta", "raw"}:
        raise ContractError("unsupported_input_declaration")
    if isinstance(data, bytes):
        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ContractError("input_not_utf8") from exc
    if format == "auto":
        if not data.lstrip().startswith(">"):
            raise ContractError("sequence_representation_unrecognized")
        format = "fasta"
    alphabet = {"dna": set("ACGTRYSWKMBDHVN"), "rna": set("ACGURYSWKMBDHVN"),
                "protein": set("ABCDEFGHIKLMNPQRSTVWXYZJUO*")}.get(molecule)
    records = []
    seen: dict[str, int] = {}

    def append(header: str, sequence: str) -> None:
        fields = header.strip().split(maxsplit=1)
        if not fields:
            raise ContractError("empty_sequence_identifier")
        sequence = "".join(sequence.split()).upper()
        if not sequence:
            raise ContractError("empty_sequence")
        if not sequence.isascii() or any(not char.isprintable() for char in sequence):
            raise ContractError("unrepresentable_sequence_symbol")
        occurrence = seen.get(fields[0], 0)
        seen[fields[0]] = occurrence + 1
        issues = []
        if alphabet is not None and not set(sequence) <= alphabet:
            issues.append("unexpected_symbol_for_declared_molecule")
        if molecule == "protein" and "*" in sequence[:-1]:
            issues.append("internal_protein_stop_symbol")
        if occurrence:
            issues.append("duplicate_source_identifier")
        records.append(SequenceRecord(fields[0], sequence, fields[1] if len(fields) > 1 else "", occurrence, tuple(issues)))

    if format == "raw":
        append(name, data)
    else:
        header, sequence = None, []
        for line in data.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    append(header, "".join(sequence))
                header, sequence = line[1:], []
            elif header is None:
                raise ContractError("sequence_before_fasta_header")
            else:
                sequence.append(line)
        if header is not None:
            append(header, "".join(sequence))
    if not records:
        raise ContractError("empty_input")
    return records


def parse_fasta(data: str | bytes, *, protein: bool = False) -> list[SequenceRecord]:
    return parse_sequences(data, format="fasta", molecule="protein" if protein else "dna")
