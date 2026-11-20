"""The return: controlled data only; no path and no text. Always: ``credit`` and the ``finding``: the state of the
preparation (``usable``, ``failed``, ``incomplete`` or ``not_launched``), the sequences and letters counted from the
input set, the files of the product and the last failure code (from a fixed vocabulary; absent when none). Selectable:
``prepared_data_refs``, the usable prepared-data record this episode established, which the parent holds and names
in later commissions."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.blast_preparation_receipt import (
    FAILURE_CODES)

FAILURE_VOCABULARY = (*FAILURE_CODES, 'job_not_accepted', 'job_not_fetched')
FINDING_FORM = RecordForm({
    'state': ChoiceField('text', 'The preparation: usable, failed, incomplete (the receipt does not establish it) '
                                 'or not_launched', ('usable', 'failed', 'incomplete', 'not_launched')),
    'sequence_count': Field('integer', 'The sequences of the input set, counted by code'),
    'letters': Field('integer', 'The letters (residues) of the input set, counted by code'),
    'files_count': Field('integer', 'The files the job produced (0 when no record was written)'),
    'last_failure_code': ChoiceField('text', 'The failure code of the last unit that failed', FAILURE_VOCABULARY,
                                     required=False),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The state of the preparation and its counted facts', form=FINDING_FORM),
    'prepared_data_refs': Field('record_refs', 'The usable prepared-data record this episode established',
                                required=False),
})


def final_to_parent(summary, completion, selection):
    units = [unit for unit in summary['units'] if unit['action'] == 'launch_local']
    written = [row for row in summary['prepared'] if not row['passed_by_parent']]
    if summary['prepared_refs']:
        state = 'usable'
    elif units:
        state = units[-1]['status']
    else:
        state = 'not_launched'
    failures = [unit['failure_code'] for unit in units if unit['failure_code'] is not None]
    finding = {'state': state, 'sequence_count': summary['input']['sequences'], 'letters': summary['input']['letters'],
               'files_count': written[-1]['features'].get('files_count', 0) if written else 0}
    if failures:
        finding['last_failure_code'] = failures[-1]
    facts = {'prepared_data_refs': list(summary['prepared_refs'])}
    return {'credit': completion['credit'], 'finding': finding, **{name: facts[name] for name in selection}}
