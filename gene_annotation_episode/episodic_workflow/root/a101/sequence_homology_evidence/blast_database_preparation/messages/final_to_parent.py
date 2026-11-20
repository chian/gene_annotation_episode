"""The return: controlled data only. Always: the credit and the finding: how many launches and result
acquisitions were made, the state of the product (``usable``, ``failed``, ``not_established`` while the job had not
ended, or ``not_launched`` when no handoff exists), whether it is usable, why not, and the controlled features of
the receipt's checks, each absent when the receipt did not establish it. Selectable: ``prepared_data_refs`` (the
record the head holds and passes on to the searches that need it) and ``execution_handoff_refs`` (the launched
job's handoff). No path and no text leaves the episode."""
from method_loop import ChoiceField, Field, RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.blast_preparation_receipt import (
    FAILURE_CODES)

FINDING_FORM = RecordForm({
    'launches': Field('integer', 'The launch commissions this episode made'),
    'acquisitions': Field('integer', 'The result acquisitions this episode commissioned'),
    'state': ChoiceField('text', 'The product: usable, failed, not established while the job had not ended, or '
                                 'not launched when no handoff exists',
                         ('usable', 'failed', 'not_established', 'not_launched')),
    'usable': Field('boolean', 'Whether the prepared product is usable'),
    'failure_codes': SubsetField('text', 'Why the product is not usable, from the fixed vocabulary', FAILURE_CODES),
    'prepared_kind': Field('text', 'What was prepared', required=False),
    'input_records': Field('integer', 'The records of the input sequence set', required=False),
    'input_residues': Field('integer', 'The residues of the input sequence set', required=False),
    'files_count': Field('integer', 'The files the job produced', required=False),
    'bytes_total': Field('integer', 'The bytes of the produced files', required=False),
    'sequences': Field('integer', 'A database: the sequences the native summary reports', required=False),
    'letters': Field('integer', 'A database: the letters the native summary reports', required=False),
    'integrity_ok': Field('boolean', 'A database: whether reading back every sequence returned the input\'s counts',
                          required=False),
    'counts_match': Field('boolean', 'A database: whether its counts equal the input counts', required=False),
    'inventory_complete': Field('boolean', 'A database: whether all its files are present', required=False),
    'masked_residues': Field('integer', 'A mask: the residues masked', required=False),
    'masked_fraction': Field('number', 'A mask: the fraction of the input residues masked', required=False),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The state of the prepared product and its checked facts', form=FINDING_FORM),
    'prepared_data_refs': Field('record_refs', 'The prepared-data record this episode established', required=False),
    'execution_handoff_refs': Field('record_refs', 'The handoff row of the launched job', required=False),
})
FEATURES = ('prepared_kind', 'input_records', 'input_residues', 'files_count', 'bytes_total', 'sequences', 'letters',
            'integrity_ok', 'counts_match', 'inventory_complete', 'masked_residues', 'masked_fraction')


def final_to_parent(summary, completion, selection):
    latest = summary['latest_finding']
    counts = {'launches': len(summary['launches']), 'acquisitions': len(summary['results'])}
    if latest is None:
        finding = {**counts, 'state': 'not_launched' if not summary['handoff_refs'] else 'not_established',
                   'usable': False, 'failure_codes': []}
    else:
        finding = {**counts, 'state': latest['state'], 'usable': latest['usable'],
                   'failure_codes': list(latest['failure_codes']),
                   **{name: latest[name] for name in FEATURES if name in latest}}
    facts = {'prepared_data_refs': list(summary['prepared_refs']),
             'execution_handoff_refs': list(summary['handoff_refs'])}
    return {'credit': completion['credit'], 'finding': finding, **{name: facts[name] for name in selection}}
