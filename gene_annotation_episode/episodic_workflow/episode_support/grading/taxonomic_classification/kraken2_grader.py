"""The grader of one Kraken 2 classification of one sequence: the facts of the native output, per taxon.

Kraken 2 looks up every k-mer of the sequence (through its minimizer) in the index and reads the taxon the index holds for
it: the lowest common ancestor of the genomes that contain it. Its per-sequence output line holds, tab-separated: ``C`` or
``U`` (classified or not), the sequence name, the taxon the sequence is assigned, the sequence length and the k-mer
mapping, a list ``<taxon id>:<count>`` in the order of the sequence (``0`` no taxon in the index, ``A`` a k-mer with an
ambiguous letter; ``|:|`` separates the mates of a pair and does not occur for one sequence).

The sheet states, and nothing more: the sequence (name, length, the taxon assigned), the k-mer counts (all, with no taxon,
ambiguous, with a taxon) and one row for every taxon that has a k-mer of its own or below it: its id, name, rank code
(Kraken 2's: ``D`` domain, ``F`` family, ``G`` genus, ``S`` species, a digit for a level between two ranks), its parent,
its lineage from the root (ids, the root left out), the k-mers mapped to the taxon itself (``kmers_direct``) and to the
taxon or any taxon below it (``kmers_clade``). A k-mer that the index maps to a family counts for the family and for every
taxon above it; it says nothing of which genus of the family, so it is in no genus row.

No threshold and no judgement is here: how much a count is worth is the scoring sheet's
(``taxon_candidates``). The taxonomy is the index's own (``ktaxonomy.tsv`` of the index folder: id, parent, rank code,
depth, name, separated by ``|`` between tabs), so every id of the output is found in it; an id that is not raises."""

SHEET = 'kraken2_classification_sheet'
ROOT = 1
UNCLASSIFIED, AMBIGUOUS = '0', 'A'


def read_taxonomy(text):
    """``{taxon id: {'parent', 'rank_code', 'name'}}`` of the index's ``ktaxonomy.tsv`` text."""
    nodes = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        fields = [field.strip() for field in line.split('|')]
        if len(fields) != 5:
            raise ValueError('kraken2_taxonomy_line_has_not_five_fields')
        nodes[int(fields[0])] = {'parent': int(fields[1]), 'rank_code': fields[2], 'name': fields[4]}
    if ROOT not in nodes:
        raise ValueError('kraken2_taxonomy_has_no_root')
    return nodes


def lineage(nodes, taxon):
    """The ids from below the root down to ``taxon`` (the root left out; empty for the root)."""
    if taxon not in nodes:
        raise ValueError('kraken2_taxon_not_in_the_index_taxonomy:' + str(taxon))
    path = []
    while taxon != ROOT:
        path.append(taxon)
        taxon = nodes[taxon]['parent']
        if taxon not in nodes or len(path) > len(nodes):
            raise ValueError('kraken2_taxonomy_parent_chain_broken')
    return path[::-1]


def grade_kraken2_classification(*, output_text, taxonomy_text, sequence_name, sequence_length):
    """``{'sheet': ...}`` of one sequence's output line (the module's description states the sheet). ``output_text`` must
    hold exactly one line, of the sequence named ``sequence_name`` with length ``sequence_length``."""
    lines = [line for line in output_text.splitlines() if line.strip()]
    if len(lines) != 1:
        raise ValueError('kraken2_output_has_not_one_sequence_line')
    fields = lines[0].split('\t')
    if len(fields) != 5 or fields[0] not in ('C', 'U'):
        raise ValueError('kraken2_output_line_malformed')
    if fields[1] != sequence_name or int(fields[3]) != sequence_length:
        raise ValueError('kraken2_output_of_another_sequence')
    nodes = read_taxonomy(taxonomy_text)
    direct, counts = {}, {'all': 0, 'without_taxon': 0, 'ambiguous': 0}
    for item in fields[4].split():
        key, _, number = item.partition(':')
        if key == '|' or not number.isdigit():
            raise ValueError('kraken2_kmer_mapping_item_malformed')
        number = int(number)
        counts['all'] += number
        if key == AMBIGUOUS:
            counts['ambiguous'] += number
        elif key == UNCLASSIFIED:
            counts['without_taxon'] += number
        else:
            direct[int(key)] = direct.get(int(key), 0) + number
    counts['with_taxon'] = counts['all'] - counts['without_taxon'] - counts['ambiguous']
    clade = {}
    for taxon, number in direct.items():
        for member in lineage(nodes, taxon):
            clade[member] = clade.get(member, 0) + number
    rows = [{'taxon_id': taxon, 'name': nodes[taxon]['name'], 'rank_code': nodes[taxon]['rank_code'],
             'parent_taxon_id': nodes[taxon]['parent'], 'lineage_taxon_ids': lineage(nodes, taxon),
             'kmers_direct': direct.get(taxon, 0), 'kmers_clade': number}
            for taxon, number in clade.items()]
    rows.sort(key=lambda row: (len(row['lineage_taxon_ids']), -row['kmers_clade'], row['taxon_id']))
    assigned = int(fields[2])
    if assigned and assigned not in nodes:
        raise ValueError('kraken2_taxon_not_in_the_index_taxonomy:' + str(assigned))
    return {'sheet': {'schema': SHEET, 'sequence': {'name': sequence_name, 'length': sequence_length, 'classified': fields[0] == 'C',
                                   'assigned_taxon_id': assigned or None},
                      'kmers': counts, 'taxa': rows}}


__all__ = ['SHEET', 'grade_kraken2_classification', 'lineage', 'read_taxonomy']
