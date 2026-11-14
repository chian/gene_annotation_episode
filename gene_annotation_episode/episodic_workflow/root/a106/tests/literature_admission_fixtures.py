"""Exercise the real private scientific-credit admission before any acquisition."""
from dataclasses import replace
from types import SimpleNamespace

from ..communication import plain
from ..episode_bindings import EpisodeBindingRegistry
from ..episode_journal import Journal
from ..episode_services import WorkflowServices
from ..method_loop.identities import EpisodeRef
from ..published_evidence_assessment.episode import LiteratureEpisode
from ..runtime import Workflow


def admit_original_literature_credit(store,context):
    host=SimpleNamespace(store=store,run_id=context.run_id)
    host.journal=Journal(store,context.run_id)
    binding=LiteratureEpisode(WorkflowServices(host))
    host.episode_bindings=EpisodeBindingRegistry((binding,))
    path=(('annotation','original-parent'),('literature','original-child'))
    context=replace(context,path=path,episode_id=EpisodeRef(context.run_id,path).episode_id)
    # The actual selector calls this binding's original commissioned-task check.
    # A failed check has no selected work, model response or iterator observation.
    projector=Workflow.scientific_projector_for_context(host,context)
    # Selection returns a lazy projector. Evaluate its original missing-task
    # gate, as the runtime does before acquiring an episode's first unit.
    return Workflow.projection_view(host,projector,plain(context.scope),
        known_record_refs=tuple(context.received_record_refs),
        assignment=plain(context.assignment),episode_id=context.episode_id,run_id=context.run_id)


def selected_work_rows(store,run_id):
    """Retain existing work evidence; schema installation is not selected work."""
    Journal(store,run_id)
    return {table:tuple(tuple(row) for row in store.db.execute(
        f'SELECT * FROM {table} WHERE run_id=? ORDER BY rowid',(run_id,)))
        for table in ('runtime_actions','runtime_observations','runtime_model_calls')}
