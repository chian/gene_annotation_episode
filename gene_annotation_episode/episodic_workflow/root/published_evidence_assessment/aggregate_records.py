"""The private literature binding records and the aggregate record of a family."""

def private_record(binding, home):
    from .family import HOMES, classes
    owners = classes()
    if home not in HOMES or type(binding) is not owners[HOMES.index(home)]:
        raise ValueError('exact_root_literature_private_record_owner_required')
    from .record_algorithm import current_aggregate_record
    record = current_aggregate_record(binding)
    return {**record, 'version': 'root_private_literature_episode_v1', 'binding_id': home}


def family_record(members):
    from gene_annotation_episode.episodic_workflow.root.literature_families import validate_members
    from .record_algorithm import current_aggregate_record
    head = validate_members(members)[0]
    return current_aggregate_record(head)


def binding_record_pairs(bindings):
    from gene_annotation_episode.episodic_workflow.root.literature_families import binding_groups
    for binding, members in binding_groups(bindings):
        yield binding, (binding.as_record() if members is None else family_record(members))


def registry_records(bindings):
    return [record for _, record in binding_record_pairs(bindings)]
