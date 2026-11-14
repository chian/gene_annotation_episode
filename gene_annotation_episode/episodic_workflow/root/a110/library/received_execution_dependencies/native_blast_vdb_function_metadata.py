from __future__ import annotations
from copy import deepcopy
import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_database_metadata as _metadata
_SCHEMA_ID = 'native_blast_vdb_function_metadata_v1'
_object, _array = (_metadata._object, _metadata._array)
_nullable, _enum = (_metadata._nullable, _metadata._enum)
_TOKEN, _I0, _I1 = (_metadata._TOKEN, _metadata._I0, _metadata._I1)
_PROV, _ID, _FUNCTION = (_metadata._PROV, _metadata._IDENTIFIER, _metadata._FUNCTION)
_SHA, _BOOL = (_metadata._SHA, _metadata._BOOL)
_MEMBER = _metadata._MEMBER_KEY
_ADDRESS = _object(assignment_scope=_enum('whole_sequence', 'feature'), member_key=_MEMBER, feature_identifier=_nullable(_ID))
_ASSIGNMENT = _object(assignment_key=_TOKEN, function=_FUNCTION, assignment_scope=_enum('whole_sequence', 'feature', 'sample'), target=_object(member_key=_nullable(_MEMBER), feature_identifier=_nullable(_ID), sample_key=_nullable(_TOKEN)), metadata_key=_TOKEN, function_ordinal=_I0, scope_origin=_enum('native_feature_record', 'supplied_explicit_scope'), scope_source=_PROV, whole_sequence_cds_feature_identifier=_nullable(_ID), sources=_array(_PROV))
_DEPENDENCY = _object(dependency_key=_TOKEN, relation=_enum('same_original_molecule', 'same_library', 'same_study', 'declared_dependent'), entities=_array(_ADDRESS), sources=_array(_PROV), native_record={'type': ['object', 'string']})
_SEQUENCE_IDENTITY = _object(molecule=_enum('nt'), sha256=_SHA, length=_I1)
_TARGET_IDENTITY = _object(assignment_scope=_enum('whole_sequence', 'feature'), representation=_enum('full_member_nt_v1', 'oriented_feature_nt_v1'), molecule=_enum('nt'), sha256=_SHA, length=_I1, coding=_nullable(_object(genetic_code=_I1, codon_start={'type': 'integer', 'enum': [1, 2, 3]}, translation_sha256=_SHA, translation_length=_I1)))
_CENSUS = _object(census_key=_TOKEN, assignment_scope=_enum('whole_sequence', 'feature'), function_namespace=_TOKEN, scope=_enum('searched_population', 'dataset_census', 'supplied_subset'), datasets=_array(_object(dataset_key=_TOKEN, identifier=_ID, snapshot=_metadata._SNAPSHOT, selected_input=_metadata._SELECTED, sra_mode={'type': 'integer', 'enum': [0, 1, 2]}, include_filtered_reads=_BOOL)), annotation_snapshot=_object(identifier=_ID, content_sha256=_SHA, assignment_namespace=_TOKEN, source=_PROV), enumeration=_object(base_count_unit=_enum('member_instance', 'feature_instance'), reported_total=_nullable(_I0), complete=_BOOL, pagination_complete=_nullable(_BOOL), source=_PROV, native_record={'type': 'object'}), entities=_array(_object(entity_key=_TOKEN, address=_ADDRESS, target_identity=_TARGET_IDENTITY, parent_sequence_identity=_SEQUENCE_IDENTITY, functions=_array(_FUNCTION), function_assignment_sources=_array(_PROV), origin_sample_keys=_array(_TOKEN), sample_relation_status=_enum('available', 'unavailable', 'incompatible'), source=_PROV)), dependency_records=_array(_DEPENDENCY), annotation_bindings=_array(_object(assignment_key=_TOKEN, census_entity_key=_TOKEN, annotation_snapshot_sha256=_SHA, source=_PROV)), identity_proofs=_array(_object(entity_key=_TOKEN, sequence_source=_PROV, linkage_source=_PROV, normalization=_enum('full_member_nt_v1', 'oriented_feature_nt_v1'), symbols={'type': 'string', 'minLength': 1})), source=_PROV, native_record={'type': 'object'})
_UNIT_FIELDS = dict(supplied_assignments=_array(_ASSIGNMENT), dependency_records=_array(_DEPENDENCY), census_records=_array(_CENSUS))
_UNIT = _object(search_key=_metadata._SEARCH, **_UNIT_FIELDS)
_SCHEMA = _object(schema=_enum(_SCHEMA_ID), documents=_array(_metadata._DOCUMENT), searches=_array(_UNIT))

def native_blast_vdb_function_metadata_schema() -> dict:
    """Return the single closed wire schema, detached from validator state."""
    return deepcopy(_SCHEMA)
