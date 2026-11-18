"""Original private Scientific completion snapshot from supplied operands only."""

def completion_snapshot(workflow, source, context, snapshot, facts):
    snapshot.update(initial_credit=workflow.journal.row('runtime_episodes', source.episode_id)['initial_credit'], credit=facts['credit'], controller_credit=workflow.source_controller_credit(source), episode_yield=facts['episode_yield'], parent_invocation_ref=workflow.services.scientific_parent_invocation(context))
