"""Opt-in practical resource specialization of the shared episode loop.

This binding supplies actual operations and validated outcomes. It never calls
a model, chooses the next operation or runs an investigation loop.
"""
from __future__ import annotations

from copy import deepcopy
import asyncio
import base64
import json
from pathlib import Path

from .communication import plain, validate_form
from .domain import validate_schema
from .practical_execution_operations import LocalPracticalOperations, confined, digest
from .practical_execution_records import (ASSIGNMENT_SCHEMA, assess_validations,
                                          validate_assignment, validate_context)
from .practical_execution_state import PracticalState


VERSION = 'practical_resource_episodes_v1'
ROLE_KINDS = {'launch_local': 'local', 'launch_hpc': 'hpc'}


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
            'additionalProperties': False}


STR = {'type': 'string', 'minLength': 1}
ENV = {'type': 'object', 'additionalProperties': {'type': 'string'}}
ARGV = {'type': 'array', 'minItems': 1, 'items': STR}


def operation_catalog(kind):
    descriptions = {
        'practical.inspect': ('Observe the assignment\'s declared file predicates now.', obj({})),
        'practical.inventory.refresh': ('Read the selected structured preparation catalog and reconcile its local mirror.',
            obj({'path': STR})),
        'practical.context.set': ('Validate and persist cwd and explicit environment for subsequent actions.',
            obj({'cwd': STR, 'environment': ENV})),
        'practical.directory.create': ('Create the selected directory in project storage.', obj({'path': STR})),
        'practical.file.write': ('Write the exact selected UTF-8 bytes in project storage.',
            obj({'path': STR, 'text': {'type': 'string'}})),
        'practical.file.read': ('Read the selected byte window with its exact offset and original bytes.',
            obj({'path': STR, 'offset': {'type': 'integer', 'minimum': 0},
                 'limit': {'type': 'integer', 'minimum': 1}})),
        'practical.command.run': ('Run one selected preparation or diagnostic command; retain its native outcome.',
            obj({'argv': ARGV, 'environment': ENV})),
        'practical.job.start': ('Start the original requested job once; return its durable native identity.', obj({})),
        'practical.job.status': ('Read the original requested job, including observable execution information.', obj({})),
        'practical.job.collect': ('Read the original job outcome and validate requested outputs.', obj({})),
    }
    if kind == 'hpc':
        descriptions['practical.job.start'] = (
            'Submit the original requested job to the selected PBS queue with explicit resources and charging account.',
            obj({'queue': STR, 'resources': {'type': 'array', 'items': STR, 'minItems': 1}}))
    description, initial = descriptions['practical.job.start']
    retry = deepcopy(initial)
    retry['properties']['retry_failed_execution_id'] = STR
    retry['required'].append('retry_failed_execution_id')
    descriptions['practical.job.start'] = (description +
        ' To retry after a confirmed failure, explicitly supply that failed execution ID; '
        'active or uncertain executions are never replaced.', {'anyOf': [initial, retry]})
    for name in ('practical.job.status', 'practical.job.collect'):
        description, original = descriptions[name]
        descriptions[name] = (description +
            ' Supply receipt_ref to observe an original execution handed off by another episode.',
            {'anyOf': [original, obj({'receipt_ref': STR})]})
    return [{'name': name, 'description': description, 'input_schema': schema}
            for name, (description, schema) in descriptions.items()]


class PracticalResourceEpisodes:
    replaces_default_instructions = True
    def __init__(self, services, *, directory, resources, initial_information=None, store=None,
                 flux_balance_input_reader=None):
        self.services, self.directory = services, Path(directory)
        self.store = store
        if flux_balance_input_reader is not None and not callable(flux_balance_input_reader):
            raise ValueError('native_flux_balance_input_reader_invalid')
        self.flux_balance_input_reader = flux_balance_input_reader
        self.resources = json.loads(json.dumps(plain(resources), allow_nan=False))
        if not self.resources or not set(self.resources) <= {'local', 'hpc'}:
            raise ValueError('explicit_practical_resources_required')
        self.initial_information = plain(initial_information or {})
        from .execution_inventory import validate_snapshot
        if not set(self.initial_information) <= set(self.resources):
            raise ValueError('initial_inventory_resource_not_bound')
        for kind, snapshot in self.initial_information.items():
            validate_snapshot(snapshot, tool_map={entry['name']: entry for entry in operation_catalog(kind)})
        self.roles = tuple(role for role, kind in ROLE_KINDS.items() if kind in resources)
        self.entry_roles = self.roles
        self._states = {}

    def _operations(self, kind):
        config = self.resources[kind]
        if kind == 'local':
            return LocalPracticalOperations(config, flux_balance_input_reader=self.flux_balance_input_reader)
        from .practical_pbs_operations import PBSPracticalOperations
        return PBSPracticalOperations(config)

    def _assignment(self, context):
        value = validate_assignment(plain(context.assignment))
        kind = ROLE_KINDS.get(context.role)
        if value['resource_kind'] != kind or kind not in self.resources:
            raise ValueError('practical_resource_assignment_mismatch')
        confined(value['workspace'], self.resources[kind]['workspace'])
        validator = getattr(self._operations(kind), 'validate_assignment', None)
        if validator is not None:
            validator(value)
        if value['inventory_snapshot']:
            from .execution_inventory import validate_snapshot
            validate_snapshot(value['inventory_snapshot'],
                tool_map={entry['name']: entry for entry in operation_catalog(kind)})
        return value

    def _state_directory(self, context):
        return self.directory/'practical-execution'/digest({
            'run_id': context.run_id, 'episode_id': context.episode_id})

    def initialize(self, context):
        """Explicit pre-decision baseline capture; reopening never re-probes."""
        assignment = self._assignment(context)
        directory = self._state_directory(context)
        if not directory.exists():
            operations = self._operations(assignment['resource_kind'])
            outcome = operations.initial_outcome(assignment)
            validations = assess_validations(assignment, outcome, assignment['initial_context'])
            state = PracticalState(directory, context.run_id, context.episode_id,
                assignment, initial_outcome=outcome, initial_validations=validations)
        else:
            state = PracticalState(directory, context.run_id, context.episode_id, assignment)
        self._states[context.episode_id] = state
        return state

    def state(self, context):
        if context.episode_id not in self._states:
            self._states[context.episode_id] = PracticalState(self._state_directory(context),
                context.run_id, context.episode_id, self._assignment(context))
        return self._states[context.episode_id]

    def as_record(self):
        return {'binding_id': 'practical_execution', 'version': VERSION,
            'configuration': {'resources': deepcopy(self.resources),
                              'initial_information': deepcopy(self.initial_information)}}

    def child_roles(self, role):
        return ()

    def credit_kind(self, role):
        return 'operational'

    def assignment_schema(self, role):
        return deepcopy(ASSIGNMENT_SCHEMA)

    def permitted_common_actions(self, context):
        return ('tool',)

    def allowed_children(self, parent, caller_capabilities):
        return ()

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        assignment = validate_assignment(plain(selection))
        if ROLE_KINDS.get(role) != assignment['resource_kind']:
            raise ValueError('practical_resource_assignment_mismatch')
        confined(assignment['workspace'], self.resources[assignment['resource_kind']]['workspace'])
        validator = getattr(self._operations(assignment['resource_kind']), 'validate_assignment', None)
        if validator is not None:
            validator(assignment)
        return assignment

    def initial_decision_context(self, context):
        return {'practical_resource_information': deepcopy(self.initial_information),
                'practical_resource_capabilities': [self._resource_information(kind)
                    for kind in self.resources]}

    def _resource_information(self, kind):
        config = self.resources[kind]
        return {'resource_kind': kind, 'workspace': config['workspace'],
            **{field: deepcopy(config[field]) for field in ('policy', 'account', 'python_executable')
               if field in config},
            'inventory_snapshot': deepcopy(self.initial_information.get(kind))}

    def instructions(self, context):
        return ('You own this practical execution assignment in the shared episode loop. '
            'Choose one actual operation each turn from the available catalog. Reuse, '
            'inspect, prepare or repair components as the actual situation warrants. '
            'The saved inventory describes preparations; it does not establish present usability. '
            'A subprocess cd/export does not change the next action\'s cwd/environment: '
            'use practical.context.set for a persistent change. A command can run and fail; '
            'retain that outcome and repair through later selected actions. Each executed '
            'action is validated and assessed, including at zero credit. The original requested '
            'job and endpoint remain fixed. Only authoritative endpoint validation establishes '
            'completion. Completion supplies exact zero future yield; the ordinary controller '
            'owns continuation. Do not invent a stop action, extra endpoint or action limit.')

    def decision_context(self, context, current_view):
        state = self.state(context)
        current_inventory = plain(context.assignment).get('inventory_snapshot', {})
        for receipt in reversed(state.receipts()):
            if 'inventory_snapshot' in receipt['outcome']:
                current_inventory = receipt['outcome']['inventory_snapshot']
                break
        return {'practical_assignment': plain(context.assignment),
            'practical_resource_configuration': self._resource_information(context.assignment['resource_kind']),
            'practical_working_context': state.context(),
            'practical_progress': state.credit_view(),
            'practical_yield_binding': self.practical_estimator(context).as_record(),
            'practical_completion': state.completion_proof(),
            'practical_current_inventory': current_inventory,
            'practical_initial_information': deepcopy(self.initial_information)}

    def catalog(self, context):
        return operation_catalog(self._assignment(context)['resource_kind'])

    def _received_target(self, context, reference):
        if self.store is None:
            raise ValueError('practical_handoff_store_binding_required')
        from .practical_receipt_information import PracticalReceiptInformation
        body = PracticalReceiptInformation(self.store, context.run_id).read(reference, context.scope)
        receipt = body['receipt']
        job = receipt['outcome']['facts'].get('requested_job')
        if (receipt['tool_name'] not in {'practical.job.start', 'practical.job.status', 'practical.job.collect'}
                or job is None or job['handoff'] is None
                or job['requested_job_sha256'] != digest(plain(context.assignment)['requested_job'])
                or job['resource_kind'] != context.assignment['resource_kind']):
            raise ValueError('practical_received_execution_assignment_mismatch')
        source = self.store.get(reference)
        original = json.loads(self.store.get_artifact(source['request_ref']))['assignment']
        if (plain(context.assignment).get('resource_id') != original.get('resource_id')
                and ('resource_id' in context.assignment or 'resource_id' in original)):
            raise ValueError('practical_received_execution_resource_mismatch')
        row = self.store.db.execute('SELECT settings FROM runtime_runs WHERE run_id=?',
                                   (context.run_id,)).fetchone()
        directory = self.directory if row is None else Path(json.loads(row[0])['directory'])
        origin_episode_id = body['episode_id']
        if {'native_flux_balance', 'native_lumpy'} & set(original['requested_job']):
            from .execution_progress import ExecutionTargetReader
            resource_id = original['resource_id']
            target_info = ExecutionTargetReader(self.store, run_id=context.run_id, directory=directory,
                resources={resource_id: self.resources['local']}, api_execution=None).read_target(reference, context.scope)
            original = target_info['assignment']
            origin_episode_id = target_info['origin_episode_id']
        target_directory = directory/'practical-execution'/digest({
            'run_id': context.run_id, 'episode_id': origin_episode_id})
        if not (target_directory/'assignment.json').is_file():
            raise ValueError('practical_handoff_original_state_unavailable')
        target = PracticalState(target_directory,
            context.run_id, origin_episode_id, original)
        return target, job['execution_id']

    async def execute(self, context, tool_name, arguments, operation_key):
        catalog = {entry['name']: entry for entry in self.catalog(context)}
        arguments = plain(arguments)
        received_target, expected_execution = None, None
        try:
            if tool_name not in catalog:
                raise ValueError('practical_operation_not_available')
            validate_schema(arguments, catalog[tool_name]['input_schema'])
            # Reject malformed/out-of-scope selections before freezing an
            # intent. A valid native failure remains an executed action.
            if 'path' in arguments:
                confined(arguments['path'], context.assignment['workspace'])
            if 'cwd' in arguments:
                confined(arguments['cwd'], context.assignment['workspace'])
            if 'environment' in arguments:
                validate_context({'revision': 0, 'cwd': context.assignment['workspace'],
                    'environment': arguments['environment']}, workspace=context.assignment['workspace'])
            operands = arguments
            if 'receipt_ref' in arguments:
                received_target, expected_execution = self._received_target(context, arguments['receipt_ref'])
                operands = {}
            validator = getattr(self._operations(context.assignment['resource_kind']), 'validate_action', None)
            if validator is not None:
                validator(plain(context.assignment), tool_name, operands)
        except (ValueError, TypeError) as error:
            return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': str(error)}}
        state = self.state(context)
        intent = state.begin(operation_key, tool_name, arguments)
        if intent['state'] == 'completed':
            receipt = intent['receipt']
        else:
            # Each primitive reconciles its own original native/file identity.
            # No backend is allowed to replace an uncertain native submission.
            outcome, context_after = await self._operations(context.assignment['resource_kind']).execute(
                received_target or state, tool_name, {} if received_target is not None else arguments, operation_key)
            if received_target is not None:
                actual = outcome.get('facts', {}).get('requested_job', {})
                if actual.get('execution_id') != expected_execution:
                    outcome = {'facts': {}, 'native_outcome': {'failure': {
                        'code': 'practical_received_execution_target_changed',
                        'expected_execution_id': expected_execution,
                        'observed_execution_id': actual.get('execution_id')}}}
                else:
                    # The launch need not have requested these output checks.
                    # Validate the receiver's declared predicates against the
                    # actual resource while retaining the original native job.
                    initial_arguments = {}
                    if 'native_flux_balance' in context.assignment['requested_job']:
                        from .practical_execution_records import flux_balance_role_paths
                        roles = [role for requirement in context.assignment['progress_requirements']
                            for role in requirement['predicate'].get('output_roles', [])]
                        if roles:
                            initial_arguments['flux_balance_output_paths'] = flux_balance_role_paths(
                                plain(context.assignment), actual, roles)
                    if 'native_macs2_peak' in context.assignment['requested_job']:
                        from .practical_execution_records import requested_job_role_paths
                        roles = [role for requirement in context.assignment['progress_requirements']
                            for role in requirement['predicate'].get('output_roles', [])]
                        if roles:
                            initial_arguments['macs2_peak_output_paths'] = requested_job_role_paths(
                                plain(context.assignment), actual, roles)
                    if 'native_lumpy' in context.assignment['requested_job']:
                        from .practical_execution_records import requested_job_role_paths
                        roles = list(dict.fromkeys(role for requirement in context.assignment['progress_requirements']
                            for role in requirement['predicate'].get('output_roles', [])))
                        if roles:
                            initial_arguments['lumpy_output_paths'] = requested_job_role_paths(
                                plain(context.assignment), actual, roles)
                    checked = await asyncio.to_thread(
                        self._operations(context.assignment['resource_kind']).initial_outcome,
                        plain(context.assignment), **initial_arguments)
                    outcome['facts']['paths'] = checked['facts'].get('paths', [])
                    if not {'native_flux_balance', 'native_macs2_peak', 'native_lumpy'} & set(plain(context.assignment)['requested_job']):
                        actual['output_paths'] = sorted({path for requirement in
                            plain(context.assignment)['progress_requirements']
                            if requirement['predicate']['kind'] == 'requested_job_outputs'
                            for path in requirement['predicate']['output_paths']})
                    if 'path_observation_failures' in checked:
                        outcome['path_observation_failures'] = checked['path_observation_failures']
                context_after = None
            if 'inventory_catalog' in outcome:
                from .execution_inventory import reconcile_inventory, validate_catalog
                try:
                    validate_catalog(outcome['inventory_catalog'], tool_map=catalog)
                    raw = base64.b64decode(outcome['inventory_bytes_base64'], validate=True)
                    if json.loads(raw) != outcome['inventory_catalog']:
                        raise ValueError('practical_inventory_original_bytes_mismatch')
                    outcome['inventory_snapshot'] = reconcile_inventory(
                        state.directory/'inventory-mirror.json', lambda: raw, tool_map=catalog)
                except (ValueError, TypeError, OSError) as error:
                    outcome['inventory_failure'] = {'code': 'practical_inventory_validation_or_mirror_failed',
                                                    'exception_type': type(error).__name__}
            after = state.context() if context_after is None else context_after
            validations = assess_validations(plain(context.assignment), outcome, after,
                                             tool_name=tool_name)
            receipt = state.finish(operation_key, outcome, validations, context_after=context_after)
        references = []
        if self.store is not None:
            from .practical_receipt_information import PracticalReceiptInformation
            information = PracticalReceiptInformation(self.store, context.run_id)
            references.append(information.publish(context, receipt))
        return {'status': 'completed', 'record_refs': references, 'changed_record_refs': references,
            'operation_ref': digest(operation_key), 'result': receipt}

    def completion_for_action(self, context, operation_key):
        proof = self.state(context).completion_proof()
        return proof if proof is not None and proof['operation_key'] == operation_key else None

    def practical_estimator(self, context):
        from .practical_yield import PracticalYieldEstimator
        return PracticalYieldEstimator(self.state(context).verify_completion)

    def fact_sources(self, role):
        return {'practical_completed': {'type': 'boolean', 'meaning':
                    'Whether this exact practical assignment has a persisted verified endpoint proof.'},
                'practical_receipt_digests': {'type': 'array', 'meaning':
                    'Canonical digests of this episode\'s original completed action receipts.'},
                'practical_receipt_refs': {'type': 'array', 'meaning':
                    'Scoped immutable Store sources containing original action, validation and outcome records.',
                    'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {
                        'type': 'string', 'format': 'reference',
                        'x-reference-namespace': 'practical_receipt'},
                        'x-source': 'practical_receipt_refs'}}}

    def facts(self, context, completion_snapshot):
        state = self.state(context)
        references = []
        if self.store is not None:
            from .practical_receipt_information import PracticalReceiptInformation
            information = PracticalReceiptInformation(self.store, context.run_id)
            references = [information.publish(context, receipt) for receipt in state.receipts()]
        return {'practical_completed': state.completion_proof() is not None,
            'practical_receipt_digests': [digest(receipt) for receipt in state.receipts()],
            'practical_receipt_refs': references}

    def resolve(self, context, reference, namespace):
        if self.store is not None and isinstance(reference, str) and reference.startswith('source_'):
            from .practical_receipt_information import PracticalReceiptInformation
            return PracticalReceiptInformation(self.store, context.run_id).resolve(context, reference, namespace)
        return (namespace == 'practical_receipt' and
            reference in {digest(receipt) for receipt in self.state(context).receipts()})

    def validate_report(self, context, form, original_schema):
        validate_form(form, original_schema,
                      lambda reference, namespace: self.resolve(context, reference, namespace))
        facts = self.facts(context, {})
        for name, node in original_schema.get('properties', {}).items():
            source = node.get('x-source')
            if source in facts and form[name] != facts[source]:
                raise ValueError('practical_report_disagrees_with_recorded_facts')

    def credit_view(self, context, receiver_selection):
        return self.state(context).credit_view()


__all__ = ['PracticalResourceEpisodes', 'operation_catalog', 'VERSION']
