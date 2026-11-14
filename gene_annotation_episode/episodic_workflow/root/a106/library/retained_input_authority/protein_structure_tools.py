"""Ordinary selected protein operations over the existing native primitives.

Configuration and argument schemas are declarations. Preparation authenticates
one actual selected action, runs or recovers its original native unit, and
qualifies retained inputs for the shared projection reader. It publishes no
Source, report, observation or scientific interpretation.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import re
from pathlib import Path
from typing import TypedDict
from gene_annotation_episode.episodic_workflow.root.a106.communication import plain
from gene_annotation_episode.episodic_workflow.root.a106.domain import ContractError, validate_schema
from gene_annotation_episode.episodic_workflow.root.a106.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_protein_structure_acquisition import decode_protein_structure_json, retained_protein_structure_file
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_protein_structure_contracts import POLICY, _environment, _path, protein_structure_execution_schema, validate_protein_structure_bindings
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_protein_structure_preparation import _check_handle as _check_worker_handle, _intent as _worker_intent, _stored_json as _stored_control_json, validate_prepared_protein_structure_worker
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.protein_structure_contracts import same
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.protein_structure_result_views import protein_structure_projection_schema
SAVED_MODES = ('read_stored', 'recalculate', 'select_projection')
SAVED_WORK_VERSION = 'ordinary_protein_structure_saved_work_v1'

class PreparedSavedProteinWork(TypedDict):
    version: str
    mode: str
    tool_name: str
    arguments: dict
    scope: dict
    invocation: dict
    admission: dict
    binding: dict | None
    worker: dict | None
    qualified_files: dict
    scientific: dict | None
    issues: list[dict]
    redisplay: dict | None

def _require(condition, code):
    if not condition:
        raise ContractError(code)

def _copy(value):
    return json.loads(canonical(plain(value)))

def _definitions_for(roots):
    definitions = protein_structure_execution_schema('ScientificRequest', action_custody=True)['$defs']
    for name, value in protein_structure_projection_schema('ProjectionSelection', action_custody=True)['$defs'].items():
        _require(name not in definitions or same(definitions[name], value), 'protein_structure_schema_definition_conflict')
        definitions[name] = value
    selected = {}

    def visit(value):
        if isinstance(value, dict):
            reference = value.get('$ref')
            if reference is not None:
                _require(type(reference) is str and reference.startswith('#/$defs/'), 'protein_structure_schema_reference_invalid')
                name = reference[len('#/$defs/'):]
                _require(name in definitions, 'protein_structure_schema_reference_invalid')
                if name not in selected:
                    selected[name] = deepcopy(definitions[name])
                    visit(selected[name])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    for root in roots:
        visit({'$ref': '#/$defs/' + root})
    return selected

def _saved_argument_schemas(choices=None):
    reference = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source', 'pattern': '^source_[a-f0-9]{24,64}$'}
    projections = {'type': 'array', 'items': {'allOf': [{'$ref': '#/$defs/ProjectionSelection'}, {'properties': {'delivery_kind': {'const': 'values'}, 'family': {'enum': ['comparison_summary', 'transform', 'site_measurements', 'correspondence', 'structure_coordinates', 'native_uncertainty']}}}]}}
    common = dict(saved_sheet={'$ref': '#/$defs/SavedSheetDescriptorV2'}, projections=projections)
    shapes = {'read_stored': dict(result_ref=reference), 'recalculate': dict(resource_id={'type': 'string'}, binding_ordinal_0based={'type': 'integer', 'minimum': 0}, parameters={'$ref': '#/$defs/CalculationParameters'}, **common), 'select_projection': dict(result_ref=reference, **common)}
    result = {}
    for mode, properties in shapes.items():
        properties = dict(mode={'const': mode}, **deepcopy(properties))
        schema = {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties, '$defs': _definitions_for(('SavedSheetDescriptorV2', 'CalculationParameters', 'ProjectionSelection'))}
        if mode == 'recalculate' and choices is not None:
            alternatives = []
            for row in choices:
                selection = dict(resource_id={'const': row['resource_id']}, binding_ordinal_0based={'const': row['binding_ordinal_0based']})
                if row['scientific_mode'] is not None:
                    selection['parameters'] = {'properties': {'mode': {'const': row['scientific_mode']}}}
                alternatives.append({'properties': selection})
            schema['allOf'] = [{'anyOf': alternatives}]
        schema['$id'] = 'urn:gene-annotation:ordinary-protein-saved-tool:' + digest(schema)
        result[mode] = schema
    return result

def _retained_bytes(store, identity):
    path = retained_protein_structure_file(store, identity)
    raw = path.read_bytes()
    _require(len(raw) == identity['byte_length'] and hashlib.sha256(raw).hexdigest() == identity['sha256'], 'input_digest_mismatch')
    return raw

def _retained_json(store, identity):
    return decode_protein_structure_json(_retained_bytes(store, identity), canonical_bytes=True)

def _validate_selected_result_worker(store, prepared, *, plan, binding):
    worker = validate_prepared_protein_structure_worker(store, prepared, plan=plan)
    intent = _worker_intent(plan, executable=binding['software']['python_executable'], package_root=None, environment=binding['environment'])
    _require(same(_stored_control_json(store, 'artifact_' + digest(intent)), intent), 'original_commission_mismatch')
    handle_ref = worker['execution']['handle_artifact_ref']
    if handle_ref is not None:
        body = _stored_control_json(store, handle_ref, canonical_bytes=False)
        _require(type(body) is dict and type(body.get('request_sha256')) is str, 'original_commission_mismatch')
        request = _stored_control_json(store, 'artifact_' + body['request_sha256'], canonical_bytes=False)
        _check_worker_handle(body, request, intent)
    return worker

def _check_saved_binding(binding, arguments):
    _require(type(binding) is dict and set(binding) == {'resource_id', 'binding_ordinal_0based', 'operation', 'scientific_mode', 'software', 'environment', 'workspace', 'policy'}, 'original_commission_mismatch')
    validate_protein_structure_bindings([{key: binding[key] for key in ('operation', 'scientific_mode', 'software')}])
    _require(binding['operation'] == 'compare' and binding['resource_id'] == arguments['resource_id'] and (type(arguments['binding_ordinal_0based']) is int) and (binding['binding_ordinal_0based'] == arguments['binding_ordinal_0based']) and (binding['scientific_mode'] is None or binding['scientific_mode'] == arguments['parameters']['mode']) and same(binding['policy'], POLICY), 'original_commission_mismatch')
    _path(binding['workspace'], absolute=True)
    _environment(binding['environment'])

def _saved_worker_plan(store, arguments, invocation, binding):
    descriptor = arguments['saved_sheet']
    root = Path(binding['workspace']) / '.episode-operations' / digest({'run': invocation['run_id'], 'episode': invocation['episode_id']}) / digest(invocation['operation_key'])
    return {'version': 'protein_structure_result_worker_plan_v1', 'mode': 'saved_sheet_recalculation', 'directory': str(root / 'result-worker'), 'parameters': deepcopy(arguments['parameters']), 'sheet': {'file_identity': deepcopy(descriptor['sheet_file']), 'path': str(retained_protein_structure_file(store, descriptor['sheet_file']))}, 'original_components': {'file_identity': deepcopy(descriptor['original_components_file']), 'path': str(retained_protein_structure_file(store, descriptor['original_components_file']))}}

def _selected_legacy_parameter_reader(authority, transform):
    if transform is None or transform['origin'] != 'received_fitted' or transform['received_from']['saved_sheet']['version'] != 'protein_structure_saved_sheet_v1':
        return None
    from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.retained_protein_owner import RetainedProteinReader as ExecutionEpisodes
    legacy = getattr(authority, 'legacy_returns', None)
    owner = getattr(legacy, 'owner', None)
    _require(type(owner) is ExecutionEpisodes and legacy is owner.native_protein_structure_returns and (legacy.results is owner.native_protein_structure_results) and (owner.store is authority.store) and (owner.run_id == authority.run_id), 'protein_structure_legacy_parameter_authority_required')
    return dict(version='protein_structure_legacy_parameter_reader_v1', run_id=owner.run_id, directory=str(owner.directory))

def _authenticate_saved_parameters(store, context, parameters, authority, *, index, reader):
    transform = parameters['declared_transform']
    if transform is None or transform['origin'] != 'received_fitted':
        _require(reader is None, 'original_commission_mismatch')
        return
    from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.protein_structure_operands import authenticate_received_structure_transform
    legacy = transform['received_from']['saved_sheet']['version'] == 'protein_structure_saved_sheet_v1'
    if not legacy:
        _require(reader is None, 'original_commission_mismatch')
        authenticate_received_structure_transform(store, context, transform, returns=authority, before_decision_index=index)
        return
    from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.retained_protein_owner import RetainedProteinReader as ExecutionEpisodes
    from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.protein_structure_action_records import ProteinStructureActionRecords
    _require(type(reader) is dict and set(reader) == {'version', 'run_id', 'directory'} and (reader['version'] == 'protein_structure_legacy_parameter_reader_v1') and (reader['run_id'] == context.run_id), 'original_commission_mismatch')
    retained = ExecutionEpisodes.retained_protein_structure_reader(store, run_id=reader['run_id'], directory=reader['directory'])
    records = ProteinStructureActionRecords(store, context.run_id, legacy_returns=retained)
    value = authenticate_received_structure_transform(store, context, transform, returns=records, before_decision_index=index)
    if authority.legacy_returns is not None:
        _require(same(reader, _selected_legacy_parameter_reader(authority, transform)), 'original_commission_mismatch')
        original = authenticate_received_structure_transform(store, context, transform, returns=authority, before_decision_index=index)
        _require(same(value, original), 'original_commission_mismatch')

def validate_saved_protein_work(store, work, *, context, input_authority, prepared=False):
    """Reconstruct one selected saved action from actual retained authority.

    This performs no fit, parsing, worker dispatch or publication. Original
    descriptor custody and newly selected parameters remain separate records.
    """
    from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.protein_structure_calculations import validate_recorded_protein_structure_components
    from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.protein_structure_contracts import validate_protein_structure_sheet
    _require(type(work) is dict and set(work) == set(PreparedSavedProteinWork.__annotations__) and (work['version'] == SAVED_WORK_VERSION) and (work['mode'] in SAVED_MODES) and (work['tool_name'] == 'compare_protein_structures'), 'protein_structure_work_invalid')
    arguments, mode = (_copy(work['arguments']), work['mode'])
    _validate_saved_arguments(arguments)
    _require(arguments['mode'] == mode and same(work['scope'], plain(context.scope)) and (input_authority is not None) and (input_authority.store is store) and (input_authority.run_id == context.run_id), 'original_commission_mismatch')
    invocation = work['invocation']
    prefix = context.run_id + ':' + context.episode_id + ':'
    key = invocation.get('operation_key')
    suffix = key[len(prefix):] if type(key) is str and key.startswith(prefix) else ''
    _require(re.fullmatch('0|[1-9][0-9]*', suffix) is not None, 'original_commission_mismatch')
    index = int(suffix)
    _require(same(invocation, dict(run_id=context.run_id, episode_id=context.episode_id, operation_key=key, request_sha256=digest(plain(context.request)))), 'original_commission_mismatch')
    action = store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (context.run_id, context.episode_id, index)).fetchone()
    _require(action is not None and same(json.loads(action['action']), dict(kind='tool', tool=work['tool_name'], arguments=arguments)), 'original_commission_mismatch')
    fresh = deepcopy(work)
    if mode == 'read_stored':
        original = input_authority.read_stored_result(context, arguments['result_ref'], before_decision_index=index)
        _require(same(work['admission'], original.pop('admission')) and work['binding'] is None and (work['worker'] is None) and (work['scientific'] is None) and (work['qualified_files'] == {}) and same(work['redisplay'], original) and same(work['issues'], original['result']['issues']), 'original_commission_mismatch')
        return fresh
    inputs = input_authority.saved_action_inputs(context, arguments['saved_sheet'], required_use='recalculate' if mode == 'recalculate' else 'select_projection', before_decision_index=index, result_ref=arguments.get('result_ref'))
    expected_admission = deepcopy(inputs['admission'])
    if mode == 'recalculate' and work['admission'].get('parameter_reader') is not None:
        expected_admission['parameter_reader'] = deepcopy(work['admission']['parameter_reader'])
    _require(same(work['admission'], expected_admission), 'original_commission_mismatch')
    original, basis = (inputs['original'], inputs['basis'])
    if mode == 'recalculate':
        _authenticate_saved_parameters(store, context, arguments['parameters'], input_authority, index=index, reader=work['admission'].get('parameter_reader'))
    files = {name: deepcopy(original[name]) for name in ('native_file', 'sequence_file', 'residue_map_file', 'sheet_file', 'original_components_file', 'components_file')}
    scientific = None
    issues = deepcopy(original['native_issues'])
    if mode == 'recalculate':
        _check_saved_binding(work['binding'], arguments)
        plan = _saved_worker_plan(store, arguments, invocation, work['binding'])
        _require(type(work['worker']) is dict and set(work['worker']) == {'prepared', 'plan', 'execution', 'result'}, 'original_commission_mismatch')
        worker = _validate_selected_result_worker(store, work['worker']['prepared'], plan=plan, binding=work['binding'])
        _require(same(worker, work['worker']), 'original_commission_mismatch')
        issues.extend(worker['prepared']['issues'])
        result = worker['result']
        files['components_file'] = None
        if result is not None:
            issues.extend(result['issues'])
            if result['sheet_file'] is not None and result['components_file'] is not None:
                _require(same(result['sheet_file']['file_identity'], files['sheet_file']), 'original_commission_mismatch')
                files['components_file'] = deepcopy(result['components_file']['file_identity'])
    else:
        _require(work['binding'] is None and work['worker'] is None, 'original_commission_mismatch')
        files['components_file'] = deepcopy(basis['components_file'])
        issues.extend(basis.get('operation_issues', []))
        if same(arguments['projections'], [view['selection'] for view in basis['published']['result']['views']]):
            fresh['redisplay'] = deepcopy(basis['published'])
    if files['components_file'] is not None:
        sheet = validate_protein_structure_sheet(_retained_json(store, files['sheet_file']))
        components = validate_recorded_protein_structure_components(sheet, components=_retained_json(store, files['components_file']))
        _require(same(_retained_json(store, files['original_components_file']), sheet['native_baseline']), 'original_commission_mismatch')
        if mode == 'recalculate':
            _require(same(components['parameters'], arguments['parameters']), 'original_commission_mismatch')
        scientific = dict(kind='comparison', sheet=sheet, components=components)
        issues.extend(sheet['parse_issues'])
        issues.extend(sheet['correspondence_issues'])
        issues.extend(components['issues'])
    issues = list({canonical(value): value for value in issues}.values())
    if not prepared:
        _require(same(work['qualified_files'], files) and (work['scientific'] is None or same(work['scientific'], scientific)) and same(work['issues'], issues) and same(work['redisplay'], fresh['redisplay']), 'original_commission_mismatch')
    fresh.update(qualified_files=files, scientific=scientific, issues=issues)
    return fresh

def _validate_saved_arguments(arguments):
    from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.protein_structure_contracts import validate_calculation_parameters, validate_saved_sheet_descriptor_v2
    from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.protein_structure_result_views import validate_protein_structure_projection_selection
    mode = arguments.get('mode')
    _require(mode in SAVED_MODES, 'invalid_schema')
    validate_schema(arguments, _saved_argument_schemas()[mode])
    if 'result_ref' in arguments:
        _require(type(arguments['result_ref']) is str and re.fullmatch('source_[a-f0-9]{24,64}', arguments['result_ref']) is not None, 'invalid_schema')
    if mode == 'read_stored':
        return
    validate_saved_sheet_descriptor_v2(arguments['saved_sheet'])
    if mode == 'recalculate':
        _require(type(arguments['binding_ordinal_0based']) is int, 'protein_structure_binding_selection_invalid')
        validate_calculation_parameters(arguments['parameters'])
    selections = [validate_protein_structure_projection_selection(value) for value in arguments['projections']]
    _require(len({value['projection_id'] for value in selections}) == len(selections), 'duplicate_selection')
