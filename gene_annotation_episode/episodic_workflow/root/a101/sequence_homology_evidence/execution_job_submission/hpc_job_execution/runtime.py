"""A101 HPC job execution on the generic runner (``episode_runtime``).

One Episode gets one commissioned practical job (``practical_assignment_v1``,
``resource_kind`` ``hpc``) executing on the configured PBS resource reached
through its existing SSH transport. Each unit is one ``exec_command`` the model
writes (shell code on the resource, or on the coordinator for transfers),
executed by A101's ``TerminalExecution`` with the immutable intent/receipt
custody of ``PracticalState``. Every executed command, including a failed one,
is one unit; its receipt is published to the run's shared Store as a
``source`` record and enters the iterator with the credit measured after it.
A model response that fails admission (schema, duplicate environment name, a
workdir outside the workspace) creates no unit; the model decides again with
that feedback.

Credit is the assignment's own practical requirement credit
(``project_practical_credit``): the sum of the credits of its currently
satisfied ``progress_requirements``, validated from the actual command facts.
It is never bounded, clamped or rescaled. Continuation is the completion yield
controller toward the assignment's own finite target, the total credit of its
requirements, with the ``continuation`` collaborator's ``cutoff`` and
``parameters`` for this binding path. Once ``PracticalState`` holds a
completion proof for the assignment's endpoint it admits no further command,
so the source has no further unit.

The A101 ``hpc_job_execution`` binding (below the head) mixes in
``HpcJobExecutionRuntime``; ``a101_home_factory`` constructs it (``construct``)
with its own ``HpcJobTools`` over the shared Store and the axis's frozen
``LaunchInstructions``.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path, PurePosixPath

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import Field, RecordForm
from method_loop import Episode, Leaf

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.state import Store

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.sequence_homology_evidence.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import LaunchInstructions
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.practical_execution_records import assess_validations, validate_assignment
from gene_annotation_episode.episodic_workflow.episode_support.jobs.sequence_homology_evidence.practical_execution_state import PracticalState
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.sequence_homology_evidence.terminal_execution import TerminalExecution
from gene_annotation_episode.episodic_workflow.episode_support.findings.sequence_homology_evidence.terminal_scientific_evidence import finalize_scientific_command, terminal_artifact_paths
from ...contract_binding import AXIS, RETURN_FORM, SCOPE, Record

MODEL_ROLE = 'REASONING'
TOOL = 'exec_command'
RECEIPT_PROVIDER = 'episode.practical_receipt'
RECEIPT_VERSION = 'practical_receipt_information_v1'
CONTINUATION_FIELDS = frozenset({'cutoff', 'parameters'})

JOB = Field('record', 'The practical_assignment_v1 job the commissioning launch parent hands over: resource_kind '
                      'hpc, resource_id of the chosen resource, workspace under the configured resource workspace, '
                      'requested_job, progress_requirements, completion_keys, initial_context, inventory_snapshot '
                      'and constraints')
# The assignment field that carries the job, and A101's form for this binding.
JOB_FIELD = 'job'
ASSIGNMENT_FORM = RecordForm({'scope': SCOPE, JOB_FIELD: JOB})


def returned(credit, finding):
    """The binding's result record in A101's return form."""
    return Record({'credit': credit, 'finding': finding})

INSTRUCTIONS = (
    "You are the execution agent for the actual job and resource assigned below. Use exec_command to write and "
    "run the shell code needed for that job. Choose scripts, environment preparation, software invocation and "
    "recovery from the actual resource instructions and observed results. No sequence of setup or job-stage "
    "operations is prescribed. Preserve the caller's scientific inputs, desired outputs and acceptance criteria. "
    "Historical inventory is context, not proof of present usability. Each command is one ordinary episode "
    "action: its actual result and earned credit enter the iterator, including failure or zero progress. Host "
    "bookkeeping records command versions and actual native job identities; do not maintain a parallel receipt "
    "ledger. If a submission outcome is uncertain, investigate that original submission rather than create a "
    "duplicate. Use the provided resource-specific instructions, account, storage and existing authentication "
    "route. workdir and env apply to the selected command only. target=resource runs on the assigned resource; "
    "target=coordinator runs in the local run directory for supplied-input and transport work. Both are ordinary "
    "journaled actions; resource computation belongs on its actual allocation. For coordinator-side transfers, "
    "execution_resource.ssh_argv is the exact configured transport prefix. Append the remote shell command as its "
    "final argument and preserve stdin. target=resource uses that transport directly. The episode iterator "
    "decides continuation from credit; add no stopping budget. Return exactly one command: cmd is its argv (use "
    "[\"/bin/bash\", \"-c\", <script>] for shell code), env lists the environment variables it sets.")

ACTION_SCHEMA = {
    'type': 'object', 'additionalProperties': False, 'required': ['cmd', 'workdir', 'target', 'env'],
    'properties': {
        'cmd': {'type': 'array', 'minItems': 1, 'items': {'type': 'string', 'minLength': 1},
                'description': 'The argv of the one command to execute.'},
        'workdir': {'type': 'string', 'minLength': 1,
                    'description': 'Absolute working directory inside the target workspace.'},
        'target': {'enum': ['resource', 'coordinator'],
                   'description': 'resource: the assigned HPC resource; coordinator: the local run directory.'},
        'env': {'type': 'array', 'description': 'Environment variables this command sets.',
                'items': {'type': 'object', 'additionalProperties': False, 'required': ['name', 'value'],
                          'properties': {'name': {'type': 'string', 'minLength': 1},
                                         'value': {'type': 'string'}}}},
    },
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _plain(value):
    return json.loads(canonical(value))


class HpcJobTools:
    """The binding's own tool registry: ``exec_command`` on its configured PBS resource, over the shared Store."""

    def __init__(self, store, *, resource, directory):
        if not isinstance(store, Store):
            raise ContractError('a101_hpc_job_tools_require_the_shared_store')
        if not isinstance(resource, Mapping) or resource.get('kind') != 'pbs_ssh':
            raise ContractError('a101_hpc_job_resource_must_be_a_pbs_ssh_configuration')
        self.store, self.resource = store, _plain(dict(resource))
        self.directory = Path(directory).resolve()
        self.operations = TerminalExecution(self.resource, coordinator_workspace=self.directory,
                                            artifact_selector=terminal_artifact_paths)

    def catalog(self, scope=None):
        return {TOOL: {'name': TOOL, 'description': 'Execute the shell command you write on the assigned resource '
                       '(or the coordinator run directory); returns its actual output and saved action receipt.',
                       'input_schema': deepcopy(ACTION_SCHEMA)}}

    def resource_information(self):
        """What the model may know about the configured resource (no credentials are configured here)."""
        return {name: deepcopy(self.resource[name])
                for name in ('kind', 'workspace', 'account', 'ssh_argv', 'python_executable', 'scheduler')}

    def state(self, bound, job):
        """This Episode's immutable intent/receipt custody, opened once for its own run, episode and job."""
        directory = self.directory / 'practical-execution' / digest({'run_id': bound.run_id,
                                                                    'episode_id': bound.episode_id})
        initial = None if (directory / 'assignment.json').is_file() else self.operations.initial_outcome(job)
        return PracticalState(directory, bound.run_id, bound.episode_id, job, initial_outcome=initial)

    def validate_job(self, job):
        job = validate_assignment(_plain(dict(job)))
        if job['resource_kind'] != 'hpc':
            raise ContractError('a101_hpc_job_execution_requires_an_hpc_job')
        return self.operations.validate_assignment(job)

    def admit_arguments(self, job, selection):
        """The ``exec_command`` arguments of one admitted model selection; raises when the selection is refused."""
        Draft202012Validator(ACTION_SCHEMA).validate(selection)
        env = {}
        for item in selection['env']:
            if item['name'] in env:
                raise ValueError('exec_command_environment_name_repeats:' + item['name'])
            env[item['name']] = item['value']
        arguments = {'cmd': list(selection['cmd']), 'workdir': selection['workdir'], 'env': env,
                     'target': selection['target']}
        self.operations.validate_action(job, TOOL, arguments)
        return arguments

    async def execute_async(self, state, scope, arguments, operation_key):
        """Execute one admitted command (once per operation key) and publish its receipt to the Store."""
        intent = state.begin(operation_key, TOOL, arguments)
        if intent['state'] == 'completed':
            receipt = intent['receipt']
        else:
            try:
                outcome, _ = await self.operations.execute(state, TOOL, arguments, operation_key)
            except (ValueError, TypeError, OSError, AcquisitionError) as error:
                outcome = {'facts': {}, 'native_outcome': {'failure': {
                    'code': 'execution_action_failed', 'exception_type': type(error).__name__, 'detail': str(error)}}}
            outcome = finalize_scientific_command(state.assignment, arguments, outcome)
            before = state.context()
            after = deepcopy(before)
            if (arguments['target'] == 'resource'
                    and PurePosixPath(arguments['workdir']).is_relative_to(state.assignment['workspace'])):
                after.update({'cwd': arguments['workdir'], 'environment': arguments['env']})
            after['revision'] += int(any(after[name] != before[name] for name in ('cwd', 'environment')))
            validations = assess_validations(state.assignment, outcome, after, tool_name=TOOL)
            receipt = state.finish(operation_key, outcome, validations, context_after=after)
        return receipt, self.publish(state, scope, receipt)

    def publish(self, state, scope, receipt):
        """The receipt's ``source`` record in the shared Store (content-addressed, so republishing is idempotent)."""
        body = {'version': RECEIPT_VERSION, 'run_id': state.run_id, 'episode_id': state.episode_id,
                'assignment_sha256': state.assignment_sha256, 'scope': scope, 'receipt': receipt}
        snapshot = {'version': 'practical_receipt_assignment_v1', 'run_id': state.run_id,
                    'episode_id': state.episode_id, 'scope': scope, 'assignment': state.assignment}
        with self.store.transaction():
            artifact = self.store.artifact(canonical(body), 'application/json')
            request = self.store.artifact(canonical(snapshot), 'application/json')
            source = self.store.put('source', {
                'provider': RECEIPT_PROVIDER,
                'accession': 'practical_receipt_' + digest([state.run_id, state.episode_id, receipt['operation_key']]),
                'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request,
                'version': RECEIPT_VERSION, 'retrieved_at': receipt['finished_at']}, origin='tool')
        return source['id']


def _continuation(binding, collaborators):
    settings = collaborators['continuation'].get(binding.binding_path)
    if not isinstance(settings, Mapping) or set(settings) != CONTINUATION_FIELDS:
        raise ContractError('a101_hpc_job_continuation_requires_cutoff_and_parameters:' + binding.binding_path)
    return settings


def _target(job):
    """The assignment's own finite completion target: the total credit of its progress requirements."""
    return math.fsum(item['credit'] for item in job['progress_requirements'])


class HpcJobExecutionRuntime:
    """Hooks of an A101 ``hpc_job_execution`` binding over its own ``HpcJobTools``."""

    required_collaborators = ('model_provider', 'store', 'continuation')
    assignment_form = ASSIGNMENT_FORM
    return_form = RETURN_FORM

    def __init__(self, *, tool_registry, launch_instructions):
        if not isinstance(tool_registry, HpcJobTools):
            raise ContractError('a101_hpc_job_execution_requires_its_own_hpc_job_tools')
        if not isinstance(launch_instructions, LaunchInstructions):
            raise ContractError('a101_hpc_job_execution_requires_launch_instructions')
        self.tool_registry, self.launch_instructions = tool_registry, launch_instructions

    def opened(self, bound, collaborators):
        store = collaborators['store']
        if self.tool_registry.store is not store:
            raise ContractError('a101_hpc_job_tools_are_not_over_the_run_store')
        scope = store.validate_scope(dict(bound.assignment['scope']))
        job = self.tool_registry.validate_job(bound.assignment[JOB_FIELD])
        return store, scope, job, self.tool_registry.state(bound, job)

    def build_controller(self, bound, collaborators):
        from yield_control import CompletionYieldController, YieldParameters
        settings = _continuation(self, collaborators)
        _, _, job, state = self.opened(bound, collaborators)
        opening = bound.recorder.recorded('a101.hpc_job_execution.opening_credit',
                                          lambda: state.credit_view()['credit'])
        return CompletionYieldController(bound.episode_id, opening, settings['cutoff'], _target(job),
                                         YieldParameters(**settings['parameters']))

    def build_episode(self, grain, bound, collaborators, child_builders):
        if child_builders:
            raise ContractError('a101_hpc_job_execution_commissions_no_children')
        source = HpcJobSource(self, bound, collaborators)
        return Episode(grain, bound.key, source, bound.request, source.result)

    def restore_controller_input(self, record):
        return Record(dict(record))


SETTINGS = ('directory', 'launch_instructions', 'resource')


def construct(binding_class, store, settings):
    """One HPC job binding with its own ``HpcJobTools`` over ``store``, from the home factory's settings.

    ``settings`` is exactly ``resource`` (the ``pbs_ssh`` resource configuration: ``kind``, ``workspace``,
    ``ssh_argv``, ``python_executable``, ``account``, ``scheduler``), ``directory`` (the coordinator run
    directory holding this binding's practical custody) and ``launch_instructions`` (the frozen
    ``LaunchInstructions``).
    """
    if not isinstance(settings, Mapping) or set(settings) != set(SETTINGS):
        raise ContractError('a101_hpc_job_execution_settings_require_exactly:' + ','.join(SETTINGS))
    return binding_class(tool_registry=HpcJobTools(store, resource=settings['resource'],
                                                   directory=settings['directory']),
                         launch_instructions=settings['launch_instructions'])


class HpcJobSource:
    """The model-selected ``exec_command`` units of one A101 HPC job Episode."""

    def __init__(self, binding, bound, collaborators):
        self._binding, self._bound = binding, bound
        self._tools = binding.tool_registry
        self._provider = collaborators['model_provider']
        self._store, self._scope, self._job, self._state = binding.opened(bound, collaborators)
        self._applied, self._receipt_refs, self._feedback = 0, [], None

    def _catch_up(self, position):
        while self._applied < position:
            self._apply(self._bound.recorder.recall('outcome.' + str(self._applied)))

    def _apply(self, outcome):
        self._receipt_refs.extend(ref for ref in outcome['record_refs'] if ref not in self._receipt_refs)
        self._feedback = None
        self._applied += 1

    def instructions(self):
        text = INSTRUCTIONS
        selected = self._binding.launch_instructions.for_resource(self._tools.resource)
        if selected:
            text += '\nResource instructions supplied from the frozen library:\n' + '\n\n'.join(
                section['text'] for section in selected['sections'])
        pinned = self._binding.launch_instructions.materialize(self._job.get('launch_instructions'))
        if pinned:
            text += '\nLaunch instructions selected by the commissioning parent:\n' + '\n\n'.join(
                section['text'] for section in pinned['sections'])
        return text

    def decision_context(self, view):
        state = view.controller_state
        return {
            'goal': self._bound.request.goal.as_record(),
            'evidence_axis': AXIS,
            'scope': self._scope,
            'execution_assignment': self._job,
            'execution_resource': self._tools.resource_information(),
            'coordinator_workspace': str(self._tools.directory),
            'execution_progress': self._state.credit_view(),
            'execution_completion': self._state.completion_proof(),
            'receipts': [{key: receipt[key] for key in ('operation_key', 'arguments', 'outcome', 'validations',
                                                        'context_after', 'finished_at')}
                         for receipt in self._state.receipts()],
            'controller': state.as_record() if hasattr(state, 'as_record') else None,
            'units_consumed': view.units_consumed,
            'feedback': self._feedback,
        }

    async def next(self, view):
        position = view.units_consumed
        self._catch_up(position)
        if self._state.completion_proof() is not None:
            # PracticalState admits no command after the assignment's endpoint is proven.
            return None
        attempt = 0
        while True:
            context, instructions = self.decision_context(view), self.instructions()
            response = await self._bound.recorder.recorded_async(
                'decision.' + str(position) + '.' + str(attempt),
                lambda: self._provider.complete(self._bound.episode_id, MODEL_ROLE, instructions, context,
                                                deepcopy(ACTION_SCHEMA)))
            try:
                arguments = self._tools.admit_arguments(self._job, response)
            except (ValueError, KeyError, TypeError, ValidationError) as error:
                # Rejected before acquisition: no unit, no observation; decide again with the feedback.
                self._feedback = {'status': 'invalid', 'category': 'action_contract',
                                  'detail': error.message if isinstance(error, ValidationError) else str(error)}
                attempt += 1
                continue
            return Leaf(arguments, lambda chosen: self._execute(position, chosen),
                        lambda chosen, outcome: self._controller_input(position, outcome), TOOL + ':' + str(position))

    async def _execute(self, position, arguments):
        operation_key = self._bound.run_id + ':' + self._bound.episode_id + ':' + str(position)

        async def execute():
            receipt, reference = await self._tools.execute_async(self._state, self._scope, arguments, operation_key)
            failure = receipt['outcome'].get('native_outcome', {}).get('failure')
            return {'kind': 'tool', 'tool': TOOL, 'status': 'failed' if failure else 'completed',
                    'record_refs': [reference], 'operation_key': operation_key, 'receipt_sha256': digest(receipt)}
        outcome = await self._bound.recorder.recorded_async('outcome.' + str(position), execute)
        self._apply(outcome)
        return outcome

    def _controller_input(self, position, outcome):
        return Record({'credit': self._state.credit_view()['credit'],
                       'estimation_context': {'progress_time': self._bound.progress.receipt(position)},
                       'unit': {'position': position, 'kind': outcome['kind'], 'status': outcome['status']}})

    def result(self, record):
        self._catch_up(record.units_consumed)
        view = self._state.credit_view()
        proof = self._state.completion_proof()
        return returned(view['credit'], {
            'evidence_axis': AXIS, 'scope': self._scope, 'resource_kind': 'hpc',
            'assignment_id': self._job['assignment_id'], 'assignment_sha256': self._state.assignment_sha256,
            'endpoint': self._job['endpoint'], 'completed': proof is not None, 'completion_proof': proof,
            'satisfied_requirement_keys': view['satisfied_keys'], 'requirements': view['requirements'],
            'receipt_refs': list(self._receipt_refs), 'known_record_refs': list(self._receipt_refs),
            'ended_by': record.ended_by, 'units': record.units_consumed})


__all__ = ['ASSIGNMENT_FORM', 'HpcJobExecutionRuntime', 'HpcJobSource', 'HpcJobTools', 'SETTINGS', 'construct']
