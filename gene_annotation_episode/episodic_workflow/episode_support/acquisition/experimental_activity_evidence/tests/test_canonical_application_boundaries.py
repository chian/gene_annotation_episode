"""Canonical infrastructure with genuine private validators and saved receipts.

Journal/request rows are context fixtures, not commissioned scientific work.
No scientific result, model call, publication producer or authority is simulated.
"""
from dataclasses import replace
from importlib import import_module
import json

import pytest

from gene_annotation_episode.domain import canonical
from gene_annotation_episode.state import Store
from method_loop import EpisodeGoal, EpisodeRequest
from method_loop.identities import EpisodeRef
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_context import LiteratureContext


PRIVATE = 'gene_annotation_episode.episodic_workflow.root.experimental_activity_evidence'
ROOT = 'gene_annotation_episode.episodic_workflow.root'
RUN = 'canonical-private-context-boundary'






def test_acquisition_failure_retains_original_operational_fields():
    error_type = import_module('gene_annotation_episode.episodic_workflow.episode_support.acquisition.experimental_activity_evidence.acquisition').AcquisitionError
    diagnostic, operational = {'phase': 'read'}, {'job': 'retained'}
    failure = error_type('read_failed', retry_after=2.5, job_ref='job:boundary',
        phase='download', submission_outcome='unavailable', diagnostic=diagnostic, operational=operational)
    assert type(failure) is import_module('gene_annotation_episode.acquisition').AcquisitionError
    assert failure.args == ('read_failed',) and failure.code == 'read_failed'
    assert failure.retry_after == 2.5 and failure.job_ref == 'job:boundary'
    assert failure.phase == 'download' and failure.submission_outcome == 'unavailable'
    assert failure.snapshot is None and failure.diagnostic is diagnostic and failure.operational is operational














