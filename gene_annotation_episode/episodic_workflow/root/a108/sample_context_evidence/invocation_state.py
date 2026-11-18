"""invocation state for this private A108 episode."""
from __future__ import annotations
from .scientific_contracts import ContractError, _object, deepcopy, plain, scientific_digest, validate_filled_process

import json
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext

class ScientificInvocationState:

    def _scientific_saved_request_invocation(self, services, context: BindingContext, *, active_only=True) -> dict | None:
        """Read an existing request; yielded requests can finish their first form."""
        if type(active_only) is not bool:
            raise ValueError('scientific_saved_request_active_flag_invalid')
        workflow = services.workflow
        journal = workflow.journal
        if context.run_id != workflow.run_id or journal.run_id != workflow.run_id or context.role != 'sample_context_evidence' or (EpisodeRef(context.run_id, context.path).episode_id != context.episode_id):
            raise ValueError('scientific_saved_request_identity_mismatch')
        row = journal.row('runtime_episodes', context.episode_id)
        if row is None:
            return None
        if row['run_id'] != context.run_id or row['episode_id'] != context.episode_id or json.loads(row['path']) != plain(context.path):
            raise ValueError('scientific_saved_request_identity_mismatch')
        if row['state'] == 'active':
            if row['completion'] is not None or row['archive'] is not None:
                return None
        elif not active_only and row['state'] == 'yielded':
            if row['completion'] is None or row['archive'] is None:
                return None
            completion, archive = (json.loads(value) for value in (row['completion'], row['archive']))
            if not isinstance(completion, dict) or not completion or (not isinstance(archive, dict)) or (not archive):
                raise ValueError('scientific_saved_request_invalid')
        else:
            return None
        request = json.loads(row['request'])
        if not isinstance(request, dict):
            raise ValueError('scientific_saved_request_invalid')
        return request

    def restore_closed_process(self, context) -> dict | None:
        """Restore only the original mechanics identity of an exact closed request."""
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
            saved = validate_filled_process(original['message']['sample_context_evidence'])
            filled = validate_filled_process(candidate['message']['sample_context_evidence'])
            saved_binding = saved['mechanics_binding']
        except (KeyError, TypeError) as error:
            raise ContractError('scientific_closed_request_invalid') from error
        current = self.as_record()
        if saved_binding != current or filled['mechanics_binding'] != current:
            raise ContractError('scientific_filled_identity_mismatch')
        if candidate != original or plain(context.scope) != original['message'].get('scope') or plain(context.assignment) != original['message'].get('episode_assignment'):
            raise ContractError('scientific_filled_identity_mismatch')
        return saved

    def restore_saved_process(self, context, *, original_request, active_only=True) -> dict | None:
        """Project an approved repair onto the exact saved journal request.

        Workflow supplies its existing active row before its unchanged full
        request comparison. Inspection can also finish an authenticated yielded
        request's first form. New commissions keep the current implementation.
        """
        from gene_annotation_episode.episodic_workflow.root.a108.episode_composition import scientific_binding_compatible
        self._role(context.role)
        original = _object(original_request, 'scientific_saved_request_invalid')
        read_saved = getattr(self.services, 'scientific_saved_request', None)
        read_private = getattr(self.services, 'scientific_saved_request_for', None)
        recorded = (read_private(self._scientific_saved_request_invocation, context, active_only=active_only)
            if callable(read_saved) and callable(read_private)
            else read_saved(context, active_only=active_only) if callable(read_saved) else None)
        if recorded is None:
            return None
        if scientific_digest(recorded) != scientific_digest(original):
            raise ContractError('scientific_saved_request_mismatch')
        candidate = _object(context.request, 'scientific_filled_request_required')
        try:
            saved = validate_filled_process(original['message']['sample_context_evidence'])
            filled = validate_filled_process(candidate['message']['sample_context_evidence'])
            current = self.as_record()
            if not scientific_binding_compatible(current, saved['mechanics_binding']):
                return None
            if scientific_digest(filled['mechanics_binding']) not in {scientific_digest(current), scientific_digest(saved['mechanics_binding'])}:
                raise ContractError('scientific_saved_identity_mismatch')
            candidate['message']['sample_context_evidence']['mechanics_binding'] = deepcopy(saved['mechanics_binding'])
            if scientific_digest(candidate) != scientific_digest(original) or scientific_digest(plain(context.scope)) != scientific_digest(original['message']['scope']) or scientific_digest(plain(context.assignment)) != scientific_digest(original['message']['episode_assignment']):
                raise ContractError('scientific_saved_identity_mismatch')
        except (KeyError, TypeError) as error:
            raise ContractError('scientific_saved_request_invalid') from error
        return saved
