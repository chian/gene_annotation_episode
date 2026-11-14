"""Original pure saved-schema initialization; no providers or native actions."""
from importlib import import_module
import pytest
from jsonschema import Draft202012Validator

AXES=('a101','a105','a106','a108')
BLAST_NAMES={'blast_program_context','blast_utility_contracts','blast_utility_result_views','native_blast_utility_contracts','native_hmmer_contracts','native_hmmer_preparation_contracts'}
def owner(axis,name):
    base='gene_annotation_episode.episodic_workflow.root.'+axis+'.'
    return import_module(base + ('library.' if axis == 'a101' and name in BLAST_NAMES else 'library.retained_input_authority.') + name)

@pytest.mark.parametrize('axis',AXES)
@pytest.mark.parametrize('program,query,reported',[('psiblast','pssm','psiblast'),('psiblast','msa','psiblast'),('tblastn','pssm','psitblastn')])
def test_original_blast_query_geometry_and_invalid_kind(axis,program,query,reported):
    module=owner(axis,'blast_program_context')
    args=dict(execution_program=program,reported_program=reported,scientific_mode='database',query_kind=query,reference_kind='sequence',native_version=None)
    result=module.resolve_blast_program_context(**args)
    assert result['query_kind']==query and result['reported_program']==reported
    assert result['geometry_program']==('tblastn' if program=='tblastn' else 'blastp')
    with pytest.raises(ValueError,match='blast_program_query_kind_conflict'):
        module.resolve_blast_program_context(**{**args,'query_kind':'unsupported_fixture_kind'})

@pytest.mark.parametrize('axis',AXES)
def test_blast_saved_version_schema_registry_and_view_identity(axis):
    module=owner(axis,'blast_utility_contracts')
    assert {'PreparationDocument','ParameterObservation','MaterializationReceipt','VDBUtilityContext','VDBMember'}<=module.SCHEMAS.keys()
    assert module.SCHEMAS['Operation']['anyOf'][1]==module._VDB_SCHEMAS['Operation']
    assert module.SCHEMAS['Operation']['anyOf'][0]['anyOf'][1]==module._NEW_SCHEMAS['Operation']
    assert module.SCHEMAS['ArtifactOccurrence']==module._VDB_SCHEMAS['ArtifactOccurrence']
    assert module.SCHEMAS['NativeField']['anyOf']==[*module._FIELD['anyOf'],*module._VDB_SCHEMAS['NativeField']['anyOf']]
    views=owner(axis,'blast_utility_result_views')
    assert views.ARTIFACT_SCHEMA['properties']['occurrence_id']==views._OCCURRENCE
    assert views.ARTIFACT_SCHEMA['properties']['artifact_ref']==views._ARTIFACT
    assert 'description' in views._SLOT_SCHEMA['properties']['ordinal']

@pytest.mark.parametrize('axis',AXES)
def test_native_blast_retained_version_fields_and_conditional_argv(axis):
    module=owner(axis,'native_blast_utility_contracts')
    assert 'realized_token' not in module._ENTRY['properties'] and 'realized_token' not in module._ENTRY['required']
    assert module.INPUT_SCHEMA_V3['properties']['role']=={'enum':['entry_batch','database_list']}
    assert module.INPUT_SCHEMA_V3['properties']['format']=={'const':'text'}
    assert {'sequence_input','taxid_map','identifier_list'}<=set(module.INPUT_SCHEMA_V2['properties']['role']['enum'])
    assert 'gi_list_binary' in module.INPUT_SCHEMA_V2['properties']['format']['enum']
    schema={'allOf':module.NATIVE_BLAST_UTILITY_REQUESTED_JOB_SCHEMA['allOf']}
    validator=Draft202012Validator(schema)
    assert validator.is_valid({'native_blast_utility':{'version':module.JOB_VERSION},'argv':['tool']})
    assert not validator.is_valid({'native_blast_utility':{'version':module.JOB_VERSION},'argv':['']})
    assert all(module.FAILURE_STAGES[code]=='execution' for code in module.OFFLINE_FAILURE_CODES)

@pytest.mark.parametrize('axis',AXES)
def test_hmmer_original_program_modes_and_calibration_domain(axis):
    module=owner(axis,'native_hmmer_contracts')
    validator=Draft202012Validator({'allOf':module.NATIVE_HMMER_JOB_SCHEMA['allOf']})
    assert validator.is_valid({'program':'nhmmer','mode':'alignment'})
    assert validator.is_valid({'program':'hmmalign','mode':'align'})
    assert not validator.is_valid({'program':'hmmalign','mode':'search'})
    prep=owner(axis,'native_hmmer_preparation_contracts')
    assert {key:prep.FORMAT_ARGUMENTS[key] for key in ('stockholm','pfam','afa','a2m','clustal','phylip')}==dict(stockholm='Stockholm',pfam='Pfam',afa='AFA',a2m='A2M',clustal='Clustal',phylip='PHYLIP')
    assert prep._CALIBRATION['--Eft']=='open_fraction'
    assert prep._number('0.04',prep._CALIBRATION['--Eft'],'--Eft')==0.04
    with pytest.raises(ValueError,match='invalid_option_operand'):
        prep._number('0',prep._CALIBRATION['--Eft'],'--Eft')

@pytest.mark.parametrize('axis',AXES)
def test_fluorescence_saved_format_scaling_and_native_comparison_schema(axis):
    result=owner(axis,'fluorescence_result_contracts')
    file={'artifact_ref':'artifact_'+'a'*64,'sha256':'a'*64,'size_bytes':0,'format':result.core.SHEET_SCHEMA}
    validator=Draft202012Validator(result.SAVED_FILE_SCHEMA)
    assert validator.is_valid(file)
    assert not validator.is_valid({**file,'format':'unrelated_scientific_sheet'})
    assert result.DOMAIN_CONTEXT_SCHEMA['properties']['scaling']==result.PREPARATION_SCHEMA
    native=owner(axis,'native_fluorescence_contracts')
    assert native.DOMAIN_SCHEMA['properties']['scaling']==native.PREPARATION_SCHEMA
    assert native.JOB_V2_SCHEMA['properties']['version']=={'const':'native_fluorescence_job_v2'}
    assert set(native.JOB_V2_SCHEMA['required'])==set(native.JOB_V2_SCHEMA['properties'])
    requests=native.JOB_V2_SCHEMA['properties']['parameters']['properties']['native_comparison_requests']
    assert Draft202012Validator(requests).is_valid(['comparison-original'])
    assert not Draft202012Validator(requests).is_valid(['comparison-original','comparison-original'])
    reports=owner(axis,'fluorescence_native_report_contracts')
    assert reports.PROFILE_SOURCES[reports.CYTOKINE_CSV_PROFILE]==reports.PROFILE_SOURCES[reports.CYTOKINE_LOG_PROFILE]
    assert reports.PROFILE_SOURCES[reports.CYTOKINE_CSV_PROFILE] is not reports.PROFILE_SOURCES[reports.CYTOKINE_LOG_PROFILE]

@pytest.mark.parametrize('axis',AXES)
def test_reference_edit_schema_keeps_descriptive_denominators(axis):
    module=owner(axis,'reference_edit_outcomes')
    assert module._EVENT['description']=='One retained substitution/deletion column or existing contiguous insertion run; not a normalized variant or repair event.'
    props=module._POPULATION['properties']['categories']['items']['properties']
    assert props['fraction_of_classified']['description']=='Category occurrences divided by full-global classified pair occurrences; zero denominator remains null.'
    assert props['observed_fraction_of_declared']['description']=='Observed category occurrences divided by all declared pair occurrences; unclassified occurrences contribute only to the denominator, not inferred absence.'
