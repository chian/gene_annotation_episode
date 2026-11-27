"""What the parent gives: the commission of one all-vs-all, controlled values and record references only. This is the only
place the assignment is read. A wrong commission raises and the run fails; nothing repairs it.

``query_refs``: exactly one protein subject record of the parent's scope (the target); ``input_refs``: the records its sequence
and the search are read from, passed in custody. ``search_refs``: exactly one record, the held graded BV-BRC search whose
candidates' hits form the set; ``candidates``: the product candidates that take part, each ``{name}`` exactly as the search's
source gives the product (at least two, chosen by the parent from the candidates it admitted from that search);
``per_candidate``: how many sequences of each (2 to 20; code chooses which); ``handoff_unit``, ``information_unit`` and
``graded_unit``: the credit units (positive): the database prepared, the matrix of the set, and the committed clustering. The
episode's target is the credit still obtainable: the three units. (The clustering's tuning is the child's own model's choice.)"""
import math

from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.all_vs_all_run import (
    MINIMUM_CANDIDATES, PER_CANDIDATE_RANGE)

UNITS = ('handoff_unit', 'information_unit', 'graded_unit')
CANDIDATE_FORM = RecordForm({'name': Field('text', 'A product candidate\'s name exactly as the search gives it')})
ORGANISM_FORM = RecordForm({
    'taxon_id': Field('integer', 'The candidate taxon (NCBI taxonomy id)'),
    'name': Field('text', 'The taxonomy\'s own name of the taxon'),
    'rank_code': Field('text', 'The rank code of the taxon'),
    'score': Field('number', 'The candidate\'s score'),
    'role': ChoiceField('text', 'The leading candidate', ('leader',)),
})
ASSIGNMENT_FORM = RecordForm({
    'query_refs': Field('record_refs', 'The target: exactly one protein subject record of the parent\'s scope, passed in custody'),
    'input_refs': Field('record_refs', 'The records the target\'s sequence and the search are read from, passed in custody'),
    'search_refs': Field('record_refs', 'The held graded BV-BRC database search whose candidates\' hits form the set: exactly '
                                        'one source record, passed in custody'),
    'candidates': Field('list', 'The product candidates of that search that take part (at least two)', items=CANDIDATE_FORM),
    'per_candidate': Field('integer', 'How many sequences of each candidate are in the set (' + str(PER_CANDIDATE_RANGE[0])
                           + ' to ' + str(PER_CANDIDATE_RANGE[1]) + '); code chooses which'),
    'handoff_unit': Field('number', 'The credit of the established database (positive)'),
    'information_unit': Field('number', 'The credit of the established matrix of bit scores (positive)'),
    'graded_unit': Field('number', 'The credit of the committed graded clustering (positive)'),
    'scope': Field('record', 'The parent\'s scope: what the annotations are settled over after the graded result'),
    'organism': Field('record', 'The leading candidate organism the parent holds, told to the claim tool',
                      form=ORGANISM_FORM, required=False),
})


def read_from_parent(assignment, message):
    (query,) = assignment['query_refs']
    (search,) = assignment['search_refs']
    names = [row['name'] for row in assignment['candidates']]
    if len(set(names)) != len(names) or len(names) < MINIMUM_CANDIDATES:
        raise ValueError('all_vs_all_two_or_more_distinct_candidates_required')
    if not PER_CANDIDATE_RANGE[0] <= assignment['per_candidate'] <= PER_CANDIDATE_RANGE[1]:
        raise ValueError('all_vs_all_per_candidate_out_of_range')
    if any(not math.isfinite(assignment[unit]) or assignment[unit] <= 0 for unit in UNITS):
        raise ValueError('all_vs_all_credit_units_must_be_positive')
    units = {unit: assignment[unit] for unit in UNITS}
    return {'per_candidate': assignment['per_candidate'], 'query_ref': query, 'search_ref': search, 'candidates': names,
            'units': units, 'target': units['handoff_unit'] + units['information_unit'] + units['graded_unit'],
            'scope': assignment['scope'], 'organism': assignment.get('organism')}
