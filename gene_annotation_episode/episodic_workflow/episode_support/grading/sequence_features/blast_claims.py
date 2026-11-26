"""The converter of one graded BLAST search of a nucleotide sequence into claims about its features: the subscoring sheet
of the search (``blast_feature_claim_sheet``) and the rows the sheet of feature calls reads from it.

The grader (``blast_database_sheet``, the same for every BLAST program) states the facts of every hit: its rank, its bit
score and E-value, where its best alignment lies on the searched sequence and on the known sequence, and what the database says of it
(its product, its family ids, its taxon, its own feature type). A local alignment finds a part of a feature: it says
that its letters lie inside a feature, on which strand and, for a search against proteins, in which frame; it claims an
end only where it reaches the first or the last position of the known sequence.

How the hits become claims is how the owner reads a hit list (2026-11-25): "(1) reasonable score/E-value; (2) rank of
first different hit; i.e., sameness of hits down the list give me a sense that there is no better hit in the database and
no controversey; (3) taxa sensibleness, i.e, top hits are kind of from same part of tree and then more distant as rank goes
down ... after this, i'm usually fine with the top hit and positions depending on how firm the other items are. from that
I grade claims." And: "Different means different annotation call (when a positive annotation call is made, not counting
unknowns or unlabeled annotations unless they are conserved hypotheticals or a whole lot of them in a row down the ranking
...). Your thought on different frame is also key. They all have to be in the same frame." A call is what an annotation
indicates, not its wording ("names can be fluffy. more like annotating or indicating something similar"). "the other
different calls can also support a second claim from the same blast search ... this is how i block them together".

So, going down the hits in the order of their rank:

* A PLACE is the hits that say the same kind of thing of letters they share with its first hit: one type, one strand, one
  frame (``feature_candidates.same_reading``). The many hits of a place are one statement, not many: variants of one
  thing in the database.
* A hit makes a CALL when the database says something positive of it. Which hits make the same call is a judgement of
  what their annotations indicate, not of their wording, and it is made in this head (the owner, 2026-11-25: "i think you
  need to resolve via names in this head and not wait until root"). Hits of one protein family of the database
  (``pgfam_id``) carry one label; a hit with no family id carries its product's wording as its label (``place_labels``).
  The step that keeps the claims has the labels of each place sorted by meaning (a model is shown the annotations and
  answers with a group number for each label, nothing else) and gives the result here (``groups``). In the first real
  search of a piece of a virus, whose hits had no family id, eleven hits of one protein under six wordings ("RNA-dependent
  RNA polymerase VP1", "RdRp", "VP1", ...) had come out as ten calls when wordings were compared as text. A hit with no
  product, or with a label of ignorance (``uncharacterized_labels``), makes no call and is passed over: it neither agrees
  nor disagrees. "Conserved hypothetical protein" is a call here, by the owner's rule above.
* A BLOCK is the hits of a place that make one call. Each block is a claim: its positions, strand and ends are those of
  its top hit (nothing is made up from the other hits), and the rest says how firm it is:

  - ``bit_score``, ``evalue``: of the top hit;
  - ``hits``: the hits of the block;
  - ``run_before_different_call``: the hits of the block before the first hit of the place that makes another call (the
    hits that make no call passed over); ``different_call_met`` says whether there is such a hit;
  - ``run_before_different_frame``: the hits of the place before the first hit that shares letters with the top hit on
    the other strand or in another frame; ``different_frame_met`` says whether there is such a hit;
  - ``unlabeled_run``: the longest row of hits of the place, one after the other, that make no call (the owner: "a whole
    lot of them in a row" suggests something else, or an unknown family; counted here, judged by whoever reads it);
  - ``taxon_count``: the taxa of the block's hits. Whether the top hits are of one part of the tree and get more distant
    down the list needs the lineage of each hit, which the search does not ask the database for yet.

  The hits of a place that make no call are its own block when the place has no other: the claim that a feature of that
  type is there, read that way, needs no name.

What the feature calls take from a claim is its type, strand, positions and claimed ends, and one value (``bit``): the
claims of one place all say the same of the feature's type and reading, so the place's value is one, carried by its first
block: ``run / (run + 1)`` with ``run = run_before_different_frame``: 1 hit 0.5, 3 hits 0.75, 9 hits 0.9. A starting rule
of 2026-11-25 with no run behind it. The other fields are kept for the grading of the claims as they are refined, and for
the naming of the feature.

The type of a claim: a hit of a database of proteins is of a coding sequence; a hit of a database of nucleotide features
is of its own feature type as the database gives it, mapped to our types (``database_feature_types``), and of no stated
type (``sequence_region``) when the database's value has no mapping yet.

WORDS. A run has one query: the sequence the root was given (the owner, 2026-11-25: "There is only one query for this
whole run from root. that is the input DNA sequence"). That word is kept for it. What a search is run on is called here
the SEARCHED SEQUENCE; the grader's sheet calls it ``query`` after the program's own word, and that is only the name of a
field. A claim is about a sequence, in that sequence's own positions. The searched sequence can be that sequence itself,
in whatever letters, or a sequence derived from it. A search of a translation is as valid as a search of the nucleotides
read in six frames (the owner: "either you have a translated version of the dna in some frame or you do not. if you do
and have a protein alignment, as long as you can map it to positions and frame and strand, then you are fine ... this is
valid b/c blastx is valid for this"): the positions of each alignment on the derived sequence are carried back by its own
mapping (``searched_mapping``: the ``mapping`` of the product record, ``sequence_mapping.map_interval``), which gives the
positions and the strand, and so the frame. Nothing here decides which sequence may be searched with
which program: that is the tool's own knowledge (the owner: "certain tools only do certain things, so you know, keep it
general and modular").

No I/O: this module reads a grading and returns values."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features.database_feature_types import (
    bvbrc_feature_kind)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features.feature_candidates import (
    READERS, SHEET_WEIGHT, same_reading, shared_letters)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features.feature_types import (
    CODING, KINDS)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.blast_search import (
    PROGRAM_UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.grading.uncharacterized_labels import (
    is_uncharacterized_label)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_operations.sequence_mapping import (
    map_interval)

SHEET = 'blast_feature_claim_sheet'
GRADED_SHEET = 'blast_database_sheet'
UNTYPED = 'sequence_region'
# A label of ignorance that is a call here (the owner's rule quoted above).
CONSERVED_UNKNOWN = 'conserved hypothetical protein'
NO_CALL = ''
# The family of technique of a search, by the letters of the database it searches.
FAMILY = {'aa': 'protein_similarity', 'nt': 'nucleotide_similarity'}


def _label(function):
    """What stands for a hit's annotation when hits are sorted into calls: its protein family of the database when it has
    one, else its product's wording (case and spacing apart); ``None`` when the database says nothing positive of it (no
    annotation, or a label of ignorance other than a conserved hypothetical)."""
    if function is None:
        return None
    name = ' '.join(function['function'].casefold().split())
    if is_uncharacterized_label(name) and name != CONSERVED_UNKNOWN:
        return None
    return function['bvbrc_feature'].get('pgfam_id') or name


def place_labels(grading, searched_mapping=None):
    """What has to be sorted into calls, per place of a graded search (in the order of the places): for each label of the
    place's hits (a family id or a wording, ``_label``) the annotations the database gives the hits that carry it, as
    written. Two hits of one family are one label; which labels indicate the same thing is a judgement of meaning, made
    by whoever calls ``blast_claim_sheet`` and given to it as ``groups``."""
    found = []
    for place in _places(hit_statements(grading, searched_mapping)):
        labels = {}
        for hit in place:
            if hit['label'] is not None and hit['annotation'] not in labels.setdefault(hit['label'], []):
                labels[hit['label']].append(hit['annotation'])
        found.append([{'label': label, 'annotations': annotations} for label, annotations in labels.items()])
    return found


def _kind(function, reference_unit):
    """The type a hit is of (the module's description)."""
    if reference_unit == 'aa':
        return CODING
    if function is None or 'feature_type' not in function['bvbrc_feature']:
        return UNTYPED
    return bvbrc_feature_kind(function['bvbrc_feature']['feature_type']) or UNTYPED


def _on_the_subject(searched, reference, searched_mapping):
    """``(segments, strand, forward)`` of an alignment on the sequence the claims are about: the searched sequence
    itself, or, when the searched sequence was derived from it (``searched_mapping``: a translation, an extracted
    stretch), the sequence the mapping carries the alignment's span back to. ``searched`` and ``reference`` are the
    alignment's spans on the searched and on the known sequence. ``forward`` says whether the known sequence runs the way
    the positions rise: the alignment runs the known sequence along the searched one or against it, and a searched
    sequence derived from the minus strand turns that round. The strand is ``+`` or ``-`` by that on a sequence of
    nucleotides; a sequence of protein letters has none (``.``)."""
    along = searched['direction'] == reference['direction']
    if searched_mapping is None:
        return ([{'start': searched['interval'][0], 'end': searched['interval'][1]}],
                '.' if searched['unit'] != 'nt' else '+' if along else '-', along)
    path = map_interval(searched_mapping, searched['interval'][0], searched['interval'][1])
    forward = along if path[0]['strand'] == '+' else not along
    return (sorted(({'start': row['start'], 'end': row['end']} for row in path), key=lambda segment: segment['start']),
            '.' if path[0]['unit'] != 'nt' else '+' if forward else '-', forward)


def hit_statements(grading, searched_mapping=None):
    """What each hit of a graded search states, in the order of rank: its ``rank``, ``bit_score`` and ``evalue``, the
    type, strand and positions of its best alignment on the sequence the claims are about (``kind``, ``strand``,
    ``segments``), the ends it claims (``claims_start``: the alignment reaches the end of the known sequence that lies at
    the lowest position; ``claims_end``: at the highest), its ``call`` and its ``taxon_id`` (``None`` when the database
    gives none). ``searched_mapping`` is the mapping of the searched sequence when it was derived from that sequence.

    A hit whose best alignment the grader could give no positions for (``geometry_available`` false) states nothing of
    where anything lies and has no row. A hit that is of no stated type (an entry of a database of whole sequences, which
    is not a feature) states only that its letters match: its strand is ``.`` and it claims no end, since the direction
    and the ends of such an entry are not those of a feature."""
    rows = []
    for hit in sorted(grading['sheet']['hits'], key=lambda item: item['hit_index']):
        component = hit['hsp_components'][0]
        if not component['geometry_available']:
            continue
        spans = component['endpoint_spans']
        searched, reference = spans['query'], spans['reference']     # ``query``: the grader's field name
        segments, strand, forward = _on_the_subject(searched, reference, searched_mapping)
        functions = hit['associations'][0]['functions']
        function = functions[0] if functions else None
        kind = _kind(function, reference['unit'])
        typed = kind != UNTYPED
        at_first = reference['interval'][0] == 0
        at_last = reference['interval'][1] == reference['operand_length']
        rows.append({
            'rank': hit['hit_index'], 'bit_score': hit['measurements']['maximum_bit_score'],
            'evalue': hit['measurements']['minimum_evalue'], 'kind': kind,
            'strand': strand if typed else '.', 'segments': segments,
            'claims_start': typed and (at_first if forward else at_last),
            'claims_end': typed and (at_last if forward else at_first),
            'label': _label(function), 'annotation': None if function is None else function['function'],
            'taxon_id': None if function is None else function['bvbrc_feature'].get('taxon_id')})
    return rows


def _places(hits):
    """The hits gathered into places, in the order of rank: a hit joins the first place whose first hit it has the same
    reading as; a hit that has the reading of no place opens one."""
    places = []
    for hit in hits:
        for place in places:
            if same_reading(place[0], hit):
                place.append(hit)
                break
        else:
            places.append([hit])
    return places


def _longest_run_without_call(place):
    longest = current = 0
    for hit in place:
        current = current + 1 if hit['call'] == NO_CALL else 0
        longest = max(longest, current)
    return longest


def _claims_of_place(place, hits):
    """The claims of one place, one per block, in the order of the rank of their top hit."""
    top = place[0]
    # the first hit, of any place, that shares letters with this place's top hit and does not have its reading
    crossing = [hit['rank'] for hit in hits if hit['rank'] > top['rank'] and shared_letters(top, hit) > 0
                and not same_reading(top, hit)]
    before_frame = [hit for hit in place if not crossing or hit['rank'] < crossing[0]]
    calls = [call for call in dict.fromkeys(hit['call'] for hit in place) if call != NO_CALL] or [NO_CALL]
    unlabeled = _longest_run_without_call(place)
    claims = []
    for call in calls:
        block = [hit for hit in place if hit['call'] == call]
        first = block[0]
        other = [hit['rank'] for hit in place if hit['rank'] > first['rank'] and hit['call'] not in (call, NO_CALL)]
        run = [hit for hit in block if not other or hit['rank'] < other[0]]
        claims.append({
            'rank': first['rank'], 'kind': first['kind'], 'strand': first['strand'],
            'segments': [dict(segment) for segment in first['segments']],
            'claims_start': first['claims_start'], 'claims_end': first['claims_end'],
            'bit_score': first['bit_score'], 'evalue': first['evalue'],
            # what the database says of the block's hits, as written, and their families: for the naming of the feature
            'annotations': list(dict.fromkeys(hit['annotation'] for hit in block if hit['annotation'] is not None)),
            'family_ids': sorted({hit['label'] for hit in block if hit['label'] is not None and hit['label'].startswith('PGF_')}),
            'makes_call': call != NO_CALL, 'hits': len(block),
            'run_before_different_call': len(run), 'different_call_met': bool(other),
            'run_before_different_frame': len(before_frame), 'different_frame_met': bool(crossing),
            'unlabeled_run': unlabeled,
            'taxon_count': len({hit['taxon_id'] for hit in block if hit['taxon_id'] is not None}),
            'first_of_place': call == calls[0]})
    return claims


def blast_claim_sheet(grading, groups, searched_mapping=None):
    """The subscoring sheet of one graded search: ``{'schema', 'program', 'database', 'hit_count', 'claims'}`` with the
    claims of every place (the module's description), in the order of the rank of their top hit. ``groups`` says which
    labels of each place indicate the same thing: per place (in the order of ``place_labels``) ``{label: group number}``,
    one entry for every label of the place; labels with one number are one call, and the number 0 is for an annotation
    that states nothing of what the feature is (its hits make no call). ``searched_mapping`` is the mapping of the
    searched sequence when it was derived from the sequence the claims are about."""
    hits = hit_statements(grading, searched_mapping)
    search = grading['sheet']['normalized_result']['search']
    places = _places(hits)
    for place, grouping in zip(places, groups, strict=True):
        if set(grouping) != {hit['label'] for hit in place if hit['label'] is not None}:
            raise ValueError('blast_claims_groups_do_not_cover_the_labels_of_the_place')
        for hit in place:
            number = 0 if hit['label'] is None else grouping[hit['label']]
            hit['call'] = NO_CALL if number == 0 else 'call_' + str(number)
    claims = [claim for place in places for claim in _claims_of_place(place, hits)]
    return {'schema': SHEET, 'program': search['program'], 'database': search['request']['database'],
            'hit_count': len(hits), 'claims': sorted(claims, key=lambda claim: claim['rank'])}


def claim_bit(claim):
    """The value a claim carries into the feature calls (the module's description): the place's value, at its first
    block; nothing at the other blocks of the place, which say the same of the feature's type and reading."""
    if not claim['first_of_place']:
        return 0.0
    run = claim['run_before_different_frame']
    return run / (run + 1)


def read_claim_sheet(grading):
    """The reader of a kept claim sheet for the sheet of feature calls (``feature_candidates.READERS``): ``(sheet name,
    covers, rows)``. The sheet name starts with the family of technique: a search of a database of proteins is
    ``protein_similarity`` and can speak of coding sequences; a search of a database of nucleotide sequences is
    ``nucleotide_similarity`` and can speak of whatever types its entries are."""
    sheet = grading['sheet']
    unit = PROGRAM_UNITS[sheet['program']][1]
    return (FAMILY[unit] + ':' + sheet['program'] + ':' + sheet['database'], [CODING] if unit == 'aa' else list(KINDS),
            statement_rows(sheet, [claim['feature_ref'] for claim in sheet['claims']]))


def statement_rows(sheet, feature_refs):
    """The rows the sheet of feature calls reads (``feature_candidates.READERS``): one per claim of the claim sheet, with
    the feature record that states it (``feature_refs``: per claim, in the sheet's order)."""
    return [{'kind': claim['kind'], 'strand': claim['strand'], 'segments': claim['segments'],
             'claims_start': claim['claims_start'], 'claims_end': claim['claims_end'], 'feature_ref': feature_ref,
             'bit': claim_bit(claim)}
            for claim, feature_ref in zip(sheet['claims'], feature_refs)]


# Entered into the sheet of feature calls when this module is imported: the reader of the kept claim sheet, and the
# weight of the two families of technique a BLAST search belongs to. The value of a place is run / (run + 1), near 1 for
# a firm one, so the weight is 1. Starting values of 2026-11-25 with no run behind them.
READERS[SHEET] = read_claim_sheet
SHEET_WEIGHT.update({family: 1.0 for family in FAMILY.values()})

__all__ = ['FAMILY', 'GRADED_SHEET', 'SHEET', 'blast_claim_sheet', 'claim_bit', 'hit_statements', 'place_labels',
           'read_claim_sheet',
           'statement_rows']
