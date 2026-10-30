"""Compact FBA selections and their authenticated, private host materialization.

The original episode assignment stays compact. This module fills execution
bookkeeping only; existing FBA input witnesses and native contracts retain
scientific admission, and existing practical records retain endpoint credit.
"""
from copy import deepcopy
import json
from pathlib import Path

from .bvbrc_appservice_custody import AppServiceCustody
from .communication import plain
from .episode_bindings import BindingContext
from .execution_contracts import canonical, checked, digest, obj
from .flux_balance_contracts import flux_balance_schema, validate_flux_balance_record
from .native_file_capture import _metadata, capture_native_file, retained_native_file
from .native_flux_balance_bindings import validate_flux_balance_bindings
from .native_flux_balance_contracts import (
    ATTEMPT_DIRECTORY_NAME, DRIVER_MODULE, RUN_PLAN_FILENAME, SOURCE_FUNCTION_SHA256,
    flux_balance_environment,
)
from .practical_execution_records import validate_assignment
from .genomic_overlap_result_receipts import immutable, read_control


ASSIGNMENT_VERSION = 'flux_balance_scientific_assignment_v1'
LAUNCH_VERSION = 'flux_balance_scientific_launch_v1'
REQUEST_VERSION = 'flux_balance_scientific_request_v1'
LEGACY_CONTROL_VERSION = 'flux_balance_request_binding_v1'
CONTROL_VERSION = 'flux_balance_request_binding_v2'
# The immutable original control, rather than a mutable public result tag,
# fixes which exact projection is valid throughout recovery and closed replay.
_PUBLIC_VERSIONS = {LEGACY_CONTROL_VERSION: 'flux_balance_practical_outcome_v1',
                    CONTROL_VERSION: 'flux_balance_practical_outcome_v2'}
_TEXT = {'type': 'string', 'minLength': 1}
_SOURCE_FIELDS = ('artifact_ref', 'text_ref', 'request_ref', 'stdout_ref', 'stderr_ref')
OUTPUT_ROLES = ('original_model', 'selected_request', 'effective_model', 'effective_problem',
                'solution', 'flux_csv', 'native_log', 'manifest')
_TABLE = 'runtime_flux_balance_request_bindings'


def _require(condition, code):
    if not condition:
        raise ValueError('flux_balance_request_' + code)


def is_compact_assignment(value):
    return value.get('version') == ASSIGNMENT_VERSION


def is_compact_launch(value):
    return value.get('version') == LAUNCH_VERSION


def _file_schema():
    return obj({'witness_ref': {**_TEXT, 'format': 'reference'},
        'version': {'type': ['string', 'null']},
        'artifact_field': {'enum': [None, *_SOURCE_FIELDS]}, 'format': deepcopy(_TEXT)})


def scientific_request_schema():
    source = {'anyOf': [obj({'file': _file_schema(), 'pointer': {
        'type': 'string', 'pattern': r'^(?:/(?:[^~]|~[01])*)*$'}}), {'type': 'null'}]}
    bound = flux_balance_schema('Bound')
    bound['properties']['source'] = source
    bound['required'] = ['kind', 'value']
    change = obj({'reaction_id': deepcopy(_TEXT), 'lower': deepcopy(bound), 'upper': deepcopy(bound)})
    return obj({'version': {'const': REQUEST_VERSION},
        'operation': {'const': 'perform_flux_balance_analysis'},
        'mode': {'const': 'steady_state_linear_fba'},
        'model_input': obj({'file': _file_schema(),
            'original_loader_selection': {'enum': ['sbml_file', 'json_file', 'repository_identifier']},
            'repository_identifier': {'type': ['string', 'null']},
            'acquisition_receipt_file': {'anyOf': [_file_schema(), {'type': 'null'}]}}),
        'constraints': {'anyOf': [{'type': 'array', 'items': change}, {'type': 'null'}]},
        'objective': flux_balance_schema('ObjectiveRequest'),
        'solver_options': flux_balance_schema('RequestedSolverOptions')})


def resource_assignment_schema(resource_id, *, selected=True):
    predicates = [obj({'kind': {'const': 'requested_job_handoff'}}),
        obj({'kind': {'const': 'requested_job_outputs'}, 'output_roles': {
            'type': 'array', 'minItems': 1, 'uniqueItems': True,
            'items': {'enum': list(OUTPUT_ROLES)}}})]
    fields = {'version': {'const': ASSIGNMENT_VERSION},
        'resource_id': {'const': resource_id}, 'resource_kind': {'const': 'local'},
        'endpoint': {'enum': ['usable_handoff', 'completed_job_outputs']},
        'request': scientific_request_schema(),
        'progress_requirements': {'type': 'array', 'items': obj({'key': deepcopy(_TEXT),
            'credit': {'type': 'number', 'minimum': 0}, 'predicate': {'anyOf': predicates}})},
        'completion_keys': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
            'items': deepcopy(_TEXT)}, 'constraints': {'type': 'object'}}
    schema = obj(fields)
    if not selected:
        schema['required'].remove('resource_id')
    from .launch_instructions import SELECTION_SCHEMA
    schema['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
    return schema


def launch_assignment_schema(resources):
    fields = {key: resource_assignment_schema(key, selected=False)
        for key, configuration in resources.items() if configuration.get('native_flux_balance')}
    schema = obj({'version': {'const': LAUNCH_VERSION}, 'requests': {
        'type': 'object', 'properties': fields, 'minProperties': 1, 'additionalProperties': False},
        'constraints': {'type': 'object'}})
    from .launch_instructions import SELECTION_SCHEMA
    schema['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
    return schema


def validate_compact_assignment(value, resource_id):
    value = checked(value, resource_assignment_schema(resource_id, selected='resource_id' in value),
        'flux_balance_request_invalid_assignment')
    endpoint_kind = ('requested_job_handoff' if value['endpoint'] == 'usable_handoff'
        else 'requested_job_outputs')
    keys = [row['key'] for row in value['progress_requirements']]
    _require(len(set(keys)) == len(keys) and set(value['completion_keys']) <= set(keys),
        'completion_keys_conflict')
    _require(any(row['key'] in value['completion_keys'] and row['predicate']['kind'] == endpoint_kind
        for row in value['progress_requirements']), 'endpoint_requirement_missing')
    return value


def _files(request):
    yield request['model_input']['file']
    if request['model_input']['acquisition_receipt_file'] is not None:
        yield request['model_input']['acquisition_receipt_file']
    for change in request['constraints'] or []:
        for side in ('lower', 'upper'):
            source = change[side].get('source')
            if source is not None:
                yield source['file']


def _resolve_file(store, selection, records):
    record = records[selection['witness_ref']]
    _require(record.get('id') == selection['witness_ref'], 'witness_identity_conflict')
    version = selection['version']
    _require(version is None or str(record.get('revision')) == version, 'witness_version_conflict')
    field = selection['artifact_field']
    if record.get('record_type') == 'artifact':
        _require(field is None, 'artifact_field_conflict')
        reference = record['id']
    else:
        _require(record.get('record_type') == 'source' and field in _SOURCE_FIELDS,
            'source_witness_required')
        reference = record.get(field)
        _require(type(reference) is str and reference, 'artifact_field_unavailable')
    metadata = _metadata(store, reference)
    _require(reference == 'artifact_' + metadata['sha256'], 'artifact_identity_conflict')
    return {'artifact_ref': reference, 'sha256': metadata['sha256'],
        'size_bytes': metadata['size'], 'format': selection['format']}


def _materialize(store, row):
    selection, binding = row['selection'], row['binding']
    request, records = selection['request'], {item['reference']: item['record'] for item in row['witness_records']}
    model_selection = request['model_input']
    model = _resolve_file(store, model_selection['file'], records)
    _require(model['format'] in binding['model_formats'], 'model_format_not_bound')
    model_path = str(store.path / 'artifacts' / model['sha256'][:2] / model['sha256'])
    acquisition = model_selection['acquisition_receipt_file']

    def bound(value):
        source = value.get('source')
        return validate_flux_balance_record('Bound', {'kind': value['kind'], 'value': value['value'],
            'native_token': value.get('native_token'), 'float_hex': value.get('float_hex'),
            'source': None if source is None else {'file': _resolve_file(store, source['file'], records),
                'pointer': source['pointer']}})

    changes = request['constraints']
    job = {'version': 'native_flux_balance_job_v1', 'operation': request['operation'], 'mode': request['mode'],
        'source_alias': 'biomni.tool.systems_biology.perform_flux_balance_analysis',
        'model_input': {'file': {'path': model_path, 'sha256': model['sha256'], 'size_bytes': model['size_bytes']},
            'artifact_ref': model['artifact_ref'], 'format': model['format'],
            'original_loader_selection': model_selection['original_loader_selection'],
            'repository_identifier': model_selection['repository_identifier'],
            'acquisition_receipt_file': None if acquisition is None else _resolve_file(store, acquisition, records)},
        'constraints': None if changes is None else [{'reaction_id': change['reaction_id'],
            'lower': bound(change['lower']), 'upper': bound(change['upper'])} for change in changes],
        'objective': deepcopy(request['objective']), 'solver_options': deepcopy(request['solver_options']),
        'software': deepcopy(binding['software']), 'output_prefix': 'fba-output', 'flux_output_name': 'fluxes.csv',
        'source_function_sha256': SOURCE_FUNCTION_SHA256}
    software = binding['software']
    lifecycle = str(Path(row['workspace']) / '.fba-selected-runtime' / row['assignment_id'])
    environment = flux_balance_environment(software, attempt_directory=str(Path(lifecycle) / ATTEMPT_DIRECTORY_NAME),
        lifecycle_directory=lifecycle)
    assignment = {'version': 'practical_assignment_v1', 'assignment_id': row['assignment_id'],
        'resource_id': row['resource_id'], 'resource_kind': 'local', 'workspace': row['workspace'],
        'endpoint': selection['endpoint'], 'requested_job': {
            'argv': [software['python']['path'], '-B', '-S', '-m', DRIVER_MODULE, RUN_PLAN_FILENAME],
            'environment': environment, 'native_flux_balance': job},
        'progress_requirements': deepcopy(selection['progress_requirements']),
        'completion_keys': deepcopy(selection['completion_keys']),
        'initial_context': {'revision': 0, 'cwd': row['workspace'], 'environment': {}},
        'inventory_snapshot': {}, 'constraints': deepcopy(selection['constraints']),
        'native_flux_balance_execution': {'version': 'flux_balance_execution_selection_v1',
            'environment_realization': 'operation_scoped_tmp_and_cache_v1'}}
    if 'launch_instructions' in selection:
        assignment['launch_instructions'] = deepcopy(selection['launch_instructions'])
    return validate_assignment(assignment)


def _table_exists(store):
    return store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (_TABLE,)).fetchone() is not None


def _commission(custody, context):
    saved = custody.store.db.execute('SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?',
        (context.run_id, context.episode_id)).fetchone()
    return custody._commission(context, unsaved=saved is None)


def read_request_binding(store, run_id, episode_id):
    """Read only this host's original control and authenticate its commission."""
    _require(_table_exists(store), 'original_control_missing')
    saved = store.db.execute(f'SELECT file FROM {_TABLE} WHERE run_id=? AND episode_id=?',
        (run_id, episode_id)).fetchone()
    _require(saved is not None, 'original_control_missing')
    file = validate_flux_balance_record('File', json.loads(saved['file']))
    _require(file['format'] in _PUBLIC_VERSIONS, 'control_format_conflict')
    raw = retained_native_file(store, file).read_bytes()
    value = json.loads(raw)
    _require(raw == canonical(value).encode('utf-8') and value['version'] == file['format']
        and value['run_id'] == run_id and value['episode_id'] == episode_id, 'control_identity_conflict')
    context = BindingContext(**value['context'])
    custody = AppServiceCustody(store, run_id)
    custody.authenticate(context, allow_unsaved=True)
    _require(is_compact_launch(plain(context.assignment)) if context.role == 'launch'
        else context.role == 'launch_local' and is_compact_assignment(plain(context.assignment)),
        'original_context_conflict')
    for row in value['requests']:
        _require(_materialize(store, row) == row['assignment'], 'materialization_conflict')
    if context.role == 'launch':
        original = plain(context.assignment)
        _require(set(original['requests']) == {row['resource_id'] for row in value['requests']}, 'selection_conflict')
        for row in value['requests']:
            _require(row['selection'] == {**original['requests'][row['resource_id']],
                'resource_id': row['resource_id']}, 'selection_conflict')
    else:
        parent, _ = _commission(custody, context)
        original = read_request_binding(store, run_id, parent.episode_id)
        _require(value['parent_file'] == original['file'] and len(value['requests']) == 1
            and value['version'] == original['version'], 'parent_control_conflict')
        row = value['requests'][0]
        _require(row['selection'] == plain(context.assignment)
            and row in original['requests'], 'selection_conflict')
    return {**deepcopy(value), 'file': file}


def materialized_assignment(store, context):
    control = read_request_binding(store, context.run_id, context.episode_id)
    _require(control['context'] == context.as_record() and len(control['requests']) == 1,
        'original_context_conflict')
    return deepcopy(control['requests'][0]['assignment'])


def practical_outcome_view(receipt, *, assignment=None, control_version=LEGACY_CONTROL_VERSION):
    """Project facts under the original control's fixed presentation contract."""
    if receipt is None:
        return None
    _require(control_version in _PUBLIC_VERSIONS, 'public_outcome_version_conflict')
    facts = receipt['outcome'].get('facts', {})
    job = facts.get('requested_job')
    native = receipt['outcome'].get('native_outcome') or {}
    failure = native.get('failure') or {}
    outputs = [{key: row[key] for key in ('role', 'available', 'bytes', 'writer_closed') if key in row}
        for row in native.get('observed_outputs', [])]
    if control_version == CONTROL_VERSION and outputs:
        from .practical_execution_records import flux_balance_role_paths
        _require(type(assignment) is dict and type(job) is dict
            and job.get('requested_job_sha256') == digest(assignment['requested_job']),
            'public_output_request_conflict')
        paths = flux_balance_role_paths(assignment, job, OUTPUT_ROLES)
        _require(len(paths) == len(set(paths)), 'public_output_role_ambiguous')
        roles = {'requested_output:' + path: role for role, path in zip(OUTPUT_ROLES, paths)}
        roles.update({role: role for role in ('stdout', 'stderr')})
        for row in outputs:
            _require(row.get('role') in roles, 'public_output_role_conflict')
            row['role'] = roles[row['role']]
        _require(len(outputs) == len({row['role'] for row in outputs}), 'public_output_role_ambiguous')
    return {'version': _PUBLIC_VERSIONS[control_version], 'operation': receipt['tool_name'],
        'job': None if job is None else {key: job[key] for key in ('status', 'returncode')},
        'outputs': outputs,
        'failure': {key: failure[key] for key in ('code', 'exception_type', 'errno') if key in failure} or None,
        'validations': [{'key': row['key'], 'satisfied': row['satisfied']} for row in receipt['validations']]}


def match_practical_public_outcome(value, receipt, reference, *, assignment=None,
                                   control_version=LEGACY_CONTROL_VERSION):
    """Authenticate the exact committed view; pending metadata belongs to runtime."""
    value = deepcopy(plain(value))
    if 'pending_work_after_action' in value:
        from .waiting import validate_pending
        validate_pending(value.pop('pending_work_after_action'))
    expected = {'status': 'completed', 'record_refs': [reference], 'changed_record_refs': [reference],
        'result': practical_outcome_view(receipt, assignment=assignment, control_version=control_version)}
    _require(canonical(value) == canonical(expected), 'public_outcome_conflict')


def scientific_job_view(job):
    """Preserve selected scientific operands without execution bookkeeping."""
    model = job['model_input']
    changes = deepcopy(job['constraints'])
    for change in changes or []:
        for side in ('lower', 'upper'):
            source = change[side]['source']
            if source is not None:
                source['file'] = {key: source['file'][key] for key in ('artifact_ref', 'format')}
    acquisition = model['acquisition_receipt_file']
    return {'operation': job['operation'], 'mode': job['mode'],
        'model_input': {'artifact_ref': model['artifact_ref'], 'format': model['format'],
            'original_loader_selection': model['original_loader_selection'],
            'repository_identifier': model['repository_identifier'],
            'acquisition_receipt_file': None if acquisition is None else {
                key: acquisition[key] for key in ('artifact_ref', 'format')}},
        'constraints': changes, 'objective': deepcopy(job['objective']),
        'solver_options': deepcopy(job['solver_options'])}


class FluxBalanceRequestBindings:
    def __init__(self, owner):
        self.owner, self.store = owner, owner.store
        with self.store.transaction():
            self.store.db.execute(f'''CREATE TABLE IF NOT EXISTS {_TABLE} (
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL, file TEXT NOT NULL,
                PRIMARY KEY(run_id,episode_id))''')

    def validate_practical_history(self, context, practical_context, practical):
        """Check original private records and committed views without publishing."""
        from .practical_receipt_information import PracticalReceiptInformation
        actions = list(self.store.db.execute('SELECT decision_index,result FROM runtime_actions '
            'WHERE run_id=? AND episode_id=?', (context.run_id, context.episode_id)))
        if not (practical._state_directory(practical_context) / 'assignment.json').is_file():
            _require(not actions, 'original_practical_state_missing')
            return
        state = practical.state(practical_context)
        _require(canonical(state.assignment) == canonical(plain(practical_context.assignment)),
            'original_practical_assignment_conflict')
        receipts = state.receipts()
        keys = {row['operation_key'] for row in receipts}
        committed = set()
        for row in actions:
            if row['result'] is None:
                continue
            outcome = json.loads(row['result'])
            _require(type(outcome) is dict, 'public_outcome_conflict')
            if outcome.get('status') in {'completed', 'partial'}:
                committed.add(f'{context.run_id}:{context.episode_id}:{row["decision_index"]}')
        _require(committed <= keys, 'original_practical_receipt_missing')
        information = PracticalReceiptInformation(self.store, context.run_id)
        for receipt in receipts:
            selected = information._selected(receipt)
            sources = information._sources(information._accession(context.episode_id, receipt['operation_key']))
            _require(len(sources) == 1 if selected['result'] is not None else len(sources) <= 1,
                'original_practical_publication_missing')
            if sources:
                body = information.read(sources[0]['id'], context.scope)
                _require(canonical(body['receipt']) == canonical(receipt), 'original_practical_receipt_conflict')

    def _write(self, context, rows, parent_file=None, *, version=CONTROL_VERSION):
        _require(version in _PUBLIC_VERSIONS, 'control_format_conflict')
        value = {'version': version, 'run_id': context.run_id, 'episode_id': context.episode_id,
            'context': context.as_record(), 'requests': rows, 'parent_file': parent_file}
        root = self.owner.directory / 'fba-request-bindings' / digest([context.run_id, context.episode_id])
        root.mkdir(parents=True, exist_ok=True)
        immutable(root / 'materialization.json', value)
        file = capture_native_file(self.store, directory=str(root), relative_path='materialization.json', format=version)
        with self.store.transaction():
            old = self.store.db.execute(f'SELECT file FROM {_TABLE} WHERE run_id=? AND episode_id=?',
                (context.run_id, context.episode_id)).fetchone()
            if old is None:
                self.store.db.execute(f'INSERT INTO {_TABLE} VALUES(?,?,?)',
                    (context.run_id, context.episode_id, canonical(file)))
            else:
                _require(json.loads(old['file']) == file, 'control_identity_conflict')
        return read_request_binding(self.store, context.run_id, context.episode_id)

    def _row(self, context, resource_id, supplied):
        selection = validate_compact_assignment({**supplied, 'resource_id': resource_id}, resource_id)
        configuration = self.owner.resources[resource_id]
        candidates = [row for row in validate_flux_balance_bindings(configuration.get('native_flux_balance', []))
            if selection['request']['model_input']['file']['format'] in row['model_formats']]
        _require(len(candidates) == 1, 'binding_ambiguous' if candidates else 'binding_unavailable')
        records, versions = {}, []
        for file in _files(selection['request']):
            reference = file['witness_ref']
            record = records.setdefault(reference, self.store.get(reference))
            _resolve_file(self.store, file, records)
            primary = record['id'] if record['record_type'] == 'artifact' else record.get('artifact_ref')
            version = {'reference': reference, 'version': file['version'],
                'content_sha256': None if primary is None else _metadata(self.store, primary)['sha256']}
            previous = next((row for row in versions if row['reference'] == reference), None)
            _require(previous is None or previous == version, 'witness_version_conflict')
            if previous is None:
                versions.append(version)
        row = {'resource_id': resource_id, 'selection': selection, 'binding': candidates[0],
            'workspace': configuration['workspace'], 'assignment_id': digest({
                'run_id': context.run_id, 'episode_id': context.episode_id, 'resource_id': resource_id,
                'selection': selection}), 'input_versions': versions,
            'witness_records': [{'reference': ref, 'record': record} for ref, record in records.items()]}
        row['assignment'] = _materialize(self.store, row)
        self.owner._validate_request(row['assignment'], resource_id=resource_id)
        self.owner.flux_balance_inputs.validate_selected(context, row['assignment'], input_versions=versions)
        return row

    def preview(self, parent, selection):
        value = checked(selection, launch_assignment_schema(self.owner.resources), 'flux_balance_request_invalid_launch')
        self.owner._constraints(value['constraints'])
        rows = [self._row(parent, key, request) for key, request in value['requests'].items()]
        for row in rows:
            self.owner._match_request(value, row['selection'])
        return value, rows

    def initialize(self, context):
        saved = self.store.db.execute(f'SELECT 1 FROM {_TABLE} WHERE run_id=? AND episode_id=?',
            (context.run_id, context.episode_id)).fetchone()
        if saved is not None:
            return read_request_binding(self.store, context.run_id, context.episode_id)
        custody = AppServiceCustody(self.store, context.run_id)
        custody.authenticate(context, allow_unsaved=True)
        root = self.owner.directory / 'fba-request-bindings' / digest([context.run_id, context.episode_id])
        previous = read_control(root / 'materialization.json')
        if previous is not None:
            _require(previous['context'] == context.as_record(), 'original_context_conflict')
            return self._write(context, previous['requests'], previous['parent_file'], version=previous['version'])
        _require(not root.exists() and self.owner.flux_balance_inputs._new_control_allowed(context),
            'original_control_missing')
        if context.role == 'launch':
            _, rows = self.preview(context, plain(context.assignment))
            return self._write(context, rows)
        _require(context.role == 'launch_local', 'resource_context_required')
        parent, _ = _commission(custody, context)
        original = read_request_binding(self.store, context.run_id, parent.episode_id)
        selection = plain(context.assignment)
        row, = [row for row in original['requests'] if row['resource_id'] == selection['resource_id']]
        _require(selection == row['selection'], 'selection_conflict')
        return self._write(context, [row], original['file'], version=original['version'])


__all__ = ['ASSIGNMENT_VERSION', 'LAUNCH_VERSION', 'LEGACY_CONTROL_VERSION', 'CONTROL_VERSION', 'OUTPUT_ROLES',
    'is_compact_assignment', 'is_compact_launch', 'scientific_request_schema',
    'resource_assignment_schema', 'launch_assignment_schema', 'validate_compact_assignment',
    'read_request_binding', 'materialized_assignment', 'FluxBalanceRequestBindings']
