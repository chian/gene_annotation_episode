"""The sequence set an all-vs-all BLAST runs over: its records, its digest and its query chunks.

A set is one FASTA artifact held in custody. Every record's identity is the first token of its header and must be
unique, because the similarity graph names sequences by it. A large run is split into query chunks: contiguous
ordinal ranges of the set, each written as its own FASTA text, searched against the whole set. These functions are
pure: they read supplied text and return values; they open no file, hold no state and call no tool.
"""
from __future__ import annotations

import hashlib
import re

from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import (
    ContractError, parse_sequences)

_ALPHABET = re.compile(r"[A-Z*\-]+")


def parse_set_fasta(text):
    """The ordered records of a set as ``[{'id', 'length', 'ordinal'}]``. Ids are unique, every record has at least
    one letter, and a set has at least two records (a set of one has nothing to relate)."""
    if type(text) is not str:
        raise ValueError("blast_all_vs_all_set_text_required")
    try:
        parsed = parse_sequences(text, format="fasta", molecule="unspecified")
    except ContractError as error:
        raise ValueError("blast_all_vs_all_set_" + str(error)) from error
    records = []
    for record in parsed:
        if _ALPHABET.fullmatch(record.sequence) is None:
            raise ValueError("blast_all_vs_all_set_invalid_sequence_line")
        records.append((record.name, len(record.sequence.replace("-", ""))))
    ids = [name for name, _ in records]
    if len(set(ids)) != len(ids):
        raise ValueError("blast_all_vs_all_set_duplicate_record_id")
    if any(length < 1 for _, length in records):
        raise ValueError("blast_all_vs_all_set_empty_record")
    if len(records) < 2:
        raise ValueError("blast_all_vs_all_set_needs_two_records")
    return [{"id": name, "length": length, "ordinal": index} for index, (name, length) in enumerate(records)]


def set_summary(text):
    """The set's identity: content digest, record count, total letters. The total is the search space of every
    search against the whole set."""
    records = parse_set_fasta(text)
    return {"sha256": hashlib.sha256(text.encode()).hexdigest(), "record_count": len(records),
            "total_letters": sum(item["length"] for item in records)}


def chunk_ranges(record_count, chunk_count):
    """Contiguous ordinal ranges ``[(first, last), ...]`` (inclusive) covering ``record_count`` records in
    ``chunk_count`` pieces as even as possible, the earlier pieces one record longer when it does not divide."""
    if (type(record_count) is not int or type(chunk_count) is not int or record_count < 2
            or not 1 <= chunk_count <= record_count):
        raise ValueError("blast_all_vs_all_chunk_count_invalid")
    base, extra = divmod(record_count, chunk_count)
    ranges, start = [], 0
    for index in range(chunk_count):
        size = base + (1 if index < extra else 0)
        ranges.append((start, start + size - 1))
        start += size
    return ranges


def chunk_text(text, first, last):
    """The FASTA text of the records ``first`` to ``last`` (inclusive ordinals) of the set, in the set's own order
    and with its own header and sequence lines, so a chunk is exactly a slice of the set."""
    count = len(parse_set_fasta(text))
    if type(first) is not int or type(last) is not int or not 0 <= first <= last < count:
        raise ValueError("blast_all_vs_all_chunk_range_invalid")
    out, ordinal = [], -1
    for line in text.splitlines():
        if line.startswith(">"):
            ordinal += 1
        if first <= ordinal <= last and (line.startswith(">") or line.strip()):
            out.append(line)
    return "\n".join(out) + "\n"


def chunk_matches_set(set_text, chunk, first, last):
    """True when ``chunk`` is exactly the slice ``first``..``last`` of the set: the check that a declared chunk is
    what it claims to be."""
    return chunk == chunk_text(set_text, first, last)


__all__ = ["chunk_matches_set", "chunk_ranges", "chunk_text", "parse_set_fasta", "set_summary"]
