"""Private A102 scientific saved scientific state."""
from __future__ import annotations
from .scientific_contracts import ContractError, _object, plain, scientific_digest, scientific_invocation_ref, validate_filled_process

class ScientificSavedScientificState:

    def restore_closed_process(self, context) -> dict | None:
        """Return the recorded scientific process of an exact closed request."""
        self._role(context.role)
        read_closed = getattr(self.services, 'scientific_closed_request', None)
        if not callable(read_closed):
            return None
        original = read_closed(context)
        if original is None:
            return None
        original = _object(original, 'scientific_closed_request_invalid')
        candidate = _object(context.request, 'scientific_filled_request_required')
        try:
            saved = validate_filled_process(original['message']['scientific_process'])
            filled = validate_filled_process(candidate['message']['scientific_process'])
        except (KeyError, TypeError) as error:
            raise ContractError('scientific_closed_request_invalid') from error
        current = self.as_record()
        if saved['mechanics_binding'] != current or filled['mechanics_binding'] != current:
            raise ContractError('scientific_filled_identity_mismatch')
        if candidate != original or plain(context.scope) != original['message'].get('scope') or plain(context.assignment) != original['message'].get('episode_assignment'):
            raise ContractError('scientific_filled_identity_mismatch')
        return saved

    def validate_context(self, context):
        self._role(context.role)
        request = _object(context.request, 'scientific_filled_request_required')
        try:
            message = request['message']
            filled = validate_filled_process(message['scientific_process'])
            contract = request['report_contract']
            original = self._invocation({'objective': request['goal']['objective'], 'purpose': contract['decision'], 'report_schema': contract['measurements']['schema'], 'initial_report': message['initial_report']}, message['scope'])
            assignment = self._assignment(context.assignment, context.scope, context=context)
        except (KeyError, TypeError) as error:
            raise ContractError('scientific_filled_request_required') from error
        if assignment != message.get('episode_assignment') or plain(context.scope) != message['scope'] or message.get('scientific_invocation_ref') != scientific_invocation_ref(context.run_id, context.path) or (filled['selection'] != assignment['selection']) or (filled['assignment_sha256'] != scientific_digest(assignment)) or (filled['invocation_sha256'] != scientific_digest(original)):
            raise ContractError('scientific_filled_identity_mismatch')
        if scientific_digest(self.as_record()) != scientific_digest(filled['mechanics_binding']):
            raise ContractError('scientific_filled_identity_mismatch')
        if 'revision_origin' in assignment:
            self._validate_origin(context, assignment, preparation_reader=self.services.scientific_parent_preparation, expected_path=context.path[:-1])

    def validate_execution_context(self, context) -> None:
        """A closed request permits inspection/replay, never new dispatch."""
        self.validate_context(context)
        if self.restore_closed_process(context) is not None:
            raise ContractError('scientific_execution_identity_mismatch')
        read_saved = getattr(self.services, 'scientific_saved_request', None)
        active = read_saved(context) if callable(read_saved) else None
        if active is None and callable(read_saved) and (read_saved(context, active_only=False) is not None):
            raise ContractError('scientific_execution_identity_mismatch')
