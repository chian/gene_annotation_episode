"""Private root annotation received context."""
from __future__ import annotations
from dataclasses import replace
from .episode_return_records import EpisodeReturnRecords

def receiver_context(store, run_id, episode_id, known_record_refs):
    if not run_id or not episode_id:
        raise ValueError('signed_root_actual_receiver_identity_required')
    if store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_episodes'").fetchone() is None:
        raise ValueError('signed_root_saved_context_required')
    context = EpisodeReturnRecords(store, run_id, failure_prefix='signed_root_').context(episode_id)
    return replace(context, received_record_refs=tuple(known_record_refs))
