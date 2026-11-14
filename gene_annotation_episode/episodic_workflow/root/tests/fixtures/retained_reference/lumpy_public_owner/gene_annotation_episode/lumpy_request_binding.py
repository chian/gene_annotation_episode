"""Received scientific File selections and private LUMPY job materialization.

The original compact assignment remains the commission. Native execution uses
the selected installation and original practical handle; VCF interpretation
belongs to the existing shared result tool.
"""
from copy import deepcopy
from collections.abc import Mapping
import json
import os
from pathlib import Path

from .bvbrc_appservice_custody import AppServiceCustody
from .communication import plain
from .episode_bindings import BindingContext
from .execution_contracts import canonical, checked, digest, obj
from .genomic_overlap_result_receipts import immutable, read_control
from .native_file_capture import _identity, _metadata, capture_native_file, retained_native_file
from .practical_execution_records import validate_assignment
from .received_native_file_inputs import received_file_context, validate_received_native_file_inputs


ASSIGNMENT_VERSION = 'lumpy_scientific_assignment_v1'
LAUNCH_VERSION = 'lumpy_scientific_launch_v1'
CONTROL_VERSION = 'lumpy_request_binding_v1'
PUBLIC_OUTCOME_VERSION = 'lumpy_practical_outcome_v1'
OUTPUT_ROLES = ('vcf', 'stderr', 'seal', 'bam_headers')
_TABLE = 'runtime_lumpy_request_bindings'
_TEXT = {'type': 'string', 'minLength': 1}


def _require(condition, code):
    if not condition:
        raise ValueError('lumpy_request_' + code)


def _lumpy_resource_commission(custody, context):
    saved = custody.store.db.execute('SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?',
        (context.run_id, context.episode_id)).fetchone()
    return custody._commission(context, unsaved=saved is None)


def is_compact_assignment(value):
    return isinstance(value, dict) and value.get('version') == ASSIGNMENT_VERSION


def is_compact_launch(value):
    return isinstance(value, dict) and value.get('version') == LAUNCH_VERSION


def _compact_files(schema):
    """Detach only File metadata from this scientific request schema."""
    if isinstance(schema, list):
        return [_compact_files(value) for value in schema]
    if not isinstance(schema, dict):
        return schema
    value = {key: _compact_files(item) for key, item in schema.items()}
    properties = value.get('properties')
    if isinstance(properties, dict) and set(properties) == {'artifact_ref', 'sha256', 'size_bytes', 'format'}:
        value['properties'] = {key: properties[key] for key in ('artifact_ref', 'format')}
        value['required'] = ['artifact_ref', 'format']
    return value


def scientific_request_schema():
    from .native_lumpy_execution import lumpy_execution_schema
    return _compact_files(lumpy_execution_schema('Request'))


def resource_assignment_schema(resource_id, *, selected=True, bindings=None):
    ordinal = {'type': 'integer', 'minimum': 0}
    if bindings is not None:
        from .native_lumpy_execution import validate_lumpy_bindings
        ordinal['enum'] = list(range(len(validate_lumpy_bindings(bindings))))
    predicates = [obj({'kind': {'const': 'requested_job_handoff'}}),
        obj({'kind': {'const': 'requested_job_outputs'}, 'output_roles': {
            'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': {'enum': list(OUTPUT_ROLES)}}})]
    schema = obj({'version': {'const': ASSIGNMENT_VERSION}, 'resource_id': {'const': resource_id},
        'resource_kind': {'const': 'local'}, 'binding_ordinal_0based': ordinal,
        'endpoint': {'enum': ['usable_handoff', 'completed_job_outputs']}, 'request': scientific_request_schema(),
        'progress_requirements': {'type': 'array', 'items': obj({'key': deepcopy(_TEXT),
            'credit': {'type': 'number', 'minimum': 0}, 'predicate': {'anyOf': predicates}})},
        'completion_keys': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': deepcopy(_TEXT)},
        'constraints': {'type': 'object'}})
    if not selected:
        schema['required'].remove('resource_id')
    from .launch_instructions import SELECTION_SCHEMA
    schema['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
    return schema


def launch_assignment_schema(resources):
    schema = obj({'version': {'const': LAUNCH_VERSION}, 'requests': {'type': 'object',
        'properties': {key: resource_assignment_schema(key, selected=False, bindings=value['native_lumpy'])
            for key, value in resources.items() if value.get('native_lumpy')},
        'minProperties': 1, 'additionalProperties': False}, 'constraints': {'type': 'object'}})
    from .launch_instructions import SELECTION_SCHEMA
    schema['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
    return schema


def validate_compact_assignment(value, resource_id, *, bindings=None):
    value = checked(value, resource_assignment_schema(resource_id, selected='resource_id' in value,
        bindings=bindings), 'lumpy_request_invalid_assignment')
    _require(type(value['binding_ordinal_0based']) is int, 'invalid_assignment')
    keys = [row['key'] for row in value['progress_requirements']]
    _require(len(keys) == len(set(keys)) and set(value['completion_keys']) <= set(keys), 'completion_keys_conflict')
    endpoint = 'requested_job_handoff' if value['endpoint'] == 'usable_handoff' else 'requested_job_outputs'
    _require(any(row['key'] in value['completion_keys'] and row['predicate']['kind'] == endpoint
        for row in value['progress_requirements']), 'endpoint_requirement_missing')
    return value


def _files(request):
    for signal in request['signals']:
        yield signal, 'bam', signal['signal_key'] + ':bam'
        if signal['kind'] == 'paired_end':
            yield signal, 'histogram', signal['signal_key'] + ':histogram'


def _scientific_file_view(request):
    request = deepcopy(request)
    for signal, key, _ in _files(request):
        signal[key] = {field: signal[key][field] for field in ('artifact_ref', 'format')}
    return request


def scientific_job_view(job):
    from .native_lumpy_execution import validate_lumpy_native_job
    job = validate_lumpy_native_job(plain(job))
    return _scientific_file_view(job['request'])


def select_lumpy_execution_values(value):
    """Recognize exact LUMPY metadata before generic execution presentation."""
    if not isinstance(value, Mapping):
        return None
    from .native_lumpy_execution import (
        REQUEST_VERSION, PLAN_VERSION, validate_lumpy_bindings, validate_lumpy_request,
        validate_lumpy_requested_job, validate_lumpy_run_plan,
    )
    value = plain(value)
    try:
        if set(value) == {'argv', 'environment', 'native_lumpy'}:
            job = validate_lumpy_requested_job(value)['native_lumpy']
            return {'native_lumpy': {'request': scientific_job_view(job)}}
        if set(value) == {'request', 'software', 'input_bindings'}:
            return {'request': scientific_job_view(value)}
        if value.get('version') == PLAN_VERSION:
            plan = validate_lumpy_run_plan(value)
            return {'request': scientific_job_view(plan['requested_job']['native_lumpy'])}
        if value.get('version') == REQUEST_VERSION:
            try:
                native = validate_lumpy_request(value)
            except ValueError:
                return checked(value, scientific_request_schema(), 'lumpy_presentation_invalid')
            return _scientific_file_view(native)
        if (set(value) == {'request'} and isinstance(value['request'], dict)
                and value['request'].get('version') == REQUEST_VERSION):
            selected = select_lumpy_execution_values(value['request'])
            return None if selected is None else {'request': selected}
        if is_compact_assignment(value):
            return validate_compact_assignment(value, value['resource_id'])
        if set(value) == {'operation', 'mode', 'software'}:
            binding, = validate_lumpy_bindings([value])
            return {key: binding[key] for key in ('operation', 'mode')}
    except (ValueError, TypeError, KeyError, IndexError, RecursionError):
        return None
    return None


def validate_lumpy_job_inputs(store, context, assignment, *, reference_access):
    if not (type(assignment) is dict and type(assignment.get('requested_job')) is dict
            and 'native_lumpy' in assignment['requested_job']):
        return []
    from .native_lumpy_execution import validate_lumpy_requested_job
    job = validate_lumpy_requested_job(assignment['requested_job'])['native_lumpy']
    for binding in job['input_bindings']:
        _identity(binding['file'])
    return validate_received_native_file_inputs(store, context, job['input_bindings'],
        metadata_source_refs=[], reference_access=reference_access, failure_prefix='lumpy_input_')


def _materialize(store, row):
    from .native_atac_differential_contracts import _dependency_roots
    from .native_lumpy_execution import requested_job_from_lumpy, validate_lumpy_request
    selection = row['selection']
    request, bindings = deepcopy(selection['request']), []
    occurrences = list(_files(request))
    _require(len(occurrences) == len(row['input_files']), 'input_selection_conflict')
    for (signal, key, input_key), file in zip(occurrences, row['input_files']):
        _require(signal[key] == {field: file[field] for field in ('artifact_ref', 'format')}, 'input_selection_conflict')
        metadata = _metadata(store, file['artifact_ref'])
        _require(file['artifact_ref'] == 'artifact_' + metadata['sha256']
            and metadata['sha256'] == file['sha256'] and metadata['size'] == file['size_bytes'], 'input_metadata_conflict')
        signal[key] = deepcopy(file)
        bindings.append(dict(input_key=input_key, file=deepcopy(file),
            path=str(Path(row['store_path']) / 'artifacts' / file['sha256'][:2] / file['sha256'])))
    request = validate_lumpy_request(request)
    software, root = row['binding']['software'], Path(row['workspace']) / '.lumpy-selected-runtime' / row['assignment_id']
    driver = software['driver_runtime']
    environment = dict(PATH='/usr/bin:/bin', LC_ALL='C.UTF-8',
        PYTHONHOME=str(Path(driver['python_executable']).parent.parent),
        PYTHONPATH=os.pathsep.join([driver['module_root'], *_dependency_roots(driver)]),
        PYTHONNOUSERSITE='1', PYTHONSAFEPATH='1', PYTHONDONTWRITEBYTECODE='1',
        OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', TMP=str(root / 'tmp'), TEMP=str(root / 'tmp'),
        TMPDIR=str(root / 'tmp'), XDG_CACHE_HOME=str(root / 'cache'), PIP_CACHE_DIR=str(root / 'cache/pip'))
    requested = requested_job_from_lumpy(dict(request=request, software=deepcopy(software), input_bindings=bindings),
        environment=environment)
    assignment = dict(version='practical_assignment_v1', assignment_id=row['assignment_id'],
        resource_id=row['resource_id'], resource_kind='local', workspace=row['workspace'],
        endpoint=selection['endpoint'], requested_job=requested,
        progress_requirements=deepcopy(selection['progress_requirements']), completion_keys=deepcopy(selection['completion_keys']),
        initial_context=dict(revision=0, cwd=row['workspace'], environment={}), inventory_snapshot={},
        constraints=deepcopy(selection['constraints']))
    if 'launch_instructions' in selection:
        assignment['launch_instructions'] = deepcopy(selection['launch_instructions'])
    return validate_assignment(assignment)


def read_request_binding(store, run_id, episode_id):
    _require(store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (_TABLE,)).fetchone()
        is not None, 'original_control_missing')
    saved = store.db.execute(f'SELECT file FROM {_TABLE} WHERE run_id=? AND episode_id=?',
        (run_id, episode_id)).fetchone()
    _require(saved is not None, 'original_control_missing')
    file = json.loads(saved['file'])
    _require(file['format'] == CONTROL_VERSION, 'control_format_conflict')
    raw = retained_native_file(store, file).read_bytes()
    value = json.loads(raw)
    _require(raw == canonical(value).encode() and value['version'] == CONTROL_VERSION
        and value['run_id'] == run_id and value['episode_id'] == episode_id, 'control_identity_conflict')
    context = BindingContext(**value['context'])
    custody = AppServiceCustody(store, run_id)
    custody.authenticate(context, allow_unsaved=True)
    _require(is_compact_launch(plain(context.assignment)) if context.role == 'launch' else
        context.role == 'launch_local' and is_compact_assignment(plain(context.assignment)), 'original_context_conflict')
    for row in value['requests']:
        _require(canonical(_materialize(store, row)) == canonical(row['assignment']), 'materialization_conflict')
    if context.role == 'launch':
        original = plain(context.assignment)
        _require(set(original['requests']) == {row['resource_id'] for row in value['requests']}, 'selection_conflict')
        for row in value['requests']:
            _require(canonical(row['selection']) == canonical({**original['requests'][row['resource_id']],
                'resource_id': row['resource_id']}), 'selection_conflict')
    else:
        parent, _ = _lumpy_resource_commission(custody, context)
        original = read_request_binding(store, run_id, parent.episode_id)
        _require(value['parent_file'] == original['file'] and len(value['requests']) == 1, 'parent_control_conflict')
        row = value['requests'][0]
        _require(canonical(row['selection']) == canonical(plain(context.assignment))
            and any(canonical(row) == canonical(candidate) for candidate in original['requests']), 'selection_conflict')
    return {**deepcopy(value), 'file': file}


def materialized_assignment(store, context):
    control = read_request_binding(store, context.run_id, context.episode_id)
    _require(canonical(control['context']) == canonical(context.as_record()) and len(control['requests']) == 1,
        'original_context_conflict')
    return deepcopy(control['requests'][0]['assignment'])


def practical_outcome_view(receipt):
    """Project only this LUMPY resource episode's native caller result."""
    if receipt is None:
        return None
    job = receipt['outcome'].get('facts', {}).get('requested_job')
    native = receipt['outcome'].get('native_outcome') or {}
    failure = native.get('failure') or {}
    return dict(version=PUBLIC_OUTCOME_VERSION, operation=receipt['tool_name'],
        job=None if job is None else {key: job[key] for key in ('status', 'returncode')},
        failure={key: failure[key] for key in ('code', 'exception_type', 'errno') if key in failure} or None,
        validations=[{'key': row['key'], 'satisfied': row['satisfied']} for row in receipt['validations']])


def match_practical_public_outcome(value, receipt, reference):
    value = deepcopy(plain(value))
    if 'pending_work_after_action' in value:
        from .waiting import validate_pending
        validate_pending(value.pop('pending_work_after_action'))
    _require(canonical(value) == canonical(dict(status='completed', record_refs=[reference],
        changed_record_refs=[reference], result=practical_outcome_view(receipt))), 'public_outcome_conflict')


class LumpyRequestBindings:
    """Private LUMPY launch and resource bindings."""
    def __init__(self, owner):
        self.owner, self.store = owner, owner.store

    def validate_practical_history(self, context, practical_context, practical):
        """Authenticate this LUMPY resource child's recorded VCF job receipts."""
        from .practical_receipt_information import PracticalReceiptInformation
        _require(context.role == 'launch_local' and is_compact_assignment(plain(context.assignment)),
            'resource_context_required')
        control = read_request_binding(self.store, context.run_id, context.episode_id)
        row, = control['requests']
        _require(canonical(row['assignment']) == canonical(plain(practical_context.assignment))
            and 'native_lumpy' in row['assignment']['requested_job'], 'original_practical_assignment_conflict')
        actions = list(self.store.db.execute('SELECT decision_index,result FROM runtime_actions '
            'WHERE run_id=? AND episode_id=?', (context.run_id, context.episode_id)))
        if not (practical._state_directory(practical_context) / 'assignment.json').is_file():
            _require(not actions, 'original_practical_state_missing')
            return
        state = practical.state(practical_context)
        _require(canonical(state.assignment) == canonical(row['assignment']),
            'original_practical_assignment_conflict')
        receipts = state.receipts()
        receipt_keys = {receipt['operation_key'] for receipt in receipts}
        committed = {f'{context.run_id}:{context.episode_id}:{action["decision_index"]}'
            for action in actions if action['result'] is not None
            and json.loads(action['result']).get('status') in {'completed', 'partial'}}
        _require(committed <= receipt_keys, 'original_practical_receipt_missing')
        information = PracticalReceiptInformation(self.store, context.run_id)
        for receipt in receipts:
            selected = information._selected(receipt)
            sources = information._sources(information._accession(context.episode_id, receipt['operation_key']))
            _require(len(sources) == 1 if selected['result'] is not None else len(sources) <= 1,
                'original_practical_publication_missing')
            if sources:
                body = information.read(sources[0]['id'], context.scope)
                _require(canonical(body['receipt']) == canonical(receipt), 'original_practical_receipt_conflict')

    def _write(self, context, rows, parent_file=None):
        value = dict(version=CONTROL_VERSION, run_id=context.run_id, episode_id=context.episode_id,
            context=context.as_record(), requests=rows, parent_file=parent_file)
        root = self.owner.directory / 'lumpy-request-bindings' / digest([context.run_id, context.episode_id])
        root.mkdir(parents=True, exist_ok=True)
        immutable(root / 'materialization.json', value)
        file = capture_native_file(self.store, directory=str(root), relative_path='materialization.json', format=CONTROL_VERSION)
        with self.store.transaction():
            self.store.db.execute(f'''CREATE TABLE IF NOT EXISTS {_TABLE} (
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL, file TEXT NOT NULL,
                PRIMARY KEY(run_id,episode_id))''')
            old = self.store.db.execute(f'SELECT file FROM {_TABLE} WHERE run_id=? AND episode_id=?',
                (context.run_id, context.episode_id)).fetchone()
            if old is None:
                self.store.db.execute(f'INSERT INTO {_TABLE} VALUES(?,?,?)',
                    (context.run_id, context.episode_id, canonical(file)))
            else:
                _require(canonical(json.loads(old['file'])) == canonical(file), 'control_identity_conflict')
        return read_request_binding(self.store, context.run_id, context.episode_id)

    def _row(self, context, resource_id, supplied):
        from .native_lumpy_execution import validate_lumpy_bindings
        configuration = self.owner.resources[resource_id]
        bindings = validate_lumpy_bindings(configuration.get('native_lumpy', []))
        selection = validate_compact_assignment({**supplied, 'resource_id': resource_id}, resource_id, bindings=bindings)
        known, _ = received_file_context(self.store, context, failure_prefix='lumpy_input_')
        files, versions = [], []
        for signal, key, _ in _files(selection['request']):
            selected = signal[key]
            reference = selected['artifact_ref']
            _require(reference in known, 'input_not_received')
            _require(self.owner.resolve_received_reference(context, reference, None) is not False, 'protected_reference_denied')
            record = self.store.get(reference)
            _require(record['record_type'] == 'artifact' and record['id'] == reference, 'artifact_required')
            metadata = _metadata(self.store, reference)
            _require(reference == 'artifact_' + metadata['sha256'], 'artifact_identity_conflict')
            files.append(dict(artifact_ref=reference, sha256=metadata['sha256'], size_bytes=metadata['size'], format=selected['format']))
            version = dict(reference=reference, version=None, content_sha256=metadata['sha256'])
            if version not in versions:
                versions.append(version)
        row = dict(resource_id=resource_id, selection=selection,
            binding=deepcopy(bindings[selection['binding_ordinal_0based']]), workspace=configuration['workspace'],
            store_path=str(self.store.path), assignment_id=digest(dict(run_id=context.run_id, episode_id=context.episode_id,
                resource_id=resource_id, selection=selection)), input_files=files, input_versions=versions)
        row['assignment'] = _materialize(self.store, row)
        self.owner._validate_request(row['assignment'], resource_id=resource_id)
        self.owner._lumpy_inputs(context, row['assignment'])
        self.owner._versions(versions, context.scope, context=context, lumpy_assignments=[row['assignment']])
        return row

    def preview(self, parent, selection):
        value = checked(selection, launch_assignment_schema(self.owner.resources), 'lumpy_request_invalid_launch')
        self.owner._constraints(value['constraints'])
        rows = [self._row(parent, key, request) for key, request in value['requests'].items()]
        return value, rows

    def _recorded_control(self, context):
        exists = self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (_TABLE,)).fetchone()
        saved = None if exists is None else self.store.db.execute(
            f'SELECT 1 FROM {_TABLE} WHERE run_id=? AND episode_id=?', (context.run_id, context.episode_id)).fetchone()
        if saved is not None:
            return read_request_binding(self.store, context.run_id, context.episode_id)
        custody = AppServiceCustody(self.store, context.run_id)
        custody.authenticate(context, allow_unsaved=True)
        root = self.owner.directory / 'lumpy-request-bindings' / digest([context.run_id, context.episode_id])
        previous = read_control(root / 'materialization.json')
        if previous is not None:
            _require(canonical(previous['context']) == canonical(context.as_record()), 'original_context_conflict')
            return self._write(context, previous['requests'], previous['parent_file'])
        return None

    def initialize_launch(self, context):
        """Build this launch episode's LUMPY request control before decisions."""
        _require(context.role == 'launch' and is_compact_launch(plain(context.assignment)),
            'launch_context_required')
        recorded = self._recorded_control(context)
        if recorded is not None:
            return recorded
        root = self.owner.directory / 'lumpy-request-bindings' / digest([context.run_id, context.episode_id])
        practical = self.owner.directory / 'practical-execution' / digest(dict(run_id=context.run_id, episode_id=context.episode_id))
        _require(not root.exists() and not practical.exists() and all(self.store.db.execute(
            f'SELECT 1 FROM {table} WHERE run_id=? AND episode_id=? LIMIT 1',
            (context.run_id, context.episode_id)).fetchone() is None for table in
            ('runtime_actions', 'runtime_model_calls', 'runtime_forms', 'runtime_observations')), 'original_control_missing')
        _, rows = self.preview(context, plain(context.assignment))
        return self._write(context, rows)

    def initialize_resource(self, context):
        """Bind this LUMPY resource episode to its selected launch request."""
        _require(context.role == 'launch_local' and is_compact_assignment(plain(context.assignment)),
            'resource_context_required')
        recorded = self._recorded_control(context)
        if recorded is not None:
            return recorded
        root = self.owner.directory / 'lumpy-request-bindings' / digest([context.run_id, context.episode_id])
        practical = self.owner.directory / 'practical-execution' / digest(dict(run_id=context.run_id, episode_id=context.episode_id))
        _require(not root.exists() and not practical.exists() and all(self.store.db.execute(
            f'SELECT 1 FROM {table} WHERE run_id=? AND episode_id=? LIMIT 1',
            (context.run_id, context.episode_id)).fetchone() is None for table in
            ('runtime_actions', 'runtime_model_calls', 'runtime_forms', 'runtime_observations')), 'original_control_missing')
        custody = AppServiceCustody(self.store, context.run_id)
        parent, _ = _lumpy_resource_commission(custody, context)
        original = read_request_binding(self.store, context.run_id, parent.episode_id)
        row, = [row for row in original['requests'] if row['resource_id'] == plain(context.assignment)['resource_id']]
        _require(canonical(plain(context.assignment)) == canonical(row['selection']), 'selection_conflict')
        return self._write(context, [row], original['file'])


_DESCRIPTION = 'Run LUMPY on supplied paired-end or split-read evidence and retain native structural-variant calls.'
_INSTRUCTIONS = (
    'Use the supplied signal BAM Files, paired-end insert-size histograms, sample labels, read-group filters and '
    'explicit settings with the selected local LUMPY installation. Run one selected caller command. Preserve the '
    'native VCF, original BAM headers, stderr and execution seal from that original attempt, including useful '
    'partial output after failure. Caller exit status and output validity are separate facts. Use the existing '
    'VCF result tool for later interpretation and saved calculations. Preserve native signed lengths, support '
    'counts, confidence offsets, missing genotypes and sample/reference associations. Unknown reference build '
    'and biological sample identity stay unknown. Read extraction, filtering and annotation require separate '
    'explicit selections.'
)


def lumpy_tool_contracts(bindings, *, resource_kind, resource_id):
    from .native_lumpy_execution import OPERATION, validate_lumpy_bindings
    _require(resource_kind == 'local' and type(resource_id) is str and bool(resource_id), 'local_resource_required')
    bindings = validate_lumpy_bindings(bindings)
    if not bindings:
        return []
    return [dict(name=OPERATION, description=_DESCRIPTION, resources='local', instructions=_INSTRUCTIONS,
        input_schema=resource_assignment_schema(resource_id, bindings=bindings),
        invocation_route=dict(kind='commission', routes=[dict(entry_role='launch', resource_id=resource_id,
            resource_role='launch_local')]))]


__all__ = ['ASSIGNMENT_VERSION', 'LAUNCH_VERSION', 'CONTROL_VERSION', 'PUBLIC_OUTCOME_VERSION', 'OUTPUT_ROLES',
    'is_compact_assignment', 'is_compact_launch', 'scientific_request_schema', 'resource_assignment_schema',
    'launch_assignment_schema', 'validate_compact_assignment', 'scientific_job_view', 'select_lumpy_execution_values',
    'validate_lumpy_job_inputs',
    'read_request_binding', 'materialized_assignment', 'practical_outcome_view', 'match_practical_public_outcome',
    'LumpyRequestBindings', 'lumpy_tool_contracts']
