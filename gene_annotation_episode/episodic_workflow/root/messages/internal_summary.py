"""Where the annotation stands, from the loop's view: what the commissioner gave, the claims made and, for each of the
nine axes, what its head's returns add up to. Only the reports ``messages/read_from_child.py`` made and the outcomes of
the root's own tool are read (numbers, flags, looked-up names and record references); a head's own result is not.

For each axis: ``credit`` (the axis credit; 0 before its head's first return), ``credit_after_each_return`` (the axis
credit after each return, in order), ``finding`` (the numbers and flags of its latest finding), ``annotation_rows``
(the rows of a head that scores the annotations it finds: those of its latest return that carried any), ``claim_rows``
(the rows of a head that checks claims, by claim: the latest row its sheet gave each claim), ``claim_sheets`` (by
claim, the sheet states of the head's latest return on that claim, which go back to it when it is commissioned on that
claim again), ``claim_commissions`` (by claim, how often the head was commissioned on it), ``record_refs`` (every record
its head returned so far, which goes back to that head at its next commission), ``outstanding_job_refs`` (the job
records of its latest return) and ``outstanding_jobs`` (how many jobs its head left running at its latest return). ``commissions`` lists the axes commissioned, in order.

The axis credit is made from what the head's returned credit measures (``read_from_child.CREDIT_RETURNED``): a
``standing`` return is the axis credit itself; a ``rise`` return is added to the axis credit before it.

Claims. ``claims`` lists the claims the tool ``make_claims`` made, each with the annotation it was made from (the tool
was called for that annotation: nothing attaches a claim to an annotation afterwards), what it says (predicate and the
looked-up name of its molecule) and its records; ``claims_made`` holds the annotations the tool was called for.
``units`` says of every unit, in order, whether its outcome is pending (``credit.outcome_pending``).

The root's scoring sheet (``annotations``): one line per function, with one row per axis that scored it.

Which names are one function is decided here, where all the evidence is (the owner, 2026-11-23: an annotation is a
function; "leave a101 names alone until root"). Two heads, and one head, name one function in several ways: scoring it
on several lines wastes work, and joining two different functions corrupts the score. The rule (``same_function``;
its starting point is the note on deduplicating candidate annotations of 2026-11-23, not settled knowledge):

1. A name or an alias never joins two annotations.
2. Two annotations are one function only when a deciding source of function-level identifiers
   (``read_from_child.DECIDING_SOURCES``) gives both the same identifier and no deciding source that gives both an
   identifier separates them. The identifiers are read by the head from the proteins behind its candidate, never from
   a search by a name.
3. What a source gives an annotation is the set of its identifiers that EVERY protein behind the annotation that has
   the source carries (the hit count of the identifier equals the source's protein count). One protein may carry
   several identifiers of one source (found on CspA: two NCBIfam identifiers), and then the set is that pair; proteins
   that split over identifiers (half carry one, half another) share none, the set is empty, and the annotation is
   unsettled in that source: it is joined to nothing and separated from nothing by it. Two annotations agree in a
   source when their sets overlap and are separated by it when both sets are non-empty and do not overlap.
4. A line holds annotations that are one function pair by pair (the relation does not chain: A with B and B with C does
   not join A with C when a source separates them).
Two annotations of the same vocabulary and the same identifier of their own (a family accession, a record reference)
are the same annotation. Everything else stands on its own line.

A line is shown under its leading member (the one with the highest score): its vocabulary, name and identifiers, and
``members``: every annotation on the line with the axis that named it and the score that axis gave it. The row an axis
gives a line. An axis that scores annotations and has applied the root's grouping (the owner, 2026-11-23: "the purpose
is to make the arms annotation scores honest"; the head rescores its own records under the grouping, the mean over the
hits of all the members, which the root cannot compute from the per-name scores): the score of the head's group
whose members are exactly the line's members from that axis. Where no such group exists (the head has not been given
this grouping yet, or takes none): the highest score it gave a member, a stand-in that never adds the members' scores
(that would count the same tests twice). ``groups`` holds, per axis that takes a grouping, the grouping the root would
send it now (``groups_of``): one group per line with two or more of that axis's own candidates. An axis that checks claims gives the
line one row made from its rows of the line's claims (``claim_axis_row``): the support of the claims of known status
summed, their opposition summed, and the score ``tanh((support - opposition) / CLAIM_SCALAR_DIVISOR)``, which for one
claim is exactly the scalar that head's own sheet gives it (A105's rule for its sheet, applied over the claims of one
annotation: each claim is a separate thing the annotation says, checked on its own). A claim is on the line of the
annotation it was made from.

The merger of the axes is the root's hypervolume (``credit.hypervolume``, the owner's rule for the root): the score of
an annotation is ``prod_i (1 + K * s_i) ** w_i - 1`` over the nine axes, where ``s_i`` is the score axis ``i`` gives
that annotation. The concept: the axes are independent kinds of evidence, and an annotation stands on how many of
them agree. So the axes multiply: an annotation scored on one axis alone has exactly that axis's score (times ``K``),
and the same evidence spread over several axes scores more than it would on one. An axis that has not scored the
annotation, or whose row for it is of unknown status, takes ``s_i = 0``: its factor is 1, so it neither adds nor erases
what the other axes established (the offset ``credit.EPSILON`` of the hypervolume), and the row keeps its status, so
unknown is never read as a measured zero. An axis whose score is negative (its evidence says the annotation does not
hold) has a factor below 1 and discounts what the other axes built; it cannot reach 0 or below (``credit.axis_gain``
fails there). The same arithmetic over the axis credits is the annotation credit; the score reads no credit and the
credit reads no score.

An annotation with no row of known status has status unknown and no score. The sheet is ordered: the annotations of
known status by score, highest first, then the unknown ones; the first, when its status is known, is the best
annotation."""
import math

from ..credit import AXIS_WEIGHTS, hypervolume
from .read_from_child import CREDIT_RETURNED, DECIDING_SOURCES, ORGANISM_FINDER

ROW_FIELDS = ('status', 'score', 'support', 'opposition')
# net -> the score of an axis that checks claims: tanh(net / CLAIM_SCALAR_DIVISOR), the divisor that head's sheet uses.
CLAIM_SCALAR_DIVISOR = 2.0


IDENTITY_FIELDS = ('vocabulary', 'name', 'identifier', 'function_identifiers', 'identifier_sources',
                   'hits_without_identifier')


def settled_identifiers(annotation):
    """``{source: the identifiers of that source every protein behind the annotation that has the source carries}``,
    for the deciding sources in which that set is not empty (rule 3 of the module text)."""
    proteins = {row['source']: row['protein_count'] for row in annotation.get('identifier_sources', ())}
    settled = {}
    for row in annotation.get('function_identifiers', ()):
        if row['source'] in DECIDING_SOURCES and row['hit_count'] == proteins[row['source']]:
            settled.setdefault(row['source'], set()).add(row['identifier'])
    return settled


def same_function(first, second):
    """Whether two annotations are one function (rules 1 to 3 of the module text), or the same annotation by their
    own vocabulary and identifier."""
    one, other = settled_identifiers(first), settled_identifiers(second)
    shared = [source for source in one if source in other]
    if shared:
        return all(one[source] & other[source] for source in shared)
    return ('identifier' in first and 'identifier' in second and first['vocabulary'] == second['vocabulary']
            and first['identifier'] == second['identifier'])


def annotation_key(annotation):
    """The identity of a candidate annotation as one text: its settled function-level identifiers when it has any, else
    its vocabulary and its own identifier, or its name when it has none."""
    settled = settled_identifiers(annotation)
    if settled:
        return 'function:' + ';'.join(source + '=' + '+'.join(sorted(settled[source])) for source in sorted(settled))
    return annotation['vocabulary'] + ':' + (annotation['identifier'] if 'identifier' in annotation
                                             else annotation['name'])


def identity_of(annotation):
    """The identity fields of an annotation as the sheet carries them."""
    return {name: annotation[name] for name in IDENTITY_FIELDS if name in annotation}


def claim_axis_row(rows):
    """The row an axis that checks claims gives one annotation, from its rows of that annotation's claims."""
    known = [row for row in rows if row['status'] != 'unknown']
    if not known:
        return {'status': 'unknown'}
    support = math.fsum(row['support'] for row in known)
    opposition = math.fsum(row['opposition'] for row in known)
    return {'status': 'measured_zero' if all(row['status'] == 'measured_zero' for row in known) else 'measured',
            'score': math.tanh((support - opposition) / CLAIM_SCALAR_DIVISOR),
            'support': support, 'opposition': opposition}


def on_line(annotation, line):
    """Whether ``annotation`` (the annotation a claim was made from) is on ``line``: it is one function with a member, or
    it is that member."""
    return any(same_function(annotation, member) or annotation_key(annotation) == annotation_key(member)
               for _, member in line)


def member_identity(row):
    """A candidate named exactly as its head returned it: its vocabulary, name and own identifier."""
    return {name: row[name] for name in ('vocabulary', 'name', 'identifier') if name in row}


def groups_of(slot, lines):
    """The grouping of the candidates of ``slot`` the lines give, in the form a head's commission takes it
    (``[{'members': [...]}]``): one group per line that holds two or more of that axis's own candidates, each member
    named exactly as the head returned it, in a fixed order."""
    groups = [sorted((member_identity(row) for member_slot, row in line if member_slot == slot),
                     key=lambda member: (member['vocabulary'], member['name'])) for line in lines]
    return [{'members': group} for group in sorted((group for group in groups if len(group) > 1),
                                                   key=lambda group: (group[0]['vocabulary'], group[0]['name']))]


def function_lines(axes):
    """The annotations the axes named, grouped into lines (rule 4 of the module text): each line a list of
    ``(slot, row)``, the annotation with the highest score first. An annotation joins the first line every member of
    which it is one function with (or is the same annotation as)."""
    named = [(slot, row) for slot, axis in axes.items() for row in axis['annotation_rows']]
    lines = []
    for slot, row in sorted(named, key=lambda item: -item[1]['score']):
        line = next((line for line in lines if all(same_function(row, member) for _, member in line)), None)
        if line is None:
            lines.append([(slot, row)])
        else:
            line.append((slot, row))
    return lines


def scoring_sheet(axes, claims):
    """The root's scoring sheet from the rows of the axes and the claims (see the module text)."""
    sheet = []
    lines = function_lines(axes)
    placed = set()
    for line in lines:
        leader = line[0][1]
        by_axis = {}
        for slot, row in line:
            if slot not in by_axis or row['score'] > by_axis[slot]['score']:
                by_axis[slot] = {name: row[name] for name in ROW_FIELDS if name in row}
        for slot in list(by_axis):
            members = sorted((member_identity(row) for member_slot, row in line if member_slot == slot),
                             key=lambda member: (member['vocabulary'], member['name']))
            for group in axes[slot]['grouped_rows']:
                if sorted(group['members'], key=lambda member: (member['vocabulary'], member['name'])) == members:
                    by_axis[slot] = {'status': 'measured' if group['score'] else 'measured_zero', 'score': group['score']}
        for slot, axis in axes.items():
            rows = [axis['claim_rows'][claim['claim_ref']] for claim in claims
                    if claim['claim_ref'] in axis['claim_rows'] and on_line(claim['annotation'], line)]
            if rows:
                by_axis[slot] = claim_axis_row(rows)
        placed.update(claim['claim_ref'] for claim in claims if on_line(claim['annotation'], line))
        sheet.append(_line(identity_of(leader), by_axis,
                           [{**{name: row[name] for name in ('vocabulary', 'name', 'identifier') if name in row},
                             'axis': slot, 'score': row['score']} for slot, row in line]))
    # a claim whose annotation no axis names any more still has its line (the annotation it was made from)
    orphans = {}
    for claim in claims:
        if claim['claim_ref'] not in placed:
            orphans.setdefault(annotation_key(claim['annotation']), []).append(claim)
    for group in orphans.values():
        by_axis = {}
        for slot, axis in axes.items():
            rows = [axis['claim_rows'][claim['claim_ref']] for claim in group if claim['claim_ref'] in axis['claim_rows']]
            if rows:
                by_axis[slot] = claim_axis_row(rows)
        if by_axis:
            sheet.append(_line(identity_of(group[0]['annotation']), by_axis, []))
    return sorted(sheet, key=lambda annotation: (annotation['status'] == 'unknown', -annotation.get('score', 0.0)))


def _line(identity, by_axis, members):
    """One line of the sheet: the identity it is shown under, its merged score, its axis rows and its members."""
    line = dict(identity)
    known = {slot: row for slot, row in by_axis.items() if row['status'] != 'unknown'}
    if known:
        line.update(
            status='measured_zero' if all(row['status'] == 'measured_zero' for row in known.values()) else 'measured',
            score=hypervolume({slot: known[slot]['score'] if slot in known else 0.0 for slot in AXIS_WEIGHTS}))
    else:
        line['status'] = 'unknown'
    return {**line, 'rows': [{'axis': slot, **row} for slot, row in by_axis.items()], 'members': members}


def passed_down(organism):
    """What the root passes to a head that takes the organism: of the candidate taxa the organism identification head
    returned, the leading candidate with the nested candidates on its lineage (the vaguer calls that support it, so the
    receiver sees how much of its score each level carries) and the leading rival, each with its role. A head reads
    them by degree: the scores say how far the placement is settled."""
    rows, placement = organism['candidates'], organism['placement']
    if 'leader_taxon_id' not in placement:
        return []
    leader = next(row for row in rows if row['taxon_id'] == placement['leader_taxon_id'])
    chosen = [{**leader, 'role': 'leader'}]
    chosen.extend({**row, 'role': 'on_the_leaders_lineage'} for row in rows
                  if row['taxon_id'] != leader['taxon_id'] and row['taxon_id'] in leader['lineage_taxon_ids'])
    if 'rival_taxon_id' in placement:
        chosen.extend({**row, 'role': 'rival'} for row in rows if row['taxon_id'] == placement['rival_taxon_id'])
    return [{name: row[name] for name in ('taxon_id', 'name', 'rank_code', 'score', 'role')} for row in chosen]


def internal_summary(view):
    axes = {slot: {'credit': 0.0, 'credit_after_each_return': [], 'finding': {}, 'record_refs': [],
                   'outstanding_job_refs': [], 'outstanding_jobs': 0, 'annotation_rows': [], 'grouped_rows': [],
                   'grouping_in_force': [], 'groups_sent': None, 'claim_rows': {}, 'claim_sheets': {},
                   'claim_commissions': {}}
            for slot in AXIS_WEIGHTS}
    claims, claims_made, commissions, units = [], [], [], []
    organism = {'commissions': 0, 'credit': 0.0, 'candidates': [], 'placement': {}, 'test_count': 0, 'record_refs': []}
    for outcome in view.outcomes:
        units.append({'pending': outcome['kind'] == 'child' and outcome['report']['outstanding_jobs'] > 0})
        if outcome['kind'] == 'child' and outcome['slot'] == ORGANISM_FINDER:
            report = outcome['report']
            organism = {'commissions': organism['commissions'] + 1, 'credit': report['credit'],
                        'candidates': report['organism_rows'], 'placement': report['placement'],
                        'test_count': report['test_count'], 'record_refs': report['record_refs']}
            continue
        if outcome['kind'] == 'tool':
            annotation = outcome['arguments']['annotation']
            claims_made.append(annotation_key(annotation))
            claims.extend({**claim, 'annotation': annotation} for claim in outcome['outcome']['result']['claims'])
            continue
        slot, report = outcome['slot'], outcome['report']
        axis = axes[slot]
        commissions.append(slot)
        axis['credit'] = axis['credit'] + report['credit'] if CREDIT_RETURNED[slot] == 'rise' else report['credit']
        axis['credit_after_each_return'].append(axis['credit'])
        axis['finding'] = report['finding']
        if report['annotation_rows']:
            axis['annotation_rows'] = report['annotation_rows']
        axis['grouped_rows'], axis['grouping_in_force'] = report['grouped_rows'], report['grouping_in_force']
        axis['groups_sent'] = outcome['arguments'].get('candidate_groups', [])
        axis['claim_rows'].update({row['claim_ref']: row for row in report['claim_rows']})
        if 'claim_ref' in outcome['arguments']:
            claim_ref = outcome['arguments']['claim_ref']
            axis['claim_sheets'][claim_ref] = report['sheet_state_refs']
            axis['claim_commissions'][claim_ref] = axis['claim_commissions'].get(claim_ref, 0) + 1
        axis['record_refs'].extend(ref for ref in report['record_refs'] if ref not in axis['record_refs'])
        axis['outstanding_job_refs'] = report['outstanding_job_refs']
        axis['outstanding_jobs'] = report['outstanding_jobs']
    lines = function_lines(axes)
    return {**view.parent_input, 'axes': axes, 'claims': claims, 'claims_made': claims_made,
            'annotations': scoring_sheet(axes, claims), 'groups': {slot: groups_of(slot, lines) for slot in axes},
            'commissions': commissions, 'units': units,
            'organism': {**organism, 'passed_down': passed_down(organism)}}
