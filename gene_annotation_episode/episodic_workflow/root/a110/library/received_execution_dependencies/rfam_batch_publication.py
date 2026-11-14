from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError

def validate_rfam_metadata_source_scope(store, reference, scope):
    """Read only source records/operand roots; never read artifact bytes.

    Store does not propagate source operand/parent roots into record_roots, so
    their explicit retained relationships must be checked as well. The return
    reader reuses this exact validation before trusting a metadata parent.
    """
    selected = store._require(reference, {'source'})
    allowed = set(store.validate_scope(scope)['subject_refs'])
    pending, seen = ([selected], set())
    while pending:
        source = pending.pop()
        if source['id'] in seen:
            continue
        seen.add(source['id'])
        roots = set(store.roots(source['id']))
        for operand in source.get('operand_refs', []):
            roots.update(store.roots(operand))
        if source.get('query_selection_ref') is not None:
            roots.update(store.roots(source['query_selection_ref']))
        if not roots <= allowed:
            raise ContractError('rfam_subject_out_of_scope')
        pending.extend((store._require(ref, {'source'}) for ref in source.get('parent_source_refs', [])))
    return selected
