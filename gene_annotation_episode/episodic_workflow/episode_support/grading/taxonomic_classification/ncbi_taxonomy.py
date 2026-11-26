"""A lookup of taxon names in the prepared NCBI taxonomy: a name to its taxon id, and a taxon to its rank code and
lineage. It turns what a tool reports as names (geNomad, VITAP) into the same ids and lineages the k-mer indexes use, so
every sheet's taxa meet on one taxonomy.

The prepared taxonomy is named by a manifest (``name``, ``version``, what it ``holds``, and its two files): ``nodes.tsv``
(taxon id, parent, NCBI rank, rank code as Kraken 2 writes it, scientific name) and ``names.tsv`` (name, name class, taxon
id; the classes kept are the scientific name, synonyms and equivalent names). A name resolves when it is the scientific name
of exactly one taxon, or, failing that, a synonym or equivalent name of exactly one. A name that is not held is ``unknown``;
a name of more than one taxon is ``ambiguous``. Neither is guessed."""
import functools
import json
import mmap
from pathlib import Path

# The prepared taxonomy the scoring of candidate taxa holds: a fixed fact, not a property of a run. It sits in the
# repository's ``resources`` directory (data that is not in git; a pinned worktree links that directory).
PREPARED_MANIFEST = (Path(__file__).parents[5] / 'resources' / 'software' / 'ncbi-taxonomy-20261022'
                     / 'taxonomy.manifest.json')
ROOT = 1
RESOLVED, UNKNOWN, AMBIGUOUS = 'resolved', 'unknown', 'ambiguous'


def _first_line(data, below):
    """The offset of the first line of the sorted file ``data`` whose first field is not ``below`` the one sought."""
    low, high = 0, len(data)
    while low < high:
        start = data.rfind(b'\n', 0, (low + high) // 2) + 1
        if below(data[start:data.find(b'\t', start)]):
            low = data.find(b'\n', start) + 1
        else:
            high = start
    return low


class _Nodes:
    """``nodes.tsv`` read in place (it is sorted by taxon id): ``taxon in nodes`` and ``nodes[taxon]``, a taxon's
    ``{'parent', 'rank', 'rank_code', 'name'}``. A taxon is read from the file once."""

    def __init__(self, data):
        self._data, self._read = data, {}

    def _row(self, taxon):
        if taxon not in self._read:
            start = _first_line(self._data, lambda field: int(field) < taxon)
            fields = self._data[start:self._data.find(b'\n', start)].decode().split('\t')
            self._read[taxon] = None if fields[0] != str(taxon) else {
                'parent': int(fields[1]), 'rank': fields[2], 'rank_code': fields[3], 'name': fields[4]}
        return self._read[taxon]

    def __contains__(self, taxon):
        return self._row(taxon) is not None

    def __getitem__(self, taxon):
        row = self._row(taxon)
        if row is None:
            raise KeyError(taxon)
        return row


class _Names:
    """``names.tsv`` read in place (it is sorted by name): ``names.get(name)``, the name's ``{class: [taxon ids]}`` or
    ``None``."""

    def __init__(self, data):
        self._data = data

    def get(self, name):
        data, sought = self._data, name.encode()
        start, held = _first_line(data, lambda field: field < sought), {}
        while data[start:start + len(sought) + 1] == sought + b'\t':
            end = data.find(b'\n', start)
            _, kind, taxon = data[start:end].decode().split('\t')
            held.setdefault(kind, []).append(int(taxon))
            start = end + 1
        return held or None


def _in_place(path):
    with Path(path).open('rb') as stream:
        return mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ)


def load_taxonomy(manifest_path):
    """``{'manifest', 'nodes', 'names'}``: ``nodes[taxon]`` is ``{'parent', 'rank', 'rank_code', 'name'}`` and
    ``names.get(name)`` is ``{class: [taxon ids]}``. The two files are read in place, not held in memory: the whole
    taxonomy has three million taxa."""
    manifest = json.loads(Path(manifest_path).read_text())
    return {'manifest': manifest, 'nodes': _Nodes(_in_place(manifest['files']['nodes.tsv']['path'])),
            'names': _Names(_in_place(manifest['files']['names.tsv']['path']))}


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


@functools.lru_cache(maxsize=None)
def prepared_taxonomy():
    """The prepared taxonomy (``PREPARED_MANIFEST``), loaded once."""
    return load_taxonomy(PREPARED_MANIFEST)


def identity(taxonomy):
    """The prepared taxonomy's identity as a sheet records it."""
    manifest = taxonomy['manifest']
    return {'name': manifest['name'], 'version': manifest['version']}


__all__ = ['AMBIGUOUS', 'PREPARED_MANIFEST', 'RESOLVED', 'UNKNOWN', 'identity', 'lineage', 'load_taxonomy',
           'prepared_taxonomy', 'resolve', 'taxon_row']
