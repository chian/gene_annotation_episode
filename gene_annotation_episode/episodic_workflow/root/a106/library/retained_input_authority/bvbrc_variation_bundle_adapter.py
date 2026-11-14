"""Selected Variation VCF artifacts through the existing AppService owner.

VCF parsing and calculations belong to vcf_result_measurements. This adapter
joins the original task artifacts and caller selections to that authority;
saved reading copies its retained components without calling it again.
Per-library and annotated VCFs remain separate populations. Grouped all.var.tsv
is never substituted for original alleles, samples or native VCF headers.
"""
from copy import deepcopy
from jsonschema import Draft202012Validator
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority import vcf_result_measurements as vcf
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.bvbrc_annotation_contracts import selected_field_schema as _literal_schema
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.bvbrc_annotation_native import _canonical, _content, _finite_json
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.appservice_read_contracts import validate_contract
SELECTION_VERSION = 'bvbrc_variation_selection_v1'
VALUE_VERSION = 'bvbrc_variation_selected_field_v1'

def _require(condition, code='bvbrc_variation_bundle_invalid'):
    if not condition:
        raise ValueError(code)

def _object(properties):
    return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)

def _text():
    return dict(type='string', minLength=1)

def _validate(value, schema, code):
    _finite_json(value)
    try:
        Draft202012Validator(schema).validate(value)
    except Exception as error:
        raise ValueError(code) from error
    return deepcopy(value)

def selection_schema():
    result = vcf.vcf_result_schema('Selection')
    definitions = result.pop('$defs')
    return {**_object(dict(version=dict(const=SELECTION_VERSION), document_id=_text(), vcf=result)), '$defs': definitions}

def validate_selection(value):
    value = _validate(value, selection_schema(), 'bvbrc_variation_selection_invalid')
    vcf.validate_vcf_selection(value['vcf'], sheet=None)
    return value

def selected_field_schema():
    definitions = _literal_schema()['$defs']
    native = vcf.vcf_result_schema('Value')
    native_definitions = native.pop('$defs')
    native_definitions.pop('Return')
    _require(not set(definitions).intersection(native_definitions))
    definitions.update(native_definitions)
    selection = selection_schema()
    selection.pop('$defs')
    result = _object(dict(version=dict(const=VALUE_VERSION), selection=selection, state=dict(enum=['available', 'source_unavailable']), value=dict(anyOf=[native, dict(type='null')]), context={'$ref': '#/$defs/AnnotationJSON32'}, issues={'$ref': '#/$defs/AnnotationJSON32'}))
    result['allOf'] = [{'if': {'properties': {'state': {'const': 'source_unavailable'}}}, 'then': {'properties': {'value': {'type': 'null'}}}}, {'if': {'properties': {'state': {'const': 'available'}}}, 'then': {'properties': {'value': native}}}]
    return {**result, '$defs': definitions}

def validate_selected_field(value):
    value = _validate(value, selected_field_schema(), 'bvbrc_variation_selected_field_invalid')
    validate_selection(value['selection'])
    context = value['context']
    _require(type(context) is dict and set(context) == {'analysis_id', 'original_task', 'document_id', 'resolution', 'representation', 'content', 'vcf_sheet_sha256'} and (type(context['analysis_id']) is str) and bool(context['analysis_id']) and (context['document_id'] == value['selection']['document_id']) and (context['representation'] == 'vcf') and (type(context['resolution']) is str) and (context['resolution'] in {'available', 'missing', 'ambiguous', 'incompatible'}))
    validate_contract('OriginalTask', context['original_task'])
    if value['state'] == 'available':
        content = _content(context['content'])
        _require(context['resolution'] == 'available')
        vcf.validate_vcf_components(dict(version=vcf.COMPONENTS_VERSION, sheet_sha256=context['vcf_sheet_sha256'], value=value['value']))
        _require(_canonical(value['value']['selection']) == _canonical(value['selection']['vcf']) and value['value']['input']['source_ref'] == value['value']['input']['input_id'] == content['source_ref'] and (value['value']['input']['retained_file'] == dict(artifact_ref=content['artifact_ref'], sha256=content['sha256'], size_bytes=content['byte_count'], format='vcf')))
    else:
        _require(context['resolution'] != 'available' and context['content'] is None and (context['vcf_sheet_sha256'] is None))
    return value
