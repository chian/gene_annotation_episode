"""The return: controlled data only. Always: the credit and the finding. The finding says how many acquisitions were
made, whether the prepared product is established (``state``: ``usable``, ``failed``, or ``not_established`` while
the job had not ended), whether it is usable, and the controlled features of the receipt's checks, each absent when
the receipt did not establish it. Selectable: ``prepared_data_refs``, the reference of the prepared-data record the
Episode wrote (what later searches name). No path and no text leaves the Episode."""
from method_loop import ChoiceField, Field, RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.blast_preparation_receipt import (
    FAILURE_CODES)

FINDING_FORM = RecordForm({
    'acquisitions': Field('integer', 'The acquisitions of the prepared-data record this Episode made'),
    'state': ChoiceField('text', 'The product: usable, failed, or not established while the job had not ended',
                         ('usable', 'failed', 'not_established')),
    'usable': Field('boolean', 'Whether the prepared product is usable'),
    'failure_codes': SubsetField('text', 'Why the product is not usable, from the fixed vocabulary', FAILURE_CODES),
    'prepared_kind': Field('text', 'What was prepared', required=False),
    'input_records': Field('integer', 'The records of the input sequence set', required=False),
    'input_residues': Field('integer', 'The residues of the input sequence set', required=False),
    'files_count': Field('integer', 'The files the job produced', required=False),
    'bytes_total': Field('integer', 'The bytes of the produced files', required=False),
    'sequences': Field('integer', 'A database: the sequences the native summary reports', required=False),
    'letters': Field('integer', 'A database: the letters the native summary reports', required=False),
    'integrity_ok': Field('boolean', 'A database: whether reading back every sequence returned the input\'s counts', required=False),
    'counts_match': Field('boolean', 'A database: whether its counts equal the input counts', required=False),
    'inventory_complete': Field('boolean', 'A database: whether all its files are present', required=False),
    'masked_residues': Field('integer', 'A mask: the residues masked', required=False),
    'masked_fraction': Field('number', 'A mask: the fraction of the input residues masked', required=False),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The state of the prepared product and its checked facts', form=FINDING_FORM),
    'prepared_data_refs': Field('record_refs', 'The prepared-data record this Episode wrote', required=False),
})
FEATURES = ('prepared_kind', 'input_records', 'input_residues', 'files_count', 'bytes_total', 'sequences', 'letters',
            'integrity_ok', 'counts_match', 'inventory_complete', 'masked_residues', 'masked_fraction')


def final_to_parent(summary, completion, selection):
    prepared = summary['prepared']
    if prepared is None:
        finding = {'acquisitions': summary['acquisitions'], 'state': 'not_established', 'usable': False,
                   'failure_codes': []}
    else:
        finding = {'acquisitions': summary['acquisitions'], 'state': prepared['state'], 'usable': prepared['usable'],
                   'failure_codes': list(prepared['failure_codes']),
                   **{name: prepared['features'][name] for name in FEATURES if name in prepared['features']}}
    facts = {'prepared_data_refs': list(summary['prepared_refs'])}
    return {'credit': completion['credit'], 'finding': finding, **{name: facts[name] for name in selection}}
