"""Saved native612 bytes in explicitly synthetic producer/capture fault fixtures.

No native masking executable runs here. One test exercises the actual bounded
Python result-worker services; the other workers run inside the outer bounded
verification process for focused custody/projection tests.
"""
from unittest.mock import patch

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.jobs.sequence_masking.sequence_homology_evidence import native_blast_masking_result_worker as worker
from gene_annotation_episode.episodic_workflow.episode_support.calculations.sequence_masking.sequence_homology_evidence import sequence_masking_calculations as calculations
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_masking.sequence_homology_evidence.native_blast_masking_contracts import native_blast_digest
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_masking.sequence_homology_evidence.sequence_masking_result_views import project_masking_result


def selector(**changes):
    return {"version": "native_blast_masking_result_selector", "mode": "native_result",
        "records": {"mode": "all"}, "quantities": [], "statistics_fields": [],
        "statistics_unit_codes": [], "include_checks": False, "artifacts": [],
        "saved_data": [], "saved_sheet_ref": None, **changes}


