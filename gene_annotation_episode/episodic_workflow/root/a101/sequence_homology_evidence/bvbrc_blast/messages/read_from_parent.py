"""What the parent gives: the commission of one BV-BRC database search, controlled values and record references only.
This is the only place the assignment is read. A wrong commission raises and the run fails; nothing repairs it.

``query_refs``: exactly one subject record of the parent's scope, and ``input_refs``: the records its sequence is read
from (the sequence artifact), both passed in custody. ``program`` (a program of the service), ``database`` (the
precomputed BV-BRC databases the episode offers) and ``resource_id`` (the bound BV-BRC resource) are chosen by the
parent. ``handoff_unit``, ``information_unit`` and ``graded_unit`` are the credits of the handoff, of an estimate held or
a status request that shows a fact the earlier ones did not, and of the graded result. One commission does the whole
search: nothing from an earlier visit is passed back."""
import math

from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.blast_search import (
    PROGRAM_UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_blast_search import (
    DATABASES)

UNITS = ('handoff_unit', 'information_unit', 'graded_unit')
ASSIGNMENT_FORM = RecordForm({
    'query_refs': Field('record_refs', 'The query: exactly one subject record of the parent\'s scope, passed in custody'),
    'input_refs': Field('record_refs', 'The records the query\'s sequence is read from (its sequence artifact), passed '
                                       'in custody'),
    'program': ChoiceField('text', 'The BLAST program; it must take the query\'s molecule', tuple(sorted(PROGRAM_UNITS))),
    'database': ChoiceField('text', 'The precomputed BV-BRC database, as the application spells it', tuple(DATABASES)),
    'resource_id': Field('text', 'The bound BV-BRC resource of the job service the search is launched on'),
    'handoff_unit': Field('number', 'The credit of the established handoff (positive)'),
    'information_unit': Field('number', 'The credit of an estimate held and of a status request that shows a fact the '
                                       'earlier ones did not (positive)'),
    'graded_unit': Field('number', 'The credit of the established graded result (positive)'),
})


def read_from_parent(assignment, message):
    (query,) = assignment['query_refs']
    if any(not math.isfinite(assignment[name]) or assignment[name] <= 0 for name in UNITS):
        raise ValueError('bvbrc_blast_credit_units_must_be_positive')
    if DATABASES[assignment['database']] != PROGRAM_UNITS[assignment['program']][1]:
        raise ValueError('bvbrc_blast_database_does_not_hold_what_the_program_searches')
    fields = {name: assignment[name] for name in ('program', 'database', 'resource_id')}
    return {'fields': fields, 'query_ref': query, 'units': {name: assignment[name] for name in UNITS}}
