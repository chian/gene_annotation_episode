"""The fixed original read library as a data target, and the identity of its lazy read-local subjects.

The library is a data target, never a biological sequence or organism. Its
position measure is disjoint original member-local symbols, not joined bases,
unique genes, independent molecules or recovered genome completeness. Its
membership, selections and scope arithmetic are the Store's, reached through
the scoped store.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import ContractError

VERSION = "fixed_original_read_position_measure_v1"


def is_library(row):
    return row.get("record_type") == "input" and row.get("target_kind") == "read_library"


def read_ref(library_ref, member_ref):
    # Existing content identities are 24 hex digits. Their pair fits the closed
    # persistent-ref syntax without a second row/file for each original read.
    if not library_ref.startswith("input_") or not member_ref.startswith("member_"):
        raise ContractError("invalid_original_read_identity")
    return "read_subject_" + library_ref[6:] + member_ref[7:]
