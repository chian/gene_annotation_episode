"""Finite somatic native contracts; no execution, admission or VCF arithmetic.

Software and reference associations are explicit supplied declarations. Physical
pins do not establish a loaded-library trace, database correctness or clinical
validity. The ordinary host must authenticate every File before dispatch.
"""
from __future__ import annotations
from copy import deepcopy
import math
from pathlib import PurePosixPath
import re
STAGES = ('raw', 'filtered', 'annotated')
INPUTS = (('tumor_bam', 'tumor.bam', 'bam'), ('tumor_bai', 'tumor.bam.bai', 'bai'), ('normal_bam', 'normal.bam', 'bam'), ('normal_bai', 'normal.bam.bai', 'bai'), ('reference_fasta', 'reference.fasta', 'fasta'), ('reference_fai', 'reference.fasta.fai', 'fai'), ('reference_dictionary', 'reference.dict', 'sam_sequence_dictionary'), ('intervals', 'intervals.interval_list', 'gatk_interval_list'))
POLICY = {'memory_bytes': 20 * 1024 ** 3, 'scratch_bytes': 4 * 1024 ** 3}
PACKET_VERSION = 'ordinary_somatic_variant_values_v1'
CONTEXT_VERSION = 'somatic_variant_context_v1'
FACT_SOURCE = 'somatic_variant_outcomes'
ISSUE_CODES = ('input_identity_conflict', 'software_identity_conflict', 'header_unavailable', 'sample_identity_conflict', 'software_changed_after_execution', 'staged_input_changed', 'native_nonzero_exit', 'native_spawn_failed', 'required_output_missing', 'output_unavailable', 'output_empty')

def require(value, code):
    if not value:
        raise ValueError('somatic_variant_' + code)

def closed(value, fields, code):
    require(type(value) is dict and set(value) == set(fields.split()), code)

def _sha(value):
    return type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None

def validate_file(value, *, format=None):
    closed(value, 'artifact_ref sha256 size_bytes format', 'file_invalid')
    require(_sha(value['sha256']) and value['artifact_ref'] == 'artifact_' + value['sha256'] and (type(value['size_bytes']) is int) and (value['size_bytes'] >= 0) and (type(value['format']) is str) and value['format'], 'file_invalid')
    require(format is None or value['format'] == format, 'file_format_conflict')
    return deepcopy(value)

def validate_source(value):
    require(value is None or (type(value) is str and re.fullmatch('source_[a-f0-9]{24,64}', value)), 'source_invalid')
    return value

def _literal(value, code):
    require(type(value) is str and value and (not any((c in value for c in '\x00\r\n\t'))), code)
    return value

def _database_files(identifier, files):
    require(type(identifier) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]*', identifier), 'database_id_invalid')
    require(type(files) is list and files, 'database_files_invalid')
    names = []
    for row in files:
        closed(row, 'relative_path sha256 size_bytes', 'database_file_invalid')
        name = row['relative_path']
        require(type(name) is str and name and (not any((c in name for c in '\x00\r\n\\'))), 'database_path_invalid')
        path = PurePosixPath(name)
        require(bool(path.parts) and (not path.is_absolute()) and (str(path) == name) and ('..' not in path.parts) and (path.parts[0] == identifier), 'database_path_invalid')
        require(_sha(row['sha256']) and type(row['size_bytes']) is int and (row['size_bytes'] >= 0), 'database_file_invalid')
        names.append(name)
    require(len(names) == len(set(names)), 'database_paths_duplicate')
    require(identifier + '/snpEffectPredictor.bin' in names, 'database_predictor_missing')

def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

def somatic_result_schema(kind='Value'):
    """Detached closed schemas; the VCF owner remains the only value authority."""
    from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority import vcf_result_measurements as vcf
    definitions = deepcopy(vcf.vcf_result_schema('Value')['$defs'])
    integer = {'type': 'integer', 'minimum': 0}
    text = {'type': 'string', 'minLength': 1}
    nullable_text = {'anyOf': [{'type': 'null'}, text]}
    identity = _object({'sha256': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}, 'size_bytes': integer})
    source = {'anyOf': [{'type': 'null'}, {'type': 'string', 'pattern': '^source_[a-f0-9]{24,64}$'}]}
    sample = _object({'tumor': text, 'normal': text})
    context = _object({'version': {'const': CONTEXT_VERSION}, 'inputs': {'type': 'array', 'minItems': 7, 'maxItems': 8, 'items': _object({'role': {'enum': [row[0] for row in INPUTS]}, 'file': {'$ref': '#/$defs/File'}, 'source_ref': source})}, 'sample_ids': _object({'declared': sample, 'observed': _object({role: {'type': 'array', 'items': text, 'uniqueItems': True} for role in ('tumor', 'normal')})}), 'reference_id': nullable_text, 'software': _object({**{key: deepcopy(identity) for key in ('java', 'gatk_jar', 'snpeff_jar', 'snpeff_config')}, 'reported_versions': _object({key: nullable_text for key in ('java', 'gatk', 'snpeff')}), 'loaded_dependencies_verified': {'const': False}}), 'annotation_database': _object({'id': text, 'files': {'type': 'array', 'minItems': 1, 'items': _object({'relative_path': text, **identity['properties']})}, 'reference_association': {'const': 'caller_declared'}}), 'parameters': _object({'java_heap_mb': {'type': 'integer', 'minimum': 1, 'maximum': 20479}, 'pair_hmm_implementation': {'const': 'LOGLESS_CACHING'}}), 'stages': {'type': 'array', 'minItems': 3, 'maxItems': 3, 'items': _object({'stage': {'enum': list(STAGES)}, 'state': {'enum': ['not_attempted', 'spawn_failed', 'exited']}, 'returncode': {'type': ['integer', 'null']}})}, 'outputs': {'type': 'array', 'maxItems': 3, 'items': _object({'role': {'enum': list(STAGES)}, **identity['properties']})}, 'issues': {'type': 'array', 'items': {'enum': list(ISSUE_CODES)}, 'uniqueItems': True}, 'definitions': _object({key: {'const': value} for key, value in {'native_exit': 'process status, not VCF validity or biological correctness', 'software': 'selected byte pins and supplied version metadata, not observed loaded-library or build-source equivalence', 'population': 'retained VCF record slots and explicitly selected ALT/sample/GT observations', 'filter': 'literal native FILTER fields; no caller-independent somatic truth assignment', 'annotation': 'literal native INFO annotations; no additional effect or clinical scoring', 'sample_reference_database': 'explicit supplied associations and observed BAM SM labels; no filename or assembly inference'}.items()})})
    definitions['SomaticContext'] = context
    definitions['SomaticSelection'] = _object({'stage': {'enum': list(STAGES)}, 'vcf': {'$ref': '#/$defs/Selection'}})
    definitions['SomaticValue'] = _object({'version': {'const': PACKET_VERSION}, 'selection': {'$ref': '#/$defs/SomaticSelection'}, 'context': {'$ref': '#/$defs/SomaticContext'}, 'value': {'$ref': '#/$defs/Value'}})
    definitions['SomaticReturn'] = _object({**definitions['SomaticValue']['properties'], 'source_ref': {'type': 'string', 'pattern': '^source_[a-f0-9]{24,64}$'}})
    selected_file = _object({'role': {'enum': [row[0] for row in INPUTS]}, 'namespace': {'enum': ['source', 'artifact']}, 'reference': text, 'max_bytes': {'type': 'integer', 'minimum': 1, 'maximum': POLICY['scratch_bytes']}})
    run_arguments = _object({'mode': {'const': 'run_native'}, 'inputs': {'type': 'array', 'minItems': 7, 'maxItems': 8, 'items': selected_file}, 'sample_ids': sample, 'reference_id': nullable_text, 'annotation_database_id': text, 'selection': {'$ref': '#/$defs/SomaticSelection'}})
    saved_arguments = _object({'mode': {'const': 'calculate_saved'}, 'result_ref': text, 'selection': {'$ref': '#/$defs/SomaticSelection'}})
    read_arguments = _object({'mode': {'const': 'read_stored'}, 'result_ref': text})
    definitions['SomaticArguments'] = {'oneOf': [run_arguments, saved_arguments, read_arguments]}
    names = {'Arguments': 'SomaticArguments', 'Context': 'SomaticContext', 'Selection': 'SomaticSelection', 'Value': 'SomaticValue', 'Return': 'SomaticReturn'}
    require(kind in names, 'schema_kind_invalid')
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema', '$ref': '#/$defs/' + names[kind], '$defs': definitions}

def _wire(value, kind):
    from jsonschema import Draft202012Validator, validators
    strict = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER.redefine('integer', lambda _checker, x: type(x) is int).redefine('number', lambda _checker, x: type(x) is int or (type(x) is float and math.isfinite(x))).redefine('array', lambda _checker, x: type(x) is list).redefine('object', lambda _checker, x: type(x) is dict))
    require(strict(somatic_result_schema(kind)).is_valid(value), kind.lower() + '_invalid')
    return deepcopy(value)

def validate_somatic_context(value):
    value = _wire(value, 'Context')
    _database_files(value['annotation_database']['id'], value['annotation_database']['files'])
    require([row['role'] for row in value['inputs']] == [row[0] for row in INPUTS[:len(value['inputs'])]], 'context_input_order_invalid')
    for row, (_role, _name, format) in zip(value['inputs'], INPUTS):
        validate_file(row['file'], format=format)
        validate_source(row['source_ref'])
    require(value['sample_ids']['declared']['tumor'] != value['sample_ids']['declared']['normal'], 'sample_ids_identical')
    require([row['stage'] for row in value['stages']] == list(STAGES), 'context_stage_order_invalid')
    previous = True
    for row in value['stages']:
        require(row['state'] == 'exited' and type(row['returncode']) is int or (row['state'] != 'exited' and row['returncode'] is None), 'context_exit_invalid')
        if row['state'] != 'not_attempted':
            require(previous, 'context_stage_prerequisite_conflict')
        previous = row['state'] == 'exited' and row['returncode'] == 0
    if any((row['state'] != 'not_attempted' for row in value['stages'])):
        require(all((value['sample_ids']['observed'][role] == [value['sample_ids']['declared'][role]] for role in ('tumor', 'normal'))), 'context_sample_association_conflict')
    roles = [row['role'] for row in value['outputs']]
    require(roles == [stage for stage in STAGES if stage in roles] and len(roles) == len(set(roles)), 'context_output_order_invalid')
    return value

def validate_somatic_selection(value, *, sheet=None):
    from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority import vcf_result_measurements as vcf
    value = _wire(value, 'Selection')
    value['vcf'] = vcf.validate_vcf_selection(value['vcf'], sheet=sheet)
    return value

def validate_somatic_arguments(value):
    value = _wire(value, 'Arguments')
    if value['mode'] == 'run_native':
        require([row['role'] for row in value['inputs']] == [row[0] for row in INPUTS[:len(value['inputs'])]], 'arguments_input_order_invalid')
        for row in value['inputs']:
            pattern = 'source_[a-f0-9]{24,64}' if row['namespace'] == 'source' else 'artifact_[a-f0-9]{64}'
            require(re.fullmatch(pattern, row['reference']) is not None, 'arguments_input_reference_invalid')
        for sample in value['sample_ids'].values():
            _literal(sample, 'sample_id_invalid')
        require(value['sample_ids']['tumor'] != value['sample_ids']['normal'], 'sample_ids_identical')
        require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]*', value['annotation_database_id']) is not None, 'arguments_database_invalid')
    else:
        require(validate_source(value['result_ref']) is not None, 'arguments_result_source_missing')
    if value['mode'] != 'read_stored':
        validate_somatic_selection(value['selection'])
    return value

def validate_somatic_stage_input(value, *, context, stage):
    """Join an already validated VCF Input to retained native byte metadata."""
    context = validate_somatic_context(context)
    require(stage in STAGES, 'stage_invalid')
    closed(value, 'input_id retained_file original_file source_ref capture', 'stage_input_descriptor_invalid')
    output = next((row for row in context['outputs'] if row['role'] == stage), None)
    if value['capture']['state'] == 'complete':
        require(output is not None and value['retained_file'] is not None and all((value['retained_file'][key] == output[key] for key in ('sha256', 'size_bytes'))), 'packet_native_bytes_conflict')
    elif value['retained_file'] is not None:
        require(output is not None and value['retained_file']['size_bytes'] <= output['size_bytes'], 'packet_capture_size_conflict')
    if value['capture']['original_size_bytes'] is not None:
        require(output is not None and value['capture']['original_size_bytes'] == output['size_bytes'], 'packet_original_size_conflict')
    return deepcopy(value)

def validate_somatic_packet(value):
    from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority import vcf_result_measurements as vcf
    value = _wire(value, 'Value')
    value['context'] = validate_somatic_context(value['context'])
    value['selection'] = validate_somatic_selection(value['selection'])
    value['value'] = vcf._validate_value(value['value'])
    require(value['selection']['vcf'] == value['value']['selection'], 'packet_selection_conflict')
    validate_somatic_stage_input(value['value']['input'], context=value['context'], stage=value['selection']['stage'])
    return value

def project_somatic_return(packet, source_ref):
    packet = validate_somatic_packet(packet)
    require(validate_source(source_ref) is not None, 'return_source_missing')
    return {**packet, 'source_ref': source_ref}

def validate_somatic_return(value):
    value = _wire(value, 'Return')
    source_ref = value.pop('source_ref')
    return project_somatic_return(value, source_ref)

def somatic_fact_sources():
    schema = somatic_result_schema('Return')
    schema.update({'$id': 'https://gene-annotation.invalid/somatic-variant-facts-v1'})
    schema['$defs']['SomaticReturn']['properties']['source_ref']['x-reference-namespace'] = 'source'
    schema['$defs']['SomaticReturn']['properties']['source_ref']['format'] = 'reference'
    schema.pop('$ref')
    schema.update({'type': 'array', 'items': {'$ref': '#/$defs/SomaticReturn'}})
    return {FACT_SOURCE: {'type': 'array', 'report_schema': schema}}
