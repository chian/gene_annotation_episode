"""What the parent gives: the commission of one database search, controlled values and record references only. This is
the only place the assignment is read. A wrong commission raises and the run fails; nothing repairs it.

``analysis_kind``: the declared kind of BLAST use (this episode is a database search; the kind derived from the job
must agree, ``database_blast_search.submit_search``). ``query_refs``: exactly one subject record of the parent's scope,
and ``input_refs``: the records its sequence is read from (the sequence artifact), both passed in custody. ``program``
(a program of the service), ``database`` (the hosted databases the episode offers) and ``hitlist_size`` (an integer in
its range) are chosen by the parent; ``resource_id`` is the bound API resource. ``handoff_unit``, ``information_unit``
and ``graded_unit`` are the credits of the handoff, of a status request that shows a fact the earlier ones did not, and
of the graded result.

On a later visit the parent passes back, in custody, the records this episode returned: ``handoff_refs``,
``check_refs``, ``closure_refs`` and ``graded_refs``. What they hold is what the parent already has: only what is new
since earns credit."""
import math

from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.blast_search import (
    PROGRAM_UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.database_blast_search import (
    ANALYSIS_KIND, DATABASES, HITLIST_RANGE)

UNITS = ('handoff_unit', 'information_unit', 'graded_unit')
PRIOR = ('handoff_refs', 'check_refs', 'closure_refs', 'graded_refs')
ASSIGNMENT_FORM = RecordForm({
    'analysis_kind': ChoiceField('text', 'The declared kind of BLAST use: a database search', (ANALYSIS_KIND,)),
    'query_refs': Field('record_refs', 'The query: exactly one subject record of the parent\'s scope, passed in custody'),
    'input_refs': Field('record_refs', 'The records the query\'s sequence is read from (its sequence artifact), passed '
                                       'in custody'),
    'program': ChoiceField('text', 'The BLAST program; it must take the query\'s molecule', tuple(sorted(PROGRAM_UNITS))),
    'database': ChoiceField('text', 'The hosted database, as the service spells it', tuple(DATABASES)),
    'hitlist_size': Field('integer', 'The largest number of database sequences to report (1 to 200)'),
    'resource_id': Field('text', 'The bound API resource of the job service the search is submitted on'),
    'handoff_unit': Field('number', 'The credit of the established handoff (positive)'),
    'information_unit': Field('number', 'The credit of a status request that shows a fact the earlier ones did not '
                                        '(positive)'),
    'graded_unit': Field('number', 'The credit of the established graded result (positive)'),
    'handoff_refs': Field('record_refs', 'The handoff record of an earlier visit, passed back in custody',
                          required=False),
    'check_refs': Field('record_refs', 'The check records of earlier visits, passed back in custody', required=False),
    'closure_refs': Field('record_refs', 'The closure record of an earlier visit, passed back in custody',
                          required=False),
    'graded_refs': Field('record_refs', 'The graded records of an earlier visit, passed back in custody',
                         required=False),
})


def read_from_parent(assignment, message):
    (query,) = assignment['query_refs']
    if not HITLIST_RANGE[0] <= assignment['hitlist_size'] <= HITLIST_RANGE[1]:
        raise ValueError('database_blast_hitlist_size_out_of_range')
    if any(not math.isfinite(assignment[name]) or assignment[name] <= 0 for name in UNITS):
        raise ValueError('database_blast_credit_units_must_be_positive')
    if DATABASES[assignment['database']] != PROGRAM_UNITS[assignment['program']][1]:
        raise ValueError('database_blast_database_does_not_hold_what_the_program_searches')
    fields = {name: assignment[name] for name in ('analysis_kind', 'program', 'database', 'hitlist_size', 'resource_id')}
    return {'fields': fields, 'query_ref': query, 'units': {name: assignment[name] for name in UNITS},
            'prior': {name: list(assignment.get(name, [])) for name in PRIOR}}
