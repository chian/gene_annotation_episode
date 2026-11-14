from __future__ import annotations

def _object(**fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}

def _array(item):
    return {'type': 'array', 'items': item}

def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}

def _enum(*values):
    return {'enum': list(values)}

def _slot(schema, kind):
    return dict(schema, **{'x-wire': kind})
_STRING = {'type': 'string'}
_TOKEN = {'type': 'string', 'minLength': 1, 'maxLength': 512, 'pattern': '^[^\\x00\\r\\n]+$'}
_I0 = {'type': 'integer', 'minimum': 0}
_I1 = {'type': 'integer', 'minimum': 1}
_NUMBER = {'type': 'number'}
_BOOL = {'type': 'boolean'}
_SHA = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
_POINTER = {'type': 'string', 'pattern': '^(?:/(?:[^~]|~[01])*)?$'}
_NATIVE = {}
_NATIVE_OBJECT = {'type': 'object'}
_INTERVAL = {'type': 'array', 'prefixItems': [_I0, _I1], 'minItems': 2, 'maxItems': 2, 'x-wire': 'interval'}
_IDENTIFIER = _object(namespace=_TOKEN, value=_TOKEN, version=_nullable(_TOKEN))
_FUNCTION = _object(namespace=_TOKEN, value=_TOKEN)
_PROV = _slot(_object(source_ref=_TOKEN, pointer=_POINTER), 'provenance')
_SOURCE = _slot(_TOKEN, 'source')
_SEARCH = _slot(_object(output_key=_TOKEN, member_ordinal=_nullable(_I0), report_index=_I0, search_pointer=_POINTER), 'search')
_PSSM = _slot(_object(document_key=_TOKEN, record_ordinal=_I0), 'pssm')
_LINEAGE = _array(_object(taxid=_I1, rank=_TOKEN, name=_nullable(_STRING)))
_DESCRIPTION = _object(id=_nullable(_STRING), accession=_nullable(_STRING), title=_nullable(_STRING), taxid=_nullable(_I1))
_DATABASE = _slot(_object(namespace=_TOKEN, value=_TOKEN, version=_nullable(_TOKEN), release=_nullable(_TOKEN), scope=_nullable(_TOKEN), preparation_type=_enum('sequence_database', 'rps', 'delta', 'unknown'), source=_PROV), 'database')
_OPERAND = _object(role=_enum('query', 'subject', 'database', 'profile', 'msa', 'checkpoint'), artifact_key=_nullable(_TOKEN), record_ordinal=_nullable(_I0), native_id=_nullable(_STRING), native_title=_nullable(_STRING), subject_ref=_nullable(_TOKEN), molecule=_enum('dna', 'rna', 'protein', 'unknown'), length=_nullable(_I1), selected_interval=_nullable(_INTERVAL), identity=_nullable(_IDENTIFIER))
_ADDRESS = {'oneOf': [_object(kind=_enum('input'), input_key=_TOKEN), _object(kind=_enum('output'), output_key=_TOKEN, relative_path=_TOKEN), _object(kind=_enum('database_manifest'), database_key=_TOKEN), _object(kind=_enum('database_metadata_manifest'), database_key=_TOKEN, manifest_index=_I0), _object(kind=_enum('database_sidecar'), database_key=_TOKEN, role=_enum('preparation_input_manifest', 'offline_configuration')), _object(kind=_enum('received'), source_ref=_TOKEN, artifact_ref=_TOKEN, sha256=_SHA, size_bytes=_I0)]}
_DOCUMENT = _object(document_key=_TOKEN, artifact=_ADDRESS, format=_enum('json', 'text', 'fasta', 'clustal', 'scoremat_asn_text', 'runinfo_csv', 'blast_vdb_cmd_table', 'ncbi_gbseq_xml'))
_SEQUENCE_BINDING = _object(report_index=_I0, hit_index=_I0, kind=_enum('full_sequence_digest'), sequence_group=_TOKEN, algorithm=_enum('sha256'), digest=_SHA, molecule=_enum('aa', 'nt'), sequence_length=_I1, source_ref=_SOURCE, pointer=_POINTER, linkage_source_ref=_SOURCE, linkage_pointer=_POINTER)
_SEQUENCE_PROOF = _slot(_object(binding_index=_I0, document_key=_TOKEN, representation=_enum('fasta_record', 'json_sequence'), record_ordinal=_nullable(_I0), sequence_pointer=_nullable(_POINTER), molecule=_enum('aa', 'nt'), sha256=_SHA, length=_I1), 'proof')
_BOUND_SEQUENCE = _object(search_key=_SEARCH, binding=_SEQUENCE_BINDING)
_DESCRIPTION_BINDING = _object(report_index=_I0, hit_index=_I0, description_index=_I0, metadata_index=_I0, native_description=_DESCRIPTION, metadata_identifier=_object(namespace=_TOKEN, value=_TOKEN), metadata_source_ref=_SOURCE, metadata_pointer=_POINTER, linkage_source_ref=_SOURCE, linkage_pointer=_POINTER)
_ASSEMBLY = _object(accession=_nullable(_TOKEN), completeness_fraction=_nullable({'type': 'number', 'minimum': 0, 'maximum': 1}), contamination_fraction=_nullable({'type': 'number', 'minimum': 0}), contig_count=_nullable(_I0), contig_n50=_nullable(_I0), total_sequence_length=_nullable(_I0), quality_method=_nullable(_TOKEN), quality_version=_nullable(_TOKEN), measurement_methods=_object(**{k: _nullable(_TOKEN) for k in ('completeness_fraction', 'contamination_fraction', 'contig_count', 'contig_n50', 'total_sequence_length')}), source=_SOURCE, linkage_source=_SOURCE)
_SEQUENCE_RECORD = _object(identifier_namespace=_TOKEN, accession=_TOKEN, source=_SOURCE, native_pointer=_POINTER, taxid=_nullable(_I1), lineage=_LINEAGE, functions=_array(_object(function=_TOKEN, evidence=_array(_NATIVE), source=_SOURCE)), origin={'type': 'object', 'propertyNames': _TOKEN, 'additionalProperties': {'type': ['string', 'number', 'boolean', 'null']}}, assembly=_nullable(_ASSEMBLY), sequence_group=_nullable(_TOKEN), study_groups=_array(_TOKEN), native_record=_NATIVE)
_SEQUENCE_POPULATION = _object(database=_TOKEN, release=_nullable(_TOKEN), scope=_TOKEN, count_unit=_enum('unique_sequences', 'sequence_groups'), total_count=_I1, function_counts={'type': 'object', 'propertyNames': _TOKEN, 'additionalProperties': _I0}, source=_SOURCE)
_PROFILE_RECORD = _object(profile_key=_TOKEN, database_identity=_DATABASE, model_identifier=_IDENTIFIER, pssm_key=_nullable(_PSSM), num_columns=_nullable(_I1), master_sequence_ref=_nullable(_PROV), specific_bits_threshold=_nullable(_NUMBER), reporting_bits_threshold=_nullable(_NUMBER), source=_PROV, native_record=_NATIVE_OBJECT)
_PROFILE_BINDING = _object(search_key=_SEARCH, hit_ordinal=_I0, description_ordinal=_I0, profile_key=_TOKEN, native_description=_DESCRIPTION, provenance=_PROV)
_PROFILE_FUNCTION = _object(profile_key=_TOKEN, function=_FUNCTION, evidence_refs=_array(_PROV), provenance=_PROV)
_MODEL_RELATION = _object(left_profile_key=_TOKEN, right_profile_key=_TOKEN, relation=_enum('identical_model', 'same_family', 'same_superfamily', 'overlapping_training_set'), provenance=_PROV)
_EVIDENCE = _object(origin=_enum('supplied_source_record'), source=_PROV, source_format=_TOKEN, original_record={'type': ['object', 'array', 'string']}, extractor={'type': 'null'})
_SNAPSHOT = _object(release=_nullable(_TOKEN), snapshot_id=_nullable(_TOKEN), manifest_sha256=_nullable(_SHA))
_SELECTED = _object(kind=_enum('accession', 'path', 'alias'), value=_TOKEN)
_DATASET = _object(dataset_key=_TOKEN, identifier=_nullable(_IDENTIFIER), dataset_type=_enum('sra', 'csra', 'wgs', 'unknown'), selected_input=_SELECTED, snapshot=_SNAPSHOT, search_context=_object(search_key=_SEARCH, sra_mode=_enum(0, 1, 2, None), include_filtered_reads=_nullable(_BOOL), subject_genetic_code=_nullable(_I1), input_pssm_key=_nullable(_PSSM), source=_PROV, query_extent=_object(mode=_enum('full', 'interval', 'unknown'), interval=_nullable(_INTERVAL), source=_nullable(_PROV))), run_identifiers=_array(_IDENTIFIER), sample_links=_array(_object(sample_key=_TOKEN, sample_identifier=_IDENTIFIER, biosample_identifier=_nullable(_IDENTIFIER), source=_PROV)), assembly_links=_array(_object(assembly_identifier=_IDENTIFIER, source=_PROV)), metadata_keys=_array(_TOKEN), source=_PROV)
_MEMBER_KIND = _enum('read', 'reference', 'wgs_sequence', 'unknown')
_MEMBER_KEY = _object(dataset_key=_TOKEN, member_kind=_MEMBER_KIND, member_identifier=_IDENTIFIER)
_MEMBER_BINDING = _object(search_key=_SEARCH, hit_ordinal=_I0, description_ordinal=_I0, native_description=_DESCRIPTION, dataset_key=_TOKEN, member_kind=_MEMBER_KIND, member_identifier=_IDENTIFIER, relationship=_enum('reported_origin', 'catalog_membership'), read_identity=_nullable(_object(native_read_name=_TOKEN, spot_id=_nullable(_TOKEN), read_index=_nullable(_I0), source=_PROV)), reference_identity=_nullable(_object(identifier=_IDENTIFIER, full_length=_nullable(_I1), sequence_sha256=_nullable(_SHA), source=_PROV)), sample_key=_nullable(_TOKEN), provenance=_PROV)
_ENTITY = _slot(_object(kind=_enum('dataset', 'sample', 'member', 'feature', 'query_master'), dataset_key=_nullable(_TOKEN), member_identifier=_nullable(_IDENTIFIER), sample_key=_nullable(_TOKEN), feature_identifier=_nullable(_IDENTIFIER), pssm_key=_nullable(_PSSM)), 'entity')
_VDB_ISSUE = _object(code=_TOKEN, search_key=_nullable(_SEARCH), hit_ordinal=_nullable(_I0), hsp_ordinal=_nullable(_I0), source_pointer=_nullable(_POINTER), details=_NATIVE_OBJECT)
_VDB_RECORD = _object(metadata_key=_TOKEN, entity=_ENTITY, linkage_source=_nullable(_PROV), source_format=_enum('supplied_explicit'), source_version=_nullable(_TOKEN), native_record={'type': ['object', 'string']}, source=_PROV, identifiers=_array(_IDENTIFIER), sequence=_nullable(_object(symbols=_STRING, molecule=_enum('nt', 'aa'), length=_I1, sha256=_SHA)), functions=_array(_object(function=_FUNCTION, evidence=_array(_NATIVE_OBJECT), source=_PROV)), taxid=_nullable(_I1), taxid_scope=_enum('entity_organism', 'sample_context', 'reported_subject', 'unknown'), lineage=_LINEAGE, assembly=_nullable(_object(identifier=_IDENTIFIER, completeness_percent=_nullable(_NUMBER), contamination_percent=_nullable(_NUMBER), contig_count=_nullable(_I0), contig_n50=_nullable(_I0), total_sequence_length=_nullable(_I0), method=_nullable(_TOKEN), method_version=_nullable(_TOKEN), source=_PROV, linkage_source=_PROV)), feature=_nullable(_object(feature_identifier=_IDENTIFIER, key=_TOKEN, location=_STRING, segments=_array(_INTERVAL), strand=_enum(-1, 1, None), partial5=_nullable(_BOOL), partial3=_nullable(_BOOL), codon_start=_enum(1, 2, 3, None), genetic_code=_nullable(_I1), translation=_nullable(_STRING), qualifiers=_array(_object(name=_TOKEN, value=_nullable(_STRING))), member_sequence_metadata_key=_nullable(_TOKEN))), master_mapping=_nullable(_object(pssm_key=_PSSM, num_columns=_I1, columns=_array(_object(column=_I0, master_position=_nullable(_I0), symbol=_STRING)))), extraction_method=_enum('supplied_explicit'), issues=_array(_VDB_ISSUE))
_FEATURE_BINDING = _object(search_key=_SEARCH, hit_ordinal=_I0, member_binding_index=_I0, member_identifier=_IDENTIFIER, feature_identifier=_IDENTIFIER, feature_kind=_TOKEN, member_interval=_INTERVAL, segments=_array(_INTERVAL), location_status=_enum('exact', 'partial', 'unsupported'), strand=_enum(-1, 1, None), genetic_code=_nullable(_I1), codon_start=_enum(1, 2, 3, None), function=_nullable(_FUNCTION), feature_sequence_sha256=_nullable(_SHA), translation_metadata_key=_nullable(_TOKEN), provenance=_PROV)
_POP_ENTITY = _slot(_object(kind=_enum('read', 'reference', 'wgs_sequence', 'unique_sequence', 'feature', 'sample'), member_key=_nullable(_MEMBER_KEY), sequence_group_key=_nullable(_TOKEN), feature_identifier=_nullable(_IDENTIFIER), sample_key=_nullable(_TOKEN)), 'population_entity')
_POPULATION = _object(population_key=_TOKEN, datasets=_array(_object(dataset_key=_TOKEN, identifier=_nullable(_IDENTIFIER), snapshot=_SNAPSHOT, sra_mode=_enum(0, 1, 2, None), include_filtered_reads=_nullable(_BOOL))), count_unit=_enum('reads', 'references', 'wgs_sequences', 'unique_sequences', 'features', 'samples'), scope=_enum('searched_population', 'dataset_census', 'supplied_subset'), total_count=_nullable(_I0), complete=_BOOL, members=_nullable(_array(_POP_ENTITY)), function_counts=_nullable(_array(_object(function=_FUNCTION, count=_I0, assignment_scope=_enum('whole_sequence', 'feature', 'sample'), source=_PROV))), function_members=_nullable(_array(_object(function=_FUNCTION, entities=_array(_POP_ENTITY)))), source=_PROV, native_record=_NATIVE_OBJECT)
_EXTRACTION = _object(dataset_key=_TOKEN, selected_input=_SELECTED, snapshot=_SNAPSHOT, entry_identifiers=_array(_IDENTIFIER), native_returncode=_nullable({'type': 'integer'}), producer_complete=_nullable(_BOOL), include_filtered_reads=_nullable(_BOOL), reference_selection=_nullable(_BOOL), outfmt=_enum('%i\t%a\t%l\t%s'), source=_PROV)
_PARSED_SOURCE = _slot(_object(document_key=_TOKEN, parser=_enum('runinfo_csv', 'blast_vdb_cmd_table', 'ncbi_gbseq_xml'), source_version=_nullable(_TOKEN), extraction_context=_nullable(_EXTRACTION)), 'parsed_source')
_METADATA_BINDING = _object(binding_key=_TOKEN, record_key=_object(source_ref=_SOURCE, record_ordinal=_I0), metadata_key=_TOKEN, entity=_ENTITY, parent_metadata_key=_nullable(_TOKEN), member_binding_index=_nullable(_I0), identifier_links=_array(_object(source_identifier=_IDENTIFIER, target_identifier=_IDENTIFIER, representation=_enum('literal', 'sra_general_tag'), source=_PROV)), source=_PROV)

def _payload(consumer, **fields):
    schema_id = 'native_blast_database_' + consumer + '_metadata_v1'
    return _object(schema=_enum(schema_id), documents=_array(_DOCUMENT), **fields)
_SCHEMAS = {'query_identity': _payload('query', sequence_records=_array(_object(input_key=_TOKEN, record_ordinal=_I0, subject_ref=_nullable(_TOKEN), identity=_nullable(_IDENTIFIER), source=_PROV)), effective_msa_masters=_array(_object(input_key=_TOKEN, record_ordinal=_I0, source=_PROV)), master_subjects=_array(_object(kind=_enum('msa', 'pssm'), input_key=_TOKEN, record_ordinal=_I0, subject_ref=_TOKEN, sequence_sha256=_SHA, source=_PROV)), search_bindings=_array(_slot(_object(search_key=_SEARCH, stage=_enum('sequence_database', 'domain_database', None), biological_round=_nullable(_I1), database_key=_nullable(_TOKEN), input_pssm_key=_nullable(_PSSM), provenance=_nullable(_PROV)), 'search_binding')), target_contexts=_array(_object(search_key=_SEARCH, taxid=_nullable(_I1), lineage=_LINEAGE, independent_of_search=_nullable(_BOOL), source=_PROV))), 'sequence_database': _payload('sequence', searches=_array(_object(search_key=_SEARCH, reference_metadata=_array(_SEQUENCE_RECORD), description_bindings=_array(_object(search_key=_SEARCH, binding=_DESCRIPTION_BINDING)), sequence_identity_bindings=_array(_BOUND_SEQUENCE), sequence_proofs=_array(_SEQUENCE_PROOF), database_profile=_nullable(_SEQUENCE_POPULATION)))), 'profile': _payload('profile', searches=_array(_object(search_key=_SEARCH, profile_records=_array(_PROFILE_RECORD), profile_bindings=_array(_PROFILE_BINDING), function_bindings=_array(_PROFILE_FUNCTION), model_relations=_array(_MODEL_RELATION)))), 'iteration': _payload('iteration', checkpoint_bindings=_array(_object(pssm_key=_PSSM, role=_enum('input', 'after_search', 'output'), search_key=_nullable(_SEARCH), biological_round=_nullable(_I1), provenance=_PROV)), comparison_pairs=_array(_object(comparison_key=_TOKEN, earlier_search_key=_SEARCH, later_search_key=_SEARCH, identity_basis=_enum('full_sequence_digest', 'profile_model_identifier'), relation_source=_PROV)), inclusion_records=_array(_object(record_key=_TOKEN, pssm_key=_PSSM, search_key=_nullable(_SEARCH), membership_kind=_enum('checkpoint_sequence_members'), query_membership=_enum('included', 'excluded', 'unknown'), complete=_BOOL, members=_array(_object(identity=_IDENTIFIER, provenance=_PROV)), evidence=_EVIDENCE)), convergence_records=_array(_object(record_key=_TOKEN, search_key=_nullable(_SEARCH), query_operand=_nullable(_OPERAND), native_converged=_BOOL, evidence=_EVIDENCE))), 'vdb': _payload('vdb', searches=_array(_object(search_key=_SEARCH, dataset_records=_array(_DATASET), member_bindings=_array(_MEMBER_BINDING), sequence_identity_bindings=_array(_BOUND_SEQUENCE), sequence_proofs=_array(_SEQUENCE_PROOF), feature_bindings=_array(_FEATURE_BINDING), reference_metadata=_array(_VDB_RECORD), population_records=_array(_POPULATION), parsed_sources=_array(_PARSED_SOURCE), metadata_bindings=_array(_METADATA_BINDING))))}
_SEQUENCE_V2 = 'native_blast_database_sequence_metadata_v2'
_SEQUENCE_V3 = 'native_blast_database_sequence_metadata_v3'
_RECORD_LOCATOR = _nullable(_object(kind=_enum('fasta_record'), record_ordinal=_I0))
_SEQUENCE_SCHEMA_V2 = _object(schema=_enum(_SEQUENCE_V2), documents=_array(_DOCUMENT), searches=_array(_object(search_key=_SEARCH, reference_metadata=_array(_object(**_SEQUENCE_RECORD['properties'], record_locator=_RECORD_LOCATOR)), description_bindings=_array(_object(search_key=_SEARCH, binding=_object(**_DESCRIPTION_BINDING['properties'], metadata_record_locator=_RECORD_LOCATOR))), sequence_identity_bindings=_array(_object(search_key=_SEARCH, binding=_object(**_SEQUENCE_BINDING['properties'], record_locator=_RECORD_LOCATOR))), sequence_proofs=_array(_SEQUENCE_PROOF), database_profile=_nullable(_SEQUENCE_POPULATION))))

def _schema_for(consumer, schema_id):
    if (consumer, schema_id) == ('sequence_database', _SEQUENCE_V3):
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_database_population_metadata import native_blast_database_sequence_population_metadata_schema
        return native_blast_database_sequence_population_metadata_schema()
    if (consumer, schema_id) == ('vdb_function', 'native_blast_vdb_function_metadata_v1'):
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_vdb_function_metadata import native_blast_vdb_function_metadata_schema
        return native_blast_vdb_function_metadata_schema()
    if (consumer, schema_id) == ('sequence_database', _SEQUENCE_V2):
        return _SEQUENCE_SCHEMA_V2
    schema = _SCHEMAS.get(consumer)
    if schema is None or schema['properties']['schema']['enum'] != [schema_id]:
        raise _Invalid('', 'metadata_tuple_unregistered', 'schema_unsupported')
    return schema

class _Invalid(ValueError):

    def __init__(self, pointer, detail, code='payload_invalid', document=None, search=None):
        self.pointer, self.detail, self.code = (pointer, detail, code)
        self.document, self.search = (document, search)

def _record_relation_failed(validation, pointer):
    """Qualification belongs to the original payload slot, not a compact index."""
    original = _original_pointer(validation, pointer)
    return any((issue['pointer'] in {original + '/record_locator', original + '/metadata_record_locator'} for issue in validation['issues']))

def _original_pointer(validation, pointer):
    candidates = [r for r in validation['normalization_map'] if pointer == r['normalized_pointer'] or pointer.startswith(r['normalized_pointer'] + '/')]
    if not candidates:
        return pointer
    row = max(candidates, key=lambda r: len(r['normalized_pointer']))
    return row['payload_pointer'] + pointer[len(row['normalized_pointer']):]
