"""Original selected application observations through existing typed returns.

One AppService publication/receipt owner serves the finite new application
adapters. It performs no acquisition, native parsing or calculation. Original
selected values are authenticated against saved Source-backed documents; only
the top publication Source implies custody. Nested native identifiers are data.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a106.library.bvbrc_application_facts import FACT_SOURCE, IDENTIFIER_NAMESPACE, _PREFIX, _SOURCE, _object, _require, encode_field
from copy import deepcopy
import re
from urllib.parse import quote, unquote
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.bvbrc_annotation_contracts import VALUE_VERSION, selected_field_schema, validate_selected_field
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.bvbrc_assembly_contracts import VALUE_VERSION as ASSEMBLY_VALUE_VERSION, selected_field_schema as assembly_field_schema, validate_selected_field as validate_assembly_field
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority import bvbrc_variation_bundle_adapter as variation
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority import bvbrc_influenza_ha_bundle_adapter as influenza_ha
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority import bvbrc_subspecies_contracts as subspecies_contracts
from gene_annotation_episode.episodic_workflow.root.a106 import bvbrc_intervention_bundle_adapter as intervention
from gene_annotation_episode.episodic_workflow.root.a106.execution_contracts import canonical

def application_fact_sources():
    value = selected_field_schema()
    definitions = value.pop('$defs')
    assembly = assembly_field_schema()
    _require(canonical(assembly.pop('$defs')) == canonical(definitions), 'literal_definitions_conflict')
    ha = influenza_ha.selected_field_schema()
    strains = subspecies_contracts.selected_field_schema()
    perturbation = intervention.selected_field_schema()
    for field in (ha, strains, perturbation):
        _require(canonical(field.pop('$defs')) == canonical(definitions), 'literal_definitions_conflict')
    variants = variation.selected_field_schema()
    for name, node in variants.pop('$defs').items():
        _require(name not in definitions or canonical(definitions[name]) == canonical(node), 'literal_definitions_conflict')
        definitions[name] = node
    schema = {'type': 'array', 'items': _object({'source_ref': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'}, 'field': {'type': 'string', 'format': 'identifier', 'x-reference-namespace': IDENTIFIER_NAMESPACE}, 'value': {'oneOf': [value, assembly, variants, ha, strains, perturbation]}}), '$defs': definitions, 'x-source': FACT_SOURCE}
    return {FACT_SOURCE: {'type': 'array', 'meaning': 'Literal original selected BV-BRC application observations and shared calculated components.', 'report_schema': schema}}

def validate_application_rows(rows):
    """Closed whole-row validation; this grants no Source or nested identifier."""
    _require(type(rows) is list, 'returned_facts_invalid')
    result = []
    for row in rows:
        _require(type(row) is dict and set(row) == {'source_ref', 'field', 'value'} and (type(row['source_ref']) is str) and (_SOURCE.fullmatch(row['source_ref']) is not None) and (type(row['field']) is str) and row['field'].startswith(IDENTIFIER_NAMESPACE + ':'), 'returned_facts_invalid')
        candidate = row['value']
        _require(type(candidate) is dict and candidate.get('version') in (VALUE_VERSION, ASSEMBLY_VALUE_VERSION, variation.VALUE_VERSION, influenza_ha.VALUE_VERSION, subspecies_contracts.VALUE_VERSION, intervention.VALUE_VERSION), 'returned_facts_invalid')
        value = {VALUE_VERSION: validate_selected_field, ASSEMBLY_VALUE_VERSION: validate_assembly_field, variation.VALUE_VERSION: variation.validate_selected_field, influenza_ha.VALUE_VERSION: influenza_ha.validate_selected_field, subspecies_contracts.VALUE_VERSION: subspecies_contracts.validate_selected_field, intervention.VALUE_VERSION: intervention.validate_selected_field}[candidate['version']](candidate)
        parts = row['field'][len(IDENTIFIER_NAMESPACE) + 1:].split('/')
        _require(type(value['context']) is dict and len(parts) == 2 and all(parts) and (value['context'].get('analysis_id') == unquote(parts[0])) and (row['field'] == encode_field(unquote(parts[0]), unquote(parts[1]))), 'returned_facts_invalid')
        result.append(deepcopy(row))
    return result
