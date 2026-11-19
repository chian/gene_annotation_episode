"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (whether
the requested endpoint was verified, which requirements are satisfied and which commands failed). Selectable: the
terminal practical facts (``practical_completed``, ``practical_receipt_digests``, ``practical_receipt_refs``),
``execution_handoff_refs``, ``execution_result_refs``, ``execution_completed``, ``execution_blast_hsps``,
``execution_blast_pairwise_result_refs`` and the array-valued native result family sources. A launch acquires no
results: every family source and the result and hsp sources are empty for it."""
import re

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
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.practical_execution_records import (
    digest)

FINDING_FORM = RecordForm({
    'practical_completed': Field('boolean', 'Whether the original requested endpoint predicates have a verified '
                                            'completion'),
    'endpoint': Field('text', 'The requested endpoint: usable_handoff or completed_job_outputs'),
    'commands_run': Field('integer', 'The number of commands executed'),
    'satisfied_keys': Field('list', 'The original requirement keys currently satisfied'),
    'unsatisfied_keys': Field('list', 'The original requirement keys not satisfied'),
    'failures': Field('list', 'The recorded failures of the commands that failed, in order'),
})

_FAMILY_SOURCE_FUNCTIONS = (native_hmmer_fact_sources, standard_blast_database_fact_sources,
                            native_blast_database_fact_sources, preparation_fact_sources, native_blast_fact_sources)
_IDENTIFIER = re.compile(r'^[a-z][a-z0-9_]*$')


def _family_sources():
    """The array-valued native result family sources of this role, by name: ``(meaning, type)``."""
    found = {}
    for source in _FAMILY_SOURCE_FUNCTIONS:
        for name, declared in source().items():
            if _IDENTIFIER.fullmatch(name) and declared['type'] == 'array':
                found[name] = (declared['meaning'], declared['type'])
    return found


FAMILY_SOURCES = _family_sources()

_FIELDS = {
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'Whether the requested endpoint was verified, and what each command did',
                     form=FINDING_FORM),
    'practical_completed': Field('boolean', 'Whether original requested endpoint predicates have a saved validated '
                                            'completion', required=False),
    'practical_receipt_digests': Field('list', 'Host-recorded digests of the original selected command receipts',
                                       required=False),
    'practical_receipt_refs': Field('record_refs', 'Original selected command, actual result and earned operational '
                                                   'credit sources: the saved receipts', required=False),
    'execution_handoff_refs': Field('record_refs', 'Qualified original handoff sources available to this episode: '
                                                   'the saved receipts of the commands that handed a job off',
                                    required=False),
    'execution_result_refs': Field('record_refs', 'Qualified actual requested result acquisitions: none, a launch '
                                                  'acquires no results', required=False),
    'execution_completed': Field('boolean', 'Whether this assignment has actual verified endpoint information; '
                                            'yielding alone is false', required=False),
    'execution_blast_hsps': Field('list', 'Optional explicitly requested native measurements of acquired HSPs: '
                                          'none for a launch', required=False),
    'execution_blast_pairwise_result_refs': Field('record_refs', 'BLAST pairwise result references: none for a '
                                                                  'launch', required=False),
    **{name: Field('list', meaning, required=False) for name, (meaning, _) in FAMILY_SOURCES.items()},
}
RETURN_FORM = RecordForm(_FIELDS)


def _facts(summary):
    """The facts a parent may select for a practical assignment: the terminal facts and the handoff
    references."""
    completed = summary['execution_completion'] is not None
    facts = {'practical_completed': completed,
             'practical_receipt_digests': [digest(receipt) for receipt in summary['receipts']],
             'practical_receipt_refs': list(summary['receipt_refs']),
             'execution_handoff_refs': sorted(summary['handoff_refs']), 'execution_result_refs': [],
             'execution_completed': completed, 'execution_blast_hsps': [],
             'execution_blast_pairwise_result_refs': []}
    facts.update({name: [] for name in FAMILY_SOURCES})
    return facts


def final_to_parent(summary, completion, selection):
    progress = summary['execution_progress']
    satisfied = list(progress['satisfied_keys'])
    unsatisfied = [row['key'] for row in progress['requirements'] if not row['satisfied']]
    failures = [command['failure'] for command in summary['commands'] if command['failure'] is not None]
    facts = _facts(summary)
    result = {'credit': completion['credit'],
              'finding': {'practical_completed': facts['practical_completed'],
                          'endpoint': summary['assignment']['endpoint'], 'commands_run': len(summary['commands']),
                          'satisfied_keys': satisfied, 'unsatisfied_keys': unsatisfied, 'failures': failures}}
    for name in selection:
        result[name] = facts[name]
    return result
