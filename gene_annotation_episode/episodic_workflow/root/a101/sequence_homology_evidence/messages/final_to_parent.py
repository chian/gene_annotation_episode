"""The return. Always returned: ``credit`` (``completion['credit']``: the productivity signal, which no field restates)
and ``finding``: the controlled features code read from the A101 axis sheet of each target of the scope
(``INVESTIGATION_FINDING_FEATURES_a101.md`` sections 2.3 and 10) and the number of handoffs still waiting for their
results. No held-record lists, no per-child rows and no prose: the root decides which axis to commission next and
whether to come back for an outstanding job, and that is what it needs.

Selectable: ``committed_record_refs`` (the records this episode committed through its reasoning units and the graded
records of its comparisons: the records its credit reads, which a parent passes back on a later visit) and
``execution_handoff_refs`` (the handoff records its launches returned)."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.axis_features import (
    FEATURES, MEANINGS)

FIELD_TYPES = {'number': 'number', 'count': 'integer', 'boolean': 'boolean'}


def feature_field(name, rule):
    if rule[0] == 'choice':
        return ChoiceField('text', MEANINGS[name], rule[1])
    return Field(FIELD_TYPES[rule[0]], MEANINGS[name], required=rule[-1] != 'optional')


TARGET_FORM = RecordForm({name: feature_field(name, rule) for name, rule in FEATURES.items()})
FINDING_FORM = RecordForm({
    'evidence_axis': ChoiceField('text', 'The evidence axis', ('A101',)),
    'targets': Field('list', 'One entry per target of the scope: the features of its axis sheet', items=TARGET_FORM),
    'outstanding_handoff_count': Field('integer', 'Handoffs its launches returned for which no completed result '
                                                  'acquisition has reported yet'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The controlled features of the A101 axis sheet of each target', form=FINDING_FORM),
    'committed_record_refs': Field('record_refs', 'The records this episode committed or graded: what its credit '
                                                  'reads', required=False),
    'execution_handoff_refs': Field('record_refs', 'The original handoff records its launches returned',
                                    required=False),
})


# The slots whose report closes one handoff (a result acquisition that completed). A child is added here when built.
CLOSING_SLOTS = ()


def final_to_parent(summary, completion, selection):
    completed = sum(1 for row in summary['child_reports'] if row['slot'] in CLOSING_SLOTS
                    and row['finding']['execution_completed'])
    result = {'credit': completion['credit'],
              'finding': {'evidence_axis': 'A101', 'targets': summary['axis_findings'],
                          'outstanding_handoff_count': max(len(summary['handoff_refs']) - completed, 0)}}
    if 'committed_record_refs' in selection:
        result['committed_record_refs'] = summary['committed_record_refs']
    if 'execution_handoff_refs' in selection:
        result['execution_handoff_refs'] = summary['handoff_refs']
    return result
