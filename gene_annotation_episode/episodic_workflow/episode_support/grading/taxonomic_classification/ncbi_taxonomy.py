"""A lookup of taxon names in a prepared part of the NCBI taxonomy: a name to its taxon id, and a taxon to its rank code and
lineage. It turns what a tool reports as names (geNomad, VITAP) into the same ids and lineages the k-mer indexes use, so
every sheet's taxa meet on one taxonomy.

The prepared taxonomy is named by a manifest (``name``, ``version``, what it ``holds``, and its two files): ``nodes.tsv``
(taxon id, parent, NCBI rank, rank code as Kraken 2 writes it, scientific name) and ``names.tsv`` (name, name class, taxon
id; the classes kept are the scientific name, synonyms and equivalent names). A name resolves when it is the scientific name
of exactly one taxon, or, failing that, a synonym or equivalent name of exactly one. A name that is not held is ``unknown``;
a name of more than one taxon is ``ambiguous``. Neither is guessed."""
import json
from pathlib import Path

ROOT = 1
RESOLVED, UNKNOWN, AMBIGUOUS = 'resolved', 'unknown', 'ambiguous'


def load_taxonomy(manifest_path):
    """``{'manifest', 'nodes': {taxon id: {'parent', 'rank', 'rank_code', 'name'}}, 'names': {name: {class: [taxon ids]}}}``."""
    manifest = json.loads(Path(manifest_path).read_text())
    nodes, names = {}, {}
    with Path(manifest['files']['nodes.tsv']['path']).open() as stream:
        for line in stream:
            taxon, parent, rank, code, name = line.rstrip('\n').split('\t')
            nodes[int(taxon)] = {'parent': int(parent), 'rank': rank, 'rank_code': code, 'name': name}
    with Path(manifest['files']['names.tsv']['path']).open() as stream:
        for line in stream:
            name, kind, taxon = line.rstrip('\n').split('\t')
            names.setdefault(name, {}).setdefault(kind, []).append(int(taxon))
    return {'manifest': manifest, 'nodes': nodes, 'names': names}


def resolve(taxonomy, name):
    """``(taxon id or None, RESOLVED | UNKNOWN | AMBIGUOUS)`` of a name."""
    held = taxonomy['names'].get(name)
    if held is None:
        return None, UNKNOWN
    for found in (held.get('scientific name', []),
                  sorted({taxon for kind in ('synonym', 'equivalent name') for taxon in held.get(kind, [])})):
        if len(found) == 1:
            return found[0], RESOLVED
        if len(found) > 1:
            return None, AMBIGUOUS
    return None, UNKNOWN


def lineage(taxonomy, taxon):
    """The ids from below the root down to ``taxon`` (the root left out)."""
    nodes, path = taxonomy['nodes'], []
    while taxon != ROOT:
        if taxon not in nodes or len(path) > 200:
            raise ValueError('taxon_not_in_the_prepared_taxonomy:' + str(taxon))
        path.append(taxon)
        taxon = nodes[taxon]['parent']
    return path[::-1]


def taxon_row(taxonomy, taxon):
    """The row of a taxon as the classification sheets write one."""
    node = taxonomy['nodes'][taxon]
    return {'taxon_id': taxon, 'name': node['name'], 'rank_code': node['rank_code'], 'parent_taxon_id': node['parent'],
            'lineage_taxon_ids': lineage(taxonomy, taxon)}


def identity(taxonomy):
    """The prepared taxonomy's identity as a sheet records it."""
    manifest = taxonomy['manifest']
    return {'name': manifest['name'], 'version': manifest['version']}


__all__ = ['AMBIGUOUS', 'RESOLVED', 'UNKNOWN', 'identity', 'lineage', 'load_taxonomy', 'resolve', 'taxon_row']
