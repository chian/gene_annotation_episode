"""The return. Always returned: ``credit`` (``completion['credit']``: the productivity signal, which no field restates)
and ``finding``: the controlled features code read from the A101 axis sheet of each target of the scope
(``INVESTIGATION_FINDING_FEATURES_a101.md`` sections 2.3 and 10) and the number of handoffs still waiting for their
results. No held-record lists, no per-child rows and no prose: the root decides which axis to commission next and
whether to come back for an outstanding job, and that is what it needs.

Selectable: ``committed_record_refs`` (the records this episode committed through its reasoning units and the graded
records of its comparisons: the records its credit reads, which a parent passes back on a later visit) and
``execution_handoff_refs`` (the handoff records its launches returned), ``execution_check_refs`` and ``execution_closure_refs`` (the status and closure records its children returned)."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.axis_features import (
    FEATURES, MEANINGS)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.candidate_measurements import (
    VOCABULARIES)

FIELD_TYPES = {'number': 'number', 'count': 'integer', 'boolean': 'boolean'}


def feature_field(name, rule):
    if rule[0] == 'choice':
        return ChoiceField('text', MEANINGS[name], rule[1])
    return Field(FIELD_TYPES[rule[0]], MEANINGS[name], required=rule[-1] != 'optional')


WAITING_FORM = RecordForm({
    'slot': ChoiceField('text', 'The child episode the job runs under', ('bvbrc_blast', 'bvbrc_msa', 'bvbrc_metacats')),
    'seconds_since_launch': Field('number', 'The seconds from the launch to the latest thing the child knew'),
    'expected_remaining_seconds': Field('number', 'The seconds still expected, as the child last knew them'),
})
CANDIDATE_REFERENCE_FORM = RecordForm({
    'vocabulary': ChoiceField('text', 'The vocabulary of the candidate: product (a database search\'s function), '
                                      'profile_family (a family of a profile database) or reference_sequence (a '
                                      'sequence record it was compared with)', VOCABULARIES),
    'name': Field('text', 'The candidate\'s name exactly as its source gives it'),
    'identifier': Field('text', 'The candidate\'s identifier exactly as its source gives it (a family accession or '
                                'a record reference; a product has none)', required=False),
})
SHEET_FORM = RecordForm({
    'sheet': Field('text', 'The subscoring sheet: the kind of test (the part of the test name before the @)'),
    'value': Field('number', 'The candidate\'s value on the sheet: the sum of its values in the tests of that kind'),
})
CANDIDATE_FORM = RecordForm({
    **CANDIDATE_REFERENCE_FORM.fields,
    'score': Field('number', 'The candidate\'s annotation score: the sum of its sheet values, that is, of its mean '
                             'value (0 to 1) in each test it has undergone'),
    'sheets': Field('list', 'The candidate\'s subscoring sheets, one per kind of test it has undergone', items=SHEET_FORM),
    'tests': Field('list', 'The tests the candidate has undergone, each as the controlled test name'),
    'measurement_count': Field('integer', 'The measurements of the candidate over all its tests'),
    'best_value': Field('number', 'The highest single value of the candidate, 0 to 1'),
})
DIFFERENTIAL_FORM = RecordForm({
    'test': Field('text', 'The test two listed candidates both underwent'),
    'first': Field('record', 'The first candidate', form=CANDIDATE_REFERENCE_FORM),
    'second': Field('record', 'The second candidate', form=CANDIDATE_REFERENCE_FORM),
    'value': Field('number', 'The difference of the moves of their scores over the test (the credit it earned)'),
})
TARGET_FORM = RecordForm({
    **{name: feature_field(name, rule) for name, rule in FEATURES.items()},
    'candidates': Field('list', 'The possible annotations found for the target, each with its score, the leading one '
                                'first', items=CANDIDATE_FORM),
    'candidate_count': Field('integer', 'The number of possible annotations found'),
    'unlabelled_hit_count': Field('integer', 'The hits of database searches that carry no function and name no '
                                             'candidate'),
    'differentials': Field('list', 'The tests that differentiated two listed candidates', items=DIFFERENTIAL_FORM),
})
FINDING_FORM = RecordForm({
    'evidence_axis': ChoiceField('text', 'The evidence axis', ('A101',)),
    'targets': Field('list', 'One entry per target of the scope: the features of its axis sheet', items=TARGET_FORM),
    'waiting_searches': Field('list', 'The BV-BRC jobs (searches, alignments) launched and not extracted: for each the slot, the seconds since '
                                      'its launch and the seconds still expected, as the child last knew them',
                              items=WAITING_FORM, required=False),
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
    'execution_check_refs': Field('record_refs', 'The status records its children returned for their searches, which a '
                                                'later visit passes back', required=False),
    'execution_closure_refs': Field('record_refs', 'The closure records its children returned for fetched reports',
                                    required=False),
    'data_product_refs': Field('record_refs', 'The data-product rows it holds (labelled files: EDAM type and format, what '
                                              'made them, where else they lie), which a later visit passes back for reuse',
                               required=False),
})


# The slots whose report closes one handoff, by the state of the child's finding that does it. A child is added here when
# built.
CLOSING_STATES = {'bvbrc_blast': 'extracted', 'bvbrc_msa': 'extracted', 'bvbrc_metacats': 'extracted'}


def final_to_parent(summary, completion, selection):
    completed = sum(1 for row in summary['child_reports'] if row['slot'] in CLOSING_STATES
                    and row['finding']['state'] == CLOSING_STATES[row['slot']])
    waiting = [{'slot': row['slot'], 'seconds_since_launch': row['finding']['seconds_since_launch'],
                'expected_remaining_seconds': row['finding']['expected_remaining_seconds']}
               for index, row in enumerate(summary['child_reports'])
               if row['slot'] in ('bvbrc_blast', 'bvbrc_msa', 'bvbrc_metacats') and row['finding'].get('parked')
               and not any(later['slot'] == row['slot'] and later['finding']['state'] == 'extracted'
                           for later in summary['child_reports'][index + 1:])]
    result = {'credit': completion['credit'],
              'finding': {'evidence_axis': 'A101', 'targets': summary['axis_findings'],
                          'outstanding_handoff_count': max(summary['handoff_count'] - completed, 0),
                          **({'waiting_searches': waiting} if waiting else {})}}
    if 'committed_record_refs' in selection:
        result['committed_record_refs'] = summary['committed_record_refs']
    if 'execution_handoff_refs' in selection:
        result['execution_handoff_refs'] = summary['handoff_refs']
    if 'execution_check_refs' in selection:
        result['execution_check_refs'] = summary['check_refs']
    if 'data_product_refs' in selection:
        result['data_product_refs'] = summary['data_product_refs']
    if 'execution_closure_refs' in selection:
        result['execution_closure_refs'] = summary['closure_refs']
    return result
