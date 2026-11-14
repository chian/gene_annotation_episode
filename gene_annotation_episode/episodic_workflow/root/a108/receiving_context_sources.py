"""Actual generic receiving-context source operands for this axis's existing hashes."""
from pathlib import Path
import hashlib

_REPOSITORY = Path(__file__).resolve().parents[4]
_RECEIVING_CONTEXT_SOURCES = (
    'gene_annotation_episode/__init__.py',
    'gene_annotation_episode/episodic_workflow/__init__.py',
    'gene_annotation_episode/episodic_workflow/root/__init__.py',
    'gene_annotation_episode/episodic_workflow/root/receiving_context.py',
)


def receiving_context_source_paths():
    return {key: _REPOSITORY / key for key in _RECEIVING_CONTEXT_SOURCES}


def receiving_context_source_bytes():
    return b''.join(path.read_bytes() for path in receiving_context_source_paths().values())


def receiving_context_source_fingerprints():
    return {key: hashlib.sha256(path.read_bytes()).hexdigest()
            for key, path in receiving_context_source_paths().items()}
