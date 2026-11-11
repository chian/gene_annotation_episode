"""Explicit scientific MACS2 selections and private host materialization.

The model supplies received File handles and scientific associations. The host
fills only immutable File metadata, actual selected software and execution
coordinates. Existing practical records own the one original native job.
"""
from copy import deepcopy
import json
import os
from pathlib import Path

from .bvbrc_appservice_custody import AppServiceCustody
from .communication import plain
from .episode_bindings import BindingContext
from .execution_contracts import canonical, checked, digest, obj
from .genomic_overlap_result_receipts import immutable, read_control
from .native_file_capture import _metadata, capture_native_file, retained_native_file
from .practical_execution_records import validate_assignment
from .received_native_file_inputs import received_file_context


ASSIGNMENT_VERSION = 'macs2_peak_scientific_assignment_v1'
LAUNCH_VERSION = 'macs2_peak_scientific_launch_v1'
CONTROL_VERSION = 'macs2_peak_request_binding_v1'
PUBLIC_OUTCOME_VERSION = 'macs2_peak_practical_outcome_v1'
OUTPUT_ROLES = ('peaks_xls', 'narrowpeak', 'summits', 'model', 'stdout', 'stderr', 'seal')
_TABLE = 'runtime_macs2_peak_request_bindings'
_TEXT = {'type': 'string', 'minLength': 1}


def _require(condition, code):
    if not condition:
        raise ValueError('macs2_peak_request_' + code)


def _macs2_resource_commission(custody, context):
    saved = custody.store.db.execute('SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?',
        (context.run_id, context.episode_id)).fetchone()
    return custody._commission(context, unsaved=saved is None)


def is_compact_assignment(value):
    return isinstance(value, dict) and value.get('version') == ASSIGNMENT_VERSION


def is_compact_launch(value):
    return isinstance(value, dict) and value.get('version') == LAUNCH_VERSION


def scientific_request_schema():
    from .native_macs2_peak_execution import macs2_peak_execution_schema
    schema = macs2_peak_execution_schema('Request')
    schema['properties']['inputs']['items']['properties']['file'] = obj({
        'artifact_ref': {'type': 'string', 'pattern': '^artifact_[0-9a-f]{64}$'},
        'format': deepcopy(schema['properties']['inputs']['items']['properties']['file']['properties']['format'])})
    return schema


def resource_assignment_schema(resource_id, *, selected=True, bindings=None):
    ordinal = {'type': 'integer', 'minimum': 0}
    if bindings is not None:
        from .native_macs2_peak_execution import validate_macs2_peak_bindings
        ordinal['enum'] = list(range(len(validate_macs2_peak_bindings(bindings))))
    predicates = [obj({'kind': {'const': 'requested_job_handoff'}}),
        obj({'kind': {'const': 'requested_job_outputs'}, 'output_roles': {'type': 'array',
            'minItems': 1, 'uniqueItems': True, 'items': {'enum': list(OUTPUT_ROLES)}}})]
    schema = obj({'version': {'const': ASSIGNMENT_VERSION}, 'resource_id': {'const': resource_id},
        'resource_kind': {'const': 'local'}, 'binding_ordinal_0based': ordinal,
        'endpoint': {'enum': ['usable_handoff', 'completed_job_outputs']}, 'request': scientific_request_schema(),
        'progress_requirements': {'type': 'array', 'items': obj({'key': deepcopy(_TEXT),
            'credit': {'type': 'number', 'minimum': 0},
            'predicate': {'anyOf': predicates}})},
        'completion_keys': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': deepcopy(_TEXT)},
        'constraints': {'type': 'object'}})
    if not selected:
        schema['required'].remove('resource_id')
    from .launch_instructions import SELECTION_SCHEMA
    schema['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
    return schema


def launch_assignment_schema(resources):
    schema = obj({'version': {'const': LAUNCH_VERSION}, 'requests': {'type': 'object',
        'properties': {key: resource_assignment_schema(key, selected=False,
            bindings=value['native_macs2_peak']) for key, value in resources.items()
            if value.get('native_macs2_peak')}, 'minProperties': 1, 'additionalProperties': False},
        'constraints': {'type': 'object'}})
    from .launch_instructions import SELECTION_SCHEMA
    schema['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
    return schema


def validate_compact_assignment(value, resource_id, *, bindings=None):
    value = checked(value, resource_assignment_schema(resource_id, selected='resource_id' in value,
        bindings=bindings), 'macs2_peak_request_invalid_assignment')
    _require(type(value['binding_ordinal_0based']) is int, 'invalid_assignment')
    keys = [row['key'] for row in value['progress_requirements']]
    _require(len(keys) == len(set(keys)) and set(value['completion_keys']) <= set(keys), 'completion_keys_conflict')
    endpoint_kind = 'requested_job_handoff' if value['endpoint'] == 'usable_handoff' else 'requested_job_outputs'
    _require(any(row['key'] in value['completion_keys'] and row['predicate']['kind'] == endpoint_kind
        for row in value['progress_requirements']), 'endpoint_requirement_missing')
    return value


def _materialize(store, row):
    from .native_atac_differential_contracts import _dependency_roots
    from .native_macs2_peak_execution import requested_job_from_macs2_peak, validate_macs2_peak_request
    selection = row['selection']
    request = deepcopy(selection['request'])
    bindings = []
    for selected, file in zip(request['inputs'], row['input_files']):
        _require(selected['file'] == {key: file[key] for key in ('artifact_ref', 'format')}, 'input_selection_conflict')
        metadata = _metadata(store, file['artifact_ref'])
        _require(file['artifact_ref'] == 'artifact_' + metadata['sha256']
            and metadata['sha256'] == file['sha256'] and metadata['size'] == file['size_bytes'], 'input_metadata_conflict')
        selected['file'] = deepcopy(file)
        # The control fixes the original lexical location. Retained reads in an
        # owned Store clone validate metadata without rebasing native history.
        bindings.append({'input_key': selected['input_key'], 'file': deepcopy(file),
            'path': str(Path(row['store_path']) / 'artifacts' / file['sha256'][:2] / file['sha256'])})
    request = validate_macs2_peak_request(request)
    software = row['binding']['software']
    driver = software['driver_runtime']
    root = Path(row['workspace']) / '.macs2-selected-runtime' / row['assignment_id']
    environment = dict(PATH='/usr/bin:/bin', LC_ALL='C.UTF-8',
        PYTHONHOME=str(Path(driver['python_executable']).parent.parent),
        PYTHONPATH=os.pathsep.join([driver['module_root'], *_dependency_roots(driver)]),
        PYTHONNOUSERSITE='1', PYTHONSAFEPATH='1', PYTHONDONTWRITEBYTECODE='1',
        OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', TMP=str(root / 'tmp'), TEMP=str(root / 'tmp'),
        TMPDIR=str(root / 'tmp'), XDG_CACHE_HOME=str(root / 'cache'), PIP_CACHE_DIR=str(root / 'cache/pip'))
    requested = requested_job_from_macs2_peak(dict(request=request, software=deepcopy(software), input_bindings=bindings),
        environment=environment)
    assignment = dict(version='practical_assignment_v1', assignment_id=row['assignment_id'],
        resource_id=row['resource_id'], resource_kind='local', workspace=row['workspace'],
        endpoint=selection['endpoint'], requested_job=requested,
        progress_requirements=deepcopy(selection['progress_requirements']),
        completion_keys=deepcopy(selection['completion_keys']),
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
        parent, _ = _macs2_resource_commission(custody, context)
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


class Macs2PeakRequestBindings:
    """Private MACS2 peak launch and resource bindings."""
    def __init__(self, owner):
        self.owner, self.store = owner, owner.store

    def validate_practical_history(self, context, practical_context, practical):
        """Authenticate this MACS2 resource child's recorded peak job receipts."""
        from .practical_receipt_information import PracticalReceiptInformation
        _require(context.role == 'launch_local' and is_compact_assignment(plain(context.assignment)),
            'resource_context_required')
        control = read_request_binding(self.store, context.run_id, context.episode_id)
        row, = control['requests']
        _require(canonical(row['assignment']) == canonical(plain(practical_context.assignment))
            and 'native_macs2_peak' in row['assignment']['requested_job'],
            'original_practical_assignment_conflict')
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
        root = self.owner.directory / 'macs2-request-bindings' / digest([context.run_id, context.episode_id])
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
        configuration = self.owner.resources[resource_id]
        from .native_macs2_peak_execution import validate_macs2_peak_bindings
        bindings = validate_macs2_peak_bindings(configuration.get('native_macs2_peak', []))
        selection = validate_compact_assignment({**supplied, 'resource_id': resource_id}, resource_id, bindings=bindings)
        known, _ = received_file_context(self.store, context, failure_prefix='macs2_peak_input_')
        files, versions = [], []
        for selected in selection['request']['inputs']:
            reference = selected['file']['artifact_ref']
            _require(reference in known, 'input_not_received')
            _require(self.owner._atac_reference_access(context, reference, None) is not False, 'protected_reference_denied')
            record = self.store.get(reference)
            _require(record['record_type'] == 'artifact' and record['id'] == reference, 'artifact_required')
            metadata = _metadata(self.store, reference)
            _require(reference == 'artifact_' + metadata['sha256'], 'artifact_identity_conflict')
            # Format is an explicit scientific label; AUTO remains the native
            # detector. Store media_type is not inferred to be BED/BAM.
            files.append(dict(artifact_ref=reference, sha256=metadata['sha256'], size_bytes=metadata['size'],
                format=selected['file']['format']))
            version = dict(reference=reference, version=None, content_sha256=metadata['sha256'])
            if version not in versions:
                versions.append(version)
        row = dict(resource_id=resource_id, selection=selection,
            binding=deepcopy(bindings[selection['binding_ordinal_0based']]), workspace=configuration['workspace'],
            store_path=str(self.store.path), assignment_id=digest(dict(run_id=context.run_id, episode_id=context.episode_id,
                resource_id=resource_id, selection=selection)), input_files=files, input_versions=versions)
        row['assignment'] = _materialize(self.store, row)
        self.owner._validate_request(row['assignment'], resource_id=resource_id)
        self.owner._macs2_peak_inputs(context, row['assignment'])
        self.owner._versions(versions, context.scope, context=context, macs2_peak_assignments=[row['assignment']])
        return row

    def preview(self, parent, selection):
        value = checked(selection, launch_assignment_schema(self.owner.resources), 'macs2_peak_request_invalid_launch')
        self.owner._constraints(value['constraints'])
        rows = [self._row(parent, key, request) for key, request in value['requests'].items()]
        return value, rows

    def _recorded_control(self, context):
        exists = self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (_TABLE,)).fetchone()
        saved = (None if exists is None else self.store.db.execute(
            f'SELECT 1 FROM {_TABLE} WHERE run_id=? AND episode_id=?',
            (context.run_id, context.episode_id)).fetchone())
        if saved is not None:
            return read_request_binding(self.store, context.run_id, context.episode_id)
        custody = AppServiceCustody(self.store, context.run_id)
        custody.authenticate(context, allow_unsaved=True)
        root = self.owner.directory / 'macs2-request-bindings' / digest([context.run_id, context.episode_id])
        previous = read_control(root / 'materialization.json')
        if previous is not None:
            _require(canonical(previous['context']) == canonical(context.as_record()), 'original_context_conflict')
            return self._write(context, previous['requests'], previous['parent_file'])
        return None

    def initialize_launch(self, context):
        """Build this launch episode's MACS2 peak request control."""
        _require(context.role == 'launch' and is_compact_launch(plain(context.assignment)),
            'launch_context_required')
        recorded = self._recorded_control(context)
        if recorded is not None:
            return recorded
        root = self.owner.directory / 'macs2-request-bindings' / digest([context.run_id, context.episode_id])
        practical = self.owner.directory / 'practical-execution' / digest(dict(run_id=context.run_id, episode_id=context.episode_id))
        _require(not root.exists() and not practical.exists() and all(self.store.db.execute(
            f'SELECT 1 FROM {table} WHERE run_id=? AND episode_id=? LIMIT 1',
            (context.run_id, context.episode_id)).fetchone() is None for table in
            ('runtime_actions', 'runtime_model_calls', 'runtime_forms', 'runtime_observations')), 'original_control_missing')
        _, rows = self.preview(context, plain(context.assignment))
        return self._write(context, rows)

    def initialize_resource(self, context):
        """Bind this MACS2 resource episode to its selected launch request."""
        _require(context.role == 'launch_local' and is_compact_assignment(plain(context.assignment)),
            'resource_context_required')
        recorded = self._recorded_control(context)
        if recorded is not None:
            return recorded
        root = self.owner.directory / 'macs2-request-bindings' / digest([context.run_id, context.episode_id])
        practical = self.owner.directory / 'practical-execution' / digest(dict(run_id=context.run_id, episode_id=context.episode_id))
        _require(not root.exists() and not practical.exists() and all(self.store.db.execute(
            f'SELECT 1 FROM {table} WHERE run_id=? AND episode_id=? LIMIT 1',
            (context.run_id, context.episode_id)).fetchone() is None for table in
            ('runtime_actions', 'runtime_model_calls', 'runtime_forms', 'runtime_observations')), 'original_control_missing')
        custody = AppServiceCustody(self.store, context.run_id)
        parent, _ = _macs2_resource_commission(custody, context)
        original = read_request_binding(self.store, context.run_id, parent.episode_id)
        selection = plain(context.assignment)
        row, = [row for row in original['requests'] if row['resource_id'] == selection['resource_id']]
        _require(canonical(selection) == canonical(row['selection']), 'selection_conflict')
        return self._write(context, [row], original['file'])


__all__ = ['ASSIGNMENT_VERSION', 'LAUNCH_VERSION', 'CONTROL_VERSION', 'PUBLIC_OUTCOME_VERSION', 'OUTPUT_ROLES',
    'is_compact_assignment', 'is_compact_launch', 'scientific_request_schema', 'resource_assignment_schema',
    'launch_assignment_schema', 'validate_compact_assignment', 'read_request_binding',
    'materialized_assignment', 'practical_outcome_view', 'match_practical_public_outcome', 'Macs2PeakRequestBindings']
