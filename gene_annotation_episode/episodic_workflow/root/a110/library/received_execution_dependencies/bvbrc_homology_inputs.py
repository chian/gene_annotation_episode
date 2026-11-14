from __future__ import annotations
FIELDS = ['qseqid', 'sseqid', 'pident', 'length', 'mismatch', 'gapopen', 'qstart', 'qend', 'sstart', 'send', 'evalue', 'bitscore', 'qlen', 'slen']
FORMATS = {'blast_json15_raw': 'blast_json15', 'homology_processed_json': 'homology_processed_json', 'blast_tabular': 'blast_tabular', 'blast_tabular_header': 'blast_tabular_header', 'homology_metadata_json': 'homology_metadata_json', 'blast_archive': 'blast_archive'}

def _text(value):
    return isinstance(value, str) and bool(value)

def _index(value):
    return type(value) is int and value >= 0
