"""The annotations of an episode settled after a unit changed its candidates: the one step a tool that keeps a graded
result about what a sequence is runs afterwards, by code, in the same unit. No model decides whether it runs.

1. Joining. While a candidate name of the held table was not sorted by the latest joining held, one model call sorts
   all the names by what they indicate (``blast_claim_keeping.same_calls``: numbers only come back), and the names
   sorted together (two or more) are kept as a grouping: a ``source`` record of ``GROUPING_PROVIDER`` whose artifact
   is the grouping and whose second artifact lists every candidate sorted. The table is read under the latest
   grouping from then on.
2. Claims. For each sequence, each of its two leading annotations under that grouping that has no claims yet gets
   them (``claim_generation.generate_claims``), under its member of the highest score.

Reads and writes only through ``ctx.store``."""
import json

from gene_annotation_episode.domain import canonical
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.candidate_measurements import (
    GROUPING_PROVIDER, candidate_table, held_groupings, held_sources, member_key)
from gene_annotation_episode.episodic_workflow.episode_support.tools.annotation_claims.claim_generation import (
    TRACE_PROVIDER, generate_claims)
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_features.blast_claim_keeping import (
    same_calls)


async def settle_annotations(ctx, *, scope, organism):
    """Settle the joining of the candidate names and the claims of the leading annotations of ``scope`` from the
    records held (see the module). ``organism`` is the leading candidate organism the commission carries, or ``None``:
    it is told to the claim tool. Returns the references of the records written."""
    store, refs = ctx.store, []
    found = {member_key(row): {name: row[name] for name in ('vocabulary', 'name', 'identifier') if name in row}
             for held in candidate_table(store, scope, held_sources(store))['targets'].values()
             for row in held['candidates']}
    joinings = [store.get(ref) for ref in held_sources(store) if store.get(ref)['provider'] == GROUPING_PROVIDER]
    sorted_before = json.loads(store.get_artifact(joinings[-1]['auxiliary_artifact_refs'][0])) if joinings else []
    if not set(found) <= set(sorted_before):
        candidates = sorted(found.values(), key=lambda member: (member['vocabulary'], member['name']))
        sorted_into = await same_calls(ctx.model, [{'label': number, 'annotations': [member['name']]}
                                                   for number, member in enumerate(candidates)])
        groups = {}
        for number, group in sorted_into.items():
            if group:
                groups.setdefault(group, []).append(candidates[number])
        grouping = [{'members': members} for members in groups.values() if len(members) > 1]
        refs.append(store.put('source', {
            'provider': GROUPING_PROVIDER, 'accession': None, 'uri': None,
            'artifact_ref': store.artifact(canonical(grouping), 'application/json'),
            'auxiliary_artifact_refs': [store.artifact(canonical([member_key(member) for member in candidates]),
                                                       'application/json')],
            'text_ref': None, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='tool')['id'])
    groupings = held_groupings(store)
    table = candidate_table(store, scope, held_sources(store), groupings[-1] if groupings and groupings[-1] else None)
    made = {(trace['subject_ref'], member_key(trace['annotation']))
            for trace in (json.loads(store.get_artifact(source['artifact_ref'])) for source in store.list('source')
                          if source['provider'] == TRACE_PROVIDER)}
    for target, held in table['targets'].items():
        lines = ([group['members'] for group in held['grouped_candidates']] if 'grouped_candidates' in held
                 else [[row] for row in held['candidates']])
        names = [next({name: row[name] for name in ('vocabulary', 'name', 'identifier', 'function_identifiers',
                                                     'identifier_sources', 'hits_without_identifier') if name in row}
                      for row in held['candidates'] if any(member_key(row) == member_key(member) for member in members))
                 for members in lines]
        for name in names[:2]:
            if (target, member_key(name)) not in made:
                claimed = await generate_claims(store, ctx.model, ctx.operation_key, annotation=name,
                                                rivals=[other for other in names if other != name],
                                                subject_ref=target, organism=organism)
                refs.extend(claimed['record_refs'])
    return refs


__all__ = ['settle_annotations']
