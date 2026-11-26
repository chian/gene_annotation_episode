"""The feature record of each candidate feature call: the one step every tool that keeps statements about a sequence's
features runs afterwards.

A tool's statements stay in its graded sheet: they are the evidence and are never altered. The candidate feature calls
are settled from all the statements held (``feature_candidates.feature_table``), and each has ONE ``feature`` record:
written when the candidate is first listed, and changed in place, keeping its reference, when the evidence moves the
candidate's positions or strand (the earlier positions are added to its ``changes`` with the source whose statements
moved them). When two candidates become one, the record of the later is marked with the record of the earlier
(``joined_ref``). A coding candidate's record names its protein (``protein_ref``): translated here under the genetic
code held, and translated again when the positions or the code held change.

Writes only through ``ctx.store``."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features.feature_candidates import (
    feature_table, held_sources, letters, positions)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features.feature_types import CODING
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_features.feature_translation import (
    STRANDS, translate_feature_call)


def _protein_code(store, product_ref):
    """The genetic code the protein record ``product_ref`` was translated under (its translation context)."""
    context = store.get(store.get(product_ref)['context_refs'][0])
    return str(context['attributes'][0]['value']['value'])


def settle_feature_records(ctx, *, subject_ref, source_ref):
    """Bring the feature records of the sequence ``subject_ref`` in line with its candidate feature calls, after the
    statements of the source ``source_ref`` were kept (see the module). Returns the references of the feature record
    of every candidate and of every record a translation made."""
    store = ctx.store
    table = feature_table(store, {'subject_refs': [subject_ref]}, held_sources(store))['targets'][subject_ref]
    code = table['readings'].get('genetic_code', {}).get('held')
    refs = []
    with store.transaction():
        for row in table['rows']:
            if not row['feature_refs']:
                ref = store.put('feature', {'subject_ref': subject_ref, 'kind': row['kind'], 'segments': row['segments'],
                                            'strand': row['strand'], 'context_refs': []}, origin='tool')['id']
            else:
                ref, *later = row['feature_refs']
                for other in later:
                    store.change_feature(other, {'joined_ref': ref})
                record = store.get(ref)
                if positions(record) != positions(row) or record['strand'] != row['strand']:
                    store.change_feature(ref, {
                        'segments': row['segments'], 'strand': row['strand'], 'protein_ref': None,
                        'changes': [*record.get('changes', []), {'segments': record['segments'],
                                                                 'strand': record['strand'], 'source_ref': source_ref}]})
            refs.append(ref)
            # a coding sequence, or a mature peptide, that can be read in codons on a strand is translated under the
            # code held
            if (row['kind'] in (CODING, 'mature_peptide') and code is not None and row['strand'] in STRANDS
                    and letters(row) % 3 == 0):
                record = store.get(ref)
                if 'protein_ref' not in record or _protein_code(store, record['protein_ref']) != code:
                    refs.extend(translate_feature_call(ctx, feature_ref=ref, code=int(code))['refs'])
    return refs


__all__ = ['settle_feature_records']
