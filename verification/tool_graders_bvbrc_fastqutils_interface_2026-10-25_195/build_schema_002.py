"""Build the additive contract asset. No parser, calculator or runtime code.

The original193 schema remains immutable; this emits its complete v2 successor
and a frozen copy of the existing generic host contracts under Host_* names.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BASE = ROOT / 'verification/tool_graders_bvbrc_fastqutils_contract_2026-10-25_193'
old = json.loads((BASE / 'SCHEMAS_001.json').read_text())
host = json.loads((ROOT / 'gene_annotation_episode/bvbrc_appservice_schemas.json').read_text())
D = deepcopy(old['$defs'])

def ref(name): return {'$ref': '#/$defs/' + name}
def arr(item, **kw): return {'type': 'array', 'items': item, **kw}
def obj(props, **kw): return {'type': 'object', 'properties': props, 'required': list(props), 'additionalProperties': False, **kw}
def en(*values): return {'type': 'string', 'enum': list(values)}
def nullable(s): return {'anyOf': [s, {'type': 'null'}]}
def const(value): return {'const': value}
def add(name, **props):
    D[name]['properties'].update(props)
    D[name]['required'] += list(props)
def rename_refs(v):
    if isinstance(v, dict):
        return {k: ('#/$defs/Host_' + x.removeprefix('#/$defs/') if k == '$ref' and x.startswith('#/$defs/') else rename_refs(x)) for k,x in v.items()}
    if isinstance(v, list): return [rename_refs(x) for x in v]
    return v
for name,value in host['$defs'].items(): D['Host_' + name] = rename_refs(value)

STR = {'type': 'string'}
TEXT = {'type': 'string', 'minLength': 1}
TOKEN = {'type': 'string', 'pattern': '^[A-Za-z][A-Za-z0-9_.-]{0,127}$'}
REF = {'type': 'string', 'minLength': 1}
UINT = {'type': 'integer', 'minimum': 0}
NUMBER = {'type': 'number'}
SHA = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
POINTER = {'type': 'string', 'pattern': '^(?:/(?:[^~/]|~[01])*)*$'}
INPUT_POINTER = {'type': 'string', 'pattern': '^/(paired_end_libs|single_end_libs|srr_libs)/(0|[1-9][0-9]*)$'}
STATE = deepcopy(D['Cell']['properties']['state'])
METRIC = deepcopy(D['Cell']['properties']['metric'])
COMPONENT_METRIC = deepcopy(D['Component']['properties']['metric'])
FORMAT = deepcopy(D['Artifact']['properties']['declared_format'])
METHOD = deepcopy(D['Component']['properties']['method'])
UNIT = deepcopy(D['Cell']['properties']['unit'])
MATE = deepcopy(D['Association']['properties']['mate'])
BRANCH = deepcopy(D['Association']['properties']['branch'])
PAIR_RULE = en('exact_title', 'first_token', 'first_token_slash_mate', 'fastq_pair_0_3')
extra_codes = ['selection_ambiguous', 'selection_cardinality_mismatch', 'metadata_binding_missing',
    'metadata_value_conflict', 'encoding_declaration_conflict', 'explicit_encoding_assumption',
    'lineage_asserted_only', 'native_report_local_lineage', 'trim_pair_counter_mixed',
    'source_row_absent', 'document_identity_conflict', 'native_header_conflict', 'record_boundary_invalid',
    'supplied_version_assumption', 'saved_relationship_conflict', 'explicit_lineage_assumption']
CODES = deepcopy(D['Diagnostic']['properties']['code'])
CODES['enum'] += extra_codes
for name in ('Diagnostic',): D[name]['properties']['code'] = CODES
for name in ('Cell', 'Component'): D[name]['properties']['diagnostic_codes']['items'] = CODES
D['Requirement']['properties']['code'] = CODES
D['Requirement']['properties']['required_data']['enum'] += ['selected_document', 'source_bound_metadata', 'exact_source_cardinality']
D['ContractFailure'] = obj({'code': en('shape_invalid', 'nonfinite_json', 'reference_invalid',
    'duplicate_identity', 'binding_conflict', 'requested_form_invalid', 'saved_relationship_conflict',
    'saved_hash_conflict', 'unsupported_contract_version'), 'path': POINTER,
    'source_refs': arr(REF, uniqueItems=True), 'affected_refs': arr(REF, uniqueItems=True)})

# Artifact selection is commissioned before acquisition or names exact possessed bytes.
D['ArtifactSelection'] = {'oneOf': [
    obj({'kind': const('output_requirement'), 'requirement_id': TOKEN}),
    obj({'kind': const('possessed_content'), 'content': ref('Host_ContentBinding')})]}
D['DocumentBinding'] = obj({'document_id': TOKEN, 'selection': ref('ArtifactSelection'),
    'format': FORMAT, 'producer_version': nullable(TEXT)})
D['ResolvedDocument'] = obj({'document_id': TOKEN, 'selection': ref('ArtifactSelection'),
    'state': en('available', 'missing', 'ambiguous', 'incompatible'),
    'matched_contents': arr(ref('Host_ContentBinding')),
    'artifact_ref': nullable(REF), 'requirement_refs': arr(REF), 'diagnostic_codes': arr(CODES)})
D['ParseContext'] = obj({'analysis_id': TOKEN, 'document_id': TOKEN, 'task_ref': REF,
    'content': ref('Host_ContentBinding'), 'native_name': nullable(TEXT),
    'declared_format': FORMAT, 'producer_version': nullable(TEXT),
    'transfer_scope': en('complete', 'partial', 'unknown'),
    'identity': deepcopy(D['Artifact']['properties']['identity'])})
add('Artifact', document_id=TOKEN, content_binding=ref('Host_ContentBinding'))

section_keys = ['fastq_records', 'fastq_summary', 'bam_header', 'bam_records', 'bam_summary',
    'fastqc_basic_statistics', 'fastqc_per_base_quality', 'fastqc_per_tile_quality',
    'fastqc_per_sequence_quality', 'fastqc_per_base_content', 'fastqc_per_sequence_gc',
    'fastqc_per_base_n', 'fastqc_length_distribution', 'fastqc_duplication',
    'fastqc_overrepresented', 'fastqc_adapter_content', 'fastqc_kmer_content',
    'trim_summary', 'trim_pair_validation', 'trim_configuration', 'trim_adapter_detection',
    'cutadapt_embedded', 'fastq_pair_summary', 'hostile_report', 'unsupported']
SECTION = en(*section_keys)
pop_keys = ['fastq_reads', 'fastq_bases', 'fastq_quality_characters', 'verified_read_pairs',
    'bam_records', 'bam_primary_records', 'bam_quality_bases', 'fastqc_module',
    'trim_processed', 'trim_removed_short', 'trim_removed_n', 'trim_removed_long',
    'trim_pairs_in', 'trim_pairs_removed', 'fastq_pair_left_paired', 'fastq_pair_right_paired',
    'fastq_pair_left_single', 'fastq_pair_right_single', 'hostile_in', 'hostile_out', 'hostile_removed']
POP_KEY = en(*pop_keys)
D['NativeSection'] = obj({'key': SECTION, 'ordinal': UINT, 'locator': ref('Locator'),
    'state': en('complete', 'partial', 'absent', 'unsupported', 'malformed'),
    'cell_refs': arr(REF), 'category_refs': arr(REF), 'label_refs': arr(REF), 'raw_block_ordinals': arr(UINT)})
D['NativeLabel'] = obj({'id': REF, 'artifact_ref': REF, 'locator': ref('Locator'),
    'kind': en('filename', 'encoding_inference', 'producer_version', 'adapter', 'possible_source',
        'reference', 'aligner', 'option', 'command', 'path', 'native_label'), 'value': STR})
D['HeaderField'] = obj({'tag': TEXT, 'native_value': STR})
D['AlignmentHeader'] = obj({'id': REF, 'artifact_ref': REF, 'ordinal': UINT,
    'record_type': en('HD', 'SQ', 'RG', 'PG', 'CO', 'unrecognized'),
    'fields': arr(ref('HeaderField')), 'comment': nullable(STR), 'locator': ref('Locator')})
D['ReferenceEntry'] = obj({'ordinal': UINT, 'name': TEXT, 'length': UINT,
    'header_ref': nullable(REF), 'md5': nullable(TEXT)})
for name in ('Cell', 'Category', 'NativeLabel'):
    add(name, section_key=SECTION, section_ordinal=UINT)

# A source-bound declaration is an explicit assumption, never an attestation.
D['EncodingDeclaration'] = obj({'version': const('fastqutils_encoding_declaration_v1'),
    'document_id': TOKEN, 'encoding': en('phred33', 'phred64'), 'basis': const('explicit_assumption')})
D['EncodingBasis'] = obj({'basis': en('unknown', 'explicit_source_bound_declaration', 'native_bam_phred'),
    'encoding': en('unknown', 'phred33', 'phred64', 'bam_phred'),
    'metadata_id': nullable(TOKEN), 'evidence': nullable(ref('Host_SourceEvidence')),
    'declaration': nullable(ref('EncodingDeclaration')), 'native_locator': nullable(ref('Locator'))})
add('Population', document_ids=arr(TOKEN, uniqueItems=True), population_key=POP_KEY,
    population_ordinal=UINT, section_key=nullable(SECTION), section_ordinal=nullable(UINT),
    encoding_basis=ref('EncodingBasis'))
D['NativeLineage'] = obj({'id': REF, 'kind': en('native_report_before_after', 'observed_record_correspondence'),
    'before_population_ref': REF, 'after_population_ref': REF,
    'document_ids': arr(TOKEN, minItems=1, uniqueItems=True), 'source_refs': arr(REF, minItems=1),
    'locators': arr(ref('Locator'), minItems=1),
    'scope': const('artifact_local'), 'task_stage_ref': const(None)})
D['NativeDocument']['properties']['schema_version'] = const('fastqutils_native_v2')
add('NativeDocument', analysis_id=TOKEN, document_id=TOKEN,
    sections=arr(ref('NativeSection')), labels=arr(ref('NativeLabel')),
    populations=arr(ref('Population')), native_lineage=arr(ref('NativeLineage')),
    alignment_headers=arr(ref('AlignmentHeader')), reference_dictionary=arr(ref('ReferenceEntry')),
    requirements=arr(ref('Requirement')))

D['LibraryAnnotation'] = obj({'version': const('fastqutils_library_annotation_v1'),
    'input_pointer': INPUT_POINTER, 'sample_ref': nullable(REF), 'condition_ref': nullable(REF),
    'replicate_ref': nullable(REF), 'platform': deepcopy(D['Library']['properties']['platform'])})
D['AssociationAssertion'] = obj({'version': const('fastqutils_association_assertion_v1'),
    'document_id': TOKEN, 'input_pointer': INPUT_POINTER, 'recipe_ordinal': nullable(UINT),
    'mate': MATE, 'branch': BRANCH, 'basis': const('explicit_assertion')})
D['PairDeclaration'] = obj({'version': const('fastqutils_pair_declaration_v1'),
    'left_document_id': TOKEN, 'right_document_id': TOKEN, 'pair_key_rule': PAIR_RULE})
D['ReferenceDeclaration'] = obj({'version': const('fastqutils_reference_declaration_v1'),
    'document_id': TOKEN, 'reference_identifier': TEXT, 'reference_sha256': nullable(SHA),
    'completeness': en('declared_complete', 'declared_partial', 'unknown'), 'basis': const('explicit_assertion')})
D['LineageDeclaration'] = obj({'version': const('fastqutils_lineage_declaration_v1'),
    'before': ref('PopulationSelector'), 'after': ref('PopulationSelector'),
    'relation': en('successor_population', 'subset_population', 'same_population'),
    'basis': const('explicit_assumption')})
D['LineageBasis'] = obj({'basis': en('native_report', 'observed_record_correspondence',
    'explicit_source_bound_declaration', 'unknown'), 'metadata_id': nullable(TOKEN),
    'evidence': nullable(ref('Host_SourceEvidence')), 'declaration': nullable(ref('LineageDeclaration')),
    'native_lineage_ref': nullable(REF)})
metadata_kinds = {'encoding_declaration': 'EncodingDeclaration', 'library_annotation': 'LibraryAnnotation',
    'association_assertion': 'AssociationAssertion', 'pair_declaration': 'PairDeclaration',
    'reference_declaration': 'ReferenceDeclaration', 'lineage_declaration': 'LineageDeclaration'}
D['MetadataBinding'] = obj({'metadata_id': TOKEN, 'kind': en(*metadata_kinds), 'evidence': ref('Host_SourceEvidence')})
D['SuppliedValue'] = obj({'evidence': ref('Host_SourceEvidence'), 'value': ref('Host_Json')})
D['SelectedMetadata'] = {'oneOf': [obj({'metadata_id': TOKEN, 'kind': const(kind),
    'evidence': ref('Host_SourceEvidence'), 'value': ref(definition)}) for kind,definition in metadata_kinds.items()]}
D['MetadataInputs'] = obj({'analysis_id': TOKEN, 'original_task': ref('Host_OriginalTask'),
    'bindings': arr(ref('MetadataBinding')), 'supplied_values': arr(ref('SuppliedValue'))})
add('Library', submitted_value=ref('Host_Json'), metadata_ids=arr(TOKEN))
add('Stage', request_pointer=POINTER, requested_reference_genome_id=nullable(TEXT))
add('Association', basis=en('original_input_binding', 'explicit_assertion', 'observed_record_correspondence'),
    metadata_ids=arr(TOKEN), document_ids=arr(TOKEN, uniqueItems=True))
D['Metadata']['properties']['schema_version'] = const('fastqutils_metadata_v2')
D['Metadata']['required'].append('schema_version')
add('Metadata', analysis_id=TOKEN, original_task=ref('Host_OriginalTask'),
    supplied_metadata=arr(ref('SelectedMetadata')), native_lineage=arr(ref('NativeLineage')),
    measurements=arr(ref('Cell')))
D['Sheet']['properties']['schema_version'] = const('fastqutils_sheet_v2')
add('Sheet', analysis_id=TOKEN, original_task=ref('Host_OriginalTask'),
    document_resolutions=arr(ref('ResolvedDocument')), supplied_metadata=arr(ref('SelectedMetadata')),
    native_lineage=arr(ref('NativeLineage')))

# Closed semantic selectors do not require hashes or parser-generated identifiers.
D['RowSelector'] = {'oneOf': [obj({'kind': const('all')}), obj({'kind': const('ordinal'), 'ordinal': UINT})]}
D['AxisSelector'] = {'oneOf': [obj({'kind': const('all')}), obj({'kind': const('exact'), 'axis': ref('Axis')})]}
D['MeasurementSelector'] = {'oneOf': [
    obj({'selection': const('record'), 'record_ref': REF}),
    obj({'selection': const('semantic'), 'document_id': TOKEN, 'section_key': SECTION,
        'section_ordinal': UINT, 'metric': METRIC, 'rows': ref('RowSelector'), 'axis': ref('AxisSelector')})]}
D['CategorySelector'] = {'oneOf': [
    obj({'selection': const('record'), 'record_ref': REF}),
    obj({'selection': const('semantic'), 'document_id': TOKEN, 'section_key': SECTION, 'section_ordinal': UINT})]}
D['PopulationSelector'] = {'oneOf': [
    obj({'selection': const('record'), 'record_ref': REF}),
    obj({'selection': const('semantic'), 'document_id': TOKEN, 'population_key': POP_KEY,
        'population_ordinal': UINT})]}
D['AssociationSelector'] = {'oneOf': [
    obj({'selection': const('record'), 'record_ref': REF}),
    obj({'selection': const('semantic'), 'document_id': TOKEN, 'input_pointer': INPUT_POINTER,
        'recipe_ordinal': nullable(UINT), 'mate': MATE, 'branch': BRANCH})]}
D['ComponentSelector'] = {'oneOf': [
    obj({'selection': const('record'), 'record_ref': REF}),
    obj({'selection': const('semantic'), 'calculation_id': TOKEN, 'metric': COMPONENT_METRIC,
        'threshold': nullable({'type': 'integer', 'minimum': 0, 'maximum': 93})})]}

common_calc = {'calculation_id': TOKEN}
D['CalculationRequest'] = {'oneOf': [
    obj({**common_calc, 'method': const('composition_v1'), 'population': ref('PopulationSelector')}),
    obj({**common_calc, 'method': const('quality_phred_v1'), 'population': ref('PopulationSelector'),
        'quality_thresholds': arr({'type': 'integer', 'minimum': 0, 'maximum': 93}, uniqueItems=True)}),
    obj({**common_calc, 'method': const('retention_v1'),
        'comparison_kind': en('read_retention', 'base_retention', 'pair_retention', 'native_report_retention'),
        'before_population': ref('PopulationSelector'), 'after_population': ref('PopulationSelector'),
        'before_measurement': ref('MeasurementSelector'), 'after_measurement': ref('MeasurementSelector')}),
    obj({**common_calc, 'method': const('mapping_v1'), 'population': ref('PopulationSelector'),
        'input_population': nullable(ref('PopulationSelector')), 'read_key_rule': nullable(PAIR_RULE)}),
    obj({**common_calc, 'method': const('report_consistency_v1'),
        'report_measurement': ref('MeasurementSelector'), 'observed_measurement': ref('MeasurementSelector')})]}
D['CalculationBinding'] = obj({'calculation_id': TOKEN, 'method': METHOD,
    'state': en('ready', 'unavailable', 'incompatible'), 'population_refs': arr(REF),
    'operand_measurement_refs': arr(REF), 'comparison_kind': nullable(en('read_retention', 'base_retention',
        'pair_retention', 'native_report_retention', 'report_count_consistency')),
    'quality_thresholds': arr({'type': 'integer', 'minimum': 0, 'maximum': 93}, uniqueItems=True),
    'read_key_rule': nullable(PAIR_RULE), 'lineage_ref': nullable(REF),
    'lineage_basis': nullable(ref('LineageBasis')),
    'requirement_refs': arr(REF), 'diagnostic_codes': arr(CODES)})
D['CalculatorParameters'] = obj({'version': const('fastqutils_calculators_v2'),
    'analysis_id': TOKEN, 'calculations': arr(ref('CalculationBinding'))})
add('Component', calculation_id=TOKEN, encoding_basis=nullable(ref('EncodingBasis')),
    lineage_basis=nullable(ref('LineageBasis')))
D['Components']['properties']['schema_version'] = const('fastqutils_components_v2')
add('Components', analysis_id=TOKEN)
D['ProviderParameters'] = obj({'version': const('fastqutils_provider_v2'), 'analysis_id': TOKEN,
    'documents': arr(ref('DocumentBinding'), minItems=1), 'metadata_bindings': arr(ref('MetadataBinding')),
    'calculation_requests': arr(ref('CalculationRequest'))})

families = {'measurement': 'MeasurementSelector', 'component': 'ComponentSelector',
    'category': 'CategorySelector', 'population': 'PopulationSelector', 'association': 'AssociationSelector'}
D['FactTarget'] = {'oneOf': [obj({'kind': const(k), 'selector': ref(v)}) for k,v in families.items()] + [
    obj({'kind': const('requirements')}), obj({'kind': const('request_status'), 'field': TOKEN})]}
D['FactSelection'] = obj({'target': ref('FactTarget'), 'cardinality': en('one_target', 'exact_rows'),
    'expected_cardinality': UINT, 'availability_requirement': en('typed_state', 'available_value')})
D['RequestedForm'] = obj({'version': const('fastqutils_projection_v2'), 'fields': arr(obj({
    'field': TOKEN, 'selection': ref('FactSelection')}), minItems=1)})

# Payloads contain actual records only. An absent category/population never supplies
# fake category values, population kinds, association identities or numerical zero.
payloads = {}
D['ProjectedAxis'] = obj({'kind': deepcopy(D['Axis']['properties']['kind']),
    'label_ref': nullable(REF), 'lower': nullable(NUMBER), 'upper': nullable(NUMBER)})
D['MeasurementPayload'] = obj({'measurement_ref': REF, 'document_id': TOKEN, 'quantity': METRIC,
    'axis': ref('ProjectedAxis'), 'state': STATE, 'value': nullable(NUMBER), 'unit': UNIT,
    'meaning': deepcopy(D['Cell']['properties']['meaning']), 'precision': deepcopy(D['Cell']['properties']['precision']),
    'population_ref': nullable(REF), 'association_ref': nullable(REF), 'native_token_ref': nullable(REF)})
D['ComponentPayload'] = obj({'component_ref': REF, 'calculation_id': TOKEN, 'quantity': COMPONENT_METRIC,
    **{key: deepcopy(D['Component']['properties'][key]) for key in ('state','value','unit','method',
        'population_refs','operand_measurement_refs','numerator','denominator','threshold','meaning',
        'uncertainty','parameter_sha256','encoding_basis','lineage_basis')}})
D['CategoryPayload'] = obj({'category_ref': REF, 'native_label_ref': REF,
    'value': deepcopy(D['Category']['properties']['value']), 'association_ref': nullable(REF)})
D['PopulationPayload'] = obj({'population_ref': REF, **{key: deepcopy(D['Population']['properties'][key])
    for key in ('kind','scope','representation','association_ref','member_artifact_refs',
        'parent_population_refs','quality_encoding','encoding_basis')}})
D['AssociationPayload'] = obj({'association_ref': REF, **{key: deepcopy(D['Association']['properties'][key])
    for key in ('library_ref','stage_ref','mate','branch','state','basis','artifact_refs')}})
for kind in ('measurement','component','category','population','association'):
    payloads[kind] = kind.title() + 'Payload'
payloads['requirements'] = 'RequirementsPayload'
payloads['request_status'] = 'RequestStatusPayload'
D['RequirementsPayload'] = obj({'requirements': arr(ref('Requirement'))})
D['RequestStatusPayload'] = obj({'field': TOKEN, 'satisfied': {'type': 'boolean'},
    'state': en('satisfied', 'missing_value', 'ambiguous', 'cardinality_mismatch', 'invalid'),
    'matched_count': UINT, 'requirement_refs': arr(REF)})
fact_state = en(*STATE['enum'], 'ambiguous')
D['FactRecord'] = {'oneOf': [obj({'kind': const(kind), 'record_ref': nullable(REF),
    'state': fact_state, 'payload': nullable(ref(definition)), 'source_refs': arr(REF, uniqueItems=True),
    'requirement_refs': arr(REF, uniqueItems=True), 'diagnostic_codes': arr(CODES, uniqueItems=True)})
    for kind,definition in payloads.items()]}
for kind in payloads:
    D[kind.title().replace('_','') + 'Fact'] = D['FactRecord']['oneOf'][list(payloads).index(kind)]
D['RequestStatusFact'] = D['FactRecord']['oneOf'][-1]
D['ProjectedField'] = obj({'selection': ref('FactSelection'), 'matched_count': UINT,
    'state': en('satisfied', 'missing_value', 'ambiguous', 'cardinality_mismatch', 'invalid'),
    'satisfied': {'type': 'boolean'}, 'records': arr(ref('FactRecord')),
    'requirement_refs': arr(REF, uniqueItems=True), 'diagnostic_codes': arr(CODES, uniqueItems=True)})
D['Facts'] = {'type': 'object', 'propertyNames': TOKEN, 'additionalProperties': ref('ProjectedField')}
D['ProjectionFailureContext'] = obj({'requirements': arr(ref('Requirement')), 'diagnostics': arr(ref('Diagnostic'))})
D['ProjectionResult'] = obj({'facts': ref('Facts'), 'status': en('ok', 'partial', 'invalid'),
    'requirements': arr(ref('Requirement')), 'diagnostics': arr(ref('Diagnostic')),
    'failure_context': ref('ProjectionFailureContext')})
D['SavedComponents'] = obj({'version': const('fastqutils_saved_components_v2'),
    'calculations': nullable(ref('Components')), 'projection_failure_context': ref('ProjectionFailureContext'),
    'native_requirements': arr(ref('Requirement')), 'native_diagnostics': arr(ref('Diagnostic'))})
D['ProviderResult'] = obj({'status': en('ok', 'partial', 'invalid'), 'facts': ref('Facts'),
    'missing_requirements': arr(ref('Host_AcquisitionRequirement')), 'diagnostics': arr(ref('Host_Diagnostic')),
    'sheet': nullable(ref('Sheet')), 'components': ref('SavedComponents')})
D['EncodedFailures'] = obj({'missing_requirements': arr(ref('Host_AcquisitionRequirement')),
    'diagnostics': arr(ref('Host_Diagnostic'))})
D['ReferenceParts'] = obj({'kind': en('document','artifact','cell','category','label','sequence','alignment',
    'header','population','library','stage','association','lineage','component','requirement','field'),
    'analysis_id': TOKEN, 'pointer': POINTER})

schema = {'$schema': 'https://json-schema.org/draft/2020-12/schema',
    '$id': 'urn:gene-annotation:fastqutils:interfaces:002',
    'description': 'Contract-only additive successor to193. No implementation or runtime verification claim.',
    '$defs': D}
(HERE / 'SCHEMAS_002.json').write_text(json.dumps(schema, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
print(json.dumps({'definitions': len(D), 'measurements': len(METRIC['enum']),
    'components': len(COMPONENT_METRIC['enum']), 'schema_sha256': hashlib.sha256((HERE/'SCHEMAS_002.json').read_bytes()).hexdigest()}))
