"""Original molecular result constants and literal value helpers."""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.library.molecular_sequence_result_contracts import FACT_SOURCES

VERSION = "molecular_sequence_result_receipt_v1"

PUBLIC_VERSION = "molecular_sequence_public_result_v1"

PREFIX = "molecular_sequence_received_report_prefix"

POLICY = {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296}

def _json(raw):
    from gene_annotation_episode.episodic_workflow.root.library.molecular_sequence_driver import _json as decode
    return decode(raw)

def _facts():
    return {source: [] for source in FACT_SOURCES}

def _retained(identity, declaration=None):
    return dict(state="retained" if declaration is not None else "retained_undeclared", file=identity,
        declared=deepcopy(declaration), observed_identity={k: identity[k] for k in ("sha256", "size_bytes")}, failure=None)
