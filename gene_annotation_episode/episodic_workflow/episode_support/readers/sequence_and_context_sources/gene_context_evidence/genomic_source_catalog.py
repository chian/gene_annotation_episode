"""A103 private source-neighborhood and genomic acquisition contracts."""
import json
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import REF, canonical, obj
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.sequence_and_context_sources.gene_context_evidence.string_acquisition import PROVIDER_ARGUMENTS_SCHEMAS
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.sequence_and_context_sources.gene_context_evidence.ucsc_acquisition import ARGUMENTS_SCHEMA as UCSC_ARGUMENTS_SCHEMA
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.sequence_and_context_sources.gene_context_evidence.ensembl_acquisition import ARGUMENTS_SCHEMA as ENSEMBL_ARGUMENTS_SCHEMA

INTEGER = {"type": "integer", "minimum": 0}
TEXT = {"type": "string", "minLength": 1}


def catalog():
    definitions = {
        "reference.neighborhood": ("Inspect actual acquired GenBank features around one explicitly selected reference locus or coordinate. Preserve source labels, partial boundaries and unavailable context; infer no orthology or target function. Left/right follow the reference axis.",
            obj({"reference_ref": REF, "selector": obj({"locus_tag": TEXT, "protein_id": TEXT,
                "coordinate": INTEGER, "coordinate_frame": {"enum": ["record", "original"]}, "feature_kind": TEXT}, []),
                "left_bp": INTEGER, "right_bp": INTEGER}, ["reference_ref", "selector", "left_bp", "right_bp"])),
        "public.string.network": ("Acquire one STRING 12.5 functional-network response for the supplied disambiguated STRING IDs, explicit taxon and score threshold. Add no network nodes or identifier-mapping request. Retain native endpoint identities, channel scores and response qualifications within the supplied byte limit; no returned edge is a gene-function annotation, and no returned edge does not establish biological absence.",
            json.loads(canonical(PROVIDER_ARGUMENTS_SCHEMAS['public.string.network']))),
        "public.ucsc.request": ("Acquire one explicitly selected UCSC assembly, hub, track, schema or DNA-interval response within the supplied byte limit. Preserve native fields, repeated members, exact numeric tokens and separate request, capture and item-limit meanings. Sequence intervals use zero-based half-open coordinates; returned DNA retains its actual orientation and masking case. Extra requests, whole-population coverage and gene-function assignments are not inferred.",
            json.loads(canonical(UCSC_ARGUMENTS_SCHEMA))),
        "public.ensembl.request": ("Acquire one explicitly selected Ensembl 116 BioMart registry, dataset inventory, dataset configuration or gene-homology response. Select literal source and target datasets, supplied gene IDs, advertised attributes and byte limit. Preserve native XML, ordered TSV rows, duplicate mappings, blank targets, native homology types and one-based inclusive gene coordinates. Dependent requests require received discovery Sources; each request is a separate selected action. Native completion, captured bytes and matching-population coverage remain distinct.",
            json.loads(canonical(ENSEMBL_ARGUMENTS_SCHEMA))),
    }
    return {name: {"description": description, "input_schema": schema}
        for name, (description, schema) in definitions.items()}
