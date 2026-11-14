"""Request monitoring of one actually exposed direct dependency."""
from gene_annotation_episode.episodic_workflow.root.a101.domain import ContractError

def prepare_dependency_request(binding, parent, value):
    original = binding._assignment(parent.assignment, parent.scope)
    eligible = {row['handle'] for row in binding.services.dependencies(original['target_handle'], parent.scope)}
    if value['target_handle'] not in eligible:
        raise ContractError('monitor_child_target_not_exposed_direct_dependency')
    if not set(value['permitted_committed_record_types']) <= set(original['permitted_committed_record_types']):
        raise ContractError('monitor_child_expands_permitted_record_types')
    return value
