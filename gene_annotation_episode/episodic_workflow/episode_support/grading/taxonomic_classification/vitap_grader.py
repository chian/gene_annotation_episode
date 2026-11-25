"""The grader of one VITAP assignment of one sequence: the facts of its two native tables, with its taxon names turned into
taxon ids.

VITAP aligns the sequence's predicted proteins to the proteins of the viruses of its database and scores each lineage of the
official virus taxonomy from the hits. ``best_determined_lineages.tsv`` holds, for a sequence it could assign, the lineage it
settled on (eight names from species up to realm, ``-`` where it settled on none, a bracketed placeholder where the taxonomy
has no name at that rank), its ``lineage_score`` and a ``Confidence_level``. ``all_lineages.tsv`` holds every lineage it
considered with its score, the same lineage cut at different depths included.

The sheet states, for the best lineage and for each lineage considered: the names as written (the finest first), the score,
the finest name that resolves in the prepared NCBI taxonomy with its taxon row, and the finer names that did not resolve with
why. VITAP's database is of an earlier release of the virus taxonomy than the prepared NCBI taxonomy, so a name can have
been replaced since: NCBI keeps earlier names as synonyms, and a name it does not keep is reported unresolved, never guessed.
No threshold and no judgement is here; the confidence level is recorded as VITAP wrote it."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.taxonomic_classification.ncbi_taxonomy import (
    RESOLVED, identity, resolve, taxon_row)

SHEET = 'vitap_assignment_sheet'
RANKS = ('species', 'genus', 'family', 'order', 'class', 'phylum', 'kingdom', 'realm')
CONFIDENCE_LEVELS = ('High-confidence', 'Medium-confidence', 'Low-confidence')


def _rows(text, required):
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError('vitap_table_empty')
    header = lines[0].split('\t')
    if any(name not in header for name in required):
        raise ValueError('vitap_table_header_unexpected')
    return [dict(zip(header, line.split('\t'), strict=True)) for line in lines[1:]]


def _lineage(text, score, taxonomy):
    names = text.split(';')
    if len(names) != len(RANKS):
        raise ValueError('vitap_lineage_has_not_eight_ranks')
    stated = [{'rank': rank, 'name': name} for rank, name in zip(RANKS, names, strict=True)
              if name != '-' and not name.startswith('[')]
    taxon, unresolved = None, []
    for item in stated:
        found, state = resolve(taxonomy, item['name'])
        if state == RESOLVED:
            taxon = taxon_row(taxonomy, found)
            break
        unresolved.append({**item, 'state': state})
    return {'names': names, 'lineage_score': float(score), 'taxon': taxon, 'unresolved_names': unresolved}


def grade_vitap_assignment(*, best_text, all_text, sequence_name, taxonomy):
    """``{'sheet': ...}`` of the sequence ``sequence_name``. ``best_text`` and ``all_text`` may be ``None`` (VITAP wrote no
    such table) or hold no row of the sequence: VITAP assigned it nothing."""
    best = [] if best_text is None else [
        row for row in _rows(best_text, ('Genome_ID', 'lineage', 'lineage_score', 'Confidence_level'))
        if row['Genome_ID'] == sequence_name]
    if len(best) > 1:
        raise ValueError('vitap_best_lineages_has_more_than_one_row_of_the_sequence')
    if best and best[0]['Confidence_level'] not in CONFIDENCE_LEVELS:
        raise ValueError('vitap_confidence_level_unexpected:' + best[0]['Confidence_level'])
    considered = [] if all_text is None else [
        row for row in _rows(all_text, ('Genome_ID', 'lineage', 'lineage_score')) if row['Genome_ID'] == sequence_name]
    return {'sheet': {'schema': SHEET, 'sequence': {'name': sequence_name},
                      'best': None if not best else {**_lineage(best[0]['lineage'], best[0]['lineage_score'], taxonomy),
                                                     'confidence_level': best[0]['Confidence_level']},
                      'lineages': [_lineage(row['lineage'], row['lineage_score'], taxonomy) for row in considered],
                      'taxonomy': identity(taxonomy)}}


__all__ = ['CONFIDENCE_LEVELS', 'RANKS', 'SHEET', 'grade_vitap_assignment']
