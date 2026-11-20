"""The controlled source class of a database hit: what kind of source a reference sequence came from.

The owner's point: a hit whose reference came from a cultured, closed genome or from a curated entry is a different
kind of evidence from one assembled out of a metagenome. This module records that difference as data, as a value of
a fixed vocabulary, and never as a weight. It does not grade reliability and it does not read a name, a title or a
description. It reads three explicitly reported fields of a hit's association, in this order:

1. ``origin['genome_notes']``: an exact entry that the table maps to a derived-source class (derived from a
   metagenome, derived from a single cell);
2. ``assembly['assembly_level']``: the assembly level the assembly report states;
3. ``origin['entry_type']``: the reviewed or unreviewed status a curated database states for its own entry.

The first of the three that is reported and found in its table decides the class, and the class's basis (which
field decided it) is returned beside it. A hit with none of them reported, or reported with a value the table does
not hold, is ``unclassified``: nothing is defaulted and nothing is guessed. The tables are parameters of the
function; the defaults hold only the exact values the two services document, and the real report's actual strings
must be checked against them in a real run before the classes are relied on.
"""
from collections import defaultdict

SOURCE_CLASSES = ('curated_reference', 'unreviewed_reference', 'complete_genome', 'chromosome_level_genome',
                  'scaffold_level_genome', 'contig_level_genome', 'metagenome_derived', 'single_cell_derived',
                  'unclassified')
BASES = ('genome_notes', 'assembly_level', 'entry_type')

DEFAULT_TABLES = {
    'genome_notes': {'derived from metagenome': 'metagenome_derived',
                     'derived from single cell': 'single_cell_derived'},
    'assembly_level': {'Complete Genome': 'complete_genome', 'Chromosome': 'chromosome_level_genome',
                       'Scaffold': 'scaffold_level_genome', 'Contig': 'contig_level_genome'},
    'entry_type': {'UniProtKB reviewed (Swiss-Prot)': 'curated_reference',
                   'UniProtKB unreviewed (TrEMBL)': 'unreviewed_reference'},
}


def _checked(tables):
    if (not isinstance(tables, dict) or set(tables) != set(BASES)
            or any(not isinstance(tables[name], dict) for name in BASES)):
        raise ValueError('blast_source_class_tables_invalid')
    for name in BASES:
        if any(type(key) is not str or value not in SOURCE_CLASSES or value == 'unclassified'
               for key, value in tables[name].items()):
            raise ValueError('blast_source_class_table_value_invalid:' + name)
    return tables


def source_class(association, tables=DEFAULT_TABLES):
    """``{'source_class', 'basis'}`` of one association of a hit: the class and the reported field that decided it
    (``None`` when the class is ``unclassified``)."""
    tables = _checked(tables)
    origin = association.get('origin') if isinstance(association.get('origin'), dict) else {}
    assembly = association.get('assembly') if isinstance(association.get('assembly'), dict) else {}
    notes = origin.get('genome_notes')
    for note in (notes if isinstance(notes, list) else []):
        if type(note) is str and note in tables['genome_notes']:
            return {'source_class': tables['genome_notes'][note], 'basis': 'genome_notes'}
    level = assembly.get('assembly_level')
    if type(level) is str and level in tables['assembly_level']:
        return {'source_class': tables['assembly_level'][level], 'basis': 'assembly_level'}
    entry = origin.get('entry_type')
    if type(entry) is str and entry in tables['entry_type']:
        return {'source_class': tables['entry_type'][entry], 'basis': 'entry_type'}
    return {'source_class': 'unclassified', 'basis': None}


def source_class_counts(sheet, tables=DEFAULT_TABLES):
    """The number of sequence groups of a saved database sheet that carry each class, as a list of
    ``{'source_class', 'sequence_group_count'}`` in the vocabulary's order, only for classes that occur.

    A sequence group counts once for each distinct class its hits' associations carry, so a group whose duplicate
    hits come from two kinds of source counts under both (the sheet's taxonomy counts the same way). A group with
    no association at all counts as ``unclassified``. Duplicate hits never raise a class's count."""
    groups = {group['group_index'] for group in sheet['sequence_groups']}
    classes = defaultdict(set)
    for hit in sheet['hits']:
        index = hit['sequence_group_index']
        for association in hit['associations']:
            classes[index].add(source_class(association, tables)['source_class'])
    counts = defaultdict(int)
    for index in groups:
        for value in (classes.get(index) or {'unclassified'}):
            counts[value] += 1
    return [{'source_class': value, 'sequence_group_count': counts[value]}
            for value in SOURCE_CLASSES if counts.get(value)]


__all__ = ['SOURCE_CLASSES', 'BASES', 'DEFAULT_TABLES', 'source_class', 'source_class_counts']
