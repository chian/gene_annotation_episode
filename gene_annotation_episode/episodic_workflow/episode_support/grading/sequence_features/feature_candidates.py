"""The sheet of feature calls: what the graded sheets an episode holds say about which features a sequence holds: the
candidate feature calls (the slots) with their scores, the claims that sit in them, the claims that wait for one, and the
credit of having found, refined and separated them.

A feature call is a type and a location together (the owner, 2026-11-25: "Identifying type of feature has to come with
location as well. they must come together"): a ``kind`` (a type of ``feature_types``), position ranges on the sequence
(``segments``: ``start`` and ``end``, zero-based, the end not included; several when the feature is read from joined
stretches) and a ``strand`` (``+``, ``-``, or ``.`` when the call names none). ``start`` is always the lower position on
the sequence and ``end`` the upper, whatever the strand. A call that codes a protein (``CDS``), and a call of a part of a
protein, is read in codons from its first letter in reading order, so its positions also state its frame.

CALLS AND CLAIMS. What a tool states about a sequence is one row of its converter (``READERS``):

* A FEATURE CALL states the feature itself: where it starts and where it ends (``claims_start`` and ``claims_end`` both
  true). Tools made for boundaries make these.
* A CLAIM states less. An INTERIOR claim says only that its letters lie inside a feature of this type, read this way; it
  can also claim one end (the lowest position is the feature's start, or the highest is its end). A local alignment makes
  interior claims: it finds a part of a feature, with the strand and the frame, and says nothing of where the feature
  starts or ends, except where it reaches the first or the last position of the known sequence it aligned to.

SLOTS. A slot is one candidate feature call (the owner: "home == a specific feature_call candidate slot"). Slots are what
is scored. Feature calls of one type whose strands agree and that share letters are calls of one slot when they are coding
calls on a strand and read the letters they share in the same frame (separate genes do not overlap in one frame), or, for
any other type, share at least ``SAME_SHARE`` of the letters of the LONGER call (of the longer, because a feature can lie
wholly inside another of its type and be another feature). The owner: "you need a threshold to recognize 'sameness'. So we
should set an overlap threshold now (and for coding features a frame)". A slot is all the feature calls that are the same,
pair by pair or through a chain of such pairs; every position called for it is one of its ``versions`` (each with the
weighted support of the calls that stated exactly it), and its positions are those of the best supported version (the
earliest on a tie). A later, better supported call moves the positions to it: the slot is the unit that is refined.

CLAIMS IN SLOTS, AND CLAIMS THAT WAIT. A claim sits in every slot that includes it: the slot is of the claim's type, their
strands agree, the claim's letters lie WHOLLY inside one version of the slot ("interior here at least implies 100% overlap
so it's a subset of a span"), that version has every end the claim claims at the same position (for a coding claim the end read last may
lie one stop codon inside the version's: a protein alignment ends before the stop codon a gene call includes), and a
coding claim is read in the slot's frame. A claim in a slot adds to the slot's score ("interior claim adds to a score when it sits usefully in a
feature_call slot"). Claims are never joined with each other and no positions are made up from them: a claim is in a slot
or it is not. A claim that no slot includes WAITS ("these are claims waiting for a home"; "they might immediately slot into
a home if homes already exist, or they might wait on the side for a home"): it is kept as it was stated, with its support,
adds to no score, and sits in a slot as soon as one that includes it is called, by whatever tool. A claim that reaches
past a slot's end does not sit in it and stays in view. Nothing here needs a feature call to exist before a claim.

Everything is settled from all the records held, whatever the order they came in: the same records always give the same
slots, the same claims in them and the same waiting claims.

NESTING is by type, not by size, the way the owner ruled for candidate taxa (2026-11-24: "this support from vaguer levels
makes sense with the fines grain level having the most score. never rivals, just different supporting bits of info. rivals
are when there is a difference in call that is not nested."; 2026-11-25: "finer candidate has to do with feature type not
size ... within a gene you might have a motif or a secondary structure or a protein region (ATP binding site) or something
like that. That's nested. But two proteins are not nested."):

* The types are nested in one hierarchy (``feature_types.ABOVE``).
* One slot is WITHIN another when its type is under the other's in that hierarchy, their strands agree, its letters lie
  wholly inside the other's and, for a part of a protein within a coding sequence, it is read in that frame.
* The support at a slot (its own calls and the claims in it) is support for every slot within it. The score of a slot is
  the sum, over the tests, of the weight of the test's sheet times the test's bits at the slot and at every slot it is
  within. The finest slot the tests agree on has the highest score, as a species has the support of its genus and family.

RIVALS. What may share letters was read from the literature on 2026-11-25 and settled with the owner: a gene can lie wholly
inside another in a different frame (phage phiX174 gene E in gene D; the surface gene of hepatitis B virus in its polymerase
gene); a few shared letters between neighbouring genes are ordinary everywhere (in 7,450 reference virus genomes 84 per
cent of the overlaps were under 50 letters, Schlub and Holmes 2020; in 338 genomes of bacteria and archaea the overlaps of
60 letters or more of genes of one direction were found to be wrong start codons, Palleja, Harrington and Bork 2008); a
regulatory element can lie wholly inside a gene on either strand; a protein domain can lie wholly inside another. So:

* Only slots of what a stretch is made into compete (``COMPETING``: gene, coding sequence, tRNA, rRNA). Two of
  them are RIVALS when they share ``RIVAL_LETTERS`` letters or more and are neither the same slot nor nested. Fewer shared
  letters are the ordinary overlap of neighbours and get no notice.
* A tRNA or an rRNA (``RNA_UNITS``) competes for its letters with a coding sequence on either strand and with another
  tRNA or rRNA call: the two are rivals when they share more than ``RNA_SHARE`` (half) of the RNA gene's letters (of the
  shorter, between two RNA genes). No virus was found in which one overlaps a coding sequence; a coding sequence called
  across one is the usual false call. A tRNA is about 75 letters, so the 60 letters of coding sequences would notice
  almost nothing; the half is a starting value of 2026-11-25 with no source behind it. Which rRNA or tRNA it is, is
  identity, which belongs to the annotation and is not known here.
* Every other RNA gene (``ncRNA``) competes with nothing, like a regulatory element: microRNAs lie inside open reading
  frames on both strands (human cytomegalovirus miR-UL70-1, UL112-1, UL148D, US33-1; Kaposi's sarcoma herpesvirus miR-K10
  inside the K12 reading frame), a long non-coding RNA runs over the end of one (PAN over K7), a phage antisense RNA
  covers 55 letters of one (lambda OOP over cII), and small RNAs sit inside longer RNA genes. Looked up 2026-11-25; the
  owner: "your rule is fine for now".
* A rival is a competitor for the same letters, not a verdict that one of the two is false: in a virus both may stand.
  Nothing is ever removed or lowered for having a rival; the facts of the shared letters are kept with the pair
  (``overlap_facts``) for when the organism is known.
* A regulatory element, a transcription unit, a mobile element, a repeat and the parts of a protein are listed with their
  scores and positions and have no rivals (the owner: "regulatory elements just get marked without any rival notice, same
  with domains").

ONE READING OF THE WHOLE SEQUENCE. Some things hold for a sequence as a whole and cannot be two at once: its genetic code
(the owner, 2026-11-25: "you definitely shouldn't gain credit for a different genetic code. you can only gain credit on one
or another. you can't shift codes in one genome, so it's kind of like an organismal taxa. you can't have two in one
genome"). A test made under such a reading says so (``ALTERNATIVES``: per sheet schema, the dimension and the value its
grading was made under, for example the genetic code 11). Tests of one sequence under different values of one dimension
are alternatives, never added together: the value whose tests carry the most weighted support is the one held (the first
made on a tie), and the tests under any other value are set aside: they stay held and listed, and add to no score and no
credit. Tests under the same value add as usual. Running another value can therefore gain only by being the better one.

The cutoffs are hard: two calls are one slot or they are not, a claim is in a slot or it is not, two slots are rivals or
they are not (the owner: "rivals are vs each other and are units"). The degrees are in the scores.

A test is one graded source: ``<sheet>@<source reference>``. What a sheet's bits are and what its weight is are stated with
the tool that makes the sheet (``READERS``, ``SHEET_WEIGHT``); a bit is a number from 0 to 1. No tool is entered yet, and
the subscoring of the tools that speak to the same question (so that many hits of one search do not simply add up) is
entered with them.

Which slots a test can measure: a test measures a slot only when the test can speak of the slot's kind (``covers``:
kinds; a kind above or under one of them in the hierarchy counts).

The score is part of the annotation scoring: an annotation belongs to one feature call and cannot be better than the
feature it sits on (the owner, 2026-11-25: "features need to be scored and those features get annotations"); the root
applies it. It names nothing.

THE CREDIT, counted by going through the tests in the order they came, over what all the records held settle:

* Entry of a slot, at the first test that called it. A new possibility (nested with no listed slot) earns its score. A
  finer slot within a listed one earns what it adds: its score less the score of the highest scoring listed slot it is
  within. A slot that only has listed slots within it earns nothing. Another call of a listed slot has no entry.
* A claim earns when it is found (the owner: "a waiting claim in my scheme should earn credit otherwise there is no
  reason to do it"), and earns the same whether a slot called so far includes it or not (the owner, 2026-11-25: "the
  scoring should not depend on order in this case with claim being put in a feature call right away vs not. that seems
  like a trivial fix."): a claim earns its weighted bit when it is the first claim of its type and reading on its letters
  (the strongest of a test's claims first); a claim on letters where a claim of that type and reading was already held
  earns nothing. A feature call is not an earlier statement that takes a claim's credit away. What a claim earned is not
  paid again: it is taken off the first entry of a slot it sits in that was not yet listed when the claim was paid, or of
  a slot within such a slot (their scores count it). So a call and a claim that sits in it earn the same together in
  either order: the call's own weighted bit and the claim's.
* Differential. A test earns the absolute difference of the moves of ONE pair: the two leading rival slots among those
  listed before the test that the test can measure (the highest score, then the highest score among its rivals).
* Credit is the sum of these. A test is held once: the same test twice raises. When a later call joins two slots into one, the entry
  the second had earned is no longer there: the credit steps down once, because it was not a new possibility.

Measurements of different sequences are never compared: every table is per sequence. Nothing here reads a file or runs a
tool: it reads the records the episode holds, through the reader it is given."""
import math

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    source_tool_grading_entries)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features.feature_types import (
    ABOVE, CODING, KINDS, PROTEIN_PARTS, STRANDS)

# The share of the LONGER call's letters two feature calls of one type (not coding) must share to be calls of one slot. A
# starting value set on 2026-11-25 with no run and no source behind it. To be tuned from real runs.
SAME_SHARE = 0.8
# The shared letters at or above which two competing slots are rivals: the length above which the overlaps of genes of
# one direction in bacteria and archaea were found to be wrong calls (60, Palleja et al. 2008), which also lies above
# 84 per cent of the gene overlaps of viruses (under 50, Schlub and Holmes 2020).
RIVAL_LETTERS = 60
# The types that compete for letters: what a stretch is made into.
COMPETING = ('gene', CODING, 'tRNA', 'rRNA')
# The RNA genes that compete for their letters, and the share of the RNA gene's letters above which a slot of one and
# another competing slot are rivals.
RNA_UNITS = ('tRNA', 'rRNA')
RNA_SHARE = 0.5
# The types read in codons.
IN_CODONS = (CODING, *PROTEIN_PARTS)
# The letters of a stop codon: how far the end of a protein lies inside the end of its coding sequence.
STOP_CODON = 3
# Per family of technique (the first part of a sheet name: ``protein_similarity``, ``nucleotide_similarity``, ...): its
# weight; and per sheet schema: its reader ``grading -> (sheet name, covers, rows)`` with one row per statement of the
# test: ``{'kind', 'strand', 'segments', 'claims_start', 'claims_end', 'feature_ref', 'bit'}``. Entered by each tool's
# converter when it is imported.
SHEET_WEIGHT = {}
READERS = {}
# Per sheet schema: ``grading -> (dimension, value)``, the reading of the whole sequence its test was made under (the
# module's description: tests under different values of one dimension are alternatives). Entered by a tool's converter.
ALTERNATIVES = {}


def held_sources(reader):
    """The sources the episode holds, in the order it obtained them (receipt order)."""
    return [ref for ref in reader.refs() if ref.startswith('source_')]


def sheet_of(test):
    return test.split('@', 1)[0]


def sheet_family(test):
    """The family of technique a test's sheet belongs to: the first part of its sheet name."""
    return sheet_of(test).split(':', 1)[0]


def sheet_weight(test):
    family = sheet_family(test)
    if family not in SHEET_WEIGHT:
        raise ValueError('feature_sheet_family_has_no_stated_weight:' + family)
    return SHEET_WEIGHT[family]


def positions(row):
    """The position ranges of a statement as a tuple of ``(start, end)``."""
    return tuple((segment['start'], segment['end']) for segment in row['segments'])


def low(row):
    """The lowest position a statement gives."""
    return min(segment['start'] for segment in row['segments'])


def high(row):
    """The position after the highest a statement gives."""
    return max(segment['end'] for segment in row['segments'])


def letters(row):
    """The letters a statement gives."""
    return sum(segment['end'] - segment['start'] for segment in row['segments'])


def shared_letters(first, second):
    """The letters two statements both give."""
    return sum(max(0, min(one['end'], other['end']) - max(one['start'], other['start']))
               for one in first['segments'] for other in second['segments'])


def inside(inner, outer):
    """Whether every letter of ``inner`` is a letter of ``outer`` (each range of the one lies in a range of the other)."""
    return all(any(other['start'] <= segment['start'] and segment['end'] <= other['end'] for other in outer['segments'])
               for segment in inner['segments'])


def strands_agree(first, second):
    """Whether two statements are on one strand, or one of them names none."""
    return first['strand'] == second['strand'] or '.' in (first['strand'], second['strand'])


def _read_before(row, boundary, strand):
    """The letters of ``row`` read before ``boundary`` in the reading order of ``strand``: those below it on ``+``, those
    at or above it on ``-``."""
    if strand == '-':
        return sum(max(0, segment['end'] - max(segment['start'], boundary)) for segment in row['segments'])
    return sum(max(0, min(segment['end'], boundary) - segment['start']) for segment in row['segments'])


def same_frame(first, second):
    """Whether two statements on one strand that share letters read them in the same frame: the first shared letter in
    reading order stands at the same place of a codon in both."""
    strand = first['strand']
    shared = [(max(one['start'], other['start']), min(one['end'], other['end']))
              for one in first['segments'] for other in second['segments']
              if max(one['start'], other['start']) < min(one['end'], other['end'])]
    boundary = max(end for _, end in shared) if strand == '-' else min(start for start, _ in shared)
    return (_read_before(first, boundary, strand) - _read_before(second, boundary, strand)) % 3 == 0


def _frames_agree(first, second):
    """Two statements read in codons on named strands must read their shared letters in one frame; any other pair
    agrees."""
    if first['kind'] not in IN_CODONS or second['kind'] not in IN_CODONS or '.' in (first['strand'], second['strand']):
        return True
    return same_frame(first, second)


def same_reading(first, second):
    """Whether two statements say the same kind of thing of letters they share: one type, strands that agree, shared
    letters and, read in codons, one frame."""
    return (first['kind'] == second['kind'] and strands_agree(first, second) and shared_letters(first, second) > 0
            and _frames_agree(first, second))


def same_slot(first, second):
    """Whether two feature calls are calls of one slot (the module's description)."""
    if not same_reading(first, second):
        return False
    if first['kind'] == CODING and '.' not in (first['strand'], second['strand']):
        return True
    return shared_letters(first, second) >= SAME_SHARE * max(letters(first), letters(second))


def sits_in(claim, slot):
    """Whether a claim sits in a slot: the slot is of its type, their strands agree, its letters lie wholly inside one
    version of the slot that has every end the claim claims at the same position, and it is read in the slot's frame. At
    the end a coding sequence is read last (the upper end on ``+``, the lower on ``-``) the claim's end may also lie one
    stop codon inside the version's: a protein alignment that reaches the last residue of a known protein ends before
    the stop codon, and a gene finder's call includes it."""
    if claim['kind'] != slot['kind'] or not strands_agree(claim, slot):
        return False
    # the end read last, where a coding call may carry a stop codon the claim does not
    strand = slot['strand'] if slot['strand'] != '.' else claim['strand']
    stop = STOP_CODON if claim['kind'] == CODING else 0
    after_low, after_high = (stop if strand == '-' else 0), (stop if strand == '+' else 0)
    return any(inside(claim, version)
               and (not claim['claims_start'] or low(claim) - low(version) in (0, after_low))
               and (not claim['claims_end'] or high(version) - high(claim) in (0, after_high))
               and _frames_agree(claim, {**version, 'kind': slot['kind'], 'strand': slot['strand']})
               for version in slot['versions'])


def within(inner, outer):
    """Whether the slot ``inner`` lies within the slot ``outer`` by type (the module's description)."""
    return (outer['kind'] in ABOVE[inner['kind']] and strands_agree(inner, outer) and inside(inner, outer)
            and _frames_agree(inner, outer))


def nested(first, second):
    """Whether one of two slots is within the other."""
    return within(first, second) or within(second, first)


def rivals(first, second):
    """Whether two slots compete for the same letters: both are of a competing type, they are neither one slot nor
    nested, and they share enough letters: more than ``RNA_SHARE`` of the RNA gene (the shorter of two) when one is a
    tRNA or an rRNA, else ``RIVAL_LETTERS`` letters or more."""
    if first['kind'] not in COMPETING or second['kind'] not in COMPETING:
        return False
    if same_slot(first, second) or nested(first, second):
        return False
    rna_genes = [slot for slot in (first, second) if slot['kind'] in RNA_UNITS]
    if rna_genes:
        return shared_letters(first, second) > RNA_SHARE * min(letters(slot) for slot in rna_genes)
    return shared_letters(first, second) >= RIVAL_LETTERS


def overlap_facts(first, second):
    """The plain facts of the letters two slots share, kept for whoever judges the pair later."""
    on_one_strand = first['strand'] == second['strand'] and first['strand'] != '.'
    return {'shared_letters': shared_letters(first, second), 'same_type': first['kind'] == second['kind'],
            'same_strand': on_one_strand,
            'same_frame': (on_one_strand and first['kind'] in IN_CODONS and second['kind'] in IN_CODONS
                           and same_frame(first, second))}


def measurable(slot, covers):
    """Whether a test that can speak of the kinds ``covers`` can measure the slot."""
    return any(slot['kind'] == kind or kind in ABOVE[slot['kind']] or slot['kind'] in ABOVE[kind] for kind in covers)


def feature_tests(reader, scope, sources):
    """The tests the episode holds, in arrival order: ``[{'test', 'target', 'covers', 'rows'}]``, one per graded sheet of a
    source whose operand is a subject of ``scope`` and whose sheet has a reader. ``rows`` are the test's statements
    (``kind``, ``strand``, ``segments``, ``claims_start``, ``claims_end``, ``feature_ref``, ``bit``); a test that found
    nothing has no row and is still a test."""
    scope = reader.validate_scope(scope)
    tests = []
    for reference in sources:
        source = reader.get(reference)
        for entry in source_tool_grading_entries(reader, reference):
            schema = entry['grading']['sheet'].get('schema')
            if schema not in READERS:
                continue
            target = source['operand_refs'][0]
            if target not in scope['subject_refs']:
                continue
            sheet, covers, rows = READERS[schema](entry['grading'])
            tests.append({'test': sheet + '@' + reference, 'target': target, 'covers': covers, 'rows': rows,
                          'alternative': ALTERNATIVES[schema](entry['grading']) if schema in ALTERNATIVES else None})
    return tests


def held_readings(tests):
    """For the tests of one sequence: per dimension the value held (the one whose tests carry the most weighted support,
    the first made on a tie) with each value's support, and the names of the tests set aside (made under another value)."""
    support = {}
    for test in tests:
        if test['alternative'] is not None:
            dimension, value = test['alternative']
            total = sheet_weight(test['test']) * math.fsum(row['bit'] for row in test['rows'])
            support.setdefault(dimension, {})
            support[dimension][value] = support[dimension].get(value, 0.0) + total
    readings = {dimension: {'held': max(values, key=lambda value: values[value]), 'support': values}
                for dimension, values in support.items()}
    aside = [test['test'] for test in tests if test['alternative'] is not None
             and readings[test['alternative'][0]]['held'] != test['alternative'][1]]
    return readings, aside


def _order(slots, score):
    """The slot numbers, the highest score first; on a tie the slot of the finer type (the type with more types above
    it), then the one called first."""
    return sorted(score, key=lambda item: (-score[item], -len(ABOVE[slots[item]['kind']]), item))


def lead_rivals(slots, score, covers=None):
    """``(leader, rival)`` among the listed slots (those a test with ``covers`` can measure, or all with ``None``): the
    highest score and the highest score among its rivals; ``None`` when there are not two."""
    listed = [item for item in _order(slots, score) if covers is None or measurable(slots[item], covers)]
    if not listed:
        return None
    against = [item for item in listed[1:] if rivals(slots[listed[0]], slots[item])]
    return (listed[0], against[0]) if against else None


def _statements(tests):
    """Every statement the tests made with support, in arrival order (those of one test: the outer types first, then by
    position and strand), each with the place of its test among the tests (``test``)."""
    return [{'test': place, **row}
            for place, test in enumerate(tests)
            for row in sorted(test['rows'], key=lambda item: (len(ABOVE[item['kind']]), positions(item), item['strand']))
            if row['bit'] > 0]


def _groups(calls):
    """The feature calls gathered into slots: two calls of one slot are in one group, and so are two calls joined by a
    chain of such pairs. The groups depend on which calls there are and not on the order they came in. Each group is a list
    of places in ``calls``; the groups are in the order of their first call."""
    leader = list(range(len(calls)))

    def find(place):
        while leader[place] != place:
            leader[place] = leader[leader[place]]
            place = leader[place]
        return place
    for place, call in enumerate(calls):
        for earlier in range(place):
            if same_slot(call, calls[earlier]):
                first, second = sorted((find(place), find(earlier)))
                leader[second] = first
    groups = {}
    for place in range(len(calls)):
        groups.setdefault(find(place), []).append(place)
    return [groups[first] for first in sorted(groups)]


def _slot(members, weights):
    """The slot a group of feature calls is: its kind, its strand (the strand its calls name; ``.`` when none does), its
    versions (every position called for it, each with the weighted support of the calls that stated exactly it, in the
    order they were first called), its positions (``segments``: those of the best supported version, the earliest on a
    tie), the feature records that state it and the place of the first test that called it."""
    versions, refs = [], []
    for call in members:
        support = weights[call['test']] * call['bit']
        for version in versions:
            if positions(version) == positions(call):
                version['support'] += support
                break
        else:
            versions.append({'segments': [dict(segment) for segment in call['segments']], 'support': support})
        if call['feature_ref'] not in refs:
            refs.append(call['feature_ref'])
    best = max(versions, key=lambda version: version['support'])
    return {'kind': members[0]['kind'],
            'strand': next((call['strand'] for call in members if call['strand'] != '.'), '.'),
            'segments': [dict(segment) for segment in best['segments']], 'versions': versions, 'feature_refs': refs,
            'first_test': min(call['test'] for call in members)}


def _waiting_row(claim, support):
    return {'kind': claim['kind'], 'strand': claim['strand'], 'segments': [dict(segment) for segment in claim['segments']],
            'start': low(claim), 'end': high(claim), 'claims_start': claim['claims_start'],
            'claims_end': claim['claims_end'], 'support': support, 'feature_refs': [claim['feature_ref']]}


def target_table(tests):
    """The arithmetic of one sequence's tests (``feature_tests`` rows of that sequence, in arrival order).

    What there is is settled first, from all the statements held and whatever their order: the slots (``_groups``,
    ``_slot``, numbered in the order of their first call), which claims sit in which slots (``sits_in``; a claim can sit in
    several) and which claims wait. The credit is then counted by going through the tests in the order they came (the
    module's description). So the slots, their positions and scores and the waiting claims depend only on what is held;
    only who earned what depends on the order.

    Returns ``slots`` (per number its kind, strand, positions, versions, feature records and the number of claims in it),
    ``score``, ``sheets`` (per slot, per sheet, its summed weighted bits), ``waiting`` (the claims no slot includes, the
    same statement held twice as one row, the best supported first), ``entries`` (per slot its entry credit and the test
    that called it), ``claim_credits`` (per test what its claims earned, whether they wait or sit in a slot),
    ``differentials`` (per test at most one: the pair, the two moves, the difference), ``test_credits`` and ``credit``."""
    names = [test['test'] for test in tests]
    if len(set(names)) != len(names):
        raise ValueError('feature_test_held_twice:' + next(name for name in names if names.count(name) > 1))
    # tests made under a reading of the whole sequence that is not the one held state nothing here
    readings, aside = held_readings(tests)
    tests = [{**test, 'rows': []} if test['test'] in aside else test for test in tests]
    weights = [sheet_weight(name) for name in names]
    statements = _statements(tests)
    calls = [row for row in statements if row['claims_start'] and row['claims_end']]
    claims = [row for row in statements if not (row['claims_start'] and row['claims_end'])]
    members = dict(enumerate(_groups(calls)))
    slots = {number: _slot([calls[place] for place in group], weights) for number, group in members.items()}
    homes = [[number for number, slot in slots.items() if sits_in(claim, slot)] for claim in claims]
    # per slot, per test: the bits of its own calls and of the claims in it
    bits = {number: {} for number in slots}
    for number, group in members.items():
        for place in group:
            bits[number][calls[place]['test']] = bits[number].get(calls[place]['test'], 0.0) + calls[place]['bit']
    for claim, found in zip(claims, homes):
        for number in found:
            bits[number][claim['test']] = bits[number].get(claim['test'], 0.0) + claim['bit']
    for number, slot in slots.items():
        slot['claim_count'] = sum(number in found for found in homes)
    # the slots each slot is within: the support at them is its support too
    around = {number: [other for other, outer in slots.items() if other != number and within(slot, outer)]
              for number, slot in slots.items()}

    def move(number, place):
        """What the test at ``place`` adds to a slot: the weight times its bits at the slot and at every slot the slot
        is within."""
        return weights[place] * math.fsum(bits[item].get(place, 0.0) for item in (number, *around[number]))
    listed, score, sheets, entries, differentials, claim_credits, test_credits = {}, {}, {}, {}, [], {}, {}
    # per claim (its place in ``claims``): what it earned, not yet taken off, and the slots it sits in that were not yet
    # listed when it was paid (the entry of one of them, or of a slot within one, counts it in its score)
    paid = {}
    seen = []                     # the claims of the tests gone through, for "the first claim of its type and reading"
    for place, test in enumerate(tests):
        sheet, credit = sheet_of(test['test']), 0.0
        pair = lead_rivals(listed, score, test['covers'])
        if pair is not None:
            moves = [move(item, place) for item in pair]
            differentials.append({'test': test['test'], 'pair': list(pair), 'moves': moves,
                                  'difference': abs(moves[0] - moves[1])})
            credit += abs(moves[0] - moves[1])
        for item in listed:
            change = move(item, place)
            if change:
                score[item] += change
                sheets[item][sheet] = sheets[item].get(sheet, 0.0) + change
        # the claims of this test, whether they wait or sit in a slot called so far: each earns when it is the first
        # claim of its type and reading on its letters, the strongest first
        earned_by_claims = 0.0
        here = sorted((index for index, claim in enumerate(claims) if claim['test'] == place),
                      key=lambda index: (-claims[index]['bit'], positions(claims[index]), claims[index]['strand']))
        for index in here:
            if not any(same_reading(claims[index], other) for other in seen):
                paid[index] = (weights[place] * claims[index]['bit'],
                               {number for number in homes[index] if number not in listed})
                earned_by_claims += paid[index][0]
            seen.append(claims[index])
        claim_credits[test['test']] = earned_by_claims
        credit += earned_by_claims
        # the slots this test is the first to call, those of the outer types first, so that a slot within them earns
        # what it adds to them
        for number in sorted((number for number, slot in slots.items() if slot['first_test'] == place),
                             key=lambda number: (len(ABOVE[slots[number]['kind']]), number)):
            above = [other for other in listed if other in around[number]]
            below = [other for other in listed if number in around[other]]
            own = {}
            for earlier in range(place + 1):
                change = move(number, earlier)
                if change:
                    own[sheet_of(names[earlier])] = own.get(sheet_of(names[earlier]), 0.0) + change
            base = max((score[other] for other in above), default=0.0)
            listed[number], score[number], sheets[number] = slots[number], math.fsum(own.values()), own
            # what the claims counted in its score earned is not paid again: the claims that sit in it, and those that
            # sit in a slot it is within (their bits are in its score too), of the slots not yet listed when they were
            # paid (a claim paid in a slot listed then is not taken off again here: this slot's base is at least the
            # score of that slot, which holds it)
            counted_in = {number, *around[number]}
            taken = [index for index, (_, awaited) in paid.items() if counted_in.intersection(awaited)]
            already = math.fsum(paid.pop(index)[0] for index in taken)
            earned = 0.0 if (below and not above) else max(0.0, score[number] - base - already)
            entries[number] = {'test': test['test'], 'credit': earned}
            credit += earned
        test_credits[test['test']] = credit
    waiting = {}
    for claim, found in zip(claims, homes):
        if found:
            continue
        key = (claim['kind'], claim['strand'], positions(claim), claim['claims_start'], claim['claims_end'])
        support = weights[claim['test']] * claim['bit']
        if key in waiting:
            waiting[key]['support'] += support
            if claim['feature_ref'] not in waiting[key]['feature_refs']:
                waiting[key]['feature_refs'].append(claim['feature_ref'])
        else:
            waiting[key] = _waiting_row(claim, support)
    return {'slots': listed, 'score': score, 'sheets': sheets,
            'waiting': sorted(waiting.values(), key=lambda row: (-row['support'], row['start'], row['end'], row['kind'],
                                                                  row['strand'])),
            'entries': entries, 'claim_credits': claim_credits, 'differentials': differentials,
            'readings': readings, 'set_aside': aside,
            'test_credits': test_credits, 'credit': math.fsum(test_credits.values())}


def _outer(segments):
    return {'start': min(segment['start'] for segment in segments), 'end': max(segment['end'] for segment in segments)}


def feature_table(reader, scope, sources):
    """The sheet of the scope: per sequence its table (``target_table``) with the slot rows in order (the highest score
    first: ``kind``, ``strand``, ``segments``, ``start`` and ``end`` (the outer positions), ``versions`` (every position
    called for the slot, each with its outer positions and support), ``claim_count`` (the claims that sit in it),
    ``feature_refs``, ``score``, ``sheets`` and ``rivals``: for each row that is its rival the place of that row in the
    order and the facts of the letters the two share), ``rival_rank`` (the place of the leading rival of the first row,
    ``None`` when it has none), the waiting claims and the tests; and the ``credit`` of the scope (the sum over
    sequences)."""
    tests = feature_tests(reader, scope, sources)
    targets = {}
    for target in reader.validate_scope(scope)['subject_refs']:
        table = target_table([test for test in tests if test['target'] == target])
        order = _order(table['slots'], table['score'])
        pair = lead_rivals(table['slots'], table['score'])
        rows = []
        for item in order:
            slot = table['slots'][item]
            rows.append({
                'kind': slot['kind'], 'strand': slot['strand'], 'segments': slot['segments'], **_outer(slot['segments']),
                'versions': [{**version, **_outer(version['segments'])} for version in slot['versions']],
                'claim_count': slot['claim_count'], 'feature_refs': slot['feature_refs'],
                'score': table['score'][item], 'sheets': table['sheets'][item],
                'rivals': [{'rank': rank, **overlap_facts(slot, table['slots'][other])}
                           for rank, other in enumerate(order) if rivals(slot, table['slots'][other])]})
        targets[target] = {**table, 'rows': rows, 'rival_rank': None if pair is None else order.index(pair[1]),
                           'tests': [test['test'] for test in tests if test['target'] == target]}
    return {'targets': targets, 'credit': math.fsum(table['credit'] for table in targets.values())}


__all__ = ['ABOVE', 'ALTERNATIVES', 'COMPETING', 'KINDS', 'READERS', 'RIVAL_LETTERS', 'RNA_SHARE', 'RNA_UNITS', 'SAME_SHARE',
           'SHEET_WEIGHT', 'STRANDS',
           'feature_table', 'feature_tests', 'held_readings', 'held_sources', 'high', 'inside', 'lead_rivals', 'letters', 'low',
           'measurable', 'nested', 'overlap_facts', 'positions', 'rivals', 'same_frame', 'same_reading', 'same_slot',
           'shared_letters', 'sheet_family', 'sheet_of', 'sheet_weight', 'sits_in', 'strands_agree', 'target_table',
           'within']
