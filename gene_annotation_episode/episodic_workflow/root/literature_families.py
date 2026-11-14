"""The original configured Literature state with explicit parent-specific owners.

Construction initializes the original scientific configuration exactly once.
Each actual commissioning parent has its own seven predefined implementation
classes. Repeated invocations reuse those classes and retain original state,
record, source, grading and configuration identities.
"""


def parent_families():
    from .published_evidence_assessment import family as annotation
    from .legacy_annotation.published_evidence_assessment import family as improvement
    from .scientific_process.published_evidence_assessment import family as scientific
    return annotation, improvement, scientific


def _attach_parent_families(annotation_members):
    families = parent_families()
    groups = [families[0].validate_members(annotation_members)]
    state = groups[0][0].__dict__
    for family in families[1:]:
        owners = family.classes()
        head = object.__new__(owners[0])
        head.__dict__ = state
        groups.append(family._attach_children(owners, head))
    members = tuple(member for group in groups for member in group)
    state['_root_literature_parent_members'] = members
    return validate_members(members)


def construct(services, **configuration):
    return _attach_parent_families(parent_families()[0].construct(services, **configuration))


def construct_reference_evidence(services, **configuration):
    return _attach_parent_families(
        parent_families()[0].construct_reference_evidence(services, **configuration))


def _factories(constructor, configuration):
    current = None

    def head(services):
        nonlocal current
        current = constructor(services, **configuration)
        return current[0]

    def child(index):
        def factory(services):
            if current is None or current[0].services is not services:
                raise ValueError('root_literature_family_constructor_order')
            return current[index]
        return factory

    return (head, *(child(index) for index in range(1, 21)))


def factories(**configuration):
    return _factories(construct, configuration)


def reference_factories(**configuration):
    return _factories(construct_reference_evidence, configuration)


def validate_members(members):
    families = parent_families()
    if type(members) is not tuple or len(members) not in (7, 21):
        raise ValueError('complete_root_literature_family_required')
    if len(members) == 7:
        for family in families:
            if type(members[0]) is family.classes()[0]:
                return family.validate_members(members)
        raise ValueError('exact_root_literature_family_classes_required')
    state = members[0].__dict__
    if state.get('_root_literature_parent_members') is not members:
        raise ValueError('complete_root_literature_parent_family_required')
    for index, family in enumerate(families):
        actual = family.family_of(members[index * 7])
        selected = members[index * 7:(index + 1) * 7]
        if actual is None or any(left is not right for left, right in zip(actual, selected)):
            raise ValueError('root_literature_parent_family_order_changed')
        if any(member.__dict__ is not state for member in actual):
            raise ValueError('original_root_literature_family_state_required')
    return members


def family_of(binding):
    for family in parent_families():
        local = family.family_of(binding)
        if local is not None:
            whole = binding.__dict__.get('_root_literature_parent_members')
            return validate_members(local if whole is None else whole)
    return None


def binding_groups(bindings):
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


def context_bindings(bindings, role, *, use_context=False, selected_owner=None):
    """One actual callback owner at the original logical configuration position.

Runtime lineage supplies its selected private owner. Role-only, non-executing
contract queries retain the original logical family's identical configuration;
they do not select or execute another parent's episode.
    """
    result = []
    seen = set()
    selected_role = (role if isinstance(role, str) else getattr(role, 'role', None)) if use_context else role
    for binding in bindings:
        members = family_of(binding)
        if members is None:
            result.append(binding)
            continue
        identity = id(members[0].__dict__)
        if identity in seen:
            continue
        seen.add(identity)
        if any(selected_owner is member for member in members):
            result.append(selected_owner)
        else:
            result.append(next((member for member in members
                                if selected_role in member.roles), members[0]))
    return result


def role_only_context_permitted(bindings):
    """Only this authenticated logical family's repeated role is collapsible."""
    for values in bindings.values():
        if len(values) <= 1:
            continue
        groups = [family_of(value) for value in values]
        if any(group is None for group in groups):
            return False
        if any(group[0].__dict__ is not groups[0][0].__dict__ for group in groups):
            return False
    return True
