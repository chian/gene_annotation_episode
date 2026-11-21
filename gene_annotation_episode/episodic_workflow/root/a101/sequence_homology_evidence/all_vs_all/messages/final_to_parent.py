"""The return: controlled data only; no path and no text. EVERY RETURNED RECORD LIST IS CLOSED UNDER NAMING
(``internal_summary`` builds each with ``job_records.returned_with_names``). Always: ``credit`` and the ``finding``: the state of
the work (``nothing_done``, ``database_ready``, ``matrix_ready`` or ``clustered``), the sequences and letters of the set, the pairs
of the matrix, one row per graded clustering (inflation, cluster count, the target's cluster size) and the last failure code.
Selectable: ``execution_handoff_refs``, ``closure_refs`` and ``graded_refs`` (the graded records: the set, database, matrix and
clusters data-product rows with their artifacts, and each clustering's source and grading artifact, which the parent's credit
reads)."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.blast_preparation_receipt import (
    FAILURE_CODES)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.all_vs_all_run import (
    OWN_FAILURE_CODES)

CLUSTERING_FORM = RecordForm({
    'inflation': Field('number', 'The MCL inflation of the clustering'),
    'cluster_count': Field('integer', 'The clusters of the set'),
    'target_cluster_size': Field('integer', 'The sequences in the target\'s cluster, the target included'),
})
FINDING_FORM = RecordForm({
    'state': ChoiceField('text', 'The work: nothing_done, database_ready, matrix_ready or clustered',
                         ('nothing_done', 'database_ready', 'matrix_ready', 'clustered')),
    'sequence_count': Field('integer', 'The sequences of the set (the target and the chosen hits)'),
    'letters': Field('integer', 'The letters (residues) of the set'),
    'pair_count': Field('integer', 'The ordered pairs of distinct sequences with an alignment in the matrix', required=False),
    'clusterings': Field('list', 'The graded clusterings, one per inflation', items=CLUSTERING_FORM),
    'last_failure_code': ChoiceField('text', 'The failure code of the last unit that failed', (*FAILURE_CODES, *OWN_FAILURE_CODES),
                                     required=False),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The state of the work and its controlled facts', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'The handoff records of the jobs run', required=False),
    'closure_refs': Field('record_refs', 'The closure records of the jobs run', required=False),
    'graded_refs': Field('record_refs', 'The graded records: the data-product rows (set, database, matrix, clusters) with their '
                                        'artifacts, and each clustering\'s source and grading artifact', required=False),
})


def final_to_parent(summary, completion, selection):
    finding = {'state': summary['state'], 'sequence_count': summary['planned']['sequences'], 'letters': summary['planned']['letters'],
               'clusterings': [{key: row[key] for key in ('inflation', 'cluster_count', 'target_cluster_size')}
                               for row in summary['clusterings']]}
    if summary['matrix']:
        finding['pair_count'] = summary['matrix'][-1]['pair_count']
    if summary['last_failure_code'] is not None:
        finding['last_failure_code'] = summary['last_failure_code']
    facts = {'execution_handoff_refs': list(summary['handoff_refs']), 'closure_refs': list(summary['closure_refs']),
             'graded_refs': list(summary['graded_refs'])}
    return {'credit': completion['credit'], 'finding': finding, **{name: facts[name] for name in selection}}
