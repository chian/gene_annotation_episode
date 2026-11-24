"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (the
endpoint state of the commissioned job and what the commands established). A parent selects the facts it wants: the
practical facts, the handoff records of the commands that submitted the requested job, ``execution_completed`` and
the result-side facts. The native result families (HMMER, BLAST, database, BVBRC data) belong to the result
acquisition role: an HPC execution never holds their data, so each is empty."""
import re

from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.gene_context_evidence.hmmer_preparation_result_views import (
    preparation_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_and_context_sources.gene_context_evidence.bvbrc_data_views import (
    bvbrc_data_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_masking.gene_context_evidence.sequence_masking_result_views import (
    masking_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.gene_context_evidence.blast_pairwise_result_views import (
    native_blast_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.gene_context_evidence.blast_utility_result_views import (
    blast_utility_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.gene_context_evidence.hmmer_native_result_views import (
    native_hmmer_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.gene_context_evidence.native_blast_database_result_views import (
    native_blast_database_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.gene_context_evidence.native_blast_standard_database_result_views import (
    standard_blast_database_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.practical_execution_records import (
    digest)

_NAME = re.compile(r'^[a-z][a-z0-9_]*$')

# The result-family fact sources of this role whose names a form can carry and whose value is a list.
_FAMILIES = {}
for _sources in (native_hmmer_fact_sources(), masking_fact_sources(), blast_utility_fact_sources(),
                 standard_blast_database_fact_sources(), native_blast_database_fact_sources(),
                 preparation_fact_sources(), native_blast_fact_sources(), bvbrc_data_fact_sources()):
    _FAMILIES.update(_sources)
_FAMILIES['execution_blast_pairwise_result_refs'] = {
    'type': 'array', 'meaning': 'Requested native pairwise BLAST result references of the acquired result.'}
_FAMILIES = {name: definition for name, definition in _FAMILIES.items()
             if _NAME.fullmatch(name) and definition['type'] == 'array'}


def _family_field(name, definition):
    return Field('record_refs' if name.endswith('_refs') else 'list', definition['meaning'], required=False)


FINDING_FORM = RecordForm({
    'practical_completed': Field('boolean', 'Whether the original requested endpoint predicates have a validated '
                                            'completion in the latest command'),
    'endpoint': Field('text', 'The endpoint the commission requested'),
    'completion_keys': Field('list', 'The requirement keys whose satisfaction completes the assignment'),
    'satisfied_keys': Field('list', 'The requirement keys the actual facts currently satisfy'),
    'receipt_count': Field('integer', 'The number of commands run'),
    'failed_command_count': Field('integer', 'The commands whose execution failed or returned a non-zero code'),
    'completion': Field('record', 'The completion proof, when the endpoint is validated', required=False),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The endpoint state of the commissioned job', form=FINDING_FORM),
    'practical_completed': Field('boolean', 'Whether original requested endpoint predicates have a saved validated '
                                            'completion.', required=False),
    'practical_receipt_digests': Field('list', 'Host-recorded digests of the original selected command receipts.',
                                       required=False),
    'practical_receipt_refs': Field('record_refs', 'The original selected command receipts, with their actual '
                                                   'results and earned operational credit.', required=False),
    'execution_handoff_refs': Field('record_refs', 'Qualified original handoff sources actually available to this '
                                                   'episode; failed attempts do not establish a successful '
                                                   'endpoint.', required=False),
    'execution_result_refs': Field('record_refs', 'Qualified actual requested result acquisitions available to '
                                                  'this episode.', required=False),
    'execution_completed': Field('boolean', 'Whether this assignment has actual verified endpoint information. '
                                            'Yielding alone is false.', required=False),
    'execution_result_origin': Field('list', 'Actual acquisition semantics of retained results; empty when no '
                                             'qualified retained data exists.', required=False),
    'execution_blast_hsps': Field('list', 'Optional explicitly requested native measurements of all published '
                                          'HSPs of an acquired result.', required=False),
    **{name: _family_field(name, definition) for name, definition in _FAMILIES.items()},
})


def _handoff_refs(summary):
    """The saved receipts of the commands whose requested job was submitted with a handoff."""
    refs = []
    for ref, receipt in zip(summary['receipt_refs'], summary['receipts']):
        job = receipt['outcome']['facts'].get('requested_job')
        if job is not None and job['handoff'] is not None:
            refs.append(ref)
    return refs


def _facts(summary):
    receipts = summary['receipts']
    completed = summary['execution_completion'] is not None
    facts = {'practical_completed': completed,
             'practical_receipt_digests': [digest(receipt) for receipt in receipts],
             'practical_receipt_refs': list(summary['receipt_refs']),
             'execution_handoff_refs': _handoff_refs(summary),
             'execution_result_refs': [], 'execution_completed': completed, 'execution_result_origin': [],
             'execution_blast_hsps': []}
    facts.update({name: [] for name in _FAMILIES})
    return facts


def final_to_parent(summary, completion, selection):
    receipts = summary['receipts']
    completed = summary['execution_completion'] is not None
    assignment = summary['assignment']
    failed = sum(1 for receipt in receipts
                 if 'failure' in (receipt['outcome'].get('native_outcome') or {})
                 or receipt['outcome'].get('facts', {}).get('command', {}).get('returncode') not in (0, None))
    finding = {'practical_completed': completed, 'endpoint': assignment['endpoint'],
               'completion_keys': list(assignment['completion_keys']),
               'satisfied_keys': list(summary['execution_progress']['satisfied_keys']),
               'receipt_count': len(receipts), 'failed_command_count': failed}
    if completed:
        finding['completion'] = summary['execution_completion']
    facts = _facts(summary)
    result = {'credit': completion['credit'], 'finding': finding}
    for name in selection:
        result[name] = facts[name]
    return result
