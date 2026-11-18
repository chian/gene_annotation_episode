"""Private scientific process state."""
from __future__ import annotations
from .scientific_contracts import ContractError, _object, plain, validate_filled_process

class SequenceHomologyEvidenceState:

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
            saved = validate_filled_process(original['message']['sequence_homology_evidence'])
            filled = validate_filled_process(candidate['message']['sequence_homology_evidence'])
        except (KeyError, TypeError) as error:
            raise ContractError('scientific_closed_request_invalid') from error
        current = self.as_record()
        if saved['mechanics_binding'] != current or filled['mechanics_binding'] != current:
            raise ContractError('scientific_filled_identity_mismatch')
        if candidate != original or plain(context.scope) != original['message'].get('scope') or plain(context.assignment) != original['message'].get('episode_assignment'):
            raise ContractError('scientific_filled_identity_mismatch')
        return saved

