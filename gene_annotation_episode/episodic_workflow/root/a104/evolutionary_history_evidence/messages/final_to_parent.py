"""The return: what this episode declares it can return.

Always returned: ``credit`` (the system hands the Episode's credit in ``completion``; it is the productivity signal
and nothing restates it) and ``finding``: the controlled features code read from the A104 sheets this episode saved
or its own-kind children returned (``INVESTIGATION_FINDING_FEATURES_a104.md``: one entry per native measurement with
the references of its sheet, one entry per target with the attributed dimensions of the credit view, the count of
each evidence type and of received native contributions). No model-written text is returned. Selectable:
``committed_record_refs``, the records this episode committed through its interpretations."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.finding import (
    EVIDENCE_TYPES, SHEET_FEATURES, TARGET_FEATURES)

RECORD_SOURCE = 'committed_record_refs'
FIELD_TYPES = {'number': 'number', 'count': 'integer', 'boolean': 'boolean', 'refs': 'record_refs'}
SHEET_REQUIRED = ('evidence_type', 'sheet_refs', 'attribution_state', 'missing_input_count')


def feature_form(table, required):
    fields = {}
    for name, (rule, meaning) in table.items():
        if rule[0] == 'choice':
            fields[name] = ChoiceField('text', meaning, rule[1], required=name in required)
        else:
            fields[name] = Field(FIELD_TYPES[rule[0]], meaning, required=name in required)
    return RecordForm(fields)


SHEET_FORM = feature_form(SHEET_FEATURES, SHEET_REQUIRED)
TARGET_FORM = feature_form(TARGET_FEATURES, tuple(TARGET_FEATURES))
TYPE_COUNTS = {kind: kind + '_count' for kind in EVIDENCE_TYPES.values()}
FINDING_FORM = RecordForm({
    'sheets': Field('list', 'One entry per native measurement (its current per-use attribution sheet), saved by this '
                    'episode or returned by its own-kind children', items=SHEET_FORM),
    'targets': Field('list', 'One entry per target of the scope: the attributed dimensions of the credit view',
                     items=TARGET_FORM),
    'contribution_count': Field('integer', 'V7: received native measurements that contribute to the credit'),
    **{name: Field('integer', 'Measurements of evidence type ' + kind) for kind, name in TYPE_COUNTS.items()},
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The controlled features of the A104 sheets', form=FINDING_FORM),
    RECORD_SOURCE: Field('record_refs', 'The records this episode committed through its interpretations',
                         required=False),
})


def finding(summary):
    sheets = summary['a104_sheets']
    return {'sheets': sheets, 'targets': summary['a104_targets'],
            'contribution_count': summary['credit_view']['source_contribution_count'],
            **{name: sum(1 for sheet in sheets if sheet['evidence_type'] == kind) for kind, name in TYPE_COUNTS.items()}}


def final_to_parent(summary, completion, selection):
    result = {'credit': completion['credit'], 'finding': finding(summary)}
    if RECORD_SOURCE in selection:
        result[RECORD_SOURCE] = list(summary['committed_record_refs'])
    return result
