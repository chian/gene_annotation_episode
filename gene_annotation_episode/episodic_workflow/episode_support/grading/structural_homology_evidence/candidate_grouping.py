"""The grouping of candidates a commissioner passes to the A102 head, and what applying it does to the measurements.

A candidate is one candidate of the head's own table, named as the head returned it. A MEMBER names one:
``{'vocabulary', 'name'}`` and ``'identifier'`` when the candidate has its own identifier; its KEY is
``vocabulary + ':' + (identifier or name)``, the key ``candidate_measurements`` gives the candidate. A GROUP is a list of members
of one vocabulary; a GROUPING is a list of groups, no member in two of them. The commissioner decides the groups; the head merges
nothing by itself.

``canonical_grouping`` is the form the head holds and returns: each group's members sorted by key, the groups sorted by their
first key. ``validate_groups`` checks the shape and returns the canonical form; a wrong shape raises. ``group_lookup`` maps every
member key to its group: the GROUP KEY is the smallest member key of the group and the group is named by that member.
``apply_grouping`` reads each measurement row of a member under the key of its group (the row also takes the name and identifier of
the member that names the group): the rows of the members of one group in one test are then replicates of that test, which
``differential_credit`` averages (for a structure search the rows are the hits, so the group's value in the test is the mean over
the hits of all its members). Nothing else changes: the arithmetic of ``differential_credit`` is the same for a grouped or an
ungrouped list of rows."""

_MEMBER_FIELDS = {'vocabulary', 'name', 'identifier'}


def member_key(member):
    """The key of the candidate a member names: ``vocabulary:identifier`` when it has an identifier, else ``vocabulary:name``."""
    return member['vocabulary'] + ':' + (member.get('identifier') or member['name'])


def member_of(row):
    """The member that names the candidate of a measurement row (``vocabulary``, ``name`` and ``identifier`` when it has one)."""
    return {'vocabulary': row['vocabulary'], 'name': row['name'],
            **({} if row['identifier'] is None else {'identifier': row['identifier']})}


def _member(member, vocabularies, where):
    if not isinstance(member, dict) or not {'vocabulary', 'name'} <= set(member) or set(member) - _MEMBER_FIELDS:
        raise ValueError('candidate_groups_member_needs_vocabulary_and_name_and_optionally_identifier:' + where)
    if member['vocabulary'] not in vocabularies:
        raise ValueError('candidate_groups_member_vocabulary_not_known:' + where)
    for field in set(member) - {'vocabulary'}:
        if type(member[field]) is not str or not member[field].strip():
            raise ValueError('candidate_groups_member_' + field + '_must_be_text:' + where)
    return {field: member[field] for field in ('vocabulary', 'name', 'identifier') if field in member}


def canonical_grouping(groups):
    """The canonical form of a grouping of well-formed groups: members sorted by key within each group, groups by first key."""
    return sorted((sorted((dict(member) for member in group), key=member_key) for group in groups),
                  key=lambda group: member_key(group[0]))


def validate_groups(groups, vocabularies):
    """The canonical grouping of ``groups``; raises ``ValueError`` when the shape is wrong: ``groups`` is a list of groups, a group
    is a list of at least one member, a member is ``{vocabulary (one of vocabularies), name, identifier?}``, the members of one
    group share one vocabulary, and no member (key) is in two groups or twice in one."""
    if not isinstance(groups, (list, tuple)):
        raise ValueError('candidate_groups_must_be_a_list_of_groups')
    seen, checked = set(), []
    for position, group in enumerate(groups):
        if not isinstance(group, (list, tuple)) or not group:
            raise ValueError('candidate_groups_group_must_be_a_list_of_at_least_one_member:' + str(position))
        members = [_member(member, vocabularies, str(position) + '.' + str(index)) for index, member in enumerate(group)]
        if len({member['vocabulary'] for member in members}) != 1:
            raise ValueError('candidate_groups_members_of_one_group_must_share_one_vocabulary:' + str(position))
        for member in members:
            if member_key(member) in seen:
                raise ValueError('candidate_groups_member_in_two_groups_or_twice:' + member_key(member))
            seen.add(member_key(member))
        checked.append(members)
    return canonical_grouping(checked)


def group_lookup(grouping):
    """``{member key: {'key', 'member', 'members'}}`` for a canonical grouping: the group key (the smallest member key), the member
    that names the group and all the group's members."""
    found = {}
    for group in grouping or ():
        head = group[0]
        for member in group:
            found[member_key(member)] = {'key': member_key(head), 'member': head, 'members': group}
    return found


def apply_grouping(measurements, grouping):
    """The measurement rows read under ``grouping`` (``None`` or empty: the rows as they are): each row of a member takes its group's
    key, name and identifier; a row of no member is unchanged."""
    lookup = group_lookup(grouping)
    if not lookup:
        return measurements
    rows = []
    for row in measurements:
        group = lookup.get(row['candidate'])
        rows.append(row if group is None else {**row, 'candidate': group['key'], 'name': group['member']['name'],
                                               'identifier': group['member'].get('identifier')})
    return rows


__all__ = ['apply_grouping', 'canonical_grouping', 'group_lookup', 'member_key', 'member_of', 'validate_groups']
