"""What the parent gives: the commission of one BV-BRC database search, controlled values and record references only.
This is the only place the assignment is read. A wrong commission raises and the run fails; nothing repairs it.

``searched_refs``: exactly one sequence record the parent holds (the sequence to search), and ``input_refs``: the records its sequence is read
from (the sequence artifact), both passed in custody. ``program`` (a program of the service), ``database`` (one of the
precomputed BV-BRC databases this episode searches, protein and nucleotide: ``task.DATABASES``) and ``resource_id`` (the
bound BV-BRC resource) are chosen by the parent. ``handoff_unit``, ``information_unit`` and ``graded_unit`` are the credits of the handoff, of an estimate held or
a status request that shows a fact the earlier ones did not, and of the graded result. ``until`` says where this commission ends:
``launched`` (estimate and launch, then the child parks: it returns at once with a wait notice) or ``extracted`` (follow
the search to its graded result; also how a parked search is resumed). On a resuming commission the parent passes back, in
custody, the records the earlier commission returned: ``handoff_refs``, ``check_refs`` and ``closure_refs`` (what the child's
code reads to rebuild its state), with ``known_ended`` (a passed-back status already shows the search ended). The
commission's finite target is the credit still obtainable under ``until``: the estimate held and the launch (unless a
handoff is passed back), the search known ended (``until`` ``extracted`` and not already known ended) and the graded
result (``until`` ``extracted``); each is worth its unit once."""
import math

from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.blast_search import (
    PROGRAM_UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_blast_search import (
    UNTIL)

from ..task import DATABASES, PROGRAMS

UNITS = ('handoff_unit', 'information_unit', 'graded_unit')
ASSIGNMENT_FORM = RecordForm({
    'searched_refs': Field('record_refs', 'The sequence to search: exactly one sequence record the parent holds, passed in custody'),
    'input_refs': Field('record_refs', 'The records that sequence is read from (its sequence artifact), passed '
                                       'in custody'),
    'program': ChoiceField('text', 'The BLAST program; it must take the letters of the searched sequence', PROGRAMS),
    'database': ChoiceField('text', 'The precomputed BV-BRC database: a genome set as the application spells it (its '
                                    'proteins), or the set, a dot and the application\'s nucleotide type (ffn or fna)'
                                    '', tuple(DATABASES)),
    'resource_id': Field('text', 'The bound BV-BRC resource of the job service the search is launched on'),
    'until': ChoiceField('text', 'Where this commission ends: launched (estimate and launch, then park and return) or '
                                 'extracted (follow the search to its graded result)', UNTIL),
    'handoff_unit': Field('number', 'The credit of the established handoff (positive)'),
    'information_unit': Field('number', 'The credit of an estimate held and of a status request that shows a fact the '
                                       'earlier ones did not (positive)'),
    'graded_unit': Field('number', 'The credit of the established graded result (positive)'),
    'handoff_refs': Field('record_refs', 'The handoff record of a search an earlier visit launched, passed back in custody',
                          required=False),
    'check_refs': Field('record_refs', 'The status records of that search, passed back in custody', required=False),
    'closure_refs': Field('record_refs', 'The closure record of that search, passed back in custody', required=False),
    'known_ended': Field('boolean', 'Whether a passed-back status record already shows the search ended', required=False),
})


PRIOR = ('handoff_refs', 'check_refs', 'closure_refs')


def read_from_parent(assignment, message):
    (searched,) = assignment['searched_refs']
    if any(not math.isfinite(assignment[name]) or assignment[name] <= 0 for name in UNITS):
        raise ValueError('bvbrc_blast_credit_units_must_be_positive')
    if DATABASES[assignment['database']]['unit'] != PROGRAM_UNITS[assignment['program']][1]:
        raise ValueError('bvbrc_blast_database_does_not_hold_what_the_program_searches')
    units, until = {name: assignment[name] for name in UNITS}, assignment['until']
    prior = {name: list(assignment.get(name, [])) for name in PRIOR}
    resumed, known_ended = bool(prior['handoff_refs']), assignment.get('known_ended', False)
    if until == 'launched' and resumed:
        raise ValueError('bvbrc_blast_a_continuation_follows_the_search_to_its_result')
    # The units still obtainable under ``until``: the estimate held and the launch (not when a handoff is passed back), the
    # search known ended and the graded result (``extracted`` only; the first not when it is already known ended).
    target = 0.0 if resumed else units['information_unit'] + units['handoff_unit']
    if until == 'extracted':
        target += units['graded_unit'] + (0.0 if known_ended else units['information_unit'])
    fields = {name: assignment[name] for name in ('program', 'database', 'resource_id')}
    return {'fields': fields, 'searched_ref': searched, 'units': units, 'until': until, 'prior': prior,
            'resumed': resumed, 'known_ended': known_ended, 'target': target}
