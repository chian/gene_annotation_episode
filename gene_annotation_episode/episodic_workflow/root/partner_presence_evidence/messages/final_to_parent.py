"""The return. Always returned: the Episode's credit (the system hands it in ``completion``; it is the productivity
signal and nothing restates it) and the controlled finding read by code from the A107 scoring sheet
(``INVESTIGATION_FINDING_FEATURES_a107.md`` E1/E2): the evidence type, direction, target correspondence and sheet
reference of the strongest literature partner sheet (``scoring_sheet.strongest_sheet``; ``not_reported`` without one),
every literature partner sheet's features side by side and the agreement counts over them. No model-written text.
Selectable, one field per fact a parent may want: the records this Episode committed (``committed_record_refs``) and
the received A107 qualification, genomic execution and native component records (``a107_qualification_records``,
``a107_genomic_execution_records``, ``component_axis_native_component_records``,
``component_axis_native_execution_records``)."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.grading.partner_presence_evidence.scoring_sheet import (
    strongest_sheet)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.partner_presence_evidence.partner_population_catalog import (
    PARTNER_CELLS_MEANING)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.partner_presence_evidence.literature_partner_findings import (
    AGREEMENT, CORRESPONDENCE, DIRECTIONS, EVIDENCE_TYPE, FEATURES, MEANINGS, agreement)

FIELD_TYPES = {'number': 'number', 'count': 'integer', 'refs': 'record_refs'}
NOT_REPORTED = 'not_reported'


def feature_field(name, rule, required):
    if rule[0] == 'choice':
        return ChoiceField('text', MEANINGS[name], rule[1], required)
    return Field(FIELD_TYPES[rule[0]], MEANINGS[name], required)


SHEET_FORM = RecordForm({name: feature_field(name, rule, required) for name, (rule, required) in FEATURES.items()})
FINDING_FORM = RecordForm({
    'evidence_type': ChoiceField('text', 'The evidence type of the strongest finding (C1); not_reported without one',
                                 (EVIDENCE_TYPE, NOT_REPORTED)),
    'direction': ChoiceField('text', 'The direction of the strongest finding, computed by code (C6)', DIRECTIONS),
    'target_correspondence': ChoiceField('text', 'The target correspondence of the strongest finding (C5)',
                                         CORRESPONDENCE),
    'sheet_refs': Field('record_refs', 'The sheet of the strongest finding (C2); none without one'),
    # Owner's grading decision (row 6), the meaning of the partner sheet's cells.
    'partner_sheets': Field('list', 'One entry per literature partner sheet returned to this Episode. '
                            + PARTNER_CELLS_MEANING, items=SHEET_FORM),
    **{name: Field('integer', meaning) for name, meaning in AGREEMENT.items()},
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The controlled finding of the A107 scoring sheet', form=FINDING_FORM),
    'committed_record_refs': Field('record_refs', 'The scientific records this Episode committed and the committed '
                                                  'records its children returned', required=False),
    'a107_qualification_records': Field('record_refs', 'Actual received host-issued A107 per-use qualification '
                                                       'records; no implicit upstream receipt', required=False),
    'a107_genomic_execution_records': Field('record_refs', 'Actual received original genomic HPC admission, '
                                                           'pending-attribution and failure records. Operational '
                                                           'status is not scientific credit', required=False),
    'component_axis_native_component_records': Field('record_refs', 'Actually received, automatically graded A107 '
                                                                    'native component publications',
                                                     required=False),
    'component_axis_native_execution_records': Field('record_refs', 'Actually received native '
                                                                    'execution/admission failures and missing '
                                                                    'original operand findings', required=False),
})


def final_to_parent(summary, completion, selection):
    sheets = summary['literature_sheets']
    strongest = strongest_sheet(sheets)
    head = ({'evidence_type': NOT_REPORTED, 'direction': 'unknown', 'target_correspondence': 'not_evaluated',
             'sheet_refs': []} if strongest is None else
            {name: strongest[name] for name in ('evidence_type', 'direction', 'target_correspondence', 'sheet_refs')})
    result = {'credit': completion['credit'], 'finding': {**head, 'partner_sheets': sheets, **agreement(sheets)}}
    if 'committed_record_refs' in selection:
        result['committed_record_refs'] = summary['committed_record_refs']
    for name, key in (('a107_qualification_records', 'qualifications'),
                      ('a107_genomic_execution_records', 'genomic_execution'),
                      ('component_axis_native_component_records', 'native_components'),
                      ('component_axis_native_execution_records', 'native_execution')):
        if name in selection:
            result[name] = sorted(row['source_ref'] for row in summary['received'][key])
    return result
