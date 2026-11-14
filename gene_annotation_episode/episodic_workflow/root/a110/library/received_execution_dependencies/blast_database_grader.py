from __future__ import annotations
from copy import deepcopy
import json
import re
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.blast_fasta_record_identity import blast_record_identity
_DESCRIPTION_BINDING_FIELDS = {'report_index', 'hit_index', 'description_index', 'metadata_index', 'native_description', 'metadata_identifier', 'metadata_source_ref', 'metadata_pointer', 'linkage_source_ref', 'linkage_pointer'}
_SEQUENCE_BINDING_FIELDS = {'report_index', 'hit_index', 'kind', 'sequence_group', 'algorithm', 'digest', 'molecule', 'sequence_length', 'source_ref', 'pointer', 'linkage_source_ref', 'linkage_pointer'}

def _uses_record_locators(metadata, descriptions, sequences):
    """Detect only explicitly extended association rows, never native payloads."""
    return any((isinstance(row, dict) and field in row for rows, field in ((metadata, 'record_locator'), (descriptions, 'metadata_record_locator'), (sequences, 'record_locator')) for row in (rows if isinstance(rows, list) else [])))

def _validate_record_locators(metadata, descriptions, sequences, *, association_version):
    """Keep public partial metadata while validating the closed new addresses."""
    if association_version not in (1, 2):
        raise ValueError('blast_database_association_version_invalid')
    if association_version == 1:
        if _uses_record_locators(metadata, descriptions, sequences):
            raise ValueError('blast_record_locator_requires_v2_sheet')
        return
    for rows, field, source, pointer in ((metadata, 'record_locator', 'source', 'native_pointer'), (descriptions, 'metadata_record_locator', 'metadata_source_ref', 'metadata_pointer'), (sequences, 'record_locator', 'source_ref', 'pointer')):
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, dict) and field in row:
                blast_record_identity(source_ref=row.get(source), pointer=row.get(pointer), record_locator=row[field])

def _binding_fields_valid(row, fields, locator_field, association_version):
    return isinstance(row, dict) and (set(row) == fields or (association_version == 2 and set(row) == fields | {locator_field}))

def _text(value):
    return value if isinstance(value, str) and value else None

def _json_copy(value):
    json.dumps(value, allow_nan=False)
    return deepcopy(value)

def _index(value):
    return type(value) is int and value >= 0

def _pointer(value):
    return isinstance(value, str) and (value == '' or value.startswith('/')) and (re.search('~(?![01])', value) is None)

def _calculation_context(value):
    """Validate the explicit context port; never manufacture request fields."""
    if value is None:
        return None
    try:
        value = _json_copy(value)
    except (TypeError, ValueError) as error:
        raise ValueError('blast_database_calculation_context_finite_json_required') from error
    if not isinstance(value, dict) or set(value) != {'reporting', 'database_identity'}:
        raise ValueError('blast_database_calculation_context_fields_invalid')
    reporting = value['reporting']
    if not isinstance(reporting, dict) or set(reporting) != {'native_hit_array_present', 'native_hit_count', 'requested_hit_limit', 'requested_hsp_limit', 'native_returncode', 'producer_complete'} or type(reporting['native_hit_array_present']) is not bool or any((reporting[key] is not None and (not _index(reporting[key])) for key in ('native_hit_count', 'requested_hit_limit', 'requested_hsp_limit'))) or (reporting['native_returncode'] is not None and type(reporting['native_returncode']) is not int) or (reporting['producer_complete'] is not None and type(reporting['producer_complete']) is not bool):
        raise ValueError('blast_database_calculation_reporting_invalid')
    identity = value['database_identity']
    if identity is not None:
        if not isinstance(identity, dict) or set(identity) != {'namespace', 'value', 'version', 'release', 'scope', 'preparation_type', 'source'} or any((_text(identity[key]) is None for key in ('namespace', 'value'))) or any((identity[key] is not None and _text(identity[key]) is None for key in ('version', 'release', 'scope'))) or (identity['preparation_type'] not in ('sequence_database', 'rps', 'delta', 'unknown')) or (not isinstance(identity['source'], dict)) or (set(identity['source']) != {'source_ref', 'pointer'}) or (_text(identity['source']['source_ref']) is None) or (not _pointer(identity['source']['pointer'])):
            raise ValueError('blast_database_calculation_identity_invalid')
    return value
