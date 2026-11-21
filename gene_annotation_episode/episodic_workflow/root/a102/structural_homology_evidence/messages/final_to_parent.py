"""The return. Always returned: ``credit`` (``completion['credit']``: the productivity signal, which no field restates) and
``finding``: per target of the scope its leading candidates (at most 10, the leading one first, each with its score and its
subscoring sheets), the number of candidates, the counts of the hits of the graded searches (hits, named, not asked) and the
facts of the model of the target (origin, residues, mean pLDDT 0 to 100: the model's own confidence, not similarity), and the
number of handoffs still waiting for their closure. All of it numbers, counts, values of a fixed vocabulary, the
annotation names of the candidates (names from the looked-up list of a database) and record references: no paragraph.

Selectable: ``committed_record_refs`` (the graded records this episode holds: the records its credit reads, which a parent passes
back on a later visit), ``execution_handoff_refs``, ``execution_check_refs`` and ``execution_closure_refs`` (the handoff, status
and closure records its child returned) and ``data_product_refs`` (the held data-product rows). EVERY RETURNED RECORD LIST IS
CLOSED UNDER NAMING: each is ``internal_summary``'s ``returned_refs`` entry, built with ``job_records.returned_with_names``."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.candidate_measurements import (
    VOCABULARIES)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.foldseek_search import (
    MODEL_ORIGINS)

WAITING_FORM = RecordForm({
    'slot': ChoiceField('text', 'The child episode the job runs under', ('structure_search',)),
    'seconds_since_launch': Field('number', 'The seconds from the launch to the latest thing the child knew'),
    'expected_remaining_seconds': Field('number', 'The seconds still expected, as the child last knew them'),
})
SHEET_FORM = RecordForm({
    'sheet': Field('text', 'The subscoring sheet: the kind of test (the part of the test name before the @)'),
    'value': Field('number', 'The candidate\'s value on the sheet: the sum of its values in the tests of that kind'),
})
CANDIDATE_FORM = RecordForm({
    'vocabulary': ChoiceField('text', 'The vocabulary of the candidate: product (the function name of a hit)', VOCABULARIES),
    'name': Field('text', 'The candidate\'s name exactly as its source gives it'),
    'score': Field('number', 'The candidate\'s annotation score: the sum of its sheet values, that is, of its mean value '
                             '(0 to 1) in each test it has undergone'),
    'sheets': Field('list', 'The candidate\'s subscoring sheets, one per kind of test it has undergone', items=SHEET_FORM),
})
TARGET_FORM = RecordForm({
    'target_ref': Field('text', 'The target: a subject record of the scope'),
    'molecule': ChoiceField('text', 'The molecule of the target', ('protein', 'dna', 'rna', 'unspecified')),
    'search_count': Field('integer', 'The graded structure searches of the target'),
    'hit_count': Field('integer', 'The hits of those searches'),
    'named_count': Field('integer', 'The hits that carry a product name'),
    'not_asked_count': Field('integer', 'The hits never asked about (the naming stopped once the candidates settled): their '
                                        'function is unknown, not absent'),
    'candidate_count': Field('integer', 'The possible annotations found for the target'),
    'candidates': Field('list', 'The leading possible annotations found for the target (at most 10), each with its score, the '
                                'leading one first', items=CANDIDATE_FORM),
    'model_origin': ChoiceField('text', 'Where the model of the target came from', MODEL_ORIGINS, required=False),
    'model_residues': Field('integer', 'The residues the model covers', required=False),
    'model_mean_plddt': Field('number', 'The mean pLDDT of the model, 0 to 100: its own confidence, not similarity',
                              required=False),
})
FINDING_FORM = RecordForm({
    'evidence_axis': ChoiceField('text', 'The evidence axis', ('A102',)),
    'targets': Field('list', 'One entry per protein target of the scope', items=TARGET_FORM),
    'waiting_searches': Field('list', 'The structure searches launched and not extracted: for each the slot, the seconds since '
                                      'its launch and the seconds still expected, as the child last knew them',
                              items=WAITING_FORM, required=False),
    'outstanding_handoff_count': Field('integer', 'The job handoffs it holds (those its child returned) whose closure it does '
                                                  'not hold'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The leading candidates of each target with their scores and the counts of the graded searches',
                     form=FINDING_FORM),
    'committed_record_refs': Field('record_refs', 'The graded records this episode holds: what its credit reads', required=False),
    'execution_handoff_refs': Field('record_refs', 'The original handoff records its child returned', required=False),
    'execution_check_refs': Field('record_refs', 'The status records its child returned, which a later visit passes back',
                                  required=False),
    'execution_closure_refs': Field('record_refs', 'The closure records its child returned for fetched results', required=False),
    'data_product_refs': Field('record_refs', 'The data-product rows it holds (labelled files: EDAM type and format, what made '
                                              'them, where else they lie), which a later visit passes back for reuse',
                               required=False),
})


def final_to_parent(summary, completion, selection):
    waiting = [{'slot': row['slot'], 'seconds_since_launch': row['finding']['seconds_since_launch'],
                'expected_remaining_seconds': row['finding']['expected_remaining_seconds']}
               for index, row in enumerate(summary['child_reports'])
               if row['finding'].get('parked')
               and not any(later['finding']['state'] == 'extracted' for later in summary['child_reports'][index + 1:])]
    result = {'credit': completion['credit'],
              'finding': {'evidence_axis': 'A102', 'targets': summary['findings'],
                          'outstanding_handoff_count': summary['outstanding_handoff_count'],
                          **({'waiting_searches': waiting} if waiting else {})}}
    result.update({name: refs for name, refs in summary['returned_refs'].items() if name in selection})
    return result
