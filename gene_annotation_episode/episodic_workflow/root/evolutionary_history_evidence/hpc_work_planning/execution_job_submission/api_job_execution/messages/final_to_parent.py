"""The return. Always returned: the Episode's credit (the system hands it in ``completion``), the finding (what the
job's handoff came to), the original handoff records (returned in custody) and whether the original handoff was
established. Selectable: ``execution_result_refs``, ``execution_blast_hsps`` and the array-valued native result
family sources, which have no rows for an API launch."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.evolutionary_history_evidence.hmmer_preparation_result_views import (
    preparation_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.blast_pairwise_result_views import (
    native_blast_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.hmmer_native_result_views import (
    native_hmmer_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.native_blast_database_result_views import (
    native_blast_database_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.native_blast_standard_database_result_views import (
    standard_blast_database_fact_sources)

FINDING_FORM = RecordForm({
    'handoff_established': Field('boolean', 'Whether the original usable handoff of the service job was established'),
    'handoff_count': Field('integer', 'The distinct original handoffs this episode established'),
    'result_count': Field('integer', 'The distinct result identities this episode acquired'),
    'operations_run': Field('integer', 'The operations of the service this episode ran'),
    'submission_uncertain': Field('boolean', 'Whether a submission reply is missing: that does not establish that '
                                             'no job was created'),
    'last_status': Field('text', "The status of the last operation, or 'none'"),
})

# The array-valued native result family sources: no rows for an API launch.
_NATIVE = {**native_hmmer_fact_sources(), **standard_blast_database_fact_sources(),
           **native_blast_database_fact_sources(), **preparation_fact_sources(), **native_blast_fact_sources()}
_LISTS = [name for name, source in _NATIVE.items() if source['type'] == 'array' and name.isidentifier()]

RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the job came to', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'Qualified original handoff records actually established by '
                                    'this episode'),
    'execution_completed': Field('boolean', 'Whether this assignment has actual verified endpoint information '
                                 '(an original usable handoff). Yielding alone is false.'),
    'execution_result_refs': Field('record_refs', 'Qualified actual result acquisitions available to this episode',
                                   required=False),
    'execution_blast_hsps': Field('list', 'Optional explicitly requested native measurements for all published '
                                  'HSPs of an acquired result; none for an API launch', required=False),
    **{name: Field('list', _NATIVE[name]['meaning'], required=False) for name in _LISTS},
})


def _facts(summary):
    facts = {'execution_handoff_refs': list(summary['handoff_refs']),
             'execution_result_refs': list(summary['result_refs']),
             'execution_completed': summary['completed'],
             'execution_blast_hsps': []}
    facts.update({name: [] for name in _LISTS})
    return facts


def final_to_parent(summary, completion, selection):
    facts = _facts(summary)
    last = summary['operations'][-1]['status'] if summary['operations'] else 'none'
    result = {'credit': completion['credit'],
              'finding': {'handoff_established': summary['completed'],
                          'handoff_count': len(summary['handoff_identities']),
                          'result_count': len(summary['result_identities']),
                          'operations_run': len(summary['operations']),
                          'submission_uncertain': summary['submission_uncertain'], 'last_status': last},
              'execution_handoff_refs': facts['execution_handoff_refs'],
              'execution_completed': facts['execution_completed']}
    for name in selection:
        result[name] = facts[name]
    return result
