"""The original supplied inputs of an HPC plan.

This is a plan reader. It starts no job, observes no scheduler and
creates no receipt or execution authority.
"""
from collections.abc import Mapping
import hashlib

from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import ContractError


def planned_input_files(plan):
    """Read the original supplied inputs of an HPC plan.

    This is planned byte identity, not proof that a path was staged or executed.
    The actual received execution/result receipts remain separately required.
    """
    if 'supplied_files' not in plan:
        raise ContractError('hpc_scientific_original_plan_files_missing')
    rows = plan['supplied_files']
    if not isinstance(rows, (list, tuple)):
        raise ContractError('hpc_scientific_original_plan_files_invalid')
    seen = {}
    for row in rows:
        if (not isinstance(row, Mapping) or not isinstance(row.get('path'), str)
                or not isinstance(row.get('text'), str) or not isinstance(row.get('sha256'), str)):
            raise ContractError('hpc_scientific_original_plan_files_invalid')
        value = (row['text'], row['sha256'])
        if (hashlib.sha256(row['text'].encode()).hexdigest() != row['sha256']
                or seen.setdefault(row['path'], value) != value):
            raise ContractError('hpc_scientific_original_plan_files_bytes_conflict')
    return rows
