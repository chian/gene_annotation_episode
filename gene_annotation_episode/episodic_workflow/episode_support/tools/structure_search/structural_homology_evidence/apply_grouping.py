"""A102's one-shot tool ``apply_grouping``: the head keeps the grouping of its candidates that its commissioner passed down.

The commission may carry ``candidate_groups`` (``messages/read_from_parent.py``): groups over the head's own candidates, each
member named exactly as the head returned it. The head merges nothing by itself. The model is never offered this tool: the head owes
it, and the system takes it as the unit (``task.resume_action``) while the commission's grouping is not yet kept.

THE UNIT (``keep_grouping``). It checks that every member names a candidate the head holds (a candidate of the table as found, as
``candidate_measurements.candidate_table`` gives it, of a target of the scope): a member the head does not hold raises, a wrong
commission fails. It keeps the canonical grouping (``candidate_grouping.validate_groups``) through custody as a JSON artifact
(``MEDIA_TYPE``) and a source record of provider ``PROVIDER`` over it, and returns controlled numbers: ``group_count``,
``member_count``, ``discrimination_before`` (the highest discrimination over no grouping and the groupings held before, summed over
the targets) and ``discrimination_after`` (the same with this grouping held). A grouping already held raises: it is owed only while
not kept. The record is among the head's ``committed_record_refs``, so the commissioner passes it back on a later visit.

``held_groupings(reader)`` reads the groupings a reader holds (the kept sources, in the order held, each once): what the credit's
discrimination takes the highest over. Writes only through ``ctx.store``."""
import json
import math

from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.candidate_grouping import (
    member_key, validate_groups)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.candidate_measurements import (
    VOCABULARIES, candidate_credit, candidate_table, held_sources)

PROVIDER = 'candidate_grouping'
MEDIA_TYPE = 'application/vnd.gene-annotation.candidate-grouping+json'
TOOL_NAME = 'apply_grouping'


def held_groupings(reader):
    """The groupings the reader holds: the artifact of each held source of provider ``PROVIDER``, in the order held, each once."""
    found = []
    for source in reader.list('source'):
        if source['provider'] == PROVIDER:
            grouping = json.loads(reader.get_artifact(source['artifact_ref']))
            if grouping not in found:
                found.append(grouping)
    return found


def highest_discrimination(reader, scope, sources, groupings):
    """The discrimination of the head's credit, summed over the targets of the scope: per target the highest over no grouping and
    every grouping of ``groupings``."""
    return math.fsum(row['discrimination'] for row in candidate_credit(reader, scope, sources, groupings)['targets'].values())


def keep_grouping(ctx, *, candidate_groups, scope):
    """Keep the commission's grouping ``candidate_groups`` over ``scope`` through custody (see the module) and return its numbers."""
    store = ctx.store
    grouping = validate_groups(candidate_groups, VOCABULARIES)
    sources = held_sources(store)
    held = {row['vocabulary'] + ':' + row.get('identifier', row['name'])
            for target in candidate_table(store, scope, sources)['targets'].values() for row in target['candidates']}
    for group in grouping:
        for member in group:
            if member_key(member) not in held:
                raise ValueError('candidate_grouping_member_is_not_a_candidate_the_head_holds:' + member_key(member))
    before_groupings = held_groupings(store)
    if grouping in before_groupings:
        raise ValueError('candidate_grouping_already_kept')
    before = highest_discrimination(store, scope, sources, before_groupings)
    after = highest_discrimination(store, scope, sources, before_groupings + [grouping])
    with store.transaction():
        artifact_ref = store.artifact(json.dumps(grouping, sort_keys=True, separators=(',', ':')).encode('utf-8'), MEDIA_TYPE)
        record = store.put('source', {
            'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': artifact_ref, 'text_ref': None,
            'request_ref': None, 'version': None, 'retrieved_at': None, 'auxiliary_artifact_refs': [],
            'operand_refs': list(store.validate_scope(scope)['subject_refs'])}, origin='tool')
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'graded_refs': [record['id']],
            'record_refs': [record['id']], 'source_ref': record['id'], 'group_count': len(grouping),
            'member_count': sum(len(group) for group in grouping), 'discrimination_before': before, 'discrimination_after': after}


__all__ = ['MEDIA_TYPE', 'PROVIDER', 'TOOL_NAME', 'held_groupings', 'highest_discrimination', 'keep_grouping']
