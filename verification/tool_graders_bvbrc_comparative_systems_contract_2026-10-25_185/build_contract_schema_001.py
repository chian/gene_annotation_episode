"""Build a review-only static schema. No production module is changed/imported."""
from pathlib import Path
import json

BASE = Path(__file__).resolve().parent
D = {}
def obj(**p):
    return {'type': 'object', 'properties': p, 'required': list(p), 'additionalProperties': False}
def ref(n): return {'$ref': '#/$defs/' + n}
def arr(s, unique=False): return {'type': 'array', 'items': s, **({'uniqueItems': True} if unique else {})}
def enum(*v): return {'type': 'string', 'enum': list(v)}
def null(s): return {'anyOf': [s, {'type': 'null'}]}
def con(v): return {'const': v}
S = {'type': 'string'}
ID = {'type': 'string', 'minLength': 1}
I = {'type': 'integer', 'minimum': 0}
N = {'type': 'number', 'minimum': 0}
B = {'type': 'boolean'}
SHA = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
PTR = {'type': 'string', 'pattern': r'^(?:/(?:[^~/]|~[01])*)*$'}

codes = '''outer_json_invalid duplicate_json_key format_incompatible tsv_header_mismatch
tsv_row_width_mismatch numeric_token_invalid nonfinite_number artifact_truncated
original_task_mismatch producer_version_unverified native_first_object_discard
native_query_completeness_unknown group_membership_unknown native_identifier_placeholder
identity_conflict duplicate_identical_representation duplicate_record_conflict inner_join_missing
inner_join_many_to_many variant_matrix_extra_column genome_name_collision conflicting_native_categories
hex_count_width_ambiguous native_formula_mismatch reference_release_unknown reference_membership_missing
population_incomplete population_incompatible empty_denominator unrequested_dependency_missing
page_gap page_overlap snapshot_consistency_unknown data_input_binding_mismatch
data_input_unavailable unsupported_server_filter annotation_filter_applied
later_snapshot_not_original missing_required_field incomplete_reference_membership
native_category_imputed absent_record_not_measured dependent_representation
invalid_component_request ambiguous_document_selection missing_document_selection
byte_identity_mismatch no_native_rows not_selected source_version_mismatch'''.split()
D['DiagnosticCodeV1'] = enum(*codes)
D['RoleV1'] = enum('family_summary','pathway_summary','pathway_ec_summary','pathway_associations',
    'subsystem_summary','subsystem_associations','subsystem_overview','subsystem_variants',
    'family_feature_records','pathway_records','subsystem_records','genome_records',
    'family_reference','pathway_reference','subsystem_reference','original_genome_population',
    'producer_identity','native_document','reference_membership')
D['TableV1'] = enum('plfam','pgfam','pathway','ecnumber','genes','subsystems','overview',
    'pathways_tsv','subsystems_tsv','variant_matrix','data_rows','document')
D['BasisV1'] = enum('service_artifact','source_executed_synthetic','synthetic_fixture','supplied_data_api')
D['CompletenessV1'] = enum('complete_for_declared_population','partial','unknown','incompatible')
D['CellReferenceV1'] = obj(kind=enum('native','sheet','supplied','component'), owner_id=ID, pointer=PTR)
D['SourceLocationV1'] = obj(source_ref=ID, raw_artifact_ref=ID, document_id=null(ID),
    json_pointer=PTR, table=null(ref('TableV1')), row_ordinal=null(I), column_ordinal=null(I), native_field=null(S))
D['NumericCellV1'] = obj(state=enum('available','missing','not_measured','failed','truncated','incompatible','invalid'),
    value=null({'type':'number'}), unit=enum('occurrence','genome','feature','feature_token','ec_token','role_token',
    'family','subsystem_name','record','genome_ec_pair','genome_role_pair','ec_genome_opportunity',
    'role_genome_opportunity','amino_acid','fraction','percent','feature_per_ec_genome',
    'feature_per_role_genome','occurrence_per_positive_genome','dimensionless'),
    origin=enum('program_reported_derived','derived_retained_records','derived_supplied_records','derived_calculation','unavailable'),
    population_id=null(ID), method_id=enum('native_field','native_hex_exact_width','distinct_valid_members',
    'record_occurrences','distinct_valid_feature_pairs','distinct_valid_genome_ec_pairs',
    'distinct_valid_genome_role_pairs','opportunity_product','ratio','coefficient_of_variation',
    'set_intersection','set_union','set_jaccard','explicit_category_exact_set','reported_formula_check','unavailable'),
    input_refs=arr(ref('CellReferenceV1')), uncertainty={'type':'null'}, qualification_codes=arr(ref('DiagnosticCodeV1'),True))
D['NumericCellV1']['allOf'] = [{'if':{'properties':{'state':con('available')}},
    'then':{'properties':{'value':{'type':'number'}}},'else':{'properties':{'value':{'type':'null'}}}}]
D['NativeNumberV1'] = obj(native_field=S, raw_lexeme=null(S), location=ref('SourceLocationV1'), cell=ref('NumericCellV1'))
D['DiagnosticV1'] = obj(code=ref('DiagnosticCodeV1'), phase=enum('decode','association','population','calculation','projection'),
    document_id=null(ID), row_ordinal=null(I), field=null(ref('RoleV1')), source_refs=arr(ID,True),
    locations=arr(ref('SourceLocationV1')), affected_field_ids=arr(ID,True), required_input_role=null(ref('RoleV1')))
D['RequirementV1'] = obj(requirement_id=ID, code=ref('DiagnosticCodeV1'), required_input_role=ref('RoleV1'),
    document_id=null(ID), affected_field_ids=arr(ID,True), source_refs=arr(ID,True))
D['ProducerEvidenceV1'] = obj(evidence_id=ID, identity_kind=enum('source_examined','source_executed','deployed_attested','unknown'),
    repository_url=null(ID), commit=null({'type':'string','pattern':'^[0-9a-f]{40}$'}),
    source_sha256=null(SHA), runtime_version=null(S), dependency_version=null(S),
    reference_release=null(S), source_locations=arr(ref('SourceLocationV1')))
D['QualifiedProducerEvidenceV1'] = obj(evidence=ref('ProducerEvidenceV1'),
    qualification=obj(original_task_ref=null(ID),basis=enum('source_only','source_execution','native_task_bound','unknown'),
        evidence_source_refs=arr(ID,True),host_binding_verified=con(True),evidence_fields_verified=con(True),receiver_possession_verified=con(True)))
D['OriginalRequestV1'] = obj(application=con('ComparativeSystems'), task_ref=ID,
    request_source_ref=ID, genome_ids=arr(ID), genome_groups=arr(ID), output_path=ID, output_file=ID,
    executed_genome_ids=null(arr(ID,True)), executed_population_evidence=arr(ref('SourceLocationV1')))
D['SourceDocumentV1'] = obj(document_id=ID, role=ref('RoleV1'), format_profile=enum(
    'comparative_systems_pathways_json_v1','comparative_systems_subsystems_json_v1',
    'comparative_systems_families_json_v1','comparative_systems_pathways_tsv_v1',
    'comparative_systems_subsystems_tsv_v1','comparative_systems_variant_matrix_source670b_v1'),
    source_ref=ID, raw_artifact_ref=ID, byte_count=I, sha256=SHA, transfer_body_complete=enum('complete','partial','unknown'),
    object_complete=enum('complete','partial','unknown'), original_task_ref=ID, producer_evidence_id=null(ID), basis=ref('BasisV1'))
D['PopulationV1'] = obj(population_id=ID, kind=enum('requested_direct_genomes','executed_genomes',
    'declared_query_genomes','native_view_represented_genomes','native_retained_records','supplied_data_records','selected_component_membership'),
    member_kind=enum('genome_id','record_id','family_id','ec_number','role_id','feature_id'),
    members=arr(ID), source_locations=arr(ref('SourceLocationV1')),
    raw_occurrence_count=ref('NumericCellV1'), distinct_valid_member_count=ref('NumericCellV1'),
    completeness=ref('CompletenessV1'), missing_members=arr(ID,True), unresolved_members=arr(S),
    relationship_to_original_task=enum('original_execution_snapshot','later_selected_snapshot','unverified','not_applicable'),
    qualification_codes=arr(ref('DiagnosticCodeV1'),True))
D['NativeFieldV1'] = obj(name=S, raw_text=S, location=ref('SourceLocationV1'))
D['NativeTableRowV1'] = obj(row_ordinal=I, tokens=arr(S), status=enum('ok','partial','invalid'),
    numeric_fields=arr(ref('NativeNumberV1')), qualification_codes=arr(ref('DiagnosticCodeV1'),True))
D['NativeTableV1'] = obj(table=ref('TableV1'), json_pointer=PTR, raw_text=S,
    dialect=enum('manual_tabs_unquoted','pandas_tsv','pinned_variant_matrix'),
    headers=arr(arr(S)), rows=arr(ref('NativeTableRowV1')))
# Full original JSON bytes are retained externally; scalar metadata is preserved without inferred biology.
D['NativeMetadataV1'] = obj(location=ref('SourceLocationV1'), value=ref('JSONValueV1'))
D['JSONValueV1'] = {'oneOf':[{'type':['null','boolean','number','string']},
    arr(ref('JSONValueV1')),{'type':'object','additionalProperties':ref('JSONValueV1')}]}
D['NativeDocumentResultV1'] = obj(version=con('bvbrc_comparative_systems_native_v1'),
    status=enum('ok','partial','invalid','failed'), document=ref('SourceDocumentV1'),
    tables=arr(ref('NativeTableV1')), metadata=arr(ref('NativeMetadataV1')),
    reported_numbers=arr(ref('NativeNumberV1')), diagnostics=arr(ref('DiagnosticV1')))
entity_fields = ['genome_id','family_id','pathway_id','ec_number','subsystem_id','role_id',
    'superclass_native','superclass_aggregation','class_name','subclass','subsystem_name','comparison_id']
D['EntityV1'] = obj(kind=enum('genome','family','pathway','pathway_ec','subsystem','subsystem_role','overview','variant','pair','population','document'),
    family_kind=null(enum('plfam','pgfam')), **{x:null(S) for x in entity_fields})
identity_fields = ['record_id','genome_id','feature_id','patric_id','pathway_id','ec_number',
    'subsystem_id','role_id','plfam_id','pgfam_id','accession','sequence_id']
D['AssociationRowV1'] = obj(association_id=ID, document_id=null(ID), record_set_id=null(ID),
    table=ref('TableV1'), row_ordinal=I, identifiers=obj(**{x:null(ID) for x in identity_fields}),
    active_category=null(enum('active','likely','inactive')), fields=arr(ref('NativeFieldV1')),
    identity_status=enum('valid','partial','conflicting'),
    coordinate_convention=enum('one_based_inclusive','unknown','not_applicable'),
    qualification_codes=arr(ref('DiagnosticCodeV1'),True))
D['GenomeFamilyCountV1'] = obj(genome_id=ID, genome_ordinal=I, reported_occurrences=ref('NumericCellV1'),
    presence_state=enum('recorded_positive','zero_in_qualified_record_population','no_record_completeness_unknown',
    'not_measured','failed','truncated','incompatible','conflicting'), source_locations=arr(ref('SourceLocationV1')))
def row_base():
    return dict(document_id=ID, native_row_ordinal=I, entity=ref('EntityV1'),
        source_locations=arr(ref('SourceLocationV1')), qualification_codes=arr(ref('DiagnosticCodeV1'),True))
D['FamilyRowV1'] = obj(**row_base(), raw_hex_counts=S, positive_genome_ids=arr(ID),
    genome_counts=arr(ref('GenomeFamilyCountV1')), **{k:ref('NumericCellV1') for k in [
        'reported_feature_occurrences','reported_genome_count','reported_length_min','reported_length_max',
        'reported_length_mean','reported_length_population_sd','positive_genome_count_from_list']})
D['PathwayRowV1'] = obj(**row_base(), **{k:ref('NumericCellV1') for k in ['reported_genome_count',
    'reported_ec_token_count','reported_feature_token_count','reported_genome_ec_count',
    'reported_ec_conservation_percent','reported_gene_conservation']})
D['PathwayECRowV1'] = obj(**row_base(), **{k:ref('NumericCellV1') for k in ['reported_genome_count',
    'reported_ec_token_count','reported_feature_token_count','reported_genome_ec_count']})
D['SubsystemRowV1'] = obj(**row_base(), **{k:ref('NumericCellV1') for k in ['reported_role_token_count',
    'reported_feature_token_count','reported_genome_count','reported_gene_conservation',
    'reported_role_conservation_percent','reported_record_genome_fraction']})
D['OverviewRowV1'] = obj(**row_base(), level=enum('superclass','class','subclass'),
    reported_subsystem_name_count=ref('NumericCellV1'),reported_feature_count=ref('NumericCellV1'))
D['VariantRowV1'] = obj(**row_base(), raw_tokens=arr(S), header_field_count=I, data_field_count=I,
    **{k:ref('NumericCellV1') for k in ['reported_active_occurrences','reported_likely_occurrences',
       'reported_inactive_placeholder','reported_missing_genome_count']})
D['DuplicateGroupV1'] = obj(group_id=ID, kind=enum('identical_record','conflicting_record','dependent_view'),
    members=arr(ref('CellReferenceV1')), native_unique_key=null(ID), affected_field_ids=arr(ID,True))
D['JoinResultV1'] = obj(join_id=ID, left_view_id=ID,right_view_id=ID,
    keys=arr(enum('genome_id','feature_id','patric_id','subsystem_id','role_id','pathway_id','ec_number'),True),
    join_kind=con('inner'), left_occurrence_count=ref('NumericCellV1'),
    right_occurrence_count=ref('NumericCellV1'),output_occurrence_count=ref('NumericCellV1'),
    unmatched_left_refs=arr(ref('CellReferenceV1')), unmatched_right_refs=arr(ref('CellReferenceV1')),
    multiplicity=enum('one_to_one','one_to_many','many_to_one','many_to_many','unknown'),
    qualification_codes=arr(ref('DiagnosticCodeV1'),True))
D['ReferenceMembershipV1'] = obj(membership_id=ID, component_kind=enum('ec_number','role_id'),
    entity=ref('EntityV1'), members=arr(ID), map_id=null(ID), release=null(S),
    completeness=ref('CompletenessV1'), basis=ref('BasisV1'), source_locations=arr(ref('SourceLocationV1')),
    qualification_codes=arr(ref('DiagnosticCodeV1'),True))
D['InputSelectionV1'] = {'oneOf':[
    obj(kind=con('requirement'),requirement_id=ID),
    obj(kind=con('possessed_artifact'),source_ref=ID,raw_artifact_ref=ID)]}
D['DocumentSelectionV1'] = obj(version=con('bvbrc_comparative_systems_document_selection_v1'),
    documents=arr(obj(document_id=ID, role=ref('RoleV1'),format_profile=D['SourceDocumentV1']['properties']['format_profile'],
        producer_evidence_id=null(ID),input=ref('InputSelectionV1'))),
    authoritative_views=arr(obj(view_id=ID,document_id=ID,table=ref('TableV1'))),
    dependent_views=arr(obj(left_view_id=ID,right_view_id=ID)))
D['PopulationAssignmentsV1'] = obj(version=con('bvbrc_comparative_systems_population_assignments_v1'),
    assignments=arr(obj(population_id=ID,kind=enum('requested_direct_genomes','executed_genomes',
        'native_view_represented_genomes','native_retained_records','selected_component_membership'),
        view_id=null(ID),entity=null(ref('EntityV1')),component_kind=null(enum('ec_number','role_id','family_id')))))

# Exact existing Data QualifiedResult transitive shapes, namespaced without scientific changes.
data = json.loads((BASE/'DATA_QUALIFIED_RESULT_SCHEMA_001.json').read_text())
def prefix(x):
    if isinstance(x,list): return [prefix(a) for a in x]
    if isinstance(x,dict): return {k:('#/$defs/Data__'+v[len('#/$defs/'):] if k=='$ref' and v.startswith('#/$defs/') else prefix(v)) for k,v in x.items()}
    return x
for name, definition in data['$defs'].items(): D['Data__'+name]=prefix(definition)
D['QualifiedDataInputV1'] = obj(qualified_result=ref('Data__QualifiedResult'),
    raw_binding=obj(source_ref=ID,raw_artifact_ref=ID,sha256=SHA,byte_count=I,bytes_key=ID))
D['SnapshotEvidenceV1'] = obj(kind=enum('single_complete_response','immutable_snapshot','unknown'),
    snapshot_id=null(ID), source_locations=arr(ref('SourceLocationV1')))
D['DataPopulationSelectionV1'] = obj(version=con('bvbrc_comparative_systems_data_selection_v1'),
    record_sets=arr(obj(record_set_id=ID,collection=enum('genome','genome_feature','pathway','subsystem',
        'protein_family_ref','pathway_ref','subsystem_ref'), source_refs=arr(ID,True),
        declared_genome_population=ref('PopulationV1'),
        query_population_key=SHA, selected_fields=arr(ref('Data__Field'),True),sort=arr(ref('Data__Sort')),
        annotation_filter=enum('exact_PATRIC','none'),
        relationship_to_original_task=enum('original_execution_snapshot','later_selected_snapshot','unverified'),
        snapshot_evidence=ref('SnapshotEvidenceV1'), release=null(S), roles=arr(ref('RoleV1'),True))))
D['SuppliedRecordV1'] = obj(record_set_id=ID, source_ref=ID,native_sha256=SHA,page_row_key=ID,
    native_unique_key=null(ID),native_row=ref('Data__NativeRow'), association=null(ref('AssociationRowV1')),
    filter_state=enum('included','excluded_by_explicit_filter','filter_undetermined'),
    duplicate_state=enum('unique','identical_repeat','conflicting_repeat'),qualification_codes=arr(ref('DiagnosticCodeV1'),True))
D['PageEvidenceV1'] = obj(binding=ref('Data__ResultBinding'),requested_offset=I,response_start=null(I),
    returned_row_count=I,reported_total=null(I),num_found_exact=null(B),
    body_complete=B,partial_results=null(B),snapshot_evidence=ref('SnapshotEvidenceV1'))
D['SuppliedRecordSetV1'] = obj(record_set_id=ID,collection=D['DataPopulationSelectionV1']['properties']['record_sets']['items']['properties']['collection'],
    population=ref('PopulationV1'),pages=arr(ref('PageEvidenceV1')),rows=arr(ref('SuppliedRecordV1')),
    annotation_filter=enum('exact_PATRIC','none'),page_coverage=enum('complete','partial','unknown','incompatible'),
    snapshot_consistency=enum('single_response','proven_same_snapshot','unknown','conflicting'),
    original_query_record_count=ref('NumericCellV1'),locally_included_record_count=ref('NumericCellV1'))
D['SuppliedRecordSetsV1'] = obj(version=con('bvbrc_comparative_systems_supplied_records_v1'),
    selection=ref('DataPopulationSelectionV1'),record_sets=arr(ref('SuppliedRecordSetV1')),
    requirements=arr(ref('RequirementV1')),diagnostics=arr(ref('DiagnosticV1')))
D['ComparativeSystemsSheetV1'] = obj(version=con('bvbrc_comparative_systems_sheet_v1'),analysis_id=ID,
    original_request=ref('OriginalRequestV1'),source_documents=arr(ref('SourceDocumentV1')),
    producer_evidence=arr(ref('ProducerEvidenceV1')),populations=arr(ref('PopulationV1')),
    document_selection=ref('DocumentSelectionV1'),population_assignments=ref('PopulationAssignmentsV1'),native_documents=arr(ref('NativeDocumentResultV1')),
    family_rows=arr(ref('FamilyRowV1')),pathway_rows=arr(ref('PathwayRowV1')),
    pathway_ec_rows=arr(ref('PathwayECRowV1')),subsystem_rows=arr(ref('SubsystemRowV1')),
    association_rows=arr(ref('AssociationRowV1')),overview_rows=arr(ref('OverviewRowV1')),
    variant_rows=arr(ref('VariantRowV1')),supplied_record_sets=null(ref('SuppliedRecordSetsV1')),
    reference_memberships=arr(ref('ReferenceMembershipV1')),duplicate_groups=arr(ref('DuplicateGroupV1')),
    join_results=arr(ref('JoinResultV1')),requirements=arr(ref('RequirementV1')),diagnostics=arr(ref('DiagnosticV1')))
quantities = '''family_returned_genome_occupancy family_record_genome_occupancy family_occurrences_per_positive_genome
family_length_cv pathway_retained_ec_occupancy_percent pathway_retained_feature_density
pathway_record_ec_occupancy_percent pathway_record_feature_density
subsystem_retained_role_occupancy_percent subsystem_retained_feature_density
subsystem_record_role_occupancy_percent subsystem_record_feature_density subsystem_explicit_category_genome_count
observed_family_set_intersection_count observed_family_set_union_count observed_family_set_jaccard
reference_component_representation reported_formula_check'''.split()
D['QuantityV1'] = enum(*quantities)
D['ViewSelectionV1'] = obj(kind=enum('native_view','supplied_record_set'),view_id=null(ID),record_set_id=null(ID))
D['ComponentRequestV1'] = obj(component_id=ID, quantity=ref('QuantityV1'),entity=ref('EntityV1'),
    view_selection=ref('ViewSelectionV1'),population_id=ID,family_kind=null(enum('plfam','pgfam')),
    comparison_genome_ids=null({'type':'array','items':ID,'minItems':2,'maxItems':2,'uniqueItems':True}),
    reference_membership_id=null(ID),category=null(enum('active','likely','inactive')),
    native_formula=null(enum('pathway_ec_conservation','pathway_gene_conservation','subsystem_role_conservation','subsystem_gene_conservation','subsystem_prop_active')))
D['CalculationParametersV1'] = obj(version=con('bvbrc_comparative_systems_calculation_parameters_v1'),
    requests=arr(ref('ComponentRequestV1')),duplicate_policy=con('preserve_native_occurrences_and_deduplicate_identical_record_ids'),
    absolute_tolerance=N,relative_tolerance=N)
D['RatioComponentV1'] = obj(numerator=ref('NumericCellV1'),denominator=ref('NumericCellV1'),
    scale={'enum':[1,100]},output=ref('NumericCellV1'),genome_population_id=null(ID),component_population_id=null(ID))
D['CalculatedComponentV1'] = obj(component_id=ID,quantity=ref('QuantityV1'),entity=ref('EntityV1'),
    value=ref('NumericCellV1'),ratio=null(ref('RatioComponentV1')),input_refs=arr(ref('CellReferenceV1')),
    population_ids=arr(ID,True),reference_membership_id=null(ID),qualification_codes=arr(ref('DiagnosticCodeV1'),True))
D['ComparativeSystemsComponentsV1'] = obj(version=con('bvbrc_comparative_systems_components_v1'),
    formula_version=con('bvbrc_comparative_systems_formulas_v1'),analysis_id=ID,sheet_sha256=SHA,
    parameters=ref('CalculationParametersV1'),components=arr(ref('CalculatedComponentV1')),
    requirements=arr(ref('RequirementV1')),diagnostics=arr(ref('DiagnosticV1')))
D['ProviderParametersV1'] = obj(analysis_id=ID,document_selection=ref('DocumentSelectionV1'),
    population_assignments=ref('PopulationAssignmentsV1'),
    producer_evidence_selections=arr(obj(evidence_id=ID,source_ref=ID,raw_artifact_ref=ID,record_path=PTR)),
    supplied_data_selection=null(ref('DataPopulationSelectionV1')),
    reference_memberships=arr(ref('ReferenceMembershipV1')),calculation_parameters=ref('CalculationParametersV1'))
D['NativeMeasurementFieldV1'] = enum(*sorted(set(k for name in ['FamilyRowV1','PathwayRowV1','PathwayECRowV1','SubsystemRowV1','OverviewRowV1','VariantRowV1']
    for k,v in D[name]['properties'].items() if v==ref('NumericCellV1'))))
D['FactSelectorV1'] = {'oneOf':[
    obj(kind=con('measurement'),view_id=ID,entity=ref('EntityV1'),native_field=ref('NativeMeasurementFieldV1')),
    obj(kind=con('computed_measurement'),component_id=ID),
    obj(kind=con('ratio'),component_id=ID),obj(kind=con('population'),population_id=ID),
    obj(kind=con('membership'),entity=ref('EntityV1'),genome_id=null(ID),member_id=ID,population_id=ID),
    obj(kind=con('requirement'),required_input_role=ref('RoleV1')),
    obj(kind=con('qualification'),code=ref('DiagnosticCodeV1')),
    obj(kind=con('request_status'))]}
D['RequestedFieldV1'] = obj(field_id=ID,selector=ref('FactSelectorV1'),expected_cardinality=I,
    availability_requirement=enum('typed_state','available_value','available_complete_population'))
D['RequestedSelectionV1'] = obj(version=con('bvbrc_comparative_systems_requested_selection_v1'),fields=arr(ref('RequestedFieldV1')))
D['MembershipFactV1'] = obj(entity=ref('EntityV1'),genome_id=null(ID),member_id=ID,
    population_id=ID,presence_state=D['GenomeFamilyCountV1']['properties']['presence_state'],source_locations=arr(ref('SourceLocationV1')))
D['PopulationFactV1'] = obj(population_id=ID,kind=D['PopulationV1']['properties']['kind'],
    raw_occurrence_count=ref('NumericCellV1'),distinct_valid_member_count=ref('NumericCellV1'),
    completeness=ref('CompletenessV1'),qualification_codes=arr(ref('DiagnosticCodeV1'),True))
D['FactValueV1'] = {'oneOf':[ref('NumericCellV1'),ref('RatioComponentV1'),
    ref('PopulationFactV1'),ref('MembershipFactV1'),ref('RequirementV1'),ref('DiagnosticV1'),
    obj(status=enum('satisfied','partial','invalid','unavailable'),affected_field_ids=arr(ID,True))]}
D['ProjectedFieldV1'] = obj(field_id=ID,values=arr(ref('FactValueV1')),status=enum('satisfied','partial','invalid','unavailable'))
D['ProviderFactsV1'] = {'type':'object','propertyNames':ID,'additionalProperties':ref('ProjectedFieldV1')}
D['RequestedFactV1'] = obj(source_ref=ID,field=ID,value=ref('ProjectedFieldV1'))
D['RequestedFactsV1'] = obj(version=con('bvbrc_comparative_systems_requested_facts_v1'),
    facts=ref('ProviderFactsV1'),status=enum('satisfied','partial','invalid','unavailable'),
    missing_requirements=arr(ref('RequirementV1')),diagnostics=arr(ref('DiagnosticV1')))
D['ProviderResultV1'] = obj(adapter_id=con('bvbrc_comparative_systems'),adapter_version=con('1'),
    status=enum('ok','partial','invalid'),sheet=null(ref('ComparativeSystemsSheetV1')),
    components=null(ref('ComparativeSystemsComponentsV1')),facts=ref('ProviderFactsV1'),
    missing_requirements=arr(ref('RequirementV1')),diagnostics=arr(ref('DiagnosticV1')))

schema={'$schema':'https://json-schema.org/draft/2020-12/schema',
    '$id':'urn:gene-annotation:review:comparative-systems:handoffs:001',
    '$comment':'Review-only proposal. Shape validation never confers custody, scientific completeness, or live provenance. See SCHEMA_DECISIONS_001.md for relational invariants.',
    '$ref':'#/$defs/ComparativeSystemsSheetV1','$defs':D}
(BASE/'HANDOFF_SCHEMAS_001.json').write_text(json.dumps(schema,indent=2,allow_nan=False)+'\n')
print(json.dumps({'schema_definitions':len(D),'output':'HANDOFF_SCHEMAS_001.json'}))
