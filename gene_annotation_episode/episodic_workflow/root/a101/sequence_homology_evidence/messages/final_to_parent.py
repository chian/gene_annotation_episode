"""The return. Always returned: ``credit`` (``completion['credit']``: the productivity signal, which no field restates)
and ``finding``: the controlled features code read from the A101 axis sheet of each target of the scope
(``INVESTIGATION_FINDING_FEATURES_a101.md`` sections 2.3 and 10) and the number of handoffs still waiting for their
results. No held-record lists, no per-child rows and no prose: the root decides which axis to commission next and
whether to come back for an outstanding job, and that is what it needs.

Selectable: ``committed_record_refs`` (the records this episode committed through its reasoning units and the graded
records of its comparisons: the records its credit reads, which a parent passes back on a later visit) and
``execution_handoff_refs`` (the handoff records its launches returned), ``execution_check_refs`` and
``execution_closure_refs`` (the status and closure records its children returned) and ``data_product_refs`` (the held
data-product rows). EVERY RETURNED RECORD LIST IS CLOSED UNDER NAMING: each is ``internal_summary``'s ``returned_refs`` entry, built with
``job_records.returned_with_names`` (the records chosen with everything they name among the records held), so the parent holds
whatever a returned record names."""
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
    'test': Field('text', 'The test the top two listed candidates both underwent'),
    'first': Field('record', 'The first candidate', form=CANDIDATE_REFERENCE_FORM),
    'second': Field('record', 'The second candidate', form=CANDIDATE_REFERENCE_FORM),
    'value': Field('number', 'The credit the test earned by differentiating the top two: the difference of the moves of their '
                             'scores over the test times the weaker evidence of the two (1 except in a cluster test, where '
                             'a candidate with n sequences in the set has evidence n/(n+4))'),
})
TARGET_FORM = RecordForm({
    **{name: feature_field(name, rule) for name, rule in FEATURES.items()},
    'candidates': Field('list', 'The possible annotations found for the target, each with its score, the leading one '
                                'first', items=CANDIDATE_FORM),
    'candidate_count': Field('integer', 'The number of possible annotations found'),
    'not_asked_hit_count': Field('integer', 'The hits of database searches whose function was not asked: the naming of the '
                                            'hits stopped once the candidates settled, so their function is unknown, not absent'),
    'no_product_hit_count': Field('integer', 'The hits of database searches whose function was asked and that carry no '
                                             'product: they name no candidate'),
    'uncharacterized_hit_count': Field('integer', 'The hits of database searches whose every function is a label of '
                                                  'ignorance (hypothetical protein, uncharacterized protein): they '
                                                  'name no candidate'),
    'differentials': Field('list', 'The tests that differentiated the top two listed candidates they measured (one per test)', items=DIFFERENTIAL_FORM),
})
FINDING_FORM = RecordForm({
    'evidence_axis': ChoiceField('text', 'The evidence axis', ('A101',)),
    'targets': Field('list', 'One entry per target of the scope: the features of its axis sheet', items=TARGET_FORM),
    'waiting_searches': Field('list', 'The BV-BRC jobs (searches, alignments) launched and not extracted: for each the slot, the seconds since '
                                      'its launch and the seconds still expected, as the child last knew them',
                              items=WAITING_FORM, required=False),
    'outstanding_handoff_count': Field('integer', 'The job handoffs it holds (its own and those its children returned) '
                                                  'whose closure it does not hold'),
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


def final_to_parent(summary, completion, selection):
    waiting = [{'slot': row['slot'], 'seconds_since_launch': row['finding']['seconds_since_launch'],
                'expected_remaining_seconds': row['finding']['expected_remaining_seconds']}
               for index, row in enumerate(summary['child_reports'])
               if row['slot'] in ('bvbrc_blast', 'bvbrc_msa', 'bvbrc_metacats') and row['finding'].get('parked')
               and not any(later['slot'] == row['slot'] and later['finding']['state'] == 'extracted'
                           for later in summary['child_reports'][index + 1:])]
    result = {'credit': completion['credit'],
              'finding': {'evidence_axis': 'A101', 'targets': summary['axis_findings'],
                          'outstanding_handoff_count': summary['outstanding_handoff_count'],
                          **({'waiting_searches': waiting} if waiting else {})}}
    result.update({name: refs for name, refs in summary['returned_refs'].items() if name in selection})
    return result
