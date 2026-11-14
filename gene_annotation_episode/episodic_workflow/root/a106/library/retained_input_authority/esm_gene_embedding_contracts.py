"""Supplied-protein occurrences and literal ESM2 embedding result contracts.

This module performs no acquisition, model inference, vector arithmetic or
similarity scoring. The native worker alone delegates inference and the two
explicit means to ESM/PyTorch. Identifiers are caller/source labels, not inferred
gene correspondence or functional confidence.
"""
from copy import deepcopy
import json
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_atac_differential_contracts import driver_runtime_schema
FACT_SOURCE = 'esm_gene_embedding_outcomes'
MODEL = 'esm2_t6_8M_UR50D'
INPUT_VERSION = 'esm_supplied_proteins_v1'
REQUEST_VERSION = 'esm_gene_embedding_request_v1'
DOCUMENT_VERSION = 'esm_gene_embeddings_v1'
SELECTION_VERSION = 'esm_gene_embedding_selection_v1'
VALUE_VERSION = 'esm_gene_embedding_values_v1'
WORKER_RESULT_VERSION = 'esm_gene_embedding_worker_result_v1'
PROTEIN_POOLING = 'mean_model_tokens_excluding_bos_eos_padding'
GENE_POOLING = 'equal_mean_successful_isoform_occurrences'
_SOURCE = '^source_[0-9a-f]{24,64}$'
_NONFINITE = ('NaN', 'Infinity', '-Infinity')

def _require(condition, code):
    if not condition:
        raise ValueError('esm_gene_embedding_' + code)

def _copy(value):
    try:
        return json.loads(json.dumps(value, allow_nan=False))
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        raise ValueError('esm_gene_embedding_finite_json_required') from error

def _obj(properties):
    return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)

def _array(item, **extra):
    return dict(type='array', items=item, **extra)

def _nullable(schema):
    return dict(anyOf=[schema, dict(type='null')])
_INDEX = dict(type='integer', minimum=0)
_TEXT = dict(type='string', minLength=1)
_SOURCE_REF = dict(type='string', pattern=_SOURCE)
_FILE = _obj(dict(artifact_ref=dict(type='string', pattern='^artifact_[0-9a-f]{64}$'), sha256=dict(type='string', pattern='^[0-9a-f]{64}$'), size_bytes=_INDEX, format=dict(const='fasta')))
_PIN = _obj(dict(path=_TEXT, sha256=dict(type='string', pattern='^[0-9a-f]{64}$'), size_bytes=_INDEX))
_ASSIGNMENT = _obj(dict(record_ordinal=_INDEX, protein_id=_TEXT, isoform_id=_TEXT))
_GENE = _obj(dict(gene_id=_TEXT, isoforms=_array(_ASSIGNMENT)))
_PARAMETERS = _obj(dict(layer=dict(const=6), batch_size=dict(type='integer', minimum=1), max_sequence_length=dict(type='integer', minimum=1), protein_pooling=dict(const=PROTEIN_POOLING), gene_pooling=dict(const=GENE_POOLING)))
_DEPLOYMENT = _obj(dict(version=dict(const='esm_gene_embedding_deployment_v1'), model_name=dict(const=MODEL), layer_count=dict(const=6), embedding_dimension=dict(const=320), device=dict(const='cpu'), torch_threads=dict(const=1), checkpoint=_PIN, regression_checkpoint=_PIN, driver=driver_runtime_schema()))
_GROUP_SELECTION = _obj(dict(row_ordinals=_nullable(_array(_INDEX, uniqueItems=True)), component_indices=_nullable(_array(_INDEX, uniqueItems=True)), offset=_INDEX, limit=_INDEX))
_SELECTION = _obj(dict(version=dict(const=SELECTION_VERSION), residues=_GROUP_SELECTION, proteins=_GROUP_SELECTION, isoforms=_GROUP_SELECTION, genes=_GROUP_SELECTION))
_SEGMENT = _obj(dict(byte_start=_INDEX, byte_end=_INDEX, text=dict(type='string')))
_INPUT_ROW = _obj(dict(record_ordinal=_INDEX, raw_header=dict(type='string'), sequence=dict(type='string'), header_byte_start=_INDEX, header_byte_end=_INDEX, sequence_segments=_array(_SEGMENT), status=dict(enum=['available', 'malformed']), issues=_array(_TEXT, uniqueItems=True)))
_INPUT = _obj(dict(version=dict(const=INPUT_VERSION), file=_FILE, source_ref=_nullable(_SOURCE_REF), raw_hex=dict(type='string', pattern='^(?:[0-9a-f]{2})*$'), catalog_complete=dict(type='boolean'), record_count=_nullable(_INDEX), records=_array(_INPUT_ROW), issues=_array(_TEXT, uniqueItems=True)))
_NUMBER = dict(anyOf=[dict(type='number'), dict(enum=list(_NONFINITE))])
_VECTOR = _array(_NUMBER, minItems=320, maxItems=320)
_PROTEIN = _obj(dict(protein_ordinal=_INDEX, raw_header=dict(type='string'), sequence=dict(type='string'), status=dict(enum=['unrequested', 'length_filtered', 'invalid', 'failed', 'available', 'nonfinite']), model_token_count=_nullable(_INDEX), residue_vectors=_nullable(_array(_VECTOR)), mean_vector=_nullable(_VECTOR), issues=_array(_TEXT, uniqueItems=True)))
_ISOFORM = _obj(dict(isoform_ordinal=_INDEX, gene_ordinal=_INDEX, ordinal_within_gene=_INDEX, record_ordinal=_INDEX, protein_id=_TEXT, isoform_id=_TEXT, status=dict(enum=['unavailable', 'available', 'nonfinite']), mean_vector=_nullable(_VECTOR)))
_GENE_ROW = _obj(dict(gene_ordinal=_INDEX, gene_id=_TEXT, isoform_ordinals=_array(_INDEX), successful_isoform_ordinals=_array(_INDEX), mean_vector=_nullable(_VECTOR), status=dict(enum=['unavailable', 'failed', 'available', 'nonfinite'])))
_OBSERVED = _obj(dict(model_name=dict(const=MODEL), layer_count=dict(const=6), embedding_dimension=dict(const=320), torch_version=_TEXT, esm_version=_TEXT, parameter_dtype=_TEXT, device=dict(const='cpu'), torch_threads=dict(const=1), alphabet_tokens=_array(_TEXT, uniqueItems=True), prepend_bos=dict(const=True), append_eos=dict(const=True)))
_EXECUTION = _obj(dict(state=dict(enum=['completed', 'partial', 'failed']), model_load=dict(enum=['completed', 'failed']), attempts=dict(const=1), model_forward_calls=_INDEX, runtime_verified=dict(type='boolean'), failure=_nullable(_obj(dict(code=_TEXT, exception_type=_TEXT)))))
_DOCUMENT = _obj(dict(version=dict(const=DOCUMENT_VERSION), input=_INPUT, genes=_array(_GENE), parameters=_PARAMETERS, deployment=_DEPLOYMENT, observed_model=_nullable(_OBSERVED), proteins=_array(_PROTEIN), isoforms=_array(_ISOFORM), gene_rows=_array(_GENE_ROW), execution=_EXECUTION))
_REQUEST = _obj(dict(version=dict(const=REQUEST_VERSION), input=_obj(dict(path=_TEXT, file=_FILE, source_ref=_nullable(_SOURCE_REF))), genes=_array(_GENE), parameters=_PARAMETERS, deployment=_DEPLOYMENT))

def _output_file(name, file_format):
    return _obj(dict(path=dict(const='esm-gene-embeddings/' + name), format=dict(const=file_format), sha256=dict(type='string', pattern='^[0-9a-f]{64}$'), size_bytes=_INDEX))
_WORKER_RESULT = _obj(dict(version=dict(const=WORKER_RESULT_VERSION), request_sha256=dict(type='string', pattern='^[0-9a-f]{64}$'), input_document_file=_output_file('input.json', 'json'), result_document_file=_output_file('embeddings.json', 'json'), vector_file=_nullable(_output_file('vectors.pt', 'pt')), execution=_EXECUTION))
_ARGUMENTS = dict(oneOf=[_obj(dict(mode=dict(const='embed'), input=_obj(dict(reference=_TEXT, namespace=dict(enum=['source', 'artifact']))), genes=_array(_GENE), model_name=dict(const=MODEL), parameters=_PARAMETERS, selection=_SELECTION)), _obj(dict(mode=dict(const='read_stored'), result_ref=_SOURCE_REF, selection=_SELECTION))])
_COMPONENTS = _array(_INDEX, uniqueItems=True)
_CELLS = _nullable(_array(_NUMBER, maxItems=320))
_PUBLIC_RESIDUE = _obj(dict(row_ordinal=_INDEX, protein_ordinal=_INDEX, token_ordinal_0based=_INDEX, symbol=dict(type='string', minLength=1, maxLength=1), status=dict(enum=['available', 'nonfinite']), component_indices=_COMPONENTS, values=_CELLS))
_PUBLIC_PROTEIN = _obj(dict(row_ordinal=_INDEX, protein_ordinal=_INDEX, raw_header=dict(type='string'), sequence=dict(type='string'), status=_PROTEIN['properties']['status'], model_token_count=_nullable(_INDEX), issues=_array(_TEXT, uniqueItems=True), component_indices=_COMPONENTS, values=_CELLS))
_PUBLIC_ISOFORM = _obj(dict(row_ordinal=_INDEX, **{k: v for k, v in _ISOFORM['properties'].items() if k != 'mean_vector'}, component_indices=_COMPONENTS, values=_CELLS))
_PUBLIC_GENE = _obj(dict(row_ordinal=_INDEX, **{k: v for k, v in _GENE_ROW['properties'].items() if k != 'mean_vector'}, component_indices=_COMPONENTS, values=_CELLS))
_GENE_POPULATION = _obj(dict(gene_ordinal=_INDEX, gene_id=_TEXT, supplied_isoform_count=_INDEX, successful_isoform_ordinals=_array(_INDEX), status=_GENE_ROW['properties']['status']))
_CONTEXT = _obj(dict(model_name=dict(const=MODEL), selected_checkpoint_sha256=dict(type='string', pattern='^[0-9a-f]{64}$'), selected_regression_checkpoint_sha256=dict(type='string', pattern='^[0-9a-f]{64}$'), parameters=_PARAMETERS, observed_model=_nullable(_OBSERVED), execution=_EXECUTION, input_file=_FILE, input_source_ref=_nullable(_SOURCE_REF), input_catalog_complete=dict(type='boolean'), input_record_count=_nullable(_INDEX), input_issues=_array(_TEXT, uniqueItems=True), supplied_gene_occurrence_count=_INDEX, supplied_isoform_occurrence_count=_INDEX, requested_protein_ordinals=_array(_INDEX, uniqueItems=True), successful_protein_ordinals=_array(_INDEX, uniqueItems=True), length_filtered_protein_ordinals=_array(_INDEX, uniqueItems=True), failed_protein_ordinals=_array(_INDEX, uniqueItems=True), unavailable_requested_protein_ordinals=_array(_INDEX, uniqueItems=True), gene_populations=_array(_GENE_POPULATION), quantity_meaning=dict(const='dimensionless_model_representation_not_function_probability'), protein_denominator=dict(const='actual_model_tokens_excluding_bos_eos_padding'), gene_denominator=dict(const='successful_isoform_occurrences_only_equal_weight'), biological_isoform_population_completeness=dict(const='unknown')))

def _public_group(row):
    return _obj(dict(population_count=_INDEX, selected_count=_INDEX, returned_count=_INDEX, rows=_array(row)))
_VALUE = _obj(dict(version=dict(const=VALUE_VERSION), selection=_SELECTION, context=_CONTEXT, residues=_public_group(_PUBLIC_RESIDUE), proteins=_public_group(_PUBLIC_PROTEIN), isoforms=_public_group(_PUBLIC_ISOFORM), genes=_public_group(_PUBLIC_GENE)))
_RETURN = _obj(dict(source_ref={**_SOURCE_REF, 'format': 'reference', 'x-reference-namespace': 'source'}, **_VALUE['properties']))

def _check(value, schema):
    from jsonschema import Draft202012Validator, ValidationError, validators
    value = _copy(value)
    strict = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER.redefine('integer', lambda _checker, item: type(item) is int))
    try:
        strict(schema).validate(value)
    except ValidationError as error:
        raise ValueError('esm_gene_embedding_schema_invalid') from error
    return value

def _file(value):
    _require(value['artifact_ref'] == 'artifact_' + value['sha256'], 'file_identity_conflict')

def validate_esm_embedding_value(value):
    value = _check(value, _VALUE)
    _file(value['context']['input_file'])
    context = value['context']
    _require(value['genes']['population_count'] == context['supplied_gene_occurrence_count'] and value['isoforms']['population_count'] == context['supplied_isoform_occurrence_count'] and (context['input_record_count'] is None or value['proteins']['population_count'] == context['input_record_count']), 'public_group_population_conflict')
    _require(len(context['gene_populations']) == context['supplied_gene_occurrence_count'], 'public_gene_population_conflict')
    _require(sum((r['supplied_isoform_count'] for r in context['gene_populations'])) == context['supplied_isoform_occurrence_count'], 'public_isoform_population_conflict')
    for ordinal, row in enumerate(context['gene_populations']):
        _require(row['gene_ordinal'] == ordinal and len(row['successful_isoform_ordinals']) <= row['supplied_isoform_count'], 'public_gene_population_conflict')
    for kind in ('residues', 'proteins', 'isoforms', 'genes'):
        group, selection = (value[kind], value['selection'][kind])
        ordinals = list(range(group['population_count'])) if selection['row_ordinals'] is None else selection['row_ordinals']
        _require(all((i < group['population_count'] for i in ordinals)) and group['selected_count'] == len(ordinals), 'public_selection_population_conflict')
        returned = ordinals[selection['offset']:selection['offset'] + selection['limit']]
        components = list(range(320)) if selection['component_indices'] is None else selection['component_indices']
        _require(all((i < 320 for i in components)) and group['returned_count'] == len(group['rows']) and ([r['row_ordinal'] for r in group['rows']] == returned), 'public_selection_order_conflict')
        for row in group['rows']:
            _require(row['component_indices'] == components and (row['values'] is None or len(row['values']) == len(components)), 'public_vector_shape_conflict')
            _require((row['values'] is not None) == (row['status'] in ('available', 'nonfinite')), 'public_vector_state_conflict')
            if kind in ('proteins', 'isoforms', 'genes'):
                identity = {'proteins': 'protein_ordinal', 'isoforms': 'isoform_ordinal', 'genes': 'gene_ordinal'}[kind]
                _require(row['row_ordinal'] == row[identity], 'public_row_identity_conflict')
            if kind == 'genes':
                population = context['gene_populations'][row['gene_ordinal']]
                _require(all((row[k] == population[k] for k in ('gene_id', 'successful_isoform_ordinals', 'status'))) and len(row['isoform_ordinals']) == population['supplied_isoform_count'], 'public_gene_population_conflict')
    return value

def validate_esm_embedding_return(value):
    value = _check(value, _RETURN)
    validate_esm_embedding_value({k: v for k, v in value.items() if k != 'source_ref'})
    return value

def esm_gene_embedding_fact_sources():
    return {FACT_SOURCE: dict(type='array', meaning='Selected literal ESM2 representations and explicit occurrence/pooling populations; not function probabilities.', report_schema={'type': 'array', 'items': esm_gene_embedding_schema('Return'), 'x-source': FACT_SOURCE})}

def esm_gene_embedding_schema(kind='Arguments'):
    schemas = dict(Arguments=_ARGUMENTS, Selection=_SELECTION, Input=_INPUT, Deployment=_DEPLOYMENT, Request=_REQUEST, WorkerResult=_WORKER_RESULT, Document=_DOCUMENT, Value=_VALUE, Return=_RETURN)
    _require(kind in schemas, 'schema_kind_required')
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema', **deepcopy(schemas[kind])}
