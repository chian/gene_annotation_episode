"""The A103 local job execution episode on the generic runner (``episode_runtime``).

The three A103 local job execution bindings (``.../execution_job_submission/local_job_execution``
below the head, below HPC work planning and below HPC allocation execution) bind this module
through ``A103LocalJobRuntime``; each binding declares its own path and commissioning parent.

One local job execution Episode gets one frozen ``practical_assignment_v1`` (``resource_kind``
``local``), commissioned by its submission parent as ``role_assignment``, executing on the
configured local resource. Each unit is one ``exec_command`` action: shell code the A103 model
writes, executed by A103's ``TerminalExecution`` on the assigned resource (or the coordinator
workspace) with its immutable command receipt recorded in the episode's ``PracticalState``. A
selection that fails admission (schema, duplicate environment name, a workdir outside the
workspace) creates no unit; the model decides again with that feedback. Every executed action,
including a failed command, is one unit and enters the iterator with its measured credit.

Credit is the assignment's own practical requirement credit (``project_practical_credit``: the
sum of the caller-valued requirement keys currently satisfied by validated receipt facts). It is
signed and never bounded, clamped or rescaled. Continuation is the completion yield controller:
its target is the total requirement credit the assignment declares, so the Episode is complete
exactly when every credited requirement is satisfied. An assignment that credits a requirement
outside its ``completion_keys`` raises (practical completion would then forbid further actions
while credit is still below the target).

Every model decision (``decision.<position>.<attempt>``) and every action outcome
(``outcome.<position>``) is recorded through the Episode's ``EpisodeRecorder``; the command
receipts are the ``PracticalState``'s own durable, append-only records, so a resumed Episode
neither asks the model again nor repeats a recorded command. Each command receipt, with the
captured output snapshots it names, is also published to the run's shared Store as a ``source``
record of provider ``episode.practical_receipt`` in the form the HPC job route publishes
(``publish_receipt``); the handoff finding names those records as ``receipt_refs`` and
``known_record_refs``, so ``execution_result_acquisition`` acquires a local handoff's outputs
from the Store as it does an HPC handoff's.

Runtime collaborators: ``model_provider`` and ``store`` (the assignment's ``scope`` must be
exactly a scope the run's Store admits). Construction operands (the A103 home factory), each
required: ``resource`` (the local execution resource configuration ``TerminalExecution``
accepts), ``coordinator_workspace``, ``state_directory`` (where each Episode's practical state
is kept), ``launch_instruction_directory`` (the run-frozen launch instruction library whose
resource prompt and assignment selection are presented) and ``continuation``
(``{'cutoff', 'uncertainty_alpha'}``).
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import json
import math
from pathlib import Path, PurePosixPath

from jsonschema import Draft202012Validator, ValidationError

from method_loop import ClosedRecord, Episode, Leaf

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.gene_context_evidence.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import canonical
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import LaunchInstructions
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.practical_execution_records import assess_validations, validate_assignment
from gene_annotation_episode.episodic_workflow.episode_support.jobs.gene_context_evidence.practical_execution_state import PracticalState
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.gene_context_evidence.terminal_execution import TerminalExecution, digest
from gene_annotation_episode.episodic_workflow.episode_support.findings.gene_context_evidence.terminal_scientific_evidence import finalize_scientific_command, terminal_artifact_paths

MODEL = 'model_provider'
STORE = 'store'
REQUIRED_COLLABORATORS = (MODEL, STORE)
MODEL_ROLE = 'REASONING'
TOOL = 'exec_command'
RECEIPT_PROVIDER = 'episode.practical_receipt'
RECEIPT_VERSION = 'practical_receipt_information_v1'
ASSIGNMENT_FIELD = 'role_assignment'


class LocalJobExecutionError(ValueError):
    """A local job assignment, collaborator, operand or decision does not satisfy this binding's contract."""


@dataclass(frozen=True)
class LocalJobRecord(ClosedRecord):
    """A plain JSON record: one unit's controller input or the Episode's result."""
    value: Mapping

    def as_record(self):
        return json.loads(json.dumps(dict(self.value), allow_nan=False))


def _plain(value):
    return json.loads(json.dumps(value, allow_nan=False))


def store_scope(store, scope):
    """The assignment's scope, which must be exactly the scope the run's Store admits."""
    value = _plain(scope)
    if _plain(store.validate_scope(value)) != value:
        raise LocalJobExecutionError('local_job_scope_must_be_store_admitted')
    return value


def completion_target(assignment):
    """The total requirement credit the assignment declares: the Episode's completion target."""
    requirements = assignment['progress_requirements']
    credited = {item['key'] for item in requirements if item['credit'] > 0}
    outside = sorted(credited - set(assignment['completion_keys']))
    if outside:
        raise LocalJobExecutionError('local_job_credited_requirement_outside_completion_keys:' + ','.join(outside))
    target = math.fsum(item['credit'] for item in requirements)
    if not target > 0:
        raise LocalJobExecutionError('local_job_completion_target_must_be_positive')
    return target


def publish_receipt(store, state, scope, receipt):
    """One command receipt as its ``source`` record on the run's shared Store, in the form the HPC job route
    publishes (content-addressed, so republishing a recovered receipt is idempotent)."""
    body = {'version': RECEIPT_VERSION, 'run_id': state.run_id, 'episode_id': state.episode_id,
            'assignment_sha256': state.assignment_sha256, 'scope': scope, 'receipt': receipt}
    snapshot = {'version': 'practical_receipt_assignment_v1', 'run_id': state.run_id,
                'episode_id': state.episode_id, 'scope': scope, 'assignment': state.assignment}
    with store.transaction():
        artifact = store.artifact(canonical(body), 'application/json')
        request = store.artifact(canonical(snapshot), 'application/json')
        source = store.put('source', {
            'provider': RECEIPT_PROVIDER,
            'accession': 'practical_receipt_' + digest([state.run_id, state.episode_id, receipt['operation_key']]),
            'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request,
            'version': RECEIPT_VERSION, 'retrieved_at': receipt['finished_at']}, origin='tool')
    return source['id']


_ENVIRONMENT_ITEM = {'type': 'object', 'additionalProperties': False, 'required': ['name', 'value'],
                     'properties': {'name': {'type': 'string', 'pattern': '^[A-Za-z_][A-Za-z0-9_]*$'},
                                    'value': {'type': 'string'}}}
ACTION_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['selection'], 'properties': {
    'selection': {'type': 'object', 'additionalProperties': False,
                  'required': ['tool', 'cmd', 'workdir', 'target', 'env'], 'properties': {
                      'tool': {'type': 'string', 'enum': [TOOL]},
                      'cmd': {'anyOf': [{'type': 'string', 'minLength': 1},
                                        {'type': 'array', 'minItems': 1,
                                         'items': {'type': 'string', 'minLength': 1}}],
                              'description': 'Shell code (a string) or an argv list.'},
                      'workdir': {'type': 'string', 'minLength': 1,
                                  'description': 'Absolute working directory inside the selected target workspace.'},
                      'target': {'type': 'string', 'enum': ['resource', 'coordinator'],
                                 'description': 'resource: the assigned execution resource workspace; coordinator: '
                                                'the local coordinator workspace for supplied-input work.'},
                      'env': {'type': 'array', 'items': _ENVIRONMENT_ITEM,
                              'description': 'Environment variables for this command only.'}}}}}

INSTRUCTIONS = (
    'You are the execution agent for the one job and local resource assigned below. Use exec_command to write '
    'and run the shell code that job needs: inspect files, author scripts, prepare the environment, run the '
    'software and examine its outputs. No sequence of setup or job stages is prescribed. Preserve the '
    "caller's requested job, scientific inputs, desired outputs and acceptance criteria (progress_requirements "
    'and completion_keys). Historical inventory is context, not proof of present usability. Each command is one '
    'ordinary action: its actual result, including a failure or no progress, enters the iterator with the '
    'credit it earned. The host records command receipts and native job identities; do not keep a parallel '
    'ledger. If an earlier submission outcome is uncertain, investigate that original submission rather than '
    'start a duplicate. workdir and env apply to the selected command only. target=resource runs in the assigned '
    'resource workspace; target=coordinator runs in the local coordinator workspace for supplied-input and '
    'transport work. execution_progress is the practical requirement credit from actual validated facts; the '
    'completion target is the total credit of the assignment\'s requirements. The numerical controller owns '
    'continuation: do not emit a stop action or invent a turn budget, approval review or quality gate. Do not '
    'execute native provider tools; the host executes your selected action.')


class LocalJobSource:
    """Decide and execute one local job Episode's exec_command actions; replay recorded ones on resume."""

    def __init__(self, binding, bound, collaborators):
        self._binding, self._bound = binding, bound
        self._model, self._store = collaborators[MODEL], collaborators[STORE]
        self.scope = store_scope(self._store, bound.assignment['scope'])
        self.assignment = binding.execution_assignment(bound)
        self.target = completion_target(self.assignment)
        self.state = binding.practical_state(bound, self.assignment)
        self.units = 0
        self.last_outcome = None
        self.feedback = None
        self.receipt_refs = []

    # -- state --------------------------------------------------------------------------------------------------
    def _apply(self, outcome):
        self.receipt_refs.extend(ref for ref in outcome['record_refs'] if ref not in self.receipt_refs)
        self.last_outcome, self.feedback, self.units = outcome, None, self.units + 1

    def _restore(self, position):
        """Rebuild what the replayed units returned from their recorded outcomes."""
        while self.units < position:
            self._apply(self._bound.recorder.recall('outcome.' + str(self.units)))

    def credit(self):
        return self.state.credit_view()['credit']

    # -- decisions ----------------------------------------------------------------------------------------------
    def decision_context(self, view):
        terminal = self._binding.terminal
        return {
            'goal': self._bound.request.goal.as_record(),
            'scope': self.scope,
            'execution_assignment': self.assignment,
            'execution_resource': {name: deepcopy(terminal.configuration[name])
                                   for name in ('kind', 'workspace', 'policy') if name in terminal.configuration},
            'coordinator_workspace': terminal.coordinator_workspace,
            'resource_launch_instructions': self._binding.resource_instructions(),
            'selected_launch_instructions': self._binding.selected_instructions(self.assignment),
            'execution_context': self.state.context(),
            'execution_progress': self.state.credit_view(),
            'execution_completion': self.state.completion_proof(),
            'completion_target': self.target,
            'controller': _plain(view.controller_state.as_record()),
            'units_consumed': view.units_consumed,
            'last_local_outcome': self.last_outcome,
            'feedback': self.feedback,
        }

    def admit(self, response):
        """The exec_command arguments of an admitted response; any failure is a rejection before acquisition."""
        Draft202012Validator(ACTION_SCHEMA).validate(_plain(response))
        selection = response['selection']
        names = [item['name'] for item in selection['env']]
        if len(set(names)) != len(names):
            raise LocalJobExecutionError('exec_command_environment_name_repeated')
        arguments = {'cmd': selection['cmd'], 'workdir': selection['workdir'], 'target': selection['target'],
                     'env': {item['name']: item['value'] for item in selection['env']}}
        self._binding.terminal.validate_action(self.assignment, TOOL, arguments)
        return arguments

    async def next(self, view):
        position = view.units_consumed
        self._restore(position)
        attempt = 0
        while True:
            context = self.decision_context(view)
            response = await self._bound.recorder.recorded_async(
                'decision.' + str(position) + '.' + str(attempt),
                lambda: self._model.complete(self._bound.episode_id, MODEL_ROLE, INSTRUCTIONS, context,
                                             ACTION_SCHEMA))
            try:
                arguments = self.admit(response)
            except (ValidationError, ValueError, TypeError, KeyError) as error:
                # Rejected before acquisition: no unit and no observation; the model decides again.
                self.feedback = {'status': 'invalid', 'category': 'action_contract',
                                 'detail': error.message if isinstance(error, ValidationError) else str(error)}
                attempt += 1
                continue
            return Leaf(arguments, lambda chosen: self.execute(position, chosen),
                        lambda chosen, outcome: self.controller_input(position, outcome),
                        TOOL + ':' + str(position))

    # -- execution ----------------------------------------------------------------------------------------------
    async def execute(self, position, arguments):
        key = self._bound.run_id + ':' + self._bound.episode_id + ':' + str(position)

        async def run():
            intent = self.state.begin(key, TOOL, arguments)
            if intent['state'] == 'completed':
                receipt = intent['receipt']
            else:
                try:
                    outcome, _ = await self._binding.terminal.execute(self.state, TOOL, arguments, key)
                except (ValueError, TypeError, OSError, AcquisitionError) as error:
                    outcome = {'facts': {}, 'native_outcome': {'failure': {
                        'code': 'execution_action_failed', 'exception_type': type(error).__name__,
                        'detail': str(error)}}}
                outcome = finalize_scientific_command(self.assignment, arguments, outcome)
                before = self.state.context()
                after = deepcopy(before)
                if arguments['target'] == 'resource' and PurePosixPath(arguments['workdir']).is_relative_to(
                        self.assignment['workspace']):
                    after.update(cwd=arguments['workdir'], environment=arguments['env'])
                after['revision'] += int(any(after[name] != before[name] for name in ('cwd', 'environment')))
                validations = assess_validations(self.assignment, outcome, after, tool_name=TOOL)
                receipt = self.state.finish(key, outcome, validations, context_after=after)
            reference = publish_receipt(self._store, self.state, self.scope, receipt)
            failed = 'failure' in (receipt['outcome'].get('native_outcome') or {})
            return {'kind': 'tool', 'tool': TOOL, 'status': 'failed' if failed else 'completed',
                    'operation_key': key, 'receipt_sha256': digest(receipt), 'receipt': receipt,
                    'record_refs': [reference]}
        outcome = await self._bound.recorder.recorded_async('outcome.' + str(position), run)
        self._apply(outcome)
        return outcome

    def controller_input(self, position, outcome):
        return LocalJobRecord({'credit': self.credit(),
                               'estimation_context': {'progress_time': self._bound.progress.receipt(position)},
                               'unit': {'position': position, 'tool': outcome['tool'], 'status': outcome['status'],
                                        'receipt_sha256': outcome['receipt_sha256']}})

    # -- result -------------------------------------------------------------------------------------------------
    def finding(self, record):
        """The local job's handoff: its completion, requirement states, receipts and the requested job facts."""
        self._restore(record.units_consumed)
        view = self.state.credit_view()
        receipts = self.state.receipts()
        job = next((receipt['outcome']['facts']['requested_job'] for receipt in reversed(receipts)
                    if 'requested_job' in receipt['outcome'].get('facts', {})), None)
        return view['credit'], {
            'assignment_id': self.assignment['assignment_id'],
            'assignment_sha256': digest(self.assignment),
            'endpoint': self.assignment['endpoint'],
            'completion_target': self.target,
            'completed': self.state.completion_proof() is not None,
            'completion_proof': self.state.completion_proof(),
            'requested_job': job,
            'satisfied_keys': view['satisfied_keys'],
            'requirements': [{name: row[name] for name in ('key', 'credit', 'satisfied')}
                             for row in view['requirements']],
            'receipt_sha256s': [digest(receipt) for receipt in receipts],
            'receipt_refs': list(self.receipt_refs),
            'known_record_refs': list(self.receipt_refs),
            'ended_by': record.ended_by,
            'units': record.units_consumed,
        }

    def result(self, record):
        credit, finding = self.finding(record)
        return LocalJobRecord(self._binding.local_job_result(credit, finding))


class A103LocalJobRuntime:
    """The episode_runtime hooks of an A103 local job execution binding (mixed in before ``A103ContractBinding``)."""

    required_collaborators = REQUIRED_COLLABORATORS

    def __init__(self, *, resource, coordinator_workspace, state_directory, launch_instruction_directory,
                 continuation):
        self.terminal = TerminalExecution(resource, coordinator_workspace=coordinator_workspace,
                                          artifact_selector=terminal_artifact_paths)
        if self.terminal.configuration['kind'] != 'local':
            raise LocalJobExecutionError('local_job_execution_requires_a_local_resource:' + self.binding_path)
        self.state_directory = Path(state_directory).expanduser().resolve()
        self.launch_instructions = LaunchInstructions(launch_instruction_directory)
        self.resource_instructions()
        settings = _plain(continuation)
        if not isinstance(settings, dict) or set(settings) != {'cutoff', 'uncertainty_alpha'}:
            raise LocalJobExecutionError('local_job_continuation_requires_cutoff_and_uncertainty_alpha')
        self.continuation = settings

    # -- the commissioned assignment -----------------------------------------------------------------------------
    def execution_assignment(self, bound):
        """The admitted frozen practical assignment for the configured local resource."""
        assignment = validate_assignment(_plain(bound.assignment[ASSIGNMENT_FIELD]))
        if assignment['resource_kind'] != 'local':
            raise LocalJobExecutionError('local_job_execution_requires_local_resource_kind')
        self.terminal.validate_assignment(assignment)
        completion_target(assignment)
        return assignment

    def practical_state(self, bound, assignment):
        """This Episode's durable practical state, its baseline frozen when first opened."""
        directory = self.state_directory / digest({'run_id': bound.run_id, 'episode_id': bound.episode_id})
        if (directory / 'assignment.json').is_file():
            return PracticalState(directory, bound.run_id, bound.episode_id, assignment)
        outcome = {'facts': {}}
        return PracticalState(directory, bound.run_id, bound.episode_id, assignment, initial_outcome=outcome,
                              initial_validations=assess_validations(assignment, outcome,
                                                                     assignment['initial_context']))

    def resource_instructions(self):
        """The configured resource prompt from the frozen launch instruction library (``None`` when unset)."""
        return self.launch_instructions.for_resource(self.terminal.configuration)

    def selected_instructions(self, assignment):
        """The launch instruction sections the commissioning parent selected for this assignment."""
        return self.launch_instructions.materialize(assignment.get('launch_instructions'))

    # -- episode_runtime hooks -----------------------------------------------------------------------------------
    def build_controller(self, bound, collaborators):
        """The completion yield controller, opened at the practical baseline credit, toward the declared target."""
        from yield_control import CompletionYieldController, YieldParameters
        store_scope(collaborators[STORE], bound.assignment['scope'])
        assignment = self.execution_assignment(bound)
        initial = self.practical_state(bound, assignment).credit_view()['initial_credit']
        return CompletionYieldController(bound.episode_id, initial, self.continuation['cutoff'],
                                         completion_target(assignment),
                                         YieldParameters(uncertainty_alpha=self.continuation['uncertainty_alpha']))

    def build_episode(self, grain, bound, collaborators, child_builders):
        if dict(child_builders):
            raise LocalJobExecutionError('local_job_execution_has_no_child_slots:' + self.binding_path)
        extra = sorted(set(bound.report_form.fields) - set(self.return_form.fields))
        if extra:
            # The local job returns its own credit and handoff finding; it has no source for other fields.
            raise LocalJobExecutionError('local_job_commissioned_report_fields_not_supplied:' + ','.join(extra))
        source = LocalJobSource(self, bound, collaborators)
        return Episode(grain, bound.key, source, bound.request, source.result)

    def restore_controller_input(self, record):
        return LocalJobRecord(dict(record))

    def local_job_result(self, credit, finding):
        """A103's return form: the practical credit and the handoff finding record."""
        return {'credit': credit, 'finding': finding}


__all__ = ['A103LocalJobRuntime', 'ACTION_SCHEMA', 'INSTRUCTIONS', 'LocalJobExecutionError', 'LocalJobRecord',
           'LocalJobSource', 'completion_target', 'publish_receipt', 'store_scope']
