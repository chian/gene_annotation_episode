"""The A101 head's credit and continuation on ``episode_runtime``.

The head's credit is A101's native sequence-correspondence projection
(``A101SequenceCredit``) over the commissioned scope and the records this
episode has received (``EpisodeReceipts`` in the A101 Store). Its continuation
is the yield binding the head was configured with for that task. Credit is
passed through unchanged: never clamped, bounded or rescaled.

Opening a head episode binds its receipts once: a head commissioned by
another A101 head inherits that parent's frozen receipt prefix; any other
head starts from its scope's subjects. The opening credit is recorded once
through ``bound.recorder`` so a resumed run opens with the credit it opened
with before.
"""
from __future__ import annotations

from collections.abc import Mapping

from episode_runtime import grain_name_for
from method_loop import EpisodeRef

from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.episode_receipts import EpisodeReceipts
from .native_correspondence_credit import A101SequenceCredit

HEAD_BINDING_PATH = 'sequence_homology_evidence'
STORE = 'store'
INITIAL_CREDIT_DECISION = 'a101.head.initial_credit'


class A101HeadCreditError(ValueError):
    """The head's credit cannot be projected from what it was given."""


def head_store(binding, collaborators):
    """The run's shared Store (the standard ``store`` collaborator; checked at link).

    The native projection reads the operation records of the head's own tool
    registry, so that registry must be the one built over this same Store.
    """
    store = collaborators[STORE]
    if binding.tool_registry.store is not store:
        raise A101HeadCreditError('a101_tool_registry_is_not_over_the_run_store')
    return store


def head_scope(bound, store):
    scope = bound.assignment.get('scope')
    if not isinstance(scope, Mapping):
        raise A101HeadCreditError('a101_head_scope_required:' + bound.binding_path)
    return store.validate_scope(dict(scope))


def parent_head_episode_id(bound):
    """The commissioning A101 head's episode id, or None when the parent is not an A101 head."""
    if len(bound.path) > 1 and bound.path[-2][0] == grain_name_for(HEAD_BINDING_PATH):
        return EpisodeRef(bound.run_id, tuple(bound.path[:-1])).episode_id
    return None


def open_head_receipts(bound, store):
    """Bind this head episode's receipts once and record its initial knowledge."""
    receipts = EpisodeReceipts(store, bound.run_id)
    parent = parent_head_episode_id(bound)
    receipts.bind(bound.episode_id, parent)
    if parent is None:
        receipts.receive(bound.episode_id, list(head_scope(bound, store)['subject_refs']), kind='initial')
    return receipts


def head_credit_view(bound, store, receipts):
    """The head's current native-correspondence projection over its received records."""
    return A101SequenceCredit()(store, head_scope(bound, store),
                                known_record_refs=list(receipts.known(bound.episode_id)),
                                episode_id=bound.episode_id, run_id=bound.run_id)


def head_controller(binding, bound, collaborators):
    """The head's own continuation controller, opened with its recorded opening credit."""
    store = head_store(binding, collaborators)
    receipts = open_head_receipts(bound, store)
    initial = bound.recorder.recorded(INITIAL_CREDIT_DECISION,
                                      lambda: head_credit_view(bound, store, receipts)['credit'])
    return binding.head_yield_controller(bound.episode_id, initial)


__all__ = ['A101HeadCreditError', 'HEAD_BINDING_PATH', 'INITIAL_CREDIT_DECISION', 'head_controller',
           'head_credit_view', 'head_scope', 'head_store', 'open_head_receipts', 'parent_head_episode_id']
