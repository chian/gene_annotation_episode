"""Construct the seven concrete Root literature owners from one original state.

This module selects no action and implements no episode policy. Each declared
class owns its scientific behavior; the original initializer runs once per
explicit family construction, as it did for the former aggregate binding.
"""

ROLES = ('literature', 'literature_strategy', 'literature_search',
         'literature_page', 'literature_table', 'literature_ordered',
         'literature_targeted')
HOMES = (
    'published_evidence_assessment',
    'published_evidence_assessment/evidence_search_strategy_improvement',
    'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment',
    'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination',
    'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction',
    'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement',
    'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction',
)
_MODULES = tuple('gene_annotation_episode.episodic_workflow.root.' +
                 home.replace('/', '.') + '.episode' for home in HOMES)


def classes():
    # Imports are reached only for this explicit Root family, never while
    # registering an unrelated caller's bindings or the separate A105 owners.
    from .episode import LiteratureEpisode as Head
    from .evidence_search_strategy_improvement.episode import LiteratureEpisode as Strategy
    from .evidence_search_strategy_improvement.source_relevance_assessment.episode import LiteratureEpisode as Search
    from .evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.episode import LiteratureEpisode as Page
    from .evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.episode import LiteratureEpisode as Table
    from .evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.episode import LiteratureEpisode as Ordered
    from .evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.episode import LiteratureEpisode as Targeted
    return (Head, Strategy, Search, Page, Table, Ordered, Targeted)


def construct(services, **configuration):
    owners = classes()
    head = owners[0](services, **configuration)
    return _attach_children(owners, head)


def construct_reference_evidence(services, **configuration):
    owners = classes()
    head = owners[0].reference_evidence(services, **configuration)
    return _attach_children(owners, head)


def _attach_children(owners, head):
    members = [head]
    for owner in owners[1:]:
        member = object.__new__(owner)
        member.__dict__ = head.__dict__
        members.append(member)
    members = tuple(members)
    head._root_literature_members = members
    return members


def factories(**configuration):
    """Explicit ordered factories for the existing ordinary constructor loop."""
    current = None

    def head(services):
        nonlocal current
        current = construct(services, **configuration)
        return current[0]

    def child(index):
        def factory(services):
            if current is None or current[0].services is not services:
                raise ValueError('root_literature_family_constructor_order')
            return current[index]
        return factory

    return (head, *(child(index) for index in range(1, len(ROLES))))


def reference_factories(**configuration):
    """Explicit ordered factories for the existing ordinary constructor loop."""
    current = None

    def head(services):
        nonlocal current
        current = construct_reference_evidence(services, **configuration)
        return current[0]

    def child(index):
        def factory(services):
            if current is None or current[0].services is not services:
                raise ValueError('root_literature_family_constructor_order')
            return current[index]
        return factory

    return (head, *(child(index) for index in range(1, len(ROLES))))


def validate_members(members):
    owners = classes()
    if type(members) is not tuple or len(members) != len(owners):
        raise ValueError('complete_root_literature_family_required')
    if any(type(member) is not owner for member, owner in zip(members, owners)):
        raise ValueError('exact_root_literature_family_classes_required')
    state = members[0].__dict__
    if (state.get('_root_literature_members') is not members or
            any(member.__dict__ is not state for member in members)):
        raise ValueError('original_root_literature_family_state_required')
    for role, member in zip(ROLES, members):
        if member.roles != (role,) or member.entry_roles != (('literature',) if role == 'literature' else ()):
            raise ValueError('root_literature_family_role_identity_changed')
        index = ROLES.index(role)
        expected_parent = 'annotation' if index == 0 else HOMES[index].rsplit('/', 1)[0]
        if member.binding_path != HOMES[index] or member.commissioning_parent != expected_parent:
            raise ValueError('root_literature_original_role_placement_required')
    return members


def family_of(binding):
    owner = type(binding)
    # Use the concrete class metadata without probing arbitrary binding objects.
    # Exact identity is then checked against the real imported private classes.
    module = type.__getattribute__(owner, '__module__')
    name = type.__getattribute__(owner, '__name__')
    if (type(module) is not str or module not in _MODULES or
            type(name) is not str or name != 'LiteratureEpisode'):
        return None
    if not any(owner is expected for expected in classes()):
        return None
    return validate_members(binding.__dict__.get('_root_literature_members'))


def member_for_role(binding, role):
    members = family_of(binding)
    if members is None:
        raise ValueError('complete_root_literature_family_required')
    for declared, member in zip(ROLES, members):
        if role == declared:
            return member
    raise ValueError('root_literature_family_role_not_declared:' + str(role))


def binding_groups(bindings):
    """Yield each original logical binding slot without wrapping its behavior."""
    values = tuple(bindings)
    index = 0
    while index < len(values):
        binding = values[index]
        members = family_of(binding)
        if members is None:
            yield binding, None
            index += 1
            continue
        actual = values[index:index + len(members)]
        if len(actual) != len(members) or any(a is not b for a, b in zip(actual, members)):
            raise ValueError('complete_ordered_root_literature_family_required')
        yield members[0], members
        index += len(members)


def configuration_bindings(bindings):
    return tuple(binding for binding, _ in binding_groups(bindings))


def context_bindings(bindings, role, *, use_context=False):
    """One concrete scientific owner per original family callback position."""
    result = []
    for binding, members in binding_groups(bindings):
        if members is None:
            result.append(binding)
        else:
            selected_role = (role if isinstance(role, str) else getattr(role, 'role', None)) if use_context else role
            # External/annotation hooks keep the original head's responsibility.
            result.append(next((member for declared, member in zip(ROLES, members)
                                if selected_role == declared), members[0]))
    return result

