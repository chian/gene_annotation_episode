"""The commission of each child. A commission is controlled data only: the model chooses among values this episode holds
(``task.commission_fields``: a subject of the scope, a program and a hosted database of fixed sets, a number in a range,
a bound API resource), and this file builds the child's assignment, in the child's own form, from those choices and this
episode's summary. The model writes no assignment, objective or message: the objective is this episode's own fixed text
for the slot and the message is empty. A commission the child does not admit fails (no check here).

Every record the child's code reads is named in a ``record_refs`` field of the assignment: the query subject record and,
in ``input_refs``, every held record it names, and those name in turn (a subject and its sequence artifact: ``_custody``
over the summary's ``named_refs``). When this episode holds an outstanding search of the query that the commission
names (``summary['bvbrc_searches']``), the commission continues it and code passes back, in custody, the records the
child returned for it: its handoff, status and closure records (the rows and what they name, as held). The credit units
are this episode's ``child_credit_units``: ``handoff_unit`` for the handoff, ``information_unit`` for a status request
that shows something new and ``acquired_record_unit`` for the graded result.

Required return fields: of a BV-BRC child, every kind of record the child returns for its job (handoff, status, closure and
graded records), so that this episode holds the job's rows, reads its state from them and can pass them back on a later
visit; of ``all_vs_all``, which waits for and closes its own jobs inside its units, the graded records only (its labelled
products and the committed clustering), so none of its job rows, and none of the files they name, reach this episode."""
from episode_runtime import ChildMessage

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.candidate_measurements import (
    ALIGNMENT_KIND, REPORT_KIND)

ANALYSIS_KIND = 'database_search'

# The objective of each commission: this episode's own text, never the model's.
OBJECTIVES = {
    'bvbrc_blast': 'Search the query sequence against the precomputed BV-BRC database through the BV-BRC application '
                   'service, in this one commission: estimate the duration, launch the search, monitor it until the '
                   'service has ended it and extract the graded result, and return what it established.',
    'bvbrc_msa': 'Align the target with the sequences of the chosen candidates of the held graded BV-BRC search through '
                 'the BV-BRC application service: estimate the duration, launch the alignment, monitor it until the '
                 'service has ended it and extract the graded alignment, and return what it established.',
    'all_vs_all': 'Put the target and the sequences of the chosen candidates of the held graded BV-BRC search in one set, search it '
                  'against itself with BLAST+ on a local resource, tune and commit a clustering of the pairwise bit scores, and '
                  'return what it established: the labelled data products and the graded clustering.',
    'bvbrc_metacats': 'Test the held alignment with MetaCATS through the BV-BRC application service, with groups built by '
                      'code from its candidates and the target in none: estimate the duration, launch the job, monitor it '
                      'until the service has ended it and extract the graded result, and return what it established.',
}
# The return fields every commission of a slot selects.
REQUIRED_RETURN = {
    'bvbrc_blast': ('execution_handoff_refs', 'check_refs', 'closure_refs', 'graded_refs'),
    'bvbrc_msa': ('execution_handoff_refs', 'check_refs', 'closure_refs', 'graded_refs'),
    'bvbrc_metacats': ('execution_handoff_refs', 'check_refs', 'closure_refs', 'graded_refs'),
    'all_vs_all': ('graded_refs',),
}


def _selection(slot, arguments):
    return tuple(dict.fromkeys([*REQUIRED_RETURN[slot], *arguments.get('selection', [])]))


def _custody(references, summary):
    """The held records ``references`` with every held record they name, and those name in turn (the summary's
    ``named_refs``): a pass carries only the records named, and the child's code follows the names (a subject to its
    sequence)."""
    found, pending = [], list(references)
    while pending:
        reference = pending.pop(0)
        if reference not in found:
            found.append(reference)
            pending.extend(summary['named_refs'].get(reference, []))
    return found


def _continued(assignment, job, summary):
    """The assignment of a commission that continues the held job ``job``: its handoff, status and closure rows, passed
    back, and in ``input_refs`` every held record the rows name (and those name in turn): the child returned them with
    the rows, so the head holds them and passes them back."""
    rows = [job['handoff_ref'], *job['check_refs'], *job['closure_refs']]
    assignment.update(handoff_refs=[job['handoff_ref']], check_refs=job['check_refs'], closure_refs=job['closure_refs'],
                      known_ended=job['known_ended'],
                      input_refs=list(dict.fromkeys([*assignment['input_refs'],
                                                     *(ref for ref in _custody(rows, summary) if ref not in rows)])))


def _bvbrc_blast(arguments, summary):
    """The assignment of one BV-BRC database search: the query and its sequence in custody, the program, the database,
    the resource, ``until`` and the three credit units. When the commission continues an outstanding search of the query
    (``summary['bvbrc_searches']``) code passes back, in custody, the records the child returned for it: its handoff and
    status records and the closure record, with whether a status already shows it ended: nothing is submitted again."""
    query = arguments['query_ref']
    units = summary['child_credit_units']
    # the child settles the annotations after it grades its search, from every graded source held: it is passed the
    # scope's records and every source and feature record this episode holds, with the records they name, and the
    # data-product rows the candidate table reads beside a held MetaCATS source (the alignments and the reports)
    settled = [*summary['scope_refs'],
               *(ref for ref in summary['held_record_refs'] if ref.split('_')[0] in ('source', 'feature'))]
    rows = [row['row_ref'] for row in summary['data_products'] if row['kind'] in (ALIGNMENT_KIND, REPORT_KIND)]
    assignment = {'query_refs': [query],
                  'input_refs': [*(ref for ref in _custody([query, *settled], summary)
                                   if ref != query and not ref.startswith('row_')), *rows],
            'program': arguments['program'], 'database': arguments['database'], 'resource_id': arguments['resource_id'],
            'until': arguments['until'], 'handoff_unit': units['handoff_unit'],
            'information_unit': units['information_unit'], 'graded_unit': units['acquired_record_unit'],
            'scope': summary['scope']}
    organisms = [row for row in summary['organism_candidates'] if row['role'] == 'leader']
    if organisms:
        assignment['organism'] = organisms[0]
    held = [search for search in summary['bvbrc_searches'] if search['query_ref'] == query and search['outstanding']]
    if held:
        (search,) = held
        _continued(assignment, search, summary)
    return assignment


def _bvbrc_msa(arguments, summary):
    """The assignment of one BV-BRC alignment: the target and the held search in custody (with every held record they
    name), the candidates (each ``{name}``), ``per_candidate``, the resource, ``until``, the three credit units, the held
    alignment data-product rows (what the child's launch check looks for a reusable alignment in) and, when the commission
    continues an outstanding job of the same fields, the records of that job passed back."""
    query, search = arguments['query_ref'], arguments['search_ref']
    units = summary['child_credit_units']
    # the child settles the annotations after it grades its alignment: passed as to ``bvbrc_blast``
    settled = [*summary['scope_refs'],
               *(ref for ref in summary['held_record_refs'] if ref.split('_')[0] in ('source', 'feature'))]
    rows = [row['row_ref'] for row in summary['data_products'] if row['kind'] in (ALIGNMENT_KIND, REPORT_KIND)]
    named = [ref for ref in _custody([query, search, *settled], summary)
             if ref not in (query, search) and not ref.startswith('row_')]
    assignment = {'query_refs': [query], 'search_refs': [search],
                  'input_refs': list(dict.fromkeys([*named, *summary['alignment_product_refs'], *rows])),
                  'candidates': [{'name': name} for name in arguments['candidates']],
                  'per_candidate': arguments['per_candidate'], 'resource_id': arguments['resource_id'],
                  'until': arguments['until'], 'handoff_unit': units['handoff_unit'],
                  'information_unit': units['information_unit'], 'graded_unit': units['acquired_record_unit'],
                  'scope': summary['scope']}
    organisms = [row for row in summary['organism_candidates'] if row['role'] == 'leader']
    if organisms:
        assignment['organism'] = organisms[0]
    held = [job for job in summary['bvbrc_msa_jobs'] if job['outstanding'] and job['identity'] == {
        'query_ref': query, 'search_ref': search, 'candidates': sorted(arguments['candidates']),
        'per_candidate': arguments['per_candidate']}]
    if held:
        (job,) = held
        _continued(assignment, job, summary)
    return assignment


def _bvbrc_metacats(arguments, summary):
    """The assignment of one MetaCATS analysis: the target, the alignment's data-product row and the alignment's source (the
    held record whose alignment artifact the row labels), each in custody with every held record it names (the sheet and the
    alignment artifact), the resource, ``until``, the three credit units and, when the commission continues an
    outstanding job of the same fields, the records of that job passed back."""
    query, alignment = arguments['query_ref'], arguments['alignment_ref']
    units = summary['child_credit_units']
    (option,) = [item for item in summary['metacats_options'] if item['alignment_ref'] == alignment]
    # the child settles the annotations after it grades its report: passed as to ``bvbrc_blast``
    settled = [*summary['scope_refs'],
               *(ref for ref in summary['held_record_refs'] if ref.split('_')[0] in ('source', 'feature'))]
    rows = [row['row_ref'] for row in summary['data_products'] if row['kind'] in (ALIGNMENT_KIND, REPORT_KIND)]
    named = [ref for ref in _custody([query, option['source_ref'], *settled], summary)
             if ref != query and not ref.startswith('row_')]
    assignment = {'query_refs': [query], 'alignment_refs': [alignment],
                  'input_refs': [*named, *(ref for ref in rows if ref != alignment)],
                  'resource_id': arguments['resource_id'], 'until': arguments['until'],
                  'handoff_unit': units['handoff_unit'], 'information_unit': units['information_unit'],
                  'graded_unit': units['acquired_record_unit'], 'scope': summary['scope']}
    organisms = [row for row in summary['organism_candidates'] if row['role'] == 'leader']
    if organisms:
        assignment['organism'] = organisms[0]
    held = [job for job in summary['bvbrc_metacats_jobs'] if job['outstanding'] and job['resource_id'] == arguments[
        'resource_id'] and job['identity']['groups_ref'] == option['groups_ref']]
    if held:
        (job,) = held
        _continued(assignment, job, summary)
    return assignment


def _all_vs_all(arguments, summary):
    """The assignment of one all-vs-all: the target and the held search in custody (with every held record they name), the
    candidates (each ``{name}``), ``per_candidate`` and the three credit units. The child runs on a local resource and chooses the
    clustering tuning itself."""
    query, search = arguments['query_ref'], arguments['search_ref']
    units = summary['child_credit_units']
    # the child settles the annotations after it commits a clustering: passed as to ``bvbrc_blast``
    settled = [*summary['scope_refs'],
               *(ref for ref in summary['held_record_refs'] if ref.split('_')[0] in ('source', 'feature'))]
    rows = [row['row_ref'] for row in summary['data_products'] if row['kind'] in (ALIGNMENT_KIND, REPORT_KIND)]
    named = [ref for ref in _custody([query, search, *settled], summary)
             if ref not in (query, search) and not ref.startswith('row_')]
    assignment = {'query_refs': [query], 'search_refs': [search], 'input_refs': [*named, *rows],
                  'candidates': [{'name': name} for name in arguments['candidates']],
                  'per_candidate': arguments['per_candidate'],
                  'handoff_unit': units['handoff_unit'], 'information_unit': units['information_unit'],
                  'graded_unit': units['acquired_record_unit'], 'scope': summary['scope']}
    organisms = [row for row in summary['organism_candidates'] if row['role'] == 'leader']
    if organisms:
        assignment['organism'] = organisms[0]
    return assignment


ASSIGNMENTS = {'bvbrc_blast': _bvbrc_blast, 'bvbrc_msa': _bvbrc_msa, 'bvbrc_metacats': _bvbrc_metacats,
               'all_vs_all': _all_vs_all}


def msg_to_child(slot, arguments, summary):
    return ChildMessage(objective=OBJECTIVES[slot], message={}, assignment=ASSIGNMENTS[slot](arguments, summary),
                        selection=_selection(slot, arguments))
